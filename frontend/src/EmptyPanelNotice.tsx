/**
 * `app.py:963-983`'s empty-panel notice — **valuation only**, and deliberately
 * so.
 *
 * The last cycle left this open: is the reference's notice valuation-only by
 * design or by omission, given the raw-facts chart produces "No Data" panels
 * just as routinely? **By design**, and the reasoning is stated twice.
 *
 * Once in the comment above the call site (app.py:959): *"An empty panel still
 * renders as an axis grid ... Without this the reader sees a chart frame with no
 * line and no reason for it, **next to a working current multiple at the top of
 * the page**."* And once in the message itself, whose middle sentence — *"The
 * current multiple above still works because it is computed from market data"* —
 * is a claim about the snapshot marker and the current-multiple table, neither
 * of which exists on the fundamentals, growth or raw-facts charts.
 *
 * So the notice is not "a grid has empty panels"; it is "**this** panel is empty
 * while the number above it is not, and that is not a contradiction." Only the
 * valuation tab can say that, and it is why this port does not extend it. See
 * the report.
 *
 * **Deliberately neutral about the cause**, with one exception. The comment at
 * app.py:970 gives the measurement behind that: 170 of the 500 exported tickers
 * have at least one empty panel and 97 of those are `dividend_yield` on a
 * company that pays no dividend — *"a true statement about the business, not a
 * defect."* The one cause the app will name is the one it can establish from its
 * own data, and `share_history_absent`'s docstring is emphatic that it is the
 * strict case: zero SharesOutstanding values, never merely thin.
 */

export default function EmptyPanelNotice({
  /** The empty panels' labels, in panel order. Empty renders nothing. */
  names,
  /** `null` = not known yet; the clause is appended when it resolves to true. */
  shareHistoryMissing,
}: {
  names: readonly string[];
  shareHistoryMissing: boolean | null;
}) {
  if (names.length === 0) return null;

  return (
    <p className="notice-inline" role="status">
      <strong>No data for: {names.join(", ")}</strong> — nothing to draw in this window.
      {shareHistoryMissing === true && (
        <>
          {" "}
          No share-count history is available for this ticker in the SEC&apos;s structured data, and
          every per-share multiple needs one as its denominator.
        </>
      )}{" "}
      The current multiple above still works because it is computed from market data, which has no
      filed-history equivalent. <strong>Nothing was hidden or filtered</strong> — the value is absent
      from the source data, and the empty column is still listed in the <strong>Data</strong> tab.
    </p>
  );
}
