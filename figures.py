import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from matplotlib.ticker import PercentFormatter


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


def plot_fundamentals(ticker: str, metrics_long: pd.DataFrame, output_path: str) -> None:
    concepts_to_plot = [
        ("revenue_yoy_growth", "Umsatzwachstum", 0, True, False),
        ("income_yoy_growth", "Gewinnwachstum", 0, True, True),
        ("operating_margin", "Operative Marge", None, True, False),
        ("roe", "Eigenkapitalrendite", None, True, False),
        ("debt_to_equity", "Verschuldungsgrad", None, False, False),
        ("payout_ratio", "Ausschüttungsquote", None, True, True),
        ("fcf_margin", "Free Cash Flow Marge", None, True, False),
        ("net_debt_to_ebitda", "Net Debt / EBITDA", 0, False, False),
        ("rule_of_40", "Rule of 40", 0.4, True, False),
    ]

    fig, axes = plt.subplots(3, 3, figsize=(15, 10))

    for ax, (concept, ylabel, ref_line, percent, symlog) in zip(axes.flatten(), concepts_to_plot):
        plot_metric(ax, metrics_long, ticker, concept, ylabel, ref_line, percent, symlog)

    fig.suptitle(f"Fundamentaldaten {ticker}")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def plot_valuation(ticker: str, valuation_history: pd.DataFrame, output_path: str, years: int = 5) -> None:
    cutoff = pd.Timestamp.today() - pd.DateOffset(years=years)
    filtered = valuation_history[valuation_history["end"] >= cutoff]

    concepts_to_plot = [
        ("pe_ratio", "P/E (TTM)", None, False),
        ("pb_ratio", "P/B", None, False),
        ("pfcf_ratio", "P/FCF (TTM)", None, False),
        ("ev_ebitda", "EV/EBITDA", None, False),
        ("ev_sales", "EV/Sales", None, False),
        ("dividend_yield", "Dividendenrendite", None, True),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))

    for ax, (concept, ylabel, ref_line, percent) in zip(axes.flatten(), concepts_to_plot):
        plot_metric(ax, filtered, ticker, concept, ylabel, ref_line, percent, show_mean=True)

    fig.suptitle(f"Bewertungsdaten {ticker}")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)