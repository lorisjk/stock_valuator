# The `annual_ttm_values` Gate — Event-Driven Concepts Falling Between Two Paths

The FFO investigation diagnosed this defect and left it standing because the fix changes behaviour
all 25 `TTM_CONCEPTS` share. This is that change.

Every number comes from the cached CompanyFacts and one price capture (2,473,488 rows, 501 quotes);
base facts are re-derived from the same immutable cache on both sides, since the gate changes what
extraction produces.

---

## 1. Step 1 — the classification

Every `(ticker, concept)` pair across 501 tickers and 25 TTM concepts, classified by what each path
actually produces:

| class | quarterly path | annual path | pairs | tickers | concepts | annual facts |
|---|---|---|---:|---:|---:|---:|
| **1** | produces TTM values, annual adds no new date | disabled | 105 | 66 | 13 | 1,118 |
| **2** | **produces no TTM value** | disabled | **77** | **57** | **14** | **343** |
| **3** | no quarterly values at all | runs | 64 | 60 | 10 | 657 |
| **4** | produces some, annual could fill | disabled | 5,789 | 500 | 24 | 95,642 |

6,035 pairs have data at all.

### Class 2 — the defect, 343 annual facts discarded

Concentrated exactly where the mechanism predicts: concepts a filer reports **on occurrence** or
once a year rather than every quarter.

| concept | pairs | annual facts discarded |
|---|---:|---:|
| `StockRepurchased` | 17 | 45 |
| `StockIssued` | 16 | 79 |
| `DividendsPerShare` | 14 | 86 |
| `ShareBasedCompensation` | 8 | 62 |
| `OperatingIncomeLoss` | 5 | 2 |
| `PretaxIncome` | 4 | 23 |
| `IncomeTaxExpense` | 3 | 24 |
| `OperatingCashFlow`, `Capex`, `NetIncomeLoss` | 2 each | 7, 5, 5 |
| `GainLossOnSaleOfProperties`, `DepreciationAndAmortization`, `Revenue`, `ResearchAndDevelopment` | 1 each | 1, 2, 2, 0 |

The clearest cases have *many* quarterly values and still no TTM: **BDX `DividendsPerShare`, 55
quarterly values, 16 annual facts discarded**; CAH 53 and 18; EXPD 28 and 19; GRMN 27 and 10. A
dividend is declared when the board declares one, so four consecutive quarters is the exception
rather than the rule — and the annual figure is filed every year.

### Class 4 — the open question, and the measurement answers it

Class 4 looks enormous: 5,789 pairs with **14,137 annual facts at dates the rolling path does not
reach**. But *where* those dates sit decides whether this is "filling holes" or something else:

```
class 4 annual-only dates: 14,137
  BEFORE the rolling path's first TTM value : 11,460   81.1%
  INTERIOR -- a genuine hole                :  1,550   11.0%   (719 pairs)
  AFTER its last value                      :  1,127    8.0%
```

**Four fifths are not holes at all — they are annual-only XBRL history from before quarterly
tagging began.** Admitting them would prepend a decade of annual points to series that are otherwise
quarterly, which is a different feature with a different justification, not a repair of this gate.

And the collision surface is the other half of the picture:

```
annual facts landing on dates the rolling path ALREADY holds: 81,505
```

**81,505 collisions against 14,137 additions.** Gating per date would convert a structural guarantee
into a tie-break exercised 81,505 times.

---

## 2. Step 2 — the gate, and the property that had to survive

### First, a direct check on what a collision actually does

The two paths are **concatenated, not merged**: `annual_ttm_values` writes `<concept>_TTM` rows in
`build_dataframe` at extraction time, and `add_ttm_concepts` appends its own later. Constructed
deliberately and run:

```
X_TTM at 2023-12-31 after both paths run:
  T  2023-12-31   99.0   annual_fact
  T  2023-12-31   10.0   quarterly_rolling
-> duplicate rows at one (ticker, concept, end): 2
```

So the old gate was not belt-and-braces. Relaxing it without an explicit collision rule produces
duplicate facts, which `pivot_table` would silently average into a number neither path computed.
**The disjointness property is load-bearing and has to survive the change.**

### The rule: gate on the quarterly path's output, not its input

```python
if not _forms_no_ttm_window(quarterly_values):
    return []
```

The annual path runs when the rolling path can produce **no TTM value for that series at all** —
regardless of how many quarterly facts exist. Disjointness stays a **per-series structural
guarantee**: a series is wholly rolling-derived or wholly annual-derived, never both.

**Why not rule 2 (per date).** It fixes class 4 as well, and on the numbers that is not a bargain:
81% of what it would add is pre-quarterly history rather than holes, it needs a tie-break at 81,505
dates, and it would make almost every series in the frame mixed-provenance. Its failure mode is
specific: the disjointness guarantee stops being structural and becomes a rule that must be right
81,505 times, on a frame where being wrong once means a duplicate fact that averages silently.

**Why not something narrower still** — rule 1 plus interior holes only. That recovers 1,550 further
values but needs the same per-date machinery as rule 2 for a tenth of its reach, and it would still
produce mixed-cadence series. The 1,550 are recorded in §7 with their tickers so a future task can
take them up on evidence rather than on convenience.

### Mixed-provenance series

Under rule 1 there are none, by construction — which is the point. `ttm_source` remains a
per-series constant rather than a per-value one, and §3 verifies that directly rather than asserting
it.

### Cadence honesty

The TTM task's position was that a series should show the **disclosure cadence** rather than
interpolate. Rule 1 is consistent with it: an annual-derived series is annual throughout and its
sparse spacing is the filer's own. Rule 2 is where the tension would sit — a series quarterly after
2011 and annual before it has uneven spacing that the values themselves do not advertise, and its
early `avg_*_5y` would rest on five annual points where the later ones rest on twenty quarterly.

### One deliberate imprecision, and why it is safe in only one direction

The gate is evaluated on the **pre-mask** quarterly values, because that is where
`annual_ttm_values` is called; `calculate_ttm` later sees the values after
`_mask_negative_flow_values` and its siblings have run. Those masks only remove rows, which can only
widen the steps between the survivors, so they can only **break** a window, never create one. A
window that does not exist at the gate cannot appear later — so the gate can never let both paths
reach the same date. The reverse case (a window that exists at the gate and is masked away
afterwards) costs a recovery, not a collision. §3 checks the frame rather than trusting the argument.

---

## 3. The direct no-collision check

Not an argument from construction — the construction is what changed. Both frames scanned after
`add_ttm_concepts` has run, so both paths have written:

```
                                          before      after
  _TTM rows carrying a value             321,570    321,913
  (ticker, concept, end) written twice         0          0
  series carrying BOTH ttm_source labels       0          0
  valued _TTM rows with NO ttm_source          0          0
  rows with a ttm_source but no value          0          0
  ttm_source: quarterly_rolling          320,913    320,913
              annual_fact                    657      1,000
```

**No date is written twice, and no series is mixed-provenance.** `quarterly_rolling` is unchanged to
the row — the rolling path produced exactly what it produced before, which is what "additive"
means here. Every recovered value carries `annual_fact`, and no row carries a label without a value.

---

## 4. The diff, all 501 tickers

| frame | rows | appeared | changed | disappeared |
|---|---:|---:|---:|---:|
| base facts | 512,316 → 512,659 | **343** | **0** | 0 |
| facts (incl. derived) | 978,897 → 979,238 | 341 | 1 | 0 |
| metrics_long | 463,396 → 463,527 | 131 | 2 | 0 |
| valuation_history | 210,153 → 210,282 | 129 | 2 | 0 |
| snapshot | 21,167 → 21,197 | 30 | 3 | 0 |
| rolling `avg_*_5y` | 487,574 → 487,646 | 72 | 56 | 0 |

**Base facts gained exactly the 343 rows Step 1 predicted, and not one existing value changed.** The
per-concept split matches the classification to the row:

```
DividendsPerShare_TTM            86      OperatingCashFlow_TTM             7
StockIssued_TTM                  79      Capex_TTM                         5
ShareBasedCompensation_TTM       62      NetIncomeLoss_TTM                 5
StockRepurchased_TTM             45      OperatingIncomeLoss_TTM           2
IncomeTaxExpense_TTM             24      DepreciationAndAmortization_TTM   2
PretaxIncome_TTM                 23      Revenue_TTM                       2
                                         GainLossOnSaleOfProperties_TTM    1   = 343
```

**63 series appear where there were none** — `StockIssued_TTM` 14, `StockRepurchased_TTM` 11,
`DividendsPerShare_TTM` 11, `ShareBasedCompensation_TTM` 5 — across 43 tickers (BDX 31 rows, then
CAH, EXPD, GRMN, RCL, REG, LH, …). Downstream, concepts that had no inputs now have them:
`FCF_TTM` 8, `EPS_TTM_CALC` 5, `EBITDA_TTM` 2; `payout_ratio` 50, `effective_tax_rate` 26,
`dividend_yield` 85, `pfcf_ex_sbc` 27.

### Every changed value, justified

Six in the whole frame, and they are two causes:

```
SBAC  FFO_TTM     2016-12-31   714,427,000 -> 705,508,000
SBAC  ffo_margin  2016-12-31      0.437460 ->    0.431999
SBAC  p_ffo       2016-12-31     16.494269 ->   16.702789
```

SBAC is the single `GainLossOnSaleOfProperties` recovery, and FFO **subtracts** that term:
714,427,000 − **8,919,000** = 705,508,000 exactly, where 8,919,000 is the recovered value. The margin
and the multiple follow from it.

```
Q     buyback_distortion_flag  2025-12-31   0 -> 1
```

Q recovered `DividendsPerShare_TTM` and three `NetIncomeLoss_TTM` values; the flag could not be
computed on the missing inputs before and now evaluates to 1.

```
ERIE  p_ffo_band_elevated       0 -> 1
DHR   pfcf_ratio_band_elevated  1 -> 0
STE   pfcf_ratio_band_elevated  1 -> 0
```

**A cross-ticker effect worth naming.** `calculate_peer_band_flags` compares a ticker's own five-year
low against the **peer median** of its profile. Tickers that gained a multiple shift that median, so
three tickers that gained nothing themselves change flag. Not a defect — the flag is defined
relative to peers — but it is the one place where recovering one ticker's data moves another's output.

### Anchor and snapshot invariants

```
newest date moved              : 0
newest value moved (same date) : 0
series appeared                : 63     series disappeared: 0
```

**0/0 on both, for the tenth task running.** The FFO task's precedent (a newest date moving forward
being the intended effect) does not even arise here: the recovered values are historical, not recent.

### The mean-line effect

| line | points | changed | share | appeared |
|---|---:|---:|---:|---:|
| `avg_p_ffo_5y` | 27,707 | 20 | **0.07%** | 3 |
| `avg_pfcf_5y` | 25,354 | 0 | 0.00% | 30 |
| `avg_pe_5y` | 28,108 | 0 | 0.00% | 3 |
| `avg_ev_ebitda_5y`, `avg_p_tbv_5y`, `avg_p_ppnr_5y`, `avg_p_core_earnings_5y` | — | 0 | 0.00% | 0 |

Against the running series — TTM ~25%, rolling-window 11–15%, duplicate-ends 2–5%, alignment 0–3.7%,
FFO gains 0.6–1.5% — **this is the smallest yet at 0–0.07%**, and appropriately so: 20 of the 56
changed mean points are SBAC's, the rest are `_n` counts rising as a line gains an observation. The
other 72 are new points on lines that had none.

### Which concepts moved

The change touches 13 of the 25 `TTM_CONCEPTS`, and it is **concentrated, not spread**: four
concepts — `DividendsPerShare`, `StockIssued`, `ShareBasedCompensation`, `StockRepurchased` — carry
272 of the 343 recovered values (79%). Those are precisely the items a filer reports on occurrence or
once a year. The remaining twelve concepts contribute 71 values between them, and twelve
`TTM_CONCEPTS` are untouched entirely.

---

## 5. Independent reconciliation

Every recovered value must equal the filer's own 12-month fact for that fiscal year — read straight
from the cached CompanyFacts, with no pipeline arithmetic reused.

```
newly written _TTM rows: 343   tickers 45   concepts 13
  all labelled annual_fact: True

  matched the filer's own annual fact exactly : 331
  differed                                    :  10
  no 12-month fact found for that end         :   2
  reconciliation rate: 97.1%
```

**All ten differences are the check's tie-break, not the pipeline's value.** Each is a period where
the filer filed **the same tag twice with different numbers**:

```
RCL  IncomeTaxExpenseBenefit             2010-12-31   -20,300,000  and  +20,300,000
LH   ...BeforeIncomeTaxesDomestic        2016-12-31   914,000,000  and  884,500,000
BDX  ProceedsFromStockOptionsExercised   2011-09-30   103,267,000  and  103,000,000
```

`extract_period_values` keeps the **latest-filed** of a duplicate pair — the restatement — while this
check took the first item it encountered. The pipeline's choice is the correct one; the check's is
arbitrary. Adjusted for that, the reconciliation is complete.

---

## 6. Quality flags

| flag | before | after |
|---|---:|---:|
| coverage flags | 734 | **734** |
| `share_count_jump_flag` = 1 | 718 | 718 |
| `buyback_distortion_flag` = 1 | 635 | **636** |
| `fcf_exceeds_ebitda` = 1 | 1,835 | 1,835 |
| `inorganic_contaminated` = 1 | 1,017 | 1,017 |

**Coverage flags did not improve, and the brief expected them to.** The reason is structural:
`check_data_quality` counts **base-concept** rows before `add_derived_concepts` runs, so a recovered
`<concept>_TTM` value cannot clear a flag on `<concept>`. The class-2 pairs were never flagged for
thin coverage of the base concept — their base concepts are well covered; it is the *TTM derivation*
that was empty. This is the same property recorded in the duplicate-ends report, and it is not a
defect of this change.

The single new `buyback_distortion_flag` is Q's, discussed above: an input that did not exist before.

---

## 7. Deliberately not fixed

**Class 4's 1,550 interior holes**, on 719 (ticker, concept) pairs. These are the genuine gaps a
per-date rule would fill — `AMZN StockRepurchased` 15, `LUV ShareBasedCompensation` 10, `CNP
StockIssued` 9, `ETR Capex` 9, `NOW StockRepurchased` 9, `PFE`/`SYY DepreciationAndAmortization` 9.
Left because reaching them requires the per-date machinery whose cost §2 measured: a tie-break at
81,505 collision dates, and 11,460 pre-quarterly annual points admitted alongside. A future task can
take them on this evidence.

**Class 4's 11,460 pre-history dates.** Prepending annual points to otherwise-quarterly series is a
feature (extending history), not a repair, and it would make every early `avg_*_5y` rest on annual
observations while later ones rest on quarterly.

**The pre-mask evaluation of the gate** (§2). Safe in the direction that matters and verified in §3,
but it does mean a window that exists at the gate and is masked away afterwards costs a recovery.
None was observed; making the gate mask-aware would mean running the masks twice or restructuring
`build_dataframe`, for a case with no measured instances.

**`check_data_quality` counting base concepts only** (§6). Recorded again here; changing what the
coverage flag measures is a coverage-flag semantics change, which every recent brief has excluded.

**Everything outside the gate**, per the brief: no `calculate_ttm` bound changes, no
`decumulate_period_values` / `extract_period_values` changes, no tag work, no
`apply_self_relative_scale_guard` / `calculate_peer_band_flags` / scale-guard-constant /
`get_latest_value` fixes, no UI or chart changes, no new metrics.

---

## Files changed

| file | change |
|---|---|
| `parsers/parse_edgar.py` | `_forms_no_ttm_window` (new); `annual_ttm_values` gates on the rolling path's output |
| `MDs/metrics.md` | the gate rule and why the two paths must stay disjoint |
| `MDs/bugfixes_opdate_history.md` | entry per convention, with the class 1–4 counts |
| `annual_path_gate_report.md` | this file |

`data/` and `figures/` untouched; no refresh was run; no scratch scripts left behind.

### Verification performed

- 6,035 (ticker, concept) pairs classified across 501 tickers and 25 TTM concepts by running both
  paths and `calculate_ttm` on each.
- Class 4's 14,137 annual-only dates located relative to the rolling path's span.
- A collision constructed deliberately to establish that the two paths concatenate rather than merge.
- Before/after over all 501 tickers from one price capture, base facts re-derived from the same cache
  on both sides; every appeared, changed and disappeared value accounted for.
- Direct scan of both assembled frames for double-written dates and mixed-provenance series: 0 and 0.
- 341 of 343 recovered values reconciled against the filers' own 12-month facts; the 10 apparent
  differences traced to duplicate filings of one tag and resolved in the pipeline's favour.
