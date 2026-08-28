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
 * The as-of checkbox that sits below the ticker in `app.py` is item 15 and is
 * deliberately absent, not forgotten.
 */
import type { Meta } from "../contracts.ts";
import type { UniverseEntry } from "../data/DataContext.ts";
import { VIEWS, VIEW_LABELS, isTickerView, type ViewId } from "./navigation.ts";
import Freshness from "./Freshness.tsx";


export default function Sidebar({
  meta,
  view,
  onView,
  ticker,
  profile,
  universe,
  onTicker,
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
