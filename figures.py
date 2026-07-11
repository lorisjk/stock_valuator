import matplotlib.pyplot as plt
import pandas as pd

import matplotlib.pyplot as plt
import pandas as pd


def plot_metric(ax, metrics_long: pd.DataFrame, ticker: str, concept: str, ylabel: str) -> None:
    filtered = metrics_long[(metrics_long["ticker"] == ticker) & (metrics_long["concept"] == concept)]
    filtered = filtered.sort_values("end")

    ax.plot(filtered["end"], filtered["value"])
    ax.set_title(concept)
    ax.set_ylabel(ylabel)
    ax.grid()


def plot_historical_pe(pe_df: pd.DataFrame, rolling_pe_df: pd.DataFrame, ticker: str, output_path: str, start_date: str = "2015-01-01") -> None:
    filtered_pe_df = pe_df[pe_df["ticker"] == ticker]
    filtered_rolling_pe_df = rolling_pe_df[rolling_pe_df["ticker"] == ticker]
    merged_df = pd.merge(filtered_pe_df, filtered_rolling_pe_df, on=["ticker", "end"])

    if start_date is not None:
        merged_df = merged_df[merged_df["end"] >= pd.to_datetime(start_date)]

    fig, ax = plt.subplots()
    ax.plot(merged_df["end"], merged_df["pe_ratio"], label="P/E")
    ax.plot(merged_df["end"], merged_df["avg_pe_5y"], label="Ø P/E (5 Jahre)")
    ax.set_title(f"historical_pe and rolling_pe for {ticker}")
    ax.set_xlabel("Datum")
    ax.set_ylabel("P/E")
    ax.grid()
    ax.legend()
    fig.savefig(output_path)
    plt.close(fig)