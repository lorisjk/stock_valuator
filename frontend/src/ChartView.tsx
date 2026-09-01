/**
 * One chart view: a metric picker and the grid. Was `ValuationChart`; now takes
 * the chart id, because all three charts need the identical shell -- the only
 * thing that varies between them is which builder runs.
 *
 * The figure is rebuilt whenever the ticker, the chart, the selection or the
 * window changes -- `useMemo` over exactly those. That is not a performance
 * choice. A selection change alters the panel count directly; a *window* change
 * alters it indirectly but just as really, because `_window_frame` runs before
 * the empty rule and a panel with no value left in the window becomes a blank
 * one. Either way `makeGrid` derives rows and columns from the count, and a
 * finished figure cannot be re-tiled (inventory 4.1). The only genuinely
 * client-side control in the whole app is the comparison chart's legend, and
 * neither of these is it.
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
import { useMemo, useState, useEffect} from "react";
import Plot from "react-plotly.js";
import MetricPicker from "./MetricPicker.tsx";
import WindowSlider from "./WindowSlider.tsx";
import OutlierControls, {
  VALUATION_MASK_HELP,
  VALUATION_MASKED_NOTE,
} from "./OutlierControls.tsx";
import EmptyPanelNotice from "./EmptyPanelNotice.tsx";
import { shareHistoryAbsent } from "./data/shareHistory.ts";
import type { ChartId, Frames, Registry } from "./contracts.ts";
import { useTickerFacts, useTickerFrames } from "./data/DataContext.ts";
import { DEFAULT_YEARS, defaultSelection, migrateSelection } from "./charts/defaults.ts";
import { buildFundamentals } from "./charts/fundamentals.ts";
import { buildGrowth } from "./charts/growth.ts";
import { buildValuation } from "./charts/valuation.ts";
import { offerableMetricIds } from "./charts/select.ts";
import type { FigureSpec } from "./charts/panel.ts";
import type { HiddenSeries } from "./charts/outliers.ts";

interface ChartResult {
  figure: FigureSpec | null;
  panels: string[];
  offerable: string[];
  /** Only the valuation builder fills this; the other two return nothing to hide. */
  outliers?: HiddenSeries[];
  /** Likewise: only the valuation grid has an empty-panel notice -- see that component. */
  empty?: string[];
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
  options?: {
    requested?: readonly string[] | null;
    years?: number;
    anchor?: Date;
    /** Only `buildValuation` reads it, exactly as only `build_valuation` takes it. */
    snapshot?: boolean;
    /** Likewise: `build_fundamentals` and `build_growth` have no `mask_outliers`. */
    mask?: boolean;
  },
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
  asOf,
}: {
  registry: Registry;
  ticker: string;
  chart: ChartId;
  /**
   * The sidebar's as-of date, or null. **Reaches the valuation builder only.**
   * `build_fundamentals` and `build_growth` call `_window_frame` with a
   * hard-coded `as_of=None` (figures.py:589, :646) and take no such parameter,
   * so forwarding it to them would invent an upper bound the reference does not
   * have -- on the two charts whose windows are the widest.
   */
  asOf: Date | null;
}) {
  const { frames, error } = useTickerFrames(ticker);
  // `undefined` for a chart = "the user has not touched this picker yet", which
  // is what selects the default. Not the same as `[]`, which is a deliberately
  // cleared picker and is honoured as one -- see migrateSelection.
  const [picked, setPicked] = useState<Partial<Record<ChartId, readonly string[]>>>({});
  // The window, also per chart, because the three builders default it
  // differently -- 5 for valuation against 15 for the other two -- and a single
  // shared value cannot honour three different defaults at once. Streamlit does
  // the same thing with three separate keys (`fundamentals_years`,
  // `growth_years`, `valuation_years`). Unlike the selection this needs no
  // migration: the range is 1-15 for every chart, ticker and profile, so a
  // value the user sets is simply carried.
  const [windowYears, setWindowYears] = useState<Partial<Record<ChartId, number>>>({});
  const years = windowYears[chart] ?? DEFAULT_YEARS[chart];
  // Not per chart, unlike the two above: only the valuation grid has the control
  // at all (`build_fundamentals` and `build_growth` take no `mask_outliers`), so
  // one boolean is the whole of it. app.py keeps it in `st.session_state` under
  // `val_mask_outliers`, which is one key for the same reason.
  const [masked, setMasked] = useState(false);

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
    () =>
      frames && build
        ? // `snapshot` is on because app.py:954 always hands `build_valuation`
          // the snapshot frame -- the marker is the app's normal state, not a
          // mode. It is an *option* rather than the default so that the option
          // being absent still reproduces the pre-item-13 figure byte for byte,
          // which is what the item-8 baseline measures.
          build(registry, frames, ticker, {
            requested: selected,
            years,
            snapshot: true,
            mask: masked,
            // Valuation only -- see the prop's docstring. `undefined`, not
            // `null`: the builders test `anchor !== undefined`, which is the
            // port's spelling of `as_of is not None`.
            anchor: chart === "valuation" && asOf !== null ? asOf : undefined,
          })
        : null,
    [build, registry, frames, ticker, selected, years, masked, chart, asOf],
  );

  // `facts_full` is fetched only once the notice is actually going to render --
  // see `useTickerFacts`' `enabled`. Ordered after the build and before the
  // early returns so the hook count is stable whatever branch runs.
  const emptyPanels = result?.empty ?? [];
  const notice = chart === "valuation" && emptyPanels.length > 0;
  const { facts } = useTickerFacts(ticker, notice);

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
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(document.fullscreenElement !== null);

      // Plotly muss seine Größe nach dem Wechsel neu berechnen
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
  return (
    <section>
      
      <MetricPicker
        chart={chart}
        offerable={offerable}
        selected={selected}
        byId={byId}
        onChange={(next) => setPicked({ ...picked, [chart]: next })}
      />

      <WindowSlider
        chart={chart}
        years={years}
        onChange={(next) => setWindowYears({ ...windowYears, [chart]: next })}
      />

      {/* app.py:942 puts the toggle above the chart and the caption below it.
          Both live in one component, so it sits here and the reading order is
          toggle, chart, what-was-hidden -- see its docstring. */}
      <OutlierControls
        report={result?.outliers ?? []}
        masked={masked}
        onMasked={setMasked}
        label={(id) => byId.get(id)?.label ?? id}
        help={VALUATION_MASK_HELP}
        maskedNote={VALUATION_MASKED_NOTE}
        medianLabel="median"
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

      {/* app.py:963. Between the chart and the outlier caption, which is where
          the reference puts it, and valuation-only -- the component's docstring
          has the evidence that this is the reference's design rather than its
          oversight. */}
      {notice && (
        <EmptyPanelNotice
          names={emptyPanels.map((id) => byId.get(id)?.label ?? id)}
          shareHistoryMissing={shareHistoryAbsent(facts)}
        />
      )}

      {/* app.py:1015, a fixed caption on the valuation tab. Item 13 shipped the
          marker without it -- found while reading app.py's outlier block, which
          sits immediately above this line in the reference. It belongs here
          rather than in a later cycle because it is the sentence that tells a
          reader the green point is *excluded from the mean*, which is the same
          promise the masking caption above makes about the hidden points. */}
      {chart === "valuation" && result?.figure !== null && (
        <p className="caption">
          The green circle is the current multiple — today&apos;s price against the latest
          available fundamentals — not a filed period. It is excluded from the mean line, and
          hidden when the as-of date predates it.
        </p>
      )}
    </section>
  );
}
