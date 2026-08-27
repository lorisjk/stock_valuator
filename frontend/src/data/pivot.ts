/**
 * The data tab's pivot and column rules: `app.py`'s `pivot_ticker`,
 * `is_quality_flag`, `fact_base`, `fact_is_derived` and `order_fact_columns`,
 * in TypeScript.
 *
 * No React and no DOM, for the same reason `load.ts` has none: everything here
 * runs unchanged in Node, which is what makes the element-wise comparison
 * against the parquet-derived reference possible.
 *
 * **This is a different pivot axis from the one the charts use.** `load.ts`
 * reconstructs a frame into parallel arrays and every chart then walks it
 * concept by concept, drawing one series per panel -- concept-major, and the
 * period axis is whatever plotly is handed. The data tab needs the transpose of
 * that: rows = period end, columns = concept, one cell per pair. Reusing
 * `reconstructFrame`'s output as the input is the reuse that was available
 * (nothing refetches, nothing re-parses dates); the pivot itself is genuinely a
 * second pass and is written here rather than bolted onto the chart path.
 */
import type { Frame } from "../contracts.ts";

/** app.py:47 -- 4 years of quarters. */
export const DEFAULT_TABLE_PERIODS = 16;

/**
 * A pivot: rows = period end (newest first), columns = concept (ascending).
 *
 * Cells are `null` where the source had no value, and stay that way -- see
 * `pivotTicker`. `nonfinite` names the cells whose value was +-inf in the
 * pipeline, which the export cannot carry as a number (per_ticker_export_report
 * §1.4); the cell itself is null there, and a renderer that reads this map can
 * say "infinite" instead of "missing".
 */
export interface Pivot {
  /** Row labels, `YYYY-MM-DD`, newest first. */
  ends: string[];
  /** Column labels, ascending by code point -- pandas' own column order. */
  concepts: string[];
  /** `cells[row][column]`. `null` is a real absence, never a filled zero. */
  cells: (number | null)[][];
  /** `"row,column" -> sign` for the cells whose true value is +-inf. */
  nonfinite: Map<string, "Infinity" | "-Infinity">;
}

export const EMPTY_PIVOT: Pivot = { ends: [], concepts: [], cells: [], nonfinite: new Map() };

/** `Date` -> `YYYY-MM-DD`, read back out of the UTC fields `load.ts` parsed into. */
export function isoDate(date: Date): string {
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const day = String(date.getUTCDate()).padStart(2, "0");
  return `${date.getUTCFullYear()}-${month}-${day}`;
}

/**
 * Ascending by UTF-16 code unit, which for these ASCII names is Python's own
 * `sorted` order. Deliberately not `localeCompare`: that folds case, so it would
 * put `Revenue_TTM` and `revenue_yoy_growth` in an order pandas never produces.
 */
const byCodePoint = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);

/**
 * `app.py:176 pivot_ticker`, for a frame already narrowed to one ticker.
 *
 * Three semantics are reproduced deliberately, each checked against pandas
 * rather than assumed:
 *
 * 1. **`aggfunc="first"` is first *non-null*, not first row.** pandas'
 *    `GroupBy.first` skips NaN. There are 22 duplicate `(ticker, end, concept)`
 *    groups in the export -- NAVN, PYPL, BF-B, HNGE, KMI -- and every one of
 *    them is a real value followed by nulls, so "first row" would agree today
 *    and disagree the first time the pipeline emits them the other way round.
 * 2. **`dropna=False` keeps an all-null column.** A concept that exists for the
 *    ticker but is null in every period stays as an all-null column, because
 *    "not applicable to this business model" versus "extraction failed" is the
 *    question this tab exists to answer. 298 of 609 tickers have at least one
 *    such column in `facts_full` within the default 16 periods alone.
 * 3. **Rows are the observed `end` values, newest first; columns the observed
 *    concepts, ascending.** Both dtypes are plain `object` in the parquet, not
 *    categorical, so no unobserved label can appear -- checked, because a
 *    categorical column under `dropna=False` would have produced every category.
 */
export function pivotTicker(frame: Frame | undefined): Pivot {
  if (!frame || frame.rowCount === 0) return EMPTY_PIVOT;

  const ends = [...new Set(frame.end.map(isoDate))].sort(byCodePoint).reverse();
  const concepts = [...new Set(frame.concept)].sort(byCodePoint);
  const rowAt = new Map(ends.map((end, i) => [end, i]));
  const columnAt = new Map(concepts.map((concept, i) => [concept, i]));

  const cells: (number | null)[][] = ends.map(() => concepts.map(() => null));
  const nonfinite = new Map<string, "Infinity" | "-Infinity">();

  for (let i = 0; i < frame.rowCount; i += 1) {
    const value = frame.value[i];
    const sign = frame.nonfiniteRows.get(i);
    // Rule 1: the first non-null wins, so a later null never overwrites it.
    // A +-inf row counts as a value even though the array holds null there --
    // the pipeline had a number, and skipping it would report a gap instead.
    if (value === null && sign === undefined) continue;
    const row = rowAt.get(isoDate(frame.end[i]));
    const column = columnAt.get(frame.concept[i]);
    if (row === undefined || column === undefined) continue;
    const key = `${row},${column}`;
    if (cells[row][column] !== null || nonfinite.has(key)) continue;
    if (sign !== undefined) nonfinite.set(key, sign);
    else cells[row][column] = value;
  }
  return { ends, concepts, cells, nonfinite };
}

/** The newest `count` periods, as a pivot in its own right. */
export function headPeriods(pivot: Pivot, count: number): Pivot {
  if (count >= pivot.ends.length) return pivot;
  const nonfinite = new Map<string, "Infinity" | "-Infinity">();
  for (const [key, sign] of pivot.nonfinite) {
    if (Number(key.slice(0, key.indexOf(","))) < count) nonfinite.set(key, sign);
  }
  return {
    ends: pivot.ends.slice(0, count),
    concepts: pivot.concepts,
    cells: pivot.cells.slice(0, count),
    nonfinite,
  };
}

/** Keep only these columns, in the order given. Unknown names are dropped. */
export function selectColumns(pivot: Pivot, concepts: string[]): Pivot {
  const from = new Map(pivot.concepts.map((concept, i) => [concept, i]));
  const taken = concepts.filter((concept) => from.has(concept));
  const sources = taken.map((concept) => from.get(concept) as number);
  const nonfinite = new Map<string, "Infinity" | "-Infinity">();
  sources.forEach((source, column) => {
    for (let row = 0; row < pivot.ends.length; row += 1) {
      const sign = pivot.nonfinite.get(`${row},${source}`);
      if (sign) nonfinite.set(`${row},${column}`, sign);
    }
  });
  return {
    ends: pivot.ends,
    concepts: taken,
    cells: pivot.cells.map((row) => sources.map((source) => row[source])),
    nonfinite,
  };
}

/**
 * One column's values, with `Infinity` back where the export could not carry it.
 *
 * The formatting rule reads a column's own maximum magnitude (app.py:373), and
 * the reference reads it off the **parquet**, which still holds the +-inf the
 * JSON had to write as `null`. Those cells are not merely missing from the
 * magnitude scan -- they are the largest value in it, and dropping them changes
 * the whole column's treatment: CEG's `EPS_TTM_CALC` is `9.62` in Streamlit and
 * was `9.6250` here, because an infinite maximum puts the column above
 * `ABSOLUTE_THRESHOLD` and a finite one of 11.9 does not.
 *
 * So the sidecar is folded back in for the magnitude scan only. The rendered
 * cell is still drawn as an infinity by the table, and the CSV still writes
 * `inf` -- this changes which *rule* the column's finite values are printed
 * under, which is exactly what the reference does.
 */
export function columnMagnitudes(pivot: Pivot, column: number): (number | null)[] {
  return pivot.cells.map((row, index) => {
    const sign = pivot.nonfinite.get(`${index},${column}`);
    if (sign) return sign === "Infinity" ? Number.POSITIVE_INFINITY : Number.NEGATIVE_INFINITY;
    return row[column];
  });
}

/** Columns that are null in every row shown -- the null-column caption's number. */
export function allNullColumns(pivot: Pivot): number {
  let count = 0;
  for (let column = 0; column < pivot.concepts.length; column += 1) {
    let empty = true;
    for (let row = 0; row < pivot.ends.length && empty; row += 1) {
      if (pivot.cells[row][column] !== null || pivot.nonfinite.has(`${row},${column}`)) {
        empty = false;
      }
    }
    if (empty) count += 1;
  }
  return count;
}

/* ----------------------------------------------------------- quality flags */

/**
 * app.py:211. The comment there is the reasoning and it has not changed: neither
 * `config.py` nor `quality.py` can supply this test, so the rule is name-based
 * and lives in exactly one place on each side.
 */
const QUALITY_FLAG_CONCEPTS = new Set(["fcf_exceeds_ebitda", "inorganic_contaminated"]);

export const isQualityFlag = (concept: string) =>
  concept.endsWith("_flag") || QUALITY_FLAG_CONCEPTS.has(concept);

/* ------------------------------------------------------ the raw/derived split */

/** app.py:229 `_FACT_SUFFIXES`. */
const FACT_SUFFIXES = ["_CALC", "_TTM", "_QUARTERLY"];

/** app.py:230 `fact_base` -- suffixes stripped repeatedly, so `X_TTM_CALC` -> `X`. */
export function factBase(concept: string): string {
  let base = concept;
  for (let changed = true; changed; ) {
    changed = false;
    for (const suffix of FACT_SUFFIXES) {
      if (base.endsWith(suffix) && base.length > suffix.length) {
        base = base.slice(0, -suffix.length);
        changed = true;
      }
    }
  }
  return base;
}

/**
 * app.py:218 `fact_is_derived` -- structural, not a suffix match.
 *
 * The names the pipeline asks EDGAR for are exactly `get_concept_candidates`'s
 * keys, so anything else in the facts frame was derived. That is what catches
 * `PPNR`, `CoreOperatingEarnings` and `TangibleEquity`, which are derived and
 * carry no suffix -- a suffix rule calls all three raw.
 */
export const factIsDerived = (candidates: ReadonlySet<string>, concept: string) =>
  !candidates.has(concept);

/**
 * app.py:245 `order_fact_columns` -- grouped by base concept, raw before its own
 * derivations, then by name. Python sorts the tuple `(base, derived, name)` with
 * `False < True`, which is what the `? 1 : 0` reproduces.
 */
export function orderFactColumns(candidates: ReadonlySet<string>, concepts: string[]): string[] {
  return [...concepts].sort((a, b) => {
    const base = byCodePoint(factBase(a), factBase(b));
    if (base !== 0) return base;
    const derived =
      (factIsDerived(candidates, a) ? 1 : 0) - (factIsDerived(candidates, b) ? 1 : 0);
    return derived !== 0 ? derived : byCodePoint(a, b);
  });
}

export type FactFilter = "All" | "Raw only" | "Derived only";

export const FACT_FILTERS: FactFilter[] = ["All", "Raw only", "Derived only"];

/** app.py:581 -- `All` keeps everything, the other two split on `fact_is_derived`. */
export function filterFactColumns(
  candidates: ReadonlySet<string>,
  concepts: string[],
  filter: FactFilter,
): string[] {
  const keep =
    filter === "All"
      ? concepts
      : concepts.filter(
          (concept) => (filter === "Derived only") === factIsDerived(candidates, concept),
        );
  return orderFactColumns(candidates, keep);
}
