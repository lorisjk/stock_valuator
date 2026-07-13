# `metrics.py`

## Overview

Pure DataFrame calculations. No network access, no file I/O, no knowledge of where the data came from.

Every function takes a DataFrame and returns a new one. Nothing is mutated in place, and no function reads from `config.py` — everything it needs arrives as an argument. This keeps the module testable in isolation and reusable regardless of the data source.

The functions are deliberately generic. There is no `calculate_operating_margin()`; there is `calculate_ratio(df, "OperatingIncomeLoss_TTM", "Revenue_TTM", "operating_margin")`. Nine of the eleven metrics in this project are built from three primitives.

---

## Functions

### Building blocks

| Function | What it does |
|---|---|
| `calculate_growth` | Growth rate against a value *n* periods back |
| `calculate_ratio` | One concept divided by another, same period |
| `calculate_difference` | One concept plus or minus another, same period |
| `calculate_ratio_from_dfs` | Ratio of two already-computed DataFrames |
| `calculate_sum_from_dfs` | Sum of two already-computed DataFrames |

### Time series operations

| Function | What it does |
|---|---|
| `calculate_ttm` | Rolling four-quarter sum |
| `calculate_rolling_average` | Rolling mean over *n* periods |

### Selection and reshaping

| Function | What it does |
|---|---|
| `get_latest_value` | Newest row per ticker, for a given concept |
| `get_latest_row` | Newest row per ticker, for any DataFrame |
| `to_long_format` | Renames a value column to `value` and adds a `concept` column |
| `add_ttm_concepts` | Appends `<concept>_TTM` series to the facts table |
| `add_as_concept` | Appends any computed DataFrame as a new concept |

---

## Two ways of combining data

The `_from_dfs` variants exist because the input shape differs.

`calculate_ratio` operates on the **long-format facts table**: it filters two concepts out of one DataFrame and merges them. It needs a `concept` column.

`calculate_ratio_from_dfs` operates on **two separate DataFrames** that are already results. FCF margin, for instance, is `fcf` (a computed DataFrame) over `Revenue_TTM` (a concept). No `concept` column exists on the left side, so the concept-filtering variant cannot be used.

Both merge on `["ticker", "end"]` — an inner join, so periods present on only one side drop out. That is the intended behavior: a ratio requires both inputs.

---

## Masking undefined values

Two functions can produce mathematically meaningless output, and both guard against it.

### `calculate_growth`

```python
filtered_df["prev_value"] = filtered_df["prev_value"].where(filtered_df["prev_value"] > 0)
```

A growth rate is `(new / old) - 1`. When `old` is negative or near zero, the formula explodes. NVIDIA's 2011 loss year produced a growth rate of **-6300%** — arithmetically correct, analytically worthless.

`.where(cond)` keeps values where the condition holds and sets the rest to `NaN`. The subsequent division propagates the `NaN`, and matplotlib draws a gap in the line. That is more honest than a spike that looks like a signal.

### `calculate_ratio` with `require_positive_denominator`

Same idea, but optional — because it is not always appropriate.

**Payout ratio** (`dividend / EPS`) needs it: when EPS is near zero, the ratio goes to infinity; when EPS is negative, it goes negative, which is nonsense.

**ROE** (`income / equity`) does **not** get it: a loss-making quarter genuinely *has* a negative return on equity. That is real information, not an artifact. Masking it would hide something the reader should see.

The distinction is whether a broken **denominator** makes the metric undefined, or whether a negative **result** is a legitimate outcome.

---

## `calculate_ttm` and why it matters

A rolling four-quarter sum. This is not a cosmetic smoothing choice — it changes which numbers are usable at all.

Microsoft's Q4 2012 was a loss (the aQuantive goodwill write-off). Computed on that single quarter:
- income growth: **-1100%**
- operating margin: **-10%**
- ROE: **-8%**

All three are correct for that quarter, and all three are useless for judging the business. On a TTM basis the same event appears as a modest dip, because three normal quarters absorb it.

Every ratio metric in this project is therefore built on `_TTM` concepts. The exceptions are pure balance-sheet ratios (`debt_to_equity`), where there is nothing to sum.

**`calculate_ttm` must never be applied to per-share values or balance-sheet positions.** Summing four quarterly equity balances gives four times the equity. Summing four quarterly EPS figures breaks across stock splits. See `config.py` for why `EPS` is absent from `TTM_CONCEPTS`.

---

## Pandas patterns worth remembering

### `groupby(...).shift(n)` and `groupby(...).rolling(n)`

Both `shift` and `rolling` must be grouped by ticker. Without the `groupby`, `shift(4)` would happily take Apple's last four quarters as the "previous year" for Microsoft's first row, because the two sit adjacent in the same DataFrame.

### `.reset_index(level=0, drop=True)` after a grouped rolling

`groupby(...).rolling(...)` returns a result with a MultiIndex (ticker + original row index). Assigning that back as a column requires stripping the outer ticker level first. This is a Pandas quirk, not something derivable from first principles — just a pattern to copy.

### `.transform("max")` vs `.max()`

Not used here, but relevant in `quality.py`: `.max()` returns one value per group; `.transform("max")` returns the group's max **for every row**, so it can be assigned back as a column. The tool for broadcasting a group aggregate back onto individual rows.
