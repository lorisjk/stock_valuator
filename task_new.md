# Task: Fix Valuation-History Coupling Bug (One Missing Concept Kills Unrelated Multiples)

## Context

V (Visa) and STZ (Constellation Brands) both have a genuine, confirmed, unfixable gap in
`SharesOutstanding` (EDGAR/XBRL side — not the separate yfinance-sourced `shares_outstanding`
used for `market_cap`). Both were pulled from production for this reason. But investigating V's
charts surfaced something bigger than "the metrics that need `SharesOutstanding` are empty, as
expected": **every single valuation multiple was empty** — `pe_ratio`, `pb_ratio`,
`pfcf_ratio`, `ev_ebitda`, `ev_sales`, `peg_ratio`. Only `dividend_yield` survived.

This is wrong. `ev_ebitda` and `ev_sales` need `market_cap` (from yfinance, present) and
net-debt/EBITDA or revenue — **neither needs `SharesOutstanding` or `EPS_TTM_CALC` at all.**
`pb_ratio` needs `market_cap` and `StockholdersEquity`, not EPS. The fact that these are also
empty for V strongly suggests `build_valuation_history()` merges all the TTM concepts needed
across *every* multiple through a shared join, so a ticker missing even one input concept
entirely (here, `SharesOutstanding` → `EPS_TTM_CALC`) loses every row for every multiple, not
just the ones that actually depend on the missing piece.

**This is an architecture bug, not a per-ticker data gap**, and it may silently affect other
tickers with a gap in any single concept the valuation pipeline touches — not just V/STZ, and
not just `SharesOutstanding`.

## Step 1 — Confirm the root cause by reading the actual code

Read `build_valuation_history()` (and anything it calls) in full. Identify exactly how the
individual concepts (`market_cap`, `EPS_TTM_CALC`, `FFO_TTM`, `StockholdersEquity`,
`net_debt`, `ebitda`, `Revenue_TTM`, `fcf`, etc.) are combined before each ratio is computed.
Confirm directly (don't assume) whether this uses one shared merge across all concepts (e.g. a
single wide dataframe built via repeated inner joins or a `pd.concat`/`pivot` step that drops
any row missing a value in *any* column) versus independent per-ratio merges.

Reproduce the V failure by hand: trace what happens when `EPS_TTM_CALC` has zero rows for a
ticker, and confirm exactly which downstream step causes `ev_ebitda`/`ev_sales`/`pb_ratio` to
also come out empty as a consequence, even though their own required inputs are present.

## Step 2 — Scope-check: does this affect any other cached ticker?

Before fixing anything, check whether any other currently-active ticker has a similarly severe
gap in any single concept the valuation pipeline touches (not just `SharesOutstanding`/
`EPS_TTM_CALC` — check `StockholdersEquity`, `Revenue_TTM`, `FFO_TTM`, `net_debt`/`ebitda`
inputs, etc. too). For each candidate found, confirm whether it shows the same "everything
downstream is empty" symptom, the same way V does. Report the full list — this determines
whether the fix's impact is narrow (just V/STZ, already excluded) or broader (other active
tickers currently showing incorrectly-empty valuation charts without anyone having noticed).

## Step 3 — Design and implement the fix

Rework the valuation-history construction so each multiple is computed from **only the
concepts it actually needs**, independently of whether unrelated concepts are present for that
ticker/period. A ticker missing `SharesOutstanding` should still get `ev_ebitda`, `ev_sales`,
`pb_ratio`, `dividend_yield` computed normally — only `pe_ratio`, `pfcf_ratio` (if it uses EPS
rather than FCF per share — verify which inputs it actually needs), and `peg_ratio` (which
likely depends on `pe_ratio`) should come out empty for that specific reason.

Be precise about which multiples genuinely share a dependency (e.g. `peg_ratio` legitimately
needs `pe_ratio`, so it should stay empty whenever `pe_ratio` is) versus which were only
empty because of an overly-broad shared merge. Don't just loosen every join blindly — verify
each multiple's real input requirements from the actual formula in the code before deciding
whether it should be affected by a given missing concept.

## Step 4 — Verify against V and STZ

Even though both are currently excluded from production, use them as the clearest available
test cases (their cached data still exists). After the fix, confirm:
- `pe_ratio`, `pfcf_ratio` (if EPS-dependent), `peg_ratio` remain correctly empty for V/STZ
  (the genuine, unfixable gap).
- `ev_ebitda`, `ev_sales`, `pb_ratio`, `dividend_yield` now populate correctly with real,
  plausible values for both tickers.

## Step 5 — Verify against any other tickers found in Step 2

Apply the same before/after check to every ticker Step 2 flagged as similarly affected.

## Step 6 — Mandatory non-regression check (this touches a shared base function)

1. Extract every valuation multiple for every cached ticker across every profile, before and
   after.
2. For every ticker that was **not** flagged in Step 2 (i.e., already had complete data), every
   multiple's value must be byte-identical before and after — confirm this directly across the
   full universe, not just a sample.
3. For every ticker that **was** flagged, confirm only the previously-wrongly-empty multiples
   now show real values, and the genuinely-dependent ones remain correctly empty.

## Document

Add to `bugfixed_update_history.md`: the root cause (the shared-merge coupling), the fix
(per-multiple independent computation), the full scope-check results from Step 2, and the
before/after for every affected ticker.

## Output

One file, `valuation_history_coupling_fix_report.md`: the confirmed root cause with the V
failure traced step by step, the Step 2 scope-check results (full ticker list, even if empty),
the fix implementation, the V/STZ and any-other-ticker verification, and the full
non-regression results.

No scratch scripts left behind. Do not reassign any ticker's profile or change any
`TICKER_PROFILES`/`TICKER_CONCEPT_OVERRIDES` entry — this task fixes the valuation-history
construction logic itself, not any tag configuration.