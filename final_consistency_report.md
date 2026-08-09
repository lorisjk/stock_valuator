# Final Consistency Items

Four items each earlier task recorded and left standing, plus one evaluation. They are
independent, so each is its own change group with its own diff.

**Method.** One price capture for the whole task — 501 tickers, 2,473,488 daily closes, no
fetch failures — because `get_price_history` is not bit-reproducible across calls. Base facts
re-derived from the same EDGAR cache on every side (`check_staleness=False`), 512,659 rows on
all five runs. Five full pipeline runs: `before`, `afterA`, `afterB`, `afterC`, `afterD`.

**Result in one line: 107 snapshot values appeared, 112 disappeared, and nothing else in the
project moved at all.** Base facts, facts, `metrics_long`, `valuation_history` and every
`avg_*_5y` line are byte-identical from `before` to `afterD`.

---

## Part A — `apply_self_relative_scale_guard`'s 17-row window

### A.1 The brief's description of the window is off by a factor of two

`window=8` gives `2*8+1 = 17` rows, which is **eight quarters either side, not four years
either side** — four years of total span. The measurement confirms it: the modal span of a
full 17-row window is **exactly 1,461 days**, sixteen quarter-steps, ±730.

### A.2 The span distribution

Every 17-row window the guard forms, over all 501 tickers and both frames it covers:

| | `operating_margin` | `fcf_margin` |
|---|---|---|
| rows | 24,566 on 420 tickers | 27,194 on 466 tickers |
| full 17-row windows | 18,015 (73.3%) | 19,876 (73.1%) |
| median span | 1,461 | 1,461 |
| p95 / p99 | 1,465 / 1,582 | 1,588 / 2,003 |
| max | 3,927 (10.8 y) | 4,475 (12.3 y) |

```
span (days)      operating_margin        fcf_margin
   <1,400              73   0.41%            48   0.24%
1,400..1,500       17,077  94.79%        17,557  88.33%
1,500..1,600          685   3.80%         1,277   6.42%
1,600..1,800           94   0.52%           606   3.05%
1,800..2,200           52   0.29%           286   1.44%
2,200..3,000           11   0.06%            47   0.24%
3,000..5,000           23   0.13%            55   0.28%
```

**Tail:** 180 windows over 1,600 days on 30 tickers and 73 over five years on 10 (op margin);
994 on 111 tickers and 304 on 36 (fcf margin). Worst offenders IP 15, TROW 13, HST 9 and
NVDA 31, INTU 30, ETR 20.

### A.3 There is no empty run here either, and the reason is structural

The brief asked whether the rolling-window task's reasoning applies. **It does.** The widest
gaps in the `fcf_margin` support are 91, 91, 90, 90, 89, 89, 89, 89 days — the quarter step
itself. A span is a sum of quarter-steps, so its support is a lattice with ~91-day spacing,
and the distribution decays smoothly through 1,553 / 1,645 / 1,736 / 1,826 / 1,918: one, two,
three, four, five missing quarters. Every "gap" is the lattice spacing, not a boundary between
two populations. The one wide gap (3,652 → 4,383) sits in a tail of a few dozen observations.

So no threshold can be derived from the data, which is precisely the argument for **defining
the window directly rather than masking a wrong one** — the same conclusion, on the same
evidence, as the five-year window.

### A.4 What centring implies, stated before designing

The window looks forward as well as back. Two consequences, both real:

1. **The guard is not causal.** A row's visibility can change when a *later* period is filed,
   because a new, much larger revenue raises the window maximum behind it.
2. **An as-of view does not reproduce it.** `build_snapshot_as_of` cuts rows after the metrics
   are computed, so the surviving margins were guarded using data from after the cut.

**Kept centred anyway.** The quantity is "the scale of this business around this period", which
is symmetric. A backward-only reference would judge the early years of a company that later
grew twentyfold against nothing at all, and the years after a divestiture against a business
that no longer exists. Making it causal is a different, more conservative guard that would
change the 27% of rows sitting near a series start, and no evidence in this measurement asks
for it. The non-causality is recorded in the docstring rather than removed.

### A.5 The rule, and the minimum-observation question

Date-filter, `[end - 730d, end + 730d]`, both ends closed (`f"{2*half+1}D"` with
`center=True`). The quantity is a calendar statement, so the window is one.

**No new notion of "too thin" is needed, and that is a property rather than a choice.**
`min_periods=1` puts the row in its own window, so a row with no neighbours is compared
against itself and `|ref| < 0.10 * |ref|` is False — it passes. That is the same "cannot
evaluate, therefore do not blank" behaviour `apply_denominator_scale_guard` has with a missing
reference, and it means the guard degrades gracefully at the series ends without a second
concept alongside `avg_*_5y_history_too_short`. Measured: 8 and 11 rows have a window holding
only themselves; 490 and 340 have fewer than five neighbours.

### A.6 The change moves no value — and the reason is the interesting part

| | `operating_margin` | `fcf_margin` |
|---|---|---|
| blanked, row rule | 20 | 26 |
| blanked, date rule | 20 | 26 |
| un-blanked by the change | 0 | 0 |
| newly blanked | 0 | 0 |

That is not because the two rules agree. **They disagree about the reference on a quarter of
all rows:**

```
                              operating_margin        fcf_margin
rows with a different max     6,086 (24.77%)          6,782 (24.94%)
  on tickers                    397                     445
row rule sees a LARGER max    6,078 of 6,086          6,780 of 6,782
row_max / date_max: median      1.024                   1.024
                       p95      1.114                   1.136
                       max      5.939                   4.051
```

The row window reaches further back in time and so sees a bigger maximum — by 2.4% at the
median and up to **5.9x** at the worst. The conclusion survives anyway because **the guard
fires at a factor of ten and the error is a factor of 1.02**: among the differing rows the
smallest `|ref| / max` is 0.0543 under the row rule and 0.0636 under the date rule, both
already below 0.10, so those rows are blanked either way. **Fourteen rows sit in
[0.10, 0.15)** — that is exactly how much headroom the "no change today" result has, and it is
a property of this data rather than of the rule.

### A.7 Verification

`apply_self_relative_scale_guard` assigns positionally (`.to_numpy()`) because
`groupby(...).rolling(on=...)` returns a `(ticker, end)` MultiIndex that cannot be aligned by
index — the same trap that produced an all-NaN column in the rolling-window task. Checked the
same way: **51,760 rows recomputed by a naive per-ticker Python loop sharing no code with the
implementation, 0 mismatches.**

### A.8 Diff (`before` → `afterA`)

```
base_facts          512,659 -> 512,659    appeared 0  changed 0  disappeared 0
facts             1,120,570 -> 1,120,570  appeared 0  changed 0  disappeared 0
metrics_long        693,135 -> 693,135    appeared 0  changed 0  disappeared 0
valuation_history   472,080 -> 472,080    appeared 0  changed 0  disappeared 0
snapshot             25,372 -> 25,372     appeared 0  changed 0  disappeared 0
rolling (all 21 columns)                  appeared 0  changed 0  disappeared 0
anchors 18,877: date moved 0, value changed 0    quality flags 734 -> 734
peer bands 2,106: appeared 0, disappeared 0, flipped 0
```

Stated up front and confirmed: zero.

---

## Part B — `calculate_peer_band_flags` anchored on `pd.Timestamp.today()`

### B.1 What the anchor costs, measured

Re-running **the same cached data** with only the run date moved:

```
anchor        flags   appeared  disappeared  flipped
today          2,106         -            -        -
  +30 d        2,106         0            0        1
  +60 d        2,103         0            3        7
 +182 d        2,097         0            9       19
 +365 d        2,090         0           16       35
 -182 d        2,115         9            0       20
 -365 d        2,124        18            0       38
```

**35 of 2,106 flags change and 16 vanish over a year of run-date drift with no new data.**
353 of the 2,106 are currently elevated, so the drift is ~10% of the positive flags.

### B.2 The fix, and the second copy of a windowing rule

`as_of: pd.Timestamp | None = None`, `None` keeping today's behaviour. The window arithmetic
is now `within_avg_5y_window`, which uses `AVG_5Y_WINDOW` — the same definition
`calculate_rolling_harmonic_stats` uses. It was `pd.Timestamp.today() - pd.DateOffset(years=5)`
here and `1826D` there: the second divergent copy of a windowing rule this project has had to
consolidate, after the two revenue-growth computations.

On this run date the two agree exactly (both land on 2021-08-09; 0 valuation-history rows lie
between them), which is why the consolidation costs nothing here and would cost a day whenever
a leap day falls differently. The helper also **closes** the window at the anchor, which the
`today()` form never needed and an as-of view does — 0 rows are affected today because no
period end lies in the future.

### B.3 Does the app pass its `as_of` through to these flags?

**No, and it structurally cannot — but nothing is silently current either.** Three findings:

- The app reads **precomputed** parquet frames. Its `as_of` is a chart-window filter
  (`figures._window_frame`) and a suppression rule for the snapshot marker. It recomputes
  nothing, so there is no path by which it could reach `calculate_peer_band_flags`.
- The only place an as-of view is *computed*, `build_snapshot_as_of`, passes no
  `peer_band_flags` at all. So an as-of snapshot carries **no** band flags — absent, not stale.
- `SNAPSHOT_AS_OF_DATES` is empty, so no as-of snapshot is produced today in any case.

The parameter is added so the one place that could emit them has a correct way to. Wiring band
flags into `build_snapshot_as_of` would put new fields into a historical view, which is a
feature rather than a consistency fix, and the brief excludes new metrics.

**The cross-ticker property matters more here than anywhere else.** Every other flag is a
function of its own ticker's data. This one compares against a peer **median**, so one ticker
gaining or losing an observation moves another ticker's output — three band flags moved that
way in the annual-gate task without those tickers' own data changing at all. A window whose
start depends on when the pipeline happened to run therefore propagates across the universe.

### B.4 Diff (`afterA` → `afterB`)

Zero in every frame, including the peer bands themselves (2,106 → 2,106, 0 flipped) — as B.2
predicted, since the two cutoffs coincide on this run date. The value of the change is that the
next run gives the same answer.

---

## Part C — the two scale-guard constants

### C.1 The disagreement, on every guarded multiple

Rows published by the history and the count each constant would blank:

```
                published   fires@0.001   fires@0.01   disagree
pe_ratio           26,611            28          484        456
pfcf_ratio         22,257            39          454        415
pfcf_ex_sbc        19,651            27          414        387
ev_fcf             18,917            37          418        381
p_tbv              19,880            27          250        223
p_ffo              26,087             7          150        143
ev_ebitda          18,294             7           86         79
p_core_earnings       664             1            9          8
pb_ratio           24,805             3            9          6
p_ppnr              1,321             0            1          1
```

Only `pb_ratio` and `p_tbv` are actually computed twice with different constants, so the live
disagreement is **6 history rows and 8 snapshot markers for `p_tbv`, 6 and 6 for `pb_ratio`**.

### C.2 The larger half of the disagreement was not the constant at all

Measuring the two expressions side by side turned up something the brief did not name: the
snapshot **has no positivity mask on the denominator**, while the history has one
(`StockholdersEquity.where(> 0)`, `TangibleEquity.where(> 0)`).

```
snapshot p_tbv    : 458 published, 111 NEGATIVE, min -201.30
snapshot pb_ratio : 386 published,   1 NEGATIVE, min   -4.22
history  p_tbv    : 19,880 published, 0 negative
history  pb_ratio : 24,805 published, 0 negative
```

**111 of 458 published `p_tbv` markers were negative**, drawn onto valuation charts whose line
is blank at that period by construction. Step 3 of this part — "the marker and the line agree
on every published point" — cannot be satisfied without fixing this, so it is part of C.

### C.3 Which constant is right, argued on the measurement

The alignment task's warning applies: do not pick the stricter one because the values it kills
look bad. So, the populations:

```
pb_ratio   passes both  n=24,796  median   2.38   p99  29.3   max     352.2
           band only    n=     6  median 268.74               max     827.2
           blanked@.001 n=     3  median 9,981.04             max 1,069,650
p_tbv      passes both  n=19,630  median   4.83   p99 127.0   max   1,007.7
           band only    n=   223  median 279.50               max   6,815.9
           blanked@.001 n=    27  median 3,485.80             max 1,236,338
```

The band population is far outside the normal one — which is an argument for tightening, until
you look at what 0.01 actually rejects. **Cencora (COR) has $3.05bn of equity against $332.8bn
of revenue — 0.92% — and a P/B of 20.0.** That is a real, thin-equity distribution business,
and 20.0 sits inside the population 0.01 passes (p99 = 29.3). One percent of revenue is inside
the range a genuinely low-margin, high-turnover filer occupies; a tenth of a percent is not.
So 0.01 is not separating broken denominators from usable ones at that level — it is
misclassifying a business model.

Two structural points decide the rest:

- **0.01 is the *metrics* constant** (`MIN_DENOMINATOR_SCALE_RATIO`, shared with ROE, ROTCE
  and the effective tax rate). Its appearance here is inheritance from before the valuation
  constant existed, not a calibration anyone performed for these multiples. After the change it
  is used only by those three metrics again.
- **Unifying downward leaves exactly one constant governing valuation multiples in both code
  paths.** Unifying upward would leave two of the ten multiples in
  `build_valuation_history`'s guard loop at 0.01 and eight at 0.001, an exception with no
  reason behind it but the snapshot's inheritance, and would remove 229 history points.

**Decision: 0.001, plus the positivity mask.**

*One honest caveat.* The Cencora example demonstrates the miscalibration but does not itself
produce a visible change: COR's tangible equity is −$13.5bn, so the existing
`TangibleEquity < 0` veto blanks its `pb_ratio` regardless of the constant. The same is true of
all six `pb_ratio` band tickers (GDDY, HPQ, MTD, LYV, COR, CLX), which is why no `pb_ratio`
marker appears in the diff below.

### C.4 Diff (`afterB` → `afterC`)

```
snapshot   25,372 -> 25,264    appeared 4   changed 0   disappeared 112
  appeared     p_tbv     4   AVY, CE, CHRW, JBL
  disappeared  p_tbv   111   every negative marker
               pb_ratio  1   the single negative marker
```

Everything else zero: base facts, facts, `metrics_long`, `valuation_history`, `rolling`,
anchors, quality flags, peer bands, and all seven mean lines at 0.000%.

### C.5 Verification — the marker and the line now agree on every point

A predicate check over all 501 tickers, asserting `published ⟺ denominator > 0 and
|denominator| ≥ 0.001·|scale|` (plus the tangible-equity veto for `pb_ratio`):

```
pb_ratio : expected 385 published, actually 385, mismatches 0, negatives 0
p_tbv    : expected 351 published, actually 351, mismatches 0, negatives 0
```

The four new markers reconstruct exactly from price × share count and the raw balance-sheet
tags:

```
      TangibleEquity        / Revenue_TTM   = ratio     0.001?  0.01?   market_cap/TE   snapshot
AVY      60,800,000           9,248,100,000   0.00657    pass   fail        222.9041    222.9041
CE       16,000,000           9,712,000,000   0.00165    pass   fail        301.0550    301.0550
CHRW    119,355,000          16,996,512,000   0.00702    pass   fail        146.2121    146.2121
JBL      95,000,000          33,590,000,000   0.00283    pass   fail        376.3732    376.3732
```

And the removals: **all 111 tickers have a negative newest `TangibleEquity`, and for all 111 the
history's `p_tbv` line has no point at that period.** The markers were floating above nothing.

---

## Part D — `get_latest_value` returning a null newest row

### D.1 The exposure

Every concept `build_snapshot` reads through `get_latest_value`:

```
concept                       tickers  null newest  recoverable  no value at all
DividendsPerShare_TTM             407           53           49                4
FFO_TTM                           499           15           14                1
ShareBasedCompensation_TTM        493            8            8                0
EPS_TTM_CALC                      498            7            7                0
Revenue_TTM                       501            4            4                0
CoreOperatingEarnings              15            1            1                0
SharesOutstanding / StockholdersEquity / LongTermDebt /
CashAndEquivalents / TangibleEquity / PPNR          0            0                0
```

**83 (ticker, concept) pairs on 69 tickers**, concentrated exactly where the annual-gate task
predicted: `DividendsPerShare` is declared when a board declares one, so its newest rows are
routinely empty.

### D.2 The distance distribution, which is where the bound comes from

```
 90   1      273  11      546   5      1,004  5      2,099  2      3,466  1
 91   2      274   1      547   1      1,096  1      2,282  1      4,291  1
181  10      364   2      638   2      1,186  1      2,373  2      4,293  1
182   3      365   6      640   1      1,369  3      2,374  1      4,565  1
184   1              <-- 366..545 empty -->  1,461  1      2,465  1      4,929  1
                                             1,734  1      2,466  1      5,021  1
```

Median 546, p90 2,684, **max 5,021 days — a dividend from 2012**. This is why the obvious form
of the fix is worse than the bug.

**The bound is 365 days**, and it comes from the definition: a TTM figure covers twelve months,
so a value whose period ended more than four quarters before the concept's newest row describes
a year that no longer overlaps the one the newest period would cover. The measurement
corroborates without being what chose it — the lattice stops at 365 and does not resume until
546, so **every bound in [365, 545] selects the identical 37 pairs**. The choice is insensitive
across a 180-day range. (With 83 observations that run is corroboration, not derivation; the
definitional argument is the one carrying the weight.)

```
bound   admits   rejects
  200       17        66
  273       28        55
  365       37        46
  546       42        41
```

**The age is measured inside the series, not against today**, which keeps it from duplicating
`days_since_last_filing` / `fundamentals_stale`. A filer whose whole series ended three years
ago has age 0 — its newest row *is* its value — and absolute staleness remains the staleness
fields' job.

### D.3 Recording the date, not just using it

A snapshot value that did not come from the newest period is a fact about the value, so it is
published: `<field>_age_days`, emitted only when non-zero. That is the same "here is how this
number was obtained" signal `ttm_source` and `ffo_gains_source` already carry in the facts
frame, and it needs no UI change — the snapshot section renders whatever concepts are present.

One caller opts out. The scale guard's `_revenue_scale` reference passes
`max_value_age_days=None`, because it asks an order-of-magnitude question that an older year
answers as well as the current one — the argument `fill_scale_reference` already makes on the
history side. Bounding it would take the reference away from exactly the filers whose revenue
is missing.

### D.4 Diff (`afterC` → `afterD`)

**Stated up front: this part changes snapshot values by design.** What it actually did was add
only.

```
snapshot   25,264 -> 25,367    appeared 103   changed 0   disappeared 0

  the 37 age rows                  the 66 recovered values
  dividends_ttm_age_days   21      dividends_ttm          21    p_ffo                6
  ffo_ttm_age_days          7      dividend_yield         21    eps_ttm              4
  eps_ttm_age_days          4      pe_ratio                4    revenue_ttm          3
  revenue_ttm_age_days      3      ev_sales                3    pfcf_ex_sbc          2
  sbc_ttm_age_days          2      pe_to_revenue_growth    2
```

The 37 age rows match the 37 pairs the bound admits, concept for concept. Every other frame is
unchanged; anchors 0/0; flags 734 → 734; all mean lines 0.000%.

### D.5 Verification

**AVB, the case the brief names.** `FFO_TTM` is NaN at 2026-03-31 and 2026-06-30 and
1,601,911,000 at 2025-09-30, 273 days back.

```
market_cap 26,781,757,961 / FFO_TTM 1,601,911,000 = 16.7186      snapshot p_ffo = 16.7186
```

It also gains `eps_ttm` 8.142 and `pe_ratio` 23.03, both carrying `age_days = 273`, and its
`avg_p_ffo_5y` of 18.11 now has a marker to sit beside.

**Nothing older than the bound is published:** the 37 age rows run 90 to 365 days, maximum
exactly 365.

**One recovered input produces no multiple, for a real reason.** TAP has `ffo_ttm_age_days`
but no `p_ffo`: its newest `FFO_TTM` value (2025-12-31) is −1.43bn, and `where(ffo_ttm > 0)`
blanks it — exactly as the history does, and the same case as ARE in the product-cleanup task.

**Independent reconciliation** against the filers' own 12-month XBRL facts, read straight from
the cached `companyfacts` JSON with no pipeline code on that side:

```
11  derived quantities with no single filed tag (EPS_TTM_CALC, FFO_TTM) -- not checkable
15  the filer publishes no 12-month fact at that end date -- nothing to compare
11  checkable:  10 match to within 0.5%,  1 differs
```

The one difference is **AWK: 3.2475 against a filed FY figure of 3.31**, and it is not a Part D
effect. The pipeline's TTM is `0.765 + 0.8275 × 3`, the four quarterly dividends of that year;
0.765 is the Q1 *cash paid* figure and 0.8275 the Q1 *declared* figure, which differ by one
quarter's timing across a rate rise. The value was already in the facts frame before this
change — **Part D publishes values the pipeline had already computed and never computes a new
one** — so this is a pre-existing question about `DividendsPerShare`'s tag list, and tag work is
excluded by the brief.

### D.6 `get_latest_row` has the same defect and is deliberately not changed

The metric frames the snapshot reads through `get_latest_row` carry 147 recoverable cases:

```
operating_leverage 83   fcf 23   capex_intensity 21   ebitda 13
revenue_growth      4   provision_ratio 2   rd_intensity 1
```

Not extended, for a reason rather than for scope: **a null in a metric frame is frequently a
deliberate rejection of that period's value**, not an absent one. `operating_leverage` alone is
83 of the 147, and its nulls are produced by `MAX_OPERATING_LEVERAGE_ABS` and the revenue-growth
floor — the current period's value exists and was judged unusable. Substituting an older
period's answer there is a different decision from filling in a value that was never filed, and
it deserves its own argument.

---

## Part E — class 4's interior holes: evaluated, not implemented

### E.1 Re-measured against the current code

The gate has changed since these were counted, and this measurement also uses the **post-mask**
quarterly values to define the rolling path's reach (the gate report measured pre-mask, which is
where the gate runs), so the rolling path is slightly smaller here:

```                            gate report   now
class 4 pairs                       5,789   5,888   (500 tickers)
  collisions                       81,505  82,434
  pre-history                      11,460  11,493   80.2% of annual-only
  interior holes                    1,550   1,653   11.5%   on 812 pairs
  post-history                      1,127   1,176    8.2%
  annual-only total                14,137  14,322
```

The shape is unchanged: **four fifths of what a per-date rule would add is annual-only history
from before quarterly tagging, and the collisions outnumber the additions six to one.** The
interior holes are thinly spread — 405 of the 812 pairs have exactly one, and only one pair has
ten.

### E.2 Such a rule exists on paper

> **R:** for a class-4 pair, admit an annual date `d` iff `first(rolling) < d < last(rolling)`
> and `d ∉ rolling_dates`.

R reaches all 1,653 interior holes, excludes the 11,493 pre-history and 1,176 post-history
dates by the interval test, and excludes the 82,434 collisions by a **set-membership test rather
than a tie-break**. So the brief's question — can the 1,550 be reached without admitting the
11,460 and without a tie-break — has the answer *yes, mechanically*.

### E.3 What it costs — measured, and it is not what I expected

`rolling_dates` is not knowable where the decision is made. `annual_ttm_values` runs inside
`build_dataframe`, before `_mask_negative_flow_values` and its three siblings; the rolling
`_TTM` rows are emitted later by `add_ttm_concepts`, after them. R's membership test would be
evaluated against the pre-mask date set and enforced against the post-mask one. Today's gate
survives that gap because it asks a coarser question — *does this series produce any window at
all* — while R needs the two sets to agree **date by date**.

Measured over all 501 tickers and 25 concepts:

```
pairs with a post-mask rolling series                        5,893
pairs whose pre- and post-mask date sets differ                206   (3.5%)
  dates the pre-mask view has and the post-mask does not     1,290
  dates the post-mask view has and the pre-mask does not         0
annual dates R would admit that the rolling path DOES reach      0   <- no collisions
genuine holes R would refuse because pre-mask had a value      240
```

**So the mask-timing gap does not break R the way I expected it to.** The post-mask date set is
a strict subset of the pre-mask one in this data — 1,290 dates lost, 0 gained — so R's test on
the pre-mask set is *stricter* than it needs to be and admits **zero** colliding dates. The
error falls entirely in the safe direction, exactly as it does for the existing gate.

What it costs instead is coverage: **240 of the 1,653 interior holes are refused**, because the
pre-mask view had a value at that date and R therefore treats it as reached. R would deliver
1,413, not 1,653.

The second cost is independent of mask timing: **`ttm_source` stops being a per-series
constant.** A series would carry `quarterly_rolling` at most dates and `annual_fact` at a few
interior ones, and `app.cadence_markers` would be describing a series with two provenances.
Today "wholly one path or wholly the other" is a property you can verify by reading nine lines
of `annual_ttm_values`. Under R it becomes a property of a set subtraction performed against a
set computed at a different point in the pipeline — and one whose safety rests on the
post-mask-subset-of-pre-mask asymmetry above, which is an observation about this data and not a
theorem. E.4 shows it is not one.

### E.4 A correction to the gate's stated safety argument

The gate report justified evaluating pre-mask like this: *"the masks remove rows, which can only
widen the steps between the survivors and so can only break a window, never create one."*

**That reasoning is incomplete.** Removing a row widens a step, and a widened step can move
*into* the valid band from below. Constructed directly against `calculate_ttm`:

```
rows at days 0, 45, 91, 182, 273           -> 0 TTM windows   (the 45-day step fails)
the same rows with the day-45 row removed  -> 1 TTM window    (91, 91, 91; span 273)
```

So a mask *can* create a window. **The conclusion still holds empirically** — over all 501
tickers and 25 concepts, the number of pairs where the pre-mask gate opens and the post-mask
values nevertheless form a window is **0**, and more broadly no post-mask series reaches a date
its pre-mask self did not (0 of 1,290 differences go that way) — but it holds by measurement,
not by the argument given. The docstring in `parse_edgar` should be read with that correction.

This is why E.3's "no collisions" result is not a licence: R's safety and the current gate's
safety rest on the same empirical asymmetry, and the counterexample shows the asymmetry is not
guaranteed. The difference is what breaks if it ever fails. The current gate would lose a
recovery; R would write a duplicate key that `pivot_table` silently averages.

### E.5 The gate does already produce three duplicate keys

Scanning the assembled facts frame:

```
duplicate (ticker, concept, end) rows: 6   (3 dates, each written twice)
  BF-B  StockIssued_TTM             2012-04-30   -10,000,000  annual_fact  +  NaN
  KMI   ShareBasedCompensation_TTM  2013-12-31             0  annual_fact  +  NaN
  PYPL  DividendsPerShare_TTM       2025-12-31          0.14  annual_fact  +  NaN
of which both rows carry a value: 0
mixed-provenance (ticker, concept) series: 0
```

No value is corrupted — `pivot_table` averages over the single non-null — but `run_full_refresh`'s
duplicate check will now print a warning for them, and one of the three is why PYPL appeared in
Part D's exposure list. These arise because `add_ttm_concepts` emits a NaN `_TTM` row at every
quarterly date, including a fiscal year end the annual path also wrote. **Three keys under the
per-series rule; R would multiply the surface by the 1,653 dates it inserts.**

### E.6 Recommendation: confirmed not worth the mechanism

**Do not implement.** The measurement was kinder to R than I expected — it produces no
collisions on this data — and the recommendation still goes against it. The reasoning, in order
of weight:

1. **The prize is 1,413 rows** (1,653 holes less the 240 R cannot see) against 512,659 base
   facts and 320,913 rolling TTM values — **0.28%** — spread one and two at a time across
   812 series.
2. **It demotes the disjointness guarantee from structural to empirical.** Today it is
   "a series is wholly one path or wholly the other", true by construction. Under R it is "the
   sets are disjoint because we subtracted one from the other, using a set computed before the
   masks run" — safe only while post-mask stays a subset of pre-mask, which E.4 shows is not a
   theorem. And what it protects is load-bearing: the two paths concatenate rather than merge,
   and the gate task established by construction that a collision yields two rows at one key
   which `pivot_table` averages into a number neither path computed.
3. **`ttm_source` stops being a per-series constant** and the cadence markers start describing
   series with two provenances — a real loss of a signal the project added deliberately.
4. **The concepts holding the holes barely reach a displayed number.** The top four —
   `StockRepurchased` 349, `StockIssued` 293, `DividendsPerShare` 211,
   `DepreciationAndAmortization` 169 — feed the buyback flag, the share-count jump flag, the
   dividend yield and EBITDA. A one-quarter hole in a TTM series that already has neighbours on
   both sides moves none of them.

"Confirmed not worth the mechanism" was named as a fully successful outcome, and that is the
finding. Nothing was implemented for Part E; there is no fifth change group.

---

## The four groups together

Cumulative diff, `before` → `afterD`, all 501 tickers from one price capture:

```
base_facts          512,659 -> 512,659      0 /   0 /   0
facts             1,120,570 -> 1,120,570    0 /   0 /   0
metrics_long        693,135 -> 693,135      0 /   0 /   0
valuation_history   472,080 -> 472,080      0 /   0 /   0
rolling              33,006 -> 33,006       0 /   0 /   0
snapshot             25,372 -> 25,367     107 /   0 / 112
                                    appeared / changed / disappeared
```

**Not one value changed anywhere in the project.** Every difference is a snapshot value that
began or stopped being published, and each is attributed above: 112 removals are Part C's
negative markers, 107 additions are Part C's four recovered `p_tbv` values plus Part D's 37 age
rows and 66 recovered values.

### The mean-line effect

| line | n | mean \|Δ\| | max \|Δ\| |
|---|---|---|---|
| `avg_pe_5y` | 28,111 | 0.000% | 0.000% |
| `avg_p_ffo_5y` | 27,710 | 0.000% | 0.000% |
| `avg_pfcf_5y` | 25,384 | 0.000% | 0.000% |
| `avg_p_tbv_5y` | 24,239 | 0.000% | 0.000% |
| `avg_ev_ebitda_5y` | 20,742 | 0.000% | 0.000% |
| `avg_p_ppnr_5y` | 1,311 | 0.000% | 0.000% |
| `avg_p_core_earnings_5y` | 805 | 0.000% | 0.000% |

Running series: TTM ~25%, rolling-window 11–15%, duplicate-ends 2–5%, alignment 0–3.7%, FFO
gains 0.6–1.5%, annual-gate 0–0.07%, **this task 0.000%**. The mean lines are computed from
`valuation_history`, which none of the four groups touches; only the snapshot moved.

### Anchor and snapshot invariants

**Anchors: 18,877 (ticker, concept) pairs, 0 dates moved, 0 values changed** — eleven tasks in a
row. Part D's expected exception, stated up front, was that snapshot values would change by
design; what it actually did was add 103 rows and change none.

### Quality flags

**734 → 734 after every group; 0 cleared, 0 new.** As the gate report noted,
`check_data_quality` counts base-concept rows before `add_derived_concepts` runs, and none of
these four changes touches a base concept — Part A guards a metric, B a flag, C and D the
snapshot only.

### Peer bands

**2,106 → 2,106 after every group; 0 appeared, 0 disappeared, 0 flipped.**

---

## Deliberately not fixed

**Three snapshot multiples still lack the history's positivity mask.** Found while measuring
Part C, same class of defect, same one-line shape:

```
pe_ratio     491 published,  25 negative, min -2,385.04
pfcf_ratio   443 published,  40 negative, min   -881.63
ev_ebitda    391 published,   7 negative, min   -315.38
```

**72 snapshot markers sitting on charts whose line is blank at that period.** Part C's brief
scopes the inconsistency to `pb_ratio` and `p_tbv` and its verification step to those two, and
fixing five multiples inside a task about two constants is exactly the unattributable diff this
brief opens by warning against. This is the strongest candidate for the next task: it is three
lines and it falsifies a displayed number.

**`get_latest_row`'s 147 recoverable cases** (D.6) — a metric-frame null is often a deliberate
rejection rather than an absent value, which is a different argument to make.

**The `DividendsPerShare` tag list mixing declared and cash-paid figures** (D.5, AWK). Tag work,
excluded, and pre-existing.

**`apply_self_relative_scale_guard` remains non-causal** (A.4), by decision rather than
oversight, and an as-of view therefore does not reproduce its masking.

**The correction to the annual gate's pre-mask safety argument** (E.4) is recorded here but the
docstring in `parsers/parse_edgar.py` is left as written — editing it is an
`annual_ttm_values` change, which the brief excludes. The claim it makes is true of this data;
only the reason given is incomplete.

**The three duplicate `_TTM` keys** (E.5). No value is affected, but `run_full_refresh` will
print a duplicate warning. The fix belongs with `add_ttm_concepts`, which is the annual-path
machinery this brief excludes.

**Everything the brief excluded:** no coverage-flag semantics, no `calculate_ttm` /
`calculate_rolling_harmonic_stats` / `decumulate_period_values` / `extract_period_values` /
`annual_ttm_values` changes, no tag work, no UI or chart changes, no new metrics.

---

## Files changed

| file | change |
|---|---|
| `metrics.py` | A: `apply_self_relative_scale_guard` takes `half_window_days`, calendar window; `REVENUE_SELF_SCALE_HALF_WINDOW_DAYS = 730`. D: `get_latest_value` skips nulls within `MAX_LATEST_VALUE_AGE_DAYS = 365` and returns `value_age_days`. |
| `main.py` | A: both call sites. B: `within_avg_5y_window` (new), `calculate_peer_band_flags(as_of=...)`. C: `pb_ratio` and `p_tbv` in `build_snapshot` take the valuation constant and the positivity mask. D: `latest_value` helper and the `<field>_age_days` rows. |
| `MDs/metrics.md` | the calendar window; the staleness bound |
| `MDs/main.md` | the unified valuation constant; the snapshot's carried-forward inputs |
| `MDs/bugfixes_opdate_history.md` | entry per convention |
| `final_consistency_report.md` | this file |

`data/` and `figures/` untouched; no refresh was run; no scratch scripts left behind.

### Verification performed

- One price capture (501 tickers, 2,473,488 rows, 0 failures) shared by all five pipeline runs;
  base facts re-derived from the same EDGAR cache each time, 512,659 rows on every run.
- Part A: 37,891 full 17-row window spans measured across both guarded frames; the row and
  calendar references compared on all 51,760 rows; the implementation checked against a naive
  per-ticker loop sharing no code with it, 0 mismatches.
- Part B: the flags recomputed at eight anchor dates on identical data to quantify the drift.
- Part C: every call to `apply_denominator_scale_guard` in both code paths recorded and replayed
  under both constants; a 501-ticker predicate check after the change, 0 mismatches; all 111
  removals confirmed against negative tangible equity and a blank history line.
- Part D: all 83 exposed pairs located and their distances tabulated; 11 of the 37 recoveries
  reconciled against the filers' own 12-month XBRL facts (10 match, 1 explained); AVB
  reconstructed from market cap and FFO directly.
- Part E: the three populations re-measured against current code; rule R specified and its
  failure mode located; a counterexample constructed showing a mask can create a TTM window;
  both assembled frames scanned for duplicate keys and mixed provenance.
