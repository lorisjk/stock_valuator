# Task: Pipeline Export Layer + Streamlit Frontend Prototype

**Depends on the `METRICS` registry task being complete and shipped.** Read
`metrics_registry_report.md`, `figures_parametrization_report.md` and the current `figures.py`,
`config.py` and `main.py` before changing anything.

## Context

`figures.py` is finished for a web frontend: the `build_*` functions return figure objects,
accept an explicit `concepts` narrowing list, allow `width=None` for responsive rendering, and
take an `as_of` anchor for the valuation window. `config.get_plottable_metrics()` enumerates
selectable metrics per chart type with `is_hidden` already applied.

What does not exist yet is the **connection between the batch pipeline and a frontend**: the
pipeline computes everything in memory and writes charts to disk, but nothing hands the
dataframes over in a form a separate process can read.

The target architecture is the batch/read split this project already decided on: `main.py` runs
nightly and writes pre-computed data; the frontend process reads only that data and renders on
demand. **No pipeline computation in the request path.**

**Explicitly NOT in this task:** no changes to `figures.py` or `config.py` (both are finished for
this purpose — if you believe one needs a change, report it instead of making it), no Phase 4
(cross-sectional/peer scatter), no `PROFILE_HIDDEN` refactor, no `SharesOutstanding` fix, no
deployment/hosting work, no authentication, no styling beyond what is needed for the prototype to
be usable.

---

## Step 0 — Audit `run_full_refresh()` before touching it

Read `run_full_refresh()` and `main()` in full and report their **current actual** behaviour —
not what earlier reports said they did. Several tasks have modified `main.py` since this function
was last examined end to end (the Plotly migration changed all six plot call sites; the
comparison cleanup removed `render_comparison_charts`, its two call sites and its timing entry).

Report specifically:

- The current execution order and what each stage produces.
- **The exact names, shapes and dtypes of the three dataframes the chart builders consume** —
  whatever `run_full_refresh` currently calls `metrics_long`, `valuation_history` and the facts
  frame. Confirm the actual column names, in particular that the growth frame's column is
  `yoy_growth` and that `end` is a real datetime dtype and not an object/string column.
- What is currently written to disk, where, and in what format (CSV? Parquet? which directory?),
  including anything written by `write_full_refresh_report`.
- Whether `main()`'s ad-hoc path and `run_full_refresh()` have drifted apart — do they compute
  the same things the same way, or has one been updated and the other not?
- **Anything stale, dead, or inconsistent**: leftover names from removed features, timing
  entries that no longer match the stages that exist, exclusions handled in two places,
  hardcoded ticker lists, or steps whose output nothing consumes. Report these; fix only the ones
  that are unambiguously dead code left behind by a previous task, and list anything you chose
  not to touch with your reasoning.

This audit goes in the report **before** the export design, because the export contract depends
on what the frames actually are.

## Step 1 — The export layer in `main.py`

Add a function (e.g. `export_for_app(...)`) that writes the frontend's inputs to disk, called at
the end of `run_full_refresh()`.

**Format: Parquet, not CSV.** The decisive reason is dtype preservation: `build_valuation` and
`build_ticker_comparison` compare `frame["end"]` against a `pd.Timestamp` cutoff, and a CSV
round-trip turns `end` into a string, which either raises or — worse — compares wrong silently.
Parquet also loads far faster, which matters because a Streamlit script re-runs on every widget
interaction. If you find a concrete reason Parquet will not work here, report it rather than
silently falling back to CSV.

Write, at minimum:

| file | contents | why the frontend needs it |
|---|---|---|
| `metrics_long.parquet` | the fundamentals frame | `build_fundamentals` |
| `valuation_history.parquet` | the valuation frame | `build_valuation` |
| `facts_growth.parquet` | facts narrowed to `ticker`, `concept`, `end`, `yoy_growth` | `build_growth` — the full facts frame is large and the frontend needs only this |
| `universe.parquet` | the tickers that actually produced data in this run | the ticker picker must not offer tickers that exist in `TICKER_PROFILES` but failed or were skipped in the run |
| `meta.json` | run timestamp, ticker count, and whatever else identifies the run | the app shows the user how fresh the data is — this project treats data transparency as a differentiator, so it belongs in the UI, not just in a log |

Decide and state:

1. **Where these live** — reuse `DATA_DIR`, or a separate subdirectory so app inputs are not
   mixed with existing CSV outputs. State the choice.
2. **Whether existing CSV outputs stay.** Do not remove them in this task unless you have
   confirmed nothing consumes them; if they are redundant, report that as a recommendation.
3. **Atomicity.** A nightly run writing these files while the app is reading them can serve a
   half-written file. Decide whether to write-then-rename (or another approach), and state it. A
   prototype can accept the risk — but say so deliberately rather than not noticing it.
4. **Whether `main()`'s ad-hoc path should also export.** Consider that an ad-hoc single-ticker
   run would otherwise overwrite a full universe export with one ticker's data. State your
   decision; refusing to export from the ad-hoc path is a legitimate answer.

## Step 2 — The frontend prototype

Create **`app.py`** in the project root.

**Do not name this file `streamlit.py`.** A module of that name shadows the installed package on
`sys.path`, and `import streamlit as st` then imports the file itself. Name it `app.py` and run it
with `streamlit run app.py`.

`app.py` is a standalone entry point, not a module imported by `main.py`. The import direction is
`app.py` → `figures.py` → `config.py`, never the reverse, and `app.py` must not import `main.py`
or trigger any pipeline computation.

Required capability:

1. **Load and cache the exported frames** with `@st.cache_data`, because Streamlit re-executes
   the whole script on every widget interaction. Cache the **dataframes only, never the figure
   objects** — building a figure is cheap, and a cached figure is a stale-state trap.
   Handle missing export files with a clear message telling the user to run the pipeline, not a
   traceback.
2. **Ticker selection** from `universe.parquet`.
3. **Three chart sections** (fundamentals, growth, valuation), each with a metric multiselect
   populated from `config.get_plottable_metrics(chart, ticker=...)`, which already returns
   `(id, label)` pairs with `is_hidden` applied. Display the label, pass the id. Note the
   namespace difference the registry now makes explicit: fundamentals/valuation ids are metric
   names, growth ids are XBRL concept names — call the accessor per chart type rather than
   building one shared metric list.
4. **Render via `st.plotly_chart(fig, use_container_width=True)`**, passing `width=None` to the
   builders so the layout does not fight the container width. Handle a `None` return (nothing
   selected, or everything hidden) with an informational message rather than an exception.
5. **An as-of date control** wired to `build_valuation`'s `as_of` parameter.
6. **A comparison section**: pick a metric and 2+ tickers, route the right dataframe using
   `figures.concept_source()`, call `build_ticker_comparison`, and **surface the returned
   `excluded` list in the UI** (e.g. `st.caption`/`st.warning`) — the whole point of that return
   value is that a user sees why a ticker is missing.
7. **Show the run timestamp** from `meta.json` somewhere visible.

Keep it a prototype: no custom CSS, no multi-page structure, no session-state gymnastics.
`st.tabs` and the standard widgets are enough. Add `streamlit` and (if not already present) a
Parquet engine to `requirements.txt`.

## Step 3 — Verify

- **The export round-trips losslessly, and this is the decisive check:** load the exported
  Parquet files back, feed them to `build_fundamentals` / `build_growth` / `build_valuation` /
  `build_ticker_comparison`, and confirm the resulting `fig.to_json()` is **byte-identical** to
  the figure built from the in-memory frames in the same run, for at least three tickers spanning
  different profiles (e.g. `standard`, `financial`, `reit`). This proves the dtype and content
  preservation the whole format decision rests on. Include an `as_of` call and a narrowed
  `concepts` call among them, since those are the paths that depend on `end` being a real
  datetime.
- **`universe.parquet` matches what the run actually produced** — not `TICKER_PROFILES`, and not
  a hardcoded list.
- **`app.py` imports cleanly** and its non-Streamlit logic (loading, routing a concept to the
  right frame, building the selection lists) is exercised directly, without a browser. State
  honestly what could and could not be verified headlessly — do not claim the UI was tested if it
  was not.
- **Nothing regressed:** `main()` and `run_full_refresh()` still run end to end; the existing
  chart files are still written exactly as before; `figures.py` and `config.py` are unmodified
  (confirm by diff, not by memory).
- **Missing-export handling:** deleting one exported file produces the intended message, not a
  traceback.

## Output

One file, `app_export_layer_report.md`, containing:
1. The Step 0 audit of `run_full_refresh()` — its current behaviour, the exact frame shapes, and
   the list of stale/inconsistent things found, split into what you fixed and what you left alone
   with reasoning.
2. The export design decisions (location, atomicity, ad-hoc path) with reasoning.
3. What `app.py` does and its known limitations as a prototype.
4. The Step 3 verification results, including the byte-identity evidence and an honest statement
   of what was not verifiable without a browser.

No scratch scripts left behind.s