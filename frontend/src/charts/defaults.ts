/**
 * What a picker starts with, and what happens to a selection when the ticker
 * changes. Pure functions over id lists -- no React, no registry lookups -- so
 * the ticker-switch rule can be verified from Node rather than by clicking.
 *
 * This is the one part of the picker that is a *product* decision rather than a
 * transcription of `figures.py`, and both decisions are made here rather than
 * inside the component so there is a single place to argue with.
 */
import type { ChartId } from "../contracts.ts";

/**
 * The metric each tab opens on, taken from what `app.py` *meant*.
 *
 * All three Streamlit defaults are written `[i for i in ids if i in ("x")]` --
 * a string in parentheses is a string, so `in` is a substring test, not a
 * membership test. Two of them land on the right metric because an id is a
 * substring of itself. The growth one is a typo, `"Revenueyoy_growth"`, that
 * substring-matches `Revenue` by luck: written as a real tuple it would select
 * **nothing**, on every one of the 24 profiles. These are the ids the author
 * meant, which is what a rebuild should carry -- see the report.
 */
export const PREFERRED_DEFAULT: Record<ChartId, string> = {
  fundamentals: "revenue_yoy_growth",
  valuation: "pe_ratio",
  growth: "Revenue",
};

/**
 * The initial selection for one chart: the preferred metric, or the first the
 * profile does offer.
 *
 * The fallback is not defensive padding. `pe_ratio` is hidden for `reit`, so
 * Streamlit's valuation tab opens **empty** for all 29 REITs and shows
 * "Nothing selected, or no valuation data for this ticker." -- a message about
 * a selection the user never made. And it cannot be fixed by picking a better
 * constant: measured over the 13 valuation metrics, **no id is offered by all
 * 24 profiles**, so every possible hardcoded valuation default has a hole
 * somewhere. Fundamentals has two universal ids and growth four; valuation has
 * none. A fallback is therefore required, not merely prudent.
 */
export function defaultSelection(chart: ChartId, offerable: readonly string[]): string[] {
  if (offerable.length === 0) return [];
  const preferred = PREFERRED_DEFAULT[chart];
  return offerable.includes(preferred) ? [preferred] : [offerable[0]];
}

/**
 * The selection to use for a ticker, given what the user last picked.
 *
 * **Intersect, then fall back.** Keeping the parts of the selection the new
 * profile also offers is what makes "look at the same multiple across three
 * tickers" work, which is the reason people switch tickers at all. Resetting to
 * the default every time would throw that away on every switch.
 *
 * The fallback covers the case intersection alone handles badly: a selection
 * the new profile offers *none* of. A REIT has no `pe_ratio`, so a user who
 * narrowed AAPL down to P/E and then switched would land on an empty chart with
 * no indication of why. Falling back to this profile's default shows something
 * readable instead.
 *
 * **An empty selection is honoured, not corrected.** `previous = []` means the
 * user cleared the picker deliberately; falling back there would make the
 * control impossible to clear. Only a *non-empty* selection that survives
 * nothing is replaced.
 *
 * The result is in catalogue order, because it is built by filtering
 * `offerable` rather than `previous` -- the same ordering rule the builders
 * follow, so what the picker holds and what the grid renders cannot disagree.
 */
export function migrateSelection(
  chart: ChartId,
  previous: readonly string[],
  offerable: readonly string[],
): string[] {
  const kept = offerable.filter((id) => previous.includes(id));
  if (kept.length > 0) return kept;
  return previous.length === 0 ? [] : defaultSelection(chart, offerable);
}
