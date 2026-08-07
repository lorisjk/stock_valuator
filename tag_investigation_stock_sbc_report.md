# Tag Investigation — `StockIssued`, `StockRepurchased`, `ShareBasedCompensation`

Input: the 2026-08-07 full refresh (`full_refresh_report.md`), 501 tickers, **1,000 data
quality flags**, of which **574 across 427 distinct tickers** come from these three concepts.

Every flagged (ticker, concept) pair was investigated individually against that ticker's
cached CompanyFacts. No sampling, no extrapolation.

The whole investigation was reproduced from the local cache with no network access. As a
control, the pipeline's own `build_dataframe` + `check_data_quality` over all 501 cached
tickers reproduces the refresh report's flags **exactly** — 1,000 flags, every
(ticker, concept, count, denominator, MISSING/thin) tuple identical. Everything below rests
on that reproduction.

---

## 1. The class A/B/C breakdown

| concept | **A** tag gap | **B** genuine absence | **C** structurally unavailable | total | actionable |
|---|---:|---:|---:|---:|---:|
| `StockIssued` | **302** | 55 | 10 | 367 | 82% |
| `ShareBasedCompensation` | **26** | 47 | 8 | 81 | 32% |
| `StockRepurchased` | **0** | 111 | 15 | 126 | **0%** |
| **total** | **328** | **213** | **33** | **574** | **57%** |

B splits further, by measured disclosure cadence rather than by assertion — a pair is
*annual-only* when the concept's tag family yields an annual value in ≥80% of the fiscal
years the ticker has any data for, while quarterly coverage stays under the 50% threshold:

| concept | B — annual-only disclosure | B — episodic / no activity |
|---|---:|---:|
| `StockIssued` | 2 | 53 |
| `ShareBasedCompensation` | 25 | 22 |
| `StockRepurchased` | 4 | 107 |

**246 of the 574 flags (43%) are not actionable by any tag change.** That number is the
main output of this task. `StockRepurchased` is the extreme case: not one of its 126 flags
is a tag gap.

### How each class was decided

For every flagged pair, the *accepted tag family* (section 2) was extracted from the ticker's
own CompanyFacts using the pipeline's own extractor, at both quarterly and annual granularity:

- **A** — a family tag the pipeline does not query yields quarterly values at end-dates the
  current series lacks.
- **B** — the family exists for this filer but yields nothing new. Either the item is
  disclosed annually only, or the missing quarters carry no fact at all.
- **C** — no accepted-family tag exists in the filer's CompanyFacts.

**"thin" is genuinely thin, not lost in extraction.** Across all 126 `StockRepurchased`
flagged tickers, the number of raw facts with a quarterly (80–100 day) duration never exceeds
the number of quarters the extractor produced — **0 tickers, 0 ends lost**. The extractor
produces *more* quarters than there are quarterly-duration facts, because `decumulate_period_values`
derives them from year-to-date points. Coverage is limited by what filers tag, not by the parser.

### Class B ticker lists

**`StockRepurchased` — annual-only (4):** AMZN, MCHP, NOW, VTRS

**`StockRepurchased` — episodic (107):** AEE, AES, AJG, ALB, AMD, APD, ARE, ARES, ATO, AVB,
AWK, AXON, BA, BG, BLK, BSX, BX, CASY, CIEN, CME, COHR, COIN, CPT, CRM, CRWD, CSGP, D, DHR,
DUK, DXCM, ED, EIX, EQIX, EQR, EQT, ERIE, ETR, EVRG, EXC, EXE, EXR, FANG, FCX, FE, FTV, GE,
GEHC, HOOD, HST, HWM, IBKR, IFF, INCY, INVH, IRM, KHC, KIM, LITE, LYV, MAA, MLM, MPWR, MTB,
NCLH, NEE, NEM, NUE, O, OKE, PCG, PEG, PGR, PKG, PLD, PODD, PPL, PSA, Q, RDDT, REG, REGN, ROP,
SATS, SCHW, SMCI, SO, SOFI, SOLV, SPG, STLD, TAP, TDG, TECH, TKO, TRGP, TTD, TTWO, UDR, VEEV,
VLTO, VRT, VZ, WDAY, WELL, WMB, XEL, XYZ

**`ShareBasedCompensation` — annual-only (25):** AIG, ALL, ATO, AWK, BALL, CI, COP, DAL, DOW,
EMR, ES, F, HIG, MET, NEE, NI, NWS, NWSA, OXY, PCG, PEG, PRU, PSX, WEC, WMT

**`ShareBasedCompensation` — episodic (22):** AEP, AES, C, CB, CEG, D, DTE, ETN, ETR, EXC, FE,
GE, HAL, PGR, PM, PNC, RF, STT, T, TSN, TXT, VZ

**`StockIssued` — annual-only (2):** OTIS, UAL

**`StockIssued` — episodic (53):** ACGL, ADM, AES, AIG, AIZ, AMZN, APTV, BAC, BDX, BG, C, DG,
EVRG, EXE, F, FE, FOX, FOXA, FTV, GE, GEV, GM, GOOG, GOOGL, GS, HCA, HST, IP, JPM, KHC, KKR,
KMI, KVUE, L, LLY, LYB, MGM, MU, ODFL, PEG, PM, PNC, Q, SNDK, SOLV, SPG, STLD, SYF, TFC, TPL,
VST, WMT, ZTS

### Class C ticker lists

Class C means *no tag carrying the concept's own quantity exists* — not "no tag mentioning the
topic". CVX and XOM, for instance, carry 42 and 22 share-based-compensation-family tags each,
but every one of them is ancillary (tax benefit realised, unrecognised cost remaining, cash
received on exercise, withholding paid). **The recognised expense itself is never tagged.**

| concept | nothing at all | only a deliberately-rejected tag |
|---|---|---|
| `ShareBasedCompensation` | CMS, CNP, CVX, ERIE, MO, XOM | DLR, SPG *(shares-issued value only)* |
| `StockIssued` | BKR, BX, EMR, ERIE, NWS, NWSA, PSKY, TKO | CEG, PAYX *(acquisition stock only)* |
| `StockRepurchased` | AEP, BXP, CMS, ES, LNT, TSLA | CNP, DDOG, DLR, FRT, FSLR, PSKY, SNDK, VICI, VTR |

The class-C `StockIssued` tickers have `ProceedsFromIssuanceOfLongTermDebt` and nothing
equity-side; the class-C `StockRepurchased` names are TSLA, DDOG, FSLR, VICI, FRT, LNT — the
list you would predict from knowing the companies. ERIE has no tag from any of the three
families, in any form.

---

## 2. The survey, aggregated by candidate tag

Tag names were taken from the tickers' actual CompanyFacts (8,477 distinct us-gaap tags across
the 501-ticker universe), never guessed. Each candidate's economic content was then read from
**the element's own `description` field in the cached companyfacts JSON** — that documentation
ships with the data and needs no network call.

Counts below are over flagged tickers only. "new quarterly ends" is the number of end-dates the
tag would add on top of the current series.

### `StockIssued` (367 flagged tickers)

| status | tag | flagged tickers with it | new quarterly ends |
|---|---|---:|---:|
| accepted | `ProceedsFromStockOptionsExercised` | 264 | **7,741** |
| accepted | `ProceedsFromIssuanceOfSharesUnderIncentiveAndShareBasedCompensationPlansIncludingStockOptions` | 94 | 3,155 |
| accepted | `StockIssuedDuringPeriodValueStockOptionsExercised` | 147 | 2,746 |
| accepted | `ProceedsFromStockPlans` | 44 | 1,503 |
| accepted | `StockIssuedDuringPeriodValueEmployeeStockPurchasePlan` | 87 | 1,123 |
| accepted | `ProceedsFromSaleOfTreasuryStock` | 26 | 614 |
| accepted | `ProceedsFromIssuanceOfSharesUnderIncentiveAndShareBasedCompensationPlans` | 35 | 494 |
| accepted *(existing)* | `ProceedsFromIssuanceOfCommonStock` | 152 | 0 |
| accepted *(existing)* | `StockIssuedDuringPeriodValueNewIssues` | 174 | 0 |
| accepted *(existing)* | `ProceedsFromIssuanceOrSaleOfEquity` | 35 | 0 |
| rejected | `StockIssuedDuringPeriodValueShareBasedCompensation` | 206 | 4,908 |
| rejected | `StockIssuedDuringPeriodValueTreasuryStockReissued` | 59 | 805 |
| rejected | `StockIssued1` | 64 | 413 |
| rejected | `ProceedsFromIssuanceOfPreferredStockAndPreferenceStock` | 43 | 387 |
| rejected | `StockIssuedDuringPeriodValueAcquisitions` | 157 | 315 |
| rejected | `StockIssuedDuringPeriodValueEmployeeBenefitPlan` | 26 | 276 |
| rejected | `ProceedsAndExcessTaxBenefitFromSharebasedCompensation` | 25 | 202 |
| rejected | `ProceedsFromIssuanceOfCommonLimitedPartnersUnits` | 6 | 23 |
| rejected | `StockIssued` | 18 | 18 |

### `ShareBasedCompensation` (81 flagged tickers)

| status | tag | flagged tickers with it | new quarterly ends |
|---|---|---:|---:|
| accepted | `AdjustmentsToAdditionalPaidInCapitalSharebasedCompensationRequisiteServicePeriodRecognitionValue` | 30 | **660** |
| accepted *(existing)* | `AllocatedShareBasedCompensationExpense` | 61 | 0 |
| accepted *(existing)* | `ShareBasedCompensation` | 29 | 0 |
| rejected | `StockIssuedDuringPeriodValueShareBasedCompensation` | 38 | 952 |
| rejected | `EmployeeBenefitsAndShareBasedCompensation` | 5 | 112 |
| rejected | `StockGrantedDuringPeriodValueSharebasedCompensation` | 6 | 79 |
| rejected | `EmployeeBenefitsAndShareBasedCompensationNoncash` | 2 | 44 |
| rejected | `AdjustmentsToAdditionalPaidInCapitalSharebasedCompensationAndExerciseOfStockOptions` | 1 | 42 |
| rejected | `ShareBasedCompensationArrangementByShareBasedPaymentAwardCompensationCost` | 12 | 4 |
| rejected | `AllocatedShareBasedCompensationExpenseNetOfTax` | 16 | 0 |

### `StockRepurchased` (126 flagged tickers)

| status | tag | flagged tickers with it | new quarterly ends |
|---|---|---:|---:|
| accepted *(all six existing)* | `PaymentsForRepurchaseOfCommonStock` (108), `StockRepurchasedDuringPeriodValue` (63), `TreasuryStockValueAcquiredCostMethod` (58), `StockRepurchasedAndRetiredDuringPeriodValue` (44), `PaymentsForRepurchaseOfEquity` (9), `PartnersCapitalAccountTreasuryUnitsPurchases` (1) | — | **0** |
| rejected | `PaymentsRelatedToTaxWithholdingForShareBasedCompensation` | 65 | 1,170 |
| rejected | `PaymentsForRepurchaseOfPreferredStockAndPreferenceStock` | 28 | 162 |
| rejected | `PaymentsForRepurchaseOfOtherEquity` | 9 | 41 |
| rejected | `TreasuryStockValueAcquiredParValueMethod` | 4 | 4 |
| rejected | `AcceleratedShareRepurchasesSettlementPaymentOrReceipt` | 5 | 0 |
| rejected | `TreasuryStockValue` | 58 | 0 |

**The existing six tags already extract everything there is.** 103 of the 126 flagged tickers
carry `PaymentsForRepurchaseOfCommonStock` and it contributes zero further quarters.

### Why each rejected tag was rejected

Every rejection is an element-definition argument, not a judgement call:

| tag | element description | why rejected |
|---|---|---|
| `PaymentsRelatedToTaxWithholdingForShareBasedCompensation` | "cash outflow to satisfy **grantee's tax withholding obligation**" | A payment to a tax authority, not a reacquisition of stock. See section 3. |
| `StockIssuedDuringPeriodValueShareBasedCompensation` | "Value, **after forfeiture**, of shares issued under share-based payment arrangement" | Shares issued, not cost recognised. Where co-reported with `ShareBasedCompensation` (5,832 quarters, 190 tickers) it is within 1% in only **10.9%**; the ratio runs from **−0.099** at the 10th percentile to 2.2 at the 90th. A different quantity that sometimes has the opposite sign. |
| `StockIssued1` / `StockIssued` | "fair value of stock issued in **noncash** financing activities" | Non-cash; and the unsuffixed one is **deprecated 2011-01-31**. |
| `StockIssuedDuringPeriodValueAcquisitions` | "Value of stock issued pursuant to **acquisitions**" | Non-cash M&A consideration. 157 flagged tickers carry it and it yields only 315 new ends. |
| `ProceedsFromIssuanceOfPreferredStockAndPreferenceStock`, `PaymentsForRepurchaseOfPreferredStockAndPreferenceStock` | preferred / preference stock | Different security from the common shares the concept tracks. |
| `EmployeeBenefitsAndShareBasedCompensation` | "expense for employee benefit **and** equity-based compensation" | A combined line — pension plus SBC. 24.7% within 1% of `ShareBasedCompensation`, 10th percentile ratio 0.0. |
| `AllocatedShareBasedCompensationExpenseNetOfTax` | net of tax | Not the gross expense the concept means. |
| `ShareBasedCompensationArrangementByShareBasedPaymentAwardCompensationCost` | per-award-type footnote | A subset of the total, per plan. |
| `TreasuryStockValue` | balance | A point-in-time balance, not a period flow. Present for 58 flagged tickers and structurally unusable. |
| `PaymentsForRepurchaseOfOtherEquity` | "reacquire equity classified as **other**" | Not common stock. |
| `TreasuryStockValueAcquiredParValueMethod` | "cost of common **and preferred** stock repurchased" | Mixes preferred; 4 flagged tickers, 4 ends. |
| `AcceleratedShareRepurchasesSettlementPaymentOrReceipt` | "cash **receipt from (payment to)** bank" | Sign is ambiguous by construction, and **0** flagged tickers have it. |
| `ProceedsAndExcessTaxBenefitFromSharebasedCompensation` | proceeds **and** tax benefit | Two quantities in one line. |
| `ProceedsFromIssuanceOfCommonLimitedPartnersUnits` | LP units | 6 tickers, 23 ends, clears nothing. |

---

## 3. The three concentration hypotheses

### H1 — `ShareBasedCompensation` in `utilities` (21 of 81): **rejected as stated; the real cause is different and more useful**

The hypothesis was "the industry uses a different tag". It does not. Of the 21 flagged utilities:

| verdict | count | tickers |
|---|---:|---|
| A — tag gap | 3 | ED, EIX, SO |
| B — annual-only disclosure | 8 | ATO, AWK, ES, NEE, NI, PCG, PEG, WEC |
| B — episodic | 8 | AEP, AES, CEG, D, DTE, ETR, EXC, FE |
| C — structurally unavailable | 2 | CMS, CNP |

**18 of 21 cannot be fixed by any tag.** The dominant pattern is that utilities disclose
share-based compensation **once a year, in the 10-K footnote**. AEP, NEE, PEG and ES all carry
`AllocatedShareBasedCompensationExpense` — and every single fact under it has a 12-month
duration:

```
NEE  AllocatedShareBasedCompensationExpense: 48 facts, durations {12 months: 48}
     annual values = 21, quarterly values = 0
     2022-12-31  142,000,000     2024-12-31  138,000,000
     2023-12-31  139,000,000     2025-12-31  185,000,000
```

`decumulate_period_values` needs sub-annual year-to-date points to derive a quarter. With only
12-month facts there is nothing to decumulate, so a pipeline running at `PERIOD = "quarterly"`
gets zero — and 21 annual values against a 74-quarter denominator is 28%, permanently under the
50% threshold. **This is class B by the task's own definition, and no tag closes it.**

The 3 class-A cases are real and were fixed: ED, EIX and SO tag the amount in the equity
statement instead (section 4, group 2). SO goes 0 → 45 quarters, EIX 19 → 70.

### H2 — `StockIssued` in `standard` + `industrials` (137 of 367): **confirmed as a tag gap; the alternative premise is false**

| verdict | count |
|---|---:|
| A — tag gap | **122** |
| B | 12 |
| C | 3 |

The suggested alternative — "these filers report issuance only as a net financing figure that
cannot be decomposed" — is **not what the data shows**. They report it perfectly well, on a line
the candidate list did not know about:

| tag that closes the gap | tickers (standard + industrials) |
|---|---:|
| `ProceedsFromStockOptionsExercised` | 56 |
| `ProceedsFromIssuanceOfSharesUnderIncentiveAndShareBasedCompensationPlansIncludingStockOptions` | 27 |
| `StockIssuedDuringPeriodValueStockOptionsExercised` | 14 |
| `ProceedsFromStockPlans` | 14 |
| others | 11 |

**The candidate list only knew about capital-raising issuance.** All three existing tags —
`ProceedsFromIssuanceOfCommonStock`, `StockIssuedDuringPeriodValueNewIssues`,
`ProceedsFromIssuanceOrSaleOfEquity` — describe a company *selling shares to raise money*, which
a mature S&P 500 industrial does roughly never. What such a company does every single quarter is
issue shares through employee option exercises and ESPP purchases, and that has its own
cash-flow line. 192 of the 367 `StockIssued` flags were `MISSING` — 0 of ~75 quarters — which
read like "this company has never issued stock" and actually meant "this company has never done
a secondary offering".

### H3 — `StockRepurchased` in `reit` + `utilities` (46 of 126): **confirmed class B, not a tag gap**

| verdict | count | |
|---|---:|---|
| A | **0** | |
| B — episodic | 32 | |
| B — annual-only | 4 | |
| C | 10 | incl. VICI, FRT (reit); AEP, CMS, CNP, ES, LNT (utilities) |

And the finding generalises past the two named profiles: **the whole concept is 0/126 class A.**
Supporting measurements:

- Across the 126 flagged tickers, the median number of quarters with a repurchase value is
  **29.6%** of the quarters that have an `OperatingCashFlow` value. Companies report the line in
  roughly 3 quarters out of 10 — because in the other 7 they did not repurchase anything, and
  XBRL does not tag a line that is not presented.
- 16 flagged tickers have **zero** repurchase quarters against ≥20 quarters of operating cash
  flow. They are the class-C list: TSLA, DDOG, FSLR, VICI, FRT, LNT, CMS, CNP, AEP, BXP, ES, …
- AEP, BXP and DLR carry only `PaymentsForRepurchaseOfPreferredStockAndPreferenceStock` — they
  redeem preferred, they do not buy back common.

**The fix and the non-fix look identical from the flag count, which is exactly why this was worth
measuring rather than assuming.** A tag added here would have produced a plausible wrong number
in place of an honest gap.

---

## 4. Changes proposed, applied, and their mode decisions

Two change groups. Both use `mode: "fallback"` and both **append only** — no existing tag's
position changed. That matters structurally: `extract_merged_values` iterates the tag list in
order and skips any end-date already merged, so a tag appended to a `fallback` list can only add
values at dates that had none. It can never override or remove one. Section 5 confirms this
empirically across all 501 tickers rather than resting on the argument.

### Group 1 — `StockIssued`: seven tags appended

```python
"tags": [
    "ProceedsFromIssuanceOfCommonStock",                       # existing
    "StockIssuedDuringPeriodValueNewIssues",                   # existing
    "ProceedsFromIssuanceOrSaleOfEquity",                      # existing
    "ProceedsFromIssuanceOfSharesUnderIncentiveAndShareBasedCompensationPlansIncludingStockOptions",
    "ProceedsFromStockPlans",
    "ProceedsFromStockOptionsExercised",
    "ProceedsFromIssuanceOfSharesUnderIncentiveAndShareBasedCompensationPlans",
    "ProceedsFromSaleOfTreasuryStock",
    "StockIssuedDuringPeriodValueStockOptionsExercised",
    "StockIssuedDuringPeriodValueEmployeeStockPurchasePlan",
],
"mode": "fallback",
```

**Mechanism: global candidate-list addition.** The gap is not idiosyncratic — 302 tickers across
17 profiles report employee-plan issuance this way. A `TICKER_CONCEPT_OVERRIDES` entry per ticker
would be 302 entries encoding one fact. `_KNOWN_BAD_FACTS` is for single-value corrections and
does not apply.

**Order: aggregate before component**, following the `LongTermDebt` precedent. The element
descriptions establish the hierarchy exactly:

- `…IncludingStockOptions` — "cash inflow from issuance of shares under share-based payment
  arrangement. **Includes** … option exercised" → the whole plan inflow.
- `ProceedsFromStockOptionsExercised` — "cash inflow from **exercise of option**" → part of it.
- `…Plans` (no suffix) — "**Excludes** option exercised" → the other part.

**`sum` vs `fallback`: `fallback`, and the evidence is unambiguous.**

Filers double-tag the same cash-flow line. Where both the aggregate `…IncludingStockOptions` tag
and the component `ProceedsFromStockOptionsExercised` appear in the same quarter — 145 quarters
across 32 tickers — **60 of them carry an identical value** and the median ratio is exactly
1.000:

```
ABNB 2023-09-30   Including…Options = 14,000,000   OptionsExercised = 14,000,000
ABNB 2024-03-31                       46,000,000                      46,000,000
ALL  2012-03-31                       15,000,000                      15,000,000
ANET 2017-03-31                       19,481,000                      19,481,000
```

`sum` would report exactly twice the true figure in every one of those quarters — a plausible
wrong number, not an error. The same trap sits between `…Plans` (excluding options) and
`…IncludingStockOptions`: 14 of the 34 tickers carrying the Excluding tag also carry the
Including tag, and 10 of their 27 co-reported quarters are identical.

**The trade-off this accepts, stated plainly:** where a filer reports genuinely separate,
non-overlapping lines — say `ProceedsFromIssuanceOfCommonStock` = 500 for a secondary offering
*and* `ProceedsFromStockOptionsExercised` = 40 for employee exercises — `fallback` reports 500,
not 540. It **undercounts** rather than double-counting. Measured across the 717 quarters where
those two are co-reported, the options line is a median **8.1%** of the common-stock line, so the
undercount is small and bounded; only 13.9% of those quarters are identical double-tags. This is
the same trade the project made for `LongTermDebt` in July, for the same reason: an undercount
degrades gracefully, a double-count does not.

### Group 2 — `ShareBasedCompensation`: one tag appended

```python
"tags": [
    "ShareBasedCompensation",                                   # existing
    "AllocatedShareBasedCompensationExpense",                   # existing
    "AdjustmentsToAdditionalPaidInCapitalSharebasedCompensationRequisiteServicePeriodRecognitionValue",
],
"mode": "fallback",
```

**Mechanism: global candidate-list addition.** 57 tickers across 12 profiles.

The element is described as "amount of increase to additional paid-in capital for **recognition
of cost** for award under share-based payment arrangement" — the same cost, credited to equity
instead of added back on the cash-flow statement. The numbers agree: across **9,498 quarters and
270 tickers** where it is co-reported with `ShareBasedCompensation`, it is **within 1% in 65.4%**
of them and its interquartile ratio range is exactly [1.00, 1.00] (10th/90th percentiles 0.936 /
1.065, the residual being capitalised or non-employee portions). For comparison, the existing
second candidate `AllocatedShareBasedCompensationExpense` is within 1% in 79.1% — the same kind
of agreement.

**`sum` vs `fallback`: `fallback`.** This is the *same* cost recognised in a different statement,
not an additional cost. Summing it with `ShareBasedCompensation` would double the expense for the
270 tickers that report both — and `pfcf_ex_sbc` subtracts SBC from free cash flow, so a doubled
SBC directly halves or negates the owner-earnings figure.

### `StockRepurchased` — no change, deliberately

Zero of 126 flags are class A. Every candidate that would have moved the number was rejected on
its own element definition. The one that mattered is worth spelling out because it is the exact
scenario the brief anticipated:

**`PaymentsRelatedToTaxWithholdingForShareBasedCompensation` would have cleared 44 flags and
filled 71 of the 126 pairs. It was rejected.** Its description is "amount of cash outflow to
satisfy **grantee's tax withholding obligation** for award under share-based payment arrangement"
— cash paid to a tax authority when shares vest, not cash paid to reacquire stock. Under
`fallback` it would populate precisely those quarters in which the company ran **no buyback**,
labelling a tax payment as a repurchase. And the magnitudes make it useless even for the consumer
that would receive it: measured over 4,632 quarters where both are reported and the buyback is
positive, withholding is a **median 2.9%** of the repurchase, and under 10% of it in 67.3% of
quarters. `StockRepurchased`'s only consumer is `share_count_jump_flag`, which asks whether an
equity cash flow is large enough to explain a >15% share-count move; a number at 3% of buyback
scale will never corroborate anything.

So the fix would have removed 44 flags, changed no downstream answer, and made the series mean
two different things depending on the quarter. **Not fixing it is the successful outcome here.**

---

## 5. Before/after diff, all 501 tickers, per change group

Baseline and each post-change state were rebuilt from the same cached CompanyFacts with the
pipeline's own `build_dataframe`, over all 501 active tickers and **all** concepts — 496,691
starting rows. Each group was diffed before the next was applied.

### Group 1 — `StockIssued`

```
rows before=496,691  after=510,559  delta=+13,868
APPEARED     13,868   concepts=['StockIssued']
CHANGED           0   concepts=[]
DISAPPEARED       0   concepts=[]
```

13,868 values appeared across **338 tickers**. **Nothing changed and nothing disappeared** — the
append-only property of `fallback`, confirmed rather than assumed.

Of the 338 tickers that gained values, **302 were flagged and 36 were not**. Those 36 gained 369
values between them. They need no separate justification beyond `CHANGED = 0`: every one of the
369 landed on an end-date that previously held no value, so no ticker's existing series was
altered. They were simply sitting above the 50% threshold with gaps, and the gaps are now filled.

### Group 2 — `ShareBasedCompensation`

```
rows before=510,559  after=511,464  delta=+905
APPEARED        905   concepts=['ShareBasedCompensation']
CHANGED           0   concepts=[]
DISAPPEARED       0   concepts=[]
```

905 values across 57 tickers. Again zero changed, zero lost.

### Cumulative invariants (9/9 checks passed)

| check | result |
|---|---|
| `max_for_ticker` (the flag denominator) unchanged for every still-flagged ticker | ok — 370 compared |
| all concepts other than the two edited ones identical row-for-row | ok — 460,772 rows both sides |
| `StockIssued`: every pre-existing value survives unchanged | ok — 9,647 → 23,515 |
| `ShareBasedCompensation`: every pre-existing value survives unchanged | ok — 26,272 → 27,177 |
| no quarter became newly `share_count_jump_flag`-flagged | ok — 0 |
| `share_count_jump_flag` row set unchanged | ok |
| no `owner_fcf` value disappeared | ok — 0 |
| every ticker with a changed `owner_fcf` gained `ShareBasedCompensation` values | ok — 0 unexplained |
| every ticker with a new `owner_fcf` gained `ShareBasedCompensation` values | ok — 0 unexplained |

---

## 6. Downstream consumers

### `pfcf_ex_sbc` — via `owner_fcf = FCF_TTM − ShareBasedCompensation_TTM`

`pfcf_ex_sbc = market_cap / owner_fcf`, and market cap is untouched by a tag change, so diffing
`owner_fcf` is equivalent and needs no price fetch.

```
appeared = 651     changed = 68 (20 tickers)     disappeared = 0
```

**15 of the 20 tickers with a changed `owner_fcf` were never flagged** (AMCR, AMGN, BG, CBRE,
FCX, HBAN, HWM, JCI, LDOS, MOS, SNDK, SRE, TDY, TER, TMUS). The mechanism, and the justification:

`calculate_ttm` is `.rolling(window=4).sum()` **over the rows present in the series**, not over
calendar quarters. On a sparse concept it therefore sums the last four *available* values, which
may span several years. Filling a gap re-anchors that window at nearby dates, which is why adding
data changes existing TTM values rather than only adding new ones. Every change traces to a
ticker that gained `ShareBasedCompensation` quarters (asserted; 0 unexplained), and every change
moves toward a window that spans less time. Examples:

- **SRE** gained the 8 consecutive quarters 2016-03-31 … 2017-12-31, which had been an unbroken
  two-year hole between 2015-12-31 and 2018-03-31.
- **KR** gained its fiscal-year-end quarter in each of 8 years (2019-02-02 … 2026-01-31); it had
  been reporting SBC in Q2 and Q3 only.
- **TMUS** gained exactly one quarter, 2013-09-30 ($48m), and shows the largest relative move
  at 17.6%.

The largest relative change is TMUS at 17.6%; 15 of the 20 tickers move by under 4%.

**Carried forward, not fixed here:** the row-based TTM window is a real weakness for sparse
concepts — a `ShareBasedCompensation_TTM` built from four quarters spanning three years is
labelled "trailing twelve months" and is not. It affects any thin concept, is unrelated to tag
selection, and is out of this task's scope.

### `share_count_jump_flag` — via `StockIssued` / `StockRepurchased`

```
flagged quarters: 1,312 -> 1,308        quarters whose flag value moved: 4
all four moved 1 -> 0; none moved 0 -> 1
```

Four quarters, two events (the flag deliberately marks both quarters bracketing a transition):
INCY 2013-06-30/09-30 and URI 2011-03-31/06-30.

**Both are honest-to-report regressions, not improvements.** The arithmetic:

```
INCY 2013-09-30  shares 284,568,000 -> 155,067,000  (45.5%, delta 129,501,000)
  before: StockIssued=NaN                     -> flow_cash 0,  not corroborated -> FLAGGED
  after:  StockIssued=28,364,000              -> implied_flow_shares 152,767,198
          equity 28,791,000 / 155,067,000 shares = implied_price $0.1857
          152,767,198 >= 0.5 x 129,501,000 = 64,750,500  -> corroborated -> UNFLAGGED

URI 2011-06-30   shares 60,850,000 -> 74,052,000   (21.7%, delta 13,202,000)
  before: StockIssued=NaN, StockRepurchased=0 -> flow_cash 0,  not corroborated -> FLAGGED
  after:  StockIssued=26,000,000              -> implied_flow_shares 96,267,600
          equity -20,000,000 / 74,052,000 shares = implied_price $0.2701
          96,267,600 >= 0.5 x 13,202,000 = 6,601,000     -> corroborated -> UNFLAGGED
```

Both corroborations are spurious. `implied_price` is book value per share, and both companies had
near-zero or **negative** book equity in those quarters — $0.19 and $0.27 per share against real
market prices two orders of magnitude higher. Any equity cash flow at all "explains" an unlimited
number of shares at that price.

Worse, the flags they silenced were doing useful work. Both share-count "jumps" are artefacts of
`normalize_split_adjusted`, which invented split steps that never happened:

```
INCY SharesOutstanding      raw            normalized      factor
     2013-06-30      142,284,000       284,568,000          2.0
     2013-09-30      155,067,000       155,067,000          1.0     <- fabricated -45.5% step

URI  SharesOutstanding      raw            normalized      factor
     2012-06-30       83,231,000        83,231,000          1.0
     2012-09-30      105,273,000        52,636,500          0.5     <- fabricated -50% step
```

Incyte never split 2:1; the raw series runs smoothly 138m → 155m. United Rentals never split
1:2 — the +26.5% step at 2012-09-30 is the RSC Holdings acquisition, a real share issuance that
the normaliser read as a split and then divided out of every subsequent quarter.

**This does not justify reverting the tag change.** It is 4 quarters of 30,986 (0.013%) and 2
flag events of 1,312, the added data is independently correct, and the two defects it exposed are
pre-existing and live in `SharesOutstanding` normalisation and in the jump-flag corroboration
formula — neither in scope here. Both are recorded in section 8.

---

## 7. Re-measured flag counts

| concept | before | after group 1 | after group 2 | delta | `MISSING` before → after |
|---|---:|---:|---:|---:|---|
| `StockIssued` | 367 | 123 | 123 | **−244** | 192 → 27 |
| `ShareBasedCompensation` | 81 | 81 | 68 | **−13** | 46 → 35 |
| `StockRepurchased` | 126 | 126 | 126 | 0 | 18 → 18 |
| **all 24 profiles, all concepts** | **1,000** | 756 | **743** | **−257** | |

No concept outside these three changed its flag count — measured, not assumed.
Distinct tickers carrying at least one of the three flags: **427 → 241**.

The A/B/C classification predicted exactly which pairs would clear: **257 predicted, 257
measured, 0 mismatches in either direction** over all 574 pairs.

What remains flagged, by class:

| concept | A (improved, still under 50%) | B annual-only | B episodic | C | total |
|---|---:|---:|---:|---:|---:|
| `StockIssued` | 58 | 2 | 53 | 10 | 123 |
| `ShareBasedCompensation` | 13 | 25 | 22 | 8 | 68 |
| `StockRepurchased` | 0 | 4 | 107 | 15 | 126 |
| **total** | **71** | **31** | **182** | **33** | **317** |

**246 of the 317 remaining flags are permanent** — B and C, correctly reported gaps. The 71
class-A remainders gained values but stayed under the 50% threshold; they are genuine partial
improvements, not failures.

---

## 8. Deliberately not fixed

**`StockRepurchased`, all 126 flags.** Zero are tag gaps. Documented above; the tag that would
have cleared 44 of them is a tax payment, not a repurchase.

**The B-annual-only cases (31 pairs), including 8 of the 21 flagged utilities.** No tag can
produce a quarterly value from a disclosure that only ever exists at 12-month duration. Closing
these would need a different mechanism — allowing an annual value to satisfy a quarterly concept,
or exempting such (profile, concept) pairs from the coverage threshold. Both are architecture
decisions, not tag decisions.

**`normalize_split_adjusted` invents splits that did not happen.** Proven for two tickers:
INCY (everything before 2013-09-30 doubled) and URI (everything from 2012-09-30 halved, reading
the RSC Holdings share issuance as a 1:2 split). For scale, the normaliser rescales **8,908 of
32,061 `SharesOutstanding` rows (27.8%) across 338 of 498 tickers**; most of those factors (2, 3,
4, 10) are surely real splits and no claim is made that the rest are wrong — but two are
demonstrably wrong, and the mechanism has no corroborating source. Only history is affected: the
most recent value is the anchor and is never rescaled, so current snapshots are unaffected.

**`share_count_jump_flag`'s `implied_price` is book value per share.** For a company with
near-zero or negative equity this collapses to cents, and any equity cash flow then "corroborates"
an unlimited share-count move. Both flag flips in section 6 run through this. A price from
`price_history` — already loaded in the same run — would be the obvious substitute.

**`calculate_ttm` rolls over rows, not calendar quarters.** A `_TTM` value on a sparse concept can
span several years while being labelled trailing-twelve-months. Affects every thin concept, not
just these three.

**The undercount accepted by `fallback` on `StockIssued`.** Where a filer reports a secondary
offering and employee-plan proceeds as separate lines, only the first is taken. Median impact is
8.1% of the reported figure in the 717 quarters where both appear. Accepted knowingly, in
preference to `sum`'s 2× failure mode.

**Concepts outside the three named.** `DividendsPerShare`, `Goodwill`, `LongTermDebt`,
`OperatingIncomeLoss` and the rest remain untouched, per the task's scope.

---

## Files changed

| file | change |
|---|---|
| `config.py` | `CONCEPT_CANDIDATES["StockIssued"]["tags"]`: 3 → 10 tags (append only). `CONCEPT_CANDIDATES["ShareBasedCompensation"]["tags"]`: 2 → 3 (append only). Both keep `mode: "fallback"`, both carry the reasoning as comments. |

No other source file was touched. `METRICS` still holds 52 entries with no undocumented metric,
and the five derived structures still have their existing shapes (29 / 13 / 10 / 11 / 7).
