# Backlog Cleanup Report

Three independent, previously-logged items, each with its own root cause and treated separately.

---

## PART A — `net_debt_to_ebitda`: the remaining 33 unguarded explosions

### Step 1 — Characterization

Re-derived the explosion set by computing `net_debt_to_ebitda` (`net_debt = LongTermDebt −
CashAndEquivalents`, `ebitda = OperatingIncomeLoss_TTM + DepreciationAndAmortization_TTM`) across the
full cached universe. Using |ratio| > 60 reproduces the prior Tier-1 task's set almost exactly: **52
cases total** (the task's "53"; the drift is newer quarters added since), of which **19 are already
masked** by the absolute floor (`min_denominator_abs = $10M`, near-zero EBITDA) and **33 remain
unguarded** — matching the task's stated 33 precisely.

The 33 are genuinely a *small-EBITDA-relative-to-scale* problem, not near-zero:

| Measure | Value across the 33 |
|---|---|
| median \|EBITDA\| | **$111M** (well above the $10M floor — that's why the floor misses them) |
| \|EBITDA\| range | $10M – $726M |
| EBITDA / Revenue_TTM | 0.0011 – 0.0376 (EBITDA < 3.8% of revenue in every case) |
| EBITDA / net_debt | 0.0017 – 0.0164 (very tightly clustered) |

These are EBITDA-*collapse* quarters, not permanently-thin-margin businesses: WDC (memory-industry
downturn), BA (737-MAX crisis quarters), INTC (2024-25 trough), the COVID cruise/casino names
(NCLH/CCL/RCL/LVS/WYNN/HLT/MAR), WBD (merger-year D&A), VTRS, EL, VLO's 2021 recovery quarters.

### Step 2 — Guard design and calibration

Evaluated both scale references the task named:

- **Revenue_TTM — rejected.** Real capital-intensive, thin-margin, high-revenue businesses have the
  same low EBITDA/revenue as the explosions but perfectly sane leverage: VLO refining (0.8% EBITDA/rev,
  ratio 3.8x), HAL (0.8%, 1.8x), HPQ (1.1%, −3.6x). Any Revenue-relative threshold that catches all 33
  also masks ~260 legitimate readings — the exact over-masking Step 3 warns against.
- **net_debt — selected, implemented honestly.** Because net_debt is the ratio's own *numerator*,
  "mask when |EBITDA| < k·|net_debt|" is algebraically "mask when |ratio| > 1/k" — a magnitude cap.
  Rather than add a redundant parameter disguising that, implemented it via the existing
  `max_abs_result` on the `net_debt_to_ebitda` call. This is the only choice that **cannot over-mask a
  genuinely low-leverage thin-margin business**, whose ratio is small and therefore never touched.

Calibration (marginal-return / clean-gap method on this specific data): the 52 explosions all sit at
|ratio| ≥ **61.06** (EBITDA/net_debt ≤ 0.0164); the next-highest reading anywhere is **56.16**. There
is a clean gap with nothing between 56.16 and 61.06. Set `MAX_NET_DEBT_TO_EBITDA_ABS = 60`, which lands
in that gap.

```python
# metrics.py
MAX_NET_DEBT_TO_EBITDA_ABS = 60

# main.py
m["net_debt_to_ebitda"] = calculate_ratio_from_dfs(
    m["net_debt"], m["ebitda"], "net_debt", "ebitda", "net_debt_to_ebitda",
    min_denominator_abs=MIN_NET_DEBT_TO_EBITDA_ABS,   # existing near-zero floor, kept
    max_abs_result=MAX_NET_DEBT_TO_EBITDA_ABS,        # new scale-relative (= magnitude) cap
)
```

The near-zero absolute floor is retained alongside the cap: the two guard different pathologies
(denominator ≈ 0 vs. ratio implausibly large).

### Step 3 — No over-masking

Spot-checked legitimate thin-margin / high-leverage businesses after the guard — all survive with real
values:

| Ticker | net_debt_to_ebitda (kept) | Type |
|---|---|---|
| VLO | 3.79 / 13.10 / 5.93 | refiner, thin margin, high revenue |
| HAL | 1.78 | oilfield services |
| HPQ | −3.57 | thin-margin hardware |
| D (Dominion) | 8.35 | levered utility |
| KMI | 8.31 | levered midstream |
| WMB | 5.43 | levered midstream |

Highest surviving reading is CRWD −56.16, then a continuous band down through the 40s — the grey zone
(|ratio| 20-56) is fully intact. That grey zone is, on inspection, the *same* thin-EBITDA artifact at
lower magnitude (more COVID cruise/casino/BA quarters); it is deliberately left untouched here to honor
"only the confirmed-explosion cases newly mask," and is flagged as a candidate for a future,
separately-scoped tightening.

### Step 4 — Non-regression (base metric, full universe)

**33 newly masked, 0 values changed, 0 newly unmasked.** The 33 span 19 tickers: BA, CRWD, EL, HLT,
INTC, LITE, LVS, MAR, MAS, NCLH, NRG, PANW, STX, VLO, VST, VTRS, WBD, WDC, WYNN.

---

## PART B — GLW Capex 2011-03-31 = $100,000,000,000

### Step 1 — Investigation

Corning reports Capex via `PaymentsToAcquireProductiveAssets`. The tag holds a single fact for
2011-Q1:

```
2011-01-01 -> 2011-03-31   val = 100,000,000,000   fp=Q1 form=10-Q filed=2011-04-29
```

$100B is **~200× GLW's entire annual capex** (~$1-2B, per the tag's own 2019-2020 facts) and larger
than GLW's total 2011 revenue (~$7.9B) — implausible under any scenario. It is already a standalone
Q1 span, so it flows straight into the quarterly series with no decumulation. There is **only one
fact** for 2011-03-31; **no later filing corrects it**. The cached SEC JSON carries no `decimals`
attribute, so a scale-error signature cannot be confirmed from metadata — but the exactly-round value
strongly suggests a data-entry error.

### Step 2 — Fix: mask, do not guess

This is a different evidentiary situation from every prior `_KNOWN_BAD_FACTS` entry, all of which had
a competing correct value to fall back to. Here the true scale cannot be inferred with confidence:
÷1000 → $100M, ÷100 → $1B, and GLW's real Q1-2011 capex was ~$450M — none matching cleanly, with no
in-window neighbor (the next fact is 2019) to reconcile against. Per the task's "prefer masking over
guessing" rule, added the fact to `_KNOWN_BAD_FACTS`; because it is the only fact for the period, the
drop leaves **no replacement** — the point simply disappears.

```python
("GLW", "PaymentsToAcquireProductiveAssets"): [
    {"end": "2011-03-31", "filed": "2011-04-29", "val": 100000000000},
],
```

### Step 3 — Non-regression

GLW Capex before: {2011-03-31: $100B, 2019-09-30: $508M, 2020-09-30: $153M}. After: the 2011-03-31
point is gone; the 2019/2020 points are unchanged. Annual GLW Capex was already empty (the fact is a
Q1 span, never picked up by annual extraction). No other GLW concept or ticker affected (confirmed in
the combined check below).

---

## PART C — FIX (Comfort Systems USA): a period-tagging error

### Step 1 — Investigation

The flagged "~80% jump within a two-month filing window" is FIX's FY2025 revenue:

```
Revenues  2025-01-01 -> 2025-12-31 :
    9,101,641,000   filed 2026-02-19 (10-K)
    1,831,286,000   filed 2026-04-23 (10-Q)      <- 2.1 months later, ~80% lower
```

This is **not a corporate event** — it is a period-tagging error in the Q1-2026 10-Q. That filing
tagged its prior-year Q1-2025 comparatives with `end=2025-12-31` instead of `end=2025-03-31`. Evidence:

1. The mislabeled value ($1,831,286,000) is **exactly** FIX's real Q1-2025 revenue (the 2025-03-31
   quarterly value already in the series).
2. The **identical error hit every income-statement line filed that day** — Revenues, GrossProfit,
   OperatingIncomeLoss, CostOfRevenue, SG&A, Depreciation, NonoperatingIncomeExpense — each collapsing
   to ~20% (the Q1 fraction) of its 10-K value. A real restatement does not uniformly shrink every line
   to exactly one quarter; a Q1-stamped-as-FY tagging error does.
3. FIX is a roll-up acquirer with no divestiture that would cut revenue ~80%, and a divestiture would
   not retroactively rewrite the just-filed 10-K's full-year figure two months later to a
   quarterly-sized number.

Because "later filed wins," the mislabeled FY figures beat the correct 10-K values in the pipeline:

| Concept | Corrupted (before) | Correct (10-K) |
|---|---|---|
| FY2025 Revenue | $1.83B (−74% vs 2024, absurd for a ~30%/yr grower) | $9.10B |
| FY2025 OperatingIncomeLoss | $209M | $1.31B |
| Q4-2025 Revenue | negative → masked (missing point) | — |
| Q4-2025 OperatingIncomeLoss | **visible wrong −$679M** | — |

### Step 2 — Classification and fix

This matches the task's second branch — "the same restatement signature as this project's known bug
classes (two differently-scoped filed values for the same period)" — so applied `_KNOWN_BAD_FACTS`,
dropping the two mislabeled facts that feed pipeline concepts:

```python
("FIX", "Revenues"): [
    {"end": "2025-12-31", "filed": "2026-04-23", "val": 1831286000},
],
("FIX", "OperatingIncomeLoss"): [
    {"end": "2025-12-31", "filed": "2026-04-23", "val": 209098000},
],
```

After the fix, the correct 10-K values win: FY2025 Revenue $9.10B, FY2025 OpInc $1.31B, Q4-2025 Revenue
$2.646B (exact decumulation), Q4-2025 OpInc $426.7M — all clean and consistent with FIX's growth trend.

**Noted, out of scope (different root cause):** FIX's quarterly D&A carries a *separate, pre-existing*
tag-definition inconsistency — its quarterly YTD `DepreciationAndAmortization` facts (~$34M/qtr) sum to
more than its annual D&A ($62.4M), so Q4-2025 D&A decumulates negative and is masked. The winning D&A
tag has no mislabeled 2026-04-23 fact, so this is independent of the tagging error above; it is not the
flagged item and is left untouched.

### Step 3 — Non-regression

The two `_KNOWN_BAD_FACTS` entries are keyed to FIX only and match on exact end+filed+val — they touch
only these facts (confirmed in the combined check below).

---

## Combined non-regression (all three parts)

One full-universe before/after across all **381 cached tickers**, both periods (quarterly + annual),
370,852 rows each side.

**Raw-fact level (build_dataframe) — only GLW and FIX touched:**

```
removed=1   added=1   changed=3     affected tickers: [FIX, GLW]

removed:  GLW Capex           2011-03-31 quarterly  $100B                    (Part B)
added:    FIX Revenue         2025-12-31 quarterly  $2.646B (recovered Q4)   (Part C)
changed:  FIX OperatingIncomeLoss 2025-12-31 annual     $209M  -> $1.31B     (Part C)
          FIX OperatingIncomeLoss 2025-12-31 quarterly  -$679M -> $426.7M    (Part C)
          FIX Revenue         2025-12-31 annual     $1.83B -> $9.10B         (Part C)
```

**Metric level (`net_debt_to_ebitda`) — Part A:** 33 newly masked (19 tickers), 0 other values changed.

No cross-contamination: Part A is a metrics-level guard that touches only `net_debt_to_ebitda`; Parts B
and C touch only GLW and FIX raw facts (and those tickers' own downstream metrics, which are intended
corrections). Nothing outside the specific tickers/concepts/dates each part confirms was affected.

No scratch scripts left behind.
