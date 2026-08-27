/**
 * Types for the two export contracts this frontend consumes.
 *
 * Both files carry a `schema` integer and both are produced by the same
 * pipeline run (main.py's export_for_app writes them before meta.json), so a
 * mismatch means the app is newer or older than the data it is being handed --
 * never that one half of the export is stale relative to the other.
 *
 * These are hand-written from `registry_export_report.md` and
 * `per_ticker_export_report.md`. Nothing here is `any`: a field that is absent
 * in the data is optional here, and a field that is nullable is `| null`.
 */

export const REGISTRY_SCHEMA = 1;
export const TICKER_SCHEMA = 1;
/** `concept_candidates.json`, the registry export's second file. */
export const CANDIDATES_SCHEMA = 1;

/**
 * `meta.json`'s schema, as `main.py`'s APP_EXPORT_SCHEMA currently writes it.
 *
 * **Not enforced the way the other two are**, and the difference is deliberate.
 * The registry and the per-ticker files are *interpreted* -- a version this
 * build cannot read means it cannot draw anything, so a mismatch is fatal.
 * `meta.json` feeds one caption. A mismatch there is worth saying out loud and
 * is not worth refusing to start over, so `Shell` shows the freshness block it
 * can and flags the version rather than replacing the app with an error.
 *
 * That is not hypothetical: the export currently in `data/app/` and
 * `frontend/public/` declares **schema 2**, predates the registry and
 * per-ticker blocks `main.py` now writes into it, and is therefore stale
 * against the very `registry.json` sitting beside it. See the report.
 */
export const META_SCHEMA = 4;

/* -------------------------------------------------------------- registry.json */

export type ChartId = "fundamentals" | "valuation" | "growth";

/** What an id in a chart names, and which column of the frame holds its values. */
export interface ChartSpec {
  /** "metric" for fundamentals/valuation, "xbrl_concept" for growth. */
  id_namespace: "metric" | "xbrl_concept";
  /** "value" for fundamentals/valuation, "yoy_growth" for growth. */
  value_column: "value" | "yoy_growth";
  /** Catalogue order. Panel order follows this, never the user's pick order. */
  metric_ids: string[];
}

export interface Metric {
  id: string;
  chart: ChartId;
  label: string;
  ref_line: number | null;
  percent: boolean;
  quarterly: boolean;
  harmonic: boolean;
  label_de: string | null;
  description: string | null;
  formula: string | null;
  documented: boolean;
  id_namespace: ChartSpec["id_namespace"];
  value_column: ChartSpec["value_column"];
}

export interface Registry {
  schema: number;
  generated_at: string;
  language_primary: string;
  default_profile: string;
  charts: Record<ChartId, ChartSpec>;
  metrics: Metric[];
  undocumented: string[];
  /** {profile: {metric_id: visible}} -- straight from config.is_hidden. */
  profile_visibility: Record<string, Record<string, boolean>>;
  ticker_profile: Record<string, string>;
  quarterly_counterpart: Record<string, string>;
  harmonic_mean_concepts: string[];
  notes: { growth_mechanism: string; valuation_mechanism: string };
}

/* -------------------------------------------------------------- meta.json */

/**
 * Run provenance, for the sidebar's freshness block (`render_freshness`,
 * app.py:619). Every field is optional because this file is read leniently --
 * see META_SCHEMA.
 */
export interface Meta {
  schema?: number;
  run_start?: string;
  exported_at?: string;
  period?: string;
  tickers_requested?: number;
  tickers_with_data?: number;
  tickers_without_data?: string[];
}

/* ------------------------------------------------------ tickers/{TICKER}.json */

/**
 * The four frames in `tickers/{TICKER}.json` -- 14 kB gzipped, and what every
 * chart tab needs.
 */
export type CoreFrameName =
  | "metrics_long"
  | "valuation_history"
  | "facts_growth"
  | "current_snapshot";

/**
 * The one frame in `tickers/{TICKER}.facts.json`, split off because it is 62%
 * of a ticker's payload on its own (per_ticker_export_report §1.1). No chart
 * reads it; the data tab and item 16's Raw Facts tab do, so it is fetched when
 * one of them is opened and never before.
 */
export type FactsFrameName = "facts_full";

export type FrameName = CoreFrameName | FactsFrameName;

/** One frame's slice, column-major, exactly as the exporter writes it. */
export interface ColumnarFrame {
  columns: string[];
  /** One array per column, all the same length. `null` is a real null. */
  data: (string | number | null)[][];
  /**
   * JSON cannot carry +-inf. Where one occurred the value array holds `null`
   * and the true value is here, keyed by column name then row index as a
   * string. Absent when there were none.
   */
  nonfinite?: Record<string, Record<string, "Infinity" | "-Infinity">>;
}

export interface TickerFile {
  schema: number;
  ticker: string;
  frames: Partial<Record<FrameName, ColumnarFrame>>;
}

/* ------------------------------------------------- concept_candidates.json */

/**
 * `get_concept_candidates(ticker)`, deduplicated.
 *
 * 577 of 609 tickers resolve to their profile's baseline verbatim, so the
 * resolved dicts collapse to **39 variants** and each ticker points at one by
 * index -- 11.7x smaller than inlining, and lossless
 * (registry_export_report §2.2).
 *
 * Only the **keys** matter here. They are the concept names the pipeline asked
 * EDGAR for, which is exactly what makes everything else in `facts_full`
 * derived; the tag lists and `mode`/`point_in_time` flags inside each entry
 * describe the extraction and nothing in the browser reads them.
 */
export interface ConceptCandidates {
  schema: number;
  /** One resolved `{concept: spec}` dict per variant. */
  variants: Record<string, unknown>[];
  /** `{ticker: index into variants}`, covering every universe ticker. */
  ticker_variant: Record<string, number>;
}

/* ------------------------------------------------------------ reconstruction */

/**
 * A frame after reconstruction: row-major, dates parsed once, nulls preserved.
 *
 * Row `i` of every array belongs to row `i` of the parquet slice -- the export
 * report established that column-major reconstructs the slice row for row with
 * no ordering assumption, and nothing here sorts or filters, so that property
 * survives into the browser.
 */
export interface Frame {
  /** Column names in the parquet's order, `ticker` excluded. */
  columns: string[];
  rowCount: number;
  /** Parsed once at load, never per render. */
  end: Date[];
  concept: string[];
  /** The numeric column: `value`, or `yoy_growth` for facts_growth. */
  value: (number | null)[];
  /**
   * Row indices whose `value` was +-inf in the pipeline. The value array holds
   * `null` at these positions -- see reconstructFrame for the reasoning.
   */
  nonfiniteRows: Map<number, "Infinity" | "-Infinity">;
}

export type Frames = Partial<Record<FrameName, Frame>>;

/** A per-ticker file that is not in this bundle -- distinct from a real failure. */
export class MissingTickerFile extends Error {
  ticker: string;
  url: string;
  constructor(ticker: string, url: string) {
    super(
      `No data bundled for ${ticker} (${url} returned 404). The dev bundle in ` +
        `frontend/public/tickers/ carries a subset; the published export carries all 609.`,
    );
    this.name = "MissingTickerFile";
    this.ticker = ticker;
    this.url = url;
  }
}

export class SchemaMismatch extends Error {
  file: string;
  expected: number;
  found: unknown;
  constructor(file: string, expected: number, found: unknown) {
    super(
      `${file} has schema ${String(found)}, this build expects ${expected}. ` +
        `Re-run the pipeline export, or check out the frontend that matches it.`,
    );
    this.name = "SchemaMismatch";
    this.file = file;
    this.expected = expected;
    this.found = found;
  }
}
