/**
 * The valuation view: a metric picker and the grid.
 *
 * The figure is rebuilt whenever the ticker, the selection or the window
 * changes -- `useMemo` over exactly those. That is not a performance choice: a
 * selection change alters the panel count, `makeGrid` derives rows and columns
 * from it, and a finished figure cannot be re-tiled (inventory 4.1). The only
 * genuinely client-side control in the whole app is the comparison chart's
 * legend, and this is not it.
 */
import { useMemo, useState } from "react";
import Plot from "react-plotly.js";
import type { Registry } from "./contracts.ts";
import { useTickerFrames } from "./data/DataContext.ts";
import { buildValuation } from "./charts/valuation.ts";

export default function ValuationChart({
  registry,
  ticker,
}: {
  registry: Registry;
  ticker: string;
}) {
  const { frames, error } = useTickerFrames(ticker);
  // null = "the caller said nothing", which is what build_valuation's
  // concepts=None means: the whole visible catalogue. A user's first click has
  // to turn that into a real list, so the picker seeds itself from `offerable`.
  const [requested, setRequested] = useState<readonly string[] | null>(null);

  const result = useMemo(
    () => (frames ? buildValuation(registry, frames, ticker, { requested }) : null),
    [registry, frames, ticker, requested],
  );

  if (error) {
    return (
      <p role="alert">
        Could not load {ticker}: {error.message}
      </p>
    );
  }
  if (!result) return <p>Loading {ticker}…</p>;

  const selected = new Set(requested ?? result.offerable);
  const toggle = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setRequested(result.offerable.filter((candidate) => next.has(candidate)));
  };

  return (
    <section>
      <fieldset>
        <legend>
          Metrics — {result.panels.length} of {result.offerable.length} shown for this profile
        </legend>
        {result.offerable.map((id) => (
          <label key={id} style={{ marginRight: "1rem", whiteSpace: "nowrap" }}>
            <input type="checkbox" checked={selected.has(id)} onChange={() => toggle(id)} /> {id}
          </label>
        ))}
      </fieldset>

      {result.figure === null ? (
        // build_valuation returns None and writes no file. There is no empty
        // grid to show, so say which of the two reasons applies -- a profile
        // that hides everything is not the same as a picker cleared to nothing.
        <p role="status">
          {result.offerable.length === 0
            ? `No valuation metrics are shown for ${ticker}'s profile.`
            : "No metrics selected — pick at least one above."}
        </p>
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
