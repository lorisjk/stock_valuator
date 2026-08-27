# The years window

Rebuild-list item 8. The builders already took `years`; this cycle adds the control and establishes
what the control is allowed to assume.

---

## 1. What the Streamlit version does

### 1.1 The three chart sliders — and two more

All three chart tabs do have one, and all three are the same call with a different default:

| tab | line | call | key | goes to |
|---|---|---|---|---|
| Fundamentals | app.py:907 | `st.slider("Window (years)", 1, 15, 15)` | `fundamentals_years` | `build_fundamentals(years=…)` |
| Growth | app.py:919 | `st.slider("Window (years)", 1, 15, 15)` | `growth_years` | `build_growth(years=…)` |
| Valuation | app.py:931 | `st.slider("Window (years)", 1, 15, **5**)` | `valuation_years` | `build_valuation(years=…)` |

Two more exist outside this item's scope, both `1, 15, 15`: `comparison_years` (app.py:1036) and
`raw_years` (app.py:1119).

**The slider defaults equal the builder defaults, all three.** `build_fundamentals(years: int = 15)`,
`build_growth(years: int = 15)`, `build_valuation(years: int = 5)`. So the chart you get before
touching the slider is the chart the builder draws when nobody passes `years` — which this rebuild
makes structural rather than coincidental by deriving `DEFAULT_YEARS` from the builders' exported
constants instead of restating `15 / 5 / 15`.

### 1.2 The floor — incidental, and it excludes exactly one degenerate value

Nothing in `app.py` or `figures.py` justifies the floor of 1; there is no comment and no guard.
What it excludes is nevertheless precisely one value, and that value is degenerate rather than
merely small.

`_window_frame` computes `anchor - DateOffset(years=0)` = today, and every period end in the export
is in the past, so `years = 0` keeps **no rows at all**. Measured on four tickers across three
charts, all twelve combinations:

```
AAPL fundamentals  y=0: 0 traces / 9 panels     y=1: 12 traces
KO   fundamentals  y=0: 0 traces / 13 panels    y=1: 11 traces
JPM  valuation     y=0: 0 traces / 5 panels     y=1: 5 traces
O    growth        y=0: 0 traces / 7 panels     y=1: 5 traces
```

Not `None` — a **full grid of "No Data" panels**, on both implementations. The builders handle it
without special-casing.

**The frontend keeps the floor at 1**, for the reference's range rather than for safety: a setting
whose only possible output is a blank chart is not a setting worth offering. `years = 0` stays
reachable through the builder API and is still exercised by the verification, where it remains the
sharpest test of the axis-reference rule — every axis in that figure is reachable only through its
"No Data" annotation.

### 1.3 Streamlit's slider-persistence rule — different from `multiselect`'s

Read from Streamlit 1.61's source, as the brief asked, rather than inferred from the pickers cycle.
`SliderSerde.deserialize` (`elements/widgets/slider.py:197`):

> *"Reset to default if any value is outside `[min_value, max_value]`."*

So the two widgets do opposite things with a stale value: `multiselect` **filters and writes the
survivors back** (the pickers report §1.3); `slider` **discards the whole value and reverts to the
default**. Neither clamps.

For this control the rule never fires. The range is `1, 15` for every chart, ticker and profile —
it does not depend on the data — so a persisted value is always in range and **simply carries
across a ticker change**, untouched. That is the reference behaviour, and it is what the frontend
reproduces.

---

## 2. Design

### 2.1 Per chart

Per chart, matching Streamlit's three separate keys. The argument is not preference: **the three
defaults differ** — 5 for valuation, 15 for the other two — and one shared value cannot honour
three different defaults at once. Whatever it initialised to would be wrong for at least one tab.

The cost is real and worth stating: a user who wants five years on all three tabs sets it three
times. The alternative — a shared value with per-chart defaults — is incoherent at startup, and a
shared value with one default silently changes what two of the three charts open on.

### 2.2 No migration is needed, and that is the interesting part

The pickers cycle needed `migrateSelection` because a metric selection's *validity depends on the
ticker*: the option set changes with the profile, so a carried value can name things that no longer
exist. **The window has no such dependence.** Its range is `1–15` for every chart, every ticker and
every profile; there is no value the user can hold that becomes invalid when the context changes.

So there is no `migrateYears` to go with `migrateSelection`, and the state is a plain
`Partial<Record<ChartId, number>>` read with `?? DEFAULT_YEARS[chart]`. Writing one anyway would be
machinery for a case that cannot occur. The reasoning is recorded in `defaults.ts` next to the
constants, with the note that item 15's as-of is the change that would create the dependence — if
the range ever comes to depend on the data, that is where the function goes.

### 2.3 The range stays 1–15 — and 15 is **not** "all history"

The brief asks whether 15 is the maximum useful value, and suggests a "show everything" option
would need a different mechanism than a larger number. Both halves turned out otherwise.

Measured against the export:

| frame | rows | oldest | span | dropped at `years=15` | first year that keeps everything |
|---|---:|---|---:|---:|---:|
| `metrics_long` | 571,114 | 2007-09-30 | 18.9 y | **55,972 (9.8%)** | 20 |
| `valuation_history` | 352,639 | 2005-12-31 | 20.7 y | **51,872 (14.7%)** | 21 |
| `facts_growth` | 242,180 | 2005-12-31 | 20.7 y | **28,321 (11.7%)** | 21 |

So the reference's ceiling hides roughly a tenth to a seventh of the exported history — a real gap
between what the pipeline produces and what the app can show, not a rounding artifact.

And a larger number **would** work: `_window_frame` is just `end >= anchor - DateOffset(years=N)`,
so `years = 21` includes every row today. No different mechanism is required. The genuine
difficulty is that the bound is *date-relative*: 21 covers everything on 2026-08-26 and will stop
doing so as the archive grows, so an honest "All" would have to be a sentinel the builder
interprets, not a bigger integer — and `_window_frame` has no such sentinel.

**Decision: keep 1–15.** Offering 16+ would put the frontend in a state Streamlit cannot produce,
which every cycle so far has treated as out of bounds absent an explicit instruction, and a correct
"All" needs a `figures.py` change that this brief excludes. The gap is recorded here and in
`defaults.ts` as a finding for whoever decides.

### 2.4 Rebuild cost — measured, and no debounce

Every movement rebuilds the figure from the raw series. Measured in Node on the real builders,
600 samples per case (40 repetitions of a full 1→15 sweep, after 30 warm-up builds):

| chart | ticker | panels | traces | points | build p50 | p95 |
|---|---|---:|---:|---:|---:|---:|
| **fundamentals** | **KO** | **13** | **11** | **607** | **0.17 ms** | **0.34 ms** |
| fundamentals | AAPL | 9 | 12 | 702 | 0.15 ms | 0.24 ms |
| valuation | KO | 9 | 9 | 531 | 0.12 ms | 0.26 ms |
| valuation | DAL | 9 | 9 | 540 | 0.11 ms | 0.17 ms |
| growth | KO | 7 | 7 | 412 | 0.08 ms | 0.13 ms |
| growth | DAL | 7 | 7 | 413 | 0.07 ms | 0.13 ms |

**The brief's "29-panel fundamentals chart" does not exist.** The catalogue has 29 metrics but the
most any profile shows is **13** (`consumer_staples`, e.g. KO); valuation tops out at 9 and growth
at 7. KO's fundamentals chart is therefore the widest case reachable, and it rebuilds in **0.17 ms
median, 0.34 ms at p95** — roughly fifty times inside a 16.7 ms frame.

So: **no debouncing.** `onChange` fires per `input` event, so the chart tracks the handle during a
drag, which is the behaviour worth having and the reason the cost was worth measuring at all.

One boundary, stated rather than glossed: this measures **building the figure spec**, which is what
item 8 owns. It does not measure plotly.js re-rendering it, which happens in a browser and is
almost certainly the larger number. If a slider drag ever feels slow, the spec build is not where
the time is going — and that is exactly what this measurement establishes.

---

## 3. The mean line follows the window

No code change was needed: `buildValuation` already computes `meanOver(series.y, …)` where `series`
is the windowed series, so the mean has always moved with `years`. What this cycle adds is the
evidence and the place to read the distinction.

**The first panel's mean line at each setting** (both implementations identical at every one):

| ticker | panel | y=1 | y=3 | y=5 | y=10 | y=15 |
|---|---|---|---|---|---|---|
| AAPL | `pe_ratio` | Ø (harm.) 32.5 | Ø (harm.) 31.7 | **Ø (harm.) 29.0** | Ø (harm.) 21.7 | **Ø (harm.) 16.4** |
| JPM | `pe_ratio` | Ø (harm.) 14.3 | Ø (harm.) 11.5 | Ø (harm.) 10.0 | Ø (harm.) 9.8 | Ø (harm.) 8.4 |
| XOM | `pe_ratio` | Ø (harm.) 19.2 | Ø (harm.) 14.1 | Ø (harm.) 10.7 | Ø (harm.) 12.5 | Ø (harm.) 9.8 |
| DAL | `pe_ratio` | Ø (harm.) 9.9 | Ø (harm.) 7.7 | Ø (harm.) 10.1 | Ø (harm.) 9.1 | Ø (harm.) 7.4 |
| KO | `pe_ratio` | Ø (harm.) 22.6 | Ø (harm.) 23.7 | Ø (harm.) 23.7 | Ø (harm.) 25.1 | Ø (harm.) 20.1 |
| O | `pb_ratio` | Ø 1.4 | Ø 1.2 | Ø 1.2 | Ø 1.3 | Ø 1.2 |

AAPL's benchmark doubles between the 15-year and the 1-year window. This is not cosmetic: the mean
line is what a current multiple is judged against, and the slider chooses which mean.

(O shows `pb_ratio` because `pe_ratio` is hidden for `reit` and the picker falls back — the pickers
report §1.2. It is also arithmetic rather than harmonic, which the label reflects.)

### The distinction, written where the next reader will find it

Two statements that sound alike and are not:

- **The mean follows the window**, because the window defines which observations are *in scope*.
- **The mean does not follow what is drawn within that scope.** Item 13's snapshot marker and item
  14's masked outliers change what appears on the panel while remaining inside the window, and the
  mean must not move for either.

`valuation.ts` keeps these apart structurally rather than by convention: `mean` is computed from
`series.y` and the trace is handed `series.y` through a *different field*, so a later change to
what is drawn has no path to the mean. `plot_metric` does the same thing from the other direction
— `drawn = filtered` unless masking is on, and the mean is always computed from `filtered`.

---

## 4. What was implemented

| file | what |
|---|---|
| `src/charts/defaults.ts` | `YEARS_MIN`, `YEARS_MAX`, `DEFAULT_YEARS` — the last **derived from the builders' own constants**, not restated. The module docstring now covers both controls and records why the window needs no `migrate` |
| `src/WindowSlider.tsx` | **new** — the control: range, live value, "Default (N)" reset |
| `src/ChartView.tsx` | per-chart window state; `years` added to the build call and to its `useMemo` deps; the docstring now explains why a *window* change is a rebuild |

**No builder needed changes.** All three already took `years` and already ran `_window_frame` first;
`ChartBuilder`'s option type has carried `years?: number` since item 5 wrote it as the declared home
for this item.

`panel.ts` also shows as modified in the working tree — that is an **uncommitted dark theme** that
arrived between cycles and is not part of this item. It is accounted for in §5.

---

## 5. Verification

**39 tickers covering all 24 profiles.** Chosen for window sensitivity rather than profile spread:
ten measured in Step 1 as changing their panel count with the window (AAOI, ABNB, ADSK, AJG, ALB,
ABBV, AEE, AEP, ALGM, AIZ), ten short-history tickers (CRWV, FIG, NAVN, SAIL, TTAN, EQR, APLD, AUR,
Q, PSKY), and the established tickers and sector aggregates from earlier cycles.

Each ticker × 3 charts × **8 windows** (0, 1, 2, 3, 5, 10, 15, and `years` omitted entirely) × 3
selections (full catalogue, picker default, first three) — compared as whole figures: every
annotation on ten fields in order, ten axis properties, element-wise traces including nulls, every
shape, and the orphan-axis check on both sides.

| | |
|---|---:|
| cases (chart × ticker × window × selection) | **2,808** |
| figures compared | 2,808 |
| traces | 8,695 |
| **data points, element-wise** | **204,067** |
| annotations, 10 fields in order | 16,952 |
| shapes, 9 fields | 6,390 |
| axis objects, 10 properties | 22,336 |
| **structural checks passed** | **13,461 / 13,461** |
| **field-level differences** | **0** |

### The Step 5 list

| # | check | result |
|---:|---|---|
| 1 | figures match `build_*` at 1, 2, 3, 5, 10, 15 (and 0, and omitted) | ✓ 2,808 figures, 204,067 points, 0 differences |
| 2 | the window changes the panel set, on real tickers | ✓ **15/39 fundamentals, 17/39 valuation, 13/39 growth**, both sides agreeing at every setting — see below |
| 3 | the grid follows `_make_grid` at every setting | ✓ every figure |
| 4 | mean lines follow the window | ✓ 1,377 mean annotations; 36 of 39 tickers change theirs with the window |
| 5 | `years = 0` → all blank, zero orphan axes | ✓ 234 figures (39 × 3 × both sides), 0 traces and 0 orphans in every one |
| 6 | the default path is unchanged | ✓ byte-identical, two ways — see below |
| 7 | picker × window together | ✓ 351 cases: a 3-metric selection at years ∈ {1, 5, 15} produces the same figure as `build_*(concepts=…, years=…)` |
| 8 | `tsc -b`, `eslint .`, `vite build` | ✓ clean; nothing outside `frontend/` changed |

### The panel set really does move

Both implementations agree on the drawn-panel count at every one of the six settings, for every
ticker — and for a large minority of them that count is not constant:

| ticker | profile | chart | drawn traces at years = 1 / 2 / 3 / 5 / 10 / 15 |
|---|---|---|---|
| AAOI | `standard` | valuation | **2 / 2 / 2 / 2 / 8 / 8** |
| ABNB | `marketplace` | fundamentals | **6 / 7 / 12 / 12 / 12 / 12** |
| AJG | `standard` | valuation | 4 / 4 / 5 / 5 / 8 / 8 |
| APLD | `standard` | fundamentals | **1 / 7 / 7 / 9 / 9 / 9** |
| ALB | `materials` | fundamentals | 12 / 12 / 13 / 13 / 13 / 13 |
| ADSK | `standard` | valuation | 7 / 7 / 7 / 7 / 7 / **8** |
| AEP | `utilities` | growth | 6 / 6 / 6 / 6 / 6 / **7** |

AAOI's valuation chart shows two panels at a five-year window and eight at ten years. ADSK and AEP
are the opposite shape — a single panel appears only at the very last step. Universe-wide the
step-1 sweep over 120 tickers found **45 / 62 / 41** tickers whose count changes between years 1
and 15 on fundamentals / valuation / growth, so this is a third to a half of the universe, not a
handful of edge cases.

### The default path

Two guarantees, both byte-level.

**Omitting `years` equals passing the chart's default.** 351 comparisons (39 tickers × 3 charts × 3
selections): the figure built with no `years` argument is byte-identical to the one built with
`DEFAULT_YEARS[chart]`. This is what makes deriving the control's default from the builder's
constant meaningful rather than decorative.

**Against a reconstructed pre-cycle tree** (this cycle's `WindowSlider.tsx` removed and the window
block cut from `defaults.ts`), the default-path specs across all 39 tickers:

| chart | selection | bytes | identical |
|---|---|---:|---|
| fundamentals | full catalogue | 882,936 | **yes** |
| fundamentals | picker default | 106,556 | **yes** |
| valuation | full catalogue | 467,448 | **yes** |
| valuation | picker default | 72,693 | **yes** |
| growth | full catalogue | 604,497 | **yes** |
| growth | picker default | 107,267 | **yes** |

### Three classes of difference, all named

Nothing was tolerated silently. The comparison classifies and counts:

- **Mean-line values: 400 of 1,370 are not bit-identical**, worst relative deviation **7.34 × 10⁻¹⁶
  — 3.3 ULP**, from summation order (numpy against a JS reduce). The rendered labels are string-
  identical at every setting, so nothing visible depends on it. My first pass compared these with
  `==` where the rest of the harness uses a 1e-9 tolerance; that check was wrong, not the code, and
  it now reports the deviation instead of hiding it.
- **±infinity: 117 points** and **tie ordering: 50 points**, both in `metrics_long`, both
  established and bounded in the growth report. The classifier fails the run if a difference is not
  one of those two shapes.
- **The dark theme: 11,168 added annotation colours** plus nine layout/axis keys the reference has
  no equivalent for (`layout.paper_bgcolor`, `layout.plot_bgcolor`, `layout.font`,
  `layout.title.font`, `layout.legend.font.color`, `axis.color`, `axis.gridcolor`,
  `axis.zerolinecolor`, `axis.title.font.color`). Enforced as **"may add, must not change"**: every
  field the reference sets matches exactly, and the allowance is narrow enough that a `tickformat`
  appearing where the reference has `None` would still fail. This is the operator's uncommitted
  work in `panel.ts`, not this item's.

### What was not verified

**Nothing was opened in a browser.** The rebuild cost in §2.4 is the *spec build* only; plotly.js's
re-render is not measured and cannot be from Node. Whether dragging the handle feels smooth is
therefore not established here — only that the part item 8 owns contributes 0.17 ms to it.

---

## 6. What items 12, 13, 14, 15 and 17 should know

1. **`as_of` does two things, and only two builders accept it.** `_window_frame(frame, years,
   as_of)` uses `as_of` both to move the anchor *and* to add an upper bound
   (`windowed[windowed["end"] <= anchor]`). `build_valuation` (figures.py:737) and
   `build_ticker_comparison` (:851) pass a real one; `build_fundamentals` (:589), `build_growth`
   (:646) and `build_raw_facts` (:1111) hardcode `as_of=None` and have no parameter for it. Item
   15's scope is therefore fixed by the reference, not by preference.

2. **The frontend has no upper bound yet, and `seriesFor` has nowhere to put one.**
   `windowCutoff(years, anchor)` returns a lower bound and `seriesFor` filters `end >= cutoff` and
   nothing else — correct today because every call is the `as_of = None` case. Item 15 has to add
   the upper bound to `seriesFor`, not to `windowCutoff`, because it is a second comparison rather
   than a different cutoff. `anchor` is already a parameter on both, which is where the moved
   anchor goes.

3. **Item 15 is the change that gives the window a migration rule.** Today `years` needs none
   because its range never varies. An as-of control makes the two interact: `years` counted back
   from a chosen date can reach before the data starts, and the pair (`as_of`, `years`) can select
   an empty window that neither control looks wrong on its own. `defaults.ts` is where that rule
   would go, next to `migrateSelection`.

4. **The mean's two invariants are different invariants.** It *does* follow the window (§3) and
   *does not* follow what is drawn inside it. Items 13 and 14 only touch the second. The structural
   guarantee is that `PanelSpec.mean` and `PanelSpec.traces[].y` are separate fields — a masked or
   marker-augmented trace cannot reach the mean because there is no path from one to the other.

5. **The window changes the panel set often enough to design for.** Measured over 120 tickers:
   **45 change their drawn-panel count** between `years=1` and `years=15` on fundamentals, **62** on
   valuation, **41** on growth. Item 17's empty-panel notice therefore has to be recomputed on every
   slider movement, not cached per ticker — the set of blank panels is a function of the window, and
   for a third to a half of the universe it is not a constant one.

6. **The widest chart any profile reaches is 13 panels, not 29.** The fundamentals catalogue has 29
   metrics and `consumer_staples` shows the most at 13; valuation tops out at 9 and growth at 7.
   Anything sized against "the whole catalogue" — a layout budget, a performance target, a grid
   assumption — is sized against a case that cannot occur. Item 12's comparison chart is the one
   that can exceed these, because its panel count comes from the requested ticker list.

7. **The reference's 15-year ceiling hides 10–15% of the exported history** (§2.3). Reachable with
   `years = 21` today; a durable "all history" needs a sentinel `_window_frame` does not have.

8. **The uncommitted dark theme in `panel.ts` is additive, and now measured as such.** Nine keys the
   reference has no equivalent for — `layout.paper_bgcolor`, `layout.plot_bgcolor`, `layout.font`,
   `layout.title.font`, `layout.legend.font.color`, `axis.color`, `axis.gridcolor`,
   `axis.zerolinecolor`, `axis.title.font.color` — plus a colour on the subplot-title annotations.
   The verification enforces **"may add, must not change"**: a field the reference sets must match
   exactly, and the allowance for an added colour is narrow enough that, say, a `tickformat`
   appearing where the reference has `None` still fails. Whoever finishes that theme should keep it
   inside those bounds, or the comparison harness stops being able to tell a theme from a defect.

No scratch files were left behind.
