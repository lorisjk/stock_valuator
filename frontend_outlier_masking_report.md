# Outlier masking — item 14

The four findings item 13 handed over held up, all four, and one of them got sharper. One premise in
the brief was wrong (the toggle's scope), one design suggestion in the brief was declined with a
reason (nulling versus removing), and the harness caught one ordering mistake of mine that no amount
of reading would have.

**A note on sources.** `outlier_masking_report.md` does not exist — not in the working tree and not
in any commit in this repository's history. I searched every commit for one. The calibration lives
in `figures.py`'s own comments (figures.py:171-199), which are unusually complete about it, and in
`streamlit_inventory.md` §5. Since the brief asked me to confirm from the code rather than from that
report anyway, nothing was lost; it is recorded here so the next cycle does not go looking.

---

## 1. Step 1 — the reference, read exactly

### 1.1 The rule and `k`

`outlier_points` (figures.py:201-221):

```python
usable = values[np.isfinite(values)]
if len(usable) < min_points: return mask          # all False
median = usable.median()
if not (median > 0): return mask                  # all False
mask.loc[usable.index] = (usable / median) > k
```

Still **ratio-to-median**, unchanged from the design description. `k = OUTLIER_MEDIAN_RATIO = 5.0`
(figures.py:179) and **global** — one value, used by the valuation grid and the comparison chart
alike, with no per-chart-type variant anywhere in the file. A second constant gates it:
`OUTLIER_MIN_POINTS = 8` (figures.py:187), below which the rule does not apply at all.

Both constants are measured rather than round, and the derivations are in the comments above them —
k=4 additionally hides DAL's 47.2, which does not need hiding; k=6 keeps CRM's 337.8, which does.

### 1.2 Which charts have the toggle — **valuation + comparison**

The inventory's "both tabs" is right, and the two are the **valuation grid and the comparison
chart**. Confirmed three ways:

- `mask_outliers` appears on exactly three functions: `plot_metric` (figures.py:348),
  `build_valuation` (figures.py:716), `build_ticker_comparison` (figures.py:912).
- `build_fundamentals` and `build_growth` **have no such parameter**, and their `plot_metric` calls
  leave it at its `False` default.
- The scope note (figures.py:190-199) says why, with the measurement: *"0.0% of its 3,260 series
  have a non-positive median, against 6.2% of fundamentals and 24.7% of growth. Growth is the clear
  case against extending — it crosses zero constantly … That is not the rule finding outliers, it is
  the rule being meaningless."*

Inside the comparison chart the gate is `if mask_outliers and is_valuation` (figures.py:974), and
`comparison_outlier_report` returns `{}` early for a non-valuation concept (figures.py:891). So
picking a growth or fundamentals concept there ignores the flag rather than applying a rule whose
precondition does not hold.

### 1.3 The toggle's conditional presence — **hidden when inert**

`app.py:942` (`if outliers:`) and `app.py:1054` (`if cmp_outliers:`). The comment is the rule: *"a
toggle that appears on a clean chart teaches the reader to ignore it."*

Two details that matter for a faithful port: the report is computed over the **windowed** frame and
the **current selection** (`figures.outlier_report(figures._window_frame(val_frame, years, as_of),
ticker, chosen)`, app.py:939), so the control appears and disappears as the slider and the picker
move; and it is computed *before* and independently of the toggle's own state.

### 1.4 The expander

`app.py:999` for the grid, `app.py:1093` for the comparison chart. Label
`Show the {N} extreme value(s)`; **default closed** (`st.expander` with no `expanded=True`); content
per series a heading `**{label}** — median {median:,.2f}` and a table of `Period`, `Value`,
`x median`, where the ratio is `.round(1)` and **the value is not rounded at all**. Present whether
or not masking is on.

Its reason is stated at the call site (app.py:997): *"A silent filter would be the wrong thing in a
tool whose argument is auditability, so every hidden number is one click away, with the ratio that
got it hidden."*

### 1.5 Direction — **one-directional, high side only**

`(usable / median) > k`, and the comment above the constant (figures.py:190) says the measurement was
done: *"across the fifteen calibration series not one point sits below 0.2x its median, and the
lowest ratio anywhere in the set is 0.29x. A two-sided rule would be machinery for a case that does
not occur."*

---

## 2. Step 2 — design

### 2.1 Where the mask lives — **rows removed, not nulled**

The brief argued for nulling masked points so they become gaps: *"matching how the pivot/display
work treats absence — a masked point becomes a gap, not a deleted array element, so x-alignment
across traces is preserved."*

**Declined, and the reference is the reason.** `plot_metric` builds `drawn = filtered.loc[~hidden]`
(figures.py:376) — a row filter, so `x` shrinks with `y`. Nulling would render *identically*, since
`connectgaps: true` bridges a null exactly as a removed row is bridged; but it would emit a longer
`x` array than the reference, and the element-wise comparison in §4.1 would fail on every masked
panel. And the alignment the brief wanted to preserve is not a constraint here: each trace in this
figure spec carries its own `x`, so there is nothing to align against.

Otherwise the brief's shape is exactly right — this is **a derived view of an existing trace's
arrays**, not a new trace and not a new field:

```ts
const hidden = mask && !empty ? outlierMask(series.y) : null;
const drawn = hiddenCount ? { x: series.x.filter(…), y: series.y.filter(…) } : { x: series.x, y: series.y };
```

It composes with the two other users of `PanelSpec.traces` without either noticing:

- **the snapshot marker (item 13)** is a *separate entry* in `traces`, appended after this one, and
  masking touches only `traces[0]`. §4.3 measures that it is untouched;
- **the dual TTM/quarterly traces (item 5)** are on the fundamentals chart, which has no
  `mask_outliers` at all (§1.2), so they never meet the mask. Had they, each is its own entry with
  its own arrays and the same per-trace transformation would apply to each.

`PanelSpec` gained one optional field, `hiddenCount`, for the annotation — a count, not the points.
The points go to the expander, which is built from `outlierReport`, not from the figure, so the
drawing layer stays a drawing layer.

### 2.2 The toggle's scope — **one toggle, per-panel rule**

The brief said the original design "argued for per-panel (one panel might need it, eight might
not)". What shipped is **one flag for the whole chart with the rule evaluated per panel**, and
figures.py:731 is explicit in a way that is easy to read backwards:

> `mask_outliers` … **Per panel, not per figure**: the flag is passed to every panel, but the rule is
> evaluated against each panel's own series, so a grid where one multiple is pathological and eight
> are not loses points from the one.

So the *behaviour* the brief wanted is there — eight clean panels lose nothing — but it comes from
the rule, not from eight controls. app.py keeps one `st.session_state` key (`val_mask_outliers`) and
renders one `st.toggle`. Matched: one boolean in `ChartView`, one in `ComparisonView`, separate from
each other because app.py gives them separate keys.

### 2.3 Finding 2's decision — **the marker is masked independently, matching the reference**

Stated as a decision, with §5's numbers behind it: `snapshot_point` and `mask_outliers` are
independent parameters of `plot_metric`, and the snapshot trace is added after the mask has already
been applied to `drawn`. **This port does the same.** The consequence is measured in §6.

### 2.4 The expander's content

Full precision, and specifically the *same* full precision as everywhere else: values render through
`csvNumber` — item 11's Python-`repr` renderer, the one the CSV downloads use — so a number copied
out of the expander matches one copied out of a download character for character. The `x median`
ratio is `.toFixed(1)`, matching app.py's `.round(1)`; the heading's median is grouped to two
decimals, matching `{median:,.2f}`. §4.6 verifies the values against the source frame.

### 2.5 Window first, then mask

The reference fixes the order structurally rather than by convention: `build_valuation` calls
`_window_frame` (figures.py:738) and hands the *result* to `plot_metric`, which masks it
(figures.py:372). The comparison chart is the same shape through `_comparison_selection`
(figures.py:851). So the ratio is always against the median of **what is on screen**.

That matters exactly as the brief says: run it on the unwindowed series and the same `k` would mean
something different at every slider position. This port keeps the order — `seriesFor(frame, id,
cutoff)` then `outlierMask(series.y)` — and §4.1 exercises it at 5 and 15 years, where the masked
sets genuinely differ (CRM hides 4 points at 5y and 5 at 15y).

`as_of` composes for free: it is an input to `windowCutoff`, upstream of everything here. Item 13's
snapshot suppression is likewise upstream and unaffected. Item 15's still-missing upper bound will
enter at the same place and needs nothing from this cycle.

---

## 3. Step 3 — what was implemented

Nine files, all inside `frontend/`:

| file | change |
|---|---|
| [`src/charts/outliers.ts`](frontend/src/charts/outliers.ts) | **new.** `OUTLIER_MEDIAN_RATIO`, `OUTLIER_MIN_POINTS`, `median`, `outlierMask`, `outlierReport`, `hiddenTotal`. Pure, no DOM, runs in Node. |
| [`src/charts/panel.ts`](frontend/src/charts/panel.ts) | `PanelSpec.hiddenCount` → the bottom-right per-panel note; `ComparisonPanelSpec.hiddenByTicker` → the top-right figure note. |
| [`src/charts/valuation.ts`](frontend/src/charts/valuation.ts) | `mask?: boolean`; the per-panel mask; `outliers` in the result. |
| [`src/charts/comparison.ts`](frontend/src/charts/comparison.ts) | `mask?: boolean`, gated on the concept being a valuation one; the per-line mask; `outliers` in the result. |
| [`src/OutlierControls.tsx`](frontend/src/OutlierControls.tsx) | **new.** Toggle + caption + expander, one component for both tabs, with the four reference strings. |
| [`src/outliers.css`](frontend/src/outliers.css) | **new.** |
| [`src/ChartView.tsx`](frontend/src/ChartView.tsx) | the toggle state and the controls; **and** the green-circle caption — see below. |
| [`src/ComparisonView.tsx`](frontend/src/ComparisonView.tsx) | the toggle state and the controls. |
| [`src/data/csv.ts`](frontend/src/data/csv.ts) | `csvNumber` exported (no behaviour change; the A/B in §4.8 shows the CSV output is byte-identical). |

### 3.1 One thing added that item 13 had missed

app.py:1015 carries a fixed caption on the valuation tab — *"The green circle is the current multiple
… It is excluded from the mean line, and hidden when the as-of date predates it."* Item 13 shipped
the marker without it. I found it while reading app.py's outlier block, which sits immediately above
that line, and added it rather than leaving a known gap in the block I was editing. It is also the
sentence that makes the same promise about the marker that the masking caption makes about hidden
points, so the two belong together.

---

## 4. Step 4 — verification

### 4.1 Against the reference, element-wise

**260 scenarios · 60,790 checks · 0 failures.** 40 tickers × {5y, 15y} × {masked, unmasked} for the
valuation grid, plus 26 ticker groups × 5 concepts × {masked, unmasked} for the comparison chart.
The sample is deliberate: **CRM** is the calibration's canonical case; **DAL, INTC, CCL, XOM, KO,
JNJ, PG, MSFT, BA** are the fifteen-series calibration set named in figures.py:171-176; **FDX, MDT,
MXL, FN, DD, OMC** are the top of item 13's 64-panel set; plus 20 random.

Compared: every trace field, every annotation, every shape, in order — and, separately, `outlier_report`
and `comparison_outlier_report`'s keys, medians, dates, values and ratios against the JS report.

**127 masked valuation panels** and **85 hidden comparison points** in the sweep, so the masked paths
are genuinely exercised rather than trivially matching on empty ones.

The concept list for the comparison sweep includes `revenue_yoy_growth` (fundamentals) and `Revenue`
(growth) precisely so the `is_valuation` gate is tested from the other side.

**The harness caught a real mistake of mine.** I pushed the comparison chart's *outliers-hidden*
annotation before its *exclusion* annotation; figures.py adds them at :1010 and :1024, in the other
order. 60 field mismatches across 5 scenarios, all of them that one swap. My code comment had even
claimed the order matched the reference — reading it was not enough, and positional comparison of
`layout.annotations` is what made it visible.

### 4.2 Mean invariance, numerically, a third time

Over 40 tickers × {2y, 5y, 15y}, comparing masked against unmasked: every red shape (mean hlines and
reference lines) serialised **identical**, every `Ø` label **identical**, panel lists identical.
**132 masked panels** in that sample, so the check is not vacuous.

The canonical case, with the mean unchanged while four points vanish:

| ticker / window | the note masking added | the mean labels, unchanged |
|---|---|---|
| **CRM / 5y** | `4 outliers hidden (>5x median) · Ø unchanged` | `Ø (harm.) 60.2`, `Ø 3.9`, `Ø (harm.) 23.1`, `Ø 26.6`, `Ø 45.2` |
| **CRM / 15y** | `5 outliers hidden` | `Ø (harm.) 82.2`, `Ø 6.6`, `Ø (harm.) 32.3`, `Ø 36.0`, `Ø 82.8` |
| **DAL / 5y** | `2 outliers hidden` | `Ø (harm.) 10.1`, `Ø 2.3`, `Ø (harm.) 17.9`, `Ø 39.1`, `Ø 17.8` |
| **INTC / 2y** | `1 outlier hidden` | `Ø (harm.) 812.4`, `Ø 2.0`, `Ø (harm.) 231.3`, … |

Both mean kinds are covered — `Ø (harm.)` is the harmonic path, bare `Ø` the arithmetic one, and the
percent path (`dividend_yield`) is in the same figures. CRM's `pe_ratio` harmonic mean stays at
**60.2** while its 337.8 / 574.9 / 791.4 / 508.3 come off the chart, which is the whole point: were
the mean wired to `drawn`, it would fall.

The structural guarantee behind it is one line in
[valuation.ts](frontend/src/charts/valuation.ts#L219): `mean: meanOver(series.y, …)`, never
`drawn.y`. Item 4 wrote it, item 13 was the first to use it, and item 14 is the first case where
`drawn.y` is a *genuinely different and shorter array* — so it is now load-bearing rather than tidy.

### 4.3 The snapshot marker survives masking

Across all **609 tickers** at 5y, the serialised set of snapshot traces is **identical** with masking
on and off — asserted per ticker, not sampled. **1,754 markers** sit on figures where masking
actually fired, and none of them moved, changed value, or disappeared.

Confirmed live too, on CRM: with masking on, the filed trace drops from 19 points to 15, the note
appears, and the marker stays at exactly `22.302072790726662` on `2026-08-21`.

### 4.4 The fully-masked panel — confirmed unreachable, not assumed

Three ways:

1. **Exhaustively, on the real data.** All 609 tickers × 13 valuation concepts × 4 windows =
   **16,922 non-empty series**. Fully masked: **0**. The **worst masked share of any single series
   was 46.2%** — under half, with room to spare.
2. **Synthetically, at the adversarial limit.** The most hostile series the rule admits is one value
   at the median with everything else arbitrarily far above it. At n = 8, 9, 20 and 101, survivors
   were always ≥ ⌈n/2⌉.
3. **From the rule.** At least half of any series lies at or below its median, so at least ⌈n/2⌉
   points have a ratio ≤ 1, and `k = 5 > 1` cannot reach them. This is a property of the rule, not a
   guard inside it — which is why neither `outlierMask` nor `drawPanel` checks for it, per finding 1.

Four boundary cases were checked while there: a point at **exactly** 5× is kept, one at 5.0000001×
is masked, a 7-point series is untouched (below `OUTLIER_MIN_POINTS`), and a series with a
non-positive median is untouched.

### 4.5 The toggle's conditional presence

At the default 5-year window, over all 609 tickers: **268 offer the toggle, 341 do not.** Two
invariants asserted per ticker — the report never names a concept that is not a drawn panel, and the
report is *identical* whether or not masking is on (so the control cannot make itself disappear by
being used).

Live, with the default `pe_ratio` pick:

- **CRM** — toggle present, caption `Extreme values present in: P/E (TTM) (4 points).`
- **AAPL** — **no toggle at all**, no caption, no expander. Nothing inert on screen.

### 4.6 The expander shows full-precision values

**850 hidden points** across all 609 tickers, each checked against the windowed source series by
`Object.is` on the double *and* by identical `csvNumber` rendering — not "close to", the same number.

Live, CRM's four:

| Period | Value | x median |
|---|---|---|
| 31.07.2022 | `337.8197638668231` | 5.1 |
| 31.10.2022 | `574.909951189439` | 8.7 |
| 31.01.2023 | `791.4332151412964` | 12.0 |
| 30.04.2023 | `508.3285422614508` | 7.7 |

heading `P/E (TTM) — median 65.74`. `337.8197638668231` at 5.1× is the point figures.py:174 names as
`CRM's 337.8 (5.14x)` — the calibration's own example, reproduced to the digit.

### 4.7 Comparison masking is per line, never pooled

Constructed the report's own case, **CRM / KO / MSFT on `pe_ratio`**:

- each ticker's masked line is **byte-identical** whether it is charted alone with one other ticker
  or with both — so no line's mask depends on its company;
- **per-line hidden counts: CRM 5, KO 1, MSFT 0.** A pooled median over the same three series would
  hide **14** — so the check is emphatically not vacuous;
- a non-valuation concept (`revenue_yoy_growth`, `Revenue`) produces a **byte-identical figure** with
  masking on and off, and an empty report, per the `is_valuation` gate.

Live, on CRM + AAOI + a third: trace lengths go `[60, 59, 59] → [55, 59, 58]` — one line loses five,
one loses one, one loses nothing, on a single shared axis. The note reads
`Outliers hidden (>5x each line's own median): CRM (5), AAOI (1)`, and the expander shows
`CRM — own median 111.31` next to `AAOI — own median 25.93`: two medians, two scales, one chart.

### 4.8 Nothing else regressed

Rather than trust remembered hashes, I built a copy of `src/` with item 14 reverted and ran four
sweeps against both trees:

| baseline | sweep | before | after |
|---|---|---|---|
| item 8 — three charts, default path | 3,936 figures, 465,488 points | `fe09bcf21e00…` | **same** |
| item 13 — valuation with the marker, unmasked | 328 figures | `f732b8901ea7…` | **same** |
| item 12 — comparison **figures** | 130 figures | `7e17bb1c333e…` | **same** |
| item 11 — CSV / copy text | 328 blocks, 904,962 chars | `55fd62aff02f…` | **same** |

The item-8 and item-11 hashes are also byte-for-byte the numbers the last cycle recorded, so the
continuity runs across two cycles.

One line legitimately differs: the item-12 hash over the **whole `ComparisonResult`** moved
(`d24889e4…` → `b7cc392f…`), because the result object gained its `outliers` field. The *figure* did
not, which is the thing that matters and is why it is hashed separately.

Browser harnesses: `check-chart-width` **30/30** · `check-tab-state` **13/13** ·
`check-table-format` **6,107/6,107**.

`npx tsc -b`, `npx eslint .`, `npx vite build` — all clean. Nine files changed, all inside
`frontend/`. No scratch files left behind.

---

## 5. Finding 1, confirmed

**The fully-masked panel cannot occur**, and §4.4 is the test rather than the argument: 16,922 real
series with zero occurrences and a worst case of 46.2%, four synthetic adversarial constructions at
the theoretical limit, and the ⌈n/2⌉ derivation. **No guard was built**, in `outlierMask` or in
`drawPanel`, per the finding's instruction. The bare-axis-id rule from the placeholder-fix cycle is
untouched and remains what protects genuinely empty panels, which is where it came from.

## 6. Finding 2, decided

**The port masks the filed series independently of the snapshot marker, matching the reference.**

The numbers, re-measured this cycle at the default 5-year window across all 609 tickers:

- **64 panels** where the marker itself exceeds 5× its panel's own median — item 13's figure,
  reproduced exactly;
- of those, **60 are on figures where the toggle is offered**, so the reader can mask the filed
  outliers and will still see the axis stretched by a green point that did not move;
- and **4 are on figures where the toggle is not offered at all** — the filed series is clean, only
  the marker is extreme, so there is no control to reach for. This is the sharper half of the
  finding, and it is new this cycle;
- the extremes are unchanged: `FDX`/`pe_ratio` at **129,740×**, `MDT`/`pe_ratio` at **103,301×**,
  then `MXL`/`pfcf_ratio` at 87.5×, `FN`/`pfcf_ratio` at 86.8×.

**Why match rather than fix.** The marker is not a filed period and the rule is about a *series*
against *its own* median — a single point has no median, and judging it against the filed series'
median would be a different rule with a different meaning, invented here and present in neither the
reference nor the calibration. More decisively: the reference's caption tells the reader in so many
words that the green circle *is* the current multiple, so hiding it because it is extreme would hide
the answer to the question the chart is being asked. FDX at 129,740× the median is not noise to be
suppressed; it is a fact about FDX's trailing earnings.

The green-circle caption added in §3.1 is what makes that legible on screen, and it now sits directly
below the masking caption, which is where app.py puts it.

## 7. For item 15 and later

1. **Masking needs nothing from `as_of`.** It runs on whatever `windowCutoff` produced, so item 15's
   upper bound enters upstream and composes for free. The one thing to check when it lands is that
   `outlier_report`'s series and the *drawn* series stay the same series — figures.py:832 records
   what goes wrong otherwise: *"the control could name points the chart does not draw, or miss ones
   it does."* In this port they cannot diverge, because the builder derives both and returns them
   together.
2. **Three `layout` fields item 12 did not carry across**, found while implementing the comparison
   note and left alone as out of scope: `build_ticker_comparison` sets `legend.font.size = 10`
   (the port's `createGrid` always writes 9), `margin = dict(b=110 if excluded else 80)`, and
   `layout.meta` carrying `{concept, tickers, excluded, outliers_hidden}`. Item 12's harness compared
   traces, annotations and shapes, so none of the three was covered. `meta` exists so a *serialised*
   figure carries what was dropped; this port returns it in `ComparisonResult` instead, which serves
   the app but not a downstream consumer of the JSON. Worth one small cycle, and worth extending the
   comparison harness to `layout` while doing it.
3. **Item 17 (the empty-panel notice)** shares this cycle's block: app.py renders it between the
   chart and the outlier caption (app.py:963). The slot is free and the ordering is already right.
4. **The `PanelSpec` invariant now has three users** — `mean` reads `series.y`, and `traces` carries
   the drawn arrays, the snapshot marker and the mask. Anything that changes what is drawn goes in
   `traces`; anything that would change the mean does not belong in this file at all.
