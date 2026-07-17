# Task: Follow-Up on the Three Open Questions from priority_merge_report.md

Three independent sub-tasks. Do them in order — A is quick and may turn out to
be a non-issue; B and C are real tag hunts that reuse the established
methodology (`search_tags` + `SEARCH_HINTS`, the five compatibility criteria,
the four pilot learnings about flow-vs-balance/forward-looking/name-sanity/
overlap-≠-additive) from the scan tasks. Every config change, in every part,
must pass the same non-regression discipline used in the last two tasks:
diff every `(ticker, concept, end)` value across the full known ticker
universe (all cached `company_info.json` files plus everything in
`TICKER_PROFILES`) before vs. after, zero tolerance for any previously-
populated value changing or disappearing, only new fills are acceptable.

## Part A — Confirm no other concept has the same architecture bug

`priority_merge_report.md` Part D already confirmed via `grep` that
`LongTermDebt` and both `DepreciationAndAmortization` entries were the only
users of `fallback_then_sum`/`fallback_sum`. This part is a second, more
careful pass — grep alone proves no *other* concept uses those two mode
*names*, but doesn't prove no other concept has a similar underlying symptom
under a different mode.

1. For every concept in `CONCEPT_CANDIDATES` and every `PROFILE_CONCEPT_OVERRIDES`
   entry, check its `mode`. Plain `fallback` and `sum` do not have the
   architecture bug (both already operate per-date with a single tier), so
   they don't need migration. Confirm there are genuinely no other
   `fallback_then_sum`/`fallback_sum` users (re-verify the report's grep
   result directly rather than trusting it blindly).
2. Separately, revisit `GLW`'s `Capex` gap (3/71, 4%) specifically, since it's
   the open question's example. Per Run 2's own finding, every `Capex`
   candidate for GLW was either a wrong-direction PP&E-disposal tag or failed
   the period filter — i.e., this was already established as "no viable
   candidate exists," not a merge-mechanics problem. Confirm this conclusion
   still holds (a quick re-check of `Capex`'s current `mode` — if it's plain
   `fallback`, the architecture fix is irrelevant here and the gap is a
   genuine no-candidate case, not something Part A can help with).
3. If step 1 finds no other affected concept and step 2 confirms GLW's Capex
   gap is a genuine no-candidate case: **close this question with a short
   note, make no config changes for Part A, and move to Part B.** Do not
   invent work here — if there's nothing to migrate, say so plainly.
4. If step 1 *does* find another concept with the same symptom (a ticker with
   partial primary-tag coverage where a configured fallback/sum tag is
   structurally unreachable), migrate it to `priority_merge` using the same
   staged B1 (byte-identical proof, no new tags) → B2 (extend) process as the
   previous task, each step separately verified.

## Part B — Targeted LongTermDebt search: the 11 remaining tech tickers

`ADI, ANET, CDNS, FFIV, FTNT, MPWR, PLTR, PTC, SNDK, SWKS, TYL` — confirmed by
the last task's report to have no `LongTermDebtAndCapitalLeaseObligations[...]`
data at all. The merge mechanism is no longer the blocker for these; the
question is purely whether a different tag exists.

1. For each of the 11, run `search_tags` with the current `LongTermDebt`
   `SEARCH_HINTS` entries, plus one broader pass using just `["debt"]` and
   `["notes"]` individually (accept the noise — with only 11 tickers this is
   affordable to review by hand, unlike a full S&P scan) to catch anything
   the narrower hints might have missed.
2. Apply the same rejection rules as before: forward-looking maturity-
   schedule tags, cash-flow proceeds/repayments (flow, not balance) tags,
   fair-value-basis tags, name-mismatch tags (read the name even when the
   numbers look clean) — all rejected regardless of coverage/magnitude
   scores. Apply the "overlap ≠ additive" rule to anything that overlaps an
   existing source with different values.
3. For anything that survives: add it to that concept's `sources` list at
   lowest priority (after everything currently there, including the two
   capital-lease tags from the last task) and run the full non-regression
   diff. If it introduces any regression, remove it and log why rather than
   forcing it through.
4. Some of these 11 may genuinely have no usable tag (Run 2 already suggested
   several, e.g. PLTR, are simply low-debt companies with sparse reporting).
   That's an acceptable outcome — report it as such per ticker, don't strain
   to find a candidate that isn't there.

## Part C — Bank Revenue gap: try a genuine sum, not just another single tag

`TFC, FITB, HBAN, RF, BNY, MTB, SYF` — Run 2 found only revenue *components*
(interest income alone, or a single fee line) for these, never a total. A
single-tag fallback can't fix this; a bank's total revenue is structurally
`NetInterestIncome + NoninterestIncome`, which `priority_merge`'s `"sum"`
source type can express *if* both components are reliably tagged for these
banks and the sum is genuinely additive (not double-counting a tag that
already includes both pieces).

1. **Validate the approach on a bank that already works, before touching the
   broken ones.** For JPM (or another bank with a clean `Revenue` value via
   `RevenuesNetOfInterestExpense`), pull the raw values of whatever tags
   correspond to net interest income and noninterest income (`NetInterestIncome`
   / `InterestIncomeExpenseNet` and `NoninterestIncome`, or their raw XBRL
   equivalents) for the same dates, and confirm
   `interest_component + noninterest_component ≈ RevenuesNetOfInterestExpense`
   (allow a small tolerance — a few percent — for rounding/other adjustments).
   If this doesn't hold reasonably closely, the sum approach is unsound and
   Part C should stop here with that finding reported, rather than applying
   an unvalidated formula to the broken banks.
2. If validated: for each of the 7 tickers, check whether it reports both an
   interest-income(-net) tag and a noninterest-income tag with reasonable
   coverage (use `search_tags` with `["interestincome", "interestexpensenet"]`
   and `["noninterestincome"]`, consistent with the existing `SEARCH_HINTS`
   entries for `NetInterestIncome`/`NoninterestIncome`).
3. For any ticker where both components are present and cover a meaningful
   number of periods: add a `{"type": "sum", "tags": [interest_tag,
   noninterest_tag]}` source to that ticker's effective `Revenue` config
   (the `financial` profile override) at the lowest priority (after the
   existing single-tag entries), non-regression-test it as usual, and report
   the resulting coverage.
4. For tickers where the components aren't both cleanly available, or where
   step 1's validation doesn't hold well enough to trust the formula: do not
   guess. Report as still-unresolved with the specific reason (missing
   component / validation didn't hold / etc.) rather than adding a shaky sum.
5. **Note on scope:** this changes the `financial` profile's shared `Revenue`
   config, which every bank in `TICKER_PROFILES` uses — the non-regression
   diff must cover all of them (JPM included), not just the 7 target tickers,
   since a new low-priority sum source could in principle also fire for a
   bank that wasn't part of this investigation if it happens to have a gap
   too. That's fine if it only fills gaps, but it must be verified, not
   assumed.

## Output

One file, `followup_report.md`, with one section per part (A, B, C), each
reporting: what was checked, what was found, what was added (if anything)
with its regression-test result, and what remains unresolved with a specific
reason. If a part concludes "nothing to do," say so briefly rather than
padding it. No scratch scripts left behind.