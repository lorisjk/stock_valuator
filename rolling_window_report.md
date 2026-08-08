# Row-Based Windows — `calculate_rolling_harmonic_stats` and `pct_change`

**Task:** the TTM task established that a window counted in rows rather than calendar time produces
a number that is not what its name claims, and fixed `calculate_ttm`. Two places still carried the
defect. Both are fixed here, as two separate change groups with a diff after each.

Measured over all 501 cached tickers through the pipeline's own functions; no refresh was run. Base
facts 512,078 rows, identical in every run below — this task changes nothing upstream of the pivot.

---

## 1. Part 1.1 — the span distribution

### The expected figure, stated before measuring

Twenty consecutive calendar quarters span **nineteen quarter-steps**, so the distance between the
outer end dates is

```
19 x 365.25/4 = 1,734.9 days
```

not 1,826. Five calendar years is 1,826 days; a twenty-row window *covers* five years but its outer
observations are nineteen quarters apart. Same arithmetic as the TTM window's 273 rather than 365,
one layer up.

### What the measurement says

```
rows in the seven series          232,365
full 20-row windows formed        166,138   over 489 tickers and 7 concepts
partial windows (< 20 rows)        66,227   min_periods=1, so a mean is published anyway
```

**The seven concepts form exactly the same windows.** Each has 23,734 full windows and an identical
span distribution, because `build_valuation_history` pivots on `(ticker, end)`: a row exists
wherever *any* of the fourteen needed concepts reported, so all seven multiples share one row set —
the ticker's reporting calendar, not the concept's own observations. Every count below is therefore
quoted once over the **23,734 distinct windows**; multiply by seven for the frame total.

| span (days) | windows | share |
|---|---:|---:|
| < 1,500 | 226 | 0.95% |
| 1,500–1,699 | 1,850 | 7.80% |
| 1,700–1,710 | 22 | 0.09% |
| 1,711–1,730 | 551 | 2.32% |
| **1,731–1,740** | **17,771** | **74.88%** |
| 1,741–1,750 | 190 | 0.80% |
| 1,751–1,825 | 30 | 0.13% |
| 1,826–1,900 | 406 | 1.71% |
| 1,901–2,000 | 1,262 | 5.32% |
| 2,001–2,200 | 1,157 | 4.88% |
| 2,201–2,600 | 182 | 0.77% |
| 2,601–3,650 | 74 | 0.31% |
| > 3,650 | 13 | 0.05% |

Day by day around the core (frame counts, all multiples of 7 — one ticker-date is seven windows):

```
  1708       84                <- 52/53-week filers, 12+12+12+16-week years
  1715      364
  1729    3,255  ########
  1732      399
  1733      581  #
  1734   41,440  ############################################################
  1735   33,292  ############################################################
  1736   46,312  ############################################################
  1737    1,638  ####
  1743    1,190  ##
  1750        7
  1765       14
  1782        7                <- last observation before the gap population begins
  ...
  1826+                        <- windows reaching past five years
```

**The measurement confirms the arithmetic:** 78.1% of windows are within a month of 1,735 days, and
the three-day mode 1,734 / 1,735 / 1,736 alone is 72.9%.

### There is no empty run, and that decides the rule

Between 1,600 and 2,600 days the distribution is a **continuum**. The holes are 3 to 29 days wide
and there are forty-five of them; the widest anywhere near the boundary are 1,797–1,819 (23 days)
and 1,835–1,856 (22 days), neither of which separates anything — 1,783–1,825 holds 133 windows and
1,826–1,900 holds 2,842.

This is unlike the TTM span, where two clean empty runs (5 and 58 days wide) handed over both
bounds. The reason is structural: a TTM window is broken in one way, by skipping a quarter, which
puts it a discrete ~91 days away from a legitimate one. A five-year window is broken by *whatever
gaps a ten-year reporting history happens to contain* — one missing quarter, a missing year, an
acquisition stub — and those come in every size. **A threshold could not have been derived from
this distribution.** That is the finding, and it is the argument for the rule chosen in §2.

### The size of the defect: 21% of windows are not five years

| | windows | share | tickers |
|---|---:|---:|---:|
| longer than 1,826 days (> 5 years) | 2,921 | **12.31%** | 476 of 489 |
| shorter than 1,700 days (< 4.65 years) | 2,076 | **8.75%** | 126 |
| **not a five-year window** | **4,997** | **21.05%** | — |

The extremes: **EXE reaches 4,110 days — 11.25 years** — and NXPI 4,106. The most affected tickers
are HBAN and MTB (266 and 259 over-long windows across the seven lines), BX, LHX, TTWO, CNC, GLW.

**Both directions are real defects, and the short one was not expected.** The steps inside the
window show each mechanism directly:

```
HBAN ending 2025-09-30, span 1,918 d:  [92, 92, 90, 275, 90, 91, 92, ...]   <- a missing quarter
LHX  ending 2025-01-03, span 2,107 d:  [462, 91, 91, 91, ...]               <- a missing year
BX   ending 2025-06-30, span 2,008 d:  [366, 90, 91, 92, ...]

BBY  ending 2023-07-29, span 1,638 d:  [1, 90, 91, 91, ...]                 <- an EXTRA row
WAT  ending 2025-09-30, span 1,095 d:  [91, 90, 1, 91, 91, 92, 90, 1, 90, 1, 90, 2, 92, 88, 2, ...]
```

**The extra rows are a population of their own: 193 pivot rows across 102 tickers sit 1–7 days
after their predecessor** (124 of them exactly one day) because different concepts of the *same*
quarter carry different end dates. Read off the raw frame:

```
BBY  2012-03-03  DividendsPerShare_TTM, EBITDA_TTM, EPS_TTM_CALC, FCF_TTM, LongTermDebt,
                 Revenue_TTM, ShareBasedCompensation_TTM, SharesOutstanding, StockholdersEquity
     2012-03-04  CashAndEquivalents

CAT  2016-12-31  nine concepts
     2017-01-01  StockholdersEquity

WAT  2025-06-28  CashAndEquivalents, LongTermDebt, ShareBasedCompensation_TTM, StockholdersEquity
     2025-06-30  EPS_TTM_CALC, Revenue_TTM, SharesOutstanding
```

This is a *different* population from the duplicated period ends fixed in the previous task. That
merge worked within a concept; these pairs are one quarter split **across** concepts, which a
per-concept pass cannot see. Waters alone contributes 16 of them, which is why its twenty-row
window covers 1,095 days — **exactly three years, sold as five**.

---

## 2. Part 1.2 — the rule

### Chosen: option 1, filter by date

```python
AVG_5Y_WINDOW = "1826D"     # 5 x 365.25, measured back from each row's own end
```

The window is every observation whose end lies in `(end − 1826 days, end]`.

**Why not option 2 (keep the row window, mask it when its span is wrong).** Two reasons, one of
them measured:

1. **There is no threshold to mask against.** Option 2 needs bounds, and §1 shows the distribution
   has no empty run to take them from. Any pair of numbers would be an assertion, and the TTM
   task's whole method was to avoid exactly that.
2. **Masking answers the wrong question.** A TTM window *must* hold four quarters — three quarters
   plus a hole is not a year, and no partial answer exists. A five-year mean over eighteen
   observations instead of twenty is still a five-year mean. Option 2 would delete 12.3% of the
   mean line rather than correct it, and would leave the 8.8% that are too *short* untouched,
   because their span looks unremarkable from the row side.

The failure mode of option 1, stated: **the observation count is no longer constant.** A clean
quarterly series yields twenty as before; a 52/53-week filer whose twentieth-oldest quarter sits at
1,820 days yields twenty-one; a series with a gap yields fewer. That is the intended behaviour —
`_n` is published precisely so the count is visible — but it does mean two tickers' means can rest
on different numbers of observations. They already could, because `_n` already varied through
masked multiples; now it varies for an honest reason.

**A second property, not the motivation but a real gain:** a row carrying no usable value no longer
displaces an older observation, because it occupies no time. Under the row window, a masked
multiple — negative earnings, missing FFO — consumed a slot and pushed a real observation out of
the window. The seven concepts share one row set, so a quarter present for *any* of the fourteen
needed concepts was consuming a slot in *all seven* means.

### The minimum observation count: unchanged, and deliberately so

`min_periods=1` stays. A mean is published from a single observation, exactly as before, and
`avg_*_5y_n` carries the count into the snapshot where `avg_*_5y_history_too_short` marks
`n < MIN_AVG_5Y_OBSERVATIONS = 12`.

The task asked for this to stay coherent with the existing machinery rather than introduce a second
notion of "not enough history", and the existing machinery is a *flag*, not a filter — it publishes
the number and labels it thin. Adding a hard cut-off would silently remove data the flag already
describes, and would mean two different rules for the same idea. What changes is that the flag now
tells the truth: under the row window a mean over 12 rows spanning nine years counted as
sufficient history.

### The anchor: five years back from the row's own end date

That is what a rolling mean means, and it is what `rolling(window="1826D")` does. The alternative —
five years back from a fixed reference such as today — would make the historical series a set of
overlapping windows all anchored at the present, which is not a series at all. (`calculate_peer_band_flags`
does use a fixed `today − 5 years` cutoff, correctly, because it computes one number per ticker
rather than a series. It is untouched.)

### The harmonic/arithmetic split is not affected — confirmed, not assumed

`HARMONIC_MEAN_CONCEPTS = {m.id for m in METRICS if m.harmonic}` is a per-metric flag in the config
registry that decides *which* multiples get a harmonic mean. The window decides *which observations*
enter it. The two are orthogonal, and the full inventory of rolling windows in the codebase
confirms there is nothing else to keep in step:

| site | window | status |
|---|---|---|
| `calculate_rolling_harmonic_stats` | was 20 rows | **fixed here** |
| `calculate_ttm` | 4 rows + calendar test | fixed in the TTM task |
| `apply_self_relative_scale_guard` | 17 rows, centered | genuinely positional — see §8 |
| `calculate_rolling_average` (arithmetic) | *n* rows | **zero call sites** |

`calculate_rolling_average` is the arithmetic sibling and has no callers anywhere in the project, so
the split cannot fall out of step through it. Left in place; removing dead code is not this task.

---

## 3. Part 2 — the growth comparison

### The two defects, and a third one underneath them

```python
wide["revenue_yoy_growth"] = wide.groupby("ticker")["Revenue_TTM"].pct_change(periods=4)
```

- **It counts rows.** Four rows back is four quarters back only on a series with exactly one row per
  quarter.
- **`fill_method="ffill"` is pandas' default**, so a missing `Revenue_TTM` is bridged by the previous
  value and the comparison is against a date other than the one intended.
- **It is a second implementation of a quantity the pipeline already computes.** `metrics.py`'s
  `calculate_growth` has done this by date since 2026-07-27, and `metrics["revenue_growth"]` — the
  Revenue growth panel, and the `yoy_growth` behind the *snapshot's* PEG — goes through it. Only
  `build_valuation_history` computed it a second, different way, so the snapshot's PEG and the
  history's PEG were built from two different growth numbers. The bugfix log records this as a
  deliberate narrow-scope tradeoff at the time ("a simplified version without the `min_base_ratio`
  near-zero-base guard … for chart display only"); the sidebar-encyclopedia task flagged the
  consequence ("The Revenue growth panel and this panel are two differently-computed numbers").

### The fix

```python
    # Four quarters back by calendar, not four rows back, and no forward fill. This is the
    # same lookup metrics["revenue_growth"] and the snapshot's PEG already use -- this was
    # the one place computing the quantity a second, different way.
    growth = calculate_growth(facts, "Revenue_TTM", 4, "revenue_yoy_growth")
    wide = wide.merge(growth[["ticker", "end", "revenue_yoy_growth"]], on=["ticker", "end"], how="left")
```

Reusing `calculate_growth` rather than writing a third date-based lookup is the point: it removes an
implementation, it removes the divergence between the two PEG series, and `fill_method` disappears
with the call that had it.

### The tolerance convention, and which quantity it bounds

`GROWTH_PERIOD_TOLERANCE_DAYS_PER_4Q = 45`, scaled as `periods × 45/4`, matching against
`end − periods × 365.25/4` with `direction="nearest"`.

**This bounds the lag between two observation dates that should be four quarters apart — 365.2 days.**
It is *not* the TTM window's span, which is the distance between the outer rows of a four-row window
and is 273.9 days. Same arithmetic, three steps versus four, and the two must not be confused.

The bound was calibrated in the 2026-07-27 growth-alignment task from an empty band at 380–430 days
(the brief attributes it to the TTM task; the TTM task contributed the empty-run *method*, not this
number). Re-measured here on the current data, the lag population is:

```
  364     3,913
  365    16,499                 <- calendar quarters
  366     5,737
  371       812                 <- 53-week fiscal years
  380         2
  ------------- nothing between 381 and 387 -------------
  ...                           2 values above 387, none at all above 410
```

93.8% at 364–367, 3.0% at 368–375. **±45 days is the right width for this quantity** and can be
shown to be safe rather than assumed: three quarters is 273.9 days and five is 456.6, each 91 days
from the target, so a window of ±45 cannot reach either. The observed extremes confirm it — the
largest lag in the whole population is 380 and the smallest inside the band is 356.

### What the old call was actually comparing against

```
  4-row lag       values   share
  0-180                5   0.02%
  181-270            109   0.39%     <- two quarters back
  271-320            673   2.41%     <- THREE quarters back
  321-355             43   0.15%
  356-380         27,049  97.01%
  381+                 2   0.01%
```

**787 growth values (2.82%, 130 tickers) had a base that was not four quarters old**, and the
failure is almost entirely in the *short* direction — the base was too *recent*, because the pivot
carries extra rows, not because quarters were missing. That is the same cross-concept extra-row
population as §1: WAT 43, BBY 25, JCI 20, CAT 20.

Separately, **845 growth values over 157 tickers were produced through `ffill`** — 514 where the
base row's `Revenue_TTM` was absent, 483 where the current row's was (some rows both). MAA 28,
TROW 28, WAT 27, O 26, EQR 25.

---

## 4. The two diffs

Applied as separate change groups, all 501 cached tickers, diffed after each.

### 4.1 — Part 1 diff (`before` → `after1`)

**Nothing outside the rolling aggregates moved, which is the required property:**

| frame | rows | appeared | changed | disappeared |
|---|---:|---:|---:|---:|
| base facts | 512,078 | 0 | **0** | 0 |
| facts (incl. every `_TTM`) | 978,477 | 0 | **0** | 0 |
| metrics_long | 463,416 | 0 | **0** | 0 |
| valuation_history (every single-period multiple) | 211,108 | 0 | **0** | 0 |
| snapshot | 20,457 | 0 | 272 | 0 |
| rolling `avg_*_5y` frame | 490,151 | 78 | **44,460** | 128 |

All 272 snapshot changes are `avg_*` fields — 47 `avg_pe_5y`, 42 `avg_pfcf_5y`, 30 `avg_ev_ebitda_5y`,
their `_median` siblings, and 8 flag flips. **This is the expected exception, stated up front**: the
task's purpose is to change these fields, and no other snapshot field moved.

**The 78 appearances and 128 disappearances are all on very thin series** (median `_n` of 1 or 2).
A disappearance is a row whose only positive observation is now more than five years old — MAA, MAR,
LHX, PCG, TTWO, VICI. An appearance is a row on a ticker whose *row* window was too short to reach
any positive observation and whose date window does — BA, WBD, FLEX, DLTR, WAT.

**Observation counts move in both directions, as the two mechanisms predict:**

| line | matched | `_n` unchanged | `_n` fell (median) | `_n` rose |
|---|---:|---:|---:|---:|
| avg_pe_5y | 28,243 | 24,808 | 1,672 (−2) | 1,763 |
| avg_p_ffo_5y | 27,828 | 24,543 | 1,540 (−2) | 1,745 |
| avg_pfcf_5y | 25,460 | 22,612 | 1,272 (−2) | 1,576 |
| avg_p_tbv_5y | 24,356 | 21,445 | 1,320 (−2) | 1,591 |
| avg_ev_ebitda_5y | 20,818 | 18,512 | 1,098 (−2) | 1,208 |
| avg_p_ppnr_5y | 1,317 | 1,113 | 136 (−2) | 68 |
| avg_p_core_earnings_5y | 807 | 784 | 2 (−1) | 21 |

**Anchor invariant: 0 newest dates moved, 0 newest values moved.** Part 1 cannot move them — it
touches no fact.

**Flags: coverage 737 → 737, `share_count_jump_flag` 718 → 718, `buyback_distortion_flag` 635 → 635 —
all unchanged.** The `avg_*` companions move only slightly: `_history_too_short` 161 → 162
(`avg_ev_ebitda_5y` 65 → 67, `avg_pe_5y` 34 → 33), `_diverges` 106 → 107 (`avg_pe_5y` 53 → 55,
`avg_p_ffo_5y` 3 → 2).

### 4.2 — Part 2 diff (`after1` → `after2`)

**Confined to exactly one concept, which is the whole intended footprint:**

| frame | rows | appeared | changed | disappeared |
|---|---:|---:|---:|---:|
| base facts | 512,078 | 0 | 0 | 0 |
| facts | 978,477 | 0 | 0 | 0 |
| metrics_long | 463,416 | 0 | **0** | 0 |
| valuation_history | 211,108 → 210,952 | 23 | 232 | 179 |
| snapshot | 20,457 | 0 | **0** | 0 |
| rolling `avg_*_5y` | 490,101 | 0 | **0** | 0 |

All 23 appeared, 232 changed and 179 disappeared are `pe_to_revenue_growth`, over **122 tickers**.
Net −156 rows. Nothing else in the frame moved, and the row count of every other multiple is
identical, which also confirms the `merge` did not duplicate a single row.

`metrics_long` at 0 is the confirmation that the Revenue growth panel was **already** date-based —
this change brought the history's copy into line with it, it did not move the panel.

### The two deltas, reported separately

**The growth delta** (`revenue_yoy_growth`, an internal column of `build_valuation_history`, not
published anywhere):

```
old (4-row pct_change) vs new (date-based calculate_growth), 27,881 values
  identical         26,652   95.6%
  different            487    1.7%
  disappear            742    2.7%      173 tickers: MAA 28, TROW 28, O 26, EQR 25, MOS 22, BBY 20
  appear                 0
```

**The PEG delta** (`pe_to_revenue_growth`, the published concept): 17,208 → 17,052.

```
  disappeared 179   BX 8, AME 7, APP 7, CINF 7, TROW 7, O 7, KEYS 7, ITW 6, UDR 6
  appeared     23   KDP 3, DPZ 2, then 18 tickers with one each
  changed     232
  one ticker loses PEG entirely: VTRS.  None gains it entirely.
```

The two are far apart (742 vs 179) because a growth value only reaches PEG where a `pe_ratio` also
exists and the growth clears the 2% floor.

**The `MIN_PEG_REVENUE_GROWTH = 0.02` interaction**, measured on the growth column before the floor
is applied: values above the floor go 19,149 → 18,818, with **359 crossing downward** (published →
blank) and **28 crossing upward**. Both previous reports traced a PEG appearing or vanishing to
exactly this; here the crossings are counted rather than inferred.

### The 232 changes, justified

Every large change is the same mechanism, and it is the *same* mechanism as the short rolling
windows — the extra pivot rows of §1 shifting what "four rows back" reaches:

```
CIEN 2020-05-02   PEG 9.588 -> 1.272
  4 rows back = 2019-10-31, lag 184 days -- TWO quarters, not four
    Revenue_TTM 3,655.6m / 3,572.1m - 1 =  2.3%   (a half-year change, used as a year)
  date base   = 2019-05-04, lag 364 days
    Revenue_TTM 3,655.6m / 3,108.5m - 1 = 17.6%
  CIEN's rows: 2019-07-31(NaN) 2019-08-03 2019-10-31 2019-11-02(NaN) 2020-01-31(NaN) 2020-02-01

AIG  2021-09-30   PEG 0.852 -> 1.973
  4 rows back = 2020-12-31, lag 273 days -- three quarters; the extra row is 2021-01-01
  date base   = 2020-09-30, lag 365 days

CAT  2017-09-30   PEG 7.529 -> 13.112
  4 rows back = 2016-12-31, lag 273 days; the extra row is 2017-01-01 (StockholdersEquity alone)
  date base   = 2016-09-30, lag 365 days
```

### Independent check: the two PEG series now agree

`pe_to_revenue_growth` in the valuation history should be reproducible from `pe_ratio` and the
*Revenue growth panel's* own growth figure in `metrics_long`, since after the fix both come from
`calculate_growth`. Rebuilt from those two frames and compared:

| | before Part 2 | after Part 2 |
|---|---:|---:|
| published PEG values | 17,208 | 17,052 |
| reproducible from the panel's growth | 15,969 | 15,969 |
| both present, **identical** | 15,717 | **15,969** |
| both present, **different** | **229** | **0** |
| reproducible but not published | 23 | **0** |

The 1,083 published-but-not-reproducible rows in both columns are **29 REITs whose `pe_ratio` is
hidden by profile** while PEG is not, so the rebuild has no numerator — not a growth disagreement.
(That a profile publishes PEG while hiding P/E is a config question, noted in §8.)

### The `FutureWarning`

Measured with the same instrument before and after — every warning `build_valuation_history` and
`calculate_rolling_multiple_averages` emit, recorded over the full 501-ticker frame:

```
before:  warnings 1   FutureWarning 1
         "The default fill_method='ffill' in SeriesGroupBy.pct_change is deprecated ..."  main.py:810
after:   warnings 0   FutureWarning 0
```

It was the only warning either function emitted.

### The two groups are disjoint

`before → after2` is exactly the sum of the two diffs: 0 base facts, 0 facts, 0 metrics_long,
272 snapshot (all `avg_*`), 44,460 rolling, and 23/232/179 on `pe_to_revenue_growth`. Neither group
touched the other's territory.

---

## 5. The mean-line effect, stated plainly

**Part 1 moves 11–15% of the points on every mean line but one.**

| line | points | changed | share |
|---|---:|---:|---:|
| `avg_p_ppnr_5y` | 1,317 | 204 | **15.5%** |
| `avg_pe_5y` | 28,249 | 3,435 | **12.2%** |
| `avg_p_tbv_5y` | 24,370 | 2,911 | **12.0%** |
| `avg_p_ffo_5y` | 27,834 | 3,285 | **11.8%** |
| `avg_pfcf_5y` | 25,484 | 2,848 | **11.2%** |
| `avg_ev_ebitda_5y` | 20,832 | 2,306 | **11.1%** |
| `avg_p_core_earnings_5y` | 807 | 23 | 2.9% |

The `_median` siblings move slightly less on each line (2.9–14.7%), the `_n` counts 0.07–10.4%.

Against the precedent: the TTM task moved ~25% of points, the duplicate-ends task 2–5%, the
decumulation task 0.2–0.6%. **This one lands second, at 11–15%** — which is roughly what §1
predicts, since 21% of windows were the wrong length and a wrong-length window only changes the
mean if the observations it wrongly holds (or wrongly misses) carry a usable value.

`avg_p_core_earnings_5y` is the outlier at 2.9% because it exists for 15 tickers, all insurers with
uninterrupted quarterly histories.

**How large are the moves.** Most are small; the large ones are all on thin series, where a window
holding three observations and a window holding one are genuinely different statistics:

```
PCG   avg_pfcf_5y      2022-12-31    116.62 ->  1113.96    n  3 -> 1
EQT   avg_pe_5y        2020-12-31     56.52 ->   267.14    n  4 -> 2
TTWO  avg_ev_ebitda_5y 2019-12-31     11.35 ->    58.75    n 12 -> 8
TRGP  avg_p_tbv_5y     2024-12-31      2.51 ->     9.07    n 11 -> 6
FITB  avg_p_ppnr_5y    2015-06-30      3.15 ->     3.83    n 20 -> 18
```

Every one of these carries `avg_*_5y_history_too_short` in the snapshot, which is the field that
exists to say so.

---

## 6. The independent checks

### 6.1 — The arithmetic, against an implementation that shares no code

A naive per-ticker Python loop — no pandas rolling, no groupby, an explicit date mask per row —
recomputed the harmonic mean, median and count for **every row of every line**:

```
avg_ev_ebitda_5y        33,195 rows   0 mismatches
avg_p_core_earnings_5y  33,195 rows   0 mismatches
avg_p_ffo_5y            33,195 rows   0 mismatches
avg_p_ppnr_5y           33,195 rows   0 mismatches
avg_p_tbv_5y            33,195 rows   0 mismatches
avg_pe_5y               33,195 rows   0 mismatches
avg_pfcf_5y             33,195 rows   0 mismatches
                       232,365 rows   0 mismatches
```

This also discharges the one assumption the implementation makes. `groupby(...).rolling(on=...)`
returns a `(ticker, end)` MultiIndex that cannot be aligned back onto the frame by index, so the
result is assigned positionally, which is only valid because the frame is sorted by ticker then end
and groupby walks the tickers in that order. **Verified over the whole frame rather than asserted.**

A second check recomputed 168 sampled windows by hand from the calendar-filtered series
(12 tickers per line, newest row and a mid-history row): **0 mismatches**.

### 6.2 — TSLA: which value is right, and why

The duplicate-ends task reported `avg_p_ffo_5y` moving 68.67 → 70.73 with `_n` going 19 → 20, on a
ticker where no value had changed. **The correct window produces 70.73** — the new calendar window
leaves it at exactly 70.7318, unchanged from the current state:

```
TSLA avg_p_ffo_5y at 2026-06-30   n = 20   span 1,734 days = 4.75 y   (limit 1,826)
  2021-09-30  164.69   1734 days back        2024-03-31   35.19    821 days back
  2021-12-31  160.55   1642 days back        2024-06-30   42.34    730 days back
  2022-03-31  119.50   1552 days back        2024-09-30   54.65    638 days back
  2022-06-30   66.63   1461 days back        2024-12-31  126.00    546 days back
  2022-09-30   68.30   1369 days back        2025-03-31   87.31    456 days back
  2022-12-31   28.58   1277 days back        2025-06-30  107.57    365 days back
  2023-03-31   50.17   1187 days back        2025-09-30  158.52    273 days back
  2023-06-30   60.60   1096 days back        2025-12-31  179.81    181 days back
  2023-09-30   63.06   1004 days back        2026-03-31  144.82     91 days back
  2023-12-31   47.26    912 days back        2026-06-30  161.07      0 days back
  hand harmonic mean = 70.7318
```

**Why 70.73 and not 68.67.** TSLA's twenty most recent rows span 1,734 days, comfortably inside
five years, so the row window and the date window hold the same twenty observations and agree.
68.67 came from a nineteen-observation window: a duplicated period end was occupying one of the
twenty row slots, and the observation it displaced was a real quarter. The previous task removed the
duplicate; this task makes the result independent of whether it had. TSLA is now unchanged in this
diff — the point is that it can no longer move for that reason.

### 6.3 — The two mechanisms, at a point where each bites

```
HBAN  avg_pe_5y at 2018-03-31        7.679 (n=20)  ->  8.355 (n=16)
  20-row window  2012-06-30 .. 2018-03-31   2,100 days = 5.75 y
  date window    2013-06-30 .. 2018-03-31   1,735 days
  dropped: 2012-06-30, 2012-09-30, 2012-12-31, 2013-03-31   (four quarters of 2012 crisis-era P/E)

WAT   avg_pe_5y at 2021-12-31       26.930 (n=10)  -> 33.207 (n=15)
  20-row window  2018-12-31 .. 2021-12-31   1,096 days = 3.00 y
  date window    2017-04-01 .. 2021-12-31   1,735 days, 28 rows
  added: 2017-04-01, 2017-07-01, 2017-09-30, 2017-12-31, 2018-03-31, 2018-06-30, 2018-09-29, 2018-09-30
```

HBAN's five-year mean was carrying four quarters from six years earlier. Waters' was a **three-year**
mean labelled five, because its extra rows had eaten eight slots — and note `2018-09-29` and
`2018-09-30` in the added list, the extra-row population of §1 caught in the act.

Both windows land on 1,735 days, which is the figure §1 stated before measuring.

---

## 7. Flags, re-measured

| flag | before | after both parts |
|---|---:|---:|
| coverage flags (`check_data_quality`) | 737 | **737** |
| `share_count_jump_flag` = 1 | 718 | **718** |
| `buyback_distortion_flag` = 1 | 635 | **635** |
| `avg_*_5y_history_too_short` = 1 (all seven) | 161 | 162 |
| `avg_*_5y_diverges` = 1 (all seven) | 106 | 107 |

The first three cannot move and do not: they are computed from facts, which neither part touches.
The `avg_*` companions move by one or two — `avg_ev_ebitda_5y_history_too_short` 65 → 67,
`avg_pe_5y_history_too_short` 34 → 33, `avg_pe_5y_diverges` 53 → 55, `avg_p_ffo_5y_diverges` 3 → 2 —
which is the correct magnitude for fields that describe the newest window on 395–495 tickers.

`SNAPSHOT_AS_OF_DATES` is empty, so no historical snapshots were produced; had it not been, they
would move exactly as the current one does, since `build_snapshot_as_of` slices this same rolling
frame.

---

## 8. What was implemented

**Part 1** — `metrics.py`:

```python
def calculate_rolling_harmonic_stats(
    df: pd.DataFrame, value_col: str, window: str, result_prefix: str
) -> pd.DataFrame:
    df = df.sort_values(["ticker", "end"]).copy()
    positive = df[value_col].where(df[value_col] > 0)

    work = df[["ticker", "end"]].copy()
    work["_value"] = positive.to_numpy()
    work["_inverse"] = 1 / positive.to_numpy()

    rolling = work.groupby("ticker").rolling(window=window, on="end", min_periods=1)

    df[result_prefix] = 1 / rolling["_inverse"].mean().to_numpy()
    df[f"{result_prefix}_median"] = rolling["_value"].median().to_numpy()
    df[f"{result_prefix}_n"] = rolling["_value"].count().to_numpy()
    return df[["ticker", "end", result_prefix, f"{result_prefix}_median", f"{result_prefix}_n"]]
```

`main.py`: `AVG_5Y_WINDOW = 20` → `AVG_5Y_WINDOW = "1826D"`. `MIN_AVG_5Y_OBSERVATIONS = 12` and
`MIN_AVG_5Y_DIVERGENCE = 0.20` unchanged.

**Part 2** — `main.py`, inside `build_valuation_history`:

```python
    growth = calculate_growth(facts, "Revenue_TTM", 4, "revenue_yoy_growth")
    wide = wide.merge(growth[["ticker", "end", "revenue_yoy_growth"]], on=["ticker", "end"], how="left")
```

replacing `wide["revenue_yoy_growth"] = wide.groupby("ticker")["Revenue_TTM"].pct_change(periods=4)`.
No new constant: the tolerance is `calculate_growth`'s existing `GROWTH_PERIOD_TOLERANCE_DAYS_PER_4Q = 45`.

---

## 9. Deliberately not fixed

**The cross-concept extra rows — 193 pivot rows on 102 tickers.** This is the root cause behind both
of this task's symptoms: it makes twenty rows span three years (WAT) and it makes "four rows back"
reach two quarters (CIEN). Both *consumers* are now immune, because both now count days. The rows
themselves remain, and they still mean a ticker gets two `pe_ratio` points a day apart for one
quarter, priced at two different closes. Fixing that means deciding that `StockholdersEquity` at
2017-01-01 and the other nine concepts at 2016-12-31 are the same period end — a cross-concept
alignment pass in the parser, with its own diff, and a larger blast radius than either change here.
**It is the natural next task, and it is now the only place this defect can still surface.**

**`apply_self_relative_scale_guard` uses a 17-row centered window** (`REVENUE_SELF_SCALE_WINDOW = 8`).
Left alone on purpose: it asks "is this value implausibly small next to its neighbours", which is a
genuinely positional question about a value's surroundings, not a claim about a period of time. It
is also scale work, which the task excludes.

**`calculate_rolling_average` is dead code** — the arithmetic sibling, zero call sites. Not removed;
deleting unused functions is not this task.

**`min_periods=1` still publishes a mean from a single observation.** Kept deliberately (§2), and it
is why the largest moves in §5 are on series with `_n` of 1–4. The existing
`avg_*_5y_history_too_short` flag is the mechanism that describes them, and adding a second one
would have been the incoherence the task warned against.

**`calculate_peer_band_flags` anchors on `pd.Timestamp.today()`**, so its five-year peer window
moves with the run date rather than with the data. Correct for a one-number-per-ticker flag, but it
does mean the flag is not reproducible from a fixed dataset. Untouched — not a rolling window, and
outside the scope.

**REIT profiles publish `pe_to_revenue_growth` while hiding `pe_ratio`** (29 tickers, 1,083 rows,
found while building the §4.2 check). A config/visibility question, not a computation one.

**`AVG_5Y_WINDOW` is 1,826 days, and five calendar years is 1,826 or 1,827.** The one-day slack can
only ever exclude an observation five years and one day old. Using a true `DateOffset(years=5)` is
not available to `rolling`, and the alternative — a per-row calendar subtraction — would cost a
Python loop for a boundary that no observation in the measured population sits on.

**Everything outside the two windows**, per the task's scope: no `calculate_ttm` change, no
`extract_period_values` / `decumulate_period_values` change, no split/scale/tag work, no
`apply_denominator_scale_guard` or `ffo.fillna(0)` fix, no coverage-flag semantics, no UI or chart
changes, no new metrics.

---

## Files changed

| file | change |
|---|---|
| `metrics.py` | `calculate_rolling_harmonic_stats` takes a calendar window instead of a row count |
| `main.py` | `AVG_5Y_WINDOW = "1826D"`; `build_valuation_history` uses `calculate_growth` for `revenue_yoy_growth` |
| `MDs/metrics.md` | documents both, in the sections that describe the windows |
| `MDs/main.md` | the `revenue_yoy_growth` convention in `build_valuation_history` |
| `MDs/bugfixes_opdate_history.md` | entry per convention |
| `rolling_window_report.md` | this file |

`data/` and `figures/` untouched; no refresh was run; no scratch scripts left behind.

### Verification performed

- 166,138 twenty-row windows measured for span across 489 tickers and 7 concepts; expected figure
  (1,734.9 days) stated from the arithmetic before measuring and confirmed by the mode.
- Full-frame independent recomputation of all three outputs against a naive per-ticker loop sharing
  no code with the implementation: **232,365 rows, 0 mismatches** — which also discharges the
  positional-alignment assumption.
- 168 hand-recomputed windows from the calendar-filtered series: 0 mismatches.
- Two diffs over all 501 cached tickers, every appeared / changed / disappeared value accounted for,
  plus the combined diff confirming the groups are disjoint.
- Anchor invariant: 0 newest dates moved, 0 newest values moved, in both groups.
- `FutureWarning` count measured with the same instrument before (1) and after (0).
- PEG convergence against the Revenue growth panel: 229 disagreements → 0.
- Three largest PEG changes traced to the actual base dates in the raw pivot.
- All modules re-imported after the change.
