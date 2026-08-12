# `figures.py`

## Overview

All plotting. Takes finished long-format DataFrames and produces **Plotly** figures.
Contains no calculations beyond drawing a mean line, and no data access.

The module is split in two layers, and the split is the thing to understand before
changing anything here:

- **`build_*`** returns a `go.Figure` (or `None`) and touches no files. This is what a web
  layer wants.
- **`plot_*`** is a thin wrapper: call the matching `build_*`, return early if it produced
  `None`, hand the figure to `_write_figure`.

Every behavioural change belongs in the `build_*` function. The wrappers exist only so the
nightly run can write files without the frontend inheriting file I/O.

---

## Functions

| Function | Purpose |
|---|---|
| `build_fundamentals` / `plot_fundamentals` | grid of fundamental metrics, TTM with quarterly overlay |
| `build_growth` / `plot_growth` | grid of YoY growth panels |
| `build_valuation` / `plot_valuation` | grid of valuation multiples, each with its own mean line |
| `build_ticker_comparison` / `plot_ticker_comparison` | one metric, one line per ticker |
| `build_raw_facts` / `plot_raw_facts` | filed concepts before any metric is computed |
| `plot_metric` | draws one panel into a supplied `(fig, row, col)` |
| `plot_metric_dual` | the same, with a quarterly series behind the TTM one |
| `concept_source` | which frame a concept lives in: `fundamentals`, `valuation`, `growth` |
| `available_raw_concepts` | the raw-facts picker's options for one ticker |

`plot_metric` takes `(fig, row, col)` rather than creating its own figure — that is what
lets the same function fill one cell of a grid or a standalone chart.

---

## Grid layout

`_make_grid(n, max_cols=3)` wraps at three columns. Every chart uses it, including
`build_growth`, which was a single row while there were only ever three growth panels. The
registry now yields up to seven, and one row of seven is a 3,500px-wide figure. For three
panels or fewer the grid is still 1×n at the same pixel size, so those figures are
unchanged.

`_make_subplot_figure` passes a `specs` matrix with `None` in the trailing cells, so a
grid with an incomplete last row leaves empty space rather than empty axes.

---

## `concepts`, and why narrowing can only narrow

Each `build_*` takes an optional `concepts` list. `_select_concepts` resolves it:

```python
visible = [c for c in catalogue if not is_hidden(ticker, c[0])]
```

**`is_hidden` is applied to the catalogue first, and the caller's list only narrows what
survives.** An explicit request can therefore never surface a concept the ticker's profile
hides. The property is structural — it follows from the order of the two filters — and it
is easy to destroy by "simplifying" the function into a single intersection.

Requested entries that are unknown or hidden are **dropped with a printed note, not
refused**. A UI hands one selection to several tickers, and a concept that is fine for one
is routinely hidden for another; that is normal operation, not a caller error.

Panel order always follows the catalogue, never the caller's list, so a chart's layout is
stable no matter what order the UI sends.

---

## `width` / `height` and the `KEEP` sentinel

```python
KEEP = _Keep()          # repr: <unchanged>
```

Three-way, because `None` is already meaningful:

| passed | effect |
|---|---|
| `KEEP` (default) | the chart's historical size — `500*cols` by `330*rows`, etc. |
| `None` | the key is **omitted from the layout entirely** |
| a number | that value |

`None` is what a responsive frontend needs: Plotly only honours a container-width request
when the figure does not pin a width of its own. So `None` cannot double as "use the
default", which is why the sentinel exists.

`_size` returns a dict to splat into `update_layout` rather than a merged layout dict, so
each caller keeps its original keyword order and the serialised JSON stays byte-identical
to what it produced before these parameters existed.

---

## The time window and `as_of`

```python
def _window_frame(frame, years, as_of):
    anchor = pd.Timestamp.today() if as_of is None else pd.Timestamp(as_of)
    windowed = frame[frame["end"] >= anchor - pd.DateOffset(years=years)]
    if as_of is not None:
        windowed = windowed[windowed["end"] <= anchor]
```

Shared by `build_valuation` and `build_ticker_comparison` so the two cannot drift.

The window is relative to the anchor, not to a hardcoded date. That started as a
workaround — Apple's pre-2019 P/E is unusable because EDGAR restates per-share figures
retroactively but not uniformly, so TTM sums straddling a split produce garbage — and it
survives for a better reason: **the split zone is old data, and old data is not the
question.** "Is this expensive now" is answered by the last few years.

**With an explicit `as_of` the window is bounded above as well.** The caller asked for "the
last `years` years as of that date"; leaving the upper bound open would instead answer
"everything since that date" and put data on the chart the chosen date could not have
known.

Note what `as_of` does **not** do: it filters. Nothing is recomputed. See `MDs/app.md`.

---

## The snapshot marker

`build_valuation` optionally takes the exported snapshot and adds the current multiple as
one extra marker per panel — the value the history exists to be judged against.

Three properties worth keeping:

- **It is a separate trace**, so it never enters the mean line. The mean is computed from
  `filtered`, which the snapshot never joins. That is a structural guarantee rather than an
  ordering convention: the benchmark cannot be contaminated by the value being compared
  against it.
- **It is suppressed when `as_of` predates the snapshot** (`_snapshot_point` returns
  `None`). Appending a run-date point to a window that ends earlier is exactly the error
  `as_of` exists to prevent.
- **One legend entry for all panels**, attached to whichever panel got the first marker.

A concept with no snapshot row simply renders without a marker. `build_snapshot` now
computes every valuation panel, so a missing row means the ticker's profile hides that
metric.

Colour: green (`_SNAPSHOT_COLOR`), never red — red is already the mean line and the
reference line.

---

## `build_ticker_comparison` returns `(fig, excluded)`

The only builder with a tuple return, and the second element is load-bearing:

```python
fig, excluded = build_ticker_comparison(tickers, concept, frame)
```

`excluded` is `[(ticker, reason), ...]`. Drops are never silent — they are returned,
printed, written onto the chart as an annotation, **and** stamped onto `fig.layout.meta`
so they survive `to_json`/`from_json` for a consumer that only receives the serialised
figure.

`fig is None` has two meanings and `excluded` tells them apart:

| `fig` | `excluded` | meaning |
|---|---|---|
| `None` | non-empty | every requested ticker was dropped — a data outcome |
| `None` | empty | the request was rejected — unknown concept, or fewer than `MIN_COMPARISON_TICKERS` |

A ticker is dropped when `is_hidden` hides the metric for its profile. The profile system
already decides where a number is meaningful, and a comparison chart must not go behind
its back.

**Two limits, deliberately different in kind.** `MIN_COMPARISON_TICKERS = 2` is *enforced*:
one ticker is not a comparison, which is a category check.
`SUGGESTED_MAX_COMPARISON_TICKERS = 3` is *advisory only* — a readability limit belongs in
the UI that picks the tickers, not in the rendering layer, where a hard refusal would turn
a UI mistake into a missing chart. Colours are assigned by position in the requested list,
so a ticker keeps its colour when another drops out, and the index wraps rather than
raising.

**No per-ticker mean lines and no snapshot markers**, both for the same reason: n of them
would bury the data. n markers at the same x would cluster into what reads as a vertical
spike rather than n current values, and the comparison chart answers "how have these moved
relative to each other", where the shape of the history is the content.

---

## Writing files: `write_charts` and `write_html`

`_write_figure` writes **JSON always, HTML on request**. They are not the same kind of
artifact: the JSON is the interface (~20–50KB, what `from_json` reads back), the HTML is a
standalone viewer with plotly.js inlined (~5MB, about 7.5GB across a 501-ticker run). So
JSON is unconditional and HTML is opt-in rather than the two sharing one switch.

The "both files or neither" guarantee applies to a *single chart's pair* and is kept by
deriving both names from one stem in one call.

Above that, `write_charts` decides whether any chart is produced at all. It defaults to
`True` in `main()` (a run that exists to look at output) and `False` in
`run_full_refresh()` (the nightly run feeds the app, which reads parquet and never opens a
chart file).

---

## Empty data

A panel with no rows gets a red "No Data" annotation and its axes' ticks and grid turned
off, rather than an empty axis. Without it Plotly falls back to the epoch and draws an
axis labelled 1970, which reads as a bug rather than as an absence.

This is not an edge case. Banks have no operating margin, no capex and no conventional
long-term debt, so several fundamental panels are legitimately empty for JPM — and the
profile system hides most of them before they are even built.

---

## Colours are pinned

`_PRIMARY_COLOR` / `_SECONDARY_COLOR` are fixed rather than left to Plotly's colour cycle.
One figure holds every subplot, so an automatic cycle would give each panel a different
colour and imply a distinction that does not exist. The TTM series and its quarterly
overlay must also be the same two colours in every panel that has both.
