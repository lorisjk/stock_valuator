import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from matplotlib.ticker import PercentFormatter
from config import is_hidden, FUNDAMENTALS_TO_PLOT, QUARTERLY_COUNTERPART, GROWTH_PANELS, VALUATIONS_TO_PLOT
import numpy as np


def plot_metric(
    ax,
    metrics_long: pd.DataFrame,
    ticker: str,
    concept: str,
    ylabel: str,
    ref_line=None,
    percent: bool = False,
    symlog: bool = False,
    show_mean: bool = False,
) -> None:

    filtered = metrics_long[
        (metrics_long["ticker"] == ticker) & (metrics_long["concept"] == concept)
    ].sort_values("end")

    if filtered.empty:
        ax.text(0.5, 0.5, "keine Daten", ha="center", va="center",
                transform=ax.transAxes, color="red")
        ax.set_title(concept)
        ax.set_xticks([])
        ax.set_yticks([])
        return

    ax.plot(filtered["end"], filtered["value"])
    ax.set_title(concept)
    ax.set_ylabel(ylabel)
    ax.grid()

    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    if show_mean:
        mean_value = filtered["value"].mean()
        label = f"Ø {mean_value:.2%}" if percent else f"Ø {mean_value:.1f}"
        ax.axhline(mean_value, color="red", linewidth=1, label=label)
        ax.legend(fontsize=8)

    if ref_line is not None:
        ax.axhline(ref_line, color="red", linewidth=1)

    if percent:
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=1))

    if symlog:
        ax.set_yscale("symlog", linthresh=1)

def plot_metric_dual(
    ax,
    metrics_long: pd.DataFrame,
    ticker: str,
    concept: str,
    quarterly_concept: str,
    ylabel: str,
    ref_line=None,
    percent: bool = False,
    symlog: bool = False,
) -> None:

    ttm = metrics_long[
        (metrics_long["ticker"] == ticker) & (metrics_long["concept"] == concept)
    ].sort_values("end")
    quarterly = metrics_long[
        (metrics_long["ticker"] == ticker) & (metrics_long["concept"] == quarterly_concept)
    ].sort_values("end")

    if ttm.empty and quarterly.empty:
        ax.text(0.5, 0.5, "keine Daten", ha="center", va="center",
                transform=ax.transAxes, color="red")
        ax.set_title(concept)
        ax.set_xticks([])
        ax.set_yticks([])
        return

    if not ttm.empty:
        ax.plot(ttm["end"], ttm["value"], label="TTM", linewidth=1.5)
    if not quarterly.empty:
        ax.plot(quarterly["end"], quarterly["value"], label="Quartal", linewidth=0.8, alpha=0.6)

    ax.set_title(concept)
    ax.set_ylabel(ylabel)
    ax.grid()
    ax.legend(fontsize=7)

    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    if ref_line is not None:
        ax.axhline(ref_line, color="red", linewidth=1)

    if percent:
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=1))

    if symlog:
        ax.set_yscale("symlog", linthresh=1)


def _make_grid(n: int, max_cols: int = 3):
    if n == 0:
        return 1, 1
    cols = min(max_cols, n)
    rows = -(-n // cols)  
    return rows, cols


def plot_fundamentals(ticker: str, metrics_long: pd.DataFrame, output_path: str) -> None:

    concepts_to_plot = [c for c in FUNDAMENTALS_TO_PLOT if not is_hidden(ticker, c[0])]

    rows, cols = _make_grid(len(concepts_to_plot))
    fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 3.3 * rows))
    axes = np.atleast_1d(axes).flatten()

    for ax, (concept, ylabel, ref_line, percent, symlog) in zip(axes, concepts_to_plot):
        quarterly_concept = QUARTERLY_COUNTERPART.get(concept)
        if quarterly_concept and not is_hidden(ticker, quarterly_concept):
            plot_metric_dual(ax, metrics_long, ticker, concept, quarterly_concept, ylabel, ref_line, percent, symlog)
        else:
            plot_metric(ax, metrics_long, ticker, concept, ylabel, ref_line, percent, symlog)

    for ax in axes[len(concepts_to_plot):]:
        ax.axis("off")

    fig.suptitle(f"Fundamentals {ticker}")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def plot_growth(ticker: str, facts: pd.DataFrame, output_path: str, growth_column: str = "yoy_growth") -> None:

    if growth_column not in facts.columns:
        return

    panels = [(c, label) for c, label in GROWTH_PANELS if not is_hidden(ticker, c)]

    fig, axes = plt.subplots(1, len(panels), figsize=(5 * len(panels), 3.6))
    axes = np.atleast_1d(axes).flatten()

    for ax, (concept, label) in zip(axes, panels):
        series = facts[
            (facts["ticker"] == ticker) & (facts["concept"] == concept)
        ].dropna(subset=[growth_column]).sort_values("end")

        if series.empty:
            ax.text(0.5, 0.5, "keine Daten", ha="center", va="center",
                    transform=ax.transAxes, color="red")
            ax.set_title(concept)
            ax.set_xticks([])
            ax.set_yticks([])
            continue

        ax.plot(series["end"], series[growth_column])
        ax.set_title(concept)
        ax.set_ylabel(label)
        ax.grid()
        ax.axhline(0, color="red", linewidth=1)
        ax.xaxis.set_major_locator(mdates.YearLocator(2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=1))

    fig.suptitle(f"Growth (YoY) {ticker}")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def plot_valuation(ticker: str, valuation_history: pd.DataFrame, output_path: str, years: int = 5) -> None:
    cutoff = pd.Timestamp.today() - pd.DateOffset(years=years)
    filtered = valuation_history[valuation_history["end"] >= cutoff]


    concepts_to_plot = [c for c in VALUATIONS_TO_PLOT if not is_hidden(ticker, c[0])]

    rows, cols = _make_grid(len(concepts_to_plot))
    fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 4 * rows))
    axes = np.atleast_1d(axes).flatten()

    for ax, (concept, ylabel, ref_line, percent) in zip(axes, concepts_to_plot):
        plot_metric(ax, filtered, ticker, concept, ylabel, ref_line, percent, show_mean=True)

    for ax in axes[len(concepts_to_plot):]:
        ax.axis("off")

    fig.suptitle(f"Valuation Data {ticker}")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)