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
CHART_LABELS = {
    "fundamentals": "Fundamentals",
    "growth": "Growth (YoY)",
    "valuation": "Valuation",
}


# --- loading -----------------------------------------------------------------
# Dataframes are cached, figures never are: building a figure is cheap, and a
# cached figure would silently outlive the widget state that produced it.

def missing_files() -> list[str]:
    needed = list(FRAME_FILES.values()) + ["universe.parquet", "meta.json"]
    return [n for n in needed if not os.path.exists(os.path.join(APP_DATA_DIR, n))]


@st.cache_data(show_spinner=False)
def load_frame(name: str) -> pd.DataFrame:
    return pd.read_parquet(os.path.join(APP_DATA_DIR, name))


@st.cache_data(show_spinner=False)
def load_meta() -> dict:
    with open(os.path.join(APP_DATA_DIR, "meta.json"), encoding="utf-8") as fh:
        return json.load(fh)


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


def render(fig, empty_message: str) -> None:
    if fig is None:
        st.info(empty_message)
        return
    # width="stretch" is the current spelling of use_container_width=True, which
    # Streamlit deprecated with a removal date of 2025-12-31 and now warns about
    # on every call. The builders are passed width=None so the figure does not
    # pin a width and fight the container.
    st.plotly_chart(fig, width="stretch")


# --- page --------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="Stock Valuator", layout="wide")
    st.title("Stock Valuator")

    absent = missing_files()
    if absent:
        st.error(
            "No exported data found — the app reads what the pipeline wrote, it does "
            "not compute anything itself.\n\n"
            f"Missing in `{APP_DATA_DIR}`: {', '.join(f'`{n}`' for n in absent)}\n\n"
            "Run the pipeline first: "
            "`python -c \"from main import run_full_refresh; run_full_refresh()\"`"
        )
        st.stop()

    meta = load_meta()
    universe = load_frame("universe.parquet")

    st.caption(
        f"Data exported {meta['exported_at']} · run started {meta['run_start']} · "
        f"{meta['tickers_with_data']} of {meta['tickers_requested']} tickers produced data · "
        f"period `{meta['period']}`"
    )
    if meta.get("tickers_without_data"):
        st.caption(f"No data in this run: {', '.join(meta['tickers_without_data'])}")

    tickers = universe["ticker"].tolist()
    profiles = dict(zip(universe["ticker"], universe["profile"]))

    with st.sidebar:
        st.header("Ticker")
        ticker = st.selectbox(
            "Ticker", tickers,
            format_func=lambda t: f"{t} — {profiles.get(t, '')}",
        )
        st.caption(f"Profile: `{profiles.get(ticker, '')}`")
        as_of_enabled = st.checkbox("Use an as-of date for valuation", value=False)
        as_of = None
        if as_of_enabled:
            as_of = pd.Timestamp(st.date_input("As of", value=pd.Timestamp.today().date()))
            st.caption("The valuation window runs backwards from this date and stops there.")

    tab_fund, tab_growth, tab_val, tab_cmp = st.tabs(
        [CHART_LABELS["fundamentals"], CHART_LABELS["growth"],
         CHART_LABELS["valuation"], "Comparison"]
    )

    with tab_fund:
        ids, labels = metric_options("fundamentals", ticker)
        chosen = st.multiselect("Metrics", ids, default=ids,
                                format_func=lambda i: labels[i], key="fund_metrics")
        render(
            figures.build_fundamentals(ticker, frame_for("fundamentals"),
                                       concepts=chosen, width=None),
            "Nothing selected, or no data for the selected metrics.",
        )

    with tab_growth:
        ids, labels = metric_options("growth", ticker)
        chosen = st.multiselect("Concepts", ids, default=ids,
                                format_func=lambda i: labels[i], key="growth_metrics")
        render(
            figures.build_growth(ticker, frame_for("growth"),
                                 concepts=chosen, width=None),
            "Nothing selected, or no growth data for this ticker.",
        )

    with tab_val:
        ids, labels = metric_options("valuation", ticker)
        chosen = st.multiselect("Multiples", ids, default=ids,
                                format_func=lambda i: labels[i], key="val_metrics")
        years = st.slider("Window (years)", 1, 15, 5)
        render(
            figures.build_valuation(ticker, frame_for("valuation"), years=years,
                                    concepts=chosen, as_of=as_of, width=None),
            "Nothing selected, or no valuation data for this ticker.",
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
        st.caption(
            f"At least {figures.MIN_COMPARISON_TICKERS} tickers; "
            f"{figures.SUGGESTED_MAX_COMPARISON_TICKERS} stay comfortably readable."
        )
        frame, source = frame_for_concept(concept)
        if frame is None:
            st.info("That metric is not plottable.")
        else:
            fig, excluded = figures.build_ticker_comparison(
                picked, concept, frame, as_of=as_of, width=None)
            for dropped, reason in excluded:
                st.warning(f"**{dropped}** not shown — {reason}")
            render(fig, "Pick at least two tickers that can show this metric.")


if __name__ == "__main__":
    main()
