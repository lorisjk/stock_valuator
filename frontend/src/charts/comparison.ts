/**
 * `figures.py`'s `build_ticker_comparison` (figures.py:903) and the half of
 * `_comparison_selection` (figures.py:822) that decides which tickers survive.
 *
 * The first chart that is not per-ticker: one concept, one line per ticker. It
 * differs from the other three in four ways that all come from the reference,
 * not from this port:
 *
 *   - **no mean line** (figures.py:930), so item 14's mean-invariance rules have
 *     nothing here to apply to;
 *   - **no snapshot point** (figures.py:941), so item 13's marker is out of this
 *     chart's scope by the reference's own decision, not merely by a brief;
 *   - **one panel, N traces**, where the others are N panels of one or two;
 *   - **exclusions are part of the result**, returned rather than logged, because
 *     the app has to word them.
 *
 * No React and no DOM: this runs in Node, which is what lets every trace be
 * compared element-wise against the Python builder.
 */
import type { ChartId, Frame, Frames, Registry } from "../contracts.ts";
import { createGrid, drawComparisonPanel, COMPARISON_COLORS } from "./panel.ts";
import type { ComparisonTrace, FigureSpec } from "./panel.ts";
import { hasAnyValue, selectMetricIds, seriesFor, windowCutoff } from "./select.ts";
import { outlierMask, outlierReport, type HiddenSeries } from "./outliers.ts";

/** figures.py:40. Enforced -- one ticker is not a comparison. */
export const MIN_COMPARISON_TICKERS = 2;

/**
 * figures.py:38. **Advisory only**, and the comment there is explicit that this
 * is deliberate: *"a readability limit belongs in the UI that picks the tickers
 * ... not in the rendering layer, where a hard refusal would turn a UI mistake
 * into a missing chart."* So the builder never enforces it; the picker does.
 */
export const SUGGESTED_MAX_COMPARISON_TICKERS = 3;

/** app.py:1032 -- the comparison tab's own slider default, not figures' 5. */
export const COMPARISON_YEARS = 15;

/** figures.py:1046 -- `_size(width, height, 900, 520)` with width dropped. */
const COMPARISON_HEIGHT = 520;

/**
 * Which frame a chart's concepts live in -- `figures.concept_source`
 * (figures.py:811) as a lookup, since the registry already carries the chart.
 */
const FRAME_FOR: Record<ChartId, keyof Frames> = {
  fundamentals: "metrics_long",
  valuation: "valuation_history",
  growth: "facts_growth",
};

export interface Exclusion {
  ticker: string;
  /**
   * The reference's own words, unchanged: `"for profile 'X' not shown"` or
   * `"No Data"`. The app rewrites the second one (app.py:1067) and must be able
   * to tell them apart to do it.
   */
  reason: string;
}

export interface ComparisonOptions {
  years?: number;
  /**
   * The window's anchor -- `build_ticker_comparison`'s `as_of`, reaching
   * `_window_frame` through `_comparison_selection` (figures.py:851) exactly as
   * the valuation grid's does.
   *
   * Item 15 attached the control here and closed the half that was missing: with
   * this set the window is bounded **above** as well as below, so the chart
   * cannot show a line running past the date the reader asked about. Undefined
   * leaves both the upper bound and item 13's marker check off -- though this
   * chart draws no marker, so only the bound is observable here.
   */
  anchor?: Date;
  /**
   * `build_ticker_comparison`'s `mask_outliers` (figures.py:912).
   *
   * **Per line, against that line's own median — never a pooled one.** The
   * measurement behind that is in `comparison_outlier_report`'s docstring
   * (figures.py:878): a pooled median flags two NVDA points on NVDA/KO/JPM
   * `pe_ratio`, three series with nothing wrong with any of them, purely because
   * NVDA trades higher than a bank — and the same pooled rule simultaneously
   * over-masks CRM (7 points against 4) and under-masks INTC (1 against 3).
   * *"Punishing a ticker for sitting at a different level is the opposite of
   * what a comparison chart is for."*
   *
   * Worth more here than in the valuation grid, for a structural reason
   * figures.py:970 gives: these lines share one y-axis, so a single ticker's
   * outlier flattens every other line too.
   *
   * **Ignored for a non-valuation concept**, per figures.py:974's
   * `if mask_outliers and is_valuation` — the rule needs a positive median to
   * mean anything, and only the valuation frame has one everywhere.
   */
  mask?: boolean;
}

export interface ComparisonResult {
  /** Null when there is nothing to draw -- see `excluded` to tell why. */
  figure: FigureSpec | null;
  /** Tickers that made it onto the chart, in requested order. */
  plotted: string[];
  /**
   * Dropped tickers with the reference's reason.
   *
   * figures.py:924 -- when `figure` is null this is what separates the two
   * cases: **non-empty** means every requested ticker was dropped, a data
   * outcome; **empty** means the request itself was rejected (unknown concept,
   * or fewer than `MIN_COMPARISON_TICKERS`).
   */
  excluded: Exclusion[];
  /**
   * `comparison_outlier_report`, keyed by **ticker** rather than by concept —
   * this chart holds one concept and several lines (app.py:1047). Empty for a
   * non-valuation concept, which is what keeps the toggle off there.
   *
   * The reference puts the *counts* into `layout.meta` as well, so a serialised
   * figure carries them to a consumer that gets nothing else. This port has no
   * `meta` (see the report — it is one of three layout fields item 12 did not
   * carry across), and the view reads this field instead.
   */
  outliers: HiddenSeries[];
}

/**
 * One concept across N tickers.
 *
 * `framesByTicker` is a map rather than a fetch, for the same reason every other
 * builder takes `Frames`: the builder does no I/O, so it runs in Node against
 * files read from disk. A ticker missing from the map is treated as having no
 * rows, which lands it in `excluded` as `"No Data"` -- the same place a ticker
 * with an empty window lands, and the honest one while its file is in flight.
 */
export function buildComparison(
  registry: Registry,
  framesByTicker: ReadonlyMap<string, Frames>,
  tickers: readonly string[],
  concept: string,
  options: ComparisonOptions = {},
): ComparisonResult {
  const { years = COMPARISON_YEARS, anchor, mask = false } = options;

  // figures.py:838 `_concept_plot_spec` -- METRICS_BY_ID, so any registered id
  // from any of the three catalogues, and nothing else.
  const metric = registry.metrics.find((m) => m.id === concept);
  if (!metric) return { figure: null, plotted: [], excluded: [], outliers: [] };

  // figures.py:845 `list(dict.fromkeys(tickers))` -- dedup, order preserved.
  const requested = [...new Set(tickers)];
  if (requested.length < MIN_COMPARISON_TICKERS) {
    return { figure: null, plotted: [], excluded: [], outliers: [] };
  }

  const cutoff = windowCutoff(years, anchor);
  const frameName = FRAME_FOR[metric.chart];

  const plotted: { position: number; ticker: string; trace: ComparisonTrace }[] = [];
  const excluded: Exclusion[] = [];

  requested.forEach((ticker, position) => {
    // figures.py:854 `is_hidden(ticker, concept)`. Routed through
    // `selectMetricIds`, which is the function every other chart narrows with --
    // so there is exactly one implementation of "may this ticker show this
    // metric" in the frontend, and this chart cannot drift from the pickers.
    if (selectMetricIds(registry, metric.chart, ticker, [concept]).length === 0) {
      const profile = registry.ticker_profile[ticker] ?? registry.default_profile;
      excluded.push({ ticker, reason: `for profile '${profile}' not shown` });
      return;
    }

    const frame: Frame | undefined = framesByTicker.get(ticker)?.[frameName];
    const series = frame
      ? seriesFor(frame, concept, cutoff, anchor)
      : { rows: [], x: [] as Date[], y: [] as (number | null)[] };

    // figures.py:861 `series.dropna(subset=["end", column]).empty`.
    if (!hasAnyValue(series)) {
      excluded.push({ ticker, reason: "No Data" });
      return;
    }

    plotted.push({
      position,
      ticker,
      trace: {
        name: ticker,
        x: series.x,
        y: series.y,
        // Step 1.1's finding, and the one line that implements it: the colour
        // index is the ticker's position in `requested`, so removing a ticker
        // never recolours the others.
        color: COMPARISON_COLORS[position % COMPARISON_COLORS.length],
      },
    });
  });

  // figures.py:960 -- everything was dropped. `excluded` is non-empty here,
  // which is what tells this apart from a rejected request.
  if (plotted.length === 0) return { figure: null, plotted: [], excluded, outliers: [] };

  // figures.py:974 `if mask_outliers and is_valuation`, and figures.py:891's
  // `if not spec[4]: return {}` for the report -- both gated the same way, so a
  // fundamentals or growth concept ignores the flag rather than applying a rule
  // whose precondition does not hold there.
  const isValuation = metric.chart === "valuation";
  const outliers = isValuation
    ? outlierReport(plotted.map((p) => ({ key: p.ticker, x: p.trace.x, y: p.trace.y })))
    : [];

  // One mask per line, computed from that line alone. The loop is over `plotted`
  // rather than over `outliers` so the drawn arrays stay in plotted order, which
  // is what keeps the colours attached to the right tickers.
  const hiddenByTicker: [string, number][] = [];
  if (mask && isValuation) {
    for (const p of plotted) {
      const hidden = outlierMask(p.trace.y);
      const count = hidden.filter(Boolean).length;
      if (count === 0) continue;
      hiddenByTicker.push([p.ticker, count]);
      // Rows removed, not nulled -- `series.loc[~hidden]`, as in the grid.
      p.trace = {
        ...p.trace,
        x: p.trace.x.filter((_, i) => !hidden[i]),
        y: p.trace.y.filter((_, i) => !hidden[i]),
      };
    }
  }

  const names = plotted.map((p) => p.ticker);
  const figure = createGrid(
    [concept],
    COMPARISON_HEIGHT,
    // figures.py:1045 `title_text=f"{ylabel} — {', '.join(plotted)}"`. The plotted
    // tickers, not the requested ones: an excluded ticker is named in the note
    // below the chart, never in its title.
    `${metric.label} — ${names.join(", ")}`,
  );

  drawComparisonPanel(figure, {
    ylabel: metric.label,
    percent: metric.percent,
    refLine: metric.ref_line,
    traces: plotted.map((p) => p.trace),
    excludedNote: excluded.length
      ? `Not shown: ${excluded.map((e) => `${e.ticker} (${e.reason})`).join(", ")}`
      : null,
    hiddenByTicker,
  });

  return { figure, plotted: names, excluded, outliers };
}
