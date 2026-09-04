/**
 * `cadence_markers` (app.py:257): which facts columns get a ᵃ or a ᵐ, and the
 * legend that explains them.
 *
 * **Per column, not per cell** — and the reference is emphatic that this is a
 * measurement rather than a convenience (app.py:260-266):
 *
 * > *"`calculate_ttm` and `parse_edgar.annual_ttm_values` are disjoint by
 * > construction -- the annual path runs only where the quarterly extraction
 * > produced nothing -- so provenance is a property of the series. 0 of 5,836
 * > series in the exported frame carry both labels. A per-cell suffix would cost
 * > readability in every row to express something that never varies within a
 * > column."*
 *
 * Re-measured on the current export, which has grown since that number was
 * written: **7,099 (ticker, concept) series carry provenance — 6,959
 * quarterly-only, 140 annual-only, and still 0 mixed.** So the ᵐ branch below is
 * unreachable today. It is implemented anyway, for the reason the docstring
 * gives: a marker that quietly rounded a mixed series to "annual" would assert
 * something the pipeline has not established.
 *
 * **The marker names a series, not a window.** It is computed from every row the
 * ticker has, so a column keeps its ᵃ even when the periods currently on screen
 * happen to hold no annual-cadence value. That is the point — the reader is
 * being told how this series is built, which does not change with the scroll.
 *
 * The legend is returned as the **markdown string app.py builds**, character for
 * character, rather than as a structure to be re-rendered. `react-markdown` is
 * already in the bundle for the update notice, so the port renders the same text
 * through the same kind of renderer, and the comparison against Python is a
 * string equality rather than a DOM approximation.
 */
import type { Frame } from "../contracts.ts";

/** app.py:253 — modifier letter small a. Already superscript; no `<sup>` needed. */
export const ANNUAL_CADENCE_MARKER = "ᵃ";
/** app.py:254 — modifier letter small m. */
export const MIXED_CADENCE_MARKER = "ᵐ";

/** config.py:214. The only two values `ttm_source` takes; confirmed on the export. */
const ANNUAL_FACT = "annual_fact";

export interface Cadence {
  /** concept -> marker, for the marked concepts only. */
  markers: ReadonlyMap<string, string>;
  /** The legend, as markdown. `""` when nothing is marked. */
  legend: string;
}

const NONE: Cadence = { markers: new Map(), legend: "" };

const backticked = (concepts: readonly string[]) => concepts.map((c) => `\`${c}\``).join(", ");

/**
 * `cadence_markers(frame, ticker)`, minus the ticker.
 *
 * The reference filters `frame["ticker"] == ticker` because it holds one frame
 * for all 609; here `facts_full` arrives as `tickers/{T}.facts.json` and is
 * already one ticker's, so that clause has nothing to do. The other half of its
 * filter — `ttm_source.notna()` — is real and is kept: a row with no value
 * carries no provenance, and counting `null` as a third label would invent a
 * cadence for an empty cell.
 *
 * `frame.text` not carrying `ttm_source` at all maps to app.py:272's
 * `if "ttm_source" not in frame.columns` — both return "no markers" rather than
 * failing, so an older bundle degrades instead of breaking.
 */
export function cadenceMarkers(frame: Frame | null | undefined): Cadence {
  const source = frame?.text.get("ttm_source");
  if (!frame || !source) return NONE;

  // concept -> the distinct labels seen for it. `groupby(...).agg(set)`.
  const sources = new Map<string, Set<string>>();
  for (let i = 0; i < frame.rowCount; i += 1) {
    const label = source[i];
    if (label === null || label === undefined) continue;
    const concept = frame.concept[i];
    const seen = sources.get(concept);
    if (seen) seen.add(label);
    else sources.set(concept, new Set([label]));
  }
  if (sources.size === 0) return NONE;

  // Ascending by code point, which is pandas' `sorted` over these ASCII names --
  // the same ordering `pivot.ts` documents and for the same reason.
  const byCodePoint = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);
  const annual: string[] = [];
  const mixed: string[] = [];
  for (const [concept, seen] of sources) {
    if (seen.size > 1) mixed.push(concept);
    else if (seen.has(ANNUAL_FACT)) annual.push(concept);
  }
  annual.sort(byCodePoint);
  mixed.sort(byCodePoint);
  if (annual.length === 0 && mixed.length === 0) return NONE;

  const markers = new Map<string, string>();
  for (const concept of annual) markers.set(concept, ANNUAL_CADENCE_MARKER);
  for (const concept of mixed) markers.set(concept, MIXED_CADENCE_MARKER);

  // app.py:283-303, verbatim. The closing paragraph is appended only on this
  // path, so a ticker with nothing marked gets no legend at all rather than a
  // lone sentence about columns that carry no provenance.
  const parts: string[] = [];
  if (annual.length > 0) {
    parts.push(
      `${ANNUAL_CADENCE_MARKER} **annual cadence** — ${backticked(annual)}. ` +
        "This filer discloses the item once a year, so the value is the 12-month " +
        "figure taken as filed rather than four quarters summed. One point a year " +
        "is complete coverage of what was published, not a gap.",
    );
  }
  if (mixed.length > 0) {
    parts.push(
      `${MIXED_CADENCE_MARKER} **mixed cadence** — ${backticked(mixed)}: ` +
        "some periods summed from quarters, others read from a 12-month fact.",
    );
  }
  parts.push(
    "Unmarked `_TTM` columns are summed from four quarters. `FCF_TTM`, `EBITDA_TTM`, " +
      "`FFO_TTM` and `EPS_TTM_CALC` are built from other columns further down the " +
      "pipeline and carry no provenance of their own — theirs is their inputs', " +
      "visible in this same table.",
  );
  // Two trailing spaces before the newline: a markdown hard line break, which is
  // what `st.caption`'s markdown does with `"  \n"` and what CommonMark — hence
  // react-markdown — does with it too.
  return { markers, legend: parts.join("  \n") };
}
