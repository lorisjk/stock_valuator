# The metric pickers

Rebuild-list item 7. Small in code and almost entirely product decisions, as the brief predicted —
but the reference turned out to contain a second defect behind the one the brief named, and it is
the one users actually hit.

---

## 1. What the Streamlit version does

All three pickers are the same six lines with different strings:

| | Fundamentals (app.py:903) | Growth (app.py:915) | Valuation (app.py:927) |
|---|---|---|---|
| label | `"Metrics"` | `"Concepts"` | `"Multiples"` |
| options | `metric_options("fundamentals", ticker)` | `("growth", ticker)` | `("valuation", ticker)` |
| shown as | `format_func=lambda i: labels[i]` — **labels, not ids** | same | same |
| default literal | `("revenue_yoy_growth")` | `("Revenueyoy_growth")` | `("pe_ratio")` |
| key | `fund_metrics` | `growth_metrics` | `val_metrics` |
| empty → | `st.info("Nothing selected, or no data for the selected metrics.")` | `"Nothing selected, or no growth data for this ticker."` | `"Nothing selected, or no valuation data for this ticker."` |

`metric_options` is a two-line wrapper over `config.get_plottable_metrics(chart, ticker=ticker)`,
which is already narrowed by `is_hidden`. The empty branch is `render(fig, msg)` at app.py:541:
`if fig is None: st.info(empty_message)`.

### 1.1 The substring defect — confirmed, and it is **three**, not two

The brief names two. It is all three: `("x")` is a string in every one of them, so `in` is a
substring test in every one of them. Inventory §2.7 has this right (its line numbers 900/911/928
are now 904/916/928).

Measured over **all 609 tickers**, not just AAPL:

| tab | literal | what the substring test selects | what a real tuple would select |
|---|---|---|---|
| Fundamentals | `"revenue_yoy_growth"` | `['revenue_yoy_growth']` | `['revenue_yoy_growth']` |
| Growth | `"Revenueyoy_growth"` | `['Revenue']` | **`[]` — on all 24 profiles** |
| Valuation | `"pe_ratio"` | `['pe_ratio']` | `['pe_ratio']` |

So the substring test happens to land on the intended metric everywhere: **0 of 609 tickers select
more than one, and 0 select none they should have selected**, on any of the three charts. Two work
because an id is a substring of itself; the growth one works because `"Revenueyoy_growth"` — a typo
with the separator missing — happens to contain `Revenue`.

**The direction of the fix matters.** Writing the growth literal as a proper tuple *without* also
correcting the string would silently empty the growth tab for every ticker. That is the trap in
"port the expression faithfully": the bug and the typo cancel, and removing only one of them breaks
it.

**The intended defaults** are therefore `revenue_yoy_growth`, `Revenue`, `pe_ratio` — one metric
per chart — and that is what `PREFERRED_DEFAULT` carries.

### 1.2 The defect the brief did not name: `pe_ratio` is hidden for `reit`

This is the one that reaches users, and the substring test has nothing to do with it.

`pe_ratio` is not in `profile_visibility["reit"]`. So for all **29 REIT tickers** the valuation
default evaluates to `[]` regardless of how it is written, `build_valuation` returns `None`, and
the tab opens on *"Nothing selected, or no valuation data for this ticker."* — a message about a
selection the user never made, on a ticker that has five perfectly good valuation panels.

And it cannot be fixed by choosing a better constant. Measured across the 24 profiles:

| chart | metrics offered by **every** profile | of |
|---|---|---:|
| fundamentals | `revenue_yoy_growth`, `roe` | 29 |
| growth | `Revenue`, `NetIncomeLoss`, `SharesOutstanding`, `StockholdersEquity` | 10 |
| **valuation** | **none** | 13 |

There is no valuation id every profile offers, so **every possible hardcoded valuation default has
a hole somewhere.** A fallback is required, not merely prudent.

### 1.3 And the same hole again on a ticker switch

Read from Streamlit 1.61's own source rather than guessed. When a `multiselect`'s options change
under a persisted key, `validate_and_sync_multiselect_value_with_options`
(`elements/lib/options_selector_utils.py:486`) filters the stored value down to the still-valid
options. Its docstring states the rule:

> *"Unlike selectbox which resets to a default when the value is invalid, multiselect filters out
> invalid values and keeps the valid ones."*

Two consequences:

1. **Pure intersect, never a fallback.** A user who narrowed AAPL to P/E and switches to a REIT gets
   an empty picker and the same misleading message as in §1.2.
2. **The loss is sticky.** The function's documented side-effect is that it *writes the filtered
   list back into session state*. Switching back to AAPL does not restore `pe_ratio` — it is gone.

---

## 2. Design decisions

### 2.1 One selection per chart, held in `ChartView`

Per chart. The three catalogues share no ids at all — fundamentals and valuation ids are metric
names, growth ids are XBRL concept names (inventory §3.2) — so a shared selection would arrive at
the next tab as a list of names that chart has never heard of, and narrow to nothing. The sizes
rule it out independently: 29 fundamentals metrics against 13 valuation and 10 growth, and 19 of
24 profiles share one 7-metric growth catalogue while valuation ranges from 5 to 9.

It sits in `ChartView`, keyed by `ChartId`, because that is the component that owns the builder
call. It is deliberately **not** in `DataProvider`: app.py:93 records why the Streamlit app caches
frames and never figures — *a cached figure would outlive the widget state that produced it* — and
the provider having nowhere to put derived state is what enforces that here.

### 2.2 Ticker change: **intersect, then fall back — and store the pick raw**

The decision the user notices, so it gets the most reasoning.

> Keep the parts of the selection the new profile also offers. If it offers *none* of them, show
> that profile's default instead. If the selection was deliberately empty, leave it empty.

- **Intersect rather than reset**, because comparing one metric across several tickers is the
  reason people switch tickers at all. Resetting to the default on every switch throws that away
  every time.
- **Fall back when nothing survives**, because pure intersect produces §1.3's blank chart. The
  fallback fires on **1,423 of 16,335** measured switch cases — 8.7%, not a corner.
- **An empty selection is honoured, not corrected.** `previous = []` means the user cleared the
  picker; filling it back in would make the control impossible to clear. Only a *non-empty*
  selection that survives nothing is replaced. 3,267 cases exercise this branch.

The implementation detail that makes the third departure from Streamlit possible: **state holds
what the user last ticked, and the effective selection is derived at render** by
`migrateSelection(chart, raw, offerable)`. Nothing is migrated in place. So switching away from a
ticker and back **restores the original pick**, where Streamlit's write-back has destroyed it. It
also means reacting to a ticker change needs no `useEffect` and no setState-during-render — the
switch is a pure recomputation, and there is no dependency list that could go stale against it.

`migrateSelection` returns its result by filtering `offerable`, so the output is always in
catalogue order and always a subset of what the profile offers, whatever went in.

### 2.3 The empty selection, and the three states it is not

`ChartView` distinguishes what Streamlit's single `st.info` per tab cannot. The reference messages
say *"Nothing selected, **or** no data…"* — the reference is itself acknowledging that it does not
know which happened. Four distinct situations exist:

| situation | what is shown |
|---|---|
| the profile hides every metric on this chart | "No {chart} metrics are shown for {ticker}'s profile." |
| the user cleared the picker | "No metrics selected — pick at least one above." |
| the ticker has no rows in the frame at all | "No {chart} data for {ticker}." |
| a **drawn** panel has no data in the window | the "No Data" placeholder — **not** this branch |

The fourth is the one the brief flags as item 17's: a figure *is* built, panels *are* drawn, and
some of them carry the red placeholder. It never reaches the no-figure branch, which is why item
17's notice belongs next to the chart rather than instead of it.

### 2.4 Label first, id second

Streamlit shows labels (`format_func`), and the labels are the readable half —
"Shares Outstanding (Stock Dilution/Repurchase)" against `SharesOutstanding`, "P/E (TTM)" against
`pe_ratio`. But item 4 established that **panel titles are ids** while the y-axes carry labels. A
picker showing only labels would leave nothing connecting a ticked box to the panel it produces,
and this is the first place a user reads a metric name outside a chart.

So both: the label as the primary text, the id after it in muted monospace. The picker becomes the
one place the two names are visibly the same thing.

### 2.5 Catalogue order, and the selection has no order

The picker lists options in `charts[chart].metric_ids` order — the order the panels render in.
The selection's own order is not preserved anywhere and is not offered as if it were:
`_select_concepts` orders by catalogue and `selectMetricIds` does the same, so a reversed request
comes back in catalogue order (verified again below, on all 99 pairs). Presenting the options in
any other order would imply a control the builders do not have.

The three bulk buttons — **All / None / Default** — are there because a 29-checkbox fundamentals
catalogue cannot be cleared by hand, and because once the default has been changed there needs to
be a way back to it. `All` and `None` also make the two ends of the range reachable in one click,
which is what the verification exercises as `full` and `empty`.

---

## 3. What was implemented

| file | what |
|---|---|
| `src/charts/defaults.ts` | **new** — `PREFERRED_DEFAULT`, `defaultSelection`, `migrateSelection`. Pure functions over id lists, so the ticker-switch rule is verifiable from Node rather than by clicking |
| `src/MetricPicker.tsx` | **new** — the control: options, label+id, All/None/Default |
| `src/ChartView.tsx` | raw selection state per chart; `offerable` from `offerableMetricIds`; the three empty states |

`App.tsx` is untouched. No chart module is touched — `panel.ts`, `grid.ts`, `select.ts`, `mean.ts`
and the three builders are exactly as item 6 left them.

**One path to "what this ticker offers."** The picker's options come from
`offerableMetricIds(registry, chart, ticker)`, which *is* `selectMetricIds(registry, chart, ticker,
null)` — the same function every builder calls for its own narrowing, not a second implementation
of `is_hidden`. It is evaluated in the component as well as inside the builder because the options
are an **input** to the build: the selection has to be resolved against this ticker's catalogue
before there is a request to build with. That the two agree is asserted, not assumed — see below.

---

## 4. Verification

**33 tickers covering all 24 profiles**, with four REITs (AMT, EQR, O, PLD) because the fallback
default and the empty-intersection switch both fire only there.

Twelve selection shapes per (ticker, chart) — `null` (`concepts=None`), `full`, `default`,
`reversed`, `empty`, `unknown`, `first1/2/4/7`, `with_hidden`, `only_hidden` — each built on both
sides and compared as a whole figure: every annotation on ten fields in order, ten axis properties,
element-wise traces including nulls, every shape.

| | |
|---|---:|
| option lists compared against `get_plottable_metrics` | **99** (33 × 3), identical ids in identical order |
| selection shapes built on both sides | **1,169** |
| figures compared | **872** |
| traces | 3,636 |
| **data points, element-wise** | **153,148** |
| annotations | 5,193 |
| shapes | 2,619 |
| axis objects | 7,450 |
| ticker-switch cases | **16,335** |
| **structural checks passed** | **4,681 / 4,681** |
| **field-level differences** | **0** |

### The Step 4 list

| # | check | result |
|---:|---|---|
| 1 | option lists match `get_plottable_metrics`, same ids, same order | ✓ 99 pairs, 24 profiles. Also: the builder's own `offerable` equals the picker's on all 1,169 shape cases, and **no offered id is `is_hidden` for its ticker** |
| 2 | a hidden metric cannot be selected | ✓ 99 cases. `with_hidden` (default + every hidden id) produces **exactly the `default` panel set**; `only_hidden` produces no panels and no figure. An unknown id behaves the same |
| 3 | narrowing produces the right grid | ✓ 1 → 99 cases, 2 → 99, 4 → 99, 7 → 80, full → 99. Every figure's rows/cols equal `_make_grid(len(panels))`, and every figure matches `build_*` called with the same `concepts` list |
| 4 | empty selection | ✓ all three charts, all 33 tickers: no panels, no figure, both sides |
| 5 | ticker switch | ✓ 16,335 cases — see below |
| 6 | items 4, 5 and 6 unchanged | ✓ see §5 |
| 7 | `tsc -b`, `eslint .`, `vite build` | ✓ clean; nothing outside `frontend/` changed |

### The ticker-switch rule, exercised

Every ordered pair of the 33 tickers × 3 charts × five plausible held selections (the default, the
whole catalogue, the first two, the last one, cleared). Each case is checked against `is_hidden`
directly — the non-circular part — and against the stated rule:

| property | cases |
|---|---:|
| result never leaves the new ticker's catalogue | 16,335 ✓ |
| result contains no id `is_hidden` for the new ticker | 16,335 ✓ |
| result is in catalogue order | 16,335 ✓ |
| migrating twice changes nothing (idempotent) | 16,335 ✓ |
| **intersect** branch — result is exactly the surviving ids | 11,645 ✓ |
| — of which the selection was **partly** dropped | **2,252** |
| — of which it survived whole | 9,393 |
| **fallback** branch — nothing survived, result is the new default | **1,423** ✓ |
| **cleared** branch — an empty selection stays empty | 3,267 ✓ |
| round trip A → B → A restores the original pick | 13,068 ✓ |

All three branches are genuinely exercised; none is dead code. A representative fallback:
`fundamentals | A → ACGL | ['fcf_margin'] → ['revenue_yoy_growth']` — `fcf_margin` is not in the
`insurance_pc` catalogue, so the pick survives nothing and the default takes over.

### The default rule

`defaultSelection` returns the preferred id where the profile offers it and the first offered id
otherwise. Over the set: 29 of 33 tickers get `pe_ratio` for valuation and **the four REITs get
`pb_ratio`**; fundamentals is `revenue_yoy_growth` and growth is `Revenue` for all 33. Every
default is checked to be in the option list and not `is_hidden`.

### Two differences, both pre-existing

28 y-value differences, all `tie_order` on NAVN — same-date rows that pandas' unstable
`sort_values` orders differently from `seriesFor`'s stable comparator, with an identical (x, y)
multiset. Established and bounded in the growth report; the classifier fails the run if a
difference is not one of the two known shapes. **Zero `nonfinite` differences** in this set, and
zero differences of any kind on the growth and valuation charts.

### What was not verified

**Nothing was opened in a browser.** The picker's *rules* are verified exhaustively because they
were deliberately written as pure functions; what is not verified is that clicking a checkbox in
Chrome calls them — that the `onChange` handler is wired, that `disabled` renders as disabled, that
29 checkboxes wrap legibly. Those are DOM facts, and this harness compares figure specs.

---

## 5. Items 4, 5 and 6 are unchanged

Two guarantees, as in the last cycle.

**Against the reference.** All 872 figures across every selection shape match `build_*` called with
the same `concepts` list — including the `null` shape, which is the item 4/5/6 full-catalogue path
re-run in full.

**Byte-identity.** The harness takes the source root as a parameter and was run against a
reconstructed pre-cycle tree (this cycle's `defaults.ts` and `MetricPicker.tsx` removed). The
serialised full-catalogue specs across all 33 tickers:

| chart | bytes | identical to the pre-cycle tree |
|---|---:|---|
| valuation | 398,888 | **yes** |
| fundamentals | 798,821 | **yes** |
| growth | 557,647 | **yes** |

And the change this item *could* have made invisibly: the app now always passes an explicit list
where it used to pass `null`. **`requested = offerable` and `requested = null` produce byte-identical
figures on all 99 (ticker, chart) pairs**, so nothing moved when the picker took over the argument.

---

## 6. What items 8, 12, 13, 14 and 17 should know

1. **`pe_ratio` is hidden for `reit`, and there is no universal valuation metric.** Anything that
   hardcodes a valuation id — a default, an example, a deep link, a comparison-chart starting
   metric — has a hole for 29 tickers. Item 12 picks *one* metric to compare tickers on and is the
   next place this bites: a comparison across a REIT and a bank has no `pe_ratio` for one and no
   `p_ffo` for the other, and `_comparison_selection` already has exclusion wording for exactly
   this shape.

2. **Streamlit's `multiselect` filters stale selections and writes the filtered list back.** Any
   remaining Streamlit-behaviour question of the form "what happens to widget state when the
   options change" has this answer, and it is *sticky* — the original is gone, not hidden. The
   frontend stores the raw pick instead, so `ChartView`'s state is the user's intent and the
   effective list is derived. Item 8's `years` should follow the same shape (store the slider
   value, derive nothing into it) so a window narrowed for one ticker is not silently rewritten by
   another.

3. **The empty-figure branch has three causes and item 17 is a fourth thing entirely.** The
   distinction is now in `ChartView`: no metrics offered / none selected / no rows at all. Item
   17's notice is about panels that *were* drawn and carry the "No Data" placeholder, which never
   reaches that branch. The two must not be merged back into one message — the reference's
   `"Nothing selected, or no data…"` is what merging them looks like.

4. **`PanelSpec` and the builders never see the picker.** The selection arrives as `concepts`, the
   same argument `app.py` passes, and the builders narrow again on their own. That double narrowing
   (inventory §3.1) is what makes a stale client selection *silently correct* rather than an error,
   and it is why items 13 and 14 can add per-panel behaviour without touching the picker at all.

5. **`migrateSelection` and `defaultSelection` are pure and exported.** Item 8's years and item
   15's as-of will want the same treatment — a rule about what a control's value becomes when its
   context changes, written as a function over plain values rather than inside a component. It is
   what made 16,335 switch cases checkable without a browser.

6. **The picker shows label + id together.** Item 12's comparison legend and item 17's notice both
   have to name metrics in prose. The panel titles are ids and the y-axes are labels, so neither
   name alone is unambiguous — say which one is being used, or use both, as the picker does.

No scratch files were left behind.
