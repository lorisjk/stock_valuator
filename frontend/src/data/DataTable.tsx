/**
 * One pivot as a table: rows = period, columns = concept.
 *
 * **A plain `<table>`, no virtualisation and no pagination**, and that is a
 * measurement rather than a preference. The brief's estimate for `facts_full`
 * was 610 rows x 50 columns; measured over all 609 tickers the widest pivot any
 * of them produces is **95 x 43 (WAT), and the largest by area is 84 x 40 =
 * 3,360 cells (BBY)** -- the median is 72 x 34. The default view shows 16
 * periods, so the common case is ~600 cells and the worst case with "Show all
 * periods" on is 3,360. Virtualisation earns its complexity somewhere above
 * 10,000 DOM nodes; this is an order of magnitude below that, and the report
 * carries the timing to say so rather than the estimate.
 *
 * **A cell's text comes from `format.ts` and its value never does.** The table
 * is handed a `CellFormat` per column and calls `formatCell(value, kind)`; it
 * has no way to write a formatted string back anywhere, which is what keeps the
 * CSV path on the numbers. See the note on `formats` below.
 */
import type { CellFormat } from "./format.ts";
import { formatCell } from "./format.ts";
import type { Pivot } from "./pivot.ts";

export default function DataTable({
  pivot,
  formats,
  caption,
}: {
  pivot: Pivot;
  /**
   * One treatment per column of `pivot`, in the same order.
   *
   * Passed in rather than derived here, because the reference decides it from
   * the column's own maximum **over the rows being shown** (app.py:373) and the
   * caller is what knows which rows those are. Deriving it inside the table
   * would silently use whichever slice happened to be rendered.
   */
  formats: readonly CellFormat[];
  caption: string;
}) {
  return (
    <div className="table-scroll">
      <table className="data-table">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            <th scope="col" className="data-table__corner">
              end
            </th>
            {pivot.concepts.map((concept) => (
              <th scope="col" key={concept}>
                {concept}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {pivot.ends.map((end, row) => (
            <tr key={end}>
              <th scope="row" className="data-table__corner">
                {end}
              </th>
              {pivot.concepts.map((concept, column) => {
                const sign = pivot.nonfinite.get(`${row},${column}`);
                if (sign) {
                  // The export writes null here because JSON has no infinity,
                  // but the pipeline had a value -- a division by zero, 44 of
                  // them across the whole export. Drawing this as a gap would
                  // report "no data" for a place where the data is the problem.
                  return (
                    <td key={concept} className="cell cell--inf" title={`${sign} in the pipeline`}>
                      {sign === "Infinity" ? "∞" : "−∞"}
                    </td>
                  );
                }
                const value = pivot.cells[row][column];
                return value === null ? (
                  <td key={concept} className="cell cell--null" title="no value">
                    —
                  </td>
                ) : (
                  <td key={concept} className="cell">
                    {formatCell(value, formats[column])}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** The snapshot's concept/value list, which is a pivot only in spirit. */
export function PairTable({
  rows,
  caption,
}: {
  /**
   * The snapshot decides its treatment **per value** (app.py:487), because one
   * value per concept leaves no column to measure -- so the row carries its own.
   */
  rows: { concept: string; value: number | null; format: CellFormat }[];
  caption: string;
}) {
  return (
    <div className="table-scroll">
      <table className="data-table data-table--pairs">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            <th scope="col" className="data-table__corner">
              concept
            </th>
            <th scope="col">value</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ concept, value, format }) => (
            <tr key={concept}>
              <th scope="row" className="data-table__corner">
                {concept}
              </th>
              {value === null ? (
                <td className="cell cell--null" title="no value">
                  —
                </td>
              ) : (
                <td className="cell">{formatCell(value, format)}</td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
