/**
 * Loading and reconstruction for the two contracts. No React in here on
 * purpose: everything below runs unchanged in Node, which is what makes the
 * verification against the Python builder possible.
 */
import {
  CANDIDATES_SCHEMA,
  REGISTRY_SCHEMA,
  TICKER_SCHEMA,
  MissingTickerFile,
  SchemaMismatch,
  type ColumnarFrame,
  type ConceptCandidates,
  type Frame,
  type FrameName,
  type Frames,
  type Meta,
  type Registry,
  type TickerFile,
} from "../contracts.ts";

/** The numeric column of each frame. facts_growth is the odd one out. */
const VALUE_COLUMN: Record<FrameName, string> = {
  metrics_long: "value",
  valuation_history: "value",
  facts_growth: "yoy_growth",
  current_snapshot: "value",
  // facts_full carries `yoy_growth` too, and the data tab does not read it:
  // app.py's pivot_ticker takes `value` and the growth chart reads the separate
  // facts_growth frame. `ttm_source` and `ffo_gains_source` are likewise not
  // reconstructed -- ttm_source is item 19's cadence markers, and app.py has
  // never read ffo_gains_source at all (inventory §2.6).
  facts_full: "value",
};

/**
 * `YYYY-MM-DD` -> Date, parsed as UTC midnight.
 *
 * `new Date("2024-03-31")` already parses a bare date as UTC, but going through
 * Date.UTC states it rather than relying on that: every `end` in the export is a
 * period end at midnight, and a local-time parse would shift a whole series by a
 * day for anyone west of Greenwich.
 */
function parseDate(iso: string): Date {
  const year = Number(iso.slice(0, 4));
  const month = Number(iso.slice(5, 7));
  const day = Number(iso.slice(8, 10));
  return new Date(Date.UTC(year, month - 1, day));
}

/**
 * Column-major -> a small row-major struct of parallel arrays.
 *
 * Not an array of row objects: a 2,357-row facts slice would become 2,357
 * objects with the same four keys, and every panel then walks them again to
 * pull two columns back out. Parallel arrays keep the export's own shape, cost
 * one pass, and hand plotly exactly what it wants -- an `x` array and a `y`
 * array.
 *
 * Nothing here sorts, filters or fills. Row `i` stays row `i`.
 */
export function reconstructFrame(name: FrameName, block: ColumnarFrame): Frame {
  const index = (column: string) => {
    const at = block.columns.indexOf(column);
    if (at < 0) {
      throw new Error(`${name}: exported columns ${JSON.stringify(block.columns)} have no ${column}`);
    }
    return at;
  };
  const endColumn = block.data[index("end")] as string[];
  const conceptColumn = block.data[index("concept")] as string[];
  const valueColumn = block.data[index(VALUE_COLUMN[name])] as (number | null)[];

  const lengths = new Set(block.data.map((column) => column.length));
  if (lengths.size > 1) {
    throw new Error(`${name}: columns have different lengths ${[...lengths].join(", ")}`);
  }

  const nonfiniteRows = new Map<number, "Infinity" | "-Infinity">();
  const sidecar = block.nonfinite?.[VALUE_COLUMN[name]];
  if (sidecar) {
    for (const [row, sign] of Object.entries(sidecar)) nonfiniteRows.set(Number(row), sign);
  }

  return {
    columns: block.columns,
    rowCount: endColumn.length,
    end: endColumn.map(parseDate),
    concept: conceptColumn,
    // The +-inf positions keep the `null` the exporter put there. A chart cannot
    // draw an infinity, and the Python builder does not either -- np.isfinite
    // gates the mean line, and a trace point at Infinity would blow the y range
    // for every other point in the panel. The sidecar is carried alongside so a
    // panel can say the value is infinite rather than missing; nothing in this
    // task reads it yet, and that is the deliberate part.
    value: valueColumn,
    nonfiniteRows,
  };
}

function checkSchema(file: string, found: unknown, expected: number): void {
  if (found !== expected) throw new SchemaMismatch(file, expected, found);
}

export function parseRegistry(raw: unknown): Registry {
  const registry = raw as Registry;
  checkSchema("registry.json", registry?.schema, REGISTRY_SCHEMA);
  return registry;
}

export function parseTickerFile(ticker: string, raw: unknown): Frames {
  const file = raw as TickerFile;
  checkSchema(`tickers/${ticker}.json`, file?.schema, TICKER_SCHEMA);
  if (file.ticker !== ticker) {
    throw new Error(`tickers/${ticker}.json declares ticker ${JSON.stringify(file.ticker)}`);
  }
  const frames: Frames = {};
  for (const [name, block] of Object.entries(file.frames)) {
    if (block) frames[name as FrameName] = reconstructFrame(name as FrameName, block);
  }
  return frames;
}

/**
 * `tickers/{TICKER}.facts.json` -> the one `facts_full` frame it carries.
 *
 * Separate from `parseTickerFile` rather than folded into it, because the two
 * files are fetched at different times for different reasons and a shared
 * parser would have to be told which frames to expect anyway.
 */
export function parseTickerFactsFile(ticker: string, raw: unknown): Frame {
  const file = raw as TickerFile;
  checkSchema(`tickers/${ticker}.facts.json`, file?.schema, TICKER_SCHEMA);
  if (file.ticker !== ticker) {
    throw new Error(`tickers/${ticker}.facts.json declares ticker ${JSON.stringify(file.ticker)}`);
  }
  const block = file.frames.facts_full;
  if (!block) throw new Error(`tickers/${ticker}.facts.json carries no facts_full frame`);
  return reconstructFrame("facts_full", block);
}

export function parseCandidates(raw: unknown): ConceptCandidates {
  const candidates = raw as ConceptCandidates;
  checkSchema("concept_candidates.json", candidates?.schema, CANDIDATES_SCHEMA);
  return candidates;
}

/**
 * `get_concept_candidates(ticker)`'s keys, as a set.
 *
 * A ticker with no entry gets an **empty** set, and that is the honest answer
 * rather than a fallback: without the candidate list there is no way to say
 * which of its concepts EDGAR was asked for, and an empty set makes every
 * concept read as derived, which is visible in the UI. Guessing a variant would
 * silently mislabel the split this file exists to decide. The validator asserts
 * the candidates cover the universe, so this path means the export is broken.
 */
export function candidatesFor(candidates: ConceptCandidates, ticker: string): Set<string> {
  const at = candidates.ticker_variant[ticker];
  const variant = at === undefined ? undefined : candidates.variants[at];
  return new Set(variant ? Object.keys(variant) : []);
}

async function fetchJson(url: string): Promise<unknown> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${url} -- ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export const fetchRegistry = async (base = ""): Promise<Registry> =>
  parseRegistry(await fetchJson(`${base}/registry.json`));

/**
 * `meta.json`, read leniently: no schema check, no required fields.
 *
 * Unlike the two contracts above this file is not interpreted, only displayed,
 * so a version drift degrades one caption instead of the app. The caller
 * compares `schema` against META_SCHEMA itself and decides what to say.
 */
export const fetchMeta = async (base = ""): Promise<Meta> =>
  (await fetchJson(`${base}/meta.json`)) as Meta;

/**
 * The update notice's raw markdown, or null when there is none.
 *
 * "No file" is a normal answer here, not a failure: `read_content` (app.py:114)
 * returns "" for an absent or unreadable file precisely so that "nothing to
 * say" needs no special case. A dev server's SPA fallback answers 200 with
 * index.html, so the content type is checked as well as the status -- the same
 * trap fetchTickerFrames documents.
 */
export async function fetchNotice(base = ""): Promise<string | null> {
  try {
    const response = await fetch(`${base}/update_notice.md`);
    if (!response.ok) return null;
    const type = response.headers.get("content-type") ?? "";
    if (type.includes("html")) return null;
    return await response.text();
  } catch {
    return null;
  }
}

/**
 * `concept_candidates.json`, 7.8 kB gzipped.
 *
 * Fetched on demand rather than at mount, on the registry export report's own
 * recommendation (§5): it is 3x `registry.json` raw and is needed by the data
 * tab and item 16's Raw Facts tab only, so putting it in the first paint would
 * make every reader pay for the raw/derived split whether or not they open a
 * table.
 */
export const fetchCandidates = async (base = ""): Promise<ConceptCandidates> =>
  parseCandidates(await fetchJson(`${base}/concept_candidates.json`));

async function fetchTickerJson(ticker: string, url: string): Promise<unknown> {
  const response = await fetch(url);
  // A missing file here is a bundling fact, not a broken app: the picker offers
  // all 609 tickers because universe.json lists them, and the dev bundle
  // carries a subset. Saying which of the two it is saves the next reader a
  // debug session.
  //
  // Two ways it shows up, and both have to be caught. A static host answers
  // 404. A dev/preview server with an SPA fallback answers 200 with index.html,
  // which would otherwise surface as an unexplained JSON parse error -- so the
  // content type is checked as well as the status.
  const contentType = response.headers.get("content-type") ?? "";
  if (response.status === 404 || (response.ok && !contentType.includes("json"))) {
    throw new MissingTickerFile(ticker, url);
  }
  if (!response.ok) throw new Error(`${url} -- ${response.status} ${response.statusText}`);
  return response.json();
}

export const fetchTickerFrames = async (ticker: string, base = ""): Promise<Frames> =>
  parseTickerFile(ticker, await fetchTickerJson(ticker, `${base}/tickers/${ticker}.json`));

/**
 * A ticker's `facts_full` slice -- the data tab's largest section and item 16's
 * whole input, 21 kB gzipped against the core file's 14 kB.
 *
 * A separate fetch from `fetchTickerFrames` because it is a separate file, and
 * a separate file because the export split it: on a night without new filings
 * `facts_full` does not change at all, and no chart tab ever needs it.
 */
export const fetchTickerFacts = async (ticker: string, base = ""): Promise<Frame> =>
  parseTickerFactsFile(ticker, await fetchTickerJson(ticker, `${base}/tickers/${ticker}.facts.json`));
