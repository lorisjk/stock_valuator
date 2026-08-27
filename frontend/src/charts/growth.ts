/**
 * `build_growth`, client-side. The third chart over `panel.ts`, and the one
 * that does not go through `plot_metric` at all.
 *
 * **`build_growth` calls neither `plot_metric` nor `plot_metric_dual`.** It
 * inlines its own trace, `_style_axes` call and `add_hline` (figures.py:660-680).
 * That matters more than it looks: every question the brief asks about what
 * `build_growth` *passes* to `plot_metric` has the same answer -- it passes
 * nothing, because it never calls it. In particular there is no `show_mean` to
 * set, so this chart draws no mean line for a different reason than the
 * fundamentals chart does.
 *
 * What the inline drawing does, line by line:
 *
 *   - `_window_frame(facts, years=years, as_of=None)` with `years: int = 15` --
 *     the same window as the fundamentals chart, not the valuation chart's five.
 *   - one trace, `mode="lines + markers"`, `_PRIMARY_COLOR`, `connectgaps=True`,
 *     named for the concept: the valuation chart's trace exactly.
 *   - `_style_axes(fig, r, col, label, percent=True)` -- **percent hardcoded**.
 *   - `fig.add_hline(y=0, ...)` -- **the reference line hardcoded**, inside the
 *     loop and after the `continue`, so a blank panel gets no line.
 *   - `_size(width, height, 500 * cols, 360 * rows)` -- 360, a third distinct
 *     row height.
 *
 * `percent` and `ref_line` are read off the registry here rather than pinned to
 * `true` and `0`, because the registry is this frontend's only source of truth
 * and inferring either from the chart id is exactly the mistake §3.2 of the
 * inventory warns about. The two agree today: all ten growth metrics carry
 * `percent: true` and `ref_line: 0`, so every figure this produces is identical
 * to the reference. They are nonetheless two independent declarations of the
 * same fact -- see the report.
 */
import type { Frames, Registry } from "../contracts.ts";
import { PRIMARY_COLOR, createGrid, drawPanel, type FigureSpec, type PanelSpec } from "./panel.ts";
import { hasAnyValue, seriesFor, selectMetricIds, windowCutoff } from "./select.ts";

/** figures.py: `_size(width, height, 500 * cols, 360 * rows)`. */
export const GROWTH_ROW_HEIGHT = 360;
/** figures.py: `build_growth(..., years: int = 15, ...)`. */
export const GROWTH_YEARS = 15;

export interface GrowthOptions {
  requested?: readonly string[] | null;
  years?: number;
  anchor?: Date;
}

export interface GrowthResult {
  figure: FigureSpec | null;
  panels: string[];
  offerable: string[];
}

export function buildGrowth(
  registry: Registry,
  frames: Frames,
  ticker: string,
  options: GrowthOptions = {},
): GrowthResult {
  const { requested = null, years = GROWTH_YEARS, anchor } = options;
  const byId = new Map(registry.metrics.map((m) => [m.id, m]));

  const offerable = selectMetricIds(registry, "growth", ticker, null);

  // `build_growth` returns None when the growth column is missing, before it
  // looks at the panels at all. Here the column cannot go missing on its own --
  // `reconstructFrame` throws if `facts_growth` arrives without `yoy_growth` --
  // so the whole frame being absent is what is left of that branch.
  const frame = frames.facts_growth;
  if (!frame) return { figure: null, panels: [], offerable };

  const panels = selectMetricIds(registry, "growth", ticker, requested);
  if (panels.length === 0) return { figure: null, panels: [], offerable };

  const figure = createGrid(panels, GROWTH_ROW_HEIGHT, `Growth (YoY) ${ticker}`);
  const cutoff = windowCutoff(years, anchor);

  panels.forEach((id, idx) => {
    const metric = byId.get(id);
    if (!metric) throw new Error(`registry lists ${id} in charts.growth but has no metric for it`);
    // `frame.value` is `yoy_growth` -- load.ts's VALUE_COLUMN resolves it per
    // frame, which is the same resolution `_percent_applies` makes on
    // `value_column` rather than on the id. The growth ids are XBRL concept
    // names and all ten of them also name rows in `facts_full`, where the same
    // row carries an absolute-dollar `value`; the narrow `facts_growth` export
    // does not carry that column at all, so the wrong one cannot be read here.
    const series = seriesFor(frame, id, cutoff);

    // `series_values = series.dropna(subset=[growth_column])` then
    // `if series_values.empty`. Same rule as the valuation chart, and note what
    // is drawn when it does not fire: `series`, not `series_values` -- the full
    // windowed series with its nulls in place.
    const empty = !hasAnyValue(series);

    const spec: PanelSpec = {
      concept: id,
      ylabel: metric.label,
      percent: metric.percent,
      refLine: metric.ref_line,
      traces: [{
        name: id,
        x: series.x,
        y: series.y,
        mode: "lines+markers",
        color: PRIMARY_COLOR,
        connectgaps: true,
      }],
      // Never a mean line: `build_growth` has no `plot_metric` call to pass
      // `show_mean` to. Only `build_valuation` sets it (figures.py:753).
      mean: null,
      empty,
    };
    drawPanel(figure, idx, spec);
  });

  return { figure, panels, offerable };
}
