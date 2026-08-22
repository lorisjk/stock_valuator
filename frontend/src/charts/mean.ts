/**
 * The mean line, and the invariant that defines it.
 *
 * The mean is computed over the **full selected series**, never over the points
 * a panel happens to draw. Today those are the same set; they stop being the
 * same set the moment outlier masking (item 14) or a snapshot marker (item 13)
 * arrives, and recomputing on the drawn points would then compare today's
 * multiple against a benchmark with the bad years taken out -- a different and
 * flattering quantity, and an invisible one, because the number still looks
 * reasonable.
 *
 * That is why `meanOver` takes its own array and the panel builder passes it
 * `series.mean`, not `series.drawn`: the two are separate fields so a later
 * change to what is drawn cannot silently reach the mean.
 */

/**
 * metrics.harmonic_mean, exactly: keep values > 0 (which drops NaN and null,
 * since neither compares greater than zero), then n / sum(1/x). NaN when
 * nothing survives.
 */
export function harmonicMean(values: readonly (number | null)[]): number {
  let count = 0;
  let inverseSum = 0;
  for (const v of values) {
    if (v === null || !Number.isFinite(v) || v <= 0) continue;
    count += 1;
    inverseSum += 1 / v;
  }
  if (count === 0) return NaN;
  return count / inverseSum;
}

/**
 * pandas Series.mean(): skips nulls, averages the rest, NaN when all are null.
 *
 * Non-finite values are not skipped here, deliberately -- pandas does not skip
 * them either, and an inf in the series makes the mean inf, which the caller
 * then rejects with the same isFinite gate the Python builder uses. Reproducing
 * that matters more than producing a "nicer" number.
 */
export function arithmeticMean(values: readonly (number | null)[]): number {
  let count = 0;
  let total = 0;
  for (const v of values) {
    if (v === null || Number.isNaN(v)) continue;
    count += 1;
    total += v;
  }
  if (count === 0) return NaN;
  return total / count;
}

/**
 * The label: `Ø 7.8` or `Ø (harm.) 29.0`, and `.2%` instead of `.1f` when the
 * metric is a percentage -- Python's f"{v:.2%}" multiplies by 100 and appends
 * the sign.
 */
export function meanLabel(value: number, harmonic: boolean, percent: boolean): string {
  const prefix = harmonic ? "Ø (harm.)" : "Ø";
  const text = percent ? `${(value * 100).toFixed(2)}%` : value.toFixed(1);
  return `${prefix} ${text}`;
}

export interface MeanLine {
  value: number;
  label: string;
}

/**
 * The mean line for one panel, or null when there is none to draw.
 *
 * `np.isfinite` gates it on the Python side: an all-null series gives NaN, and a
 * series containing an infinity gives Infinity. Both mean "no line", not "a line
 * at zero".
 */
export function meanOver(
  values: readonly (number | null)[],
  harmonic: boolean,
  percent: boolean,
): MeanLine | null {
  const value = harmonic ? harmonicMean(values) : arithmeticMean(values);
  if (!Number.isFinite(value)) return null;
  return { value, label: meanLabel(value, harmonic, percent) };
}
