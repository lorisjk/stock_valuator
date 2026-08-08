# FFO Gains Term — Tag Coverage and the Extraction Failure

**One change group, not two.** Part A's diagnosis turned out to have no fix of its own: the value is
not lost in extraction, and the one place it *could* be changed is shared behaviour the brief says to
report rather than touch. Part A's remedy **is** Part B. §1 sets that out; §6 diffs the single group.

Prices and price history come from one capture (2,473,488 rows, 501 quotes). Base facts are
re-derived from the same immutable cache for the after-state, since the tag list changes what
extraction produces — the constraint the brief sets is on the *price* source, which is fetched once.

---

## 1. Part A — the diagnosis: not an extraction failure

### 1.1 The facts reach the pipeline intact

CPT, IRM and MAA each have a queried tag in their raw `us-gaap` facts, and **extraction works on all
three**. Traced tag → `extract_period_values` → `decumulate_period_values` → `extract_with_mode`:

```
CPT  GainLossOnSaleOfProperties               19 raw facts -> 10 kept -> 5 quarterly values
IRM  GainLossOnSaleOfProperties                7 raw facts ->  5 kept -> 2 quarterly values
     GainsLossesOnSalesOfInvestmentRealEstate  1 raw fact  ->  1 kept -> 1 quarterly value
MAA  GainsLossesOnSalesOfInvestmentRealEstate 12 raw facts ->  8 kept -> 4 quarterly values
```

No duration mismatch, no sign problem, no units problem, no mode problem. The durations are ordinary
quarters (89, 90, 91 days) and the values are plausible.

### 1.2 The value is lost at the TTM window, and correctly so

`GainLossOnSaleOfProperties` is in `TTM_CONCEPTS`, so the published value is
`GainLossOnSaleOfProperties_TTM` — a rolling four-quarter sum that, since the TTM task, checks it is
looking at four *consecutive* quarters. Their quarterly ends are not:

```
CPT  2014-12-31  2015-03-31  2015-12-31  2016-06-30  2016-09-30   steps  90, 275, 182, 92
IRM  2017-06-30  2018-09-30  2018-12-31                           steps 457,  92
MAA  2010-03-31  2010-06-30  2010-09-30  2014-03-31               steps  91,  92, 1278
```

`calculate_ttm` refuses every window, correctly. Compare a REIT that works: O has 44 quarterly values
with long consecutive runs and gets 35 TTM values; EQR 52 → 47.

**The cause is that this concept is event-driven, not periodic.** A REIT tags a property gain in the
quarters it sells something and omits the tag otherwise, so a four-consecutive-quarter window is
available only to filers who happen to sell (or tag a zero) four quarters running.

### 1.3 The annual fallback is switched off by the very values that are too sparse to use

`parse_edgar.annual_ttm_values` exists for exactly this shape — a filer whose 12-month facts are the
only usable ones — but its gate is:

```python
    if quarterly_values:
        return []
```

CPT has **13 FY facts** and 5 quarterly values. The five quarterly values are too scattered to build
a window, and their existence disables the annual path that could have used the thirteen. The filer
falls between the two paths. The TTM report called the two paths "disjoint by construction"; this is
the same disjointness producing a gap instead of an overlap.

### 1.4 Is the mechanism general? Yes — and it is not fixed here

Nothing about this is specific to FFO or to these three tickers. Any concept that is reported on
occurrence rather than every period is exposed: the quarterly path yields too few values to form a
window, and the annual path is disabled by their presence.

Widening the gate — for instance, letting the annual path supply dates the quarterly path could not
reach — is **shared extraction behaviour that all 25 `TTM_CONCEPTS` depend on**, and `calculate_ttm`
is explicitly out of scope. Per the brief's instruction for exactly this case: **reported with the
evidence, not fixed.** It needs its own change and its own diff, because it would move every thin
concept in the frame at once.

**What does fix CPT, IRM and MAA is the tag list** — more tags means more quarterly values means
consecutive runs. Measured in §4: CPT 0 → 10 TTM values, MAA 0 → 26, IRM 0 → 5. That is why Part A
has no separate change group.

---

## 2. The tag survey, all 29 REITs

Every `us-gaap` tag in the 29 cached CompanyFacts files whose name contains a gain/loss on a
disposal, sale, property, real estate or asset. Read from the facts, not guessed.

| tag | REITs | facts | queried | units |
|---|---:|---:|---|---|
| `DiscontinuedOperationGainLossOnDisposalOfDiscontinuedOperationNetOfTax` | 23 | 998 | – | USD |
| `GainLossOnSaleOfProperties` | 16 | 885 | **yes** | USD |
| `GainsLossesOnSalesOfInvestmentRealEstate` | 13 | 1,014 | **yes** | USD |
| `GainLossOnDispositionOfAssets` | 12 | 626 | – | USD |
| `EquityMethodInvestmentRealizedGainLossOnDisposal` | 11 | 265 | – | USD |
| `DiscontinuedOperationGainLossFromDisposalOfDiscontinuedOperationBeforeIncomeTax` | 10 | 153 | – | USD |
| `GainLossOnDispositionOfAssets1` | 10 | 351 | – | USD |
| `GainLossOnDispositionOfRealEstateDiscontinuedOperations` | 9 | 255 | – | USD |
| `GainLossOnSaleOfPropertyPlantEquipment` | 9 | 397 | – | USD |
| `GainLossOnSaleOfPropertiesNetOfApplicableIncomeTaxes` | 8 | 383 | – | USD |
| `DisposalGroupNotDiscontinuedOperationGainLossOnDisposal` | 5 | 224 | – | USD |
| `GainLossOnDispositionOfProperty` | 5 | 35 | – | USD |
| `GainLossOnSaleOfProperty` | 5 | 121 | – | USD |
| `GainLossOnSaleOfPropertiesApplicableIncomeTaxes` | 4 | 85 | – | USD |
| `GainLossOnSaleOfPropertiesBeforeApplicableIncomeTaxes` | 3 | 92 | – | USD |
| `GainsLossesOnSalesOfOtherRealEstate` | 2 | 17 | – | USD |
| `GainLossOnDispositionOfOtherAssets` | 1 | 3 | – | USD |
| `GainLossOnSaleOfTimberProperty` | 1 | 29 | – | USD |
| *(6 further per-share, tax-expense and FX variants)* | 1–2 | 3–50 | – | mixed |

All amounts are `USD`; the only non-USD entries are per-share variants, which are a different
quantity and are not candidates.

**Two corrections to the alignment report's starting list**, both from reading the facts:

- **SPG's `GainLossOnSaleOfPropertiesBeforeApplicableIncomeTaxes` is a single fact.** The alignment
  report said SPG "uses a tag the pipeline does not query", which is true and useless — one fact
  cannot produce a quarterly series, let alone a TTM window. SPG gains nothing from the tag work.
- **`GainLossOnSaleOfPropertiesNetOfTax`, already queried, appears in no REIT's facts at all.** It has
  been dead weight in the list; harmless, and left alone.

---

## 3. A/B/C classification

| class | REITs | tickers |
|---|---:|---|
| **A — tag gap, and the fix recovers coverage** | **15** | ARE, BXP, CPT, DLR, EQIX, FRT, HST, IRM, KIM, MAA, PLD, REG, UDR, VTR, WY |
| **A — already covered by the queried tags** | 9 | AVB, DOC, EQR, ESS, EXR, INVH, O, PSA, WELL |
| **B — genuine absence** | 4 | AMT, CCI, SBAC, SPG |
| **C — structurally unavailable** | 1 | VICI |

15 + 9 + 4 + 1 = 29. The five in B and C stay at zero TTM values after the change.

**Class B and C, confirmed from the raw facts rather than inherited:**

- **VICI — class C.** Not one gain/loss-on-disposal tag of any kind, in any namespace the API
  returns. A 2017 spin-off whose portfolio is triple-net leased; it has not reported a property
  disposal gain in XBRL.
- **CCI — class B.** 77 facts, all `DiscontinuedOperationGainLossOnDisposalOfDiscontinuedOperationNetOfTax`
  plus per-share and FX variants. Those are the fiber/small-cell **business** disposals, not sales of
  depreciable real property. CCI reports no property-disposal gain.
- **AMT — class B.** Three facts of `GainLossOnDispositionOfOtherAssets` and ten discontinued-operation
  entries. "Other assets" is explicitly not the quantity FFO adjusts for.
- **SBAC — class B in effect.** Four `GainLossOnSaleOfPropertyPlantEquipment` facts and eleven
  `...Assets1`; the accepted list yields one quarterly value and no window. Too thin to matter either
  way.
- **SPG — class B in effect**, per §2: one unqueried fact.

For these five the `imputed_zero` label stands, and §5 says what that now means.

---

## 4. The tags added, each with its evidence

### 4.1 Mode: `fallback`, unchanged, and that is the load-bearing decision

The concept keeps `mode: "fallback"`, which takes **the first tag in list order that reports a given
period end** and never sums. That is what makes it safe to list tags that measure overlapping scopes:

- A filer reporting the same gain **pre-tax and net-of-tax** — BXP has 75 facts of one and 7 of the
  other — cannot have them added together. Ordering decides which is used; both are never used at once.
- A **narrower** tag placed after a property-scoped one can only fill period ends the property-scoped
  tag left empty. It can never override a value the filer tagged as a property gain.

Ordering therefore carries the whole argument, and the list is ordered by scope:

```python
"GainLossOnSaleOfProperties",                                # existing
"GainsLossesOnSalesOfInvestmentRealEstate",                  # existing
"GainLossOnSaleOfPropertiesNetOfTax",                        # existing (present in 0 REITs)
"GainLossOnDispositionOfRealEstate",                         # existing
"GainLossOnSaleOfPropertiesNetOfApplicableIncomeTaxes",      # + property, net of tax
"GainLossOnSaleOfPropertiesBeforeApplicableIncomeTaxes",     # + property, pre-tax
"GainLossOnDispositionOfRealEstateDiscontinuedOperations",   # + real estate, discontinued ops
"GainsLossesOnSalesOfOtherRealEstate",                       # + real estate
"GainLossOnDispositionOfProperty",                           # + property
"GainLossOnSaleOfProperty",                                  # + property
"GainLossOnSaleOfTimberProperty",                            # + WY's real property
"GainLossOnSaleOfPropertyPlantEquipment",                    # + last: fills only empty periods
```

**Net-of-tax before pre-tax**, for two reasons: FFO starts from net income, so the figure that
actually flowed through it is the consistent one; and it is the commoner tag (8 REITs / 383 facts
against 3 / 92).

### 4.2 Sign convention — checked, and uniform

The expression *subtracts* the gains term, so a tag with an inverted sign would push FFO the wrong
way. Share of negative values per tag, across all REIT facts:

```
GainLossOnSaleOfPropertiesNetOfApplicableIncomeTaxes      0.5%
GainLossOnDispositionOfRealEstateDiscontinuedOperations   2.5%
GainsLossesOnSalesOfInvestmentRealEstate    (existing)    5.0%
GainLossOnSaleOfTimberProperty                            5.3%
GainLossOnSaleOfPropertiesBeforeApplicableIncomeTaxes     5.5%
GainLossOnDispositionOfProperty                           7.7%
GainLossOnSaleOfProperty                                  7.7%
GainLossOnSaleOfProperties                  (existing)    7.9%
GainLossOnSaleOfPropertyPlantEquipment                   11.0%
GainsLossesOnSalesOfOtherRealEstate                      21.4%
```

Every tag is **gain-positive, loss-negative**, matching the two existing ones (5.0% and 7.9%
negative). No tag needed a sign flip; the higher negative share on the two smallest tags is a
small-sample effect (14 and 3 negative facts).

### 4.3 Two candidates rejected — and they were the largest

`GainLossOnDispositionOfAssets` and `GainLossOnDispositionOfAssets1` would have contributed
**+145 TTM values of the +350 a permissive list produces — more than every accepted tag combined.**
They are rejected because they measure something else.

The test: where a filer reports both an "Assets" tag and a property-scoped tag **for the same
period**, do the values agree?

```
GainLossOnDispositionOfAssets      agree 11, disagree 35
   AVB 2011-12-31   property 294,806,000   assets  13,716,000
   AVB 2012-12-31   property 146,591,000   assets     280,000
   AVB 2013-12-31   property 278,471,000   assets     240,000

GainLossOnDispositionOfAssets1     agree 12, disagree 20
   PLD 2018-03-31   property 656,900,000   assets 195,111,000
   CPT 2014-12-31   property 155,700,000   assets 159,289,000     <- near-synonym, for this filer
   KIM 2015-06-30   property  58,731,000   assets  58,600,000     <- near-synonym, for this filer
```

AVB's 2011 property gain is **21× the "assets" figure**; PLD's is 3.4×. These are gains on disposing
non-real-estate assets, which is exactly what NAREIT FFO does **not** adjust for. That some filers
(CPT, KIM) use `...Assets1` as a near-synonym makes it worse, not better: a tag that means the
property gain for one filer and something else for another cannot be added globally, and adding it
per-filer would be picking the tickers where the number looks convenient.

**Saying no here costs 145 of 350 recoverable values.** That is the point of the check.

Also rejected, without needing the numeric test:

| tag | why |
|---|---|
| `DiscontinuedOperationGainLossOnDisposalOfDiscontinuedOperationNetOfTax` (23 REITs, 998 facts) | the largest unqueried tag in the survey, and it measures the disposal of a **business**, not of property — CCI's 77 facts are its fiber-segment sale |
| `DiscontinuedOperationGainLossFromDisposalOfDiscontinuedOperationBeforeIncomeTax` | same quantity, pre-tax |
| `EquityMethodInvestmentRealizedGainLossOnDisposal` (11 REITs) | disposal of an equity-method **investment**, not of property |
| `DisposalGroupNotDiscontinuedOperationGainLossOnDisposal` | a disposal group, which may be any asset class |
| `GainLossOnSaleOfPropertiesApplicableIncomeTaxes` | the **tax** on the gain, not the gain |
| `GainLossOnDispositionOfOtherAssets` (AMT only, 3 facts) | "other assets", named as not-property |
| the per-share and FX variants | different units and quantities |

### 4.4 What the accepted list recovers

Simulated on the cached facts before applying anything — `GainLossOnSaleOfProperties_TTM` values per
REIT, current tags against the accepted list:

```
REIT   now -> after      REIT   now -> after      REIT   now -> after
ARE     23 ->  41        EQIX     0 ->   5        PSA     29 ->  29
AVB     52 ->  52        EQR     47 ->  47        REG     30 ->  46
AMT      0 ->   0  (B)   ESS     28 ->  28        SBAC     0 ->   0  (B)
BXP      9 ->  29        EXR      1 ->   1        SPG      0 ->   0  (B)
CCI      0 ->   0  (B)   FRT      0 ->   9        UDR     27 ->  43
CPT      0 ->  10        HST      0 ->   1        VICI     0 ->   0  (C)
DLR      1 ->  39        INVH    39 ->  39        VTR      0 ->  11
DOC     36 ->  36        IRM      0 ->   5        WELL    39 ->  39
                         KIM      5 ->  13        WY       0 ->  21
                         MAA      0 ->  26
                         O       35 ->  35
                         PLD     11 ->  12

TOTAL  quarterly values 571 -> 847      TTM values 412 -> 617   (+205, +50%)
```

The permissive list including the two rejected tags would have given 762 (+350). **The difference,
145 values, is the price of the scope check** — and on AVB's evidence those 145 would have been
wrong numbers rather than missing ones.

---

## 5. Part C — the `ffo_gains_source` labels

### The decision: two labels, unchanged

`ffo_gains_source ∈ {reported, imputed_zero}` stays as it is. A third label for a *confirmed* genuine
absence was considered and rejected, for a reason specific to what the label is:

**The label is computed per row at runtime; class B/C is a per-ticker judgement made by reading raw
facts.** The pipeline cannot re-derive "CCI genuinely reports no property-disposal gain" — that came
from a person opening CCI's CompanyFacts and recognising that 77 discontinued-operation entries are
a fiber-segment sale. Encoding it as a data label would freeze a hand-made finding into the frame
with no mechanism to keep it true: the day CCI tags a property gain, the row would still say
"confirmed absent" and the pipeline would have no way to notice.

The honest place for an evidenced, dated, attributable finding is the history, which is where the
brief also asks for it. So:

- **`reported` / `imputed_zero`** keep their exact current meanings — did a fact exist for this
  period, or was zero assumed.
- **The class B/C list goes into `bugfixed_update_history.md`** as a permanent record, with the
  evidence for each of the five.

This also keeps the label parallel to `ttm_source`, which likewise records only what the pipeline
did, never why.

### The re-measured distribution

```
                before   after
  reported         427     597    +170   (23.3% -> 32.5% of REIT FFO periods)
  imputed_zero   1,409   1,239    -170   (76.7% -> 67.5%)
```

**170 periods move from assumed to filed.** The remaining 1,239 are the class B/C REITs and the
periods where no filer tagged a property gain under any name — for those the label is now a
statement backed by a survey rather than an untested default.

---

## 6. The diff, all 501 tickers

Before and after computed from the same price capture; base facts re-derived from the same cache.

| frame | rows | appeared | changed | disappeared |
|---|---:|---:|---:|---:|
| base facts | 512,078 → 512,316 | 238 | 6 | 0 |
| facts (incl. `_TTM`) | 978,477 → 978,897 | 420 | 348 | 0 |
| metrics_long | 463,396 | 0 | 292 | 0 |
| valuation_history | 210,153 | 0 | **161** | 0 |
| snapshot | 21,167 | 0 | 6 | 0 |
| rolling `avg_*_5y` | 487,574 | 0 | 725 | 0 |

**Every changed value is inside the FFO set, and nothing else moved** — the brief's hard requirement:

```
base facts        GainLossOnSaleOfProperties        +238 appeared, 6 changed
facts             GainLossOnSaleOfProperties_TTM    +182 appeared, 9 changed
                  FFO_TTM                            165 changed
                  FFO_QUARTERLY                      168 changed
metrics_long      ffo_margin                         140 changed
                  ffo_margin_quarterly               152 changed
valuation_history p_ffo                              161 changed      <- and no other concept
snapshot          p_ffo 2, avg_p_ffo_5y 2, avg_p_ffo_5y_median 2
rolling           avg_p_ffo_5y 413, avg_p_ffo_5y_median 312          <- every other line 0.00%
```

**Non-REITs are untouched.** The change lives in `PROFILE_CONCEPT_OVERRIDES["reit"]`, and the two
ticker overrides folded in (FRT, ARE) are both REITs.

### The `p_ffo` movement

| line | points | changed | share |
|---|---:|---:|---:|
| `p_ffo` (valuation history) | 26,064 | 161 | **0.62%** |
| `avg_p_ffo_5y` | 27,707 | 413 | **1.49%** |
| `avg_p_ffo_5y_median` | 27,707 | 312 | 1.13% |
| every other `avg_*_5y` line | — | 0 | 0.00% |

Against the running series — TTM ~25%, rolling-window 11–15%, duplicate-ends 2–5%, alignment 0–3.7% —
this lands at **0.6–1.5%, and only on the REIT lines.** The brief expected more, and the reason it is
less is worth stating: the gains term is a median 13.5% of FFO **in the periods where it exists**, and
the tag work recovered 205 of the ~1,409 zero-filled periods (15%). The other 85% are still
zero-filled — the class B/C REITs, and the periods where no filer tagged anything under any name.
**The zero-fill was costing less than the headline 77% suggested, because the recoverable part of it
is one seventh of the total.**

Where it does bite it bites hard. DLR's newest `FFO_TTM` falls **3,333.6m → 2,338.3m, −29.9%**, MAA's
1,022.1m → 1,001.8m, WY's newest `FFO_QUARTERLY` 289.0m → 218.0m.

### Anchor invariant — the exceptions, named

```
newest date moved            : 10   all forward, all on the recovered concept
newest value moved (same date):  5
series appeared              : 12   series disappeared: 0
```

This is the first task in nine to move the anchor, and it is the intended effect rather than an
exception to explain away: **a series that had no recent values now has them.**

```
FWD  BXP  GainLossOnSaleOfProperties      2018-09-30 -> 2020-09-30
FWD  BXP  GainLossOnSaleOfProperties_TTM  2015-09-30 -> 2020-09-30
FWD  DLR  GainLossOnSaleOfProperties      2018-12-31 -> 2026-03-31
FWD  DLR  GainLossOnSaleOfProperties_TTM  2018-12-31 -> 2026-03-31
FWD  IRM  GainLossOnSaleOfProperties      2018-12-31 -> 2020-09-30
FWD  KIM  GainLossOnSaleOfProperties      2016-03-31 -> 2016-12-31
FWD  KIM  GainLossOnSaleOfProperties_TTM  2010-12-31 -> 2016-12-31
FWD  MAA  GainLossOnSaleOfProperties      2014-03-31 -> 2026-03-31
FWD  PLD  GainLossOnSaleOfProperties      2019-06-30 -> 2019-09-30
FWD  PLD  GainLossOnSaleOfProperties_TTM  2019-06-30 -> 2019-09-30
```

DLR and MAA gain seven and twelve years of reach. **No date moved backwards and no series
disappeared.** The five value moves are the four-quarter sums now carrying a gains term they were
missing: DLR and MAA `FFO_TTM`/`FFO_QUARTERLY`, WY `FFO_QUARTERLY`.

### Quality flags

| flag | before | after |
|---|---:|---:|
| coverage flags | 737 | **734** |
| `share_count_jump_flag` = 1 | 718 | 718 |
| `buyback_distortion_flag` = 1 | 635 | 635 |
| `fcf_exceeds_ebitda` = 1 | 1,835 | 1,835 |
| `inorganic_contaminated` = 1 | 1,017 | 1,017 |

Three coverage flags cleared, all of them the concept this task is about: **BXP, DLR and MAA
`GainLossOnSaleOfProperties`.** No flag was raised.

---

## 7. Independent plausibility check

`alignment_and_defaults_report.md` §C.5 established the obvious check is unavailable — no REIT
publishes an FFO tag in a namespace the SEC API returns. The substitute uses the filer's own
arithmetic instead of the pipeline's: **four recovered quarters must sum to the 12-month fact the
filer separately tagged for the same fiscal year.** The annual fact plays no part in producing the
quarterly values, so agreement is not circular.

```
fiscal years where four recovered quarters tile a filer's own annual fact:  69
  exact (<= 0.1%)  58        within 5%   4        differs   7
```

**58 of 69 reconcile to the dollar**, across ARE, AVB, BXP, CPT, DLR, DOC, EQIX, EQR, ESS, FRT and
others:

```
EQR  2016-12-31   4,044,055,000  vs  4,044,055,000     exact
AVB  2024-12-31     364,159,000  vs    364,159,000     exact
DLR  2024-12-31     595,825,000  vs    595,825,000     exact
ARE  2020-12-31     154,089,000  vs    154,089,000     exact
```

Two of the seven disagreements are worth naming rather than burying:

- **AVB 2010: +74,074,000 against −74,074,000** — the same magnitude with the opposite sign. A
  sign-convention inconsistency *within one filer's own tagging*, not something the tag list
  introduces; §4.2 measured the population-level convention as uniform, and this is the exception.
- **DOC 2017: 85.2m against 356.6m** — the quarters recovered cover part of the year only; the annual
  fact includes disposals the quarterly tags never carried.

---

## 8. Deliberately not fixed

**The `annual_ttm_values` gate** (§1.3–1.4). The general defect this task uncovered: a concept
reported on occurrence rather than every period gets too few quarterly values to form a TTM window,
and the annual fallback is disabled by the mere existence of those values. CPT has 13 FY facts it
cannot use. Fixing it means changing behaviour all 25 `TTM_CONCEPTS` share — it would move every thin
concept in the frame at once and needs its own diff. **This is the largest thing found here and it is
left standing deliberately.**

**The four class-B REITs and one class-C** (AMT, CCI, SBAC, SPG, VICI). No tag exists to add. Their
FFO stays zero-filled, now with the evidence recorded in the history rather than unexamined.

**`GainLossOnDispositionOfAssets` / `...Assets1`** (§4.3) — rejected on evidence, not deferred. Adding
them per-filer where they happen to agree would be selecting the tickers where the number looks right.

**The other 85% of zero-filled periods.** The tag work reaches the periods where a filer tagged a
property gain under *some* name. Where nothing was tagged, nothing can be recovered, and the
`imputed_zero` label is the honest record of that.

**AVB's internal sign inconsistency** (§7) — one filer, one fiscal year, found by the check. Not a
pipeline defect and not worth a per-filer override.

---

## Files changed

| file | change |
|---|---|
| `config.py` | eight tags added to the `reit` profile's `GainLossOnSaleOfProperties`, ordered by scope, with the rejection evidence in comments; FRT and ARE ticker overrides folded in |
| `MDs/bugfixes_opdate_history.md` | entry per convention, including the permanent class B/C record |
| `ffo_gains_report.md` | this file |

No code changed outside `config.py`. `data/` and `figures/` untouched; no refresh was run; no scratch
scripts left behind.

### Verification performed

- All 29 REITs' cached CompanyFacts read directly for the tag survey; 19 disposal-gain tags enumerated
  with counts, units and queried status.
- CPT, IRM and MAA traced fact-by-fact through `extract_period_values` → `decumulate_period_values` →
  `extract_with_mode` → `calculate_ttm`.
- Every candidate tag tested for scope against a property-scoped tag in the same period, and for sign
  convention across all REIT facts.
- The accepted list simulated on the cache before any config change, per REIT.
- One before/after diff over all 501 tickers from one price capture, every appeared/changed/
  disappeared value accounted for.
- 69 fiscal years reconciled against the filers' own annual facts.
