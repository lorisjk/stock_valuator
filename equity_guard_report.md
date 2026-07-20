# Equity-Denominator Masking Guard

## Summary

Added a generic relative-threshold guard (`apply_denominator_scale_guard` in `metrics.py`) that
masks any ratio whose denominator is `StockholdersEquity` or `TangibleEquity` when that
denominator's magnitude falls below **1% of `Revenue_TTM`** for the same `(ticker, end)`. Applied
to `roe`, `debt_to_equity` (via `calculate_ratio`'s new optional
`min_denominator_scale_ref`/`min_denominator_scale_ratio` parameters), and the snapshot-level
`pb_ratio` / `p_tbv` in `build_snapshot`. Not applied anywhere else — no other `calculate_ratio`
call site passes the new parameters, so every other ratio (operating margin, ROA, combined ratio,
inventory turnover, etc.) is completely unaffected. `build_valuation_history`'s time-series
`pb_ratio`/`p_tbv` were **not** touched — see "Deliberately out of scope" below.

## Step 1 — Design

```python
MIN_DENOMINATOR_SCALE_RATIO = 0.01

def apply_denominator_scale_guard(ratio, denominator, scale_reference, min_denominator_scale_ratio):
    too_small = denominator.abs() < min_denominator_scale_ratio * scale_reference.abs()
    too_small = too_small & scale_reference.notna()
    return ratio.where(~too_small)
```

`calculate_ratio` gained two new optional parameters (`min_denominator_scale_ref`,
`min_denominator_scale_ratio`); when both are supplied it merges in the named scale-reference
concept and applies the guard. Every existing call site that doesn't pass them is unaffected —
same "optional, additive" shape as `min_base_ratio` on `calculate_growth`.

`Revenue_TTM` was used as the scale reference, per the task's own reasoning: it's fetched for
every profile (`standard`, `financial`, `insurance_pc`, `insurance_life`, `retail`), unlike
`Assets` (financial-only).

**One design correction made during testing, not before**: the first version treated a *missing*
scale reference as "can't verify → mask." This was wrong and caught in the non-regression pass —
see Step 3.

## Step 2 — Empirically tuning the threshold

### Confirmed the ORLY explosion, and matched the task's own cited numbers almost exactly

Computed `StockholdersEquity`, `Revenue_TTM`, `roe`, and `debt_to_equity` directly from cached
data for ORLY's full history. The worst point:

```
2021-03-31   equity = -$6.977M   revenue_ttm = $12.22B   equity/revenue = -0.00057
             roe = -279.99 (-27,999%)   debt_to_equity = -591.11
```

This matches the task's cited "-25,000% / -600" almost exactly — confirms this is the specific
event in question, not a different quarter.

### AZO checked directly — and turns out **not** to be the same pattern

AZO's `StockholdersEquity` has been **continuously negative since at least 2009** — not a brief
near-zero crossing like ORLY's, but a large, stable, deeply negative balance from AZO's much
longer-running aggressive buyback history (a well-known, deliberate AutoZone capital-structure
choice). AZO's smallest-ever `|equity|/revenue_ttm` across its whole cached history is **0.0635**
(6.35%) — more than 6x above the chosen 1% threshold. AZO's resulting ROE/D-E values, while
unusual (negative, since equity is negative), stay in a bounded range (roughly -0.5 to -2 for ROE,
-1.7 to -6.6 for D/E) — large and negative, but not the numerically-exploding, unbounded values
ORLY showed while its equity was oscillating through zero. **The task asked to confirm whether AZO
shows the same pattern — it does not, and the guard correctly leaves it untouched, confirmed
empirically rather than assumed from the "similar buyback profile" framing.**

### The threshold-selection problem turned out to be broader than ORLY/AZO alone

Extending the same computation to every cached ticker (145, across all 5 profiles) surfaced that
near-zero/negative `StockholdersEquity` relative to revenue is a **common pattern across
`standard`-profile tech/industrial names with long buyback histories** — CDW, HD, HPQ, DELL, MSI,
MCHP, CIEN, STX, VRSN, GDDY, IT, GEN, AMD, FTNT all show multiple quarters with `|equity|/revenue`
under 1.5%, most with correspondingly extreme ROE/D-E values. This confirms the task's own framing
("this is not retail-specific") — it is a real, general pipeline gap, not something to special-case
for ORLY.

This also ruled out a naive "IBM-style clean gap" approach: the smallest-values distribution here
is *continuous*, not bimodal — there is no threshold that perfectly separates "genuinely
degenerate" from "structurally thin but stable" equity bases the way `min_base_ratio`'s IBM growth-
rate case could. **0.01 (1%) was chosen deliberately conservative**: it reliably catches the
clearly-extreme cases (every masked value has `|roe|` or `|debt_to_equity|` in the high single
digits to several hundred — see the full list in Step 3) while staying comfortably below AZO's
smallest legitimate value (6.35x margin) and the smallest already-validated financial/insurance
equity/revenue ratio found anywhere in the cached universe, **ALL, at 26.1% (Allstate,
2023-09-30)** — a >26x margin. Some of ORLY's own milder elevated quarters (e.g. 2021-09-30,
roe=-14.5, ratio=1.09%, just over the 1% line) are deliberately left unmasked rather than chasing
a more aggressive threshold that would start sweeping in the broad "thin-but-stable" tech
population — same "pragmatic, not perfect" philosophy as `MAX_MULTIPLE` and `min_base_ratio`.

## Step 3 — Mandatory non-regression check (all profiles, all cached tickers)

Computed `roe` and `debt_to_equity` under the old (unguarded) and new (guarded) logic for every
one of the 145 cached tickers across all 5 profiles, and separately verified the `pb_ratio`/`p_tbv`
masking condition (denominator-only, since these don't require live price data to test the guard
logic itself).

### First pass caught a real bug in the guard's own design

The first implementation treated a missing scale reference (`Revenue_TTM` not available for that
`(ticker, end)`) as "can't verify the denominator is safe → mask." This **masked 144 previously
clean values**, including **Goldman Sachs' entire 2009–2012 ROE series** (13%–21%, completely
sane) and **Caterpillar's 2011-03-31 ROE (33%, sane)** — not because their equity was ever small,
but because `Revenue_TTM` itself has real, unrelated coverage gaps for those tickers/dates (the
same class of bank-Revenue-tag gap documented in earlier sessions). Caught by the "zero tolerance,
diff against the old logic" check before being kept — exactly the discipline this whole session
has run on. **Fixed**: a missing scale reference now means "can't judge, don't mask" (pass the
original value through unchanged) rather than "mask." Re-ran the full diff after the fix.

### Final result: 0 unexplained changes, 37 intentional maskings, 0 accidental ones

```
ROE:             0 unexplained value changes | 37 newly masked | 0 newly appeared
Debt-to-Equity:  0 unexplained value changes | 37 newly masked | 0 newly appeared
```

(Same 37 `(ticker, end)` pairs for both — both ratios share the same `StockholdersEquity`
denominator and `Revenue_TTM` scale reference, so the mask condition is identical.)

**Every single masked value is genuinely extreme** — smallest-magnitude masked ROE is AMD
2015-03-28 at -33.1 (-3,312%); smallest-magnitude masked D/E is STX 2022-07-01 at 8.84. No masked
value was anywhere close to a plausible economic ratio.

Full list of masked `(ticker, end)` pairs (all `standard` profile, plus ORLY from `retail` — zero
`financial`/`insurance_pc`/`insurance_life` tickers affected):

```
AMD 2015-03-28   CDW 2011-06-30   CDW 2011-09-30   CDW 2011-12-31   CDW 2012-03-31
CDW 2012-06-30   CDW 2012-09-30   CIEN 2011-10-31  DELL 2020-07-31  FTNT 2023-03-31
GDDY 2020-12-31  GDDY 2021-06-30  GEN 2020-04-03   HD 2019-11-03    HD 2020-08-02
HD 2021-10-31    HD 2022-07-31    HD 2022-10-30    HD 2023-01-29    HD 2023-04-30
HD 2023-07-30    HD 2023-10-29    HD 2024-01-28    HPQ 2025-10-31   HPQ 2026-04-30
IT 2016-09-30    IT 2026-03-31    LOW 2021-04-30   LOW 2021-07-30   MCHP 2015-03-31
MCHP 2016-03-31  MSI 2021-12-31   ORLY 2021-03-31  ORLY 2021-12-31  STX 2022-07-01
STX 2025-10-03   VRSN 2011-06-30
```

`pb_ratio` masking (equity-denominator, numerator-independent check): the exact same 37 pairs.
`p_tbv` masking (tangible-equity denominator): 81 pairs — a larger, mostly *different* set,
dominated by serial acquirers whose `TangibleEquity = StockholdersEquity − Goodwill` goes
near-zero even when `StockholdersEquity` itself is healthy (IBM, UNH, ROP, TDY, TYL, MA, GE, WDC,
APH — all well-known heavy-goodwill acquirers). Full list omitted here for length; available by
re-running `apply_denominator_scale_guard` against `TangibleEquity`/`Revenue_TTM`.

**`GL` and every other `financial`/`insurance_pc`/`insurance_life` ticker: zero maskings, in any
of the four checks.** Confirmed empirically, not assumed — the smallest equity/revenue ratio
anywhere in that reference set (ALL, 26.1%) sits more than 26x above the threshold.

## Step 4 — Trade-off documented

Added to `MDs/bugfixes_opdate_history.md` (see the diff below) — third deliberate design
compromise in that log, same category as `min_base_ratio` and `MAX_MULTIPLE`.

## Deliberately out of scope

- **`build_valuation_history`'s time-series `pb_ratio`/`p_tbv`** (as opposed to
  `build_snapshot`'s single-latest-value versions) were **not** touched. The task named
  "snapshot-level `pb_ratio` and `p_tbv`" specifically. These are the same failure mode and would
  show the identical explosion in the historical chart data, but fixing them wasn't asked for here
  — flagged as a known, parallel gap rather than silently fixed or silently ignored.
- **`p_ppnr` and `p_core_earnings`** (bank/insurance-specific valuation multiples) were not
  extended with this guard — the task scoped the fix to `StockholdersEquity`/`TangibleEquity`
  denominators specifically; these use `PPNR`/`CoreOperatingEarnings`, a different failure mode
  not investigated here.

## Net code changes

- `metrics.py`: added `MIN_DENOMINATOR_SCALE_RATIO = 0.01`, added
  `apply_denominator_scale_guard()`, extended `calculate_ratio()` with two new optional
  parameters (default `None`, i.e. off).
- `main.py`: imported the new helper/constant; `roe` and `debt_to_equity` in
  `calculate_all_metrics()` now pass `min_denominator_scale_ref="Revenue_TTM",
  min_denominator_scale_ratio=MIN_DENOMINATOR_SCALE_RATIO`; `build_snapshot()`'s `pb_ratio` and
  `p_tbv` now route through `apply_denominator_scale_guard()` instead of plain division.

No scratch scripts were left behind.
