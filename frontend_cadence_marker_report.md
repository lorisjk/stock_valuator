# Item 19 — TTM Cadence Markers

`cadence_markers` (app.py:257) plus its rendering in `render_data_section` (app.py:419–424), ported.
The hand-off was right that this is a data-loading task before it is a rendering task, and the
brief's one wrong premise — per-cell — is overturned by the reference's own docstring and by
measurement.

---

## 1. Step 1 — the gap, precisely

### 1.1 `ttm_source` is in the export, in one file, with two values

`tickers/{TICKER}.facts.json` → `frames.facts_full`, whose columns are:

```
["concept", "end", "value", "ttm_source", "ffo_gains_source", "yoy_growth"]
```

Confirmed by reading a real exported file, not the pipeline report. Values, measured across all 609
tickers and **1,152,894 rows**: `"quarterly_rolling"`, `"annual_fact"`, and `null` — nothing else.
The two labels are `config.TTM_SOURCE_ROLLING` / `TTM_SOURCE_ANNUAL` (config.py:213–214), written by
`metrics.py:422` and `parsers/parse_edgar.py:959`.

`null` is not a third cadence. It is the state of a row with no value, and app.py's `.notna()` filter
(app.py:274) exists to say so: *"Rows with no value carry `ttm_source = None` and contribute nothing,
so an empty cell is never claimed to have a provenance."*

### 1.2 `load.ts` drops it, at a nameable line

`reconstructFrame` (load.ts:62) reads **exactly three columns** and no others:

```ts
const endColumn     = block.data[index("end")]                  // load.ts:70
const conceptColumn = block.data[index("concept")]              // load.ts:71
const valueColumn   = block.data[index(VALUE_COLUMN[name])]     // load.ts:72
```

and returns `{ columns, rowCount, end, concept, value, nonfiniteRows }` (load.ts:85–96). So
`ttm_source` was never *dropped* in a filtering step — **it was never indexed**. `Frame.columns`
carried the column *name* the whole time (it is `block.columns` verbatim), which is exactly the kind
of half-presence that reads like the data is there.

The old comment on `VALUE_COLUMN` said so in as many words and named this item:

> *"`ttm_source` and `ffo_gains_source` are likewise not reconstructed — ttm_source is item 19's
> cadence markers, and app.py has never read ffo_gains_source at all (inventory §2.6)."*

**It reaches the frontend in no other frame.** `metrics_long`, `valuation_history`, `facts_growth`
and `current_snapshot` do not carry the column at all — checked against the exported JSON, not
assumed.

### 1.3 The reference's marker — and it is **per column**, not per cell

This is the brief's one wrong premise, and the reference rebuts it in its own docstring
(app.py:260–266):

> *"Marked per column rather than per cell, and that is a measurement rather than a convenience:
> `calculate_ttm` and `parse_edgar.annual_ttm_values` are disjoint by construction — the annual path
> runs only where the quarterly extraction produced nothing — so **provenance is a property of the
> series**. 0 of 5,836 series in the exported frame carry both labels. A per-cell suffix would cost
> readability in every row to express something that never varies within a column."*

**Re-measured on today's export**, since the universe has grown since that number was written:
**7,099 (ticker, concept) series carry provenance — 6,959 quarterly-only, 140 annual-only, and still
0 mixed.** The claim holds; the number is now 7,099.

The treatment itself:

| what | value | source |
|---|---|---|
| annual marker | `ᵃ` (U+1D43, modifier letter small a) | app.py:253 |
| mixed marker | `ᵐ` (U+1D50) | app.py:254 |
| where it goes | appended to the **column header** with a space: `f"{concept} {marker}"` | app.py:419–422 |
| what it is applied to | the **display** frame only, so downloads and copy blocks keep clean names | app.py:397–399 |
| legend | `st.caption(marker_legend)`, **after** the table, before the download | app.py:423–424 |
| legend gate | `marker_legend and column_markers and any(c in shown.columns for c in column_markers)` | app.py:423 |

The marker is a single character *because* the table is already ~37 columns wide (app.py:250–252);
the legend under it names the concepts in full. Both marker characters are already superscript
codepoints, so no `<sup>` is involved on either side.

The legend text, verbatim (app.py:283–303), is three runs joined by `"  \n"` — a markdown hard line
break. The closing run is appended **only when something is marked**, so an unmarked ticker gets `""`
and no caption at all, not a lone paragraph about columns that carry no provenance:

> ᵃ **annual cadence** — \`C1\`, \`C2\`. This filer discloses the item once a year, so the value is
> the 12-month figure taken as filed rather than four quarters summed. One point a year is complete
> coverage of what was published, not a gap.
> ᵐ **mixed cadence** — \`C3\`: some periods summed from quarters, others read from a 12-month fact.
> Unmarked \`_TTM\` columns are summed from four quarters. \`FCF_TTM\`, \`EBITDA_TTM\`, \`FFO_TTM\`
> and \`EPS_TTM_CALC\` are built from other columns further down the pipeline and carry no provenance
> of their own — theirs is their inputs', visible in this same table.

### 1.4 One table, and no overlap with item 13

`cadence_markers` has **one caller**: app.py:587, the `Raw & derived facts` section. The other four
Data-tab sections pass no markers, and `figures.py` never reads `ttm_source` or `ffo_gains_source` at
all — no chart, no hover template, no tooltip. This is strictly a Data-tab-table feature.

**Not item 13.** The snapshot marker is a green point drawn on a valuation panel to mark the
current market-derived multiple; this marks a *filed-history column's* extraction path in a table.
Different frame, different tab, different question. No shared code and none wanted.

### 1.5 Scoping, per item 18's warning

Item 18 put a second table into the Quality-flags section, so `section.querySelector('table')` is no
longer unambiguous there, and "the first table on the page" was never a safe way to find anything.

The target here is the section whose `<h2>` reads **`Raw & derived facts`**. This cycle's DOM harness
finds it by that heading and never by index:

```js
[...document.querySelectorAll('.data-tab .section')]
  .find(s => s.querySelector('h2')?.textContent === 'Raw & derived facts')
```

`check-table-format.mjs` still selects by index and still skips index 2, so it is unaffected — but it
would have been the next thing to break, and this is the pattern that replaces it.

---

## 2. Step 2 — design

### 2.1 Carrying the column: one convention, and the second column deliberately left out

There was **no existing pattern** to follow — no metadata column of any kind reached the frontend
before this cycle. So the shape is a decision, and the deciding fact is the *second* provenance
column: `facts_full` exports `ffo_gains_source` too, built by the same instrument for the same
reason (config.py:216: *"Same instrument as ttm_source and for the same reason"*), and **app.py never
reads it** — inventory §2.6 records it as exported-and-unused and §6's decision list keeps
*"surface it or stop exporting it"* open.

Surfacing it here would be settling that decision on the reference's behalf. Naming a field
`ttmSource` on `Frame` would guarantee a second argument about the second column. So:

```ts
const TEXT_COLUMNS: Partial<Record<FrameName, readonly string[]>> = {
  facts_full: ["ttm_source"],
};
```

feeding `Frame.text: ReadonlyMap<string, readonly (string | null)[]>`, empty for every other frame.
The **shape is the convention and the list is the scope**: adding `"ffo_gains_source"` to that array
is the whole change, whenever the decision is made.

Costs nothing at load: the map holds a reference to the array the JSON parse already produced — no
copy, no extra fetch, no extra file. A column named in `TEXT_COLUMNS` that the export does not carry
is skipped rather than thrown on, which mirrors app.py:272's `if "ttm_source" not in frame.columns`
— an older bundle degrades to "no markers" instead of failing.

### 2.2 Per column, computed from the whole frame — and that is observable

`cadenceMarkers(frame)` takes the ticker's whole `facts_full`, groups the non-null labels by concept,
and marks a concept `ᵃ` when its label set is exactly `{annual_fact}` and `ᵐ` when it holds more than
one. No cell ever carries a marker.

The reference's ticker filter has nothing to do here — `facts_full` arrives as
`tickers/{T}.facts.json` and is already one ticker's. The `.notna()` half of the filter is real and
is kept.

**The window does not enter it**, and that difference is visible rather than theoretical: **28 marked
columns hold no value at all in the default 16-period window** and keep their `ᵃ` regardless.
`AMZN / StockIssued_TTM` is one; rendered, its header reads `StockIssued_TTM ᵃ` above sixteen em
dashes. A per-visible-cell rule would strip the marker there and tell the reader nothing about why
the column is empty — which is the opposite of what the marker is for.

### 2.3 The legend is app.py's markdown string, rendered as markdown

`cadenceMarkers` returns the legend as the **exact string app.py builds**, hard breaks and all, and
`Section` renders it through `react-markdown` — already in the bundle for the update notice
(`UpdateNotice.tsx`), so no dependency is added. Two consequences worth having:

- the port's `**bold**` and `` `code` `` become real elements, as Streamlit's `st.caption` does;
- the A/B against Python is a **string equality**, not a DOM approximation.

Placement matches: after the table, before the download.

### 2.4 The filter and the period control

The legend's gate is `shown.concepts`, i.e. the columns after the raw/derived filter — app.py:423
gates on `shown.columns` for the same reason. The row count never enters it, because `head(periods)`
drops rows and not columns, so **"Show all periods" cannot make the legend appear or vanish**.
Measured across all 112 marked tickers:

| filter | markers on screen | legend |
|---|---|---|
| All | yes | shown |
| Raw only | **0 of 112** — every marked concept is a `_TTM`, hence derived | hidden |
| Derived only | **112 of 112** | shown |

The legend still names every marked concept even when the filter hides some of them. That is the
reference's behaviour and it is right: the list is the ticker's provenance, not the view's.

The marker never enters the `Pivot`, only the `<th>` text — so `pivotToCsv` cannot see it and the
download keeps filed concept names. Structural, and checked anyway (§3.4).

---

## 3. What was implemented

| file | change |
|---|---|
| `frontend/src/contracts.ts` | `Frame.text: ReadonlyMap<string, readonly (string \| null)[]>` |
| `frontend/src/data/load.ts` | `TEXT_COLUMNS`, and `reconstructFrame` populating `text`. The `VALUE_COLUMN` comment rewritten — it no longer describes a deferral |
| `frontend/src/data/cadence.ts` | **new.** `ANNUAL_CADENCE_MARKER`, `MIXED_CADENCE_MARKER`, `cadenceMarkers(frame)` → `{ markers, legend }`. Pure and React-free |
| `frontend/src/data/DataTable.tsx` | optional `markers` prop; the header renders `` `${concept} ${marker}` `` |
| `frontend/src/data/DataTab.tsx` | one `useMemo` for the cadence; `Section` gains an optional `cadence` prop, gates the legend on its own shown columns, and renders it with `react-markdown`; the facts section is the only caller |
| `frontend/src/data/data-tab.css` | `.cadence-legend` |

Nothing else. `format.ts`, `pivot.ts`, `csv.ts`, the raw/derived split, the Quality-flags section and
every chart module are untouched.

**Not implemented, deliberately:** `ffo_gains_source` is not surfaced (§2.1); no marker on any other
table or chart (§1.4); no per-cell treatment (§1.3).

---

## 4. Step 4 — verification

### 4.1 `ttm_source` reaches the frontend intact — 1,152,894 cells

Element-wise, every row of every ticker: the array in `frame.text.get("ttm_source")` against the
column in the exported JSON, plus length-against-`rowCount`.

### 4.2 Markers and legend against `app.py` — 3,654 checks, 609 tickers, 0 failures

The reference side calls **`app.cadence_markers` itself** (imported, not retyped) over
`facts_full.parquet`. The port side runs `parseTickerFactsFile` → `cadenceMarkers` from Node over the
exported JSON. Compared per ticker: the full concept→marker map, and the legend **character for
character**.

```
3654/3654 checks pass over 609 tickers (1,152,894 ttm_source cells; 112 tickers marked)
```

112 marked tickers on both sides. Distribution: 98 with one marked concept, 11 with two, and one each
with 3 (`Q`), 7 (`NAVN`) and 10 (`PSKY`). Most-marked concepts: `StockIssued_TTM` (37 tickers),
`StockRepurchased_TTM` (30), `ShareBasedCompensation_TTM` (17), `DividendsPerShare_TTM` (16).

**Zero tickers carry a `ᵐ`**, so that branch is unreachable on today's export — like item 18's
empty-flags branch. It is implemented anyway, because the docstring is explicit that a marker which
quietly rounded a mixed series to "annual" would assert something the pipeline has not established.

**The harness is sensitive**, by mutation:

| mutation | failures | why that number |
|---|---:|---|
| count `null` as a label | **1,218** | every ticker becomes "mixed" — 609 marker maps and 609 legends |
| sort concepts descending | **14** | exactly the 14 tickers with more than one marked concept |
| drop the closing legend paragraph | **112** | exactly the marked tickers |

Each lands precisely where its own reasoning predicts, which is what makes the passing run mean
something.

### 4.3 On a real render — 184 checks, 14 tickers, 0 failures

A headless browser over 14 tickers spanning the whole distribution (4 unmarked, and 1/2/3/7/10-marker
cases including `Q`, `NAVN`, `PSKY`), scoped to the facts section **by its heading** (§1.5). Each
ticker is read in four states: default, `Raw only`, `Derived only`, and `Show all periods`.

```
184/184 DOM checks pass over 14 tickers
```

Per ticker: every marked header carries exactly the reference's marker and no unmarked header carries
one; the legend's presence matches; its **rendered text** equals the reference markdown as a browser
renders it; it is rendered exactly once; `Raw only` removes every marker *and* the legend;
`Derived only` keeps both; `Show all periods` changes the row count and leaves markers and legend
byte-identical; and the copy block's CSV header line carries **no marker character**.

Structure spot-checked on `PSKY`: one `<br>`, one `<strong>` reading `annual cadence`, and 15
`<code>` elements — its 10 marked concepts plus the closing paragraph's five.

**The displayed-slice question, rendered:** `AMZN`'s facts table shows

```
header: "StockIssued_TTM ᵃ"
cells:  ["—","—","—","—","—","—","—","—","—","—","—","—","—","—","—","—"]
```

The marker is a statement about the series, and it survives a window that shows none of it.

### 4.4 No duplicated computation

`DataTab` calls `useTickerFacts(ticker)` once; the same `facts` object feeds `pivotTicker` (the
table) and `cadenceMarkers` (the markers). No second fetch, no second parse, no second pass over a
differently-derived frame. Item 17's and item 18's discipline, structurally.

### 4.5 Nothing else regressed

| check | result |
|---|---|
| `check-chart-width.mjs` | **36/36** |
| `check-tab-state.mjs` | **13/13** |
| `check-table-format.mjs` | **6,107/6,107** |
| item 18's flag-summary A/B | **12,466/12,466**, unchanged |
| `npx tsc -b` / `npx eslint .` | clean |
| `npx vite build` | `✓ built in 15.53s` |

**A/B over the chart builders — 23 scenarios, all identical.** This one is load-bearing this cycle:
unlike item 18, this change touches `contracts.ts` and `load.ts`, which every chart reads. The tree
was actually reverted — those two files restored from `HEAD` (item 18 touched neither, so the revert
isolates item 19 exactly), the sweep re-run, then the changes restored and re-run:

```
before == after   23/23 digests
… and identical to item 18's baseline, which was itself identical to item 17's
```

The sweep is sensitive: changing `MAX_COLS` from 3 to 2 in `charts/grid.ts` moves 12 of the 23.

`git status`: the six files in §3 plus `task_new.md` (operator-owned). Nothing outside `frontend/`.

---

## 5. For items 20, 21 and 22

### Item 20 — the encyclopedia does not describe cadence, and should not start

`ttm_source` has no registry entry, exactly as the quality flags have none (item 18 §1.3). The
mechanism notes it *would* belong to — `config.GROWTH_MECHANISM_NOTE` and
`VALUATION_MECHANISM_NOTE`, rendered at app.py:649/652 — say nothing about TTM provenance. The whole
explanation lives in the Data tab's legend, which is now built. Do not add a third home for it.

### Item 21 — nothing owed

`profile_visibility()` is keyed by registry id; cadence is a property of a *fact* column, which has
none.

### Item 22 — the About page's "derivation provenance" clause is now true

`content/about.md:22` promises *"Coverage gaps, **derivation provenance**, and data-quality flags are
shown in the Data view rather than smoothed over."* That middle clause was the only one the build had
not yet delivered; after this cycle all three are literal. Item 22 can port the sentence as-is.

### `ffo_gains_source` is now a one-word change, and still an open decision

Inventory §6's decision #4 — *"exported and never read. Either surface it beside `ttm_source` or stop
exporting it"* — is untouched here on purpose. If it is ever decided in favour of surfacing, the
loader change is adding `"ffo_gains_source"` to `TEXT_COLUMNS.facts_full`; everything after that is a
new rendering decision (and a new legend), because app.py has no rendering to port.

### Two numbers worth not re-deriving

- **7,099 series carry provenance: 6,959 quarterly-only, 140 annual-only, 0 mixed.** The `ᵐ` path is
  live code with no live input; a harness that wants to exercise it needs a synthetic frame. (The
  docstring's older figure of 5,836 is the same claim on a smaller universe.)
- **28 marked columns are entirely empty in the default 16-period window.** That set is the regression
  test for anyone who later mistakes the marker for a per-cell annotation.

### A harness trap, hit again

A `\n` inside a CDP `Runtime.evaluate` expression built from a template literal lost its escaping in
transit and became a literal newline inside a string literal, producing a bare
`SyntaxError: Invalid or unexpected token` with no hint of the cause. Same family as the
`/\s+/g` → `/s+/g` slip from item 17, and the same fix applies: **keep escape sequences out of
browser-evaluated expressions** — `String.fromCharCode(10)` cannot be mangled, and normalising
captured text in Python rather than in the page avoids the whole class.
