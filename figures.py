import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import (
    is_hidden, FUNDAMENTALS_TO_PLOT, QUARTERLY_COUNTERPART, GROWTH_PANELS,
    VALUATIONS_TO_PLOT, HARMONIC_MEAN_CONCEPTS, TICKER_PROFILES, DEFAULT_PROFILE,
)
from metrics import harmonic_mean

# Colors pinned so every subplot looks like the matplotlib version did
# (each mpl axes restarted its color cycle; one Plotly figure would not).
_PRIMARY_COLOR = "#1f77b4"
_SECONDARY_COLOR = "#ff7f0e"
_PERCENT_TICKFORMAT = ".1~%"
_KNOWN_OUTPUT_EXTENSIONS = {".png", ".html", ".json"}

# One line per ticker; colors assigned by position in the requested list so a
# ticker keeps its color even when another one drops out of the chart.
# Indexing wraps, so more tickers than colors repeats rather than erroring --
# which is what SUGGESTED_MAX_COMPARISON_TICKERS exists to keep rare.
_COMPARISON_COLORS = [
    "#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e",
    "#8c564b", "#e377c2", "#17becf", "#bcbd22", "#7f7f7f",
]
# Advisory only -- a readability limit belongs in the UI that picks the tickers
# (e.g. st.multiselect(max_selections=...)), not in the rendering layer, where a
# hard refusal would turn a UI mistake into a missing chart.
SUGGESTED_MAX_COMPARISON_TICKERS = 3
# Enforced: one ticker is not a comparison. A category check, not a readability guess.
MIN_COMPARISON_TICKERS = 2


def _output_paths(output_path: str) -> tuple[str, str]:
    stem, ext = os.path.splitext(output_path)
    if ext.lower() not in _KNOWN_OUTPUT_EXTENSIONS:
        stem = output_path
    return stem + ".html", stem + ".json"


def _write_figure(fig: go.Figure, output_path: str) -> None:
    html_path, json_path = _output_paths(output_path)
    fig.write_html(html_path, include_plotlyjs=True, full_html=True)
    fig.write_json(json_path)


def _make_grid(n: int, max_cols: int = 3):
    # n == 0 is unreachable: every builder returns early on an empty panel list.
    # Kept as a defensive no-op so a future caller cannot get a ZeroDivisionError
    # out of `min(max_cols, 0)` -> cols=0.
    if n == 0:
        return 1, 1
    cols = min(max_cols, n)
    rows = -(-n // cols)
    return rows, cols


def _select_concepts(ticker: str, catalogue: list, requested: list[str] | None) -> list:
    """Panels to draw: config order, visibility-filtered, optionally narrowed.

    Every catalogue entry is a tuple whose first element is the concept name
    (FUNDAMENTALS_TO_PLOT, VALUATIONS_TO_PLOT, GROWTH_PANELS all share that shape).

    `is_hidden` is applied to the catalogue first and the caller's list only
    narrows what survives, so an explicit request can never surface a concept the
    ticker's profile hides. Requested entries that are unknown or hidden are
    dropped with a printed note rather than refused: a UI hands one selection to
    several tickers, and a concept that is fine for one is routinely hidden for
    another -- normal operation, not a caller error.

    Order always follows `catalogue`, never the caller's list, so a chart's panel
    order is stable no matter what order the UI happens to send.
    """
    visible = [c for c in catalogue if not is_hidden(ticker, c[0])]
    if requested is None:
        return visible

    wanted = set(requested)
    selected = [c for c in visible if c[0] in wanted]
    dropped = sorted(wanted - {c[0] for c in selected})
    if dropped:
        known = {c[0] for c in catalogue}
        detail = ", ".join(
            f"{name} ({'für dieses Profil ausgeblendet' if name in known else 'unbekannt'})"
            for name in dropped
        )
        print(f"[figures] {ticker}: angeforderte Konzepte nicht darstellbar -- {detail}")
    return selected


class _Keep:
    """Sentinel: 'caller said nothing, use this chart's historical value'.

    None cannot serve as that default because None is itself meaningful here --
    it means 'leave the key out of the layout entirely'.
    """
    def __repr__(self):
        return "<unchanged>"


KEEP = _Keep()


def _size(width, height, default_width, default_height) -> dict:
    """The width/height part of a layout, for splatting into update_layout().

    KEEP -> the chart's historical value, None -> omit the key entirely (what a
    responsive frontend needs; Plotly only honours use_container_width when the
    figure does not pin a width), anything else -> that value.

    Returned as a dict to splat rather than merged into a layout dict, so each
    caller keeps its original keyword order and the serialised JSON stays
    byte-identical to what it produced before these parameters existed.
    """
    resolved_width = default_width if width is KEEP else width
    resolved_height = default_height if height is KEEP else height
    sized = {}
    if resolved_width is not None:
        sized["width"] = resolved_width
    if resolved_height is not None:
        sized["height"] = resolved_height
    return sized


def _window_frame(frame: pd.DataFrame, years: int, as_of: pd.Timestamp | None) -> pd.DataFrame:
    """The trailing `years` window ending at `as_of` (default: today).

    Shared by build_valuation and build_ticker_comparison so the two cannot
    drift. With an explicit `as_of` the window is bounded above as well: the
    caller asked for "the last `years` years as of that date", and leaving the
    upper bound open would instead answer "everything since that date" and show
    data the chosen date could not have known.
    """
    anchor = pd.Timestamp.today() if as_of is None else pd.Timestamp(as_of)
    windowed = frame[frame["end"] >= anchor - pd.DateOffset(years=years)]
    if as_of is not None:
        windowed = windowed[windowed["end"] <= anchor]
    return windowed


def _make_subplot_figure(rows: int, cols: int, titles: list[str]) -> go.Figure:
    n = len(titles)
    specs = [
        [{} if r * cols + c < n else None for c in range(cols)]
        for r in range(rows)
    ]
    return make_subplots(rows=rows, cols=cols, specs=specs, subplot_titles=titles)


def _annotate_no_data(
    fig: go.Figure,
    row: int,
    col: int,
) -> None:

    fig.add_annotation(
        text="Keine Daten",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(
            color="red",
            size=14,
        ),
        xanchor="center",
        yanchor="middle",
        row=row,
        col=col,
    )

    fig.update_xaxes(
        showticklabels=False,
        showgrid=False,
        zeroline=False,
        row=row,
        col=col,
    )

    fig.update_yaxes(
        showticklabels=False,
        showgrid=False,
        zeroline=False,
        row=row,
        col=col,
    )


def _style_axes(fig: go.Figure, row: int, col: int, ylabel: str, percent: bool) -> None:
    fig.update_xaxes(dtick="M24", tickformat="%Y", row=row, col=col)
    fig.update_yaxes(
        title_text=ylabel, title_font_size=11,
        tickformat=_PERCENT_TICKFORMAT if percent else None,
        row=row, col=col,
    )


def plot_metric(
    fig: go.Figure,
    row: int,
    col: int,
    metrics_long: pd.DataFrame,
    ticker: str,
    concept: str,
    ylabel: str,
    ref_line=None,
    percent: bool = False,
    show_mean: bool = False,
    harmonic: bool = False,
) -> None:

    filtered = metrics_long[
        (metrics_long["ticker"] == ticker)
        & (metrics_long["concept"] == concept)
    ].sort_values("end")

    valid_values = filtered.dropna(subset=["end", "value"])

    # Erst prüfen, ob Daten vorhanden sind
    if valid_values.empty:
        _annotate_no_data(fig, row, col)
        return

    # Erst danach den Plot hinzufügen
    fig.add_trace(
        go.Scatter(
            x=filtered["end"],
            y=filtered["value"],
            mode="lines + markers",
            name=concept,
            line=dict(color=_PRIMARY_COLOR),
            connectgaps=True,
            hovertemplate=("Date: %{x|%d.%m.%Y}""<br>Value: %{y}""<extra></extra>")
        ),
        row=row,
        col=col,

    )

    _style_axes(fig, row, col, ylabel, percent)

    if show_mean:
        mean_value = (
            harmonic_mean(filtered["value"])
            if harmonic
            else filtered["value"].mean()
        )

        if np.isfinite(mean_value):
            prefix = "Ø (harm.)" if harmonic else "Ø"

            label = (
                f"{prefix} {mean_value:.2%}"
                if percent
                else f"{prefix} {mean_value:.1f}"
            )

            fig.add_hline(
                y=mean_value,
                line_color="red",
                line_width=1,
                row=row,
                col=col,
            )

            fig.add_annotation(
                text=label,
                x=0.02,
                y=0.98,
                xref="x domain",
                yref="y domain",
                xanchor="left",
                yanchor="top",
                showarrow=False,
                font=dict(color="red", size=10),
                row=row,
                col=col,
            )

    if ref_line is not None:
        fig.add_hline(
            y=ref_line,
            line_color="red",
            line_width=1,
            row=row,
            col=col,
        )

def plot_metric_dual(
    fig: go.Figure,
    row: int,
    col: int,
    metrics_long: pd.DataFrame,
    ticker: str,
    concept: str,
    quarterly_concept: str,
    ylabel: str,
    ref_line=None,
    percent: bool = False,
) -> None:

    # TTM-Daten holen
    ttm = metrics_long[
        (metrics_long["ticker"] == ticker)
        & (metrics_long["concept"] == concept)
    ].sort_values("end")

    # Quartalsdaten holen
    quarterly = metrics_long[
        (metrics_long["ticker"] == ticker)
        & (metrics_long["concept"] == quarterly_concept)
    ].sort_values("end")

    # Wenn keine echten TTM-Werte existieren:
    # komplettes Panel leer lassen und "keine Daten" anzeigen
    ttm_valid = ttm.dropna(subset=["end", "value"])
    if ttm_valid.empty:
        _annotate_no_data(fig, row, col)
        return

    # TTM immer anzeigen, wenn vorhanden
    fig.add_trace(
        go.Scatter(
            x=ttm["end"],
            y=ttm["value"],
            mode="lines + markers",
            name=f"{concept} · TTM",
            line=dict(
                color=_PRIMARY_COLOR,
                width=1.5,
            ),
            connectgaps=True,
            hovertemplate=("Date: %{x|%d.%m.%Y}""<br>Value: %{y}""<extra></extra>")
        ),
        row=row,
        col=col,

    )

    # Quartal nur anzeigen, wenn Quartalsdaten vorhanden sind
    quarterly_valid = quarterly.dropna(subset=["end", "value"])
    if not quarterly_valid.empty:
        fig.add_trace(
            go.Scatter(
                x=quarterly["end"],
                y=quarterly["value"],
                mode="lines",
                name=f"{concept} · Quartal",
                line=dict(
                    color=_SECONDARY_COLOR,
                    width=0.8,
                ),
                opacity=0.6,
                hovertemplate=("Date: %{x|%d.%m.%Y}""<br>Value: %{y}""<extra></extra>")
            ),
            row=row,
            col=col,

        )

    _style_axes(
        fig,
        row,
        col,
        ylabel,
        percent,
    )

    if ref_line is not None:
        fig.add_hline(
            y=ref_line,
            line_color="red",
            line_width=1,
            row=row,
            col=col,
        )

def build_fundamentals(
    ticker: str,
    metrics_long: pd.DataFrame,
    concepts: list[str] | None = None,
    width: int | None = KEEP,
    height: int | None = KEEP,
) -> go.Figure | None:
    """Build the fundamentals grid. None when there is nothing to draw.

    `concepts` narrows the panel set (None = everything the config shows).
    `width`/`height` keep the historical 500*cols / 330*rows unless given; pass
    width=None for a figure with no width in its layout, which is what a
    responsive frontend needs.
    """

    concepts_to_plot = _select_concepts(ticker, FUNDAMENTALS_TO_PLOT, concepts)

    if not concepts_to_plot:
        print(f"[build_fundamentals] {ticker}: no visible panels, nothing to build.")
        return None

    rows, cols = _make_grid(len(concepts_to_plot))
    fig = _make_subplot_figure(rows, cols, [c[0] for c in concepts_to_plot])

    # 5th tuple element is the legacy symlog flag; unused by any metric, not rendered.
    for idx, (concept, ylabel, ref_line, percent, _symlog) in enumerate(concepts_to_plot):
        r, c = idx // cols + 1, idx % cols + 1
        quarterly_concept = QUARTERLY_COUNTERPART.get(concept)
        if quarterly_concept and not is_hidden(ticker, quarterly_concept):
            plot_metric_dual(fig, r, c, metrics_long, ticker, concept, quarterly_concept,
                             ylabel, ref_line, percent)
        else:
            plot_metric(fig, r, c, metrics_long, ticker, concept, ylabel, ref_line, percent)

    fig.update_layout(
        title_text=f"Fundamentals {ticker}",
        **_size(width, height, 500 * cols, 330 * rows),
        legend=dict(font=dict(size=9)),
    )
    return fig


def plot_fundamentals(
    ticker: str,
    metrics_long: pd.DataFrame,
    output_path: str,
    concepts: list[str] | None = None,
) -> None:
    """File-writing wrapper around build_fundamentals."""
    fig = build_fundamentals(ticker, metrics_long, concepts)
    if fig is None:
        return
    _write_figure(fig, output_path)


def build_growth(
    ticker: str,
    facts: pd.DataFrame,
    growth_column: str = "yoy_growth",
    concepts: list[str] | None = None,
    width: int | None = KEEP,
    height: int | None = KEEP,
) -> go.Figure | None:
    """Build the YoY growth row. None when there is nothing to draw."""

    if growth_column not in facts.columns:
        print(f"[build_growth] {ticker}: column '{growth_column}' missing, nothing to build.")
        return None

    panels = _select_concepts(ticker, GROWTH_PANELS, concepts)

    if not panels:
        print(f"[build_growth] {ticker}: no visible panels, nothing to build.")
        return None

    fig = _make_subplot_figure(1, len(panels), [c for c, _ in panels])

    for idx, (concept, label) in enumerate(panels):
        col = idx + 1
        series = facts[
            (facts["ticker"] == ticker) & (facts["concept"] == concept)
        ].sort_values("end")

        series_values = series.dropna(subset=[growth_column])

        if series_values.empty:
            _annotate_no_data(fig, 1, col)
            continue

        fig.add_trace(
            go.Scatter(
                x=series["end"], y=series[growth_column], mode="lines + markers",
                name=concept, line=dict(color=_PRIMARY_COLOR), connectgaps=True, hovertemplate=("Date: %{x|%d.%m.%Y}""<br>Value: %{y}""<extra></extra>")
            ),
            row=1, col=col,
        )
        _style_axes(fig, 1, col, label, percent=True)
        fig.add_hline(y=0, line_color="red", line_width=1, row=1, col=col)

    fig.update_layout(
        title_text=f"Growth (YoY) {ticker}",
        **_size(width, height, 500 * len(panels), 360),
        legend=dict(font=dict(size=9)),
    )
    return fig


def plot_growth(
    ticker: str,
    facts: pd.DataFrame,
    output_path: str,
    growth_column: str = "yoy_growth",
    concepts: list[str] | None = None,
) -> None:
    """File-writing wrapper around build_growth."""
    fig = build_growth(ticker, facts, growth_column, concepts)
    if fig is None:
        return
    _write_figure(fig, output_path)


def build_valuation(
    ticker: str,
    valuation_history: pd.DataFrame,
    years: int = 5,
    concepts: list[str] | None = None,
    as_of: pd.Timestamp | None = None,
    width: int | None = KEEP,
    height: int | None = KEEP,
) -> go.Figure | None:
    """Build the valuation grid over the trailing `years` window. None when empty.

    `as_of` anchors that window: None means today (unchanged), a date means the
    window runs backwards from that date and is bounded above by it.
    """
    filtered = _window_frame(valuation_history, years, as_of)

    concepts_to_plot = _select_concepts(ticker, VALUATIONS_TO_PLOT, concepts)

    if not concepts_to_plot:
        print(f"[build_valuation] {ticker}: no visible panels, nothing to build.")
        return None

    rows, cols = _make_grid(len(concepts_to_plot))
    fig = _make_subplot_figure(rows, cols, [c[0] for c in concepts_to_plot])

    for idx, (concept, ylabel, ref_line, percent) in enumerate(concepts_to_plot):
        r, c = idx // cols + 1, idx % cols + 1
        plot_metric(fig, r, c, filtered, ticker, concept, ylabel, ref_line, percent,
                    show_mean=True, harmonic=concept in HARMONIC_MEAN_CONCEPTS)

    fig.update_layout(
        title_text=f"Valuation Data {ticker}",
        **_size(width, height, 500 * cols, 400 * rows),
        legend=dict(font=dict(size=9)),
    )
    return fig


def plot_valuation(
    ticker: str,
    valuation_history: pd.DataFrame,
    output_path: str,
    years: int = 5,
    concepts: list[str] | None = None,
    as_of: pd.Timestamp | None = None,
) -> None:
    """File-writing wrapper around build_valuation."""
    fig = build_valuation(ticker, valuation_history, years, concepts, as_of)
    if fig is None:
        return
    _write_figure(fig, output_path)


def _concept_plot_spec(concept: str):
    """Chart furniture for a concept, read off the same config tuples the
    single-ticker charts use, so a comparison chart cannot drift from them.

    Returns (source, ylabel, ref_line, percent, is_valuation, value_column) or
    None if the concept is not something this project plots.
    """
    for c in VALUATIONS_TO_PLOT:
        if c[0] == concept:
            # plot_valuation applies the rolling year cutoff; comparisons must too
            return "valuation", c[1], c[2], c[3], True, "value"
    for c in FUNDAMENTALS_TO_PLOT:
        if c[0] == concept:
            return "fundamentals", c[1], c[2], c[3], False, "value"
    for c, label in GROWTH_PANELS:
        if c == concept:
            # plot_growth draws facts[growth_column] as a percentage against a 0 line
            return "growth", label, 0, True, False, "yoy_growth"
    return None


def concept_source(concept: str) -> str | None:
    """Which dataframe a concept lives in: 'fundamentals' (metrics_long),
    'valuation' (valuation_history), 'growth' (facts), or None if unplottable.

    Lets callers route a concept to the right frame without duplicating the
    config lookup.
    """
    spec = _concept_plot_spec(concept)
    return spec[0] if spec else None


def build_ticker_comparison(
    tickers: list[str],
    concept: str,
    data: pd.DataFrame,
    years: int = 5,
    value_column: str | None = None,
    as_of: pd.Timestamp | None = None,
    width: int | None = KEEP,
    height: int | None = KEEP,
) -> tuple[go.Figure | None, list[tuple[str, str]]]:
    """One metric, one line per ticker, for comparison. Returns (fig, excluded).

    No file I/O -- for a web layer that wants the figure object. `plot_ticker_comparison`
    is the thin file-writing wrapper around this.

    A ticker is dropped when `is_hidden` hides the metric for its profile -- the
    profile system already decides per metric where a number is meaningful, so a
    comparison must not go behind its back. Drops are never silent: they are
    returned as `excluded` [(ticker, reason), ...], stamped onto `fig.layout.meta`
    so they survive JSON serialisation, printed, and written onto the chart.

    `fig` is None when there is nothing to draw. `excluded` then tells the two
    cases apart: non-empty means every requested ticker was dropped (a data
    outcome), empty means the request itself was rejected (unknown concept, or
    fewer than MIN_COMPARISON_TICKERS tickers).

    No per-ticker mean lines (n of them would bury the data); the metric-level
    reference line stays because it does not depend on the ticker. Per-ticker
    show/hide is left to Plotly's legend, which does it natively.
    """
    spec = _concept_plot_spec(concept)
    if spec is None:
        print(f"[ticker_comparison] '{concept}' is not a plotted concept, nothing to build.")
        return None, []
    _source, ylabel, ref_line, percent, is_valuation, default_column = spec
    column = value_column or default_column

    requested = list(dict.fromkeys(tickers))
    if len(requested) < MIN_COMPARISON_TICKERS:
        print(f"[ticker_comparison] {concept}: {len(requested)} distinct ticker(s) "
              f"requested, need at least {MIN_COMPARISON_TICKERS}, nothing to build.")
        return None, []

    frame = _window_frame(data, years, as_of) if is_valuation else data

    plotted, excluded = [], []
    for position, ticker in enumerate(requested):
        if is_hidden(ticker, concept):
            profile = TICKER_PROFILES.get(ticker, DEFAULT_PROFILE)
            excluded.append((ticker, f"für Profil '{profile}' ausgeblendet"))
            continue
        series = frame[
            (frame["ticker"] == ticker) & (frame["concept"] == concept)
        ].sort_values("end")
        if series.dropna(subset=["end", column]).empty:
            excluded.append((ticker, "keine Daten"))
            continue
        plotted.append((position, ticker, series))

    excluded_text = [f"{ticker} ({reason})" for ticker, reason in excluded]
    if excluded:
        print(f"[ticker_comparison] {concept}: nicht dargestellt -- "
              f"{', '.join(excluded_text)}")

    if not plotted:
        print(f"[ticker_comparison] {concept}: no ticker left to plot.")
        return None, excluded

    fig = _make_subplot_figure(1, 1, [concept])

    for position, ticker, series in plotted:
        fig.add_trace(
            go.Scatter(
                x=series["end"],
                y=series[column],
                mode="lines + markers",
                name=ticker,
                line=dict(color=_COMPARISON_COLORS[position % len(_COMPARISON_COLORS)]),
                connectgaps=True,
                hovertemplate="%{fullData.name}: %{y}<extra></extra>",
            ),
            row=1,
            col=1,
        )

    _style_axes(fig, 1, 1, ylabel, percent)

    if ref_line is not None:
        fig.add_hline(
            y=ref_line,
            line_color="red",
            line_width=1,
            row=1,
            col=1,
        )

    if excluded:
        fig.add_annotation(
            text="Nicht dargestellt: " + ", ".join(excluded_text),
            x=0.0,
            xref="paper",
            xanchor="left",
            y=-0.16,
            yref="paper",
            yanchor="top",
            showarrow=False,
            font=dict(color="red", size=10),
        )

    fig.update_layout(
        title_text=f"{ylabel} — {', '.join(t for _, t, _ in plotted)}",
        **_size(width, height, 900, 520),
        legend=dict(font=dict(size=10)),
        hovermode="x unified",
        margin=dict(b=110 if excluded else 80),
        # travels with the figure through to_json/from_json, so a consumer that
        # only receives the serialised figure still learns what was dropped
        meta={
            "concept": concept,
            "tickers": [ticker for _, ticker, _ in plotted],
            "excluded": [{"ticker": t, "reason": r} for t, r in excluded],
        },
    )
    return fig, excluded


def plot_ticker_comparison(
    tickers: list[str],
    concept: str,
    data: pd.DataFrame,
    output_path: str,
    years: int = 5,
    value_column: str | None = None,
    as_of: pd.Timestamp | None = None,
) -> None:
    """File-writing wrapper around build_ticker_comparison.

    Nothing to draw -> neither file is written, preserving the both-files-or-neither
    guarantee the other plot functions give.
    """
    fig, _excluded = build_ticker_comparison(tickers, concept, data, years, value_column, as_of)
    if fig is None:
        return
    _write_figure(fig, output_path)
