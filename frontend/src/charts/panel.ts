/**
 * The drawing layer: a subplot grid and the furniture that goes into one panel.
 *
 * This mirrors the split in figures.py, where `build_valuation` decides *which*
 * series to draw and `plot_metric` draws one panel into a figure it is handed.
 * Items 5 (fundamentals, dual TTM/quarterly traces) and 6 (growth, a fixed y=0
 * line) need the same furniture with different selection rules, so the two
 * halves are separate modules rather than one `buildValuation`.
 *
 * Everything here is plain data. Nothing imports React or plotly.js -- the
 * output is a `{data, layout}` figure spec, which is what `<Plot>` takes and
 * what the Python builder serialises, so the two are directly comparable.
 *
 * One rule binds everything below. **An axis that no trace references may only
 * be referenced by a bare id (`"x5"`), never by `"x5 domain"`.** plotly.js
 * registers component-referenced axes through `cleanId(ref, letter, false)`,
 * which rejects domain refs outright, so a domain-only axis is never created and
 * every reference to it silently falls back to the first axis. Panels that carry
 * a trace may use either form. See annotateNoData for the full derivation; the
 * verification enforces it structurally for every axis of every figure.
 */
import { axisNumber, axisSuffix, cellDomain, cellFor, makeGrid } from "./grid.ts";
import type { MeanLine } from "./mean.ts";

/** figures.py:19-24 -- pinned, not left to plotly's cycle. */
export const PRIMARY_COLOR = "#1f77b4";
/** The quarterly line on a dual fundamentals panel. */
export const SECONDARY_COLOR = "#ff7f0e";
export const PERCENT_TICKFORMAT = ".1~%";
const REFERENCE_COLOR = "red";

export interface Trace {
  type: "scatter";
  mode: string;
  name: string;
  x: (Date | string)[];
  y: (number | null)[];
  line?: { color: string; width?: number };
  opacity?: number;
  connectgaps?: boolean;
  hovertemplate?: string;
  xaxis: string;
  yaxis: string;
  showlegend?: boolean;
}

export interface Annotation {
  text: string;
  x: number;
  y: number;
  xref: string;
  yref: string;
  xanchor: string;
  yanchor: string;
  showarrow: false;
  font: { color?: string; size: number };
}

export interface Shape {
  type: "line";
  x0: number;
  x1: number;
  y0: number;
  y1: number;
  xref: string;
  yref: string;
  line: { color: string; width: number };
}

export interface Axis {
  anchor: string;
  domain: [number, number];
  dtick?: string;
  tickformat?: string | null;
  title?: { text: string; font: { size: number } };
  showticklabels?: boolean;
  showgrid?: boolean;
  zeroline?: boolean;
}

export interface FigureSpec {
  data: Trace[];
  layout: {
    title: { text: string };
    height: number;
    hovermode: string;
    legend: { font: { size: number } };
    annotations: Annotation[];
    shapes: Shape[];
    /** `xaxis`, `xaxis2`, ... and `yaxis`, `yaxis2`, ... */
    [axis: string]: unknown;
  };
  rows: number;
  cols: number;
}

/**
 * An empty grid with make_subplots' axes, domains and subplot titles.
 *
 * Titles are the **concept ids**, not the labels -- `_make_subplot_figure` is
 * handed `[c[0] for c in concepts_to_plot]` and the label goes on the y axis
 * instead. Reproduced rather than improved: the brief's table calls the panel
 * title "the metric's label", and the reference implementation disagrees with
 * it. See the report.
 */
export function createGrid(titles: string[], perRowHeight: number, title: string): FigureSpec {
  const n = titles.length;
  const { rows, cols } = makeGrid(n);
  const layout: FigureSpec["layout"] = {
    title: { text: title },
    height: perRowHeight * rows,
    hovermode: "x unified",
    legend: { font: { size: 9 } },
    annotations: [],
    shapes: [],
  };

  for (let idx = 0; idx < n; idx += 1) {
    const { row, col } = cellFor(idx, cols);
    const k = axisNumber(row, col, cols);
    const suffix = axisSuffix(k);
    const domain = cellDomain(row, col, rows, cols);
    layout[`xaxis${suffix}`] = { anchor: `y${suffix}`, domain: domain.x } satisfies Axis;
    layout[`yaxis${suffix}`] = { anchor: `x${suffix}`, domain: domain.y } satisfies Axis;
    layout.annotations.push({
      text: titles[idx],
      x: (domain.x[0] + domain.x[1]) / 2,
      y: domain.y[1],
      xref: "paper",
      yref: "paper",
      xanchor: "center",
      yanchor: "bottom",
      showarrow: false,
      font: { size: 16 },
    });
  }
  return { data: [], layout, rows, cols };
}

/** Which axes a cell's traces and panel-relative annotations refer to. */
export function panelRefs(idx: number, cols: number) {
  const { row, col } = cellFor(idx, cols);
  const suffix = axisSuffix(axisNumber(row, col, cols));
  return {
    xaxis: `x${suffix}`,
    yaxis: `y${suffix}`,
    xKey: `xaxis${suffix}`,
    yKey: `yaxis${suffix}`,
  };
}

/**
 * One line in a panel. A panel holds a list of these rather than one x/y pair.
 *
 * The valuation chart draws one; the fundamentals chart draws a TTM line and,
 * where a quarterly counterpart exists and has values, a second thinner one
 * behind it. Item 12's comparison chart is the same shape again -- one entry per
 * ticker, each with its own colour and name -- and item 13's snapshot marker is
 * one more entry with `mode: "markers"`. A sibling `drawDualPanel` would have
 * served this chart and none of those.
 *
 * Every style field is explicit because figures.py:19-36 pins them: an automatic
 * colour cycle would give each subplot a different colour and imply a
 * distinction that is not there.
 */
export interface PanelTrace {
  /** Legend and hover name. `pe_ratio`, `operating_margin · TTM`, ... */
  name: string;
  x: (Date | string)[];
  /** Nulls kept in place. `connectgaps` decides how they render, not a filter. */
  y: (number | null)[];
  mode: string;
  color: string;
  /** Omitted from the emitted trace when undefined, as the reference omits it. */
  width?: number;
  opacity?: number;
  connectgaps?: boolean;
}

export interface PanelSpec {
  /** Subplot title: the metric id. */
  concept: string;
  /** y-axis title: the metric's registry label. */
  ylabel: string;
  percent: boolean;
  refLine: number | null;
  /** Drawn in order. Empty is legal only when `empty` is true. */
  traces: PanelTrace[];
  /**
   * Computed over the selected series, never over any trace's `y`. Null = no
   * line -- which is also what the fundamentals chart always passes, because
   * `build_fundamentals` never sets `show_mean`.
   */
  mean: MeanLine | null;
  /** True when the panel's own empty rule fired: the "No Data" panel. */
  empty: boolean;
}

/**
 * figures.py `_annotate_no_data`: the text, and the panel's furniture removed.
 *
 * The references are **bare axis ids** (`"x5"`, `"y5"`), not `"x5 domain"`, and
 * that is load-bearing rather than cosmetic. plotly.js only creates a subplot
 * for an axis it can see, and it can see one in exactly two ways: a trace names
 * it, or a component (annotation, shape, image) names it. The component path
 * runs through `include_components.js`, which calls
 * `axisIds.cleanId(ref, letter, false)` -- and `cleanId` *rejects* a `" domain"`
 * ref when its `domainId` argument is false rather than stripping the suffix
 * (axis_ids.js:35), despite the comment above the call saying otherwise.
 *
 * A "No Data" panel has no trace by definition. So a domain-referenced
 * placeholder makes its axis invisible to plotly.js, and then three things
 * happen at once: the panel is never drawn, `coerceRef` falls back to
 * `_subplots.xaxis[0]` and drops the annotation onto the *first* panel, and
 * because that fallback is a data reference, x = 0.5 is read as 0.5 ms after the
 * epoch and drags the first panel's date axis back to 1970.
 *
 * `plot_metric` reaches the same place from the other direction: it passes
 * `row=`/`col=` to `add_annotation`, and plotly.py resolves that to a bare
 * `"x5"`. x and y are therefore data coordinates on both sides -- 0.5 on an axis
 * with no data, which auto-ranges around it.
 */
function annotateNoData(fig: FigureSpec, idx: number): void {
  const refs = panelRefs(idx, fig.cols);
  fig.layout.annotations.push({
    text: "No Data",
    x: 0.5,
    y: 0.5,
    xref: refs.xaxis,
    yref: refs.yaxis,
    xanchor: "center",
    yanchor: "middle",
    showarrow: false,
    font: { color: "red", size: 14 },
  });
  const blank = { showticklabels: false, showgrid: false, zeroline: false };
  Object.assign(fig.layout[refs.xKey] as Axis, blank);
  Object.assign(fig.layout[refs.yKey] as Axis, blank);
}

/** figures.py `_style_axes`: two-year x ticks, y title, percent tickformat. */
function styleAxes(fig: FigureSpec, idx: number, ylabel: string, percent: boolean): void {
  const refs = panelRefs(idx, fig.cols);
  Object.assign(fig.layout[refs.xKey] as Axis, { dtick: "M24", tickformat: "%Y" });
  Object.assign(fig.layout[refs.yKey] as Axis, {
    title: { text: ylabel, font: { size: 11 } },
    tickformat: percent ? PERCENT_TICKFORMAT : null,
  });
}

/** A horizontal line spanning the panel: red, width 1 -- mean and ref alike. */
function hline(fig: FigureSpec, idx: number, y: number): void {
  const refs = panelRefs(idx, fig.cols);
  fig.layout.shapes.push({
    type: "line",
    x0: 0,
    x1: 1,
    y0: y,
    y1: y,
    xref: `${refs.xaxis} domain`,
    yref: refs.yaxis,
    line: { color: REFERENCE_COLOR, width: 1 },
  });
}

/**
 * One panel, drawn into `fig` at position `idx` -- `plot_metric` and
 * `plot_metric_dual` in one function, because they differ only in how many
 * traces they push.
 *
 * Order matches both references: every trace, then the axes, then the mean line
 * and its label, then the reference line. It matters, because the comparison
 * against the Python figure reads annotations and shapes in order.
 */
export function drawPanel(fig: FigureSpec, idx: number, panel: PanelSpec): void {
  if (panel.empty) {
    annotateNoData(fig, idx);
    return;
  }
  const refs = panelRefs(idx, fig.cols);
  for (const series of panel.traces) {
    // Conditional spreads rather than assignment after the fact: an absent
    // `opacity` or `connectgaps` must be absent from the emitted trace, exactly
    // as the reference omits it, and the key order has to stay fixed so a
    // single-trace panel still serialises byte-for-byte as it did before this
    // list existed.
    fig.data.push({
      type: "scatter",
      mode: series.mode,
      name: series.name,
      x: series.x,
      y: series.y,
      line: series.width === undefined
        ? { color: series.color }
        : { color: series.color, width: series.width },
      ...(series.opacity === undefined ? {} : { opacity: series.opacity }),
      ...(series.connectgaps === undefined ? {} : { connectgaps: series.connectgaps }),
      hovertemplate: "Date: %{x|%d.%m.%Y}<br>Value: %{y}<extra></extra>",
      xaxis: refs.xaxis,
      yaxis: refs.yaxis,
    });
  }
  styleAxes(fig, idx, panel.ylabel, panel.percent);

  if (panel.mean) {
    hline(fig, idx, panel.mean.value);
    fig.layout.annotations.push({
      text: panel.mean.label,
      x: 0.02,
      y: 0.98,
      xref: `${refs.xaxis} domain`,
      yref: `${refs.yaxis} domain`,
      xanchor: "left",
      yanchor: "top",
      showarrow: false,
      font: { color: "red", size: 10 },
    });
  }

  if (panel.refLine !== null) hline(fig, idx, panel.refLine);
}
