/**
 * `build_fundamentals`, client-side. The second chart over `panel.ts`, and the
 * first test of whether that layer generalises.
 *
 * Three things differ from the valuation chart, and all three come off the
 * reference implementation rather than a description of it:
 *
 *   1. **There is a window, and it is fifteen years**, not five --
 *      `build_fundamentals(ticker, metrics_long, years=15, ...)` calls
 *      `_window_frame(metrics_long, years=years, as_of=None)`. It cuts 55,972 of
 *      571,114 rows, so it is not decorative.
 *   2. **Eleven of the 29 metrics carry a quarterly counterpart** and draw a
 *      second, thinner trace behind the TTM line.
 *   3. **No mean lines.** `build_fundamentals` never passes `show_mean`, so
 *      `plot_metric` defaults it to False, and `plot_metric_dual` has no such
 *      parameter at all. Every panel here passes `mean: null`.
 *
 * Row height is 330, not 400 (`_size(width, height, 500 * cols, 330 * rows)`).
 */
import type { Frames, Registry } from "../contracts.ts";
import {
  PRIMARY_COLOR,
  SECONDARY_COLOR,
  createGrid,
  drawPanel,
  type FigureSpec,
  type PanelSpec,
  type PanelTrace,
} from "./panel.ts";
import { hasAnyValue, seriesFor, selectMetricIds, windowCutoff } from "./select.ts";

/** figures.py: `_size(width, height, 500 * cols, 330 * rows)`. */
export const FUNDAMENTALS_ROW_HEIGHT = 330;
/** figures.py: `build_fundamentals(..., years: int = 15, ...)`. */
export const FUNDAMENTALS_YEARS = 15;

export interface FundamentalsOptions {
  requested?: readonly string[] | null;
  years?: number;
  anchor?: Date;
}

export interface FundamentalsResult {
  figure: FigureSpec | null;
  panels: string[];
  offerable: string[];
}

export function buildFundamentals(
  registry: Registry,
  frames: Frames,
  ticker: string,
  options: FundamentalsOptions = {},
): FundamentalsResult {
  const { requested = null, years = FUNDAMENTALS_YEARS, anchor } = options;
  const byId = new Map(registry.metrics.map((m) => [m.id, m]));

  const offerable = selectMetricIds(registry, "fundamentals", ticker, null);
  const panels = selectMetricIds(registry, "fundamentals", ticker, requested);
  if (panels.length === 0) return { figure: null, panels: [], offerable };

  const frame = frames.metrics_long;
  const figure = createGrid(panels, FUNDAMENTALS_ROW_HEIGHT, `Fundamentals ${ticker}`);
  const cutoff = windowCutoff(years, anchor);
  const empty = { rows: [] as number[], x: [] as Date[], y: [] as (number | null)[] };

  panels.forEach((id, idx) => {
    const metric = byId.get(id);
    if (!metric) throw new Error(`registry lists ${id} in charts.fundamentals but has no metric`);

    const ttm = frame ? seriesFor(frame, id, cutoff) : empty;
    const counterpart = registry.quarterly_counterpart[id];
    // `build_fundamentals` guards the dual path with
    // `if quarterly_concept and not is_hidden(ticker, quarterly_concept)`. The
    // second half of that guard is a no-op in every configuration this registry
    // can express: `is_hidden` strips a `_quarterly` suffix and falls back to
    // the base name, and no PROFILE_HIDDEN set names a `_quarterly` id, so a
    // counterpart is hidden exactly when its base metric is -- and a hidden base
    // never reaches this loop. Measured over all 609 tickers: 0 of 1,846 dual
    // candidates diverge. The registry carries no per-`_quarterly` visibility,
    // so this equivalence is what makes `quarterly_counterpart` sufficient.
    const quarterly = counterpart && frame ? seriesFor(frame, counterpart, cutoff) : empty;

    // **The empty rule.** `plot_metric_dual` blanks the panel when the *TTM*
    // series has no value, whatever the quarterly series holds -- "the quarterly
    // line alone would be read as the metric itself". It is not "no data in
    // either"; a panel with 44 quarterly points and no TTM point is blank.
    const blank = !hasAnyValue(ttm);

    const traces: PanelTrace[] = [];
    if (!blank) {
      traces.push({
        name: counterpart ? `${id} · TTM` : id,
        x: ttm.x,
        y: ttm.y,
        mode: "lines+markers",
        color: PRIMARY_COLOR,
        // 1.5 on the dual path, plotly's default on the single path. The name
        // differs too -- `plot_metric` names the trace `concept`, and
        // `plot_metric_dual` names it `concept · TTM` even when it ends up
        // drawing only the one line.
        ...(counterpart ? { width: 1.5 } : {}),
        connectgaps: true,
      });
      // Drawn only when it has a value of its own, and then the *whole* windowed
      // series is drawn -- nulls included, as with the TTM line. No connectgaps
      // here: the reference does not set it, so a gap in the quarterly series
      // breaks the line where the TTM line above would bridge it.
      if (counterpart && hasAnyValue(quarterly)) {
        traces.push({
          name: `${id} · quarterly`,
          x: quarterly.x,
          y: quarterly.y,
          mode: "lines",
          color: SECONDARY_COLOR,
          width: 0.8,
          opacity: 0.6,
        });
      }
    }

    const spec: PanelSpec = {
      concept: id,
      ylabel: metric.label,
      percent: metric.percent,
      refLine: metric.ref_line,
      traces,
      // Never a mean line on this chart -- see the module docstring.
      mean: null,
      empty: blank,
    };
    drawPanel(figure, idx, spec);
  });

  return { figure, panels, offerable };
}
