/**
 * `figures.py`'s `available_raw_concepts` (figures.py:1081) and `build_raw_facts`
 * (figures.py:1100): concepts as filed, one bar panel each.
 *
 * **This is a different feature from the Data tab's "Raw & derived facts"
 * table**, despite the shared words. The table (items 9-11) pivots every concept
 * against every period with downloads and a copy block; this draws a time series
 * per concept. They share their *source frame* and one rule -- what counts as
 * derived -- and nothing else. See the report for the confirmation.
 *
 * Four things separate this chart from the other three, and all four are
 * absences rather than additions:
 *
 *   - **the catalogue is per ticker and is not in the registry.** Fundamentals,
 *     valuation and growth read `charts[chart].metric_ids`; this one is computed
 *     from what the ticker's own facts contain.
 *   - **no profile narrowing here.** `available_raw_concepts`' docstring says
 *     why: *"facts_full is already post-filter_hidden_rows, so profile
 *     visibility is respected without consulting is_hidden here."* So there is
 *     no `selectMetricIds` call and there should not be one.
 *   - **no `as_of`.** `_window_frame(facts, years=years, as_of=None)`
 *     (figures.py:1110), hard-coded, which is why `seriesFor` is called here
 *     without its `until`.
 *   - **no mean, no reference line, no axis styling, no outlier masking.**
 *
 * No React and no DOM: this runs in Node, so every panel can be compared
 * element-wise against the Python builder.
 */
import type { Frame } from "../contracts.ts";
import { createGrid, drawBarPanel, type FigureSpec } from "./panel.ts";
import { hasAnyValue, seriesFor, windowCutoff } from "./select.ts";

/** figures.py:1145 -- `_size(width, height, 500 * cols, 330 * rows)`, width dropped. */
export const RAW_ROW_HEIGHT = 330;

/** figures.py:1103 and app.py:1119's slider, which agree. */
export const RAW_YEARS = 15;

/**
 * app.py:1115 -- the four concepts the multiselect opens on, in this order,
 * each kept only if the ticker actually offers it.
 */
export const RAW_DEFAULT_CONCEPTS = [
  "Revenue",
  "NetIncomeLoss",
  "Assets",
  "StockholdersEquity",
] as const;

export interface RawOptions {
  /** null = every available concept, as `concepts=None` does in Python. */
  requested?: readonly string[] | null;
  years?: number;
  /** app.py:1110's checkbox. False keeps only the queried concepts. */
  includeDerived?: boolean;
  /** Pins "today" for the window's lower bound. Never an as-of -- see the module docstring. */
  anchor?: Date;
}

export interface RawResult {
  /** null when nothing is selected or nothing is available -- `build_raw_facts` returns None. */
  figure: FigureSpec | null;
  /** Panel ids, in the order drawn. Empty when the figure is null. */
  panels: string[];
  /** Every concept this ticker could show, for the picker. */
  offerable: string[];
}

/**
 * `available_raw_concepts(ticker, facts, include_derived)`.
 *
 * Three steps, in this order and no other:
 *
 *   1. rows for this ticker with a **non-null value** -- `dropna(subset=["value"])`,
 *      so a concept present only as gaps is not offered;
 *   2. the distinct concepts of those rows;
 *   3. unless `includeDerived`, intersected with `get_concept_candidates(ticker)`'s
 *      **keys**.
 *
 * Step 3 is worth stating precisely because it is easy to describe wrongly: the
 * reference does **not** strip a `_TTM` / `_QUARTERLY` / `_CALC` suffix family.
 * It keeps what the pipeline *queried* and drops everything else, and derived
 * concepts happen to be exactly what is left over. That is the same rule the
 * data tab's raw/derived split already uses (`factIsDerived` in `pivot.ts` is
 * `!candidates.has(concept)`), so the two features share one definition of
 * "derived" rather than two that agree by accident.
 *
 * Sorted, which is `sorted()` on Python strings: code-point order. There is no
 * registry catalogue to inherit an order from here.
 *
 * The ticker filter is implicit -- a per-ticker export file holds one ticker's
 * rows -- and the frame is the *unwindowed* one, exactly as the reference
 * computes availability before it windows anything.
 */
export function availableRawConcepts(
  facts: Frame | null | undefined,
  candidates: ReadonlySet<string> | null,
  includeDerived = false,
): string[] {
  if (!facts) return [];
  const seen = new Set<string>();
  for (let i = 0; i < facts.rowCount; i += 1) {
    if (facts.value[i] === null) continue;
    seen.add(facts.concept[i]);
  }
  const out = includeDerived
    ? [...seen]
    // A missing candidates file narrows to nothing rather than to everything:
    // silently showing every derived column would be the wrong way to fail.
    : [...seen].filter((c) => candidates?.has(c) ?? false);
  return out.sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
}

export function buildRawFacts(
  facts: Frame | null | undefined,
  candidates: ReadonlySet<string> | null,
  ticker: string,
  options: RawOptions = {},
): RawResult {
  const {
    requested = null,
    years = RAW_YEARS,
    includeDerived = false,
    anchor,
  } = options;

  const offerable = availableRawConcepts(facts, candidates, includeDerived);
  // figures.py:1112 `[c for c in available if c in set(concepts)]` -- the request
  // narrows, and the *order* stays `available`'s. Same discipline as
  // `selectMetricIds`, reached from a different catalogue.
  const wanted = requested === null ? null : new Set(requested);
  const panels = wanted === null ? offerable : offerable.filter((c) => wanted.has(c));

  if (panels.length === 0 || !facts) return { figure: null, panels: [], offerable };

  const figure = createGrid(
    panels,
    RAW_ROW_HEIGHT,
    `Raw Facts ${ticker}`,
    // figures.py:1144 sets no `hovermode`, unlike every other builder.
    null,
  );
  // `as_of=None`, so `seriesFor` is called with no `until`.
  const cutoff = windowCutoff(years, anchor);

  panels.forEach((concept, idx) => {
    const series = seriesFor(facts, concept, cutoff);
    drawBarPanel(figure, idx, {
      concept,
      // The trace is built from the whole windowed series, nulls included:
      // figures.py:1134 plots `series`, while it is `series.dropna(...)` that
      // decides whether to draw at all. Two different frames, one line apart.
      x: series.x,
      y: series.y,
      empty: !hasAnyValue(series),
    });
  });

  return { figure, panels, offerable };
}
