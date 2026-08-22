/**
 * `build_valuation`, client-side: selection, then the drawing layer.
 *
 * The two halves stay apart. Everything specific to *this* chart is in this
 * file -- which frame, which chart id, the 400px row height, the title, the
 * mean line. Items 5 and 6 are the same twenty lines against a different frame
 * and different per-panel furniture, over the same `panel.ts`.
 */
import type { Frames, Registry } from "../contracts.ts";
import { meanOver } from "./mean.ts";
import { createGrid, drawPanel, type FigureSpec, type PanelSpec } from "./panel.ts";
import { hasAnyValue, seriesFor, selectMetricIds, windowCutoff } from "./select.ts";

/** figures.py: `_size(width, height, 500 * cols, 400 * rows)`. */
export const VALUATION_ROW_HEIGHT = 400;
export const VALUATION_YEARS = 5;

export interface ValuationOptions {
  /** null = the whole visible catalogue, as `concepts=None` does in Python. */
  requested?: readonly string[] | null;
  years?: number;
  /** Injectable so a test can pin "today"; `_window_frame`'s anchor. */
  anchor?: Date;
}

export interface ValuationResult {
  /** null when nothing is visible -- `build_valuation` returns None there. */
  figure: FigureSpec | null;
  /** Panel ids in catalogue order. Empty when the figure is null. */
  panels: string[];
  /** Every id the ticker's profile allows, for a picker. */
  offerable: string[];
}

export function buildValuation(
  registry: Registry,
  frames: Frames,
  ticker: string,
  options: ValuationOptions = {},
): ValuationResult {
  const { requested = null, years = VALUATION_YEARS, anchor } = options;
  const byId = new Map(registry.metrics.map((m) => [m.id, m]));

  const offerable = selectMetricIds(registry, "valuation", ticker, null);
  const panels = selectMetricIds(registry, "valuation", ticker, requested);

  // build_valuation prints and returns None. There is no figure to draw and no
  // grid to size, so the caller renders a message instead -- see ValuationChart.
  if (panels.length === 0) return { figure: null, panels: [], offerable };

  const frame = frames.valuation_history;
  const figure = createGrid(panels, VALUATION_ROW_HEIGHT, `Valuation Data ${ticker}`);
  const cutoff = windowCutoff(years, anchor);

  panels.forEach((id, idx) => {
    const metric = byId.get(id);
    if (!metric) throw new Error(`registry lists ${id} in charts.valuation but has no metric for it`);
    const series = frame
      ? seriesFor(frame, id, cutoff)
      : { rows: [], x: [] as Date[], y: [] as (number | null)[] };
    const empty = !hasAnyValue(series);
    const spec: PanelSpec = {
      concept: id,
      ylabel: metric.label,
      percent: metric.percent,
      refLine: metric.ref_line,
      x: series.x,
      y: series.y,
      // `series.y` here and `series.y` in the trace are the same array *today*.
      // They are passed as two separate arguments so that item 13's snapshot
      // point and item 14's outlier mask change what is drawn without being
      // able to reach this. The invariant is structural, not a convention.
      mean: empty ? null : meanOver(series.y, metric.harmonic, metric.percent),
      empty,
    };
    drawPanel(figure, idx, spec);
  });

  return { figure, panels, offerable };
}
