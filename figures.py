import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import (
    is_hidden, FUNDAMENTALS_TO_PLOT, QUARTERLY_COUNTERPART, GROWTH_PANELS,
    VALUATIONS_TO_PLOT, HARMONIC_MEAN_CONCEPTS,
)
from metrics import harmonic_mean

from datetime import datetime

# Colors pinned so every subplot looks like the matplotlib version did
# (each mpl axes restarted its color cycle; one Plotly figure would not).
_PRIMARY_COLOR = "#1f77b4"
_SECONDARY_COLOR = "#ff7f0e"
_PERCENT_TICKFORMAT = ".1~%"
_KNOWN_OUTPUT_EXTENSIONS = {".png", ".html", ".json"}


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
    if n == 0:
        return 1, 1
    cols = min(max_cols, n)
    rows = -(-n // cols)
    return rows, cols


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


def plot_fundamentals(ticker: str, metrics_long: pd.DataFrame, output_path: str) -> None:

    concepts_to_plot = [c for c in FUNDAMENTALS_TO_PLOT if not is_hidden(ticker, c[0])]

    if not concepts_to_plot:
        print(f"[plot_fundamentals] {ticker}: no visible panels, skipping chart output.")
        return

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
        width=500 * cols, height=330 * rows,
        legend=dict(font=dict(size=9)),
    )
    _write_figure(fig, output_path)


def plot_growth(ticker: str, facts: pd.DataFrame, output_path: str, growth_column: str = "yoy_growth") -> None:

    if growth_column not in facts.columns:
        print(f"[plot_growth] {ticker}: column '{growth_column}' missing, skipping chart output.")
        return

    panels = [(c, label) for c, label in GROWTH_PANELS if not is_hidden(ticker, c)]

    if not panels:
        print(f"[plot_growth] {ticker}: no visible panels, skipping chart output.")
        return

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
        width=500 * len(panels), height=360,
        legend=dict(font=dict(size=9)),
    )
    _write_figure(fig, output_path)


def plot_valuation(ticker: str, valuation_history: pd.DataFrame, output_path: str, years: int = 5) -> None:
    cutoff = pd.Timestamp.today() - pd.DateOffset(years=years)
    filtered = valuation_history[valuation_history["end"] >= cutoff]

    concepts_to_plot = [c for c in VALUATIONS_TO_PLOT if not is_hidden(ticker, c[0])]

    if not concepts_to_plot:
        print(f"[plot_valuation] {ticker}: no visible panels, skipping chart output.")
        return

    rows, cols = _make_grid(len(concepts_to_plot))
    fig = _make_subplot_figure(rows, cols, [c[0] for c in concepts_to_plot])

    for idx, (concept, ylabel, ref_line, percent) in enumerate(concepts_to_plot):
        r, c = idx // cols + 1, idx % cols + 1
        plot_metric(fig, r, c, filtered, ticker, concept, ylabel, ref_line, percent,
                    show_mean=True, harmonic=concept in HARMONIC_MEAN_CONCEPTS)

    fig.update_layout(
        title_text=f"Valuation Data {ticker}",
        width=500 * cols, height=400 * rows,
        legend=dict(font=dict(size=9)),
    )
    _write_figure(fig, output_path)
