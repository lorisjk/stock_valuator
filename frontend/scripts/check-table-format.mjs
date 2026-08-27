/**
 * Does every cell in the data tab's numeric tables carry a display format?
 *
 * The companion to `check-chart-width.mjs`, and it exists for the same reason:
 * the harness that actually proves this correct compares 4,390,657 rendered
 * strings against `app.py`'s `format_for_display`, and it needs Python, pandas
 * and the parquet export to do it. That harness is the authority; it cannot run
 * from this directory. This one can, and it catches the failure the operator
 * actually reported -- a table full of `82300000000` where `82.30B` belongs.
 *
 * It asserts **shape, not value**: every cell of the four numeric sections must
 * match one of the three treatments `format_for_display` can produce, or be one
 * of the three non-values the table draws deliberately.
 *
 *     absolute   -1,234.56K   (2 decimals, optional T/B/M/K, grouped)
 *     percent    -12.34%      (2 decimals)
 *     ratio      -1.2345      (exactly 4 decimals)
 *     not a value   ""  |  em dash  |  +-infinity
 *
 * A raw `82300000000` matches none of them, and neither does a `0.1730` that
 * should have been `17.30%` -- the second only if the wrong *rule* was applied
 * to a whole column, which shape alone cannot see. That limit is real and is
 * why this is the complement to the Python comparison rather than a replacement
 * for it.
 *
 * Run it: start the dev server, then
 *
 *     node scripts/check-table-format.mjs
 *     APP_URL=http://localhost:5187 node scripts/check-table-format.mjs
 *
 * Launches its own headless browser, exits non-zero on a mismatch. Deliberately
 * not wired into `npm test` or CI, for the reason the width check gives.
 */
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const APP = process.env.APP_URL ?? "http://localhost:5173";
const PORT = Number(process.env.CDP_PORT ?? 9223);
const BROWSER =
  process.env.BROWSER_PATH ??
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";

/**
 * Tickers worth walking. AUR and DDOG are the two whose tables carry all three
 * treatments at once; CEG's EPS columns hold the infinities that decide a whole
 * column's rule; WAT is the largest pivot in the universe.
 */
const TICKERS = (process.env.TICKERS ?? "AAPL,JPM,AUR,DDOG,CEG,CRWV,WAT").split(",");

const sleep = (ms) => new Promise((ok) => setTimeout(ok, ms));
const profile = mkdtempSync(join(tmpdir(), "table-format-"));
const browser = spawn(BROWSER, [
  "--headless=new", "--disable-gpu", "--no-sandbox", "--window-size=1600,1100",
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, "about:blank",
], { stdio: "ignore" });

let ws;
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

// The four sections `format_for_display` covers. Quality flags (index 2) are
// excluded on purpose -- app.py formats them elsewhere and item 18 owns them.
const NUMERIC_SECTIONS = [0, 1, 3, 4];

const ABSOLUTE = /^-?\d{1,3}(,\d{3})*\.\d{2}[TBMK]?$/;
const PERCENT = /^-?\d+\.\d{2}%$/;
const RATIO = /^-?\d+\.\d{4}$/;
const NOT_A_VALUE = /^(|—|∞|−∞)$/;

try {
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

  for (const ticker of TICKERS) {
    await send("Page.navigate", { url: `${APP}/?tf=${ticker}#/analysis/${ticker}/data` });
    await waitFor("document.querySelectorAll('.data-tab table').length >= 4", `${ticker}'s tables`);
    await sleep(1600);
    const cells = JSON.parse(await evaluate(`JSON.stringify((() => {
      const secs = [...document.querySelectorAll('.data-tab .section')];
      const out = [];
      for (const i of ${JSON.stringify(NUMERIC_SECTIONS)}) {
        const s = secs[i]; const t = s && s.querySelector('table'); if (!t) continue;
        const title = s.querySelector('h2').textContent;
        const heads = [...t.querySelectorAll('thead th')].slice(1).map(th => th.textContent);
        for (const tr of t.querySelectorAll('tbody tr')) {
          const row = tr.querySelector('th').textContent;
          [...tr.querySelectorAll('td')].forEach((td, c) => {
            out.push([title, row, heads[c] ?? String(c), td.textContent]);
          });
        }
      }
      return out;
    })())`));

    for (const [section, row, column, text] of cells) {
      checked += 1;
      if (NOT_A_VALUE.test(text) || ABSOLUTE.test(text) || PERCENT.test(text) || RATIO.test(text)) continue;
      failures.push(`${ticker} / ${section} / ${row} / ${column}: ${JSON.stringify(text)}`);
    }
    console.log(`  ${ticker}: ${checked} cells so far, ${failures.length} unformatted`);
  }

  for (const f of failures.slice(0, 20)) console.error(`FAIL ${f}`);
  if (failures.length > 20) console.error(`... and ${failures.length - 20} more`);
  console.log(`${checked - failures.length}/${checked} cells carry a display format`);
  process.exitCode = failures.length ? 1 : 0;
} finally {
  stop();
}
