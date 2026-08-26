# The fundamentals chart, rebuilt from the raw series

**Date:** 2026-08-26
**Touched:** `frontend/` only — one new builder, one new view, two edited modules, one file renamed.
`git status` shows nothing changed outside `frontend/` beyond the operator's own `task_new.md`.

Rebuild-list **item 5**, and the first reuse of the drawing layer item 4 built. **25 checks over
42 tickers spanning all 24 profiles, all passing** — 426 fundamentals traces (109 TTM, 108
quarterly), 21,106 points compared element-wise, 414 annotations field by field, 732 axis objects.
The valuation chart's output is **byte-identical** to the pre-refactor baseline over 50 tickers.

Three things the brief asked me to check rather than assume turned out differently than it stated.
They are in §6.

---

## 1. Where the dual case lives

`PanelSpec` gained a **`traces: PanelTrace[]`** list in place of its single `x`/`y` pair, and
`drawPanel` iterates it. `plot_metric` and `plot_metric_dual` collapse into one function, because
they differ only in how many traces they push.

```ts
export interface PanelTrace {
  name: string;                 // "pe_ratio" | "operating_margin · TTM" | ...
  x: (Date | string)[];
  y: (number | null)[];         // nulls kept in place
  mode: string;
  color: string;
  width?: number;               // omitted from the emitted trace when undefined
  opacity?: number;
  connectgaps?: boolean;
}
```

### Which later items this shape serves

| item | what it needs | served? |
|---|---|---|
| **5** fundamentals | TTM + quarterly in one cell | ✓ two entries |
| **12** comparison | N traces, one per ticker, each with its own colour and name | ✓ N entries — the same generalisation |
| **13** snapshot marker | one extra `mode: "markers"` trace on a valuation panel | ✓ one more entry, and `mean` is a separate field it cannot reach |
| **14** outlier masking | a different `y` drawn from the one the mean uses | ✓ already separate fields; masking edits `traces[0].y` only |
| **6** growth | one trace, a fixed `y = 0` reference line | ✓ but needs nothing new — it is the single-trace case |

A sibling `drawDualPanel` would have served item 5 and none of the others: items 12 and 13 are
*N*-trace and *heterogeneous*-trace problems, not two-trace ones. Every caller would then have had
to choose between two functions on a rule ("does this panel have exactly two lines?") that stops
being true at item 12.

### What must not change, checked rather than assumed

The single-trace path is verified against 66 tickers in the previous report, so the refactor had to
be output-preserving. The valuation spec for 50 tickers was serialised **before** touching
`panel.ts` and compared byte-for-byte afterwards:

```
VALUATION BYTE-IDENTICAL to the pre-refactor baseline (50 tickers)
```

That is byte identity, not field equality, so it also pins **key order**. The emitted trace keeps
`type, mode, name, x, y, line, [opacity], [connectgaps], hovertemplate, xaxis, yaxis` — the optional
two are conditional spreads rather than post-hoc assignment, precisely so an absent `opacity` is
absent from the JSON and the surviving keys stay in their original positions.

`line` is `{color}` when no width is given and `{color, width}` when one is, which is what makes the
valuation trace (no width, plotly's default 2) and the dual TTM trace (width 1.5) both exact.

### Trace styling, off the implementation

| | TTM line | quarterly line | valuation / single |
|---|---|---|---|
| `mode` | `lines+markers` | **`lines`** — no markers | `lines+markers` |
| `name` | `{id} · TTM` | `{id} · quarterly` | `{id}` |
| colour | `#1f77b4` | **`#ff7f0e`** | `#1f77b4` |
| `line.width` | **1.5** | **0.8** | absent (plotly default) |
| `opacity` | absent | **0.6** | absent |
| `connectgaps` | `true` | **absent** | `true` |
| hovertemplate | `Date: %{x|%d.%m.%Y}<br>Value: %{y}<extra></extra>` | same | same |

Four fields distinguish the two lines, not one. The `connectgaps` asymmetry is the least obvious and
was easy to miss: the TTM line bridges a null, the quarterly line breaks at one. Both are reproduced
because the reference does it, not because either is better.

The colours are pinned rather than left to plotly's cycle for the reason figures.py:19–36 gives —
one figure holds every subplot, so an automatic cycle would give each panel a different colour and
imply a distinction that is not there.

---

## 2. The empty rule, exactly

> **A dual panel is blank when the *TTM* series has no value in the window — whatever the quarterly
> series holds.**

From `plot_metric_dual`:

```python
ttm_valid = ttm.dropna(subset=["end", "value"])
if ttm_valid.empty:
    _annotate_no_data(fig, row, col)
    return
```

The quarterly series is never consulted for that decision. The comment states the reason: *"the
quarterly line alone would be read as the metric itself"*. The rule is **not** "no data in either",
and it is **not** symmetric — the reverse case (TTM present, quarterly absent) draws the TTM line
alone and is perfectly normal.

### The disagreement cases are real, not synthetic

Eight (ticker, metric) pairs in the universe have an empty TTM series and a non-empty quarterly one
inside the fifteen-year window:

| ticker | metric | quarterly points | panel |
|---|---|---:|---|
| **GD** | `payout_ratio` | **44** | blank |
| VTRS | `payout_ratio` | 10 | blank |
| CEG | `payout_ratio` | 12 | blank |
| PSKY | `payout_ratio` | 5 | blank |
| EQR | `ffo_margin` | 4 | blank |
| NWS / NWSA | `payout_ratio` | 3 each | blank |
| VLTO | `payout_ratio` | 2 | blank |

**GD is the case worth naming**: 44 quarterly values, zero TTM values, and the panel renders "No
Data" **by design**. Both implementations blank it, verified per ticker:

```
GD/payout_ratio:  panel 6  TTM 44 rows / 0 non-null | quarterly 44 rows / 44 non-null
                  traces for this panel: []   react No Data=True   reference No Data=True
```

GD, CEG, NWS, NWSA and EQR are all in the verification set. The branch is additionally exercised
**synthetically** on both sides — a two-row TTM series that is all null against a quarterly series
that is not — so the branch stays covered if the universe ever loses the real cases. The reverse
shape is in the set too: ACGL and FSLR draw `payout_ratio`'s TTM line with no quarterly trace.

### The interaction with the axis-reference rule

A blanked dual panel has **no trace at all**, so its placeholder must use bare axis ids — the rule
from the placeholder fix applies here unchanged, and this chart produces 48 such panels in the
verification set. A dual panel that draws only one of its two lines *does* have a trace, so its
mean/reference-line domain references are safe.

The structural check runs over both charts: **zero orphan axes on both sides, for every ticker.**

---

## 3. Quarterly-counterpart visibility

`build_fundamentals` chooses its path with:

```python
quarterly_concept = QUARTERLY_COUNTERPART.get(concept)
if quarterly_concept and not is_hidden(ticker, quarterly_concept):
    plot_metric_dual(...)
else:
    plot_metric(...)
```

**The second half of that guard is a no-op in every configuration this registry can express**, and
that matters because the registry export carries no per-`_quarterly` visibility — `profile_visibility`
is keyed on the 52 `METRICS` ids, none of which is a `_quarterly` name. If the guard could bite, the
frontend could not answer it.

It cannot, for two reasons that compose:

1. `config.is_hidden` strips a `_quarterly` suffix and tests the **base** name as well as the full
   one, so `is_hidden(t, "operating_margin_quarterly")` is true whenever `is_hidden(t,
   "operating_margin")` is.
2. **No `PROFILE_HIDDEN` set contains an explicit `_quarterly` id** — checked across all 24
   profiles, zero such entries.

So a counterpart is hidden exactly when its base metric is, and a hidden base never reaches the
loop. Measured across all 609 tickers × their visible fundamentals metrics: **0 of 1,846 dual
candidates diverge.** The verification asserts this against `is_hidden` itself rather than restating
it — 129 dual and 237 single decisions over the set, all matching.

The frontend therefore uses `registry.quarterly_counterpart[id]` alone, and that is sufficient
**because the equivalence holds**, not because the guard was ignored. If a future profile hides a
`_quarterly` id explicitly, this check fails and the export needs a new field. That is the
right failure mode.

**The id-namespace note (§3.2)** was respected without needing special handling: `revenue_yoy_growth`
and `income_yoy_growth` sit on the *fundamentals* chart with `percent: true` despite their names,
and nothing here infers anything from a name — `metric.percent` and `metric.ref_line` come straight
off the registry entry. 21 of the 29 fundamentals metrics are percent, and the verification confirms
the percent tickformat lands on exactly those: **247 percent axes over 318 drawn panels**, none
elsewhere.

---

## 4. Verification

Same instrument as the placeholder fix — every annotation on all ten fields in order, ten axis
properties, element-wise traces, and the orphan-axis check — extended with the three trace style
fields the dual panel turns on (`width`, `opacity`, `connectgaps`), which the valuation chart never
varied.

**42 tickers, one per profile for all 24, plus the empty-rule cases and the edge tickers from
earlier reports.** Five of cycle 33's newly-admitted candidates are in it: GWRE, SMTC, MORN, RGTI,
APPF.

| check | result |
|---|---|
| **[fund]** panel sets identical, in order | ✓ 42 tickers, 24 profiles, 20 with at least one blank panel |
| **[fund]** title, height (330 × rows), hovermode, grid | ✓ |
| **[fund]** every annotation, 10 fields, in order | ✓ **414 annotations, 48 "No Data"** |
| **[fund]** every trace, 9 style fields + element-wise x and y | ✓ **426 traces (109 TTM, 108 quarterly), 21,106 points** |
| **[fund]** every shape, 9 fields | ✓ 122 shapes |
| **[fund]** every axis, 10 properties | ✓ 732 axis objects |
| **[fund]** zero orphan axes, both sides | ✓ |
| **[valu]** the whole item-4 comparison, re-run | ✓ 676 annotations, 266 traces, 5,223 points, 676 axes, 0 orphans |
| dual/single decision matches `is_hidden` per (ticker, metric) | ✓ 129 dual / 237 single; 0 divergences universe-wide |
| `build_fundamentals` windows by 15 years | ✓ (see §6) |
| **no mean lines on this chart, either side** | ✓ 0 mean annotations; the 122 shapes are all reference lines |
| synthetic: TTM all-null + quarterly with values → blank | ✓ 0 traces, "No Data" |
| synthetic: TTM with a null + quarterly + ref line → 2 traces | ✓ |
| grid matches `_make_grid`, n = 0…13 | ✓ |
| a request narrows, never widens | ✓ |
| an empty selection produces no figure | ✓ both sides |
| percent tickformat on exactly the registry's metrics | ✓ 247 over 318 drawn panels |

**Dual panels specifically.** 109 panels drew a TTM trace and 108 of those drew a quarterly trace
alongside it; the one that did not is the ACGL/FSLR shape above. Every one of the 217 traces matched
on `name`, `mode`, `color`, `width`, `opacity`, `connectgaps`, `hovertemplate` and axis assignment,
and element-wise on x and y including nulls.

A representative slice of the per-ticker table, both sides identical:

| ticker | profile | panels | grid | traces | blank panels |
|---|---|---:|:--:|---:|---|
| AAPL | `standard` | 9 | 3×3 | 12 | — |
| JPM | `financial` | 9 | 3×3 | 12 | — |
| AMT | `reit` | 4 | 2×3 | 5 | — |
| AFL | `insurance_life` | 9 | 3×3 | 12 | 8 |
| ACGL | `insurance_pc` | 9 | 3×3 | 12 | — |
| ADM | `consumer_staples` | 13 | 5×3 | 8 | 3, 8, 9, 10, 11, 12, 13 |
| GD | `industrials` | 11 | 4×3 | 13 | 6 |
| EQR | `reit` | 4 | 2×3 | 1 | 1, 2, 4 |
| FIG | `standard` | 9 | 3×3 | 5 | 1, 2, 5, 6, 8, 9 |

**Item 4 unchanged**, two ways: the byte-identical baseline in §1, and the full valuation comparison
re-run here against the Python builder with the same 25-check harness.

`npx tsc -b`, `npx eslint .`, `npx vite build` — all clean. Nothing outside `frontend/` changed.

### What was not verified

**Nothing was opened in a browser.** Every claim above compares the figure spec this code hands
`<Plot>` against the one `build_fundamentals` hands plotly.py. Whether the 0.8-width orange line at
opacity 0.6 actually reads as a background series at a real container width is unverified — that is
a visual judgement, and the spec matching a reference known to render correctly is the standard here
as before.

---

## 5. What was implemented, by file

| file | what |
|---|---|
| `src/charts/panel.ts` | `PanelTrace`; `PanelSpec.traces` replaces `x`/`y`; `drawPanel` iterates; `SECONDARY_COLOR` |
| `src/charts/fundamentals.ts` | **new** — `buildFundamentals`, the 15-year window, the dual path, the empty rule |
| `src/charts/valuation.ts` | one panel spec now builds a one-element `traces` list — output byte-identical |
| `src/ChartView.tsx` | **renamed from `ValuationChart.tsx`** and given a `chart` prop; a `BUILDERS` map is the one place a chart id becomes a builder |
| `src/App.tsx` | `REBUILT` lists the charts built from raw series; growth still falls back to the pre-rendered figure |

`ChartView` keeps its metric selection **per chart**, because the two catalogues share no ids — a
selection made on the valuation tab must not survive into the fundamentals tab as a set of unknown
names.

---

## 6. What the reference turned out to be

Three of the brief's premises did not survive contact with the code. Items 6, 12 and 13 hit the same
layer, so these are worth more than the diff.

1. **`build_fundamentals` does take a `years` argument, and it is 15.**
   The brief said *"No five-year window. `build_fundamentals` takes no `years` argument. Confirm
   that against the code rather than assuming."* Confirmed — and the opposite is true:
   `build_fundamentals(ticker, metrics_long, years: int = 15, ...)` calls
   `_window_frame(metrics_long, years=years, as_of=None)`. It is not decorative: the cutoff at
   2011-08-26 excludes **55,972 of 571,114 rows**. A chart built without it would have shown extra
   years on every panel and, worse, would have changed which panels are blank. **Item 6 must check
   `build_growth`'s own default rather than inheriting either number.**

2. **The fundamentals chart draws no mean lines at all.**
   `plot_metric` takes `show_mean` and defaults it to `False`; `build_fundamentals` never passes it;
   `plot_metric_dual` has no such parameter. So the mean module — the piece with the most carefully
   guarded invariant in the whole layer — is simply unused here. Verified as a check rather than
   assumed: 0 mean annotations across the set on both sides, and the 122 shapes present are all
   reference lines. **Item 6 should ask the same question before implementing anything.**

3. **The row height is 330, not 400**, and the layout key order differs (`title, size, hovermode,
   legend` here against `title, size, legend, hovermode` in `build_valuation`). The height matters;
   the key order does not, but it is the kind of difference that makes a naive byte comparison of
   the two Python figures useless and is worth knowing before someone tries one.

Two more that the brief did not raise:

4. **`plot_metric_dual` names its TTM trace `{concept} · TTM` even when it draws only that one
   line.** The single-trace fallback in the `else` branch names it `{concept}`. So the trace name
   encodes *which code path ran*, not *how many lines are visible* — and since the guard on that
   branch is a no-op (§3), the `else` branch is reached only by metrics with no counterpart at all.
   Getting this backwards produces a chart that looks right and has 109 wrong legend entries.

5. **`plot_metric_dual` plots the full windowed series for both lines, not the `dropna`'d one.**
   `ttm_valid` and `quarterly_valid` exist *only* to decide whether to draw; what gets drawn is
   `ttm` and `quarterly` with their nulls intact. Dropping the nulls would silently close every
   coverage gap — the same trap the null handling in item 4 was written to avoid, reached from a
   different direction.

No scratch files were left behind.
