# The snapshot marker — item 13

The last piece item 4 was scoped to leave out: one extra point per valuation panel, the current
multiple against the history it is there to be judged against.

Two of the brief's premises turned out to be wrong, both in the same direction — the marker is
*less* independent of the rest of the chart than the framing assumed. Both are in §1 and §5.5.

---

## 1. Step 1 — the reference, read exactly

### 1.1 Where the value comes from — **no new fetch**

`current_snapshot` is already a per-ticker frame in the item-2 export
([contracts.ts:109](frontend/src/contracts.ts#L109), [load.ts:27](frontend/src/data/load.ts#L27)) and
`DataTab` already reads it ([DataTab.tsx:184](frontend/src/data/DataTab.tsx#L184)) for its "Current
snapshot" section. Columns `end, concept, value`; one date for every row in the bundle,
**2026-08-21**. `app.py:954` hands `build_valuation` the same frame on every render, so the marker is
the app's normal state rather than a mode.

Nothing needed wiring. The builder takes a boolean and reads the frame it already has.

### 1.2 Which concepts get a marker — measured, not assumed

Scanned all **609 bundled tickers × the 13 valuation concepts = 7,917 pairs**:

| | count |
|---|---:|
| `value` null anywhere in `current_snapshot` | **0** |
| a (concept) appearing twice for one ticker | **0** |
| hidden by the profile **and** present in the snapshot | **0** |
| visible **and** present | 4,006 |
| visible but **absent** from the snapshot | **995** |
| present with **no filed history at all** | **17** |

Three consequences:

- **"No value" and "not computed for this concept" are the same condition — absence.** The export
  never carries a null. `_snapshot_point`'s `dropna` and `sort_values("end").iloc[-1]`
  (figures.py:324-329) are therefore faithfulness to the parquet the JSON is projected from, not
  logic the JSON exercises. They are implemented anyway, because the rule is the rule.
- `_snapshot_point`'s docstring claim that a profile-hidden concept "still has no row" (figures.py:315)
  **holds exactly**, 0 exceptions. So that case needs no code: it arrives as absence.
- 995 visible-but-absent pairs means Step 3.3's case is the common one, not an edge — AAOI's
  `pe_ratio` and 62 others like it.

### 1.3 Visual distinction — figures.py:475

```python
marker=dict(color="#2ca02c", size=9, symbol="circle", line=dict(color="white", width=1))
```

Green (figures.py:22, with its reason in the comment above it: *"never red, which is already the mean
line and the reference line"*), size 9, circle, **white 1px outline**. `mode="markers"` and — worth
noting because it decides the emitted shape — **no `line` kwarg at all**, where the filed trace has
`line=dict(color=_PRIMARY_COLOR)`.

### 1.4 Hover text, and the x-position — **a correction**

figures.py:477-481:

```
Snapshot (current value)<br>Date: {stamp:%d.%m.%Y}<br>Value: %{y}<extra></extra>
```

The brief asked "specifically whether it includes an as-of/snapshot date **distinct from** the
x-axis position (the x-position is 'today', per the docstring's framing in prior reports)."

**It is not today, and the two are not distinct.** figures.py:330 sets `stamp = latest["end"]` and
figures.py:468 plots at `x=[stamp]` — the same value that the hover prints. The date in the hover is
the x-position spelled out, not a second date. Nothing in the reference reads `meta.json` or a run
date here; `end` in the snapshot frame is the price date, and the export's is 2026-08-21, not today.
The prior framing was loose, and the difference is visible: on a chart rendered today the marker sits
seven days left of "now".

The date is baked in as a literal, not written as `%{x|%d.%m.%Y}` — so it is formatted once at build
time, which is why `germanDate` exists.

### 1.5 Legend — one entry per figure, not per panel

figures.py:470-474 gives the trace `name="Snapshot (current value)"`, `legendgroup="snapshot"` and
`showlegend=snapshot_in_legend`, and `build_valuation` latches it (figures.py:748-757):

```python
snapshot_in_legend=not snapshot_shown
...
snapshot_shown = snapshot_shown or point is not None   # "one legend entry for all of them"
```

So: **one entry, on whichever panel drew the first marker**, and the shared `legendgroup` means
clicking it toggles every panel's marker at once. Confirmed live in §5.6 — 9 markers, 1 legend entry.

One subtlety reproduced deliberately: the latch advances on `point is not None`, **not** on the
marker being drawn. A panel that has a snapshot value but is empty (§1.6 below) consumes the legend
entry without drawing anything. Only observable when such a panel comes first in the grid; faithful
either way.

### 1.6 The `as_of` rule — the brief's guess was right

figures.py:333:

```python
if as_of is not None and pd.Timestamp(as_of) < stamp:
    return None
```

**Suppressed only when `as_of` strictly predates the snapshot's own date.** An `as_of` *on* the
snapshot day keeps the marker; so does any later one; and `as_of=None` — which is app.py:867's
default, behind an opt-in checkbox — disables the check entirely rather than defaulting to today.

That last clause matters for the port. `ValuationOptions.anchor` is this port's `as_of`, and it is
now **undefined = `None`**: an absent anchor both anchors the window on today *and* leaves the marker
unjudged, exactly as Python does. What item 15 still owes is `_window_frame`'s *upper* bound
(figures.py:157), which `windowCutoff` does not apply; the suppression half is done and tested.

### 1.7 A fourth absence the brief did not ask about

`plot_metric` returns at figures.py:358 — `if valid_values.empty: _annotate_no_data(); return` —
**before** the snapshot block at figures.py:466. So an empty panel draws "No Data" and no marker,
even when a current value exists. This is what makes §5.5 come out the way it does.

---

## 2. Step 2 — the mean invariance, from the other side

The structural half was already in place from item 4, and it is one line
([valuation.ts:151](frontend/src/charts/valuation.ts#L151)): `mean` is computed from `series.y`,
while the traces carry their own arrays. The marker is appended to `traces` and that line is
untouched, so `meanOver` cannot see it whatever `traces` holds — the same guarantee figures.py:389
states as `filtered` versus `drawn`.

Measured anyway, over **41 tickers × 3 windows (2/5/15y)**, comparing marker-on against marker-off:

- every red shape (mean hlines **and** reference lines), serialised, **identical**;
- every `Ø` label, serialised, **identical**;
- the filed trace itself, serialised, **identical**;
- the panel list **identical**.

**3,275/3,275 checks pass.** Actual labels, covering harmonic, arithmetic and percent:

| ticker / window | labels (unchanged with the marker on) |
|---|---|
| AAPL / 2y | `Ø (harm.) 33.6`, `Ø 48.0`, `Ø (harm.) 32.8`, `Ø 33.7`, `Ø 37.6`, `Ø (harm.) 25.1`, `Ø 8.8`, `Ø 0.42%`, `Ø 7.4` |
| AAPL / 5y | `Ø (harm.) 29.0`, `Ø 44.2`, `Ø (harm.) 28.0`, `Ø 29.5`, `Ø 32.2`, `Ø (harm.) 22.5`, `Ø 7.8`, `Ø 0.50%`, `Ø 5.4` |
| AAPL / 15y | `Ø (harm.) 16.4`, `Ø 20.4`, `Ø (harm.) 14.4`, `Ø 20.1`, `Ø 20.2`, `Ø (harm.) 12.8`, `Ø 5.2`, `Ø 4.20%`, `Ø 2.9` |
| AAOI / 15y | `Ø (harm.) 22.8`, `Ø 2.1`, `Ø (harm.) 51.5`, `Ø 93.0`, `Ø 73.3`, `Ø (harm.) 14.3`, `Ø 2.4`, `Ø 0.8` |

AAPL's `pe_ratio` 5y mean is `Ø (harm.) 29.0` against a marker at **35.53** — the marker is well
outside the mean and moves it not at all, which is the whole point of the separation.

---

## 3. Step 3 — design

### 3.1 A trace, not a drawing path

**One more entry in `PanelSpec.traces`**, exactly as item 5's report predicted when it generalised
`PanelSpec` from an x/y pair to a list. `PanelTrace` gained four optional fields — `marker`,
`hovertemplate`, `legendgroup`, `showlegend` — and `drawPanel`'s existing loop draws it.

The one thing worth checking before accepting that was **order**, since figures.py adds the snapshot
trace *last*, after `_style_axes`, the mean and the reference line, while `drawPanel` draws all
traces first. It does not matter, and for a concrete reason: `fig.data`, `layout.shapes` and
`layout.annotations` are three independent arrays. Within `fig.data` the reference's order is
`[filed, snapshot]` and so is this port's; the shapes and annotations are untouched by where the
trace push sits. Verified rather than reasoned — §5.1 compares all three arrays element-wise and in
order.

Two emission rules keep the trace shaped like the reference's:

- `marker` **replaces** `line` rather than joining it. figures.py's snapshot Scatter passes no `line`
  kwarg, and an emitted `line: {color}` on a `mode: "markers"` trace would be a field the reference
  does not have.
- `hovertemplate` falls back to the per-point default, so the filed trace is byte-for-byte what it
  was.

### 3.2 Suppression as a pure predicate

[`charts/snapshot.ts`](frontend/src/charts/snapshot.ts) — `snapshotPoint(frame, concept, asOf)`,
returning the point or null, no React, no DOM, runnable in Node. It is a module rather than four
lines inline because the interesting part of this feature is *when the marker is absent*, and the
module's docstring is where the three ways that happens (and the fourth that belongs to the panel)
are recorded next to the measurements behind them.

`asOf` is `undefined = None`, per §1.6.

### 3.3 A concept with a filed series and no snapshot value

`snapshotPoint` returns null, `marker` is `[]`, the spec is what it was, the panel renders exactly as
today. 995 pairs in the export. No error, no notice — the reference says nothing either, and a panel
that simply has no current value is not a fault.

### 3.4 A concept with **only** a snapshot value

**It happens — 17 (ticker, concept) pairs**: `LULU`/`ev_fcf`, `PLTR`/`ev_ebitda`, `F`/`ev_ebitda`,
`ARES`/`ev_sales`, `REG`/`ev_sales`, `PYPL`/`dividend_yield` among them.

The behaviour is the reference's, and it falls out with no new code: `drawPanel` returns at
`panel.empty` before it reaches the trace loop, exactly as `plot_metric` returns before its snapshot
block. **The panel shows "No Data" and no marker.**

This is worth stating plainly because it is mildly surprising: a panel can show "No Data" while a
current value for that concept exists and is visible in the data tab two clicks away. It is the
reference's choice — "No Data" is about the *history*, and a chart of one point is not a history.

---

## 4. Step 4 — what was implemented

Four files, all inside `frontend/`:

| file | change |
|---|---|
| [`src/charts/snapshot.ts`](frontend/src/charts/snapshot.ts) | **new.** `snapshotPoint`, the three constants, `germanDate`, `snapshotHovertemplate`. |
| [`src/charts/panel.ts`](frontend/src/charts/panel.ts) | `Marker` interface; four optional fields on `PanelTrace`; `drawPanel` emits `marker` in place of `line` and honours a supplied `hovertemplate`. Additive — the filed-period path is unchanged, proven in §5.2. |
| [`src/charts/valuation.ts`](frontend/src/charts/valuation.ts) | `snapshot?: boolean` option; the per-panel point; the `snapshotShown` legend latch; `anchor`'s docstring rewritten as `as_of`. |
| [`src/ChartView.tsx`](frontend/src/ChartView.tsx) | passes `snapshot: true`, matching app.py:954. |

`snapshot` is an **option defaulting to false**, mirroring `build_valuation`'s
`snapshot: pd.DataFrame | None = None` and its docstring's promise that omitting it "reproduces this
function's output exactly as before". That promise is what the item-8 baseline is worth here, and
§5.2 measures it.

### 4.1 The item-14 interaction — it matters, but not the way the brief expected

The brief asked whether the placeholder-fix cycle's structural rule (*an axis with no trace may only
be referenced by a bare id*) could be reached through a panel whose only remaining visible thing
after masking is the marker.

**That specific case cannot occur, and the reason is in `outlier_points` itself** (figures.py:210):
the mask is `(usable / median) > 5`, and at least half of any series is at or below its own median,
so at least ⌈n/2⌉ points always survive. The docstring says it outright — *"All-False — never
all-True"*. A fully-masked panel does not exist, so the axis rule is not reachable that way. If
anything the marker makes it *safer*: a second trace on the axis is one more thing keeping the
subplot alive.

**A different interaction is real and worth measuring**, and item 14 should have the number. Masking
touches `drawn`; the marker is a separate trace it never reaches. So on a panel where the *snapshot
itself* is extreme, the toggle hides the filed outliers and the y-axis stays stretched by the marker
— the toggle appearing to do nothing. At the default 5-year window, over all 609 tickers:

- 3,518 visible panels are long enough and positive enough for the rule to apply;
- on **64 of them (1.8%)** the snapshot value exceeds 5× the panel's own median;
- the extremes: `FDX`/`pe_ratio` at **129,740×**, `MDT`/`pe_ratio` at **103,301×**, then `MXL`/`pfcf_ratio`
  at 87.5×.

The reference behaves identically — `snapshot_point` and `mask_outliers` are independent parameters
of `plot_metric` — so this is inherited, not introduced. Item 14 can leave it, or extend the hidden
count to say so; either way it should be a decision rather than a surprise.

---

## 5. Step 5 — verification

### 5.1 Against `build_valuation`, element-wise

**196 scenarios · 53,821 checks · 0 failures.** 40 tickers (16 named — including the brief's
`V`/`STZ`/`ERIE`/`BKR`, the no-history cases `LULU`/`PLTR`/`F`/`ARES`/`REG`/`NAVN`/`PL`, the REIT `O`
and the bank `JPM` — plus 24 random), each at 5/15/2 years with the marker on, once with it off, and
12 of them at three `as_of` dates.

Both sides read **the exported JSON**, not `data/*.csv` — the export in `frontend/public` is dated
2026-08-21 and the csv 2026-08-14, and comparing against the csv would have compared two different
snapshots. Every trace field, every annotation, every shape, in order.

**808 markers drawn; exactly 142 carry a legend entry** — one per figure that has any.

Two normalisations, both recorded in the harness: numpy scalars against Python ones and `NaN` against
the `null` the JSON carries in its place; and `font.color` compared only where the reference sets one,
because the frontend themes its panel titles and axis text for a dark shell (a divergence recorded in
the shell cycle). The colours that *mean* something — red for the mean and reference lines, green for
the marker — are set on both sides and are compared.

### 5.2 The item-8 baseline, as an A/B

The item-8 harness was scratch in its own cycle, so rather than trust a remembered hash I built a
copy of `src/` with item 13 reverted and ran the same sweep against both trees — 41 tickers × 3
charts × 8 windows × 4 selection shapes, no options:

```
AFTER  (current tree)          3936 figures, 465488 points, sha256 fe09bcf21e00…8b09c907
BEFORE (item 13 reverted)      3936 figures, 465488 points, sha256 fe09bcf21e00…8b09c907
```

**Byte-identical.** The default path — no `snapshot` option — emits exactly what it emitted before,
including key order, which is the part an element-wise comparison would not have caught.

The same A/B over the other two harnesses' surfaces:

```
comparison   130 figures       d24889e43e83…f627a297   identical on both trees
csv          328 blocks, 904,962 characters   55fd62aff02f…5e1b982a   identical on both trees
```

Both reach code this cycle touched — `comparison.ts` draws through the same `panel.ts` — so
"unchanged" is measured rather than argued.

### 5.3 `as_of` suppression, exercised

41 tickers, four dates each, counting markers:

| `as_of` | markers |
|---|---:|
| 2026-08-20 — one day **before** the snapshot | **0** |
| 2026-08-21 — **on** the snapshot's own date | 249 |
| 2026-08-22 — one day after | 249 |
| `None` | 249 |

Exactly §1.6's rule: strictly-before suppresses, on-the-day does not, and `None` is not "today".

### 5.4 Agreement with the data tab

**249 marker/data-tab value pairs compared, all equal.** Every marker's `y` is `Object.is`-equal to
the value `DataTab`'s "Current snapshot" section shows for the same concept, and every marker has a
row there. That is not a coincidence to be maintained — both read `frames.current_snapshot` from the
same per-ticker file — but the two could still have diverged through a filter or a coercion, and now
they demonstrably do not.

### 5.5 The window — **the brief's second premise, corrected**

> it is not part of the windowed series, so it should be unaffected by `years` — confirm this rather
> than assume.

**Half true, and the false half is the interesting one.** Over 41 tickers × 8 windows (1…15y):

- **1,913 marker values are stable across every window** — a marker that is drawn never moves. The
  value and the date come from the snapshot frame, which `windowCutoff` never touches. That half is
  confirmed.
- **79 markers disappear** as the window narrows. Not because the marker is windowed, but because
  its *panel* is: shrink the window until the filed series is empty and §1.7's early return fires,
  the panel becomes "No Data", and the marker goes with it.

So the marker is not part of the windowed series but it is not independent of the window either — it
is conditional on the panel the window decides. **124 visible panels** across the export have a
snapshot value and an empty 5-year window; at 15 years that falls to 19.

### 5.6 Live, in the browser

Not a substitute for §5.1 — the builders being right does not prove `<Plot>` shows it:

| page | traces | markers | legend entries | green points in the SVG |
|---|---:|---:|---:|---:|
| AAPL valuation, default pick | 2 | 1 | 1 | 1 |
| AAPL valuation, every panel | 18 | **9** | **1** | **9** |
| AAOI valuation, every panel | 4 | 2 | 1 | 2 |
| AAPL **fundamentals** | 1 | 0 | 0 | 0 |

The first marker reads back as `x: Fri Aug 21 2026`, `y: 35.52841572015822`, `color: #2ca02c`,
`size: 9`, `symbol: circle`, `line: {color: white, width: 1}`, hover
`Snapshot (current value)<br>Date: 21.08.2026<br>Value: %{y}<extra></extra>`. Nine markers, one
legend entry — the latch, end to end. The fundamentals row is the scope check: the marker is
valuation-only.

### 5.7 Nothing else regressed

`check-chart-width` **30/30** · `check-tab-state` **13/13** · `check-table-format` **6,107/6,107** ·
`npx tsc -b`, `npx eslint .`, `npx vite build` all clean · four files changed, all inside
`frontend/` · no scratch files left behind.

---

## 6. For item 14

1. **The fully-masked panel does not exist.** `outlier_points` can never return an all-True mask
   (figures.py:210 and its docstring), so the bare-axis-id rule is not reachable through masking.
   Do not build a guard for it; do keep the rule for genuinely empty panels, which is where it came
   from.
2. **The marker is not maskable, and on 64 panels (1.8%) that is visible.** The snapshot itself
   exceeds 5× its panel's median there; hiding the filed outliers will leave the axis stretched by
   the marker. `FDX`/`pe_ratio` at 129,740× is the case to look at. Inherited from the reference, so
   matching it is defensible — but say which was chosen.
3. **The outlier-count annotation has a home already.** figures.py:400 puts it bottom-right at
   `x=0.98, y=0.02` in domain coordinates, explicitly *"because the mean label occupies the top-left
   of the same panel"*. The marker occupies neither.
4. **`PanelSpec.traces` is the place for anything else drawn per panel**, and it now has a second
   user. Masking is a change to what goes *into* the first trace's arrays, not a new one — and
   `mean` must keep reading `series.y`, which is the invariant §2 measures.

## 7. For item 15

`ValuationOptions.anchor` is now the port's `as_of` on both counts — the window's anchor and the
marker's cut-off — and undefined means `None`, matching app.py:867's default. The control to build is
a checkbox plus a date input; the one piece of plumbing still missing is `_window_frame`'s **upper**
bound (figures.py:157), which `windowCutoff` does not apply. §5.3's table is the regression test for
the half that is done.
