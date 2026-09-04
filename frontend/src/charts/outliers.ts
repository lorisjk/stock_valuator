/**
 * `figures.py`'s `outlier_points` (figures.py:201) and the two reports built on
 * it — the masking rule, as pure functions.
 *
 * A rendering concern and nothing else, which the reference states first
 * (figures.py:163): *"The values stay in the data, in the exports and in the data
 * tab; what this controls is whether one panel draws them."* So nothing here
 * touches a frame, a mean, or an export — it answers one question, "which points
 * would a masked panel omit", and two callers ask it: the builder, to decide what
 * to draw, and the view, to name what it is about to hide. **One rule, two
 * callers**, for the reason figures.py:235 gives: *"a silent filter would be the
 * wrong thing in a tool whose argument is auditability, and a filter that
 * disagrees with its own description would be worse."*
 *
 * The three constants are the whole calibration and each is measured, not
 * chosen round — the derivations are in figures.py:171-199 and are not repeated
 * here, only cited, because two copies of a calibration is one too many.
 */

/**
 * figures.py:179. A point is an outlier above 5× its series' own median.
 *
 * Global, not per chart type: one `k` is used by the valuation grid and by the
 * comparison chart alike, and there is no second value anywhere in the
 * reference. Calibrated against fifteen real series — k=4 additionally hides
 * DAL's 47.2, which does not need hiding; k=6 keeps CRM's 337.8, which does.
 */
export const OUTLIER_MEDIAN_RATIO = 5;

/** figures.py:187. Below this many usable points the rule does not apply at all. */
export const OUTLIER_MIN_POINTS = 8;

/**
 * pandas' `Series.median()`: the average of the two middle values at even
 * length, not the lower of them. Spelled out because that difference is exactly
 * one ULP of divergence away from a mask that disagrees with the reference on a
 * point sitting near 5×.
 *
 * The input must already be free of nulls and non-finite values — `outlierMask`
 * filters before calling, as `np.isfinite` does on the other side.
 */
export function median(values: readonly number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = sorted.length >> 1;
  return sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

/**
 * figures.py `outlier_points`: a boolean per input position, true where the
 * value is a **high** outlier.
 *
 * One-directional, and measured rather than assumed (figures.py:190): *"across
 * the fifteen calibration series not one point sits below 0.2x its median, and
 * the lowest ratio anywhere in the set is 0.29x. A two-sided rule would be
 * machinery for a case that does not occur."*
 *
 * **All-false — never all-true**, which the reference's own docstring states and
 * which is a property of the rule rather than a guard in it: at least half of
 * any series lies at or below its median, so at least ⌈n/2⌉ points have a ratio
 * of 1 or less and `k = 5 > 1` cannot reach them. That is why nothing here (and
 * nothing in `drawPanel`) checks for a fully-masked panel — see the report.
 *
 * `values` carries the frame's nulls in place; a null stands for NaN or ±∞ in
 * the parquet, which is precisely what `np.isfinite` drops, so filtering on
 * `!== null` reproduces `usable` exactly.
 */
export function outlierMask(
  values: readonly (number | null)[],
  k: number = OUTLIER_MEDIAN_RATIO,
  minPoints: number = OUTLIER_MIN_POINTS,
): boolean[] {
  const mask = values.map(() => false);
  const usable: number[] = [];
  for (const v of values) if (v !== null && Number.isFinite(v)) usable.push(v);
  if (usable.length < minPoints) return mask;
  const centre = median(usable);
  // `if not (median > 0)` -- a NaN median fails this too, which is the point of
  // writing it in the negative on both sides.
  if (!(centre > 0)) return mask;
  for (let i = 0; i < values.length; i += 1) {
    const v = values[i];
    if (v !== null && Number.isFinite(v) && v / centre > k) mask[i] = true;
  }
  return mask;
}

/** One hidden point, as the expander lists it. */
export interface HiddenPoint {
  end: Date;
  /** The value at full precision. The expander must never show a rounded one. */
  value: number;
  /** `Value / median`, rounded to 1dp — app.py:1011 `.round(1)`. */
  ratio: number;
}

export interface HiddenSeries {
  /** The concept (valuation grid) or the ticker (comparison chart). */
  key: string;
  /** The series' own median, which is what the ratios are against. */
  median: number;
  /** In date order, as `sort_values("end")` leaves them. */
  points: HiddenPoint[];
}

/** app.py:1011 -- the ratio column is rounded to one decimal; the value is not. */
const round1 = (v: number) => Math.round(v * 10) / 10;

/**
 * `outlier_report` / `comparison_outlier_report`: what a masked view would omit,
 * for the caption, the toggle's presence and the expander.
 *
 * One function for both because the two differ only in what they key by — the
 * valuation grid asks per concept, the comparison chart per ticker
 * (app.py:1047: *"the report is keyed by ticker here rather than by concept,
 * because this chart holds one concept and several lines"*). Series with nothing
 * hidden are left out, so an empty result is exactly the reference's falsy
 * `outliers` and is what hides the toggle.
 */
export function outlierReport(
  series: readonly { key: string; x: readonly Date[]; y: readonly (number | null)[] }[],
): HiddenSeries[] {
  const out: HiddenSeries[] = [];
  for (const { key, x, y } of series) {
    const mask = outlierMask(y);
    if (!mask.some(Boolean)) continue;
    const usable = y.filter((v): v is number => v !== null && Number.isFinite(v));
    const centre = median(usable);
    const points: HiddenPoint[] = [];
    for (let i = 0; i < mask.length; i += 1) {
      if (mask[i]) points.push({ end: x[i], value: y[i]!, ratio: round1(y[i]! / centre) });
    }
    points.sort((a, b) => a.end.getTime() - b.end.getTime());
    out.push({ key, median: centre, points });
  }
  return out;
}

/** How many points a report hides in total — the expander's label. */
export const hiddenTotal = (report: readonly HiddenSeries[]) =>
  report.reduce((n, s) => n + s.points.length, 0);
