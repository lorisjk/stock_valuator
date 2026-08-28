/**
 * `figures.py`'s `_snapshot_point` (figures.py:306) — the current-value marker's
 * rule, as a pure function.
 *
 * A rule module rather than four lines inside `buildValuation`, for the same
 * reason `mean.ts` and `notice.ts` are modules: the interesting part of this
 * feature is *when the marker is absent*, and there are three separate ways for
 * that to happen. Each is checkable from Node against the real export.
 *
 * The three:
 *
 *   1. **No row for this concept.** Measured across all 609 bundled tickers ×
 *      the 13 valuation concepts: a concept either has exactly one row with a
 *      real number, or no row at all. `value` is *never* null in the export and
 *      no (ticker, concept) pair ever appears twice. So in practice "no snapshot
 *      value" and "not computed for this concept" are the same condition —
 *      absence — and the `dropna`/`sort`/`last` below are faithfulness to the
 *      parquet the JSON is projected from, not dead weight against it.
 *   2. **The profile hides it.** `_snapshot_point`'s docstring claims a hidden
 *      concept simply has no row; that holds exactly, 0 exceptions in 7,917
 *      (ticker, concept) pairs. So this case needs no code of its own — it
 *      arrives as case 1.
 *   3. **`as_of` predates the snapshot.** figures.py:333, and note the direction:
 *      the marker is suppressed when `as_of < stamp`, so an `as_of` *on or
 *      after* the snapshot's own date keeps it. A historical view must not show
 *      a value that date could not have known; a view dated on the snapshot day
 *      legitimately can.
 *
 * There is a fourth absence that is **not** here, because it belongs to the
 * panel rather than to the point: `plot_metric` returns early on an empty panel
 * (figures.py:358) *before* it would draw the marker, so a concept whose filed
 * series is empty in the current window shows "No Data" and no marker even when
 * a current value exists. 17 (ticker, concept) pairs in the export have a
 * snapshot value and no filed history at all. `drawPanel`'s own early return
 * reproduces this without a line of new code.
 */
import type { Frame } from "../contracts.ts";

/** figures.py:22 `_SNAPSHOT_COLOR` — green, "and never red, which is already the mean line and the reference line". */
export const SNAPSHOT_COLOR = "#2ca02c";

/** figures.py:470 — the legend entry, the trace name and the first hover line, all one string. */
export const SNAPSHOT_NAME = "Snapshot (current value)";

/** figures.py:471 — one group, so the single legend entry toggles every panel's marker at once. */
export const SNAPSHOT_LEGENDGROUP = "snapshot";

export interface SnapshotPoint {
  /** The snapshot's own `end`. This *is* the marker's x-position — see below. */
  end: Date;
  value: number;
}

/**
 * The current value for one panel, or null.
 *
 * `asOf` is the port's `anchor`, which is the port's `as_of`: **undefined means
 * `None`**, and `None` disables the check entirely rather than defaulting to
 * today (figures.py:333 tests `as_of is not None` first). app.py:867 defaults it
 * to `None` behind an opt-in checkbox, so that is the production path on both
 * sides until item 15 builds the control.
 */
export function snapshotPoint(
  frame: Frame | undefined,
  concept: string,
  asOf?: Date,
): SnapshotPoint | null {
  if (!frame || frame.rowCount === 0) return null;

  // `rows.dropna(subset=["end", "value"])` then `sort_values("end").iloc[-1]`.
  // Reproduced as a running maximum: same answer, no allocation, and it keeps
  // the tie-break explicit — pandas' sort is stable, so among equal dates the
  // last row in file order wins, which is what `>=` gives.
  let latest: SnapshotPoint | null = null;
  for (let i = 0; i < frame.rowCount; i += 1) {
    if (frame.concept[i] !== concept) continue;
    const value = frame.value[i];
    if (value === null || Number.isNaN(value)) continue;
    const end = frame.end[i];
    if (latest === null || end.getTime() >= latest.end.getTime()) latest = { end, value };
  }
  if (latest === null) return null;

  if (asOf !== undefined && asOf.getTime() < latest.end.getTime()) return null;
  return latest;
}

/** `f"{stamp:%d.%m.%Y}"`. UTC getters because `parseDate` builds the dates as UTC midnight. */
export function germanDate(date: Date): string {
  const day = String(date.getUTCDate()).padStart(2, "0");
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  return `${day}.${month}.${date.getUTCFullYear()}`;
}

/** figures.py:477-481 — the literal date is baked in, not a `%{x}` directive. */
export const snapshotHovertemplate = (end: Date) =>
  `${SNAPSHOT_NAME}<br>Date: ${germanDate(end)}<br>Value: %{y}<extra></extra>`;
