# Follow-Up Report — The Three Open Questions from priority_merge_report.md

All non-regression diffs below cover every cached ticker (111 `cache/*_company_info.json` files,
which include all 19 `TICKER_PROFILES` entries — nothing needed fetching). `config.py` was
modified in Parts B and C; Part A made no changes.

## Part A — No other concept has the architecture bug

**Step 1: re-verified directly from `config.py`, not by trusting the earlier grep.** Read every
entry in `CONCEPT_CANDIDATES` and every entry in `PROFILE_CONCEPT_OVERRIDES["financial"]` and
recorded each one's `mode`:

| Concept | Base mode | `financial` override mode |
|---|---|---|
| Revenue | `fallback` | `priority_merge` *(changed in Part C)* |
| NetIncomeLoss | `fallback` | — |
| SharesOutstanding | `fallback` | — |
| StockholdersEquity | `fallback` | — |
| OperatingIncomeLoss | `fallback` | — |
| OperatingCashFlow | `fallback` | — |
| **Capex** | **`fallback`** | (excluded for financial) |
| DepreciationAndAmortization | `priority_merge` | `priority_merge` |
| LongTermDebt | `priority_merge` | (excluded for financial) |
| CashAndEquivalents | `fallback` | `fallback` |
| DividendsPerShare | `fallback` | — |
| Assets | — | `fallback` |
| NetInterestIncome | — | `fallback` |
| NoninterestExpense | — | `fallback` |
| Goodwill | — | `fallback` |
| ProvisionForCreditLosses | — | `fallback` |
| NoninterestIncome | — | `fallback` |

Every concept is either plain `fallback` (single-tier, already per-date, no sum step to be
gated) or the already-migrated `priority_merge`. **Confirmed: no other concept used
`fallback_then_sum`/`fallback_sum`, and none does now** — the grep in the previous report's
Part D was correct, and this direct read of every entry confirms it independently rather than
re-trusting the same tool call.

**Step 2: GLW's `Capex` re-checked.** `Capex`'s mode is plain `fallback` — confirmed in the table
above. Plain `fallback` has no sum tier at all, so the merge-mechanics bug categorically cannot
apply to it; this was never a `priority_merge` candidate. Pulled GLW's `Capex` search results
again from the cached data: the only two non-forward-looking, non-zero-coverage hits are
`ProceedsFromSaleOfPropertyPlantAndEquipment` (disposal proceeds — wrong cash-flow direction) and
`ProceedsFromSaleOfOtherPropertyPlantAndEquipment`/`ProceedsFromSaleOfProductiveAssets` (same
issue) — exactly Run 2's original finding. **Confirmed: GLW's Capex gap (3/71, 4%) is a genuine
no-viable-candidate case, unrelated to merge architecture.**

**Conclusion: nothing to migrate. No config changes made for Part A.**

## Part B — Targeted LongTermDebt search: 11 remaining tech tickers

Searched all 11 (`ADI, ANET, CDNS, FFIV, FTNT, MPWR, PLTR, PTC, SNDK, SWKS, TYL`) with the current
`SEARCH_HINTS` (`["longtermdebt", "borrowings", "notespayable"]`) plus separate broad passes on
`["debt"]` and `["notes"]` — 18–38 hits per ticker (306 total), reviewed by hand.

**The broad hints surfaced several new false-positive families** not seen in earlier scans
(worth naming since they'll recur in any future "debt"/"notes" search): investment-portfolio
`AvailableForSaleSecurities*`/debt-securities-holdings tags (asset side — the company's own
investments *in* debt securities, not debt it owes); `*Receivable`/`StockholdersEquityNote*`
(unrelated, the latter a false positive from "notes" matching mid-word); discount/premium/
issuance-cost contra-accounts (`*UnamortizedDiscount*`, `*DebtIssuanceCost*`, `WriteOffOf*`) —
small adjustment amounts, not the balance itself; single-debt-instrument disclosures
(`DebtInstrumentFaceAmount`, `DebtInstrumentCarryingAmount`) — ambiguous whether a company-wide
total or one tranche among several; and bare `*Current`-suffixed tags (`DebtCurrent`,
`UnsecuredDebtCurrent`) — current-portion-only components, same exclusion logic as
`LongTermDebtAndCapitalLeaseObligationsCurrent` from the previous task. All of these were rejected
or flagged, none silently discarded.

**What survived, and the magnitude check that mattered:**

| Ticker | Candidate | Verdict | Reasoning |
|---|---|---|---|
| ADI | `UnsecuredLongTermDebt` | ✅ **Added** | Overlap with existing `LongTermDebt` values at 5 dates: ratio 0.988–0.996, tight and consistent — same underlying figure, alternate name. |
| CDNS | `UnsecuredLongTermDebt` | ⚠️ **Added, flagged lower-confidence** | Same tag name, but overlap is inconsistent for CDNS: some dates match closely (ratio ~1.0–1.19), one date is a complete mismatch (existing=$324.8M vs candidate=$0), and several "overlapping" dates have existing=$0 while the candidate shows real values. Added anyway since it's the same shared config entry that fixes ADI cleanly and, being lowest-priority, can only fill CDNS's currently-null dates — but the new CDNS fills should be treated with less confidence than ADI's. |
| PTC | `SeniorNotes` | ❌ **Not added** | Overlap with existing `LongTermDebt` at 4 dates: ratio 0.44–0.78, inconsistent and well below 1x — this is a debt *component* (PTC evidently has other debt instruments beyond its senior notes), not the total. Adding it would understate PTC's debt in any gap period where other debt existed. |

All other candidates were cash-flow (`ProceedsFrom*`/`RepaymentsOf*`/`*Repayment*`/`*Borrowings*`),
fair-value-basis, thin (<3 new points), or 0-coverage — rejected per the established criteria.

**Non-regression check:** added only `UnsecuredLongTermDebt` (shared `LongTermDebt.sources`, at
the very end, after the capital-lease tags from the previous task). Diffed `LongTermDebt` across
all 111 tickers: **0 regressions**, **110 new fills** — ADI +50, CDNS +38, plus bonus coverage for
three tickers outside the original 11: KLAC +17, GS +4, GE +1.

**Per-ticker outcome for the 11:**
- **Resolved via a real candidate: ADI** (clean fix).
- **Partially filled, lower confidence: CDNS** (see caveat above).
- **No viable candidate, genuinely unresolved: ANET, FFIV, FTNT, MPWR, PLTR, PTC, SNDK, SWKS,
  TYL** — consistent with Run 2's original expectation that several of these (PLTR named
  explicitly) are simply low-debt companies with sparse XBRL debt tagging. Not manufactured; if a
  candidate isn't there, it isn't there.

## Part C — Bank Revenue: validated sum, not just another single tag

### Step 1 — Validation (mandatory gate before touching anything)

Pulled quarterly values for `RevenuesNetOfInterestExpense`, `InterestIncomeExpenseNet`, and
`NoninterestIncome` for **JPM**: `InterestIncomeExpenseNet + NoninterestIncome` matched
`RevenuesNetOfInterestExpense` **exactly** (0% difference) across **all 49** overlapping quarters
(e.g. 2025-09-30: $23,966M + $22,461M = $46,427M = reported revenue, to the dollar). Repeated on
**WFC** as a second data point: exact match across all 25 overlapping quarters too. This is not an
approximation — it's the literal accounting identity (total revenue = net interest income +
noninterest income) that the two tags decompose. **Validation holds cleanly; proceeding.**

### Step 2 — Component availability for the 7 target tickers

`search_tags` with `["interestincome", "interestexpensenet"]` and `["noninterestincome"]` against
`TFC, FITB, HBAN, RF, BNY, MTB, SYF`: **all 7 report both `InterestIncomeExpenseNet` and
`NoninterestIncome`**, each with 51–71 quarters of coverage (full history for most). No ticker was
missing a component.

### Step 3 — Added, verified, and the result

Migrated the `financial` profile's `Revenue` override from `fallback`/`tags` to `priority_merge`/
`sources` (verified byte-identical first: 0 diffs, 0 new fills, across all 111 tickers), then
appended `{"type": "sum", "tags": ["InterestIncomeExpenseNet", "NoninterestIncome"]}` as the
lowest-priority source, after both existing single-tag entries.

**Non-regression check, scoped to the full `financial` universe as instructed (all 19
`TICKER_PROFILES` tickers, not just the 7):** **0 regressions**, **638 new fills.** Every one of
the 7 target tickers gained coverage, plus 6 more banks that weren't part of the original
investigation: WFC +34, AXP +30, KEY +29, USB +28, COF +16, NTRS +55.

**Coverage before → after** (via `check_data_quality`, full concept set):

| Ticker | Before | After |
|---|---|---|
| TFC | 0/74 (0%) | **71/74 (96%)** |
| FITB | 0/77 (0%) | **71/77 (92%)** |
| HBAN | 0/70 (0%) | **67/70 (96%)** |
| RF | 0/74 (0%) | **71/74 (96%)** |
| BNY | 28/73 (38%) | **71/74 (96%)** |
| MTB | 1/74 (1%) | **71/74 (96%)** |
| SYF | 0/54 (0%) | **53/54 (98%)** |
| WFC | 37/74 (50%) | **71/74 (96%)** |
| AXP | 41/74 (55%) | **71/74 (96%)** |
| KEY | 42/74 (57%) | **70/74 (95%)** |
| USB | 42/74 (57%) | **70/74 (95%)** |
| COF | 55/74 (74%) | **71/74 (96%)** |
| NTRS | 15/73 (21%) | **70/74 (95%)** |
| BAC | 71/74 (96%) | 71/74 (96%) — already clean, unaffected |
| C | 69/72 (96%) | 69/72 (96%) — already clean, unaffected |
| JPM | 71/74 (96%) | 71/74 (96%) — already clean, unaffected |
| PNC | 70/74 (95%) | 70/74 (95%) — already clean, unaffected |
| CFG | 50/53 (94%) | 50/53 (94%) — already clean, unaffected |
| STT | 70/74 (95%) | 70/74 (95%) — already clean, unaffected |

**All 19 financial-profile tickers now sit at ≥92% Revenue coverage.** This fully resolves the
bank Revenue gap that recurred across every prior scan (Runs 2, 3, and the structural-fix task) —
it turned out to genuinely be a "need a sum, not a single tag" problem, exactly as this task's
premise suspected, and the validated formula generalized cleanly to every bank in scope with zero
exceptions.

## Net effect on `config.py`

- `CONCEPT_CANDIDATES["LongTermDebt"]["sources"]`: `+ {"type": "tag", "tag":
  "UnsecuredLongTermDebt"}` (appended last)
- `PROFILE_CONCEPT_OVERRIDES["financial"]["Revenue"]`: migrated from `fallback`/`tags` to
  `priority_merge`/`sources` (same 2 tags, same order — verified byte-identical), then `+
  {"type": "sum", "tags": ["InterestIncomeExpenseNet", "NoninterestIncome"]}` appended last

No other changes. All migrations and additions were verified non-regressive against the full
cached-ticker universe before being kept.

## Open items for the human reviewer

1. **CDNS's `UnsecuredLongTermDebt` fill is lower-confidence than ADI's** — the tag's relationship
   to CDNS's actual total debt is inconsistent in the few periods with a baseline to check against.
   Worth a manual look at CDNS's filings if precision there matters.
2. **9 of the 11 tech tickers from Part B remain genuinely without a `LongTermDebt` fix** (ANET,
   FFIV, FTNT, MPWR, PLTR, PTC, SNDK, SWKS, TYL) — not a merge-mechanics or search-hint problem at
   this point, just sparse/absent debt tagging for low-debt companies.
3. **PTC's `SeniorNotes`** is real data (14 new points) but was correctly withheld as a partial
   component, not a total — if PTC's other debt instruments are ever separately identified and
   tagged, a genuine `sum` source (senior notes + the rest) could be constructed the same way
   Part C did for bank revenue, but that would need its own validation pass.

No scratch scripts were left behind.
