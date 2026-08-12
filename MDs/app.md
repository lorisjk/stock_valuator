# `app.py`

## Overview

The Streamlit frontend. Run with `streamlit run app.py`.

It is a **reader**, not a stage of the pipeline. Everything it displays was computed by
the nightly run and written to `data/app/`; nothing here fetches, extracts or derives a
number. If a figure looks wrong, the bug is upstream — this file can only fail to *show*
something correctly.

---

## The architecture boundary

The import direction is **`app → figures → config`**, and `app.py` never imports
`main.py`. That is what keeps the frontend from acquiring a dependency on the pipeline's
network and file-writing code.

**One honest exception:** `figures.py` imports `harmonic_mean` from `metrics.py`, so the
real chain is `app → figures → metrics`. It is a single pure function — arithmetic over a
Series, no I/O, no config reads — and it exists there because the mean line drawn on a
valuation panel has to be computed the same way `calculate_rolling_harmonic_stats`
computes the stored one. Stating this accurately matters more than the tidier claim: the
constraint that is actually enforced is "no `main.py`, no fetchers, no parsers", not "no
pipeline module at all".

`APP_DATA_DIR` is derived from `config.DATA_DIR` rather than imported from `main`, for the
same reason — `main.APP_EXPORT_DIR` is the same path, computed independently on both
sides.

---

## The data contract

`main.export_for_app` writes six frames plus `meta.json`. `missing_files()` checks for all
of them before the page renders anything and stops with an explicit message if one is
absent, because the alternative is a `FileNotFoundError` three layers into a chart
builder.

| file | who reads it | what it holds |
|---|---|---|
| `metrics_long.parquet` | fundamentals charts, data tab | every computed metric, long format |
| `valuation_history.parquet` | valuation charts, data tab | the multiples over time |
| `facts_growth.parquet` | growth charts | `ticker, concept, end, yoy_growth`, narrowed to the growth-chart concepts |
| `facts_full.parquet` | data tab, raw-facts chart | the whole facts frame, raw and derived |
| `current_snapshot.parquet` | data tab, snapshot markers | one value per (ticker, concept) at the run date |
| `universe.parquet` | ticker list and profile map | `ticker, profile, n_metrics, n_valuation, n_growth` |
| `meta.json` | the freshness caption | run timestamps, period, ticker counts, row counts, schema |

`meta.json` is written **last**, so its presence means every frame above it is already in
place. Each frame is written to a `.tmp` file and `os.replace`d over the target, which is
atomic on one filesystem — a frontend reading during a nightly run sees the old file or
the new one, never half of either.

### Why `facts_growth` and `facts_full` both exist

They come from the same source frame and neither is derivable from the other cheaply at
render time.

`facts_growth` is what `build_growth` needs: three concepts, four columns, roughly a tenth
of the rows. `facts_full` is what the data tab needs, and its whole point is that a raw
concept sits next to its own `_TTM` derivation in the same table — which is what makes the
TTM auditable by eye. Narrowing one frame to serve both would break the data tab; widening
one to serve both would make every growth chart load ten times more data than it draws.

---

## View structure

Two levels of navigation, and the split is not cosmetic.

**The sidebar radio (`VIEWS`)** chooses between the ticker-specific analysis view and the
ticker-**independent** reference pages — `Metric encyclopedia`, `Profile coverage`,
`About`. Reference material is reached here rather than as more tabs for two reasons: nine
tabs in one row is not navigable, and — the deciding one — sitting a page that describes
the pipeline next to a ticker-specific tab set invites the reader to assume it describes
the selected ticker. Switching away from Analysis also hides the ticker controls, so there
is nothing left to misread.

**The tabs inside `render_analysis`** are the ticker-specific views: Data, Raw Facts,
Growth, Fundamentals, Valuation, Comparison. The `with` blocks that fill them are named
containers, so their order in the source is independent of the order they render in — the
list passed to `st.tabs` is the only thing that decides.

---

## How metric selection works

Never by hardcoded lists. `config.get_plottable_metrics(chart, ticker=...)` returns
`(id, label)` pairs for a chart type, already filtered by `is_hidden`.

**The namespaces differ per chart, and mixing them is the trap:**

- `fundamentals` and `valuation` ids are **metric names** (`operating_margin`, `pe_ratio`).
- `growth` ids are **XBRL concept names** (`Revenue`, `NetIncomeLoss`,
  `SharesOutstanding`), and their values are read from the `yoy_growth` column rather than
  from `value`.

`metric_options` is therefore called once per chart type rather than once overall. The
registry keeps the two namespaces apart and refuses a duplicate id at import
(`_index_metrics`), so an id maps to exactly one chart — which is what lets
`figures.concept_source` route a concept to its frame without the caller knowing which.

**`is_hidden` is authoritative and narrowing-only.** The UI may pass a `concepts` list to
a builder, but `figures._select_concepts` applies `is_hidden` to the catalogue *first* and
lets the caller's list only narrow what survives. A request can never surface a metric the
ticker's profile hides — including through the comparison chart, which drops such tickers
into its `excluded` list rather than plotting them.

---

## Caching

`@st.cache_data` sits on `load_frame` and `load_meta` — the parquet reads — and on nothing
else.

**Figures are never cached.** Building one is cheap, and a cached figure would silently
outlive the widget state that produced it: change the metric multiselect, get a figure
built from the previous selection.

**Content files are not cached either.** `read_content` reads `content/about.md` and
`content/update_notice.md` on every rerun, because those are the files a human edits by
hand and a cache would hold the old text until someone knew to clear it.

---

## Provenance signals in the data tab

The data tab exists to show how a number was obtained, not only what it is. Four signals
reach it, all computed upstream:

| signal | where it appears | what it says |
|---|---|---|
| `ttm_source` | cadence markers on facts columns | whether a `_TTM` value was summed from four quarters (`quarterly_rolling`) or read from one 12-month fact (`annual_fact`) |
| `ffo_gains_source` | facts frame | whether FFO's real-estate-gains term was filed or imputed as zero |
| quality flags | their own section, pulled out of `metrics_long` | buyback distortion, share-count jumps, inorganic contamination, band-elevated, and the rest |
| `<field>_age_days` | snapshot section | a snapshot input carried forward from an earlier period, and how far back |

`cadence_markers` renders `ttm_source` as a single superscript character per column with a
legend underneath, because the facts table already runs to ~37 columns and a second row of
labels would not fit.

Quality flags are separated from the metrics because they are 0/1 columns and leaving them
interleaved among the ratios makes both harder to read. The test for "is this a flag" is
**name-based and lives only in `app.py`** — neither `config.py` nor `quality.py` offers
one. `METRICS` is not the test: it excludes the flags, but it also excludes `rotce`,
`effective_tax_rate` and the nine `*_quarterly` series. `quality.py`'s "flags" are an
unrelated thing (EDGAR coverage warnings that never reach these frames).

---

## Known limitations

**`as_of` is a chart-window filter, not a recomputation.** The sidebar control is passed to
`figures.build_valuation` and `figures.build_ticker_comparison`, where it moves the
plotted window and suppresses the snapshot marker when the chosen date predates it. It
does **not** re-run any metric. A number displayed under an as-of date was computed by the
nightly run with everything that run knew — including, for
`apply_self_relative_scale_guard`, data from after the chosen date. Peer-band flags are
likewise not recomputed; `calculate_peer_band_flags` takes an `as_of` parameter, but only
the pipeline can call it.

**`facts_full` is written post-`filter_hidden_rows`, and that is visible.** A concept the
ticker's profile hides is absent from the exported frame, not merely hidden at render
time. NEE's annual `ShareBasedCompensation` series is the standing example: it exists in
the pipeline's own frames and cannot appear in the app at all, because the export happens
after the filter. The data tab therefore shows what the profile allows, never everything
that was extracted.

**No write path.** Nothing in the app can trigger a refresh. The page reports what the last
run produced and, when files are missing, prints the command that produces them.

**Streamlit swaps Plotly's default template on import.** Figures built inside the app do
not serialise byte-identically to figures built by a plain script, even from identical
data. Any comparison of figure output has to happen within one process state.

---

## Editable content

`content/about.md` and `content/update_notice.md` hold text rather than code, so the
operator can change what the site says without touching a module the pipeline imports.

Both are read through `read_content`, which returns `""` for a missing or unreadable file
— that is what lets "no notice file" mean "nothing to announce" with no separate switch.
`strip_comments` removes `<!-- -->` blocks before rendering, because Streamlit renders
markdown with HTML disabled and would otherwise print the editing instructions to the
page.

The update notice's dismissal lives in `st.session_state`. Streamlit re-executes the whole
script on every widget interaction, so a module-level or local flag would be reset by the
next click; session state persists for the browser session and resets on reload, which is
the intended lifetime. The dismiss button uses an `on_click` **callback** rather than
`if st.button(...)`: callbacks run before the script body, so the flag is already set when
the notice's early return is evaluated. With the `if` form the notice is drawn before the
branch that sets the flag is reached, and survives until some unrelated widget triggers
the next rerun.
