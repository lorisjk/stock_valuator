# Nine Data-Quality / Metric Improvements from External Review

Each of the nine was investigated against real cached data (498 active tickers) before any
code was written. **Seven implemented, one deliberately not implemented, one found unnecessary
because its premise didn't survive contact with the data.** Per the task's explicit framing,
those last two are reported as complete answers with their evidence, not as failures.

The non-regression baseline for this task was produced by *reconstructing the pre-task source
files* (`main.py`, `metrics.py`, `config.py`) into a separate package and running the pipeline
through them, because an early background run had already picked up half-finished edits. Every
reverted hunk was asserted to apply exactly once, and the reconstruction was validated by
reproducing the prior task's known-good row count exactly (`metrics_long` = 535,874).

---

## PART 1 — Symmetric share-count resolution — **IMPLEMENTED**

### 1.1 Scope-check

Across all 495 tickers with both sources, 57 have a negative `shares_delta_pct` (yfinance
larger than EDGAR). Sorted by yfinance/EDGAR ratio:

| ticker | yf/edgar | EDGAR shares | yfinance shares |
|---|---|---|---|
| KLAC | **9.91×** | 131,750,000 | 1,306,275,210 |
| CRWD | **3.95×** | 257,881,000 | 1,018,259,280 |
| DVN | **1.87×** | 618,000,000 | 1,153,403,107 |
| BKR | 1.23× | 806,000,000 *(as of 2021-06-30)* | 992,674,071 |
| TSLA | 1.12× | 3,540,000,000 | 3,949,547,394 |
| FITB | 1.09× | 830,273,720 | 906,573,000 |
| …then a continuous tail down to 1.00× | | | |

So the three named tickers were **not** the whole story — BKR and TSLA also sit above the
inverted 1.10 line, and both turned out to be cases where switching would have been wrong.

### 1.2 Design — deliberately *not* 1.10 inverted

The task asked to calibrate rather than reuse `1.10` inverted, and that check mattered: the
negative-delta distribution has **no separation at 1.10**. The only wide gap is between
DVN (1.87×) and TSLA (1.12×). Two findings drove the final design:

1. **Threshold = 1.50** (`MIN_YF_SHARE_OVERSTATEMENT`), sitting in that gap. The three above
   it are wrong by near-integer factors (≈10×, ≈4×, ≈2×) — the signature of a units/split
   error on yfinance's side. TSLA's 1.12× is not near an integer factor and is far more likely
   an ordinary definitional difference; switching it would be a guess, not a fix.
2. **An EDGAR-staleness condition**, which the task didn't anticipate and the data forced.
   **BKR's newest `SharesOutstanding` fact is 2021-06-30 while its newest fact of any kind is
   2026-06-30 — a 1,826-day lag.** For BKR, yfinance (992.7M) is right and EDGAR (806M) is a
   five-year-old number; preferring EDGAR would have made `market_cap` *worse*. So EDGAR is
   only preferred in the yfinance-larger direction when its own share count is current
   (`MAX_EDGAR_SHARE_LAG_DAYS = 200`, ~two quarters, measured against the ticker's own newest
   fact rather than today's date so a wholly SEC-lagged payload isn't punished twice).

The original EDGAR-larger rule (`> 1.10`) is untouched.

### 1.3 Verification

| ticker | metric | before | after | real scale |
|---|---|---|---|---|
| KLAC | shares | 1,306,275,210 | **131,750,000** | ~131M ✓ |
| | market_cap | $238.8B | **$24.1B** | ~$24B ✓ |
| | pb_ratio | 40.96 | **4.13** | |
| | ev_ebitda | 340.00 | **39.45** | |
| CRWD | shares | 1,018,259,280 | **257,881,000** | ~258M ✓ |
| | market_cap | $194.3B | **$49.2B** | ~$49B ✓ |
| DVN | shares | 1,153,403,107 | **618,000,000** | ~618M ✓ |
| | market_cap | $52.1B | **$27.9B** | ~$28B ✓ |

BKR and TSLA correctly still use yfinance (`shares_source_is_edgar = 0.0`).

### A pre-existing bug this exposed and fixed

Switching three tickers for the first time revealed that `build_snapshot()` called
`_resolve_share_sources()` a **second** time against `snap` *after* overwriting
`snap["shares_outstanding"]` with the resolved count — so for any ticker that actually
switched, the audit columns compared EDGAR against EDGAR: reporting `shares_delta_pct = 0.0`
and `shares_source_is_edgar = 0.0` for precisely the tickers that had switched.

**This means the prior task's reported finding "0 tickers currently cross the 10% switch
threshold" was an artifact of this bug.** In reality **35 tickers** were already resolving to
EDGAR via the original dual-class rule (ABNB, AOS, APP, BF-B, C, COIN, DD, DDOG, DELL, EL, FOX,
FOXA, GOOG, GOOGL, HOOD, HSY, LEN, LITE, META, NKE, NWS, NWSA, PLTR, RDDT, RL, SATS, TAP, TKO,
TSN, TTD, UHS, UPS, WDAY, WDC, XYZ) with their true deltas (10.2%–15.7%+) misreported as 0.0%.
Fixed by resolving once off the untouched `prices` and reusing the result for both purposes.
This correction accounts for 73 of the 97 changed snapshot rows below.

---

## PART 2 — `debt_inferred_zero` — **NOT IMPLEMENTED (deliberately)**

### 2.1 Investigation

15 of 498 active tickers have no resolvable `LongTermDebt` balance tag: ALGN, DASH, DDOG,
EXPD, GM, GRMN, ISRG, LULU, MPWR, RDDT, TPL, TROW, TTD, TXT, VEEV.

Checking each for hard debt evidence (principal-maturity schedules, borrowings balances,
debt issuance/repayment flows):

| ticker | hard debt-evidence tags found |
|---|---|
| GM | `LongTermDebtMaturitiesRepaymentsOfPrincipal` ×6 (**$219B total liabilities**) |
| TXT | maturities ×5 + `ProceedsFromIssuanceOfLongTermDebt`, `ProceedsFromConvertibleDebt` |
| DDOG, DASH | `ProceedsFromConvertibleDebt` (both have real convertible notes) |
| TROW | `ProceedsFromIssuanceOfLongTermDebt` |
| TTD | `LongTermLineOfCredit`, `RepaymentsOfSecuredDebt` |
| EXPD | `LineOfCreditFacilityAmountOutstanding`, `ProceedsFromLinesOfCredit` |
| ALGN | `LineOfCredit`, `InterestExpense` |
| RDDT | `LineOfCreditFacility*` |
| **VEEV, ISRG, MPWR** | **none** |

### 2.2 Why no blanket rule — the heuristic fails its own sanity check

The task proposed validating "no debt tag AND no debt-flow tags ⇒ real zero" against the
already-confirmed GRMN/LULU/DECK cases. **All three fail it:**

- **GRMN** has `RepaymentsOfLongTermDebt`.
- **LULU** has `ShortTermBorrowings`, `OtherBorrowings`, `LineOfCreditFacilityAmountOutstanding`.
- **DECK** has `ProceedsFromIssuanceOfLongTermDebt`, `RepaymentsOfLongTermDebt`,
  `ShortTermBorrowings`, `OtherShortTermBorrowings` — and isn't even a candidate, because it
  *does* resolve a `LongTermDebt` balance.

So the proposed rule would **exclude all three of the reference cases it was supposed to be
validated against**, while a looser rule that included them would sweep in GM ($219B
liabilities) and TXT — a catastrophic false "zero debt" for two companies with unmistakable
real debt. Only **3 of 15** candidates (VEEV, ISRG, MPWR) have genuinely clean evidence.

The evidence is therefore mixed and unreliable for 80% of candidates, which is exactly the
condition under which the task says not to implement a blanket rule.

**Recommendation:** targeted `TICKER_CONCEPT_OVERRIDES`-style treatment for **VEEV, ISRG,
MPWR** only — the same targeted-over-generic principle used for `_KNOWN_BAD_FACTS`. Not
applied here, since introducing synthetic zero facts is a data-model decision beyond this
task's scope.

---

## PART 3 — Dual-class share counts — **3.1/3.2 UNNECESSARY, 3.3 IMPLEMENTED**

### 3.1 The premise doesn't survive the raw data

The task assumed classes are tagged separately (e.g. `CommonClassACommonStockSharesOutstanding`)
and merely need summing. Dumping the raw payloads:

**No class-specific share tag exists in any cached ticker's payload.** The SEC `companyfacts`
API returns only **consolidated, non-dimensional** facts — per-class values live in the XBRL
*dimensions*, which this endpoint does not expose at all. There is nothing to sum.

Worse, the existing values are **already the all-class totals**:

| ticker | tag used | value | real all-class total |
|---|---|---|---|
| GOOGL | `CommonStockSharesOutstanding` | 12,230,000,000 | ~12.1–12.2B (A+B+C) ✓ |
| META | `WeightedAverageNumberOfSharesOutstandingBasic` | 2,534,000,000 | ~2.5B (A+B) ✓ |

- **BRK** is not in the active universe at all, so it could not be checked as the task assumed.
- **FOX/FOXA** are two tickers on one CIK with identical payloads, and their sole
  `dei:EntityCommonStockSharesOutstanding` fact is a **garbage value of `1`** from a 2019
  10-Q — a separate real data defect, noted here, not fixed (out of scope).

**Conclusion: 3.2 is not implementable and not needed** — the counts are already consolidated,
and the failure mode the task describes ("picks one class") does not exist.

### 3.3 QoQ share-count guard — implemented

`share_count_jump_flag`: `SharesOutstanding` moves >15% QoQ with no buyback
(`PaymentsForRepurchaseOfCommonStock`) or issuance (`ProceedsFromIssuanceOfCommonStock`) of
comparable size. Informational, does not mask — same convention as `buyback_distortion_flag`.

**Threshold calibrated**, not assumed: the real |QoQ change| distribution is median 0.48%,
p90 3.3%, p95 6.6%, **p97 12.7%**, p99 46%. 15% sits just above p97 → **824 of 30,706 periods
(2.68%)** flagged before corroboration, 763 after.

**Checked whether the named tickers actually clear the bar, rather than assuming:**

| ticker | evaluable | flagged | when |
|---|---|---|---|
| RDDT | 14 | **6** | 2023-06-30 … 2024-09-30 (IPO period) |
| META | 59 | **3** | 2012-06-30, 2012-09-30, 2013-03-31 (IPO era) |
| FOX / FOXA | 32 | 1 each | 2020-09-30 |
| **GOOGL** | 42 | **0** | — |

So RDDT and META do clear it (during their IPO windows, when share counts genuinely jumped),
but **GOOGL never does** — the report's implication that it would was wrong.

Coverage caveat, measured up front and handled explicitly: `PaymentsForRepurchaseOfCommonStock`
covers 96.2% of tickers but `ProceedsFromIssuanceOfCommonStock` only **54.6%**. A missing
issuance tag is treated as "no corroboration available", which makes the flag conservative in
the reporting direction (it may flag a real issuance whose tag is absent) rather than silently
missing suspect share counts.

---

## PART 4 — `history_too_short` — **IMPLEMENTED**

`calculate_rolling_harmonic_stats()` now also emits `_n`, the number of valid (positive,
non-masked) observations each rolling mean/median was actually built from — necessary because
`min_periods=1` means a "5-year average" can be computed from a single quarter.
`build_snapshot()` turns that into `avg_X_5y_history_too_short` for all seven multiples.

**Cutoff 12 confirmed against real data** (the task's hypothesis held): valid `pe_ratio`
quarters per ticker in a 5-year window run median 19, p25 18.75, p10 13, p5 10, p2 6. A cutoff
of 12 sits just below the 10th percentile — selective, catching genuine short-history cases
without sweeping in normal tickers.

**18 of 493 tickers flagged on `avg_pe_5y`**, and every one is genuinely young or newly
separated — verified by checking each one's total valid history and first valid quarter:

| ticker | total valid quarters | first valid |
|---|---|---|
| Q, SNDK, PSKY | 1 | 2026 |
| MRVL | 3 | 2025-11 |
| CRWD | 4 | 2024-01 |
| **RDDT** | **6** | **2025-03** ✓ (task's named case) |
| DASH, TKO | 6 | 2024-12 |
| BLK, SOFI | 7 | 2024-09 |
| SOLV, GEV, SW | 9 | 2024 (spin-offs) |
| HOOD, VLTO | 10 | 2023-12 / 2024-03 |
| PLTR, CRH, UBER | 11 | 2023 |

**RDDT is correctly flagged**, as required.

Honest scope note: the flag measures observations *in the window that produced the number*, per
the task's wording. It therefore catches genuinely-short history but **not** "long history with
sparse recent data" (e.g. BA has only 3 valid P/E quarters in the last 5 years because
loss-making quarters are masked, yet its rolling window still fills from older observations).
That is a different condition and would need a different flag.

---

## PART 5 — `fcf_exceeds_ebitda` — **IMPLEMENTED, neutrally named**

### 5.1 The SBC hypothesis was checked and is *not* reliably the driver

The condition holds in **1,969 periods across 207 tickers**. Decomposing the gap for the named
ticker plus the most frequent cases — what share of `FCF − EBITDA` does SBC actually cover?

| ticker | gap | SBC (TTM) | SBC as % of gap | largest working-capital item |
|---|---|---|---|---|
| **NOW** | $1,829M | $1,909M | **104%** | AP +$825M (45%) |
| CRM | $2,152M | $3,283M | 153% | AR −$15,903M (−739%) |
| ADSK | $645M | $764M | 118% | AR −$2,415M (−374%) |
| FFIV | $71M | $232M | **326%** | contract liab. +$414M (583%) |
| **FTNT** | $516M | $276M | **54%** | AR −$1,219M (−236%) |
| ADBE | $431M | $1,910M | **443%** | accrued liab. −$1,538M (−357%) |
| CSCO | $500M | $3,370M | **674%** | AR −$7,290M (−1458%) |
| **EA** | $838M | $568M | **68%** | AR −$576M (−69%) |

SBC covers anywhere from **54%** (FTNT) to **674%** (CSCO) of the gap. For FTNT and EA it is
not sufficient — working capital does the rest. For CSCO, ADBE and FFIV it *massively exceeds*
the gap, meaning the observed gap is a small net residual of large offsetting effects, and
calling it "SBC-driven" would be actively misleading. The population also isn't purely
software: CNC, MCK and CAH (healthcare distributors with structurally negative working capital)
are among the most frequent cases.

### 5.2 Implementation

Named `fcf_exceeds_ebitda` — purely descriptive, asserting only what was verified. Both sides
must be positive (a negative EBITDA makes the comparison trivially true and meaningless).
NOW is flagged in **38 of 38** evaluable periods.

---

## PART 6 — `sbc_ttm`, `owner_fcf`, `pfcf_ex_sbc` — **IMPLEMENTED**

### 6.1 Coverage checked first

Surveyed across all 498 tickers and every profile before building anything:
**98.2%** have a usable SBC tag (87.8% the plain `ShareBasedCompensation`). Weakest profiles
are `energy_integrated` 75% (6/8) and `materials_integrated` 87.5% (7/8); every other profile
is ≥93%. Broad enough to build on.

### 6.2 Implementation

`ShareBasedCompensation` added as a base concept (auto-TTM'd via `TTM_CONCEPTS`);
`owner_fcf = FCF_TTM − ShareBasedCompensation_TTM`;
`pfcf_ex_sbc = market_cap / owner_fcf`, guarded by the same denominator-scale guard as
`pfcf_ratio`, and hidden in the same profiles. Both inner-join on SBC availability, so a
ticker missing the tag gets **no** value rather than one silently identical to `pfcf_ratio`.
Realised coverage: **415 tickers** with `pfcf_ex_sbc` vs 457 with `pfcf_ratio`.

### 6.3 Verification — it tells a materially different story

| ticker | `pfcf_ratio` | `pfcf_ex_sbc` | ratio |
|---|---|---|---|
| **DDOG** | 40.6 | **155.0** | **3.82×** |
| **NOW** | 22.4 | **42.9** | **1.91×** |
| PANW | 37.9 | 67.6 | 1.78× |
| CRM | 10.5 | 13.8 | 1.32× |
| ADBE | 10.1 | 12.6 | 1.25× |
| FTNT | 36.5 | 40.3 | 1.10× |
| KO *(control)* | 26.2 | 26.8 | **1.02×** |

DDOG at 3.8× and NOW at 1.9× are genuinely different valuations; KO at 1.02× confirms the
metric collapses to `pfcf_ratio` where SBC is immaterial, as it should.

---

## PART 7 — `historical_band_elevated` — **IMPLEMENTED**

### 7.1 Design

Two real choices, stated rather than buried:

1. **Peer = profile-mate** (`TICKER_PROFILES`). That assignment already encodes this project's
   structural view of comparability — it drives which metrics are even shown per sector — so
   reusing it keeps one definition instead of inventing a second. **Profiles smaller than 5
   tickers are skipped entirely** (`alt_asset_manager` has 1, `homebuilder` 2, `airline` 3): a
   "sector median" over one or two peers is noise, and flagging against it would be worse than
   not flagging.
2. **The peer median is over each peer's own most recent value, not a strict same-date
   cross-section.** Fiscal calendars differ within every profile, so a same-date cross-section
   would silently drop most peers on most dates; "what do comparable companies trade at now" is
   also the question actually being asked. The cost — peers aligned to within a quarter rather
   than exactly — is acceptable for a median and is stated, not hidden.

### 7.2 Result

`<multiple>_band_elevated` = 1 when a ticker's own 5-year *minimum* still exceeds its profile's
current median, i.e. "near its own historical low" is not a value signal for this ticker.

| flag | flagged / evaluable |
|---|---|
| `p_tbv_band_elevated` | 87 / 358 |
| `p_ffo_band_elevated` | 79 / 475 |
| `ev_ebitda_band_elevated` | 69 / 351 |
| `pfcf_ratio_band_elevated` | 69 / 408 |
| `pe_ratio_band_elevated` | 66 / 483 |
| `p_ppnr_band_elevated` | 2 / 24 |
| `p_core_earnings_band_elevated` | 2 / 15 |

---

## PART 8 — `inorganic_contaminated` — **IMPLEMENTED**

Mirrors `calculate_buyback_distortion_flag()`'s mechanism: `Goodwill` growing >20% QoQ marks
growth metrics spanning that period as M&A-driven rather than organic. Requires a positive
prior goodwill base (0 → anything is an infinite percentage, and a first-ever acquisition is
already visible from the line appearing at all).

**Threshold confirmed against real data**: QoQ goodwill change is median **exactly 0.000**
(goodwill is static between deals), p90 4.6%, p95 14.5%, **p97 30.7%**. 20% sits between p95
and p97 → **1,006 of 24,919 periods (4.04%)** flagged across 361 tickers — a genuine tail.

**Both named tickers are flagged**, as expected:
- **NOW**: 10 periods — 2014-09-30, 2016-06-30, 2020-03-31, 2021-03-31, 2021-06-30, 2023-09-30, …
- **CRM**: 9 periods — 2010-07-31, 2011-01-31, 2011-07-31, 2012-10-31, 2013-07-31, 2016-07-31, …

---

## PART 9 — Effective tax rate + NOL flag — **IMPLEMENTED**

### 9.1 Tag coverage checked first

`IncomeTaxExpenseBenefit` **99.4%**; some pretax-income tag **99.0%** (the post-2009
`...MinorityInterestAndIncomeLossFromEquityMethodInvestments` variant first, older/narrower
variants as fallbacks). Both added as base concepts.

`effective_tax_rate = IncomeTaxExpense_TTM / PretaxIncome_TTM`, requiring a **positive** pretax
denominator (a loss-making quarter produces a tax *benefit* over negative pretax income, whose
ratio is arithmetically positive but means the opposite of a low tax burden), plus the same
`MIN_DENOMINATOR_SCALE_RATIO` guard used for `roe` against a near-break-even base.

**Correctness check**: the observed median effective rate is **22.5%** against a 21% US federal
statutory rate — the metric lands where it should.

### 9.2 The low-rate flag and verification

`low_tax_rate_flag` at <10%: **4,122 of 25,235 periods (14.2%)**. Distribution: p10 3.2%,
p25 15.1%, median 22.5%, p75 30.5%. 10% is less than half the statutory rate — an economic
definition rather than a bare percentile.

**60 tickers have a latest effective rate below 10%**, and the extreme end is exactly the
recently-profitable-young-company population Part 9.2 asked for:
**AXON −86%**, **UBER −76%**, AES −71%, MGM −36%, HPE −34%, FANG −28%. Negative rates are real
net tax *benefits* (valuation-allowance releases as accumulated NOLs become usable) — precisely
the NOL signature this flag was meant to surface.

---

## Final combined full-universe non-regression

All 498 tickers, full outer join on `(ticker, end, concept)`, reconstructed pre-task baseline
vs. post-change:

| table | base rows | new rows | unchanged | **changed** | removed | added |
|---|---|---|---|---|---|---|
| `metrics_long` | 535,874 | 664,101 | 535,874 | **0** | **0** | +128,227 |
| `valuation_history` | 252,508 | 272,219 | 252,508 | **0** | **0** | +19,711 |
| `snapshot` | 19,771 | 24,190 | 19,674 | **97** | **0** | +4,419 |

**`metrics_long` and `valuation_history`: not a single pre-existing value changed or was
removed.** Additions trace one-to-one to specific parts:

- `metrics_long` +128,227: `share_count_jump_flag` 30,706 (Part 3.3), `effective_tax_rate`
  28,997 + `low_tax_rate_flag` 25,235 (Part 9), `inorganic_contaminated` 24,919 (Part 8),
  `fcf_exceeds_ebitda` 18,370 (Part 5).
- `valuation_history` +19,711: `pfcf_ex_sbc` (Part 6).
- `snapshot` +4,419: 7 × `avg_X_5y_history_too_short` (Part 4) + 7 × `<multiple>_band_elevated`
  (Part 7).

**All 97 snapshot changes accounted for exactly:**

| rows | what | why |
|---|---|---|
| 38 | `shares_source_is_edgar` | 35 pre-existing dual-class switches previously misreported as 0.0 (bug fix) + KLAC/CRWD/DVN newly switching (Part 1) |
| 35 | `shares_delta_pct` | the same 35 tickers, previously reporting a false 0.0% delta (bug fix) |
| 24 | 8 concepts × KLAC/CRWD/DVN | `shares_outstanding`, `market_cap`, `ev`, `ev_ebitda`, `ev_sales`, `pb_ratio`, `p_tbv`, `pfcf_ratio` — Part 1's intended correction |

38 + 35 + 24 = 97. Nothing implemented in an earlier part was disturbed by a later one, and no
value outside these three groups moved.

Plotting was smoke-tested end-to-end (`plot_valuation` + `plot_fundamentals`) for NOW
(standard), JPM (financial), O (reit) and KLAC (a Part 1-corrected ticker) — all render with
the new `pfcf_ex_sbc` panel and no errors.

---

## Summary

| part | outcome |
|---|---|
| 1 — symmetric share-count resolution | **Implemented** (+ fixed a pre-existing audit-column bug) |
| 2 — `debt_inferred_zero` | **Not implemented** — heuristic fails all three of its own reference cases |
| 3.1/3.2 — dual-class summing | **Unnecessary** — no per-class facts exist; values already consolidated |
| 3.3 — share-count QoQ guard | **Implemented** |
| 4 — `history_too_short` | **Implemented** |
| 5 — `fcf_exceeds_ebitda` | **Implemented**, neutrally named after disproving the SBC hypothesis |
| 6 — `sbc_ttm` / `owner_fcf` / `pfcf_ex_sbc` | **Implemented** |
| 7 — `historical_band_elevated` | **Implemented** |
| 8 — `inorganic_contaminated` | **Implemented** |
| 9 — effective tax rate + NOL flag | **Implemented** |

No scratch scripts left behind.
