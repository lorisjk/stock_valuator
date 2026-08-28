/**
 * The sidebar: freshness, the view radio, and — in Analysis only — the ticker.
 *
 * Order and content follow `app.py:852-874` exactly:
 *
 *   1. `render_freshness(meta)` first, "so it survives every tab and page
 *      switch" (app.py:620).
 *   2. a divider, then the four-way view radio (app.py:856).
 *   3. a divider, then **only in the Analysis view** the ticker selector and its
 *      profile caption. On the other three the reference prints a caption
 *      saying why there is nothing to select (app.py:872-877), and that
 *      sentence is carried over: a visible ticker next to the encyclopedia
 *      would imply the encyclopedia describes that company.
 *
 *   4. the **as-of control** (app.py:867), below the ticker and inside the same
 *      Analysis-only branch. It is here rather than on a tab because that is
 *      where the reference puts it, and the placement is the design: one date
 *      feeds *two* tabs (`render_analysis(ticker, as_of, ...)` at app.py:887
 *      hands it to the valuation grid and the comparison chart alike), so a
 *      per-tab control would have had to be two controls that must agree.
 */
import type { Meta } from "../contracts.ts";
import type { UniverseEntry } from "../data/DataContext.ts";
import { VIEWS, VIEW_LABELS, isTickerView, type ViewId } from "./navigation.ts";
import Freshness from "./Freshness.tsx";

/**
 * `pd.Timestamp.today().date()` -- app.py:869's default when the box is first
 * ticked. Midnight UTC, because every `end` in the export is parsed that way and
 * the upper bound compares the two directly.
 */
function todayUtc(): Date {
  const now = new Date();
  return new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()));
}

/** `<input type="date">` speaks `YYYY-MM-DD`, and reads it back the same way. */
const isoDay = (date: Date) =>
  `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}-${String(date.getUTCDate()).padStart(2, "0")}`;

const parseDay = (value: string) => new Date(`${value}T00:00:00.000Z`);


export default function Sidebar({
  meta,
  view,
  onView,
  ticker,
  profile,
  universe,
  onTicker,
  asOf,
  onAsOf,
  open,
  onClose,
}: {
  meta: Meta | null;
  view: ViewId;
  onView: (view: ViewId) => void;
  ticker: string;
  profile: string;
  universe: UniverseEntry[];
  onTicker: (ticker: string) => void;
  /** The as-of date, or null for "no as-of" -- app.py's `as_of = None`. */
  asOf: Date | null;
  onAsOf: (next: Date | null) => void;
  open: boolean;
  onClose: () => void;
}) {
  return (
    <aside className={`sidebar${open ? "" : " sidebar--closed"}`} aria-label="Navigation">
      <div className="sidebar__inner">
        <button type="button" className="sidebar__close" onClick={onClose} aria-label="Hide sidebar">
          x
        </button>

        <Freshness meta={meta} />

        <hr />

        <fieldset className="radio">
          <legend>View</legend>
          {VIEWS.map((id) => (
            <label key={id}>
              <input
                type="radio"
                name="view"
                value={id}
                checked={view === id}
                onChange={() => onView(id)}
              />{" "}
              {VIEW_LABELS[id]}
            </label>
          ))}
        </fieldset>

        <hr />

        {isTickerView(view) ? (
          <>
            <h2>Ticker</h2>
            <label className="sr-only" htmlFor="ticker-select">
              Ticker
            </label>
            {/* 609 options in one native select. That is what the reference
                does, and whether it is usable at that length is a DOM question
                this build cannot answer -- see the report. */}
            <select
              id="ticker-select"
              value={ticker}
              onChange={(e) => onTicker(e.target.value)}
              className="ticker"
            >
              {universe.map((entry) => (
                <option key={entry.ticker} value={entry.ticker}>
                  {entry.ticker} — {entry.profile}
                </option>
              ))}
            </select>
            <p className="caption">
              Profile: <code>{profile}</code> — see <strong>{VIEW_LABELS.coverage}</strong> for what
              this profile shows and hides.
            </p>

            {/* app.py:867-870. The label says "for valuation" and the reference
                nevertheless threads the date into the comparison chart too --
                carried verbatim rather than corrected, because the label is what
                a reader of the two apps compares. See the report. */}
            <label className="as-of__toggle">
              <input
                type="checkbox"
                checked={asOf !== null}
                onChange={(e) => onAsOf(e.target.checked ? todayUtc() : null)}
              />{" "}
              Use an as-of date for valuation
            </label>

            {asOf !== null && (
              <>
                <label className="as-of__date">
                  <span>As of</span>
                  {/* No `min`/`max`: `st.date_input` at app.py:869 has none
                      either, and a date outside the data is not an error -- it
                      lands on the panels' own "No Data" path, which already
                      says what happened. A picker that refuses the date would
                      have to explain itself; the chart already does. */}
                  <input
                    type="date"
                    value={isoDay(asOf)}
                    onChange={(e) => onAsOf(e.target.value ? parseDay(e.target.value) : null)}
                  />
                </label>
                {/* app.py:870, verbatim. */}
                <p className="caption">
                  The valuation window runs backwards from this date and stops there.
                </p>
              </>
            )}
          </>
        ) : (
          <p className="caption">
            Reference pages describe the pipeline itself and do not depend on the selected ticker.
          </p>
        )}
      </div>
    </aside>
  );
}
