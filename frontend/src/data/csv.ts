/**
 * `app.py:385 to_csv_text` -- a pivot as CSV at full precision, plus the two
 * things that consume it: the file download and the copy block.
 *
 * The rule this whole file exists to observe, because getting it wrong is the
 * failure mode inventory §3.4 names by hand: **the CSV is produced from the
 * numbers, never from what the table displays.** Item 10 put a formatting layer
 * between the pivot and the render, and it deliberately cannot be reached from
 * here -- `format.ts` neither imports `Pivot` nor accepts one, and nothing in
 * this file imports `format.ts`. The separation is structural rather than a
 * convention someone has to remember.
 */
import type { Pivot } from "./pivot.ts";

/**
 * app.py:48 `DEFAULT_COPY_PERIODS`. The download gets the periods on screen;
 * the copy block gets eight, always.
 *
 * app.py:44-48 records why the two differ: *"the copy block is deliberately
 * smaller, because a full facts table pasted into a chat is already near the
 * practical limit and the recent periods are what a question is usually
 * about."* Measured on this export, eight periods of the widest facts table is
 * about 3.9 kB; the same table at 95 periods is 44 kB.
 */
export const DEFAULT_COPY_PERIODS = 8;

/**
 * One value as CSV text: Python's `repr` of a float, exactly.
 *
 * pandas writes a float column with `repr`, so this is what byte-identity with
 * the reference's download requires. Three things have to be right and none of
 * them is `String(value)`:
 *
 * 1. **The digits.** `repr` is the shortest string that round-trips back to the
 *    same double; `toExponential()` with no argument gives exactly those digits.
 * 2. **The notation.** Python switches to exponential when the decimal point
 *    position `decpt` satisfies `decpt <= -4 || decpt > 16`; JavaScript switches
 *    at `1e-7` and `1e21`. Between them lie 109 of the export's 1,888,605 finite
 *    values -- `1.4383458646616541e-05` against `0.000014383458646616541` -- the
 *    same double written two ways, which item 9 measured and left, and which
 *    this item owns. Verified against the reference at the boundaries: `1e-4` is
 *    `0.0001`, `1e-5` is `1e-05`, `1e15` is `1000000000000000.0`, `1e16` is
 *    `1e+16`.
 * 3. **The trailing `.0` and the sign of `-0`.** `repr(0.0)` is `"0.0"` and
 *    `repr(-0.0)` is `"-0.0"`; `String(0)` and `String(-0)` are both `"0"`.
 *    Exactly one value in the export is a negative zero (`MAS`'s
 *    `operating_leverage` at 2025-06-30) and it is only a sign on a zero, but a
 *    reference implementation that is right except where nobody looks is not a
 *    reference implementation.
 *
 * The exponential form carries a signed exponent of at least two digits and no
 * forced `.0` on a single-digit mantissa -- `1e-05`, not `1.0e-05`.
 */
export function csvNumber(value: number): string {
  // The parquet holds +-inf where the JSON export had to write null; pandas
  // writes them like this, and `pivotToCsv` restores them from the sidecar.
  if (!Number.isFinite(value)) return Number.isNaN(value) ? "nan" : value > 0 ? "inf" : "-inf";

  const negative = value < 0 || Object.is(value, -0);
  const sign = negative ? "-" : "";
  const exponential = Math.abs(value).toExponential();
  const at = exponential.indexOf("e");
  const digits = exponential.slice(0, at).replace(".", "");
  const exponent = Number(exponential.slice(at + 1));
  // `decpt` is Python's own name for it: value = 0.<digits> x 10^decpt.
  const decpt = exponent + 1;

  if (decpt <= -4 || decpt > 16) {
    const mantissa = digits.length > 1 ? `${digits[0]}.${digits.slice(1)}` : digits;
    const exponentSign = exponent < 0 ? "-" : "+";
    return `${sign}${mantissa}e${exponentSign}${String(Math.abs(exponent)).padStart(2, "0")}`;
  }
  if (decpt <= 0) return `${sign}0.${"0".repeat(-decpt)}${digits}`;
  if (decpt >= digits.length) return `${sign}${digits}${"0".repeat(decpt - digits.length)}.0`;
  return `${sign}${digits.slice(0, decpt)}.${digits.slice(decpt)}`;
}

/**
 * A pivot as CSV: `end` plus one column per concept, newest period first.
 *
 * A null cell is an empty field, which is what pandas writes and what keeps a
 * gap distinguishable from a zero on the way out as well as on screen.
 * A cell that was +-inf carries `inf`/`-inf`, the value the parquet still holds
 * and the one Streamlit's own download therefore carries.
 */
export function pivotToCsv(pivot: Pivot): string {
  const lines = [["end", ...pivot.concepts].join(",")];
  pivot.ends.forEach((end, row) => {
    const fields = pivot.concepts.map((_, column) => {
      const sign = pivot.nonfinite.get(`${row},${column}`);
      if (sign) return sign === "Infinity" ? "inf" : "-inf";
      const value = pivot.cells[row][column];
      return value === null ? "" : csvNumber(value);
    });
    lines.push([end, ...fields].join(","));
  });
  return `${lines.join("\n")}\n`;
}

/** `concept,value` for the snapshot, whose shape is a list rather than a grid. */
export function pairsToCsv(rows: { concept: string; value: number | null }[]): string {
  const lines = ["concept,value"];
  for (const { concept, value } of rows) {
    lines.push(`${concept},${value === null ? "" : csvNumber(value)}`);
  }
  return `${lines.join("\n")}\n`;
}

/**
 * Hand the browser a file. Nothing here is retained: the object URL is revoked
 * on the next frame, because a data tab that is opened repeatedly would
 * otherwise pin every CSV it has ever produced in memory for the session.
 */
export function downloadCsv(name: string, text: string): void {
  const url = URL.createObjectURL(new Blob([text], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  requestAnimationFrame(() => URL.revokeObjectURL(url));
}

/**
 * Put text on the clipboard, reporting whether it actually got there.
 *
 * `navigator.clipboard` is **undefined outside a secure context**, and this app
 * is routinely served over plain http from a LAN address during development --
 * so the missing-API case is the normal case there, not an exotic one. It
 * resolves `false` rather than throwing, and the caller says "select and copy"
 * instead of claiming a success that did not happen. The disclosure holding the
 * same text is what makes that a real fallback rather than a dead end.
 */
export async function copyText(text: string): Promise<boolean> {
  try {
    if (!navigator.clipboard?.writeText) return false;
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
