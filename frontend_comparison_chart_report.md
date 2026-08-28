# The comparison chart — item 12

One metric, one line per ticker, wired into the Comparison tab. **No new export was built**, and
§2 has the measurement that says so rather than the assumption.

Verified trace by trace against `build_ticker_comparison` over **20 scenarios — 5,404 checks, 50
traces, 2,500 points, 0 failures** — including the `pe_ratio`/`reit` exclusion, the reverse
`p_ffo`/`standard` case, "No Data", the one-ticker rejection, the all-excluded case, dedup, and the
colour wrap past a 10-colour palette.

---

## 1. Step 1 — the reference

### 1.1 Colour follows the **requested** position, not the plotted one

```python
line=dict(color=_COMPARISON_COLORS[position % len(_COMPARISON_COLORS)])   # figures.py:990
```

where `position` comes from `enumerate(requested)` (figures.py:855) and `requested` is
`list(dict.fromkeys(tickers))` (figures.py:845) — deduplicated, order preserved. The comment above
the palette (figures.py:26-28) states the intent: *"colors assigned by position in the requested list
so a ticker keeps its color even when another one drops out of the chart."* Ten colours, indexing
wraps.

The brief asks whether a user "removing and re-adding a ticker" gets a stable answer. Measured (§5.2),
the guarantee is narrower than it first reads and the distinction is worth stating:

- **A ticker that is *excluded*** — present in the list, dropped by the chart — **does not recolour
  anything.** AAPL keeps `#1f77b4` and KO keeps `#2ca02c` when O is excluded between them.
- **A ticker *removed from the list* shifts every ticker after it**, because the index is the
  position in the list you built. That is the reference's semantics exactly, and it is at least
  explainable: the colour is the ticker's place in your set.

### 1.2 Exclusion — two reasons, and the app rewords one

`_comparison_selection` (figures.py:854-863) produces exactly two:

| condition | reason string | source |
|---|---|---|
| `is_hidden(ticker, concept)` | `f"for profile '{profile}' not shown"` | figures.py:857 |
| windowed series has no non-null value | `"No Data"` | figures.py:863 |

They render in **two places at once**:

- **On the figure**, as an annotation `"Not shown: " + ", ".join(f"{t} ({reason})")`, paper
  coordinates `x=0, y=-0.16`, red, size 10 (figures.py:1010-1020).
- **Above the chart in the app**, one `st.warning` per ticker: `f"**{dropped}** not shown — {detail}."`
  (app.py:1072). `detail` is the reason verbatim, except `"No Data"`, which app.py:1067 rewrites to
  `"no values in this window"` plus `" — no share-count history is available for it"` when
  `share_history_absent(dropped)`. The comment there says why: *"figures.py reports the fact ('No
  Data'); the wording is the app's job, and it has to match the valuation tab's notice."*

Note the reference's own redundancy in the profile case — *"**O** not shown — for profile 'reit' not
shown."* — reproduced rather than tidied.

### 1.3 Legend — plotly's, untouched

figures.py:932: *"Per-ticker show/hide is left to Plotly's legend, which does it natively."* No
custom handler, no `legendgroup`, no click callback. The only legend styling is
`legend=dict(font=dict(size=10))` (figures.py:1047).

### 1.4 The concept picker is **open**, not restricted

`_concept_plot_spec` is `METRICS_BY_ID.get(concept)` (figures.py:799) — any registered id from any
chart. app.py:1023-1029 builds the options from `config.get_plottable_metrics(chart)` **without a
ticker**, i.e. the full registry catalogue, and concatenates all three in the order
**fundamentals → growth → valuation**, each label prefixed `"{CHART_LABELS[chart]}: "`.

So the reference lets you pick anything and excludes the tickers that cannot answer. That is what
makes the exclusion notice the chart's job rather than the picker's, and it is why the
`pe_ratio`/`reit` case is reachable at all.

### 1.5 Ticker count — minimum 2 enforced, maximum 3 advisory

| | value | enforced? | source |
|---|---:|---|---|
| `MIN_COMPARISON_TICKERS` | **2** | **yes** — below it the builder returns `(None, [])` | figures.py:40, 846 |
| `SUGGESTED_MAX_COMPARISON_TICKERS` | **3** | **no** | figures.py:38 |

figures.py:35-37 is explicit that the maximum is advisory on purpose: *"a readability limit belongs
in the UI that picks the tickers … not in the rendering layer, where a hard refusal would turn a UI
mistake into a missing chart."* With one or zero tickers the builder draws nothing and app.py shows
`"Pick at least two tickers that can show this metric."` (app.py:1075).

### 1.6 No snapshot marker — **plainly, and by the reference's own decision**

figures.py:941-948, quoted because item 13 needs it in the reference's words rather than this brief's:

> **No snapshot point either, deliberately** — `build_valuation` grows one and this does not. Same
> reasoning as the mean lines: n markers, one per ticker, all at the same x just past the last filed
> period, would cluster into what reads as a vertical spike rather than n separate current values.

### 1.7 No mean line — none, of any kind

figures.py:930-931: *"No per-ticker mean lines (n of them would bury the data); the metric-level
reference line stays because it does not depend on the ticker."* The reference line **is** drawn
(`add_hline(y=ref_line, line_color="red", line_width=1)`, figures.py:1002), because it is a property
of the metric, not of a series.

So this chart does not inherit item 4's mean module at all, and figures.py:934-937 draws the
consequence for item 14 explicitly: *"The mean-line invariance that governs build_valuation has no
counterpart to protect here, precisely because this chart draws no means."*

---

## 2. Step 2 — the data axis: **no new export**, on the numbers

### 2.1 What the naive approach actually costs

A comparison needs one concept from one frame per ticker, and all three candidate frames
(`metrics_long`, `valuation_history`, `facts_growth`) live in the **core** per-ticker file. The
143 kB `facts_full` file is never touched — confirmed in the browser, **0 `.facts.json` requests**
across the whole session (§5.4).

| | raw | gzipped |
|---|---:|---:|
| one core file, median of 609 | 95.4 kB | ~19.2 kB |
| **a 3-ticker comparison (CRM, KO, MSFT)** | **338.5 kB** | **57.6 kB** |
| of a file's rows, the ones actually plotted (MSFT `pe_ratio`) | 74 of 2,657 | **2.8%** |

Yes, 97% of each file is discarded. That is the argument *for* a by-concept axis, and it is the wrong
number to decide on.

### 2.2 What a by-concept export would cost — measured, not estimated

Built the same column-major way item 2 builds the per-ticker files, for every plotted concept:

| catalogue | files | mean gzipped | largest |
|---|---:|---:|---|
| valuation | 14 | 182.4 kB | 320.0 kB (`pe_ratio`) |
| fundamentals | 45 | 81.6 kB | 298.9 kB (`roe`) |
| growth | 10 | 186.8 kB | 318.3 kB (`Revenue`) |
| **all** | **69** | **117.3 kB** | — |

**39.2 MB raw added to every nightly commit**, on a branch that keeps every night.

### 2.3 The decision

**Break-even is 6.1 tickers** (117.3 kB ÷ 19.2 kB). The suggested maximum is **3** and the minimum is
**2**, so the naive approach wins across the entire range the chart is designed for — by 2× at three
tickers, and by more for the valuation and growth concepts a comparison most often uses, where the
concept file is 182–187 kB against 58 kB for three tickers.

It wins by more than the arithmetic suggests, for a reason item 2 also named: **the comparison
tickers are the ones the reader has been browsing**, so their core files are already in
`DataProvider`'s cache. Measured in the browser (§5.4): removing a ticker and adding it back costs
**zero** additional requests.

**Verdict: no by-concept export. `main.py` and the pipeline are untouched.**

*A correction worth recording:* item 2's report put the break-even at **13 tickers**. That number
averaged only the 13 valuation concepts (186 kB) against a per-ticker core file of 14.0 kB. Averaging
all 69 concepts across three catalogues, and against today's 19.2 kB core file, gives 6.1. Both are
far above 3, so the conclusion is the same — but quoting 13 as if it still held would have been
wrong.

### 2.4 Reuse, not duplication

`framesFor` in `DataProvider` already fetches and caches a ticker's core file, and
`useTickerFrames` already consumes it for the chart tabs. This item adds **`useTickersFrames`**, a
sibling hook over the *same* cache — no second fetch path, no second parser. Results accumulate into
a map rather than replacing it, so a slow ticker never blanks the lines that already arrived and a
removed ticker is still cached when it comes back.

---

## 3. Step 3 — design

**Selection state** lives in `ComparisonView`: `concept`, `picked` (the ticker list) and `years`, each
independent. The ticker set is seeded once from the shell's current ticker and then owned by the
view — changing the sidebar ticker afterwards does not disturb a set the reader has edited. This is
unlike `ChartView`, whose state is per chart tab and keyed on the shell's ticker.

**The concept catalogue is open** (§1.4): all three chart catalogues concatenated in the reference's
order, labels prefixed with the chart name. The id-namespace split needs no handling here — growth
ids are XBRL concept names and the other two are metric names, but `registry.charts[chart].metric_ids`
already keeps them apart and registry ids are globally unique, so one flat list cannot collide. The
`value_column` split needs none either: `reconstructFrame` already selects `yoy_growth` for
`facts_growth` and `value` for the others, so `Frame.value` is always the right column.

**Exclusion goes through `selectMetricIds`** — the same function the pickers and all three chart
builders narrow with:

```ts
if (selectMetricIds(registry, metric.chart, ticker, [concept]).length === 0) { … }
```

There is exactly one implementation of "may this ticker show this metric" in the frontend, and this
chart uses it rather than reading `profile_visibility` itself. §5.3 is the check.

**Colour** is `COMPARISON_COLORS[position % 10]` with `position` from the requested list, per §1.1.

**Drawing** needed a new entry point, and it lives in the shared layer: `drawComparisonPanel` in
`panel.ts`, next to `drawPanel`, reusing `panelRefs`, `styleAxes` and `hline`. `createGrid` covers the
single-panel case unchanged (`makeGrid(1)` → 1×1). A `PanelSpec` variant would not have worked, for
three reference differences rather than taste: the hover template (`"%{fullData.name}: %{y}"` under
`hovermode: "x unified"`, so one box lists every ticker at that date, against `drawPanel`'s per-point
`Date: … Value: …`), the absence of any mean field, and the exclusion annotation no per-ticker panel
has. **No existing export changed** — the addition is purely additive.

---

## 4. What was implemented, by file

| file | new? | what |
|---|---|---|
| `src/charts/comparison.ts` | **new** | `buildComparison`, `MIN_COMPARISON_TICKERS`, `SUGGESTED_MAX_COMPARISON_TICKERS`, `COMPARISON_YEARS`. Pure, Node-runnable |
| `src/charts/panel.ts` | edited (**additive**) | `COMPARISON_COLORS`, `ComparisonTrace`, `ComparisonPanelSpec`, `drawComparisonPanel` |
| `src/data/DataContext.ts` | edited (**additive**) | `useTickersFrames` over the existing `framesFor` cache |
| `src/ComparisonView.tsx` | **new** | the tab: metric picker, ticker chips, window slider, exclusion notices, the plot |
| `src/comparison.css` | **new** | the controls. Defines no palette variables — they come from `.app` in `shell.css` |
| `src/App.tsx` | edited | the item-12 placeholder replaced. The resize effect was not touched |

Nothing outside `frontend/`. **No `main.py`, no export, no pipeline change** (§2.3).

---

## 5. Step 5 — verification

### 5.1 Against `build_ticker_comparison`, element-wise

The reference generator calls the real `figures.build_ticker_comparison` and reads the resulting
figure **object** (not `to_json`, which base64-encodes numeric arrays). The comparer imports the
shipped `data/load.ts` and `charts/comparison.ts`. `_window_frame` uses `pd.Timestamp.today()` when
`as_of` is `None`, so the reference emits the exact anchor it used and the comparer is handed the same
instant — the two windows cannot differ by the seconds between the processes.

| | |
|---|---:|
| scenarios | **20** |
| checks | **5,404** |
| traces compared (name, colour, mode, connectgaps, hovertemplate, length) | **50** |
| points compared (x and y, element-wise) | **2,500** |
| **failures** | **0** |

Also compared per scenario: the figure title, the exclusion list with its reasons **in order**, the
reference line as a shape, and the annotation list.

The 20 scenarios and what each is for:

| scenario | exercises |
|---|---|
| `pe_ratio` × AAPL, **O**, MSFT | **the `pe_ratio`/`reit` exclusion** |
| `p_ffo` × O, AMT, **AAPL** | the reverse — `p_ffo` hidden for `standard` |
| `net_interest_margin` × JPM, **AAPL** | a third profile exclusion |
| `pe_ratio` × **V, STZ, ERIE** | `"No Data"` — no share-count history |
| `pe_ratio` × **BKR, PSKY**, AAPL | `"No Data"` — thin share history |
| `pe_ratio` × **O, AMT** | every ticker excluded → `figure` null, `excluded` non-empty |
| `ev_ebitda` × **AAPL** alone | below `MIN_COMPARISON_TICKERS` → null, `excluded` **empty** |
| `NotAConcept` × AAPL, MSFT | unknown id → null, `excluded` empty |
| `pe_ratio` × **AAPL, AAPL**, MSFT | `dict.fromkeys` dedup |
| `Revenue`, `SharesOutstanding` | the growth catalogue's XBRL-name namespace |
| `roe` × JPM, BAC, C · `operating_margin` × KO, PEP, MO | fundamentals across profiles |
| `pe_ratio` × CRWV, FIG, AAPL | short history |
| `pe_ratio` at years = 1, 5, 15 | the window |
| `p_ffo` × 7 REITs · `pe_ratio` × **11 tickers** | many lines, and the colour wrap |

### 5.2 Colour stability

| check | result |
|---|---|
| a ticker excluded mid-list recolours nothing | **AAPL keeps `#1f77b4`, KO keeps `#2ca02c`** across O's exclusion at position 1 |
| the palette wraps | 11 tickers: the 11th is `#1f77b4` again, same as the 1st |
| removing a ticker *from the list* shifts the rest | confirmed, and it is the reference's semantics — see §1.1 |

The UI makes that legible rather than mysterious: the ticker chips are shown in order, so the
position that decides the colour is on screen.

### 5.3 The `is_hidden` guarantee, with no second implementation

Constructed directly: `pe_ratio` with `O` (profile `reit`, `profile_visibility.reit.pe_ratio ===
false`) in the set. Result, in the real browser:

- notice above the chart: **`O not shown — for profile 'reit' not shown.`**
- annotation on the figure: **`Not shown: O (for profile 'reit' not shown)`**
- traces drawn: `AAPL=#1f77b4`, `A=#d62728`, `AAOI=#2ca02c` — O absent, the others uncoloured by its
  departure

No second `is_hidden` was written. `buildComparison` calls `selectMetricIds`, the same function
`buildValuation`, `buildFundamentals`, `buildGrowth` and `offerableMetricIds` call — and the item-8
sweep's unchanged sha256 (§5.5) is the evidence that adding this caller changed nothing for them.

### 5.4 The data axis performs as predicted

Measured on a genuinely cold load (a distinct query string per run, because a hash-only navigation
does not reload and would carry the previous run's resource timeline):

| | predicted (§2) | measured |
|---|---|---|
| requests for a 3-ticker comparison | 3 core files | **3** — `AAPL.json`, `A.json`, `AAOI.json` |
| bytes | ~338 kB raw / ~58 kB gzipped | **278,707 bytes** raw (dev server, uncompressed) |
| `facts_full` requests | 0 | **0** |
| adding a 4th ticker | +1 | **+1** |
| removing a ticker and adding it back | +0 | **+0** |

### 5.5 Nothing else regressed

| check | result |
|---|---|
| `scripts/check-chart-width.mjs` | **24/24** |
| `scripts/check-table-format.mjs` | **6,107/6,107** |
| item-8 chart sweep — 3,936 figures, 213,205 points | sha256 `1987837d155d3adfc9252ccdf2406bab502dd555324fd14d113432e067f38e8a` — **unchanged** |
| item-11 CSV/copy harness — 609 tickers | **14,007** comparisons, 0 differences, 544,252 nulls empty |

`npx tsc -b`, `npx eslint .`, `npx vite build` — clean. `git status` shows six files, all inside
`frontend/`, plus the operator's own `task_new.md` and this report. No scratch files left behind; the
dev server and headless browser were stopped and confirmed down.

---

## 6. What items 13, 14 and 15 should know

### Item 13 — the snapshot marker: **this chart is out of scope by the reference**

Not merely excluded by a brief. `build_ticker_comparison`'s docstring (figures.py:941-948) states the
decision and the reasoning: n markers at the same x would read as a vertical spike, and *"the current
level for several tickers side by side is what the snapshot table already shows better."* There is
nowhere in `drawComparisonPanel` for a marker to attach, deliberately.

### Item 14 — outlier masking: **there is no mean line for the invariance rules to protect**

This chart draws none, of any kind (§1.7). figures.py:934-937 already says what that means: *"The
mean-line invariance that governs build_valuation has no counterpart to protect here … the only
computed line is `ref_line`, which is a property of the metric and not of any series, so masking
cannot move it."*

What item 14 *does* need to know about this chart:

- The reference's rule here is **per line, against that line's own median**, never a pooled one
  (figures.py:967) — different from the valuation grid's, and figures.py:973-975 says why it matters
  more here: *"these lines share one y-axis, so a single ticker's outlier flattens every other line
  too. On CRM/KO/MSFT it costs the whole chart a 5.0x y-range expansion."*
- It is **gated on `is_valuation`** (figures.py:970), so picking a fundamentals or growth concept
  ignores the flag rather than applying a rule whose precondition does not hold.
- `mask_outliers` is a parameter of `build_ticker_comparison`, and `comparison_outlier_report`
  (figures.py:870) is the separate function app.py uses to decide whether to *offer* the toggle. Both
  go through `_comparison_selection`, which is why they cannot disagree about which points exist —
  `buildComparison` will need the same split.
- The attachment point is `ComparisonOptions`, and the drawing point is `drawComparisonPanel`'s
  `traces`, which already takes the y array the mask would thin.

### Item 15 — the as-of control attaches at `ComparisonOptions.anchor`

Already plumbed and already used: `buildComparison(…, { years, anchor })` passes `anchor` to
`windowCutoff`, which is `_window_frame`'s anchor. The verification in §5.1 exercises it — the
reference's `pd.Timestamp.today()` is handed through this parameter for all 20 scenarios, so the path
is not theoretical.

**One thing is not built and item 15 owns it:** `_window_frame` bounds the window **above** as well as
below when `as_of` is given (figures.py:260), and `windowCutoff`/`seriesFor` currently apply only the
lower bound. The upper bound is one comparison in `seriesFor` and it is item 15's to add — the
inventory's §3.5 warning ("leaving the upper bound open would instead answer 'everything since that
date'") applies to this chart and the valuation chart alike.

---

## 7. One deliberate departure, and one thing not built

**The ticker set is seeded from the shell's ticker.** app.py defaults to the first three of the
universe (app.py:1030) with no link to the ticker being analysed; here the seed is the shell's ticker
followed by the universe order. The reader arrived on this tab from that company, and the remaining
two follow the reference's rule. It is the only place this view departs from app.py, and it is
recorded rather than absorbed.

**The share-history clause is not built.** app.py:1068 appends *" — no share-count history is
available for it"* to a `"No Data"` notice when `share_history_absent(ticker)` — which reads
`facts_full` for a `SharesOutstanding` series. This view fetches only the core file, and pulling a
143 kB facts file per ticker to refine one sentence would undo §2's entire argument. The notice reads
`"no values in this window"` without the clause. If it is wanted, the honest way is a per-ticker flag
in the export rather than a second fetch — that is an export change and would need its own cycle.

## 8. What to re-check by hand

**Open the Comparison tab and click a legend entry.** Per-ticker show/hide is plotly's native
behaviour and is the one thing here with no reference implementation to compare against — figures.py
delegates it, so this port delegates it too, and neither side has a test for it.

Also worth a look: pick a metric where your chosen tickers span profiles (`P/E` with a REIT in the
set is the ready-made case) and confirm the notice above the chart and the note under it agree, and
that removing the excluded ticker leaves the remaining lines exactly the colours they had.
