# Task: Insurance (P&C) Tag Coverage Scan — CB, PGR, ALL, AIG, WRB, CINF, ACGL, HIG, L, EG

TRV is the fully verified reference ticker for the `insurance_pc` profile. Its seven
concepts and nine fundamentals + five valuation metrics are built and confirmed correct
(see the session history: `EarnedPremiums`, `IncurredLosses`, `BenefitsLossesAndExpenses`,
`NetInvestmentIncome`, `Investments`, `ClaimsReserve`, `RealizedInvestmentGains`, plus
`Goodwill` shared from the base config). The goal now is to check whether the same
tag names give clean, complete coverage for the other ten `insurance_pc` tickers — and
where they don't, find and safely apply replacements or additions, exactly like the
Banks/Tech follow-up task.

## Ticker set

CB, PGR, ALL, AIG, WRB, CINF, ACGL, HIG, L, EG — all already listed as `insurance_pc` in
`TICKER_PROFILES`. Fetch/cache each ticker's `company_info.json` if not already cached.

## Step 1 — Coverage scan

For each of the 10 tickers, run `check_data_quality` using `get_expected_concepts(ticker)`
(this already resolves the `insurance_pc` overlay correctly — verify it does, given this
profile is new). Flag anything below 50% coverage, **excluding** `DividendsPerShare`
(same rule as the pilot — non-payers are expected to show 0%).

## Step 2 — For each flagged concept, search and evaluate candidates

Reuse the full established methodology from the prior scan tasks:

- `search_tags` with the concept's `SEARCH_HINTS` entry, plus one broader pass if the
  hints return nothing (same as done for the 11 remaining `LongTermDebt` tickers).
- Reject on **name semantics** even with clean numbers — insurance tagging has its own
  version of this trap. Watch specifically for:
  - `Ceded*` / `Assumed*` prefixes (reinsurance-adjusted views — usually NOT what a
    "net" concept wants unless the ticker's *only* net-equivalent tag is a Ceded/Assumed
    combination that needs summing — verify, don't assume).
  - `Direct*Written` / `Direct*Earned` (direct-only, excludes assumed reinsurance —
    typically a subset, not the total, unless it's the only premium tag the company has).
  - `SupplementaryInsuranceInformation*` tags — these are segment/footnote disclosures,
    not necessarily the consolidated figure. Check whether the segment sum matches the
    consolidated total before treating one as equivalent to the other.
  - Bracket/reserve *component* tags (e.g. IBNR-only, case-reserve-only) that are a
    **piece** of `LiabilityForClaimsAndClaimsAdjustmentExpense`, not a replacement for it.
  - Realized/unrealized investment gain-loss variants — same "which one is the total,
    which are stale predecessor tags" pattern seen with TRV's three candidates. Verify
    which is current and complete the same way (check for identical overlapping values
    between old and new tag names, favor the one with continuous, current coverage).
- **Combined Ratio and its components are the highest-value target.** If
  `BenefitsLossesAndExpenses` doesn't exist for a given ticker, check whether the
  company instead reports separate `Losses` and `Underwriting/Policy Acquisition
  Expense` tags that could be summed to reconstruct it — but only if you can verify
  the sum is genuinely additive (no overlap with a tag that already includes both), the
  same discipline used for the bank Revenue sum investigation. If no clean
  reconstruction is possible, report the ticker's combined/loss/expense ratios as
  "not currently buildable" rather than forcing an approximation.
- Some of these insurers may have life/health sub-segments that report additional,
  irrelevant tags (several P&C-classified names — AIG, ALL — also carry legacy life
  business). Don't let that confuse the P&C-focused concepts; if a ticker's mix makes a
  concept genuinely ambiguous, flag it for a human decision rather than picking a side.

## Step 3 — Mode decisions, if needed

If a concept needs a `sum` or a lower-priority fallback tag (the same kind of decision
made for `LongTermDebt` and `DepreciationAndAmortization`), migrate that concept to
`priority_merge` using the same **two-step discipline** as yesterday:

1. If the concept is currently plain `fallback`, first restructure it to
   `sources`/`priority_merge` with **zero new tags**, and confirm byte-identical output
   for every ticker currently using that concept (all `insurance_pc` tickers plus TRV)
   before adding anything.
2. Only then add the new candidate tag(s), at the lowest priority (after everything
   already there), and re-run the full diff.

You are authorized to make these mode changes and apply tags directly — **on the
condition that the mandatory non-regression check (Step 4) passes for every single
change**. If a change would alter or remove any previously-populated value for TRV or
any other already-working ticker, do not keep it — revert that one change and log it
for manual review instead of forcing it through.

## Step 4 — Mandatory non-regression check (same rule as yesterday, no exceptions)

Before finalizing any config change:

1. Extract every affected concept for **all** cached tickers (not just the 10 new
   ones — TRV must be included, since it's the trusted reference and any regression
   there is the most important one to catch) under the old config and the new one.
2. Diff every `(ticker, concept, end)` value. Zero tolerance: any previously-populated
   value that changes or disappears means that specific addition is wrong — revert it,
   log exactly which ticker/date/concept was affected and why, and move on. Do not keep
   a change that "mostly" works.
3. Only previously-null values may newly appear. That's the expected, good outcome —
   report it, don't suppress it or force it to look identical to before.
4. If a mode migration in Step 3's sub-step 1 isn't byte-identical to the old mode, this
   is only acceptable if it's explainable by the *same* class of bug fixed yesterday (an
   all-or-nothing gate or a priority inversion) — not a new discrepancy you can't
   explain. If you can't explain a difference, don't proceed to Step 3's sub-step 2.

## Step 5 — Coverage re-check

After all safe changes are applied, re-run `check_data_quality` on the 10 tickers.
Produce a before/after coverage table like the previous follow-up report, plus a summary:
fully resolved, improved-but-not-clean, and unchanged (with the specific reason per
unchanged concept — structural gap vs. still needs a human tag decision).

## Output

One file, `insurance_pc_scan_report.md`: the scan findings, what was changed and why,
the non-regression check results (including anything reverted), and the before/after
coverage table. No scratch scripts left behind. Do not touch any ticker outside this
list of 10, and do not touch any concept unrelated to `insurance_pc`'s metric set.