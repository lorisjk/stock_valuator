import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.dates as mdates
from matplotlib.ticker import PercentFormatter

def plot_metric(ax, metrics_long, ticker, concept, ylabel, ref_line=None, percent=False, symlog=False) -> None:
    filtered = metrics_long[(metrics_long["ticker"] == ticker) & (metrics_long["concept"] == concept)]
    filtered = filtered.sort_values("end")

    ax.plot(filtered["end"], filtered["value"])
    ax.set_title(concept)
    ax.set_ylabel(ylabel)
    ax.grid()
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    if ref_line is not None:
        ax.axhline(ref_line, color="red", linestyle="solid", linewidth=1)
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
    axes_flat = axes.flatten()
 
    for ax, (concept, ylabel, ref_line, percent, symlog) in zip(axes_flat, concepts_to_plot):
        plot_metric(ax, metrics_long, ticker, concept, ylabel, ref_line, percent, symlog)
       

    fig.suptitle(f"Fundamentaldaten {ticker}")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)