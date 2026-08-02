# Documentation Catch-Up + Five SoFi-Driven Improvements

Part 0 updated the bugfix history; Parts 1-5 are five improvements from a SOFI analysis.
**Four implemented, one confirmed not implementable with this project's real data.**
Two of the implemented parts produced findings that contradict the brief's own expectations,
reported as found rather than forced to match.

---

## PART 0 — `bugfixes_opdate_history.md` caught up

### 0.1 The gap

The file is `MDs/bugfixes_opdate_history.md` (the brief called it
`bugfixed_update_history.md`; no file by that name exists). Its last entry was
**2026-07-29**, and it had 47 entries.

**None of the eight task reports the brief lists as sources exist** — not
`quarterly_and_growth_expansion_report.md`, not `nine_improvements_report.md`, none of
them. They have been removed from the working tree since being written. So Step 0.2's
fallback applied in full: every entry was reconstructed from **the actual current code
state**, verified by reading the live files, not from any report and not from memory of
intent.

Checking which prior "add an entry" instructions were actually followed: **none of the
eight tasks after 2026-07-29 had been logged**. One item on the brief's minimum list was
already covered, though, and was deliberately **not** duplicated: the `calculate_growth`
date-alignment fix is documented in the existing **2026-07-27** entry ("New bug class:
positional vs. date-based period alignment").

### 0.2 What was added

Eight entries, dated 2026-07-30 through 2026-08-02:

| date | entry |
|---|---|
| 2026-08-02 | Nine external-review improvements (7 built, 1 refused, 1 premise disproven) + the share-count audit bug |
| 2026-08-01 | Buyback-distortion flag, tangible-book P/B hide, harmonic-mean 5y averages, share-count transparency, `ev_fcf` |
| 2026-08-01 | Full-universe validation of the staleness-aware refetch |
| 2026-07-31 | `fetch_or_cache` TTL mechanism built on the submissions index |
| 2026-07-31 | META's SEC-aggregation-lag finding, share-count source conflict, `peg_ratio` rename |
| 2026-07-30 | Denominator guard wired into `build_valuation_history`, six ticker data bugs, `MAX_MULTIPLE` removed |
| 2026-07-30 | `build_valuation_history` market-cap coupling fix |
| 2026-07-30 | Quarterly values alongside TTM + growth columns on every non-TTM concept |

Every claim was verified against the live code before writing: `MAX_MULTIPLE` and
`calculate_historical_pe` confirmed **absent**; `_KNOWN_BAD_FACTS` confirmed at **44
`(ticker, tag)` keys / 120 facts**, of which the 10 keys / 39 facts from the ticker-bug
task were counted individually; all new constants read from source
(`MIN_VALUATION_DENOMINATOR_SCALE_RATIO = 0.001`, `MIN_BUYBACK_EQUITY_QOQ_DECLINE = 0.15`,
`MIN_GOODWILL_QOQ_GROWTH = 0.20`, `MIN_PEER_GROUP_SIZE = 5`, and the rest).

**Dating caveat, stated rather than hidden.** The three most recent entries are anchored to
hard evidence (cache sidecars showing `last_refetch_attempt: 2026-08-01`, file mtimes, and
this session's own observed runs). The 2026-07-30/31 dates are reconstructed from
**ordering**, not from a dated artifact — the reports that would have carried exact dates
were deleted. The sequence is certain; the exact calendar days for those five entries are
a best reconstruction.

### 0.3 Verification of the file itself

Re-read after writing: **55 entries, 0 chronological violations** (strict newest-first),
**0 duplicate titles**, and no entry contradicts an existing one.

### A live bug found during the audit — reported, not fixed

`VALUATIONS_TO_PLOT` in `config.py` still lists `("peg_ratio", "PEG Ratio Revenue", ...)`,
but the pipeline renamed that concept to `pe_to_revenue_growth` and **no longer produces
`peg_ratio` at all** (confirmed: zero occurrences as an output concept in `main.py`). That
valuation panel therefore renders "keine Daten" for every one of the 498 tickers. The
rename reached `main.py`, `figures.py` and the encyclopedia but missed this list.

Not fixed here, because the brief states Part 0 is documentation-only and Parts 1-5 don't
cover it. It is logged in the 2026-07-31 history entry as a known open gap. **The fix is
one line** — change that tuple's first element to `"pe_to_revenue_growth"` — and I'd
recommend it as the next thing done.

---

## PART 1 — `share_count_jump_flag` as an edge event — **IMPLEMENTED**

### 1.1 Confirmed current behaviour

The flag attached to the **later** quarter of each QoQ pair. SOFI is exactly the case the
brief describes:

| end | SharesOutstanding | flagged (before) |
|---|---|---|
| 2023-09-30 | 1,902,366,214 | no |
| **2023-12-31** | **1,890,048,000** | **no** |
| **2024-03-31** | **1,042,477,000** (−44.8%) | **yes** |
| 2024-06-30 | 1,065,171,000 | no |

The 1.89bn side is the suspect one (SOFI has run ~1.0-1.4bn since), yet it carried no flag
and **fed every rolling average normally** — the bias the finding is about.

### 1.2 Implementation, and the deliberate asymmetry

`calculate_share_count_jump_flag()` now emits **both** bracketing quarters. Reasoning: a QoQ
test can only say the *transition* is unexplained; it can never say which side holds the bad
count, so marking one is arbitrary.

Downstream consumers were traced rather than guessed. Every multiple in
`HARMONIC_MEAN_CONCEPTS` is share-count-derived — through `market_cap` for
`pb_ratio`/`pfcf_ratio`/`ev_*`/`p_tbv`/`p_ppnr`/`p_core_earnings`/`p_ffo`, and through
`EPS_TTM_CALC` for `pe_ratio`. Both flagged quarters are now excluded from:

- `calculate_rolling_multiple_averages()` — the `avg_X_5y` harmonic mean, `_median` and `_n`;
- `calculate_peer_band_flags()` — where it matters most, since `own_5y_low` is a **min** and
  a single suspect quarter can define it outright.

**Point-in-time metrics are deliberately NOT masked** (`market_cap`, `pe_ratio`, `pb_ratio`
… for that quarter still show). The reasoning: the flag establishes that one of two counts
is wrong, not which, so masking both quarters' multiples would delete a correct value on
suspicion — a pure loss for whichever side is fine. For an *aggregate* the calculus
reverses: one bad observation contaminates a statistic meant to describe a multi-year norm,
so exclusion is cheap and inclusion is expensive. Verified structurally: `valuation_history`
came out **byte-identical, 0 changed / 0 removed / 0 added**.

### 1.3 SOFI verification — honest result

The bracketing works: SOFI's flagged set went from `[2021-03-31, 2021-06-30, 2024-03-31]` to
`[2020-12-31, 2021-03-31, 2021-06-30, 2023-12-31, 2024-03-31]`.

The bias correction on SOFI itself is **real but small**:

| field | before | after | change |
|---|---|---|---|
| `avg_p_tbv_5y` | 3.105 | 3.071 | **−1.1%** |
| `avg_pe_5y` | 40.023 | 40.023 | 0.0% |

`avg_pe_5y` doesn't move because SOFI has no valid `pe_ratio` in the excluded quarters (it
was loss-making then), so there was nothing to exclude. Reported rather than presented as a
larger win than it is — the structural fix is right, but **SOFI is not the ticker where it
pays off most.** Universe-wide it is substantial: **129 tickers, 663 changed fields**,
including AAPL, AMD, COF, DUK, ETN, FCX.

### 1.4 Non-regression

- `metrics_long`: **516 changed, all `share_count_jump_flag`**; 48 added (prior quarters that
  previously had no flag row). Nothing else touched.
- `valuation_history`: **0 changed / 0 removed / 0 added** — the exclusion provably did not
  leak into any per-period metric.
- `snapshot`: 667 changed, **every one an `avg_X_5y*` field or a `_band_elevated` flag**
  (band changes: CL, COHR, SCHW, WAT).
- Attribution check: of the 129 tickers whose averages moved, **0 lack a genuinely flagged
  jump**.

---

## PART 2 — `shares_basis` — **IMPLEMENTED**

### 2.1 Classification — and a correction to my own first pass

A first classification asked "which configured tag exists for this ticker" and concluded the
field was constant. That was wrong, and re-reading `extract_merged_values()` showed why:
the `fallback` mode resolves **per end-date**, not per ticker — tags are tried in order and
the first with a value for a given date supplies it. Redone correctly:

| scope | result |
|---|---|
| per (ticker, period) | 31,320 `diluted_wavg` vs **503 `period_end`** |
| per ticker, whole history | 396 pure `diluted_wavg`, **99 mixed** |
| per ticker, at its latest period | 490 `diluted_wavg`, **5 `period_end`** (HSY, LYB, REG, SJM, WAT) |

`resolve_shares_basis()` mirrors the per-date fallback and reports the basis of the
**newest** value, since that is the one `shares_delta_pct` compares against yfinance.

**The finding is much broader than SOFI.** 490 of 495 tickers compare a *diluted
weighted-average* EDGAR count against yfinance's *period-end* count — a systematic
definitional mismatch across essentially the whole universe, not a SOFI quirk. SOFI's
`shares_basis = diluted_wavg` with `shares_delta_pct = 6.80%`, confirming the brief's read
that its delta is definitional rather than a bug.

### 2.2 / 2.3

Emitted as `shares_basis` for 495 tickers, encoded numerically (`SHARES_BASIS_CODES`:
`diluted_wavg` = 0.0, `period_end` = 1.0) for the same reason `fundamentals_stale` is —
the long format's single `value` column would become `object` dtype on reload if any row
held a string. Purely additive: **+495 snapshot rows, 0 changed, 0 removed.**

---

## PART 3 — `filing_likely_overdue` — **IMPLEMENTED, with the verification failing as specified**

### 3.1 Per-ticker cadence, and why the buffer is small

17,779 filings across all 498 tickers. Lag from fiscal period end to filing date:

| | median | p90 | max |
|---|---|---|---|
| 10-K | 52 d | 59 d | 172 d |
| 10-Q | 32 d | 39 d | 176 d |
| per-ticker median (pooled) | 34 d | — | 49 d |

Pooling the two forms is what makes a ticker's own variance look large: within-ticker
`p90 − median` is **17.8 days pooled**, but only **3.0 days** once split by form (p90 across
tickers = 7 days). So the cadence is stored **per (ticker, form)**, and
`FILING_LAG_BUFFER_DAYS = 7` is the p90 of real within-(ticker, form) variation — calibrated,
not a round number.

### 3.2 Implementation, and a correction to the brief's formula

The brief's literal rule (most recent **known** period end + lag + buffer) fires perpetually:
the most recent known period end is by definition one that was already filed, so its due
date is always in the past. The implementation projects **one quarter forward** to the next
*expected* period end — safe, because consecutive period-end spacing is a tight median 91
days (p10 90, p90 92) — picks the expected form from the ticker's own fiscal-year-end month,
and suppresses the flag if a newer filing has already appeared. Also emits
`days_past_expected_filing` so the margin is visible, not just the boolean.

**5 of 498 tickers currently flagged**: ARE, C, CAH, KMB, TAP.

### 3.3 META — the verification does **not** confirm what the brief expected

| | |
|---|---|
| META 10-Q median lag | **31 days** (10-K: 29.5) |
| 2026-06-30 10-Q actually filed | **2026-07-30** (lag 30 days) |
| Flag's predicted due date | 2026-06-30 + 31 + 7 = **2026-08-07** |

META filed **8 days before** the flag would have fired, so `filing_likely_overdue` would
**not** have caught META's case — and it is correct not to. META's filing cadence is
extremely regular (last nine filings: 32, 31, 30, 31, 31, 30, 29, 30, 30 days); it was never
late. **META's problem was never a late filing — it was SEC-side aggregation lag after an
on-time one**, which is precisely what the reactive `fundamentals_stale` guard already
covers. The brief's framing of META as the predictive case is a category error, and forcing
the buffer down to make it fire would have produced false positives across the universe for
no gain.

### 3.4 Non-regression

Purely additive: **+996 snapshot rows** (498 `filing_likely_overdue` + 498
`days_past_expected_filing`), 0 changed, 0 removed.

---

## PART 4 — `fair_value_marks_to_tbv` — **NOT IMPLEMENTABLE (confirmed)**

The brief explicitly warned not to assume `CumulativeFairValueAdjustments` is real. It is
not — **the tag does not exist in SOFI's payload, or anywhere in the cached universe.**

Investigating what SOFI actually has:

| | value |
|---|---|
| `AccumulatedOtherComprehensiveIncomeLossNetOfTax` | **−$2,743,000** @ 2026-03-31 |
| `StockholdersEquity` | $10,811,591,000 |
| `Goodwill` | $1,393,505,000 |
| ⇒ TangibleEquity | $9,418,086,000 |
| ⇒ AOCI / TangibleEquity | **−0.03%** |

The motivating analysis's **21.4%** cannot be reproduced, and not by a small margin — the
only AOCI figure SOFI reports is **negative and three orders of magnitude too small**. SOFI
has exactly **two** AOCI tags total, and the only loan-level fair-value tag,
`LoansReceivableFairValueDisclosure`, last reports at **2022-09-30** — over three years
stale, and a fair-value *level* rather than a cumulative adjustment.

Profile-wide coverage of the plausible alternatives is also weak:
`AccumulatedOtherComprehensiveIncomeLossNetOfTax` 25/26 `financial` tickers, but the
AFS-specific components that would isolate securities marks are 11/26 and 18/26, and two
plausible candidates are **0/26**.

So there is no tag, at SOFI or across the profile, that reproduces the intended quantity.
Building the metric from AOCI-net-of-tax would ship a number that is **not** what the name
claims and is off by orders of magnitude for the one ticker it was specified from. Per the
brief's explicit instruction, this is reported as a complete answer and left undone rather
than approximated.

---

## PART 5 — `ROTCE` — **IMPLEMENTED**

### 5.1 Scope decided from evidence, not assumed

`rotce = NetIncomeLoss_TTM / TangibleEquity`, guarded exactly as `roe` is
(`require_positive_denominator` plus the `MIN_DENOMINATOR_SCALE_RATIO` scale guard against
`Revenue_TTM`), with `TangibleEquity` substituted for `StockholdersEquity`.

Scope is **not** financial-only. Measured median `Goodwill / StockholdersEquity`:

| profile | median goodwill/equity | `p_tbv` visible? |
|---|---|---|
| `financial` | **19.5%** | yes |
| `insurance_life` | **10.7%** | yes |
| `insurance_pc` | **7.7%** | yes |

Goodwill is material in all three, and those are exactly the three profiles where `p_tbv` is
already visible — so `rotce` follows `p_tbv`'s visibility precisely. Verified programmatically:
the set of profiles where `rotce` is visible equals the set where `p_tbv` is, and
`filter_hidden_rows()` reduces `rotce` from 25,392 raw rows to **2,274 rows across exactly 40
tickers** (25 financial + 10 insurance_pc + 5 insurance_life).

SOFI, the motivating case: **`roe` 5.34% vs `rotce` 6.13%** — rotce higher, as it must be for
a bank carrying $1.39bn of goodwill against $10.8bn of equity.

### 5.2 The scatter plot — confirmed feasible, deliberately not built

Not built, per the brief. Confirmed the inputs are ready: **25 of 26 `financial` tickers have
both `p_tbv` and `rotce`** cleanly available per ticker (SOFI: `p_tbv` 2.323, `rotce` 6.13%,
both at 2026-03-31). A cross-sectional `p_tbv` vs `rotce` scatter is straightforward whenever
the web app arrives; this project's current output is per-ticker matplotlib figures, so it
remains future scope.

### 5.3 Non-regression

Purely additive: +25,392 raw `metrics_long` rows (2,274 after profile filtering), 0 changed,
0 removed.

---

## Final combined non-regression (all 498 tickers)

| table | base | new | unchanged | **changed** | removed | added |
|---|---|---|---|---|---|---|
| `metrics_long` | 664,101 | 689,541 | 663,585 | **516** | **0** | +25,440 |
| `valuation_history` | 272,219 | 272,219 | 272,219 | **0** | **0** | **0** |
| `snapshot` | 24,190 | 25,681 | 23,523 | **667** | **0** | +1,491 |

Every change traces to a specific part:

- `metrics_long` 516 changed = **all `share_count_jump_flag`** (Part 1 bracketing);
  added = 25,392 `rotce` (Part 5) + 48 new flag rows (Part 1).
- `valuation_history` **entirely unchanged** — the strongest confirmation that Part 1's
  behavioural change did not leak into any other metric's calculation, exactly as required.
- `snapshot` 667 changed = **all `avg_X_5y*` rolling fields plus 4 `_band_elevated` flags**
  (Part 1); added = 498 `filing_likely_overdue` + 498 `days_past_expected_filing` (Part 3) +
  495 `shares_basis` (Part 2).
- Attribution verified: **0 of the 129 tickers whose averages moved lack a genuinely flagged
  jump.**

Two self-inflicted errors were caught by this task's own verification and fixed before
shipping: a bulk regex adding `rotce` alongside `p_tbv` also injected it into
`HARMONIC_MEAN_CONCEPTS` (causing a `KeyError` on the first pipeline run) and into a
`VALUATIONS_TO_PLOT` tuple (silently malforming it). Both corrected, and all plot-list tuple
shapes re-validated programmatically afterwards.

Plotting smoke-tested end-to-end for SOFI and JPM (`financial`), PGR (`insurance_pc`), AAPL
(`standard`) and O (`reit`) — all render, including the new `rotce` panel.

---

## Summary

| part | outcome |
|---|---|
| 0 — history catch-up | **Done** — 8 entries added, verified; 1 already-covered item not duplicated; 1 live bug found and reported |
| 1 — jump as edge event | **Implemented** — both quarters excluded from aggregates, point-in-time deliberately preserved |
| 2 — `shares_basis` | **Implemented** — and the mismatch is universe-wide (490/495), not SOFI-specific |
| 3 — `filing_likely_overdue` | **Implemented** — but META verification honestly fails; META was never late |
| 4 — `fair_value_marks_to_tbv` | **Not implementable** — the tag doesn't exist; SOFI's AOCI is −0.03%, not +21.4% |
| 5 — `rotce` | **Implemented** — scoped to all three `p_tbv` profiles on measured goodwill materiality |

No scratch scripts left behind.
