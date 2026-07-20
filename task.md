# Task: Retail Tag Coverage Scan (18 tickers) + Equity-Denominator Masking Guard

This task has two independent parts. Part A extends the `retail` profile's tag coverage
to the remaining 18 tickers. Part B fixes a denominator-near-zero explosion bug discovered
in ORLY that affects any profile using `StockholdersEquity` as a ratio denominator, not
just retail. Do not conflate the two — they touch different files and have separate
non-regression checks.

---

## PART A — Retail Tag Coverage Scan

ORLY is the fully verified reference ticker for the `retail` profile. Its four new
concepts (`Inventory`, `CostOfRevenue`, `AccountsReceivable`, `AccountsPayable`) and five
new fundamental metrics (`inventory_turnover`, `dio`, `dso`, `dpo`,
`cash_conversion_cycle`) are built and confirmed correct (see session history — tags
`InventoryNet`, `CostOfGoodsAndServicesSold`, `AccountsReceivableNetCurrent`,
`AccountsPayableCurrent`, plus everything ORLY inherits unchanged from the base
`CONCEPT_CANDIDATES`). The goal is to check whether the same tag names give clean,
complete coverage for the other 18 `retail` tickers — and where they don't, find and
safely apply replacements or additions, exactly like the insurance_life follow-up task.

### Ticker set

AZO, BBY, GPC, HD, LOW, LULU, NKE, POOL, RL, ROST, TJX, TSCO, ULTA, WSM, DECK, TPR, HAS,
GRMN — confirm all 18 are listed as `retail` in `TICKER_PROFILES` (ORLY should already be
there too). Fetch/cache each ticker's `company_info.json` if not already cached.

### Step 1 — Coverage scan

For each of the 18 tickers, run `check_data_quality` using `get_expected_concepts(ticker)`.
Flag anything below 50% coverage, **with these expected exceptions that are not bugs**:

- `DividendsPerShare` at 0% for any non-payer (same rule as always).
- `AccountsReceivable` at or near 0% for pure consumer-cash retailers where card/cash
  checkout means no meaningful trade receivable line exists: ORLY, AZO, ROST, TJX, ULTA,
  TSCO, WSM are expected candidates for this — confirm low coverage here is a real business
  characteristic, not a missed tag, before excluding it. Conversely, HD, LOW, GPC, NKE,
  GRMN, HAS, DECK, TPR run B2B/pro-contractor/wholesale channels and **should** show real
  AccountsReceivable coverage — if any of these come up empty, that's a genuine gap to
  investigate, not an expected exception.

### Step 2 — For each flagged concept, search and evaluate candidates

Reuse the full established methodology from the P&C and insurance_life scans, plus these
retail-specific traps:

- **Inventory tag primacy.** `InventoryNet` is the clean primary tag for most large
  retailers. Only fall back to `InventoryFinishedGoodsNetOfReserves` /
  `InventoryFinishedGoods` if `InventoryNet` is genuinely absent for that ticker's full
  history, not just less frequently used in some periods. Do not sum these — they are
  alternate names for the same fact, never additive.
- **CostOfRevenue naming convergence.** `CostOfGoodsAndServicesSold` vs
  `CostOfGoodsSold` vs `CostOfRevenue` typically reflect a taxonomy-version relabeling
  across time (older filings use one, newer filings use another for the same underlying
  line) rather than two genuinely different figures. Treat as a `fallback` list (pick
  first available per period) — do not `sum`. Before accepting a fallback chain, check
  for any period where two of these tags appear simultaneously with materially different
  values; that would indicate a real double-count risk requiring manual review instead of
  a silent fallback.
- **Manufacturer/wholesale segment inventory caution (NKE, HAS, DECK, TPR, GRMN).** These
  five sell through both wholesale and direct-to-consumer channels and may report
  segment-level inventory or COGS tags alongside — or instead of — a clean consolidated
  figure. Same caution as MET/PRU's segment premiums in the insurance_life task: verify a
  segment sum actually reconciles to the consolidated total before treating it as
  equivalent. If no clean consolidated tag exists and segment reconciliation can't be
  verified, report "not currently buildable" rather than forcing an approximation.
- **Non-calendar fiscal years are expected, not a bug.** HD, LOW, TJX, ROST, BBY, WSM, and
  ULTA use fiscal years ending in late Jan/early Feb. This will show up as `end` dates
  clustered away from typical calendar quarter-ends — this is correct filing behavior, not
  a data quality issue. Do not attempt to force-align these to calendar quarters.

### Step 3 — Mode decisions, if needed

If a concept needs a `fallback` extension or a `priority_merge`-style layered fallback,
you're authorized to migrate it — **on the condition that the mandatory non-regression
check (Step 4) passes for every single change.** If a change would alter or remove any
previously-populated value for ORLY or any other already-working ticker, do not keep it —
revert that one change and log it for manual review instead of forcing it through.

### Step 4 — Mandatory non-regression check (same rule as every prior task, no exceptions)

1. Extract every affected concept for **all** cached retail tickers (ORLY included, as the
   trusted reference) under the old config and the new one.
2. Diff every `(ticker, concept, end)` value. Zero tolerance: any previously-populated
   value that changes or disappears means that specific addition is wrong — revert it, log
   exactly which ticker/date/concept was affected and why.
3. Only previously-null values may newly appear — report this as the expected, good
   outcome.
4. If you can't cleanly explain a discrepancy, don't proceed — log it as ambiguous rather
   than guessing which value is "correct."

### Step 5 — Coverage re-check

After all safe changes are applied, re-run `check_data_quality` on the 18 tickers. Produce
a before/after coverage table, plus a summary: fully resolved, improved-but-not-clean, and
unchanged (with the specific reason per unchanged concept, including the expected
AccountsReceivable exceptions from Step 1).

---

## PART B — Equity-Denominator Masking Guard

### Context

ORLY's `roe` and `debt_to_equity` briefly explode to economically meaningless magnitudes
(ROE ≈ −25,000%, D/E ≈ −600) around 2021 because `StockholdersEquity` — the denominator in
both ratios — approaches zero and briefly goes negative from aggressive share buybacks.
This is the same class of problem already solved once in this project: `calculate_growth`
got a `min_base_ratio=0.33` guard to suppress meaningless growth rates from near-zero
earnings bases. This is that same fix, applied to a different denominator.

**This is not retail-specific.** Any profile computing a ratio with `StockholdersEquity` or
`TangibleEquity` in the denominator is exposed to the same failure mode if a ticker's
equity ever approaches zero (buybacks, accumulated losses, etc.). Implement the guard
generically in `metrics.py`, not inside the `retail` profile config.

### Step 1 — Design the guard

Add a relative-threshold mask, following the same principle already used for
`min_base_ratio` (relative validity masks are more robust than absolute floors for
near-zero-denominator problems — same logic, different variable). Concretely:

- Introduce a new optional guard on ratio calculation — e.g. a `min_denominator_scale_ref`
  concept name and a `min_denominator_scale_ratio` threshold — that masks the output
  (returns NaN, does not drop the row) when `abs(denominator) < threshold * scale_reference`
  for that `(ticker, end)`.
- Use `Revenue_TTM` as the scale reference, since it's fetched for every profile
  (`standard`, `financial`, `insurance_pc`, `insurance_life`) unlike `Assets`, which is
  financial-profile-only. This keeps the guard usable everywhere without pulling a new tag
  into profiles that don't already have it.
- Apply the guard to: `roe` (StockholdersEquity denominator), `debt_to_equity`
  (StockholdersEquity denominator), and the snapshot-level `pb_ratio` and `p_tbv`
  (StockholdersEquity / TangibleEquity denominators respectively).

### Step 2 — Empirically tune the threshold

Same methodology as the `min_base_ratio` tuning: test the candidate threshold against
multiple tickers before finalizing.

- **Must suppress the outlier:** ORLY's 2021 explosion should be masked (NaN), not shown.
- **Must also check AZO** — structurally near-identical to ORLY (same aggressive-buyback
  profile) — confirm whether it shows the same near-zero-equity pattern; if so, the guard
  should suppress it there too without any special-casing per ticker.
- **Must NOT suppress legitimate values:** run the same threshold against GL (or whichever
  already-validated `insurance_life`/`financial` ticker has the smallest — but real and
  stable — equity base) and confirm no previously-valid ROE/D-to-E value gets masked.
  If the chosen threshold masks anything that was previously a clean, sane value anywhere
  in the already-validated ticker set, tighten the threshold and re-test — do not ship a
  threshold that trades a real fix for new false negatives elsewhere.

### Step 3 — Mandatory non-regression check

1. Extract `roe`, `debt_to_equity`, `pb_ratio`, `p_tbv` for **every already-validated
   ticker across every profile** (not just retail) under the old and new logic.
2. Diff every `(ticker, concept, end)` value. Zero tolerance outside the intended fix: any
   previously-populated value that changes, other than the specific outlier periods being
   intentionally masked, means the threshold is wrong — tighten it and re-test.
3. Report exactly which `(ticker, end)` pairs get newly masked, for every profile, so the
   change is fully auditable — not just for ORLY.

### Step 4 — Document the trade-off

Add an entry to `bugfixed_update_history.md` in the existing prose style, logging this as
a deliberate design compromise (same category as the two already logged): the threshold is
empirically tuned and may still mask a legitimate small-but-real equity value for some
future ticker not in the current test set. State the chosen threshold value and the
reasoning behind it.

---

## Output

Two files:

1. `retail_scan_report.md` — Part A findings: what was changed and why, non-regression
   check results (including anything reverted), before/after coverage table.
2. `equity_guard_report.md` — Part B findings: threshold chosen, tuning results across
   ORLY/AZO/reference ticker, full non-regression diff across all profiles, and the exact
   diff to be added to `bugfixed_update_history.md`.

No scratch scripts left behind. Do not touch any ticker outside the 18 retail tickers (Part
A) or any concept/metric unrelated to the equity-denominator guard (Part B). Do not touch
`Assets`-dependent logic in the `financial` profile — the guard must work without it.