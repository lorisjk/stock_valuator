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
| `calculate_rolling_harmonic_stats` | Harmonic mean, median and count over a calendar window |

### Selection and reshaping

| Function | What it does |
|---|---|
| `get_latest_value` | Newest row **carrying a value** per ticker, for a given concept |
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

The prior value is found **by date**, not by position: `merge_asof` against `end − periods × 365.25/4` with a tolerance of `periods × 45/4` days and `direction="nearest"`, returning nothing when no observation falls inside. The bound is on the lag between two *observation dates* four quarters apart — 365.2 days — which is a different measurement from `calculate_ttm`'s window span (273.9 days, three steps rather than four). ±45 cannot reach three quarters (273.9) or five (456.6), each 91 days away. This is the only growth convention in the project; `build_valuation_history` used to carry a second, row-based one.

### `calculate_ratio` with `require_positive_denominator`

Same idea, but optional — because it is not always appropriate.

**Payout ratio** (`dividend / EPS`) needs it: when EPS is near zero, the ratio goes to infinity; when EPS is negative, it goes negative, which is nonsense.

**ROE** (`income / equity`) does **not** get it: a loss-making quarter genuinely *has* a negative return on equity. That is real information, not an artifact. Masking it would hide something the reader should see.

The distinction is whether a broken **denominator** makes the metric undefined, or whether a negative **result** is a legitimate outcome.

### `apply_denominator_scale_guard` and `fill_scale_reference`

A third kind of broken denominator: one that is *present and positive* but far too small to be the denominator of this business — a $40k equity balance under a $60bn market cap. The guard blanks the ratio when `|denominator| < ratio × |scale reference|`, the reference normally being `Revenue_TTM`.

**A missing reference cannot fire the guard**, and that is a property of the comparison, not a policy: `denominator < ratio × NaN` is `False`, so the value passes. There used to be an explicit `& scale_reference.notna()` on that line; it was a no-op and is gone.

So the reference is filled instead of the behaviour being chosen. `fill_scale_reference` carries a ticker's reference forward, then backward for a leading hole. This is sound because the guard asks an order-of-magnitude question, which a neighbouring period's revenue answers as well as the absent one would — and it is what the data called for: ~6,700 values reached a guarded metric with no reference, and **every one was a per-period hole on a ticker that reports revenue elsewhere**. Once the guard could evaluate them it blanked 27 — VLO's 1,093% tax rate, ATO's 8,199% ROE, a P/B of 812 — and left the rest, which measured *tamer* than the population the guard was already passing. Derivation in `alignment_and_defaults_report.md`.

### `apply_self_relative_scale_guard`: two years either side, measured in days

A fourth kind of broken denominator, and the one the *series* answers rather than the period:
a revenue figure that collapsed to under a tenth of what this business reports around that
time. The reference is the maximum absolute revenue in a window centred on the row.

**The window is a calendar span, not a row count** — `REVENUE_SELF_SCALE_HALF_WINDOW_DAYS = 730`,
so `[end - 730d, end + 730d]`. It used to be seventeen rows, the last member of the family
`calculate_ttm` (4 rows), `calculate_rolling_harmonic_stats` (20 rows) and `pct_change` (4 rows)
belonged to. Seventeen rows are four years only on a series with no hole: the modal span was
exactly 1,461 days but the tail reached **4,475 — twelve years**, and 27% of windows were
truncated at a series end before that.

As with the five-year window there is **no empty run to derive a threshold from**, and for the
same structural reason: a span is a sum of quarter-steps, so its support is a lattice with
~91-day spacing and every gap in it is that spacing rather than a boundary between two
populations. That is the argument for defining the window instead of masking a wrong one.

Two things worth knowing:

- **Switching from rows to days moved no value**, but not because the rules agree. They
  disagree about the reference on **25% of rows** — the row window reaches further back and so
  sees a larger maximum, by 2.4% at the median and up to 5.9x — and the conclusion survives
  because the guard fires at a factor of ten while the error is a factor of 1.02. Fourteen rows
  sit within [0.10, 0.15) of the threshold; that is the headroom.
- **The window is centred, so the guard is not causal.** A row's visibility can change when a
  later period is filed, and an as-of view assembled by cutting rows was still guarded using
  data from after the cut. Kept, because the quantity is "the scale of this business around
  this period" and a backward-only reference would judge a company's early years against
  nothing and its post-divestiture years against a business that no longer exists.

A thin window needs no special case: `min_periods=1` puts the row in its own window, so a row
with no neighbours is compared against itself and passes — the same "cannot evaluate, therefore
do not blank" property the denominator guard has with a missing reference, and deliberately not
a second notion of "too little history" beside `avg_*_5y_history_too_short`. Derivation in
`final_consistency_report.md`.

---

## `calculate_ttm` and why it matters

A rolling four-quarter sum **that checks it is looking at four quarters**. This is not a cosmetic smoothing choice — it changes which numbers are usable at all.

Microsoft's Q4 2012 was a loss (the aQuantive goodwill write-off). Computed on that single quarter:
- income growth: **-1100%**
- operating margin: **-10%**
- ROE: **-8%**

All three are correct for that quarter, and all three are useless for judging the business. On a TTM basis the same event appears as a modest dip, because three normal quarters absorb it.

Every ratio metric in this project is therefore built on `_TTM` concepts. The exceptions are pure balance-sheet ratios (`debt_to_equity`), where there is nothing to sum.

**`calculate_ttm` must never be applied to per-share values or balance-sheet positions.** Summing four quarterly equity balances gives four times the equity. Summing four quarterly EPS figures breaks across stock splits. See `config.py` for why `EPS` is absent from `TTM_CONCEPTS`.

**`.rolling(4)` sums four *rows*, and four rows are twelve months only if the series has no hole.** On a thin concept the four nearest available values can span years — JBL once had a `StockIssued_TTM` built from ends 2013-08-31 / 2014-05-31 / 2015-05-31 / 2016-05-31. So the window is checked against the calendar before the sum is kept: the outer ends must be 248–333 days apart and every step between adjacent rows 76–137 days. Both bounds are the midpoint of an empty run in the measured distribution of all 333,737 windows — the band is wide enough for 52/53-week filers (12- and 16-week quarters, 53-week years) and fiscal-year-end changes, and 58 days clear of the nearest window that skips a quarter. A window that fails yields no value rather than a wrong one; 4.4% of them do. Derivation in `ttm_window_report.md`.

**A 12-month fact at a fiscal year end is the TTM value at that date, not an approximation of it.** For a filer that discloses an item only once a year there is nothing for `decumulate_period_values` to difference, so the quarterly pipeline gets zero and the rolling window has no rows at all. `parse_edgar.annual_ttm_values` takes such facts directly.

**It runs where the rolling path produces no TTM value for the series** — not, as it once did, where no quarterly *fact* exists. That older test was too coarse for a concept reported **on occurrence** rather than every period: BDX tags 55 quarterly `DividendsPerShare` values that are never four consecutive quarters, and their existence alone discarded the annual facts. Gating on the rolling path's output instead recovers 343 values across 77 (ticker, concept) pairs. Deliberately per *series*, not per date — 81% of what per-date gating would add is annual-only history predating quarterly tagging, and 81,505 annual facts land on dates the rolling path already holds. Derivation in `annual_path_gate_report.md`.

The two paths therefore stay disjoint per series, which matters because they are **concatenated, not merged**: a collision would put two rows at one `(ticker, concept, end)` and `pivot_table` would average them. Which path produced a value is recorded in the facts frame's `ttm_source` column (`quarterly_rolling` / `annual_fact`), and under this rule it is a per-series constant rather than a per-value one.

---

## `calculate_rolling_harmonic_stats`: five years means five years

The `avg_*_5y` lines the snapshot compares today's multiple against. Harmonic rather than
arithmetic because every one of them is a price-over-something ratio, and averaging ratios
arithmetically overweights the expensive periods.

**The window is a calendar span, not a row count** (`AVG_5Y_WINDOW = "1826D"` in `main.py`): every
observation whose end falls in `(end − 1826 days, end]`. Twenty rows are five years only on a series
with no hole and no extra row, and the valuation history has both. Twenty consecutive quarters span
**1,735 days between their outer ends**, not 1,826 — the same three-versus-four-step arithmetic as
`calculate_ttm`'s 273 — and measured over the 23,734 windows the frame forms, **12.3% reached back
more than five years (up to 11.2) and 8.8% covered less than 4.65**. Unlike the TTM window there is
no empty run to derive a threshold from, which is exactly why the fix defines the window directly
instead of masking a bad one. Derivation in `rolling_window_report.md`.

Two consequences worth knowing:

- **The observation count is no longer fixed at twenty.** `_n` reports what was actually available,
  and `avg_*_5y_history_too_short` marks `_n < MIN_AVG_5Y_OBSERVATIONS`. A mean is still published
  from a single observation, as before — the window says which observations belong, not how many are
  required.
- **A row with no usable value displaces nothing**, because it occupies no time. Under the row
  window a masked multiple consumed a slot, and since the seven multiples share one pivot row set,
  one quarter missing from any of the fourteen needed concepts cost all seven means a slot.

`calculate_rolling_average`, the arithmetic sibling, has been removed — zero call sites since it was
written, and it still carried the row-count window this function no longer uses.

---

## `get_latest_value`: the newest row that carries a number

It used to be the newest *row*, value or not. AvalonBay's `FFO_TTM` is NaN at 2026-03-31 and
2026-06-30 and 1.60bn at 2025-09-30, so the snapshot had no `p_ffo` for a REIT although one
was available three quarters back — and every snapshot input goes through this function.
**83 (ticker, concept) pairs on 69 tickers** were in that state, 49 of them
`DividendsPerShare_TTM`, which is exactly the concept a board declares on occasion rather than
every quarter.

**Skipping nulls without a bound is worse than the bug**: the distances run to 5,021 days, and a
dividend from 2012 beside today's price is not a stale number, it is a wrong one.
`MAX_LATEST_VALUE_AGE_DAYS = 365` bounds it, and the bound is definitional rather than fitted —
a TTM figure covers twelve months, so a value more than four quarters behind the concept's
newest row describes a year that no longer overlaps the current one. The measured distances
corroborate it: they form a quarterly lattice that stops at 365 and does not resume until 546,
so **every bound in [365, 545] selects the identical 37 pairs**.

**The age is measured inside the series, not against today.** A filer whose whole series ended
three years ago has age 0, because its newest row *is* its value; absolute staleness stays the
job of `days_since_last_filing` and `fundamentals_stale`. The returned `value_age_days` is what
lets `build_snapshot` publish `<field>_age_days`, the same "here is how this number was
obtained" signal `ttm_source` and `ffo_gains_source` carry in the facts frame.

`max_value_age_days=None` disables the bound, for the one caller that wants a value at any age:
the scale guard's order-of-magnitude reference, on the same argument `fill_scale_reference`
makes. Derivation in `final_consistency_report.md`.

---

## Pandas patterns worth remembering

### `groupby(...).shift(n)` and `groupby(...).rolling(n)`

Both `shift` and `rolling` must be grouped by ticker. Without the `groupby`, `shift(4)` would happily take Apple's last four quarters as the "previous year" for Microsoft's first row, because the two sit adjacent in the same DataFrame.

### `.reset_index(level=0, drop=True)` after a grouped rolling

`groupby(...).rolling(...)` returns a result with a MultiIndex (ticker + original row index). Assigning that back as a column requires stripping the outer ticker level first. This is a Pandas quirk, not something derivable from first principles — just a pattern to copy.

**With `on=` it is a different MultiIndex and the pattern does not work.** `groupby("ticker").rolling(window="1826D", on="end")` returns `(ticker, end)` — the original row index is gone, and stripping the ticker level leaves `end`, which is not unique across tickers. `calculate_rolling_harmonic_stats` therefore assigns positionally (`.to_numpy()`), which is valid only because the frame is sorted by ticker then end and `groupby` walks the tickers in that same order. That assumption is checked in `rolling_window_report.md` against an independent recomputation of all 232,365 rows rather than taken on trust.

### `.transform("max")` vs `.max()`

Not used here, but relevant in `quality.py`: `.max()` returns one value per group; `.transform("max")` returns the group's max **for every row**, so it can be assigned back as a column. The tool for broadcasting a group aggregate back onto individual rows.
