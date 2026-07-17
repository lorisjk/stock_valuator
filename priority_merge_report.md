# Priority-Merge Structural Fix — Report

## What the new mode does

`extract_with_mode` (in `parsers/parse_edgar.py`) gained a new `"priority_merge"` mode, backed by
a new `extract_priority_merge()` function, implemented exactly as specified in the task. A
concept using this mode declares an ordered `sources` list instead of `tags`/`sum_tags`/
`fallback_sum_tags`; each source is either `{"type": "tag", "tag": "..."}` or `{"type": "sum",
"tags": [...]}`. The merge is a single per-date pass: sources are walked in order, and for each
date a source can supply, the **first** source in the list to produce a value for that date wins
— a `sum` step is not special-cased, it just occupies a position and gets skipped for any date
already claimed by an earlier source. No existing `fallback`/`sum`/`fallback_sum`/
`fallback_then_sum` code paths were touched or removed; they remain in `extract_with_mode` for
any other concept that still uses them (checked — see Part D below).

This directly fixes both bugs identified in the task:
- `fallback_then_sum` let `tags` unconditionally beat `sum_tags` for any date regardless of a new
  tag's position in the list — `priority_merge` makes position the only thing that matters, tags
  and sums alike.
- `fallback_sum`'s all-or-nothing per-ticker gate (fallback only triggers if the *entire* primary
  series is empty) is gone — `priority_merge` evaluates per date, so a sum step (or a low-priority
  tag) can fill an individual gap even when higher-priority sources have data for other dates.

## Step B1 — Pure refactor: confirmed correct, with one important nuance flagged rather than hidden

`LongTermDebt`, base `DepreciationAndAmortization`, and the `financial` profile's
`DepreciationAndAmortization` override were rewritten to `sources`/`priority_merge`, preserving
the exact current tag order and placing the sum group exactly where `sum_tags`/`fallback_sum_tags`
used to sit — no new tags added in this step.

**Verification ticker universe:** all 111 tickers with cached `company_info.json` (broader than
the 92-ticker Run-2/3 universe — includes the original pilot's tickers too). All 19
`TICKER_PROFILES` entries were already among them; nothing needed fetching.

**Result:**
- **`LongTermDebt`: byte-identical.** 0 diffs, 0 new fills, 0 regressions — exactly as the task
  predicted, because `fallback_then_sum` was already doing a full per-date "tags-collectively-
  beat-sum" merge; expressing that same priority as an ordered `sources` list changes nothing.
- **`DepreciationAndAmortization` (base + financial): 0 regressions, but *not* byte-identical —
  493 new (ticker, date) values appeared that weren't there before, with zero existing values
  changed or removed.**

**This is not a bug, and I did not "fix" it to force zero differences — here's why.** The task's
own root-cause analysis (in this task's preamble) explains that `fallback_sum`'s gate blocks
`Depreciation`/`AmortizationOfIntangibleAssets` from ever reaching six specific tickers (MTB, BAC,
NTRS, TER, TRMB, KEYS) that already have *some* primary-tag D&A coverage. `priority_merge`
removes exactly that gate — and those same tags were already sitting in the config before this
task touched anything. The 493 new fills are almost entirely those six tickers finally being able
to use data that was always configured for them but structurally unreachable (sample: TER +64,
INTC +57, TRMB +54, MTB +43, BAC +42, KEYS +32, NTRS +20 — INTC and several others are bonus
beneficiaries with the same all-or-nothing problem). Spot-checked values (e.g. TER 2009-07-05:
$8.2M; MTB 2008-06-30: $16.6M; BAC 2008-06-30: $447M) are all sane magnitudes for those companies.
Manufacturing an artificial "only fall back if the whole series is empty" special case inside
`priority_merge` just to force byte-identical B1 output would reintroduce the exact bug this task
exists to remove, and there'd be no way to square that with "implement this exactly" for the
algorithm as specified. Treating this as the correct, desired, and expected consequence of the
refactor — not a defect — and reporting it transparently is the more honest reading of "verify
empirically, don't just trust the reasoning."

## Step B2 — New tags added, non-regression re-verified

With B1 accepted, the previously-blocked tags were appended as new lowest-priority `{"type":
"tag", ...}` entries, strictly after the sum step in each `sources` list:

- `LongTermDebt`: `+ LongTermDebtAndCapitalLeaseObligations`, `+
  LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities`
- Base `DepreciationAndAmortization`: `+ AdjustmentForAmortization`, `+
  FiniteLivedIntangibleAssetsAmortizationExpense`
- `financial` `DepreciationAndAmortization`: `+ DepreciationNonproduction`, `+
  DepreciationPremisesAndEquipment`, `+ CapitalizedComputerSoftwareAmortization` (the
  previously-added `AmortizationOfMortgageServicingRightsMSRs` stays inside the `sum` step,
  unchanged, exactly where B1 preserved it)

**Verification, same 111-ticker universe, diffed against the B1 snapshot:**
- **0 regressions** — no previously-populated `(ticker, concept, end)` value changed or
  disappeared.
- **703 new fills**, this time genuinely from the newly-added tags: `LongTermDebt` gains are
  large and broad — HD +60, GLW +55, ACN +53, JPM +47, COF +43, STT +38, XOM +37, APH +35, MU +33,
  JBL +32, GE +32, HPQ +31, NXPI +27, and 20+ more tickers besides. `DepreciationAndAmortization`
  picked up a further NTRS +24, RF +13, MSFT +6 on top of what B1 already unlocked.
- End-to-end (original pre-task config vs. final): **0 regressions, 1,196 total new data points**
  across the two concepts.

No tag had to be reverted this time — unlike the previous task, every addition here sits at
strictly lowest priority in a true per-date merge, so none of it could overwrite anything.

## Part C — Coverage re-check on the 36 still-unresolved tickers

(Run-3's 39 flagged tickers minus CRWD/NTRS/SYF, which were already resolved or partially
resolved by that task.)

| Ticker | Concept | Before | After |
|---|---|---|---|
| ACN | LongTermDebt | 13/73 (18%) | **66/73 (90%) ✅** |
| APH | LongTermDebt | 34/74 (46%) | **69/74 (93%) ✅** |
| ADI | LongTermDebt | 19/74 (26%) | 19/74 (26%) |
| ANET | LongTermDebt | 4/54 (7%) | 4/54 (7%) |
| CDNS | LongTermDebt | 27/70 (39%) | 27/70 (39%) |
| GLW | Capex | 3/71 (4%) | 3/71 (4%) |
| GLW | LongTermDebt | 14/71 (20%) | **69/71 (97%) ✅** |
| FFIV | LongTermDebt | 16/70 (23%) | 16/70 (23%) |
| FLEX | OperatingIncomeLoss | 23/74 (31%) | 23/74 (31%) |
| FTNT | LongTermDebt | 22/66 (33%) | 22/66 (33%) |
| IT | Capex | 0/70 (0%) | 0/70 (0%) |
| GDDY | CashAndEquivalents | 24/49 (49%) | 24/49 (49%) |
| INTC | DepreciationAndAmortization | 13/73 (18%) | **70/73 (96%) ✅** |
| IBM | OperatingIncomeLoss | 0/74 (0%) | 0/74 (0%) |
| JBL | LongTermDebt | 32/69 (46%) | **64/69 (93%) ✅** |
| KEYS | NetIncomeLoss | 14/51 (27%) | 14/51 (27%) |
| KEYS | DepreciationAndAmortization | 18/51 (35%) | **50/51 (98%) ✅** |
| KLAC | OperatingIncomeLoss | 23/69 (33%) | 23/69 (33%) |
| MU | LongTermDebt | 33/70 (47%) | **66/70 (94%) ✅** |
| MPWR | LongTermDebt | 0/66 (0%) | 0/66 (0%) |
| NXPI | LongTermDebt | 9/43 (21%) | **36/43 (84%) ✅** |
| PLTR | LongTermDebt | 5/30 (17%) | 5/30 (17%) |
| PTC | LongTermDebt | 29/70 (41%) | 29/70 (41%) |
| Q | OperatingIncomeLoss | 0/10 (0%) | 0/10 (0%) |
| Q | LongTermDebt | 1/10 (10%) | 4/10 (40%) — improved, still <50% |
| Q | Capex | 3/10 (30%) | 3/10 (30%) |
| Q | OperatingCashFlow | 3/10 (30%) | 3/10 (30%) |
| Q | CashAndEquivalents | 4/10 (40%) | 4/10 (40%) |
| Q | NetIncomeLoss | 4/10 (40%) | 4/10 (40%) |
| SNDK | LongTermDebt | 6/13 (46%) | 6/13 (46%) |
| SWKS | LongTermDebt | 32/71 (45%) | 32/71 (45%) |
| TER | DepreciationAndAmortization | 9/72 (12%) | **73/73 (100%) ✅** |
| TRMB | DepreciationAndAmortization | 13/71 (18%) | **67/71 (94%) ✅** |
| TYL | LongTermDebt | 22/67 (33%) | 22/67 (33%) |
| WDAY | SharesOutstanding | 28/63 (44%) | 28/63 (44%) |
| BAC | DepreciationAndAmortization | 29/74 (39%) | **71/74 (96%) ✅** |
| TFC | Revenue | 0/74 (0%) | 0/74 (0%) |
| FITB | Revenue | 0/77 (0%) | 0/77 (0%) |
| HBAN | Revenue | 0/70 (0%) | 0/70 (0%) |
| MTB | Revenue | 1/74 (1%) | 1/74 (1%) |
| MTB | DepreciationAndAmortization | 28/74 (38%) | **71/74 (96%) ✅** |
| RF | Revenue | 0/74 (0%) | 0/74 (0%) |
| BNY | Revenue | 28/73 (38%) | 28/73 (38%) |
| AXP | Goodwill | 18/73 (25%) | 18/73 (25%) |

### Summary

- **Fully resolved (all flagged concepts now ≥50%): 9 of 36 — ACN, APH, INTC, JBL, MU, NXPI, TER,
  TRMB, BAC.** All nine via the fixed per-date gating: the six D&A-blocked tickers from the
  previous task (INTC, TER, TRMB, BAC, MTB*, KEYS*) plus the LongTermDebt tickers where
  `LongTermDebtAndCapitalLeaseObligations[IncludingCurrentMaturities]` turned out to have broad,
  genuine coverage once it could be added safely (ACN, APH, JBL, MU, NXPI).
- **Improved but not fully clean: 4 of 36 — GLW** (LongTermDebt resolved at 97%, but its
  separately-flagged Capex gap is untouched by this task and remains a real gap with no candidate),
  **KEYS** (DepreciationAndAmortization resolved at 98%, NetIncomeLoss untouched), **Q** (LongTermDebt
  rose 10%→40%, still below the threshold — Q's short 10-quarter history limits how much any tag
  addition can help), and **MTB** (DepreciationAndAmortization resolved at 96%, Revenue still at 1%
  — no LongTermDebt/D&A-shaped fix touches MTB's Revenue gap, which was always a different,
  unrelated problem per Run 2's findings).
- **Unchanged: 22 of 36** — matches the Run-2 report's own conclusions closely: `OperatingIncomeLoss`
  structural gaps (FLEX, IBM, KLAC, Q) are untouched as expected (no tag exists to add regardless
  of merge mechanics); `Goodwill` (AXP), `Capex` (GLW, IT, Q), `CashAndEquivalents` (GDDY, Q),
  `SharesOutstanding` (WDAY), `NetIncomeLoss` (KEYS, Q), `OperatingCashFlow` (Q), and bank `Revenue`
  (TFC, FITB, HBAN, RF, BNY, MTB) gaps were never LongTermDebt/D&A problems in the first place, so
  this task's fix — scoped only to those two concepts, as instructed — correctly leaves them
  alone. The remaining unresolved `LongTermDebt` tickers (ADI, ANET, CDNS, FFIV, FTNT, MPWR, PLTR,
  PTC, SNDK, SWKS, TYL) simply don't report `LongTermDebtAndCapitalLeaseObligations[...]` at all —
  the new sources had nothing to find there, consistent with Run 2's original per-ticker findings.

## Part D — Cleanup

Checked all of `config.py` for other consumers of `fallback_sum`/`fallback_then_sum`/plain `sum`
mode (`grep -n '"mode":' config.py`) — confirmed `LongTermDebt` and both `DepreciationAndAmortization`
entries were the *only* concepts using `fallback_then_sum`/`fallback_sum`; no plain `"sum"` mode
is used anywhere. All three have now been migrated. Per the task's instruction, the old
`fallback_then_sum`/`fallback_sum` branches in `extract_with_mode` were **left in place** as dead
code rather than removed — nothing currently depends on them, but deletion wasn't the goal of
this task and there's no cost to leaving them for a possible future concept that wants that
simpler (if flawed) behavior.

## Open questions for the human reviewer

1. **GLW's Capex gap (3/71, 4%) is untouched** — this task only migrated `LongTermDebt` and
   `DepreciationAndAmortization`. If `Capex` or other concepts have similar "sum tags starved by
   the wrong merge semantics" problems, they'd need the same `priority_merge` migration treatment,
   evaluated on their own.
2. **The 11 tickers whose `LongTermDebt` gap is still unresolved** (ADI, ANET, CDNS, FFIV, FTNT,
   MPWR, PLTR, PTC, SNDK, SWKS, TYL) don't have `LongTermDebtAndCapitalLeaseObligations` data at
   all — worth a follow-up tag search specifically for these, now that the merge mechanism itself
   is no longer the blocker.
3. **Bank `Revenue` (TFC, FITB, HBAN, RF, BNY, MTB, SYF)** remains the largest unresolved block —
   per Run 2's findings this was never a merge-mechanics problem (every candidate found was a
   fee/interest-income component, not the total), so it's out of scope for a structural fix and
   needs either a real tag search continuation or a manual look at those filings.

No scratch scripts were left behind.
