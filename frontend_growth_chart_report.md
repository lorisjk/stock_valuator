# The growth chart, rebuilt from the raw series

Rebuild-list item 6. The third and last chart over `panel.ts`, and the one that answers most of the
brief's questions the same way: *it does not go through the shared plotting functions at all.*

---

## 1. The reference, read before anything was written

### 1.0 The finding that reframes the rest

**`build_growth` calls neither `plot_metric` nor `plot_metric_dual`.** It is the only builder in
`figures.py` that inlines its own trace, its own `_style_axes` call and its own `add_hline`
(figures.py:660-680). `build_fundamentals` and `build_valuation` both delegate; this one does not.

That is not a stylistic note. Three of the brief's seven questions are phrased as *"what does
`build_growth` pass to `plot_metric`"*, and they all have the same answer — nothing, because there
is no call. In particular there is no `show_mean` argument to set or leave unset, no `ref_line`
parameter to feed from the registry, and no `percent` parameter either: the builder hardcodes the
last two and the first does not exist on this path.

### 1.1 The window — **15 years**

```python
def build_growth(ticker, facts, years: int = 15, growth_column: str = "yoy_growth", ...)   # :632-636
    filtered = _window_frame(facts, years=years, as_of=None)                               # :646
```

Fifteen, the fundamentals number, not the valuation chart's five. Nothing was inherited: this is
figures.py:635 read directly, as the brief asked.

It is load-bearing. The cutoff at 2011-08-26 drops **28,321 of `facts_growth`'s 242,180 rows**, and
because the empty rule is evaluated *after* the window, it changes which panels are blank, not just
how far back they run.

### 1.2 Mean lines — **none, and for a different reason than the fundamentals chart**

`plot_metric` takes `show_mean: bool = False` (figures.py:344). `build_fundamentals` never passes
it. `build_growth` cannot pass it, because it never calls `plot_metric`. Only `build_valuation`
sets it:

```python
plot_metric(fig, r, c, filtered, ticker, concept, ylabel, ref_line, percent,
            show_mean=True, harmonic=concept in HARMONIC_MEAN_CONCEPTS, ...)                # :752-753
```

Confirming the inventory's §3.3 claim. Verified as a check rather than assumed: **zero `Ø`
annotations across 53 tickers on both sides**, and all 296 growth shapes are reference lines. No
growth metric is in `HARMONIC_MEAN_CONCEPTS` either, so `mean.ts` is untouched by this chart.

### 1.3 The row height — **360**

```python
**_size(width, height, 500 * cols, 360 * rows),                                             # :684
```

A third distinct value: 400 valuation, 330 fundamentals, 360 growth. Layout key order differs again
too (`title, size, legend, hovermode` here, matching `build_valuation`, against fundamentals'
`title, size, hovermode, legend`) — irrelevant to the rendered figure, relevant to anyone who tries
to diff two Python figures byte-for-byte.

### 1.4 The reference line — **hardcoded in the builder, not read from the registry**

The brief asks which of the two it is, and if both, which wins. It is unambiguously the builder:

```python
fig.add_hline(y=0, line_color="red", line_width=1, row=r, col=col)                          # :680
```

The registry is not consulted, and structurally cannot be: `GROWTH_PANELS` is built as
`[(m.id, m.label) for m in _metrics_for(CHART_GROWTH)]` (config.py:2681) — a **two**-tuple that
drops `ref_line` and `percent` on the floor. Compare `VALUATIONS_TO_PLOT`, whose four-tuples carry
both into `plot_metric`. So there is no "which wins": only one of the two is ever read.

They agree today. All ten growth metrics are declared `Metric(..., 0, percent=True, ...)` —
`ref_line = 0`, `percent = True`, no exceptions (config.py:2476-2515, and the same in the exported
`registry.json`).

**This frontend reads the registry**, which is the one deliberate departure from the reference in
this cycle. Two reasons: the registry is the frontend's only source of truth — there is no
`config.py` in the browser — and inferring `percent` from the chart id is precisely the mistake
§3.2 of the inventory documents (`_percent_applies` resolves on `value_column`, not on a namespace
flag, because getting it wrong renders Apple's revenue as `10941700000000.00%`). Since the two
sources agree on all ten metrics, every figure produced is identical to the reference, which the
comparison in §3 measures rather than assumes.

**One line the placeholder rule depends on:** the `add_hline` sits *inside* the loop, *after* the
`continue` on the empty branch. A blank growth panel therefore gets no reference line. `drawPanel`
already behaves this way — it returns straight after `annotateNoData` — so this needed no code, but
it is checked explicitly: every figure has exactly as many shapes as traces, 296 of each.

### 1.5 Data source and value column — confirmed

`facts_growth`, `yoy_growth`. From the registry: `charts.growth = {"id_namespace": "xbrl_concept",
"value_column": "yoy_growth"}`, straight out of `CHART_SPECS` (config.py:2215).

What the export actually contains, measured rather than assumed:

| | |
|---|---|
| columns | `ticker`, `concept`, `end`, `yoy_growth` — **no `value` column at all** |
| rows | 242,180 |
| concepts | exactly the 10 growth ids, nothing else |
| tickers | 609 of 609 — not one has zero growth rows |
| nulls in `end` | 0 |
| nulls in `yoy_growth` | 49,480 |
| non-finite in `yoy_growth` | **0** |

The narrowing in `export_for_app` (main.py:2093-2096) is what makes the id-namespace split
un-trippable here: `facts_full` carries `value` and `yoy_growth` side by side on the same row, so
`Revenue` there means both "$109 bn" and "+4.2%" depending on the column — but `facts_growth` drops
`value` entirely, and `load.ts`'s `VALUE_COLUMN` maps the frame to `yoy_growth`. The wrong column
cannot be read because it is not there. `reconstructFrame` throws if `yoy_growth` is missing, so
the failure mode is a load-time exception, not a silently wrong chart.

### 1.6 Dual traces — **none, and no growth metric can have one**

`QUARTERLY_COUNTERPART = {m.id: f"{m.id}_quarterly" for m in METRICS if m.quarterly}`
(config.py:2685). No growth metric sets `quarterly=True`, so no growth id appears as a key —
checked against the exported `registry.quarterly_counterpart`, 0 of 10. No growth id collides with a
fundamentals or valuation metric id either (0 of 52 metrics share an id), so the
`new Map(registry.metrics.map(m => [m.id, m]))` lookup in all three builders is unambiguous.

Saying it rather than leaving it implied, as the brief asked: **item 5's `traces` list carries
exactly one entry on every growth panel.** The generalisation cost nothing here and was not needed
here; it will be needed by items 12 and 13.

### 1.7 The empty rule — the `plot_metric` rule, not the dual one

```python
series_values = series.dropna(subset=[growth_column])                                       # :666
if series_values.empty:
    _annotate_no_data(fig, r, col)
    continue                                                                                # :668-670
```

> **A growth panel is blank when no row in the 15-year window has a non-null `yoy_growth`.**

Same shape as the valuation chart — `!hasAnyValue(series)`. Two details that are easy to get wrong:

1. **What is drawn when it does *not* fire is `series`, not `series_values`.** The full windowed
   series with its nulls in place. `series_values` exists only to decide, never to draw — the same
   trap noted for `plot_metric_dual` last cycle, reached from a third direction. 207 of the 296
   drawn traces in the verification set contain at least one null, so this is not a corner case.
2. **`dropna` is on `[growth_column]` alone**, where `plot_metric` uses `["end", "value"]`. The two
   agree only because `facts_growth` has no null `end` — measured above, 0 of 242,180.

The rule fires on real data constantly: **249 blank panels across the universe's 4,229 visible
ones**, on 149 tickers. And it fires on the *interesting* branch, not just on absent data — **153
of those 249 have rows inside the window whose `yoy_growth` is null throughout**. Growth needs four
quarters of lead time and both values positive, so a young or loss-making ticker produces rows with
no growth value rather than no rows:

| ticker | profile | rows in window | blank because |
|---|---|---:|---|
| CRWV | `standard` | 10 per panel | 4 panels: rows present, every `yoy_growth` null |
| APLD | `standard` | 20-21 per panel | 4 panels, same |
| AUR | `standard` | 22 per panel | 4 panels, same |
| BMY | `pharma_medtech` | 1 | `OperatingIncomeLoss_TTM` |
| EQR | `reit` | mixed | 4 panels, incl. `FFO_TTM` — a REIT with a blank FFO growth panel |

### 1.8 Where the brief and the inventory turned out to be wrong

1. **"The single-trace case plus a fixed `y = 0` line."** Right about the *shape* of the output and
   wrong about how it is produced. `build_growth` shares no drawing code with the other two charts,
   and it hardcodes `percent=True` as well as the reference line. The inventory's §4.2 row —
   *"reference lines | `plot_metric`, `build_growth`, comparison"* — is the only place that hints at
   this, by listing `build_growth` separately from `plot_metric`.

2. **"The ids are `Revenue`, `NetIncomeLoss`, `SharesOutstanding` and the sector aggregates, and
   three of them also exist as facts concepts."** There are **ten** growth ids, and **all ten**
   exist as `concept` values in `facts_full` — not three. The "three" is inherited from inventory
   §3.2, which was written when the chart had three panels. The same staleness sits in two comments
   in the shipped code: `main.py`'s `export_frames` docstring says *"the charts read the narrow one
   (3 concepts, ~10x smaller)"*, and `app.py:30` says *"the charts want the 3 growth concepts"*.
   Both are now 10. (Left alone — out of scope, and neither affects behaviour.)

3. **"The seven sector-specific growth panels added recently mean profile coverage matters here more
   than on the other charts."** Backwards, measured. There are 10 metrics and 24 profiles, but only
   **five distinct growth catalogues** between them, and **19 of the 24 profiles share one**:

   | catalogue | profiles | ids |
   |---:|---|---|
   | 7 | 19 | the standard set |
   | 6 | `alt_asset_manager` | standard set minus `FCF_TTM` |
   | 6 | `financial` | minus `FCF_TTM`, `OperatingIncomeLoss_TTM`; plus `PPNR` |
   | 7 | `insurance_life`, `insurance_pc` | minus `FCF_TTM`; plus `CoreOperatingEarnings` |
   | 7 | `reit` | minus `EPS_TTM_CALC`; plus `FFO_TTM` |

   No profile sees more than **7** panels, so the grid is 3×3 or 2×3 and never anything else. The
   verification still covers all 24 profiles — the point is that the *variation* worth hunting is in
   the data, not in the profiles, which is where the ticker set was weighted.

4. **The inventory's §3.3 claim is correct** and was checked: only `build_valuation` passes
   `show_mean=True`.

---

## 2. What was implemented

| file | what |
|---|---|
| `src/charts/growth.ts` | **new** — `buildGrowth`: the 15-year window, the single trace, the empty rule, `mean: null` |
| `src/ChartView.tsx` | `growth: buildGrowth` in `BUILDERS`; the map is now total |
| `src/App.tsx` | the `REBUILT` list and the pre-rendered fallback branch removed |

### The shared layer needed no changes

`panel.ts`, `grid.ts`, `select.ts`, `mean.ts`, `valuation.ts`, `fundamentals.ts`, `contracts.ts` and
`load.ts` are untouched. The brief asked for a finding if they were not, so the converse is worth
stating precisely: **everything growth needs was already there**, including the two pieces most at
risk of being fundamentals-shaped —

- `PanelSpec.traces` takes a one-element list without a special case, and
- `drawPanel` returns immediately on `empty`, so the reference line lands only on drawn panels,
  which is exactly what `build_growth`'s `continue` does.

Checked mechanically as well as by inspection: the shared modules contain no growth-specific token.
The only two occurrences of "growth" anywhere in the layer are the forward-looking sentences in
`panel.ts`'s and `select.ts`'s docstrings, written in cycles 39 and 41 to predict this chart. They
were right.

`Chart.tsx` and the six `public/{AAPL,MSFT}_{chart}.json` figures it read are now unreferenced —
growth was the last consumer. The files are left in place (deleting them is outside this brief), and
`App.tsx` says so in a comment; Vite drops unimported modules from the graph, so they cost nothing
in the bundle.

---

## 3. Verification

Same instrument as the last two cycles: every annotation on ten fields in order, ten axis
properties, element-wise traces including nulls, every shape on nine fields, and the structural
orphan-axis check — run over **all three charts**, not just the new one.

**53 tickers covering all 24 profiles.** Weighted toward the empty rule rather than toward profiles,
for the reason in §1.8: 21 short-history or all-null tickers (CRWV, FIG, APLD, AUR, NAVN, SAIL,
TTAN, SNDK, PSKY, Q, HNGE, ALAB, ATO, AZO, BKR, BMY, CEG, COMP, CRDO, CRWD, EQR), both 6-panel
profiles (JPM, BAC, BX), the sector aggregates (`PPNR`, `FFO_TTM`, `CoreOperatingEarnings`), the
edge tickers from earlier reports (GD, NWS, NWSA, FSLR, ADM), and five cycle-33 candidates (GWRE,
SMTC, MORN, RGTI, APPF).

| | growth | valuation | fundamentals |
|---|---:|---:|---:|
| figures | 53 | 53 | 53 |
| traces | **296** | 309 | 502 |
| points, element-wise | **13,768** | 5,837 | 21,425 |
| annotations, 10 fields in order | **440** | 852 | 526 |
| — of which "No Data" | **72** | 117 | 75 |
| shapes, 9 fields | **296** | 309 | 144 |
| axis objects, 10 properties | **736** | 852 | 902 |
| orphan axes, both sides | **0** | 0 | 0 |
| domain-only axes, both sides | **0** | 0 | 0 |

**768 structural checks passed, 0 failed. 0 field-level differences on the growth chart.**
Plus **45 edge checks** in a second harness (below). 41,030 data points compared in total.

### The Step 4 list, item by item

| # | check | result |
|---:|---|---|
| 1 | panel sets identical, in order | ✓ 53 tickers, **24 of 24 profiles**, 50 at 7 panels and 3 at 6 |
| 2 | traces element-wise on x and y incl. nulls, plus every style field | ✓ 296 traces, 13,768 points, 0 differences |
| 3 | the empty rule on real cases | ✓ **72 blank panels on 31 of the 53 tickers**; 59 of the 72 have rows in window with every value null |
| 4 | reference lines and percent axes on exactly what the registry marks | ✓ 296 shapes, all `y=0`, red, width 1, **one per drawn panel and none on a blank one**; `.1~%` on every drawn y-axis and absent from every blank one |
| 5 | means and the window, asserted not assumed | ✓ **0 mean annotations both sides**; no point older than 2011-08-26; the window excludes 28,321 real rows, so it is not a no-op |
| 6 | zero orphan axes, both sides, every ticker | ✓ 736 growth axes, 2,490 across all three charts |
| 7 | items 4 and 5 unchanged | ✓ see §4 |
| 8 | `tsc -b`, `eslint .`, `vite build` | ✓ all clean; nothing outside `frontend/` changed |

### Checks that are not comparisons

Structural assertions that run against `figures.py` / `config.py` directly, so they fail if a future
pipeline change breaks the equivalence the frontend relies on:

| check | result |
|---|---|
| every growth metric has `percent: true` (what `build_growth` hardcodes) | ✓ 10 of 10 |
| every growth metric has `ref_line: 0` (what `build_growth` hardcodes) | ✓ 10 of 10 |
| no growth metric has a quarterly counterpart | ✓ 0 of 10 |
| no growth metric is harmonic | ✓ 0 of 10 |
| growth ids do not collide with any fundamentals/valuation metric id | ✓ 0 of 52 |
| `facts_growth` has no non-finite value | ✓ 0 of 242,180 |
| `facts_growth` has no duplicated `(ticker, concept, end)` with differing values | ✓ 0 |
| blank ⇔ zero non-null `yoy_growth` in window, per panel | ✓ 368 panels, 0 disagreements |
| subplot title = metric **id**, y-axis title = registry **label** | ✓ every panel |

### The edge harness — 45 checks

Cases with no natural ticker, run against `figures._make_grid`, `_select_concepts` and
`build_growth` itself:

- `makeGrid(n)` vs `_make_grid(n)` for **n = 0…13** — ✓ all 14.
- **A request only ever narrows.** Six request shapes against JPM (`financial`, which hides
  `FCF_TTM`, `OperatingIncomeLoss_TTM` and `FFO_TTM`): `null`, hidden-only, unknown-only, reversed
  order, hidden+visible+unknown mixed, and empty. Panels, figure-or-None and subplot titles all
  match; **no hidden id is surfaced by any request**, and a reversed request comes back in catalogue
  order (`Revenue, StockholdersEquity, PPNR`, not as asked).
- **Empty selection → no figure**, both sides (`build_growth` prints and returns `None`).
- **The missing-column branch.** `build_growth` returns `None` when `growth_column not in
  facts.columns` (figures.py:643-645), before it looks at panels. Reproduced by dropping the column
  on the Python side and by passing no `facts_growth` frame on the TS side: both return no figure,
  no panels, and still report the full `offerable` list for a picker.
- **`years = 0`** — a 6-panel figure in which *every* panel is blank. This is the sharpest test of
  the axis-reference rule, because all 12 axes are reachable only through their "No Data"
  annotations: one domain ref anywhere would orphan one. ✓ 0 orphans on both sides, and the two
  figures match on trace count (0) and point count (0).

### The two differences that are *not* in the growth chart

The wider ticker set turned up 26 y-value differences on the **fundamentals** chart — on APLD, AUR
and NAVN, none of which were in cycle 41's 42-ticker set. Both classes were tracked down rather than
tolerated, and both are pre-existing properties of `metrics_long`. Neither occurs in `facts_growth`
or `valuation_history`, which is now an assertion, not an observation.

**(a) ±infinity — 18 points, a real and deliberate divergence.** `metrics_long` holds 22 non-finite
values universe-wide, all `operating_margin_quarterly` / `fcf_margin_quarterly`, on three tickers
(APLD, AUR, QRVO). The export writes `null` and records the true value in the `nonfinite` sidecar;
`reconstructFrame` keeps the `null` deliberately, on the reasoning already in `load.ts` — *"a trace
point at Infinity would blow the y range for every other point in the panel."*

I expected to be able to dismiss this as a serialisation artifact, and checked: **it is not.**
plotly 6 encodes numeric arrays as base64 `bdata`, and `-inf` survives that as raw float64 bits —
decoded back out of a real AUR figure, `operating_margin · quarterly` still begins `[-inf, -inf,
…]`. So the Streamlit chart genuinely plots the infinity and the frontend genuinely plots a gap.
That is the intended behaviour of item 2's export, but this is the first cycle in which it was
measured rather than reasoned about.

**(b) Tie ordering — 8 points, no visible effect.** `metrics_long` has 9 duplicated
`(ticker, concept, end)` groups, 6 with differing values; NAVN has 32 rows all dated 2026-01-31 in
one concept. `plot_metric` sorts with `sort_values("end")`, whose default `kind="quicksort"` is
**not stable**; `seriesFor`'s comparator breaks ties on row index and is. Verified as bounded rather
than waved through: every differing index sits on a duplicated date, and the **(x, y) multiset is
identical** on both sides — the drawn point set is the same, only its position in the array moved.
The classifier fails the run if a difference is *not* of one of these two shapes.

### What was not verified

**Nothing was opened in a browser.** Every claim compares the figure spec this code hands `<Plot>`
against the one `build_growth` hands plotly.py. Whether 3×3 panels at 360px per row read well at a
real container width is a visual judgement the spec comparison cannot make.

---

## 4. Items 4 and 5 are unchanged

Two independent guarantees.

**Against the reference.** Both comparisons were re-run in full alongside the new one, over the same
53 tickers: valuation 309 traces / 5,837 points / 852 annotations / 852 axes, fundamentals 502
traces / 21,425 points / 526 annotations / 902 axes, **0 field-level differences** beyond the two
classified `metrics_long` classes above. This is the guarantee that does not depend on knowing which
files were edited — had the shared layer broken, this is what would have caught it.

**Byte-identity.** The harness takes the source root as a parameter, so it was run twice: once
against `frontend/src`, once against a reconstructed pre-cycle tree (this cycle's `growth.ts`
removed and the `ChartView.tsx` edit inverted). The serialised valuation and fundamentals specs
across all 53 tickers:

| chart | bytes | identical to the pre-cycle tree |
|---|---:|---|
| valuation | 592,130 | **yes** |
| fundamentals | 1,090,926 | **yes** |

The pre-cycle tree produces no growth figure for any of the 53; the current one produces 53. The
harness output is deterministic — two runs of the same tree are byte-identical — so the comparison
is meaningful.

---

## 5. What the reference turned out to be, for items 7, 8, 12, 13 and 14

1. **`build_growth` is not `plot_metric` with different arguments.** Anything that changes the
   shared drawing layer has to be applied to `build_growth` separately or it will silently not reach
   the growth chart on the Streamlit side. Item 14 (outlier masking) is the live case: its
   annotation and its `drawn`/`filtered` split live inside `plot_metric`, so growth would not get
   them — and figures.py's own calibration comment says growth **must not** get them anyway
   (*"24.7% of growth series have a non-positive median … 85% would fire at k=4. That is not the
   rule finding outliers, it is the rule being meaningless"*). The frontend's `PanelSpec` has one
   `traces` list for all three charts, so the layer will happily mask a growth panel unless
   something stops it. **The stop belongs in the growth builder, not in `panel.ts`.**

2. **`percent` and `ref_line` are declared twice for growth**, in `config.METRICS` and again as
   literals inside `build_growth`, and nothing keeps them in step. They agree on all ten metrics
   today; the frontend reads the registry (§1.4). If anyone ever adds a growth metric with
   `percent=False` or a non-zero `ref_line`, Streamlit and the frontend will disagree, and only the
   frontend will be right. Two of this report's structural checks exist to catch that.

3. **Item 8's years slider already works for growth — with a caveat.** `app.py:919` builds it as
   `st.slider("Window (years)", 1, 15, 15)`, so the growth default is the *maximum*, unlike
   valuation's 5-of-15. `buildGrowth` takes `years` through the same options object as the other
   two, and `years = 0` was tested end to end (§3): both sides produce a full grid of blank panels
   rather than `None`, which is the behaviour the slider's floor of 1 currently hides.

4. **Item 7 inherits a latent bug in the Streamlit picker.** `app.py:916` reads
   `default = [i for i in ids if i in ("Revenueyoy_growth")]` — that is a *string*, not a tuple, so
   `in` is a substring test. It happens to select `Revenue` and nothing else, so it works by
   accident. `app.py:928` has the same shape at `("pe_ratio")`. A rebuild that ports the defaults
   literally will reproduce a coincidence; a rebuild that ports the *intent* should state what the
   default set actually is.

5. **Growth's panel count is capped at 7 and its grid at 3×3.** `build_growth` carries a comment
   about "one row of seven" being a 3500px figure, from when it did not wrap. It wraps now, via the
   same `_make_grid`. Item 12's comparison chart is the one that can exceed this.

6. **`facts_growth` is the only frame with no non-finite values and no meaningful duplicate rows.**
   Items 12 and 13 read `metrics_long` and `valuation_history`, and §3 records what each of those
   carries. `valuation_history` is clean on both counts; `metrics_long` is not, and item 14's
   median-based rule will meet the 22 infinities before anything else does — `outlier_points` runs
   on the Python side where they are still `-inf`, and on the frontend side where they are `null`.

7. **The `nonfinite` sidecar is still unread by any frontend code.** `reconstructFrame` builds
   `nonfiniteRows` and nothing consumes it. Item 13 or 17 is the natural place: a panel can say "the
   value is infinite" rather than showing a gap that looks like missing data. It is now measured
   rather than hypothetical — 22 points, 3 tickers, 2 concepts.

No scratch files were left behind.
