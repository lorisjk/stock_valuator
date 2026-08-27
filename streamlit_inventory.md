# Streamlit app — feature inventory for the React rebuild

Read off `app.py` (1,127 lines), `figures.py` (1,158) and `config.py` as they stand at commit
`1ef11dd`, and measured against the `data/app/` export of 2026-08-21 (610 tickers requested, 609
with data, `EA` without). Nothing in this document was changed to produce it.

**Working-tree note.** `git status` was not clean when this started: the 2026-08-21 export is
staged (`data/app/*`), `task_new.md` is modified, and `frontend/public/universe.json` is untracked.
Those are the operator's, left alone. This task adds exactly one file — this one.

---

## 1. The data contract

### 1.1 The seven files

Every frame is **long** (`ticker, end, concept, value`) except `universe`. There is no wide table
anywhere; the app pivots on demand in `pivot_ticker` (app.py:176).

| file | rows | cols | parquet | as JSON | ×
|---|---:|---:|---:|---:|---:|
| `facts_full.parquet` | 1,152,894 | 7 | 14.1 MB | **194.6 MB** | 13.8 |
| `metrics_long.parquet` | 571,114 | 4 | 3.6 MB | 55.2 MB | 15.2 |
| `valuation_history.parquet` | 352,639 | 4 | 2.5 MB | 32.4 MB | 13.1 |
| `facts_growth.parquet` | 242,180 | 4 | 1.9 MB | 24.3 MB | 12.5 |
| `current_snapshot.parquet` | 25,202 | 4 | 0.18 MB | 2.4 MB | 13.5 |
| `universe.parquet` | 609 | 5 | 0.01 MB | 0.1 MB | 4.1 |
| `meta.json` | — | — | 468 B | 468 B | 1.0 |
| **total** | | | **22.3 MB** | **309 MB** | **13.9** |

Columns and dtypes:

| file | columns |
|---|---|
| `facts_full` | `ticker` str, `concept` str, `end` datetime64[ns], `value` float64, **`ttm_source`** str/None, **`ffo_gains_source`** str/None, `yoy_growth` float64 |
| `metrics_long` | `ticker`, `end`, `value`, `concept` |
| `valuation_history` | `ticker`, `end`, `concept`, `value` |
| `facts_growth` | `ticker`, `concept`, `end`, **`yoy_growth`** (no `value`) |
| `current_snapshot` | `ticker`, `end`, `concept`, `value` — one constant `end` per ticker |
| `universe` | `ticker`, `profile`, `n_metrics`, `n_valuation`, `n_growth` |
| `meta.json` | `schema`, `run_start`, `exported_at`, `period`, `tickers_requested`, `tickers_with_data`, `tickers_without_data[]`, `rows{}` |

**Only 2 of `universe`'s 5 columns are read** (`ticker`, `profile`, app.py:851–852).
`n_metrics` / `n_valuation` / `n_growth` are exported and never used by the app.

### 1.2 Which view needs which file

| file | used by | loaded |
|---|---|---|
| `universe.parquet` | sidebar ticker list + profile labels; comparison ticker list | **eagerly, every run** (app.py:849) |
| `meta.json` | sidebar freshness caption | **eagerly, every run** (app.py:848) |
| `metrics_long` | Fundamentals tab (chart), Data tab (Calculated metrics + Quality flags), Comparison | on tab render |
| `valuation_history` | Valuation tab, Data tab, Comparison | on tab render |
| `facts_growth` | Growth tab, Comparison | on tab render |
| `facts_full` | **Raw Facts tab, Data tab, and `share_history_absent()`** | on tab render |
| `current_snapshot` | Valuation tab (green marker), Data tab | on tab render |

`facts_full` is the expensive one and it is reached from three places, one of which
(`share_history_absent`, app.py:1049) loads the whole 14 MB frame to answer a yes/no question
about one ticker's `SharesOutstanding`.

### 1.3 What JSON transport implies

**309 MB is not shippable.** Two consequences:

1. **Per-ticker slicing is mandatory.** Measured for AAPL:

   | slice | rows | JSON |
   |---|---:|---:|
   | `facts_full` | 2,357 | **406 kB** |
   | `metrics_long` | 1,209 | 118 kB |
   | `valuation_history` | 750 | 70 kB |
   | `facts_growth` | 505 | 52 kB |
   | `current_snapshot` | 46 | 4.4 kB |

   A ticker's complete payload is **~650 kB of JSON**, ~120 kB gzipped. That is a per-ticker
   fetch, not a bundle. The scaffold already does this — `frontend/public/AAPL_valuation.json`
   and friends exist.

2. **The Comparison tab breaks the per-ticker model.** It needs one concept across N tickers.
   Slicing by ticker means N fetches; slicing by concept means a second export axis. A
   concept-major file for the 13 valuation concepts across 609 tickers is ~32 MB of JSON total,
   i.e. ~2.5 MB per concept — fetchable per concept, not as a whole.

**Recommended export shape** (not built, not requested):
`{ticker}/facts.json`, `{ticker}/metrics.json`, `{ticker}/valuation.json`, `{ticker}/growth.json`,
`{ticker}/snapshot.json`, plus `universe.json`, `meta.json`, `registry.json` (§1.5) and
`by-concept/{concept}.json` for comparison.

### 1.4 Caching

Exactly two functions are cached, both `@st.cache_data(show_spinner=False)`:
`load_frame(name)` (app.py:103) and `load_meta()` (app.py:108). `read_content()` is
**deliberately not** cached (app.py:112) so hand-edited content files take effect on reload.

**Figures are never cached** — app.py:92 states the reason: a cached figure would outlive the
widget state that produced it. A rebuild caching chart output must key it on every control value.

### 1.5 What is *not* in `data/app/` and is still required

The app reads `config.py` directly at runtime. A browser cannot. This is the part of the contract
that has no exported form today:

| needed | source | used for |
|---|---|---|
| `METRICS` registry — id, label, chart, `percent`, `ref_line`, `value_column`, `description`, `formula`, `documented`, `harmonic` | `config.METRICS` | every picker label, y-axis label, reference line, percent formatting, the whole encyclopedia |
| `get_plottable_metrics(chart, ticker)` | config | which metrics a ticker is offered — see §3.1 |
| `profile_visibility()` | config | Profile coverage page (24 profiles × 52 metrics matrix) |
| `get_concept_candidates(ticker)` | config | raw-vs-derived split in the Data tab, Raw Facts concept list |
| `is_hidden(ticker, metric)` | config | authoritative visibility filter |
| `GROWTH_MECHANISM_NOTE`, `VALUATION_MECHANISM_NOTE` | config | encyclopedia section prose |
| `HARMONIC_MEAN_CONCEPTS` | config | which mean the valuation panel draws |
| `QUARTERLY_COUNTERPART` | config | the dual-trace treatment (§4.2) |
| `content/about.md`, `content/update_notice.md` | files | About page, dismissible notice |

**This is the single biggest gap in the current export.** It is small — a few hundred kB of JSON —
but nothing produces it today.

---

## 2. Feature catalogue

### 2.1 Shell

| element | source | behaviour |
|---|---|---|
| page config | app.py:816 | title "Kyhestlo", icon ▪, `layout="wide"` |
| missing-data guard | app.py:819–833 | if any of the 7 files is absent, render an error naming them plus the re-run command, then `st.stop()`. **Nothing else renders.** |
| update notice | app.py:786–814 | reads `content/update_notice.md`, strips HTML comments; if the result is empty → draws **nothing** (not an empty box). Bordered, left-aligned container with a **Dismiss** button whose `on_click` callback sets `st.session_state["update_notice_dismissed"]`. Lifetime = browser session. |
| intro caption | app.py:842 | one fixed sentence about the pipeline |
| view radio | app.py:857 | Analysis / Metric encyclopedia / Profile coverage / About |

The **Dismiss** button's `on_click` is load-bearing and documented at app.py:769: Streamlit runs
callbacks *before* the script body re-runs, so `if st.button(...)` would leave the notice on
screen until an unrelated rerun. A React rebuild has no equivalent problem — this is Streamlit
plumbing, not a feature.

### 2.2 Sidebar

| control | widget | default | notes |
|---|---|---|---|
| freshness | caption | — | `run_start[:10]`, `tickers_with_data / tickers_requested`, `period`; plus a second line listing `tickers_without_data` **only when non-empty** (app.py:628) |
| View | `st.radio` | Analysis | |
| Ticker | `st.selectbox` | first in `universe` | label `"{ticker} — {profile}"` |
| profile caption | caption | — | points at the Profile coverage page |
| "Use an as-of date for valuation" | `st.checkbox` | **False** | |
| As of | `st.date_input` | today | only shown when the checkbox is on |

On the three reference views the ticker controls are **absent by design** (app.py:872) — those
pages are ticker-independent and a visible selector would imply otherwise.

### 2.3 Analysis tabs

Tab order in `st.tabs` (app.py:857): **Data, Raw Facts, Growth (YoY), Fundamentals, Valuation,
Comparison**. The `with` blocks appear in a different order in the source; only the list decides.

#### Data tab — `render_data_tab` (app.py:545)

Five sections, in pipeline order. Two shared controls at the top:

| control | widget | default |
|---|---|---|
| Show all periods | `st.checkbox` | False → 16 periods (`DEFAULT_TABLE_PERIODS`) |
| Facts | `st.radio` horizontal | **All** / Raw only / Derived only |

| section | frame | notes |
|---|---|---|
| Raw & derived facts | `facts_full` | columns ordered by `order_fact_columns` — grouped by base concept, raw before its derivations. Cadence markers ᵃ/ᵐ on column headers (§2.6) |
| Calculated metrics | `metrics_long` | quality-flag columns removed |
| Quality flags | `metrics_long` | own presentation: per flag, `raised` / `periods evaluated` / `most recent`; per-period values in an expander |
| Valuation history | `valuation_history` | |
| Current snapshot | `current_snapshot` | rendered as concept/value list, **not pivoted** — one constant `end`, so the slice already *is* the transposed view |

Every section (`render_data_section`, app.py:394) offers:
- a caption `"{n} of {N} periods · {c} concepts"`, plus **`"· {k} null in every period shown — kept on purpose, an empty column is a finding"`** when any column is all-null;
- **Download CSV** — `{ticker}_{slug}.csv`, full precision, from the numeric frame;
- **Copy table** expander — `st.code` block of the newest **8** periods (`DEFAULT_COPY_PERIODS`), with its character count in the expander label.

Empty frame → `st.info("No rows for this ticker in this frame.")`.

#### Raw Facts tab (app.py:1105)

| control | widget | default |
|---|---|---|
| Include derived concepts (_TTM, _QUARTERLY, …) | `st.checkbox` | False |
| Concepts | `st.multiselect` | `["Revenue","NetIncomeLoss","Assets","StockholdersEquity"]` ∩ available |
| Window (years) | `st.slider` 1–15 | **15** |

Options from `figures.available_raw_concepts(ticker, facts_full, show_derived)` — concepts that
actually have a non-null value for this ticker; when `show_derived` is off it intersects with
`get_concept_candidates(ticker)`. Draws `go.Bar`, one panel per concept.

#### Fundamentals / Growth / Valuation

| | Fundamentals | Growth | Valuation |
|---|---|---|---|
| picker | `st.multiselect` "Metrics" | "Concepts" | "Multiples" |
| ids from | `get_plottable_metrics("fundamentals", ticker)` | `("growth", ticker)` | `("valuation", ticker)` |
| default | `revenue_yoy_growth` | **`Revenue`** — see §2.7 | `pe_ratio` |
| slider | 1–15, default **15** | 1–15, **15** | 1–15, **5** |
| builder | `build_fundamentals` | `build_growth` | `build_valuation` |
| extra args | — | `growth_column="yoy_growth"` | `as_of`, `snapshot`, `mask_outliers` |
| empty message | "Nothing selected, or no data for the selected metrics." | "Nothing selected, or no growth data for this ticker." | "Nothing selected, or no valuation data for this ticker." |

Valuation additionally has:

- **Hide extreme values** (`st.toggle`) — present **only when `figures.outlier_report` returns something** for the current selection and window. A toggle on a clean chart teaches the reader to ignore it (app.py:933).
- **the empty-panel notice** (app.py:963) — `st.info` naming the selected multiples with no value in the window, plus a conditional clause when the ticker has no `SharesOutstanding` at all.
- **the outlier caption** — either "Extreme values present in: …" or, when masking, "**Hidden:** … **The mean lines are unchanged**".
- **the outlier expander** — every hidden value with its `x median` ratio.
- **a fixed caption** explaining the green circle.

#### Comparison tab (app.py:1020)

| control | widget | default |
|---|---|---|
| Metric | `st.selectbox` | first option; labels prefixed `"Fundamentals: "` / `"Growth (YoY): "` / `"Valuation: "` |
| Tickers | `st.multiselect` | first **3** of the universe (`SUGGESTED_MAX_COMPARISON_TICKERS`) |
| Window (years) | `st.slider` 1–15 | **15** |
| Hide extreme values | `st.toggle` | only when `comparison_outlier_report` is non-empty |

Note the metric options come from `config.get_plottable_metrics(chart)` **without a ticker**
(app.py:1024) — the full registry, unfiltered. Per-ticker filtering happens later, inside
`_comparison_selection`, as exclusions.

Exclusions render as `st.warning` per dropped ticker. `figures.py` supplies the reason
(`"for profile 'X' not shown"` or `"No Data"`); **app.py rewrites `"No Data"`** into "no values in
this window" plus the share-history clause, so the two tabs agree (app.py:1065).

### 2.4 Reference views

**Metric encyclopedia** (app.py:632) — a `st.text_input` filter (matches id, label, description,
formula, case-insensitive), then three tabs (Fundamentals / Valuation / Growth) driven by
`metric.chart`, so a new registry entry appears without editing the function. Growth and Valuation
sections print `GROWTH_MECHANISM_NOTE` / `VALUATION_MECHANISM_NOTE` first. Undocumented metrics
raise a `st.warning` listing them, and each undocumented entry shows "Not documented yet".

**Profile coverage** (app.py:676) — a profile `st.selectbox` (default `standard`), then per chart
a "Shown / Hidden for this profile" list, then a **full matrix** of 52 metrics × 24 profiles with
✓/· and a `profiles` count column.

**About** (app.py:745) — `content/about.md`, split on `##` headings by `split_sections`. The
section titled **`disclaimer`** is rendered as `st.warning`; everything else as markdown. A
missing file is a `st.warning` (unlike the notice, this *is* an error state).

### 2.5 Downloads and copy blocks

| where | file name | contents |
|---|---|---|
| each data section | `{ticker}_facts.csv`, `_metrics.csv`, `_valuation.csv` | the **shown** periods, full precision |
| flags expander | `{ticker}_flags.csv` | shown periods |
| snapshot | `{ticker}_snapshot.csv` | concept/value |

Copy blocks are `st.code` inside an expander, 8 periods, produced from the **numeric** frame via
`to_csv_text` — never from the display strings.

### 2.6 Provenance markers, flags, staleness

- **`ttm_source`** → `cadence_markers` (app.py:255) marks a *column* ᵃ (annual cadence) or ᵐ (mixed) and appends a legend explaining both. Per column, not per cell — the docstring records that 0 of 5,836 exported series carry both labels, so provenance is a property of the series.
- **`ffo_gains_source`** — present in `facts_full` and **never read by app.py**. Exported, unused. (Finding, not fixed.)
- **quality flags** — identified name-based in app.py by `is_quality_flag`: suffix `_flag`, plus the explicit pair `{"fcf_exceeds_ebitda", "inorganic_contaminated"}` which carry no suffix. app.py:198 records why neither `config.METRICS` nor `quality.py` can supply this test.
- **staleness fields** — `days_since_last_filing`, `days_past_expected_filing` etc. exist in `current_snapshot` and are shown **only** as ordinary rows of the snapshot table. No dedicated treatment, no badge.

### 2.7 Unreachable or unfinished

| item | status |
|---|---|
| `figures.plot_raw_facts` | **no caller anywhere.** It forwards `years` but not `include_derived`, so it could only ever draw non-derived concepts |
| `figures.plot_ticker_comparison` | **no caller** (mentioned only in a docstring) |
| `figures.NOT_NEEDED_ENDING = ["_TTM"]` | defined, referenced nowhere |
| `_symlog` | unpacked from `FUNDAMENTALS_TO_PLOT` in `build_fundamentals` (figures.py:599) and never used |
| `figures.KEEP` | the sentinel default for `width`/`height`; app.py never uses it — every call passes `width=None` |
| `universe.n_metrics/_valuation/_growth` | exported, never read |
| `ffo_gains_source` | exported, never read |
| `plot_fundamentals` / `plot_valuation` / `plot_growth` | **not dead** — `main.py:68` imports them and calls them under `write_charts=True` |

**A real defect, reported not fixed.** The three chart tabs build their default selection with
`in` against a **string literal, not a tuple**:

```python
default = [i for i in ids if i in ("revenue_yoy_growth")]   # app.py:900
default = [i for i in ids if i in ("Revenueyoy_growth")]    # app.py:911
default = [i for i in ids if i in ("pe_ratio")]             # app.py:928
```

`("x")` is `"x"`, so this is substring matching. Measured for AAPL:

| tab | literal | actually selects | a tuple would select |
|---|---|---|---|
| Fundamentals | `"revenue_yoy_growth"` | `['revenue_yoy_growth']` | `['revenue_yoy_growth']` |
| **Growth** | `"Revenueyoy_growth"` | **`['Revenue']`** | `[]` |
| Valuation | `"pe_ratio"` | `['pe_ratio']` | `['pe_ratio']` |

Two work by coincidence — the id is a substring of itself. The Growth default is a **typo**
(`Revenueyoy_growth`, no separator; the real ids are `Revenue`, `NetIncomeLoss`, …) that happens
to substring-match `Revenue`, so the tab opens on the Revenue panel by accident. A rebuild should
use the ids, and should decide deliberately what the Growth default is.

`build_raw_facts` never calls `_annotate_no_data`: a concept whose data lies outside the window
renders as an **empty bar panel with no explanation**, unlike every other chart. Confirmed at
figures.py:1100–1145.

---

## 3. Non-obvious behaviours

### 3.1 `is_hidden` is authoritative, and it is applied twice

`config.get_plottable_metrics(chart, ticker)` narrows the picker; `figures._select_concepts`
(figures.py:79) narrows again inside every builder, applying `is_hidden` to the **catalogue first**
and letting the caller's list only narrow what survives. **An explicit request can never surface a
hidden concept.** Unknown or hidden requests are dropped with a printed note, not refused, because
a UI hands one selection to several tickers.

How much this varies:

| profile | fundamentals | valuation | growth |
|---|---:|---:|---:|
| `standard` (AAPL) | 9 | 9 | 7 |
| `financial` (JPM) | 9 | 5 | 6 |
| `reit` (O) | **4** | 5 | 7 |
| `consumer_staples` (KO) | **13** | 9 | 7 |
| `energy_integrated` (XOM) | 7 | 8 | 7 |
| registry total | 29 | 13 | 10 |

**What a naive rebuild gets wrong:** shipping one metric list for all tickers. A REIT offers 4
fundamentals metrics and a staples company 13, from the same registry of 29. Filtering only in the
picker is also not enough — the builder filters again, so a stale client selection is silently
correct rather than an error.

Panel **order** always follows the catalogue, never the caller's list (figures.py:94). A rebuild
that renders in click order produces a different chart from the same selection.

### 3.2 The id-namespace split

Fundamentals and valuation ids are **metric names** (`pe_ratio`, `operating_margin`). Growth ids
are **XBRL concept names** (`Revenue`, `NetIncomeLoss`, `SharesOutstanding`, `EPS_TTM_CALC`).
`metric_options` is called per chart type for exactly this reason (app.py:165).

Three ids exist in **both** worlds — `Revenue`, `NetIncomeLoss`, `SharesOutstanding` — registered
as growth metrics with `percent=True`, while `facts_full` has columns of the same name holding
absolute dollars. `_percent_applies` (app.py:337) resolves it on **`value_column`**, not on the id
and not on a namespace flag: a growth entry describes `yoy_growth` and never `value`.

**What a naive rebuild gets wrong:** formatting Apple's $109 bn revenue as `10941700000000.00%`.
The docstring records that this exact bug happened. Matching on "id namespace" would not have
fixed it, because the facts frame's columns *are* XBRL names.

### 3.3 The mean line's invariants

Only the **valuation** panels draw a mean (`show_mean=True`, figures.py:753). Harmonic when the
concept is in `HARMONIC_MEAN_CONCEPTS`, arithmetic otherwise; label `Ø (harm.) 29.0` or `Ø 7.8`,
red, top-left of the panel.

Two things are **deliberately excluded**:

1. **The snapshot marker.** Added as a separate trace *after* the mean is computed, and it never enters `filtered` (figures.py:462). Structural, not an ordering convention.
2. **Masked outliers.** `plot_metric` keeps `drawn` and `filtered` apart (figures.py:364): the trace uses `drawn`, the mean uses `filtered`. The comment states the reason — recomputing on the truncated series would compare today's multiple against a benchmark with the bad years removed, "a different and flattering quantity".

**What a naive rebuild gets wrong:** computing the mean from the array it just plotted. That
produces a flattering benchmark exactly when the chart is at its most misleading, and it is
invisible — the number still looks reasonable.

### 3.4 Display formatting versus export precision

Kept strictly apart (app.py:315). `format_for_display` returns a frame of **strings** and is only
ever handed to `st.dataframe`. Downloads and copy blocks are produced from the **numeric** frame
by `to_csv_text`.

The display rule, per column:
1. registry `percent=True` **and** matching `value_column` → `{v*100:.2f}%`;
2. else if the column's own `abs().max() >= 1e4` (`ABSOLUTE_THRESHOLD`) → scaled with T/B/M/K and 2 decimals;
3. else → `{v:.4f}`.

Per **column**, from that column's own maximum, so one column never mixes two treatments. The
snapshot section applies the same rule **per value** (app.py:487) because it has no column to
measure.

Column markers (ᵃ/ᵐ) are applied to the display frame only, so downloads keep clean concept names.

**What a naive rebuild gets wrong:** formatting once and exporting the formatted strings — the
CSV then carries `"1.09B"` instead of `1094170000000.0`.

### 3.5 `as-of` semantics

`_window_frame` (figures.py:146): the window is `end >= anchor - years`, and **when `as_of` is
given it is also bounded above** by it. Without the upper bound the control would answer
"everything since that date".

It reaches exactly two places: **the Valuation tab** and **the Comparison tab**. It does **not**
affect Fundamentals, Growth, Raw Facts or the Data tab — those call `_window_frame(..., as_of=None)`
unconditionally. The sidebar label says "for valuation", which is accurate but easy to miss.

It also suppresses the snapshot marker whenever `as_of` predates the snapshot's own date
(`_snapshot_point`, figures.py:306) — the boundary is inclusive.

**What a naive rebuild gets wrong:** applying as-of globally (changing tabs the control never
touched), or leaving the upper bound open, or leaving the snapshot marker visible in a
back-dated view.

### 3.6 Every threshold, with its home

| constant | value | file | meaning |
|---|---:|---|---|
| `OUTLIER_MEDIAN_RATIO` | **5.0** | figures.py:179 | a point is an outlier above 5× its panel's median. Calibrated against 15 real series; k=4 hides DAL's 47.2 unnecessarily, k=6 keeps CRM's 337.8 |
| `OUTLIER_MIN_POINTS` | **8** | figures.py:187 | below this the rule does not apply. Excludes 9.5% of valuation series |
| outlier scope | high side only, **valuation only** | figures.py:193 | 0.0% of valuation series have a non-positive median, against 6.2% of fundamentals and 24.7% of growth |
| `MIN_COMPARISON_TICKERS` | **2** | figures.py:40 | below this the comparison returns `(None, [])` |
| `SUGGESTED_MAX_COMPARISON_TICKERS` | **3** | figures.py:38 | the multiselect default, not a cap |
| `_make_grid` max_cols | **3** | figures.py:70 | panels wrap at 3 columns |
| `DEFAULT_TABLE_PERIODS` | **16** | app.py:48 | 4 years of quarters |
| `DEFAULT_COPY_PERIODS` | **8** | app.py:49 | deliberately smaller than the table |
| `ABSOLUTE_THRESHOLD` | **1e4** | app.py:322 | scaled-unit vs fixed-decimal formatting |
| panel pixel sizes | 500×330 / 500×360 / 500×400 / 900×520 | figures.py | fundamentals / growth / valuation / comparison, per col × per row |

**What a naive rebuild gets wrong:** treating `SUGGESTED_MAX_COMPARISON_TICKERS = 3` as a limit —
it is only the default; more tickers are allowed and merely less readable.

### 3.7 Two more that do not fit elsewhere

- **`pivot_ticker` passes `dropna=False`** (app.py:184). A concept that exists but is null in every period must stay as an all-null column: "whether a metric is not applicable or extraction failed is the question this tab exists to answer".
- **raw vs derived is structural, not a suffix match** (`fact_is_derived`, app.py:216): anything not in `get_concept_candidates(ticker)` was derived. That catches `PPNR`, `CoreOperatingEarnings` and `TangibleEquity`, which carry no suffix and which a suffix rule calls raw.

---

## 4. Rendering-side responsibilities

### 4.1 Per control: what has to happen on change

The distinction that matters: **can Plotly toggle it client-side, or does the figure have to be
rebuilt?** `_make_grid` derives rows and columns from the panel count, and
`_make_subplot_figure` builds a `specs` matrix from it — **a finished figure cannot be re-tiled.**

| control | effect | client-side? |
|---|---|---|
| **Ticker** | different data everywhere | **refetch + rebuild** |
| **Metric multiselect** (any chart tab) | changes the panel *count* → new grid | **rebuild.** Not a visibility toggle |
| **Years slider** | changes the row set → axis ranges, mean values, outlier set | **rebuild** (data selection) |
| **As-of checkbox / date** | window upper bound + snapshot suppression | **rebuild** |
| **Hide extreme values** | which points are drawn; mean unchanged; adds/removes a panel annotation | **rebuild** — the trace's `x`/`y` change, and the annotation is part of the layout |
| **Comparison: metric** | different frame, different y-label and ref line | **refetch + rebuild** |
| **Comparison: tickers** | one trace per ticker, no grid change | **could be client-side** for trace visibility, but the title, `layout.meta` and the exclusion annotation all name the plotted set → rebuild, or accept those going stale |
| **Comparison: legend click** | show/hide one line | **native Plotly, no rebuild** — figures.py:931 says this is deliberate: per-ticker show/hide is left to the legend |
| **Data tab: Show all periods** | table rows | table only, no chart |
| **Data tab: Facts filter** | which columns | table only |
| **Raw Facts: include derived** | changes the option list *and* the panel count | **rebuild** |
| **Encyclopedia filter** | list filtering | pure client-side |
| **Profile selectbox** | list rebuild from a static matrix | pure client-side |

Only **one** control in the whole app is a genuine client-side visibility toggle: the comparison
chart's legend. Everything else is a rebuild.

### 4.2 What `figures.py` does that a browser rebuild must reproduce

| responsibility | where | detail |
|---|---|---|
| **grid layout** | `_make_grid`, `_make_subplot_figure` | wrap at 3 cols; `specs` matrix with `None` for unused cells; subplot titles = concept ids |
| **"No Data" placeholder** | `_annotate_no_data` (figures.py:259) | red, size 14, centred at (0.5, 0.5) of the panel, **and** the panel's ticks/grid/zeroline are switched off. Reached from `plot_metric`, `plot_metric_dual` and `build_growth` — **not** from `build_raw_facts` |
| **percent axes** | `_style_axes` | `tickformat=".1~%"` when the metric is percent |
| **x axis** | `_style_axes` | `dtick="M24"`, `tickformat="%Y"` — a tick every two years |
| **reference lines** | `plot_metric`, `build_growth`, comparison | red, width 1. Growth adds a fixed `y=0` line |
| **mean lines** | `plot_metric` | red hline + top-left annotation, `Ø` / `Ø (harm.)`, `.2%` when percent else `.1f` |
| **outlier annotation** | `plot_metric` | bottom-right, grey #888888 size 9, `"N outliers hidden (>5x median) · Ø unchanged"` |
| **dual TTM/quarterly** | `plot_metric_dual` | TTM blue `#1f77b4` width 1.5 `lines+markers`; quarterly orange `#ff7f0e` width 0.8 opacity 0.6 `lines` only. **If the TTM series is empty the panel is "No Data" even when quarterly has values** — the quarterly line alone would be read as the metric itself |
| **colour pinning** | figures.py:19–36 | primary `#1f77b4`, secondary `#ff7f0e`, snapshot `#2ca02c`, and a fixed `_COMPARISON_COLORS` list indexed by the ticker's **position in the request**, so a ticker keeps its colour as others are added |
| **hover** | per trace | single-ticker: `"Date: %{x|%d.%m.%Y}<br>Value: %{y}"`; comparison: `"%{fullData.name}: %{y}"` with `hovermode="x unified"` throughout |
| **snapshot marker** | `_snapshot_point` + `plot_metric` | green circle size 9, white 1px border, `legendgroup="snapshot"`, `showlegend` on the **first** marker only so N panels give **one** legend entry |
| **exclusion annotation** | comparison | red size 10 below the plot, `margin.b` 110 vs 80 depending |
| **`layout.meta`** | comparison | `{concept, tickers, excluded[], outliers_hidden{}}` — survives JSON serialisation so a consumer that only gets the figure still learns what was dropped |

---

## 5. Language and copy

**The premise in the brief is out of date: there is no German in the user-facing app.**

Every string literal in `app.py` and `figures.py` was extracted via AST (docstrings excluded) and
checked. Results:

| location | language | notes |
|---|---|---|
| `figures.py` chart furniture — `"No Data"`, `"Snapshot (current value)"`, `"· TTM"`, `"· quarterly"`, `"Not shown: …"`, `"Outliers hidden (>5x each line's own median): …"` | **English** | `Ø` is a symbol, not German |
| `figures.py` console prints — `"[figures] {t}: requested concepts not plottable"`, `"no visible panels, nothing to build."` etc. | English | never reach the UI |
| `app.py` — every caption, info, warning, button, tab label | **English** | |
| `config.py` — metric labels, `GROWTH_MECHANISM_NOTE`, `VALUATION_MECHANISM_NOTE`, descriptions, formulas | **English** | |
| `content/about.md`, `content/update_notice.md` | operator-authored | not checked — they are data, not code |
| **`main.py`** — `"WARNUNG: Duplikate gefunden!"` (1584), `"WARNUNG: {n} von {m} Tickern nicht auflösbar: …"` (1955), `"WARNUNG: "` (1977) | **German** | **pipeline console output only.** Never rendered by the app |

Two non-ASCII characters are load-bearing in the UI and need care in any port: **`Ø`** (mean-line
label prefix) and **`ᵃ` / `ᵐ`** (`ANNUAL_CADENCE_MARKER`, `MIXED_CADENCE_MARKER`, app.py:246).
Both are chosen for width — the facts table is ~37 columns and a longer marker costs a column.

*Practical note: extracting a file with `subprocess.run(..., text=True)` on this machine decodes as
cp1252 and mangles `Ø`. That is a harness trap, not a code issue, but it will bite anyone diffing
chart JSON.*

**The German that remains is three `WARNUNG:` prints in `main.py`.** Settling the language question
means translating those; it does not touch the frontend at all.

---

## 6. Prioritised rebuild list

Sizes are for one developer already familiar with the pipeline. "**needs export work**" means the
data is not currently available in a browser-readable form.

### Core — without this it is not a replacement

| # | item | depends on | size | export work |
|---:|---|---|---|---|
| 1 | **Export the config registry as JSON** — METRICS, `profile_visibility()`, `get_plottable_metrics` per ticker, `get_concept_candidates`, `HARMONIC_MEAN_CONCEPTS`, `QUARTERLY_COUNTERPART`, the two mechanism notes | — | **2–3 days** | **yes — nothing produces this today** |
| 2 | **Per-ticker JSON export** of the five frames (§1.3) | 1 | 2–3 days | **yes** |
| 3 | Universe + meta load, ticker picker, freshness caption | 2 | 0.5 day | no (`universe.json` already scaffolded) |
| 4 | **Valuation chart** — panels, mean lines with `Ø`/`Ø (harm.)`, reference lines, grid wrap at 3, "No Data" placeholder, percent axes | 1, 2 | **1 week** | no |
| 5 | Fundamentals chart, incl. the **dual TTM/quarterly** treatment and its empty-TTM rule | 4 | 2–3 days | no |
| 6 | Growth chart (incl. the fixed `y=0` line) | 4 | 1 day | no |
| 7 | **`is_hidden` filtering in the picker *and* the builder**, with catalogue ordering | 1 | 1–2 days | no |
| 8 | Years slider + rebuild-on-change wiring for all charts | 4 | 1 day | no |

**Core total: roughly three weeks.** Item 4 is the week: it is the whole chart-furniture layer of
§4.2, and everything after it reuses that work.

### Expected — users would notice its absence

| # | item | depends on | size | export work |
|---:|---|---|---|---|
| 9 | **Data tab** — five sections, pivot, `dropna=False`, the null-column caption, raw/derived split, period controls | 2 | **1 week** | no |
| 10 | Display-vs-export formatting split (§3.4), incl. `ABSOLUTE_THRESHOLD` and `_percent_applies` | 9 | 2 days | no |
| 11 | CSV downloads + copy blocks | 10 | 1 day | no |
| 12 | **Comparison chart** — per-ticker colours by request position, exclusions with their wording, legend show/hide | 4, 7 | 3–4 days | **yes — a by-concept axis (§1.3)** |
| 13 | Snapshot marker with its legend-grouping and `as_of` suppression | 4 | 1 day | no |
| 14 | **Outlier masking** — both tabs, the toggle's conditional presence, the mean invariance, the expander | 4, 12 | 3 days | no |
| 15 | As-of control with the correct scope (valuation + comparison only) | 4, 12 | 1 day | no |
| 16 | Raw Facts tab (bar panels) | 2 | 1–2 days | no |
| 17 | Empty-valuation-panel notice | 4 | 0.5 day | no |
| 18 | Quality-flag section with its summary table | 9 | 1 day | no |
| 19 | Cadence markers ᵃ/ᵐ and their legend | 9 | 1 day | no |

**Expected total: roughly three more weeks.**

### Nice to have — can ship later

| # | item | depends on | size |
|---:|---|---|---|
| 20 | Metric encyclopedia with its filter | 1 | 1–2 days |
| 21 | Profile coverage page incl. the 52 × 24 matrix | 1 | 1 day |
| 22 | About page from markdown, with the `disclaimer` callout | — | 0.5 day |
| 23 | Dismissible update notice | — | 0.5 day |
| 24 | Missing-data guard screen | 3 | 0.5 day |

### Recommended order

**1 → 2 → 3 → 4** is the critical path and nothing else can start meaningfully before item 4 is
done. Item 1 is the one to start today: it is small, it blocks almost everything, and it is the
only part of the contract with no existing artefact.

### Decisions the rebuild should make deliberately

These are not bugs to carry over:

1. **The Growth tab's default** — currently `Revenue` by accident (§2.7).
2. **Whether `SharesOutstanding` should be a growth panel at all** — it is one of the three
   dual-namespace ids and the source of the percent-formatting trap (§3.2).
3. **The three German `WARNUNG:` prints in `main.py`** (§5).
4. **`ffo_gains_source`** — exported and never read. Either surface it beside `ttm_source` or stop
   exporting it.
5. **`build_raw_facts` has no "No Data" placeholder** (§2.7) — the rebuild should be consistent
   with the other four charts.
