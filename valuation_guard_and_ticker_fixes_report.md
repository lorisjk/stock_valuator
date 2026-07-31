# Wire Denominator Guard into `build_valuation_history` + Fix 6 Ticker Data Bugs + Re-assess MAX_MULTIPLE

All work verified against the full active universe (498 tickers, `get_active_tickers()`) using cached EDGAR facts and freshly-fetched yfinance price history (498/498, no failures). Non-regression was run after each part separately, always as an exact `(ticker, concept, end)` outer-join diff, never a sample.

**Two corrections to the task's premises, established before any code was changed:**

1. **WAT is not commented out of `TICKER_PROFILES`.** The task states it is "currently commented out as a known-broken ticker". It is active at `config.py:329` (`"WAT": "pharma_medtech"`) and was in the 498-ticker active set throughout. The instruction not to un-comment a parked ticker is therefore moot for WAT; nothing was un-commented, and WAT was equally not commented *out* (that would itself be a profile change, out of scope).
2. **ANET's root cause is not `SharesOutstanding`.** The task inherits Part C's claim that ANET shows implausible share counts at fiscal year-ends. Checked directly: ANET's raw share facts are clean and correct (max 1.28B, its real post-split count). The actual defect is in `NetIncomeLoss` and has a completely different mechanism — see Part 2.

---

## PART 1 — Wire `apply_denominator_scale_guard()` into `build_valuation_history()`

### Step 1.1 — Current state and the existing precedent

Read side by side and confirmed:

- **`build_snapshot()`** calls `apply_denominator_scale_guard()` exactly twice — for `pb_ratio` (denominator `equity`) and `p_tbv` (denominator `tangible_equity`), both scaled against `revenue_ttm`, both at `MIN_DENOMINATOR_SCALE_RATIO = 0.01`. Its other multiples (`pe_ttm`, `pfcf_ttm`, `ev_ebitda`, `ev_sales`, `p_ppnr`, `p_core_earnings`) are unguarded raw division.
- **`build_valuation_history()`** calls it **zero** times. All nine capped multiples were raw pandas division on the pivoted frame with only a bare `.where(x > 0)` positivity filter. `MAX_MULTIPLE` was genuinely the only protection there, not a redundant extra net — confirming the premise this task rests on.

### Step 1.2 — Implementation

Eight of the nine multiples are now guarded, each on **its own** denominator (not one shared column):

| Multiple | Denominator guarded | Scale reference |
|---|---|---|
| `pe_ratio` | implied absolute earnings (`EPS_TTM_CALC` × shares) | `Revenue_TTM` |
| `pb_ratio` | `StockholdersEquity` | `Revenue_TTM` |
| `pfcf_ratio` | `FCF_TTM` | `Revenue_TTM` |
| `ev_ebitda` | `EBITDA_TTM` | `Revenue_TTM` |
| `p_tbv` | `TangibleEquity` | `Revenue_TTM` |
| `p_ppnr` | `PPNR` | `Revenue_TTM` |
| `p_core_earnings` | `CoreOperatingEarnings` | `Revenue_TTM` |
| `p_ffo` | `FFO_TTM` | `Revenue_TTM` |
| `ev_sales` | **not guarded — see below** | — |

Two implementation notes:

- **`pe_ratio` needed conversion.** Its denominator `EPS_TTM_CALC` is *per share*; comparing a per-share figure to an absolute `Revenue_TTM` is meaningless. It is guarded on the equivalent absolute earnings (`EPS_TTM_CALC × shares_for_market_cap`), which is exactly what `pe_ratio = market_cap / earnings` implies. Computed inline rather than by adding `NetIncomeLoss_TTM` to `needed`, because widening the pivot could introduce `(ticker, end)` rows that do not exist today — a silent row-level regression.
- **`ev_sales` is deliberately left unguarded.** Its denominator *is* `Revenue_TTM`, so guarding it against a `Revenue_TTM`-derived scale reference reduces to "`Revenue_TTM` < 1% of `Revenue_TTM`" — a circular test that is never true and would be dead code. A concept that is its own scale reference has nothing to be scale-checked *against*; its existing `.where(Revenue_TTM > 0)` is the only meaningful filter available. This is the "fine answer if that's what the analysis shows" the task anticipated. Empirically confirmed harmless: `ev_sales` contributes only 3 of the 698 rows still clipped by the cap (Part 3), and all three are real.

### Step 1.3 — Over-masking verification (the critical check) — **0.01 was rejected on the evidence**

Measured every currently-displayed value (non-null and ≤ `MAX_MULTIPLE`) that a `Revenue_TTM`-scaled guard would mask, at seven thresholds:

| Multiple | displayed | @0.0001 | @0.00025 | **@0.0005** | @0.001 | @0.0025 | @0.005 | @0.01 |
|---|---|---|---|---|---|---|---|---|
| `pe_ratio` | 26,801 | 0 | 1 | 2 | 3 | 20 | 92 | 323 |
| `pb_ratio` | 29,193 | 0 | 0 | 0 | 3 | 9 | 25 | 73 |
| `pfcf_ratio` | 22,702 | 0 | 0 | 0 | 3 | 36 | 109 | 324 |
| `ev_ebitda` | 18,659 | 0 | 0 | 1 | 2 | 5 | 13 | 50 |
| `p_tbv` | 19,562 | 0 | 0 | 1 | 1 | 14 | 48 | 134 |
| `p_ppnr` | 1,345 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `p_core_earnings` | 714 | 0 | 0 | 0 | 0 | 1 | 4 | 8 |
| `p_ffo` | 26,690 | 0 | 0 | 0 | 2 | 10 | 26 | 119 |
| **total** | | **0** | **1** | **4** | **14** | **85** | **317** | **1,031** |

**Shipping at 0.01 would have destroyed real data.** It masks 1,031 currently-displayed values, and classification shows the overwhelming majority are real *and perfectly ordinary*. The concentration gives it away:

| Ticker | rows masked @0.01 | What it actually is |
|---|---|---|
| COR (Cencora) | 159 | pharmaceutical distributor, ~0.5-1% net margin |
| CAH (Cardinal Health) | 91 | pharmaceutical distributor, ~0.5-1% net margin |
| MCK (McKesson) | 51 | pharmaceutical distributor, ~0.5-1% net margin |
| JBL (Jabil) | 36 | contract manufacturer, thin margin |
| KR (Kroger) | 27 | grocery, ~1-2% net margin |

Sample values 0.01 would have deleted: **MCK `pe_ratio` 9.2**, **MCK `p_ffo` 18.7**, **CAH `pfcf_ratio` 4.7**, **COR `pe_ratio` 31.7**, **MCK `p_tbv` 10.6**, **JBL `pfcf_ratio` 32.7**. Every one of those is a completely sane, informative multiple.

**The reason is structural, and it is the important finding of this part.** The guard's premise — small denominator relative to revenue ⇒ unreliable ratio — assumes market cap scales with revenue. For a thin-margin distributor it does not: market cap tracks *earnings*. So a denominator at 0.5% of revenue implies nothing at all about whether the multiple exploded, and the multiple itself (P/E 9) proves it did not. Applying a revenue-relative 1% floor here would delete ~936 correct values to remove a handful of uninformative ones — precisely the failure mode the task warned about.

**Recalibrated to `MIN_VALUATION_DENOMINATOR_SCALE_RATIO = 0.0005`.** At that threshold the guard masks exactly **4** values across the entire universe, every one a ≥166× multiple resting on a denominator under 0.05% of revenue — the genuinely uninformative extreme, where the multiple carries no signal even though the underlying figure is real:

| Ticker | Period | Multiple | Value masked | denominator / revenue |
|---|---|---|---|---|
| MCK | 2019-03-31 | `pe_ratio` | 322.73 | 0.000159 |
| MCK | 2018-03-31 | `pe_ratio` | 206.38 | 0.000322 |
| HPQ | 2011-07-31 | `p_tbv` | 204.58 | 0.000397 |
| CAH | 2022-06-30 | `ev_ebitda` | 166.50 | 0.000469 |

The guard's value at this setting is mainly **prospective**: it is a calibrated net for the units/scale-error class that Part 2 had to repair by hand (a 1000×-too-small denominator lands around 1e-5 here, far below the threshold), positioned so it cannot silently delete a thin-margin company's ordinary valuation history.

**Required real cases — all confirmed surviving with zero masked rows:**

| | AMZN | CRM | WDAY | NOW | PANW | DDOG | FTNT | CRWD | TSLA | PLTR | NCLH | CCL |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rows before | 479 | 464 | 137 | 271 | 251 | 126 | 364 | 118 | 275 | 73 | 288 | 499 |
| rows after | 479 | 464 | 137 | 271 | 251 | 126 | 364 | 118 | 275 | 73 | 288 | 499 |
| **masked** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** |

### Step 1.4 — Non-regression for Part 1

Guard off vs. guard on, identical input data, full universe:

| | count |
|---|---|
| values **removed** (newly masked) | **4** — the complete list is the table above |
| values **added** | **0** |
| values **changed** | **0** — confirming a guard can only mask, never alter |
| previously-masked values reappearing | **0** |
| tickers touched | **3** (CAH, HPQ, MCK) |

---

## PART 2 — Fix the confirmed ticker data bugs

Each ticker was diagnosed against its raw cached EDGAR facts before anything was changed. The task's warning not to assume one mechanism was well founded: there are **three genuinely different root causes**, and one of them turned out to affect two tickers nobody had flagged.

### Step 2.1 — WAT: both of the task's cases apply

The task framed this as an either/or: either the raw facts are bad (fixable) or `normalize_split_adjusted()` is mangling good facts (not fixable here). **Both are true, in sequence.**

Raw `WeightedAverageNumberOfDilutedSharesOutstanding` contains exactly two bad values, both from the same 2026-05-12 10-Q, both exactly **1000× too large**:

```
end          val             filed        form
2025-03-29   59,711,000,000  2026-05-12   10-Q     <- same period elsewhere reads 59,711,000
2026-04-04   82,139,000,000  2026-05-12   10-Q
```

The 1000× factor is provable, not inferred: the same filing's `2025-03-31` value is `59,711,000` — the identical figure three decimal places over. Every other one of WAT's 364 raw facts is sane (58.9M–102.5M).

So the raw facts *are* specifically bad and *are* fixable. But those two values then sat at the end of the series and poisoned `normalize_split_adjusted()`'s `values.iloc[-1]` anchor, which rescaled WAT's **entire 2007–2026 history** by 50× (the largest available factor in `COMMON_SPLIT_FACTORS`) to "match" the garbage anchor. That is why a two-fact defect produced 234 clipped rows spanning two decades.

Fixed via `_KNOWN_BAD_FACTS`, listed for **both** share tags — `SharesOutstanding` is `mode="fallback"` with Diluted first and Basic second, and Basic carries the same bad values, so dropping only Diluted would let the equally-bad Basic value take over.

**Result — and an honest limit.** WAT's share count went from **3.0e9–8.2e10** to **6.9e7–1.3e8**. Against Waters Corp's real count (~102M in 2007 declining via buybacks to ~59.7M by 2025, then ~98M after the BD Biosciences Reverse-Morris-Trust merger closed in Q1 2026) that is a correction from ~50–1000× wrong to **within 2×**.

**WAT is not fully sane, and I am stating that explicitly as the task requires.** A residual exactly-2× distortion remains on 44 of 96 quarters:

```
end          raw (post-fix)   after normalize_split_adjusted   factor
2025-09-27      59,622,000              119,244,000             2.0
2025-12-31      59,763,000              119,526,000             2.0
2026-04-04      98,166,000               98,166,000             1.0
```

The cause is the same anchor logic, now with a *correct* anchor: the real merger-driven share issuance (59.7M → 98M) is misread as a stock split, so the pre-merger history is doubled to match. This is not fixable via `_KNOWN_BAD_FACTS` — the raw facts are now all correct — and per the explicit instruction (three prior repair attempts on that function already failed) **no fourth generic repair was attempted**. It remains visible in WAT's growth chart as a spurious ~+75% share-count step around 2020. Un-commenting is moot since WAT was never commented out; whether to park it is the project owner's call.

### Step 2.2 — ANET (and NTRS, and two tickers nobody flagged)

**NTRS** matched the expected shape: the 2011-02-25 10-K reports weighted-average shares ~1e6× too large (`224,053,430,000,000` where the real count is ~224 million), across both share tags, for three fiscal years. Dropped; series is now 1.87e8–2.43e8 against a real ~185–242M. Correct.

**ANET did not.** Its raw share facts are clean. Tracing the actual defect:

```
ANET NetIncomeLoss, facts covering FY2025:
  end          val            filed        form
  2025-03-31     813,800,000  2025-05-07   10-Q
  2025-06-30   1,702,600,000  2025-08-06   10-Q   (cumulative)
  2025-09-30   2,555,600,000  2025-11-05   10-Q   (cumulative)
  2025-12-31   3,511,400,000  2026-02-17   10-K   <- correct, in dollars
  2025-12-31           3,511  2026-04-16   DEF 14A <- proxy, in $-MILLIONS
```

`extract_period_values()` keeps the **latest-filed** fact per period, and the proxy statement is filed after the 10-K — so `3511` wins. Decumulation then computes Q4 = annual − (Q1+Q2+Q3) = `3511 − 2,555,600,000` = **−$2.556B**, a large negative Q4 that cancels the year's real earnings, drives `NetIncomeLoss_TTM` to ≈ 0, and pushes `EPS_TTM_CALC` to ~1e-6 and `pe_ratio` into the tens of millions — for four quarters after every fiscal year end, 2021 through 2025.

**Before choosing a fix, I checked how widespread the DEF 14A pattern is across the whole universe:** 141 active tickers have DEF 14A facts overlapping a 10-K period, and exactly **3** are units-mismatched — ANET, **SCHW** and **ED** (15 facts total). A blanket "ignore DEF 14A" extraction rule would therefore alter 141 tickers to repair 3. The targeted, zero-inference `_KNOWN_BAD_FACTS` drop-list is the correct scope, and a `TICKER_CONCEPT_OVERRIDES` entry could not have helped at all — this is not a tag-selection problem.

SCHW and ED were both already in Part C's artifact population (5 rows each) with no explanation attached; this diagnosis accounts for them.

**Before/after fiscal-year-end (Q4) `NetIncomeLoss`:**

| Ticker | Q4 before | Q4 after (2021→2025) | Sanity |
|---|---|---|---|
| ANET | −0.60B, −0.93B, −1.47B, −2.05B, −2.56B | +239M, +427M, +614M, +801M, +956M | Arista is highly profitable and growing; FY2025 Q4 ≈ $956M is right |
| SCHW | negative | +1.58B, +1.97B, +1.05B, +1.84B, +2.46B | all positive, correct scale |
| ED | negative | +224M, +190M, +334M, +310M, +297M | positive; Q4 is seasonally weak for a utility, as expected |

### Step 2.3 — ICE, SW, AMCR: `StockholdersEquity` scale errors

All three report `StockholdersEquity` in literal dollars in specific filings ($10 for ICE; $107–$14,462 for SW; $96–$130 for AMCR) against $13–22B market caps. In **all three** the fallback tag `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` already carries the correct full-unit value for the same periods, so dropping the bad facts lets the existing `mode="fallback"` chain recover the right number by itself — no new tag configuration needed.

**Deliberately *not* solved by adding `StockholdersEquity` to `_SCALE_CORRECTED_CONCEPTS`.** That mechanism infers a scale factor from neighbouring magnitudes, and for a dollar-magnitude balance item a real large jump is indistinguishable from an artifact — which is exactly why the prior generalization attempt failed. This very dataset contains two such real jumps: AMCR's equity goes 3.85B → 11.73B on the Berry Global merger (2025) and SW's 5.34B → 17.36B on the WestRock combination (2024). An inference-based mechanism would be at serious risk of "correcting" those. Targeted drop-list only, per the task's instruction to be skeptical here.

| Ticker | Before (bad periods) | After | Real scale |
|---|---|---|---|
| ICE | $10 (2013 Q2, Q3) | 2.816e9 – 2.948e10 | ~$10–29B ✓ |
| SW | $107–$14,462 (2022-12 → 2024-06) | 4.929e9 – 1.843e10 | ~$5–18B ✓ |
| AMCR | $96–$130 (2018-12, 2019-03) | 5.033e8 – 1.173e10 | ~$0.5–11.7B ✓ |

### Step 2.4 — Non-regression for Part 2

39 facts added to `_KNOWN_BAD_FACTS` across 10 `(ticker, tag)` keys. Full-universe diff on the raw facts frame:

| | count |
|---|---|
| facts **changed** | 118 |
| facts **removed** | 3 |
| facts **added** | 0 |
| **tickers touched** | **8** — AMCR, ANET, ED, ICE, NTRS, SCHW, SW, WAT — and no others |

Changed, by `(ticker, concept)`: WAT `SharesOutstanding` 96, ANET/ED/SCHW `NetIncomeLoss` 5 each, SW `StockholdersEquity` 4, AMCR `StockholdersEquity` 2, NTRS `SharesOutstanding` 1.

The 3 removed rows are the only cases where a bad fact had **no** sane fallback for that period, so the period legitimately drops out rather than being reported wrongly: ICE `StockholdersEquity` 2013-06-30 and 2013-09-30, SW `StockholdersEquity` 2023-03-31. (This is why ICE shows in the facts-level diff but not the valuation-level one — those two quarters previously produced `pb_ratio` values so extreme the cap already discarded them, so removing them changes no displayed value.)

Downstream on `valuation_history`, guard held off to isolate the data fixes: **0 removed, 337 added, 211 changed, 7 tickers touched** (WAT 122, ED 33, ANET 29, SCHW 27, plus AMCR/NTRS/SW). The 337 additions are periods whose multiples were previously so distorted that `MAX_MULTIPLE` discarded them and which now compute to sane values.

---

## PART 3 — Re-measure `MAX_MULTIPLE` with both fixes in place

### Step 3.1 — Re-run of the Part C measurement

Identical method: an uncapped copy of the (now guarded) logic diffed against the real capped output on `(ticker, concept, end)`.

| | Part C (before) | Now (after both fixes) |
|---|---|---|
| rows clipped by `MAX_MULTIPLE = 400` | 1,024 | **698** |
| classified **real** | 652 (63.7%) | **651 (93.3%)** |
| classified **artifact** | 372 (36.3%) | **47 (6.7%)** |

Every one of the six originally-named tickers has left the clipped population entirely — WAT (was 234 rows, the single largest contributor), ANET (16), SW, NTRS, ICE, AMCR, plus SCHW and ED found during this task. The artifact count fell by 87%.

Three rows my classifier initially flagged as "numerator implausible" — NCLH `ev_sales` at 2021-03-31 and 2021-06-30, CCL `ev_sales` at 2021-05-31 — were checked individually and are **real**: cruise revenue genuinely collapsed to $23–141M during the sailing shutdown, so an EV/Sales of 408–867 correctly reflects a near-zero revenue base. They are counted as real above.

The remaining 47 artifacts are all near-zero-denominator cases, spread thinly (1–2 rows each) across ~35 otherwise-normal large caps (AES, CSCO, NUE, LHX, EFX, DHI, …), concentrated in `pfcf_ratio` (20), `p_tbv` (11) and `pe_ratio` (9). They are the `decumulate_period_values()` residue identified in Part C — independently-decumulated quarters that happen to nearly cancel.

**They sit in a strikingly narrow band.** Every one of the 47 has a denominator/revenue ratio between **0.000501 and 0.000990** — i.e. all of them fall just above the 0.0005 guard threshold and all of them below 0.001.

### Step 3.2 — Recommendation (not implemented, per instruction)

The clipped population is now **93.3% real** — the task's first branch ("overwhelming majority real → recommend removing the blanket cap"). But rather than remove it and let 47 artifacts through, the band finding gives a precise paired fix:

> **Recommendation: remove `MAX_MULTIPLE` entirely, and in the same change raise `MIN_VALUATION_DENOMINATOR_SCALE_RATIO` from `0.0005` to `0.001`.**

The two must move together. Evidence for the pairing:

- Raising the guard to 0.001 covers **all 47** remaining artifacts (max ratio 0.000990 < 0.001).
- Its cost is precisely measured: **10** additional currently-displayed values masked (MCK 105.6, COR 265.8, VLO 291.4, COR 191.3, KR 97.3, BLDR 267.2, COR 136.5, LMT 264.8, COR 128.6, MPC 115.3). All are ≥97× multiples on denominators under 0.1% of revenue — high and low-information, though it is worth being explicit that a few (KR 97.3, MCK 105.6) are defensibly real, so this is a real if small cost, not a free win.
- With the cap gone, the 651 real values return to the charts — including the genuine section of Tesla's P/E history that motivated the original investigation.

One thing the project owner should weigh before removing the cap: the real population has a long tail. Uncapped, the largest surviving values are DDOG `ev_ebitda` 41,152 (2020-12-31), DDOG `pe_ratio` 25,466, DDOG `ev_ebitda` 20,098, TSLA `ev_ebitda` 11,821. These are real — DDOG's EBITDA was genuinely near zero while it scaled — but 185 real values exceed 1,000× and 15 exceed 5,000×, which will compress the readable range on a linear axis. `plot_metric` already supports `symlog`; enabling it for the valuation panels would be the natural companion change. That is a presentation decision, not a data one, and is flagged rather than made here.

Per the explicit instruction, **none of this is implemented** — the cap remains at 400 and the guard at 0.0005. The point of this task was to make the cap's removal safe; the decision is handed over with fresh numbers.

---

## PART 4 — Growth as a column on `quarterly_facts`, not rows in `metrics_long`

### Step 4.1 — What was removed

Deliberately removed, as requested (this is a requested removal, not a regression):

- `main.GROWTH_CONCEPTS` and `main.calculate_broad_growth()` — the 33 metric-layer growth series.
- The `growth_metrics` parameter of `build_metrics_long()` (signature back to `(metrics, quarterly_metrics=None)`).
- `config.GROWTH_BASE_PANELS`, `config.GROWTH_PROFILE_EXTRA`, `config.get_growth_panels()` — the per-profile panel selection existed solely to serve the removed 5-panel figure, and Step 4.4 concludes a universal 3-panel selection is right, so none of it is reused.
- `figures.GROWTH_PANEL_LABELS` and the old 5-panel `plot_growth`.

**The `min_base_ratio` calibration was preserved, not redone.** The previous task's empirical finding — that `0.33` over-masks lumpy/event-driven concepts where a >3× YoY move is routine — is carried forward, remapped onto the plain concept names now that growth is computed on the raw layer: `Capex`, `Goodwill`, `CashAndEquivalents`, `Inventory`, `LongTermDebt`, `ProvisionForCreditLosses` → `0.05`.

**Extended to one newly-in-scope concept**, using the same method: `TangibleEquity` (= `StockholdersEquity` − `Goodwill`) masks 2.52% of periods at 0.33 and moves on exactly the same M&A/impairment events as `Goodwill` itself → `0.05`. Everything else newly in scope keeps the untouched 0.33: the remaining high-mask concepts (`FCF_QUARTERLY` 7.1%, `CoreOperatingEarnings_QUARTERLY` 7.5%, `EPS_QUARTERLY_CALC` 5.7%, `NetIncomeLoss` 5.6%, `OperatingCashFlow` 5.0%, `FFO_QUARTERLY` 3.6%, `OperatingIncomeLoss` 3.3%, `EBITDA_QUARTERLY` 2.2%) are precisely the earnings-like class 0.33 was originally calibrated for.

### Step 4.2 — Which concepts get a growth value

`quarterly_facts.csv` holds 62 concepts. Growth is computed for **35**.

**Excluded — the 25 TTM-based concepts** (any name containing `_TTM`, plus `PPNR` and `CoreOperatingEarnings`, which are TTM-derived despite their names).

**This is the deliberate answer to the duplicate question the task asked to flag.** `Revenue_TTM` growth here would be the identical number already published as `revenue_yoy_growth` in `metrics_long.csv` — same value, two files, two names — and the same applies to `NetIncomeLoss_TTM`/`income_yoy_growth`, `OperatingIncomeLoss_TTM`/`operating_income_yoy_growth`. Rather than accept silent duplication, the `_TTM` rows are excluded on a principled line: a TTM growth rate is the *analyst* view, which `metrics_long` already carries where it matters; this column is the *reporting* view — single-period and point-in-time growth — matching the quarterly/reporting-view framing established for the `_QUARTERLY` concepts in the previous task. Those rows get an empty cell, not a dropped row.

**Excluded — 2 further concepts as not meaningful:** `GainLossOnSaleOfProperties` and `RealizedInvestmentGains`. Both are opportunistic one-off gain/loss lines that flip sign and sit near zero by nature, so a YoY growth rate on them is not an interpretable figure — a judgement carried forward from the previous task. The data corroborates it independently: these two have by far the highest guard-mask rates of any concept in scope (26.5% and 22.8%), i.e. a near-zero-or-negative base is their normal state rather than an anomaly.

**Included — all 35 others**, covering plain quarterly flows (Revenue, NetIncomeLoss, Capex, OperatingCashFlow, …), the `_QUARTERLY` derived concepts (FCF_QUARTERLY, EPS_QUARTERLY_CALC, FFO_QUARTERLY, EBITDA_QUARTERLY, PPNR_QUARTERLY, CoreOperatingEarnings_QUARTERLY), and **all point-in-time/balance concepts** — `SharesOutstanding` (dilution/buybacks), `StockholdersEquity` (book-value growth), `Inventory` (stock build), `LongTermDebt`, `CashAndEquivalents`, `Goodwill`, `Assets`, `Investments`, `AccountsReceivable`, `AccountsPayable`, `ClaimsReserve`, `TangibleEquity`. None turned out not to be meaningful.

### Step 4.3 — Added as a column; downstream-reader check

New column **`yoy_growth`**, giving the header exactly:

```
ticker,concept,end,value,yoy_growth
```

matching the task's worked example — verified on the exact row it names:

```
ticker concept        end      value  yoy_growth
  TSLA   Capex 2010-09-30  7768000.0         NaN
  TSLA   Capex 2011-03-31 20476000.0         NaN
  TSLA   Capex 2011-09-30 68844000.0    7.862513   <- vs 2010-09-30: 68.844M/7.768M - 1
  TSLA   Capex 2012-03-31 54774000.0    1.675034
```

**Downstream-reader check, as required.** Grepped the whole codebase for readers of `quarterly_facts.csv` / the `f"{PERIOD}_facts.csv"` output, and for positional access patterns (`.values`, `iloc[`, `usecols`, `shape[1]`, column-count assertions):

- The file is **written in exactly two places** (`main.py:778` in `main()`, `main.py:983` in `run_full_refresh()`) and **read back nowhere** — no `pd.read_csv` of it exists in the codebase.
- No positional indexing, no `.values` on the facts frame, no column-count assertion anywhere.
- The only `.iloc[` hit on this data is `metrics.py:270` (`values.iloc[-1]` inside `_normalize_series`), which operates on a Series of values long before this column exists.

So: nothing reads it positionally, and nothing breaks on an extra column. Belt and braces, the column is nonetheless attached **at the very end of the pipeline**, immediately before `to_csv`, so no intermediate consumer of the in-memory `facts` frame (`add_derived_concepts`, `calculate_all_metrics`, `build_valuation_history`, `build_snapshot`, `filter_hidden_rows`, every `pd.merge` in `metrics.py`) ever sees it.

### Step 4.4 — The three plotted series

**Revenue, NetIncomeLoss, SharesOutstanding — universal, not profile-dependent.**

Reasoning from what a reader of the chart needs: at n=3 the right choice is the trio that describes any company's growth regardless of sector — the top line, the bottom line, and the share count that bridges company-level growth to per-share value. Dilution can fully offset real revenue and earnings growth and is invisible in the other two, which is exactly why it earns the third slot over a sector-specific line. A bank, a REIT and a software company all have all three; a profile-dependent selection would add branching for no gain at this size, which is why none of the removed per-profile machinery was retained. These are the **quarterly** (single-period) growth values, complementing rather than duplicating the TTM-based `revenue_yoy_growth`/`income_yoy_growth` panels already on the fundamentals chart.

**Rendered as a small dedicated 1×3 figure**, `{ticker}_growth.png`, alongside the existing two — which keeps the fundamentals and valuation chart layouts *exactly* unchanged, the option the task states is preferred. `plot_growth` now reads the facts frame (where the growth column lives) rather than `metrics_long`. Rendered and visually verified for TSLA, WAT and ANET.

### Step 4.5 — Non-regression for Part 4

**`quarterly_facts.csv`:**

| Check | Result |
|---|---|
| row count | 745,443 → 745,443 — **identical** |
| `(ticker, concept, end)` keys | **identical** |
| `value` column | **byte-identical** |
| columns added | `['yoy_growth']` |
| columns removed | `[]` |
| growth populated | 388,112 of 745,443 rows (52.1%), across 35 concepts |
| concepts with no growth value | exactly the 25 `_TTM`-like + 2 excluded — as designed |

**`metrics_long.csv`:** 40 concepts remain.

| Check | Result |
|---|---|
| all 33 removed growth series gone | ✅ (deliberate) |
| 4 original growth series kept | ✅ `revenue_yoy_growth` 31,327 · `income_yoy_growth` 31,432 · `operating_income_yoy_growth` 24,832 · `reserve_growth` 954 |
| 11 quarterly ratio metrics from the previous task kept | ✅ untouched |
| 6 `_QUARTERLY` derived concepts kept | ✅ untouched, still in `quarterly_facts` |

---

## Files changed

| File | Change |
|---|---|
| `main.py` | Guard wired into 8 multiples in `build_valuation_history()`; new `MIN_VALUATION_DENOMINATOR_SCALE_RATIO = 0.0005`; removed `GROWTH_CONCEPTS`/`calculate_broad_growth()`; new `growth_concepts()`/`add_growth_column()`; `build_metrics_long()` signature reverted; both call sites updated |
| `parsers/parse_edgar.py` | 39 facts added to `_KNOWN_BAD_FACTS` across 10 `(ticker, tag)` keys |
| `figures.py` | `plot_growth` replaced with the universal 3-panel version reading the facts frame; `GROWTH_PANEL_LABELS` removed |
| `config.py` | `GROWTH_BASE_PANELS`, `GROWTH_PROFILE_EXTRA`, `get_growth_panels()` removed |

No `TICKER_PROFILES` entry was added, removed, commented or un-commented. No `TICKER_CONCEPT_OVERRIDES` entry was touched. No generic repair of `normalize_split_adjusted()` was attempted. Part 3's recommendation is not implemented. No scratch scripts left behind.
