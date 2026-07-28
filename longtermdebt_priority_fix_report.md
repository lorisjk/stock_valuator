# Base `LongTermDebt` Priority Fix + Negative-Value Guard

Follow-up to `p_ffo_fix_and_longtermdebt_exposure_report.md`, which scoped the current-portion
contamination to 103 tickers across 14 profiles. This task implements the fix.

**Headline:** the literal instruction in the task brief ("move the three vulnerable sources to the
end of the priority list") was verified against real data first — and it turned out to cause
regressions on ~30 tickers. The three sources are **not** equivalent, and demoting them as a block
understates debt wherever the sum was already working correctly. A more precise, two-part fix was
implemented instead. The deviation is documented in full below, per the brief's own instruction to
state explicitly if the ordering differs from "move to the end."

---

## Step 1 — Reordering (deviation from the literal brief, with evidence)

### Verification of the current structure first

Confirmed against the live `config.py` before changing anything: the priority list was still
exactly as the scan report documented — `ConvertibleDebtCurrent` at 5, `ConvertibleNotesPayableCurrent`
at 6, `sum(LongTermDebtNoncurrent, LongTermDebtCurrent, NotesPayableCurrent)` at 7, and the
combined-debt tags at 8/9/10. Nothing had shifted since the scan.

### Why "move all three to the end" was rejected

The literal reordering was implemented and measured first. It changed 782 values across 73
tickers — but **35 of those tickers had values that went DOWN**, which a fix that only ever
promotes complete-debt tags should not do. Investigating the root cause:

| Ticker | Date | `LongTermDebtNoncurrent` | Sum (old winner) | `LongTermDebtAndCapitalLeaseObligations` (new winner) |
|---|---|---|---|---|
| CARR | 2024-06-30 | 11,270,000,000 | **13,322,000,000** | 11,270,000,000 |
| ALB | 2015-06-30 | 3,562,308,000 | **3,990,308,000** | 3,562,308,000 |
| AVGO | 2022-05-01 | 40,958,000,000 | **41,227,000,000** | 39,164,000,000 |
| XOM | 2013-12-31 | 6,500,000,000 | **7,534,000,000** | 6,891,000,000 |
| GOOG | 2020-09-30 | *(absent)* | 999,000,000 ← broken | **13,902,000,000** |

The pattern is decisive: **the sum is only broken when `LongTermDebtNoncurrent` is absent.** When
that principal component *is* present, the sum equals noncurrent + current maturities = total debt,
which is *more* complete than `LongTermDebtAndCapitalLeaseObligations` (noncurrent-only). Demoting
the sum below it therefore **understates** debt for every ticker where the sum was working — a
regression, not a fix.

The two `Convertible*Current` tags are different: they are current-portion-only *by definition*,
never total debt, in every period. Demoting those is unambiguously correct (this is what hit BKNG).

### What was actually implemented

Two targeted changes rather than one blanket move:

1. **`ConvertibleDebtCurrent` and `ConvertibleNotesPayableCurrent` moved to the literal end** of the
   list, after all three combined-debt tags — exactly as the brief specified for these two.
2. **The sum source kept its original priority position**, but gained a new `"require"` key naming
   its principal component. The sum now only contributes for periods where `LongTermDebtNoncurrent`
   actually has data; where it doesn't, the period falls through to the combined-debt tags instead
   of being claimed by a degraded sum.

Resulting order: `LongTermDebt` → `DebtLongtermAndShorttermCombinedAmount` → `LongTermNotesAndLoans`
→ `ConvertibleLongTermNotesPayable` → `ConvertibleDebtNoncurrent` → **sum (with `require`)** →
`LongTermDebtAndCapitalLeaseObligations` → `...IncludingCurrentMaturities` → `UnsecuredLongTermDebt`
→ **`ConvertibleDebtCurrent`** → **`ConvertibleNotesPayableCurrent`**.

This eliminated the regression entirely: **non-zero decreases went from ~30 tickers to zero.**

### Supporting mechanism: `require` on sum sources

`extract_summed_values` adds up whatever component tags exist for a period, so a sum silently
degrades into its minor components when the principal one has a gap. `extract_priority_merge` now
honours an optional `"require"` key on a `sum` source, restricting it to periods where the named
tag is present. This is opt-in and affects no other concept.

**Bonus defect found via this change:** the old sum also **double-counted** where a filer tagged the
same amount under two different component tags. OMC at 2015-06-30 carried `LongTermDebtCurrent` =
1,005,100,000 *and* `NotesPayableCurrent` = 1,005,100,000 — the same figure — which the sum added to
2,010,200,000, roughly 2.8x OMC's actual debt level. Not previously catalogued.

---

## Step 2 — Negative-value guard

### Where the negatives actually come from (confirmed before placing the guard)

Traced to raw facts. The negatives are **filer sign errors in the source XBRL**, not a subtraction
introduced anywhere in the pipeline:

| Ticker | Date | Offending tag (priority) | Raw value | Correct same-date value |
|---|---|---|---|---|
| DD | 2018-12-31 | `LongTermDebt` (0) | −12,635,000,000 | `LongTermDebtAndCapitalLeaseObligations` = +12,624,000,000 |
| NSC | 2010-06-30 | `LongTermDebt` (0) | −6,689,000,000 | `LongTermDebtAndCapitalLeaseObligations` = +6,326,000,000 |
| FE | 2010-12-31 | `LongTermDebtCurrent` (in sum) | −1,486,000,000 | `LongTermDebtAndCapitalLeaseObligations` = +12,579,000,000 |
| GNRC | 2013-09-30 | `LongTermDebtCurrent` (in sum) | −12,000,000 | `LongTermDebtAndCapitalLeaseObligations` = +1,177,671,000 |
| ETR | 2009-06-30 | `LongTermDebtNoncurrent` **and** `LongTermDebtCurrent` | −10,184,849,000 / −805,684,000 | *(none — every source negative)* |

Note DD and NSC are negative at **priority 0**, so the reordering alone could never reach them.

### Guard placement

Because the cause is a *per-source* sign error and a correctly-signed source usually exists at the
same date, the guard skips negative readings **per source during the priority merge** (opt-in via a
`"non_negative": True` flag on the concept) rather than masking only the final resolved value. This
matters materially: it recovers 8 of the 9 negative readings from a real, same-date tag instead of
discarding them. Where *no* source has a valid value (ETR), the period ends up absent — the intended
masked outcome, with nothing invented.

A post-resolution `_mask_negative_balance_values` safety net was also added in `build_dataframe`,
kept deliberately separate from the existing `_mask_negative_flow_values` (flow concepts are
decumulated and guard only in quarterly mode; a balance-sheet level is invalid negative in either
mode). Its concept set is intentionally narrow — `StockholdersEquity` in particular must never be
added, since it is legitimately negative for real companies (DASH/ABNB pre-IPO, SBAC).

### Outcome for the three flagged cases (Step 5.4)

| Ticker | Outcome | Why |
|---|---|---|
| **FE** | **Corrected** → 12,579,000,000 | Reordering: `LongTermDebtAndCapitalLeaseObligations` present at the same date |
| **GNRC** | **Corrected** → 1,177,671,000 | Same |
| **ETR** | **Masked** | Both sum components negative and no combined-debt tag at that date — nothing valid to promote |

Plus two cases the original scan never flagged (negative at priority 0, outside the scanned
positions): **DD** (7 dates) and **NSC** (1 date), both **corrected** by the per-source skip.

**Verified: 0 negative `LongTermDebt` values remain across all 436 cached tickers.**

---

## Step 3 — Tier 1 "smoking gun" verification

| Ticker | Date | Before | After | Shadow value in scan report | Match |
|---|---|---|---|---|---|
| VZ | 2014-12-31 | 319,000,000 | 110,029,000,000 | 112,426,000,000 | see note |
| XOM | 2009-12-31 | 348,000,000 | 7,129,000,000 | 7,129,000,000 | exact |
| PEP | 2020-06-13 | 750,000,000 | 38,371,000,000 | 38,371,000,000 | exact |
| AVGO | 2022-10-30 | 403,000,000 | 39,075,000,000 | 39,075,000,000 | exact |
| GOOG | 2020-09-30 | 999,000,000 | 13,902,000,000 | 15,196,000,000 | see note |
| DGX | 2008-12-31 | 5,142,000 | 3,078,089,000 | 3,078,089,000 | exact |
| NUE | 2019-12-31 | 20,000,000 | 4,291,301,000 | 4,291,301,000 | exact |
| CVX | 2022-12-31 | 2,694,000,000 | 21,375,000,000 | 21,375,000,000 | exact |
| AMCR | 2019-09-30 | 5,000,000 | 5,454,800,000 | 5,454,800,000 | exact |

**7 of 9 match the documented shadow value exactly.** The two that differ are correct, not failures
— both are cases where *two* combined-debt tags exist at that date:

- VZ 2014-12-31: `LongTermDebtAndCapitalLeaseObligations` = 110,029,000,000 (priority 6, wins) vs.
  `...IncludingCurrentMaturities` = 112,426,000,000 (priority 7). Difference = 2,397,000,000 = the
  current maturities.
- GOOG 2020-09-30: 13,902,000,000 vs. 15,196,000,000, same relationship.

The scan report's "shadow" column recorded the **largest** available lower-priority value as proof
that a bigger correct value existed — not the value priority order would select. Both resolve to a
correct-scale figure, up from ~0.3% and ~6.6% of true debt respectively.

---

## Step 4 — Tier 3 "ambiguous" cases

Checked all 63 Tier 3 tickers. **44 unchanged as predicted** (no shadow tag to promote). **19 changed**
— investigated rather than assumed, and all 19 are correct outcomes in one of two categories:

**(a) Genuinely had a shadow tag the neighbour-only heuristic missed — the "good outcome" the brief
anticipated (4 tickers):**

| Ticker | Example | Before | After |
|---|---|---|---|
| CCL | 2008-08-31 | 232,000,000 | 9,233,000,000 |
| GEN | 2012-06-29 | 955,000,000 | 2,093,000,000 |
| ANET | 2013-12-31 | 74,050,000 | 98,793,000 |
| EQT | 2019-06-30 | 4,830,000 | 999,125,000 |

**(b) Contaminated current-portion-only values with no complete-debt alternative → correctly masked
(15 tickers):** ADSK, BIIB, CAG, ED, FANG, FFIV, FICO, HRL, INTU, META, NDSN, OMC, PAYX, PCG, SLB.

Masked values were audited against each ticker's own normal debt level: **110 of 124 sat at or below
50% of the ticker's median** (median ratio **2.9%** — i.e. ~3% of true debt), squarely the
contamination signature. The 14 that looked larger were checked individually and all confirmed
contaminated: 12 are OMC's double-counted sum (same figure added twice, above), and HRL 2011-01-30 /
INTU 2011-04-30 are isolated quarters where only `LongTermDebtCurrent` existed. SLB's 17 masked
dates likewise carry only `LongTermDebtCurrent` (e.g. 2,214,000,000 against SLB's real $12–20B
long-term debt in that era — ~15%, the current portion).

### Values changing to zero (5 total, all justified)

- **CDNS 2013-12-28** (324,826,000 → 0): not a regression. `UnsecuredLongTermDebt` *is* Cadence's real
  long-term debt tag (it reads 348,733,000 at later dates); at this date their convertible notes were
  classified as current, so long-term debt genuinely was 0. The same fix converts four *other* CDNS
  dates from a spurious 0 up to ~348M/644M — net strongly positive for this ticker.
- **EQT** (2020-06-30, 2020-09-30) and **PWR** (2010-12-31, 2011-12-31): prior values were 0.004%–1.1%
  of the ticker's median debt — garbage either way, negligible impact.

---

## Step 5 — Non-regression (maximum scope)

Full before/after extraction of `LongTermDebt` and every derived metric (`debt_to_equity`,
`net_debt`, `net_debt_to_ebitda`) across **all 436 cached tickers, every profile**.

| Metric | Values changed | Appeared | Disappeared |
|---|---|---|---|
| `LongTermDebt` | 429 | 0 | 124 |
| `debt_to_equity` | 424 | 0 | 120 |
| `net_debt` | 418 | 0 | 124 |
| `net_debt_to_ebitda` | 354 | 0 | 89 |

**Containment checks:**

1. **58 of 436 tickers affected; 378 completely untouched.** Verified directly, not assumed.
2. **Derived metrics changed for zero tickers beyond those whose `LongTermDebt` changed** — confirmed
   explicitly for all three derived metrics (no unexplained propagation).
3. **The 103-ticker flagged list was regenerated from scratch** using the original ordering and
   reproduced exactly (103), validating the earlier scan. Of those, **54 changed** and **49 were
   unchanged** — the latter being precisely the predicted "nothing to promote" case.
4. **4 tickers changed that were outside the flagged 103** — each investigated:

| Ticker | Change | Why the original scan missed it |
|---|---|---|
| BALL | 2026-03-31: 647,000,000 → 7,021,000,000 | Its neighbouring quarter was *also* contaminated (2,000,000), so the <50%-of-neighbours test could not fire — a real limitation of a neighbour-based heuristic when consecutive values are both bad |
| NSC | 2010-06-30: −6,689,000,000 → 6,326,000,000 | Negative at priority 0; the scan only examined priorities 5/6/7 |
| INTU | 2011-04-30: 500,000,000 → masked | Neighbours were similar scale, so the ratio test did not fire |
| RMD | 2010-09-30, 2010-12-31 → masked | Same |

All four are correct outcomes; the scan simply **undercounted**, it did not mis-fire.

### Impact summary

- **424 values corrected upward** (promoted from a current-portion figure to a complete-debt figure),
  across **41 tickers**.
- **124 values masked** — contaminated readings with no valid alternative at that date.
- **0 non-zero decreases**, **0 values invented**, **0 negatives remaining**.

### Affected tickers by profile

| Profile | Tickers |
|---|---|
| `standard` | 14 |
| `industrials` | 9 |
| `utilities` | 7 |
| `pharma_medtech` | 5 |
| `materials_integrated` | 4 |
| `consumer_staples` | 4 |
| `energy_integrated` | 4 |
| `energy` | 3 |
| `leisure` | 2 |
| `health_services` | 2 |
| `materials` | 1 |
| `railroads` | 1 |
| `media` | 1 |
| `telecom_cable` | 1 |

### Full per-ticker table (all 58 affected)

| Ticker | Profile | Dates changed | Corrected up | Masked | Example (date: before → after) |
|---|---|---|---|---|---|
| ADSK | `standard` | 5 | 0 | 5 | 2017-04-30: 399,100,000 → masked |
| AMCR | `materials` | 27 | 27 | 0 | 2019-09-30: 5,000,000 → 5,454,800,000 |
| ANET | `standard` | 1 | 1 | 0 | 2013-12-31: 74,050,000 → 98,793,000 |
| AVGO | `standard` | 8 | 8 | 0 | 2022-10-30: 403,000,000 → 39,075,000,000 |
| AVY | `materials_integrated` | 2 | 2 | 0 | 2016-10-01: 250,000,000 → 713,000,000 |
| BALL | `materials_integrated` | 1 | 1 | 0 | 2026-03-31: 647,000,000 → 7,021,000,000 |
| BIIB | `pharma_medtech` | 14 | 0 | 14 | 2008-12-31: 27,667,000 → masked |
| CAG | `consumer_staples` | 7 | 0 | 7 | 2008-08-24: 25,200,000 → masked |
| CCL | `leisure` | 5 | 5 | 0 | 2008-08-31: 232,000,000 → 9,233,000,000 |
| CDNS | `standard` | 9 | 8 | 0 | 2015-01-03: 342,499,000 → 348,676,000 |
| CMI | `industrials` | 42 | 42 | 0 | 2015-12-31: 39,000,000 → 1,576,000,000 |
| CRL | `pharma_medtech` | 29 | 29 | 0 | 2019-03-30: 28,225,000 → 1,540,833,000 |
| CVX | `energy_integrated` | 4 | 4 | 0 | 2022-12-31: 2,694,000,000 → 21,375,000,000 |
| DD | `materials_integrated` | 10 | 10 | 0 | 2018-12-31: −12,635,000,000 → 12,624,000,000 |
| DGX | `health_services` | 23 | 23 | 0 | 2008-12-31: 5,142,000 → 3,078,089,000 |
| DVA | `health_services` | 2 | 2 | 0 | 2014-06-30: 117,080,000 → 8,390,578,000 |
| ED | `utilities` | 4 | 0 | 4 | 2025-03-31: 350,000,000 → masked |
| EQT | `energy` | 10 | 3 | 5 | 2019-06-30: 4,830,000 → 999,125,000 |
| ETR | `utilities` | 1 | 0 | 1 | 2009-06-30: −10,990,533,000 → masked |
| FANG | `energy` | 4 | 0 | 4 | 2011-12-31: 0 → masked |
| FE | `utilities` | 16 | 16 | 0 | 2010-12-31: −1,486,000,000 → 12,579,000,000 |
| FFIV | `standard` | 4 | 0 | 4 | 2022-12-31: 0 → masked |
| FICO | `standard` | 6 | 0 | 6 | 2009-09-30: 0 → masked |
| GEN | `standard` | 3 | 3 | 0 | 2012-06-29: 955,000,000 → 2,093,000,000 |
| GLW | `standard` | 10 | 10 | 0 | 2008-12-31: 78,000,000 → 1,527,000,000 |
| GNRC | `industrials` | 16 | 16 | 0 | 2013-09-30: −12,000,000 → 1,177,671,000 |
| GOOG | `standard` | 10 | 10 | 0 | 2020-09-30: 999,000,000 → 13,902,000,000 |
| GOOGL | `standard` | 10 | 10 | 0 | 2020-09-30: 999,000,000 → 13,902,000,000 |
| HAL | `energy` | 10 | 4 | 6 | 2021-03-31: 515,000,000 → 9,127,000,000 |
| HLT | `leisure` | 4 | 4 | 0 | 2016-12-31: 33,000,000 → 6,583,000,000 |
| HPE | `standard` | 11 | 11 | 0 | 2017-10-31: 3,005,000,000 → 10,182,000,000 |
| HPQ | `standard` | 6 | 6 | 0 | 2012-01-31: 4,341,000,000 → 25,462,000,000 |
| HRL | `consumer_staples` | 1 | 0 | 1 | 2011-01-30: 350,000,000 → masked |
| HSY | `consumer_staples` | 8 | 8 | 0 | 2008-12-31: 18,384,000 → 1,505,954,000 |
| INTU | `standard` | 1 | 0 | 1 | 2011-04-30: 500,000,000 → masked |
| LII | `industrials` | 11 | 11 | 0 | 2015-12-31: 31,000,000 → 506,000,000 |
| META | `standard` | 3 | 0 | 3 | 2014-12-31: 0 → masked |
| NDSN | `industrials` | 5 | 0 | 5 | 2009-10-31: 4,290,000 → masked |
| NI | `utilities` | 3 | 3 | 0 | 2023-12-31: 23,800,000 → 11,055,500,000 |
| NOC | `industrials` | 16 | 16 | 0 | 2008-12-31: 24,000,000 → 3,443,000,000 |
| NSC | `railroads` | 1 | 1 | 0 | 2010-06-30: −6,689,000,000 → 6,326,000,000 |
| NUE | `materials_integrated` | 6 | 6 | 0 | 2019-12-31: 20,000,000 → 4,291,301,000 |
| ODFL | `industrials` | 17 | 16 | 1 | 2020-06-30: 45,000,000 → 99,923,000 |
| OMC | `media` | 24 | 0 | 24 | 2015-03-31: 600,000 → masked |
| PAYX | `industrials` | 1 | 0 | 1 | 2018-05-31: 0 → masked |
| PCG | `utilities` | 2 | 0 | 2 | 2019-06-30: 0 → masked |
| PEP | `consumer_staples` | 19 | 19 | 0 | 2020-06-13: 750,000,000 → 38,371,000,000 |
| PH | `industrials` | 10 | 10 | 0 | 2021-03-31: 186,388,000 → 6,571,908,000 |
| PODD | `pharma_medtech` | 11 | 11 | 0 | 2023-09-30: 49,800,000 → 1,370,600,000 |
| PSX | `energy_integrated` | 1 | 1 | 0 | 2016-12-31: 1,000,000,000 → 9,588,000,000 |
| PWR | `industrials` | 25 | 12 | 11 | 2019-12-31: 68,327,000 → 1,292,195,000 |
| RMD | `pharma_medtech` | 2 | 0 | 2 | 2010-09-30: 93,800,000 → masked |
| SLB | `energy_integrated` | 17 | 0 | 17 | 2010-06-30: 440,000,000 → masked |
| TECH | `pharma_medtech` | 15 | 15 | 0 | 2018-09-30: 12,500,000 → 548,973,000 |
| VZ | `telecom_cable` | 24 | 24 | 0 | 2014-12-31: 319,000,000 → 110,029,000,000 |
| WEC | `utilities` | 2 | 2 | 0 | 2024-06-30: 1,157,400,000 → 16,907,800,000 |
| XEL | `utilities` | 3 | 3 | 0 | 2014-12-31: 0 → 11,499,634,000 |
| XOM | `energy_integrated` | 11 | 11 | 0 | 2009-12-31: 348,000,000 → 7,129,000,000 |

---

## Why the ordering was wrong originally

No deliberate rationale is evident — it reads as an accretion artifact. The list appears to have
been built by appending tags as individual tickers needed them, with the `Convertible*` family added
as a contiguous block (`ConvertibleLongTermNotesPayable`, `ConvertibleDebtNoncurrent`,
`ConvertibleDebtCurrent`, `ConvertibleNotesPayableCurrent` sit adjacent in the original), so the two
*Current* members inherited a high position purely from being grouped with their *Noncurrent*
siblings rather than from any judgement about their scope. The sum's placement ahead of the combined
tags is defensible on its own terms (when complete it genuinely is the better figure) — its flaw was
never the position but the silent degradation, which is why it kept its slot and gained `require`
instead.

## Residual items (logged, not fixed)

- **`UnsecuredLongTermDebt` is a narrow sub-category tag** (unsecured slice only) sitting at priority
  8 among complete-debt tags. It happened to be correct for CDNS, but it is not structurally
  equivalent to the two tags above it. Out of scope here; worth a look if it ever surfaces a bad value.
- **The neighbour-based detection heuristic undercounts** when consecutive quarters are both
  contaminated (BALL) or when the contaminated value is close in scale to its neighbours (INTU, RMD).
  Any future scan of this class should prefer the same-date shadow-tag test, which has no such blind spot.

No scratch scripts left behind.
