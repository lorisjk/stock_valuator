/**
 * Loading and reconstruction for the two contracts. No React in here on
 * purpose: everything below runs unchanged in Node, which is what makes the
 * verification against the Python builder possible.
 */
import {
  REGISTRY_SCHEMA,
  TICKER_SCHEMA,
  MissingTickerFile,
  SchemaMismatch,
  type ColumnarFrame,
  type Frame,
  type FrameName,
  type Frames,
  type Registry,
  type TickerFile,
} from "../contracts.ts";

/** The numeric column of each frame. facts_growth is the odd one out. */
const VALUE_COLUMN: Record<FrameName, string> = {
  metrics_long: "value",
  valuation_history: "value",
  facts_growth: "yoy_growth",
  current_snapshot: "value",
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

async function fetchJson(url: string): Promise<unknown> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${url} -- ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export const fetchRegistry = async (base = ""): Promise<Registry> =>
  parseRegistry(await fetchJson(`${base}/registry.json`));

export async function fetchTickerFrames(ticker: string, base = ""): Promise<Frames> {
  const url = `${base}/tickers/${ticker}.json`;
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
  return parseTickerFile(ticker, await response.json());
}
