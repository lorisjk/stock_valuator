# The Snapshot Forward-Fill — a Third Staleness Question, and the Guard That Answers It

**Task:** stop `build_snapshot` publishing a value that is real but ten quarters old as if it
were current. AppLovin is the reproduction case and the acceptance test.

Every number below comes from the local CompanyFacts cache and one price capture (610 tickers,
2,790,575 price rows, taken 2026-09-04), driven through the pipeline's own functions. Base facts
are read from the same immutable cache on both sides of every diff, and side A is produced by
disabling exactly one thing — `split_stale` becomes a passthrough — rather than by reverting
files, so the diff isolates the guard and nothing else.

**Universe: 607, not 609.** `AVB`, `EA` and `EQR` are absent from today's SEC
`company_tickers.json` and do not resolve to a CIK. `preflight.py` reports the same three
independently. Nothing to do with this change; a real refresh today would skip them too.

---

## 1. Step 0 — what is actually broken

### 1.1 `get_latest_value` is already bounded. The report's diagnosis is half right.

> *"Confirm it selects the most recent non-null row regardless of how far that row is from the
> most recent period — that is the stated bug; verify it from the code rather than from the
> report's inference."*

Verified from the code, and **it is not what the function does** (metrics.py:412):

```python
latest["value_age_days"] = (latest["ticker"].map(newest_end) - latest["end"]).dt.days
if max_value_age_days is not None:
    latest = latest[latest["value_age_days"] <= max_value_age_days]
```

`MAX_LATEST_VALUE_AGE_DAYS = 365` has bounded it since the FFO cycle, and MDs/metrics.md states
the reference in terms that are precisely the blind spot:

> *"**The age is measured inside the series, not against today.** A filer whose whole series ended
> three years ago has age 0, because its newest row *is* its value; absolute staleness stays the
> job of `days_since_last_filing` and `fundamentals_stale`."*

That delegation is where the bug lives. `newest_end` is `filtered_df.groupby("ticker")["end"].max()`
— the newest row **of that concept**. A concept whose rows *stop altogether* therefore has an age
of **zero**: its newest row is its value. The bound cannot see it, by construction, and the
function that would notice is the one the docstring hands the question to — which measures the
*ticker*, not the *metric*.

### 1.2 …and `fcf_ttm` never goes through `get_latest_value` at all

The reproduction case runs through a second path with **no age test of any kind**:

```python
fcf = get_latest_row(metrics["fcf"]).rename(columns={"fcf": "fcf_ttm"})
```

`get_latest_row` is `df.loc[df.groupby("ticker")["end"].idxmax()]` — the newest row, whatever it
holds. And `metrics["fcf"]` is `calculate_difference(facts, "OperatingCashFlow_TTM", "Capex_TTM", …)`,
an **inner merge**. When one input stops, the frame does not gain nulls; it *ends*. The newest row
of a frame that ended in 2023 is a 2023 row.

**21 of the snapshot's fields take this path** — `fcf_ttm`, `ebitda_ttm`, `yoy_growth`,
`net_interest_margin`, `efficiency_ratio`, `roa`, `equity_to_assets`, `provision_ratio`,
`combined_ratio`, `loss_ratio`, `expense_ratio`, `net_investment_yield`, `reserve_growth`,
`inventory_turnover`, `dio`, `dso`, `dpo`, `cash_conversion_cycle`, `rd_intensity`,
`capex_intensity`, `operating_leverage` — plus 7 more through `get_latest_row(rolling_multiples)`
for the `avg_*_5y` markers. Against 11 through `get_latest_value`.

**Two mechanisms, one cause: recency measured against the wrong reference.**

### 1.3 AppLovin, from the cache

```
APP, newest period of any concept: 2026-06-30

  Capex                   16 rows, newest 2023-12-31, last value       244,000
  Capex_TTM               16 rows, newest 2023-12-31, last value     4,246,000
  FCF_TTM                 13 rows, newest 2023-12-31, last value 1,057,264,000
  OperatingCashFlow_TTM   26 rows, newest 2026-06-30, last value 4,527,589,000
```

No nulls after 2023 — the rows are simply not there. The published snapshot (side A):

| | published | lag of the input |
|---|---:|---:|
| `fcf_ttm` | $1,057,264,000 | **912 days** |
| `pfcf_ratio` | 99.96 | |
| `ev_fcf` | 100.40 | |
| `pfcf_ex_sbc` | 136.39 | |

`OperatingCashFlow_TTM` at 2026-06-30 is $4.528bn and the last quarterly `Capex` on record is
$244K, which reproduces the reported ~$4.51bn correct figure. **This task does not publish that
number** — computing it would be the tag investigation the brief excludes. It publishes nothing,
which is the honest-gap default.

A second field the report did not name has the same cause: `capex_intensity`, lag **1,004 days**.

### 1.4 The existing flags answer a different question, measured

`days_since_last_filing`, `fundamentals_stale` and `filing_likely_overdue` are all computed from
`facts.groupby("ticker")["end"].max()` against the run date or the next expected filing. They are
**ticker-level filing recency**. They cannot see a metric that stopped while the ticker kept
filing — which is the entire failure mode.

```
tickers                                        607
fundamentals_stale = 1                         128
filing_likely_overdue = 1                        0
a value withheld by the new guard              149
  of which fundamentals_stale = 0              115      (77%)
fundamentals_stale = 1 and nothing withheld     94

days_since_last_filing, median / max
  the 149 affected tickers                 66 / 247
  the other 458                            66 / 188

APP: days_since_last_filing 66, fundamentals_stale 0
```

**115 of 149 affected tickers are called current by the existing flag**, and the median filing
recency is identical in both groups — 66 days. The two questions are close to orthogonal.

### 1.5 Was a `max_staleness_quarters`-shaped guard attempted and abandoned?

Not abandoned — **scoped to a different reference, twice, and both times deliberately.**

- `MAX_LATEST_VALUE_AGE_DAYS = 365`, intra-series (§1.1).
- `MAX_EDGAR_SHARE_LAG_DAYS = 200` in `_resolve_share_sources`, which is the *only* place in the
  codebase that already measures against the ticker's newest period — and the bugfix history
  records why in exactly the terms this task needs:

  > *"measured against the ticker's own newest fact, not today's date, so a wholly SEC-lagged
  > payload isn't punished twice"*

So the reference this fix needs exists, is documented, and had been applied once, to share counts.
The annual-path-gate report also lists `get_latest_value` fixes under "deliberately not fixed",
so this defect was known and deferred rather than tried and rejected.

### 1.6 Exposure across the universe

For every one of the 39 snapshot fields, the `end` of the value its lookup lands on, against
`newest_period(facts)` — the newest period the ticker reported anything for.

```
lookups                    9,882      over 607 tickers and 39 fields
lookups carrying a value   9,654
```

| lag (days) | lookups | | lag (days) | lookups |
|---|---:|---|---|---:|
| 0 | 9,119 | | **366–453** | **0** |
| 1–100 | 44 | | 454–730 | 60 |
| 101–200 | 83 | | 731–1,095 | 56 |
| 201–300 | 21 | | 1,096–1,826 | 91 |
| 301–365 | 12 | | 1,827–3,652 | 126 |
| | | | > 3,652 | 42 |

Value by value, the non-zero lags are a quarterly lattice — 87, 89, 90, 91, 92 · 179, 181, 182,
185 · 273, 274, 280 · 364, 365 — and then **nothing at all until 454**, after which it resumes
(454, 455, 456, 457, 459, 462, 546, …) and runs out to **5,752 days**.

By path: `get_latest_value` 193 of 3,955 lookups non-zero, `get_latest_row(metrics)` 203 of
3,180, `get_latest_row(rolling)` 188 of 2,747. All three paths carry the defect.

---

## 2. Step 1 — the bound, the failure mode, the scope

### 2.1 `MAX_LATEST_VALUE_LAG_DAYS = 365`, from the empty run

**The empty run 366–453 is 88 days wide.** Highest lag in the legitimate region: 365. Lowest
beyond it: 454. Every bound in **[365, 453]** withholds the identical 375 values — and that is
not asserted, it is measured, by re-running the acceptance harness of §4.2 at several bounds:

| bound | harness |
|---:|---|
| 273 | 11,093 / 11,108 |
| 364 | 11,096 / 11,108 |
| **365** | **11,108 / 11,108** |
| 366 | 11,108 / 11,108 |
| 453 | 11,108 / 11,108 |
| 454 | 11,107 / 11,108 |
| 546 | 11,074 / 11,108 |

365 is taken from inside that run because it is the **same twelve-month definition
`MAX_LATEST_VALUE_AGE_DAYS` already uses**, and the sibling constant's own derivation took the
definitional endpoint rather than the midpoint for the same reason. Nothing is gained by moving
to 409.

**Why not the brief's suggested 1 quarter.** A bound below 365 cuts into **annual-cadence
series**, whose lag oscillates 0 → 91 → 182 → 273 → 365 through the year and resets. Of the 114
kept non-zero lookups, **36 sit on a series whose own median reporting step is 300–400 days**.
Measured against each series' own cadence:

| | n | median step | lag ÷ own step: median | min | max |
|---|---:|---|---:|---:|---:|
| kept (lag ≤ 365) | 114 | 65 quarterly, 36 annual | **0.99** | 0.24 | 4.01 |
| withheld (lag > 365) | 233 | 200 quarterly, 15 annual | **17.9** | 2.50 | 63.2 |

A kept value is about **one of its own periods** behind. A withheld one is about **eighteen**.

**A cadence-relative bound was considered and is worse.** "N of its own reporting periods"
overlaps — kept runs to 4.01, withheld starts at 2.50 — while the absolute day bound has an
88-day empty run. The absolute bound separates; the relative one does not.

### 2.2 Failure mode: blank, plus a marker that says why

Blank is the project's honest-gap default. But a bare blank is indistinguishable from "this
profile does not compute that", so the guard publishes `<field>_stale_days` — the lag of the
value it refused — beside the existing `<field>_age_days` for one it carried. Same shape, same
melt, same section; the pair reads as *carried* vs *refused*.

**Only where a number was actually withheld.** A stale row that was null anyway would have
published nothing either way, and a marker on it would claim the guard is the reason a field is
absent when it is not — the same restraint `_age_days` shows in emitting only non-zero ages.

**`_age_days` is deliberately not redefined.** It is a documented, verified quantity meaning
"how far back inside its own series the snapshot had to reach", and the lag is a different
number (lag ≥ age always). Redefining it would move a published value for no reason this task
asked for. The consequence is recorded as a follow-up in §6.

### 2.3 Scope: every field, and the reference is what makes that safe

The brief asks whether a raw point-in-time fact should be treated differently from a rolling
derived figure — "a raw fact that is merely old because the filer hasn't reported again yet is a
different situation".

**The choice of reference dissolves the question.** Because the bound is measured against the
ticker's *own* newest period, a filer who simply has not reported since March moves its reference
with it and its lag stays 0. Nothing is withheld. The guard fires only when the rest of the
filing moved on **without** this metric — which is as wrong for `LongTermDebt` as for `FCF_TTM`,
and in fact worse: `debt` is the largest single source of withheld values (43), and VRTX's
last-tagged `LongTermDebt` is **$105m from 2011-09-30**, sitting under a 2026 enterprise value.

This is the argument `MAX_EDGAR_SHARE_LAG_DAYS` already makes (§1.5), applied to the rest.

**Two deliberate opt-outs**, both commented at the call site:

- **`_revenue_scale`** — already opts out of the age bound; an order-of-magnitude reference does
  not go stale the way a published figure does, and withholding it would take the scale guard
  away from exactly the filers whose revenue stopped.
- **the share-count lookup** in `_resolve_share_sources` — it already measures lag against the
  same reference and has a **second source** to fall back on, so a guard there would not blank a
  field, it would silently switch which vendor's number `market_cap` uses. Two tickers have a
  `SharesOutstanding` lag over 365 days: BKR (1,826 days, already correctly on yfinance) and
  **ARES (546 days, `prefer_edgar = True` via the dual-class branch, EDGAR 313.17M against
  yfinance 222.03M)**. Withholding ARES's EDGAR count would move its market cap by −29% on a
  judgment about dual-class share counts that belongs to the share-count investigation, not this
  one. Recorded as a follow-up in §6.

The `avg_*_5y` markers **are** in scope: `avg_pfcf_5y` is published as *the* current five-year
average and drawn as a reference line, and a window that ended four years ago is not one.

### 2.4 Dependent ratios — traced, and they blank for free

Every ratio in `build_snapshot` is an expression over `snap[...]` columns, so a withheld input
arrives as NaN, propagates, and is removed by `long.dropna(subset=["value"])`. Traced from
`fcf_ttm` specifically and then generalised to every `_TTM`-derived ratio:

| withheld input | consumers that must blank with it |
|---|---|
| `fcf_ttm` | `pfcf_ratio`, `ev_fcf`, `pfcf_ex_sbc` (via `owner_fcf`) |
| `sbc_ttm` | `pfcf_ex_sbc` |
| `debt`, `cash` | `net_debt` → `ev` → `ev_ebitda`, `ev_sales`, `ev_fcf` |
| `ebitda_ttm` | `ev_ebitda` |
| `revenue_ttm` | `ev_sales` |
| `eps_ttm` | `pe_ratio` → `pe_to_revenue_growth` |
| `dividends_ttm` | `dividend_yield` |
| `equity` | `pb_ratio` |
| `tangible_equity` | `p_tbv`, and the `pb_ratio` veto |
| `ppnr_ttm` / `core_earnings_ttm` / `ffo_ttm` | `p_ppnr` / `p_core_earnings` / `p_ffo` |
| `avg_X_5y` | `avg_X_5y_median`, `_diverges`, `_history_too_short` |

§4.3 verifies that this is what happens, on all 646 disappearances, with nothing left over.

---

## 3. What was implemented

| file | change |
|---|---|
| `metrics.py` | `MAX_LATEST_VALUE_LAG_DAYS = 365` with the empty run it came from; `newest_period(df)`; `split_stale(rows, reference, max_lag_days) -> (publishable, withheld)`. `get_latest_value` and `get_latest_row` are **untouched** |
| `main.py` | `build_snapshot` computes `reference = newest_period(facts)` once; `latest_value` and a new `latest_metric` route both lookup paths through `split_stale`; the `avg_*_5y` loop does the same; `_record_stale` emits `<field>_stale_days`; opt-out comments at the two call sites that keep their own rule |
| `config.py` | `_ROW_ABOUT_SUFFIXES` / `_strip_row_suffix`: `is_hidden` now strips `_age_days` and `_stale_days` as it always stripped `_quarterly` |
| `MDs/metrics.md` | the three staleness questions and which reference each uses |
| `MDs/main.md` | the second lookup path, the behaviour change, the opt-outs |
| `MDs/config.md` | `_ROW_ABOUT_SUFFIXES` |
| `MDs/bugfixes_opdate_history.md` | entry per convention |
| `README.md` | `<field>_stale_days` in the honesty-signals table |

**One guard, called from three places, rather than a rule in each lookup.** The two paths fail
differently on a *null* — `get_latest_value` skips it, `get_latest_row` returns it — but
identically on a series that *stops*, which is the case that matters. Publishing policy is the
snapshot's business, so the guard sits in `build_snapshot` and `get_latest_value` keeps its
documented contract intact.

**Why `is_hidden` also changed.** Without it, **190 of the guard's 429 markers land on fields
their own profile hides** — 61 of them `avg_p_tbv_5y`. `filter_hidden_rows` is the project's
single mechanism for "this ticker does not publish this metric", and a provenance row about a
hidden metric is exactly what it should catch. `profile_visibility()` is **byte-identical to the
exported registry** after the change, because that export is keyed by metric id and no id ends in
either suffix.

No frontend file changed. No export schema, registry schema or per-ticker schema changed.

---

## 4. Step 3 — verification

### 4.1 `APP`, the reported case

```
                          A (before)              B (after)
fcf_ttm            1,057,264,000.0000                        <-- gone
fcf_ttm_stale_days                              912.0000     <-- new
pfcf_ratio                    99.9620                        <-- gone
ev_fcf                       100.3987                        <-- gone
pfcf_ex_sbc                  136.3890                        <-- gone

revenue_ttm        6,829,124,000.0000     6,829,124,000.0000
ebitda_ttm         5,422,526,000.0000     5,422,526,000.0000
eps_ttm                       13.0854               13.0854
pe_ratio                      23.9640               23.9640
ev                106,147,946,980.0000   106,147,946,980.0000
ev_ebitda                     19.5754               19.5754
ev_sales                      15.5434               15.5434
market_cap        105,686,180,980.0000   105,686,180,980.0000
debt / cash / equity / yoy_growth / price / all flags        identical
```

**Every one of the four FCF-derived figures is gone; nothing else on the ticker moved.** 42 of the
46 concepts are unchanged.

`APP`'s history is untouched: `facts`, `metrics_long` and `valuation_history` are byte-identical
frames across the whole universe (§4.3), so `FCF_TTM` is still correctly present through
2023-12-31 and correctly absent afterwards in `metrics_long`/`valuation_history`.

**And the historical snapshot is not retro-blanked.** `build_snapshot_as_of("2023-12-31")`
publishes `APP fcf_ttm = 1,057,264,000` and `pfcf_ratio = 13.67` — at that date the value *was*
current, its lag was 0, and the guard correctly references the cut frame:

```
as_of 2023-12-31: 25,643 rows, 593 tickers, 310 _stale_days rows,  APP fcf_ttm = 1.057e9
as_of 2020-12-31: 23,888 rows, 564 tickers, 246 _stale_days rows,  APP fcf_ttm = None
```

### 4.2 The rule, re-derived independently

The guard's decision is recomputed from the source frames — facts, the metrics frames, the
rolling multiples — without reading `split_stale`, for all 39 fields × 607 tickers:

```
[rule]      independent re-derivation of every marker      11,108 / 11,108
[published] every published direct field within the bound   9,302 / 9,302
```

Both directions: nothing is withheld that should not be, and nothing survives that should not.
The per-marker check also asserts the **exact lag**, not just presence.

**The harness is sensitive.** It fails where predicted under mutation — 15 failures at bound 273,
12 at 364, 1 at 454, 34 at 546 — and is identical only across the measured empty run (§2.1). The
first run of it disagreed with the pipeline on **49** pairs, all one shape: the harness modelled
`get_latest_value` as "newest non-null" and omitted the pre-existing age bound, which runs first
and drops those 49 before the lag guard ever sees them. Fixing the *harness* is what made it
11,108/11,108; the pipeline was right.

### 4.3 Universe-wide diff, 607 tickers

```
frame                A                 B                 identical
facts             (1,150,620, 6)    (1,150,620, 6)       True
metrics_long        (570,384, 4)      (570,384, 4)       True
valuation_history   (352,023, 4)      (352,023, 4)       True

snapshot             25,293            24,886
   disappeared   646
   appeared      239      all of them _stale_days
   changed         0
```

**Nothing computed moves. Nothing published moves. Values only leave.**

Every disappearance traced to a withheld input through `build_snapshot`'s own expression graph:

```
disappeared 646    accounted 646    unaccounted 0
   direct     195
   dependent  451
```

**The 195 direct**, by field: `debt` 43, `cash` 29, `dividends_ttm` 26, `avg_ev_ebitda_5y` 18,
`fcf_ttm` 14, `avg_pfcf_5y` 12, `ebitda_ttm` 11, `provision_ratio` 8, `capex_intensity` 6,
`eps_ttm` 5, `avg_pe_5y` 4, `core_earnings_ttm` 3, `operating_leverage` 3, `dso` 2, `equity` 2,
and one each of `avg_p_tbv_5y`, `avg_p_ppnr_5y`, `avg_p_core_earnings_5y`, `combined_ratio`,
`cash_conversion_cycle`, `loss_ratio`, `expense_ratio`, `revenue_ttm`, `tangible_equity`.

**The 451 dependents**, rolled up to their cause: `debt` 172, `cash` 74, `avg_ev_ebitda_5y` 54,
`fcf_ttm` 37, `avg_pfcf_5y` 36, `dividends_ttm` 26, `avg_pe_5y` 12, `sbc_ttm` 10, `ebitda_ttm` 8,
`eps_ttm` 7, then single digits. **The largest consequence of the whole change is `debt` and
`cash`: 59 tickers lose `ev`, and with it `ev_sales` (59), `ev_fcf` (63) and `ev_ebitda` (48).**

Markers: **429 raised, 239 published** after `filter_hidden_rows` strips the 190 that name a
hidden field.

### 4.4 The cases that are worse than the one that was reported

| ticker | field | lag | | what was published |
|---|---|---:|---|---|
| AEP | `dividends_ttm` | 5,569 d (15.2 y) | $1.71 from 2010-12-31 | `dividend_yield` **1.37%** against a $124.71 price |
| SLB | `dividends_ttm` | 5,387 d (14.7 y) | $0.96 from 2011-09-30 | `dividend_yield` **1.67%** against $57.41 |
| VRTX | `debt` | 5,387 d (14.7 y) | $105m from 2011-09-30 | `net_debt`, `ev` $135.4bn, `ev_sales` 10.76, `ev_fcf` 35.66 |
| ULTA | `dividends_ttm` | 4,837 d | | `dividend_yield` |
| ETN, MAR, KLAC, GPC | `ebitda_ttm` | 4,564–3,743 d | | `ev_ebitda` |
| AXP | `ebitda_ttm` | **5,752 d (15.7 y)** | | hidden for its profile; withheld, not published |

AEP's real 2026 dividend is several times $1.71, so the published yield was roughly a third of
the truth — a larger relative error than AppLovin's P/FCF, on a figure with no visible sign of
being wrong.

**On VRTX and the debt cases:** blanking `ev` for a company whose real debt may genuinely be near
zero loses a good number. The pipeline cannot tell the two apart, and the project has already
decided this exact question against inference — the 2026-08-02 entry records `debt_inferred_zero`
as **not implemented, on evidence**, because "no debt tag ⇒ real zero" failed on GRMN, LULU and
DECK. A *stale* debt tag is the same situation, so the same answer applies.

### 4.5 No false positives

```
tickers                607
untouched              458   (75.5%)
touched                149
```

Per profile, the affected share runs from **0% (airline)** to 62.5% (alt_asset_manager), with the
large profiles at 22.2% (standard, 48 of 216) and 21.1% (industrials, 15 of 71) — no profile is
wiped out and no profile is untouched by accident.

**One untouched ticker per profile, whole snapshot row for row:**

```
airline DAL 41 · alt_asset_manager AMG 28 · captive_finance CAT 44 · consumer_staples ADM 39
energy EOG 47 · energy_integrated CVX 39 · financial AXP 46 · health_services CNC 42
homebuilder DHI 39 · industrials ADP 41 · insurance_pc ACGL 38 · leisure CCL 45
marketplace BKNG 46 · materials ALB 48 · materials_integrated AVY 40 · media FOX 38
pharma_medtech A 40 · railroads NSC 43 · reit AMT 29 · retail AZO 38 · standard AAPL 46
telecom_cable CHTR 42 · utilities AEE 40
```

**23 of 24 identical, row for row.** The 24th (insurance_life, AFL) loses nothing and *gains* a
marker — see §4.6.

Across the universe the guard withholds nothing from a filer that is merely behind: **207 of the
243 tickers raising a marker filed within 135 days** (`STALENESS_DAYS_FALLBACK`), median 66.

### 4.6 The markers, and 17 that are inert

**16 tickers gain only `sbc_ttm_stale_days`** and one only `ffo_ttm_stale_days`, losing nothing:
those inputs are not published as their own concept, and the consumer they feed (`pfcf_ex_sbc`,
`p_ffo`) was already absent for other reasons. AFL is one — `sbc_ttm` is 638 days behind. The
markers are true and harmless, but they explain nothing that changed. Suppressing them would
need a consumer graph inside `build_snapshot`; noted rather than built.

### 4.7 The frontend's snapshot marker

`snapshotPoint` (`frontend/src/charts/snapshot.ts`) selects by concept from
`frames.current_snapshot` and returns null when there is no row — its documented case 1. A
withheld value is exactly that, so the marker disappears with no frontend change. **Confirmed
rather than assumed**, running the real module under Node against the A and B frames:

```
[snapshotPoint] 72/72
  APP  pfcf_ratio:   marker 99.96  -> none
  APP  ev_fcf:       marker 100.40 -> none
  APP  pfcf_ex_sbc:  marker 136.39 -> none
  VICI ev_fcf:       marker 66.06  -> none
  ARES pe_ratio:     marker 100.51 -> none
  ARES ev_sales:     marker 7.41   -> none
  ARES pe_to_revenue_growth: marker 4.18 -> none
```

The check asserts both directions — a marker exists exactly when the pipeline published a row —
and that no `_stale_days` concept collides with any of the 13 valuation ids.

### 4.8 The provenance surfaces where `_age_days` does

`render_snapshot_section` (app.py) and `DataTab.tsx` both render the snapshot as a generic
concept/value list sorted by concept, so `fcf_ttm_stale_days` lands next to `fcf_ttm`. Run through
app.py's own formatter:

```
fcf_ttm_stale_days   912.0000        eps_ttm_age_days   273.0000
```

Identical treatment to the existing marker, including its cosmetic four decimals on an integer
count — a pre-existing quirk shared with `_age_days`, noted in §6.

### 4.9 Standing regression suite

- **Export validator: `ACCEPTED: all 41 checks passed`**, run against a full `export_for_app` of
  the B frames written to a scratch directory (607 tickers, 2,765,241 rows, 1,214 per-ticker
  files, 193 MB). `current_snapshot.parquet` 24,886 rows against a floor of 19,116.
- **`preflight.py`: OK**, both sources answer.
- **`npx tsc -b`: clean.** **`npx eslint .`: the same 4 pre-existing errors** (`Chart.tsx:11`,
  `ChartView.tsx:240/242`, `Sidebar.tsx:94`) — unchanged, no frontend file was edited.
- `check-chart-width`, `check-tab-state`, `check-table-format` **not re-run**: they are DOM
  harnesses over the frontend, no frontend file changed, no export column or schema changed, and
  the one frontend behaviour downstream of this change was checked directly in §4.7.
- Chart-builder A/B **not re-run for the valuation and comparison charts**: `buildValuation` reads
  the snapshot only through `snapshotPoint` (§4.7), and `buildComparison` does not read the
  snapshot frame at all. `valuation_history` — which both actually draw from — is byte-identical.

**`data/app` was not regenerated.** A real export today drops AVB, EA and EQR for an unrelated SEC
mapping outage (§ preamble), and attributing that loss to this change would be worse than leaving
the export to the nightly run. Nothing in this change alters an export column, a schema or the
registry, so the published export needs no migration — only the next refresh.

---

## 5. Step 3.6 — the flag delta

Base-concept coverage flags are computed from the facts frame, which is byte-identical: **no
change**. Snapshot flags:

| flag | A: rows / =1 | B: rows / =1 |
|---|---:|---:|
| `fundamentals_stale` | 607 / 128 | 607 / **128** |
| `filing_likely_overdue` | 607 / 0 | 607 / 0 |
| `pe_ratio_band_elevated` | 567 / 80 | 567 / 80 |
| `pfcf_ratio_band_elevated` | 499 / 86 | 499 / 86 |
| `ev_ebitda_band_elevated` | 404 / 76 | 404 / 76 |
| `p_ffo_band_elevated` | 565 / 103 | 565 / 103 |
| `p_tbv_band_elevated` | 442 / 102 | 442 / 102 |
| `avg_ev_ebitda_5y_history_too_short` | 390 / 100 | 372 / 82 |
| `avg_pfcf_5y_history_too_short` | 485 / 77 | 473 / 65 |
| `avg_pe_5y_history_too_short` | 551 / 65 | 547 / 62 |
| `avg_ev_ebitda_5y_diverges` | 390 / 23 | 372 / 22 |

**Only the `avg_*_5y` flags move, and only by losing the rows whose mean line was withheld.** No
flag changes value on a ticker that keeps its line; the `*_band_elevated` flags are computed from
`valuation_history` and are untouched.

**The headline number the brief asks for:** **646 (ticker, metric) pairs changed from a published
value to an honest gap** — 195 withheld directly, 451 blanked as dependents — across 149 of 607
tickers, with **239 markers published** saying why. `fundamentals_stale` does not move at all,
which is the point: it was never measuring this.

---

## 6. Follow-ups

**Does the same question exist for other derived `_TTM` metrics?** Yes, and the guard already
covers them — that is why the scope is every field rather than `FCF_TTM`. The measured spread is
`debt` 43, `cash` 29, `dividends_ttm` 26, `fcf_ttm` 27, `ebitda_ttm` 28, `sbc_ttm` 32,
`tangible_equity` 22, `ffo_ttm` 12, `eps_ttm` 5, `core_earnings_ttm` 3, plus the ratio metrics.
`FCF_TTM` is not even the largest. **No second pass is needed for coverage.** The four items below
are genuinely open.

**1 — `<field>_age_days` still measures inside the series.** A value published at a lag of 273
days whose concept's newest row *is* that value has age 0 and therefore no marker at all: 160
published values are lagged, 35 carry an `_age_days` row. Publishing the lag instead of the age
would close it, and would make the pair `_age_days` / `_stale_days` one quantity under two names.
It changes a published quantity's meaning, so it was not done here.

**2 — ARES's market cap rests on a 546-day-old EDGAR share count.** `prefer_edgar` is true via
the dual-class branch, which has no lag rule at all (only the yfinance-overstatement branch checks
`MAX_EDGAR_SHARE_LAG_DAYS`). EDGAR 313.17M against yfinance 222.03M; withholding would move
market cap −29%. Whether a stale dual-class count beats a current single-class one is a
share-count question with its own evidence, and the bugfix history's 2026-08-02 entry is where
that evidence lives.

**3 — 17 inert markers** (§4.6): `sbc_ttm_stale_days` / `ffo_ttm_stale_days` on tickers whose
consumer was already absent.

**4 — the marker's formatting.** `912.0000` for a day count, because the snapshot's formatter
decides per value and a count under `ABSOLUTE_THRESHOLD` takes the ratio format. Pre-existing and
shared with `_age_days`; a `_days` suffix rule in `_percent_applies`' neighbourhood would fix
both.

**Explicitly not touched**, per the brief: `calculate_ttm`'s window logic, why `Capex` stopped
being tagged, `calculate_growth` and the growth catalogue, `PROFILE_HIDDEN` contents, and the
five items the TTM and annual-path reports list as deliberately unfixed
(`decumulate_period_values`' 80–100 day window, duplicated period ends,
`apply_denominator_scale_guard`'s missing-reference default, `pct_change`'s `ffill` default,
`ffo["gains"].fillna(0)`).

---

### Verification performed

- 9,882 snapshot lookups across 607 tickers and 39 fields, classified by lag against
  `newest_period`, on the real inputs `build_snapshot` reads.
- The bound re-run at 273 / 364 / 365 / 366 / 453 / 454 / 546 against the acceptance harness, to
  establish the empty run empirically rather than by reading the histogram.
- Cadence of every stale series measured from its own last eight reporting steps.
- Before/after over all 607 tickers from one price capture, base facts re-derived from the same
  cache on both sides, side A produced by disabling `split_stale` alone.
- Every appeared, disappeared and changed snapshot value accounted for: 646 / 646 / 0.
- The guard's decision re-derived independently from the source frames, 11,108 / 11,108, with the
  exact lag asserted per marker, and proven to fail under mutation.
- `build_snapshot_as_of` exercised at two cut-off dates.
- `snapshotPoint` run under Node against both frames, 72 / 72.
- `export_for_app` + `validate_export.py` end to end into a scratch directory: 41 / 41.
- `profile_visibility()` compared byte for byte against the exported registry after the
  `is_hidden` change.

No full refresh was run; `data/` and `figures/` are untouched. No scratch files left behind.
