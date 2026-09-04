"""Streamlit prototype for the stock valuator.

Reads only what the nightly pipeline exported to data/app/ -- no pipeline
computation happens here. Import direction is app -> figures -> config; this
file never imports main.py.

Run with:  streamlit run app.py
"""
import json
import os

import pandas as pd
import streamlit as st

import config
import figures


# Same location main.export_for_app writes to. Derived from config.DATA_DIR
# rather than imported from main, to keep the import direction one-way.
APP_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            config.DATA_DIR, "app")

FRAME_FILES = {
    "fundamentals": "metrics_long.parquet",
    "valuation": "valuation_history.parquet",
    "growth": "facts_growth.parquet",
}
# The data tab reads the unnarrowed frames. facts_full deliberately duplicates
# facts_growth: the charts want the 3 growth concepts, the data tab wants a raw
# concept next to its _TTM derivation, which is what makes the TTM auditable.
DATA_FILES = {
    "facts": "facts_full.parquet",
    "metrics": "metrics_long.parquet",
    "valuation": "valuation_history.parquet",
    "snapshot": "current_snapshot.parquet",
}
# "Growth", not "Growth (YoY)": the chart draws either year-over-year or
# quarter-over-quarter now, and the mode is named on the control and in the
# figure title rather than on the tab, which cannot follow it.
CHART_LABELS = {
    "fundamentals": "Fundamentals",
    "growth": "Growth",
    "valuation": "Valuation",
    "raw_facts": "Raw facts",
}

# How many period columns the table and the copy block show by default. The
# table gets 4 years of quarters; the copy block is deliberately smaller,
# because a full facts table pasted into a chat is already near the practical
# limit and the recent periods are what a question is usually about.
DEFAULT_TABLE_PERIODS = 16
DEFAULT_COPY_PERIODS = 8

# Reference material is reached from the sidebar rather than from more tabs. Nine
# tabs in one row is not navigable, and -- the deciding reason -- these pages are
# ticker-independent: sitting them next to a ticker-specific tab set would invite
# the reader to assume they describe the selected ticker. Switching away from
# Analysis also hides the ticker controls, so there is nothing to misread.
#
# About joins them for exactly that reason and no other: it describes the project,
# not the selected company. It sits last because it is the page a reader looks for
# once, whereas the other two are looked up repeatedly.
VIEW_ANALYSIS = "Analysis"
VIEW_ENCYCLOPEDIA = "Metric encyclopedia"
VIEW_COVERAGE = "Profile coverage"
VIEW_ABOUT = "About"
VIEWS = [VIEW_ANALYSIS, VIEW_ENCYCLOPEDIA, VIEW_COVERAGE, VIEW_ABOUT]

# Editable text that is not code: the About page and the update notice. Kept in
# files rather than in string constants so the operator can change what the site
# says without touching a module the pipeline also imports, and so "no file" can
# mean "nothing to say" without a special case.
CONTENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "content")
ABOUT_FILE = "about.md"
NOTICE_FILE = "update_notice.md"

# The one heading render_about lifts out of the flow and draws as a callout. The
# disclaimer has to be visible without scrolling past the introduction, and that is
# a rendering decision rather than something the text can enforce about itself.
PROMINENT_ABOUT_SECTIONS = {"disclaimer"}

# Dismissal lives in session state because Streamlit re-executes this whole script
# on every widget interaction -- a module-level or local flag would be reset by the
# next click. Session state persists for the browser session and is dropped on
# reload, which is exactly the requested lifetime, so no cookie is involved.
NOTICE_DISMISSED_KEY = "update_notice_dismissed"

CHART_SECTIONS = [
    (config.CHART_FUNDAMENTALS, "Fundamentals", "What the business does, independent of its share price."),
    (config.CHART_VALUATION, "Valuation", "What the market charges for a claim on that business."),
    (config.CHART_GROWTH, "Growth", "Change in the underlying filed figures, year over year or quarter over quarter."),
    
]


# Dataframes are cached, figures never are: building a figure is cheap, and a
# cached figure would silently outlive the widget state that produced it.

def missing_files() -> list[str]:
    needed = sorted(set(FRAME_FILES.values()) | set(DATA_FILES.values())
                    | {"universe.parquet", "meta.json"})
    return [n for n in needed if not os.path.exists(os.path.join(APP_DATA_DIR, n))]


@st.cache_data(show_spinner=False)
def load_frame(name: str) -> pd.DataFrame:
    return pd.read_parquet(os.path.join(APP_DATA_DIR, name))


@st.cache_data(show_spinner=False)
def load_meta() -> dict:
    with open(os.path.join(APP_DATA_DIR, "meta.json"), encoding="utf-8") as fh:
        return json.load(fh)


def read_content(name: str) -> str:
    """A content file's text, or '' when it is absent or unreadable.

    Deliberately **not** cached, unlike the frames above. These files are the ones a
    person edits by hand, and a cache would hold the old text until someone knew to
    clear it; they are a few kilobytes read once per rerun.

    An absent file is not an error. That is what lets an empty `update_notice.md` --
    or no file at all -- mean "nothing to announce" without a separate switch.
    """
    try:
        with open(os.path.join(CONTENT_DIR, name), encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def strip_comments(text: str) -> str:
    """Markdown with its HTML comments removed.

    The content files carry their editing instructions in `<!-- -->` blocks. Streamlit
    renders markdown with HTML disabled, so a comment would otherwise be printed to
    the page verbatim -- and, worse for the notice, a file holding nothing but its
    instructions would count as content and draw an empty box.
    """
    out, rest = [], text
    while True:
        start = rest.find("<!--")
        if start == -1:
            out.append(rest)
            return "".join(out)
        out.append(rest[:start])
        end = rest.find("-->", start)
        if end == -1:                      # unterminated comment: drop the remainder
            return "".join(out)
        rest = rest[end + 3:]


def frame_for(chart: str) -> pd.DataFrame:
    return load_frame(FRAME_FILES[chart])


def frame_for_concept(concept: str) -> tuple[pd.DataFrame | None, str | None]:
    """Route a concept to the frame it lives in, via figures.concept_source."""
    source = figures.concept_source(concept)
    if source is None:
        return None, None
    return frame_for(source), source


def metric_options(chart: str, ticker: str | None) -> tuple[list[str], dict[str, str]]:
    """(ids, id -> label) for a chart type, already narrowed by is_hidden.

    Called per chart type on purpose: fundamentals/valuation ids are metric
    names, growth ids are XBRL concept names, and the registry keeps those
    namespaces separate.
    """
    pairs = config.get_plottable_metrics(chart, ticker=ticker)
    return [i for i, _ in pairs], {i: label for i, label in pairs}



def pivot_ticker(frame: pd.DataFrame, ticker: str,
                 value_column: str = "value") -> pd.DataFrame:
    """One ticker's long frame as rows = period end (newest first), cols = concept.

    Returns raw, unrounded numbers -- downloads and the copy block read this,
    display formatting is applied separately in format_for_display().

    dropna=False is load-bearing: a concept that exists for the ticker but is
    null in every period must stay as an all-null column. Whether a metric is
    "not applicable to this business model" or "extraction failed" is the
    question this tab exists to answer, and dropping the column would answer
    neither.
    """
    columns = ["end", "concept", value_column]
    sub = frame.loc[frame["ticker"] == ticker, columns]
    if sub.empty:
        return pd.DataFrame()
    wide = sub.pivot_table(index="end", columns="concept", values=value_column,
                           aggfunc="first", dropna=False)
    wide = wide.sort_index(ascending=False)
    wide.columns.name = None
    return wide


# metrics_long mixes quality flags in among the metrics, and neither config.py
# nor quality.py offers a way to tell them apart. METRICS excludes the flags, but
# it also excludes rotce, effective_tax_rate and the nine *_quarterly series, so
# "absent from METRICS" is not a flag test. quality.py's "flags" are an unrelated
# thing (EDGAR coverage warnings that never reach these frames). So the rule is
# name-based and lives only here. The suffix alone is not enough -- two flags
# carry none -- hence the explicit pair; the suffix then widens the set on its
# own if the pipeline gains another *_flag.
QUALITY_FLAG_CONCEPTS = {"fcf_exceeds_ebitda", "inorganic_contaminated"}


def is_quality_flag(concept: str) -> bool:
    return concept.endswith("_flag") or concept in QUALITY_FLAG_CONCEPTS


_FACT_SUFFIXES = ("_CALC", "_TTM", "_QUARTERLY")


def fact_is_derived(ticker: str, concept: str) -> bool:
    """Did the pipeline compute this concept, or fetch it from EDGAR?

    Structural rather than a suffix match: the names the pipeline asks EDGAR for
    are exactly get_concept_candidates(ticker)'s keys, so anything else in the
    facts frame was derived. That catches PPNR, CoreOperatingEarnings and
    TangibleEquity, which are derived but carry no suffix -- a suffix rule calls
    all three raw.
    """
    return concept not in config.get_concept_candidates(ticker)


def fact_base(concept: str) -> str:
    """Concept name with the derivation suffixes stripped, so that Revenue and
    Revenue_TTM sort next to each other -- comparing them is how the TTM
    derivation gets audited."""
    base = concept
    changed = True
    while changed:
        changed = False
        for suffix in _FACT_SUFFIXES:
            if base.endswith(suffix) and len(base) > len(suffix):
                base = base[: -len(suffix)]
                changed = True
    return base


def order_fact_columns(ticker: str, concepts) -> list[str]:
    """Grouped by base concept, raw before its own derivations."""
    return sorted(concepts, key=lambda c: (fact_base(c), fact_is_derived(ticker, c), c))


# Marks a column whose _TTM values were read from 12-month facts rather than summed
# from four quarters. A single character because the facts table is already tight at
# ~37 columns; the legend underneath names the concepts in full.
ANNUAL_CADENCE_MARKER = "ᵃ"      # modifier letter small a
MIXED_CADENCE_MARKER = "ᵐ"       # modifier letter small m


def cadence_markers(frame: pd.DataFrame, ticker: str) -> tuple[dict[str, str], str]:
    """(concept -> marker, legend text) from the facts frame's `ttm_source` column.

    Marked per column rather than per cell, and that is a measurement rather than a
    convenience: `calculate_ttm` and `parse_edgar.annual_ttm_values` are disjoint by
    construction -- the annual path runs only where the quarterly extraction produced
    nothing -- so provenance is a property of the series. 0 of 5,836 series in the
    exported frame carry both labels. A per-cell suffix would cost readability in
    every row to express something that never varies within a column.

    The mixed case is still detected rather than assumed away: a marker that quietly
    rounded a mixed series to "annual" would assert something the pipeline has not
    established. Rows with no value carry `ttm_source = None` and contribute nothing,
    so an empty cell is never claimed to have a provenance.
    """
    if "ttm_source" not in frame.columns:
        return {}, ""
    sub = frame.loc[(frame["ticker"] == ticker) & frame["ttm_source"].notna(),
                    ["concept", "ttm_source"]]
    if sub.empty:
        return {}, ""
    sources = sub.groupby("concept")["ttm_source"].agg(set)
    annual = sorted(c for c, s in sources.items() if s == {"annual_fact"})
    mixed = sorted(c for c, s in sources.items() if len(s) > 1)
    if not annual and not mixed:
        return {}, ""

    markers = {c: ANNUAL_CADENCE_MARKER for c in annual}
    markers.update({c: MIXED_CADENCE_MARKER for c in mixed})
    parts = []
    if annual:
        parts.append(
            f"{ANNUAL_CADENCE_MARKER} **annual cadence** — {', '.join(f'`{c}`' for c in annual)}. "
            "This filer discloses the item once a year, so the value is the 12-month "
            "figure taken as filed rather than four quarters summed. One point a year "
            "is complete coverage of what was published, not a gap."
        )
    if mixed:
        parts.append(
            f"{MIXED_CADENCE_MARKER} **mixed cadence** — {', '.join(f'`{c}`' for c in mixed)}: "
            "some periods summed from quarters, others read from a 12-month fact."
        )
    parts.append(
        "Unmarked `_TTM` columns are summed from four quarters. `FCF_TTM`, `EBITDA_TTM`, "
        "`FFO_TTM` and `EPS_TTM_CALC` are built from other columns further down the "
        "pipeline and carry no provenance of their own — theirs is their inputs', "
        "visible in this same table."
    )
    return markers, "  \n".join(parts)


# Kept strictly apart from the numbers: format_for_display returns a frame of
# strings that is only ever handed to st.dataframe. Downloads and copy blocks
# are produced from the numeric frame, so they carry full precision.

_MAGNITUDES = ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K"))
# Above this, a column is treated as absolute (currency, share counts) and gets
# a scaled unit; below it as a ratio and gets fixed decimals. Per column, from
# the column's own maximum, so one column never mixes two treatments.
ABSOLUTE_THRESHOLD = 1e4


def _format_absolute(value: float) -> str:
    if pd.isna(value):
        return ""
    for cutoff, suffix in _MAGNITUDES:
        if abs(value) >= cutoff:
            return f"{value / cutoff:,.2f}{suffix}"
    return f"{value:,.2f}"


def _format_ratio(value: float, percent: bool) -> str:
    if pd.isna(value):
        return ""
    return f"{value * 100:.2f}%" if percent else f"{value:.4f}"


def _percent_applies(concept: str, value_column: str) -> bool:
    """Does the registry's percent flag describe *this* column of *this* frame?

    The registry spans two id namespaces, and three ids exist in both worlds:
    Revenue, NetIncomeLoss and SharesOutstanding are registered as CHART_GROWTH
    metrics keyed by XBRL concept name, with percent=True -- correct, because the
    growth chart plots YoY percentages. The facts frame holds columns with those
    same three names carrying absolute dollar figures, so reading the flag by name
    alone rendered $109bn of revenue as "10941700000000.00%".

    Matching on id_namespace would not fix it: the facts frame's columns *are*
    XBRL concept names, i.e. exactly the namespace those entries live in.
    value_column is what separates them -- a growth entry describes `yoy_growth`
    and never `value`. Registry ids are globally unique (_index_metrics raises on
    a duplicate at import), so this single test is unambiguous.
    """
    metric = config.METRICS_BY_ID.get(concept)
    return metric is not None and metric.percent and metric.value_column == value_column


def format_for_display(wide: pd.DataFrame, value_column: str = "value") -> pd.DataFrame:
    """Numeric pivot -> strings for on-screen reading. Never used for export.

    `value_column` is the column the pivot was built from; the caller always knows
    it. It decides whether a registry entry describes what is being shown -- see
    _percent_applies.

    A concept whose registry entry does describe this column and carries
    percent=True is shown as a percentage; that covers the metric frames. Facts
    concepts have no applicable entry, so the fallback is the column's own
    magnitude -- which puts Revenue and Assets in scaled units and leaves
    EPS_TTM_CALC and DividendsPerShare_TTM as plain decimals, without needing a
    per-concept table that would go stale.
    """
    if wide.empty:
        return wide
    out = {}
    for concept in wide.columns:
        column = wide[concept]
        if _percent_applies(concept, value_column):
            out[concept] = column.map(lambda v: _format_ratio(v, True))
        elif column.abs().max() >= ABSOLUTE_THRESHOLD:
            out[concept] = column.map(_format_absolute)
        else:
            out[concept] = column.map(lambda v: _format_ratio(v, False))
    display = pd.DataFrame(out, index=wide.index)
    display.index = display.index.strftime("%Y-%m-%d")
    display.index.name = "end"
    return display


def to_csv_text(wide: pd.DataFrame) -> str:
    """Full precision, index included -- for downloads and the copy block."""
    return wide.to_csv(index=True, lineterminator="\n")


def render_data_section(title: str, wide: pd.DataFrame, ticker: str, slug: str,
                        periods: int, copy_periods: int, caption: str = "",
                        value_column: str = "value",
                        column_markers: "dict[str, str] | None" = None,
                        marker_legend: str = "") -> None:
    """One section of the data tab: table, download, copy block.

    `column_markers` annotates the on-screen header of individual columns. It is
    applied to the display frame only, so downloads and the copy block keep clean
    concept names at full precision -- the same numbers/strings split the rest of
    this module observes.
    """
    st.subheader(title)
    if caption:
        st.caption(caption)
    if wide.empty:
        st.info("No rows for this ticker in this frame.")
        return

    shown = wide.head(periods)
    empty_columns = int(shown.isna().all().sum())
    st.caption(
        f"{len(shown)} of {len(wide)} periods · {shown.shape[1]} concepts"
        + (f" · {empty_columns} null in every period shown — kept on purpose, "
           "an empty column is a finding" if empty_columns else "")
    )
    display = format_for_display(shown, value_column)
    if column_markers:
        display = display.rename(columns={
            concept: f"{concept} {marker}"
            for concept, marker in column_markers.items() if concept in display.columns
        })
    st.dataframe(display, width="stretch")
    if marker_legend and column_markers and any(c in shown.columns for c in column_markers):
        st.caption(marker_legend)

    st.download_button(
        "Download CSV", to_csv_text(shown), file_name=f"{ticker}_{slug}.csv",
        mime="text/csv", key=f"dl_{slug}",
    )
    copied = wide.head(copy_periods)
    text = to_csv_text(copied)
    with st.expander(f"Copy table — {len(copied)} periods, ~{len(text):,} characters"):
        st.code(text, language="text")


def render_flag_section(wide: pd.DataFrame, ticker: str, periods: int) -> None:
    """Quality flags get their own presentation, not columns among the ratios.

    A flag is the pipeline saying where it is unsure, and a column of zeros
    between two ratios buries exactly that. The summary answers the question a
    0/1 column makes you reconstruct by eye: how often, and how recently.
    """
    if wide.empty:
        st.info("No quality flags recorded for this ticker.")
        return
    rows = []
    for concept in wide.columns:
        column = wide[concept].dropna()
        raised = column[column == 1.0]
        rows.append({
            "flag": concept,
            "raised": int(len(raised)),
            "periods evaluated": int(len(column)),
            "most recent": raised.index.max().strftime("%Y-%m-%d") if len(raised) else "—",
        })
    st.dataframe(pd.DataFrame(rows).set_index("flag"), width="stretch")
    with st.expander("Per-period flag values"):
        shown = wide.head(periods)
        display = shown.astype("Float64").astype("string").fillna("")
        display.index = shown.index.strftime("%Y-%m-%d")
        st.dataframe(display, width="stretch")
        st.download_button(
            "Download CSV", to_csv_text(shown), file_name=f"{ticker}_flags.csv",
            mime="text/csv", key="dl_flags",
        )


def render_snapshot_section(snapshot: pd.DataFrame, ticker: str) -> None:
    """The snapshot is long with one row per (ticker, concept) and a single
    constant `end`, so the ticker's slice is already a concept/value list --
    which is the transposed view. Pivoting it would produce one row and ~40
    columns that scroll sideways, and would add nothing: there is no second
    period to compare against.
    """
    st.subheader("Current snapshot")
    sub = snapshot.loc[snapshot["ticker"] == ticker, ["concept", "value", "end"]]
    if sub.empty:
        st.info("No snapshot row for this ticker.")
        return
    as_of = sub["end"].iloc[0]
    st.caption(f"{len(sub)} concepts · as of {as_of:%Y-%m-%d} · "
               "one row per concept, so a profile that does not apply is simply absent")

    table = sub[["concept", "value"]].sort_values("concept").set_index("concept")
    display = table.copy()
    # Same rule as format_for_display, via the same helper -- the snapshot is one
    # value per concept rather than a column, so it cannot use the magnitude of a
    # column and decides per value instead.
    display["value"] = [
        _format_ratio(v, True) if _percent_applies(c, "value")
        else (_format_absolute(v) if abs(v) >= ABSOLUTE_THRESHOLD else _format_ratio(v, False))
        for c, v in zip(table.index, table["value"])
    ]
    st.dataframe(display, width="stretch")
    st.download_button(
        "Download CSV", table.to_csv(index=True, lineterminator="\n"),
        file_name=f"{ticker}_snapshot.csv", mime="text/csv", key="dl_snapshot",
    )
    text = table.to_csv(index=True, lineterminator="\n")
    with st.expander(f"Copy table — ~{len(text):,} characters"):
        st.code(text, language="text")


# The four tickers that render blank valuation panels are a symptom, not a list.
# Measured over the 500-ticker export: no count-based threshold separates the
# tickers that produce a multiple from the ones that do not -- the thinnest
# working ticker has 3 EPS_TTM_CALC points, and EA has 70 and still produces
# nothing (it was taken private, so the price side is gone). The distributions
# overlap completely, so the only reliable test is the direct one: is the slice
# the panel would draw actually empty?
def empty_valuation_panels(frame: pd.DataFrame, ticker: str, concepts: list[str],
                           years: int, as_of) -> list[str]:
    """Which of `concepts` have no value at all in the window the chart will draw."""
    if not concepts:
        return []
    windowed = figures._window_frame(frame, years, as_of)
    sub = windowed[windowed["ticker"] == ticker]
    empty = []
    for concept in concepts:
        values = sub.loc[sub["concept"] == concept, "value"]
        if values.notna().sum() == 0:
            empty.append(concept)
    return empty


def share_history_absent(ticker: str) -> bool:
    """True when the ticker has no SharesOutstanding value at all.

    This is the one cause the app can establish from its own data, and it is
    deliberately the strict case -- zero, not "thin". BKR has two points and
    PSKY seven, which is too few to produce a multiple but is not the same
    statement, and EA has seventy and still produces none. Claiming a cause the
    data does not support is worse than naming only the symptom.
    """
    facts = load_frame(DATA_FILES["facts"])
    series = facts.loc[(facts["ticker"] == ticker)
                       & (facts["concept"] == "SharesOutstanding"), "value"]
    return series.notna().sum() == 0


def render(fig, empty_message: str) -> None:
    if fig is None:
        st.info(empty_message)
        return
    # width="stretch" is the current spelling of use_container_width=True, which
    # Streamlit deprecated with a removal date of 2025-12-31 and now warns about
    # on every call. The builders are passed width=None so the figure does not
    # pin a width and fight the container.
    st.plotly_chart(fig, width="stretch")


def render_data_tab(ticker: str) -> None:
    """The chain from raw filing facts to the final snapshot, as tables.

    Every frame here is the pipeline's post-filter_hidden_rows output, so a
    concept the ticker's profile suppresses is already absent -- this tab shows
    what was extracted, never more than the charts are allowed to show.
    """
    st.write(
        "Everything the charts are drawn from, for **" + ticker + "**, in pipeline order: "
        "what EDGAR returned, what was derived from it, what was computed, and the "
        "latest state. Every table downloads at full precision."
    )

    left, right = st.columns(2)
    with left:
        show_all = st.checkbox("Show all periods", value=False, key="data_all_periods")
    with right:
        fact_filter = st.radio(
            "Facts", ["All", "Raw only", "Derived only"], horizontal=True,
            key="data_fact_filter",
            help="Raw is what EDGAR returned; derived is what the pipeline computed "
                 "from it. Columns are grouped so a concept sits next to its own "
                 "derivations.",
        )
    periods = 10**6 if show_all else DEFAULT_TABLE_PERIODS
    if not show_all:
        st.caption(f"Showing the most recent {DEFAULT_TABLE_PERIODS} periods.")

    facts_frame = load_frame(DATA_FILES["facts"])
    facts = pivot_ticker(facts_frame, ticker)
    if not facts.empty:
        keep = [c for c in facts.columns
                if fact_filter == "All"
                or (fact_filter == "Derived only") == fact_is_derived(ticker, c)]
        facts = facts[order_fact_columns(ticker, keep)]
    markers, legend = cadence_markers(facts_frame, ticker)
    render_data_section(
        "Raw & derived facts", facts, ticker, "facts", periods, DEFAULT_COPY_PERIODS,
        caption="Straight from EDGAR, plus what the pipeline built on top. "
                "`Revenue` next to `Revenue_TTM` is the TTM derivation, auditable.",
        column_markers=markers, marker_legend=legend,
    )

    metrics = pivot_ticker(load_frame(DATA_FILES["metrics"]), ticker)
    flags = metrics[[c for c in metrics.columns if is_quality_flag(c)]] if not metrics.empty else metrics
    if not metrics.empty:
        metrics = metrics[[c for c in metrics.columns if not is_quality_flag(c)]]
    render_data_section(
        "Calculated metrics", metrics, ticker, "metrics", periods, DEFAULT_COPY_PERIODS,
        caption="What the pipeline computes from the facts above. Quality flags are "
                "pulled out below rather than left as 0/1 columns between the ratios.",
    )

    st.subheader("Quality flags")
    st.caption("Distortion of data.")
    render_flag_section(flags, ticker, periods)

    render_data_section(
        "Valuation history", pivot_ticker(load_frame(DATA_FILES["valuation"]), ticker),
        ticker, "valuation", periods, DEFAULT_COPY_PERIODS,
        caption="Multiples over time, priced off the closing price nearest each period end.",
    )

    render_snapshot_section(load_frame(DATA_FILES["snapshot"]), ticker)



def render_freshness(meta: dict) -> None:
    """Run provenance, in the sidebar so it survives every tab and page switch."""
    run_date = meta.get("run_start", "")[:10]
    st.caption(
        f"**Data as of {run_date}**  \n"
        f"{meta['tickers_with_data']} of {meta['tickers_requested']} tickers produced data  \n"
        f"period `{meta['period']}`"
    )
    # only when non-empty: an empty list must render as nothing, not an empty label
    if meta.get("tickers_without_data"):
        st.caption(f"No data this run: {', '.join(meta['tickers_without_data'])}")


def render_encyclopedia() -> None:
    st.header("Metric encyclopedia")
    st.write(
        "Every metric this pipeline computes, with the formula it actually uses. "
        "These are read off the implementation, not from a textbook — where the two "
        "differ, what is written here is what the code does."
    )
    missing = config.undocumented_metrics()
    if missing:
        st.warning("Undocumented metrics: " + ", ".join(f"`{m}`" for m in missing))

    query = st.text_input("Filter", placeholder="e.g. margin, EBITDA, p_tbv").strip().lower()

    tabs = st.tabs([title for _, title, _ in CHART_SECTIONS])
    for tab, (chart, title, blurb) in zip(tabs, CHART_SECTIONS):
        with tab:
            st.caption(blurb)
            if chart == config.CHART_GROWTH:
                st.markdown(config.GROWTH_MECHANISM_NOTE)
                st.divider()
            elif chart == config.CHART_VALUATION:
                st.markdown(config.VALUATION_MECHANISM_NOTE)
                st.divider()

            # driven by the registry's chart field, so a new metric appears here
            # without anyone editing this function
            entries = [m for m in config.METRICS if m.chart == chart]
            if query:
                entries = [m for m in entries
                           if query in m.id.lower() or query in m.label.lower()
                           or query in (m.description or "").lower()
                           or query in (m.formula or "").lower()]
            if not entries:
                st.info("Nothing matches that filter in this section.")
                continue
            for metric in entries:
                st.markdown(f"#### {metric.label}")
                st.caption(f"`{metric.id}`")
                if metric.documented:
                    st.markdown(metric.description)
                    st.markdown(f"**How it is computed:** {metric.formula}")
                else:
                    st.warning("Not documented yet — see the report's gap list.")
                st.divider()


def render_coverage() -> None:
    st.header("Profile coverage")
    st.write(
        "Which metrics each business profile shows, and which it suppresses. A bank "
        "has no inventory and a REIT is not valued on earnings, so showing every "
        "metric for every company would mean showing numbers that do not mean "
        "anything. "
    )

    visibility = config.profile_visibility()
    profiles = sorted(visibility)
    by_id = {m.id: m for m in config.METRICS}

    profile = st.selectbox("Profile", profiles,
                           index=profiles.index("standard") if "standard" in profiles else 0)
    shown_total = sum(visibility[profile].values())
    st.caption(f"`{profile}` shows {shown_total} of {len(by_id)} registered metrics.")

    for chart, title, _ in CHART_SECTIONS:
        ids = [m.id for m in config.METRICS if m.chart == chart]
        shown = [i for i in ids if visibility[profile][i]]
        hidden = [i for i in ids if not visibility[profile][i]]
        st.subheader(f"{title} — {len(shown)} of {len(ids)}")
        if shown:
            st.markdown("**Shown:** " + ", ".join(f"`{by_id[i].label}`" for i in shown))
        if hidden:
            st.markdown("**Hidden for this profile:** "
                        + ", ".join(f"`{by_id[i].label}`" for i in hidden))

    st.divider()
    st.subheader("Full matrix")
    st.caption(
        f"{len(by_id)} metrics × {len(profiles)} profiles. The per-profile view above answers "
        "\"what does this company show\"; this answers \"who sees this metric\", which is the "
        "question the matrix is uniquely good at. Scrolls horizontally."
    )
    rows = []
    for metric in config.METRICS:
        row = {"metric": metric.label, "chart": metric.chart,
               "profiles": sum(visibility[p][metric.id] for p in profiles)}
        row.update({p: "✓" if visibility[p][metric.id] else "·" for p in profiles})
        rows.append(row)
    st.dataframe(pd.DataFrame(rows).set_index("metric"), width="stretch")


def split_sections(text: str) -> list[tuple[str, str]]:
    """Markdown split on level-2 headings, as (heading, body) in file order.

    Anything before the first `## ` comes back as ("", intro). Splitting rather than
    rendering the file in one block is what lets one named section be drawn
    differently; every other section is passed through untouched, so the file stays
    ordinary markdown and the page order is the file's order.
    """
    sections, heading, body = [], "", []
    for line in text.splitlines():
        if line.startswith("## "):
            if heading or any(l.strip() for l in body):
                sections.append((heading, "\n".join(body).strip()))
            heading, body = line[3:].strip(), []
        else:
            body.append(line)
    if heading or any(l.strip() for l in body):
        sections.append((heading, "\n".join(body).strip()))
    return sections


def render_about() -> None:
    st.header("About")

    text = strip_comments(read_content(ABOUT_FILE))
    if not text.strip():
        # A missing About file is a deployment mistake rather than a valid state, so
        # unlike the notice it says so -- but it still must not raise.
        st.warning(
            f"No About content found. Expected `{ABOUT_FILE}` in `{CONTENT_DIR}`. "
            "The page is text held in a file so it can be edited without changing "
            "code; create that file to fill this page in."
        )
        return

    for heading, body in split_sections(text):
        if heading:
            st.subheader(heading)
        if not body:
            continue
        if heading.strip().lower() in PROMINENT_ABOUT_SECTIONS:
            st.warning(body)
        else:
            st.markdown(body)


def dismiss_update_notice() -> None:
    """Set the dismissal flag. Runs as a button callback, which is the whole point.

    Streamlit executes widget callbacks **before** it re-runs the script body. So by
    the time render_update_notice() reads the flag on the rerun a click triggers, it
    is already True and the early return fires -- one click, one rerun, gone.

    The obvious alternative, `if st.button("Dismiss"): st.session_state[...] = True`,
    is the failure mode this avoids. That branch is only reached *after* the notice
    above it has already been drawn in that same run, so the flag is set for a run
    that never happens on its own: the notice stays on screen until some unrelated
    widget triggers the next rerun.
    """
    st.session_state[NOTICE_DISMISSED_KEY] = True


def render_update_notice() -> None:
    """A dismissible notice, right-aligned at the top of the page body.

    Ordering matters and is the reverse of how it reads: check the flag, then decide
    whether to draw anything at all, and never let the drawing code be responsible
    for clearing itself.

    "Top-right" is as literal as this app can be without custom CSS. Streamlit has no
    absolute positioning in its layout model, so this is a right-aligned container at
    the top of the page body -- it scrolls with the page rather than pinning to the
    viewport. st.toast was the other candidate and is wrong here: it dismisses itself
    after a few seconds, and the notice is supposed to persist until the reader
    dismisses it.
    """
    if st.session_state.get(NOTICE_DISMISSED_KEY, False):
        return

    text = strip_comments(read_content(NOTICE_FILE)).strip()
    if not text:
        # Missing file, empty file, and a file holding only its own instructions all
        # land here, and all three mean the same thing: draw nothing. Not an empty box.
        return

    with st.container(horizontal=True, horizontal_alignment="left"):
        with st.container(border=True, width="content"):
            st.markdown(text)
            st.button("Dismiss", key="dismiss_update_notice",
                      on_click=dismiss_update_notice)


def main() -> None:
    st.set_page_config(page_title="Kyhestlo", page_icon="▪", layout="wide")
    st.title("Kyhestlo")

    absent = missing_files()
    if absent:
        st.error(
            "Exported data is missing or out of date — the app reads what the pipeline "
            "wrote, it does not compute anything itself.\n\n"
            f"Missing in `{APP_DATA_DIR}`: {', '.join(f'`{n}`' for n in absent)}\n\n"
            "Run the pipeline first: "
            "`python -c \"from main import run_full_refresh; run_full_refresh()\"`"
        )
        # Both on purpose: st.stop() ends the run for the user, and the return
        # makes the branch explicit rather than resting on st.stop() raising --
        # which it does not do outside a script run, so without it this path
        # falls through into a FileNotFoundError when exercised headlessly.
        st.stop()
        return

    meta = load_meta()
    universe = load_frame("universe.parquet")

    # Above the introduction and below the title, so it is the first thing after the
    # page name on every view. After the missing-data guard on purpose: that branch
    # stops the run, and an announcement over an error page helps nobody.
    render_update_notice()

    st.caption(
        "This pipeline fetches SEC EDGAR 10k and 10q filings of more than 600 companies, extracts the XBRL "
        "facts, computes derived metrics, and links them to yfinance course data. "
        "This data stream is as pure as possible."
    )

    tickers = universe["ticker"].tolist()
    profiles = dict(zip(universe["ticker"], universe["profile"]))

    with st.sidebar:
        # Freshness first and always, so it survives every tab and page switch.
        render_freshness(meta)
        st.divider()
        view = st.radio("View", VIEWS, key="view")
        st.divider()
        if view == VIEW_ANALYSIS:
            st.header("Ticker")
            ticker = st.selectbox(
                "Ticker", tickers,
                format_func=lambda t: f"{t} — {profiles.get(t, '')}",
            )
            st.caption(f"Profile: `{profiles.get(ticker, '')}` — see **{VIEW_COVERAGE}** "
                       "for what this profile shows and hides.")
            as_of_enabled = st.checkbox("Use an as-of date for valuation", value=False)
            as_of = None
            if as_of_enabled:
                as_of = pd.Timestamp(st.date_input("As of", value=pd.Timestamp.today().date()))
                st.caption("The valuation window runs backwards from this date and stops there.")
        else:
            # The ticker controls are deliberately absent here: these pages describe
            # the pipeline, not a company, and a visible selector would imply otherwise.
            st.caption("Reference pages describe the pipeline itself and do not "
                       "depend on the selected ticker.")

    if view == VIEW_ENCYCLOPEDIA:
        render_encyclopedia()
        return
    if view == VIEW_COVERAGE:
        render_coverage()
        return
    if view == VIEW_ABOUT:
        render_about()
        return

    render_analysis(ticker, as_of, tickers, profiles)


def render_analysis(ticker: str, as_of, tickers: list[str], profiles: dict) -> None:
    # Data first: the app opens on what was extracted, and the charts follow.
    # The `with` blocks below fill named containers, so their order in the source
    # is independent of the order the tabs render in -- only this list decides.
    tab_data, tab_raw,  tab_growth, tab_fund, tab_val, tab_cmp = st.tabs(
        ["Data", "Raw Facts",  CHART_LABELS["growth"], CHART_LABELS["fundamentals"],
         CHART_LABELS["valuation"], "Comparison"]
    )

    with tab_data:
        render_data_tab(ticker)

    with tab_fund:
        ids, labels = metric_options("fundamentals", ticker)
        default = [i for i in ids if i in ("revenue_yoy_growth")]
        chosen = st.multiselect("Metrics", ids, default=default,
                                format_func=lambda i: labels[i], key="fund_metrics")
        years = st.slider("Window (years)", 1, 15, 15, key="fundamentals_years")
        render(
            figures.build_fundamentals(ticker, frame_for("fundamentals"),
                                       years=years, concepts=chosen, width=None),
            "Nothing selected, or no data for the selected metrics.",
        )

    with tab_growth:
        ids, labels = metric_options("growth", ticker)
        default = [i for i in ids if i in ("Revenueyoy_growth")]
        chosen = st.multiselect("Concepts", ids, default=default,
                                format_func=lambda i: labels[i], key="growth_metrics")
        years = st.slider("Window (years)", 1, 15, 15, key="growth_years")
        render(
            figures.build_growth(ticker, frame_for("growth"),
                                 years=years, concepts=chosen, width=None),
            "Nothing selected, or no growth data for this ticker.",
        )

    with tab_val:
        ids, labels = metric_options("valuation", ticker)
        default = [i for i in ids if i in ("pe_ratio")]
        chosen = st.multiselect("Multiples", ids, default=default,
                                format_func=lambda i: labels[i], key="val_metrics")
        years = st.slider("Window (years)", 1, 15, 5, key="valuation_years")

        # The control is built from the same frame the chart will be drawn from, and
        # the same window, so what it offers to hide is exactly what would be hidden.
        # It is absent entirely when there is nothing to hide: a toggle that appears on
        # a clean chart teaches the reader to ignore it.
        val_frame = frame_for("valuation")
        outliers = figures.outlier_report(
            figures._window_frame(val_frame, years, as_of), ticker, chosen)

        mask_outliers = False
        if outliers:
            mask_outliers = st.toggle(
                "Hide extreme values", key="val_mask_outliers",
                help=(f"Hides points more than {figures.OUTLIER_MEDIAN_RATIO:g}x the "
                      f"panel's own median. Applies per panel, only where such points "
                      f"exist, and only to what is drawn — the values stay in the data "
                      f"tab and the exports."),
            )

        render(
            figures.build_valuation(ticker, val_frame, years=years,
                                    concepts=chosen, as_of=as_of,
                                    snapshot=load_frame(DATA_FILES["snapshot"]),
                                    width=None, mask_outliers=mask_outliers),
            "Nothing selected, or no valuation data for this ticker.",
        )

        # An empty panel still renders as an axis grid, because build_valuation
        # returns a figure as long as any selected concept has data. Without this
        # the reader sees a chart frame with no line and no reason for it, next to
        # a working current multiple at the top of the page.
        blank = empty_valuation_panels(val_frame, ticker, chosen, years, as_of)
        if blank:
            names = ", ".join(labels.get(c, c) for c in blank)
            cause = (
                " No share-count history is available for this ticker in the SEC's "
                "structured data, and every per-share multiple needs one as its "
                "denominator."
                if share_history_absent(ticker) else ""
            )
            # Deliberately neutral about the cause. 170 of the 500 exported tickers
            # have at least one empty panel and 97 of those are `dividend_yield` on a
            # company that pays no dividend -- a true statement about the business,
            # not a defect. The only claim made unconditionally is the one that always
            # holds: the value is absent, and it was not filtered away.
            st.info(
                f"**No data for: {names}** — nothing to draw in this window.{cause} "
                "The current multiple above still works because it is computed from "
                "market data, which has no filed-history equivalent. "
                "**Nothing was hidden or filtered** — the value is absent from the "
                "source data, and the empty column is still listed in the **Data** tab."
            )

        if outliers:
            summary = ", ".join(
                f"{labels.get(c, c)} ({len(rows)} point{'s' if len(rows) > 1 else ''})"
                for c, rows in outliers.items()
            )
            if mask_outliers:
                # Stated at the point of the change, not only in the toggle's help:
                # a reader watching points disappear will otherwise assume the average
                # moved with them, which is the one thing that did not happen.
                st.caption(f"**Hidden:** {summary}. "
                           f"**The mean lines are unchanged** — they are still computed "
                           f"over the full series, including the hidden points.")
            else:
                st.caption(f"Extreme values present in: {summary}.")

            # A silent filter would be the wrong thing in a tool whose argument is
            # auditability, so every hidden number is one click away, with the ratio
            # that got it hidden.
            with st.expander(f"Show the {sum(len(r) for r in outliers.values())} "
                             f"extreme value(s)"):
                for c, rows in outliers.items():
                    series = figures._window_frame(val_frame, years, as_of)
                    series = series[(series["ticker"] == ticker)
                                    & (series["concept"] == c)]["value"].dropna()
                    median = series.median()
                    table = rows.rename(columns={"end": "Period", "value": "Value"}).copy()
                    table["x median"] = (table["Value"] / median).round(1)
                    st.markdown(f"**{labels.get(c, c)}** — median {median:,.2f}")
                    st.dataframe(table, hide_index=True, width="stretch")

        st.caption(
            "The green circle is the current multiple — today's price against the "
            "latest available fundamentals — not a filed period. It is excluded from "
            "the mean line, and hidden when the as-of date predates it."
        )

    with tab_cmp:
        st.write("One metric, one line per ticker.")
        all_pairs = [(c, f"{CHART_LABELS[c]}: ") for c in ("fundamentals", "growth", "valuation")]
        options, option_labels = [], {}
        for chart, prefix in all_pairs:
            for i, label in config.get_plottable_metrics(chart):
                options.append(i)
                option_labels[i] = prefix + label
        concept = st.selectbox("Metric", options,
                               format_func=lambda i: option_labels[i], key="cmp_metric")
        picked = st.multiselect(
            "Tickers", tickers,
            default=tickers[:min(figures.SUGGESTED_MAX_COMPARISON_TICKERS, len(tickers))],
            format_func=lambda t: f"{t} — {profiles.get(t, '')}", key="cmp_tickers",
        )
        years = st.slider("Window (years)", 1, 15, 15, key="comparison_years")
        st.caption(
            f"At least {figures.MIN_COMPARISON_TICKERS} tickers; "
            f"{figures.SUGGESTED_MAX_COMPARISON_TICKERS} stay comfortably readable."
        )
        frame, source = frame_for_concept(concept)
        if frame is None:
            st.info("That metric is not plottable.")
        else:
            # Same shape as the valuation tab, and the same rule underneath -- so a
            # reader moving between the two tabs does not have to learn a second
            # meaning of "outlier". The report is keyed by ticker here rather than by
            # concept, because this chart holds one concept and several lines.
            cmp_outliers = figures.comparison_outlier_report(
                picked, concept, frame, years=years, as_of=as_of)

            cmp_mask = False
            if cmp_outliers:
                cmp_mask = st.toggle(
                    "Hide extreme values", key="cmp_mask_outliers",
                    help=(f"Hides points more than {figures.OUTLIER_MEDIAN_RATIO:g}x "
                          f"**that line's own** median. Each ticker is judged against "
                          f"itself, so a company simply trading at a higher multiple "
                          f"than its peers loses nothing."),
                )

            fig, excluded = figures.build_ticker_comparison(
                picked, concept, frame, as_of=as_of, years=years, width=None,
                mask_outliers=cmp_mask)
            # figures.py reports the fact ("No Data"); the wording is the app's
            # job, and it has to match the valuation tab's notice. Two different
            # explanations of the same absence in two tabs is the failure to avoid.
            for dropped, reason in excluded:
                if reason == "No Data":
                    detail = ("no values in this window"
                              + (" — no share-count history is available for it"
                                 if share_history_absent(dropped) else ""))
                else:
                    detail = reason
                st.warning(f"**{dropped}** not shown — {detail}.")
            render(fig, "Pick at least two tickers that can show this metric.")

            if cmp_outliers:
                summary = ", ".join(
                    f"{t} ({len(rows)} point{'s' if len(rows) > 1 else ''})"
                    for t, rows in cmp_outliers.items()
                )
                if cmp_mask:
                    # This chart draws no mean lines, so the sentence the valuation tab
                    # needs -- "the average did not move" -- has nothing to refer to.
                    # Saying what *did* stay instead: every line keeps its own scale.
                    st.caption(f"**Hidden:** {summary}. Each line was judged against its "
                               f"own median, so the remaining points are unchanged and "
                               f"still on their original scale.")
                else:
                    st.caption(f"Extreme values present in: {summary}.")

                with st.expander(f"Show the {sum(len(r) for r in cmp_outliers.values())} "
                                 f"extreme value(s)"):
                    windowed = figures._window_frame(frame, years, as_of)
                    for t, rows in cmp_outliers.items():
                        col = rows.columns[-1]
                        series = windowed[(windowed["ticker"] == t)
                                          & (windowed["concept"] == concept)][col].dropna()
                        median = series.median()
                        table = rows.rename(columns={"end": "Period",
                                                     col: "Value"}).copy()
                        table["x median"] = (table["Value"] / median).round(1)
                        st.markdown(f"**{t}** — own median {median:,.2f}")
                        st.dataframe(table, hide_index=True, width="stretch")
    with tab_raw:
            st.write("Concepts as filed, before any metric is computed.")
            facts_full = load_frame(DATA_FILES["facts"])

            show_derived = st.checkbox(
                "Include derived concepts (_TTM, _QUARTERLY, …)",
                value=False, key="raw_derived",
            )
            options = figures.available_raw_concepts(ticker, facts_full, show_derived)
            default = [c for c in ("Revenue", "NetIncomeLoss", "Assets", "StockholdersEquity")
                    if c in options]

            chosen = st.multiselect("Concepts", options, default=default, key="raw_concepts")
            years = st.slider("Window (years)", 1, 15, 15, key="raw_years")
            render(
                figures.build_raw_facts(ticker, facts_full, concepts=chosen,
                                        include_derived=show_derived, width=None, years=years),
                "Nothing selected, or no raw facts for this ticker.",
            )

if __name__ == "__main__":
    main()
