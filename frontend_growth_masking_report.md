# Outlier masking for the growth chart

Shipped. The growth chart has the toggle, the caption and the expander, wired into the same
`charts/outliers.ts` the valuation grid uses, with `k = 5` and the ratio-to-median rule unchanged.
Per mode, window first, and the visibility fix untouched.

**One thing the brief did not anticipate, and it needs to be first: the reference measured this
extension and declined it.** `figures.py:190-196` is explicit —

> *"Valuation multiples only, also measured. The rule needs a positive median to mean anything, and
> only the valuation frame has one everywhere: 0.0% of its 3,260 series have a non-positive median,
> against 6.2% of fundamentals and **24.7% of growth**. Growth is the clear case against extending —
> it crosses zero constantly, its median max-to-median ratio is 10.65, and 85% of its series would
> fire at k=4. That is not the rule finding outliers, it is the rule being meaningless."*

I re-measured it on today's data rather than repeating it, because both the catalogue (10 → 39
concepts) and `min_base_ratio` (0.33 → 0) have changed since. **The reference's numbers hold and are
slightly worse**: 24.8% non-positive median, and 90.7% of applicable series fire at the shipped
k = 5. §1.6 is the measurement.

The honest summary is not "the reference was right" or "the brief was right" — it is that **both
halves are true at once**:

- On the panels the brief is aiming at, masking works spectacularly. SWK's `EPS_TTM_CALC` YoY goes
  from a y-axis topping **25,542,473,125.7%** to one topping **10.4%**. That panel is unreadable
  without the toggle and fine with it.
- **50.6%** of the panels where the rule fires have a genuine blow-up (a hidden point above +200%);
  the other **49.4%** fire only on ordinary values. At the *point* level it is worse: **53.2% of the
  154,508 points the rule would hide are growth rates at or below +50%**, and only **3.5%** are the
  above-+1,000% values the brief cites. The median series containing a flagged point has a median
  growth of **+2.91%**, so "5× the median" is about +15%.

So the control is worth having and it over-fires by roughly two to one. That is stated in the
toggle's own help text rather than left for the reader to discover, and §5.1 carries the measured
alternative.

---

## 1. Step 1 — the reference, read exactly

### 1.1 Where the mask lives — a derived view of the trace's arrays, rows removed

Confirmed from `charts/valuation.ts:178-184`, unchanged:

```ts
const hidden = mask && !empty ? outlierMask(series.y) : null;
const hiddenCount = hidden ? hidden.filter(Boolean).length : 0;
const drawn = hiddenCount
  ? { x: series.x.filter((_, i) => !hidden![i]), y: series.y.filter((_, i) => !hidden![i]) }
  : { x: series.x, y: series.y };
```

Rows **removed**, not nulled — `filtered.loc[~hidden]` (figures.py:376), so `x` shrinks with `y`.
`PanelSpec.hiddenCount` carries the count for the per-panel note; the points go to the expander via
`outlierReport`, never through the figure.

**It composes with growth's trace shape without changing either.** Growth's panel has exactly one
trace and no second entry — no snapshot marker (valuation's), no dual TTM/quarterly pair
(fundamentals'). So the transformation applies to `traces[0]` and there is nothing else in the array
for it to reach. The only difference on this chart is *which array* `y` is: growth reads it through
`valuesFrom(frame, series, mode.column)` rather than `series.y`, because `facts_growth` carries two
numeric columns over one row set. §2 is that decision.

### 1.2 `k` — 5, global, confirmed from the code

`OUTLIER_MEDIAN_RATIO = 5` and `OUTLIER_MIN_POINTS = 8` (`charts/outliers.ts:28,31`, mirroring
figures.py:179,187). One value, no per-chart-type variant anywhere in either implementation, and the
port re-derives nothing — it cites the calibration rather than repeating it. **Unchanged by this
task**, per the brief. Verified at runtime as part of §4.1: the Python and TypeScript constants are
compared as a check, not assumed.

### 1.3 No mean line — still true, and what invariance means here

`build_growth` never calls `plot_metric`, so it has no `show_mean` to pass (figures.py:660-690); the
port's `buildGrowth` sets `mean: null` unconditionally and still does. The visibility cycle touched
only `is_hidden`, so nothing there could have changed it. Re-verified after this change: across 10
tickers × 2 modes × masked and unmasked, **no trace named like a mean exists and the trace count
never exceeds the panel count** (§4.4).

So the valuation invariance obligation — *"the mean lines are unchanged, they are still computed over
the full series"* — has no subject here. What replaces it is the weaker but real obligation the brief
names: **masking changes what is drawn and nothing else.** I checked what else reads the growth
series:

| reader | reached by masking? |
|---|---|
| `buildGrowth`'s panel traces | **yes — this is the whole change** |
| the panel's y-axis range | yes, derived from the drawn points; that is the point of the control |
| a mean line | none exists |
| a caption quoting a value | none — growth's only captions are the mode control's and the masking control's own |
| `buildComparison` on a growth concept | **no.** It reads `facts_growth` through its own builder, and masking there is gated `if (mask && isValuation)` (charts/comparison.ts:216). Verified: `comparison:Revenue` is byte-identical with `mask: true` and `mask: false` (§4.8) |
| the Data tab / Raw Facts / exports | no — masking never touches a frame |
| `outlierReport` | reports what *would* be hidden; independent of the flag, as the reference computes it |

That is the invariance this chart can promise, and it is what `GROWTH_MASKED_NOTE` says instead of
the valuation sentence.

### 1.4 The toggle's conditional presence and the expander

Reproduced from `OutlierControls.tsx` unchanged — the component already returns `null` on an empty
report (*"a toggle that appears on a clean chart teaches the reader to ignore it"*, app.py:942), and
the report is computed over the **windowed** series and the **current selection**, before and
independently of the toggle's own state. The expander keeps its label `Show the {N} extreme
value(s)`, its default-closed state, its `**{label}** — median {median:,.2f}` heading and its
`Period / Value / x median` table with the value at full `csvNumber` precision and the ratio at
`.toFixed(1)`. Growth needed **no change to any of it** — only two new strings (§3).

### 1.5 The ⌈n/2⌉ floor holds for growth's longer series — checked, not assumed

It is a property of the function, not of the length: at least half of any series lies at or below its
median, so at least ⌈n/2⌉ points have a ratio ≤ 1 and `k = 5 > 1` cannot reach them. Confirmed
empirically over **every** growth series in the universe, both modes — 23,441 series:

```
longest growth series in the universe: ESE/Goodwill/yoy, 66 periods
highest hidden share anywhere: AFL/OperatingIncomeLoss_TTM/yoy -- 22/44 = 50.0%
```

The bound is **exactly touched** and never crossed. AFL hides precisely half of a 44-point series,
which is the theoretical maximum, and no series anywhere goes past it. Length is irrelevant, as
predicted, and the 66-period series is not the one that gets closest.

### 1.6 The measurement the reference's note demanded

Population: every growth series a reader can actually reach after the visibility fix, windowed to 15
years, both modes — **23,652 series**.

| | series | |
|---|---:|---|
| rule applies | 16,005 | 67.7% |
| median ≤ 0, rule inert | 5,877 | **24.8%** (the reference measured 24.7%) |
| fewer than 8 usable points | 1,770 | 7.5% |

Of the 16,005 applicable series, **14,521 (90.7%) fire at k = 5** — the reference predicted 85% at
k=4; it is now 93.6% at k=4. **19.99% of drawn points** on those series would be hidden.

What gets hidden, by the growth rate it represents:

| the hidden point is | count | share |
|---|---:|---:|
| ≤ +25% | 51,994 | 33.7% |
| +25% … +50% | 30,151 | 19.5% |
| +50% … +100% | 29,032 | 18.8% |
| +100% … +200% | 19,930 | 12.9% |
| +200% … +500% | 13,301 | 8.6% |
| +500% … +1,000% | 4,727 | 3.1% |
| **above +1,000%** | **5,373** | **3.5%** |

Worked examples of what "5× the median" reaches on a series centred near zero:

| | value hidden | series median | ratio |
|---|---:|---:|---:|
| GD `DepreciationAndAmortization` YoY | **+5.00%** | +0.51% | 9.8× |
| MELI `Goodwill` YoY | **+5.00%** | +0.73% | 6.8× |
| BRO `Capex` QoQ | **+5.00%** | +0.24% | 20.6× |

**No value of `k` repairs this**, which is why the follow-up is a different rule and not a different
number:

| k | points hidden | % of drawn | share that are >+200% |
|---:|---:|---:|---:|
| **5 (shipped)** | 154,508 | 19.99% | **15.1%** |
| 10 | 95,126 | 12.31% | 22.6% |
| 20 | 56,962 | 7.37% | 31.5% |
| 50 | 28,709 | 3.71% | 42.0% |
| 100 | 17,089 | 2.21% | 48.1% |
| 200 | 10,331 | 1.34% | 51.7% |

Even at k = 200, only half the hidden points are extreme. Ratio-to-median does not separate on a
signed quantity centred near zero, and that is a property of the instrument.

Read at the **panel** level rather than the point level the picture is better, which is the fairest
framing: of the 14,521 panels where the rule fires, **7,353 (50.6%)** have a genuine blow-up as their
top hidden point. Five panels in the whole universe end up flat (every kept point identical) — all
`DividendsPerShare`, where a series that is 0% most quarters makes any increase a 5× event:
`TER/DividendsPerShare/yoy` hides 22 and keeps 23 identical values.

---

## 2. Step 2 — the two-column question

### 2.1 Per mode, not per concept

**Per mode**, and the reasoning is not only that the distributions differ — it is that the rule's
denominator is the series' own median, so a shared mask would judge one column's values against the
other column's scale. The two columns are measurably different populations: 3,587 QoQ series have a
non-positive median against 2,290 YoY ones (§1.6), so QoQ is *more* often the mode where the rule is
inert.

It also falls out of reusing the shipped code unchanged. `outlierMask(y)` takes the array it is
handed; the only decision was which array to hand it, and `y` is already the active mode's column
because that is what the panel draws.

**Measured consequence:** across the universe there are **3,225 panels where exactly one mode has an
outlier and the other has none.** `A/Revenue` is one — YoY hides 0, QoQ hides 11 — and it is the
worked example in §4.3.

### 2.2 Recompute on a mode switch — structurally, not by invalidation

There is no cached mask to go stale. `buildGrowth` recomputes the whole figure when `options.mode`
changes (it is in `ChartView`'s `useMemo` dependency list), and inside the panel loop the mask is
derived from `y`, which is itself derived from `mode.column`:

```ts
const y = valuesFrom(frame, series, mode.column);
const hidden = mask && !empty ? outlierMask(y) : null;
```

A stale mask would require a mask that outlives a rebuild, and there is nowhere for one to live.
Verified anyway rather than argued: for every reported series in every ticker and mode, the report's
`median` equals the median of *that mode's* column to within 1e-12 (§4.3).

### 2.3 Window first, then mask

`seriesFor(frame, id, cutoff)` resolves the windowed rows; `valuesFrom` reads the column over those
rows; `outlierMask` runs on the result. The same order the reference fixes structurally by masking
inside `plot_metric` after `_window_frame` has run, so the ratio is always against the median of what
is on screen and `k` keeps meaning the same thing as the slider moves. The years slider and the
masking toggle were exercised together in §4.9 (mask on at 7 years, then a mode switch, then a tab
round-trip).

---

## 3. Step 3 — what was implemented

Three files, all in `frontend/`. **No Python change, no export change, no new module** — the brief's
"reuse, not redesign" held: `charts/outliers.ts`, `panel.ts`, `createGrid`, `drawPanel` and
`OutlierControls.tsx`'s component are untouched.

| file | change |
|---|---|
| `src/charts/growth.ts` | `GrowthOptions.mask?`, `GrowthResult.outliers`, the five-line per-panel mask on the active mode's column, `hiddenCount`, and the `windowed` array feeding `outlierReport` |
| `src/OutlierControls.tsx` | `GROWTH_MASK_HELP` and `GROWTH_MASKED_NOTE` — two new exported strings; the component itself is unchanged |
| `src/ChartView.tsx` | `MASK_STRINGS` per chart; `masked` state became per chart |

### 3.1 Growth needed its own two strings

`VALUATION_MASKED_NOTE` says *"The mean lines are unchanged — they are still computed over the full
series, including the hidden points."* On a chart with no mean lines that sentence asserts the
existence of something the reader cannot see. `GROWTH_MASKED_NOTE` states the invariance that does
apply:

> Nothing else moved: this chart draws no mean line, and no figure shown elsewhere is computed from
> these points. The hidden values are listed below and are still in the data tab and the exports.

And the help text carries §1.6 to the point of use, because a reader who does not know that a growth
series centres near zero will read the hidden set as "the extreme values" when half of it is not:

> Hides points more than 5x the panel's own median. Growth rates centre near zero, so on a series
> growing a few percent a quarter that threshold is reached by an ordinary good quarter, not only by
> an extreme one — read the list before trusting it. Applies per panel, per mode, and only to what is
> drawn: the values stay in the data tab and the exports.

### 3.2 The mask flag became per chart

It was one boolean while the valuation grid was the only holder of the control. Growth has one now,
and the reference's own shape is one session-state key per tab (`val_mask_outliers`, plus a separate
one on the comparison tab — which is why `ComparisonView` already keeps its own). Sharing it would
have made "Hide extreme values" on the growth tab silently arm the valuation grid, where the same
`k` means something very different.

**No observable change for valuation**: it is still the only writer of its own key. Confirmed in
§4.9 — arming the growth toggle leaves the valuation tab's unarmed.

---

## 4. Step 4 — verification

### 4.1 The rule, against the reference, element-wise

`figures.outlier_points` against `charts/outliers.outlierMask`, and `outlier_report` against
`outlierReport`, over 10 tickers × 2 modes × every visible concept — 392 series, 21,622 points:

```
4,927/4,928 checks pass, 2,946 points flagged
```

Compared: `k`, `min_points`, the usable count, the median, the full boolean mask position by
position, and every reported point's date, full-precision value and rounded ratio.

**The one failure is real and pre-existing.** `CRM:yoy/OperatingIncomeLoss` at 2023-04-30 has a ratio
of exactly **75.05** (19.6 / 0.2611592271818788). The shipped `round1` is
`Math.round(v * 10) / 10` → **75.1**; app.py's `.round(1)` is numpy's round-half-to-**even** →
**75.0**. It is a display divergence in the *ratio column of the expander*, not in the rule — the
mask agrees — and it is in the module as shipped, not something this task introduced. Growth's data
is simply the first to land a ratio exactly on a half boundary: **1 of 2,946**. Left alone, because
fixing it edits a module the brief puts out of scope and would move valuation's expander output too;
recorded in §5.2.

**Sensitivity.** Mutating `OUTLIER_MEDIAN_RATIO` from 5 to 6 takes the same harness to
**3,324/4,588** (1,264 failures, naming the constant and then the masks). Restored and re-verified.

### 4.2 The figure drops exactly the reported points, and the range collapses

Every panel in all 20 scenarios, comparing `mask: false` against `mask: true` against the report:

```
407/407 checks pass
```

`x` shrinks with `y`, the removed dates are exactly the reported ones, and the report itself is
identical with the flag on and off.

Rendered, in a real browser:

| panel | points | max drawn, before → after |
|---|---|---|
| SWK `EPS Growth (TTM)` YoY | 50 → 29 | **25,542,473,125.7% → 10.4%** |
| A `Stock Issued Growth (Quartal)` YoY | 54 → 32 | 1,100.0% → 8.3% |
| A `EPS Growth (TTM)` YoY | 19 → 15 | 71.0% → 26.4% |
| A `Revenue growth (Quartal)` QoQ | 59 → 48 | 17.6% → 4.7% |

Across the universe the median panel that fires has its drawn span shrink **3.4×**.

The expander was read out of the DOM and checked against `outlier_points` recomputed from the parquet
— row counts, `dd.mm.YYYY` periods, the `Show the N extreme values` label agreeing with the row
count, the `{median:,.2f}` heading, and **the value at full `repr` precision** rather than
display-rounded. 142/142 checks across three scenarios.

### 4.3 Per-mode independence

Three separate checks, all passing (part of the 47,051 below):

- masking one mode never alters the other mode's figure (digest-compared);
- every reported series' median equals **that mode's** column median to 1e-12, so no report is built
  from a stale column;
- the two modes genuinely diverge — **3,225 panels have an outlier in exactly one mode**.

The worked example, in the rendered UI, same ticker and same three panels:

| A, three panels selected | YoY | QoQ |
|---|---|---|
| `Revenue` | untouched | **59 → 48 points** |
| `EPS_TTM_CALC` | **19 → 15** | untouched |
| `StockIssued` | **54 → 32** | untouched |

One toggle, opposite panels in the two modes. And the control's *presence* follows: with only
`EPS_TTM_CALC` and `StockIssued` selected, the toggle is **present in YoY and absent in QoQ**.

`StockIssued` QoQ is the honest counter-example in the same screenshot: it keeps a **+2,900%** point
because its own median is high enough, while YoY hides an **+8.3%** one. Both are the rule working
as specified; §1.6 is why that reads oddly.

### 4.4 No mean line introduced — the negative check, stated

10 tickers × 2 modes × {masked, unmasked}: no trace is named like a mean, and the trace count never
exceeds the panel count in any of the 40 figures. `mean: null` is still unconditional in
`buildGrowth`. Explicitly checked rather than skipped for having nothing to break.

### 4.5 The ⌈n/2⌉ floor, on growth's longest series specifically

Every series in the universe, both modes — see §1.5. Longest is **ESE/Goodwill/yoy at 66 periods**;
the tightest case anywhere is **AFL/OperatingIncomeLoss_TTM/yoy at exactly 22/44 = 50.0%**. No series
is fully masked, and none exceeds the bound.

§4.3–4.5 together:

```
47,051/47,051 checks pass
```

### 4.6 The visibility fix is undisturbed

Two checks.

`growth_visibility_fix_report.md`'s cross-check re-run unchanged:

```
is_hidden cross-check: 23,751/23,751 pass (0 failures)
dead growth panels still offered: 0
visible (profile, growth) pairs: 499
```

And, at the builder, over **all 609 tickers × 2 modes / 24,882 offered panels**:

```
7,308/7,308 checks pass
```

covering: the panel list is identical with `mask` on and off; `offerable` is identical; the panel
list equals the registry's visibility row; and a **masked** request naming hidden concepts still
returns `figure: null`. Masking narrows points inside a shown panel; it cannot add or remove a panel.

### 4.7 Toggle conditional presence

Read from the rendered page:

| ticker, selection, mode | control |
|---|---|
| SWK, `EPS_TTM_CALC`, YoY | **present** |
| A, `Revenue` + `EPS_TTM_CALC` + `StockIssued`, YoY | **present** |
| A, same three, QoQ | **present** |
| A, `EPS_TTM_CALC` + `StockIssued`, QoQ | **absent** |
| CRM, valuation tab | **present** (unchanged) |

The fourth row is the rule doing its job in both directions: those two panels have outliers in YoY
and none in QoQ, and the control disappears for the mode where it would do nothing.

### 4.8 The other three charts are unchanged

Digest A/B against the figures recorded by the previous cycle's report, same scenarios:

```
26/26 byte-identical -- 6 fundamentals, 6 valuation, 12 unmasked growth, 2 comparison
```

The 12 unmasked growth digests matching is the load-bearing one: `mask` defaults to `false`, so every
existing baseline stays valid. With `mask: true`, **12 of 12** growth scenarios move — the flag is
not inert.

Comparison: `comparison:Revenue` is byte-identical masked and unmasked, because the growth-concept
gate at `charts/comparison.ts:216` is untouched. `comparison:pe_ratio` is also identical, and that is
not a regression — the report is genuinely empty for those three tickers over 15 years, checked
rather than assumed.

### 4.9 Standing suite and toolchain

**35/35**, with masking exercised throughout:

| check | result |
|---|---|
| `check-chart-width` | growth masked YoY/QoQ 24 panels, growth unmasked 24, fundamentals 11, valuation 9 — plot 1087px in a 1087px host, doc 1570/1570, **0 overflowing**, no pinned width. Masking does not change the panel count |
| `check-tab-state` | opens unmasked; mask + 7-year window both take; mask survives a mode switch and a tab round-trip; **the valuation tab's toggle stays unarmed** when growth's is on |
| `check-table-format` | data and Raw Facts render 8 tables / 1,135 cells / 109 row headers |

```
npx tsc -b       clean
npx vite build   ✓ built in 13.87s
npx eslint .     4 errors -- the same four pre-existing ones
```

The four are `Chart.tsx:11` (`no-explicit-any`), `ChartView.tsx` ×2 (`rules-of-hooks`: the operator's
fullscreen `useState`/`useEffect` sit after the `if (!build) return` early return — this task moved
their line numbers from 219/221 to 240/242 and nothing else), and `Sidebar.tsx:94`
(`set-state-in-effect`). All predate this cycle and live in code it does not touch.

---

## 5. Follow-ups

1. **The rule is the wrong instrument for growth, and a threshold is the right one.** Not changed —
   the brief forbids touching `k` or the rule, and rightly, since that is a calibration decision with
   its own cycle. The evidence, on the same 772,921-point population:

   | rule | points hidden | % of drawn | share that are >+200% |
   |---|---:|---:|---:|
   | ratio-to-median, k = 5 (shipped) | 154,508 | 19.99% | **15.1%** |
   | absolute cut above +100% | 48,390 | 6.26% | 50.6% |
   | **absolute cut above +200%** | **24,463** | **3.17%** | **100%** |
   | absolute cut above +1,000% | 5,413 | 0.70% | 100% |

   An absolute cut is the natural rule here because a growth rate is already normalised — it is a
   ratio, so it has an absolute scale that a P/E does not, and "+200%" means the same thing on every
   panel while "5× the median" does not. The `min_base_ratio` mechanism this catalogue turned off is
   the same idea applied at computation time rather than at draw time
   (`growth_expansion_report.md`), so the pipeline already has the vocabulary for it.

2. **`round1` uses round-half-up where the reference uses round-half-to-even** (§4.1). One ratio in
   2,946 on growth, and presumably none yet on valuation — but it is a divergence from app.py's
   `.round(1)` and it is in the shipped module. The fix is `round1`, and the check is re-running the
   valuation A/B, which is why it is not folded into a growth cycle.

3. **Growth concepts on the *comparison* chart are still unmasked**, by the `isValuation` gate at
   `charts/comparison.ts:216` (figures.py:974). The brief scopes this task to the growth chart and
   forbids changing comparison's masking, so the asymmetry stands and is stated: a reader can hide
   SWK's 25-billion-percent point on the Growth tab and not on the Comparison tab. Whether that gate
   should widen depends on follow-up 1 — extending today's rule there would import today's
   over-firing.

4. **The `median ≤ 0` branch is silent.** 24.8% of growth series make the rule inert, and the reader
   is told nothing: the toggle is simply absent, which is indistinguishable from "this panel is
   clean". On the valuation grid that case does not occur (0.0% of series), so the reference never
   had to say anything. A one-line caption distinguishing "nothing to hide" from "the rule does not
   apply here" would be a real improvement, and it is a UI addition rather than a masking change.

5. **`outlier_masking_report.md` still does not exist** — not in the working tree and not in any
   commit; I searched all of history again, as the previous cycle did. The calibration lives in
   `figures.py:160-196` and that is the citable source. Recorded so the next cycle does not go
   looking.

---

## 6. Mistakes of mine, for the record

- My first DOM capture read every panel as unchanged after toggling the mask on `A/mixed`. Cause: a
  hash-only `Page.navigate` is a **same-document** navigation, so React state — the mask flag
  included — survived from the previous ticker's visit, and I was comparing masked against masked.
  Fixed by resetting the toggle at the start of each visit. The app was behaving correctly the whole
  time; the harness was reading a state it had set itself.
- I wrote `${"${JSON.stringify(id)}"}` into a CDP template literal, which interpolates the *string*
  rather than the value and produced `SyntaxError: Unexpected token '{'`. Same family as the
  backtick-in-a-template slip from the QoQ cycle.
- I picked "KO/Revenue" as a presumed clean panel for the conditional-presence test and it turned out
  to have outliers. Replaced with a case chosen from the measurement rather than from intuition,
  which is what the rest of this report does and what I should have done first.
