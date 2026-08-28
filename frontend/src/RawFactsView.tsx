/**
 * The Raw Facts tab: `app.py`'s `tab_raw` block (app.py:1106).
 *
 * Its own view rather than a fourth `ChartView` chart, and the reason is in the
 * data: `ChartView` is built around a `ChartId`, a registry catalogue and
 * `profile_visibility`, and this chart has none of the three. Its concepts come
 * from the ticker's own facts, its ids are XBRL tags with no `Metric` behind
 * them to supply a label or a reference line, and its narrowing already happened
 * upstream in the export (see `raw.ts`). Forcing it through `ChartView` would
 * have meant a fourth `ChartId` that the registry does not have and three
 * `Partial` lookups that are always empty.
 *
 * **The selection is stored raw and resolved at render**, the same discipline
 * `ChartView` uses: state holds what was last ticked, and what the builder
 * receives is that intersected with the current ticker's catalogue. So switching
 * ticker keeps the overlap and restores the rest on the way back, and toggling
 * "include derived" does not silently drop a pick it will offer again.
 */
import { useMemo, useState } from "react";
import Plot from "react-plotly.js";
import { useConceptCandidates, useTickerFacts } from "./data/DataContext.ts";
import { YEARS_MAX, YEARS_MIN } from "./charts/defaults.ts";
import { RAW_DEFAULT_CONCEPTS, RAW_YEARS, buildRawFacts } from "./charts/raw.ts";
import "./raw-facts.css";

/** app.py:1115 -- the four openers, kept only where the ticker offers them. */
const defaultsFor = (offerable: readonly string[]) =>
  RAW_DEFAULT_CONCEPTS.filter((c) => offerable.includes(c)) as unknown as string[];

export default function RawFactsView({ ticker }: { ticker: string }) {
  const { facts, error } = useTickerFacts(ticker);
  const { candidates, error: candidatesError } = useConceptCandidates(ticker);

  // `undefined` = "not touched yet", which is what selects the defaults. `[]` is
  // a deliberately cleared picker and is honoured as one -- `build_raw_facts`
  // with `concepts=[]` draws nothing, and app.py says so in as many words.
  const [picked, setPicked] = useState<readonly string[] | undefined>(undefined);
  const [includeDerived, setIncludeDerived] = useState(false);
  const [years, setYears] = useState(RAW_YEARS);

  const offerable = useMemo(
    () => buildRawFacts(facts, candidates, ticker, { includeDerived }).offerable,
    [facts, candidates, ticker, includeDerived],
  );

  const selected = useMemo(() => {
    if (picked === undefined) return defaultsFor(offerable);
    const keep = new Set(picked);
    return offerable.filter((c) => keep.has(c));
  }, [picked, offerable]);

  const result = useMemo(
    () => buildRawFacts(facts, candidates, ticker, {
      requested: selected, years, includeDerived,
    }),
    [facts, candidates, ticker, selected, years, includeDerived],
  );

  if (error) {
    return <p className="notice-inline">Could not load {ticker}: {error.message}</p>;
  }
  if (candidatesError) {
    return (
      <p className="notice-inline">
        Could not load the concept list: {candidatesError.message}
      </p>
    );
  }
  if (!facts || !candidates) return <p className="caption">Loading {ticker}…</p>;

  // Rebuilt by filtering `offerable`, never by pushing onto `selected`, so the
  // panel order is the catalogue's whatever order the boxes were ticked in.
  const setTo = (ids: Set<string>) => setPicked(offerable.filter((c) => ids.has(c)));
  const toggle = (concept: string) => {
    const next = new Set(selected);
    if (next.has(concept)) next.delete(concept);
    else next.add(concept);
    setTo(next);
  };
  const atDefault =
    JSON.stringify(selected) === JSON.stringify(defaultsFor(offerable));

  return (
    <section className="raw-facts">
      {/* app.py:1107, verbatim. */}
      <p>Concepts as filed, before any metric is computed.</p>

      {/* app.py:1110-1112. */}
      <label className="raw-facts__derived">
        <input
          type="checkbox"
          checked={includeDerived}
          onChange={(e) => setIncludeDerived(e.target.checked)}
        />{" "}
        Include derived concepts (_TTM, _QUARTERLY, …)
      </label>

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
          <button type="button" onClick={() => setPicked([])} disabled={selected.length === 0}>
            None
          </button>{" "}
          <button
            type="button"
            onClick={() => setPicked(defaultsFor(offerable))}
            disabled={atDefault}
          >
            Default
          </button>
        </legend>
        {/* No labels beside the ids, unlike `MetricPicker`: these *are* the XBRL
            tags, there is no registry entry behind them carrying a readable
            name, and the panel titles show the same string. */}
        <div className="raw-facts__options">
          {offerable.map((concept) => (
            <label key={concept}>
              <input
                type="checkbox"
                checked={selected.includes(concept)}
                onChange={() => toggle(concept)}
              />{" "}
              <code>{concept}</code>
            </label>
          ))}
        </div>
      </fieldset>

      {/* app.py:1119 -- 1 to 15, default 15, and no as-of: `build_raw_facts`
          hard-codes `as_of=None` (figures.py:1110), so the sidebar's date does
          not reach this chart at all. */}
      <label className="raw-facts__field">
        <span>Window (years)</span>
        <input
          type="range"
          min={YEARS_MIN}
          max={YEARS_MAX}
          value={years}
          onChange={(e) => setYears(Number(e.target.value))}
        />
        <output>{years}</output>
      </label>

      {result.figure === null ? (
        // app.py:1123's fallback, which covers both an empty pick and a ticker
        // with nothing filed.
        <p role="status">Nothing selected, or no raw facts for this ticker.</p>
      ) : (
        <Plot
          data={result.figure.data as never}
          layout={result.figure.layout as never}
          style={{ width: "100%", height: result.figure.layout.height }}
          useResizeHandler
        />
      )}
    </section>
  );
}
