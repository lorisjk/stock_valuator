# `fetchers/yfinance_fetcher.py`

## Overview

Supplies market data: the current share price and share count, plus the historical closing-price series.

This is deliberately the only role yfinance plays in the project. All fundamentals come from SEC EDGAR, where the data is regulated, auditable, and traceable back to a specific filing. yfinance is used for prices because prices are unambiguous and because EDGAR does not carry them.

Unlike the EDGAR fetcher, this module does **not** cache. Prices change daily; a cache would only serve stale data.

---

## Functions

| Function | Purpose | Output |
|---|---|---|
| `get_current_price_and_shares` | Latest price and share count for one ticker | `dict` |
| `get_price_history` | Daily closing prices since `start` | `DataFrame` with `ticker`, `date`, `close` |

---

## Design notes

### Why not use yfinance's precomputed metrics

`yf.Ticker(x).info` returns a large dictionary that already contains `trailingPE`, `forwardPE`, `priceToBook`, `enterpriseToEbitda`, `pegRatio`, `debtToEquity`, `returnOnEquity`, `freeCashflow` — essentially every ratio this project computes from scratch.

They are not used, for two reasons:

**Opacity.** The methodology behind those numbers is undocumented. Which EPS definition? Trailing twelve months or last fiscal year? What happens when a tag is missing? Building the ratios from EDGAR data means every number can be traced back to a specific filing.

**Reliability.** `forwardPE` in particular is known to diverge from what Yahoo Finance itself displays on its website.

They remain useful as a sanity check: if the computed P/E is wildly different from `trailingPE`, something is likely wrong. A moderate difference is expected — `trailingPE` uses TTM earnings, the last fiscal year, or something in between depending on the day.

### `.get()` instead of `[...]`

yfinance field names are neither standardized nor guaranteed to be populated. Some tickers (ADRs, certain share classes) are missing `currentPrice` or `sharesOutstanding`. `.get()` returns `None` instead of raising a `KeyError`, which lets the pipeline continue and surfaces the gap downstream rather than crashing.

### `reset_index()` in `get_price_history`

`yf.Ticker(x).history()` returns a DataFrame with the date in the **index**, not as a column. `reset_index()` moves it into a proper column, which is required for the later `merge_asof` against the EDGAR data — that function needs a real column to join on.

### Timezone handling happens elsewhere

The `date` column comes back timezone-aware (`America/New_York`) and at second resolution. EDGAR dates are timezone-naive. `merge_asof` refuses to join columns of different dtypes, so the conversion (`tz_localize(None)` and `.astype("datetime64[ns]")`) is applied in `main.py`, right before the merge.

This is arguably in the wrong place — a case could be made for normalizing inside this module instead. It sits in `main.py` because that is where the mismatch surfaced.

---

## Historical share count is not taken from here

`get_current_price_and_shares` returns **today's** share count. That is fine for the current snapshot, but useless for historical market capitalization: computing Apple's 2015 market cap with today's share count would be badly wrong, since the company has bought back a large fraction of its shares since then.

The historical share count comes from EDGAR instead, via the `WeightedAverageNumberOfDilutedSharesOutstanding` tag. See `config.py` (`CONCEPT_CANDIDATES`).

An earlier version derived it as `NetIncome / EPS`. That broke on stock splits: EDGAR restates per-share figures retroactively, but not uniformly across all filings, so the derived share count would flip sign or jump by an order of magnitude around a split. Reading the absolute share count directly from EDGAR avoids the problem entirely.