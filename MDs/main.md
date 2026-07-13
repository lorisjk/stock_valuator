# `main.py`

## Overview

Orchestration. Pulls the other modules together in the right order and writes the outputs.

Nothing here is a reusable primitive — those live in `metrics.py`. What lives here is the *wiring*: which concepts feed which metric, which data source joins to which, and in what sequence. `main()` itself is a twenty-line summary of the pipeline; the work sits in named functions above it.

The functions that combine EDGAR fundamentals with yfinance prices (`calculate_historical_pe`, `build_valuation_history`) are here rather than in `metrics.py` because they know about both data sources. `metrics.py` stays agnostic about where its DataFrames came from.

---

## Pipeline

```
load_facts()              EDGAR → quarterly values, one row per ticker/concept/date
    ↓
add_derived_concepts()    + TTM series, + EPS_TTM_CALC
    ↓
calculate_all_metrics()   9 fundamental metrics
    ↓
add_as_concept()          + FCF_TTM, EBITDA_TTM back into facts
    ↓
load_price_history()      yfinance → daily closes
load_current_prices()     yfinance → today's price and share count
    ↓
build_valuation_history() 6 valuation multiples, as a time series
calculate_historical_pe() P/E per quarter + 5-year rolling mean
build_snapshot()          one row per ticker, all current figures
    ↓
CSVs + charts
```

---

## Functions

| Function | Purpose |
|---|---|
| `load_facts` | EDGAR fundamentals for all tickers → long-format DataFrame |
| `load_price_history` | Historical closing prices |
| `load_current_prices` | Current price, share count, market cap |
| `add_derived_concepts` | Appends TTM series and computed EPS |
| `calculate_all_metrics` | The nine fundamental metrics |
| `build_metrics_long` | Metrics dict → single long-format table |
| `calculate_historical_pe` | P/E time series + rolling 5-year mean |
| `build_valuation_history` | Six valuation multiples as a time series |
| `build_snapshot` | Wide-format table: one row per ticker |

---

## The order in `main()` is not arbitrary

Three dependencies constrain it, and getting them wrong produces empty results rather than errors.

**`add_derived_concepts` before `calculate_all_metrics`.** Every ratio metric reads `_TTM` concepts. They do not exist until `add_ttm_concepts` has run.

**`calculate_all_metrics` before `add_as_concept(... "FCF_TTM")`.** FCF and EBITDA are computed metrics, not raw concepts. They have to exist as DataFrames before they can be folded back into `facts`.

**`add_as_concept` before `build_valuation_history`.** P/FCF and EV/EBITDA need `FCF_TTM` and `EBITDA_TTM` to be present in `facts`, because that function pivots `facts` into wide format and reads columns from it.

**`print_data_quality` runs on the raw facts**, before any derived concepts are added. Otherwise the `_TTM` series appear in the report as unexpected extras and skew the coverage ratios.

---

## Two output shapes, two purposes

### Long format (`facts`, `metrics_long`, `valuation_history`)

Columns: `ticker`, `end`, `concept`, `value`.

One row per observation. Adding a metric adds rows, never columns. This is what the plotting code consumes — `plot_metric` filters on `ticker` and `concept` and doesn't care what else is in the table.

### Wide format (`snapshot`)

Columns: `ticker`, `price`, `pe_ttm`, `pb_ratio`, …

One row per company, one column per figure. This is the "where does this stock stand today" table, meant to be read directly.

Both are produced, because they answer different questions. The long tables are for charts and history; the snapshot is for a glance.

---

## `EPS_TTM_CALC`

```python
eps_ttm = calculate_ratio(facts, "NetIncomeLoss_TTM", "SharesOutstanding", "value")
```

EPS is **not** derived by summing four quarterly EPS figures, even though that is the obvious approach and even though every other TTM concept works that way.

The reason is stock splits. EDGAR restates per-share figures retroactively after a split — but not uniformly across all filings. A rolling four-quarter window that straddles a split therefore mixes pre-split and post-split values. For NVIDIA around 2023 this produced a **negative** TTM EPS while net income was strongly positive, which then propagated into a negative share count, a negative market cap, and negative P/B, P/FCF and EV/Sales figures.

Computing EPS as `NetIncomeLoss_TTM / SharesOutstanding` avoids the problem entirely: both inputs are absolute quantities, immune to per-share restatement.

The share count itself comes from EDGAR (`WeightedAverageNumberOfDilutedSharesOutstanding`), not from yfinance — yfinance only reports today's count, which would be wrong for every historical quarter.

---

## `merge_asof`

```python
pd.merge_asof(..., direction="backward")
```

Fiscal quarter ends often fall on weekends or holidays, when no price exists. A plain merge on the date column would match nothing.

`merge_asof` joins to the **nearest** date instead of an exact one. `direction="backward"` takes the last available price at or before the reporting date, which is the conservative choice — the market could not have known the figures before they were filed.

`by="ticker"` is essential. Without it, `merge_asof` would happily match Apple's quarter end to Microsoft's price if that price happened to be temporally closer.

Both sides must be sorted by the join column, and both must have the **same dtype**. yfinance returns timezone-aware timestamps at second resolution; EDGAR dates are naive. The conversion (`tz_localize(None)`, `.astype("datetime64[ns]")`) happens in `load_price_history` and `load_facts` precisely so that this merge works.

---

## `build_valuation_history`: long → wide → long

The only place in the project that pivots.

Valuation multiples need several concepts **in the same row** to divide one by another (`market_cap / equity`). In long format they sit in separate rows. `pivot_table` turns each concept into a column:

```python
wide = facts[facts["concept"].isin(needed)].pivot_table(
    index=["ticker", "end"], columns="concept", values="value"
).reset_index()
```

After the arithmetic, `melt` reverses the operation — the inverse of `pivot_table`, and effectively a bulk version of `to_long_format`. The result goes back into the long format the plotting code expects.

`.dropna(subset=["value"])` at the end removes rows where a multiple could not be computed (masked denominators, missing inputs), so they simply don't appear rather than showing up as gaps.

---

## Masked denominators

Several multiples guard their denominator:

```python
wide["pe_ratio"] = wide["close"] / wide["EPS_TTM_CALC"].where(wide["EPS_TTM_CALC"] > 0)
```

A P/E with negative earnings is not a low P/E — it is undefined. Same for P/B with negative equity, EV/Sales with negative revenue, and a negative dividend (which is physically impossible; it is an artifact of the per-share split problem in `DividendsPerShare_TTM`, which has no absolute equivalent in EDGAR to reconstruct it from).

Masking turns these into `NaN`, which `dropna` then removes. The chart shows a gap instead of a misleading value.

---

## What this tool does not do

**Forward-looking metrics.** Forward P/E requires analyst estimates. EDGAR has none, and yfinance's `forwardPE` is unreliable.

**Non-GAAP figures.** Companies define their own adjustments, and they appear only in 8-K press releases, not in structured XBRL.

**Financial companies.** Banks have no operating income, no capex, and no long-term debt in the sense these metrics assume. Roughly half the charts come out empty for JPM, and that is the correct outcome — not a bug to be fixed. Financials need a different metric set (net interest margin, tier-1 capital, loan loss provisions) that this tool does not implement.