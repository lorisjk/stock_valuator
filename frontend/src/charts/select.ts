/**
 * Panel selection and the trailing-years window: the "which data" half of
 * build_valuation, kept apart from the "how it is drawn" half in panel.ts.
 *
 * Both functions are chart-agnostic. Items 5 (fundamentals) and 6 (growth) need
 * exactly this selection rule with a different chart id, and item 8 needs the
 * window with a different `years`.
 */
import type { ChartId, Frame, Registry } from "../contracts.ts";

/**
 * figures.py `_select_concepts`, over the registry instead of config.
 *
 * Two rules, both load-bearing:
 *
 * 1. Visibility is authoritative and comes first. `profile_visibility` keyed by
 *    the ticker's profile reproduces `get_plottable_metrics` exactly -- verified
 *    over all 1,827 (chart, ticker) pairs in registry_export_report.md -- so a
 *    metric the profile hides can never be surfaced by a request for it.
 * 2. A request only ever narrows. Unknown or hidden requests are dropped rather
 *    than refused, because one selection is handed to several tickers and a
 *    concept that is fine for one is routinely hidden for another.
 *
 * Order always follows `charts[chart].metric_ids`, never the request, so panel
 * order is stable no matter what order a picker sends.
 */
export function selectMetricIds(
  registry: Registry,
  chart: ChartId,
  ticker: string,
  requested?: readonly string[] | null,
): string[] {
  const profile = registry.ticker_profile[ticker] ?? registry.default_profile;
  const visibility = registry.profile_visibility[profile];
  if (!visibility) throw new Error(`registry has no visibility row for profile ${profile}`);

  const visible = registry.charts[chart].metric_ids.filter((id) => visibility[id]);
  if (requested == null) return visible;

  const wanted = new Set(requested);
  return visible.filter((id) => wanted.has(id));
}

/** Ids a picker may offer for this ticker: the visible catalogue, in order. */
export const offerableMetricIds = (registry: Registry, chart: ChartId, ticker: string) =>
  selectMetricIds(registry, chart, ticker, null);

/**
 * figures.py `_window_frame` with `as_of = None`: keep rows whose `end` is at or
 * after `anchor` minus `years` years.
 *
 * The anchor carries the time of day, exactly as `pd.Timestamp.today()` does, so
 * a row dated exactly `years` ago at midnight falls outside the window in both
 * implementations. `anchor` is a parameter rather than a call to `new Date()`
 * inside, so a test can pin it -- and so item 15 has somewhere to put `as_of`
 * without rewriting this.
 */
export function windowCutoff(years: number, anchor: Date = new Date()): Date {
  const cutoff = new Date(anchor.getTime());
  const day = cutoff.getUTCDate();
  cutoff.setUTCFullYear(cutoff.getUTCFullYear() - years);
  // 29 February minus five years is 28 February, not 1 March -- which is what
  // pandas' DateOffset does and what a naive setUTCFullYear does not.
  if (cutoff.getUTCDate() !== day) cutoff.setUTCDate(0);
  return cutoff;
}

export interface Series {
  /** Row indices into the frame, in frame order, for one concept in-window. */
  rows: number[];
  x: Date[];
  /** Nulls kept in place: a gap in coverage is information, not an absence. */
  y: (number | null)[];
}

/**
 * One concept's series out of a frame, windowed and sorted by date.
 *
 * `plot_metric` sorts by `end` before it does anything else, and the parquet is
 * not stored date-major within a (ticker, concept) group -- 110 groups across
 * the export are not even ascending -- so the sort is load-bearing rather than
 * cosmetic. It is stable, so equal dates keep their file order.
 */
export function seriesFor(frame: Frame, concept: string, cutoff: Date): Series {
  const rows: number[] = [];
  const cutoffMs = cutoff.getTime();
  for (let i = 0; i < frame.rowCount; i += 1) {
    if (frame.concept[i] === concept && frame.end[i].getTime() >= cutoffMs) rows.push(i);
  }
  rows.sort((a, b) => frame.end[a].getTime() - frame.end[b].getTime() || a - b);
  return {
    rows,
    x: rows.map((i) => frame.end[i]),
    y: rows.map((i) => frame.value[i]),
  };
}

/** figures.py's emptiness test: the panel is "No Data" when no row has a value. */
export const hasAnyValue = (series: Series) => series.y.some((v) => v !== null && !Number.isNaN(v));
