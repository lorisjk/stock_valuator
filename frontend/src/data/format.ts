/**
 * `app.py`'s display formatting: `format_for_display` (app.py:353), its two
 * helpers (app.py:319, app.py:328) and `_percent_applies` (app.py:334).
 *
 * Pure, no React and no DOM, like `pivot.ts` next to it -- so the whole thing
 * runs in Node and every string it produces can be compared against the
 * reference's own output for the same double.
 *
 * **This module returns strings and never touches a value.** That is the whole
 * architectural point of the item, and app.py:308 states it as a rule: the
 * display frame is a frame of *strings* and is only ever handed to the table;
 * downloads and copy blocks are produced from the numeric frame. Nothing here
 * takes a `Pivot` and nothing here mutates one -- `formatCell` takes a `number`
 * and returns a `string`, which makes the separation structural rather than a
 * convention someone has to remember.
 */
import type { Metric, Registry } from "../contracts.ts";

/** app.py:316. Above this a column is absolute (currency, counts); below, a ratio. */
export const ABSOLUTE_THRESHOLD = 1e4;

/** app.py:312 `_MAGNITUDES`, in the order the reference tests them. */
const MAGNITUDES: readonly (readonly [number, string])[] = [
  [1e12, "T"],
  [1e9, "B"],
  [1e6, "M"],
  [1e3, "K"],
];

/* ------------------------------------------------- exact fixed-point rounding */

/**
 * Python's `f"{value:.Nf}"`, exactly -- including how it breaks a tie.
 *
 * Neither obvious approach works, and both were measured over 120,022 real
 * values from the export plus every `value / cutoff` quotient they produce:
 *
 * - **`toFixed`** rounds the exact binary value, which is right, but breaks a
 *   tie *away from zero* where Python breaks it *to even*: `0.125` is exactly
 *   representable, so Python writes `0.12` and `toFixed(2)` writes `0.13`.
 *   24 mismatches. It also drops the sign of `-0`.
 * - **`Intl.NumberFormat` with `roundingMode: "halfEven"`** is worse -- 363
 *   mismatches -- because it rounds the number's *shortest decimal
 *   representation* rather than its value. The double nearest `2.675` is
 *   `2.67499999999999982...`, so Python writes `2.67` and Intl, seeing "2.675",
 *   writes `2.68`.
 *
 * So the rounding is done exactly, on the integer the double actually is. Every
 * finite double is `m x 2^e` for integers `m` and `e`; `value x 10^digits` is
 * therefore the exact rational `m x 10^digits / 2^-e`, and BigInt division with
 * the remainder compared against half the divisor decides the digit with no
 * floating point involved at any step.
 */
function fixed(value: number, digits: number, grouping: boolean): string {
  // Python prints an overflowed float as `inf`, and `formatRatio`'s `value *
  // 100` is the one arithmetic step here that can reach it. No exported value
  // is within 296 orders of magnitude of that, so this is unreachable on real
  // data -- it is here because it was the single difference in a 1,080,090
  // string comparison against the reference, and one unexplained difference is
  // worth two lines.
  if (!Number.isFinite(value)) return value > 0 ? "inf" : "-inf";
  // The sign is taken from the bit, not from `value < 0`, so `-0.0` keeps its
  // sign the way Python's `f"{-0.0:.2f}"` -> "-0.00" does, and so does a
  // negative value small enough to round to zero.
  const negative = value < 0 || Object.is(value, -0);
  const magnitude = Math.abs(value);

  const bits = new DataView(new ArrayBuffer(8));
  bits.setFloat64(0, magnitude);
  const raw = bits.getBigUint64(0);
  const exponent = Number((raw >> 52n) & 0x7ffn);
  const fraction = raw & 0xfffffffffffffn;
  // Subnormals carry no implicit leading 1 and sit one exponent step higher.
  const mantissa = exponent === 0 ? fraction : fraction + (1n << 52n);
  const scale = exponent === 0 ? -1074 : exponent - 1075;

  const power = 10n ** BigInt(digits);
  let scaled: bigint;
  if (scale >= 0) {
    scaled = mantissa * (1n << BigInt(scale)) * power; // exact, nothing to round
  } else {
    const divisor = 1n << BigInt(-scale);
    const numerator = mantissa * power;
    scaled = numerator / divisor;
    const twiceRemainder = (numerator % divisor) * 2n;
    if (twiceRemainder > divisor) scaled += 1n;
    else if (twiceRemainder === divisor && scaled % 2n === 1n) scaled += 1n; // half to even
  }

  const text = scaled.toString().padStart(digits + 1, "0");
  let whole = digits === 0 ? text : text.slice(0, -digits);
  const decimals = digits === 0 ? "" : `.${text.slice(-digits)}`;
  if (grouping) whole = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `${negative ? "-" : ""}${whole}${decimals}`;
}

/* -------------------------------------------------------------- the two rules */

/**
 * app.py:319 `_format_absolute` -- the largest magnitude whose cutoff the value
 * reaches, two decimals, thousands separators. `null` renders as the empty
 * string, which is what `pd.isna` produces there.
 */
export function formatAbsolute(value: number | null): string {
  if (value === null || Number.isNaN(value)) return "";
  for (const [cutoff, suffix] of MAGNITUDES) {
    if (Math.abs(value) >= cutoff) return `${fixed(value / cutoff, 2, true)}${suffix}`;
  }
  return fixed(value, 2, true);
}

/** app.py:328 `_format_ratio` -- percent with two decimals, or four decimals flat. */
export function formatRatio(value: number | null, percent: boolean): string {
  if (value === null || Number.isNaN(value)) return "";
  return percent ? `${fixed(value * 100, 2, false)}%` : fixed(value, 4, false);
}

/* ------------------------------------------------------- which rule applies */

/**
 * app.py:334 `_percent_applies` -- does the registry's percent flag describe
 * *this* column of *this* frame?
 *
 * The `valueColumn` test is the whole function and it is not defensive coding.
 * The registry spans two id namespaces and **ten** of its ids are also
 * `facts_full` concept names -- `Revenue`, `NetIncomeLoss`, `SharesOutstanding`,
 * `StockholdersEquity`, `EPS_TTM_CALC`, `FCF_TTM`, `FFO_TTM`,
 * `OperatingIncomeLoss_TTM`, `CoreOperatingEarnings`, `PPNR`, every one of them
 * a growth-chart metric with `percent: true`. Reading the flag by name alone is
 * what once rendered $109bn of revenue as `10941700000000.00%`.
 *
 * Matching on `id_namespace` would not help: the facts frame's columns *are*
 * XBRL concept names, which is exactly the namespace those entries live in.
 * `value_column` separates them, because a growth entry describes `yoy_growth`
 * and never `value`. Registry ids are globally unique, so the single test is
 * unambiguous.
 */
export function percentApplies(
  byId: ReadonlyMap<string, Metric>,
  concept: string,
  valueColumn: string,
): boolean {
  const metric = byId.get(concept);
  return metric !== undefined && metric.percent && metric.value_column === valueColumn;
}

/**
 * Which treatment a cell gets.
 *
 * The first three are `format_for_display`'s branches. **`raw` is not one of
 * them**: it is the quality-flag section, which the reference formats nowhere
 * near `format_for_display` -- `render_flag_section` (app.py:454) does
 * `shown.astype("Float64").astype("string")`, printing the stored number. That
 * section belongs to item 18, so it keeps item 9's rendering rather than
 * acquiring `0.0000` for a flag that is off.
 */
export type CellFormat = "percent" | "absolute" | "ratio" | "raw";

export const metricsById = (registry: Registry): Map<string, Metric> =>
  new Map(registry.metrics.map((metric) => [metric.id, metric]));

/**
 * app.py:371-378 -- the treatment for one whole **column**, from that column's
 * own maximum.
 *
 * Per column rather than per value, so one column never mixes two treatments:
 * a `Revenue` column reads in billions from top to bottom even in a quarter
 * where the figure happens to be small. The reference computes this on the
 * periods *being shown*, not the whole pivot, so toggling "Show all periods"
 * genuinely can move a column between treatments -- measured on AAPL, where
 * `Goodwill`, `StockIssued` and `StockIssued_TTM` do exactly that. That is
 * reproduced rather than smoothed over, because the alternative is a table
 * whose numbers disagree with the reference's.
 *
 * `pandas` skips nulls in `abs().max()` and an all-null column yields `NaN`,
 * whose comparison against the threshold is false -- so an empty column falls
 * to `ratio`, where every cell is `""` anyway.
 */
export function columnFormat(
  byId: ReadonlyMap<string, Metric>,
  concept: string,
  values: readonly (number | null)[],
  valueColumn = "value",
): CellFormat {
  if (percentApplies(byId, concept, valueColumn)) return "percent";
  let largest = Number.NaN;
  for (const value of values) {
    if (value === null || Number.isNaN(value)) continue;
    const size = Math.abs(value);
    if (Number.isNaN(largest) || size > largest) largest = size;
  }
  return largest >= ABSOLUTE_THRESHOLD ? "absolute" : "ratio";
}

/**
 * app.py:487 -- the snapshot's rule, which is the same three branches decided
 * **per value**. It has to be: the snapshot is one value per concept, so there
 * is no column whose magnitude could be measured.
 */
export function valueFormat(
  byId: ReadonlyMap<string, Metric>,
  concept: string,
  value: number | null,
  valueColumn = "value",
): CellFormat {
  if (percentApplies(byId, concept, valueColumn)) return "percent";
  if (value === null || Number.isNaN(value)) return "ratio";
  return Math.abs(value) >= ABSOLUTE_THRESHOLD ? "absolute" : "ratio";
}

/** One cell as the reference would print it. */
export function formatCell(value: number | null, kind: CellFormat): string {
  if (value === null || Number.isNaN(value)) return "";
  if (kind === "raw") return String(value);
  if (kind === "absolute") return formatAbsolute(value);
  return formatRatio(value, kind === "percent");
}
