# Insurance (P&C) Tag Coverage Scan — CB, PGR, ALL, AIG, WRB, CINF, ACGL, HIG, L, EG

All 10 tickers were freshly fetched and cached (`cache/{TICKER}_company_info.json`), plus TRV
(already cached, used as the trusted reference throughout). All non-regression diffs cover
every cached ticker (122 `cache/*_company_info.json` files), not just the 11 `insurance_pc`
tickers. `config.py` was modified; every change below was verified against the full cached
universe before being kept.

## Step 1 — Coverage scan

`get_expected_concepts(ticker)` correctly resolves the `insurance_pc` overlay: all 16
concepts (10 base + `Goodwill` + `LongTermDebt` from the base config, plus the 7
`insurance_pc`-specific concepts) showed up as expected for every ticker, with `Capex`,
`CashAndEquivalents`, and `OperatingIncomeLoss` correctly excluded by
`PROFILE_EXCLUDED_CONCEPTS["insurance_pc"]`. TRV itself came back with **zero** flagged
concepts (aside from the expected non-payer noise), confirming it really is a clean reference.

Flagged concepts (excluding `DividendsPerShare`, per the pilot's non-payer rule):

| Ticker | Concept | Coverage |
|---|---|---|
| ACGL | NetInvestmentIncome | 0/69 (0%) |
| ACGL | RealizedInvestmentGains | 0/69 (0%) |
| ACGL | LongTermDebt | 0/69 (0%) |
| ACGL | Goodwill | 14/69 (20%) |
| AIG | Goodwill | 31/73 (42%) |
| AIG | RealizedInvestmentGains | 32/73 (44%) |
| AIG | LongTermDebt | 33/73 (45%) |
| ALL | EarnedPremiums | 0/73 (0%) |
| ALL | IncurredLosses | 0/73 (0%) |
| ALL | ClaimsReserve | 15/73 (21%) |
| CB | RealizedInvestmentGains | 28/71 (39%) |
| CINF | Goodwill | 0/70 (0%) |
| EG | DepreciationAndAmortization | 0/69 (0%) |
| EG | Investments | 0/69 (0%) |
| EG | LongTermDebt | 0/69 (0%) |
| EG | Goodwill | 0/69 (0%) |
| L | DepreciationAndAmortization | 0/73 (0%) |
| L | RealizedInvestmentGains | 0/73 (0%) |
| PGR | EarnedPremiums | 9/73 (12%) |
| PGR | IncurredLosses | 11/73 (15%) |
| PGR | Investments | 36/73 (49%) |
| WRB | BenefitsLossesAndExpenses | 0/67 (0%) |
| WRB | LongTermDebt | 0/67 (0%) |

## Step 2 — Investigation findings

Every raw candidate tag was pulled and its full quarterly/point-in-time timeline dumped
directly from cached JSON (not just counted) to distinguish four genuinely different root
causes hiding behind "low coverage":

1. **Predecessor/successor tag renames** — the company switched XBRL tag names mid-history
   and the config was only pointed at one of them.
2. **Coexisting, genuinely additive instruments** — two real, distinct debt/investment line
   items that both need including (a `sum`, not a `fallback`).
3. **Annual-only tagging** — the company only tags the concept in its 10-K, never in 10-Qs, so
   under `PERIOD="quarterly"` no amount of tag-searching can produce quarterly data. Verified by
   reading the raw `start`/`end`/`fp` fields directly: pure `fp: "FY"`, `start` always Jan 1, no
   quarterly companions.
4. **Genuine absence / no reliable candidate** — the company doesn't tag the concept at all, or
   every candidate found is a subset/component whose magnitude doesn't reconcile with the
   existing total at any verifiable overlap point.

### Confirmed predecessor/successor pairs (exact or near-exact overlap verified)

- **ALL**: `PremiumsEarnedNet` (2011+, annual-only, 0 quarterly values) has no quarterly data,
  but `PremiumsEarnedNetPropertyAndCasualty` gives clean quarterly coverage 2008–2018.
  Likewise `IncurredClaimsPropertyCasualtyAndLiability` (2008–2024) replaces the absent
  `PolicyholderBenefitsAndClaimsIncurredNet`, and
  `LiabilityForClaimsAndClaimsAdjustmentExpensePropertyCasualtyLiability` (2008–2024,
  **exact match** with the current tag at all 7 overlapping dates) supplements
  `LiabilityForClaimsAndClaimsAdjustmentExpense` (annual-only 2015–2020, then a 2021–2022 gap).
- **PGR**: `PremiumsEarnedNetPropertyAndCasualty` (2008–2024) and
  `IncurredClaimsPropertyCasualtyAndLiability` (2008–2024) are the pre-2023/2024 predecessors
  of PGR's current tags — verified via **near-exact overlap** at the transition quarters
  (e.g. 2023-09-30 incurred claims: 11,387,900,000 in both tags, to the dollar).
- **AIG**: `OtherLongTermDebt` (2008–2015) is an **exact-match** predecessor of `LongTermDebt`
  (confirmed identical values at all 4 overlapping year-end dates, e.g. 2011-12-31:
  75,253,000,000 in both).
- **PGR**: `InvestmentsFairValueDisclosure` is a strict superset of `Investments` — identical at
  all 36 overlapping dates, plus one extra date PGR's `Investments` tag is missing.

### Confirmed coexisting/additive instruments (magnitude-verified, not overlapping)

- **EG**: `SeniorNotes` (2014–2026, ~$400M growing to ~$2.35B) and `NotesPayable` (2014–2018,
  a steadily-accreting ~$238M note) are two **separate, simultaneously-held** debt instruments
  — confirmed by identical dates carrying completely different magnitudes, not a rename.
  Reconstructed via `sum`.
- **WRB**: `NotesPayable` (3 sparse points, ~$1.5–1.9B) and `SubordinatedDebt` (2009–2013,
  ~$243–250M) are likewise distinct, non-overlapping-in-value instruments at the same dates.
  Reconstructed via `sum`.
- **ACGL**: `SeniorLongTermNotes` is a clean, continuous (65 points, 2009–2026), self-contained
  total — no companion tag needed.

### Confirmed structural gaps (no fix possible via tag search)

- **L, DepreciationAndAmortization**: raw JSON confirms every entry is `fp: "FY"`,
  `start`=Jan 1 — L simply never tags D&A quarterly. Same root cause independently confirmed
  for **ALL's** original `PremiumsEarnedNet` gap.
- **CINF, EG — Goodwill**: no `Goodwill`/`*Intangible*` tag exists in either company's raw
  XBRL at all (checked narrow + broad hints) — both are genuinely goodwill-free balance sheets.
- **ACGL, AIG — Goodwill**: the `Goodwill` tag itself exists but both companies only tag it
  once a year (ACGL: exactly one point per fiscal year, 2012–2025) or irregularly (AIG). No
  alternate tag exists for either. Not fixable by substitution — it's a tagging-frequency
  limitation of the filer, not a wrong-tag problem.
- **EG, DepreciationAndAmortization**: no D&A-related tag exists at all — consistent with EG
  being a reinsurer with minimal PP&E (the same reason `Capex`/`CashAndEquivalents` are already
  excluded from this profile).
- **WRB, BenefitsLossesAndExpenses**: WRB has a real, quarterly, complete `Losses` component
  (`PolicyholderBenefitsAndClaimsIncurredNet`, 67/67), but its only candidate underwriting-cost
  components (`SupplementalInformationForPropertyCasualtyInsuranceUnderwritersAmortization
  OfDeferredPolicyAcquisitionCosts` and `OtherUnderwritingExpense`) are **both annual-only**
  (raw JSON confirms `fp: "FY"` only). Summing a quarterly series with two annual-only series
  would silently produce a "losses-only" total in 3 of every 4 quarters — a periodicity
  mismatch, not a genuine sum. Per the task's own guidance for this exact case, **not
  attempted**; reported as "not currently buildable" rather than forced.

### Rejected candidates (name-plausible, magnitude-verified wrong)

- **AIG/CB/L, RealizedInvestmentGains**: every plausible-sounding component tag
  (`TradingSecuritiesRealizedGainLoss`, `EquitySecuritiesFvNiRealizedGainLoss`,
  `DebtSecuritiesAvailableForSaleRealizedGainLoss`,
  `AvailableForSaleSecuritiesGrossRealizedGainLossNet`) was checked against AIG's own
  `RealizedInvestmentGainsLosses` at the one date where both exist (2021-06-30): the "total"
  is **-1,926,000,000** while every candidate component is in the **tens/hundreds of millions**
  — off by more than an order of magnitude, confirming these are partial components (AFS
  securities, trading securities, equities — each just one slice of AIG's total realized
  gain/loss, which also includes real estate, alternative investments, and derivatives not
  separately tagged). **This candidate was initially added for L (no baseline existed to check
  it against directly) and, via the shared config, also silently filled 34 of AIG's gap
  quarters. Once the AIG magnitude check flagged it as a subset, it was reverted for both
  tickers** — see the "reverted" note in Step 4. CB's own legacy tag
  (`RealizedGainLossOnMarketableSecuritiesAndCostMethodInvestmentsExcludingOtherThanTemporary
  ImpairmentsAndOtherInvestments`, 2010–2018) was also rejected: at the sole overlap date
  (2018-06-30) it shows **+22M** while CB's actual tag shows **-13M** — opposite sign at the
  only verifiable point, not confirmable as the same underlying figure.
- **PTC-style partial-component check applied to EG's `Investments`**: `InvestmentsAndCash`
  has excellent coverage (65 points) but literally includes cash — cash is deliberately
  excluded from this profile's other concepts, so folding it back in here would contaminate
  `net_investment_yield`. Rejected as primary; the properly-scoped
  `SummaryOfInvestmentsOtherThanInvestmentsInRelatedPartiesCarryingAmount` (annual-only, 15
  points) was used instead — correct scope, just structurally sparse.
- **PGR's pre-2017 `Investments`**: no fixed-maturities/equity-securities aggregate tag exists
  before 2017 — PGR appears to have only started publishing a single consolidated "Investments"
  balance-sheet line that year. Genuine structural start date, not fixable.

## Step 3 — Config changes applied

All of the following remained in (or were migrated to) `mode: "fallback"` except `LongTermDebt`,
which required a `priority_merge` restructure to support `sum` sources cleanly.

**Simple fallback-tag additions** (`PROFILE_CONCEPT_OVERRIDES["insurance_pc"]`):

| Concept | Added tag(s) | Target ticker(s) |
|---|---|---|
| `NetInvestmentIncome` | `InvestmentIncomeNet` | ACGL (reconciled exactly: interest+dividend − expense = net, to the dollar) |
| `EarnedPremiums` | `PremiumsEarnedNetPropertyAndCasualty` | ALL, PGR |
| `IncurredLosses` | `IncurredClaimsPropertyCasualtyAndLiability` | ALL, PGR |
| `ClaimsReserve` | `LiabilityForClaimsAndClaimsAdjustmentExpensePropertyCasualtyLiability` | ALL |
| `Investments` | `InvestmentsFairValueDisclosure`, `SummaryOfInvestmentsOtherThanInvestmentsInRelatedPartiesCarryingAmount` | PGR, EG |

**`LongTermDebt` — two-step `priority_merge` migration**, since it wasn't previously overridden
for `insurance_pc` (it inherited the shared base list used by tech/standard tickers):

1. *Stage B1*: created `PROFILE_CONCEPT_OVERRIDES["insurance_pc"]["LongTermDebt"]` as an exact
   copy of the base `sources` list. Verified **byte-identical** (0 diffs, 0 new fills) across
   all 122 cached tickers before proceeding — this isolates all further insurance_pc-specific
   changes from ever touching tech/standard/financial-profile tickers.
2. *Stage B2*: appended two new lowest-priority sources:
   - `{"type": "tag", "tag": "SeniorLongTermNotes"}` (ACGL)
   - `{"type": "sum", "tags": ["SeniorNotes", "NotesPayable", "SubordinatedDebt"]}` (EG, WRB)

   Before finalizing the sum, checked whether any *other* insurance_pc ticker also carries one
   of these three tag names in a way that could misfire: **CINF and HIG both do**
   (`NotesPayable`; HIG also has `SeniorNotes`), but both already have gapless `LongTermDebt`
   coverage from higher-priority sources, so the low-priority sum never fires for them —
   confirmed empirically (0 new fills for either from this source).

**No changes**: `Goodwill`, `DepreciationAndAmortization`, `BenefitsLossesAndExpenses` — all
structural gaps per Step 2, no viable candidate found.

**Minor documentation fix**: added the missing `SEARCH_HINTS["RealizedInvestmentGains"]` entry
(`["realizedgain", "realizedinvestment"]`) — it had no entry at all, which is why this task had
to hand-construct hint lists for that concept. No effect on the data pipeline.

## Step 4 — Non-regression check (full 122-ticker cached universe)

- **Stage B1 (byte-identical copy)**: 0 regressions, 0 new fills — confirmed inert as intended.
- **Stage B2 + all fallback-tag additions, first pass**: **0 regressions**, 627 new fills.
- **One addition reverted after deeper verification**: `AvailableForSaleSecuritiesGrossRealized
  GainLossNet` had been added to `RealizedInvestmentGains` for L's benefit (no existing L data
  to check it against). It also silently filled 34 of AIG's gap quarters via the shared config.
  Because AIG *does* have an existing baseline, the magnitude check against it (see Step 2)
  showed this tag is a partial AFS-securities-only component, off by more than 10x from AIG's
  true total — meaning the same tag was almost certainly also wrong for L (no evidence it's the
  full total there either, just no baseline to catch it). **Reverted entirely** rather than kept
  for L alone; L's `RealizedInvestmentGains` and AIG's `RealizedInvestmentGains` both remain at
  their original values.
- **Final pass after reversion**: **0 regressions**, **569 new fills**, all magnitude-spot-checked
  for smoothness/continuity against neighboring existing values (AIG/CINF/HIG ClaimsReserve
  bonus fills, CB NetInvestmentIncome bonus fill, TRV ClaimsReserve bonus fill — all confirmed
  sane, no discontinuities or sign flips).

New fills by ticker/concept (final, accepted state):

```
ACGL   LongTermDebt                 +65
ACGL   NetInvestmentIncome          +67
AIG    ClaimsReserve                +15   (bonus — not originally targeted)
ALL    ClaimsReserve                +54
ALL    EarnedPremiums               +39
ALL    IncurredLosses               +63
CB     NetInvestmentIncome          +26   (bonus)
CINF   ClaimsReserve                +11   (bonus)
EG     Investments                  +15
EG     LongTermDebt                 +63
HIG    ClaimsReserve                +6    (bonus)
PGR    EarnedPremiums               +62
PGR    IncurredLosses               +60
PGR    Investments                  +8
TRV    ClaimsReserve                +2    (bonus — the reference ticker also improved)
WRB    LongTermDebt                 +13
```

No ticker outside the 10 (plus TRV) was touched by any change — verified empirically, not just
assumed from the profile-isolation logic.

## Step 5 — Before/after coverage

| Ticker | Concept | Before | After | Outcome |
|---|---|---|---|---|
| ACGL | NetInvestmentIncome | 0% | **97%** | ✅ Fully resolved |
| ACGL | LongTermDebt | 0% | **94%** | ✅ Fully resolved |
| ACGL | RealizedInvestmentGains | 0% | 0% | ❌ Unchanged — no reliable candidate (components don't reconcile across accounting-standard eras); flagged for human review |
| ACGL | Goodwill | 20% | 20% | ❌ Unchanged — structural (annual-only tagging, no alternate tag) |
| AIG | RealizedInvestmentGains | 44% | 44% | ❌ Unchanged — candidate found, tested against AIG's own data, confirmed wrong (10x+ magnitude mismatch), reverted |
| AIG | LongTermDebt | 45% | 45% | ❌ Unchanged for AIG specifically (its predecessor tag `OtherLongTermDebt` only covers 2008–2015; recent years are annual-only, structural) |
| AIG | Goodwill | 42% | 42% | ❌ Unchanged — structural (irregular annual/quarterly mix, no alternate tag) |
| ALL | EarnedPremiums | 0% | **53%** | ✅ Fully resolved (crosses threshold; residual gap is 2018+ where ALL's own successor tag is annual-only — structural) |
| ALL | IncurredLosses | 0% | **86%** | ✅ Fully resolved |
| ALL | ClaimsReserve | 21% | **95%** | ✅ Fully resolved |
| CB | RealizedInvestmentGains | 39% | 39% | ❌ Unchanged — legacy candidate rejected (sign mismatch at sole overlap point) |
| CINF | Goodwill | 0% | 0% | ❌ Unchanged — structural (no goodwill on balance sheet, no tag exists) |
| EG | LongTermDebt | 0% | **91%** | ✅ Fully resolved |
| EG | Investments | 0% | **22%** | ⚠️ Improved, not clean — real, correctly-scoped data, but the only viable tag is annual-only |
| EG | DepreciationAndAmortization | 0% | 0% | ❌ Unchanged — structural (no D&A tag exists at all; reinsurer with minimal PP&E) |
| EG | Goodwill | 0% | 0% | ❌ Unchanged — structural (no goodwill tag exists) |
| L | RealizedInvestmentGains | 0% | 0% | ❌ Unchanged — candidate found and initially added, then reverted after the AIG cross-check exposed it as a partial component, not the total |
| L | DepreciationAndAmortization | 0% | 0% | ❌ Unchanged — structural (confirmed annual-only via raw JSON) |
| PGR | EarnedPremiums | 12% | **97%** | ✅ Fully resolved |
| PGR | IncurredLosses | 15% | **97%** | ✅ Fully resolved |
| PGR | Investments | 49% | **60%** | ✅ Crosses threshold (residual gap is pre-2017, genuinely no aggregate tag existed) |
| WRB | LongTermDebt | 0% | **19%** | ⚠️ Improved, not clean — WRB is a low-debt issuer with genuinely sparse XBRL debt tagging (same pattern as several tech tickers from the prior Bank/Tech task) |
| WRB | BenefitsLossesAndExpenses | 0% | 0% | ❌ Unchanged — real components exist but periodicity mismatch (quarterly losses vs. annual-only expenses) makes a clean sum impossible; reported as not currently buildable |

**Summary**: 9 concept/ticker gaps fully resolved (crossing or far exceeding the 50%
threshold), 2 improved with genuine but structurally sparse data (EG Investments, WRB
LongTermDebt), 11 unchanged for well-documented structural reasons (annual-only tagging,
no tag exists, or candidate tested and rejected). TRV itself picked up 2 bonus ClaimsReserve
fills as a side effect, and AIG/CINF/HIG/CB each picked up small bonus fills from the shared
config additions — all magnitude-verified as legitimate.

## Open items for the human reviewer

1. **ACGL's `RealizedInvestmentGains`** has no assembled total across its full history — the
   company's own reporting is fragmented across several overlapping-but-inconsistent tag
   regimes (pre-2017 AFS-only, 2017+ FV-NI equity split, a 2019–2022 "marketable securities"
   transitional tag). A correct reconstruction would need every component identified and
   verified additive per era — not attempted here given the risk of silently under- or
   double-counting.
2. **AIG's `RealizedInvestmentGains` 2011–2021 gap** and **CB's pre-2018 gap** remain open.
   Every candidate tested is either an order-of-magnitude-mismatched subset (AIG) or has an
   unverifiable sign discrepancy at the only overlap point (CB). Both would need a full
   itemized reconstruction (all investment-category components identified and summed) to close
   safely.
3. **WRB's combined ratio (`BenefitsLossesAndExpenses`)** cannot currently be built on a
   quarterly basis — the loss component is quarterly but the two acquisition-cost/underwriting
   components WRB discloses are annual-only. If WRB ever begins tagging those quarterly, this
   should be revisited.
4. **AIG's and ACGL's `Goodwill`** are tagged only annually/irregularly by the filers
   themselves — no XBRL-level fix is possible; this would need to be accepted as a known
   limitation or the snapshot logic changed to explicitly forward-fill point-in-time annual
   values between reporting dates (a broader pipeline change, out of scope here).

No scratch scripts were left behind.
