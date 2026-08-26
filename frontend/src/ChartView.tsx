/**
 * One chart view: a metric picker and the grid. Was `ValuationChart`; now takes
 * the chart id, because all three charts need the identical shell -- the only
 * thing that varies between them is which builder runs.
 *
 * The figure is rebuilt whenever the ticker, the chart or the selection changes
 * -- `useMemo` over exactly those. That is not a performance choice: a selection
 * change alters the panel count, `makeGrid` derives rows and columns from it,
 * and a finished figure cannot be re-tiled (inventory 4.1). The only genuinely
 * client-side control in the whole app is the comparison chart's legend, and
 * this is not it.
 *
 * **The selection is stored raw and resolved at render**, never migrated in
 * place. State holds what the user last ticked for each chart; what the builder
 * receives is `migrateSelection(chart, raw, offerable)`, recomputed for the
 * current ticker. Two consequences, both deliberate:
 *
 *   - Reacting to a ticker change needs no effect and no setState during
 *     render. The switch is a pure recomputation, so there is no dependency
 *     list here that could go stale against it.
 *   - Switching away from a ticker and back **restores** the original pick. A
 *     selection migrated in place would have been overwritten at the first
 *     switch, with no way for the user to get it back.
 */
import { useMemo, useState } from "react";
import Plot from "react-plotly.js";
import MetricPicker from "./MetricPicker.tsx";
import type { ChartId, Frames, Registry } from "./contracts.ts";
import { useTickerFrames } from "./data/DataContext.ts";
import { defaultSelection, migrateSelection } from "./charts/defaults.ts";
import { buildFundamentals } from "./charts/fundamentals.ts";
import { buildGrowth } from "./charts/growth.ts";
import { buildValuation } from "./charts/valuation.ts";
import { offerableMetricIds } from "./charts/select.ts";
import type { FigureSpec } from "./charts/panel.ts";

interface ChartResult {
  figure: FigureSpec | null;
  panels: string[];
  offerable: string[];
}

/**
 * What every chart builder looks like from here. Spelled out rather than derived
 * from one of them, so no chart is implicitly the canonical one -- and so item
 * 8's `years` and item 15's `anchor` have a declared home.
 */
type ChartBuilder = (
  registry: Registry,
  frames: Frames,
  ticker: string,
  options?: { requested?: readonly string[] | null; years?: number; anchor?: Date },
) => ChartResult;

/**
 * The one place a chart id turns into a builder. All three are here now, so the
 * map is total -- kept as a `Partial` record anyway, because the `!build` branch
 * below is what makes adding a fourth chart id a compile-clean intermediate
 * state rather than a runtime crash.
 */
const BUILDERS: Partial<Record<ChartId, ChartBuilder>> = {
  valuation: buildValuation,
  fundamentals: buildFundamentals,
  growth: buildGrowth,
};

const LABELS: Record<ChartId, string> = {
  valuation: "valuation",
  fundamentals: "fundamentals",
  growth: "growth",
};

export default function ChartView({
  registry,
  ticker,
  chart,
}: {
  registry: Registry;
  ticker: string;
  chart: ChartId;
}) {
  const { frames, error } = useTickerFrames(ticker);
  // `undefined` for a chart = "the user has not touched this picker yet", which
  // is what selects the default. Not the same as `[]`, which is a deliberately
  // cleared picker and is honoured as one -- see migrateSelection.
  const [picked, setPicked] = useState<Partial<Record<ChartId, readonly string[]>>>({});

  // The option list, from `selectMetricIds(registry, chart, ticker, null)` --
  // the same call every builder makes for its own narrowing, not a second
  // implementation of `is_hidden`. It is needed here as well as inside the
  // builder because the picker's options are an *input* to the build: the
  // selection has to be resolved against this ticker's catalogue before there
  // is a request to build with. The verification asserts the two agree for
  // every (chart, ticker) pair.
  const offerable = useMemo(
    () => offerableMetricIds(registry, chart, ticker),
    [registry, chart, ticker],
  );

  const selected = useMemo(() => {
    const raw = picked[chart];
    return raw === undefined
      ? defaultSelection(chart, offerable)
      : migrateSelection(chart, raw, offerable);
  }, [picked, chart, offerable]);

  const byId = useMemo(() => new Map(registry.metrics.map((m) => [m.id, m])), [registry]);

  const build = BUILDERS[chart];
  const result = useMemo(
    () => (frames && build ? build(registry, frames, ticker, { requested: selected }) : null),
    [build, registry, frames, ticker, selected],
  );

  if (!build) return <p role="status">The {LABELS[chart]} chart is not rebuilt yet.</p>;
  if (error) {
    return (
      <p role="alert">
        Could not load {ticker}: {error.message}
      </p>
    );
  }

  // The picker renders before the frames arrive: its options come from the
  // registry, which is already loaded, so a ticker switch does not blank the
  // control while the per-ticker file is in flight.
  return (
    <section>
      <MetricPicker
        chart={chart}
        offerable={offerable}
        selected={selected}
        byId={byId}
        onChange={(next) => setPicked({ ...picked, [chart]: next })}
      />

      {!result ? (
        <p>Loading {ticker}…</p>
      ) : result.figure === null ? (
        // The builders return None and draw nothing. Three different situations
        // reach this branch and they are not the same thing to a reader: the
        // profile hides every metric on this chart, the user cleared the picker,
        // or the ticker has no rows in the frame at all (build_growth's
        // missing-column branch). A panel that *is* drawn but has no data in the
        // window is a fourth case and does not come here -- that one is the
        // "No Data" placeholder, and the notice naming those panels is item 17.
        <p role="status">
          {offerable.length === 0
            ? `No ${LABELS[chart]} metrics are shown for ${ticker}'s profile.`
            : selected.length === 0
              ? "No metrics selected — pick at least one above."
              : `No ${LABELS[chart]} data for ${ticker}.`}
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
