# `figures.py`

## Overview

All plotting. Takes finished long-format DataFrames and writes PNG files. Contains no calculations and no data access.

Two chart sets are produced per ticker, corresponding to two different questions:

**`plot_fundamentals`** — *Is this a good business?* Nine metrics over the full available history: growth, margins, returns, leverage. These are TTM-smoothed and independent of the share price.

**`plot_valuation`** — *Is the stock expensive right now?* Six valuation multiples over the last five years, each with its own five-year mean drawn as a reference line.

---

## Functions

| Function | Purpose |
|---|---|
| `plot_metric` | Draws one metric into one supplied `ax`. The reusable building block. |
| `plot_fundamentals` | 3×3 grid of fundamental metrics → one PNG per ticker |
| `plot_valuation` | 2×3 grid of valuation multiples → one PNG per ticker |

---

## Design: one ticker per figure

Charts are never drawn across tickers. Every figure covers exactly one company.

This is deliberate. A P/E of 30 means nothing in isolation and not much more next to a competitor's 25 — different businesses justify different multiples. What *is* meaningful is a company against its own history: "P/E is currently 30, the five-year average is 24" is an actionable statement. That is the question these charts answer, and putting three tickers on one axis would obscure it.

---

## `plot_metric`

Takes an `ax` rather than creating its own figure. This is what makes it reusable: the same function fills a single standalone chart or one cell of a 3×3 grid, depending on what the caller passes in.

### Parameters

| Parameter | Effect |
|---|---|
| `ref_line` | Draws a horizontal line at a fixed value. `0` for growth rates (positive/negative at a glance), `0.4` for Rule of 40 (the threshold the name refers to). |
| `percent` | Formats the y-axis as percentages. Values are stored as decimals (0.35), so `PercentFormatter(xmax=1)` maps 1.0 → 100%. |
| `symlog` | Symmetric log scale on the y-axis. Needed where a single extreme value would otherwise flatten the rest of the curve — NVIDIA's earnings grew 800% in one year, which compresses everything else into a straight line on a linear axis. `linthresh=1` keeps the range between -100% and +100% linear and only compresses beyond that. Unlike a plain log scale, `symlog` handles zero and negative values. |
| `show_mean` | Draws the mean of the **displayed** data as a reference line, with the value in the legend. Used for all valuation multiples. |

### Empty data handling

If a ticker has no data for a metric, the subplot prints "keine Daten" instead of plotting. Without this, matplotlib falls back to the Unix epoch and draws an axis labelled "1970" — which looks like a bug rather than an absence of data.

This is not an edge case. Banks have no operating margin, no capex, and no conventional long-term debt, so five of the nine fundamental subplots are legitimately empty for JPM.

### The mean is computed on filtered data

`show_mean` averages whatever rows reach `plot_metric`, not the full history. `plot_valuation` filters to the last five years *before* calling it, so the line shows the five-year mean — which is the intended comparison. Passing unfiltered data would silently produce a twenty-year average instead.

---

## The relative time window in `plot_valuation`

```python
cutoff = pd.Timestamp.today() - pd.DateOffset(years=years)
```

The window is relative to today, not a hardcoded date.

This started as a workaround. Historical P/E for Apple was unusable before roughly 2019 — EDGAR restates per-share figures retroactively after stock splits, but not uniformly across filings, so TTM sums that straddle a split produce garbage (P/E of 265 in one quarter, -22 in the next). The first fix was to hardcode a start date, which was correct for Apple and wrong for everything else.

The relative window solves it properly, and for a better reason: **the split zone is old data, and old data is not the question.** "Is this stock expensive right now" is answered by the last few years, not by 2011. Any ticker, any time — the last five years contain no split break, because splits are rare and their distortion washes out of the TTM window within a year.

The `years` parameter is exposed so this can be adjusted per call without touching the function.