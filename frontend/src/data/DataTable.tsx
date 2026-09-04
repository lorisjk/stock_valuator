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
import type { FlagSummaryRow } from "./flags.ts";
import type { CellFormat } from "./format.ts";
import { formatCell } from "./format.ts";
import type { Pivot } from "./pivot.ts";

export default function DataTable({
  pivot,
  formats,
  caption,
  markers,
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
  /**
   * concept -> cadence marker, appended to the header with a space exactly as
   * `render_data_section` does (app.py:421 `f"{concept} {marker}"`).
   *
   * On the **header** and nowhere else, which is what keeps the export clean:
   * the marker never enters the `Pivot`, so `pivotToCsv` cannot see it and the
   * download keeps the filed concept name. The reference relies on the same
   * separation -- it renames the *display* frame, not `shown`.
   */
  markers?: ReadonlyMap<string, string>;
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
            {pivot.concepts.map((concept) => {
              const marker = markers?.get(concept);
              return (
                <th scope="col" key={concept}>
                  {marker === undefined ? concept : `${concept} ${marker}`}
                </th>
              );
            })}
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

export function PairTable({
  rows,
  caption,
}: {
  rows: { concept: string; value: number | null; format: CellFormat }[];
  caption: string;
}) {
  return (
    <div className="table-scroll">
      <table className="data-table data-table--pairs-transposed">
        <caption className="sr-only">{caption}</caption>
        <tbody>
          <tr>
            <th scope="row" className="data-table__corner">
              concept
            </th>
            {rows.map(({ concept }) => (
              <th scope="col" key={concept}>
                {concept}
              </th>
            ))}
          </tr>
          <tr>
            <th scope="row" className="data-table__corner">
              value
            </th>
            {rows.map(({ concept, value, format }) =>
              value === null ? (
                <td key={concept} className="cell cell--null" title="no value">
                  —
                </td>
              ) : (
                <td key={concept} className="cell">
                  {formatCell(value, format)}
                </td>
              )
            )}
          </tr>
        </tbody>
      </table>
    </div>
  );
}

/**
 * The quality-flag summary: one row per flag, `raised` / `periods evaluated` /
 * `most recent` (app.py:445-453).
 *
 * A third table shape rather than a `Pivot` with three columns, because it is
 * not one -- its cells are two counts and a date, none of which is a measured
 * quantity and none of which goes anywhere near `format.ts`. Handing it to
 * `DataTable` would mean inventing a `CellFormat` that prints a date, which is
 * how a formatting layer starts growing cases that have nothing to do with the
 * rule it exists to apply.
 *
 * The column headings are the reference's own dictionary keys, verbatim,
 * including the lowercase and the two-word `periods evaluated`: `st.dataframe`
 * renders them as-is and they are what the reader is comparing against.
 */
export function FlagSummaryTable({
  rows,
  caption,
}: {
  rows: readonly FlagSummaryRow[];
  caption: string;
}) {
  return (
    <div className="table-scroll">
      <table className="data-table data-table--flags">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            <th scope="col" className="data-table__corner">
              flag
            </th>
            <th scope="col">raised</th>
            <th scope="col">periods evaluated</th>
            <th scope="col">most recent</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ flag, raised, evaluated, mostRecent }) => (
            <tr key={flag}>
              <th scope="row" className="data-table__corner">
                {flag}
              </th>
              <td className="cell">{raised}</td>
              <td className="cell">{evaluated}</td>
              {/* app.py:452 -- an em dash for "never". The tables use the same
                  character for a missing cell, but it means something else
                  here (evaluated every period and raised in none of them,
                  which is good news), so it is not a `cell--null`. */}
              <td className="cell">{mostRecent ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
