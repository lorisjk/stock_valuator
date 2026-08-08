# Cross-Concept Row Alignment + the Two Remaining Silent Defaults

Four change groups, diffed separately. Every number below comes from **one price capture** — the
product-cleanup task established that `get_price_history` is not bit-reproducible across calls
(two consecutive AAPL fetches differed by up to 9.155e-05), so the before-state and all four
after-states are computed from the same 2,473,488-row price history, the same 501 current prices and
the same 512,078 base facts. No refresh was run.

The reports this task reads were restored from git — the working tree had them deleted.

---

## Part A — cross-concept row alignment

### A.1.1 — the gap distribution, and there is no empty run here either

Every gap between adjacent rows of the valuation pivot, all 501 tickers:

```
pivot rows: 33,913

  1   124  ############################################################
  2    22  ######################
  3    16  ################
  4    11  ###########
  5     9  #########
  6     9  #########
  7     2  ##
  8     -
  9     6
 10     3
 11-22 ~15   (scattered singles)
 23-25  -
 26-31  54   <- a month apart: a genuinely different period
 ...
 81-100 32,061  (95.96%)  <- one quarter
```

| bucket | pairs | share |
|---|---:|---:|
| **1–7** | **193** | 0.578% |
| 8–14 | 14 | 0.042% |
| 15–21 | 13 | 0.039% |
| 22–27 | 11 | 0.033% |
| 28–31 | 45 | 0.135% |
| 32–80 | 99 | 0.297% |
| 81–100 | 32,061 | 95.957% |
| 101–400 | 976 | 2.921% |

**193 pairs over 102 tickers**, confirming the rolling-window task's figure exactly. WAT 16, TAP 8,
JCI 6, CIEN 5, CAT 5.

**No empty run separates the two populations.** The distribution decays continuously — 124, 22, 16,
11, 9, 9, 2 — with a one-day hole at 8 and singles out to 22 before the month-apart cluster at
28–31. The only empty runs below 120 days are 23–25, 67–68, 75–76 and 99–111, none of which brackets
anything. This is the same finding the duplicate-ends task reported for its own analogous
measurement, so its bound is reused rather than a second one invented: **seven days, because a
52/53-week period end is the chosen weekday nearest the month end and can sit at most six days from
it.**

The data confirms the bound is safe in a way that measurement *can* settle: clustering at 7 days
produces **193 clusters, every one containing exactly two dates, the widest spanning 7 days, and
zero chains**. A runaway chain — 0, 5, 10 collapsing into one 10-day cluster — does not occur.

### A.1.2 — the stragglers are balance-sheet items, and the two rows never collide

```
concept on the minority side of a pair      pairs
  StockholdersEquity                          70
  CashAndEquivalents                          64
  SharesOutstanding                           34
  Revenue_TTM                                 32
  LongTermDebt                                28
  EPS_TTM_CALC                                 8
  FCF_TTM                                      7
  DividendsPerShare_TTM                        7
  ShareBasedCompensation_TTM                   5
  EBITDA_TTM                                   4
```

Systematic, and the brief's hypothesis is right as far as it goes: `StockholdersEquity` and
`CashAndEquivalents` are 134 of 259 minority appearances. But it is not *only* balance-sheet items —
`Revenue_TTM`, a flow, is the straggler in 32 pairs — so a fix aimed at two concepts would leave a
third of the population behind. The minority set is a **single concept in 149 of 193 pairs**.

**The decisive measurement: 0 of the 193 pairs share a concept.** The two rows are strictly
complementary — one holds nine concepts, the other holds one, and never the same one. So merging
them cannot create a value conflict and cannot discard a value. That removes the whole
"which value wins" question before it is asked.

### A.1.3 — the split exists in the facts frame too, and the report says so

```
all concepts        : 34,133 distinct (ticker, end), 228 pairs 1-7 days apart, 116 tickers
the 14 pivot concepts: 33,913 pivot rows,             193 pairs 1-7 days apart, 102 tickers
```

**The phenomenon is not created by the pivot** — 85% of it is already visible there, and 35 further
pairs involve concepts outside the fourteen (A 2018-10-31 vs 2018-11-01 splits `Goodwill` off with
the balance sheet; ABT splits `LongTermDebt` five days later; ADI `SharesOutstanding` six days
later). The brief said this would weaken the case for fixing it in the pivot only, and it does
weaken it. It does not overturn it, for a reason the measurement also gives: in the facts frame the
two rows are **correct** — the filer really did tag those concepts at those dates, and the data tab
showing both is showing what was filed. The *harm* is specific to the join: fourteen concepts
matched on an exact date produce two half-empty rows and two prices for one quarter. So the join is
where it is repaired.

### A.2 — the decision

**Option 1, in the pivot only.** The alternative — a cross-concept pass in the parser rewriting the
recorded end dates — fails on the pipeline's standing principle: it would move nine concepts' filed
dates to accommodate one, on no evidence that the filer was wrong, and every downstream consumer
would inherit the rewrite. Its failure mode is concrete: a value whose date no longer matches the
filing it came from, with no record that it was moved.

**Canonical date = the majority date, ties to the later.** The duplicate-ends task chose "later
always" and its argument was the anchor invariant. That argument does not survive contact with this
measurement:

```
tickers whose newest pivot row is inside a cluster:  0
```

**No anchor can move under either rule**, so the tie-breaker that decided the previous task is
silent here. What remains is where the quarter is: the majority date is the earlier one in 142 of
193 clusters, the later one in 34, tied in 17. "Later always" would relabel 142 quarters by the
position of a single balance-sheet item — ADM's whole 2017 Q4 moved to 2018-01-01 because
`StockholdersEquity` alone is tagged there. Ties go to the later date, keeping the earlier task's
preference where nothing else decides.

---

## Part B — the guard that passes when its reference is missing

### B.0 — the line the brief points at is a no-op

```python
too_small = denominator.abs() < min_denominator_scale_ratio * scale_reference.abs()
too_small = too_small & scale_reference.notna()          # <- does nothing
```

`5.0 < NaN` is already `False` in pandas, so `too_small` is already `False` wherever the reference is
missing. Verified directly — the function's output is identical with and without that line:

```
ratio 10, denominator 1, references [1000, NaN, 50], ratio threshold 0.01
  with the notna() line : [nan, 10.0, 10.0]
  without it            : [nan, 10.0, 10.0]
```

**The pass-when-missing behaviour is a property of the comparison, not of that line.** Changing it
therefore requires an explicit branch, not a deletion — which is worth stating because deleting the
line is the obvious-looking fix and would change nothing at all.

### B.1 — the exposure, and the values are *tamer* than the guarded ones

| metric | values | reference missing | share | tickers |
|---|---:|---:|---:|---:|
| `pb_ratio` (history) | 24,737 | 1,906 | 7.71% | 398 |
| `p_tbv` (history) | 19,835 | 954 | 4.81% | 288 |
| `roe` | 27,842 | 693 | 2.49% | 65 |
| `pe_ratio` | 26,584 | 588 | 2.21% | 56 |
| `p_ffo` | 26,064 | 572 | 2.19% | 48 |
| `effective_tax_rate` | 24,718 | 484 | 1.96% | 50 |
| `pfcf_ratio` | 22,195 | 380 | 1.71% | 46 |
| `ev_ebitda` | 18,227 | 311 | 1.71% | 28 |
| `ev_fcf` | 18,813 | 304 | 1.62% | 39 |
| `pfcf_ex_sbc` | 19,584 | 296 | 1.51% | 42 |
| `rotce` | 18,768 | 224 | 1.19% | 44 |
| `p_core_earnings` | 663 | 8 | 1.21% | 2 |
| `p_ppnr` | 1,321 | 2 | 0.15% | 1 |
| `debt_to_equity` | 23,369 | **0** | 0.00% | 0 |

**≈6,722 values reach a guarded metric unguarded.** `debt_to_equity` is structurally exempt: its
scale reference *is* its numerator (`LongTermDebt`), so the reference is missing only when the ratio
is missing too.

**The distributions answer the brief's question, and the answer is "merely unverified":**

| metric | median \|value\|, ref present | median, ref MISSING | max, present | max, MISSING |
|---|---:|---:|---:|---:|
| `pe_ratio` | 18.66 | **17.19** | 25,466 | **1,783** |
| `pb_ratio` | 2.50 | **1.41** | 827 | 812 |
| `p_tbv` | 5.14 | **2.49** | 6,816 | **418** |
| `ev_ebitda` | 12.17 | **9.29** | 41,152 | **295** |
| `p_ffo` | 12.84 | **9.57** | 5,580 | **447** |
| `roe` | 0.159 | **0.102** | 33.1 | 82.0 |

The unguarded population is **systematically tamer** than the guarded one — lower medians on every
multiple, and maxima one to two orders of magnitude smaller. Blanking them would remove ~6,700 values
that behave better than the ones the guard lets through.

Two exceptions, named rather than averaged away:

- **`effective_tax_rate`**: p99 is **2.394 unguarded against 1.282 guarded**. This is the one metric
  where the missing reference does correlate with implausibility, and it is the path the TTM report
  traced its 274% tax rate through.
- **`p_ppnr`, TFC, 2 values at 36.9–42.5** against a guarded median of 5.97.

### B.2 — the decision: fill the reference rather than choose between blanking and passing

The brief offers blank / pass / flag. The measurement makes a fourth option available and better
than all three:

```
tickers with no Revenue_TTM anywhere : 0
tickers with Revenue_TTM             : 501
unguarded values on tickers that report revenue in other periods:
  effective_tax_rate 484 of 484   roe 693 of 693   rotce 224 of 224
```

**Every missing reference is a per-period hole, not an absent concept.** No ticker lacks a yardstick;
only this period's copy of it is missing. And a scale guard asks an order-of-magnitude question —
"is this denominator less than 1% of the business" — which a neighbouring period's revenue answers as
well as the missing one would.

So the reference is carried across the hole (forward, then backward for a leading one) and the guard
then evaluates normally. This:

- does not blank ~6,700 values that the distributions say are fine,
- does not silently pass either — the guard now runs on every one of them,
- uses evidence that exists rather than a policy about evidence that does not,
- and needs no new flag, no new concept and no third behaviour to explain.

Blanking's failure mode, for the record: it would delete `pb_ratio` for 398 tickers and `p_tbv` for
288, in each case removing the *lower* half of the distribution — the opposite of what a scale guard
is for. Passing's failure mode is what the TTM report found: a 274% tax rate published because the
one check that would have caught it could not run.

The two different constants (0.01 in `build_snapshot`, 0.001 in `build_valuation_history` for
`pb_ratio` and `p_tbv`) are **not reconciled here**, per the brief. The fix is orthogonal to them:
filling the reference changes *whether* the guard can evaluate, the constant still decides *what it
decides*. Both call sites get a filled reference and keep their own constant.

---

## Part C — `ffo["gains"].fillna(0)`

### C.1 — coverage of the gains term, per REIT

```
29 REITs
  never produce GainLossOnSaleOfProperties_TTM :  12
  produce it in some periods                   :  17
  produce it in every period                   :   0
```

Not one REIT has the term in every period. Coverage among the seventeen ranges from **1.5%** to
92.9%:

```
EXR   1/67   DLR   1/64   KIM   5/72   BXP   9/72   FRT   9/67   PLD  11/63
PSA  29/72   UDR  27/67   ESS  28/62   DOC  34/70   O    35/68   ARE  37/64
WELL 39/66   EQR  47/72   REG  26/31   AVB  50/54   INVH 39/42

never: AMT CCI CPT EQIX HST IRM MAA SBAC SPG VICI VTR WY
```

Across all REIT FFO periods, the term is present in **427 of ~1,836** — so roughly **77% of every
REIT's FFO history is built on the zero-fill**.

### C.2 — the missing periods are not zero-gain periods

Two measurements settle this.

**The tag is essentially never used to report a zero.** Of the 427 periods where it is present, only
**10 carry the value 0**; 417 carry a non-zero gain. A filer that had no disposals does not tag the
concept as zero — it omits it. So "absent" and "zero" are not the same statement, and the zero-fill
asserts the second from the first.

**Absence tracks era, not economics.** In the "some" case the tagged periods form a contiguous recent
block and the gaps are the early years:

```
ARE   tagged from 2013-12-31   missing 2010-2012      EQR   tagged from 2014-12-31   missing 2008-2013
O     tagged from 2017-12-31   missing 2009-2011      DOC   tagged from 2015-12-31   missing 2008-2010
ESS   tagged from 2017-12-31   missing 2010-2013      AVB   tagged from 2013-12-31   missing 2012-2013
```

REITs sold properties in 2009–2013. What changed in 2013–2017 was XBRL tagging practice, not
disposal activity.

**And for the twelve "none" REITs, the raw facts say the pipeline is looking in the wrong place.**
The concept queries four tags — `GainLossOnSaleOfProperties`, `GainsLossesOnSalesOfInvestmentRealEstate`,
`GainLossOnSaleOfPropertiesNetOfTax`, `GainLossOnDispositionOfRealEstate`. Read straight out of each
one's `us-gaap` facts:

| REIT | a queried tag present? | a disposal-gain tag it does use |
|---|---|---|
| SPG | no | `GainLossOnSaleOfPropertiesBeforeApplicableIncomeTaxes` |
| HST | no | `GainLossOnSaleOfPropertiesNetOfApplicableIncomeTaxes`, `GainLossOnDispositionOfProperty` |
| VTR | no | `GainLossOnDispositionOfRealEstateDiscontinuedOperations`, `GainLossOnDispositionOfAssets` |
| WY | no | `GainLossOnSaleOfTimberProperty`, `GainLossOnSaleOfProperty` |
| AMT | no | `GainLossOnDispositionOfOtherAssets` |
| EQIX, SBAC | no | `GainLossOnSaleOfPropertyPlantEquipment`, `GainLossOnDispositionOfAssets1` |
| **CPT, IRM, MAA** | **yes** | the queried tag is present and still produces no `_TTM` value |
| **CCI, VICI** | no | **no disposal-gain tag of any kind** |

So of twelve "never tags it" REITs, **two** (CCI, VICI) are even candidates for "genuinely never
reported a property gain". Eight use a tag the pipeline does not ask for. Three have a queried tag in
their raw facts that nevertheless yields no TTM value — a third failure mode, in the extraction
rather than the tag list.

### C.3 — how much the term is worth

Where it is tagged, dropping it moves FFO by:

```
median  13.5%      p75  28.8%      p90  44.5%      p99  167%      max  422%
```

This is not a rounding term. `|gains|` as a share of `|FFO|` runs to a median of **29.6% for EQR**
and 29.0% for AVB.

### C.4 — the verdict: confirmed not resolvable, and the zero-fill is kept with the reason recorded

**From the pipeline's own output the two cases cannot be told apart** — a missing gains term looks
identical whether the REIT sold nothing or the pipeline asked for the wrong tag. That is the
"confirmed not resolvable" outcome the brief allows, and the raw facts make it worse than merely
unresolvable: the evidence points at *extraction* in ten of twelve cases.

**Blanking `FFO_TTM` where the term is unknown is nonetheless the wrong response.** It would delete
~77% of REIT FFO history and remove `p_ffo` entirely for twelve REITs — the one multiple the REIT
profile is built around — because of a tag list this task is explicitly told not to change. That
trades a known overstatement for a certain, larger loss.

**So the value is kept and the imputation is recorded**, following the `ttm_source` precedent
established by the TTM task: a column on the facts frame naming how the term was obtained, so a
consumer can tell a reported gains term from an assumed one instead of having to know.

```
ffo_gains_source = "reported"      the term came from a filed fact
                 = "imputed_zero"  no fact was found; zero was assumed
```

**No FFO value changes.** That is the honest outcome, and it is deliberate: the measurement says the
computation cannot be improved without the tag work the brief excludes, so the change is to stop the
assumption being invisible rather than to replace one guess with another.

**The real fix, with its evidence, for whoever takes the tag task:** add
`GainLossOnSaleOfPropertiesBeforeApplicableIncomeTaxes`,
`GainLossOnSaleOfPropertiesNetOfApplicableIncomeTaxes`, `GainLossOnDispositionOfProperty`,
`GainLossOnDispositionOfRealEstateDiscontinuedOperations` and `GainLossOnSaleOfPropertyPlantEquipment`
to the concept's tag list, and investigate why CPT, IRM and MAA yield nothing from a tag that is
present.

### C.5 — the REIT's own reported FFO cannot be used as a check

The brief asks to verify a changed `FFO_TTM` against the REIT's own published FFO. **That check is
not available from this data source.** FFO is a NAREIT non-GAAP measure that filers report in a
company extension namespace, and the SEC `companyfacts` API returns only `us-gaap`, `dei`, `srt`,
`invest`, `ecd` and `ffd`. Searched across fifteen REITs' cached facts:

```
O AMT SPG PLD EQIX WELL PSA DLR ARE AVB VICI MAA ESS CPT REG
  us-gaap tags matching "FundsFromOperations" or "FFO":  none, for any of them
  namespaces present: dei, srt, invest, ecd, ffd -- no company extension
```

Moot in this case, since no FFO value changed, but it is the reason the check is absent rather than
omitted.

### A.3 — implemented

`canonical_period_ends(facts, concepts, max_gap_days=7)` in `main.py` returns
`(ticker, end) -> canonical_end`, and `build_valuation_history` snaps three keys onto it: the
pivot, the `revenue_yoy_growth` merge, and the `buyback_distortion_flag` merge.

The last two are not incidental. `calculate_growth` is keyed on `Revenue_TTM`'s own end, and
**`Revenue_TTM` is the straggler in 32 of the 193 clusters** — without snapping it too, those
quarters would silently lose their growth figure. The buyback flag is worse: the first run of this
change **lost 53 flag values** because the flag is computed on the facts frame's dates and the merge
no longer matched. Both were caught by the diff and fixed before the diff below.

### A.4 — the diff (`before` -> `afterA`)

**The pivot loses exactly the 193 rows it should:**

```
distinct (ticker, end) in the valuation pivot:  33,913 -> 33,720   = -193
```

| frame | rows | appeared | changed | disappeared |
|---|---:|---:|---:|---:|
| base facts | 512,078 | 0 | **0** | 0 |
| facts (incl. every `_TTM`) | 978,477 | 0 | **0** | 0 |
| metrics_long | 463,416 | 0 | **0** | 0 |
| valuation_history | 210,952 → 211,243 | 361 | **0** | 70 |
| snapshot | 21,189 | 0 | 8 | 0 |
| rolling `avg_*_5y` | 490,101 → 487,578 | 64 | 4,120 | 2,587 |

**No fact value changed and no multiple's value changed** — the required footprint. Every one of the
361 appearances and 70 disappearances is accounted for:

```
appeared 361                              disappeared 70
  ev_sales                 99               buyback_distortion_flag  53
  ev_fcf                   59               pe_ratio                  9
  pb_ratio                 58               dividend_yield            3
  buyback_distortion_flag  53               pb_ratio                  3
  ev_ebitda                49               pe_to_revenue_growth      2
  pfcf_ratio               14
  pfcf_ex_sbc              12
  pe_ratio                  9
  dividend_yield            3
  pe_to_revenue_growth      3
  p_tbv                     2
```

Two mechanisms, and they are different:

- **Relocations** — the 53 `buyback_distortion_flag`, 9 `pe_ratio`, 3 `dividend_yield` and 2–3
  `pe_to_revenue_growth` values appear on one side and disappear on the other in equal numbers.
  These are the same values at the canonical date instead of the straggler date.
- **Genuinely new multiples** — 99 `ev_sales`, 59 `ev_fcf`, 58 `pb_ratio`, 49 `ev_ebitda`. A row
  holding `LongTermDebt` and `CashAndEquivalents` but not `Revenue_TTM` could not produce `ev_sales`;
  merged with its twin it can. **This is the alignment paying for itself**: 232 multiples that the
  split had made incomputable.

**Anchor invariant: 0 newest dates moved, 0 newest values moved, 0 series appeared or disappeared.**
As A.2 predicted from the cluster measurement.

**Quality flags: every one unchanged** — coverage 737, `share_count_jump_flag` 718,
`buyback_distortion_flag` 635, `fcf_exceeds_ebitda` 1,835, `inorganic_contaminated` 1,017.

### A.5 — the plausibility check

**A collision is the only way alignment could drop a value, and there are none:**

```
source values across the 14 concepts        : 268,252
values colliding on a canonical key         :       0
values inside merged clusters, recomputed   :   1,423
mismatches against the merged row           :       0
```

Each of the 1,423 values inside a merged cluster was read back out of the merged pivot row and
compared to its source. Read one out in full:

```
ADM  2017-12-31 (8 concepts) + 2018-01-01 (1)   ->  one row at 2017-12-31
  2017-12-31  CashAndEquivalents             804,000,000
  2017-12-31  DividendsPerShare_TTM                 1.28
  2017-12-31  EPS_TTM_CALC                          2.79
  2017-12-31  FCF_TTM                     -7,015,000,000
  2017-12-31  LongTermDebt                 6,636,000,000
  2017-12-31  Revenue_TTM                 60,828,000,000
  2017-12-31  ShareBasedCompensation_TTM      66,000,000
  2017-12-31  SharesOutstanding              572,000,000
  2018-01-01  StockholdersEquity          18,322,000,000    <- the straggler, now in the same row
```

### B.3 — implemented

`metrics.py` gains `fill_scale_reference(frame, reference_col)` — forward-fill then back-fill within
the ticker — and `apply_denominator_scale_guard` loses its no-op line. Three call paths hand in a
filled reference:

- `calculate_ratio` (`effective_tax_rate`, `roe`, `rotce`, `debt_to_equity`),
- `build_valuation_history`, once for all ten guarded multiples,
- `build_snapshot`, where the reference is the **newest period the filer actually reported revenue
  in** rather than the newest row of the concept — kept as a separate `_revenue_scale` column so the
  published `revenue_ttm` and `get_latest_value`'s treatment of a trailing null are untouched, that
  being a question the brief excludes.

### B.4 — the diff (`afterA` -> `afterB`)

| frame | rows | appeared | changed | disappeared |
|---|---:|---:|---:|---:|
| base facts | 512,078 | 0 | **0** | 0 |
| facts | 978,477 | 0 | **0** | 0 |
| metrics_long | 463,416 → 463,396 | 0 | **0** | 20 |
| valuation_history | 211,243 → 211,236 | 0 | **0** | 7 |
| snapshot | 21,189 | 0 | **0** | 0 |
| rolling `avg_*_5y` | 487,578 → 487,574 | 0 | 176 | 4 |

**Only guarded metrics moved, and only by disappearing** — the guard now fires where it previously
could not evaluate. Nothing changed value, which is the expected shape: filling a reference cannot
alter a ratio, only whether it survives.

**27 values of ~6,700 exposed are blanked — 0.4% — and every one is an extreme:**

```
effective_tax_rate   VLO  2010-06-30   1,092.9%      <- the species the TTM report traced
                     PLD  2014-03-31     441.9%
                     ON   2012-03-30      77.3%
                     CINF 2020-03-31    -162.1%
roe                  ATO  2010-12-31   8,198.6%
                     DAL  2009-12-31    -504.9%
rotce                MRSH 2013-06-30   3,097.6%
                     GEN  2014-10-03   2,648.6%
pb_ratio             ATO  2010-12-31     812.2
pe_ratio             AES  2010-12-31     652.6
                     DAL  2010-06-30     339.3
pfcf_ex_sbc          VLO  2010-03-31   1,193.3
                     TRGP 2012-09-30     212.6
ev_fcf               VLO  2010-03-31     166.2
pfcf_ratio           VLO  2010-03-31      84.0
```

Plus 6 `low_tax_rate_flag` values that were derived from the blanked tax rates.

**This is the decision vindicated on the data.** Blanking on a missing reference would have deleted
~6,700 values; letting the guard evaluate deletes 27, and each of those is a ratio no reader would
have believed. The ~6,673 that survive are the ones the distributions in B.1 said were fine.

**Anchor invariant: 0/0/0. Every quality flag unchanged.** Mean lines: `avg_pe_5y` 0.14%,
`avg_pfcf_5y` 0.07%, the other five 0.00%.

### C.6 — implemented, and the diff (`afterB` -> `afterC`)

```python
    ffo["ffo_gains_source"] = np.where(ffo["gains"].notna(), FFO_GAINS_REPORTED, FFO_GAINS_IMPUTED_ZERO)
    ffo["gains"] = ffo["gains"].fillna(0)
```

| frame | rows | appeared | changed | disappeared |
|---|---:|---:|---:|---:|
| base facts | 512,078 | 0 | **0** | 0 |
| facts | 978,477 | 0 | **0** | 0 |
| metrics_long | 463,396 | 0 | **0** | 0 |
| valuation_history | 211,236 | 0 | **0** | 0 |
| snapshot | 21,189 | 0 | **0** | 0 |
| rolling `avg_*_5y` | 487,574 | 0 | **0** | 0 |

**Nothing moved, by design.** The facts frame gains a column — `(1,015,239, 5) -> (1,015,239, 6)` —
and that is the whole change:

```
ffo_gains_source
  None            1,013,403     every non-FFO_TTM row
  imputed_zero        1,409     77.3% of FFO_TTM
  reported              427     22.7%

per ticker: 12 REITs at 100% imputed (AMT CCI CPT EQIX HST IRM MAA SBAC SPG VICI VTR WY)
```

**The snapshot still reads the same `FFO_TTM` column** rather than recomputing — `get_latest_value(facts, "FFO_TTM")` is untouched — so the snapshot's `p_ffo` and the history's `p_ffo` cannot diverge on
this term. The zero-change snapshot diff is that property holding.

---

## Part D — the two small findings

Both are settled by inspection rather than by measurement, and D.1 turns out not to be the judgement
call the brief expected.

### D.1 — REIT PEG without a REIT P/E

**It is not a judgement about REIT economics. It is one missing entry in a mechanism that already
exists.**

`config.is_hidden` resolves a derived concept through `_DERIVED_CONCEPT_CONSUMERS`: a thing is hidden
when everything that consumes it is hidden. The `reit` profile hides `pe_ratio`, and the map already
carries `EPS_TTM_CALC`, `eps_ttm`, `pe_ttm`, `avg_pe_5y`, `avg_pe_5y_median`, `avg_pe_5y_diverges`,
`avg_pe_5y_n`, `avg_pe_5y_history_too_short` and `EPS_QUARTERLY_CALC`, all pointing at `["pe_ratio"]`.
So for a REIT:

```
is_hidden("O", "pe_ratio")             True
is_hidden("O", "eps_ttm")              True
is_hidden("O", "pe_ttm")               True
is_hidden("O", "avg_pe_5y")            True
is_hidden("O", "EPS_TTM_CALC")         True
is_hidden("O", "pe_to_revenue_growth") False     <- the only survivor
```

Every other thing built on GAAP earnings is already hidden for REITs. `pe_to_revenue_growth` has no
entry in the map, so it slips through — and it is a P/E divided by a growth rate, i.e. the hidden
metric with a denominator attached. Dividing by growth does not remove property depreciation from
the numerator.

**`reit` is the only profile that hides `pe_ratio`** (29 tickers), so the fix cannot have an
unintended reach into other profiles.

The alternative — unhide `pe_ratio` for REITs — would require also unhiding `eps_ttm`, `pe_ttm`,
`avg_pe_5y` and `EPS_TTM_CALC`, i.e. reversing the profile's entire position on GAAP earnings, on no
evidence. That is what makes this clear-cut enough to implement rather than propose.

**Implemented** as one entry, using the existing mechanism rather than a second one:

```python
    "pe_to_revenue_growth": ["pe_ratio"],
```

### D.2 — `calculate_rolling_average` is dead

Confirmed by grep across every `.py` in the project: **one occurrence, its own `def`**. Zero call
sites, zero imports. `MDs/metrics.md` and `rolling_window_report.md` both already record it as having
no callers.

Removed, along with its two documentation references.

---


### D.3 — the diff (`afterC` -> `afterD`)

| frame | rows | appeared | changed | disappeared |
|---|---:|---:|---:|---:|
| base facts | 512,078 | 0 | **0** | 0 |
| facts | 978,477 | 0 | **0** | 0 |
| metrics_long | 463,396 | 0 | **0** | 0 |
| valuation_history | 211,236 → 210,153 | 0 | **0** | 1,083 |
| snapshot | 21,189 → 21,167 | 0 | **0** | 22 |
| rolling `avg_*_5y` | 487,574 | 0 | **0** | 0 |

**Visibility only, exactly as the brief required: 0 computed values changed.** Every one of the
1,083 disappearances is `pe_to_revenue_growth`, on **29 tickers, all of them `reit`** — the figure
matches the product-cleanup report's count exactly. 22 of the 29 also lose the snapshot marker
(AMT, DLR, DOC, EQIX, EQR, ESS, EXR, FRT, HST, INVH, IRM, KIM, O, PLD, PSA, REG, SBAC, SPG, UDR,
VICI, VTR, WELL); the other seven had no snapshot PEG to lose. **No non-REIT ticker is affected.**

D.2 needs no diff: a function with zero call sites cannot change output, which is the same fact that
justified removing it.

---

## The four groups together

`before -> afterD` is exactly the sum of the four:

```
valuation pivot rows      33,913 -> 33,720          (A)
base facts / facts        0 changed                 (all four)
metrics_long              20 disappeared            (B)
valuation_history         361 appeared (A) / 1,160 disappeared (A 77, B 7, D 1,083 -- 2 of the
                          pe_to_revenue_growth losses are A's relocations, not D's)
snapshot                  8 changed (A) / 22 disappeared (D)
facts columns             5 -> 6                    (C)
```

**Anchor invariant across all four: 0 newest dates moved, 0 newest values moved, 0 series appeared
or disappeared.**

### The mean-line effect

| line | points | changed | share |
|---|---:|---:|---:|
| `avg_ev_ebitda_5y` | 20,826 | 762 | **3.66%** |
| `avg_pfcf_5y` | 25,464 | 250 | **0.98%** |
| `avg_p_tbv_5y` | 24,376 | 218 | **0.89%** |
| `avg_p_ffo_5y` | 27,832 | 173 | **0.62%** |
| `avg_pe_5y` | 28,246 | 85 | **0.30%** |
| `avg_p_ppnr_5y` | 1,317 | 0 | 0.00% |
| `avg_p_core_earnings_5y` | 807 | 0 | 0.00% |

Group A accounts for almost all of it (3.66% / 0.91% / 0.89% / 0.62% / 0.16%), B for the rest
(`avg_pe_5y` 0.14%, `avg_pfcf_5y` 0.07%), C and D for **none**.

Against the running series — TTM ~25%, rolling-window 11–15%, duplicate-ends 2–5%, decumulation
0.2–0.6% — **this task lands at 0–3.7%, at the low end**, which is what four changes that move no
value should look like: the mean lines move because 189 pivot rows left the frame and 27 outliers
were blanked, not because any multiple was recomputed.

### Quality flags

| flag | before | after all four |
|---|---:|---:|
| coverage flags | 737 | **737** |
| `share_count_jump_flag` = 1 | 718 | **718** |
| `buyback_distortion_flag` = 1 | 635 | **635** |
| `fcf_exceeds_ebitda` = 1 | 1,835 | **1,835** |
| `inorganic_contaminated` = 1 | 1,017 | **1,017** |
| `avg_*_5y_history_too_short` = 1 | 162 | 162 |
| `avg_*_5y_diverges` = 1 | 107 | 106 |

Every flag computed from facts is unchanged, which follows from no fact value changing. The single
`avg_pfcf_5y_diverges` flip is downstream of group A's mean-line movement.

---

## Deliberately not fixed

**The gains tag list** (Part C) — the actual fix for the FFO zero-fill, with the specific tags named
in C.2. Excluded by the brief as tag work, and it is the change that would let a future task revisit
C's verdict with data instead of a label.

**Why CPT, IRM and MAA produce no `GainLossOnSaleOfProperties_TTM` from a tag that is present in
their raw facts.** A third failure mode, in the extraction rather than the tag list. Found while
measuring C; not diagnosed.

**The 35 near-pairs outside the fourteen pivot concepts** (228 in the facts frame against 193 in the
pivot). They involve concepts no multiple consumes, so no chart or snapshot doubles because of them,
and the data tab showing both rows is showing what was filed.

**The snapshot-versus-history scale-guard constants** (0.01 against 0.001 for `pb_ratio` and
`p_tbv`) — excluded by the brief, and orthogonal to Part B: filling the reference changes whether the
guard can evaluate, the constant still decides what it concludes.

**`get_latest_value` returning the newest row even when its value is null** — excluded by the brief.
Part B routes around it with a separate `_revenue_scale` column rather than changing it.

**`apply_self_relative_scale_guard`'s 17-row centred window** — a genuinely positional question about
a value's neighbours, and scale work besides.

**`calculate_peer_band_flags` anchoring on `pd.Timestamp.today()`**, so its five-year peer window
moves with the run date rather than the data.

---

## Files changed

| file | change |
|---|---|
| `main.py` | A: `canonical_period_ends` + three snapped keys in `build_valuation_history`. B: filled scale reference in `build_valuation_history` and `build_snapshot`. C: `ffo_gains_source`. |
| `metrics.py` | B: `fill_scale_reference`, no-op line removed, `calculate_ratio` uses the fill. D.2: `calculate_rolling_average` removed. |
| `config.py` | C: `FFO_GAINS_REPORTED` / `FFO_GAINS_IMPUTED_ZERO`. D.1: the `pe_to_revenue_growth` consumers entry. |
| `MDs/metrics.md` | the scale guard and the fill; the removed function |
| `MDs/main.md` | the pivot's canonical key |
| `MDs/bugfixes_opdate_history.md` | entry per convention |
| `alignment_and_defaults_report.md` | this file |

`data/` and `figures/` untouched; no refresh was run; no scratch scripts left behind.

### Verification performed

- One price capture (2,473,488 rows), one set of current prices, one base-facts frame; five pipeline
  runs from the same inputs, so no price-source non-reproducibility enters any comparison.
- Four diffs, one per change group, plus the combined diff confirming they sum.
- A: 193 clusters measured for size and span (all 2 dates, none over 7 days, no chains); 268,252
  source values checked for collisions (0); 1,423 values inside merged clusters read back out of the
  merged rows (0 mismatches).
- B: the no-op line demonstrated by identical output with and without it; all 27 blanked values
  listed and inspected.
- C: coverage measured per REIT; the raw `us-gaap` facts of all twelve never-tagging REITs read
  directly; fifteen REITs searched for a published FFO tag (none exists in this data source).
- D.2: grep across every `.py` — one occurrence, its own `def`.
- Anchor invariant checked after every group and on the combined diff: 0/0/0 throughout.
- All modules re-imported after each change.
