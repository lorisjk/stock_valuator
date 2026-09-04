/**
 * What the two controls start with, and what happens to their values when the
 * context changes. Plain values and pure functions -- no React -- so the rules
 * can be verified from Node rather than by clicking.
 *
 * This is the part of the UI that is a *product* decision rather than a
 * transcription of `figures.py`, and the decisions are made here rather than
 * inside the components so there is a single place to argue with.
 *
 * The picker needs a migration rule because its option set varies by ticker.
 * **The window does not**: its range is 1-15 for every chart, ticker and
 * profile, so a value the user sets is simply carried, and there is no
 * `migrateYears` to go with `migrateSelection`. If item 15's as-of ever makes
 * the range depend on the data, this is where that function would go.
 */
import type { ChartId } from "../contracts.ts";
import { FUNDAMENTALS_YEARS } from "./fundamentals.ts";
import { GROWTH_YEARS } from "./growth.ts";
import { VALUATION_YEARS } from "./valuation.ts";

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

/* --------------------------------------------------------------- the window */

/**
 * The years slider's range, matching `st.slider("Window (years)", 1, 15, ...)`
 * at app.py:907, :919 and :931.
 *
 * **The ceiling is the reference's, and it is not the data's.** Measured
 * against the export: the frames reach back to 2005-12-31 / 2007-09-30, a span
 * of 18.9 to 20.7 years, and a 15-year window still drops 55,972 fundamentals
 * rows, 51,872 valuation rows and 28,321 growth rows -- 10-15% of each. It
 * takes `years = 21` to include everything. So 15 is not "all history"; it is a
 * choice the reference made, and this rebuild keeps it rather than inventing a
 * setting Streamlit cannot produce. See the report -- the gap is a finding, not
 * an accident of this range.
 *
 * The floor of 1 excludes exactly one value, and `years = 0` is degenerate
 * rather than merely small: the cutoff becomes today, every period end is in
 * the past, and all three charts return a full grid of "No Data" panels. The
 * builders handle it without special-casing and the verification still exercises
 * it through the API; the control simply does not offer it.
 */
export const YEARS_MIN = 1;
export const YEARS_MAX = 15;

/**
 * The window each chart opens on -- **taken from the builders**, not restated.
 *
 * The Streamlit sliders default to 15 / 5 / 15, and `build_fundamentals`,
 * `build_valuation` and `build_growth` default their own `years` to the same
 * three numbers. Deriving the control's default from the builder's constant
 * makes that agreement structural: the chart you get before touching the slider
 * is by construction the chart the builder draws when nobody passes `years`.
 * Restating `5` here would have made it a coincidence that holds until someone
 * edits one of the two.
 */
export const DEFAULT_YEARS: Record<ChartId, number> = {
  fundamentals: FUNDAMENTALS_YEARS,
  valuation: VALUATION_YEARS,
  growth: GROWTH_YEARS,
};
