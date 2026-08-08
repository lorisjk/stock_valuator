# `calculate_ttm` — Calendar-Aware Windows + Annual-Fact TTM Path

**Task:** stop `calculate_ttm` from labelling a sum of four arbitrary rows "trailing twelve
months", and start reading the trailing-twelve-month value that annual-only filers have been
publishing all along.

Measured over all 501 cached tickers, 24 TTM concepts with data, **333,737 windows**. Every number
below comes from the local cache through the pipeline's own functions; no refresh was run.

---

## 1. The span distribution, the gap, and the threshold

### What was measured

For every window the current implementation forms — rows *i−3 … i* of one `(ticker, concept)`
series — the elapsed days between the first and fourth row. For four consecutive calendar quarters
that is **three quarters ≈ 273 days**, not 365: the window *covers* twelve months, but the distance
between its outer *end dates* is nine.

```
windows formed: 333,737    over 501 tickers and 24 concepts
```

| span (days) | windows | cumulative |
|---|---:|---:|
| < 200 | 1,219 | 0.37% |
| 200–249 | 1,005 | 0.67% |
| 250–255 | 875 | 0.93% |
| 256–272 | 2,437 | 1.66% |
| **273–275** | **301,271** | **91.94%** |
| 276–283 | 13,988 | 96.13% |
| 284–304 | 501 | 96.28% |
| **305–362** | **0** | — |
| 363–371 | 10,062 | 99.30% |
| 372–460 | 807 | 99.54% |
| > 460 | 1,533 | 100.00% |

Day by day around the core:

```
  272     1,002
  273   141,785  ############################################################
  274    80,681  ##################################
  275    78,805  #################################
  276     4,039  #
  277–279   872
  280     9,142  ###          <- 12+12+16-week calendars
  281–283    36
  287       430               <- the same, in a 53-week year
  289–304    71               <- fiscal-year-end changes
  ---------------------------- empty, 305..362 ----------------------------
  363        11
  364     1,668
  365     6,977  ##           <- one quarter skipped
  366–371 1,406
```

### The gap is clean, and the threshold comes out of it

Two empty runs bracket the legitimate region:

- **upper: 305–362, 58 days wide.** Highest legitimate span observed: **304**. Lowest
  illegitimate: **363**.
- **lower: 246–250, 5 days wide.** Highest broken span below the core: **245**. Lowest
  legitimate: **251**.

Both bounds are the **midpoint of the empty run**, which maximises the margin on each side and is
not a round number chosen in advance:

```python
_TTM_WINDOW_MIN_DAYS = 248     # midpoint of the empty run 246..250
_TTM_WINDOW_MAX_DAYS = 333     # midpoint of the empty run 305..362
```

A second condition applies to each **step** inside the window, because a window can have a valid
total span while double-counting one quarter and skipping another. The step distribution has its
own empty runs:

```
   72        10                <- broken
   ------------ empty, 73..80 ------------
   81–83      3
   84     3,188                <- 12-week fiscal quarter
   89–98  ~978k                <- calendar quarter
   112      760                <- 16-week Q4
   119      144                <- 17-week Q4, 53-week year
   121       18                <- fiscal-year-change stub
   ------------ empty, 122..152 -----------
   153        5                <- broken
   168        8                <- two 12-week quarters as one step
```

```python
_TTM_STEP_MIN_DAYS = 76        # midpoint of the empty run 73..80
_TTM_STEP_MAX_DAYS = 137       # midpoint of the empty run 122..152
```

**The threshold is global, not per concept.** Nothing in the per-concept measurement argues
otherwise: every concept's median span is 273 or 274, and the tail fraction varies (0.4%–20.8%)
only because thin concepts have more holes — not because their legitimate windows are shaped
differently.

### 52/53-week and shifted-fiscal-year filers are inside the band, deliberately

This is where the fix could most easily have traded one defect for another, so each cluster was
identified before the bounds were set:

| span | windows | what it is |
|---:|---:|---|
| 252 | 866 | three 12-week quarters (AZO, PEP, COST, DPZ, YUM) |
| 273–275 | 301,271 | calendar quarters, all month-end conventions |
| 280 | 9,142 | 12 + 12 + 16-week quarters, 97 tickers (AZO, PEP, COST, DPZ, YUM, WDC, GIS, TGT, TSCO, HD, LOW, RL, …) |
| 287 | 430 | the same in a **53-week** year |
| 289, 296 | 26 | MAR and HST moving off a 52/53-week calendar in 2013 |
| 303, 304 | 44 | fiscal-year-end changes: GPN (May→Dec), MOS, MSCI |

All of them are kept. The one legitimate window that a lower bound of 252 would have dropped —
**HST 2012-09-07, span 251, steps 83/84/84** — is kept by the gap-derived bound of 248.

### The coverage cost, per concept, before applying anything

| concept | windows | span > 333 or a bad step | % |
|---|---:|---:|---:|
| DividendsPerShare | 20,484 | 2,491 | 12.2 |
| StockIssued | 22,103 | 1,510 | 6.8 |
| StockRepurchased | 21,895 | 1,482 | 6.8 |
| DepreciationAndAmortization | 29,041 | 1,111 | 3.8 |
| PretaxIncome | 28,078 | 1,058 | 3.8 |
| NetIncomeLoss | 30,310 | 1,040 | 3.4 |
| Revenue | 30,180 | 1,038 | 3.4 |
| Capex | 26,272 | 989 | 3.8 |
| IncomeTaxExpense | 29,900 | 938 | 3.1 |
| OperatingIncomeLoss | 23,763 | 793 | 3.3 |
| OperatingCashFlow | 30,020 | 732 | 2.4 |
| ShareBasedCompensation | 25,782 | 687 | 2.7 |
| ResearchAndDevelopment | 2,471 | 118 | 4.8 |
| GainLossOnSaleOfProperties | 549 | 114 | 20.8 |
| the remaining 10 | 12,889 | 514 | 4.0 |
| **total** | **333,737** | **14,615** | **4.38** |

### Which rule caught what

```
windows formed                     333,737
rejected by the span band only           0
rejected by the step rule only          51
rejected by both                    14,564
rejected in total                   14,615   (4.38%)
kept                               319,122
```

The two conditions agree on all but 51 windows. Those 51 are the case the span band alone cannot
see — a window of the right total length whose rows do not tile it:

```
ticker  concept                       end          span   g3   g2   g1
DHR     NetIncomeLoss                 2009-07-03    280  189   88    3
LMT     NetIncomeLoss                 2009-06-30    275  182   91    2
TAP     NetIncomeLoss                 2009-03-31    275   91  182    2
MSI     OperatingIncomeLoss           2009-07-04    280  185   91    4
JCI     StockRepurchased              2016-12-31    281   91    6  184
DPZ     StockRepurchased              2012-06-17    282    2  112  168
YUM     DepreciationAndAmortization   2016-03-31    292   84  196   12
BBY     Capex                         2012-08-04    252   98   63   91
```

Each sums a quarter twice (the 2–12 day step) and omits another (the 168–196 day step). The span
band would have passed all of them.

---

## 2. What Part 1 removed

```
facts:  appeared = 0     changed = 94     disappeared = 19,094
```

**Every one of the 19,094 is accounted for.** 14,615 are the rejected windows of the base TTM
concepts (the table above sums to exactly 14,615). The other 4,479 are the derived series built on
them, which lose a value when an input loses one:

| derived | lost |
|---|---:|
| FFO_TTM | 1,295 |
| FCF_TTM | 1,149 |
| EPS_TTM_CALC | 973 |
| EBITDA_TTM | 947 |
| CoreOperatingEarnings | 65 |
| PPNR | 50 |
| **total** | **4,479** |

**The 94 changed rows are all `FFO_TTM`, and all one mechanism.** `build_valuation_history` builds
FFO as `NetIncomeLoss_TTM + DepreciationAndAmortization_TTM − GainLossOnSaleOfProperties_TTM` with
`gains.fillna(0)`. When the gains term is removed, `fillna(0)` substitutes zero instead of
propagating the gap, so FFO changes rather than disappearing. Checked on all 94: **94 of 94** lost
their gains term.

```
ARE 2013-06-30   gains 1,443,000 -> NaN     FFO 290,230,000 -> 291,673,000
```

That `fillna(0)` is pre-existing and is noted in section 8.

### Spot-checks — the removed values genuinely did not cover a year

Ten drawn at random from the removed set, with the four source rows the window summed:

```
DHR  ShareBasedCompensation_TTM  2009-10-02  span 371d  steps [189, 91, 91]   was     88,551,000
     ends 2008-09-26 / 2009-04-03 / 2009-07-03 / 2009-10-02
TSCO StockRepurchased_TTM        2011-06-25  span 364d  steps [91, 182, 91]   was    141,946,000
     ends 2010-06-26 / 2010-09-25 / 2011-03-26 / 2011-06-25
DLR  OperatingCashFlow_TTM       2011-09-30  span 365d  steps [182, 91, 92]   was    377,347,000
     ends 2010-09-30 / 2011-03-31 / 2011-06-30 / 2011-09-30
META StockIssued_TTM             2019-03-31  span 365d  steps [91, 92, 182]   was     14,000,000
     ends 2018-03-31 / 2018-06-30 / 2018-09-30 / 2019-03-31
JBL  StockIssued_TTM             2016-05-31  span 1004d steps [273, 365, 366] was      7,391,000
     ends 2013-08-31 / 2014-05-31 / 2015-05-31 / 2016-05-31
WAT  OperatingIncomeLoss_TTM     2020-03-28  span 182d  steps [2, 92, 88]     was    651,167,000
     ends 2019-09-28 / 2019-09-30 / 2019-12-31 / 2020-03-28
```

The first four skip exactly one quarter and cover fifteen months. **JBL covers 2.75 years.** WAT
covers six months and counts one quarter twice — Waters tags both the fiscal quarter end
(2019-09-28) and the calendar month end (2019-09-30) with the same figure.

The remaining four picks were `FCF_TTM`, `EBITDA_TTM` values, which have no base concept of their
own; they follow from their inputs.

### Per ticker

```
tickers losing at least one window: 495 of 501
tickers losing none:                  6      ABNB, CRWD, JKHY, LYV, ORCL, ROST
```

| windows lost | tickers |
|---|---:|
| 1–5 | 46 |
| 6–10 | 44 |
| 11–25 | 171 |
| 26–50 | 173 |
| 51–100 | 55 |
| 101–200 | 4 |
| 201–500 | 1 |
| > 500 | 1 |

Worst by share of their own windows:

| ticker | lost | share |
|---|---:|---:|
| **KR** | 501 | **100%** |
| PSKY | 4 | 100% |
| WAT | 233 | 28.8% |
| Q | 8 | 27.6% |
| MAA | 86 | 23.0% |
| BBY | 183 | 20.4% |

**Kroger loses every TTM value it had, and that is the correct outcome.** Its step histogram is
`{84: 28, 91: 2, 196: 12, 280: 4, 287: 1}` — there is no quarter-length step at all in twelve of
its year boundaries. The cause is upstream and specific: Kroger's Q1 is **16 weeks**, and its
raw fact durations are `{83, 111, 195, 279, 363}` days. `decumulate_period_values` emits a quarter
only when the year-to-date difference falls in **80–100 days**, so the 111-day Q1 is discarded
every single year, leaving a 196-day hole. Before this change KR had 501 four-row sums that each
covered fifteen months and were labelled TTM. This is recorded in section 8 — the fix belongs in
`decumulate_period_values`, not in the TTM layer.

The pattern is not exotic: **486 of 501 tickers have at least one 180–200 day step**, and 33 have
a duplicated period end ≤10 days apart (ACN, AMCR, AME, BALL, CAG, CAH, CAT, CHD, CIEN, CPRT, CSX,
DE, DHR, DPZ, FDS, FLEX, GRMN, HSY, J, JCI, KDP, KHC, LMT, MSI, NVDA, ON, SWK, TAP, TER, TSN,
VRSK, VTRS, WAT).

---

## 3. The boundary against `decumulate_period_values`

### The rule, stated operationally

> The annual path runs for a `(ticker, concept)` pair **only when the quarterly extraction
> produced no value at all** for that pair.

That is the code-level form of "the filer's facts are exclusively 12-month duration".
`decumulate_period_values` needs a sub-annual year-to-date point to difference; with only 12-month
facts it returns `[]`. The condition is checked on the extractor's own output rather than on the
raw durations, which matters — see the six cases below.

### Why the two paths cannot collide

Disjointness is **structural, not a runtime check**. A pair with no quarterly values contributes
no rows to the facts frame; `calculate_ttm` filters `df["concept"] == concept` and therefore
produces no row at all for it, let alone a value. The annual path is the only writer. Conversely,
where the quarterly extraction produced anything, the annual path returns `[]` immediately.

Confirmed empirically by the pipeline's own duplicate check on the full frame:

```
duplicates on (ticker, concept, end): 0
(ticker, concept) series carrying both provenance labels: 0
```

### Measured across all 501 tickers × 25 TTM concepts

```
(ticker, concept) pairs examined: 6,314

  both quarterly and annual   5,944
  no facts at all               284
  annual only                    64      <- Part 2's target
  quarterly only                 22
```

**64 annual-only pairs over 60 tickers, 658 annual values.**

| concept | pairs | annual values |
|---|---:|---:|
| ShareBasedCompensation | 27 | 345 |
| StockIssued | 15 | 125 |
| PretaxIncome | 6 | 58 |
| DepreciationAndAmortization | 4 | 71 |
| DividendsPerShare | 4 | 14 |
| StockRepurchased | 3 | 14 |
| IncomeTaxExpense | 2 | 8 |
| Capex, OperatingIncomeLoss, ResearchAndDevelopment | 3 | 23 |

### The extractor test and the duration test are not the same test

Six pairs yield zero quarterly values while *having* sub-annual raw facts: **ADM, C, EXC, KHC,
OTIS** (`StockIssued`/`StockRepurchased`) and **TKO** (`DividendsPerShare`). Their sub-annual facts
are half-year and nine-month year-to-date points with no first quarter, so every difference
`decumulate_period_values` can form is ~180 days — outside its 80–100 day window. Nothing can be
decumulated, which is the condition that matters. **A rule written on raw durations would have
excluded these six wrongly.**

### The tag investigation's "annual-only" list is a different classification

That report called a pair annual-only when it had an annual value in ≥80% of fiscal years *and*
quarterly coverage under 50% — a coverage test. This task's test is "nothing to decumulate". They
overlap but are not the same:

**17 of the 31 named pairs are annual-only under the strict test.** The other 14 (AWK, BALL, EMR,
F, HIG, NI, NWS, NWSA, PCG, PSX, WEC, AMZN, MCHP, NOW, VTRS, UAL) do produce quarterly values —
they are thin, not annual-only.

---

## 4. What Part 2 added

```
facts:  appeared = 778     changed = 0     disappeared = 0
```

Exactly the intended shape: additive, nothing touched.

| concept | added |
|---|---:|
| ShareBasedCompensation_TTM | 345 |
| StockIssued_TTM | 125 |
| DepreciationAndAmortization_TTM | 71 |
| FFO_TTM | 66 |
| PretaxIncome_TTM | 58 |
| EBITDA_TTM | 41 |
| StockRepurchased_TTM | 14 |
| DividendsPerShare_TTM | 14 |
| Capex_TTM | 13 |
| FCF_TTM | 13 |
| IncomeTaxExpense_TTM | 8 |
| OperatingIncomeLoss_TTM | 5 |
| ResearchAndDevelopment_TTM | 5 |

658 are the direct annual facts; the other 120 are the derived series (FFO, EBITDA, FCF) that
become computable once their input exists.

Top gainers: AFL 47, GL 46, ERIE 44, L 36, PEG 33, MTB 26, ALL 21, then a long tail at 16–19
(RF, COP, DAL, NEE, ATO, GE, MET, PRU, MCD, OXY, PG, AIG, T, ES, D, WMT).

### NEE

```
A_before   rows = 0   non-null = 0
B_part1    rows = 0   non-null = 0
C_part2    rows = 18  non-null = 18
```

```
2008-12-31   47,000,000     2017-12-31    76,000,000
2009-12-31   51,000,000     2018-12-31    82,000,000
2010-12-31   57,000,000     2019-12-31   100,000,000
2011-12-31   49,000,000     2020-12-31   107,000,000
2012-12-31   57,000,000     2021-12-31   119,000,000
2013-12-31   67,000,000     2022-12-31   142,000,000
2014-12-31   60,000,000     2023-12-31   139,000,000
2015-12-31   60,000,000     2024-12-31   138,000,000
2016-12-31   77,000,000     2025-12-31   185,000,000
```

The four values the tag report quoted (2022 142m, 2023 139m, 2024 138m, 2025 185m) reproduce
exactly. **The count is 18, not the 21 that report stated** — `extract_with_mode` keys on
`(end, days)` and keeps the newest filing per key, which collapses NEE's 48 raw 12-month facts to
18 distinct fiscal year ends.

### The named annual-only list

15 of the 31 named pairs gained values; **239 values in total**.

| gained | tickers |
|---|---|
| ShareBasedCompensation (17–18 each) | AIG, ALL, ATO, COP, DAL, ES, MET, NEE, OXY, PEG, PRU, WMT |
| ShareBasedCompensation (10 each) | CI, DOW |
| StockIssued (8) | OTIS |
| unchanged — not annual-only under the strict test | AWK, BALL, EMR, F, HIG, NI, NWS, NWSA, PCG, WEC, PSX, AMZN, MCHP, NOW, VTRS, UAL |

**PSX gains nothing and gets nothing.** It has exactly one quarterly `ShareBasedCompensation`
value and 16 annual ones. One quarterly value disqualifies it from the annual path, and four are
needed to form a rolling window — so it ends with no `ShareBasedCompensation_TTM` at all. See
section 8.

---

## 5. Provenance

A `ttm_source` column on the facts frame, carrying the value's derivation:

```python
TTM_SOURCE_ROLLING = "quarterly_rolling"   # four consecutive quarters summed
TTM_SOURCE_ANNUAL  = "annual_fact"         # one 12-month fact, taken as filed
```

Measured on the full frame:

```
None                 799,839     base facts and derived non-TTM concepts
quarterly_rolling    319,122
annual_fact              658
(ticker, concept) series carrying both labels:  0
```

A row only claims a derivation when it carries a number — masked windows keep `None`, so the
column never asserts a provenance for a value that does not exist.

Derived TTMs (`FCF_TTM`, `EBITDA_TTM`, `FFO_TTM`, `EPS_TTM_CALC`) are added by `add_as_concept`
downstream and carry `None`. Their provenance is the provenance of their inputs, which is visible
in the same frame.

### Decision on surfacing it in the app: **yes**

`ttm_source` should appear in the data tab, next to the `_TTM` value it describes. It is precisely
the "here is how this number was derived" signal the data tab exists for, and an
annual-cadence series that renders as a sparse line is otherwise indistinguishable from a series
with missing data.

**Not implemented here** — the task excludes UI changes. What was done instead: the column is
carried all the way through `filter_hidden_rows` and `add_growth_column` into `facts_full.parquet`,
which the data tab already reads, so the UI side is a rendering change with no pipeline work
behind it. `pivot_ticker` pivots on `values="value"` and ignores extra columns, so the column is
inert until something asks for it. Verified end to end.

---

## 6. The two diffs, measured separately

Part 1 was applied and diffed against the pre-change pipeline; Part 2 was then applied and diffed
against Part 1. All 501 tickers, one pre-built base facts frame, the only difference between runs
being the code under test.

### Part 1 — `A_before → B_part1`

| frame | appeared | changed | disappeared |
|---|---:|---:|---:|
| facts | 0 | 94 | 19,094 |
| metrics_long | 4 | 93 | 18,148 |
| valuation_history | 26 | 225 | 9,359 |

**Disappearances are the intended effect** and are accounted for above. The other two columns:

**metrics_long, 93 changed:** 82 `ffo_margin` (follows the 94 changed `FFO_TTM`) and 11
`buyback_distortion_flag`, each **1 → 0** because `StockRepurchased_TTM` at that date was removed —
a flag cannot fire without its input (NFLX 2009-09-30, CRL 2010-09-25, CPRT 2011-01-31,
MSI 2011-04-02, KR 2012-01-28, MOS 2013-12-31, WAT 2017-12-31 and 2019-09-28, VST 2018-03-31, …).

**metrics_long, 4 appeared — and this one is a genuine regression, reported rather than hidden:**

```
ON   2012-06-29  effective_tax_rate  NaN -> 2.745     (274%)
ON   2012-06-29  low_tax_rate_flag   NaN -> 0
GEN  2014-10-03  rotce               NaN -> 26.49
GEN  2015-01-02  rotce               NaN -> 16.41
```

`apply_denominator_scale_guard` blanks a ratio when its denominator is small relative to
`Revenue_TTM`. ON's `PretaxIncome_TTM` is $11m against $3.0bn of revenue (0.37%) and GEN's
`TangibleEquity` is $37m against $6.7bn — both below the 1% floor, both correctly blanked before.
Part 1 removed the *reference*, and the guard reads `too_small & scale_reference.notna()`, so a
missing reference means "not too small". **A guard that stops guarding when its yardstick
disappears is the wrong default**; it is pre-existing, out of this task's scope, and recorded in
section 8. Four rows.

**valuation_history, 225 changed and 26 appeared:** 93 `p_ffo` (follows FFO), 11
`buyback_distortion_flag` (as above), and 121 changed + 26 appeared `pe_to_revenue_growth`.
The last group traces to `wide.groupby("ticker")["Revenue_TTM"].pct_change(periods=4)`, whose
pandas default is `fill_method="ffill"` — removing a `Revenue_TTM` value makes the comparison
base a forward-filled earlier one. Worked through on CAG, which tags both 2010-02-27 and
2010-02-28:

```
Revenue_TTM   2010-02-27  11.883bn      2010-02-27  11.883bn
              2010-02-28  11.998bn  ->  2010-02-28  NaN
              2010-05-30  12.176bn      2010-05-30  NaN
```

At 2011-02-27 the four-back base was 11.998bn (growth 1.19%, below `MIN_PEG_REVENUE_GROWTH` = 2%,
so PEG was blanked) and is now the forward-filled 11.883bn (growth 2.17%, above the floor, so PEG
appears). The `ffill` default is noted in section 8.

**Rolling five-year mean lines — the reference the charts compare today's multiple against:**

| line | n | changed | disappeared |
|---|---:|---:|---:|
| avg_p_ffo_5y | 28,347 | **7,859** | 851 |
| avg_pfcf_5y | 25,953 | **6,477** | 584 |
| avg_pe_5y | 28,988 | **5,859** | 826 |
| avg_ev_ebitda_5y | 21,191 | **4,925** | 533 |
| avg_p_ppnr_5y | 1,348 | 343 | 31 |
| avg_p_core_earnings_5y | 852 | 263 | 47 |
| avg_p_tbv_5y | 24,418 | 85 | 25 |

This is the largest downstream effect of the whole task and it should be read plainly: **roughly a
quarter of the historical mean lines move.** They move because they were averaging multiples whose
denominators were not twelve-month figures. `avg_p_tbv_5y` barely moves (85 of 24,418) because
tangible book value is a balance-sheet position with no TTM denominator — which is the control
case confirming the effect runs through the TTM series and nothing else.

**Flags:**

| flag | before | after | Δ |
|---|---:|---:|---:|
| share_count_jump_flag | 734 | 734 | 0 |
| buyback_distortion_flag | 644 | 633 | −11 |
| inorganic_contaminated | 1,016 | 1,016 | 0 |
| low_tax_rate_flag | 4,196 | 4,060 | −136 |
| fcf_exceeds_ebitda | 1,984 | 1,821 | −163 |
| coverage flags (`quality.py`) | 743 | 743 | 0 |

### Part 2 — `B_part1 → C_part2`

| frame | appeared | changed | disappeared |
|---|---:|---:|---:|
| facts | 778 | **0** | **0** |
| metrics_long | 279 | **0** | **0** |
| valuation_history | 270 | **0** | **0** |

**Appearances are the intended effect, and there is nothing else to justify — zero changed, zero
disappeared, in all three frames.** That is the disjointness claim of section 3 confirmed on the
numbers: an additive path cannot have moved anything.

metrics_long gains: `ffo_margin` 66, `effective_tax_rate` 53, `low_tax_rate_flag` 53,
`fcf_exceeds_ebitda` 24, `net_debt_to_ebitda` 22, `fcf_margin` 13, `capex_intensity` 13,
`rule_of_40` 13, `payout_ratio` 7, `operating_margin` 5, `rd_intensity` 4, `operating_leverage` 3,
`operating_income_yoy_growth` 3.

valuation_history gains: `pfcf_ex_sbc` 143, `p_ffo` 65, `ev_ebitda` 22, `dividend_yield` 14,
`ev_fcf` 13, `pfcf_ratio` 13. The largest is `pfcf_ex_sbc` — which is the metric the tag
investigation was chasing when it found this defect.

**Rolling mean lines: 0 changed, 446 appeared** (avg_p_ffo_5y 262, avg_ev_ebitda_5y 129,
avg_pfcf_5y 55). A mean line gains points; none moves.

**Flags:** `low_tax_rate_flag` 4,060 → 4,065 (+5), `fcf_exceeds_ebitda` 1,821 → 1,834 (+13); all
others and the coverage flags unchanged.

### The tag investigation's named cases

**SRE** — the ticker whose two-year `ShareBasedCompensation` hole started this: 64 non-null
`ShareBasedCompensation_TTM` before, **62 after**. The two removed are the windows that reached
across the remaining hole. The 8 quarters the tag change added are still there and still summed;
what is gone is the pair of sums that spanned it.

**The 20 `owner_fcf` movers** (AMCR, AMGN, BG, CBRE, FCX, HBAN, HWM, JCI, LDOS, MOS, SNDK, SRE,
TDY, TER, TMUS, KR, …): non-null `pfcf_ex_sbc` across them goes **598 → 505 → 505**. The 93 lost
are windows that did not cover a year — which is what made their `owner_fcf` move when data was
added in the first place. Part 2 does not restore them: none of these tickers is annual-only.

---

## 7. Coverage threshold — measured, not changed

`check_data_quality` counts rows of the **base** concepts in the frame that exists *before*
`add_derived_concepts`. Part 1 changes no base row and Part 2 adds only `_TTM` rows, which are not
in `get_expected_concepts` and are filtered out of the count. Verified directly:

```
flags on the frame without the annual _TTM rows: 743
flags on the frame with them:                    743
identical: True
```

**No annual-only pair clears its flag, and 60 of the 64 carry one** — all at `count = 0`, i.e.
`MISSING`, against denominators of 19–77 quarters:

```
RF   ShareBasedCompensation   0 of 75      T    ShareBasedCompensation  0 of 77
STT  ShareBasedCompensation   0 of 75      TSN  ShareBasedCompensation  0 of 76
VZ   ShareBasedCompensation   0 of 75      WMT  ShareBasedCompensation  0 of 74
ZTS  StockIssued              0 of 60      VST  StockIssued             0 of 40
UBER DividendsPerShare        0 of 36      TKO  DividendsPerShare       0 of 19
```

**The finding: for a concept whose disclosure is legitimately annual, a quarterly coverage ratio
does not mean what the threshold assumes.** The flag reads "this company has never disclosed
share-based compensation". After this task the truth is "this company discloses it once a year,
and the pipeline now reads all of it". The number the flag reports — 0 of 75 — is arithmetically
correct and semantically wrong: 18 annual values against 18 fiscal years is complete coverage of
what the filer publishes.

The honest fix is a cadence-aware denominator (count fiscal years for an annual-cadence pair, not
quarters), which changes the meaning of every flag in the report and is an architecture decision.
**Per the task, the logic is unchanged and this is reported only.**

---

## 8. Deliberately not fixed

**`decumulate_period_values` discards any quarter that is not 80–100 days.** This is the direct
cause of Kroger losing 100% of its TTM values: KR's Q1 is 16 weeks (111-day facts), so it is
dropped every year and leaves a 196-day hole that Part 1 now correctly refuses to sum across.
486 of 501 tickers have at least one 180–200 day step. Part 1 makes the damage visible instead of
plausible, which is the improvement; recovering the quarters is a separate change in
`fetchers/edgar.py`, and it would need its own 12-week/16-week evidence exactly as this task
needed its span evidence.

**Duplicated period ends.** 33 tickers tag the same period twice, 1–10 days apart, usually a
fiscal quarter end and a calendar month end carrying an identical value (WAT 2024-06-29 and
2024-06-30, both 708,529,000). The step rule now refuses the windows that double-count them, but
the duplicate rows themselves remain in the facts frame and still appear in the data tab. The fix
belongs in `extract_period_values`, whose key is `(end, days)` and therefore treats them as
distinct periods.

**`apply_denominator_scale_guard` treats a missing scale reference as "passed".** Four metric
values reappeared in the Part 1 diff for this reason, one of them a 274% effective tax rate. The
guard should distinguish "the denominator is large enough" from "I cannot tell", and currently
does not.

**`pct_change(periods=4)` on `Revenue_TTM` uses pandas' `ffill` default.** A hole in the series is
silently bridged by the previous value, so a growth figure can compare against a date other than
the one four rows back. 26 `pe_to_revenue_growth` values appeared and 121 changed through this
path. One argument (`fill_method=None`) fixes it, but it would change the growth panel's coverage
across all 501 tickers and belongs in its own diff.

**`ffo["gains"].fillna(0)` in `build_valuation_history`.** A missing gains term is treated as a
zero gain rather than as unknown FFO. All 94 changed facts values in the Part 1 diff run through
it.

**The looser Part 2 rule: filling any date the rolling window leaves empty.** Measured — it would
add **15,081 values across 5,848 (ticker, concept) pairs**, against 658 across 64 for the strict
rule. Most of those dates are fiscal year ends where a 12-month fact exists and the rolling window
now produces nothing, so the values would be correct. It was **not** taken, for one reason: it
turns disjointness from a structural property into a runtime check. The strict rule cannot write
where the other path writes because the pair has no rows at all; the looser rule would append a
row at a date that already carries a masked `_TTM` row, producing a duplicate `(ticker, concept,
end)` and making correctness depend on a fill-order convention. That is the failure Step 2.1
exists to prevent. It is the obvious next task, and it is a bigger one than it looks.

**The 25 pairs with 1–3 quarterly values.** Too few to form a rolling window, too many to qualify
as annual-only, so they get no `_TTM` value from either path: PSX and ED (`ShareBasedCompensation`),
BDX, JPM, KVUE, SNDK, SOLV, SYF, TPL, LH, APTV, BF-B, GEV (`StockIssued`), ARES, CRWD, DUK, VEEV
(`StockRepurchased`), LH and RCL (`PretaxIncome`), RCL (`IncomeTaxExpense`), PYPL and Q
(`DividendsPerShare`), IRM (`GainLossOnSaleOfProperties`), SYF, WAT (`Capex`). Closing this needs
the looser rule above.

**Cadence-aware coverage flags.** Section 7.

**Everything outside the TTM layer.** No tag work, no split or `share_count_jump_flag` work, no new
concepts or metrics, no `PROFILE_HIDDEN` refactor, no UI or chart changes — per the task's scope.

---

## Files changed

| file | change |
|---|---|
| `metrics.py` | four window bounds with the empty run each came from; `calculate_ttm` masks a window that does not cover a year; `add_ttm_concepts` labels its rows `quarterly_rolling` |
| `parsers/parse_edgar.py` | new `annual_ttm_values`; `build_dataframe` gains `annual_ttm_concepts` and emits annual-only `_TTM` rows labelled `annual_fact`; base rows carry `ttm_source = None` |
| `config.py` | `TTM_SOURCE_ROLLING` / `TTM_SOURCE_ANNUAL` |
| `main.py` | both `build_dataframe` call sites pass `annual_ttm_concepts=TTM_CONCEPTS` |
| `MDs/metrics.md` | the `calculate_ttm` section now describes the calendar test |
| `MDs/bugfixes_opdate_history.md` | entry per convention |

`data/` and `figures/` untouched.

### Verification performed

```
[ok ] shift(fill_value=False) identical to the fillna form -- 25 concepts
[ok ] duplicates on (ticker, concept, end)                 -- 0
[ok ] series carrying both provenance labels                -- 0
[ok ] build_snapshot                     rows=21,945  concepts=75
[ok ] filter_hidden_rows                 1,119,619 -> 1,015,064
[ok ] add_growth_column                  ttm_source survives to the export frame
[ok ] no TTM concept is point_in_time    (the annual path would be wrong for one)
[ok ] every disappeared facts value attributed  14,615 base + 4,479 derived = 19,094
[ok ] every changed facts value attributed      94 of 94 lost their gains term
```

**Not verified:** no full refresh was run. Every figure comes from the local companyfacts cache and
a single yfinance price capture, driven through the pipeline's own functions.
