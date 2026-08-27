/**
 * Where you are in the app, as plain values.
 *
 * Two levels, mirroring `app.py`: a **view** chosen in the sidebar
 * (`VIEWS`, app.py:65) and, inside the Analysis view, a **tab**
 * (`st.tabs([...])`, app.py:894). Nothing here imports React, so the routing
 * rules are checkable from Node -- which is most of what is checkable about a
 * shell at all.
 *
 * **The location lives in the URL hash.** A link to one ticker's valuation
 * chart is a real thing to want, and retrofitting it later means touching every
 * component that holds a piece of the location. The hash rather than a path is
 * deliberate: `load.ts` already documents that a dev/preview server answers an
 * unknown path with `index.html` rather than a 404, so a path-based route would
 * need server rewrites to work on a static host, and the hash needs none.
 *
 * What is **not** in the URL: the metric selection and the window. They are
 * per-chart, high-cardinality, and would turn a shareable link into a
 * paragraph. Adding them later is a change to `parseHash`/`formatHash` and to
 * where that state lives -- see the report; today it is inside `ChartView`,
 * which would have to be lifted first.
 */

export const VIEWS = ["analysis", "encyclopedia", "coverage", "about"] as const;
export type ViewId = (typeof VIEWS)[number];

/** Sidebar labels, matching app.py:61-64 exactly. */
export const VIEW_LABELS: Record<ViewId, string> = {
  analysis: "Analysis",
  encyclopedia: "Metric encyclopedia",
  coverage: "Profile coverage",
  about: "About",
};

/**
 * Analysis tabs in the reference's order (app.py:894-896): Data first, because
 * "the app opens on what was extracted, and the charts follow".
 *
 * The three chart labels come from `CHART_LABELS` (app.py:38) and are carried
 * verbatim -- note `"Growth (YoY)"`, not `"Growth"`. `"Data"` and `"Raw Facts"`
 * are hardcoded at the call site; `CHART_LABELS` does have a `raw_facts` entry,
 * spelled `"Raw facts"` with a lowercase f, and the tab list does not use it.
 * The reference's own two spellings disagree; the tab list wins here because it
 * is what renders.
 */
export const TABS = ["data", "raw", "growth", "fundamentals", "valuation", "comparison"] as const;
export type TabId = (typeof TABS)[number];

export const TAB_LABELS: Record<TabId, string> = {
  data: "Data",
  raw: "Raw Facts",
  growth: "Growth (YoY)",
  fundamentals: "Fundamentals",
  valuation: "Valuation",
  comparison: "Comparison",
};

/** The tabs that are a `ChartView` with a different `chart` prop. */
export const CHART_TABS = ["growth", "fundamentals", "valuation"] as const;
export type ChartTabId = (typeof CHART_TABS)[number];

export const isChartTab = (tab: TabId): tab is ChartTabId =>
  (CHART_TABS as readonly string[]).includes(tab);

/** Ticker-independent views: they describe the pipeline, not a company. */
export const isTickerView = (view: ViewId) => view === "analysis";

export interface Location {
  view: ViewId;
  /** Only meaningful in the Analysis view. */
  tab: TabId;
  /** Only meaningful in the Analysis view; null = "use the default". */
  ticker: string | null;
}

export const DEFAULT_LOCATION: Location = { view: "analysis", tab: "valuation", ticker: null };

const isView = (v: string): v is ViewId => (VIEWS as readonly string[]).includes(v);
const isTab = (v: string): v is TabId => (TABS as readonly string[]).includes(v);

/**
 * `#/analysis/AAPL/valuation` -> a Location. Unknown parts fall back rather
 * than throwing: a hand-edited or stale URL should land somewhere sensible,
 * not on an error page.
 *
 * Ticker case is normalised upward because the export's filenames are
 * uppercase; whether the ticker actually exists is the caller's question, not
 * this function's -- it has no universe to check against.
 *
 * **Empty segments are kept.** The hash is positional, and "no ticker" is a
 * real state -- `formatHash` writes it as `#/analysis//valuation` rather than
 * rewriting the URL with a ticker the user did not choose. Dropping empties
 * here would shift the tab into the ticker's place and read `#/analysis//data`
 * as ticker `DATA`; the round-trip test exists because that is exactly what an
 * earlier version of this function did.
 */
export function parseHash(hash: string): Location {
  const parts = hash.replace(/^#\/?/, "").split("/").map(decodeURIComponent);
  const [rawView, rawTicker, rawTab] = parts;
  const view = rawView && isView(rawView) ? rawView : DEFAULT_LOCATION.view;
  if (view !== "analysis") return { view, tab: DEFAULT_LOCATION.tab, ticker: null };
  const ticker = rawTicker ? rawTicker.toUpperCase() : null;
  const tab = rawTab && isTab(rawTab) ? rawTab : DEFAULT_LOCATION.tab;
  return { view, tab, ticker };
}

/**
 * A Location -> the hash it round-trips through.
 *
 * The non-Analysis views carry neither ticker nor tab, so the URL cannot
 * express "the About page, for AAPL" -- the same reason app.py hides the ticker
 * selector on those views (app.py:872).
 */
export function formatHash(location: Location): string {
  if (location.view !== "analysis") return `#/${location.view}`;
  const ticker = location.ticker ?? "";
  return `#/analysis/${encodeURIComponent(ticker)}/${location.tab}`;
}

/**
 * What a location becomes when one part of it changes.
 *
 * Kept as a function rather than three setState calls so the invariants hold in
 * one place: leaving Analysis drops the ticker and the tab, and returning to it
 * restores neither -- the caller supplies them, exactly as `parseHash` does.
 */
export function withView(location: Location, view: ViewId): Location {
  if (view === location.view) return location;
  return view === "analysis" ? { ...location, view } : { view, tab: location.tab, ticker: null };
}

export const withTab = (location: Location, tab: TabId): Location => ({ ...location, tab });

export const withTicker = (location: Location, ticker: string): Location => ({
  ...location,
  ticker: ticker.toUpperCase(),
});
