/**
 * The application shell: sidebar, four views, six Analysis tabs.
 *
 * This is `app.py`'s `main()` and `render_analysis()` (app.py:815-900) as one
 * component. It wraps and routes; it does not compute anything a view needs.
 *
 * **The three chart tabs are one `ChartView`** with a different `chart` prop,
 * which is what it was already built for — so switching between Growth,
 * Fundamentals and Valuation does not unmount it, and the per-chart metric
 * selections and window values survive for free.
 *
 * They also survive a switch to a *non-chart* tab, and that costs one line: the
 * `ChartView` stays mounted and is hidden with `hidden` rather than being
 * unmounted. Unmounting would throw away a nine-metric selection because the
 * reader glanced at the Data tab, where Streamlit's session state would have
 * kept it. The alternative — lifting the selection and window state up here —
 * would have changed `ChartView`'s props, which this item is meant not to do.
 * If item 9's data tab turns out heavy enough that keeping a figure in the DOM
 * matters, lifting is the escape hatch.
 *
 * A **view** switch does unmount it. That is the boundary, and it is where the
 * reference's own boundary is: leaving Analysis in `app.py` drops the ticker
 * controls entirely.
 */
import { useEffect, useState } from "react";
import ChartView from "./ChartView.tsx";
import DataTab from "./data/DataTab.tsx";
import { useData } from "./data/DataContext.ts";
import { DataProvider } from "./data/DataProvider.tsx";
import Sidebar from "./shell/Sidebar.tsx";
import Placeholder from "./shell/Placeholder.tsx";
import UpdateNotice from "./shell/UpdateNotice.tsx";
import GuardScreen from "./shell/GuardScreen.tsx";
import {
  DEFAULT_LOCATION,
  TABS,
  TAB_LABELS,
  VIEW_LABELS,
  formatHash,
  isChartTab,
  parseHash,
  withTab,
  withTicker,
  withView,
  type Location,
} from "./shell/navigation.ts";
import "./shell/shell.css";

/** app.py:816 — the page name, carried so the two apps answer to one thing. */
const APP_TITLE = "Kyhestlo";

/** app.py:837-841, verbatim. */
const INTRO =
  "This pipeline fetches SEC EDGAR 10k and 10q filings of more than 600 companies, extracts " +
  "the XBRL facts, computes derived metrics, and links them to yfinance course data. " +
  "This data stream is as pure as possible.";

/** The URL hash is the single source of truth for where you are. */
function useLocation(): [Location, (next: Location) => void] {
  const read = () =>
    typeof window === "undefined" ? DEFAULT_LOCATION : parseHash(window.location.hash);
  const [location, setLocation] = useState<Location>(read);

  // Back/forward, and a hash pasted into the bar, both arrive here.
  useEffect(() => {
    const onHash = () => setLocation(parseHash(window.location.hash));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const go = (next: Location) => {
    const hash = formatHash(next);
    if (window.location.hash !== hash) window.location.hash = hash;
    setLocation(next);
  };
  return [location, go];
}

function Workspace() {
  const { registry, meta, notice, universe, error, loading } = useData();
  const [location, go] = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  // Latches on the first visit to the Data tab and never clears -- see the
  // comment at its render site. Adjusted during render rather than in an
  // effect: React's own pattern for state derived from a prop-like value, and
  // the only one that mounts the tab in the render that first needs it instead
  // of one render later. The guard makes it run once; a ref would have been
  // read during render, which is the thing refs are not for.
  const [dataSeen, setDataSeen] = useState(location.tab === "data");
  if (!dataSeen && location.tab === "data") setDataSeen(true);

  // `.content`'s width changes for two reasons that are not window resizes, and
  // react-plotly.js's `useResizeHandler` listens for exactly one thing: a native
  // `resize` event on `window` (dist/create-plotly-component.min.js's `Q()` is a
  // plain `window.addEventListener("resize", ...)`, not a ResizeObserver on the
  // Plot's own container). So both reasons have to be announced by hand.
  //
  //   1. **The sidebar collapsing**, which reflows the CSS grid. Measured: the
  //      chart's SVG otherwise keeps the pixel width it had before the click.
  //
  //   2. **A chart tab being revealed**, which is the same failure one step
  //      earlier and was live in the shell from the moment tab switching was
  //      built. `ChartView` is mounted for every tab and merely hidden, so
  //      landing on a *non*-chart tab mounts `<Plot>` inside a `display: none`
  //      box: its container measures 0, plotly falls back to `layout.width =
  //      700`, and revealing the tab grows the container to 1204px while the
  //      SVG stays at 700. Measured on both this tree and a pre-item-9 one --
  //      identical, so this is a latent shell defect rather than anything the
  //      data tab introduced. Landing straight on a chart tab always looked
  //      right, which is why it survived three cycles.
  //
  // Gated on the destination being a chart tab: firing while the chart is still
  // hidden would resize it against a 0-width container, which is the failure
  // rather than the fix. One synthetic event reaches the same handler a real
  // resize would, so this stays entirely outside ChartView, `<Plot>` and the
  // figure spec.
  const activeTab = location.tab;
  useEffect(() => {
    if (!isChartTab(activeTab)) return;
    const id = requestAnimationFrame(() => window.dispatchEvent(new Event("resize")));
    return () => cancelAnimationFrame(id);
  }, [sidebarOpen, activeTab]);

  // The registry and the universe are the two files nothing can run without.
  if (error) return <GuardScreen error={error} what="The export" />;
  if (loading || !registry) {
    return (
      <main className="loading">
        <h1>{APP_TITLE}</h1>
        <p>Loading the export…</p>
      </main>
    );
  }

  // A hash naming a ticker that is not in this bundle keeps the ticker: the
  // per-ticker fetch is what knows whether it exists, and it already has a
  // message for the answer. Falling back here would silently rewrite the URL
  // someone shared.
  const ticker = location.ticker ?? universe[0]?.ticker ?? "AAPL";
  const profile = registry.ticker_profile[ticker] ?? registry.default_profile;
  const { view, tab } = location;

  return (
    <div className={`app${sidebarOpen ? "" : " app--collapsed"}`}>
      <Sidebar
        meta={meta}
        view={view}
        onView={(next) => go(withView(location, next))}
        ticker={ticker}
        profile={profile}
        universe={universe}
        onTicker={(next) => go(withTicker(location, next))}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="content">
        <header className="content__head">
          {!sidebarOpen && (
            <button type="button" onClick={() => setSidebarOpen(true)} aria-label="Show sidebar">
              ☰
            </button>
          )}
          <h1>{APP_TITLE}</h1>
        </header>

        {/* After the title and before the intro, exactly as app.py:844 places
            it — and after the guard, because an announcement over an error page
            helps nobody (app.py:838). */}
        <UpdateNotice raw={notice} />

        <p className="intro">{INTRO}</p>

        {view === "analysis" ? (
          <>
            <nav className="tabs" aria-label="Analysis sections">
              {TABS.map((id) => (
                <button
                  key={id}
                  type="button"
                  className={id === tab ? "tab tab--active" : "tab"}
                  aria-current={id === tab ? "page" : undefined}
                  onClick={() => go(withTab(location, id))}
                >
                  {TAB_LABELS[id]}
                </button>
              ))}
            </nav>

            {/* Kept mounted across tab switches — see the module docstring. */}
            <div hidden={!isChartTab(tab)}>
              <ChartView
                registry={registry}
                ticker={ticker}
                chart={isChartTab(tab) ? tab : "valuation"}
              />
            </div>

            {/* Mounted on first open and kept mounted afterwards, for the same
                reason ChartView is: the two period controls are state a reader
                set, and Streamlit's session state would have kept them across a
                tab switch. Unlike ChartView it is not mounted up front, because
                doing so would fetch `facts_full` -- the largest file in the
                export at 21 kB gzipped -- for someone who only opened the
                charts. `dataSeen` is the whole cost of having it both ways. */}
            {dataSeen && (
              <div hidden={tab !== "data"}>
                <DataTab ticker={ticker} />
              </div>
            )}
            {tab === "raw" && (
              <Placeholder title="Raw Facts" item={16}>
                One bar panel per XBRL concept that has a value for this ticker, with the
                include-derived toggle.
              </Placeholder>
            )}
            {tab === "comparison" && (
              <Placeholder title="Comparison" item={12}>
                One metric across several tickers, each keeping its colour by request position, with
                the exclusion notice naming what could not be drawn and why.
              </Placeholder>
            )}
          </>
        ) : view === "encyclopedia" ? (
          <Placeholder title={VIEW_LABELS.encyclopedia} item={20}>
            Every metric the pipeline computes with the formula it actually uses, filterable, plus
            the warning listing any metric that has no documentation.
          </Placeholder>
        ) : view === "coverage" ? (
          <Placeholder title={VIEW_LABELS.coverage} item={21}>
            The full metric-by-profile matrix — which of the 52 metrics each of the 24 profiles
            shows and hides.
          </Placeholder>
        ) : (
          <Placeholder title={VIEW_LABELS.about} item={22}>
            The About page, rendered from <code>content/about.md</code>, including its disclaimer
            callout.
          </Placeholder>
        )}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <DataProvider>
      <Workspace />
    </DataProvider>
  );
}
