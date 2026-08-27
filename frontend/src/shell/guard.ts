/**
 * What went wrong with the export, in words a reader can act on -- item 24.
 *
 * **The frontend's failure modes are not Streamlit's.** `app.py` checks seven
 * files on disk before rendering anything (`missing_files`, app.py:97) and
 * `st.stop()`s with their names; a file is either there or it is not. A browser
 * fetches over HTTP at runtime and can instead get a 404, a 200 carrying
 * `index.html` because a dev server has an SPA fallback, JSON that does not
 * parse, or JSON that parses and declares a schema this build cannot read.
 *
 * Each of those needs a different sentence, because each has a different fix,
 * and "something went wrong" sends the reader to the wrong one. This module
 * turns an Error into that sentence and nothing else -- no React, so every
 * branch is reachable from a test.
 */
import { MissingTickerFile, SchemaMismatch } from "../contracts.ts";

export type FailureKind = "missing" | "malformed" | "schema" | "network" | "unknown";

export interface Diagnosis {
  kind: FailureKind;
  /** One line, shown as the heading. */
  headline: string;
  /** What to do about it. */
  remedy: string;
  /** True when this is a normal state of a partial dev bundle, not a fault. */
  expectedInDev: boolean;
}

const RUN_PIPELINE =
  'Run the pipeline first: python -c "from main import run_full_refresh; run_full_refresh()", ' +
  "then copy data/app/ into frontend/public/.";

/**
 * A syntax error from `response.json()` almost always means the server answered
 * an unknown path with `index.html` rather than 404 -- the SPA-fallback case
 * `load.ts` catches for ticker files. Saying so is the difference between a
 * five-minute fix and an afternoon.
 */
const looksLikeHtml = (message: string) =>
  /unexpected token '?</i.test(message) || /^JSON\.parse/i.test(message);

export function diagnose(error: Error, what: string): Diagnosis {
  if (error instanceof MissingTickerFile) {
    return {
      kind: "missing",
      headline: `No data bundled for ${error.ticker}.`,
      remedy:
        `frontend/public/tickers/ carries a subset of the export while the published ` +
        `bundle carries all of them. Pick another ticker, or copy ` +
        `data/app/tickers/${error.ticker}.json into frontend/public/tickers/.`,
      expectedInDev: true,
    };
  }
  if (error instanceof SchemaMismatch) {
    return {
      kind: "schema",
      headline: `${error.file} was written by a different version of the pipeline.`,
      remedy:
        `It declares schema ${String(error.found)} and this build reads schema ` +
        `${error.expected}. Re-run the export, or check out the frontend that matches it. ` +
        `The two are always written by the same run, so one of them is stale, not both.`,
      expectedInDev: false,
    };
  }
  if (looksLikeHtml(error.message)) {
    return {
      kind: "malformed",
      headline: `${what} did not come back as JSON.`,
      remedy:
        "A dev or preview server answers an unknown path with index.html instead of a 404, " +
        "so this usually means the file is not in frontend/public/ at all. " + RUN_PIPELINE,
      expectedInDev: true,
    };
  }
  if (/\b(404|4\d\d|5\d\d)\b/.test(error.message) || /failed to fetch/i.test(error.message)) {
    return {
      kind: "network",
      headline: `${what} could not be loaded.`,
      remedy: RUN_PIPELINE,
      expectedInDev: true,
    };
  }
  return {
    kind: "unknown",
    headline: `${what} could not be read.`,
    remedy: "The message below is the whole of what is known.",
    expectedInDev: false,
  };
}
