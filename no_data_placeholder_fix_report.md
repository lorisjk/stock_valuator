# The "No Data" placeholder landed on the wrong panel

**Date:** 2026-08-22
**Touched:** `frontend/src/charts/panel.ts` — two reference expressions and the comments that
explain them — plus a corrected comment in `frontend/.gitignore`. **Nothing outside `frontend/`
changed.**

The defect is real, the hypothesis in the brief is right about the consequence and wrong about the
mechanism, and the fix is two lines. The part worth keeping is Part 1 and the structural check in
Part 4: the original verification could not have caught this, and the reason generalises to the six
items that build on this layer.

---

## 1. Why the original verification passed

`frontend_valuation_chart_report.md` §4.1 claimed subplot titles, "No Data" counts, all 196 axis
objects and every shape were compared and identical. That was true. It was also not enough.

The comparison reduced every annotation to one of three summaries before comparing:

| annotation kind | what was compared | what was not |
|---|---|---|
| subplot titles | `text` | `xref`, `yref`, `x`, `y`, anchors, font |
| **"No Data"** | **an integer count** — `sum(1 for a in anns if a.text == "No Data")` | **everything else, including `xref` and `yref`** |
| mean labels | `{xref, text}` | `yref`, `x`, `y`, anchors, colour, size |

**The hole, named:** the "No Data" annotation was reduced to a count. Both sides emitted exactly
one for AEP, so `1 == 1` and the check passed — while one side said `xref: "x5"` and the other said
`xref: "x5 domain"`.

Taking the brief's four candidates in turn, checked rather than assumed:

1. **Were annotations compared at all, or only counted?** Both, inconsistently. Mean labels *were*
   compared on `xref` — the harness had the right instinct and applied it to one of the two
   annotation classes. "No Data" got the count.
2. **Were `xref` / `yref` among the compared fields?** `xref` for mean labels only. **`yref` was
   never compared for any annotation**, in any class.
3. **Did the axis comparison cover the properties the blanking modifies?** Partly — it covered
   `showticklabels` but not `showgrid`, `zeroline`, `type` or `visible`. **This was not the hole.**
   The axis objects were identical on both sides then and are identical now; the defect never lived
   in them. The gap was real but would not have caught this.
4. **Was plotly.py's output read correctly?** Yes. The Python side read `a.xref` off the `Figure`,
   which carries the reference plotly.py *resolved* from `row=`/`col=` — `"x5"`. It was read
   correctly and then never compared for that class.

There is a fifth gap the brief did not list, and it is the one that matters most:

> **The comparison only ever asked whether the two sides agreed. It never asked whether plotly.js
> could act on what our side emitted.**

Agreement with a correct reference is necessary, not sufficient, when two encodings both look
valid. `"x5 domain"` is a legal plotly reference in general; it is illegal *for an axis that no
trace touches*, and no amount of cross-implementation diffing will say so unless the two happen to
disagree on that exact field — which they did, in the one field that was thrown away.

### The hole, demonstrated rather than argued

The extended comparison keeps the old reduction alongside the new one and reports both. Run against
the **unfixed** code over 19 tickers:

| comparison | result |
|---|---|
| the original reduction (titles by text, "No Data" by count, mean labels by ref+text) | **PASSES — 0 differences** |
| annotations field by field, in order | **FAILS — 41 "No Data" annotations, every one `"xN domain"` against the reference's `"xN"`** |
| axes reachable by plotly.js | **FAILS — 82 orphan axes across 15 of 19 tickers** |

---

## 2. Diagnosis

The brief's hypothesis — *"an unnumbered `x domain` refers to the first axis regardless of which
cell was intended"* — is **right about the consequence and wrong about the mechanism.** The
references were correctly numbered. Emitted for AEP before the fix:

```
"No Data"   xref=x5 domain   yref=y5 domain   x=0.5 y=0.5 size=14
```

and from `build_valuation` for the same ticker and data:

```
"No Data"   xref=x5          yref=y5          x=0.5 y=0.5 size=14
```

The numbering is identical. **It is the ` domain` suffix itself that is fatal**, and only for a
panel that carries no trace.

### The chain, with the evidence for each link

1. plotly.js registers an axis as a subplot in exactly two ways: a trace names it, or a component
   (annotation, shape, image) names it. The component path is
   `plots/cartesian/include_components.js:36`, which calls
   `axisIds.cleanId(itemi.xref, 'x', false)`.

2. `plots/cartesian/axis_ids.js:35` reads `if(domainTest && (!domainId)) return;`. **Executed
   against the installed plotly.js 3.7.0, not merely read:**

   | ref | `cleanId(ref, 'x', false)` | `cleanId(ref, 'x', true)` |
   |---|---|---|
   | `"x"` | `x` | `x` |
   | `"x5"` | `x5` | `x5` |
   | `"x domain"` | **`undefined`** | `x domain` |
   | `"x5 domain"` | **`undefined`** | `x5 domain` |

   The comment directly above the call site says *"call cleanId because if xref, or yref has
   something appended (e.g., ' domain') this will get removed"*. It does not get removed. The
   reference is rejected.

3. A "No Data" panel has no trace by definition, so `x5` never enters
   `_fullLayout._subplots.xaxis`.

4. `Cartesian.finalizeSubplots` — *"ensure all cartesian axes have at least one subplot"* — iterates
   `subplots.xaxis`, so it cannot rescue an axis that never got in. **Panel 5 is never created: no
   axes, no grid, no annotation.** ← *"the panel that should receive it receives nothing"*.

5. `axes.coerceRef` (`plots/cartesian/axes.js:106`) builds its enumerated value list from
   `_subplots[letter + 'axis']` and its default from `axlist[0]`. `"x5 domain"` is not in the list,
   so the annotation is coerced to the **first registered axis**. ← *"panel 1 has a red 'No Data'
   annotation"*.

6. That fallback is a **data** reference, not a domain one. On a date axis, `x: 0.5` is 0.5 ms after
   the epoch — 1 January 1970. `components/annotations/calc_autorange.js` expands an axis for every
   range-referenced annotation (`if(xRefType === 'range') calcAxisExpansion(ann, xa)`), so panel 1's
   x range is dragged back to 1970. With `dtick: "M24"` that is a tick every two years across 56
   years. ← *"the dates render as dense vertical categorical labels instead of `%Y` ticks at a
   2-year interval"*.

**One root cause, all three observed effects.**

A detail worth recording because it changes what a screenshot proves: the fallback is the first
*registered* axis, not literally panel 1. For AMT — whose empty panel **is** the first — `x` itself
is never registered, `axlist[0]` is `x2`, and the placeholder lands on **panel 2**. Any fix
validated only against tickers with data in cell 1 would have looked fine.

### Does the mean-line annotation share the defect? No — and only by luck of position

The mean labels use `"x domain"` / `"y domain"` too, and so do the mean and reference **shapes**.
They are safe for one reason: a mean line only exists on a panel that has a trace, and the trace
registers the axis, so `coerceRef` finds `"x2 domain"` in its list and keeps it.

Checked rather than assumed, as the brief asked. AEP panel 1 shows `Ø (harm.) 17.0`. Independently,
from `metrics.harmonic_mean` over the 19 non-null `pe_ratio` values in the five-year window:

```
harmonic mean = 17.017204514277278   ->  "Ø (harm.) 17.0"
arithmetic    = 17.3083391865817     (not used; pe_ratio is in HARMONIC_MEAN_CONCEPTS)
```

The label is `pe_ratio`'s own harmonic mean, and the shape sits at `y = 17.0172` on `yref: "y"` —
byte-identical to the Python builder's. It is on the right panel and it is the right number.

**But the safety is positional, not structural**, which is why the fix is not only two lines — see
below.

---

## 3. The fix

`frontend/src/charts/panel.ts`, in `annotateNoData`:

```diff
-    xref: `${refs.xaxis} domain`,
-    yref: `${refs.yaxis} domain`,
+    xref: refs.xaxis,
+    yref: refs.yaxis,
```

`x: 0.5, y: 0.5` are now data coordinates on both sides — which is what `plot_metric` has always
produced, since `add_annotation(..., row=r, col=c)` resolves to a bare `"x5"`. An axis with no data
auto-ranges around the annotation, which is why the placeholder still sits mid-panel.

**Why it belongs in the shared layer.** `drawPanel` and `createGrid` are what items 5, 6, 12, 13 and
14 reuse, and three of them walk straight into this path: item 5's fundamentals chart has a rule
that an empty TTM series blanks the panel *even when the quarterly series has values*, item 6's
growth chart adds a fixed `y = 0` line to panels that may be empty, and item 14's outlier masking
can empty a panel that previously had a trace. A fix at `buildValuation`'s call site would have left
the bug loaded for each of them.

So the constraint is now stated in the module header, where anyone adding furniture reads it before
writing any:

> **An axis that no trace references may only be referenced by a bare id (`"x5"`), never by
> `"x5 domain"`.** Panels that carry a trace may use either form.

**The panel-1 asymmetry.** `axisSuffix(1)` returns `""`, so cell 1 yields `"x"` / `"y"` and cells
2+ yield `"x2"` / `"y2"`. That was already correct and is now covered by evidence rather than
inspection: eleven tickers in the verification set have an empty **first** panel — AMT, CCI, CRWV,
STZ, V, ERIE, FIG, BKR, AAOI, APLD, AUR — and BKR's eight panels are *all* empty, so its figure
exercises every cell of a 3×3 grid as a placeholder.

**Also corrected:** `frontend/.gitignore`'s comment claimed the repository root ignores `data/`
without a leading slash. The root pattern has since been anchored to `/data/`, so the comment
described a condition that no longer held. The `!/src/data/` guard is kept — the failure it prevents
is silent — and the comment now says why it is a guard rather than a fix.

---

## 4. Closing the verification hole

Three changes to the comparison, all of them permanent:

**1. Every annotation, every field, in order.** `text`, `xref`, `yref`, `x`, `y`, `xanchor`,
`yanchor`, `showarrow`, `font.color`, `font.size` — no class reduced to a count, no field dropped.
The Python side is read from `to_plotly_json()`, so what is compared is the resolved reference
plotly.py would hand a browser.

**2. Axes on ten properties**, adding the four the placeholder path touches or could touch:
`showgrid`, `zeroline`, `type`, `visible`, alongside `domain`, `anchor`, `dtick`, `tickformat`,
`title`, `showticklabels`. Shapes likewise gained `type`, `x0`, `x1`, `y1`.

**3. A structural check that is not a comparison at all.** Agreement with the reference would not
have caught this, so the rule is asserted directly:

> For every axis in the layout, that axis must be reachable by plotly.js — named by a trace, or
> named by an annotation or shape **without** a ` domain` suffix. Any other axis is never created,
> and every reference to it silently falls back to the first registered axis.

It runs over both implementations. The reference side reports zero orphans, which is the direct
explanation of why the Streamlit chart has never shown this bug.

**4. A verification set that can tell panel 1 from panel 5.** The original set had empty panels but
no way to notice which cell they were in. The new set is **66 tickers**, chosen so that the *first*
empty panel falls at every position from 1 to 9, plus tickers with no empty panels at all and BKR
with all eight empty:

| first empty panel | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | none |
|---|---|---|---|---|---|---|---|---|---|---|
| in the set | AMT, CCI, … | ABBV, ARE, … | AES, AJG, … | ACGL, ALAB, … | AEP, BALL, … | ADM, ADP, … | BSX, CRL, … | ADBE, AKAM, … | INTC | AAPL, JPM, … |

---

## 5. Results

**17 checks over 66 tickers, all passing.**

| check | result |
|---|---|
| panel sets identical | ✓ 66 tickers |
| figure title, height, hovermode, grid | ✓ |
| **every annotation on all 10 fields, in order** | ✓ **1,060 annotations — 130 of them "No Data", 400 mean labels** |
| every shape on all 9 fields | ✓ 400 shapes |
| every trace (x dates, y incl. nulls, style, axis assignment) | ✓ **7,820 plotted points element-wise** |
| every axis on all 10 properties | ✓ **1,060 axis objects** |
| **no axis invisible to plotly.js — React side** | ✓ **0 orphans** (was 82 over 19 tickers) |
| no axis invisible to plotly.js — reference side | ✓ 0 orphans |
| grid matches `_make_grid`, n = 0…13 | ✓ |
| five-year window boundary unambiguous | ✓ nearest row 5.15 days from the cutoff |
| a request narrows, never widens | ✓ |
| an empty selection produces no figure | ✓ both sides |
| `harmonic_mean` + label formatter on nine edge cases | ✓ |
| reference line + percent axis, synthetic panel | ✓ |
| nulls preserved | ✓ 1,054 kept |
| percent tickformat on exactly the registry's metrics | ✓ 37 percent axes over 400 drawn panels |
| no unclassified difference | ✓ |

Against the Part 5 list specifically:

1. **AEP.** `pe_ratio` draws 19 points with `dtick: "M24"`, `tickformat: "%Y"` and no placeholder;
   `dividend_yield` carries the "No Data" annotation on `xref: "x5"`, `yref: "y5"` with
   `showticklabels`, `showgrid` and `zeroline` all false on `xaxis5` and `yaxis5`. Identical to
   `build_valuation` annotation by annotation and axis by axis.
2. **Spec matches for AEP** — every field of all 12 annotations, all 5 shapes, all 12 axes.
3. **63 more tickers** with empty panels in every cell position, including 11 where the empty panel
   is the first and one (BKR) where all eight are empty.
4. **The original report's tickers still match** — AAPL, JPM, O, V, STZ, ERIE, BKR, CRWV, FIG, KO,
   XOM, MSFT are all in the set, and every claim from that report is re-run here: panel sets, mean
   values and labels, the grid, percent axes, nulls, the narrowing rule, the synthetic reference
   line.
5. **`npx tsc -b`, `npx eslint .`, `npx vite build`** — all clean.
6. **Nothing outside `frontend/` changed.** The root `.gitignore` shows as modified, but that is the
   operator's own edit (anchoring `data/` to `/data/` and ignoring `frontend/public/tickers/`), not
   this task's.

### What was verified how

- **From the spec, exhaustively:** every field of every annotation, shape, trace and axis, against
  `build_valuation`'s serialised output, on 66 tickers.
- **By executing plotly.js's own code:** `cleanId` was run against the installed plotly.js 3.7.0 for
  seven reference forms, which is what turns the diagnosis from a source reading into a measurement.
  `coerceRef`'s fallback and `calc_autorange`'s expansion were **read**, not executed — both pull in
  d3 and a browser DOM at import. Their behaviour is quoted with file and line.
- **In a browser: nothing.** No page was opened. The pixel-level claims in Part 5.1 —
  that the `%Y` ticks now look right and the red placeholder sits mid-panel — follow from the spec
  matching a reference implementation that is known to render correctly, not from having seen them.
  That is the same standard as the original report, with the specific hole closed.

`frontend/public/tickers/` now holds the complete 1,218-file export (137 MB) and is gitignored, so
AEP, AMT, INTC, BSX, ADBE, SRE and ARE can all be opened directly for a visual confirmation.

---

## 6. What this leaves behind

- The rule in `panel.ts`'s header and the structural check in the verification are the durable part.
  Items 5, 6, 12, 13 and 14 add furniture to trace-less panels; each of them would have reproduced
  this bug, and now each of them fails the check instead.
- **The mean line's correctness is positional, not structural.** It uses domain references and is
  safe only because a mean line implies a trace. Item 14 (outlier masking) is the first thing that
  could break that assumption — masking every point of a panel leaves a trace with no visible data —
  so the invariant to watch is *"does this panel still have a trace"*, not *"does this panel have a
  mean"*.
- **plotly.js's `include_components.js` comment is wrong about its own call.** It says a ` domain`
  suffix "will get removed"; `cleanId` rejects the whole reference instead. Worth knowing before the
  next person reads that file and concludes domain refs are safe everywhere.

No scratch files were left behind.
