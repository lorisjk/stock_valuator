# Directional Scale-Error Detection — Downward Errors and Cross-Concept Scope

Input: sections 4 and 7 of `scale_outlier_audit_report.md`. The audit gated the upward sweep on
evidence and left two things it could not do without a new instrument: reach values that are
implausibly *large*, and decide *which* of three mutually-inconsistent numbers is the wrong one.

**Answer up front: scale errors are a `SharesOutstanding` problem, and the measurement says so
rather than the five known cases.** The instrument works, and after it the five named periods are
handled — two repaired from their own filing, three dropped. Unlike the previous task's result,
this one does reach the charts: Sherwin-Williams was being drawn with a **price/book of 3,377**.

---

## 1. Step 1 — the true scope

### 1a. Within-accession cross-tag disagreement

27 of the 35 concepts reachable through `CONCEPT_CANDIDATES` and its profile/ticker overrides
have more than one candidate tag. For every one, every ticker, every accession and period, the
candidate values were compared and the pairs more than 5x apart recorded.

**A first pass keyed cells on `(accn, start, end)` and found only 4 `SharesOutstanding` cells —
missing Sherwin-Williams entirely.** `CommonStockSharesOutstanding` is an instant fact with no
`start`; the weighted-average tags are durations. Keyed that way the two never meet, which is
exactly the comparison the audit identified. Re-keyed on `(accn, end)`:

| concept | cells at a clean power of ten | tickers |
|---|---:|---:|
| LongTermDebt | 1,541 | 229 |
| DepreciationAndAmortization | 1,536 | 243 |
| StockIssued | 446 | 117 |
| Revenue | 274 | 32 |
| **SharesOutstanding** | **244** | **68** |
| StockRepurchased | 152 | 70 |
| PretaxIncome | 84 | 30 |
| ShareBasedCompensation | 48 | 24 |
| CashAndEquivalents | 46 | 10 |
| NetIncomeLoss | 42 | 22 |
| Capex | 33 | 14 |
| DividendsPerShare / StockholdersEquity / others | 23 / 22 / 8 | |

**4,501 cells look like a power-of-ten disagreement. Almost none of them are scale errors.** The
pairs give it away immediately: `LongTermDebtCurrent` against `LongTermDebt`,
`AmortizationOfIntangibleAssets` against `DepreciationDepletionAndAmortization`,
`SalesRevenueServicesNet` against `SalesRevenueNet`. Those are components against totals that
happen to sit about 10x apart — the mirror image of the trap the split task hit, where a
plausible ratio was the algorithm's vocabulary rather than evidence.

### The discriminator, and it is measurable rather than a judgement call

A scale error is *the same number re-typed*, so the ratio's deviation from the exact power of ten
is only the two tags' genuine difference. Two unrelated quantities landing near 10x deviate at
random inside the window:

| concept | cells | median deviation from the exact power of ten |
|---|---:|---:|
| **SharesOutstanding** | 244 | **0.0026** |
| CashAndEquivalents | 46 | 0.0079 |
| ShareBasedCompensation | 48 | 0.0115 |
| StockRepurchased | 152 | 0.0121 |
| StockholdersEquity | 22 | 0.0130 |
| PretaxIncome / Revenue / LongTermDebt | 84 / 274 / 1,541 | 0.0137 – 0.0141 |
| NetIncomeLoss / DepreciationAndAmortization | 42 / 1,536 | 0.0152 / 0.0156 |
| Capex | 33 | 0.0180 |

`SharesOutstanding` sits **five times tighter than every other concept**, all of which cluster at
0.012–0.018 — uniform noise across the +/-7% window. And every one of its 244 cells is exactly
10^3 (177) or 10^6 (67), no other exponent: the signature of a table headed "in thousands" or
"in millions".

Inspection confirms the split. `NetIncomeLoss = 52,000,000` against
`NetIncomeLossAvailableToCommonStockholders = 5,283,000,000` for ABBV is not a mis-typed scale,
it is two different figures. `CashAndCashEquivalentsAtCarryingValue` against
`CashCashEquivalentsRestrictedCash...` for ADP is client funds. `PaymentsToAcquireProductiveAssets`
against `PaymentsToAcquirePropertyPlantAndEquipment` for ALB is a subset.

**Verdict: `SharesOutstanding` is the only concept in the registry whose candidate tags are
synonyms, so it is the only one where a cross-tag disagreement is interpretable at all. The
instrument is not general, and the data says the problem is not either.**

### 1b. The EPS-inconsistency set, classified directionally

`net income / shares = EPS` is symmetric. Each of the three has its own series, though, and a
scale error moves exactly one of them off its own history. Comparing each quantity against its
own median magnitude turns the symmetric test into a directional one.

Re-derived: **40 periods on 11 tickers** with a >=100x inconsistency surviving the pipeline. (The
audit reported 47; that count keyed the EPS/net-income pairing less strictly and double-counted
periods reported under two tag pairs. 40 is the corrected figure.)

| verdict | periods | who |
|---|---:|---|
| **share count wrong** | **6** | AIG 2008-06-30, ARE 2011-03-31, SHW 2007-12-31, SHW 2008-09-30, TFC 2008-06-30, COHR 2019-03-31 |
| net income wrong | 1 | CTVA 2021-09-30 |
| both out of line (the whole filing is scaled) | 2 | ATO 2009-12-31, LUV 2010-06-30 |
| neither out of line — a basis difference, or the EPS tag itself | **31** | CTVA (15), HAL (10), HIG (4), TMO (2) |

**The audit's inspection of HAL, HIG, CTVA and TMO holds up**: their share counts sit within 0.01
dex of their own series while net income moves. Of the 9 real problems, three (COHR, ATO, LUV)
are already corrected by the upward sweep, leaving exactly the **five named periods**. The
directional test rediscovers them independently and finds nothing else.

### 1c. Downward outliers, per concept

Values more than 31x above their own series' median, after the current pipeline:

| concept | rows | tickers | | concept | rows | tickers |
|---|---:|---:|---|---|---:|---:|
| StockIssued | 328 | 121 | | PretaxIncome | 14 | 5 |
| StockRepurchased | 144 | 35 | | NetIncomeLoss | 12 | 5 |
| Goodwill | 66 | 8 | | DepreciationAndAmortization | 11 | 3 |
| IncomeTaxExpense | 58 | 18 | | DividendsPerShare | 10 | 7 |
| LongTermDebt | 29 | 5 | | OperatingIncomeLoss | 9 | 3 |
| CashAndEquivalents | 27 | 13 | | **SharesOutstanding** | **5** | **4** |
| Capex | 18 | 6 | | ShareBasedCompensation | 2 | 2 |
| StockholdersEquity | 15 | 3 | | Revenue | 1 | 1 |

The large counts are all *flow* concepts, where one quarter genuinely dwarfing the rest is a real
event — a secondary offering, a buyback programme, a goodwill impairment. **None of them is
corroborated as a scale error by anything in 1a**, because their candidate tags are not synonyms
and the cross-tag test cannot speak. `SharesOutstanding`, a stock quantity that moves by single
digits per quarter, has 5 — and those five are the named cases.

---

## 2. The detector

### Magnitude floor: 5x, justified the way the split task justified its 20%

`_SIBLING_MIN_LOG = 0.7`. The three share tags are the same quantity measured differently —
diluted weighted average, basic weighted average, period-end common — and differ by a few percent
in normal operation; the widest legitimate gap seen in the universe is under 15%. Below 5x the
test would be wider than the effect it claims to detect, which is the failure the split task's
20% floor was chosen to avoid. `_SIBLING_POWER_TOL = 0.05` allows the ratio to sit up to 12% off
the exact power of ten, which is the room those measurement differences need.

### Which value wins: the sibling supplies the exponent, not the number

The brief suggested that where the accession carries a correct `CommonStockSharesOutstanding`,
using it is extraction rather than correction. **That was implemented first and it was wrong.**

```
SHW FY2007, one accession:
  WeightedAverageNumberOfDilutedSharesOutstanding = 130,924,690,000   <- the series' own measure
  CommonStockSharesOutstanding                    =     122,814,241   <- a different measure
  NetIncomeLoss 615,578,000  /  EarningsPerShareDiluted 4.70 = 130,974,043
```

The sibling is the **period-end** count, 6.2% below the diluted weighted average the series is
built from and that the filing's own EPS demands. Substituting it puts a silent measurement step
into the middle of the history. So the rule takes only the exponent: the sibling establishes that
the value is out by 10^3, and the value is divided by 10^3 in place, keeping its own measure.

Corroboration for the choice is the audit's own EPS arithmetic keyed on `(accn, start, end)` plus
the value's distance from its own series (`_OUT_OF_LINE_LOG = 2.0` — a scale error is >=100x,
series drift is nowhere near).

### Unresolved disagreements: leave as filed

If no sibling establishes an exponent and the EPS arithmetic does not independently convict the
share count, nothing is changed. A value merely *suspected* wrong is not the same as one proven
wrong, and the audit's base-rate argument applies: the mechanisms here are right far more often
than not, so acting without evidence is the losing trade. **No case in the universe reached this
branch** — every detection resolved through one of the two routes.

### Composition with the existing gate

```
raw facts -> extract -> split basis -> upward sweep -> corroboration gate -> directional repair
```

The repair runs last and only looks at values >=2 dex above their own series median. The sweep
moves values *toward* the median by construction, so a swept value cannot then be 2 dex above it.
That is the argument; the measurement confirms it: **0 values touched by both mechanisms**, over
every ticker where the sweep makes any proposal.

---

## 3. Treatment, per class

| class | count | treatment | why |
|---|---:|---|---|
| a sibling in the same accession establishes the exponent | 2 | **rescale in place** | the correct magnitude is in the filing; nothing is invented |
| no sibling, but three signals convict the value | 3 | **drop the row** | nothing supplies a replacement, and 130,248,736,000,000 shares is not a better input than a gap |
| suspected, not proven | 0 | leave as filed | |

No `_KNOWN_BAD_FACTS` entries were added, per the brief — the general rule is the deliverable.

### The full list of detections

| ticker | period | before | after | route |
|---|---|---:|---:|---|
| SHW | 2007-12-31 | 392,774,070,000 | **392,774,070** | sibling exponent, /10^3 |
| SHW | 2008-09-30 | 354,550,059,000 | **354,550,059** | sibling exponent, /10^3 |
| AIG | 2008-06-30 | 130,248,736,000,000 | **dropped** | series + EPS, no sibling |
| ARE | 2011-03-31 | 54,967,755,000 | **dropped** | series + EPS, no sibling |
| TFC | 2008-06-30 | 549,758,000,000 | **dropped** | series + EPS, no sibling |

---

## 4. Threshold sensitivity of the shipped sweep

`_GATE_LOG_GAP` decides which values the sweep looks at; `_MATCH_TOLERANCE` decides which factors
it will accept. Both were left unaudited by the previous task.

| `_GATE_LOG_GAP` | `_MATCH_TOLERANCE` | proposed | accepted | rejected |
|---:|---:|---:|---:|---:|
| 1.00 | 0.5 | 279 | 269 | 10 |
| 1.25 | 0.5 | 279 | 269 | 10 |
| **1.50** | **0.5** | **279** | **269** | **10** |
| 1.75 | 0.5 | 271 | 269 | 2 |
| 2.00 | 0.5 | 271 | 269 | 2 |
| 2.50 | 0.5 | 267 | 267 | 0 |
| 1.50 | 0.2 | 267 | 262 | 5 |
| 1.50 | 0.3 | 271 | 266 | 5 |
| 1.50 | 0.7 | 279 | 269 | 10 |
| 1.50 | 1.0 | 279 | 269 | 10 |

**The accepted set moves by 7 rows out of 32,061 across the whole range** — 262 to 269, while the
gate absorbs the variation by rejecting 0 to 10. That is the property the audit hoped for and
could not measure: the thresholds are not load-bearing once proposals are corroborated. **Left
unchanged**, on the evidence, following the model of the 0.5 corroboration ratio in the split
report.

---

## 5. Non-regression, all 501 tickers

### Facts

```
rows 511,464 -> 511,461   appeared=0   changed=2   disappeared=3
```

| check | result |
|---|---|
| **anchor invariant**: newest `SharesOutstanding` unchanged, date and value | **ok — 498 of 498 tickers** |
| no ticker lost its newest period | ok |
| no value rewritten by both the sweep and the repair | **ok — 0 double-touched** |
| Agilent's 406 and the rest of the no-evidence class unaffected | ok — the only 5 rows that moved are listed above |
| the five named downward cases handled | ok — 2 repaired, 3 dropped |

### Downstream, every difference

```
derived facts        appeared=0  changed=3  disappeared=6
metrics_long         appeared=0  changed=3  disappeared=8
valuation_history    appeared=0  changed=4  disappeared=2
```

**This one reaches the charts.** The valuation history in full:

| ticker | period | concept | before | after |
|---|---|---|---:|---:|
| SHW | 2007-12-31 | `pb_ratio` | **3,376.87** | **3.38** |
| SHW | 2008-09-30 | `pb_ratio` | 3,142.12 | 3.14 |
| SHW | 2007-12-31 | `p_tbv` | **7,641.69** | **7.64** |
| SHW | 2008-09-30 | `p_tbv` | 7,426.26 | 7.43 |
| TFC | 2008-06-30 | `pb_ratio` | 497.27 | gone |
| ARE | 2011-03-31 | `pb_ratio` | 848.17 | gone |

The derived facts: SHW's `EPS_QUARTERLY_CALC` for Q3-2008 goes 0.00050 -> **0.4995**, and the
three dropped share counts take their `EPS_QUARTERLY_CALC` with them (AIG -0.0000411, ARE
0.000574, TFC 0.000784 — all nonsense). `metrics_long` loses TFC's `payout_ratio_quarterly` of
**586.75** and seven `share_count_jump_flag` markers.

| rolling 5-year mean | points changed |
|---|---:|
| `avg_p_tbv_5y` | 20 |
| `avg_pe_5y` | 19 |
| `avg_p_ffo_5y` | 19 |
| all others | 0 |

### Flags

| flag | before | after |
|---|---:|---:|
| `share_count_jump_flag` | 744 | **734** |
| `buyback_distortion_flag` | 644 | 644 |
| `inorganic_contaminated` | 1,016 | 1,016 |
| `low_tax_rate_flag` | 4,196 | 4,196 |
| coverage flags | 743 | 743 |

Ten jump-flag markers go: they were the flag correctly firing on the discontinuities the bad rows
created. Three flip 1 -> 0 (ARE 2010-12-31, SHW 2008-09-30, SHW 2008-12-31) and seven disappear
with their dropped rows.

### Independent plausibility check

Internal consistency proves the code does what it says. The filer proves the numbers:

| | filed net income | filed diluted EPS | implied share count | repaired to | gap |
|---|---:|---:|---:|---:|---:|
| SHW FY2007 | 615,578,000 | 4.70 | **130,974,043** | 130,924,690 | **0.04%** |
| SHW Q3-2008 | 177,081,000 | 1.50 | **118,054,000** | 118,183,353 | **0.11%** |

(Both on the as-filed basis; the split basis then multiplies by 3, giving the 392,774,070 and
354,550,059 in the diff.) After the repair SHW's series runs 392.8m -> 356.1m -> 354.6m ->
354.5m -> 354.1m — continuous, the 2007-2008 step being the company's real buyback.

---

## 6. Deliberately not fixed

**The cross-tag detector is not extended to other concepts.** Measured, not assumed: their
candidate tags are components and totals, their power-of-ten "disagreements" deviate at random
where `SharesOutstanding`'s cluster at 0.26%, and treating a `LongTermDebtCurrent`/`LongTermDebt`
ratio as a scale error would corrupt 1,541 correct cells. If a concept ever gains a synonym-only
candidate list, the same instrument applies unchanged.

**`CTVA 2021-09-30`, where the *net income* is the mis-scaled quantity.** The directional test
names it, but repairing a net income needs a `NetIncomeLoss` sibling set, and that concept's two
candidates are not synonyms. One period, and it is out of this task's scope.

**The 31 "neither out of line" periods on HAL, HIG, CTVA and TMO.** The inconsistency is real but
lands on the EPS tag or on a basis difference, and neither is a share-count problem. They will
keep showing up in any symmetric scan; that is what this classification is for.

**`ATO 2009-12-31` and `LUV 2010-06-30`, whole filings tagged in thousands.** Already corrected
by the upward sweep, and correctly so — recorded here because the directional test flags them as
"both out of line", which would be the wrong reading if the sweep were ever removed.

**`calculate_ttm` still rolls over four available rows rather than four calendar quarters** —
carried forward through four tasks now, still untouched, still separate.

---

## Files changed

| file | change |
|---|---|
| `parsers/parse_edgar.py` | new `_sibling_scale_power`, `_income_is_sound`, `_series_median_log`, `_directional_scale_repair`; `build_dataframe` runs the repair after the corroboration gate. `_normalize_scale_outliers`, `_corroborated_scale_correction` and their thresholds are unchanged. |
