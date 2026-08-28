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
import {
  PRIMARY_COLOR,
  createGrid,
  drawPanel,
  type FigureSpec,
  type PanelSpec,
  type PanelTrace,
} from "./panel.ts";
import { hasAnyValue, seriesFor, selectMetricIds, windowCutoff } from "./select.ts";
import { outlierMask, outlierReport, type HiddenSeries } from "./outliers.ts";
import {
  SNAPSHOT_COLOR,
  SNAPSHOT_LEGENDGROUP,
  SNAPSHOT_NAME,
  snapshotHovertemplate,
  snapshotPoint,
} from "./snapshot.ts";

/** figures.py: `_size(width, height, 500 * cols, 400 * rows)`. */
export const VALUATION_ROW_HEIGHT = 400;
export const VALUATION_YEARS = 5;

export interface ValuationOptions {
  /** null = the whole visible catalogue, as `concepts=None` does in Python. */
  requested?: readonly string[] | null;
  years?: number;
  /**
   * `build_valuation`'s `as_of`: the window's anchor, and the date the snapshot
   * marker is judged against.
   *
   * **Undefined is `None`, not "today".** Python's `as_of=None` anchors the
   * window on today *and* switches the marker's date check off entirely
   * (figures.py:333); a pinned anchor means "as of this date" and switches it
   * on. app.py:867 leaves it `None` behind an opt-in checkbox, which item 15
   * built: the sidebar's "Use an as-of date for valuation" now supplies this,
   * and unchecked still means undefined.
   *
   * Since item 15 it carries **both** of `_window_frame`'s bounds. The lower one
   * goes through `windowCutoff`; the upper one is `seriesFor`'s `until`, applied
   * only when this is set, exactly as figures.py:157's `if as_of is not None`
   * applies it.
   */
  anchor?: Date;
  /**
   * Draw the current-value marker from `frames.current_snapshot`.
   *
   * Opt-in and off by default, mirroring `build_valuation`'s own
   * `snapshot: pd.DataFrame | None = None` and its docstring's promise that
   * "omitting it ... reproduces this function's output exactly as before". The
   * item-8 byte-identity baseline is what that promise is worth here: it still
   * holds, because the harness that computes it passes no options.
   *
   * A boolean rather than the frame itself: the frame is already in `frames`
   * (item 2 exports `current_snapshot` per ticker and `DataTab` already reads
   * it), so this needs no fetch and cannot be handed a mismatched one.
   */
  snapshot?: boolean;
  /**
   * `build_valuation`'s `mask_outliers` (figures.py:715): hide points more than
   * `OUTLIER_MEDIAN_RATIO` times their panel's own median.
   *
   * **Per panel, not per figure**, which figures.py:731 is explicit about and
   * which is easy to read the wrong way round: the *flag* reaches every panel,
   * but the *rule* runs against each panel's own series, so a grid where one
   * multiple is pathological and eight are not loses points from the one. There
   * is exactly one toggle in the UI, not nine.
   *
   * Off by default, like the reference, and for the same reason as `snapshot` —
   * the default path has to keep emitting what it emitted before.
   */
  mask?: boolean;
}

export interface ValuationResult {
  /** null when nothing is visible -- `build_valuation` returns None there. */
  figure: FigureSpec | null;
  /** Panel ids in catalogue order. Empty when the figure is null. */
  panels: string[];
  /** Every id the ticker's profile allows, for a picker. */
  offerable: string[];
  /**
   * `outlier_report` over the same windowed series the figure was drawn from —
   * keyed by concept, empty when nothing qualifies.
   *
   * Returned rather than recomputed by the view, because app.py:939 calls
   * `outlier_report` on `_window_frame(val_frame, years, as_of)` with the same
   * `chosen`, and the comment on `_comparison_selection` (figures.py:832) says
   * why that matters: *"if the two derived their series separately, the control
   * could name points the chart does not draw, or miss ones it does."* Here the
   * builder is the only thing that derives them, so there is nothing to keep in
   * step.
   *
   * Reported whether or not `mask` is on: the reference computes it first and
   * uses it to decide whether to *offer* the toggle.
   */
  outliers: HiddenSeries[];
  /**
   * `empty_valuation_panels` (app.py:511): the drawn panels that have no value
   * at all in the window, in panel order.
   *
   * **Derived from the same `empty` flag the panels were drawn with**, not
   * recomputed. app.py necessarily runs a second pass over the frame because the
   * builder returns it a finished figure and nothing else; here the builder is
   * the only thing that windows the series, so returning what it already decided
   * is both cheaper and the only way the notice cannot disagree with the "No
   * Data" boxes it is describing. Same lesson as `outlier_report`'s
   * co-derivation (figures.py:832).
   */
  empty: string[];
}

export function buildValuation(
  registry: Registry,
  frames: Frames,
  ticker: string,
  options: ValuationOptions = {},
): ValuationResult {
  const {
    requested = null,
    years = VALUATION_YEARS,
    anchor,
    snapshot = false,
    mask = false,
  } = options;
  const byId = new Map(registry.metrics.map((m) => [m.id, m]));

  const offerable = selectMetricIds(registry, "valuation", ticker, null);
  const panels = selectMetricIds(registry, "valuation", ticker, requested);

  // build_valuation prints and returns None. There is no figure to draw and no
  // grid to size, so the caller renders a message instead -- see ValuationChart.
  if (panels.length === 0) return { figure: null, panels: [], offerable, outliers: [], empty: [] };

  const frame = frames.valuation_history;
  const figure = createGrid(panels, VALUATION_ROW_HEIGHT, `Valuation Data ${ticker}`);
  const cutoff = windowCutoff(years, anchor);
  const snapshotFrame = snapshot ? frames.current_snapshot : undefined;
  // figures.py:748 -- "one legend entry for all of them, on whichever panel got
  // the first marker". Figure-level state, so it lives here rather than in the
  // per-panel spec, and it advances only when a marker is actually drawn.
  let snapshotShown = false;
  /** app.py:963's `blank`, collected as the panels are drawn. */
  const emptyPanels: string[] = [];
  /** `{concept: series}` over the windowed values, for `outlierReport`. */
  const windowed: { key: string; x: Date[]; y: (number | null)[] }[] = [];

  panels.forEach((id, idx) => {
    const metric = byId.get(id);
    if (!metric) throw new Error(`registry lists ${id} in charts.valuation but has no metric for it`);
    const series = frame
      ? seriesFor(frame, id, cutoff, anchor)
      : { rows: [], x: [] as Date[], y: [] as (number | null)[] };
    const empty = !hasAnyValue(series);
    if (empty) emptyPanels.push(id);
    windowed.push({ key: id, x: series.x, y: series.y });

    // figures.py:372 -- `drawn` against `filtered`, and this is the whole of the
    // difference between them. The mask runs on the **windowed** series, which
    // is the order the reference fixes by masking inside `plot_metric` after
    // `_window_frame` has already run: the ratio is against the median of what
    // is on screen, so the same `k` keeps meaning the same thing as the slider
    // moves.
    //
    // Rows are **removed**, not nulled -- `filtered.loc[~hidden]` drops them, so
    // `x` shrinks with `y`. Nulling would render identically (`connectgaps` is
    // on) but would emit a longer `x` than the reference, and there is no
    // alignment to preserve: each trace carries its own x array.
    const hidden = mask && !empty ? outlierMask(series.y) : null;
    const hiddenCount = hidden ? hidden.filter(Boolean).length : 0;
    const drawn = hiddenCount
      ? {
          x: series.x.filter((_, i) => !hidden![i]),
          y: series.y.filter((_, i) => !hidden![i]),
        }
      : { x: series.x, y: series.y };

    // `_snapshot_point(snapshot, ticker, concept, as_of)`. The ticker filter is
    // implicit: a per-ticker export file holds one ticker's rows and nothing
    // else. Computed even for an empty panel, then discarded there -- because
    // `plot_metric` returns before drawing it and `snapshot_shown` is advanced
    // by `point is not None` regardless, so a panel that has a point but no
    // filed series still consumes the one legend entry. Faithful, and only
    // observable when the first panel in the grid is that shape.
    const point = snapshotFrame ? snapshotPoint(snapshotFrame, id, anchor) : null;
    const marker: PanelTrace[] = point && !empty
      ? [{
          name: SNAPSHOT_NAME,
          x: [point.end],
          y: [point.value],
          mode: "markers",
          color: SNAPSHOT_COLOR,
          marker: {
            color: SNAPSHOT_COLOR,
            size: 9,
            symbol: "circle",
            line: { color: "white", width: 1 },
          },
          hovertemplate: snapshotHovertemplate(point.end),
          legendgroup: SNAPSHOT_LEGENDGROUP,
          showlegend: !snapshotShown,
        }]
      : [];
    if (point) snapshotShown = true;

    const spec: PanelSpec = {
      concept: id,
      ylabel: metric.label,
      percent: metric.percent,
      refLine: metric.ref_line,
      traces: [{
        name: id,
        x: drawn.x,
        y: drawn.y,
        mode: "lines+markers",
        color: PRIMARY_COLOR,
        connectgaps: true,
      }, ...marker],
      hiddenCount,
      // **`series.y`, never `drawn.y`.** This is the line item 14 exists to not
      // touch, and it is now load-bearing rather than merely tidy: with masking
      // on, `drawn.y` is genuinely a different and shorter array, so wiring the
      // mean to it would silently recompute the benchmark over the series with
      // its bad years taken out -- "a different and flattering quantity", as
      // figures.py:365 puts it. Item 13's marker was the same move from the
      // other direction. Structural, not a convention.
      mean: empty ? null : meanOver(series.y, metric.harmonic, metric.percent),
      empty,
    };
    drawPanel(figure, idx, spec);
  });

  // app.py:939 computes this before deciding whether to offer the toggle, over
  // the same windowed series -- so an empty result is exactly what hides the
  // control. Emptiness is not `mask`-dependent: the report says what *would* be
  // hidden, which is the question the toggle's presence turns on.
  return { figure, panels, offerable, outliers: outlierReport(windowed), empty: emptyPanels };
}
