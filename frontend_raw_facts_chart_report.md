# The raw facts chart — item 16

The distinction the brief asked me to confirm before writing anything is **real**, and the chart is
stranger than the brief's framing: it is the only builder in `figures.py` that never calls
`_style_axes`, the only one that draws `go.Bar`, and the only one that sets no `hovermode`. Three
absences, each of which would have been an invisible mistake to get wrong.

One correction to the Context section, in §1.2: the derived filter is **not** a suffix rule.

---

## 1. Step 1 — the reference, read exactly

### 1.1 Chart against table — genuinely two features

| | Data tab's "Raw & derived facts" (items 9-11) | **Raw Facts tab** (this item) |
|---|---|---|
| reference | `render_data_section` on a pivot (app.py:405) | `build_raw_facts` (figures.py:1100) |
| shape | one table, concepts × periods | one **bar panel per concept** |
| controls | show-all-periods, a three-way raw/derived/all radio | include-derived checkbox, concept multiselect, years slider |
| extras | CSV download, copy block, display formatting | none |
| source frame | `facts_full` | `facts_full` |

They share their source frame and one rule — what counts as derived (§1.2) — and nothing else. The
inventory did not conflate them; the shell's own placeholder text already said *"one bar panel per
XBRL concept"*, which turned out to be exactly right.

### 1.2 `available_raw_concepts` — and the Context's premise corrected

figures.py:1081-1097:

```python
rows = facts[(facts["ticker"] == ticker)].dropna(subset=["value"])
concepts = set(rows["concept"].unique())
if not include_derived:
    queried = set(get_concept_candidates(ticker))
    concepts &= queried
return sorted(concepts)
```

Three steps: rows with a **non-null value**, their distinct concepts, then — unless `include_derived`
— intersected with `get_concept_candidates(ticker)`'s **keys** (config.py:2176 returns a dict; `set()`
of it takes the keys).

> The brief's Context says derived concepts are excluded by *"the `_TTM`/`_QUARTERLY`/`_CALC` suffix
> family the data tab's raw/derived split already established how to detect."* **The suffix family is
> not what either feature uses.** `available_raw_concepts` keeps what the pipeline *queried* and drops
> everything else; derived concepts are simply what is left over. And the data tab agrees —
> `pivot.ts`'s `factIsDerived` is literally `!candidates.has(concept)`. The suffix helper (`factBase`)
> exists in `pivot.ts` for a different job: **grouping** a concept next to its own derivations in the
> column order, not classifying them.

So the two features share one definition of "derived" rather than two that agree by accident, and
this chart reuses `candidatesFor` unchanged.

**No profile narrowing here**, and the docstring says why: *"facts_full is already
post-filter_hidden_rows, so profile visibility is respected without consulting is_hidden here."* So
there is no `selectMetricIds` call and there should not be one.

### 1.3 Panel furniture — three absences

`build_raw_facts` (figures.py:1120-1150) draws **only** a trace or the "No Data" placeholder:

- **`go.Bar`, not `go.Scatter`** (figures.py:1133), with `marker_color=_PRIMARY_COLOR` and
  `hovertemplate="Date: %{x|%d.%m.%Y}<br>Value: %{y}<extra></extra>"`. No `mode`, no `line`, no
  `connectgaps`.
- **No `_style_axes` call at all.** It is the only builder in the file that never calls it, so these
  panels get no y-axis title, no `dtick="M24"`, no `%Y` tick format and no percent format. Confirmed
  the hard way in §4.1, which compares those four axis fields explicitly.
- **No mean line and no reference line.** The brief's guess was right and the reason is structural
  rather than aesthetic: there is no registry entry behind a raw XBRL tag to carry a `ref_line`, and
  `mean.ts` is never reached.

A fourth, found rather than looked for: **no `hovermode`**. `update_layout` (figures.py:1144) sets
`title_text`, the size and `legend=dict(font=dict(size=9))` and nothing else, where every other
builder passes `hovermode="x unified"`.

**No outlier masking**, confirming item 14's valuation+comparison scope: `build_raw_facts` has no
`mask_outliers` parameter, and `outlier_points`' own scope note (figures.py:190-199) restricts the
rule to valuation multiples on the grounds that only that frame has a positive median everywhere.

### 1.4 The window

`_window_frame(facts, years=years, as_of=None)` at figures.py:1110 — **`as_of` hard-coded `None`**, so
§5.1 of the as-of report still holds. `years` defaults to **15** in the builder (figures.py:1103) and
the slider is `st.slider("Window (years)", 1, 15, 15, key="raw_years")` (app.py:1119). The two agree,
as they do for the other three charts.

One asymmetry worth naming: `available` is computed from the **unwindowed** facts while the series
comes from the **windowed** frame. A concept can therefore be offered, selected and drawn as a "No
Data" panel because the window emptied it — the same shape as the other charts' `empty` flag.

### 1.5 Panel ordering

`sorted(concepts)` (figures.py:1097) — plain code-point order, with no registry catalogue to inherit
from. The request narrows but never reorders: `[c for c in available if c in set(concepts)]`
(figures.py:1112) iterates `available`.

Visible in §4.9: AAPL's defaults render as `NetIncomeLoss`, `Revenue`, `StockholdersEquity` — sorted,
not in app.py's `Revenue, NetIncomeLoss, Assets, StockholdersEquity` default order.

### 1.6 Concept counts — measured across all 609 tickers

| | min | median | mean | max |
|---|---:|---:|---:|---:|
| raw (`include_derived=False`) | **11** (ERIE) | 17 | 16.7 | **22** (AIZ) |
| with derived (`include_derived=True`) | 22 | 34 | 33.7 | **43** (GL, HIG) |

No adjustment needed. `makeGrid` caps at 3 columns and derives rows from the count, so the worst case
is 43 panels → 15 rows → 4,950px, which is the reference's own arithmetic. And the practical case is
much smaller: the picker opens on at most four concepts (§4.9 shows three for AAPL, because `Assets`
is not in its candidate list).

---

## 2. Step 2 — design

### 2.1 Data source — `facts_full`, already filtered upstream

`tickers/{T}.facts.json`'s `facts_full` frame, reached through the existing `useTickerFacts` hook
(item 9) — no new fetch, no new file. The ticker filter is implicit in a per-ticker file.

The **profile** filter already happened in the pipeline (`filter_hidden_rows`, per §1.2's docstring),
so reproducing it client-side would have been the redundancy the brief warned about. The **candidate**
filter did *not* already happen — the export carries derived concepts, which is exactly what the data
tab's raw/derived radio needs — so that one is reproduced, from `concept_candidates.json` via the
existing `candidatesFor`.

### 2.2 Picker catalogue

Computed per ticker from the loaded facts, not from the registry. The narrowing discipline is kept in
shape — `offerable` comes from `availableRawConcepts`, the same function the builder narrows with, so
a checkbox can never offer a concept the builder would drop — but it is a **different** narrowing
from `selectMetricIds`, because there is no `profile_visibility` row for an XBRL tag.

One decision the reference does not force: `availableRawConcepts(facts, null, false)` returns **empty**
when the candidates file is missing, not everything. Silently showing every derived column because a
7.8 kB file failed to load would be the wrong way to fail.

The picker itself is local to `RawFactsView` rather than a generalised `MetricPicker`: that component
is typed on `ChartId`, looks up `Metric` labels and calls `defaultSelection`, and all three are
registry concepts this chart does not have. It keeps the same shape — All / None / Default, catalogue
order, rebuilt by filtering `offerable` — and shows the id alone, because here the id *is* the name.

### 2.3 Panel furniture — a third entry point, `drawBarPanel`

`drawPanel` always emits `type: "scatter"` and always calls `styleAxes`, so this chart could not go
through it. `drawBarPanel` sits beside `drawComparisonPanel` — the pattern item 12 established — and
uses `panelRefs`, `annotateNoData` and `PRIMARY_COLOR` unchanged.

**The shared layer needed three small widenings, all additive:** `Trace.type` became
`"scatter" | "bar"` with `mode` optional; `Marker`'s `size`/`symbol`/`line` became optional (a bar's
`marker_color` carries none of them); and `createGrid` took an optional `hovermode` that omits the key
when `null`. No existing caller changed behaviour — proved byte-for-byte in §4.7.

The "no mean, no reference line" case needed **no** new conditional: those are `PanelSpec` fields this
chart's spec simply does not have.

### 2.4 The window

`years` 1-15 defaulting to `RAW_YEARS = 15`, taken from the builder's own constant rather than
restated — the same rule `DEFAULT_YEARS` follows for the other three. `seriesFor` is called **without
its `until`**, which is how `as_of=None` is spelled in this port since item 15.

---

## 3. Step 3 — what was implemented

Seven files, all inside `frontend/`:

| file | change |
|---|---|
| [`src/charts/raw.ts`](frontend/src/charts/raw.ts) | **new.** `availableRawConcepts`, `buildRawFacts`, `RAW_ROW_HEIGHT`, `RAW_YEARS`, `RAW_DEFAULT_CONCEPTS`. |
| [`src/charts/panel.ts`](frontend/src/charts/panel.ts) | `drawBarPanel`; `Trace.type` union; `Marker` loosened; `createGrid`'s optional `hovermode`. |
| [`src/RawFactsView.tsx`](frontend/src/RawFactsView.tsx) | **new.** The derived toggle, the picker, the window slider, the plot. |
| [`src/raw-facts.css`](frontend/src/raw-facts.css) | **new.** |
| [`src/App.tsx`](frontend/src/App.tsx) | the placeholder replaced. |
| [`src/shell/navigation.ts`](frontend/src/shell/navigation.ts) | `"raw"` added to `tabDrawsFigure`. |
| [`scripts/check-chart-width.mjs`](frontend/scripts/check-chart-width.mjs) | six new checks and a scoped selector. |

### 3.1 The hand-off that worked

The state-persistence report predicted: *"A fourth figure-bearing tab must be added to
`tabDrawsFigure`, not to `isChartTab`."* It was, and the prediction was load-bearing — §4.8 shows the
three failures that appear without it. `TabPanel` also gave this tab persistence for free: the
picker, the derived toggle and the window all survive a tab switch without a line of new code.

---

## 4. Step 4 — verification

### 4.1 Against the reference, element-wise

**360 scenarios · 182,330 checks · 0 failures.** 36 tickers × {derived on, off} × five
window/selection combinations. The sample is the concept-count extremes from §1.6 (ERIE, ACT, ARE,
BXP at the bottom; AIZ, GL, HIG, MET, AIG at the top) plus a profile spread (JPM, O, XOM, KO, CRM,
AAOI, AAPL) and 20 random.

Compared per scenario: `available_raw_concepts`' **full list including order**, the panel set, every
trace field, every annotation, `shapes`, the title, the height, the legend font size, **`hovermode`**,
and **every axis's `anchor`, `domain`, `showticklabels`, `showgrid`, `zeroline`, `dtick`, `tickformat`
and `title`** — the last three specifically so the absent `_style_axes` call is asserted rather than
assumed. **5,395 bar panels and 202 "No Data" panels** drawn across the sweep.

`_window_frame` resolves its own anchor from `pd.Timestamp.today()` and `build_raw_facts` hard-codes
`as_of=None`, so there is no parameter to pin it with. `pd.Timestamp.today` was patched to one fixed
instant and the same instant handed to the JS side — the only way to make the two windows provably
identical rather than identical-if-the-clock-cooperates.

### 4.2 The years window

Covered at 15, 5 and 1 years in every scenario above, against
`_window_frame(facts, years, as_of=None)`. Live: AAPL `NetIncomeLoss` goes from **60 points
(2011-09-24 … 2026-06-27)** at 15 years to **12 points (2023-09-30 … 2026-06-27)** at 3.

### 4.3 No `as_of` leaks in — demonstrated both ways

`RawFactsView` takes only `ticker`; the sidebar's `asOf` is not among its props, so the leak is
impossible by construction. Shown live anyway, because "impossible by construction" is what the
previous four cycles kept finding exceptions to:

| with the sidebar's as-of set to **2019-03-15** | |
|---|---|
| **Raw Facts**, AAPL `NetIncomeLoss` | 60 points, ending **2026-06-27** — unchanged |
| **Valuation**, same moment, same page | 20 points, ending **2018-12-29** — bounded |

The second row is what makes the first one evidence: the control is demonstrably live and the raw
chart demonstrably ignores it.

### 4.4 No outlier masking control

Asserted live on every raw-facts reading in §4.9: `document.querySelector('.raw-facts .outliers')` is
null. Structurally, `RawFactsView` imports neither `OutlierControls` nor `outliers.ts`, and
`buildRawFacts` has no `mask` option — matching `build_raw_facts`, which has no `mask_outliers`
parameter.

### 4.5 Panel ordering

Asserted over **all 609 tickers**: `availableRawConcepts` is code-point sorted, and a **reversed**
request comes back in catalogue order. Visible live — AAPL's defaults render `NetIncomeLoss`,
`Revenue`, `StockholdersEquity`, not in app.py's default-list order.

### 4.6 The picker's option list

The `available_raw_concepts` comparison in §4.1 covers this for 36 tickers including both extremes.
Four more properties were checked across **all 609 tickers — 4,263 checks, 0 failures**:

- raw ⊆ derived-inclusive, and no non-candidate ever leaks into the raw list;
- a reversed request does not reorder the panels;
- an empty selection produces **no figure at all** (`build_raw_facts`'s `None`);
- a missing candidates file narrows to **nothing** with derived off, and changes nothing with it on.

The measured range came out of the same pass: **11 (ERIE) … 22 (AIZ)** raw, **22 … 43** with derived.

### 4.7 Nothing else regressed

Reverted-tree A/B, six baselines:

| baseline | before | after |
|---|---|---|
| item 8 — three charts, 3,936 figures / 465,488 points | `fe09bcf21e00…` | **same** |
| item 13 — the snapshot marker | `f732b8901ea7…` | **same** |
| item 14 — masking + report | `e1aea0c8e786…` | **same** |
| item 15 — the as-of bound | `149d2d546fa2…` | **same** |
| item 12 — comparison figures | `7e17bb1c333e…` | **same** |
| item 11 — CSV / copy text | `55fd62aff02f…` | **same** |

All six are byte-for-byte the numbers the previous cycles recorded, which is what makes the three
widenings in §2.3 provably additive rather than merely intended to be.

`check-tab-state` **13/13** · `check-table-format` **6,107/6,107** · `npx tsc -b`, `npx eslint .`,
`npx vite build` clean · seven files, all inside `frontend/` · no scratch files left behind.

### 4.8 The width harness — **36/36**, up from 30

Six new checks (3 chart tabs × 2 sidebar states) for the raw-facts chart being *revealed* rather than
mounted, and the measurement selector now scopes by view (`.comparison`, `.raw-facts`) rather than
resting on DOM order, since three tabs can hold a figure at once.

**Verified by failing.** With `"raw"` removed from `tabDrawsFigure` and everything else in place:

```
FAIL raw -> Growth (YoY) -> raw, sidebar collapsed: container 1516px, svg 1159px
FAIL raw -> Fundamentals -> raw, sidebar collapsed: container 1516px, svg 1159px
FAIL raw -> Valuation    -> raw, sidebar collapsed: container 1516px, svg 1159px
33/36
```

357px of empty container — the regression this cycle would have shipped, caught by the line the
previous cycle left behind for exactly this.

### 4.9 Live

| | offered | picked | traces | trace type | y-axis title | `dtick` | masking control |
|---|---:|---|---:|---|---|---|---|
| AAPL, defaults | 17 | NetIncomeLoss, Revenue, StockholdersEquity | 3 | `bar` | **null** | **null** | **absent** |
| AAPL, include derived | **35** | unchanged | 3 | `bar` | null | null | absent |
| AIZ (most concepts) | **22** | same three | 3 | `bar` | null | null | absent |
| ERIE (fewest) | **11** | same three | 3 | `bar` | null | null | absent |

Bar colour `#1f77b4`, panel height 330 for one row, and the **"None" button** yields
*"Nothing selected, or no raw facts for this ticker."* with no plot at all — app.py:1123's fallback.

Only three of the four default concepts are picked for AAPL: `Assets` is not in its candidate list,
so it is not offered, and app.py's `[c for c in (…) if c in options]` drops it on both sides.

---

## 5. For items 17-19

1. **`tabDrawsFigure` now has four members and will keep growing.** Any new tab holding a `<Plot>`
   goes there, never in `isChartTab`. The width harness's per-view selectors are the other half —
   add a scope when you add a tab.
2. **Item 17 (the empty-panel notice)** has a second home now. `empty_valuation_panels` is
   valuation-only in the reference, but this chart produces "No Data" panels routinely (202 in the
   verification sweep) because availability is computed unwindowed and the series is windowed. Worth
   deciding whether the notice is valuation-only by design or by omission before building it.
3. **`drawBarPanel` is deliberately minimal** — trace and placeholder, nothing else. If a later item
   wants axis styling here, the thing to check first is whether `figures.py` grew a `_style_axes`
   call, because today its absence is the specification.
4. **The raw-facts catalogue is the only per-ticker one.** Anything that reasons over "all charts"
   (an encyclopedia entry, a coverage matrix, item 20/21) has three registry-backed catalogues and
   this one, which is computed from data and differs per ticker. It has no labels, no descriptions
   and no profile row, so it does not belong in a metric encyclopedia at all.
5. **`concept_candidates.json` is now load-bearing for two features** — the data tab's raw/derived
   split and this chart's catalogue. It is fetched once and shared; the failure mode is handled
   (empty catalogue, visible error) rather than silent.
