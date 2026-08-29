# Item 20 — The Metric Encyclopedia

`render_encyclopedia` (app.py:632–674), ported. The first of the two reference views, and the first
item in the rebuild whose entire content already existed in the export — the work was grouping,
ordering, and the two branches that only fire when something is missing.

---

## 1. Step 1 — the reference, read exactly

### 1.1 Grouping: three `st.tabs`, in an order that is not the Analysis tabs' order

`tabs = st.tabs([title for _, title, _ in CHART_SECTIONS])` (app.py:645), one `with tab:` block each
(app.py:646–647). Not headings that run together — three tabs, one visible at a time.

`CHART_SECTIONS` (app.py:86–91) is:

| # | chart | title | blurb (`st.caption`, app.py:648) |
|---|---|---|---|
| 1 | `fundamentals` | **Fundamentals** | What the business does, independent of its share price. |
| 2 | `valuation` | **Valuation** | What the market charges for a claim on that business. |
| 3 | `growth` | **Growth** | Year-over-year change in the underlying filed figures. |

Two things here are easy to carry over wrong and are carried as written:

- **The order is Fundamentals → Valuation → Growth.** The Analysis tabs are Growth → Fundamentals →
  Valuation (`CHART_TABS`, inventory §2.3). Two different lists in the reference; this page's is an
  argument — what the business does, what the market charges for it, how it changed — not a sort.
- **The title is `"Growth"`, not `"Growth (YoY)"`.** `CHART_LABELS` (app.py:38) has the second
  spelling and the Analysis tab strip uses it; `CHART_SECTIONS` has the first and this page uses it.
  The reference keeps both; so does the port.

### 1.2 Within a group: registry order

```python
entries = [m for m in config.METRICS if m.chart == chart]     # app.py:657
```

A filter over `config.METRICS`, which preserves the registry's own sequence. **Not alphabetical** —
and that is the same order every chart's panels have been drawn in since item 4, so the Fundamentals
chart and this page's Fundamentals tab read top-to-bottom in step. Confirmed from the code and then
from the export: `registry.json`'s `metrics` array is in that order and `charts.{id}.metric_ids`
repeats it.

Counts: **fundamentals 29, valuation 13, growth 10 — 52 in total.**

### 1.3 Per metric

```python
st.markdown(f"#### {metric.label}")      # app.py:667
st.caption(f"`{metric.id}`")             # app.py:668
if metric.documented:
    st.markdown(metric.description)                            # app.py:670
    st.markdown(f"**How it is computed:** {metric.formula}")    # app.py:671
else:
    st.warning("Not documented yet — see the report's gap list.")   # app.py:673
st.divider()                                                   # app.py:674
```

An `h4`, the id as a dimmed code caption, then two markdown blocks, then a divider. The
`**How it is computed:**` prefix is **part of the markdown string**, not a label wrapped around the
formula — which matters, because the formula is itself markdown: **50 of the 52 entries carry
backticked concept names**, and three of the mechanism notes' bullets use `*emphasis*`.

### 1.4 The `documented` flag: the entry is **shown**, with an honest gap

This is the branch the brief singles out, and the answer is neither "omit" nor "blank":

- **Per entry** (app.py:672–673): the label and the id still render, and in place of the two prose
  blocks the reference prints `st.warning("Not documented yet — see the report's gap list.")`.
  The metric keeps its position in the list.
- **Per page** (app.py:640–641): above everything,
  `st.warning("Undocumented metrics: " + ", ".join(f"\`{m}\`" for m in missing))`, from
  `config.undocumented_metrics()` — *"Registry ids missing a description or a formula … the app lists
  these honestly rather than showing an empty section"* (config.py:2611–2618).
- `documented` is a property, not a stored flag: `bool(self.description and self.formula)`
  (config.py:2250) — so a metric with one of the two is undocumented.

**Measured: 0 of 52 metrics are undocumented today**, and `registry.json`'s `undocumented` array is
empty to match. Both branches are therefore unreachable on the current registry — the same situation
as item 18's empty-flags branch and item 19's `ᵐ` marker. Both are implemented, and both were
**exercised for real** rather than reasoned about (§3.3).

### 1.5 The mechanism notes: two of the three groups, before the entries

```python
if chart == config.CHART_GROWTH:
    st.markdown(config.GROWTH_MECHANISM_NOTE); st.divider()      # app.py:649-651
elif chart == config.CHART_VALUATION:
    st.markdown(config.VALUATION_MECHANISM_NOTE); st.divider()   # app.py:652-654
```

After the blurb, before the first entry, each followed by its own divider. **Fundamentals gets
none**, and that is not an omission: each note explains one mechanism shared by a whole family of
panels (`GROWTH_MECHANISM_NOTE` — the 4-quarter lag, the positivity rule, the minimum-base guard, TTM
vs quarterly, annual cadence, the two excluded concepts; `VALUATION_MECHANISM_NOTE` — the price
convention, market cap/EV, the harmonic mean, the green marker, the scale guard). The fundamentals
metrics share no single such mechanism.

**They are in this task's scope**, not a chart view's. They are reference material about how a family
of panels is produced, they are rendered by `render_encyclopedia` and by nothing else, and
`registry.json` already exports both as `notes.growth_mechanism` / `notes.valuation_mechanism`.

### 1.6 The dual namespace: the reference does not annotate it, and does not need to

Inventory §3.2's id-namespace split shows up here as two entries describing the same underlying
quantity in two senses — `revenue_yoy_growth` (`id_namespace: metric`) in Fundamentals and `Revenue`
(`id_namespace: xbrl_concept`) in Growth. `render_encyclopedia` adds **no disambiguating text**. What
does the work is already there:

1. they are in **different tabs**, which is the sense;
2. the ids differ and each is printed under its label;
3. the labels differ — `Revenue growth` against `Revenue growth (Quartal, YoY)`.

Checked rather than assumed: across all 52 entries there are **zero duplicate labels and zero
duplicate ids**. A reader never sees the same string twice. So the port adds nothing either; adding a
"this is the growth-concept sense" note would be inventing copy.

### 1.7 The filter

`query = st.text_input("Filter", placeholder="e.g. margin, EBITDA, p_tbv").strip().lower()`
(app.py:643) — one input, **above** the tabs, shared by all three.

The match is `query in` any of four lowercased fields — `id`, `label`, `description`, `formula` —
with `(m.description or "")` (app.py:659–662), so an **undocumented** metric is still findable by its
id or label. Applied **inside each tab**, so a query can empty one group and leave the next full; an
emptied group shows `st.info("Nothing matches that filter in this section.")` (app.py:664).

---

## 2. What was implemented

| file | change |
|---|---|
| `frontend/src/Encyclopedia.tsx` | **new.** `SECTIONS` (`CHART_SECTIONS` verbatim), `matches`, `Entry`, and the page |
| `frontend/src/encyclopedia.css` | **new.** A 78ch reading measure, the filter box, the notes' list spacing, the divider hairline |
| `frontend/src/App.tsx` | the item-20 `Placeholder` replaced by `<Encyclopedia registry={registry} />` |

Nothing else. `registry.json` is untouched (§3.3 restores it byte-identically after its one
deliberate test), the shell's navigation is untouched, and no chart or table code was opened.

**Data source:** `useData().registry`, already fetched once by `DataProvider` at startup for the
pickers — `App` already holds it and passes it down, exactly as it does to `ChartView` and
`ComparisonView`. No fetch, no loading state, no new hook.

**Reused rather than restated:** `.tabs`/`.tab` for the tab strip (Streamlit draws `st.tabs` the same
way in both places, and a view switch unmounts the Analysis shell, so the two strips can never
coexist), `.caption`, and `.notice-inline` — which is this build's established rendering of an
`st.warning`, already used by `ComparisonView` for the exclusion warnings. Two modifier classes,
`.encyclopedia__undocumented` and `.encyclopedia__empty`, distinguish the page-level warning from the
per-section one; they were added because a check could not otherwise tell them apart, which is a
reason to make the markup say what it means rather than to write a cleverer selector.

**One tab's content is mounted at a time**, unlike the Analysis tabs. `TabPanel`'s
keep-mounted rule exists to preserve per-tab state across a switch; these tabs have none — the filter
is page-level in the reference too, one `st.text_input` above all three.

---

## 3. Step 4 — verification

### 3.1 The export carries what the page reads — 266/266

Before comparing the render, the input: `registry.json`'s `id`, `label`, `description`, `formula`
and `documented` against `config.METRICS`, per chart and in order, plus both mechanism notes and the
`undocumented` list.

```
registry.json vs config.METRICS: 266/266 field checks pass
```

This is the item-1 contract re-confirmed for exactly the fields this page renders, so §3.2's
comparison is genuinely about presentation.

### 3.2 The rendered page against `render_encyclopedia` — 1,173 checks, 0 failures

A headless browser reads the live page and is compared against a reference dump produced by
importing **`app.CHART_SECTIONS` and `config.METRICS` themselves** and reproducing app.py:657–662's
filter verbatim. Nine queries × three tabs:

```
"", "margin", "EBITDA", "p_tbv", "  Revenue  ", "growth", "zzz", "TTM", "harmonic"
```

```
1173/1173 encyclopedia DOM checks pass over 9 queries x 3 tabs
```

Per tab and per query: the header, the lede paragraph, the filter's label and placeholder; the tab
strip's **order**; which tab is active; the blurb; the mechanism note's presence, its full text, its
bullet list item by item, and its single divider; the **ordered list of entry ids**; every label;
every entry's two prose blocks against the markdown as a browser renders it; one divider per entry;
and the per-section empty notice appearing exactly when the reference's `entries` list is empty.

`"  Revenue  "` is in the list because `.strip()` is part of the reference's expression and an
unstripped query silently matches nothing; `"zzz"` empties all three sections at once; `"harmonic"`
matches only in `description`/`formula`, so it exercises the two fields a naive filter would skip.

**The harness is sensitive**, by mutation:

| mutation | failures | what fired |
|---|---:|---|
| entries sorted alphabetically by label | **147** of 351 | the order check plus every label/prose pairing downstream of it |
| mechanism note also rendered on Fundamentals | **1** | exactly the "unexpected mechanism note" check |
| `SECTIONS` reversed (Growth first) | **3** | the tab-order check, once per tab visit |

Two of those are single-purpose checks firing exactly once, which is what a well-aimed assertion
should do.

**One correction to my own expectation, recorded because it was mine and not the port's.** The first
two runs reported the mechanism notes as differing. The render was right both times: my
markdown-to-text model did not strip list bullets (`- `), and then did not strip single-`*` emphasis
(`*not*`, `*TTM*`, `*Quartal*`). The final model reproduces what `textContent` returns — lead
paragraph plus `<li>` texts — and the notes match exactly.

### 3.3 The undocumented branches, actually exercised

Both are unreachable on today's registry, so reasoning about them would have proved nothing. Instead
`public/registry.json` was **temporarily** rewritten to mark two metrics undocumented — `roe`
(fundamentals, position 4) and `FCF_TTM` (growth) — and the page re-read:

| what the reference specifies | what rendered |
|---|---|
| page-level warning listing the ids | `Undocumented metrics: roe, FCF_TTM` |
| the entry is **shown**, in place | `roe` still at index 3 of the Fundamentals list |
| label and id still render | `Return on Equity` / `roe` |
| the warning replaces the prose | `Not documented yet — see the report's gap list.`, and `prose: []` |
| still findable by id and by label | filtering `roe` → `['roe']`; `Return on Equity` → `['roe']`; `FCF_TTM` → `['FCF_TTM']` |

`registry.json` was then restored and verified by hash:
`0ec6c0a1cc80d4e0dc1bd572062665971a19b441b4cae1a60310e887742afa92` before and after, and `git status`
reports it clean.

### 3.4 Nothing else regressed

| check | result |
|---|---|
| `check-chart-width.mjs` | **36/36** |
| `check-tab-state.mjs` | **13/13** |
| `check-table-format.mjs` | **6,107/6,107** |
| item 18's flag-summary A/B | **12,466/12,466** |
| item 19's cadence A/B | **3,654/3,654** (1,152,894 cells) |
| chart-builder A/B | **23/23 digests**, identical to items 17/18/19's |
| `npx tsc -b` / `npx eslint .` | clean |
| `npx vite build` | `✓ built in 8.49s` |

The chart A/B is a statement of isolation as much as a regression check: this cycle touched no module
any builder imports, and the digests say so.

`git status`: `App.tsx` plus the two new files, and `task_new.md` (operator-owned). Nothing outside
`frontend/`.

---

## 4. For items 21 and 22

### Item 21 — profile coverage: the same registry, the two fields this page did not use

`registry.json` already carries `profile_visibility` (`{profile: {metric_id: visible}}`, straight
from `config.is_hidden`) and `ticker_profile`, and `Registry` in `contracts.ts` already types both.
Item 21 needs no new fetch either — `useData().registry` is the whole input, exactly as here.

Three things this cycle established that transfer directly:

- **`render_coverage` (app.py:676) iterates the same `CHART_SECTIONS`**, so its section order is
  Fundamentals → Valuation → Growth as well, and its per-chart id list is the same registry order.
  Do not re-derive either.
- The reference's caption is
  `` f"`{profile}` shows {shown_total} of {len(by_id)} registered metrics." `` (app.py:698) — the
  denominator is **all 52**, not the chart's own count.
- `.tabs`/`.tab`, `.caption` and `.notice-inline` are the shared vocabulary; `encyclopedia.css`'s
  78ch measure is deliberately page-specific and should **not** be copied to a 52 × 24 matrix, which
  wants the full width and a `.table-scroll`.

Two reusable methods rather than components: the **temporary-fixture-plus-hash-restore** of §3.3, for
any branch the live data cannot reach; and the DOM harness's habit of capturing raw `textContent` and
normalising in Python.

### Item 22 — About: the disclaimer's third clause, and the markdown path

`react-markdown` is now used in three places (`UpdateNotice`, item 19's cadence legend, and this
page's notes and entries), so the About page's markdown rendering is a solved problem — the file is
already at `frontend/public/update_notice.md`'s sibling path and `fetchNotice` shows the pattern.

Worth knowing before porting the text: `content/about.md:22` promises *"Coverage gaps, derivation
provenance, and data-quality flags are shown in the Data view"* — item 18 delivered the flags, item
19 the provenance, and item 9 the coverage gaps, so all three clauses are now literally true of the
build.

### One thing neither item should do

Do not add quality flags or `ttm_source` to either page. Both hand-offs said it and this cycle
confirmed the mechanism from the inside: **0 of 52 registry metrics is a quality flag**, and
`ttm_source` has no registry entry either, so neither can appear in a page driven by `config.METRICS`
— and `profile_visibility` is keyed by registry id, so item 21 inherits the same boundary for free.
