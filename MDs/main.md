# `main.py`

## Overview

Orchestration. Pulls the other modules together in the right order and writes the outputs.

Nothing here is a reusable primitive — those live in `metrics.py`. What lives here is the *wiring*: which concepts feed which metric, which data source joins to which, and in what sequence. `main()` itself is a twenty-line summary of the pipeline; the work sits in named functions above it.

The functions that combine EDGAR fundamentals with yfinance prices (`build_valuation_history`, `build_snapshot`, `calculate_share_count_jump_flag`) are here rather than in `metrics.py` because they know about both data sources. `metrics.py` stays agnostic about where its DataFrames came from.

---

## Pipeline

```
prices first                   yfinance → daily closes + the corporate-action feed
    ↓                          (the parser needs the splits, so this cannot move)
build_dataframe() per ticker   EDGAR → quarterly values, one row per ticker/concept/date
    ↓
print_data_quality()           coverage warnings, on the BASE concepts only
    ↓
add_derived_concepts()         + _TTM series, + EPS_TTM_CALC, + PPNR/FFO/CoreOperatingEarnings
add_quarterly_derived_concepts()
    ↓
calculate_all_metrics()        every ratio, difference and quality flag
calculate_quarterly_metrics()  their single-quarter counterparts
    ↓
add_as_concept()               + FCF_TTM, EBITDA_TTM (and the _QUARTERLY pair) into facts
    ↓
build_metrics_long()           metrics dict → one long frame
build_valuation_history()      the valuation multiples, as a time series
calculate_rolling_multiple_averages()   avg_*_5y, their medians and counts
calculate_peer_band_flags()    the one cross-sectional flag
build_snapshot()               current figures, melted to long
add_staleness_fields() / calculate_filing_overdue_flags()
    ↓
filter_hidden_rows() on every frame
    ↓
CSVs  +  export_for_app()  +  charts (only when write_charts=True)
```

**Two entry points, deliberately different.** `main()` is the local development run: it
uses `TICKERS` — a two-ticker list, not the universe — writes CSVs and defaults
`write_charts=True`, because it exists to look at output. `run_full_refresh()` is the
nightly run: `get_active_tickers()` (the full universe), CSVs *and* the app's parquet
export, and `write_charts=False`, because chart files cost about a third of the wall clock
and nothing downstream reads them — the app reads `data/app/*.parquet`.

---

## Functions

| Function | Purpose |
|---|---|
| `load_facts` / `load_price_history` / `load_current_prices` | inputs for the `TICKERS` dev run |
| `splits_by_ticker` | the corporate-action feed out of the price history, for the parser |
| `add_derived_concepts` | `_TTM` series, `EPS_TTM_CALC`, and the sector aggregates (PPNR, FFO, CoreOperatingEarnings) |
| `add_quarterly_derived_concepts` | their single-quarter counterparts |
| `calculate_all_metrics` | every ratio, difference and quality flag, as a dict of frames |
| `calculate_quarterly_metrics` | the `*_quarterly` series |
| `build_metrics_long` | metrics dict → one long-format table |
| `canonical_period_ends` | the join key that makes a pivot row a quarter |
| `build_valuation_history` | the valuation multiples as a time series |
| `calculate_rolling_multiple_averages` | `avg_*_5y`, `_median`, `_n` |
| `within_avg_5y_window` | the project's one definition of "the last five years" |
| `calculate_peer_band_flags` | own five-year low against the profile peers' median |
| `build_snapshot` | current figures for every ticker, melted to long |
| `build_snapshot_as_of` | the same at a historical cutoff |
| `add_staleness_fields` / `calculate_filing_overdue_flags` | freshness signals |
| `add_growth_column` | `yoy_growth` onto the facts frame, for the growth charts |
| `export_for_app` | the six parquet frames + `meta.json` the frontend reads |
| `main` / `run_full_refresh` | the two entry points above |

---

## The order in `main()` is not arbitrary

Three dependencies constrain it, and getting them wrong produces empty results rather than errors.

**`add_derived_concepts` before `calculate_all_metrics`.** Every ratio metric reads `_TTM` concepts. They do not exist until `add_ttm_concepts` has run.

**`calculate_all_metrics` before `add_as_concept(... "FCF_TTM")`.** FCF and EBITDA are computed metrics, not raw concepts. They have to exist as DataFrames before they can be folded back into `facts`.

**`add_as_concept` before `build_valuation_history`.** P/FCF and EV/EBITDA need `FCF_TTM` and `EBITDA_TTM` to be present in `facts`, because that function pivots `facts` into wide format and reads columns from it.

**`print_data_quality` runs on the raw facts**, before any derived concepts are added. Otherwise the `_TTM` series appear in the report as unexpected extras and skew the coverage ratios.

---

## Two output shapes, two purposes

### Long format (`facts`, `metrics_long`, `valuation_history`)

Columns: `ticker`, `end`, `concept`, `value`.

One row per observation. Adding a metric adds rows, never columns. This is what the plotting code consumes — `plot_metric` filters on `ticker` and `concept` and doesn't care what else is in the table.

### The snapshot: wide while it is built, long when it leaves

`build_snapshot` assembles a wide frame — one row per ticker, one column per figure — and
then **melts it** on the last few lines. What every consumer sees is
`ticker, end, concept, value`, the same four columns as the other frames, with `end`
constant at the run date (or at `as_of`).

That is not a cosmetic choice. The long shape is what lets a profile that does not apply
be simply *absent* rather than a column full of `NaN`, and it is what lets peer-band flags
and `<field>_age_days` rows be appended after the melt without widening a schema. It also
means `value` is one dtype for every concept, which is why `shares_basis` is stored
numerically via `SHARES_BASIS_CODES` — a string would force the whole column to `object`
on reload.

The wide stage still matters while reading the code: everything between `snap = prices.copy()`
and the melt is column arithmetic on one row per ticker.

---

## `EPS_TTM_CALC`

```python
eps_ttm = calculate_ratio(facts, "NetIncomeLoss_TTM", "SharesOutstanding", "value")
```

EPS is **not** derived by summing four quarterly EPS figures, even though that is the obvious approach and even though every other TTM concept works that way.

The reason is stock splits. EDGAR restates per-share figures retroactively after a split — but not uniformly across all filings. A rolling four-quarter window that straddles a split therefore mixes pre-split and post-split values. For NVIDIA around 2023 this produced a **negative** TTM EPS while net income was strongly positive, which then propagated into a negative share count, a negative market cap, and negative P/B, P/FCF and EV/Sales figures.

Computing EPS as `NetIncomeLoss_TTM / SharesOutstanding` avoids the problem entirely: both inputs are absolute quantities, immune to per-share restatement.

The share count itself comes from EDGAR (`WeightedAverageNumberOfDilutedSharesOutstanding`), not from yfinance — yfinance only reports today's count, which would be wrong for every historical quarter.

---

## The sector aggregates, and the one that carries an assumption

`add_derived_concepts` builds three concepts no filer reports directly, each existing so a
profile has a denominator its business model actually has: **PPNR** (pre-provision net
revenue, for banks), **CoreOperatingEarnings** (for insurers) and **FFO_TTM** (funds from
operations, for REITs).

FFO is the one with a caveat, and the caveat is published rather than hidden.

NAREIT FFO is net income plus real-estate depreciation minus gains on sales of depreciable
real property. **The gains term is present for only about 427 of ~1,836 REIT FFO periods**,
so roughly 77% of every REIT's FFO history rests on a `fillna(0)` — which asserts "no
disposals" from "not extracted".

The two cannot be told apart from the pipeline's own output:

- Absence does not mean no disposals. Of the 427 periods that do carry the term, only 10
  are zero, and the gaps track XBRL tagging practice rather than disposal activity — ARE
  tags from 2013, EQR from 2014, O from 2017, and all of them sold property before that.
- Of the twelve REITs that never produce the term at all, ten use a `us-gaap` disposal-gain
  tag this pipeline does not query.
- Where the term is measurable it moves FFO by a median 13.5%.

Blanking `FFO_TTM` wherever the term is unknown would delete three quarters of REIT FFO
history — and `p_ffo` for twelve REITs entirely — over a tag list. So the value stands and
**the assumption is labelled**: `ffo_gains_source` is `reported` or `imputed_zero` on the
row, the same instrument `ttm_source` uses for the two TTM derivations. A consumer that
cares can filter; a consumer that does not still sees a number rather than a hole.

The tag list itself is deliberately narrow. Every tag under the `reit` profile's
`GainLossOnSaleOfProperties` has to measure *depreciable real property* and nothing wider,
and the mode is `fallback` — first tag that reports a period end, never a sum — so a
filer's pre-tax and net-of-tax figures for one gain cannot be added together.
`GainLossOnDispositionOfAssets` and `GainLossOnDispositionOfAssets1` were **rejected on the
evidence, not for tidiness**: they would have contributed more TTM values than every
accepted tag combined, and they measure something else — AVB tags a 2011 property gain of
294.8m against 13.7m of "assets", PLD 656.9m against 195.1m.

---

## `merge_asof`

```python
pd.merge_asof(..., direction="backward")
```

Fiscal quarter ends often fall on weekends or holidays, when no price exists. A plain merge on the date column would match nothing.

`merge_asof` joins to the **nearest** date instead of an exact one. `direction="backward"` takes the last available price at or before the reporting date, which is the conservative choice — the market could not have known the figures before they were filed.

`by="ticker"` is essential. Without it, `merge_asof` would happily match Apple's quarter end to Microsoft's price if that price happened to be temporally closer.

Both sides must be sorted by the join column, and both must have the **same dtype**. yfinance returns timezone-aware timestamps at second resolution; EDGAR dates are naive. The conversion (`tz_localize(None)`, `.astype("datetime64[ns]")`) happens in `load_price_history` and `load_facts` precisely so that this merge works.

---

## `build_valuation_history`: long → wide → long

The only place in the project that pivots.

Valuation multiples need several concepts **in the same row** to divide one by another (`market_cap / equity`). In long format they sit in separate rows. `pivot_table` turns each concept into a column:

```python
wide = facts[facts["concept"].isin(needed)].pivot_table(
    index=["ticker", "end"], columns="concept", values="value"
).reset_index()
```

After the arithmetic, `melt` reverses the operation — the inverse of `pivot_table`, and effectively a bulk version of `to_long_format`. The result goes back into the long format the plotting code expects.

`.dropna(subset=["value"])` at the end removes rows where a multiple could not be computed (masked denominators, missing inputs), so they simply don't appear rather than showing up as gaps.

**A pivot row is not a quarter** — it was, until the join key was aligned. A row exists wherever *any* of the fourteen needed concepts reported, and a filer can end one concept's period a day or two from another's — CAT tags `StockholdersEquity` at 2017-01-01 and nine other concepts at 2016-12-31 — which produced 193 doubled rows across 102 tickers. It is why nothing downstream may count rows: `revenue_yoy_growth` and the `avg_*_5y` means both used to, and both were reaching the wrong period.

`canonical_period_ends` now collapses ends within **7 days** onto one date before the pivot: the same bound and the same mechanism as `merge_duplicate_period_ends` (a fiscal end is the chosen weekday nearest the month end, so at most six days from it), verified here to produce 193 clusters of exactly two dates with no chaining. The canonical date is the one carrying the **most** concepts, ties to the later — majority rather than the duplicate-ends task's "later always", because no ticker has its newest pivot row inside a cluster, so the anchor argument that decided that task is silent here.

**This snaps the join key only.** The facts frame keeps every concept's date exactly as filed; there is no evidence the filer was wrong. Three keys are snapped together — the pivot, the `revenue_yoy_growth` merge and the `buyback_distortion_flag` merge — because both of the latter are computed on the facts frame's own dates and would otherwise miss for every quarter whose value sits on the straggler date.

### `revenue_yoy_growth`

Computed by `calculate_growth(facts, "Revenue_TTM", 4, ...)` — the same date-based lookup behind the Revenue growth panel and the snapshot's PEG, so the history's `pe_to_revenue_growth` and the snapshot's are built from one number rather than two. It used to be `Revenue_TTM.pct_change(periods=4)`, which counted rows *and* silently forward-filled a missing base (pandas' `fill_method="ffill"` default). It is the only input to `pe_to_revenue_growth` and is not itself emitted.

---

## Masked denominators

Several multiples guard their denominator:

```python
wide["pe_ratio"] = wide["close"] / wide["EPS_TTM_CALC"].where(wide["EPS_TTM_CALC"] > 0)
```

A P/E with negative earnings is not a low P/E — it is undefined. Same for P/B with negative equity, EV/Sales with negative revenue, and a negative dividend (which is physically impossible; it is an artifact of the per-share split problem in `DividendsPerShare_TTM`, which has no absolute equivalent in EDGAR to reconstruct it from).

Masking turns these into `NaN`, which `dropna` then removes. The chart shows a gap instead of a misleading value.

**The snapshot marker and the history line must be the same quantity**, and for `pb_ratio` and
`p_tbv` they were not. `build_snapshot` guarded those two at `MIN_DENOMINATOR_SCALE_RATIO`
(0.01) while `build_valuation_history` guards them at `MIN_VALUATION_DENOMINATOR_SCALE_RATIO`
(0.001), and the snapshot had no positivity mask on the denominator at all. Both are fixed, and
the second was the larger half: **111 of 458 published `p_tbv` markers were negative**, drawn
onto charts whose line is blank at that period.

0.001 is the right constant on the measurement rather than because it is looser. 0.01 is the
*metrics* constant — it also guards ROE, ROTCE and the effective tax rate, and its use here was
inheritance from before the valuation constant existed. And it misclassifies: Cencora reports
$3.05bn of equity against $332.8bn of revenue, 0.92%, for a P/B of 20.0, which is an ordinary
multiple inside the population 0.01 passes (p99 = 29.3). One percent of revenue is inside the
range a thin-equity, high-turnover filer genuinely occupies. After the change one constant
governs valuation multiples in both code paths, and `MIN_DENOMINATOR_SCALE_RATIO` is back to
guarding only the three metrics ratios.

Still outstanding, same class of defect: `pe_ratio` (25), `pfcf_ratio` (40) and `ev_ebitda` (7)
publish negative snapshot markers where the history line is blank.

---

## The snapshot may carry a value forward, and says when it does

`build_snapshot` reads each of its inputs through `get_latest_value`, which returns the newest
row **carrying a value** rather than the newest row, bounded at
`MAX_LATEST_VALUE_AGE_DAYS = 365`. Where a value did not come from the newest period the
snapshot publishes `<field>_age_days` beside it — 37 such rows today, 90 to 365 days old.

Two boundaries worth keeping straight:

- **The age is measured inside the series**, so it says how far back the snapshot had to reach,
  not how old the data is. `days_since_last_filing` and `fundamentals_stale` answer the second
  question and are unaffected.
- **`_revenue_scale` opts out** (`max_value_age_days=None`). It is the scale guard's
  order-of-magnitude reference, and an older year answers "is this denominator 1% of the
  business" as well as the current one — the argument `fill_scale_reference` already makes on
  the history side.

### ...and it now refuses to carry one forward too far

The sentence above says "reads each of its inputs through `get_latest_value`", and that was
never the whole truth: **21 of the snapshot's fields come from `get_latest_row(metrics[...])`
instead**, which takes the newest row of a metric frame with no age test of any kind. That is
the path the AppLovin defect ran through — `metrics["fcf"]` is an inner merge of
`OperatingCashFlow_TTM` and `Capex_TTM`, so when the `Capex` tag stopped in 2023 the frame did
not gain nulls, it *ended*, and the newest row of a frame that ended in 2023 is a 2023 row.

Both paths now pass through `split_stale` against `newest_period(facts)` —
`MAX_LATEST_VALUE_LAG_DAYS`, see MDs/metrics.md for the bound and its evidence. Three things
follow, and they are the whole of the behaviour change:

- **A value more than four quarters behind the ticker's newest period is not published.** 195
  values withheld across 149 of 607 tickers; the oldest was 5,752 days.
- **Its dependents blank with it, for free.** Every ratio here is an expression over
  `snap[...]` columns, so a withheld input propagates as NaN and `long.dropna(subset=["value"])`
  removes it — 451 further values, every one traced to a withheld input, nothing traced to
  anything else. The largest single consequence is `debt` and `cash`: 59 tickers lose `ev` and
  with it `ev_sales`, `ev_ebitda` and `ev_fcf`.
- **Nothing that was published moves.** 0 changed values in the universe-wide diff, and
  `metrics_long`, `valuation_history` and the facts frame are byte-identical. This is a
  publishing rule, not a computation.

`<field>_stale_days` records the lag of a value that was withheld, next to `<field>_age_days`
for one that was carried. Only where a number was actually withheld: a stale row that was null
anyway would have published nothing either way. `_revenue_scale` and the share-count lookup opt
out — the first on the argument above, the second because it already measures lag against the
same reference (`MAX_EDGAR_SHARE_LAG_DAYS`) and has a second source to fall back on, so a guard
there would not blank a field, it would silently switch vendors.

---

## `calculate_peer_band_flags` is anchored on the data, not the run date

Its five-year window used to start at `pd.Timestamp.today()`, so the same cached facts gave
different flags on different days: moving the run date forward a year with nothing else changed
flips 35 of 2,106 flags and drops 16. It now takes `as_of` (`None` keeps today) and windows
through `within_avg_5y_window`, which uses `AVG_5Y_WINDOW` — the same five years the rolling
means use, rather than a second `DateOffset(years=5)` copy of the arithmetic.

This is the **only cross-sectional flag** in the project: it compares a ticker's own five-year
low against its profile peers' **median**, so one ticker gaining an observation moves another
ticker's output. An anchor that drifts with the run date therefore drifts across the universe.

The app cannot pass its own `as_of` through — it reads precomputed frames and its `as_of` is a
chart-window filter — and `build_snapshot_as_of` emits no band flags at all, so no as-of view is
silently current. The parameter exists so that the one place that could emit them has a correct
way to.

---

## `export_for_app`: the frontend's contract

Six parquet frames plus `meta.json`, written to `data/app/`. `MDs/app.md` documents what
each one feeds; two properties belong here, because they are guarantees this function
makes:

**Parquet, not CSV.** `end` has to survive as a real datetime — `build_valuation` and
`build_ticker_comparison` compare it against a `pd.Timestamp`, and a CSV round-trip would
hand them a string.

**Atomic writes, and `meta.json` last.** Each frame goes to a `.tmp` file and is
`os.replace`d over the target, which is atomic on one filesystem, so a frontend reading
during the nightly run sees the old file or the new one and never half of either.
`meta.json` is written after all six, so its presence means every frame is already in
place. `APP_EXPORT_SCHEMA` is bumped when the set of files changes.

`facts_growth` and `facts_full` are both written from the same source frame on purpose:
the charts read the narrow one (three concepts, about a tenth of the rows), the data tab
reads the full one, where a raw concept next to its own `_TTM` derivation is the point.

Both are written **after** `filter_hidden_rows`, so a concept a ticker's profile hides is
absent from the export rather than hidden at render time. That is visible in the app — see
`MDs/app.md`'s limitations.

---

## What this tool does not do

**Forward-looking metrics.** Forward P/E requires analyst estimates. EDGAR has none, and yfinance's `forwardPE` is unreliable.

**Non-GAAP figures.** Companies define their own adjustments, and they appear only in 8-K press releases, not in structured XBRL.

**Financial companies.** Banks have no operating income, no capex, and no long-term debt in the sense these metrics assume. Roughly half the charts come out empty for JPM, and that is the correct outcome — not a bug to be fixed. Financials need a different metric set (net interest margin, tier-1 capital, loan loss provisions) that this tool does not implement.