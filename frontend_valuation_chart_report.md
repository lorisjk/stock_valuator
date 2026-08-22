# The valuation chart, rebuilt from the raw series

**Date:** 2026-08-22
**Touched:** `frontend/` only — ten new modules, two edited, seven lines of `.gitignore`.
`git status` shows **nothing changed outside `frontend/`** beyond the operator's own
`task_new.md` and the two report files they deleted before handing over this task.

Rebuild-list **item 4**. The chart is assembled client-side from `tickers/{TICKER}.json` and
`registry.json`; nothing loads a pre-rendered figure any more. Verified against
`figures.build_valuation` on **16 checks over 12 tickers, all passing** — including
**1,209 plotted points compared element-wise** and **64 mean lines matching to the last digit and
byte-identical in their labels**.

---

## 1. Step 1 — the component shape

### 1.1 Where the data lives — one provider, frames only

`DataProvider` holds exactly two things and caches a third:

| held | why |
|---|---|
| `registry` | needed by *every* view — pickers, axis labels, reference lines, percent formatting, the encyclopedia. 11 kB gzipped, changes only when `config.py` does. Fetched once at mount. |
| `universe` | the ticker list and each ticker's profile. Also once. |
| per-ticker `Frames`, keyed | needed by four chart tabs and the data tab. Fetching per component would refetch 14 kB on every tab switch. |

**What it deliberately does not hold: anything a chart derives.** No figures, no selections, no
window. That is not an oversight — `app.py:92` records the reason the Streamlit app caches frames
and never figures: *a cached figure would outlive the widget state that produced it.* The same
trap exists in React, spelled `useMemo` with an incomplete dependency list, so the rule is enforced
by the provider having nowhere to put one.

Two smaller decisions inside the cache:

- **The promise is cached, not the result.** Two components asking for the same ticker in the same
  tick share one request instead of racing.
- **A rejected promise is evicted.** A network failure must not be cached as an answer.
- **No eviction policy.** A core file is 14 kB gzipped and a session touches a handful of tickers;
  an LRU would be more code than the thing it manages.

### 1.2 The selection / drawing split — mirrored, because items 5 and 6 need it

`build_valuation` decides *which* series to draw; `plot_metric` draws one panel into a figure it is
handed. The React side keeps that seam in the same place:

| module | role | reused by |
|---|---|---|
| `charts/select.ts` | `selectMetricIds`, `windowCutoff`, `seriesFor`, `hasAnyValue` | items 5, 6, 8, 15 |
| `charts/mean.ts` | `harmonicMean`, `arithmeticMean`, `meanOver`, `meanLabel` | items 13, 14 |
| `charts/grid.ts` | `makeGrid`, `cellDomain`, axis numbering | items 5, 6, 12 |
| `charts/panel.ts` | `createGrid`, `drawPanel` — all the §4.2 furniture | items 5, 6, 12, 13, 14 |
| `charts/valuation.ts` | the chart-specific part alone: which frame, which chart id, 400 px rows, the title | — |

The justification is the fact the brief points at: items 5 and 6 need **the same drawing layer with
different selection rules**. Fundamentals adds a second trace per panel and a rule that an empty TTM
series blanks the panel even when quarterly has values; growth adds a fixed `y=0` line and reads
`facts_growth`'s `yoy_growth` column. Neither changes the grid, the "No Data" placeholder, the axis
styling or the mean furniture. Had selection and drawing been one function, each of those items
would have forked it.

`drawPanel` takes a `PanelSpec` — a plain description of one panel — rather than a frame. That is
what lets item 5 hand it two traces and item 14 hand it a masked `y` without either being able to
reach the mean.

### 1.3 What triggers a rebuild

`ValuationChart` rebuilds via one `useMemo` keyed on **ticker, selection, window**. This is not a
performance choice. A selection change alters the panel *count*; `makeGrid` derives rows and
columns from that count; `createGrid` builds the axis and domain set from those. **A finished
figure cannot be re-tiled.** Inventory §4.1 lists exactly one genuinely client-side control in the
whole app — the comparison chart's legend — and this is not it.

| this view's controls | effect | handled by |
|---|---|---|
| ticker | different data everywhere | refetch (cached) + rebuild |
| metric checkbox | panel count → new grid | **rebuild** |
| plotly legend click | trace visibility | plotly.js, no rebuild |
| container resize | width only | `useResizeHandler`, no rebuild |

Width is the one thing the figure does not pin: `build_valuation` passes `width=None` for the web
path, and `_size`'s docstring explains why — Plotly only honours container width when the figure
does not set one. The height *is* pinned, at `400 × rows`, matching the reference.

### 1.4 Types, and what a schema mismatch does

`contracts.ts` types both files by hand from the two export reports. **No `any` anywhere in the new
code** — `npx tsc -b` and `npx eslint .` are both clean, and the one pre-existing `any` in the
scaffold's `Chart.tsx` was typed while passing.

Each fetch checks its `schema` integer and throws a `SchemaMismatch` naming the file, the expected
version and what was found, with the remedy in the message. Both files are written by the same
`export_for_app` call, so a mismatch always means *the app and the export are different versions* —
never that one half of the export is stale against the other. That is worth stating, because it
makes "re-run the export" a complete fix.

A second typed error, `MissingTickerFile`, separates "this ticker is not in the dev bundle" from a
real failure. It catches **two** shapes: a static host answering 404, and a dev/preview server's SPA
fallback answering **200 with `index.html`** — which was found by curling `/tickers/ZZZZ.json`
against `vite preview` and getting a 458-byte HTML page. Without the content-type check that
surfaces as an unexplained JSON parse error.

---

## 2. Step 2 — reconstructing the frames

**Column-major → parallel arrays**, not an array of row objects. A 2,357-row facts slice would
otherwise become 2,357 objects with the same four keys, and every panel would walk them again to
pull two columns back out. Parallel arrays keep the export's own shape, cost one pass, and hand
plotly exactly what it wants — an `x` array and a `y` array.

**The row-for-row property survives.** `reconstructFrame` does not sort, filter or fill; row *i*
stays row *i*. Sorting happens once, later and explicitly, in `seriesFor` — and it is load-bearing
rather than cosmetic, because `plot_metric` sorts by `end` and the parquet is not stored date-major
within a (ticker, concept) group.

**Dates parse once**, at load, to UTC midnight via `Date.UTC` rather than relying on `new
Date("2024-03-31")`'s implicit UTC. Never per render.

**Nulls are kept in place.** They are never dropped, filled or coerced — the column keeps its full
length, so row *i* of `x` still belongs to row *i* of `y`. Verified as a number: **85 nulls across
the 12 tickers' plotted series, matching the Python builder's count exactly**, per ticker.

**The `nonfinite` sidecar: the value array keeps the `null`, and the sidecar is carried alongside
unread.** The reasoning, stated rather than inherited by omission:

- a chart cannot draw an infinity, and the reference implementation does not either — `np.isfinite`
  gates the mean line, and a trace point at `Infinity` would blow the y range for every other point
  in the panel;
- so `null` is not a loss of fidelity here, it is the same rendering decision the Python side makes;
- the sidecar is parsed into `Frame.nonfiniteRows` so a later panel can say *"this value is
  infinite"* rather than *"this value is missing"* — item 17's territory.

In practice the valuation frame has **no** non-finite values at all; all 44 in the export are in
`facts_full` and `metrics_long`, which items 5 and 16 will meet.

---

## 3. Steps 3–5 — what was implemented, by file

| file | lines | what |
|---|---:|---|
| `src/contracts.ts` | 147 | types for both contracts, `SchemaMismatch`, `MissingTickerFile` |
| `src/data/load.ts` | 144 | reconstruction, schema checks, the two fetchers |
| `src/data/DataContext.ts` | 71 | the context, `useData`, `useTickerFrames` |
| `src/data/DataProvider.tsx` | 71 | registry + universe once, per-ticker promise cache |
| `src/charts/grid.ts` | 61 | `makeGrid`, cell → (row, col), axis numbering, domains |
| `src/charts/mean.ts` | 85 | the two means and the label, with the invariant documented |
| `src/charts/select.ts` | 99 | visibility, narrowing, the five-year window, series extraction |
| `src/charts/panel.ts` | 248 | the grid figure and every piece of §4.2 furniture |
| `src/charts/valuation.ts` | 80 | `buildValuation` |
| `src/ValuationChart.tsx` | 84 | picker, rebuild wiring, the two empty states |
| `src/App.tsx` | *edited* | provider, universe-driven ticker picker, profile caption |
| `src/Chart.tsx` | *edited* | typed; still serves fundamentals/growth until items 5 and 6 |
| `frontend/.gitignore` | +7 | see §6 |

Panel furniture reproduced, each read off the implementation rather than a screenshot: the
`lines+markers` trace with `#1f77b4` and `connectgaps`, the `Date: %{x|%d.%m.%Y}<br>Value: %{y}`
hover template, `dtick="M24"` / `tickformat="%Y"` on x, the `.1~%` percent tickformat, the y-axis
title at font size 11, the red 1 px mean and reference lines, the top-left `Ø` annotation at size
10, the centred red size-14 "No Data" with the panel's ticks, grid and zeroline switched off, the
`Valuation Data {TICKER}` title, `hovermode: "x unified"` and the size-9 legend.

**Narrowing to nothing** is two distinct states, not one. `build_valuation` returns `None` and
prints; the React side renders a message, and says *which* case it is — a profile that shows no
valuation metrics at all is not the same thing as a picker the user cleared.

---

## 4. Step 6 — verification against the reference

Both implementations were run over the same `data/app` export with the same anchor timestamp, and
their outputs compared field by field. The React modules run **unmodified** in Node — nothing in
`charts/` or `data/load.ts` imports React or plotly.js — so this compares the shipped code, not a
transcription of it.

**16 checks, all passing.**

### 4.1 Panel-set equality — 12 tickers, identical lists in identical order

| ticker | profile | panels | grid | "No Data" panels |
|---|---|---:|:--:|---:|
| AAPL | `standard` | 9 | 3×3 | 0 |
| MSFT | `standard` | 9 | 3×3 | 0 |
| KO | `consumer_staples` | 9 | 3×3 | 0 |
| JPM | `financial` | **5** | 2×3 | 0 |
| O | `reit` | **5** | 2×3 | 1 |
| XOM | `energy_integrated` | 8 | 3×3 | 1 |
| V | `standard` | 9 | 3×3 | **2** |
| STZ | `consumer_staples` | 9 | 3×3 | **3** |
| ERIE | `standard` | 9 | 3×3 | **7** |
| FIG | `standard` | 9 | 3×3 | **7** |
| CRWV | `standard` | 9 | 3×3 | **5** |
| BKR | `energy_integrated` | 8 | 3×3 | **8** |

Also compared and identical: figure title, height, `hovermode`, subplot titles, "No Data" count,
every trace's `name`/`mode`/`connectgaps`/`line.color`/`hovertemplate`/axis assignment, all
**196 axis objects** (domain, anchor, `dtick`, `tickformat`, y-title, and the blanking a "No Data"
panel applies), and every shape.

**Narrowing:** asking AAPL for `pe_ratio, not_a_metric, p_ffo, ev_sales` yields
`['pe_ratio', 'ev_sales']` on both sides — `p_ffo` is hidden for `standard` and `not_a_metric` does
not exist, and neither can widen the result. An empty request produces **no figure** on both sides.

### 4.2 Mean lines — 64 of them, values and labels

Every mean line matched to within 1e-9 relative, and **every label string matched byte for byte**.

| ticker | metric | kind | value | label |
|---|---|---|---:|---|
| AAPL | `pe_ratio` | harmonic | 28.998887415696 | `Ø (harm.) 29.0` |
| AAPL | `pb_ratio` | arithmetic | 44.156027328574 | `Ø 44.2` |
| AAPL | `pfcf_ratio` | harmonic | 28.023369230661 | `Ø (harm.) 28.0` |
| AAPL | `ev_ebitda` | harmonic | 22.546214948095 | `Ø (harm.) 22.5` |
| AAPL | `dividend_yield` | arithmetic | 0.005036584237 | `Ø 0.50%` |
| JPM | `pe_ratio` | harmonic | 10.044945315474 | `Ø (harm.) 10.0` |
| JPM | `p_tbv` | harmonic | 1.829455822094 | `Ø (harm.) 1.8` |
| JPM | `p_ppnr` | harmonic | 7.395346425453 | `Ø (harm.) 7.4` |
| JPM | `dividend_yield` | arithmetic | 0.026028485668 | `Ø 2.60%` |
| JPM | `pe_to_revenue_growth` | arithmetic | 1.943248010764 | `Ø 1.9` |

`metrics.harmonic_mean` was read rather than assumed, and its edge cases checked against nine
hand-built inputs on both sides:

| input | harmonic | arithmetic |
|---|---|---|
| `[1, 2, 4]` | `Ø (harm.) 1.7` | `Ø 2.3` |
| `[-1, 2, null, 4]` | `Ø (harm.) 2.7` — negatives excluded | `Ø 1.7` — nulls skipped, negatives kept |
| `[null, null]` | no line | no line |
| `[-3, -1]` | no line | (n/a) |
| `[0, 5]` | `Ø (harm.) 5.0` — zero excluded | (n/a) |
| `[0.0125, 0.0375]`, percent | (n/a) | `Ø 2.50%` |

The two disagree on sign handling, which is the point of implementing it rather than assuming it:
`values[values > 0]` drops nulls *and* non-positives for the harmonic mean, while pandas' `.mean()`
drops only nulls. A `[-1, 2, 4]` series therefore gets 2.7 harmonically and 1.7 arithmetically. An
all-non-positive series gets no line at all rather than a line at zero.

### 4.3 The grid — 1 to 13 panels

`makeGrid` matches `_make_grid` for every count the valuation chart can produce, and for 0:

| n | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rows×cols | 1×1 | 1×2 | 1×3 | 2×3 | 2×3 | 2×3 | 3×3 | 3×3 | 3×3 | 4×3 | 4×3 | 4×3 | 5×3 |

Trailing cells are never created: `createGrid` emits axes only for `n` panels, which is what
`_make_subplot_figure`'s `None` specs achieve.

### 4.4 Reference lines and percent formatting

**8 percent axes over 64 drawn panels** — every one of them `dividend_yield`, which is the only
percent metric in the valuation catalogue, and nowhere else.

**No valuation metric has a reference line**; all 13 `ref_line` values are `null`. The path is
therefore unexercised by real valuation data, so it was checked against `plot_metric` on a synthetic
panel with `ref_line=0.4, percent=True` and a null in the middle of the series: the red 1 px shape,
the `Ø 30.00%` mean, the `.1~%` y tickformat, the `M24` x dtick and the preserved null all match.
Items 5 and 6 use this path for real.

### 4.5 Null handling, and the edge-case tickers

Nulls survive as nulls, counted per ticker: AAPL 6, CRWV 29, FIG 17, JPM 4, KO 14, V 4, XOM 11 —
**85 in total, matching the Python builder exactly**. A metric with no value anywhere in the window
gets the placeholder, not an empty panel; the counts are in the §4.1 table.

The partial-data tickers behave as the brief expected, though not for the reason it gave:

| ticker | empty panels |
|---|---|
| V | `pe_ratio`, `pe_to_revenue_growth` |
| STZ | `pe_ratio`, `dividend_yield`, `pe_to_revenue_growth` |
| ERIE | `pe_ratio`, `ev_fcf`, `pfcf_ex_sbc`, `ev_ebitda`, `ev_sales`, `dividend_yield`, `pe_to_revenue_growth` |
| BKR | **all 8** |

`p_tbv` is not among them for any of the four — it is not in their profiles' visible catalogue at
all, so it is never offered rather than offered and empty. **The brief's premise that they are
"missing `p_tbv`" is half right and half a different mechanism**, which is exactly the distinction
§3.1 exists to keep straight.

### 4.6 Nothing else changed

`git status` outside `frontend/`: only the operator's `task_new.md` and the two report files they
deleted before this task. No Python file was opened for writing.

`npx tsc -b`, `npx eslint .` and `npx vite build` all pass clean.

### 4.7 What was **not** verified

Stated plainly, because the difference matters:

- **Nothing was viewed in a browser.** Every claim above is a comparison of data structures — the
  figure spec this code hands to `<Plot>` against the one `build_valuation` hands to plotly.py.
  Layout at real widths, legibility of a 5×3 grid, the `Ø` glyph rendering, tick density, hover
  behaviour and the resize handler are all **unverified**.
- What *is* verified is that `vite preview` serves the app and every data file at the paths the
  code fetches (`/registry.json` 83,427 B, `/universe.json` 54,454 B, `/tickers/AAPL.json`
  116,012 B), and that the page and bundle build without error.
- **Plotly's own rendering of the spec is assumed**, not checked. The domains, axis names and
  annotation references were compared against plotly.py's output, so the spec is right; whether
  plotly.js draws an identical picture from an identical spec is a property of plotly, not of this
  code.
- The `nonfinite` sidecar is parsed and carried but **never read** by this chart, because the
  valuation frame contains none. Its consumer is a later item.

---

## 5. Deliberately not done, by item number

| item | what | why not here |
|---:|---|---|
| 5 | fundamentals chart, dual TTM/quarterly | `panel.ts` is the layer it needs; `plot_metric_dual`'s empty-TTM rule is its own decision |
| 6 | growth chart, fixed `y=0` line | same layer, `facts_growth`'s `yoy_growth` column |
| 8 | years slider | `windowCutoff(years, anchor)` already takes both; only the control is missing |
| 12 | comparison view | needs item 7's picker work and a by-concept axis |
| 13 | snapshot marker | `current_snapshot` is already in the fetched core file; the mean must not see it |
| 14 | outlier masking | `PanelSpec` separates drawn `y` from the mean's array so this cannot go wrong |
| 15 | as-of control | `windowCutoff`'s `anchor` parameter is where it goes, plus the upper bound |
| 17 | empty-valuation notice | BKR makes the case for it — see below |
| 9–11, 16, 18–19 | data tab, formatting, downloads, raw facts | untouched |

Also not done and not on the list: no styling beyond the browser default, no URL state, no error
boundary per panel, no loading skeleton.

---

## 6. What the reference implementation turned out to be — the part worth more than the code

The six items that follow will hit every one of these.

1. **`make_subplots` uses vertical spacing `0.5/rows` when subplot titles are given, not the
   documented default `0.3/rows`.** I implemented `0.3` and the comparison caught it: AAPL's row-1
   y domain came out `[0.733, 1.0]` against plotly.py's `[0.778, 1.0]`. **This failure is silent** —
   the panels still tile, they just grow into their own titles. There is no way to notice it except
   by comparing domains, which is why the check compares all 196 axis objects rather than a sample.

2. **The panel title is the metric *id*, the y-axis title is the metric *label*.**
   `_make_subplot_figure` is handed `[c[0] for c in concepts_to_plot]`, so AAPL's first panel is
   titled `pe_ratio` and its y axis reads `P/E (TTM)`. The brief's Step 5 table says the panel title
   is "the metric's label from the registry"; the implementation disagrees, and the implementation
   is what Step 6 measures against. **Reproduced as-is, and flagged rather than fixed** — showing
   ids to users is a product decision, and it belongs with the other deliberate decisions in the
   inventory's §6 list.

3. **No valuation metric has a reference line.** All 13 `ref_line` values are `null`, so a whole
   documented feature of `plot_metric` is dead on this chart. Only one metric is a percentage
   (`dividend_yield`). Anyone verifying this chart against a screenshot would conclude the ref-line
   code works; it is simply never called. Items 5 and 6 are where it becomes live.

4. **`connectgaps=True` means "nulls are kept and the line bridges them".** The brief asks that "a
   gap in a series renders as one", and the reference draws *through* it. Both are true at once:
   the nulls are never dropped, so the x positions still exist and the markers are still absent
   there — what `connectgaps` decides is only whether the line is broken. The reference behaviour
   was reproduced. If the intent is a visible break, that is a one-word change and a product
   decision, not a bug fix.

5. **BKR's chart is empty because of the window, not because of missing data.** Its only valuation
   values are at 2020-06-30 and 2021-06-30 — both **before** the five-year cutoff of 2021-08-22.
   Inside the window it has 20 non-null rows and every one of them is `buyback_distortion_flag`,
   which is not a panel. So `build_valuation` returns a figure with 8 panels and all 8 say "No
   Data". **This is the strongest argument for item 8 (the years slider) and item 17 (the empty
   notice) being taken together**: widening the window fixes BKR, and until then the reader has no
   way to tell "no data ever" from "no data in the last five years".

6. **The window anchor is a wall clock, and the two implementations read different ones.**
   `_window_frame` uses `pd.Timestamp.today()` — server local time, with a time of day. The browser
   uses `new Date()` in UTC. For a user far enough east, the two can name different calendar days,
   which would shift the cutoff by one. Measured on the real data: **the nearest row to the cutoff
   is 5.17 days away**, so no ticker's panel changes either way. It is recorded because item 8 makes
   the window user-controlled, and item 15 adds an explicit `as_of` — at which point the anchor
   stops being incidental. `windowCutoff` takes the anchor as a parameter for exactly that reason.

7. **`harmonic_mean` and `Series.mean()` treat negatives differently, and neither is documented at
   the call site.** `values[values > 0]` silently excludes non-positives *and* nulls; `.mean()`
   excludes only nulls. A panel whose series contains negative values therefore gets a mean over a
   different subset depending on which kind it is. Reproduced exactly, and probed with hand-built
   inputs because no real valuation series happens to be negative.

8. **`pd.Series.mean()` does not skip infinities, and `np.isfinite` is what suppresses the line.**
   An `inf` anywhere in a series produces `inf` as the mean and therefore **no mean line at all** —
   not a line at some large value. The valuation frame has no infinities, but `metrics_long` has 22,
   so **item 5 will meet this**. `arithmeticMean` reproduces the behaviour rather than "fixing" it.

9. **The repository root's `.gitignore` contains `data/` with no leading slash**, which matches a
   directory of that name at *any* depth — including `frontend/src/data/`, where the export loaders
   live. The whole data layer was untracked: it compiled, it ran, and it was simply absent from
   `git status`. Fixed inside `frontend/.gitignore` with a `!/src/data/` re-inclusion and a comment,
   because anchoring the root pattern would be a change outside `frontend/`. **The root pattern is
   still unanchored and will catch the next `data/` directory too.**

---

## 7. Running it

The dev bundle in `frontend/public/tickers/` carries **12 tickers** (940 kB, 1,090 lines of new
TypeScript to read them) — the verification set plus MSFT, KO and XOM. The picker offers all 609
from `universe.json`, and a ticker with no bundled file gets a message naming the file rather than a
blank chart.

`data/app/tickers/` holds all 1,218 files after a pipeline run, so bundling more is a copy:

```sh
cp data/app/tickers/NVDA.json frontend/public/tickers/
```

The published deployment serves `data/app/tickers/` directly and needs no bundling step at all; only
the four chart frames are used, so `{TICKER}.facts.json` is not copied here.

No scratch files were left behind.
