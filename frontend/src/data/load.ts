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

/** The *primary* numeric column of each frame. facts_growth is the odd one out. */
const VALUE_COLUMN: Record<FrameName, string> = {
  metrics_long: "value",
  valuation_history: "value",
  facts_growth: "yoy_growth",
  current_snapshot: "value",
  // facts_full carries `yoy_growth` too, and the data tab does not read it:
  // app.py's pivot_ticker takes `value` and the growth chart reads the separate
  // facts_growth frame.
  facts_full: "value",
};

/**
 * The non-numeric columns each frame carries through, beyond `end`/`concept`.
 *
 * A map keyed by column name rather than a named field on `Frame`, and the
 * reason is the second entry that is *not* here. `facts_full` exports two
 * provenance columns built by the same instrument -- `ttm_source` (config.py:213
 * "How a <concept>_TTM value was derived") and `ffo_gains_source` (config.py:216
 * "Same instrument as ttm_source and for the same reason"). Only the first is
 * read: `cadence_markers` (app.py:257) is the sole consumer of either, and
 * **app.py never reads `ffo_gains_source` at all** -- inventory §2.6 records it
 * as exported-and-unused and §6's decision list keeps "surface it or stop
 * exporting it" open. Surfacing it here would be deciding that on the
 * reference's behalf.
 *
 * So the shape is the convention and the list is the scope: adding
 * `"ffo_gains_source"` to this array is the whole change, whenever that decision
 * is made, and until then there is one convention rather than a named field for
 * one column and an argument about the next.
 *
 * A column named here that the export does not carry is skipped rather than
 * thrown on -- the frames' schema version gates real contract drift, and an
 * older bundle missing a provenance column should degrade to "no markers", which
 * is exactly what `cadence_markers` does with a frame that has no `ttm_source`
 * (app.py:272).
 */
const TEXT_COLUMNS: Partial<Record<FrameName, readonly string[]>> = {
  facts_full: ["ttm_source"],
};

/**
 * Numeric columns beyond the primary one, by frame. Same convention as
 * `TEXT_COLUMNS`, and same tolerance: a column named here that the export does
 * not carry is skipped rather than thrown on.
 *
 * `facts_growth` carries both growth modes on the same rows -- `yoy_growth` is
 * the primary and `qoq_growth` is here -- because the mode is a control on the
 * chart, not a second fetch. The two are 30 kB apart in a ticker file; loading
 * one and fetching the other on toggle would put a network round-trip behind a
 * checkbox.
 *
 * `facts_full` carries `yoy_growth` too and is deliberately not listed: the data
 * tab pivots it on `value` and reads no growth column at all (app.py's
 * `pivot_ticker`), so listing it would allocate a 2,357-element array per ticker
 * for nothing.
 */
const EXTRA_NUMERIC_COLUMNS: Partial<Record<FrameName, readonly string[]>> = {
  facts_growth: ["qoq_growth"],
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
  // The primary column is `index`, not a lenient lookup: a frame arriving
  // without the column its charts draw is contract drift, not a degraded
  // bundle, and `facts_growth` without `yoy_growth` has to say so here.
  const valueColumn = block.data[index(VALUE_COLUMN[name])] as (number | null)[];

  const lengths = new Set(block.data.map((column) => column.length));
  if (lengths.size > 1) {
    throw new Error(`${name}: columns have different lengths ${[...lengths].join(", ")}`);
  }

  const readSidecar = (column: string) => {
    const rows = new Map<number, "Infinity" | "-Infinity">();
    const sidecar = block.nonfinite?.[column];
    if (sidecar) {
      for (const [row, sign] of Object.entries(sidecar)) rows.set(Number(row), sign);
    }
    return rows;
  };
  const nonfiniteRows = readSidecar(VALUE_COLUMN[name]);

  const numeric = new Map<string, readonly (number | null)[]>([
    [VALUE_COLUMN[name], valueColumn],
  ]);
  const nonfinite = new Map<string, ReadonlyMap<number, "Infinity" | "-Infinity">>([
    [VALUE_COLUMN[name], nonfiniteRows],
  ]);
  for (const column of EXTRA_NUMERIC_COLUMNS[name] ?? []) {
    const at = block.columns.indexOf(column);
    if (at < 0) continue;
    numeric.set(column, block.data[at] as (number | null)[]);
    nonfinite.set(column, readSidecar(column));
  }

  const text = new Map<string, readonly (string | null)[]>();
  for (const column of TEXT_COLUMNS[name] ?? []) {
    const at = block.columns.indexOf(column);
    if (at >= 0) text.set(column, block.data[at] as (string | null)[]);
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
    numeric,
    nonfiniteRows,
    nonfinite,
    // Row `i` of every array is the same export row, this one included, which is
    // what lets a caller pair a provenance label with the value it describes
    // without a join.
    text,
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
 * `about.md`'s raw markdown, or null when it is not there.
 *
 * `fetchNotice`'s twin, deliberately down to the two guards -- a non-ok status
 * and an `html` content type, because a dev or preview server answers an unknown
 * path with `index.html` at status 200 and the body would otherwise be rendered
 * as the About page.
 *
 * **Where the two part company is what the caller does with `null`.** For the
 * notice, absent means "nothing to announce" and the box is simply not drawn
 * (app.py:114's docstring says so). For About, `render_about` (app.py:748-756)
 * calls the same absence *"a deployment mistake rather than a valid state, so
 * unlike the notice it says so -- but it still must not raise."* Same lenient
 * fetch, opposite reading; the difference lives in `About.tsx`, not here.
 */
export async function fetchAbout(base = ""): Promise<string | null> {
  try {
    const response = await fetch(`${base}/about.md`);
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
