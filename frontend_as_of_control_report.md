# The as-of control — item 15

Three cycles of plumbing paid off: `anchor` was already threaded through both builders, item 13
already used it for marker suppression, item 14 already composed with it. What was missing was one
`if` and one control.

Two things the brief's framing does not quite capture, both in §4.2: **the as-of date moves the
window's lower bound too**, so "the upper bound removes data" is only half of what happens; and the
one place the previous cycles' A/B sweeps were blind, which I closed by proving the sweep is
sensitive to exactly this change.

---

## 1. Step 1 — the reference, read exactly

### 1.1 `_window_frame`, both bounds

figures.py:146-159, verbatim:

```python
anchor = pd.Timestamp.today() if as_of is None else pd.Timestamp(as_of)
windowed = frame[frame["end"] >= anchor - pd.DateOffset(years=years)]
if as_of is not None:
    windowed = windowed[windowed["end"] <= anchor]
return windowed
```

The asymmetry is the whole design: **the lower bound is unconditional**, and it anchors on `as_of`
when there is one; **the upper bound runs only when `as_of is not None`**. There is no "cap at
today" default. `<=`, so a row dated exactly on the as-of date is kept.

Its own docstring says why: *"the caller asked for 'the last `years` years as of that date', and
leaving the upper bound open would instead answer 'everything since that date' and show data the
chosen date could not have known."*

**Five callers, and only two get an `as_of`:**

| call site | `as_of` |
|---|---|
| `build_valuation` (figures.py:737) | threaded from the caller |
| `_comparison_selection` (figures.py:851) — used by `build_ticker_comparison` **and** `comparison_outlier_report` | threaded from the caller |
| `build_fundamentals` (figures.py:589) | **hard-coded `None`** |
| `build_growth` (figures.py:646) | **hard-coded `None`** |
| `available_raw_concepts` (figures.py:1111) | **hard-coded `None`** |

So the inventory's "valuation and comparison only" is exact, and it is enforced at the *call site*
rather than by a parameter the other builders quietly ignore. Item 14's finding that both
`as_of`-aware charts route their outlier report through the same `_window_frame` call held: masking
needed nothing from this cycle, confirmed numerically in §4.4.

### 1.2 The control (app.py:867-870)

```python
as_of_enabled = st.checkbox("Use an as-of date for valuation", value=False)
as_of = None
if as_of_enabled:
    as_of = pd.Timestamp(st.date_input("As of", value=pd.Timestamp.today().date()))
    st.caption("The valuation window runs backwards from this date and stops there.")
```

- **Label:** `"Use an as-of date for valuation"` — and note it says *for valuation* while app.py:887
  hands the same value to the comparison tab as well. A reference inconsistency, carried verbatim
  rather than corrected; see §2.4.
- **Checkbox default:** `value=False`.
- **Date default when first ticked:** `pd.Timestamp.today().date()` — **today**, not the latest
  filed period, not the snapshot date.
- **min/max on the picker:** **none**. `st.date_input` is called with a `value` and nothing else.
- **Unchecking:** `as_of = None`, and the date is **forgotten**. Neither widget has a `key`, so
  Streamlit's state for the date input is keyed by an auto-generated id and is discarded on a run
  where the widget is not rendered — ticking the box again offers today, not the previous pick.
- **Placement:** the sidebar, inside the `view == VIEW_ANALYSIS` branch, below the ticker and its
  profile caption. **One control, two tabs** — `render_analysis(ticker, as_of, …)` at app.py:887.

### 1.3 An as-of outside the data

No special path — it falls through to machinery that already exists, and the two charts differ:

- **The valuation grid** still returns a figure (`build_valuation` returns `None` only when nothing
  is selected, figures.py:742). Every panel's windowed series is empty, so `plot_metric` takes its
  `valid_values.empty` branch (figures.py:358) and each panel gets the **"No Data"** annotation with
  its axis furniture stripped.
- **The comparison chart** returns `(None, excluded)`: every ticker fails
  `series.dropna(…).empty` in `_comparison_selection` and lands in `excluded` as `"No Data"`, then
  `if not plotted: return None, excluded` (figures.py:960). app.py words each one as *"no values in
  this window"*.

Both confirmed live and in §4.6.

### 1.4 The comparison chart's own wiring

`build_ticker_comparison(… as_of …)` → `_comparison_selection(tickers, concept, data, years, as_of,
value_column)` → `_window_frame(data, years, as_of)` at figures.py:851. **The same function, both
bounds, one call** — which is what `_comparison_selection`'s docstring exists to guarantee: it is
extracted so the builder and the outlier report *"cannot answer 'which tickers, which window, which
column' differently."*

Item 12's report named `ComparisonOptions.anchor` as the plumbing point and it was correct; this
cycle only had to reach the upper bound through it.

---

## 2. Step 2 — design

### 2.1 Where the control lives — **the sidebar**, not a tab

Matching app.py's placement, and the placement is the design rather than an accident of Streamlit
layout: one date feeds two tabs, so a per-tab control would have had to be two controls that must
agree. The state lives in `Workspace` (`App.tsx`), which outlives every tab switch, and is passed
down as a prop to `ChartView` and `ComparisonView`.

The `anchor` field on both option types needed no change at all — only a consumer. That is what
three cycles of leaving the seam in place bought.

**Deliberately not in the URL hash.** The hash carries view, ticker and tab; `navigation.ts`'s
docstring already argues that per-chart selections stay out of it, and an as-of date has the same
character — a reading mode, not a place. Adding it later is a change to `parseHash`/`formatHash` and
one line in `Workspace`.

### 2.2 The upper bound — `seriesFor`'s `until`, not `windowCutoff`

`windowCutoff` returns a single `Date`; the upper bound is a second, *optional* condition on the same
row filter, so it belongs where the filter is:

```ts
export function seriesFor(frame: Frame, concept: string, cutoff: Date, until?: Date): Series {
  const untilMs = until === undefined ? Infinity : until.getTime();
  …
  if (end >= cutoffMs && end <= untilMs) rows.push(i);
```

**An added optional parameter, not a signature change**, and that is deliberate: `fundamentals.ts`
and `growth.ts` call `seriesFor` too, and the reference gives them `as_of=None`. A required
parameter — or folding both bounds into a `Window` object — would have forced edits to two chart
builders this task is explicitly not allowed to touch, to make them pass "no upper bound". Absent is
absent, on both sides.

`undefined` is the port's spelling of `is not None`. `windowCutoff` keeps its unconditional lower
bound and its docstring now says so explicitly, so the asymmetry is recorded at both halves.

### 2.3 Date-input constraints — **none**

The reference has no `min`/`max`, and the simpler option is also the better-behaved one: a date
outside the data is not an error, it is a question with the answer "nothing was filed by then", and
the panels' own **"No Data"** path already says that. A picker that refused the date would have to
explain itself; the chart already does. §4.6 confirms the empty path is clean rather than broken.

### 2.4 One reference inconsistency, carried

The checkbox says *"for valuation"* and the date reaches the comparison chart too. Carried verbatim,
because the label is one of the things a reader moving between the two apps compares, and a
silently-improved label is a divergence that looks like a bug in the reference. Flagged here instead
— if it is ever fixed, it should be fixed in `app.py` first.

---

## 3. Step 3 — what was implemented

Eight files, all inside `frontend/`:

| file | change |
|---|---|
| [`src/charts/select.ts`](frontend/src/charts/select.ts) | `seriesFor`'s optional `until`; `windowCutoff`'s docstring rewritten around the asymmetry. |
| [`src/charts/valuation.ts`](frontend/src/charts/valuation.ts) | `seriesFor(frame, id, cutoff, anchor)`. |
| [`src/charts/comparison.ts`](frontend/src/charts/comparison.ts) | `seriesFor(frame, concept, cutoff, anchor)`. |
| [`src/shell/Sidebar.tsx`](frontend/src/shell/Sidebar.tsx) | the checkbox, the date input and the caption, with `todayUtc`/`isoDay`/`parseDay`. |
| [`src/shell/shell.css`](frontend/src/shell/shell.css) | `.as-of__toggle` / `.as-of__date`, reusing `.ticker`'s look. |
| [`src/App.tsx`](frontend/src/App.tsx) | `asOf` state in `Workspace`, passed to the sidebar and both views. |
| [`src/ChartView.tsx`](frontend/src/ChartView.tsx) | the `asOf` prop, forwarded **only** when `chart === "valuation"`. |
| [`src/ComparisonView.tsx`](frontend/src/ComparisonView.tsx) | the `asOf` prop → `ComparisonOptions.anchor`. |

The two builders' `anchor` docstrings were updated from "item 15 still owes the upper bound" to what
they now do.

---

## 4. Step 4 — verification

### 4.1 Against the reference, element-wise

**864 scenarios · 210,028 checks · 0 failures.**

36 tickers × 8 as-of settings × 2 windows for the valuation grid (with masking on for two of the
settings), plus 6 ticker groups × 3 concepts × 8 as-of settings for the comparison chart. The dates
were chosen to hit every branch: `None`; item 13's three continuity dates around the snapshot
(2026-08-20 / -21 / -22); a mid-history date (2023-06-30); a deep one (2019-03-15); one before all
data (1990-01-01); and one in the future (2030-01-01).

**288 of the valuation scenarios had rows past their as-of date** for the bound to remove, so this
is not a sweep that passes by never exercising the new condition.

### 4.2 The upper bound demonstrated — **and what else moves with it**

The brief asks for the bound to be shown removing data. It does, but a naive before/after count is
misleading, and it is worth being precise because it is the easiest thing to misread:

> **Setting an as-of date moves *both* bounds.** The anchor feeds the lower bound too
> (figures.py:155), so the window becomes "the last `years` years **as of that date**", not "the same
> window, truncated". Turning the control on for AAPL at 15 years does not shorten the series from
> 72 points to 59 — it slides the whole window from 2011→2026 to 2008→2023.

So the bound was isolated instead, by holding the lower cutoff fixed and toggling only `until`.
Across **all 609 tickers × 13 valuation concepts, 5,001 non-empty series**:

- **59,678 points removed by the upper bound alone**;
- only **5 series** were left untouched (nothing filed after the date);
- every bounded series is exactly the **prefix** of the unbounded one — nothing reordered, nothing
  reshaped;
- and no bounded series retains a single date after the as-of.

One case in full, AAPL `pe_ratio`, lower cutoff pinned at 2008-06-30:

```
bound off: 72 points, 2008-09-27 .. 2026-06-27
bound on:  59 points, 2008-09-27 .. 2023-04-01
dropped:   2023-07-01, 2023-09-30, 2023-12-30, 2024-03-30, 2024-06-29, 2024-09-28,
           2024-12-28, 2025-03-29, 2025-06-28, 2025-09-27, 2025-12-27, 2026-03-28, 2026-06-27
```

And **clearing the as-of restores the original series exactly** — asserted per ticker over all 609,
by serialised comparison, not by count.

### 4.3 The lower bound is unaffected

141 (ticker, window) pairs at `asOf = undefined`, across 1/3/5/15 years: every drawn date is at or
after `windowCutoff(years)`, **and the latest in-window filed period is still present** — the second
half being the one that would fail if a "cap at today" had crept in as a default. The item-8 A/B in
§4.8 is the byte-level version of the same statement.

### 4.4 Items 13 and 14, with the bound now active

**Item 13's suppression table, re-run** — 36 tickers, markers counted:

| `as_of` | markers |
|---|---:|
| 2026-08-20 — one day **before** the snapshot | **0** |
| 2026-08-21 — **on** the snapshot's date | 215 |
| 2026-08-22 — one day after | 215 |
| `None` | 215 |

Identical in shape to §5.3 of the snapshot report. The upper bound does not disturb it, which is not
obvious a priori: a marker at 2026-08-21 sits *outside* the filed window for most as-of dates, and
the two rules stay independent because the marker is not drawn from the windowed frame at all.

**Item 14's mean invariance, under an active bound** — 36 tickers × 3 as-of settings, masking on
against off: every red shape and every `Ø` label **identical**, over **174 masked panels**. Plus a
new assertion this cycle needed: the outlier report never names a point beyond the as-of date, which
would mean the toggle was describing data the chart cannot draw.

Item 14 §7.1's claim that masking composes for free **held**, and the reason is structural: masking
consumes `series.y`, which `seriesFor` produced with both bounds already applied.

### 4.5 Means over the doubly-bounded series

For each of 36 tickers at `as_of = 2023-06-30`, every `Ø` label on the figure was compared against a
mean recomputed independently from the frame with **both** bounds applied by hand — **242 labels, all
matching**. And they genuinely differ from the unbounded ones, so the check is not vacuous:

| ticker | window open | as of 2023-06-30 |
|---|---|---|
| AAPL | `Ø (harm.) 16.4`, `Ø 20.4`, `Ø (harm.) 14.4` | `Ø (harm.) 14.6`, `Ø 11.7`, `Ø (harm.) 12.6` |
| CRM | `Ø (harm.) 82.2`, `Ø 6.6`, `Ø (harm.) 32.3` | `Ø (harm.) 154.1`, `Ø 7.8`, `Ø (harm.) 39.3` |
| INTC | `Ø (harm.) 10.7`, `Ø 2.1`, `Ø (harm.) 11.7` | `Ø (harm.) 9.6`, `Ø 2.1`, `Ø (harm.) 10.7` |
| DAL | `Ø (harm.) 7.4`, `Ø 2.4`, `Ø (harm.) 12.7` | `Ø (harm.) 7.7`, `Ø 2.5`, `Ø (harm.) 12.0` |

CRM going *up* from 82.2 to 154.1 is the check earning its keep: as of mid-2023 the window still
contained CRM's pathological 2022-23 multiples and had not yet reached the years that pulled the
harmonic mean back down.

### 4.6 The empty-result case

36 tickers at `as_of = 1990-01-01`: **36 figures, 0 null**, **295 "No Data" panels**, zero traces,
zero reported outliers. Exactly §1.3's prediction, and no new code — the existing placeholder path
absorbed it.

The comparison chart's variant is the other shape: `figure === null`, every requested ticker in
`excluded` with reason `"No Data"`, which `ComparisonView` already words as *"no values in this
window"*.

### 4.7 The comparison chart's upper bound

Covered element-wise in §4.1 (144 comparison scenarios across eight as-of settings) and again
directly: 11 ticker groups that had points past 2023-06-30, each checked **per line** — no plotted
ticker's line runs past the date.

### 4.8 Nothing else regressed

Reverted-tree A/B, six sweeps:

| baseline | before | after |
|---|---|---|
| item 8 — three charts, pinned anchor | `fe09bcf21e00…` | **same** |
| item 8 — three charts, **no anchor** | `fe09bcf21e00…` | **same** |
| item 13 — the marker | `f732b8901ea7…` | **same** |
| item 14 — masking + report | `e1aea0c8e786…` | **same** |
| item 12 — comparison figures | `7e17bb1c333e…` | **same** |
| item 11 — CSV / copy text | `55fd62aff02f…` | **same** |

The item-8, -11, -12 and -13 hashes are byte-for-byte the numbers the previous two cycles recorded.

**And the A/B was proved sensitive**, which matters here more than usual. Running the same builders
with an anchor that *bites* — `as_of = 2023-06-30` — the two trees differ:

```
after:  149d2d546fa254c4c0b84852b48c21e018b715dd82792b31ce4a707108dc2793
before: 2f9c4d0f70ac12dd35ccb8899d13bdf6cb00baa764af3700e562763c93977025
```

Without that, the "pinned anchor" sweep matching would have been weak evidence: the pin is
2026-08-28 and no filed period in the export is later, so the upper bound has nothing to remove
there. The sweep agrees where it should and disagrees where it should.

Browser harnesses: `check-chart-width` **30/30** · `check-tab-state` **13/13** ·
`check-table-format` **6,107/6,107**.

`npx tsc -b`, `npx eslint .`, `npx vite build` — clean. Eight files, all inside `frontend/`. No
scratch files left behind.

### 4.9 Live

| state | filed points | last period | markers | mean |
|---|---:|---|---:|---|
| unchecked | 20 | 2026-06-27 | 1 | `Ø (harm.) 29.0` |
| checked, default (today, 2026-08-28) | 20 | 2026-06-27 | 1 | `Ø (harm.) 29.0` |
| as of **2023-06-30** | 20 | **2023-04-01** | **0** | **`Ø (harm.) 21.0`** |
| as of **2026-08-20** | 20 | 2026-06-27 | **0** | `Ø (harm.) 29.0` |
| as of **1990-01-01** | 0 | — | 0 | — |
| **Fundamentals**, as of 2023-06-30 | 60 | **2026-06-27** | 0 | — |
| **Comparison**, as of 2023-06-30 | 58 / 59 / 46 | **2023-04-01** | — | — |
| Comparison, unchecked again | 60 / 59 / 58 | 2026-06-27 | — | — |

Four things worth reading off that table:

- **checking the box on today is a no-op**, correctly — there is nothing filed after today to remove;
- **2026-08-20 suppresses the marker but changes nothing else**, which is item 13's rule and the
  upper bound being independent;
- **the fundamentals row is the scope check** — the as-of is set, and that chart's window still runs
  to 2026-06-27;
- **re-checking the box after unchecking offers today again** (2026-08-28), not the previously
  chosen 2023-06-30 — matching Streamlit's unkeyed-widget behaviour from §1.2.

---

## 5. For items 16–19

1. **`seriesFor`'s `until` is the only upper bound in the port, and it is opt-in.** Anything new that
   windows a frame should take the same shape: an optional argument, absent by default, never a
   default cap at today. Item 16 (Raw Facts) reads `facts_full` and its reference call is
   `_window_frame(facts, years=years, as_of=None)` at figures.py:1111 — **hard-coded None**, so it
   takes the years slider and no as-of.
2. **The as-of date is not in the URL.** If a later item wants shareable "as of" links, the change is
   `parseHash`/`formatHash` plus the one `useState` in `Workspace`; nothing below the shell would
   move.
3. **`available_raw_concepts` is the third `as_of=None` call site** and the one item 16 will meet.
   Worth checking that it is still None when that item lands rather than assuming from here.
4. **The three `layout` fields item 12 did not carry across** are still open, and unrelated to this
   cycle: `legend.font.size = 10` on the comparison chart, `margin.b`, and `layout.meta`. Recorded in
   item 14's report §7.2; still the smallest outstanding fidelity gap I know of.
5. **The checkbox's label says "for valuation" and the control reaches two tabs.** Reference
   inconsistency, carried deliberately (§2.4). If anyone fixes it, fix `app.py` first so the two do
   not drift.
