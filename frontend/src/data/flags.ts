/**
 * `render_flag_section`'s summary rows (app.py:436), as a function of the pivot
 * the per-period table already renders.
 *
 * The reference's docstring is the whole justification and it is worth keeping
 * next to the code: *"A flag is the pipeline saying where it is unsure, and a
 * column of zeros between two ratios buries exactly that. The summary answers
 * the question a 0/1 column makes you reconstruct by eye: how often, and how
 * recently."* So this is not a second view of the flags; it is the answer to the
 * two questions the 0/1 grid poses and does not answer.
 *
 * **One input, and it is the same object the table below is drawn from.** Item
 * 17 established the discipline -- a summary that recomputes its own source can
 * disagree with what is on screen, and the only way it cannot is for there to be
 * one source. `DataTab` builds `flagsPivot` once; this reads it, and
 * `headPeriods(flagsPivot, periods)` renders it. Nothing here touches
 * `metrics_long` again.
 *
 * **Over every period, not the periods on screen.** `render_flag_section` builds
 * its rows from `wide` and applies `.head(periods)` only inside the expander
 * (app.py:458), so "Show all periods" moves the table underneath and leaves the
 * summary alone. That is the right way round: `raised` is a claim about the
 * ticker's filed history, not about the current scroll.
 *
 * Pure and React-free, like `pivot.ts`, so the comparison against pandas can be
 * run from Node over the exported JSON.
 */
import type { Pivot } from "./pivot.ts";

export interface FlagSummaryRow {
  /** The concept name, as filed -- the reference does not prettify it either. */
  flag: string;
  /** Periods whose value is exactly 1. */
  raised: number;
  /** Periods with a value at all; a gap is neither raised nor clear. */
  evaluated: number;
  /** Newest period the flag was raised in, or `null` -- rendered as an em dash. */
  mostRecent: string | null;
}

/**
 * `column.dropna()`, then `column == 1.0`, per flag column.
 *
 * Three details are pandas' and are reproduced rather than approximated:
 *
 * 1. **`dropna()` before the count**, so `evaluated` is the periods the pipeline
 *    actually judged. A flag that exists for 34 of a ticker's 72 periods reads
 *    `8 / 34`, not `8 / 72` -- AAPL's `inorganic_contaminated` is exactly that,
 *    and the difference is the whole point of showing the denominator.
 * 2. **`== 1.0` rather than truthiness.** Every flag in the export is 0 or 1, so
 *    the two agree today; they stop agreeing the first time the pipeline emits a
 *    count instead of a bit, and at that point the reference reports zero raised
 *    while a truthy test reports all of them.
 * 3. **`raised.index.max()`**, which is a maximum over the labels and not a
 *    position in the frame. `Pivot.ends` is newest-first, so the first raised
 *    row would give the same answer -- but only while that ordering holds, and
 *    an ISO date compares lexicographically, so the maximum is taken directly
 *    and the row order is not relied on.
 *
 * A cell the export could not carry as a number (`±inf`, see
 * `Pivot.nonfinite`) counts as evaluated and not raised, because that is what
 * `dropna()` does with an infinity. No flag cell is one today -- all 143,774 are
 * 0.0 or 1.0 -- so this branch is untaken and deliberately not the default.
 */
export function flagSummary(pivot: Pivot): FlagSummaryRow[] {
  return pivot.concepts.map((flag, column) => {
    let raised = 0;
    let evaluated = 0;
    let mostRecent: string | null = null;
    for (let row = 0; row < pivot.ends.length; row += 1) {
      const value = pivot.cells[row][column];
      const infinite = pivot.nonfinite.has(`${row},${column}`);
      if (value === null && !infinite) continue;
      evaluated += 1;
      if (value === 1) {
        raised += 1;
        const end = pivot.ends[row];
        if (mostRecent === null || end > mostRecent) mostRecent = end;
      }
    }
    return { flag, raised, evaluated, mostRecent };
  });
}
