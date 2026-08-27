/**
 * `app.py:385 to_csv_text` -- a pivot as CSV at full precision.
 *
 * **This is item 11's territory and this file is deliberately the smallest
 * thing that works.** It exists because the table already holds the numeric
 * pivot, so producing the download is three lines rather than a feature; the
 * copy-block expander, the character counts and the per-section file naming
 * conventions the inventory lists under §2.5 are not here. See the report's
 * hand-off section.
 *
 * The one rule it does observe, because getting it wrong is the failure mode
 * §3.4 names: **the CSV is produced from the numbers, never from what the table
 * displays.** There is no formatting step between the pivot and this function.
 */
import type { Pivot } from "./pivot.ts";

/**
 * One value as CSV text, matching Python's `repr` for a float where the two
 * notations agree.
 *
 * The `.0` on an integral value is not cosmetic: pandas writes `0.0` for a
 * quality flag and JavaScript's `String(0)` writes `0`, and that one character
 * is the difference between a byte-comparable reference check and a
 * value-by-value one.
 *
 * Where they still disagree is notation only, on 109 of the export's 1,888,605
 * finite values: Python switches to exponent form below `1e-4` and JavaScript
 * below `1e-7`, so `1.4383458646616541e-05` is written `0.000014383458646616541`
 * here. Both parse back to the same double -- no precision is lost -- and
 * chasing the notation belongs to item 11, not to this byproduct.
 */
function csvNumber(value: number): string {
  // `String(-0)` is `"0"`, so a negative zero would silently lose its sign
  // where `repr(-0.0)` keeps it. Exactly one value in the whole export is one
  // (`MAS`'s `operating_leverage` at 2025-06-30), and it is only a sign on a
  // zero -- but it is also the only place this function is not the reference,
  // and it was found by a check rather than guessed at.
  const sign = Object.is(value, -0) ? "-" : "";
  return Number.isInteger(value) ? `${sign}${value}.0` : String(value);
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
