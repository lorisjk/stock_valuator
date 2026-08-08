# Product-Side Cleanup — `ttm_source` Rendering, `write_charts` Flag, `p_ffo` Snapshot

Three independent items, implemented and verified separately. None touches the parse layer; the
data in `data/` and `data/app/` was read, never rewritten — every run below wrote into a temporary
directory.

**One document named in the brief does not exist:** `app_refinements_report.md` is not in the
repository (the report set is `ttm_window_report.md`, `decumulation_window_report.md`,
`duplicate_period_ends_report.md`, `rolling_window_report.md`, `split_normalisation_report.md`,
`scale_outlier_audit_report.md`, `directional_scale_detection_report.md`,
`sidebar_encyclopedia_report.md`, `tag_investigation_stock_sbc_report.md`,
`full_refresh_report.md`). Part 3 required re-measuring its claim anyway, which is what §3.1 does.

---

## 1. Part 1 — `ttm_source` in the data tab

### 1.1 What was decided, and the measurement behind it

**Marked per column, not per cell.** The pivot is rows = period, columns = concept, and the data
tab was already flagged as tight at ~37 columns, so the choice was between a per-cell suffix, a
per-column marker, a separate legend, and a toggle.

The deciding measurement is that **provenance does not vary within a column**:

```
(ticker, concept) series in facts_full.parquet carrying a ttm_source :  5,836
series carrying BOTH labels                                          :      0
annual-cadence series                                                :     48   over 47 tickers
```

That is not luck. `calculate_ttm` and `parse_edgar.annual_ttm_values` are disjoint by construction —
the annual path runs *only* where the quarterly extraction produced nothing — so the label is a
property of the series. A per-cell suffix would therefore pay readability in every row of the table
to express something that never changes down a column.

So: **a one-character marker on the column header, plus a legend naming the concepts in full.** The
marker costs no column and no row; the legend carries the explanation, which is the part that
actually needs words.

```
ᵃ  annual cadence
ᵐ  mixed cadence   (detected, not assumed away -- currently 0 series)
```

The mixed case is computed rather than ruled out. A marker that quietly rounded a mixed series to
"annual" would assert something the pipeline has not established, so `cadence_markers` returns the
mixed set separately and labels it differently. Injecting one synthetic `quarterly_rolling` row into
DAL's annual series flips its marker from `ᵃ` to `ᵐ` — verified.

**Requirement 2 — nothing rendered where there is no value.** A column marker cannot assert a
provenance for an empty cell, and the underlying invariant holds anyway: **0 rows in the whole
exported frame carry a `ttm_source` without a value.**

**Requirement 3 — derived TTMs stay unmarked.** `FCF_TTM`, `EBITDA_TTM`, `FFO_TTM` and
`EPS_TTM_CALC` are added downstream by `add_as_concept` and carry no source (verified: their
distinct `ttm_source` set is empty for all four). Deriving a marker for them would mean inventing a
claim the pipeline never made — their inputs are in the same table, and the legend says so
explicitly rather than leaving the reader to wonder why those columns are bare.

**The markers live in the display frame only.** Downloads and the copy block are built from the
numeric frame, so the CSV header still reads `ShareBasedCompensation_TTM` — verified.

### 1.2 The named verification ticker does not work, and that is a finding

The brief asks to verify against **NEE `ShareBasedCompensation_TTM` (18 annual values)**. In the
current export NEE has **zero** rows for that concept:

```
is_hidden("NEE", "ShareBasedCompensation_TTM")  ->  True      (profile: utilities)
NEE ttm_source counts: None 1,276 · quarterly_rolling 588 · annual_fact 0
```

The TTM report measured `ttm_source` on the **unfiltered** facts frame; `facts_full.parquet` is
written after `filter_hidden_rows`, and the `utilities` profile hides share-based compensation. So
NEE's annual series exists in the pipeline and can never appear in the data tab. Not a regression —
a mismatch between where the count was taken and where the feature renders.

Substitutes with the same shape, all present in the export:

| ticker | annual-cadence concept | values |
|---|---|---:|
| L | `DepreciationAndAmortization_TTM` | 19 |
| DAL, COP, OXY | `ShareBasedCompensation_TTM` | 18 |
| MCD | `PretaxIncome_TTM` | 18 |
| AFL | `DepreciationAndAmortization_TTM` | 18 |

### 1.3 The two look different — verified

**DAL** (annual cadence) and **AAPL** (purely rolling), same concept, six most recent periods:

```
DAL                                                              AAPL
           Revenue  Revenue_TTM  ShareBasedComp._TTM ᵃ                       ShareBasedComp._TTM
2026-06-30  19.76B       68.29B                                  2026-06-27               13.71B
2026-03-31  15.85B       65.18B                                  2026-03-28               13.47B
2025-12-31  16.00B       63.36B              313.00M             2025-12-27               13.17B
2025-09-30  16.67B       62.92B                                  2025-09-27               12.86B
2025-06-30  16.65B       61.92B                                  2025-06-28               12.54B
2025-03-31  14.04B       61.93B                                  2025-03-29               12.24B
```

One point a year with a marker, versus a value every quarter with none. AAPL's `cadence_markers`
returns `{}` and no legend is rendered.

The legend, as it appears under DAL's table:

> ᵃ **annual cadence** — `ShareBasedCompensation_TTM`. This filer discloses the item once a year, so
> the value is the 12-month figure taken as filed rather than four quarters summed. One point a year
> is complete coverage of what was published, not a gap.
> Unmarked `_TTM` columns are summed from four quarters. `FCF_TTM`, `EBITDA_TTM`, `FFO_TTM` and
> `EPS_TTM_CALC` are built from other columns further down the pipeline and carry no provenance of
> their own — theirs is their inputs', visible in this same table.

### 1.4 The encyclopedia entry

A bullet added to `GROWTH_MECHANISM_NOTE`, next to the existing "TTM versus quarterly" one, in the
same "what the code does" register as the rest: what an annual-cadence series is, why its growth
panel shows one value a year, that this is complete coverage rather than missing data, and that the
`ttm_source` column records which path produced each value and the two never mix.

### 1.5 Implemented

`app.py`: `cadence_markers()` (new), `column_markers` / `marker_legend` parameters on
`render_data_section`, and the facts section in `render_data_tab` wired to them. `config.py`: the
encyclopedia bullet. No change to `format_for_display`, `pivot_ticker`, or the other three data
sections.

---

## 2. Part 2 — `write_charts`

### 2.1 The decisions

**1. Defaults, split by entry point.**

```python
def main(write_charts: bool = True,  write_html: bool = False)          # local dev run
def run_full_refresh(write_charts: bool = False, write_html: bool = False)   # nightly
```

The two entry points have different jobs, so one default does not fit both. `run_full_refresh`
exists to feed the app, and the app renders from `data/app/*.parquet` — it never opens a chart file.
`main()` runs on `config.TICKERS` (two tickers), writes the human-facing CSVs, and its charts are
the reason a developer runs it at all. So the expensive common case is cheap by default, and the
case where someone wants to look at a chart is cheap to ask for.

A parameter rather than a commented-out line, per the brief: the previous state (`#fig.write_html(...)`)
is exactly the thing that gets lost.

**2. HTML and JSON separately, with different defaults.** They are not the same artifact. Measured
on real charts:

| | per chart | 1,503 charts |
|---|---:|---:|
| JSON | 16–53 KB (mean 32.3 KB, measured over the 1,503 on disk) | **48.6 MB** |
| HTML | 4.87–4.91 MB (mean 4.89 MB, over the 24 on disk) | **~7.3 GB** |

ratio **155×** on the three-ticker run (0.28 MB JSON vs 43.99 MB HTML for nine charts). The JSON is
the interface — `from_json` reads it back, `fig.layout.meta` survives it, and it is what a JS
frontend would consume. The HTML is a standalone viewer with plotly.js inlined. So JSON is
unconditional whenever charts are written at all, and HTML is a separate opt-in.

**How the "both files or neither" guarantee stays intact.** It is a statement about *one chart's
pair*, and it lives in `_write_figure`, which is the only place either file is written: one call
derives both names from one stem and decides both. With `write_html=True` both are written; with
`write_html=False` the pair is "JSON only" by configuration, not by a half-finished write. Verified:
in the HTML run, 9 JSON stems and 9 HTML stems with **no unpaired stem**, and with HTML off no
`.html` file is created (asserted per chart).

*Pre-existing, and not touched:* `figures/` currently holds **24 stale `.html` files** (8 tickers,
from 2026-08-06, when the call was still uncommented) and **995 `.png` files** from an older output
format, alongside 1,503 current `.json`. `AAPL_fundamentals` is `.html` from Aug 6, `.json` from Aug 7,
`.png` from Jul 29. Deleting files as a side effect of a run is worse than the stale files, so the
change does not do it — reported here instead.

**3. The run report says "skipped", not "0.0s".** `_timing_summary({})` returns zeros, and a Phase 3
line reading "total 0.0s across 0 tickers" says plotting was free rather than that it did not
happen. `write_full_refresh_report` now takes `charts_written` / `html_written`. Both branches,
from real runs:

```
charts on:   - Plot (per ticker, all three charts, JSON only): total 2.7s across 3 tickers,
               average 0.90s/ticker
             - Slowest 10 tickers (plotting): AAPL 1.60s, JPM 0.59s, ...

charts off:  - Plot: **skipped** (`write_charts=False`). No figures were built and no chart files
               were written. Nothing downstream depends on them -- the app renders from
               `data/app/*.parquet`, exported either way. Re-run with
               `run_full_refresh(write_charts=True)` to produce `figures/` again.
```

### 2.2 The export is byte-identical — proved by isolating the flag

The brief's check is that a charts-off run produces the same `data/app/` exports as a charts-on run.
Run naively as two separate `run_full_refresh` calls, **it fails** — and the reason is worth having:

```
two full run_full_refresh runs, 3 tickers, charts on vs off:
  facts_full.parquet         IDENTICAL
  facts_growth.parquet       IDENTICAL
  metrics_long.parquet       IDENTICAL
  universe.parquet           IDENTICAL
  current_snapshot.parquet   DIFFERENT
  valuation_history.parquet  DIFFERENT   (861 of 1,697 rows, all at the last ulp)
```

**The cause is not plotting, it is the price source.** Two consecutive `get_price_history("AAPL")`
calls return closes that are *not bit-identical* — same shape, `max |diff| = 9.155e-05`. Everything
that touches the price history therefore moves in the last decimal between any two runs; everything
that does not (facts, metrics, universe) is stable. `price` itself and all eighteen fundamental
snapshot inputs were identical across the two runs.

So the flag was isolated properly: **one fetch, one calculation, two exports**, differing only in
whether the plot loop ran.

```
plotted      plot 2.48s   9 chart files
not_plotted  plot 0.00s   0 chart files

  current_snapshot.parquet    IDENTICAL
  facts_full.parquet          IDENTICAL
  facts_growth.parquet        IDENTICAL
  metrics_long.parquet        IDENTICAL
  universe.parquet            IDENTICAL
  valuation_history.parquet   IDENTICAL
  meta.json                   IDENTICAL

  every parquet export byte-identical with and without plotting: True
```

And structurally, the plot loop provably reads without writing — hashing the four exported frames
before and after plotting three tickers:

```
metrics_long        unchanged by the plot loop: True
valuation_history   unchanged by the plot loop: True
facts_growth        unchanged by the plot loop: True
current_snapshot    unchanged by the plot loop: True
```

### 2.3 The write path is transparent — chart output unchanged

`build_*(...).to_json()` compared byte-for-byte against the file `plot_*` writes, three tickers
across profiles, both HTML modes:

| ticker | chart | html=False | html=True | JSON bytes | HTML bytes |
|---|---|---|---|---:|---:|
| AAPL | fundamentals | identical | identical | 50,207 | 4,906,037 |
| AAPL | valuation | identical | identical | 23,310 | 4,879,141 |
| AAPL | growth | identical | identical | 35,267 | 4,891,098 |
| O | fundamentals | identical | identical | 21,876 | 4,877,706 |
| O | valuation | identical | identical | 16,432 | 4,872,262 |
| O | growth | identical | identical | 26,558 | 4,882,389 |
| JPM | fundamentals | identical | identical | 52,889 | 4,908,719 |
| JPM | valuation | identical | identical | 15,929 | 4,871,759 |
| JPM | growth | identical | identical | 31,092 | 4,886,922 |

Enabling HTML does not change the JSON. And the `figures.py` diff touches only `_write_figure` and
the three `plot_*` wrappers — **no `build_*` function is modified**, which is what makes the table
above a check on the writer rather than on the builder.

### 2.4 The measured runtime difference

Four measurements, because "how much does this save" has a different answer at each scale, and only
the first is the one the brief is asking about.

**1. Full universe, the project's own instrumentation** (`full_refresh_report.md`, the last real
refresh):

```
Plot:  732.9s across 501 tickers   1.46s/ticker   1,503 files
Total wall clock: 2,118.7s
```

`write_charts=False` removes that phase entirely — **732.9s, 34.6% of the run**, and 48.6 MB of
files that nothing reads.

**2. The flag isolated — one fetch, one calculation, two exports** (§2.2), which is the only
measurement where nothing else varies:

```
plotted        2.48s   9 chart files
not plotted    0.00s   0 chart files
```

**3. End to end, three tickers, real fetch and real cache deletion:** the run report's own Phase 3
line measured 2.7s across 3 tickers, **0.90s/ticker**. The wall clocks (20.1s on, 17.3s off) are
*not* the signal — a three-ticker run is dominated by network fetch, which is why the 2.8s wall-clock
difference understates the per-ticker cost that matters at 501.

**4. Re-measured over the universe on this machine**, plotting all three charts per ticker from the
exported frames (`facts_full` for growth, as the real loop passes):

```
100/501   300s
200/501   596s      ->  2.98s/ticker
```

Stopped at 200 — the rate is linear and the remaining 300 tickers would have added ~15 minutes for
no new information. **2.98s/ticker is roughly twice the reference run's 1.46s**, because this
measurement ran alongside the other verification jobs; it corroborates the direction and the
per-ticker magnitude rather than replacing the reference figure. Extrapolated, plotting the full
universe here costs ~1,490s.

**With HTML on**, add ~4.89 MB per chart: ~7.3 GB and the write time for it, which is why it has its
own switch rather than riding on `write_charts`.

---

## 3. Part 3 — `p_ffo` in `build_snapshot`

### 3.1 The gap, re-measured against the current registry

Not assumed from the earlier report — recounted against `config.METRICS` and the current
`data/app/` exports:

```
valuation-chart metrics in the registry: 13
present in valuation_history          : 13
present in current_snapshot           : 10
in the history but not the snapshot   : ev_fcf, p_ffo, pfcf_ex_sbc
```

The three named in the brief are still exactly the three. A REIT had a current-value marker on
`p_tbv`, `ev_sales` and `dividend_yield` and none on the multiple its whole profile is built around.

### 3.2 Why it was absent: nothing was missing

`FFO_TTM` is added to the facts frame by `add_derived_concepts`, which runs long before
`build_snapshot`, and it is present for **29 of 29 REITs**. `build_valuation_history` reads it out of
that same frame. So the input was there and **`p_ffo` was simply never added** — no finding, no
approximation needed. The same holds for the other two: `ev_fcf` needs `ev` and `fcf_ttm`, both
already in the snapshot; `pfcf_ex_sbc` needs `ShareBasedCompensation_TTM`, present for 390 tickers.

**Verdict on all three: buildable, and all three implemented.**

### 3.3 Implemented — the same expression as the history

```python
    snap["p_ffo"] = apply_denominator_scale_guard(
        snap["market_cap"] / snap["ffo_ttm"].where(snap["ffo_ttm"] > 0),
        snap["ffo_ttm"], snap["revenue_ttm"], MIN_VALUATION_DENOMINATOR_SCALE_RATIO
    )
```

Same positivity mask, same scale guard against `Revenue_TTM` at the same
`MIN_VALUATION_DENOMINATOR_SCALE_RATIO` the history uses — so the marker and the line it sits on are
the same quantity at a newer price, which is the point. `ev_fcf` and `pfcf_ex_sbc` mirror their
history expressions the same way, including `owner_fcf = FCF_TTM − ShareBasedCompensation_TTM`.

**The `fillna(0)` dependency, per the brief, not fixed here.** `FFO_TTM` is
`NetIncomeLoss_TTM + DepreciationAndAmortization_TTM − GainLossOnSaleOfProperties_TTM` with
`fillna(0)` on the gains term, in `add_derived_concepts`. The snapshot reads the *same column* rather
than recomputing, so the two cannot diverge on it — and when that expression is fixed, both move
together, which is the property worth having.

The two helper columns `ffo_ttm` and `sbc_ttm` are dropped before the melt, so the change adds
exactly three concepts and no new raw-input concepts that would need registry visibility entries of
their own.

### 3.4 Verification on real REITs

```
overlap after the change: 13 of 13   still missing: none
p_ffo in the snapshot: 27 tickers, all REITs.  Non-REITs with a p_ffo: 0.
```

Hand-computed from the snapshot's own inputs, no pipeline arithmetic reused:

```
AMT: 172.54 x 465,960,048 shares = 80,396,746,682 market cap
     FFO_TTM 4,967,600,000 (end 2026-03-31)  ->  16.1842      snapshot 16.1842   match
O:    62.51 x 946,202,000 shares = 59,147,087,020 market cap
     FFO_TTM 3,619,506,000 (end 2026-06-30)  ->  16.3412      snapshot 16.3412   match
```

Consistent with the newest history point given the newer price:

| ticker | history `p_ffo` | at | snapshot `p_ffo` | ratio |
|---|---:|---|---:|---:|
| AMT | 15.9060 | 2026-03-31 | 16.1842 | 1.017 |
| O | 15.9326 | 2026-06-30 | 16.3412 | 1.026 |
| PLD | 19.5650 | 2026-03-31 | 20.7390 | 1.060 |
| EQIX | 27.9520 | 2026-06-30 | 27.8270 | 0.996 |
| SPG | 9.5970 | 2026-03-31 | 11.5700 | 1.206 |

Both sides divide by the same `FFO_TTM`, so the ratio *is* the market-cap ratio between the period
end and the run date — 1.017 for AMT, 1.026 for O. The wider ones (SPG 1.206, WELL 1.193) sit on a
2026-03-31 period end, four months of price movement away.

**Two REITs correctly get no marker, and both reasons are real:**

- **ARE** — latest `FFO_TTM` is **negative** (−381.9m at 2026-06-30, after positive 823.2m at
  2025-09-30). `where(FFO_TTM > 0)` blanks it, exactly as the history does: its `p_ffo` line also
  stops at 2025-09-30.
- **AVB** — latest `FFO_TTM` rows are **NaN** (2026-03-31, 2026-06-30), so `get_latest_value` picks a
  row that has no value. Its last good FFO is 2025-09-30. See §5 — this is a general property of
  `get_latest_value`, not something p_ffo introduces.

### 3.5 The marker renders

`_snapshot_point` is generic — it looks up `(ticker, concept)` — so adding the concept is all that
was needed. Per-chart marker counts, before and after:

```
O     4 -> 5        AMT   3 -> 5        PLD   4 -> 5
AAPL  7 -> 9        JPM   5 -> 5   (its profile hides all three)
```

And on the `p_ffo` panel itself, the two traces:

```
trace 'p_ffo'                     lines+markers  n=20  2021-09-30 .. 2026-06-30  y[-1]=15.9326
trace 'Snapshot (current value)'  markers        n=1   2026-08-08               y=16.3412
```

`figures._snapshot_point`'s docstring said "build_snapshot computes 10 of the 13 valuation panels --
ev_fcf, pfcf_ex_sbc and p_ffo simply have none". That is now false, so it was corrected — the only
other `figures.py` change besides Part 2's write path.

---

## 4. Verification, all parts

### 4.1 Scope of the diffs

```
app.py     +81 / -4      Part 1 only
config.py  +11 / -0      Part 1 only -- the encyclopedia bullet, nothing else
figures.py +24 / -7      Part 2's write path (4 functions) + one docstring Part 3 falsified
main.py    +93 / -22     Parts 2 and 3
```

`figures.py`'s diff touches `_write_figure` and the three `plot_*` wrappers and nothing else — **no
`build_*` function is modified**, which is what makes §2.3's byte-comparison a check on the writer.
`config.py`'s diff is eleven added lines inside `GROWTH_MECHANISM_NOTE`.

### 4.2 Both entry points run end to end

```
main()                      7.8s   2 tickers   4 CSVs   6 chart files
main(write_charts=False)    4.4s   2 tickers   4 CSVs   0 chart files

run_full_refresh(write_charts=True)                 20.1s   9 chart files (.json)
run_full_refresh(write_charts=False)                17.3s   0 chart files
run_full_refresh(write_charts=True, write_html=True) 19.3s  18 files (9 .json + 9 .html), 44.3 MB
```

**Deviations, stated plainly.** `run_full_refresh` was run on **three tickers across profiles**
(AAPL default, O reit, JPM financial), not on the 501-ticker universe, and `DATA_DIR`, `FIGURE_DIR`,
the app-export directory and the run-report path were redirected into a temporary directory. The
cache deletion and the EDGAR/yfinance refetch were **real** for those three — `cache/AAPL_*`,
`cache/O_*` and `cache/JPM_*` were deleted and refetched from SEC, which is the one side effect
outside the scratchpad; the rest of the 501-ticker cache is untouched. **No 501-ticker refresh was
run**, so `data/`, `figures/` and `full_refresh_report.md` still carry their 2026-08-07 timestamps,
and the three-ticker wall clocks above are dominated by network fetch — the plotting cost is the
per-ticker figure in §2.4, not the difference between those wall clocks.

### 4.3 `app.py`'s import direction

`app.main()` runs to completion in bare mode, as does `render_data_tab` for DAL (annual cadence),
O (REIT) and AAPL.

**One correction to the premise:** app.py does not import `main.py` — that invariant holds — but it
does pull in one pipeline module transitively. `figures.py:13` reads
`from metrics import harmonic_mean`, so `app -> figures -> metrics`. This is **pre-existing** and
untouched by this task; `metrics.py` is pure arithmetic with no I/O and no network, so the property
that matters (the app computes nothing and reaches nothing) is intact, but "imports no pipeline
module" is not literally true and should not be repeated as though it were.

### 4.4 What could not be verified without a browser

Everything below was checked at the data and figure-object level, not visually:

- **How the `ᵃ` marker looks in the rendered `st.dataframe` header** — that the string reaches the
  header is verified; column width, truncation and whether the superscript is legible at the default
  font are not.
- **That the legend caption sits where intended** relative to the table, and reads well at the
  default width.
- **The rendered colour and shape of the new `p_ffo` snapshot marker.** The trace exists with the
  right name, x and y (§3.5) and uses the same code path as the ten markers that already rendered,
  so the styling is shared rather than new — but it was not looked at.
- **Any Streamlit layout interaction** — the "Show all periods" checkbox and the Raw/Derived radio
  were exercised through their code paths, not through the widgets.

---

## 5. Not fixed, with reasons

**`get_latest_value` returns the newest *row*, even when that row has no value.** AVB's `FFO_TTM`
has NaN at 2026-03-31 and 2026-06-30 and a real value at 2025-09-30; the snapshot therefore has no
`p_ffo` for it, although a value exists three quarters back. This is general — every snapshot input
goes through `get_latest_value` — and the fix is a decision about how stale a snapshot input may be,
which the staleness fields already partly address. Out of scope here, and p_ffo did not introduce it.

**The snapshot and the history use different scale-guard constants for `pb_ratio` and `p_tbv`.**
`build_snapshot` guards those two at `MIN_DENOMINATOR_SCALE_RATIO = 0.01`; `build_valuation_history`
guards the same two at `MIN_VALUATION_DENOMINATOR_SCALE_RATIO = 0.001`, ten times looser. So for
those two the marker and the line it sits on are not strictly the same quantity. The three concepts
added here deliberately use the **history's** constant, which is the side that makes marker and line
agree. Reconciling the two existing ones is a separate change with its own diff.

**`apply_denominator_scale_guard` treats a missing scale reference as a pass** (`too_small &
scale_reference.notna()`), so a ticker with no `Revenue_TTM` is never guarded. Recorded in earlier
reports; the new concepts inherit it because they must match the history.

**The `fillna(0)` on the FFO gains term** — explicitly excluded by the brief, and the implementation
is arranged so that fixing it later moves the snapshot and the history together.

**24 stale `.html` and 995 stale `.png` files in `figures/`.** Left in place: deleting files as a
side effect of a pipeline run is worse than the staleness. `AAPL_fundamentals` currently has an
`.html` from 2026-08-06, a `.json` from 2026-08-07 and a `.png` from 2026-07-29.

**The pipeline is not bit-reproducible across runs**, because `get_price_history` is not: two
consecutive calls returned AAPL closes differing by up to 9.155e-05. Everything price-derived moves
in the last decimal between runs. Found while verifying Part 2; not caused by it, and not this
task's business — but it means "byte-identical exports" is only ever testable within one fetch.

**`app.py` reaches `metrics` through `figures`** (§4.3). Pre-existing.

**Everything outside the three parts**, per the brief: no parse-layer change, no coverage-flag
semantics, no new metrics, no chart rendering change beyond the write path and one corrected
docstring.
