# Quarterly Values Alongside TTM + Broad Growth Metrics + MAX_MULTIPLE Investigation

Three related parts executed against the live cached universe (498 active tickers, `get_active_tickers()`). All code changes are purely additive: no existing line in `add_derived_concepts()`, `calculate_all_metrics()`, `build_valuation_history()`, the pre-existing `build_metrics_long()` spec, or any `TICKER_PROFILES`/`TICKER_CONCEPT_OVERRIDES`/`PROFILE_HIDDEN` entry was modified. Non-regression was run after each part separately, and once more combined at the end (true pre-task baseline vs. final state), always via a full outer join on `(ticker, concept, end)` over every active ticker, never a sample.

---

## Part A — Quarterly (non-TTM) counterparts alongside the existing TTM values

### Step A1 — What already existed

`add_ttm_concepts(df, concepts)` (`metrics.py`) computes each `_TTM` series via `calculate_ttm()` and returns `pd.concat([df] + ttm_frames)`. This is non-destructive by construction: it only *appends* new `"{concept}_TTM"` rows: it never filters, drops, or overwrites the original plain-concept rows. Confirmed directly against cached data (not assumed):

```
TSLA concepts present in facts after the full pipeline (excerpt):
  Capex, Capex_TTM, ..., OperatingCashFlow, OperatingCashFlow_TTM, ...

OperatingCashFlow (plain quarterly)      OperatingCashFlow_TTM
2025-03-31   2,156,000,000                2025-03-31   16,837,000,000
2025-06-30   2,540,000,000                2025-06-30   15,765,000,000
2025-09-30   6,238,000,000                2025-09-30   15,748,000,000
2025-12-31   3,813,000,000                2025-12-31   14,747,000,000
2026-03-31   3,937,000,000                2026-03-31   16,528,000,000
2026-06-30   4,697,000,000                2026-06-30   18,685,000,000
```

The plain quarterly values are also already true single-quarter deltas, not YTD-cumulative figures: `fetchers/edgar.py`'s `extract_quarterly_values()` runs every flow concept through `decumulate_period_values()`, which subtracts the prior cumulative filing from the current one before the value ever reaches `facts`. So the "reporting view" is not just present, it is already correctly shaped.

**Finding:** every flow concept in `TTM_CONCEPTS` (`Revenue`, `NetIncomeLoss`, `OperatingIncomeLoss`, `OperatingCashFlow`, `Capex`, `DepreciationAndAmortization`, `DividendsPerShare`, `NetInterestIncome`, `NoninterestExpense`, `ProvisionForCreditLosses`, `NoninterestIncome`, `EarnedPremiums`, `IncurredLosses`, `BenefitsLossesAndExpenses`, `NetInvestmentIncome`, `RealizedInvestmentGains`, `CostOfRevenue`, `ResearchAndDevelopment`, `RealEstateDepreciation`, `GainLossOnSaleOfProperties`) already has a usable plain-quarterly value sitting in `facts`, already saved to `data/quarterly_facts.csv` (the `f"{PERIOD}_facts.csv"` output, `PERIOD="quarterly"`), already surviving `filter_hidden_rows()` unaffected (none of these raw concept names appear in any `PROFILE_HIDDEN` set). **Nothing needed to be added here — this settles Step A3's "metrics_long vs. quarterly_facts" question: quarterly_facts.csv is the existing, architecturally-correct home for these, and no further plumbing was required for them.**

What did **not** exist in quarterly form: the six *derived* concepts, since each is built exclusively from `_TTM` inputs in `add_derived_concepts()`/`calculate_all_metrics()`: `fcf`, `ebitda`, `EPS_TTM_CALC`, `PPNR`, `CoreOperatingEarnings`, `FFO_TTM`. And every metric in `calculate_all_metrics()` whose inputs are `_TTM` concepts.

### Classification (per concept/metric, reasoning first)

**Flow concepts already covered (no action needed, see above):** Revenue, NetIncomeLoss, OperatingIncomeLoss, OperatingCashFlow, Capex, DepreciationAndAmortization, DividendsPerShare, NetInterestIncome, NoninterestExpense, ProvisionForCreditLosses, NoninterestIncome, EarnedPremiums, IncurredLosses, BenefitsLossesAndExpenses, NetInvestmentIncome, RealizedInvestmentGains, CostOfRevenue, ResearchAndDevelopment, RealEstateDepreciation, GainLossOnSaleOfProperties.

**Balance/point-in-time concepts (already point-in-time; no "TTM version" to complement, correctly left alone, unaffected by this task):** SharesOutstanding, StockholdersEquity, Assets, Inventory, LongTermDebt, CashAndEquivalents, Goodwill, AccountsReceivable, AccountsPayable, Investments, ClaimsReserve.

**Derived concepts — meaningful, built (quarterly counterpart added):**
| Concept | Reasoning |
|---|---|
| `fcf` → `FCF_QUARTERLY` | The task's own motivating case. A flow-minus-flow difference; quarterly is exactly what a single earnings report shows. |
| `ebitda` → `EBITDA_QUARTERLY` | Same: flow ± flow. |
| `EPS_TTM_CALC` → `EPS_QUARTERLY_CALC` | NetIncomeLoss(q)/SharesOutstanding — quarterly EPS is the single most standard per-share figure companies report. |
| `PPNR` → `PPNR_QUARTERLY` | Bank pre-provision net revenue is routinely reported *quarterly* by banks — arguably more standard quarterly than TTM. |
| `CoreOperatingEarnings` → `CoreOperatingEarnings_QUARTERLY` | Insurer "core/operating earnings" (ex-realized-gains) is a standard quarterly non-GAAP disclosure. |
| `FFO_TTM` → `FFO_QUARTERLY` | FFO is THE headline REIT metric and REITs report it quarterly, arguably more standard quarterly than TTM. |

**Metrics in `calculate_all_metrics()` whose inputs are `_TTM` concepts — classified:**

*Ratio of two flows → meaningful, quarterly counterpart built* (a quarterly margin/ratio is standard and decision-useful on its own):
`operating_margin`, `payout_ratio`, `fcf_margin`, `efficiency_ratio`, `provision_ratio`, `combined_ratio`, `loss_ratio`, `expense_ratio` (derived from the two above), `rd_intensity`, `capex_intensity`, `ffo_margin`.

*Ratio mixing a flow with a point-in-time balance item → NOT built, flagged per the task's explicit instruction* (annualizing/using a single quarter's flow against a balance-sheet snapshot is a materially different, debatable choice from the TTM version, exactly the `roe` example in the task):
- `roe` (NetIncomeLoss/StockholdersEquity)
- `net_debt_to_ebitda` (point-in-time net_debt / TTM ebitda — a quarterly ebitda substituted directly would understate leverage by ~4x without an explicit annualization step the codebase doesn't make anywhere else)
- `net_interest_margin`, `roa`, `net_investment_yield` (same flow/balance-mix shape as `roe`)
- `inventory_turnover`, `dio`, `dso`, `dpo`, `cash_conversion_cycle` (all flow/balance-mix turnover ratios; conventionally computed on an annual/TTM basis by definition, not a standard quarterly figure)

*Deliberately deferred, with reasoning stated rather than silently built or silently skipped:*
- `rule_of_40` (= `revenue_growth` + `fcf_margin`): a quarterly version would need Part B's quarterly revenue-growth series as an input, which does not exist until Part B runs. Building it prematurely (e.g. against a TTM growth rate) would produce an internally inconsistent hybrid. Not built in Part A; not revisited in Part B either, since Part B's own scope is "extend `calculate_growth`", not "extend `rule_of_40`" — left as a considered, documented exclusion rather than silent scope creep.
- `operating_leverage` (= growth ratio ÷ growth ratio): same reasoning — depends on two growth series, and building a "quarterly operating leverage" was never explicitly requested; left TTM-only with the same rationale.

**Valuation layer (`build_valuation_history`, `pe_ratio`/`pb_ratio`/`pfcf_ratio`/`ev_ebitda`/`ev_sales`/`peg_ratio`/etc.):** untouched, per the task's explicit instruction. Not a single line of `build_valuation_history()` was changed.

### Step A2 — Implementation

Two new functions in `main.py`, both purely additive (never modify `facts`/`metrics` in place, only `pd.concat`/new dict entries):

- **`add_quarterly_derived_concepts(facts)`** — mirrors `add_derived_concepts()` exactly, built from plain (already-quarterly) concepts instead of `_TTM` ones. Adds `EPS_QUARTERLY_CALC`, `PPNR_QUARTERLY`, `CoreOperatingEarnings_QUARTERLY`, `FFO_QUARTERLY` to `facts`.
- **`calculate_quarterly_metrics(facts)`** — mirrors the relevant subset of `calculate_all_metrics()`. Returns `fcf_quarterly`, `ebitda_quarterly` (added to `facts` as `FCF_QUARTERLY`/`EBITDA_QUARTERLY` via the existing `add_as_concept()` mechanism, exactly like `FCF_TTM`/`EBITDA_TTM` already are) plus the 11 quarterly ratio metrics above.

Naming convention mirrored exactly: facts-level derived concepts get `_QUARTERLY` (matching the existing `_TTM` suffix style, e.g. `FCF_TTM` → `FCF_QUARTERLY`); metric-level results get `_quarterly` (matching the existing lowercase metric-name style, e.g. `operating_margin` → `operating_margin_quarterly`).

`build_metrics_long()` gained an optional second parameter `quarterly_metrics: dict = None`; when omitted, behavior is byte-for-byte identical to before (this is what the non-regression check below verifies). `config.is_hidden()` was extended to strip a trailing `"_quarterly"` before checking `PROFILE_HIDDEN`, so e.g. `operating_margin_quarterly` is hidden for exactly the profiles that already hide `operating_margin` — a no-op for every pre-existing (non-suffixed) metric name, since `base_name == metric_name` whenever there is no suffix to strip. `_DERIVED_CONCEPT_CONSUMERS` gained six new keys (`EPS_QUARTERLY_CALC`, `PPNR_QUARTERLY`, `CoreOperatingEarnings_QUARTERLY`, `FFO_QUARTERLY`, `FCF_QUARTERLY`, `EBITDA_QUARTERLY`), each pointing at the same consumer list as its TTM sibling, so e.g. `PPNR_QUARTERLY` is hidden under exactly the condition `PPNR` already is.

### Step A3 — Wiring into output and plotting

- **Data layer:** `quarterly_facts.csv` already carried the raw flow concepts (Step A1). The six new derived concepts now flow into it the same way `FCF_TTM`/`EBITDA_TTM` already did. The 11 new quarterly ratio metrics flow into `metrics_long.csv` via the extended `build_metrics_long()`.
- **Charts — two lines on the same panel, not a separate panel per pair.** Reasoning: each of the 11 quarterly ratio metrics is the *same underlying quantity* as its existing TTM panel, just at a different smoothing window — exactly the "before it has persisted long enough to drag the TTM sum" story the task opens with. Putting them on the same axes makes that story visible directly (see the `fcf_margin` panel below); a separate panel per pair would double the fundamentals grid without adding a distinct axis of comparison. `figures.plot_metric_dual()` was added (new function, `plot_metric()` itself untouched) and `plot_fundamentals()` now dispatches to it for the 11 paired concepts via a new `QUARTERLY_COUNTERPART` map, falling back to the original, byte-for-byte-unchanged `plot_metric()` call for every other panel.

Rendered and visually verified (TSLA, O, JPM `_fundamentals.png`): TTM line unchanged in shape/scale; new "Quartal" line overlaid in a lighter weight, with a legend. `fcf_margin` for TSLA now visibly shows the quarterly line diving sharply negative in isolated quarters that the TTM line smooths straight through.

### Step A4 — Verification against the motivating case

Ran the actual patched `add_quarterly_derived_concepts()`/`calculate_quarterly_metrics()` against the full cached universe (not a mock), then read back TSLA's own numbers directly:

```
TSLA FCF_QUARTERLY (last 6 quarters)      TSLA FCF_TTM (last 6 quarters)
2025-03-31    664,000,000                 2025-03-31   6,780,000,000
2025-06-30    146,000,000                 2025-06-30   5,586,000,000
2025-09-30  3,990,000,000                 2025-09-30   6,834,000,000
2025-12-31  1,420,000,000                 2025-12-31   6,220,000,000
2026-03-31  1,444,000,000                 2026-03-31   7,000,000,000
2026-06-30 -1,092,000,000                 2026-06-30   5,762,000,000
```

Confirmed exactly as the task described: TSLA's most recent quarter (2026-06-30) shows **negative** quarterly FCF (-$1.092B, from OperatingCashFlow $4.697B − Capex $5.789B), while TTM FCF at the same date is still **positive** ($5.762B) — the two series tell the different, complementary stories they should. The negative quarter is invisible in the TTM series and fully visible in the new quarterly series.

### Step A5 — Non-regression for Part A

Full-universe (498/498 active tickers) before/after, outer join on `(ticker, concept, end)`, comparing the *actual unmodified* `add_derived_concepts()`/`calculate_all_metrics()`/`build_metrics_long()` (called with no new arguments — before) against the same functions plus the two new ones (after):

| | removed | added | changed |
|---|---|---|---|
| `facts` | **0** | 113,585 (6 new concepts × up to 498 tickers) | **0** |
| `metrics_long` | **0** | 137,100 (11 new metrics × up to 498 tickers) | **0** |

Zero rows removed, zero rows changed, in either output, across the entire active universe. No duplicate `(ticker, concept, end)` rows introduced. Every added row traces to one of the 6 new facts concepts or 11 new metrics listed above.

---

## Part B — Apply `calculate_growth` broadly, with per-concept guard calibration

### Step B1 — Which concepts get a growth series

Extended from 4 (`Revenue_TTM`, `NetIncomeLoss_TTM`, `OperatingIncomeLoss_TTM`, `ClaimsReserve` — all four left completely untouched, still called directly inside `calculate_all_metrics()`) to 33 new series via a new `GROWTH_CONCEPTS` list and `calculate_broad_growth(facts)` in `main.py`.

**Point-in-time/balance concepts (10)** — plain value, 4-period (~1yr) offset, snapshot-to-snapshot is exactly what "growth" should mean for these:
`SharesOutstanding`→`shares_outstanding_growth` (dilution/buybacks), `StockholdersEquity`→`equity_growth` (book value), `LongTermDebt`→`debt_growth`, `CashAndEquivalents`→`cash_growth`, `Goodwill`→`goodwill_growth`, `Inventory`→`inventory_growth` (stock build), `AccountsReceivable`→`accounts_receivable_growth`, `AccountsPayable`→`accounts_payable_growth`, `Investments`→`investments_growth`, `Assets`→`assets_growth`.

**Flow concepts (20)** — `_TTM` form, matching the existing `revenue_growth`/`income_growth` pattern (TTM already de-seasonalizes, so a 4-period offset is like-for-like):
`OperatingCashFlow_TTM`→`ocf_growth`, `Capex_TTM`→`capex_growth`, `DepreciationAndAmortization_TTM`→`da_growth`, `DividendsPerShare_TTM`→`dividends_per_share_growth` (task's own example: "a genuinely important metric on its own"), `NetInterestIncome_TTM`→`nii_growth`, `NoninterestIncome_TTM`→`noninterest_income_growth`, `NoninterestExpense_TTM`→`noninterest_expense_growth`, `ProvisionForCreditLosses_TTM`→`provision_growth`, `EarnedPremiums_TTM`→`earned_premiums_growth`, `IncurredLosses_TTM`→`incurred_losses_growth`, `BenefitsLossesAndExpenses_TTM`→`benefits_losses_growth`, `NetInvestmentIncome_TTM`→`net_investment_income_growth`, `CostOfRevenue_TTM`→`cost_of_revenue_growth`, `ResearchAndDevelopment_TTM`→`rd_growth`, `RealEstateDepreciation_TTM`→`real_estate_depreciation_growth`, `FCF_TTM`→`fcf_growth`, `EBITDA_TTM`→`ebitda_growth`, `FFO_TTM`→`ffo_growth`, `PPNR`→`ppnr_growth`, `CoreOperatingEarnings`→`core_earnings_growth`.

**Single-quarter YoY (3)** — plain value, the standard "revenue grew X% YoY" figure companies report in earnings releases, deliberately distinct from the existing TTM-based growth series (closes the loop with Part A's quarterly reporting view):
`Revenue`→`revenue_quarterly_yoy_growth`, `NetIncomeLoss`→`income_quarterly_yoy_growth`, `OperatingIncomeLoss`→`operating_income_quarterly_yoy_growth`.

**Concluded NOT meaningful (excluded, with reasoning):**
- **`GainLossOnSaleOfProperties_TTM`** — a one-off, opportunistic property-disposal gain/loss line. `calculate_growth`'s own `valid_base` check already requires both the current and prior value to be positive, so a sign-flipping, frequently-negative line like this would produce a mostly-empty, uninterpretable series even with the guard disabled — not a "meaningful metric that got masked", just not a meaningful metric.
- **`RealizedInvestmentGains_TTM`** — same shape: an insurer's trading gains/losses line, not a recurring operating flow, frequently ≤0. Same exclusion reasoning.
- **`TangibleEquity`** — excluded as *redundant*, not meaningless: `TangibleEquity = StockholdersEquity − Goodwill`, so its growth is already implied by `equity_growth` and `goodwill_growth` together. Adding a third, derived series would be noise without new information.

### Step B2 — `min_base_ratio` guard calibration (empirical)

For every one of the 33 candidate concepts, computed `calculate_growth(..., min_base_ratio=0.0)` against the full cached universe, reconstructed the implicit `prev/value` ratio for every valid (both periods positive) period, and examined (a) what fraction of periods the default 0.33 guard currently masks, and (b) the shape of the masked-ratio distribution, looking for the same kind of clean gap used to calibrate every earlier guard in this project.

**Honest finding: no clean, single dominant gap exists for any concept checked.** The `prev/value` ratio distribution among masked periods is smooth and roughly continuous from ~0 up to 0.33 for every concept with a non-trivial mask count (10th percentile typically 0.04-0.08, median 0.19-0.24, 90th percentile 0.30-0.33) — there is no sharp bimodal split separating "obvious artifacts" from "obvious real jumps" in the ratio itself. This is itself useful evidence: it means a threshold choice here cannot be justified by "there's an obvious cliff at X", the way some earlier guards in this project could be. The chosen method instead:

1. Where the guard barely triggers at all in the current universe, there is no real-world problem to fix — keep 0.33 (this is exactly what the task predicted for `SharesOutstanding`/`StockholdersEquity`, and it matched: `SharesOutstanding` masked 5/29,686 valid periods = 0.02%, `StockholdersEquity` masked 365/28,351 = 1.3%. Both "rarely trigger", as predicted — keep 0.33, no change).
2. Where the concept is "earnings-like" — the exact case 0.33 was originally built for (per the task's own framing) — keep 0.33, since a near-zero prior-year base genuinely does make % growth meaningless for these: `Revenue`, `NetIncomeLoss`, `OperatingIncomeLoss`, `OperatingCashFlow_TTM`, `DepreciationAndAmortization_TTM`, `DividendsPerShare_TTM`, `FCF_TTM`, `EBITDA_TTM`, `NetInterestIncome_TTM`, `NoninterestIncome_TTM`, `NoninterestExpense_TTM`, `EarnedPremiums_TTM`, `IncurredLosses_TTM`, `BenefitsLossesAndExpenses_TTM`, `NetInvestmentIncome_TTM`, `CostOfRevenue_TTM`, `ResearchAndDevelopment_TTM`, `FFO_TTM`, `PPNR`, `CoreOperatingEarnings`, `AccountsReceivable`, `AccountsPayable`, `Investments`, `Assets`, `Inventory` (this last group masked 0 periods in the current data at all — no evidence to justify a change even though the task raised the general concern for `Inventory`).
3. Where the concept is lumpy, event-driven, or credit-cycle-driven — the task's own explicit framing for `Capex`/`Inventory`/`Goodwill`/`CashAndEquivalents` ("a 3x jump is entirely normal") — recalibrate. Since there's no statistical gap to cut at, the fallback is an economic-plausibility bound: an *organic* (non-M&A, non-restatement) single-year multiple beyond ~20x is implausible for an established, multi-year SEC-reporting company. `min_base_ratio=0.05` (a ~20x ceiling, vs. 0.33's ~3x ceiling) was applied to:

| Concept | Masked @ 0.33 | Masked @ 0.05 | Reasoning |
|---|---|---|---|
| `CashAndEquivalents` | 1,663 / 29,785 (5.6%) | 116 | Task-named example |
| `Goodwill` | 580 / 24,291 (2.4%) | 71 | Task-named example |
| `LongTermDebt` | 549 / 24,897 (2.2%) | 91 | Same lumpy/event-driven shape as Goodwill/Cash (debt issuances), extended by the same reasoning though not explicitly named |
| `Capex_TTM` | 240 / 24,031 (1.0%) | 19 | Task-named example |
| `ProvisionForCreditLosses_TTM` | 96 / 941 (10.2% — the highest mask rate of any concept checked) | 6 | Credit-cycle provisions genuinely swing from near-zero (benign credit environment) to material (a cycle turn) — exactly the "real, interesting movement" the task warns 0.33 would suppress, and empirically the concept the guard hits hardest |
| `Inventory` | 0 / 1,837 (0.0%) | 0 | Task-named example; recalibrated for consistency/forward robustness even though it doesn't change any value in the current data |

**Where 0.33 is right, it was kept — explicitly, not by default.** The three existing growth series (`revenue_growth`, `income_growth`, `operating_income_growth`) plus `reserve_growth` are **untouched**: still called directly in `calculate_all_metrics()`, never routed through the new broad-growth mechanism, guard unchanged. Confirmed byte-identical in the non-regression run below.

### Step B3 — Profile-aware plotting

**Data layer stays broad; charts stay conservative.** All 33 new growth series are computed and land in `metrics_long.csv` (and hence "analysis/snapshot output", per the task's own framing) for every ticker regardless of profile — cheap, and useful even where not charted. Plotting is gated through a new `config.get_growth_panels(ticker)`:

- **3 universal panels** (`GROWTH_BASE_PANELS`), relevant to every profile: `shares_outstanding_growth`, `equity_growth`, `debt_growth` — capital-structure trend applies regardless of sector.
- **0-2 profile-specific additions** (`GROWTH_PROFILE_EXTRA`), reasoned per group:
  - `retail`, `consumer_staples`, `homebuilder` → `inventory_growth` (stock build is the central working-capital question for these)
  - `pharma_medtech`, `health_services` → `rd_growth` (R&D reinvestment is the central growth-investment question)
  - `financial` → `nii_growth`, `provision_growth` (the two lines a bank's growth thesis actually turns on)
  - `insurance_pc`, `insurance_life` → `earned_premiums_growth`, `net_investment_income_growth` (underwriting + investment income growth; `reserve_growth` is not repeated here since it's already on the fundamentals chart)
  - `reit` → `ffo_growth`, `cash_growth` (FFO growth is the metric this sector is valued on)
  - capex-heavy sectors (`industrials`, `telecom_cable`, `railroads`, `airline`, `energy`, `energy_integrated`, `utilities`, `materials`, `materials_integrated`) → `capex_growth` plus a sector-fitting second panel (`ebitda_growth`, `assets_growth`, or `inventory_growth`)
  - asset-light/growth sectors (`standard`, `media`, `leisure`, `marketplace`, `captive_finance`, `alt_asset_manager`) → `fcf_growth`, `ebitda_growth`/`assets_growth`
  - Any profile not listed gets the 3 universal panels only — a conservative default, not an oversight.

Maximum 5 panels per ticker (3 base + 2 extra) — a handful, never a wall of charts. Rendered and visually verified: `O` (REIT) shows `ffo_growth` clearly (a sharp 2023 spike consistent with a real acquisition-driven jump); `TSLA` (industrials/standard-like) shows `debt_growth` spiking ~950% in 2024 from a real, near-zero-base debt raise — exactly the kind of event the 0.05 recalibration is meant to admit.

**Separate figure, not integrated into `plot_fundamentals`.** New `figures.plot_growth(ticker, metrics_long, output_path)`, saved as `{ticker}_growth.png`, called alongside `plot_fundamentals`/`plot_valuation` in both `main()` and `run_full_refresh()`. Reasoning: growth is a distinct analytical lens (rate-of-change vs. level/ratio), several profiles already render 15-20+ panels on the fundamentals chart, and a third figure keeps that chart's existing layout **exactly** unchanged (verified — the untouched `plot_metric()` code path is byte-for-byte identical for every panel without a quarterly counterpart) rather than competing for space. The new figure deliberately does not repeat `revenue_yoy_growth`/`income_yoy_growth`/`operating_income_yoy_growth`/`reserve_growth`, which already have their own panels on the existing fundamentals chart.

### Step B4 — Non-regression for Part B

See combined table below (Part B's diff is a strict superset check of Part A's: same `facts`, only `metrics_long` gains further additions). Verified specifically: `revenue_yoy_growth`, `income_yoy_growth`, `operating_income_yoy_growth`, `reserve_growth` all appear with **0 changed rows** in the diff — byte-identical, since neither their `calculate_growth()` call sites nor `min_base_ratio` were touched.

---

## Final combined non-regression (true pre-task baseline vs. final state, Parts A+B)

Same methodology, this time comparing the fully unmodified original pipeline (`add_derived_concepts` → `calculate_all_metrics` → `build_metrics_long()` with no new arguments) against the final pipeline (both new functions, `calculate_broad_growth`, extended `build_metrics_long()`), full 498-ticker universe:

| | removed | added | changed |
|---|---|---|---|
| `facts` | **0** | 113,585 | **0** |
| `metrics_long` | **0** | 590,453 | **0** |

Zero duplicates introduced (`facts.duplicated(subset=["ticker","concept","end"])` = 0 rows). Every added `facts` concept is one of the 6 from Part A. Every added `metrics_long` concept is one of the 11 quarterly-ratio metrics (Part A) or 33 growth series (Part B) documented above — no unexplained additions. No existing chart's panel set changed for any concept that already had a panel (the `plot_fundamentals` dispatch falls back to the byte-identical `plot_metric()` call for every non-paired concept); the 11 paired concepts gained a second line on their *existing* panel rather than a new panel; the new `plot_growth` figure is an additional file, not a replacement of anything.

**Conclusion: Parts A and B satisfy the standing "nothing may regress" requirement in full**, verified empirically against the entire active universe rather than a sample.

---

## Part C — Is `MAX_MULTIPLE = 400` still needed at all?

**Note on the task text:** the task's context describes this as "`MAX_MULTIPLE = 200`... raising it to 400 was tried as a stopgap." The code as of the start of this task already had `MAX_MULTIPLE = 400` (raised in a prior task, per `main.py:392`) — this section evaluates the cap currently in force, 400, not 200.

### A structural finding that changes the premise

The task frames this cap as sitting "after all" of the project's specific denominator guards (`require_positive_denominator`, `min_denominator_scale_ref`/`ratio`, `min_denominator_abs`, the negative-equity sign guard, the PEG guards, the `net_debt_to_ebitda` cap) — implying those guards already protect the 9 capped multiples and the blanket cap is now redundant. **Checked directly against the code: this is not the case for `build_valuation_history()`.** All nine capped multiples (`pe_ratio`, `pb_ratio`, `pfcf_ratio`, `ev_ebitda`, `ev_sales`, `p_tbv`, `p_ppnr`, `p_core_earnings`, `p_ffo`) are computed with raw pandas division directly on the pivoted `wide` DataFrame (e.g. `wide["pb_ratio"] = wide["market_cap"] / wide["StockholdersEquity"].where(wide["StockholdersEquity"] > 0)`) — **none of them call `calculate_ratio()`**, which is the only place `require_positive_denominator`, `min_denominator_scale_ref`/`ratio`, and `min_denominator_abs` are implemented. The only protection any of the 9 capped multiples has, upstream of the cap, is the bare `.where(x > 0)` positivity filter. (`build_snapshot()`'s *equivalent* `pb_ratio`/`p_tbv` calculations, by contrast, *do* call `apply_denominator_scale_guard()` with `MIN_DENOMINATOR_SCALE_RATIO = 0.01` — the guard exists and is calibrated, it is just not wired into the historical series.) `peg_ratio` and `dividend_yield` are correctly excluded from the `MAX_MULTIPLE` loop entirely and have their own dedicated guards (`MIN_PEG_REVENUE_GROWTH`, `MAX_PEG_RATIO_ABS`) — those two are out of scope for this question.

This matters for the recommendation below: "the specific guards already do the job" is not simply true here, because for this function they mostly aren't wired in at all.

### Step C1 — Measurement

Built an unmodified-logic copy of `build_valuation_history()` with the `MAX_MULTIPLE` `.where()` step removed (everything else byte-identical to the real function — including calling the real, unmodified `build_valuation_history()` itself for the "capped" side of the comparison, not a reconstruction), ran both against the full active universe with freshly-fetched EDGAR facts and yfinance price history (498/498 tickers, no failures), and diffed on `(ticker, concept, end)`: any row present uncapped but absent after the real capped function ran was clipped.

**1,024 rows out of 208,461 uncapped valuation-history rows (0.49%) are currently clipped by `MAX_MULTIPLE = 400`** (identified via an exact `(ticker, concept, end)` key-based diff between the real, unmodified `build_valuation_history()` output — 207,380 rows — and an uncapped copy of the same logic, not a row-count subtraction).

| Concept | Clipped rows |
|---|---|
| `pe_ratio` | 293 |
| `pfcf_ratio` | 206 |
| `ev_ebitda` | 155 |
| `p_tbv` | 152 |
| `p_ffo` | 133 |
| `pb_ratio` | 75 |
| `ev_sales` | 8 |
| `p_ppnr` | 1 |
| `p_core_earnings` | 1 |

Classified every one of the 1,024 rows as **real** or **artifact** using two objective, reproducible checks against `Revenue_TTM` (present for effectively every row) and the ticker's own raw `SharesOutstanding`/`StockholdersEquity` history (read directly, not inferred):
- **Confirmed per-ticker data bug** — verified directly against the raw facts (not inferred from the ratio alone) that the ticker's `SharesOutstanding` or `StockholdersEquity` value is wrong by orders of magnitude for an extended period. Six tickers confirmed this way: see below.
- **Numerator implausible vs. revenue** — `market_cap / Revenue_TTM > 150` (150x sales, checked case-by-case against known extreme-but-real events like 2020 SaaS peak valuations and pandemic-era cruise-line revenue collapse before counting anything here, to avoid misclassifying a genuine market event as a bug).
- **Denominator near-zero vs. revenue** — the multiple's implied denominator (`market_cap / value`, e.g. for `pe_ratio` this recovers implied `NetIncomeLoss_TTM`) is under 0.1% of `Revenue_TTM` — implausible as a real net margin/FCF margin/EBITDA margin/equity-to-revenue ratio for an operating company, even a distressed one.
- Everything else: **real**.

**Result: 652 real (63.7%), 372 artifact (36.3%) — genuinely mixed, as the task's own decision framework anticipates for this case.**

**The artifact population is dominated by a small number of confirmed, ticker-specific data-quality bugs, not by the cap catching random noise:**

| Ticker | Clipped rows | What's actually wrong (verified directly against raw facts) |
|---|---|---|
| **WAT** (Waters Corp) | 234 (23% of *all* clipped rows) | `SharesOutstanding` reads **3.0-5.1 billion** shares for essentially its entire quarterly history (2007-2025) and spikes to **59.7 billion** (2025-03-29) and **82.1 billion** (2026-04-04) in two quarters. Waters Corp's real share count is in the tens of millions. This inflates `market_cap` (and everything built on it: `ev`, `pb_ratio`, `pfcf_ratio`, `ev_ebitda`, `ev_sales`, `p_tbv`, `p_ppnr`, `p_core_earnings`, `p_ffo`) by ~2 orders of magnitude for the whole history and ~4 orders of magnitude in the two worst quarters (peak observed: a `p_tbv` of 32,667x, market cap read as $21.6 trillion). Likely cause: `normalize_split_adjusted()` anchors its correction to the *last* value in each ticker's series (see `metrics.py`); if the anchor itself is already on the wrong scale, the whole series gets normalized to match the wrong scale rather than the right one — consistent with a uniformly-wrong-by-~50x baseline plus additional one-off spikes on top. |
| **ANET** (Arista Networks) | 16 | `SharesOutstanding` is plausible quarterly (~1.28B) but reads as an extreme outlier specifically at several **fiscal-year-end** dates (2021-12-31 through 2025-12-31), driving `EPS_TTM_CALC` down to ~10⁻⁶-10⁻⁷ (a real, profitable company should not show earnings-per-share of a millionth of a cent) and `pe_ratio` up to ~55 million. |
| **NTRS** (Northern Trust) | 2 | `market_cap` reads as $150 trillion at 2008-12-31 — a share-count artifact of the same shape as WAT, isolated to one period. |
| **ICE** (Intercontinental Exchange) | 2 | `StockholdersEquity` reads as **$10** (ten dollars) for two consecutive 2013 quarters against a real ~$18B market cap — a decimal/unit-scale artifact in that specific concept for that specific ticker/period. |
| **SW** (Smurfit WestRock) | 4 | `StockholdersEquity` reads as **$107-$14,446** (real dollars, not thousands) across several quarters against a $17-22B market cap — same shape as ICE. |
| **AMCR** (Amcor) | 2 | `StockholdersEquity` reads as **$96-$130** against a $13-15B market cap — same shape again. |

None of these six are new discoveries from Task 1's flag sweep, because that sweep checked *coverage* (are enough facts present) — these are a different failure mode entirely: complete coverage, wrong magnitude. **This is a real, actionable data-quality finding, separate from the MAX_MULTIPLE question, and is flagged here for a future targeted fix (the same `TICKER_CONCEPT_OVERRIDES`/`_KNOWN_BAD_FACTS` pattern used throughout this project) — not fixed in this task**, which is diagnosis-only for Part C and explicitly must not touch tag configuration.

**The remaining artifact rows (112, spread across dozens of otherwise-normal large-cap tickers)** are near-zero-denominator cases that don't trace to an obvious per-ticker bug: e.g. `CVX` (2013-06-30) `pfcf_ratio` implying `FCF_TTM` of $3M against $232B revenue; `DE`, `ES`, `PWR`, `ADM`, `ALB`, `OXY`, `MOS`, `EXC`, `PEG`, `HII`, `IFF`, `CMI` show the same shape — a single quarter's implied FCF in the low single-digit millions for a company that normally generates hundreds of millions to billions. These look like edge cases in `decumulate_period_values()` (`fetchers/edgar.py`) where independently-decumulated `OperatingCashFlow` and `Capex` quarters happen to nearly cancel — plausible but not confirmed without a deeper per-ticker trace, which is out of Part C's scope.

**The real population (652 rows, 63.7%)** is dominated by well-known, extreme-but-genuine valuation events: `AMZN` (2011-2015, near-zero GAAP earnings while scaling), `CRM`/`WDAY`/`NOW`/`PANW`/`DDOG`/`FTNT`/`CRWD` (high-growth SaaS with thin-to-negative GAAP earnings, especially 2011-2023), `TSLA`/`PLTR`/`AXON`/`PODD`/`DXCM` (extended pre-/thin-profitability growth phases), `NCLH`/`CCL` (2020-2021 pandemic-era revenue collapse against a market cap still pricing in recovery — checked and excluded from the "numerator implausible" bucket specifically because this is a documented macro event, not a data bug), and several REITs/energy names with genuinely thin GAAP net income relative to cash flow (a normal REIT/heavy-D&A-industry accounting characteristic, not an artifact).

### Step C2 — Recommendation

**Genuinely mixed (63.7% real / 36.3% artifact) — not "overwhelming majority real," so removing the cap outright is not supported by the evidence.** But the artifacts are also not randomly-distributed noise the guards already mostly catch — they concentrate in two identifiable, fixable places, which is exactly the "identify which guard gap lets them through, and recommend fixing that gap rather than keeping a blunt cap" branch of the task's own framework:

1. **Wire `apply_denominator_scale_guard()` (already built, already calibrated at `MIN_DENOMINATOR_SCALE_RATIO = 0.01`, already used for the equivalent `pb_ratio`/`p_tbv` in `build_snapshot()`) into `build_valuation_history()`'s nine capped ratios, using `Revenue_TTM` as the scale reference.** This is the actual guard gap: the mechanism exists and is calibrated, it just isn't called here. This would directly and precisely catch the 112+ near-zero-denominator artifact rows found above (and, most likely, a larger number of near-zero-denominator distortions currently sitting *under* 400 that this analysis — scoped to only what the cap currently removes — cannot see, since a value like a `pfcf_ratio` of 390 from a genuinely tiny FCF base would look "fine" to the cap but would still be exactly the kind of artifact the scale guard is designed for).
2. **Fix the six confirmed per-ticker data bugs (WAT, ANET, NTRS, ICE, SW, AMCR)** via the existing `TICKER_CONCEPT_OVERRIDES`/`_KNOWN_BAD_FACTS` mechanism, as a separate, targeted follow-up. A denominator-scale guard cannot fix WAT/NTRS/ANET's issue, since theirs is a *numerator* (market cap, from bad `SharesOutstanding`) problem, not a denominator problem.

**Do not remove or further raise `MAX_MULTIPLE` today.** Doing so now, before either fix above lands, would let through values up to a $21.6 trillion implied market cap and a 32,667x `p_tbv` on real user-facing charts. Once both fixes are in place, the two changes together would resolve an estimated ~372 of the 375 rows the cap currently removes (WAT/ANET/NTRS/ICE/SW/AMCR = 260 rows directly; the scale guard would catch most or all of the 112 near-zero-denominator rows) — at that point the cap would be left catching almost exclusively the real, extreme-but-genuine 652-row population, and **removing `MAX_MULTIPLE` entirely (or raising it far beyond any value seen in the real population) would very likely become the right call** — but that reassessment should happen after the two precise fixes, with fresh data, not before. This recommendation and its evidence are handed to the project owner per the task's explicit instruction not to implement Part C's change in this task.
