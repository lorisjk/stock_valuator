import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from matplotlib.ticker import PercentFormatter
from config import is_hidden
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

def _make_grid(n: int, max_cols: int = 3):
    if n == 0:
        return 1, 1
    cols = min(max_cols, n)
    rows = -(-n // cols)  # ceil division
    return rows, cols


def plot_fundamentals(ticker: str, metrics_long: pd.DataFrame, output_path: str) -> None:
    concepts_to_plot = [
        ("revenue_yoy_growth", "Umsatzwachstum", 0, True, False),
        ("income_yoy_growth", "Gewinnwachstum", 0, True, False),
        ("operating_margin", "Operative Marge", None, True, False),
        ("roe", "Eigenkapitalrendite", None, True, False),
        ("debt_to_equity", "Verschuldungsgrad", None, False, False),
        ("payout_ratio", "Ausschüttungsquote", None, True, True),
        ("fcf_margin", "Free Cash Flow Marge", None, True, False),
        ("net_debt_to_ebitda", "Net Debt / EBITDA", 0, False, False),
        ("rule_of_40", "Rule of 40", 0.4, True, False),
        ("net_interest_margin", "Nettozinsmarge", None, True, False),
        ("efficiency_ratio", "Efficiency Ratio", None, True, False),
        ("roa", "Return on Assets", None, True, False),
        ("equity_to_assets", "Equity / Assets", None, True, False),
        ("provision_ratio", "Provision/Revenue", 0, True, False),
        ("combined_ratio", "Combined Ratio", 1.0, True, False),
        ("loss_ratio", "Loss Ratio", None, True, False),
        ("expense_ratio", "Expense Ratio", None, True, False),
        ("net_investment_yield", "Net Investment Yield", None, True, False),
        ("reserve_growth", "Reserve Growth", 0, True, False),
        ("inventory_turnover", "Inventory Turnover (x/Jahr)", None, False, False),
        ("dio", "Days Inventory Outstanding", None, False, False),
        ("dso", "Days Sales Outstanding", None, False, False),
        ("dpo", "Days Payable Outstanding", None, False, False),
        ("cash_conversion_cycle", "Cash Conversion Cycle (Tage)", 0, False, False),
    ]
    concepts_to_plot = [c for c in concepts_to_plot if not is_hidden(ticker, c[0])]

    rows, cols = _make_grid(len(concepts_to_plot))
    fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 3.3 * rows))
    axes = np.atleast_1d(axes).flatten()

    for ax, (concept, ylabel, ref_line, percent, symlog) in zip(axes, concepts_to_plot):
        plot_metric(ax, metrics_long, ticker, concept, ylabel, ref_line, percent, symlog)

    for ax in axes[len(concepts_to_plot):]:
        ax.axis("off")

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
        ("p_tbv", "P/TBV", None, False),
        ("p_ppnr", "P/PPNR", None, False),
      
        ("p_core_earnings", "P/Core Earnings", None, False),
        
    ]

    concepts_to_plot = [c for c in concepts_to_plot if not is_hidden(ticker, c[0])]

    rows, cols = _make_grid(len(concepts_to_plot))
    fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 4 * rows))
    axes = np.atleast_1d(axes).flatten()

    for ax, (concept, ylabel, ref_line, percent) in zip(axes, concepts_to_plot):
        plot_metric(ax, filtered, ticker, concept, ylabel, ref_line, percent, show_mean=True)

    for ax in axes[len(concepts_to_plot):]:
        ax.axis("off")

    fig.suptitle(f"Bewertungsdaten {ticker}")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)