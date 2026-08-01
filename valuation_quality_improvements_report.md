# Valuation Quality Improvements — Buyback Flag, Harmonic-Mean Averages, Share-Count Transparency, EV/FCF

Four independent improvements, each investigated against real cached data before implementing,
each verified against a real case, and all four checked together in one full-universe
before/after non-regression pass (498 active tickers, local cache + live yfinance prices, no
sampling).

---

## PART 1 — Buyback-distortion flag + tangible book value

### 1.1 Detecting the pattern — calibrated, not guessed

A "profitable company shrinking its own equity base via buybacks" flag: `StockholdersEquity`
falls more than `X`% quarter-over-quarter while `NetIncomeLoss_TTM` stays positive, restricted
to periods where equity was **positive both quarters** — an already-negative or near-zero
equity base is the existing scale guards' territory (a different, already-understood story;
confirmed directly that AZO, whose equity has been continuously negative since 2009, correctly
never qualifies for this flag at all).

Measured the QoQ equity-decline distribution across the whole cached universe, profitable/
both-positive periods only: **p97 = 13.3%, p99 = 28.3%**. Checked where the five named
buyback-heavy names actually sit (own-history percentiles): ORLY p90=33.4%, MCD p90=17.4%,
HD p90=27.7%, LOW p90=19.8% (AZO has zero qualifying quarters — see above). **Threshold set to
15%**: already a rare tail event universe-wide (above p97), while still catching the upper tail
of four of the five names' own history.

`MIN_BUYBACK_EQUITY_QOQ_DECLINE = 0.15` in `main.py`.

### 1.2 Suppress or flag — recommendation: flag, deliberately deviating from the mask convention

Every guard in this project so far **masks** (hides the number) rather than flags. Recommending
a deliberate departure here: unlike the near-zero/negative-equity cases the existing guards
mask (where the resulting ratio is genuinely nonsensical), a buyback-driven equity decline
produces a **mathematically valid, real, and informative** `pb_ratio`/`roe` — for exactly the
kind of high-quality compounder (ORLY, HD, MCD, LOW) where investors most want to see it.
Masking would delete real information; flagging preserves it with context. This mirrors a
precedent already in the codebase — `add_staleness_fields()`'s `fundamentals_stale` — a
value-triggered flag *alongside* the data it describes, not a mask of it.

Implemented as a new concept, `buyback_distortion_flag` (1.0/0.0), emitted alongside `pb_ratio`
in `valuation_history` and alongside `roe` in `metrics_long` (single shared implementation,
`calculate_buyback_distortion_flag()`, called from both places — not two independent formulas).
Confirmed directly that the flag is purely informational and does **not** suppress `pb_ratio`:
ORLY's 2017-06-30 is buyback-flagged and still shows `pb_ratio = 15.3`.

**Real-case result** (full cached history, all tickers):

| ticker | flagged periods |
|---|---|
| ORLY | 7 — 2017-06-30, 2017-09-30, 2018-03-31, 2018-12-31, 2019-06-30, 2020-03-31, 2020-12-31 |
| MCD | 4 — 2014-09-30, 2015-09-30, 2016-03-31, 2016-06-30 |
| HD | 10 — 2016-01-31 … 2024-01-28 |
| LOW | 5 — 2019-02-01 … 2021-04-30 |
| AZO | 0 (equity never positive both quarters — correctly excluded) |

Universe-wide: **641 flagged (ticker, end) pairs across 221 unique tickers** (out of 28,830
evaluable periods).

### 1.3 `tangible_book` and hiding `pb_ratio` when negative

Checked directly, project-wide (grepped every `CONCEPT_CANDIDATES` entry, not just one ticker):
**no `IntangibleAssetsNetExcludingGoodwill`-style concept exists anywhere** in this project —
every "Intangible" hit is an amortization *expense* tag (income statement), not a balance-sheet
intangibles-net stock. So the fallback applies, per the task's own precedent (same
simplification already made for FFO): `tangible_book = StockholdersEquity - Goodwill`.

That is **exactly** the existing `TangibleEquity` concept (`main.py`'s `add_derived_concepts()`,
already used for `p_tbv`) — not a second, parallel field. `tangible_book` **is** `TangibleEquity`;
no new concept was built, avoiding the "second, possibly-inconsistent version" the task warned
against. `p_tbv` itself already masks correctly (`.where(TangibleEquity > 0)`); what was missing
is that the *ordinary* `pb_ratio` (goodwill-inclusive P/B) had no equivalent guard — a negative
tangible book was silently allowed to produce a technically-computed-but-undefined P/B. Fixed in
both `build_valuation_history()` and `build_snapshot()`: `pb_ratio` is now masked wherever
`TangibleEquity < 0`.

**Real-case result**, exactly the five named tickers — every one currently has negative
tangible equity, and `pb_ratio` is now correctly hidden for all five where it previously showed
a number (some of them looking deceptively "normal"):

| ticker | tangible_equity | old `pb_ratio` | new `pb_ratio` |
|---|---|---|---|
| ORLY | -2.02B | -68.3 | *(hidden)* |
| MCD | -4.64B | -149.5 | *(hidden)* |
| HD | -8.61B | **23.9** (looked fine!) | *(hidden)* |
| LOW | -13.2B | -12.6 | *(hidden)* |
| AZO | -3.09B | -17.7 | *(hidden)* |

HD's case is the clearest argument for this fix: -8.6B tangible equity was producing a
plausible-looking `pb_ratio = 23.9` that gave no hint anything was wrong.

### 1.4 Non-regression

Full before/after outer join on `(ticker, end, concept)`, all 498 tickers, both `valuation_history`
and `metrics_long`:

- `metrics_long`: **507,044/507,044 pre-existing rows unchanged**, 0 removed, 0 changed. Only
  addition: 28,830 new `buyback_distortion_flag` rows.
- `valuation_history`: **204,262 pre-existing rows unchanged**, 0 changed. **4,756 `pb_ratio`
  rows removed** — every one is the intended negative-tangible-book hide (verified: these are
  exactly the rows where `TangibleEquity < 0`). Additions: `buyback_distortion_flag` + `ev_fcf`
  (Part 4) rows.

No other value in either table changed.

**A bug caught during this task's own verification, not by the user:** the first implementation
of `calculate_buyback_distortion_flag()` combined a freshly-computed boolean mask with a
column from a `pd.merge()` result using `&` — since `pd.merge()` resets the row index, this
silently misaligned the two by pandas' index-based operator alignment, and the function returned
almost nothing (ORLY: 0 flagged instead of 7). Caught by comparing the real function's output
against the calibration script's independent computation, which disagreed. Fixed by computing
the mask as a column *on* the pre-merge frame instead of a free-standing `Series`, so it survives
the merge row-for-row. Re-verified against the calibration numbers (641 total, exact match) and
re-ran the full non-regression pass above on the corrected code.

---

## PART 2 — `avg_pe_5y` and friends: harmonic mean, not arithmetic

### 2.1 Scope of "average of a ratio" reference lines

Two distinct constructions found, not one:

1. **`plot_metric`'s `show_mean=True`** (`figures.py`), invoked from **`plot_valuation()`** for
   *every* concept in `VALUATIONS_TO_PLOT` — 11 multiples, not just P/E.
2. **`avg_pe_5y`**, a rolling-20-quarter snapshot field built by `calculate_historical_pe()`
   (now replaced — see 2.3), P/E-only, feeding `build_snapshot()`.

### 2.2 Which multiples actually need it — measured, not assumed

Measured arithmetic-vs-harmonic divergence over each ticker's last 5 cached years, for every
candidate multiple:

| concept | n tickers | median reldiff | p90 | max | n>25% |
|---|---|---|---|---|---|
| pe_ratio | 487 | 9.9% | 105% | 766% | 143 |
| pfcf_ratio | 410 | 11.6% | 117% | 1139% | 127 |
| p_tbv | 358 | 9.9% | 92% | 1940% | 105 |
| p_ffo | 481 | 6.3% | 57% | 44524% | 89 |
| ev_ebitda | 352 | 4.0% | 43% | 23153% | 52 |
| p_ppnr | 24 | 5.7% | 14% | 480% | 2 |
| p_core_earnings | 14 | 9.5% | 104% | 422% | 3 |
| **ev_sales** | 437 | **3.2%** | 18% | 255% | 28 |
| **dividend_yield** | 372 | **4.1%*** | 21% | 664%* | 31 |
| **pe_to_revenue_growth** | 466 | **46.7%** | 205% | 6976% | 343 |

**In scope** (materially distorted by thin denominators, same "price/[flow]" or "EV/[flow]"
construction as P/E): `pe_ratio`, `pfcf_ratio`, `ev_ebitda`, `p_tbv`, `p_ppnr`,
`p_core_earnings`, `p_ffo`.

**Excluded, with evidence:**
- `ev_sales` — revenue realistically never approaches zero for an active operating company;
  measured divergence is the smallest of the group (~3%), consistent with the theory.
- `dividend_yield` — not a price/flow multiple in the same sense (already a *yield*); its large
  "divergence" figures are a floating-point artifact of comparing two near-zero numbers for
  non/low-dividend payers (e.g. NVDA: arithmetic=0.0000, harmonic=0.0000, "reldiff"=6.6 is noise,
  not a real distortion).
- `pe_to_revenue_growth` — a ratio-of-a-ratio with its own dedicated guards already
  (`MIN_PEG_REVENUE_GROWTH`, `MAX_PEG_RATIO_ABS`); 1/x here isn't a standard "yield" concept the
  way earnings-yield or FCF-yield is, so the harmonic-mean interpretation doesn't carry over
  cleanly, despite the large measured divergence.

`HARMONIC_MEAN_CONCEPTS` in `config.py` records this scope and the reasoning.

### 2.3 Implementation

`metrics.py`: `harmonic_mean(values)` (static, for the chart reference line) and
`calculate_rolling_harmonic_stats(df, value_col, window, prefix)` (rolling harmonic mean +
median per ticker, trailing window, non-positive values excluded from the sum exactly like
every existing ratio guard already excludes them).

**Chart reference line** (`figures.py`): `plot_metric` gained a `harmonic: bool` parameter;
`plot_valuation()` passes `harmonic=concept in HARMONIC_MEAN_CONCEPTS` per panel.

**Snapshot rolling field**: `calculate_historical_pe()` (P/E-only, arithmetic, its own ad-hoc
`pe_ratio` recompute with no denominator guard at all) is **replaced** by
`calculate_rolling_multiple_averages(valuation_history)`, which sources every in-scope
multiple's series from `build_valuation_history()`'s **already-guarded** output instead of
recomputing raw ratios — so the rolling average can no longer silently drift from the
denominator-scale guards applied elsewhere. Generalizes `avg_pe_5y` to seven fields
(`AVG_5Y_FIELD_NAMES` in `main.py`): `avg_pe_5y`, `avg_pfcf_5y`, `avg_ev_ebitda_5y`,
`avg_p_tbv_5y`, `avg_p_ppnr_5y`, `avg_p_core_earnings_5y`, `avg_p_ffo_5y` — each with a
`_median` sibling and a `_diverges` flag.

**Divergence flag threshold**: measured `|harmonic − median| / median` across the same 5y
window for the seven in-scope concepts: median 4.5%, p75 9.9%, **p90 19.4%**. Set to **0.20**
(~p90, flags 9.2% of ticker-concept pairs) — a deliberately selective, tail-focused signal.
`MIN_AVG_5Y_DIVERGENCE = 0.20` in `main.py`.

`is_hidden()` visibility was extended to the 21 new fields (`_DERIVED_CONCEPT_CONSUMERS` in
`config.py`): each `avg_X_5y`/`_median`/`_diverges` triple is hidden exactly when its underlying
multiple is hidden for that profile (e.g. `avg_pfcf_5y*` is hidden for `financial`, same as
`pfcf_ratio` already is) — verified directly (`is_hidden("JPM", "avg_pfcf_5y_median")` → `True`).

### 2.4 Verified against real cases

**Thin-earnings ticker — MCHP**, last 5 cached years: P/E ranged 15.9–152.4 as earnings
compressed into 2024–2026 (95.7, then 152.4 in the last two quarters). **Arithmetic mean 41.6
vs. harmonic mean 26.6** — the harmonic mean correctly refuses to let two extreme late-window
readings dominate the average the way the arithmetic mean does.

**Stable ticker — KO**, same window: P/E ranged a narrow 20.8–28.4 throughout.
**Arithmetic 23.86 vs. harmonic 23.71** — a 0.6% difference, confirming the two constructions
agree closely when there's no thin-denominator distortion to correct for.

**A genuine bug fix surfaced along the way**: the old `avg_pe_5y` for BKR was **-215.6** — a
negative "average P/E," because the old ad-hoc PE recompute had no positive-denominator guard
at all and happily averaged in negative-earnings quarters. BKR has zero qualifying (positive
P/E) quarters in its cached window either way; the new, properly-guarded computation correctly
reports no value instead of a nonsensical negative average.

### 2.5 Non-regression

`snapshot`: **11,865 pre-existing rows unchanged**. **491 rows changed — all `avg_pe_5y`**,
exactly the intended arithmetic→harmonic change (verified: 0 unexpected changes in any other
concept). **112 rows removed**: 111 `pb_ratio` (Part 1.3) + 1 `avg_pe_5y` (BKR — the bug fix
above; both old and new agree there's no valid P/E history, the old code just didn't know that).
Additions: 21 new `avg_X_5y*` fields, plus Part 3/4's new columns.

---

## PART 3 — Share-count source transparency

### 3.1 / 3.2 `shares_source_is_edgar` and `shares_delta_pct`

Refactored the existing dual-class resolution (`resolve_snapshot_share_count()`, from the prior
META-fix task) into a shared `_resolve_share_sources()` — the *same* `prefer_edgar` boolean and
underlying edgar/yfinance share counts feed both the market-cap resolution and these two new
audit columns, not a second, independently-maintained comparison.

`shares_source_is_edgar` is emitted as **1.0/0.0** rather than a literal string: this project's
long-format `(ticker, end, concept, value)` schema has a single numeric `value` column shared by
every concept in the file, and one string row would force the whole CSV column to `object` dtype
on reload, silently breaking every downstream numeric consumer. Encoded the same way this
project's existing `fundamentals_stale` flag already is, and documented here and in-code.

`shares_delta_pct = (edgar_shares − yf_shares) / yf_shares × 100`, computed for **every** active
ticker (not just ones already flagged dual-class).

**Full distribution** (495 tickers with both sources present): median 0.65%, p75 1.4%,
p90 2.8%, p95 4.4%, max (edgar-larger direction) 8.14%. **0 tickers currently cross the existing
10% switch-to-EDGAR threshold** in this cached snapshot.

**A real finding the broader scope surfaced, not caught by the existing (deliberately
asymmetric) dual-class check:**

| ticker | delta | edgar shares | yfinance shares |
|---|---|---|---|
| KLAC | **-89.9%** | 131.75M | 1,306.3M (≈9.9×) |
| CRWD | **-74.7%** | 257.9M | 1,018.3M (≈4.0×) |
| DVN | **-46.4%** | 618M | 1,153.4M (≈1.9×) |
| BKR | -18.8% | 806M (stale, 2021) | 992.7M |
| TSLA | -10.4% | 3,540M | 3,949.5M |

The existing rule only switches to EDGAR when `edgar/yf > 1.10` (EDGAR *larger*) — a
deliberate, asymmetric design from the prior task, built for EDGAR reporting a stale pre-split
share count. KLAC/CRWD/DVN are the **opposite** case, and by a much larger and more suspicious
margin than TSLA's: yfinance's count is implausibly large (KLAC's real share count is ~130M —
its EDGAR figure — not yfinance's ~1.3B; a near-exact 10× or 4× or 2× factor points at a data
quality issue on yfinance's side, not a legitimate ~10% timing difference like TSLA's). Nothing
in the current mechanism catches this, because `normalize_split_adjusted()` is only ever applied
to the EDGAR-sourced `facts` series, never to yfinance's separately-fetched
`shares_outstanding`. For KLAC/CRWD/DVN specifically, `market_cap` (and everything derived from
it: `pe_ratio`, `pb_ratio`, `ev_ebitda`, …) is very likely wrong by a large factor in the
current snapshot.

**Recommendation** (not implemented here, per this task's scope — a visibility-threshold
decision belongs to a follow-up, per this project's standing practice for structural findings):
extend the resolution rule to also catch large *negative* deltas (yfinance overstating), or at
minimum flag/hide market-cap-derived metrics for tickers past some negative-delta threshold.
This is now visible and measurable via `shares_delta_pct` specifically because it's reported for
every ticker, not only the ones the dual-class check already caught.

### 3.3 Non-regression

Purely additive by construction — both new columns are new concept rows, nothing else changes.
Confirmed as part of the combined snapshot diff in 2.5/4.5: the 7,415 added rows include exactly
495×2 = 990 `shares_source_is_edgar`/`shares_delta_pct` rows (the remainder being Part 2's 21
new field × tickers), and 0 pre-existing snapshot values changed because of this part.

---

## PART 4 — `ev_fcf`: leverage-aware FCF multiple

### 4.1 Implementation

`build_valuation_history()`: `wide["ev_fcf"] = wide["ev"] / wide["FCF_TTM"].where(wide["FCF_TTM"] > 0)`,
guarded through the same `apply_denominator_scale_guard(..., wide["FCF_TTM"], ..., MIN_VALUATION_DENOMINATOR_SCALE_RATIO)`
loop as `ev_ebitda`/`pfcf_ratio`, keyed on `FCF_TTM`'s own scale — matching the task's
instruction exactly ("use `fcf`'s own scale-sanity check the same way `ev_ebitda` guards against
thin `EBITDA_TTM`"). Snapshot-level `ev_fcf` was **not** built — out of this task's stated scope
(`build_valuation_history()` only).

### 4.2 Hiding consistency — checked per profile, not copied mechanically

Checked real cached `FCF_TTM` sign directly rather than assuming "same sector, same hide list":

| profile | tickers | quarters | % negative FCF_TTM | tickers always-positive |
|---|---|---|---|---|
| utilities | 29 | 1,677 | **61.4%** | 2 of 29 (AEP, ED) |
| **reit** | 17 | 644 | **6.8%** | **11 of 17** |
| financial | 16 | 865 | 16.3% | 4 of 16 |
| insurance_pc | 9 | 509 | 2.0% | 6 of 9 |
| insurance_life | 1 | 67 | 0.0% | 1 of 1 |

`utilities`' FCF is genuinely, persistently negative (heavy ongoing capex) — the same reasoning
`pfcf_ratio` is already hidden for, extends cleanly to `ev_fcf` (hidden).

`financial`/`insurance_pc`/`insurance_life` already hide every EV-based multiple (`ev_ebitda`,
`ev_sales`) outright — `net_debt` isn't a meaningful capital-structure concept for these balance
sheets regardless of FCF's sign — so `ev_fcf` is hidden there too, for consistency (hidden).

**`reit` is the deliberate exception, evidence-based, not a copy-paste of `pfcf_ratio`'s hide
list**: REIT `FCF_TTM` is usually *positive* (median 0% negative quarters per ticker, 11 of 17
tickers never negative at all) — the sign-based justification that applies to utilities simply
doesn't hold here. `pfcf_ratio` being hidden for REIT most plausibly reflects the sector's FFO/
AFFO valuation convention (this project already built `p_ffo`/`ffo_margin` for exactly that, and
neither is hidden for `reit`), not a sign defect — and that convention argument doesn't
obviously carry over to a leverage-aware EV multiple. `ev_fcf` is left **visible** for `reit`.

`PROFILE_HIDDEN["financial"/"insurance_pc"/"insurance_life"/"utilities"]` gained `"ev_fcf"`;
`reit` was deliberately left unchanged. `_DERIVED_CONCEPT_CONSUMERS["FCF_TTM"]` gained
`"ev_fcf"` as a third consumer — this is not cosmetic: `financial`/`insurance_pc`/
`insurance_life`/`reit` already hide both `pfcf_ratio` and `fcf_margin`, so `FCF_TTM`'s raw row
was already fully suppressed for all four via the "hidden if every consumer is hidden" rule.
Adding `ev_fcf` as an unhidden third consumer for `reit` correctly (and intentionally) flips
`FCF_TTM` back to **visible** there — a user seeing `ev_fcf` should see the raw `FCF_TTM` behind
it — while leaving the other three exactly as suppressed as before. This is a genuine behavior
change to `facts_out`, not a no-op, so it was checked directly rather than assumed: before this
change, `filter_hidden_rows()` dropped all `FCF_TTM` rows for every `reit` ticker; after, all
**644 `FCF_TTM` rows across the 17 `reit` tickers that have the data survive the filter**, while
`is_hidden("JPM", "FCF_TTM")` (financial) stays `True`, unchanged.

### 4.3 Plotting

Added `("ev_fcf", "EV/FCF (TTM)", None, False)` to `VALUATIONS_TO_PLOT`, next to `pfcf_ratio`.

### 4.4 Verified against a real leverage-change case — NRG

`ev_fcf ÷ pfcf_ratio` is algebraically exactly `EV / market_cap` at that date — a clean,
FCF-sign-independent measure of how much leverage is adding to the story. For NRG across its
full cached history this ratio (computed directly, not eyeballed) ranges from **1.35×
(2025-06-30) to 13.65× (2015-12-31)** — a full order of magnitude of genuine variation as NRG's
net debt load changed over time (2009-2011 sits around 2.0-2.7×, the 2014-2017 window climbs to
4.6-13.6× as leverage built up, then it settles back to 1.3-2.3× in 2018 onward) — `ev_fcf` and
`pfcf_ratio` genuinely diverge and tell a different story, not a constant-factor rescaling of
the same signal.

### 4.5 Non-regression

`pfcf_ratio` and every other existing `valuation_history` value: **0 changed** (see the combined
diff in Part 1.4 — the only additions across the whole table are `buyback_distortion_flag` and
`ev_fcf`, and the only removal is the Part 1.3 `pb_ratio` hide). `ev_fcf` is a pure addition.

---

## Combined full-universe non-regression summary (498 tickers)

| table | unchanged | changed | removed | added | notes |
|---|---|---|---|---|---|
| `metrics_long` | 507,044 | 0 | 0 | +28,830 | `buyback_distortion_flag` only |
| `valuation_history` | 204,262 | 0 | -4,756 | +48,246 | removed = negative-tangible-book `pb_ratio`; added = `buyback_distortion_flag` + `ev_fcf` |
| `snapshot` | 11,865 | 491 | -112 | +7,415 | changed = `avg_pe_5y` (harmonic fix, incl. 1 real bug fix); removed = 111 `pb_ratio` + 1 `avg_pe_5y`; added = 21 new `avg_X_5y*` fields + `shares_source_is_edgar`/`shares_delta_pct` |

**Zero unexpected changes** anywhere across all three tables. Every change and removal traces to
one of this task's four intended fixes; every addition is a new concept, never a modification of
an existing one's value.

One more deliberate, verified visibility change sits outside these three tables: `facts_out`
(the raw per-concept CSV `run_full_refresh()` writes) now shows `FCF_TTM` for `reit` tickers —
644 rows across 17 tickers previously suppressed entirely, now visible because of the Part 4.2
consumer-list change described above. No raw *value* anywhere in `facts_out` was touched; only
this one profile's visibility of one already-existing raw concept changed, and only because a
new, deliberately-visible derived metric (`ev_fcf`) now legitimately depends on it.

No scratch scripts left behind: `part1_calibrate.py`, `part2_measure.py`,
`part2_meandivergence.py`, `part4_fcf_sign.py`, `build_pipeline.py`, `run_new_pipeline.py`,
`nonregression.py`, `verify_cases.py`, `verify_detail.py`, and their CSV/output artifacts were
all removed from the scratchpad after this report was written.
