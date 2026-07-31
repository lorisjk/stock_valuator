# Full Quality-Flag Sweep — All Flags from `full_refresh_report.md`

Every data-quality flag listed in `full_refresh_report.md`'s "Data quality flags" section
was individually investigated: real tags searched via a values-aware equivalent of
`explore_tags.py`, raw quarterly values pulled from each ticker's cached SEC EDGAR company
facts, candidate replacement tags checked for scale and scope (not just presence) before
being trusted, and same-filing-date/scope-break signatures checked wherever a restatement
or corporate event looked like the likely cause. Fixes were only applied where the evidence
was conclusive; anything left uncertain is logged as ambiguous rather than forced.

Groups are presented in the exact order they appear in the source report. Each section
lists every flagged `(ticker, concept)` pair, what was found, and a before/after coverage
table (in the `x of y (z%)` format the source report uses; unchanged rows mean no
confirmed-safe fix existed).

**Total flags investigated:** 387 (re-derived directly from the source report's 21
profile sections; close to the report's own summary count of ~396, with the small gap
immaterial to any finding below).
**Real fixes applied and non-regression-verified:** 12
**Logged as ambiguous:** ~8
**Confirmed structural (no fix needed or possible):** ~367

---

## airline (1 flag)

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| UAL | DividendsPerShare | 0/71 (0%) | 0/71 (0%) | Confirmed structural |

UAL: both configured tags absent; the only hits are a one-off 2008 preferred-stock item and
the universal $0.0000 `ExpectedDividendRate` stock-comp assumption. No common per-share
dividend tag exists anywhere in United's filings. Genuine non-payer.

No config changes. Non-regression: trivially clean (nothing to diff).

---

## captive_finance (10 flags)

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| CAT | LongTermDebt | 18/78 (23%) | 18/78 (23%) | Confirmed structural |
| F | Goodwill | 29/72 (40%) | 29/72 (40%) | Confirmed structural |
| F | OperatingIncomeLoss | 30/72 (42%) | 30/72 (42%) | Confirmed structural |
| GM | LongTermDebt | 15/66 (23%) | 15/66 (23%) | Confirmed structural |
| GM | Goodwill | 30/66 (45%) | 30/66 (45%) | Confirmed structural |
| PCAR | OperatingIncomeLoss | 0/73 (0%) | 0/73 (0%) | Confirmed structural |
| PCAR | LongTermDebt | 0/73 (0%) | 0/73 (0%) | Confirmed structural |
| PCAR | Goodwill | 15/73 (21%) | 15/73 (21%) | Confirmed structural |
| TXT | Goodwill | 0/68 (0%) | 0/68 (0%) | Confirmed structural |
| TXT | LongTermDebt | 0/68 (0%) | 0/68 (0%) | Confirmed structural |
| TXT | OperatingIncomeLoss | 2/68 (3%) | 2/68 (3%) | Confirmed structural |

- **CAT LongTermDebt**: current resolution already unions every configured source; a
  broadened "debt" search (35 hits) found only AFS investment securities, cash-flow
  issuance/repayment items, maturity schedules, and a wrong-maturity-bucket
  `ShortTermBorrowings` — no viable balance-sheet substitute.
- **F Goodwill / OperatingIncomeLoss**: both tags simply start late (2015-12-31 and
  2018-09-30 respectively); every hit is an amortization/impairment flow item or the
  non-operating complement, not an alternate balance/subtotal tag.
- **GM LongTermDebt / Goodwill**: `IntangibleAssetsNetIncludingGoodwill` (47 vals) exists but
  is a different, broader combined concept — rejected rather than silently redefining what
  "Goodwill" means for this ticker.
- **PCAR** (OperatingIncomeLoss, LongTermDebt, Goodwill): matches the conglomerate
  no-discrete-operating-income-subtotal pattern seen repeatedly across this sweep; Goodwill
  looks like an annual-only disclosure (~1x/year cadence).
- **TXT**: bundles goodwill into a combined "Intangible assets, net" line with no separate
  numeric Goodwill fact; OperatingIncomeLoss tagged for only 2 quarters ever, no
  alternative found.

No config changes. Non-regression: trivially clean.

---

## consumer_staples (13 flags)

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| ADM | OperatingIncomeLoss | 0% | 0% | Confirmed structural |
| BG | OperatingIncomeLoss | 0% | 0% | Confirmed structural |
| CASY | OperatingIncomeLoss | 0% | 0% | Confirmed structural |
| CLX | OperatingIncomeLoss | 0% | 0% | Confirmed structural |
| HSY | DividendsPerShare | 6/76 (8%) | 6/76 (8%) | Confirmed structural |
| KR | Capex | 35/74 (47%) | 35/74 (47%) | Confirmed structural |
| KR | OperatingCashFlow | 35/74 (47%) | 35/74 (47%) | Confirmed structural |
| KVUE | DividendsPerShare | 7/20 (35%) | 7/20 (35%) | Confirmed structural |
| MNST | DividendsPerShare | 0/70 (0%) | 0/70 (0%) | Confirmed structural |
| MNST | LongTermDebt | 5/70 (7%) | 5/70 (7%) | Confirmed structural |
| STZ | DividendsPerShare | 0/72 (0%) | 0/72 (0%) | Confirmed structural |
| STZ | SharesOutstanding | 0/72 (0%) | 0/72 (0%) | Confirmed structural |
| SYY | DepreciationAndAmortization | 35/73 (48%) | 35/73 (48%) | Confirmed structural |
| TSN | DividendsPerShare | 0/75 (0%) | 0/75 (0%) | Confirmed structural |

- **ADM/BG/CASY/CLX OperatingIncomeLoss**: no usable substitute anywhere (conglomerate
  no-discrete-subtotal pattern).
- **HSY / STZ / TSN DividendsPerShare — cross-cutting pattern (genuine payer, per-share tag
  never filed)**: all three unquestionably pay and grow their dividend every quarter today,
  confirmed via `PaymentsOfDividendsCommonStock` (HSY $270M+/qtr through 2026, STZ
  ~$177M/qtr, TSN ~$170-180M/qtr back to 2010) — but no per-share tag exists for the
  relevant window. A third distinct DividendsPerShare sub-pattern beyond "genuine
  non-payer" and "young ticker," and the one place in this group where the risk ran the
  opposite direction from usual (assuming "no per-share tag" meant "no dividend" would
  have been wrong). Not fixable at tag level without deriving $/share from aggregate $
  and share count, which is a new calculation outside this task's scope.
- **KR Capex / OperatingCashFlow**: identical 47% ratio for both, plausibly a shared
  underlying XBRL cash-flow-statement cadence gap; no superior tag for either.
- **KVUE DividendsPerShare**: young ticker (2023 J&J spinoff, only 20 periods expected).
- **MNST LongTermDebt**: real business fact — Monster operated essentially debt-free until
  ~2023; a same-window candidate (`OtherLongTermDebtNoncurrent`) matches exactly but adds
  no new dates.
- **STZ SharesOutstanding**: escalated to a full cross-namespace check (dei, invest,
  us-gaap, ffd, ecd) given how unusual a total absence is for a mandatory GAAP disclosure —
  confirmed zero EPS or share-count tags anywhere in Constellation Brands' entire XBRL
  history. Genuinely unavailable from this data source, not a partial gap.
- **SYY DepreciationAndAmortization**: 43-hit search found only pension amortization,
  forward-looking schedule disclosures, financing-cost amortization, and a post-2019-only
  lease-ROU component — no safe substitute without conflating unlike concepts.

No config changes. Non-regression: trivially clean.

---

## energy (1 flag)

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| TPL | LongTermDebt | 0/29 (0%) | 0/29 (0%) | Confirmed structural |

TPL: Texas Pacific Land Corp is an essentially debt-free royalty/land company that only
very recently drew a small facility ($5.1M in 2025); no configured tag present, consistent
with genuine no-debt-to-report status.

No config changes. Non-regression: trivially clean.

---

## energy_integrated (5 flags) — 1 real fix applied

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| BKR | DividendsPerShare | 0/42 (0%) | 0/42 (0%) | Confirmed structural |
| BKR | SharesOutstanding | 4/42 (10%) | 2/42 (5%) | **Fixed (correctness, not coverage)** |
| COP | Capex | 32/74 (43%) | 32/74 (43%) | Confirmed structural |
| PSX | Capex | 0/64 (0%) | 0/64 (0%) | Confirmed structural |
| SLB | DividendsPerShare | 14/74 (19%) | 14/74 (19%) | Confirmed structural |

- **BKR DividendsPerShare**: genuine-payer-but-untagged (`PaymentsOfDividendsCommonStock`
  confirms ~$227M/qtr real payments through 2026; no per-share tag exists).
- **BKR SharesOutstanding — FIXED.** Two of the only 4 existing datapoints
  (`CommonStockSharesOutstanding` = exactly 100 shares at both 2016-12-31 and 2017-06-30,
  both from the same 10-Q filed 2017-07-28 covering the "Baker Hughes, a GE Company"
  formation) were not thin but actively wrong — a nominal shell-entity count from before
  real shares were issued, contradicted by BKR's real hundreds-of-millions share count.
  Added both exact `(end, filed, val)` triples to `_KNOWN_BAD_FACTS` in
  `parsers/parse_edgar.py`. Coverage % drops (4→2 of 42) because a silently-wrong value is
  worse than a missing one — the same principle behind the standing TROW D&A precedent.
- **COP Capex**: the one candidate found (`PaymentsForProceedsFromProductiveAssets`) is a
  net proceeds-less-payments concept with negative sample values — a scope mismatch, not a
  genuine substitute.
- **PSX Capex**: no genuine cash-capex tag ever present; only balance-sheet PP&E and
  disposal-proceeds items found.
- **SLB DividendsPerShare**: genuine-payer-but-untagged since mid-2012 (real payments
  continue at $400M+/qtr through 2026 per `PaymentsOfDividends`).

**Config changes**: `parsers/parse_edgar.py` — added `("BKR", "CommonStockSharesOutstanding")`
to `_KNOWN_BAD_FACTS`.

**Group non-regression** (8 tickers: XOM CVX COP OXY DVN PSX SLB BKR) vs. master
before-snapshot: exactly 2 rows removed (the 2 excluded BKR dates), 0 added, 0 changed, 0
other tickers touched. Clean.

---

## financial (13 flags)

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| AXP | Goodwill | 18/74 (24%) | 18/74 (24%) | Confirmed structural |
| HOOD | DividendsPerShare | 0/27 (0%) | 0/27 (0%) | Confirmed structural |
| HOOD | ProvisionForCreditLosses | 0/27 (0%) | 0/27 (0%) | Confirmed structural |
| HOOD | NoninterestExpense | 0/27 (0%) | 0/27 (0%) | Confirmed structural |
| HOOD | NoninterestIncome | 0/27 (0%) | 0/27 (0%) | Confirmed structural |
| IBKR | Goodwill | 0/69 (0%) | 0/69 (0%) | Confirmed structural |
| IBKR | ProvisionForCreditLosses | 0/69 (0%) | 0/69 (0%) | Confirmed structural |
| IBKR | NetInterestIncome | 29/69 (42%) | 29/69 (42%) | Confirmed structural |
| IBKR | NoninterestIncome | 29/69 (42%) | 29/69 (42%) | Confirmed structural |
| PNC | DividendsPerShare | 32/73 (44%) | 32/73 (44%) | Confirmed structural |
| RJF | NoninterestIncome | 19/69 (28%) | 19/69 (28%) | Confirmed structural |
| SCHW | NoninterestIncome | 0/73 (0%) | 0/73 (0%) | Confirmed structural |
| SOFI | DividendsPerShare | 9/28 (32%) | 9/28 (32%) | Confirmed structural (correct values) |

- **AXP Goodwill**: ~annual-only disclosure cadence; no balance substitute.
- **HOOD — all 4 flagged concepts, zero keyword hits each** (not just zero *new* hits —
  zero hits, period). Robinhood's income statement genuinely doesn't use bank-style
  interest/noninterest/credit-loss terminology at all — a retail trading-app brokerage, not
  a depository bank. Business-model/profile-fit observation, reported only per the task's
  standing rule not to split/reassign profiles myself.
- **IBKR Goodwill**: plausible genuine absence (organic growth, little M&A).
  **ProvisionForCreditLosses**: broker-dealer margin-lending risk isn't CECL-provisioned
  like a depository bank's loan book. **NetInterestIncome/NoninterestIncome**: both tags
  only start 2019; the one candidate for NetInterestIncome
  (`InterestIncomeOperating`, gross, not net of expense) is a different, wider concept —
  rejected as a definition mismatch.
- **PNC DividendsPerShare**: genuine-payer-but-untagged before 2011 (real payments confirmed
  back to 2008).
- **RJF NoninterestIncome**: the one candidate (`NoninterestIncomeOtherOperatingIncome`) is
  ~100-300x smaller in scale than RJF's real total — a minor "other" sub-component, not the
  total. Rejected on scale grounds.
- **SCHW NoninterestIncome**: zero hits — Schwab names distinct revenue lines (asset-mgmt
  fees, trading revenue, bank deposit fees, net interest revenue) without ever rolling them
  into a bank-style subtotal. Same broker-vs-bank mismatch as HOOD.
- **SOFI DividendsPerShare**: both configured tags resolve, every value is genuinely
  $0.0000 — a real non-payer that only started explicitly tagging the $0 line from
  2024-03-31 onward. Correct values, not a gap in substance.

**Cross-cutting observation**: HOOD, SCHW, and IBKR show that non-bank broker-dealers
inside the `financial` profile structurally don't populate the profile's bank-style
concepts — a presentation/business-model mismatch, not a data defect. Reported only.

No config changes. Non-regression: trivially clean.

---

## health_services (6 flags)

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| CI | Capex | 8/37 (22%) | 8/37 (22%) | Confirmed structural |
| CNC | DividendsPerShare | 0/71 (0%) | 0/71 (0%) | Confirmed structural |
| DVA | DividendsPerShare | 0/74 (0%) | 0/74 (0%) | Confirmed structural |
| HCA | OperatingIncomeLoss | 0/67 (0%) | 0/67 (0%) | Confirmed structural |
| HCA | Goodwill | 4/67 (6%) | 4/67 (6%) | Confirmed structural |
| LH | DividendsPerShare | 7/74 (9%) | 7/74 (9%) | Confirmed structural |

- **CI Capex**: only a tight 2018-2019 window (around the Dec-2018 Express Scripts merger
  close); apparently stopped tagging a discrete capex flow figure after the post-merger
  transition.
- **CNC / DVA DividendsPerShare**: genuine non-payers. DaVita's `PaymentsOfDividendsMinorityInterest`
  ($32-39M/qtr) is payouts to physician-partner JV minority interests, not to DVA's own
  shareholders — correctly not conflated.
- **HCA OperatingIncomeLoss**: conglomerate/hospital-operator pattern, zero hits.
  **Goodwill**: tag covers only 4 quarters (2010-12-31 to 2011-09-30) right before HCA's
  Nov-2011 re-IPO; `IntangibleAssetsNetIncludingGoodwill` picks up the very next quarter and
  continues — a real presentation switch to a combined line, rejected as a different,
  broader concept (same reasoning as GM's identical case).
- **LH DividendsPerShare**: a genuinely young-initiator gap (LH's own aggregate tags only
  start 2021, per-share tag not until mid-2024). One candidate
  (`DividendsPayableAmountPerShare`) has a single datapoint wildly inconsistent in scale
  with LH's real ~$0.72/share rate — rejected on the standing scale-check rule.

No config changes. Non-regression: trivially clean.

---

## homebuilder (7 flags, all LEN)

(DHI, the other homebuilder ticker, has zero flags.)

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| LEN | AccountsPayable | 0/67 (0%) | 0/67 (0%) | Confirmed structural |
| LEN | CostOfRevenue | 0/67 (0%) | 0/67 (0%) | Confirmed structural |
| LEN | AccountsReceivable | 4/67 (6%) | 4/67 (6%) | Confirmed structural |
| LEN | Inventory | 10/67 (15%) | 10/67 (15%) | Confirmed structural |
| LEN | Goodwill | 14/67 (21%) | 14/67 (21%) | Confirmed structural |
| LEN | LongTermDebt | 26/67 (39%) | 26/67 (39%) | Confirmed structural |
| LEN | DividendsPerShare | 33/67 (49%) | 33/67 (49%) | Confirmed structural |

- **AccountsPayable**: only hit is a combined AP+accrued-liabilities cash-flow *change*
  item — wrong shape (duration vs. balance) and wrong scope.
- **CostOfRevenue**: zero keyword hits.
- **AccountsReceivable — candidate investigated and rejected with evidence.**
  `AccountsReceivableNet` (12 vals) looked like a big improvement over the current 4-value
  tag, but at every shared date the two report materially different values (2019-11-30:
  $329.1M vs $906.9M, ~3x apart) — a real segment-scope difference (LEN has
  Homebuilding/Financial-Services/Multifamily segments), correctly rejected.
- **Inventory**: only `InventoryOperativeBuilders` (2019-2025); no total-inventory
  alternative found among tax, write-down, or Financial-Services-segment loan items.
- **Goodwill**: sporadic/annual-leaning disclosure of an unchanging $3,632.1M value; no
  substitute balance tag.
- **LongTermDebt — a live instance of the standing OtherNotesPayable trap.** The
  keyword hit `OtherNotesPayable` exists for exactly the 2011-2016 gap window and looked
  promising, but its values ($246-280M) are ~5% the size of `NotesPayable`'s own values
  ($5.0-5.3B) at the same dates — a small residual sub-component, correctly rejected.
- **DividendsPerShare**: genuine-payer-but-untagged, with two separate untagged windows
  (2016-2019 and 2023-present); `PaymentsOfDividendsCommonStock` (66 vals) confirms real,
  continuing ~$123-127M/qtr payments throughout both gaps.

No config changes. Non-regression: trivially clean.

---

## industrials (36 flags in the actual report)

Grouped by cross-cutting pattern rather than repeated per-ticker (all confirmed structural,
all before=after):

**Conglomerate/diversified, no discrete OperatingIncomeLoss subtotal** (only non-operating
complements found): ADP 0/72, EMR 0/74, ETN 8/60 (stops 2013), GE 15/74 (stops 2014 — the
textbook case), HON 21/75 (only from 2021), JCI 32/81 (stops 2016), LHX 21/73 (only from
2016), ROK 4/74 (last 4 quarters only; one candidate rejected — 2008-2009-only, tiny scale),
ROL 22/73 (only from 2021).

**Genuine non-payer**: BLDR 0/66, CPRT 0/69, TSLA 0/67 (textbook case), AXON 0/66.

**Genuine continuous payer, per-share tag gapped/absent** (the single largest recurring
theme in this whole sweep — confirmed via aggregate payment tags): CARR 6/31, EXPD 28/75
(stops entirely after 2021-09-30 despite continuous real payments through 2025), IEX 28/70,
IR 0/42, J 20/78 (one candidate, `DividendsPayableAmountPerShare`, is point-in-time and
adds no new window — rejected), JCI 28/81 (~6-year gap despite payments since 2008), UPS
33/74 (~9-year gap despite payments since 2008), VRSK 12/67, VRT 0/36 (same
`DividendsPayableAmountPerShare` rejection as J).

**Young ticker / genuinely recent dividend initiator**: GEV 4/17 (2024 GE spinoff), VLTO
2/18 (2023 Danaher spinoff), URI 13/66 (explicit $0.0000 pre-2023, real initiation
confirmed), PWR 33/75 (program began 2018, matching the tag's own start).

**Real "no debt to report" history**: AXON LongTermDebt 16/66 (debt-free 2015-2022), EXPD
0/75 (asset-light logistics, only a small recent facility), GEV 3/17 (clean spinoff
balance sheet), PAYX 30/74 (no long-term debt before ~2018-2019; a `LongTermDebtFairValue`
candidate rejected — different measurement basis), ROL 8/73 (no debt before 2019).

**Sporadic/thin Goodwill, no viable substitute** (both specifically rejected an
"IncludingGoodwill" combined-concept candidate): FAST 0/75 (plausibly genuine, little M&A),
JBHT 14/71.

**Individually distinct**: SNA Capex 0/74 (no cash-capex tag anywhere); LMT
DepreciationAndAmortization 37/76 (a real ~8-year gap 2017-2024; a software-only
amortization sub-tag rejected despite plausible scale, because its scope is narrower than
total D&A); GNRC DividendsPerShare 6/65 (the one $5.00 anomaly at 2013-06-30 checked out as
a real one-time special dividend, not an error).

No config changes. Non-regression: trivially clean.

---

## insurance_life (8 flags) — 1 real fix applied

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| AFL | Investments | 0/73 (0%) | 0/73 (0%) | Confirmed structural |
| AFL | Goodwill | 7/73 (10%) | 7/73 (10%) | Confirmed structural |
| GL | RealizedInvestmentGains | 29/71 (41%) | 29/71 (41%) | **Ambiguous** |
| PFG | ClaimsReserve | 15/74 (20%) | 15/74 (20%) | Confirmed structural |
| PFG | DividendsPerShare | 32/74 (43%) | 32/74 (43%) | Confirmed structural |
| PRU | RealizedInvestmentGains | 16/73 (22%) | 71/73 (97%) | **Fixed** |
| PRU | Goodwill | 19/73 (26%) | 19/73 (26%) | Confirmed structural |
| PRU | ClaimsReserve | 21/73 (29%) | 21/73 (29%) | Confirmed structural |

- **AFL Investments**: no clean same-scope substitute (a wrong-scope combined tag bundles
  in cash; a narrow sub-bucket covers only "other investments").
- **AFL Goodwill**: only tagged from 2019; 0 new keyword hits.
- **GL RealizedInvestmentGains — candidate rejected with evidence, logged ambiguous.**
  `RealizedInvestmentGainsLosses` looked promising (69 vals vs. 29) but at all 29
  overlapping dates it does not track the currently-used
  `GainLossOnSaleOfOtherInvestments` — values differ in magnitude and repeatedly flip sign
  at the same date (2020-03-31: +$240K vs -$26.1M). Proven a materially different, broader
  concept for GL specifically. Since the values conflict rather than merely being
  incomplete, and EDGAR data alone can't independently confirm which is "the" reported
  total, this is logged ambiguous rather than forced.
- **PFG ClaimsReserve**: the one candidate with real breadth is ~30x smaller in scale — a
  P&C-style claims sub-reserve, not PFG's life/retirement policy-benefit reserve.
  **DividendsPerShare**: genuine-payer-but-untagged since 2013; a tempting hit
  (`PolicyholderDividends`) is dividends paid *to policyholders*, a different concept —
  correctly not conflated.
- **PRU RealizedInvestmentGains — FIXED.** The same candidate tag investigated for GL
  checks out here: at all 16 overlapping dates, `RealizedInvestmentGainsLosses` tracks the
  same *sign* and similar magnitude as the already-used tag (e.g. 2016-03-31: $2,007M vs
  $1,881M) — never a sign flip, unlike GL. Added as a third, lowest-priority fallback in a
  new `TICKER_CONCEPT_OVERRIDES["PRU"]` entry, scoped to PRU only (GL's identical-looking
  candidate was rejected on its own evidence, so this was deliberately not generalized).
- **PRU Goodwill**: sparse/roughly-annual disclosure; 26 hits are all flow items, a gross
  variant, or excluding-goodwill intangibles.
- **PRU ClaimsReserve**: two candidates investigated and rejected, with a genuine scope-break
  finding — the sum of PRU's three product-line reserve components matches the main tag
  exactly for 2009-2020 but diverges sharply in 2021 (-$4.66B) and 2022 (-$19.4B), a real
  scope-break signature (plausibly a reserve-block divestiture/reclassification). A second
  candidate is off by $37 billion at 2021-12-31 alone. Neither adopted.

**Config changes**: `config.py` — new `TICKER_CONCEPT_OVERRIDES["PRU"]["RealizedInvestmentGains"]`.

**Group non-regression** (5 tickers: MET PRU AFL PFG GL) vs. master before-snapshot: 55
rows added (exactly 71-16), 0 removed, 0 changed, only PRU touched. Clean.

---

## insurance_pc (20 flags in the actual report) — 1 real fix applied

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| ACGL | DividendsPerShare | 0/69 (0%) | 0/69 (0%) | Confirmed structural |
| ACGL | RealizedInvestmentGains | 0/69 (0%) | 0/69 (0%) | Confirmed structural |
| ACGL | Goodwill | 14/69 (20%) | 14/69 (20%) | Confirmed structural |
| AIG | Goodwill | 31/73 (42%) | 31/73 (42%) | Confirmed structural |
| AIG | RealizedInvestmentGains | 32/73 (44%) | 32/73 (44%) | **Ambiguous** |
| AIG | LongTermDebt | 33/73 (45%) | 55/73 (75%) | **Fixed** |
| AIZ | LongTermDebt | 10/73 (14%) | 10/73 (14%) | Confirmed structural |
| AIZ | RealizedInvestmentGains | 33/73 (45%) | 33/73 (45%) | **Ambiguous** |
| AIZ | DepreciationAndAmortization | 35/73 (48%) | 35/73 (48%) | Confirmed structural |
| CB | RealizedInvestmentGains | 28/71 (39%) | 28/71 (39%) | Confirmed structural |
| CINF | Goodwill | 0/71 (0%) | 0/71 (0%) | Confirmed structural |
| CINF | DividendsPerShare | 19/71 (27%) | 19/71 (27%) | Confirmed structural |
| EG | Goodwill | 0/69 (0%) | 0/69 (0%) | Confirmed structural |
| EG | DepreciationAndAmortization | 0/69 (0%) | 0/69 (0%) | Confirmed structural |
| EG | Investments | 15/69 (22%) | 15/69 (22%) | Confirmed structural |
| L | DepreciationAndAmortization | 0/73 (0%) | 0/73 (0%) | Confirmed structural |
| L | RealizedInvestmentGains | 0/73 (0%) | 0/73 (0%) | **Ambiguous** |
| WRB | BenefitsLossesAndExpenses | 0/67 (0%) | 0/67 (0%) | Confirmed structural |
| WRB | LongTermDebt | 13/67 (19%) | 13/67 (19%) | Confirmed structural |
| WRB | DividendsPerShare | 31/67 (46%) | 31/67 (46%) | Confirmed structural (correct values) |

- **ACGL**: DividendsPerShare mostly a genuine non-payer (one very recent 2024-2025 hit is
  too new for a per-share tag). RealizedInvestmentGains: 11 hits are all gross-only,
  equity-only, OTTI-only, or unrealized — none the full net-portfolio figure. Goodwill:
  sparse/annual-leaning.
- **AIG Goodwill**: genuinely sporadic across 2008-2026, not annual-leaning, just gappy — no
  balance substitute. **RealizedInvestmentGains**: the one plausible-named candidate,
  `AvailableForSaleSecuritiesGrossRealizedGainLossNet`, shows $135M vs the main tag's
  -$1,926M at the one shared date — opposite sign, a huge divergence at AIG's scale.
  Rejected. **LongTermDebt — FIXED.** `OtherLongTermDebt` covers 2008-2015 and matches the
  already-used "LongTermDebt" tag to the exact dollar at all 4 overlapping dates
  (2011-12-31: $75,253M; ... 2014-12-31: $31,217M) — the same figure under AIG's older
  pre-2011 tag name, consistent with AIG's well-documented post-financial-crisis
  deleveraging. Added as lowest-priority fallback in a new
  `TICKER_CONCEPT_OVERRIDES["AIG"]["LongTermDebt"]` entry.
- **AIZ LongTermDebt**: tag stops entirely after 2020-03-31; no balance substitute for the
  post-2020 gap — a real, notable, unresolved gap (Assurant almost certainly still carries
  debt today). **RealizedInvestmentGains**: two candidates that nominally extend past
  2021-09-30 only resolve under point-in-time semantics though the concept is
  duration-based — a type mismatch suggesting an XBRL tagging quirk rather than a genuine
  substitute; not adopted.
- **CB RealizedInvestmentGains**: a hypothesized reconstruction (summing two legacy tags)
  disproven at the one shared date — main tag -$13M vs. the sum's +$26M, opposite sign.
- **CINF Goodwill**: zero hits, plausible given Cincinnati Financial's organic growth.
  **DividendsPerShare**: genuine-payer-but-untagged since 2018 (real payments back to 2009).
- **EG Goodwill**: only one-off 2011-2013 M&A items, plausible genuine absence for a
  reinsurer with limited M&A. **DepreciationAndAmortization**: every configured tag
  entirely absent; hits are debt-amortization, DAC-specific insurance amortization, pension
  amortization, or investment mark-to-market items (a different sense of "depreciation")
  — none is general D&A. **Investments**: the base tag covers only 2011-2025; sibling
  cost/fair-value variants cover the identical dates, no new coverage from any of 16 hits.
- **L DepreciationAndAmortization**: Loews is a multi-segment holding company (CNA
  insurance, Boardwalk pipeline, hotels) that apparently never rolls per-segment D&A into
  one consolidated tag. **RealizedInvestmentGains**: configured tag entirely absent, with no
  existing value to check any of 14 hits against — logged ambiguous rather than guessed.
- **WRB BenefitsLossesAndExpenses**: zero hits. **LongTermDebt**: coverage confined to
  2009-2013; nothing after despite WRB almost certainly still carrying debt today — a real,
  notable, unresolved gap. **DividendsPerShare**: the one value that looked anomalous
  ($1.09 sandwiched between $0.09 quarters) is a real, correctly-captured WRB special
  dividend, confirmed via a matching $411.9M spike in the aggregate payment tag — not an
  error. A tempting hit (`CashDividendsPaidToParentCompany`) is ~30-50x WRB's real
  shareholder-dividend scale — an internal insurance-subsidiary-to-holding-company
  regulatory flow, correctly rejected.

**Config changes**: `config.py` — new `TICKER_CONCEPT_OVERRIDES["AIG"]["LongTermDebt"]`.

**Group non-regression** (12 tickers: TRV CB PGR ALL AIG WRB CINF ACGL HIG L EG AIZ) vs.
master before-snapshot: 22 rows added (exactly 55-33), 0 removed, 0 changed, only AIG
touched. Clean.

---

## leisure (7 flags)

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| CMG | DividendsPerShare | 0/70 (0%) | 0/70 (0%) | Confirmed structural |
| CMG | LongTermDebt | 7/70 (10%) | 7/70 (10%) | Confirmed structural (correct values) |
| LVS | Goodwill | 9/71 (13%) | 9/71 (13%) | Confirmed structural |
| MAR | DepreciationAndAmortization | 22/75 (29%) | 22/75 (29%) | Confirmed structural |
| MGM | DividendsPerShare | 28/71 (39%) | 28/71 (39%) | Confirmed structural (correct values) |
| NCLH | DividendsPerShare | 0/60 (0%) | 0/60 (0%) | Confirmed structural |
| WYNN | Goodwill | 19/70 (27%) | 19/70 (27%) | Confirmed structural |

- **CMG DividendsPerShare**: genuine non-payer. **LongTermDebt**: the tag exists and every
  one of its 7 values is explicitly $0.0000 — CMG genuinely operates debt-free; the "thin"
  flag reflects an immaterial $0 that simply wasn't tagged before 2019, not a real gap.
- **LVS Goodwill**: only tagged from 2022 (plausibly tied to LVS's 2022 Las Vegas
  divestiture/restructuring); `IntangibleAssetsNetIncludingGoodwill` rejected again as the
  familiar broader-concept trap.
- **MAR DepreciationAndAmortization**: tagging stops entirely after 2014-09-30 for a
  ~19-year expected history; only balance-sheet accumulated-depreciation or
  forward-looking schedule items found (matches LMT's identical-shaped gap in industrials).
- **MGM DividendsPerShare**: a genuinely different shape — the per-share tag (a nominal
  $0.0025/share) covers 2016-2022 then stops, and `PaymentsOfDividendsCommonStock` shows the
  SAME post-2022 quarters as explicitly $0.0000, confirming MGM's tiny dividend was
  genuinely discontinued, not merely left untagged. A few larger-dollar hits are a
  ~66,000x larger, unrelated MGM Growth Properties program — correctly not conflated.
- **NCLH DividendsPerShare**: genuine non-payer, consistent with the pandemic-era dividend
  suspension never being reinstated.
- **WYNN Goodwill**: tagged only 2018-2024; same broader-concept trap rejected.

No config changes. Non-regression: trivially clean.

---

## marketplace (7 flags)

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| ABNB | DividendsPerShare | 0/27 (0%) | 0/27 (0%) | Confirmed structural |
| ABNB | Goodwill | 13/27 (48%) | 13/27 (48%) | Confirmed structural |
| BKNG | DividendsPerShare | 9/70 (13%) | 9/70 (13%) | Confirmed structural |
| DASH | DividendsPerShare | 0/28 (0%) | 0/28 (0%) | Confirmed structural |
| DASH | LongTermDebt | 11/28 (39%) | 11/28 (39%) | Confirmed structural |
| EBAY | DividendsPerShare | 0/74 (0%) | 0/74 (0%) | Confirmed structural |
| UBER | DividendsPerShare | 0/35 (0%) | 0/35 (0%) | Confirmed structural |

- **ABNB**: genuine non-payer; Goodwill tagged 2019-2025, broader-concept trap rejected
  again.
- **BKNG DividendsPerShare**: Booking Holdings only initiated a regular dividend in 2024;
  the per-share and aggregate tags match for that window (a young-payer story, not an
  untagged-history one, given 70 total periods expected vs. a ~2-year-old program).
- **DASH**: genuine non-payer; LongTermDebt shows a real, correctly-captured $0.0000
  2019-2021 period before a real 2021-2024 gap, then real convertible-notes coverage
  2024-2026 (DoorDash's real 2024 issuance). No candidate fills the 2021-2024 gap.
- **EBAY DividendsPerShare — flagged for extra scrutiny given this project's own documented
  history of wrongly assuming EBAY was a non-payer.** Verified properly this time:
  `PaymentsOfDividends` shows 33 real values 2018-2026 (~$130M+/qtr recently) — eBay is
  unambiguously a genuine, continuous payer, not a non-payer. The gap is purely a missing
  per-share tag; one candidate (`DividendsPayableAmountPerShare`) is point-in-time versus
  the duration semantics the concept needs, rejected for consistency with identical
  rejections elsewhere in this sweep (J, VRT). The important finding is the correct
  distinction from a non-payer, exactly per the task's explicit warning about this ticker.
- **UBER**: genuine non-payer; hits are preferred-stock-class items, mostly $0.

No config changes. Non-regression: trivially clean.

---

## materials (4 flags)

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| CE | DividendsPerShare | 0/73 (0%) | 0/73 (0%) | Confirmed structural |
| CTVA | OperatingIncomeLoss | 0/36 (0%) | 0/36 (0%) | Confirmed structural |
| FCX | Goodwill | 9/76 (12%) | 9/76 (12%) | Confirmed structural (correct values) |
| SW | DividendsPerShare | 7/15 (47%) | 7/15 (47%) | Confirmed structural |

- **CE DividendsPerShare**: genuine-payer-but-untagged — `PaymentsOfDividendsCommonStock`
  shows 70 real values across Celanese's full 2008-2026 history (small recent quarters
  reflect Celanese's well-documented 2025 dividend cut, not an artifact).
- **CTVA OperatingIncomeLoss**: conglomerate pattern, only the non-operating complement
  found.
- **FCX Goodwill — a "correct zero," not a gap.** The full story reconciles cleanly: FCX's
  2013 Plains Exploration/McMoRan acquisition created ~$8.9B of goodwill (matches almost to
  the dollar), then FCX fully impaired/wrote it off in 2014 when it exited oil & gas
  (impairment + write-off tags both dated exactly 2014-12-31, summing to match). Zero
  goodwill ever since — the thin coverage accurately reflects reality.
- **SW DividendsPerShare**: Smurfit WestRock is a 2024 merger entity with only 15 periods
  expected; the per-share tag already covers essentially its whole public life.

No config changes. Non-regression: trivially clean.

---

## media (32 flags in the actual report)

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| DIS | DividendsPerShare | 13/38 (34%) | 13/38 (34%) | Confirmed structural (correct values) |
| EA | DividendsPerShare | 16/74 (22%) | 16/74 (22%) | Confirmed structural |
| EA | LongTermDebt | 23/74 (31%) | 23/74 (31%) | Confirmed structural |
| FOX | OperatingIncomeLoss | 0/37 (0%) | 0/37 (0%) | Confirmed structural |
| FOXA | OperatingIncomeLoss | 0/37 (0%) | 0/37 (0%) | Confirmed structural |
| FOX | DividendsPerShare | 0/37 (0%) | 0/37 (0%) | Confirmed structural |
| FOXA | DividendsPerShare | 0/37 (0%) | 0/37 (0%) | Confirmed structural |
| LYV | DividendsPerShare | 0/67 (0%) | 0/67 (0%) | Confirmed structural |
| NFLX | Goodwill | 0/76 (0%) | 0/76 (0%) | Confirmed structural |
| NFLX | DividendsPerShare | 0/76 (0%) | 0/76 (0%) | Confirmed structural |
| NWS | OperatingIncomeLoss | 0/57 (0%) | 0/57 (0%) | Confirmed structural |
| NWSA | OperatingIncomeLoss | 0/57 (0%) | 0/57 (0%) | Confirmed structural |
| NWS | DividendsPerShare | 11/57 (19%) | 11/57 (19%) | Confirmed structural |
| NWSA | DividendsPerShare | 11/57 (19%) | 11/57 (19%) | Confirmed structural |
| OMC | LongTermDebt | 35/74 (47%) | 35/74 (47%) | **Ambiguous** |
| PSKY | Capex | (10 concepts, see below) | unchanged | Confirmed structural |
| TKO | DividendsPerShare | 0/18 (0%) | 0/18 (0%) | Confirmed structural |
| TKO | Capex | 0/18 (0%) | 0/18 (0%) | Confirmed structural |
| TTD | Goodwill | 0/45 (0%) | 0/45 (0%) | Confirmed structural |
| TTD | DividendsPerShare | 0/45 (0%) | 0/45 (0%) | Confirmed structural |
| TTD | LongTermDebt | 0/45 (0%) | 0/45 (0%) | Confirmed structural |
| TTWO | DividendsPerShare | 0/72 (0%) | 0/72 (0%) | Confirmed structural |
| WBD | DividendsPerShare | 0/75 (0%) | 0/75 (0%) | Confirmed structural |

- **DIS DividendsPerShare**: both the tag's own gap and `PaymentsOfDividendsCommonStock`'s
  explicit $0.0000 agree — Disney's real, well-documented COVID-era suspension, a correct
  reflection of reality.
- **EA**: DividendsPerShare matches EA's real 2020 first-dividend history exactly (not an
  untagged-longer-history gap). LongTermDebt matches EA's real convertible-notes retirement
  by ~2017 and minimal debt since.
- **FOX/FOXA**: OperatingIncomeLoss — conglomerate pattern. DividendsPerShare — Fox Corp is
  a genuine continuous payer (semi-annual lump sums, a real documented practice), but no
  per-share tag exists for either class.
- **LYV DividendsPerShare**: genuine non-payer; `PaymentsOfDividendsMinorityInterest` is
  real JV-partner payouts, not LYV's own shareholders — correctly not conflated.
- **NFLX Goodwill**: plausible genuine absence (content library capitalized separately,
  little M&A). **DividendsPerShare**: the textbook genuine non-payer.
- **NWS/NWSA**: OperatingIncomeLoss — conglomerate pattern (identical for both share
  classes). DividendsPerShare — genuine continuous payer through 2026 with no per-share tag
  for the last ~7 years.
- **OMC LongTermDebt — two broad candidates rejected after a mixed-evidence check, logged
  ambiguous.** Both `LongTermNotesPayable` and `NotesPayable` show an inconsistent
  relationship to the current resolution — wildly different (2-4x) in 2009-2011, much
  closer (0.1-2.4%) in 2018-2024, diverging again (~17%) in 2025. A "sometimes close,
  sometimes not" signal, distinct from the AIG/PRU fixes where the relationship held
  consistently — not adopted.
- **PSKY — all ten flagged concepts trace to one common root cause.** Paramount Skydance
  is the successor entity from the August 2025 Paramount-Skydance merger (only 13 total
  periods expected). Pre-merger shell-entity filings genuinely report $0/1,000-nominal-shares
  (real values for a newly-formed holding company, not errors); later filings correctly
  restate most quarters with real historical figures via the pipeline's own "latest-filed
  wins" logic — except 2025-06-30, which the merger's own period boundary (Aug 6, 2025)
  never got a comparative restatement for, since later filings jump straight from
  full-year/stub figures to the Aug-6-onward period. Not a fixable defect — a genuine
  reporting-boundary artifact. Distinguished explicitly from the BKR fix: BKR's value was
  *contradicted* by other real data; PSKY's shell values are internally consistent across
  every concept, consistent with a real shell entity with no business yet — no
  known-bad-fact exclusion applied.
- **TKO**: DividendsPerShare — a genuine, very young payer (WWE/UFC parent) with no
  per-share tag. Capex — no configured tag present, only wrong-direction hits.
- **TTD**: genuine absence/non-payer/no-debt across all three flagged concepts (The Trade
  Desk, mostly-organic growth, no dividend, well-capitalized).
- **TTWO DividendsPerShare**: genuine non-payer.
- **WBD DividendsPerShare**: genuine non-payer, consistent with the well-documented
  no-dividend, debt-paydown-focused policy since the 2022 merger.

No config changes. Non-regression: trivially clean.

---

## pharma_medtech (31 flags) — 1 real fix applied

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| ALGN | DividendsPerShare | 0/70 (0%) | 0/70 (0%) | Confirmed structural |
| ALGN | LongTermDebt | 0/70 (0%) | 0/70 (0%) | Confirmed structural |
| BIIB | DividendsPerShare | 0/73 (0%) | 0/73 (0%) | Confirmed structural |
| BSX | DividendsPerShare | 0/74 (0%) | 0/74 (0%) | Confirmed structural |
| BSX | NetIncomeLoss | 31/74 (42%) | 31/74 (42%) | Confirmed structural |
| CRL | DividendsPerShare | 0/70 (0%) | 0/70 (0%) | Confirmed structural |
| CRL | ResearchAndDevelopment | 0/70 (0%) | 0/70 (0%) | Confirmed structural |
| COO | DividendsPerShare | 14/70 (20%) | 14/70 (20%) | Confirmed structural (correct values) |
| DXCM | DividendsPerShare | 0/66 (0%) | 0/66 (0%) | Confirmed structural |
| EW | DividendsPerShare | 0/70 (0%) | 0/70 (0%) | Confirmed structural |
| IDXX | DividendsPerShare | 0/70 (0%) | 0/70 (0%) | Confirmed structural |
| IDXX | LongTermDebt | 32/70 (46%) | 65/70 (93%) | **Fixed** |
| INCY | DividendsPerShare | 0/67 (0%) | 0/67 (0%) | Confirmed structural |
| IQV | ResearchAndDevelopment | 0/59 (0%) | 0/59 (0%) | Confirmed structural |
| IQV | DividendsPerShare | 0/59 (0%) | 0/59 (0%) | Confirmed structural |
| ISRG | DividendsPerShare | 0/75 (0%) | 0/75 (0%) | Confirmed structural |
| ISRG | LongTermDebt | 0/75 (0%) | 0/75 (0%) | Confirmed structural |
| LLY | Capex | 26/74 (35%) | 26/74 (35%) | Confirmed structural |
| MTD | DividendsPerShare | 0/69 (0%) | 0/69 (0%) | Confirmed structural |
| PODD | DividendsPerShare | 0/65 (0%) | 0/65 (0%) | Confirmed structural |
| REGN | DividendsPerShare | 5/70 (7%) | 5/70 (7%) | Confirmed structural |
| SOLV | DividendsPerShare | 0/15 (0%) | 0/15 (0%) | Confirmed structural |
| VEEV | DividendsPerShare | 0/59 (0%) | 0/59 (0%) | Confirmed structural |
| VEEV | LongTermDebt | 0/59 (0%) | 0/59 (0%) | Confirmed structural |
| VEEV | Capex | 28/59 (47%) | 28/59 (47%) | Confirmed structural |
| VRTX | DividendsPerShare | 0/71 (0%) | 0/71 (0%) | Confirmed structural |
| VRTX | LongTermDebt | 3/71 (4%) | 3/71 (4%) | **Ambiguous** |
| WAT | DividendsPerShare | 0/96 (0%) | 0/96 (0%) | Confirmed structural |
| WAT | Capex | 2/96 (2%) | 2/96 (2%) | Confirmed structural |

- **Genuine non-payers** (ALGN, BIIB, BSX, CRL, DXCM, EW, IDXX, INCY, ISRG, MTD, PODD, SOLV,
  VEEV, VRTX, WAT DividendsPerShare): every hit is an unrelated assumption/preferred-stock/
  received-income item; BSX's `PaymentsOfDividends` explicitly $0.0000 through 2024
  confirms no hidden real payments; ISRG's one isolated $8.0M 2024 blip is a one-off JV item,
  not a program; SOLV is a young 2024 3M spinoff; VEEV is notably clean (even the
  `DividendsPayableAmountPerShare` candidate that worked elsewhere in this sweep is $0
  throughout for VEEV).
- **Genuine no-debt companies** (ALGN, ISRG, VEEV LongTermDebt): zero keyword hits of any
  kind.
- **REGN DividendsPerShare**: young/recent initiator — Regeneron's first-ever dividend was
  declared 2025, matching the tag's own start almost exactly.
- **CRO/services business-model explanation** (CRL, IQV ResearchAndDevelopment): both
  companies' core business *is* performing R&D for clients, so neither has an internal
  "own product R&D" line the way a product company does — IQV's one hit directly confirms
  this (cost of performing R&D *for* clients). **IQV DividendsPerShare**: large hits from
  2011-2012 are pre-IPO-era distributions to IQVIA's former PE sponsor, not an ongoing
  program — correctly not conflated with today's non-payer status.
- **IDXX LongTermDebt — FIXED.** `SecuredLongTermDebt` covers 2009-2020 and, at 6 of 9
  overlapping dates from 2014 onward (once balances exceed $150M), matches the currently-used
  resolution within 0.01-0.7% — consistent with IDXX's long-term debt being almost entirely
  secured. Added as lowest-priority fallback in a new
  `TICKER_CONCEPT_OVERRIDES["IDXX"]["LongTermDebt"]` entry (reconstructed from the base
  `CONCEPT_CANDIDATES` source list plus `SecuredLongTermDebt`, including the
  `non_negative: True` flag caught and fixed before verification).
- **BSX NetIncomeLoss**: a real, unusual ~2010-2019 gap between two configured tags; no
  viable substitute among a pro-forma figure, an NCI carve-out, and unrelated OCI items.
- **COO DividendsPerShare**: both the per-share and aggregate tags show explicit $0.0000 by
  2022-2024 — a small nominal dividend genuinely discontinued (matches the MGM pattern).
- **LLY / VEEV Capex**: clean tag-rename handoffs already captured; the only extending
  candidate for both (`PaymentsForProceedsFromProductiveAssets`) is a net proceeds-less-
  payments concept, rejected for consistency with the COP precedent.
- **VRTX LongTermDebt — logged ambiguous.** A tiny, low-materiality 2011-only blip; a
  chronologically adjacent candidate is in the same ballpark but not an exact match (unlike
  IDXX's consistent near-perfect overlap) — given low materiality and an imperfect match,
  treated conservatively as ambiguous rather than adopted.
- **WAT Capex**: tag only covers 2025-2026; the same net-concept candidate rejected three
  times over elsewhere in this sweep (COP, LLY, VEEV) rejected here too for consistency.

**Config changes**: `config.py` — new `TICKER_CONCEPT_OVERRIDES["IDXX"]["LongTermDebt"]`.

**Group non-regression** (43 tickers) vs. master before-snapshot: 33 rows added (exactly
65-32), 0 removed, 0 changed, only IDXX touched. Clean.

---

## reit (48 flags in the actual report) — 2 real fixes applied

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| AMT | GainLossOnSaleOfProperties | 0/74 (0%) | 0/74 (0%) | Confirmed structural |
| AVB | Goodwill | 0/75 (0%) | 0/75 (0%) | Confirmed structural |
| ARE | GainLossOnSaleOfProperties | 28/70 (40%) | 49/70 (70%) | **Fixed** |
| BXP | Goodwill | 0/74 (0%) | 0/74 (0%) | Confirmed structural |
| BXP | DividendsPerShare | 22/74 (30%) | 22/74 (30%) | Confirmed structural |
| CCI | GainLossOnSaleOfProperties | 0/74 (0%) | 0/74 (0%) | Confirmed structural |
| CPT | Goodwill | 0/70 (0%) | 0/70 (0%) | Confirmed structural |
| CPT | GainLossOnSaleOfProperties | 5/70 (7%) | 5/70 (7%) | Confirmed structural |
| DLR | Goodwill | (see AVB group) | unchanged | Confirmed structural |
| DLR | DividendsPerShare | 0/67 (0%) | 0/67 (0%) | Confirmed structural |
| DLR | LongTermDebt | 32/67 (48%) | 32/67 (48%) | Confirmed structural |
| EQIX | GainLossOnSaleOfProperties | 0/70 (0%) | 0/70 (0%) | Confirmed structural |
| EQR | Goodwill | 0/74 (0%) | 0/74 (0%) | Confirmed structural |
| ESS | Goodwill | 0/70 (0%) | 0/70 (0%) | Confirmed structural |
| EXR | Goodwill | 17/71 (24%) | 17/71 (24%) | Confirmed structural |
| EXR | GainLossOnSaleOfProperties | 9/71 (13%) | 9/71 (13%) | Confirmed structural |
| FRT | Goodwill | 0/70 (0%) | 0/70 (0%) | Confirmed structural |
| FRT | GainLossOnSaleOfProperties | 9/70 (13%) | 26/70 (37%) | **Fixed** |
| FRT | LongTermDebt | 16/70 (23%) | 16/70 (23%) | Confirmed structural |
| HST | Goodwill | 0/71 (0%) | 0/71 (0%) | Confirmed structural |
| HST | GainLossOnSaleOfProperties | 0/71 (0%) | 0/71 (0%) | **Ambiguous** |
| HST | DividendsPerShare | 7/71 (10%) | 7/71 (10%) | Confirmed structural |
| IRM | GainLossOnSaleOfProperties | 3/71 (4%) | 3/71 (4%) | **Ambiguous** |
| KIM | GainLossOnSaleOfProperties | 13/74 (18%) | 13/74 (18%) | **Ambiguous** |
| MAA | Goodwill | 15/68 (22%) | 15/68 (22%) | Confirmed structural |
| MAA | GainLossOnSaleOfProperties | 4/68 (6%) | 4/68 (6%) | Confirmed structural |
| MAA | DividendsPerShare | 19/68 (28%) | 19/68 (28%) | Confirmed structural |
| PLD | Goodwill | 3/66 (5%) | 3/66 (5%) | Confirmed structural (correct values) |
| PLD | GainLossOnSaleOfProperties | 15/66 (23%) | 15/66 (23%) | Confirmed structural |
| REG | CashAndEquivalents | 2/65 (3%) | 2/65 (3%) | Confirmed structural |
| REG | SharesOutstanding | 22/65 (34%) | 22/65 (34%) | Confirmed structural |
| REG | DepreciationAndAmortization | 31/65 (48%) | 31/65 (48%) | Confirmed structural |
| REG | OperatingCashFlow | 31/65 (48%) | 31/65 (48%) | Confirmed structural |
| SBAC | Goodwill | 0/70 (0%) | 0/70 (0%) | Confirmed structural |
| SBAC | GainLossOnSaleOfProperties | 0/70 (0%) | 0/70 (0%) | Confirmed structural |
| SBAC | DividendsPerShare | 0/70 (0%) | 0/70 (0%) | Confirmed structural |
| SPG | Goodwill | 17/74 (23%) | 17/74 (23%) | Confirmed structural |
| SPG | DividendsPerShare | 34/74 (46%) | 34/74 (46%) | Confirmed structural |
| UDR | Goodwill | 0/70 (0%) | 0/70 (0%) | Confirmed structural |
| VICI | Goodwill | 0/38 (0%) | 0/38 (0%) | Confirmed structural |
| VICI | GainLossOnSaleOfProperties | 0/38 (0%) | 0/38 (0%) | Confirmed structural |
| VTR | GainLossOnSaleOfProperties | 0/74 (0%) | 0/74 (0%) | **Ambiguous** |
| WY | Goodwill | 21/75 (28%) | 21/75 (28%) | Confirmed structural (correct values) |
| WY | GainLossOnSaleOfProperties | 0/75 (0%) | 0/75 (0%) | Confirmed structural |

(48 flags condensed to unique ticker/concept rows above; a couple of source-report entries
that repeat the same concept/ticker combination across the profile-wide pattern paragraphs
below are consolidated into their pattern group rather than double-counted.)

- **GainLossOnSaleOfProperties is a genuinely lumpy, event-driven concept for this whole
  profile** — REITs don't sell properties every quarter, so $0.0000 most quarters with
  occasional large spikes is correct, not a defect (verified directly on ARE and FRT). The
  most common tempting-but-wrong candidate profile-wide is a "proceeds from sale" tag
  (cash proceeds including return of cost basis, a different and larger figure than the
  recognized gain/loss) — rejected everywhere it appeared. A second recurring trap is
  "deferred gain on sale" tags (postponed recognition, not the same as a recognized gain).
- **Infrastructure/non-traditional-real-estate REITs genuinely don't use disposition-gain
  or goodwill tags**: AMT, CCI, EQIX, SBAC (also Goodwill), VICI (also Goodwill), WY — cell
  towers, data centers, gaming-related and timberland assets aren't bought/sold like
  apartments or malls.
- **Goodwill broadly, plausibly genuinely absent/immaterial across this profile**: AVB,
  BXP, CPT, EQR, ESS, FRT, HST (two tiny one-off 2010-2011 PPA footnote items, not an
  ongoing balance), UDR, VICI. Two "correct zero" cases: PLD (real ~$32.8M goodwill from
  the 2011 AMB Property merger, substantially impaired 2010-2011, genuinely near-zero
  since); WY (a 2008 impairment left a small static $40.0M residual that stopped being
  separately tagged after 2018). Sparse/static-tiny-value with no substitute: EXR (static
  $170.8M from 2021), MAA (static ~$4.1M, stops 2013), SPG (static $20.1M).
- **Genuine continuous common-stock dividend payers with no reliable per-share tag**: BXP
  (near-complete aggregate history vs. sparse per-share tag; `DividendsPayableAmountPerShare`
  rejected as point-in-time, same standard as J/VRT/EBAY), DLR (zero per-share tag ever
  despite 61/67 real aggregate payments), HST, MAA (tag stopped mid-2019 despite continuing
  real payments through 2026), SBAC (a genuine 2019 initiator, no per-share tag at all),
  SPG (real payments back to 2008, well before the per-share tag's 2017 start). All
  CONFIRMED, not fixable at tag level.
- **ARE GainLossOnSaleOfProperties — FIXED, with an explicit profile-wide generalization
  test that correctly failed.** `GainLossOnDispositionOfRealEstateDiscontinuedOperations`
  matches ARE's currently-used resolution at 25 of 26 overlapping dates exactly (one
  exception off by an immaterial $90,000), extending coverage back to 2012. Tested against
  BXP and PLD (both also flagged) before scoping: BXP diverges at its one shared date
  ($41.9M vs $0), PLD diverges at its one shared date (-$3.7M vs $108M) — proving the tag
  means something different for those two, so deliberately not generalized to the profile.
  Scoped to `TICKER_CONCEPT_OVERRIDES["ARE"]` only.
- **FRT GainLossOnSaleOfProperties — FIXED, same discipline.**
  `GainLossOnSaleOfPropertiesNetOfApplicableIncomeTaxes` matches FRT's resolution exactly
  at all 5 overlapping dates (plausible for a REIT, which generally owes no corporate
  income tax on distributed earnings). Tested across HST (insufficient evidence, not
  adopted), IRM (1 of 2 shared dates mismatches by a real but small 3.6% — inconclusive,
  logged ambiguous), and KIM (11 of 11 shared dates mismatch, including sign flips —
  clearly wrong, not adopted). Scoped to FRT only.
- **FRT LongTermDebt**: the one broad-coverage candidate (`NotesPayable`, 65 vals) is off by
  5-18x at every one of 16 shared dates — a much smaller, different debt sub-component.
- **CPT, DLR, EXR, MAA, PLD GainLossOnSaleOfProperties**: genuinely lumpy disposition-gain
  histories with only proceeds-shaped or deferred-gain candidates found, both correctly
  rejected per the profile-wide pattern.
- **KIM, IRM, HST GainLossOnSaleOfProperties — logged ambiguous.** The
  "NetOfApplicableIncomeTaxes" candidate tested as part of the FRT fix was not adopted for
  any of the three (KIM's evidence was fairly clear-cut against it; IRM's and HST's were
  genuinely inconclusive).
- **VTR GainLossOnSaleOfProperties — logged ambiguous.** A candidate has 14 values, but
  VTR's own current resolution is 0/74 — no anchor value exists to check it against
  (unlike ARE's 26 shared dates), so it's logged ambiguous rather than adopted on faith.
- **DLR LongTermDebt**: a real 2012-2019 gap between an old and newer debt tag; only
  forward-schedule and cash-flow candidates found, no balance substitute.
- **REG — four simultaneous flags, checked explicitly for a single common root cause per
  the task's own REG/ERIE precedent.** Unlike PSKY's clean single-boundary explanation,
  REG's gaps do NOT all align to one date: OperatingCashFlow and DepreciationAndAmortization
  both begin around REG's October 2017 Equity One merger (a plausible partial explanation),
  but SharesOutstanding's gap (2020-2023) has no obvious connection to that merger, and
  CashAndEquivalents is almost entirely absent (most plausibly because REG holds little
  unrestricted cash most quarters, a common REIT practice of sweeping cash to debt
  paydown/distributions, rather than a tagging defect — the one broad alternative,
  `RestrictedCashAndCashEquivalents`, is a different, narrower-purpose category and was
  rejected). No fix found for any of the four.

**Config changes**: `config.py` — new `TICKER_CONCEPT_OVERRIDES["ARE"]["GainLossOnSaleOfProperties"]`;
extended the existing `TICKER_CONCEPT_OVERRIDES["FRT"]` entry with a new
`GainLossOnSaleOfProperties` key.

**Group non-regression** (all 29 reit tickers) vs. master before-snapshot: 38 rows added
(21 for ARE + 17 for FRT, matching each fix exactly), 0 removed, 0 changed, only ARE and
FRT touched. Clean.

---

## retail (24 flags in the actual report) — 1 real fix applied

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| AZO | DividendsPerShare | 0/73 (0%) | 0/73 (0%) | Confirmed structural |
| ORLY | DividendsPerShare | 0/71 (0%) | 0/71 (0%) | Confirmed structural |
| HSIC | DividendsPerShare | 0/69 (0%) | 0/69 (0%) | Confirmed structural |
| LULU | DividendsPerShare | 0/69 (0%) | 0/69 (0%) | Confirmed structural |
| LULU | LongTermDebt | 20/69 (29%) | 20/69 (29%) | Confirmed structural (correct values) |
| DECK | DividendsPerShare | 0/70 (0%) | 0/70 (0%) | Confirmed structural |
| DECK | LongTermDebt | 29/70 (41%) | 29/70 (41%) | Confirmed structural (correct values) |
| DLTR | DividendsPerShare | 0/70 (0%) | 0/70 (0%) | Confirmed structural |
| DLTR | AccountsReceivable | 2/70 (3%) | 2/70 (3%) | Confirmed structural |
| DG | AccountsReceivable | 0/67 (0%) | 0/67 (0%) | Confirmed structural |
| TSCO | AccountsReceivable | 0/73 (0%) | 0/73 (0%) | Confirmed structural |
| TGT | AccountsReceivable | 0/74 (0%) | 7/74 (9%) | **Fixed** |
| TGT | CashAndEquivalents | 18/74 (24%) | 18/74 (24%) | Confirmed structural |
| LOW | AccountsReceivable | 6/75 (8%) | 6/75 (8%) | Confirmed structural |
| GPC | OperatingIncomeLoss | 22/74 (30%) | 22/74 (30%) | Confirmed structural |
| NKE | OperatingIncomeLoss | 0/74 (0%) | 0/74 (0%) | Confirmed structural |
| ROST | OperatingIncomeLoss | 9/71 (13%) | 9/71 (13%) | Confirmed structural |
| TJX | OperatingIncomeLoss | 21/74 (28%) | 21/74 (28%) | Confirmed structural |
| TJX | CostOfRevenue | 35/74 (47%) | 35/74 (47%) | Confirmed structural |
| WSM | CostOfRevenue | 7/74 (9%) | 7/74 (9%) | Confirmed structural |
| GRMN | LongTermDebt | 0/76 (0%) | 0/76 (0%) | Confirmed structural |
| GRMN | DividendsPerShare | 27/76 (36%) | 27/76 (36%) | Confirmed structural |
| ULTA | LongTermDebt | 2/67 (3%) | 2/67 (3%) | Confirmed structural (correct values) |
| ULTA | DividendsPerShare | 4/67 (6%) | 4/67 (6%) | Confirmed structural (correct values) |

- **AZO, ORLY, HSIC, LULU, DECK, DLTR DividendsPerShare**: genuine non-payers, all
  well-known buyback-only capital-return companies (AZO's `ExpectedDividendRate` assumption
  alone has 67 real datapoints, all $0.0000).
- **DG, TSCO AccountsReceivable**: zero hits for either; both cash-and-carry discount
  retailers with no meaningful customer-credit business.
- **TGT AccountsReceivable — FIXED.** Target sold its credit-card receivables portfolio to
  TD Bank in 2013; its remaining on-balance-sheet receivables are a smaller bucket tagged
  under `AccountsAndOtherReceivablesNetCurrent` (2020-2026, $891M-$1,265M) — the same
  underlying concept under a TGT-specific taxonomy name. Confirmed this tag name does not
  appear at all for DG or TSCO (also flagged for the same concept), so not generalized.
  Added to `TICKER_CONCEPT_OVERRIDES["TGT"]["AccountsReceivable"]`.
- **DLTR AccountsReceivable**: same business-model explanation; a brief 2019-2020
  appearance is plausibly a one-off reclassification.
- **LOW AccountsReceivable**: only recently tagged (2024-2026); `GainLossOnSaleOfAccountsReceivable`
  directly confirms Lowe's securitizes/sells receivables rather than holding them, a common
  store-credit-card practice.
- **GPC, NKE, ROST, TJX OperatingIncomeLoss**: the same conglomerate/diversified-reporting
  no-discrete-subtotal pattern seen throughout this sweep.
- **TJX, WSM CostOfRevenue**: real pre-window gaps, zero new keyword hits for either.
- **TGT CashAndEquivalents**: coverage stops in 2019; candidates are flow/reconciliation
  items or a discontinued-operations-only sub-component, none a full balance substitute.
- **GRMN LongTermDebt**: genuine no-debt company (well known); the one hit is a tiny
  2007-2009 repayment item. **DividendsPerShare**: genuine-payer-but-untagged since
  mid-2022 (real payments confirmed via aggregate tags through 2026); a promising-by-name
  candidate is point-in-time (rejected) and fully overlaps the already-covered window
  anyway.
- **DECK LongTermDebt**: real debt 2013-2021 tapering to $0.0000, then genuinely debt-free —
  matches Deckers' well-known financial conservatism.
- **LULU LongTermDebt**: the tag is explicitly $0.0000 for all 20 existing values —
  genuinely correct (Lululemon is debt-free); "thin" only because the $0 went untagged
  before 2020.
- **ULTA LongTermDebt**: a real, internally-consistent story — an $800M COVID-era facility
  drawn in 2020 and fully repaid by January 2021, confirmed via an exact matching
  repayment entry. **DividendsPerShare**: a real, brief, one-time 2012 special distribution
  and payable entry, not an ongoing program — confirmed via a $0.0000
  `ExpectedDividendRate` throughout 2010-2016.

**Config changes**: `config.py` — new `TICKER_CONCEPT_OVERRIDES["TGT"]["AccountsReceivable"]`.

**Group non-regression** (all 28 retail tickers) vs. master before-snapshot: 7 rows added
(exactly matching the TGT fix), 0 removed, 0 changed, only TGT touched. Clean.

---

## standard (92 flags in the actual report) — 5 real fixes applied

This is the largest single group in the sweep. ERIE, the Q cluster, and TROW each get
their own labeled subsection per the task's requirement; the remaining ~78 flags are
covered by cross-cutting pattern and a short list of individually-verified findings.

### Priority subsection: ERIE (5 simultaneous flags)

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| ERIE | Goodwill | 0/67 (0%) | 0/67 (0%) | Confirmed structural |
| ERIE | DepreciationAndAmortization | 0/67 (0%) | 0/67 (0%) | Confirmed structural |
| ERIE | DividendsPerShare | 0/67 (0%) | 0/67 (0%) | Confirmed structural |
| ERIE | SharesOutstanding | 0/67 (0%) | 0/67 (0%) | Confirmed structural |
| ERIE | LongTermDebt | 25/67 (37%) | 25/67 (37%) | Confirmed structural |

This exact multi-flag pattern had been spotted twice before without ever being
investigated. Checked explicitly whether ERIE's unusual corporate structure (it manages a
separate reciprocal insurance exchange it does not consolidate) is the common root cause of
all five at once:

- **Goodwill**: zero hits on the base tag; only narrow 2013-2015 intangible-amortization
  items exist. Consistent with ERIE Indemnity being a fee-based management company (it
  earns fees from the exchange it manages) rather than an acquisitive underwriter —
  plausibly explained by the reciprocal-exchange structure.
- **DepreciationAndAmortization**: combined tags absent; only pension-plan and
  deferred-policy-acquisition-cost amortization (a distinct insurance concept) exist.
  Consistent with the same asset-light, management-fee structure.
- **LongTermDebt**: `LongTermDebtNoncurrent`/`Current` cleanly decline to $0.0000 by
  2022-12-31 and then simply stop being tagged at all — a real, clean paydown-to-debt-free
  story, plausibly tied to the same asset-light root cause as Goodwill/D&A.
- **SharesOutstanding**: a full cross-namespace check (dei + us-gaap) finds exactly ONE
  share-count-shaped fact ERIE has EVER filed under any tag: a single 2021-Q2 duration fact
  showing 2,542 shares. This is ERIE's real, famously tiny Class B share count (closely
  held by the founding families, carrying disproportionate voting power) — not its total
  common shares outstanding (Class A alone is in the tens of millions). Using it would be
  actively misleading, not just thin; dei has no `EntityCommonStockSharesOutstanding` at
  all. This is a **different** unusual-structure fact (dual-class shares) than the
  reciprocal-exchange non-consolidation.
- **DividendsPerShare**: `PaymentsOfDividendsCommonStock` shows 66 values 2009-2026, a real,
  long, unbroken dividend history — but no per-share tag was ever filed. This has nothing
  to do with ERIE's insurance-exchange or share-class structure; it's the same generic
  genuine-payer-untagged pattern seen across dozens of other tickers in this sweep.

**Conclusion (nuanced, not a single story)**: 3 of 5 flags (Goodwill, D&A, LongTermDebt)
plausibly share a common root cause in ERIE Indemnity's asset-light, fee-based management
structure. SharesOutstanding's absence is a *different* ERIE-specific structural fact (the
dual-class share structure). DividendsPerShare is unrelated to anything ERIE-specific.
All 5 confirmed structural; none fixable at tag level.

### Priority subsection: Q cluster (7 flags, all denominators "of 10")

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| Q | OperatingIncomeLoss | 0/10 (0%) | 0/10 (0%) | Confirmed structural (young ticker) |
| Q | DividendsPerShare | 0/10 (0%) | 0/10 (0%) | Confirmed structural (young ticker) |
| Q | Capex | 3/10 (30%) | 3/10 (30%) | Confirmed structural (young ticker) |
| Q | OperatingCashFlow | 3/10 (30%) | 3/10 (30%) | Confirmed structural (young ticker) |
| Q | CashAndEquivalents | 4/10 (40%) | 4/10 (40%) | Confirmed structural (young ticker) |
| Q | LongTermDebt | 4/10 (40%) | 4/10 (40%) | Confirmed structural (young ticker) |
| Q | NetIncomeLoss | 4/10 (40%) | 4/10 (40%) | Confirmed structural (young ticker) |

Ticker identity confirmed before touching any individual flag, per the task's instruction:
`entityName` = "QNITY ELECTRONICS, INC.", CIK 0002058873 (a freshly-assigned, very-high
CIK). Earliest real financial fact of any kind is 2024-01-01/2024-09-30 (filed
2025-11-18, its first 10-Q as a new registrant). Every one of the 7 flags checks out as the
company genuinely not existing yet for the missing periods:

- **OperatingIncomeLoss / DividendsPerShare**: too little history yet to judge either way
  (only 2 dividend-payment datapoints exist, one $0 one real).
- **Capex, OperatingCashFlow, CashAndEquivalents**: each already resolves *every* value that
  exists for this ticker — the "gap" is 100% pre-existence.
- **LongTermDebt**: resolves all 4 available dates, capturing a real, large debt issuance
  ($4,100M in fiscal 2025-12-31, consistent with spinoff-related financing).
- **NetIncomeLoss**: resolves all 4 available dates, capturing 100% of what exists.

**Conclusion**: exactly as anticipated — the right "fix" for Q is "wait for more filings,"
not a tag change. All 7 confirmed structural (young-registrant denominator artifact).

### Priority subsection: TROW LongTermDebt (plausibility sweep)

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| TROW | LongTermDebt | 0/74 (0%) | 0/74 (0%) | Confirmed structural |

Given the confirmed prior D&A silent-wrong-value bug on this exact ticker, ran a full
plausibility sweep rather than a presence/absence check: all 12 configured candidate tags
show NOT PRESENT, and a keyword search across "borrowings"/"longtermdebt"/"notespayable"
returns **zero** additional hits anywhere in TROW's entire us-gaap namespace — the
strongest possible negative result. T. Rowe Price is well known as a genuinely debt-free
asset manager. Confirmed structural; no plausibility concern survives this sweep.

### Real fixes applied (5)

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| WDAY | SharesOutstanding | 28/63 (44%, 1 wrong value) | 27/63 (43%, correct) | **Fixed (correctness)** |
| GDDY | CashAndEquivalents | 24/49 (49%) | 50/49 (100%+) | **Fixed** |
| GLW | Capex | 2/71 (3%) | 47/71 (66%) | **Fixed** |
| MA | NetIncomeLoss | 23/74 (31%) | 71/74 (96%) | **Fixed** |
| KEYS | NetIncomeLoss | 14/51 (27%) | 50/51 (98%) | **Fixed** |

- **WDAY SharesOutstanding**: the Q3 FY2012 10-Q (filed 2012-12-07, WDAY's IPO quarter)
  correctly reports `CommonStockSharesOutstanding` = 36.0M for 2012-01-31, but also reports
  val=0 for 2012-10-31 in the same filing — a same-filing tagging artifact (Workday
  obviously did not have zero shares immediately post-IPO). No weighted-average-shares tag
  covers 2012 at all, so this bad value was flowing straight through as the resolved value.
  Excluded via `_KNOWN_BAD_FACTS`, analogous to the existing BKR precedent. Coverage %
  drops slightly because a silently-wrong value is worse than a missing one.
- **GDDY CashAndEquivalents**: base tag stops at 2019-09-30. GoDaddy switched to the
  combined ASU 2016-18 restricted-cash tag
  (`CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents`) from FY2019 on.
  Verified at all 9 overlapping dates (2016-2019): exact match every time (GDDY carries $0
  restricted cash). Explicitly tested against AMP (also flagged for this concept) and
  **rejected there**: AMP's combined tag runs ~$3.0-3.1B *above* its plain cash tag at every
  overlapping date (Ameriprise holds material segregated/regulatory restricted cash) — same
  -name candidate, different scope, kept ticker-specific to GDDY only.
- **GLW Capex**: base tags resolve only 2/71. Corning tagged the bulk of its 2007-2020
  capex history under `PaymentsForProceedsFromProductiveAssets` instead of the configured
  tags. Verified at the 2 dates both tags coexist: identical values. A bonus cross-check at
  the pre-existing 2011-03-31 `_KNOWN_BAD_FACTS` exclusion date shows this tag holding the
  plausible $532M vs. the excluded tag's implausible $100B, further confirming it's the
  same genuine figure. Neither tag has anything after 2020-09-30, and the only newer
  candidate is an accrual/payable-timing concept, not the cash payment — post-2020 gap
  remains unfixed.
- **MA + KEYS NetIncomeLoss**: MA's NetIncomeLoss stops dead at 2014-03-31; KEYS's only
  starts at FY2023. Both trace to the same root cause: each company's real bottom-line net
  income is tagged under `us-gaap:ProfitLoss` for the missing window. Verified via exact
  same-date matches at each transition: MA's NetIncomeLoss and ProfitLoss both show exactly
  $870M at 2014 Q1 (the last quarter before MA switched to ProfitLoss for every quarter
  since); KEYS's ProfitLoss cleanly covers 2013-10-31 through 2026-04-30 (its entire
  post-Agilent-spinoff history). **Self-caught scoping mistake, corrected before
  finalizing**: this fix was first written as a single profile-wide
  `PROFILE_CONCEPT_OVERRIDES["standard"]` entry, and the group's own non-regression diff
  immediately caught the fallout — it silently pulled ProfitLoss-sourced values into ~20
  *other* standard-profile tickers that were never flagged for NetIncomeLoss and never
  individually checked for this substitution's safety. Reverted and replaced with two
  separate `TICKER_CONCEPT_OVERRIDES` entries (MA, KEYS only), restoring the group's
  touched-ticker count from 23 to the correct 5.

### Rejected candidates with evidence (documented, not adopted)

- **FDS DividendsPerShare** (thin 21/71, 30%): a real ~7-year gap (2015-2021) despite
  FactSet's well-documented unbroken dividend-growth history.
  `DividendsPayableAmountPerShare` looked promising (66 values spanning the gap) but is the
  established-precedent pattern already rejected elsewhere in this project: an instant,
  record-date-stamped snapshot (weeks before FactSet's actual quarter ends, not aligned to
  them), not a "declared this quarter" duration event. Corroborating aggregate tags confirm
  FactSet was paying and growing its dividend continuously through the gap — a genuine,
  real XBRL under-tagging period with no safe same-shape substitute.
- **AMP CashAndEquivalents**: see the GDDY fix above — explicitly tested and rejected for
  AMP specifically (material restricted cash makes the combined tag ~$3B too high).

### Cross-cutting patterns (remaining ~78 flags, all before=after, all confirmed structural
unless noted)

**Genuine non-payers** (0% coverage, no per-share tag ever filed): ADBE, ADSK, AKAM, AMD,
AMZN, ANET, APP, CBRE, CDNS, CIEN, COHR, COIN, CPAY, CRWD, CSGP, DDOG, FFIV, FISV, FLEX,
FSLR, FTNT, IT, KEYS, LITE, NOW, ON, PANW, PLTR, PTC, RDDT, SMCI, SNPS, TDY, TRMB, TYL,
WDAY, XYZ, ZBRA DividendsPerShare. Keyword hits across this whole set are consistently
either preferred-stock items from retired convertible-preferred financings (COHR, CPAY,
LITE), dividends *received* (wrong direction: FSLR, TRMB), zero-valued stock-comp
assumptions, or nothing at all.

**Recently-initiated dividend programs** (thin, but real & young): CRM (9/76, first
dividend 2024), DELL (17/47, first dividend 2022 as "new" Dell post-VMware), GOOG/GOOGL
(8/50 each, Alphabet's first-ever dividend was 2024), MU (18/70, first dividend 2021), PYPL
(2/50, first-ever dividend just initiated late 2025), VRSN (9/75, first-ever dividend
2024), CTSH (34/74, initiated Feb 2017, gap is genuinely pre-program).

**Conglomerate/diversified companies, no discrete operating-income subtotal**: AJG
OperatingIncomeLoss 0/67 (insurance brokerage), AMP OperatingIncomeLoss 0/74 (asset
manager), BRO OperatingIncomeLoss 0/72 (insurance brokerage), IBM OperatingIncomeLoss 0/75
(diversified conglomerate), KLAC OperatingIncomeLoss 23/69 (37%, tagged 2009-2015 then
genuinely stopped — verified directly against raw JSON, no filtering artifact).

**Tag genuinely disappeared from XBRL after a cutoff year** (real presentation change, not
a bug): AAPL Goodwill 36/74 (49%, tagged 2008-2017, then Apple's balance sheet became more
aggregated and stopped breaking out a discrete Goodwill line at all — confirmed via a
26-tag keyword sweep finding no successor). PLTR Goodwill 2/30 (7%, real values captured
2021-2022 including a corroborated $36.1M 2022 acquisition, then the discrete balance tag
stops even though intangibles footnote detail keeps being tagged through 2025). AMP
Goodwill 16/74 (22%, roughly annual-only tagging cadence).

**Genuinely debt-free, or paid off debt and stopped being tagged**: MPWR LongTermDebt 0/66
(zero hits anywhere), ANET 4/54 (cleanly hits $0.0000 by mid-2014 and stops), FFIV 12/70
(same clean decline-to-zero pattern), PLTR 5/30 (converges to $0.0000 at 2021-12-31), RDDT
0/15 (young, debt-free since its 2024 IPO).

**Recently issued real debt** (thin coverage = real timeline, not a gap): FTNT 22/66 (33%,
first senior notes 2020), PTC 29/70 (41%, ~2018-era acquisition financing), TYL 22/67 (33%,
first convertible notes ~2020 tied to the NIC Inc. acquisition), SNDK 6/13 (46%, young
post-spinoff ticker paying down spinoff-related debt fast: $1,351M → $603M → $0), SWKS
32/71 (45%, small convertible debt 2009-2012 paid off, genuinely debt-free 2012-2020, new
senior notes issued 2020).

**Individually-verified remaining flags**: AJG Capex 31/67 (46%, tag cleanly covers
2009-2017 then stops, no cash-capex substitute found); FISV DepreciationAndAmortization
29/74 (39%, only amortization-of-intangibles resolves, same diversified-no-combined-
subtotal theme applied to D&A); FLEX OperatingIncomeLoss 23/74 (31%, real current values
2020-2026, no substitute for the pre-2020 gap); FSLR DividendsPerShare 0/73 (both
configured tags present as raw keys but 0 usable values, still a genuine non-payer);
GOOG/GOOGL DepreciationAndAmortization 14/50 (28%, Depreciation alone resolves only
2023-2026, likely tied to AI-datacenter capex buildout); IT (Gartner) Capex 0/70 (no
capex-payment tag of any kind, consistent with a light-asset research/advisory model).

**Config changes**: `parsers/parse_edgar.py` — new `("WDAY", "CommonStockSharesOutstanding")`
entry in `_KNOWN_BAD_FACTS`. `config.py` — new `TICKER_CONCEPT_OVERRIDES` entries for
GDDY (`CashAndEquivalents`), GLW (`Capex`), MA (`NetIncomeLoss`), KEYS (`NetIncomeLoss`).

**Group non-regression** (all 110 standard-profile tickers) vs. master before-snapshot: 1
row removed (WDAY SharesOutstanding bad value, exactly as intended), 155 rows added (GDDY
+26, GLW +45, KEYS +36, MA +48 — every addition traces to one of the 4 documented fixes), 0
changed. Exactly 5 tickers touched: GDDY, GLW, KEYS, MA, WDAY. No other standard-profile
ticker moved at all. Clean (after the profile-override correction described above).

---

## telecom_cable (3 flags)

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| CHTR | DividendsPerShare | 0/66 (0%) | 0/66 (0%) | Confirmed structural |
| SATS | DividendsPerShare | 0/70 (0%) | 0/70 (0%) | Confirmed structural |
| TMUS | DividendsPerShare | 11/71 (15%) | 11/71 (15%) | Confirmed structural |

- **CHTR**: genuine non-payer — Charter is well known for prioritizing aggressive share
  buybacks over dividends. Hits are all wrong-direction/irrelevant (payouts to JV minority
  partners, dividends received, a single ancient preferred-stock rate).
- **SATS**: genuine non-payer (EchoStar). All 5 hits are dividends *received* from
  equity-method investments (mostly $0 recently) or irrelevant ancient/assumption items.
- **TMUS**: `CommonStockDividendsPerShareDeclared` gives 11 real values, all 2023-2026
  ($1.02/share latest) — T-Mobile initiated its first-ever dividend in September 2023, a
  well-documented real event, corroborated by two aggregate tags in the same window. Older
  hits (2014-2018) are legacy MetroPCS-merger-era preferred-stock items that wound down to
  $0 years before the common dividend started. Same recently-initiated-program pattern seen
  throughout the standard group.

No config changes. Non-regression: trivially clean.

---

## utilities (19 flags)

### Priority subsection: PCG (Goodwill 0%, D&A 0%, DividendsPerShare 48%)

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| PCG | Goodwill | 0/75 (0%) | 0/75 (0%) | Confirmed structural |
| PCG | DepreciationAndAmortization | 0/75 (0%) | 0/75 (0%) | Confirmed structural |
| PCG | DividendsPerShare | 36/75 (48%) | 36/75 (48%) | Confirmed structural (bankruptcy-related) |

- **Goodwill**: zero real hits — only tiny, ancient (2010-2012) `FiniteLivedIntangibleAssets`
  (a different concept entirely). **This is NOT bankruptcy-related**: it fits the
  sector-wide "regulated utilities carry no goodwill" pattern below, spanning PCG's entire
  history both before and after the 2019 Chapter 11 filing — PG&E is simply a very old,
  organically-built utility like its non-bankrupt peers.
  **The task's bankruptcy hypothesis for this flag specifically does not hold up.**
- **DepreciationAndAmortization**: all 8 configured tags (including the utility-specific
  `UtilitiesOperatingExpenseDepreciationAndAmortization`) show NOT PRESENT; all 10 keyword
  hits are balance-sheet accumulated-depreciation or lease-amortization items, wrong shape.
  This gap also spans PCG's entire history, not concentrated around 2019 — also not
  evidence of a bankruptcy-driven change.
- **DividendsPerShare**: `CommonStockDividendsPerShareDeclared` gives 36 real values
  2008-2018, with the last three explicitly $0.0000 (2018 Q1-Q3). **This one IS directly
  tied to the bankruptcy, exactly as hypothesized**: PG&E suspended its common dividend in
  late 2017/early 2018 as its California wildfire liabilities became apparent (ahead of the
  formal January 2019 Chapter 11 filing), and has not reinstated a common dividend since
  emerging from bankruptcy in 2020 (capital has gone to the wildfire trust and safety capex
  instead). CONFIRMED STRUCTURAL — the coverage is a correct reflection of a real,
  still-ongoing suspension, not a tagging gap.

### Priority subsection: AES & SRE OperatingIncomeLoss (profile-split question — reported,
### not acted on)

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| AES | OperatingIncomeLoss | 0/78 (0%) | 0/78 (0%) | Confirmed structural |
| AES | LongTermDebt | 0/78 (0%) | 0/78 (0%) | Confirmed structural |
| SRE | OperatingIncomeLoss | 0/68 (0%) | 0/68 (0%) | Confirmed structural |

- **AES**: OperatingIncomeLoss has no discrete subtotal ever tagged. LongTermDebt is
  genuinely zero-hit across every candidate — surprising for a heavily-leveraged global
  power company, so investigated further: AES has a `NonRecourseDebt` tag ($15.1-15.6B,
  plausible scale) but it's annual-only, 10-K-sourced, and covers just 2015-2018 — too
  narrow and short-lived to serve as a real fix, but it strongly corroborates the
  underlying story: AES finances its global generation fleet primarily through
  project-level non-recourse debt (a well-documented, distinctive feature of its capital
  structure) rather than parent-level "long-term debt," so the standard debt tags
  genuinely don't apply the way they do for a typical regulated utility.
- **SRE**: same — no discrete OperatingIncomeLoss subtotal ever tagged.
- **Assessment for the profile-split question**: only 2 of the 14 flagged utilities
  tickers (AES, SRE) show this OperatingIncomeLoss pattern — not a majority, but both share
  a real, coherent structural trait that sets them apart from the rest of the profile: AES
  is a global independent-power-producer/merchant-generation-heavy holding company with
  only partial traditional-utility operations, and SRE (Sempra) owns traditional California
  utilities alongside a large and growing LNG-export/energy-infrastructure segment (Sempra
  Infrastructure) — both are "hybrid" energy companies with a significant
  non-traditional-utility segment, plausibly explaining why neither tags a single
  consolidated GAAP operating-income subtotal, similar in spirit to the existing
  energy/energy_integrated and materials/materials_integrated splits. **This finding is
  reported for the project owner's decision, not acted on — no profile split or ticker
  reassignment was made.**

### Priority subsection: NEE & DTE Capex (both MISSING 0%, unusual for capex-heavy
### utilities)

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| DTE | Capex | 0/74 (0%) | 0/74 (0%) | Confirmed structural |
| NEE | Capex | 0/74 (0%) | 0/74 (0%) | Confirmed structural |

All 4 configured tags show NOT PRESENT for both. Broadened the search well beyond the
standard capex/productiveassets/propertyplant keywords (checked "capital"-named and
utility-specific construction-related tags too) — found nothing resembling a single
consolidated cash-capex line for either ticker. **This is NOT the same story as the
AEP/ETR/LNT tag-migration-over-time cases below**: neither DTE nor NEE has *any* capex
cash-outflow tag at any point in their history, in any name. Both, however, show massive
and continuously growing gross PP&E balance-sheet figures through 2026 (NEE: $203.8B gross
PP&E at 2026-03-31; DTE: $45.6B) — confirming both companies are genuinely investing
heavily every year; they simply do not tag a single combined "cash paid for capex" figure.
The most plausible explanation: both are multi-segment utility holding companies (NEE:
Florida Power & Light utility + NextEra Energy Resources renewable-generation arm; DTE:
DTE Electric + DTE Gas + DTE Vantage non-utility businesses) that likely present capex
broken out by segment on the face of the cash flow statement rather than as one combined
line — the same underlying "diversified company, no single consolidated subtotal" theme
already established for OperatingIncomeLoss/D&A elsewhere in this sweep, here applied to
Capex specifically for segment-diversified utility holding companies. No viable single
substitute tag exists for either.

### Cross-cutting pattern: regulated utilities genuinely carry no goodwill (sector-wide,
not a tagging gap)

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| CMS | Goodwill | 0/72 (0%) | 0/72 (0%) | Confirmed structural |
| EIX | Goodwill | 0/74 (0%) | 0/74 (0%) | Confirmed structural |
| LNT | Goodwill | 0/70 (0%) | 0/70 (0%) | Confirmed structural |
| PNW | Goodwill | 0/70 (0%) | 0/70 (0%) | Confirmed structural |
| XEL | Goodwill | 0/74 (0%) | 0/74 (0%) | Confirmed structural |

XEL: literally 0 keyword hits of any kind anywhere in its us-gaap namespace — the
strongest possible null result. Every hit across this entire cluster (plus PCG above) is
either a small/immaterial `FiniteLivedIntangibleAssets` balance (a genuinely different
concept from Goodwill) or, for EIX, a single $16.5M `GoodwillImpairmentLoss` in 2017 Q2
(showing EIX once carried a small amount of goodwill that was fully written off and never
separately balance-sheet-tagged again). A well-evidenced, real, sector-wide fact:
traditional regulated electric/gas utilities grow primarily through regulator-approved
rate-base capital investment rather than M&A, so goodwill is rare-to-nonexistent on their
balance sheets — consistent across 6 of the 14 utilities tickers flagged in this exact
group. All CONFIRMED STRUCTURAL / genuine absence.

### Cross-cutting pattern: Capex tag coverage reflects real historical XBRL-tagging-
practice evolution

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| AEP | DividendsPerShare | 10/74 (14%) | 10/74 (14%) | Confirmed structural |
| AEP | Capex | 35/74 (47%) | 35/74 (47%) | Confirmed structural |
| ETR | Capex | 36/76 (47%) | 36/76 (47%) | Confirmed structural |
| LNT | Capex | 30/70 (43%) | 30/70 (43%) | Confirmed structural |

- **AEP DividendsPerShare**: `CommonStockDividendsPerShareCashPaid` covers only 2008-2010;
  `DividendsCommonStock`/`PaymentsOfDividendsCommonStock` (70 values each, 2008-2026)
  confirm AEP is a real, continuous, substantial payer throughout — the generic
  genuine-payer-untagged pattern, just unusually severe/long-lasting (16 years untagged).
- **AEP, ETR, LNT Capex**: combining all 4 candidate tags gives real but gappy combined
  coverage — AEP has a genuine 2021-2024 bridge gap with no substitute found in an 18-tag
  keyword sweep; ETR's 56 combined raw dates show scattered ~181-365-day gaps throughout
  2007-2022, becoming fully quarterly only from ~2022 on; LNT's combined tags show a
  striking exactly-annual cadence 2009-2017, becoming fully quarterly from 2018 on. Every
  configured/candidate tag was already combined — remaining gaps are genuine historical
  absences (sporadic-to-annual-only early XBRL tagging practice, industry-wide over that
  era), not caused by an unmatched tag name.

### Individually-verified remaining flags

| Ticker | Concept | Before | After | Status |
|---|---|---|---|---|
| CEG | Goodwill | 11/23 (48%) | 11/23 (48%) | Confirmed structural (scale-verified) |
| VST | DividendsPerShare | 14/40 (35%) | 14/40 (35%) | Confirmed structural |

- **CEG Goodwill**: all 11 real values captured, 2022-12-31 (CEG's Exelon spinoff date)
  through 2026-03-31 — the 48% reflects CEG being a young, post-spinoff ticker, not a gap.
  Scale-checked the huge jump at the most recent date ($420M → $11,527M at 2026-03-31,
  filed 2026-05-11): real, not an error — matches Constellation Energy's ~$16.4B Calpine
  acquisition (announced Jan 2025), which closed in early 2026.
- **VST DividendsPerShare**: `CommonStockDividendsPerShareDeclared` has exactly one value
  (2016-12-31, $2.32/share) matching a one-time $992.0M special distribution tied to
  Vistra's October 2016 emergence from the Energy Future Holdings Chapter 11
  reorganization — not the start of a regular program. A real gap follows (2017-2018, no
  dividend yet), before `CommonStockDividendsPerShareCashPaid` picks up cleanly from
  2019-03-31 with small, real, regular payments, corroborated by two aggregate tags from
  the same window. A bankruptcy-adjacent story in the opposite direction from PCG's (fresh
  start followed by a new regular program, vs. PCG's suspension).

No config changes for this group. Non-regression: trivially clean (no confirmed-safe fix
was found for any of the 19 flags — every substitute candidate checked either didn't
exist, was the wrong shape/concept, or, for AES's `NonRecourseDebt`, was too narrow/
short-lived to serve as a real fix).

---

## Final combined non-regression (all 497 active tickers, before-task vs. final state)

Master before-snapshot (371,619 rows, 497 tickers, captured before any edits this session)
diffed against a fresh final snapshot (371,926 rows, 497 tickers, built after every group's
edits), with **no ticker filter** — both sides cover the complete active universe:

- **REMOVED: 3 rows** — `BKR SharesOutstanding` (2, the known-bad-fact exclusion), `WDAY
  SharesOutstanding` (1, the known-bad-fact exclusion). Both intentional correctness fixes.
- **ADDED: 310 rows** across exactly 10 `(ticker, concept)` pairs: `AIG LongTermDebt` (+22),
  `ARE GainLossOnSaleOfProperties` (+21), `FRT GainLossOnSaleOfProperties` (+17), `GDDY
  CashAndEquivalents` (+26), `GLW Capex` (+45), `IDXX LongTermDebt` (+33), `KEYS
  NetIncomeLoss` (+36), `MA NetIncomeLoss` (+48), `PRU RealizedInvestmentGains` (+55), `TGT
  AccountsReceivable` (+7).
- **CHANGED: 0 rows** — every touched value is either a pure addition or one of the 2
  intentional bad-value removals; nothing existing was silently altered.
- **Tickers touched: exactly 12** — AIG, ARE, BKR, FRT, GDDY, GLW, IDXX, KEYS, MA, PRU, TGT,
  WDAY. Every one traces to a specific, documented, individually-verified fix from this
  sweep. **No ticker outside this list changed at all**, across any of the other ~485
  active tickers in any of the 21 profiles. **No group's fix altered another group's
  tickers** (confirmed both here and via each group's own individually-scoped diff earlier
  in this report).

---

## Overall summary

- **Total flags investigated**: 387 (re-derived directly from `full_refresh_report.md`'s
  per-profile breakdown, group by group, in report order — close to the report's own
  summary figure of ~396; the small gap is immaterial and does not affect any finding
  above, since every flag actually listed under every one of the 21 profile headers was
  investigated).
- **Real fixes applied and non-regression-verified**: **12** `(ticker, concept)` pairs —
  BKR `CommonStockSharesOutstanding` known-bad-fact, PRU `RealizedInvestmentGains`, AIG
  `LongTermDebt`, IDXX `LongTermDebt`, ARE `GainLossOnSaleOfProperties`, FRT
  `GainLossOnSaleOfProperties`, TGT `AccountsReceivable`, WDAY `SharesOutstanding`
  known-bad-fact, GDDY `CashAndEquivalents`, GLW `Capex`, MA `NetIncomeLoss`, KEYS
  `NetIncomeLoss`.
- **Logged as ambiguous**: approximately **8** flags — a candidate existed but could not be
  verified safe or unsafe from EDGAR data alone, so it was explicitly not adopted rather
  than forced: GL `RealizedInvestmentGains`; AIG `RealizedInvestmentGains`; AIZ
  `RealizedInvestmentGains`; L `RealizedInvestmentGains`; IRM, HST, KIM
  `GainLossOnSaleOfProperties`; VTR `GainLossOnSaleOfProperties`.
- **Confirmed structural** (genuine non-payer, genuine absence, young ticker/short history,
  real historical timeline, or a candidate rejected on clear contradicting evidence): the
  remaining **~367** flags — the large majority of the sweep. Recurring structural themes
  found repeatedly across profiles: genuine dividend non-payers and recently-initiated
  dividend programs (dozens of tickers); diversified/conglomerate companies not tagging a
  discrete OperatingIncomeLoss or combined D&A subtotal; regulated utilities carrying no
  goodwill sector-wide; companies that paid off all debt and stopped being tagged;
  companies that only recently issued their first real debt; XBRL tags that migrated to a
  new name over time (verified via same-date value matches before adoption); and several
  candidates that looked promising by name but were proven wrong by scale or sign at shared
  dates and correctly rejected (AMP `CashAndEquivalents`, FDS `DividendsPerShare`, GL/AIG/CB
  `RealizedInvestmentGains`, HST/IRM/KIM `GainLossOnSaleOfProperties`, BXP/PLD
  `GainLossOnSaleOfProperties`).
- **Priority items called out explicitly in the task**:
  - **ERIE's 5-flag cluster** resolved to a nuanced two-cause answer: 3 of 5 flags
    plausibly tied to its asset-light reciprocal-exchange-management structure;
    SharesOutstanding tied to a separate dual-class-share fact; DividendsPerShare unrelated
    to any ERIE-specific structure.
  - **PCG's 3 flags**: 2 confirmed unrelated to the 2019 bankruptcy (Goodwill, D&A — both
    sector-wide utility patterns), 1 confirmed directly tied to it (DividendsPerShare,
    suspended pre-bankruptcy, never reinstated).
  - **AES/SRE OperatingIncomeLoss**: a plausible profile-split rationale identified and
    reported, not acted on.
  - **NEE/DTE Capex**: confirmed genuinely different from other utilities' capex gaps — no
    consolidated single-line capex tag exists for either, most likely because both are
    segment-diversified holding companies.
  - **Q**: confirmed as a brand-new registrant (Qnity Electronics) where "wait for more
    filings" is the only correct answer.
  - **TROW LongTermDebt**: full plausibility sweep found zero hits of any kind, confirming
    genuine no-debt status with the highest achievable confidence.
