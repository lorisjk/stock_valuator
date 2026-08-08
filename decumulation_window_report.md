# `decumulate_period_values` — Fiscal-Calendar-Aware Quarter Lengths

**Task:** `decumulate_period_values` accepted a derived quarter only when the year-to-date
difference fell in **80–100 days**. That window encodes a 13-week calendar. Kroger's Q1 is 16
weeks, so it was discarded every year, and after the TTM fix Kroger — an S&P 500 constituent —
rendered with no valuation multiples at all.

Measured over all 501 cached tickers: **622,845 differences**, every one the function forms,
including the ones it rejects. Every figure below comes from the local cache through the
pipeline's own functions; no refresh was run.

---

## 1. The distribution

```
differences formed: 622,845    over 501 tickers and 24 concepts
  accepted today: 604,683      rejected: 18,162
```

| length (days) | differences | distinct periods | what it is |
|---|---:|---:|---|
| ≤ 0 | **0** | 0 | — |
| 1–20 | 223 | 60 | duplicated period ends |
| 21–79 | 114 | 26 | sub-quarter stubs |
| **80–100** | **604,683** | 53,453 | **the quarter, as the code knows it** |
| 101–105 | **0** | 0 | *empty* |
| **106–120** | **1,588** | **152** | **the 16- and 17-week fiscal quarter** |
| 121–160 | 129 | 28 | merger / spin-off / IPO / fiscal-year-change stubs |
| 161–200 | 9,307 | 3,308 | two quarters — one of the filer's points missing |
| 201+ | 6,801 | 3,358 | three or more quarters |

Day by day around the core:

```
   82        29
   83     3,218  #                12-week fiscal quarter
   84     2,949  #
   88     3,358  #
   89    69,338  ##################
   90   130,607  ###################################
   91   222,794  ############################################################
   92   164,998  ############################################
   98     2,039
  100        14
  ------------------ empty, 101..105 ------------------
  106         1                   (a stub, see below)
  109         1
  111       483                   16-week quarter
  112       877
  118        38                   17-week quarter, 53-week year
  119       182
  ------------------ empty, 120 -----------------------
  121        29                   4-month transition stubs
  122         9
  124         1
  ------------------ empty, 125..128 ------------------
  136         5
  ...
  180     3,302                   two 12-week quarters as one step
  181     3,217
```

Empty runs across the whole range: 44–58 (15 wide), 76–79 (4), **101–105 (5)**, 125–128 (4),
130–135 (6), 158–161 (4).

### The clusters, confirmed against real filers

Each was checked in the filers' own fact durations rather than assumed.

| cluster | what it is | filers |
|---|---|---|
| 83–84 | 12-week fiscal quarter | AZO, COST, DPZ, PEP, KR, YUM |
| 89–92 | 13-week calendar quarter | the other 493 |
| 97–98 | 14-week quarter, 53-week year | TGT, HD, BBY and other retailers |
| **111–112** | **16-week quarter** | KR (Q1), AZO / COST / DPZ / PEP / YUM (Q4), MAR, HST |
| **118–119** | **17-week quarter in a 53-week year** | AZO, COST, DPZ, PEP, YUM |
| 121–160 | transition stubs | CTVA, MOS, SHW, DOC, FCX, CMS, HUM, BAC, PSKY, EXE, INVH, KVUE, ETN, TTWO, KDP, WYNN, … |
| 161–200 | two quarters | 492 tickers |

```
KR    Revenue durations {83, 111, 195, 279, 363}  → ladder 111 / 84 / 84 / 84    Q1 = 16 weeks
PEP   Revenue durations {83, 167, 251, 363}       → ladder  83 / 84 / 84 / 112   Q4 = 16 weeks
COST  Revenue durations {83, 111, 118, 167, 251, 363}                            Q4 = 16-17 weeks
TGT   Revenue durations {90, 181, 272, 363}       → ladder  90 / 91 / 91 / 91    no long quarter
```

**The 16-week quarter appears in two positions, and only one of them was being rescued.** For
PEP, AZO, COST, DPZ and YUM it is Q4, whose 112-day difference was rejected — but the value
survived through a *different* code path, the `annual − (Q1+Q2+Q3)` fallback at the end of the
function. For Kroger it is **Q1**, and there is no fallback for Q1. That asymmetry is why Kroger
alone lost everything.

### The size of the prize

**1,588 differences in the 106–120 band are being discarded**, across 152 distinct periods and
20 tickers. They are not spread thinly: 8 tickers account for all the recurring ones.

| ticker | discarded differences |
|---|---:|
| COST | 333 |
| AZO | 289 |
| KR | 282 |
| PEP | 257 |
| DPZ | 231 |
| YUM | 137 |
| MAR | 35 |
| HST | 4 |

By concept: Revenue 184, NetIncomeLoss 168, ShareBasedCompensation 151, StockRepurchased 141,
PretaxIncome 132, OperatingIncomeLoss 128, DepreciationAndAmortization 114, IncomeTaxExpense 108,
StockIssued 107, DividendsPerShare 99, OperatingCashFlow 97, Capex 93, CostOfRevenue 46.

---

## 2. The rule, and why this one

### Length alone does not separate the two things in the band

The 106–120 band is **mixed**. Enumerating all 152 distinct periods in it:

```
AZO   112 × 14 periods, 111 × 10, 119 × 3, 118 × 2      52/53-week calendar
COST  112 × 13, 111 × 11, 119 × 3, 118 × 2              52/53-week calendar
DPZ   112 × 14, 111 × 9,  119 × 2, 118 × 1              52/53-week calendar
PEP   19 periods, KR 18, YUM 16, HST 4, MAR 3           52/53-week calendar
---------------------------------------------------------------------------
ES 106 × 1   JNJ 109 × 1   TKO 110 × 1   OTIS 113 × 1   one-off stubs
JBHT 114 × 1 ARES 119 × 1  LLY 119 × 1   LYB 119 × 1
```

A 17-week quarter is **119** days and a four-month transition stub is **121**. Two days apart.
The gap at 120 is one day wide — that is luck, not evidence, and a threshold resting on it would
be the kind of round number this project has twice refused to ship.

**What separates them is repetition.** A 16-week quarter is a property of a filer's calendar and
recurs every year; a stub happens once, when a company merges, spins off, lists or moves its
fiscal year end. Counted per `(ticker, concept)` — the scope of one `decumulate_period_values`
call:

```
                      periods with a length in 101-120
  the eight 52/53-week filers   15, 16, 17, 18, 19, 20, 25, 26, 28, 29 …   (85 of 93 concepts ≥ 3)
  every stub                    1                                          (8 of 8 concepts = 1)
```

Not one stub reaches 2. Not one of the eight filers' dense concepts falls below 15.

### The choice

> **A global length band, plus a per-filer recurrence test for the part of the band that is
> ambiguous.**

```python
_QUARTER_MIN_DAYS = 80
_QUARTER_MAX_DAYS = 100          # accepted unconditionally, as before
_LONG_QUARTER_MAX_DAYS = 120     # 17 weeks plus a day: the longest quarter any calendar has
_MIN_LONG_QUARTER_PERIODS = 3    # a long quarter must be part of the filer's calendar
```

A difference of 80–100 days is a quarter. A difference of 101–120 days is a quarter **only if this
filer produces at least three of them** for this concept. Everything else is rejected, as before.

### The failure mode of each alternative, and of this one

**A wider global window alone (option 1).** Simplest, one constant. It admits the 9 stub
differences listed above — a 106- to 119-day transition period would enter the facts frame as a
quarter, inflating one bar in the data tab and one TTM window. Small, but it is exactly the
"plausible wrong number" failure this project treats as the dangerous one, and it costs almost
nothing to exclude.

**A per-filer calendar derived from the filer's own pattern (option 2).** More precise, but the
calendar must be inferred from data that may be thin. The rule shipped here is the cheap half of
this: it does not try to learn the *shape* of the calendar (12/12/12/16 versus 16/12/12/12), only
whether a long quarter is part of it at all. Its measured cost is 11 conservative rejections — 9
on thin concepts of **HST** and 2 on **MAR**, both filers that used a 52/53-week calendar only
until 2013 and whose sparse concepts have fewer than three long periods. Those quarters stay
unrecovered. That is a false negative, and the honest description of the trade.

**Structural — accept a difference between adjacent year-to-date points without testing its length
(option 3).** This is the most appealing until it meets the data. **9,307 differences of 161–200
days across 492 tickers** are adjacent year-to-date points whose intermediate point the filer
never tagged. A structural rule cannot tell "this filer's Q1 is 16 weeks" from "this filer's Q1
point is missing and this is Q1 plus Q2" without looking at the length. It would need a length
test anyway, so it is option 1 with extra steps.

### The hard requirement

**No difference spanning two quarters is admitted.** The shortest two-quarter span observed is
**161 days**; the ceiling is 120. The 9,307 such differences remain rejected, unchanged.

---

## 3. What was implemented

`fetchers/edgar.py`. `decumulate_period_values` keeps its contract — it still derives a quarter by
differencing consecutive year-to-date points, and returns the same shape. What changed is which
differences are accepted, and that acceptance now needs the whole candidate set at once, so the
walk is split into two passes: build every candidate difference with the length it covers, count
the long ones, then accept.

The same 80–100 assumption sat in a second place, and is now the same constant:
`extract_period_values`' **point-in-time** quarterly test. A weighted-average share count carries
the duration of the period it averages, so Kroger's 16-week Q1 share counts were rejected there
too — recovering the Q1 revenue without the Q1 share count would have left `EPS_QUARTERLY_CALC`
missing at exactly the dates the rest of the fix filled.

### The Q4 case

Q4 is derived as `FY − (Q1+Q2+Q3)` in the fallback at the end of the function. For a
12/12/12/16-week filer that quarter is 16 weeks, so **the direct year-to-date difference for Q4
was rejected and the fallback was doing the work**. After the change the direct difference is
accepted and the fallback skips the date (`if ann["end"] in quarters: continue`), so Q4 now comes
from the filer's own ladder rather than a three-term subtraction of independently rounded figures.

Verified on all five 12/12/12/16 filers. Mostly the two routes agree exactly; where they differ,
the direct difference is the better number:

```
AZO   7 Q4 values move by exactly $1        rounding in the three-term subtraction
YUM   OperatingIncomeLoss 2015-12-26   -78,000,000  ->  441,000,000
      FY2015 quarters now sum to 1,921m against a reported ~1.9bn operating profit;
      before, they summed to 1,319m and Q4 was negative
DPZ   StockRepurchased 2012-01-01      -40,170,000  ->   35,817,000
      a negative repurchase is not a thing
DPZ   ShareBasedCompensation 2023-01-01  24,065,000 ->    7,119,000
      Domino's runs 5-9m of SBC a quarter; 24m was a year's worth in one bar
```

There is a second, smaller effect worth naming because it reaches beyond the eight filers. The
`quarter_starts` pre-filter — which decides whether an annual fact survives at all — used the same
80–100 test. Widening it lets the annual point survive for a filer whose only sub-annual fact in
that fiscal-year group is long. **JBHT** is the one ticker outside the eight that gains anything
for this reason: its 2013 `DividendsPerShare` Q4 (0.15, its actual quarterly rate that year)
becomes derivable. Its 114-day stub is still rejected by the recurrence gate.

### Duplicated period ends

33 tickers tag the same period twice, 1–10 days apart, with an identical value:

```
ACN  Revenue  2012-02-28 -> 2012-02-29   1 day    7,259,828,000 -> 7,259,828,000
ADI  Revenue  2011-01-29 -> 2011-02-04   6 days     728,504,000 ->   728,504,000
```

**223 such near-zero differences exist and all 223 stay rejected** — the 80-day floor is
unchanged, and widening happened only at the top of the band. Measured directly across the 20
worst-affected tickers, counting quarter pairs less than 11 days apart in the output:

```
before = 300     after = 300     delta = 0
```

The 300 are pre-existing and come from a different mechanism — `extract_period_values` keys on
`(end, days)` and so keeps both tagged period ends as separate quarters. This change neither
creates nor removes one. Recorded in section 7.

---

## 4. Non-regression, all 501 tickers

The pipeline was run end to end on a pre-built base facts frame, before and after, with one
captured price history — the only difference between the runs is the code under test.

| frame | appeared | changed | **disappeared** |
|---|---:|---:|---:|
| facts | 1,492 | 532 | **0** |
| metrics_long | 1,173 | 810 | **0** |
| valuation_history | 607 | 338 | **1** |
| snapshot | 28 | 19 | **0** |
| duplicates on `(ticker, concept, end)` | — | — | **0** |

### Appeared — the intended effect

```
KR    1,488 facts     1,168 metrics     604 valuation multiples
JBHT      4 facts         4 metrics       3 valuation multiples
YUM       —              1 metric        —
```

Every appeared value belongs to Kroger, to JBHT's 2013 Q4 dividend, or to one YUM metric that
became computable. Of the 1,492 appeared facts, 66 per `_TTM` concept are Kroger's newly
computable trailing series, 18 are its Q1 share counts, and 19–35 per base concept are its
recovered Q1s.

### Changed — every one inside the eight filers

```
facts             AZO 350   DPZ 108   COST 41   HST 15   YUM 8   KR 5   MAR 5
metrics_long      AZO 656   DPZ  93   COST 22   HST 20   YUM 15  KR 4
valuation_history AZO 183   COST 112  DPZ 32    KR 4     MAR 4   HST 3
```

**No ticker outside the eight changed a single value.** By relative size:

| relative move | facts values |
|---|---:|
| < 1e-7 | 28 |
| 1e-7 … 1e-5 | 336 |
| 1e-5 … 1e-3 | 98 |
| 1e-3 … 1e-2 | 45 |
| 1e-2 … 1e-1 | 11 |
| > 1e-1 | 14 |

**364 of 532 are rounding** — the direct difference replacing a three-term subtraction. The 25
material ones are the Q4 corrections listed in section 3, plus two groups:

**Kroger `StockRepurchased` 2025-02-01: 5,038,000,000 → 4,031,000,000.** This one is worth
spelling out, because the direction looks wrong until the facts are read:

```
PaymentsForRepurchaseOfCommonStock   (primary tag, cash flow statement)
    2024-02-04 → 2024-05-25   111d      103,000,000
    2024-02-04 → 2024-08-17   195d      116,000,000
    2024-02-04 → 2024-11-09   279d      125,000,000
    2024-02-04 → 2025-02-01   363d    4,156,000,000      →  Q4 = 4,156 − 125 = 4,031
TreasuryStockValueAcquiredCostMethod (fallback tag, equity statement)
    2024-11-10 → 2025-02-01    83d    5,038,000,000      ← the whole year, tagged as one quarter
```

Before the change, the primary tag produced no Q4 (its 111-day Q1 was rejected, so its annual
point was dropped by `quarter_starts`) and the fallback tag supplied 5,038,000,000 — the full
year's treasury purchases, sitting in a single quarter. The recovered ladder puts the primary tag
back in charge. **The new value is Q4's actual cash outflow; the old one was a year in one bar.**

**COST `SharesOutstanding`, 12 fiscal-year ends changed** (e.g. 2009-08-30: 440,454,000 →
441,699,000, +0.28%). At the fiscal year end Costco's 16-week Q4 weighted-average share count now
beats the full-year average, because `extract_period_values` already prefers the shorter duration
at a given end. Every other quarter in that series uses its own quarter's average; the year end
was the only one using the year's. The series is homogeneous for the first time.

### The one disappearance

```
HST  pe_to_revenue_growth  2013-12-31   12.95 -> (blank)
```

Host Hotels' `Revenue_TTM` for 2012-06-15 … 2013-09-30 each rise slightly (5,059m → 5,080m at
2012-12-31) because its 111–115-day Q4s are now direct differences. The TTM at 2013-12-31 is
unchanged at 5,165m, but its four-quarters-ago base moved, so revenue growth falls from **2.10% to
1.67%** — below `MIN_PEG_REVENUE_GROWTH` = 2%, and PEG is blanked by design. One value, and the
guard behaving exactly as specified.

### Anchor and snapshot invariants

24 `(ticker, concept)` pairs have a newest value that moved. Both groups are accounted for:

- **AZO, 7 pairs** — same date (2026-05-09), value moved in the 7th significant figure
  (`Revenue_TTM` 19,986,395,000 → 19,986,396,000). The Q4 rounding above.
- **KR, 17 pairs** — the date moved forward, from 2025-11-08 or 2026-01-31 to **2026-05-23**.
  Kroger's most recent quarter was one of the missing Q1s. This is the fix working, not an
  invariant breach: nothing was overwritten, a newer period became visible.

```
KR  Revenue              2025-11-08  33,859,000,000   ->  2026-05-23  46,121,000,000
    EPS_QUARTERLY_CALC   2025-11-08          -2.0153  ->  2026-05-23           1.4683
    EBITDA_QUARTERLY     2025-11-08    -759,000,000   ->  2026-05-23   2,396,000,000
```

Snapshot: **28 appeared, 19 changed, 0 disappeared** — all Kroger and AutoZone. Kroger gains its
whole rolling-multiple block (`avg_pe_5y`, `avg_pfcf_5y`, `avg_ev_ebitda_5y`, `avg_p_ffo_5y` and
their medians and short-history flags).

### The five-year rolling means

These are the reference line the app's charts compare today's multiple against, so the number is
stated plainly rather than buried:

| line | n | changed | appeared | disappeared |
|---|---:|---:|---:|---:|
| avg_p_ffo_5y | 27,781 | 163 | 66 | 0 |
| avg_ev_ebitda_5y | 20,802 | 151 | 66 | 0 |
| avg_pe_5y | 28,185 | 132 | 63 | 0 |
| avg_p_tbv_5y | 24,409 | 125 | 0 | 0 |
| avg_pfcf_5y | 25,442 | 60 | 66 | 0 |
| avg_p_ppnr_5y | 1,317 | 0 | 0 | 0 |
| avg_p_core_earnings_5y | 807 | 0 | 0 | 0 |

**0.2–0.6% of points per line**, against roughly a quarter of them in the TTM task. The change is
narrow because it reaches eight filers.

### Independent plausibility check

Internal consistency proves the code does what it says. To check the numbers themselves, each
recovered Kroger Q1 was compared against a reconstruction from facts the recovery never touched:
the fiscal year total, minus the three *discrete* quarterly facts that follow it — four separate
filings, none of them the year-to-date point the Q1 was derived from.

```
recovered Q1s with a complete three-quarter chain to the fiscal year end:  121
  exact to the cent : 95
  within 0.1%       : 97
  within 1%         : 107
```

Perfect agreement on `DividendsPerShare` (17/17), `IncomeTaxExpense` (12/12),
`ShareBasedCompensation` (16/16) and `StockIssued` (16/16). `Revenue` 10 of 13 exact:

```
end          recovered        FY − (Q2+Q3+Q4)      difference
2013-05-25   29,997,000,000   29,997,000,000                0
2014-05-24   32,961,000,000   32,961,000,000                0
2015-05-23   33,051,000,000   33,051,000,000                0
2016-05-21   34,604,000,000   34,604,000,000                0
2017-05-20   36,285,000,000   36,903,000,000     -618,000,000   ← FY2017 had 53 weeks
2019-05-25   37,251,000,000   37,251,000,000                0
2020-05-23   41,549,000,000   41,549,000,000                0
```

The residuals are the 53-week year (the fiscal-year total contains a week the four quarters do
not) and 10-Q-to-10-K restatements of 11–34m on 0.3–2.0bn. And against a figure published outside
the cache: the recovered **Q1 fiscal 2025, the 16 weeks ended 2025-05-24, is $45,118,000,000**;
Kroger reported total sales of $45.1 billion for that quarter.

---

## 5. Kroger, before and after

```
                        before   after
Revenue                     48      71   quarters
NetIncomeLoss               48      71
OperatingCashFlow           35      70
Capex                       35      70
SharesOutstanding           55      73

Revenue_TTM                  0      66   ← every trailing series was empty
NetIncomeLoss_TTM            0      66
FCF_TTM                      0      66
EBITDA_TTM                   0      66
EPS_TTM_CALC                 0      66

pe_ratio                     0      63   ← every multiple was empty
ev_ebitda                    0      66
ev_fcf                       0      66
ev_sales                     0      66
pfcf_ratio                   0      66
pfcf_ex_sbc                  0      66
p_ffo                        0      66
dividend_yield               0      66
pe_to_revenue_growth         0      44
p_tbv                       52      69
pb_ratio                    55      73
```

The recovered quarters tile the fiscal year with no gap and no overlap:

```
end          value            step
2024-05-25   45,269,000,000    112     16 weeks
2024-08-17   33,912,000,000     84     12 weeks
2024-11-09   33,634,000,000     84
2025-02-01   34,308,000,000     84
2025-05-24   45,118,000,000    112     16 weeks
2025-08-16   33,940,000,000     84
2025-11-08   33,859,000,000     84
2026-01-31   34,725,000,000     84
2026-05-23   46,121,000,000    112
```

112 + 84 + 84 + 84 = 364 days, and the four sum to $147.1bn against Kroger's ~$147bn of annual
sales. `Revenue_TTM` now runs 146.9–150.2bn across the recovered history. The 16-week quarter is
about a third larger than its neighbours, as it should be: 45.1bn over 16 weeks is 2.82bn a week,
33.9bn over 12 weeks is 2.83bn a week.

---

## 6. Re-measured flags

| flag | before | after | Δ |
|---|---:|---:|---:|
| share_count_jump_flag | 734 | 734 | 0 |
| buyback_distortion_flag | 633 | 637 | **+4** |
| inorganic_contaminated | 1,016 | 1,016 | 0 |
| low_tax_rate_flag | 4,066 | 4,070 | **+4** |
| fcf_exceeds_ebitda | 1,835 | 1,835 | 0 |
| coverage flags (`quality.py`) | 743 | **741** | **−2** |

The +4s are Kroger quarters that now exist and can therefore be flagged — a flag cannot fire on a
period with no data. The two cleared coverage flags are **KR/Capex** and **KR/OperatingCashFlow**,
which went from 35 quarters to 70 and crossed the 50% threshold. Kroger's other concepts were
never flagged: 48 of 74 quarters is 65%, comfortably above the line, which is precisely why a
coverage flag never announced that Kroger was missing a fifth of its history.

---

## 7. Deliberately not fixed

**Duplicated period ends — 300 quarter pairs less than 11 days apart, across 33 tickers.** ACN
tags both 2012-02-28 and 2012-02-29 with the same revenue; WAT tags both 2024-06-29 and
2024-06-30. `extract_period_values` keys on `(end, days)` and so treats them as two periods. This
change is neutral on them (300 → 300, verified) but does not remove them. The fix belongs in the
extractor's key and would need its own diff — merging two ends changes which value survives.

**HST's and MAR's thin concepts — 11 long quarters left unrecovered.** Both filers used a
52/53-week calendar only until 2013, so for their sparse concepts (`Capex`, `PretaxIncome`,
`IncomeTaxExpense`, …) fewer than three long periods exist and the recurrence gate cannot tell
them from a stub. Raising the sensitivity would mean lowering `_MIN_LONG_QUARTER_PERIODS` to 2,
which admits SHW's and TTWO's two-occurrence stubs. Conservative by choice; the cost is 11
differences on two tickers.

**The recurrence gate is per `(ticker, concept)`, not per ticker.** It is computed inside one
`decumulate_period_values` call, which sees one concept's values. A dense concept therefore
carries a filer over the threshold while a thin one may not — the HST and MAR case above. Pooling
the evidence across a filer's concepts would fix it, and would mean threading ticker-level state
into a function that currently has none.

**The 121–160 day stubs are simply rejected, not represented.** CTVA's four-month transition
period after the DowDuPont separation, PSKY's post-merger stub, MOS's fiscal-year-change period
and 25 others are real reporting periods carrying real numbers, and the pipeline shows nothing for
them. Representing a stub honestly means a quarterly series with an irregular member, which is a
data-model question, not a threshold question.

**`extract_period_values`' `(end, days)` key and the fiscal-year-change handling** are untouched
beyond the point-in-time window.

**Everything outside the decumulation window**, per the task's scope: no change to
`calculate_ttm`'s bounds, no split or scale work, no tag work, no
`apply_denominator_scale_guard` / `pct_change` / `fillna` fixes, no coverage-flag semantics, no UI
or chart changes, no new metrics.

---

## Files changed

| file | change |
|---|---|
| `fetchers/edgar.py` | four constants with the measurement behind them; `_is_quarter_length`; `decumulate_period_values` split into a candidate pass and an acceptance pass with the per-filer recurrence gate; `extract_period_values`' point-in-time quarterly test uses the same predicate |
| `decumulation_window_report.md` | this file |
| `MDs/bugfixes_opdate_history.md` | entry per convention |

`data/` and `figures/` untouched.

### Verification performed

```
[ok ] no difference spanning two quarters admitted     shortest is 161d, ceiling is 120
[ok ] near-zero differences from duplicated ends       223 of 223 still rejected
[ok ] quarter pairs <11 days apart                     300 before, 300 after, delta 0
[ok ] recurrence gate on the eight stub tickers        0-1 long periods each -> rejected
[ok ] recurrence gate on the eight 52/53-week filers   3-26 long periods each -> accepted
[ok ] differences accepted before but rejected now     0
[ok ] disappeared facts / metrics values               0 / 0
[ok ] changed values outside the eight filers          0
[ok ] duplicates on (ticker, concept, end)             0
[ok ] Kroger's recovered quarters tile the year        112+84+84+84 = 364 days
[ok ] recovered Q1s against an independent chain       95 of 121 exact to the cent
```

**Not verified:** no full refresh was run. Every figure comes from the local companyfacts cache
and a single yfinance price capture, driven through the pipeline's own functions.
