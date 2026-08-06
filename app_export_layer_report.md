# Pipeline Export Layer + Streamlit Prototype — Report

**Date:** 2026-08-05
**Touched:** `main.py` (export layer + one stale string), new `app.py`, `requirements.txt`. **`figures.py` and `config.py` are unmodified — verified by SHA-256 before and after**, not by memory:

```
6015CDE0…14CA89  figures.py   (identical before and after)
F588C13F…C0F89D  config.py    (identical before and after)
```

---

## 1. Step 0 — Audit of `run_full_refresh()` and `main()`

### Current execution order of `run_full_refresh()`

| phase | what it does | what it produces |
|---|---|---|
| setup | `get_active_tickers()`, `delete_cached_facts()` | 501 tickers, deleted cache file list |
| 1 — EDGAR | per-ticker `get_company_info` → `build_dataframe`, timed per ticker | `facts` (concatenated, `end` cast to `datetime64[ns]`), then `normalize_split_adjusted`, then `print_data_quality(collect_flags=…)` |
| 2 — yfinance | per-ticker `get_price_history` + `get_current_price_and_shares`, timed per ticker | `price_history` (tz-stripped), `prices` (with `market_cap`) |
| 3 — calculate | derived concepts, `calculate_all_metrics`, `calculate_quarterly_metrics`, four `add_as_concept` calls, duplicate check, `build_metrics_long`, `build_valuation_history`, rolling multiples, peer bands, `build_snapshot`, staleness, filing-overdue flags — all timed as one `calc_time` | `metrics_long`, `valuation_history`, `snapshot` |
| filter | `filter_hidden_rows` on all four, then `add_growth_column(facts_out)` | `facts_out` gains `yoy_growth` |
| write | four CSVs to `DATA_DIR` | see below |
| plot | per ticker: `plot_fundamentals`, `plot_valuation`, `plot_growth`, timed per ticker | `.html` + `.json` per chart in `FIGURE_DIR` |
| report | `write_full_refresh_report` | `full_refresh_report.md` in the module directory |

### The three chart-builder frames — measured, not assumed

Measured on a real 8-ticker run:

| frame | shape | columns and dtypes |
|---|---|---|
| `metrics_long` | 8,711 × 4 | `ticker` str, `end` **datetime64[ns]**, `value` float64 (484 null), `concept` str |
| `valuation_history` | 4,566 × 4 | `ticker` str, `end` **datetime64[ns]**, `concept` str, `value` float64 (1,077 null) |
| `facts_out` (growth source) | 18,120 × 5 | `ticker` str, `concept` str, `end` **datetime64[ns]**, `value` float64, **`yoy_growth`** float64 (8,819 null) |

Confirmed as the brief asked: the growth column **is** `yoy_growth`, and `end` is a **real `datetime64[ns]`** in all three — not object/string. All three carry a default `RangeIndex`, and **no column has `object` dtype**, so nothing needs coercion before Parquet.

### What is written to disk today

- `DATA_DIR` (`data/`), CSV, `index=False`: `quarterly_facts.csv` (name from `PERIOD`), `metrics_long.csv`, `valuation_history.csv`, `current_snapshot.csv`.
- `FIGURE_DIR` (`figures/`): `{ticker}_fundamentals`, `_valuation`, `_growth`, each as `.html` + `.json` (Phase 1's dual output).
- `write_full_refresh_report` writes `full_refresh_report.md` next to `main.py` — run metadata, three timing sections, and data-quality flags grouped by profile.
- **Nothing in the project ever reads a CSV back.** `read_csv` appears nowhere outside `debug_tags.py`'s own unrelated file. The CSVs are human-facing artefacts only.

### Have `main()` and `run_full_refresh()` drifted apart? Yes — six ways

| # | `main()` (ad-hoc) | `run_full_refresh()` | assessment |
|---|---|---|---|
| 1 | writes `valuation_history.dropna(subset=["value"])` to CSV | writes `valuation_history` **with** NaNs | real inconsistency: the same filename means different things depending on which entry point ran |
| 2 | sorts all four frames by `["ticker","concept"]` before writing | no sorting at all | real inconsistency in CSV row order |
| 3 | ticker source is `config.TICKERS` (currently 2 entries) | `get_active_tickers()` (501) | by design |
| 4 | runs the `SNAPSHOT_AS_OF_DATES` loop, writing `snapshot_as_of_*.csv` | does not | functional gap: historical snapshots exist only on the ad-hoc path |
| 5 | `print_data_quality` without `collect_flags` | with `collect_flags`, feeding the report | by design |
| 6 | `load_facts()` (cache-first) | deletes cache, fetches inline | by design |

Also cosmetic: `main()` reuses the name `facts` after filtering; `run_full_refresh()` uses `facts_out`. Equivalent behaviour.

### Stale / dead / inconsistent — what I fixed and what I did not

**Fixed (one, unambiguously stale text left by an earlier task):**
- `write_full_refresh_report` printed *"Plot (per ticker, **both figures**)"*. There have been **three** charts per ticker since the growth chart existed. Changed to "all three charts". Text only; no behaviour.

**Reported, deliberately not touched:**

1. **Drift items 1, 2 and 4 above.** Each is a behaviour question, not dead code: does `valuation_history.csv` mean "all rows" or "rows with a value"? Should the full refresh also emit as-of snapshots? Picking an answer silently would change an output this project has treated as stable, and the brief scoped this task to the export layer. They need a decision, not a guess.
2. **`get_active_tickers()` returns `sorted(TICKER_PROFILES.keys())`** — i.e. *profiled* tickers, not *successful* ones. Nothing downstream distinguishes "was asked for" from "produced data". That is exactly why `universe.parquet` is derived from the frames instead (see below), and it is why the run report's "Active tickers processed: 501" can overstate what actually worked. Left alone; changing `get_active_tickers` is a `config.py` change this task forbids.
3. **The four CSVs have no code consumer.** They are not dead — they are the human-inspectable output of the pipeline, and I have used them myself in earlier tasks. Recommendation: keep. Revisit only if the app fully replaces manual inspection.
4. **`calc_time` covers ten distinct operations as one number.** The report says so explicitly and explains why. Not stale, just coarse.
5. **Nothing else was found**: `_timing_summary` is used by the report writer; `load_facts` / `load_price_history` / `load_current_prices` are used by `main()`; no leftover names from `render_comparison_charts` or `COMPARISON_GROUPS` remain (verified by grep in the previous task and again here).

## 2. Export design

`export_for_app(metrics_long, valuation_history, facts_out, requested_tickers, run_start, out_dir=APP_EXPORT_DIR)`, called at the end of `run_full_refresh()` after the plot loop.

**Format: Parquet**, as the brief specified, and the verification below proves why it matters — `end` survives as `datetime64[ns]`, which `build_valuation`'s `end >= cutoff` comparison against a `pd.Timestamp` depends on. No reason was found that Parquet would not work: no column has `object` dtype, so nothing needed coercion. `pyarrow` added to `requirements.txt`.

| file | contents | rows (8-ticker run) |
|---|---|---|
| `metrics_long.parquet` | the fundamentals frame, unchanged | 8,711 |
| `valuation_history.parquet` | the valuation frame, unchanged | 4,566 |
| `facts_growth.parquet` | `ticker`, `concept`, `end`, `yoy_growth` | 1,705 |
| `universe.parquet` | `ticker`, `profile`, `n_metrics`, `n_valuation`, `n_growth` | 8 |
| `meta.json` | schema version, `run_start`, `exported_at`, `period`, requested/with-data counts, the list of tickers that produced nothing, per-file row counts | — |

**`facts_growth` is narrowed by rows as well as columns.** The brief specified the four columns; I additionally restricted rows to the growth-chart concepts, which takes the file from 18,120 to **1,705 rows — 10.6× smaller**. That is safe by construction: `build_growth`'s catalogue is `GROWTH_PANELS`, so no other concept can ever be drawn, and the concept list is derived from `config.METRICS` (`chart == growth`) rather than hardcoded, so adding a growth panel automatically widens the export. Column narrowing alone would have saved almost nothing (1.08 → 0.94 MB) because rows dominate.

### Decisions

1. **Location: `data/app/`,** a subdirectory of `DATA_DIR`. App inputs are a contract with a separate process; mixing them with the human-facing CSVs makes it unclear which files may be deleted and which would break the app. *Known wart:* `main.py` defines `APP_EXPORT_SUBDIR = "app"` and `app.py` derives the same path from `config.DATA_DIR` independently, because `app.py` must not import `main.py` and this task forbids adding the constant to `config.py`. **Recommendation for a follow-up: put `APP_EXPORT_DIR` in `config.py`** — that is the natural home and removes the duplication.
2. **Existing CSVs stay.** Confirmed by grep that no code reads them; they remain useful for manual inspection. Nothing removed.
3. **Atomicity: write-to-temp-then-`os.replace` per file.** `os.replace` is atomic within a filesystem on both Windows and POSIX, so a reader never sees a half-written Parquet file. `meta.json` is written **last**, so its presence implies the four frames are already in place. *Residual risk, stated deliberately:* this gives per-file atomicity, not a cross-file snapshot — an app reading during a run could pair a new `metrics_long` with an old `universe`. For a prototype with a nightly run that is acceptable; the fix if it ever matters is to write a whole new directory and swap a symlink or a pointer in `meta.json`.
4. **The ad-hoc `main()` path does not export.** It runs on `config.TICKERS` (2 entries right now); exporting from it would replace a 501-ticker export with two tickers' data and the app would silently offer a two-ticker universe. Refusing is the safer default, and the brief explicitly allows it.

## 3. `app.py`

At `stock_valuator/app.py` — next to `main.py`, so `import config` / `import figures` resolve without path juggling. Not named `streamlit.py`, which would shadow the package. Run with `streamlit run app.py`.

- **Caching:** `@st.cache_data` on `load_frame` / `load_meta` — **dataframes only, never figures**. Figures are rebuilt on every interaction, which is cheap and cannot go stale against the widgets that produced them.
- **Missing export:** checked up front; produces an `st.error` naming the missing files and the exact command to run, then `st.stop()` — no traceback.
- **Ticker picker** from `universe.parquet`, showing each ticker's profile.
- **Four tabs:** Fundamentals, Growth, Valuation, Comparison. Each chart tab has a metric multiselect built from `config.get_plottable_metrics(chart, ticker=…)`, **called once per chart type** — the labels are shown, the ids are passed, and the namespace difference is respected (growth options are `Revenue` / `NetIncomeLoss` / `SharesOutstanding`, not metric names).
- **Rendering:** builders are called with `width=None`, so the figure pins no width and the container decides.
- **As-of control** in the sidebar, wired to `build_valuation(as_of=…)` and to the comparison; the valuation tab also has a window-length slider (`years`).
- **Comparison tab:** metric selectbox spanning all three charts, ticker multiselect, routing via `figures.concept_source()`, and the returned `excluded` list surfaced as one `st.warning` per dropped ticker — so a user sees *"AAPL not shown — für Profil 'standard' ausgeblendet"* rather than silently getting two lines instead of three.
- **Run freshness** from `meta.json` in a caption under the title, including which tickers produced nothing.

**One deliberate deviation from the brief.** It specified `st.plotly_chart(fig, use_container_width=True)`. On the installed Streamlit 1.61.1 that parameter is deprecated **with a stated removal date of 2025-12-31, which has already passed**, and it printed a deprecation warning for every chart. `width="stretch"` is Streamlit's own documented replacement and does exactly the same thing; `requirements.txt` pins `streamlit>=1.50` accordingly. Verified: the warnings are gone and the page still renders.

**Prototype limitations:** no styling, no multi-page structure, no session-state handling, no URL state, no error boundary around individual charts (one failing builder would fail the tab). The metric multiselects default to everything selected, which for a `standard` ticker is 9 fundamentals panels — usable, but a large first paint. Comparison tickers default to the first three in the universe, which is arbitrary rather than peer-aware.

## 4. Verification

Isolated working directory with a copied cache; the project's `data/`, `cache/` and `figures/` were untouched (the export under test was written inside the scratch workspace). **All checks passed.**

### The decisive check: Parquet round-trip is figure-identical

For **AAPL (`standard`), JPM (`financial`), AMT (`reit`)**, each figure was built twice — once from the in-memory frame, once from the frame read back out of Parquet — and the `to_json()` compared:

| call | AAPL | JPM | AMT |
|---|---|---|---|
| `build_fundamentals` | 50,191 B ✓ | 52,374 B ✓ | 25,630 B ✓ |
| `build_valuation` | 23,329 B ✓ | 15,691 B ✓ | 16,118 B ✓ |
| `build_growth` | 18,966 B ✓ | 18,876 B ✓ | 18,821 B ✓ |
| `build_valuation(as_of=2020-06-30)` | 23,336 B ✓ | 16,146 B ✓ | 17,874 B ✓ |
| `build_fundamentals(concepts=[3])` | 22,322 B ✓ | 18,537 B ✓ | 18,178 B ✓ |

All **byte-identical**. Plus six `build_ticker_comparison` calls (`p_tbv` across profiles, `revenue_yoy_growth`, and the growth concept `Revenue`), each with and without `as_of` — identical figures **and** identical `excluded` lists. The `as_of` and narrowed-`concepts` calls are included precisely because they are the paths that depend on `end` being a real datetime; they pass, which is the direct evidence for the format decision.

Dtypes confirmed preserved column by column, including `end` as `datetime64[ns]` in all three frames — the thing a CSV round-trip would have destroyed.

### Universe

`universe.parquet` equals the tickers that actually appear in the exported frames (8), **not** `get_active_tickers()` (501 profiled tickers) and not a hardcoded list — asserted both ways. Every listed ticker has fundamentals rows. `meta.json` records 8 of 8 requested with an empty dropout list.

### `app.py`, headless

- **Imports checked by AST**, not by string search: `app.py` imports `config`, `figures`, `streamlit`, `json`, `os`, `pandas` — and **no pipeline module**. Direction `app → figures → config` intact.
- Non-Streamlit logic exercised directly: `missing_files()`, `frame_for`, concept routing (`roe → fundamentals`, `pe_ratio → valuation`, `Revenue → growth`, `nonsense → None`), and `metric_options` — which narrows AAPL's fundamentals to 9 of 29 exactly as `is_hidden` does, returns XBRL concept names for growth, and returns the full catalogue with no ticker. Growth and fundamentals id sets are disjoint, confirming the accessor is called per chart type rather than pooled.
- **The whole page body was executed**, not just imported: `app.main()` was run in Streamlit's bare mode and completed without raising, exercising all four tabs including every figure build. The missing-export branch was exercised by moving the export away — it reaches `st.stop()` rather than a traceback.
- **The real server starts**: `streamlit run app.py --server.headless` stayed alive and its health endpoint answered `200 ok`, with a clean stderr.

**What was not verified, honestly:** nothing was viewed in a browser. Layout, chart legibility at real container widths, tab switching, widget interaction, and the visual result of `width="stretch"` are all unverified. The health endpoint alone would not have proven the script runs — that is why `app.main()` was executed directly instead. What is verified is that the page code runs to completion and every figure it builds is correct; what it *looks like* is not.

### No regression

`main`, `figures`, `config`, `metrics`, `quality` and `parsers.parse_edgar` all import; `main()`, `run_full_refresh()` and `export_for_app()` are callable. The existing CSV and chart writes are untouched — the export is purely additive, appended after the plot loop. `figures.py` and `config.py` are byte-identical to before this task (SHA-256 above).

No scratch scripts were left behind.
