# The empty-panel notice — item 17

The scope question item 16 left open has a clean answer: **valuation-only, by design, with the
reasoning stated twice.** This port matches that scope, and the deciding evidence is in the message's
own middle sentence rather than in a comment.

---

## 1. Step 1 — the scope question, resolved

### 1.1 Where the reference has it

One place: `empty_valuation_panels` (app.py:511) is defined once and called once, at **app.py:963**,
inside the valuation tab. Nothing equivalent exists on the fundamentals, growth or raw-facts tabs.

The comparison tab has something that *looks* adjacent and is not: a `st.warning` per **excluded
ticker** (app.py:1069). That is item 12's exclusion notice — already ported — and it names whole
lines dropped before drawing, not empty panels inside a grid. Different trigger, different subject.

The data tab's null-column caption is a third distinct thing: *"N null in every period shown — kept
on purpose, an empty column is a finding"* (app.py:405, ported in item 9). It counts **columns of a
table**, is always shown when non-zero rather than as an alert, and belongs to a feature with its own
downloads. Boundary confirmed, and untouched.

### 1.2 By design, not omission — and the evidence is in two places

The last cycle speculated this might be deliberate. It is, and the reasoning is stated twice:

**In the comment above the call site** (app.py:959):

> *"An empty panel still renders as an axis grid, because `build_valuation` returns a figure as long
> as any selected concept has data. Without this the reader sees a chart frame with no line and no
> reason for it, **next to a working current multiple at the top of the page**."*

**And in the message itself** (app.py:980):

> *"The current multiple above still works because it is computed from market data, which has no
> filed-history equivalent."*

That sentence is a claim about the snapshot marker and the current-multiple table — neither of which
exists on the fundamentals, growth or raw-facts charts. So the notice is not *"this grid has empty
panels"*; it is *"**this** panel is empty while the number above it is not, and that is not a
contradiction."* Only the valuation tab can make that statement, and only it needs to.

**So the raw-facts chart's 202 empty panels are not an unaddressed gap.** They have no current
multiple beside them to contradict. A blank `Assets` bar panel in a one-year window says exactly what
it looks like it says; a blank P/E panel next to a live P/E of 22.3 does not.

**Decision: this port matches the reference's scope exactly. No deviation.** §4.4 is the check.

### 1.3 Trigger and content

- **Trigger: any** empty panel — `if blank:` (app.py:964), no count threshold.
- **Content:** a flat list of the empty panels' **labels** (`labels.get(c, c)`), then a fixed
  paragraph. No count, no per-panel detail.
- **It does not differentiate why**, and app.py:970 says that is deliberate, with the measurement
  behind it: *"170 of the 500 exported tickers have at least one empty panel and 97 of those are
  `dividend_yield` on a company that pays no dividend — a true statement about the business, not a
  defect. The only claim made unconditionally is the one that always holds: the value is absent, and
  it was not filtered away."*
- **One conditional clause**, appended when `share_history_absent(ticker)` (app.py:526) — no
  `SharesOutstanding` value at all. Its docstring is emphatic that this is the strict case: *"BKR has
  two points and PSKY seven, which is too few to produce a multiple but is not the same statement,
  and EA has seventy and still produces none. Claiming a cause the data does not support is worse
  than naming only the symptom."*

`empty_valuation_panels` itself windows the frame with the same `years` and `as_of` the chart uses,
so the notice moves with both controls.

---

## 2. Step 2 — design

### 2.1 Where the changes go

`ChartView`, gated on `chart === "valuation"`, plus one field on `ValuationResult`. Nothing else.

### 2.2 One emptiness computation, not two

`buildValuation` already computes `empty` per panel (item 4's `PanelSpec.empty`) and hands it to
`drawPanel`, which decides between a trace and the "No Data" placeholder. **The notice is that same
flag collected into a list** — one `if (empty) emptyPanels.push(id)` inside the loop that already
computed it:

```ts
const empty = !hasAnyValue(series);
if (empty) emptyPanels.push(id);
```

app.py *has* to run a second pass (`empty_valuation_panels` re-windows the frame and re-checks each
concept) because the builder hands it a finished figure and nothing else. Here the builder is the only
thing that windows the series, so returning what it already decided is both cheaper and the only way
the notice cannot disagree with the "No Data" boxes it is describing — the lesson figures.py:832
states for `outlier_report`: *"the control could name points the chart does not draw, or miss ones it
does."* §4.2 measures that they agree.

### 2.3 The years window and as-of

Both reach the notice through the series it is derived from, so no new plumbing. `emptyPanels` is
recomputed inside the same `useMemo` that rebuilds the figure, keyed on ticker, selection, years,
masking and `asOf` — the established "state holds raw intent, effective value is derived" pattern.
Verified live in §4.3, moving each control independently.

### 2.4 The share-history clause — a lazy fetch, and a rejected shortcut

`share_history_absent` reads `facts_full`, which the valuation tab does not otherwise load: item 9
deliberately deferred that file (21 kB gzipped, the largest in the export) to the Data tab. Two
things made this cheap rather than a regression:

- **The notice fires for 35 of 609 tickers at the default selection** (5.7%), measured. So the file
  is fetched rarely, and `useTickerFacts` gained an `enabled` flag to fetch only when the notice is
  actually rendering. §4.5 measures that it works.
- **A cheaper proxy was measured and rejected.** `facts_growth` also carries `SharesOutstanding`, and
  its emptiness agrees with `facts_full`'s on **all 609 bundled tickers**. But only because no ticker
  in the export has *exactly one* filed value — where a YoY series would be empty and the raw history
  would not. That is precisely the thin-versus-absent distinction the docstring exists to protect, so
  agreeing today is not the same as being the same rule. The port reads the frame the reference
  reads.

One consequence, recorded rather than hidden: the clause appears a beat after the rest of the
sentence, where Streamlit renders both at once. The sentence that always holds renders immediately;
the conditional one is appended when the frame lands. It affects **3 tickers in the whole export**
(ERIE, STZ, V — the only three with no share-count history at all).

---

## 3. Step 3 — what was implemented

Five files, all inside `frontend/`:

| file | change |
|---|---|
| [`src/EmptyPanelNotice.tsx`](frontend/src/EmptyPanelNotice.tsx) | **new.** The message, with the scope evidence in its docstring. |
| [`src/data/shareHistory.ts`](frontend/src/data/shareHistory.ts) | **new.** `shareHistoryAbsent`, a pure rule over `facts_full`. |
| [`src/charts/valuation.ts`](frontend/src/charts/valuation.ts) | `ValuationResult.empty`, collected from the existing per-panel flag. |
| [`src/data/DataContext.ts`](frontend/src/data/DataContext.ts) | `useTickerFacts(ticker, enabled)`. |
| [`src/ChartView.tsx`](frontend/src/ChartView.tsx) | the notice, valuation-only, between the chart and the outlier caption. |

`shareHistoryAbsent` lives in its own module rather than beside the component for two reasons: it is
a claim about the data that should be checkable from Node, and eslint's `react-refresh` rule forbids
exporting a function from a component file.

---

## 4. Step 4 — verification

### 4.1 Against the reference

**390 scenarios · 1,170 checks · 0 failures.** 40 tickers — including all three with no share-count
history (ERIE, STZ, V) and the three the docstring names as *thin but not absent* (BKR, PSKY, EA) —
× {full catalogue, default pick} × five window/as-of settings, one of them the extreme
`as_of = 1990-01-01` from the as-of report.

Compared per scenario: the empty-panel list against `empty_valuation_panels`' logic run on the same
exported frames, and `shareHistoryAbsent` against `share_history_absent`. **The notice fires in 216
scenarios naming 673 empty panels; 30 of those carry the share-history clause.**

**The message text was compared character-for-character** against the reference's own f-string, with
markdown emphasis stripped, for three live cases — clause present (ERIE), clause absent (AAOI), and
no notice at all (AAPL). All three match.

*(An earlier run of that comparison reported a mismatch. It was my capture expression losing a
backslash in transit — `/\s+/g` became `/s+/g` and stripped every letter `s` from the page text. The
rendered text was correct throughout; the same trap caught me once before and is worth naming again.)*

### 4.2 The count matches the panels actually drawn

Asserted in every one of the 390 scenarios, and deliberately **not** by comparing the notice's list
to itself: the "No Data" count is read back off the **finished figure**'s annotations, after
`drawPanel` has made its own independent decision from `PanelSpec.empty`.

```
len(result.empty) === figure.layout.annotations.filter(a => a.text === "No Data").length
```

390/390. Live confirmation at the extreme: AAPL with every panel selected at `as_of = 1990-01-01`
names **9 metrics** and the figure draws **9** "No Data" boxes and **0** traces.

### 4.3 It updates as either control moves

| AAPL, every panel | notice | "No Data" drawn | traces |
|---|---|---:|---:|
| 5 years, no as-of | absent | 0 | 18 |
| 1 year, no as-of | absent | 0 | 18 |
| 15 years, **as of 1990-01-01** | **9 metrics named** | **9** | 0 |
| as-of cleared again | absent | 0 | 18 |

No reload, no stale count, and the two controls are independent.

### 4.4 Scope discipline — matched, not deviated

Checked by walking every tab with `ERIE` selected, whose notice fires, and asking the browser whether
the notice is *visible* (`offsetParent !== null`) rather than merely present in the DOM:

| active tab | notice in DOM | notice **visible** |
|---|---:|---:|
| **Valuation** | 1 | **1** |
| Data | 1 | 0 |
| Raw Facts | 1 | 0 |
| Growth (YoY) | 0 | 0 |
| Fundamentals | 0 | 0 |
| Comparison | 1 | 0 |
| back to Valuation | 1 | **1** |

Two shapes of "not shown", both correct. On Growth and Fundamentals it is **not rendered at all** —
`ChartView` is the same component with a different `chart` prop and the notice is gated on
`chart === "valuation"`. On Data, Raw Facts and Comparison it is in the DOM but hidden, because
`ChartView` stays mounted-and-hidden with its last chart (the persistence cycle's design) — the same
reason its picker and slider are still there.

And from the builders themselves: `fundamentals`, `growth` and `raw` results have **no `empty` field
at all**, so there is nothing for another view to render even by accident.

### 4.5 The lazy fetch

| ticker | notice | export files fetched | `facts_full` |
|---|---|---:|---|
| AAPL | does not fire | 4 | **no** |
| ERIE | fires, clause true | 5 | yes |
| AAOI | fires, clause false | 5 | yes |

Exactly the design: the 21 kB file is fetched only when the notice is on screen, which is 5.7% of
tickers at the default selection.

### 4.6 Nothing else regressed

Reverted-tree A/B, seven baselines, all identical and all matching the numbers previous cycles
recorded:

| baseline | sha256 |
|---|---|
| item 8 — three charts, 3,936 figures / 465,488 points | `fe09bcf21e00…` |
| item 13 — the snapshot marker | `f732b8901ea7…` |
| item 14 — masking + report | `e1aea0c8e786…` |
| item 15 — the as-of bound | `149d2d546fa2…` |
| item 12 — comparison figures | `7e17bb1c333e…` |
| item 16 — raw facts | `e5d778d587fa…` |
| item 11 — CSV / copy text | `55fd62aff02f…` |

`check-chart-width` **36/36** · `check-tab-state` **13/13** · `check-table-format`
**6,107/6,107** · `npx tsc -b`, `npx eslint .`, `npx vite build` clean · five files, all inside
`frontend/` · no scratch files left behind.

---

## 5. For items 18 and 19

1. **The scope test that settled this one is reusable.** When a notice's *text* makes a claim about
   something only one chart has, that is the scope statement — stronger than any comment. Item 18's
   quality-flag summary should be read the same way before assuming where it belongs: check what the
   message asserts, not just where the call sits.
2. **`ValuationResult` is now the pattern for chart-level summaries**: the builder returns what it
   already decided, the view renders it, and nothing recomputes. Item 18 should extend the result
   type rather than re-derive flags from a frame — the same argument as §2.2.
3. **`useTickerFacts(ticker, enabled)` exists** for anything else that needs `facts_full` only
   conditionally. Item 18's quality flags live in `metrics_long` (the Data tab reads them from the
   core file), so it probably does not need this — worth confirming rather than assuming.
4. **`.notice-inline` is defined in `data-tab.css`** but is now used by four views (the data tab,
   the comparison view, the raw-facts view, and this notice). It works because `DataTab` is imported
   statically, so its stylesheet is always in the graph — but the class is a shell-level concern
   living in a feature's file. Worth moving to `shell.css` in a cleanup cycle; not moved here because
   it would touch the data tab's own styling for no functional gain.
5. **Three tickers have no share-count history at all** — ERIE, STZ, V — and 35 fire the notice at
   the default selection. Useful fixtures for anything that needs a sparse ticker.
