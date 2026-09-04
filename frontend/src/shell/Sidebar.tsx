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
import {useState, useEffect, useRef} from "react";

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
  asOf: Date | null;
  onAsOf: (next: Date | null) => void;
  open: boolean;
  onClose: () => void;
}) {

  const [search, setSearch] = useState("");
  const [comboOpen, setComboOpen] = useState(false);
  const [highlighted, setHighlighted] = useState(0);
  const [typed, setTyped] = useState<string | null>(null); // null = noch nichts getippt seit dem Öffnen
  const comboRef = useRef<HTMLDivElement>(null);
  
  // Klick außerhalb erkennen
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (comboRef.current && !comboRef.current.contains(event.target as Node)) {
        setComboOpen(false); // ComboBox schließen
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);


  useEffect(() => {
    const current = universe.find((u) => u.ticker === ticker);
    if (current) setSearch(`${current.ticker} — ${current.profile}`);
  }, [ticker, universe]);

  const filteredUniverse = universe.filter((entry) =>
    `${entry.ticker} ${entry.profile}`
      .toLowerCase()
      .includes((typed ?? "").toLowerCase())
  );



  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
  if (!comboOpen) return;

  if (e.key === "ArrowDown") {
    e.preventDefault();
    setHighlighted((i) => Math.min(i + 1, filteredUniverse.length - 1));
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    setHighlighted((i) => Math.max(i - 1, 0));
  } else if (e.key === "Enter") {
    e.preventDefault();
    const entry = filteredUniverse[highlighted];
    if (entry) {
      onTicker(entry.ticker);
      setSearch(`${entry.ticker} — ${entry.profile}`);
      setComboOpen(false);
    }
  } else if (e.key === "Escape") {
    setComboOpen(false);
  }
};

  return (
    <aside className={`sidebar${open ? "" : " sidebar--closed"}`} aria-label="Navigation">
      <div className="sidebar__inner">
        <button type="button" className="sidebar__close" onClick={onClose} aria-label="Hide sidebar">
          x
        </button>

        {isTickerView(view) ? (
          <>
            <h2>Ticker</h2>
            <label className="sr-only" htmlFor="ticker-select">
              Ticker
            </label>
              <div ref={comboRef} className="ticker-combobox">
                <label className="sr-only" htmlFor="ticker-select">
                  Ticker
                </label>
                <input
                  id="ticker-select"
                  type="text"
                  value={search}
                  placeholder="Search ticker..."
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setComboOpen(true);
                    setTyped(e.target.value);
                    setHighlighted(0);
                  }}
                  onFocus={(e) => {
                    setComboOpen(true);
                    setTyped(null);       // beim Fokussieren: noch nichts getippt, volle Liste
                    e.target.select();    // optional: markiert den Text, sofortiges Überschreiben möglich
                  }}
                  onKeyDown={handleKeyDown}
                  className="ticker"
                />
                {comboOpen && (
                  <div className="ticker-results">
                    {filteredUniverse.map((entry) => (
                      <div
                        key={entry.ticker}
                        className="ticker-option"
                        onMouseDown={() => {
                          onTicker(entry.ticker);
                          setSearch(`${entry.ticker} — ${entry.profile}`);
                          setComboOpen(false);
                          setTyped(null);
                        }}
                  >
                        {entry.ticker} — {entry.profile}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            <p className="caption">
              Profile: <code>{profile}</code> — see <strong>{VIEW_LABELS.coverage}</strong> for what
              this profile shows and hides.
            </p>

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
                  <input
                    type="date"
                    value={isoDay(asOf)}
                    onChange={(e) => onAsOf(e.target.value ? parseDay(e.target.value) : null)}
                  />
                </label>
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

        <Freshness meta={meta} />

      </div>
    </aside>
  );
}