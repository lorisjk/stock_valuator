/**
 * Does every chart render at the width of the box it is in?
 *
 * This exists because the item-8 harness cannot answer that question and never
 * could. That harness compares *figure specs* -- `fig.data`, `fig.layout`,
 * every trace and annotation -- and a byte-identical spec still renders at
 * 700px inside a 1204px container if nothing tells plotly the container
 * changed size. Three cycles closed a width defect and the fourth reopened one,
 * each time found only by someone looking at a screenshot.
 *
 * The invariant is deliberately **not** a golden pixel number. The last two
 * cycles recorded `1189px expanded / 1531px collapsed` as the baseline, and
 * those turned out to be the content box *with a vertical scrollbar present* --
 * correct, but 15px off the same page without one, which makes them a poor
 * thing to assert. What is actually invariant, at any viewport and either
 * scrollbar state, is:
 *
 *     the plot's container width === the rendered <svg>'s width
 *
 * Run it: start the dev server, then
 *
 *     node scripts/check-chart-width.mjs                 # http://localhost:5173
 *     APP_URL=http://localhost:5185 node scripts/check-chart-width.mjs
 *
 * It launches its own headless browser and exits non-zero on a mismatch.
 * Deliberately not wired into `npm test` or CI: it needs a running server and a
 * real Edge/Chrome, and a check that cannot run is worse than one that is asked
 * for by name.
 */
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const APP = process.env.APP_URL ?? "http://localhost:5173";
const TICKER = process.env.TICKER ?? "AAPL";
const PORT = Number(process.env.CDP_PORT ?? 9222);
const BROWSER =
  process.env.BROWSER_PATH ??
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";

/** Landing tab -> chart tab. The first three are the ones that mount a chart hidden. */
const ENTRY_TABS = ["data", "raw", "comparison", "valuation"];
const CHART_TABS = ["Growth (YoY)", "Fundamentals", "Valuation"];

const sleep = (ms) => new Promise((ok) => setTimeout(ok, ms));
const profile = mkdtempSync(join(tmpdir(), "chart-width-"));
const browser = spawn(BROWSER, [
  "--headless=new", "--disable-gpu", "--no-sandbox", "--window-size=1600,1100",
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, "about:blank",
], { stdio: "ignore" });

let ws;
// Best-effort, all of it: on Windows the browser still holds files in its
// profile directory for a moment after `kill()`, and an EPERM from the cleanup
// must never be what this script reports instead of the result it came for.
const stop = () => {
  try { ws?.close(); } catch { /* already gone */ }
  try { browser.kill(); } catch { /* already gone */ }
  try { rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 }); }
  catch { /* the OS will collect it */ }
};

let id = 0;
const pending = new Map();
const send = (method, params = {}) =>
  new Promise((ok) => { id += 1; pending.set(id, ok); ws.send(JSON.stringify({ id, method, params })); });
const evaluate = async (expression) =>
  (await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }))
    .result?.result?.value;
const waitFor = async (expression, label) => {
  for (let i = 0; i < 200; i += 1) { if (await evaluate(expression)) return; await sleep(200); }
  throw new Error(`timed out waiting for ${label}`);
};

try {
  // The browser needs a moment before its debugging port answers.
  let page = null;
  for (let i = 0; page === null; i += 1) {
    try {
      const targets = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      page = targets.find((t) => t.type === "page") ?? null;
    } catch (e) {
      if (i > 40) throw e;
    }
    if (page === null) await sleep(250);
  }
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((ok, no) => { ws.addEventListener("open", ok); ws.addEventListener("error", no); });
  ws.addEventListener("message", (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  });
  await send("Page.enable");

  const failures = [];
  let checked = 0;
  let run = 0;

  for (const entry of ENTRY_TABS) {
    for (const chart of CHART_TABS) {
      run += 1;
      // A distinct query string forces a real reload; a hash-only change does not.
      await send("Page.navigate", { url: `${APP}/?cw=${run}#/analysis/${TICKER}/${entry}` });
      await waitFor("!!document.querySelector('.tabs')", `the shell on ${entry}`);
      await sleep(1800);
      await evaluate(
        `[...document.querySelectorAll('.tabs .tab')].find(b => b.textContent.trim() === ${JSON.stringify(chart)})?.click()`);
      await waitFor("!!document.querySelector('.js-plotly-plot .main-svg')", `${chart} after ${entry}`);
      await sleep(1600);

      for (const sidebar of ["expanded", "collapsed"]) {
        if (sidebar === "collapsed") {
          await evaluate("document.querySelector('.sidebar__close')?.click()");
          await sleep(1200);
        }
        const seen = JSON.parse(await evaluate(`JSON.stringify({
          container: Math.round(document.querySelector('.js-plotly-plot').getBoundingClientRect().width),
          svg: Number(document.querySelector('.js-plotly-plot .main-svg').getAttribute('width')),
        })`));
        checked += 1;
        if (seen.container !== seen.svg) {
          failures.push(`${entry} -> ${chart}, sidebar ${sidebar}: container ${seen.container}px, svg ${seen.svg}px`);
        }
      }
    }
  }

  for (const f of failures) console.error(`FAIL ${f}`);
  console.log(`${checked - failures.length}/${checked} chart renders fill their container`);
  process.exitCode = failures.length ? 1 : 0;
} finally {
  stop();
}
