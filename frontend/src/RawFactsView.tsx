/**
 * The Raw Facts tab: `app.py`'s `tab_raw` block (app.py:1106).
 *
 * Its own view rather than a fourth `ChartView` chart, and the reason is in the
 * data: `ChartView` is built around a `ChartId`, a registry catalogue and
 * `profile_visibility`, and this chart has none of the three. Its concepts
 * come from the ticker's own facts, its ids are XBRL tags with no `Metric`
 * behind them to supply a label or a reference line, and its narrowing
 * already happened upstream in the export (see `raw.ts`).
 *
 * The selection is stored raw and resolved at render. Switching ticker keeps
 * the overlap and restores the rest on the way back, and toggling
 * "include derived" does not silently drop a pick it will offer again.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import Plot from "react-plotly.js";

import {
  useConceptCandidates,
  useTickerFacts,
} from "./data/DataContext.ts";

import { YEARS_MAX, YEARS_MIN } from "./charts/defaults.ts";

import {
  RAW_DEFAULT_CONCEPTS,
  RAW_YEARS,
  buildRawFacts,
} from "./charts/raw.ts";

import "./raw-facts.css";

/** app.py:1115 -- the four openers, kept only where the ticker offers them. */
const defaultsFor = (offerable: readonly string[]) =>
  RAW_DEFAULT_CONCEPTS.filter((c) => offerable.includes(c)) as string[];

export default function RawFactsView({ ticker }: { ticker: string }) {
  /*
   * --------------------------------------------------------------------------
   * DATA
   * --------------------------------------------------------------------------
   */

  const { facts, error } = useTickerFacts(ticker);
  const {
    candidates,
    error: candidatesError,
  } = useConceptCandidates(ticker);

  /*
   * --------------------------------------------------------------------------
   * STATE
   * --------------------------------------------------------------------------
   */

  // undefined = not touched yet -> use defaults
  // [] = explicitly cleared
  const [picked, setPicked] = useState<readonly string[] | undefined>(
    undefined,
  );

  const [includeDerived, setIncludeDerived] = useState(false);

  const [years, setYears] = useState(RAW_YEARS);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Combobox state
  const [comboOpen, setComboOpen] = useState(false);
  const [conceptSearch, setConceptSearch] = useState("");

  /*
   * --------------------------------------------------------------------------
   * REF
   * --------------------------------------------------------------------------
   */

  const comboRef = useRef<HTMLDivElement>(null);

  /*
   * --------------------------------------------------------------------------
   * DERIVED DATA
   * --------------------------------------------------------------------------
   */

  const offerable = useMemo(
    () =>
      buildRawFacts(
        facts,
        candidates,
        ticker,
        { includeDerived },
      ).offerable,
    [facts, candidates, ticker, includeDerived],
  );

  const selected = useMemo(() => {
    if (picked === undefined) {
      return defaultsFor(offerable);
    }

    const keep = new Set(picked);

    return offerable.filter((c) => keep.has(c));
  }, [picked, offerable]);

  const result = useMemo(
    () =>
      buildRawFacts(
        facts,
        candidates,
        ticker,
        {
          requested: selected,
          years,
          includeDerived,
        },
      ),
    [facts, candidates, ticker, selected, years, includeDerived],
  );

  /*
   * Filter concepts according to the search input.
   *
   * Empty search -> show all concepts.
   * Otherwise -> only concepts containing the search string.
   */
  const filteredOfferable = useMemo(() => {
    const query = conceptSearch.trim().toLowerCase();

    if (!query) {
      return offerable;
    }

    return offerable.filter((concept) =>
      concept.toLowerCase().includes(query),
    );
  }, [offerable, conceptSearch]);

  /*
   * --------------------------------------------------------------------------
   * EFFECTS
   * --------------------------------------------------------------------------
   */

  /*
   * Close the combobox when clicking anywhere outside it.
   */
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        comboRef.current &&
        event.target instanceof Node &&
        !comboRef.current.contains(event.target)
      ) {
        setComboOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  useEffect(() => {
  const handleFullscreenChange = () => {
    setIsFullscreen(document.fullscreenElement !== null);

    // Plotly nach dem Wechsel auf die neue Größe bringen
    setTimeout(() => {
      window.dispatchEvent(new Event("resize"));
    }, 100);
  };

  document.addEventListener("fullscreenchange", handleFullscreenChange);

  return () => {
    document.removeEventListener(
      "fullscreenchange",
      handleFullscreenChange,
    );
  };
}, []);

  /*
   * --------------------------------------------------------------------------
   * ERROR / LOADING STATES
   * --------------------------------------------------------------------------
   */

  if (error) {
    return (
      <p className="notice-inline">
        Could not load {ticker}: {error.message}
      </p>
    );
  }

  if (candidatesError) {
    return (
      <p className="notice-inline">
        Could not load the concept list: {candidatesError.message}
      </p>
    );
  }

  if (!facts || !candidates) {
    return (
      <p className="caption">
        Loading {ticker}…
      </p>
    );
  }

  /*
   * --------------------------------------------------------------------------
   * SELECTION HELPERS
   * --------------------------------------------------------------------------
   */

  const setTo = (ids: Set<string>) => {
    setPicked(
      offerable.filter((concept) => ids.has(concept)),
    );
  };

  const toggle = (concept: string) => {
    const next = new Set(selected);

    if (next.has(concept)) {
      next.delete(concept);
    } else {
      next.add(concept);
    }

    setTo(next);
  };

  const atDefault =
    JSON.stringify(selected) ===
    JSON.stringify(defaultsFor(offerable));

  /*
   * --------------------------------------------------------------------------
   * RENDER
   * --------------------------------------------------------------------------
   */

  return (
    <section className="raw-facts">

      {/* app.py:1107 */}
      <p>
        Concepts as filed, before any metric is computed.
      </p>

      {/* app.py:1110-1112 */}
      <label className="raw-facts__derived">
        <input
          type="checkbox"
          checked={includeDerived}
          onChange={(e) =>
            setIncludeDerived(e.target.checked)
          }
        />{" "}
        Include derived concepts (_TTM, _QUARTERLY, …)
      </label>

      {/* ------------------------------------------------------------------ */}
      {/* CONCEPT PICKER                                                     */}
      {/* ------------------------------------------------------------------ */}

      <fieldset className="raw-facts__picker">

        <legend>
          Concepts — {selected.length} of {offerable.length} filed for this ticker{" "}

          <button
            type="button"
            onClick={() => setTo(new Set(offerable))}
            disabled={selected.length === offerable.length}
          >
            All
          </button>{" "}

          <button
            type="button"
            onClick={() => setPicked([])}
            disabled={selected.length === 0}
          >
            None
          </button>{" "}

          <button
            type="button"
            onClick={() =>
              setPicked(defaultsFor(offerable))
            }
            disabled={atDefault}
          >
            Default
          </button>
        </legend>

        {/* -------------------------------------------------------------- */}
        {/* COMBOBOX                                                        */}
        {/* -------------------------------------------------------------- */}

        <div
          ref={comboRef}
          className="raw-facts__combobox"
        >

          {/* Combobox button */}
          <button
            type="button"
            className="raw-facts__combobox-trigger"
            onClick={() => {
              setComboOpen((open) => !open);

              // Clear search when opening the menu
              if (!comboOpen) {
                setConceptSearch("");
              }
            }}
            aria-expanded={comboOpen}
            aria-haspopup="listbox"
          >
            <span>
              {selected.length === 0
                ? "Select concepts..."
                : `${selected.length} concept${
                    selected.length === 1 ? "" : "s"
                  } selected`}
            </span>

            <span className="raw-facts__combobox-arrow">
              {comboOpen ? "▲" : "▼"}
            </span>
          </button>

          {/* Dropdown */}
          {comboOpen && (
            <div className="raw-facts__combobox-menu">

              {/* Search */}
              <div className="raw-facts__search">
                <input
                  type="text"
                  value={conceptSearch}
                  onChange={(e) =>
                    setConceptSearch(e.target.value)
                  }
                  placeholder="Search concepts..."
                  autoFocus
                />
              </div>

              {/* Concept list */}
              <div className="raw-facts__options">

                {filteredOfferable.length === 0 ? (
                  <div className="raw-facts__empty">
                    No concepts found.
                  </div>
                ) : (
                  filteredOfferable.map((concept) => (
                    <label
                      key={concept}
                      className="raw-facts__option"
                    >
                      <input
                        type="checkbox"
                        checked={selected.includes(concept)}
                        onChange={() => toggle(concept)}
                      />

                      <code>
                        {concept}
                      </code>
                    </label>
                  ))
                )}

              </div>
            </div>
          )}
        </div>
      </fieldset>

      {/* ------------------------------------------------------------------ */}
      {/* WINDOW                                                             */}
      {/* ------------------------------------------------------------------ */}

      <label className="raw-facts__field">
        <span>
          Window (years)
        </span>

        <input
          type="range"
          min={YEARS_MIN}
          max={YEARS_MAX}
          value={years}
          onChange={(e) =>
            setYears(Number(e.target.value))
          }
        />

        <output>
          {years}
        </output>
      </label>

      {/* ------------------------------------------------------------------ */}
      {/* PLOT                                                               */}
      {/* ------------------------------------------------------------------ */}

 {result.figure === null ? (
  <p role="status">
    Nothing selected, or no raw facts for this ticker.
  </p>
) : (
  <div
    style={{
      width: isFullscreen ? "100vw" : "100%",
      height: isFullscreen
        ? "100vh"
        : `${result.figure.layout.height ?? 600}px`,
      background: "var(--app-bg, #0e1117)",
      position: "relative",
    }}
  >
    <Plot
      data={result.figure.data as never}
      layout={{
        ...result.figure.layout,
        autosize: true,
      } as never}
      style={{
        width: "100%",
        height: "100%",
      }}
      useResizeHandler
      config={{
        displayModeBar: true,
        displaylogo: false,
        modeBarButtonsToAdd: [
          {
            name: "Fullscreen",
            title: isFullscreen ? "Exit fullscreen" : "Fullscreen",
            icon: {
              width: 24,
              height: 24,
              path: `
                M3 3h7v2H5v5H3V3z
                M21 3v7h-2V5h-5V3h7z
                M3 21v-7h2v5h5v2H3z
                M21 21h-7v-2h5v-5h2v7z
              `,
            },
            click: (gd: HTMLElement) => {
              const chartContainer = gd.parentElement;

              if (!chartContainer) return;

              if (document.fullscreenElement) {
                void document.exitFullscreen();
              } else {
                void chartContainer.requestFullscreen();
              }
            },
          },
        ],
      }}
    />
  </div>
)}
    </section>
  );
}