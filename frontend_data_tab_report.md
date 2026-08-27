# The Data tab — rebuild-list item 9

Five sections over the exported frames, replacing the shell's item-9 placeholder. The first view
built from tables rather than figures, and the first that needs the second per-ticker file.

Verified element-wise against the parquet-derived reference over **all 609 tickers — 3,727,478
checks, 2 failures, both notation-only in the CSV byproduct that item 11 owns**. The three chart
tabs are byte-identical before and after.

---

## 1. Step 1 — the reference, read from the code

Every point below comes from `app.py` or from a measurement, not from the inventory's summary. The
brief was right to insist: **its own sizing estimate for `facts_full` was wrong by a factor of
seven** (§2.2), and the pivot's aggregation rule turned out to be one the inventory does not
mention at all (§1.2).

### 1.1 The five sections, in the order the reference renders them

`render_data_tab` (app.py:552) in full:

| # | section | frame | source |
|---:|---|---|---|
| 1 | Raw & derived facts | `facts_full` | app.py:580–592 |
| 2 | Calculated metrics | `metrics_long`, flag columns removed | app.py:594–601 |
| 3 | Quality flags | `metrics_long`, only the flag columns | app.py:603–605 |
| 4 | Valuation history | `valuation_history` | app.py:607–611 |
| 5 | Current snapshot | `current_snapshot` | app.py:613 |

`DATA_FILES` (app.py:31) carries its own comment on why section 1 reads `facts_full` rather than the
charts' `facts_growth`: *"the charts want the 3 growth concepts, the data tab wants a raw concept
next to its `_TTM` derivation, which is what makes the TTM auditable."*

Sections 2 and 3 are one pivot split in two by `is_quality_flag` (app.py:211): suffix `_flag`, plus
the explicit pair `{fcf_exceeds_ebitda, inorganic_contaminated}` that carry no suffix. The function's
own comment records why neither `config.METRICS` nor `quality.py` can supply the test.

**One observed reference behaviour worth naming, because it looks like a bug and is not.** The split
is applied to `metrics_long` only. `valuation_history` also contains a `buyback_distortion_flag`
concept — confirmed directly, its 14 concepts are `buyback_distortion_flag`, `dividend_yield`,
`ev_ebitda`, `ev_fcf`, `ev_sales`, `p_core_earnings`, `p_ffo`, `p_ppnr`, `p_tbv`, `pb_ratio`,
`pe_ratio`, `pe_to_revenue_growth`, `pfcf_ex_sbc`, `pfcf_ratio` — and app.py:607 pivots that frame
**unfiltered**, so the flag appears as the first column of the Valuation history table. This build
reproduces that rather than silently improving on it. If it is meant to move, it is a change to both
apps and belongs to item 18, not here.

### 1.2 The pivot

`pivot_ticker` (app.py:176), verbatim:

```python
wide = sub.pivot_table(index="end", columns="concept", values=value_column,
                       aggfunc="first", dropna=False)
wide = wide.sort_index(ascending=False)
```

Three semantics, each **checked against pandas** rather than read off the call:

| | what it actually does | how it was checked |
|---|---|---|
| `dropna=False` | keeps a column that is null in every period | two-column synthetic frame, one all-null: `dropna=False` → `['A','B']`, `dropna=True` → `['A']` |
| `aggfunc="first"` | first **non-null**, not first row — pandas' `GroupBy.first` skips NaN | synthetic group `[NaN, 5.0]` → `5.0` |
| index / columns | rows = observed `end` values, **newest first**; columns = observed concepts, ascending | `sort_index(ascending=False)`; both dtypes are plain `object`, checked, so no unobserved category can appear |

The `aggfunc` question is not academic. **The export contains 22 duplicate `(ticker, end, concept)`
groups** — 13 in `facts_full` (BF-B, HNGE, KMI, PYPL, and NAVN nine times), 9 in `metrics_long`
(NAVN eight, PYPL once), 2 in `facts_growth`. Every one of them today is a real value followed by
nulls, so "first row" and "first non-null" happen to agree; the two would disagree the first time the
pipeline emits them the other way round. The reference's rule is implemented, not the one that
currently produces the same answer.

The `dropna=False` note in inventory §2.3 was verified rather than assumed, and it matters constantly
rather than occasionally: **298 of 609 tickers have at least one all-null column in `facts_full`
within the default 16 periods**, 276 in `metrics_long` and 379 in `valuation_history`. AAPL itself has
three.

### 1.3 The null-column caption

`render_data_section` (app.py:405–411). It is emitted for every section, and the second clause
appears only when a column is null across the periods *shown*:

```
{n} of {N} periods · {c} concepts[ · {k} null in every period shown — kept on purpose,
an empty column is a finding]
```

`empty_columns = int(shown.isna().all().sum())` — over `wide.head(periods)`, not over the whole
pivot. Those are different numbers: for `facts_full`, 22 tickers have an all-null column over their
whole history against 298 over the newest 16 periods.

### 1.4 The raw/derived split

`fact_is_derived` (app.py:218) is **structural, not a suffix match**:

```python
return concept not in config.get_concept_candidates(ticker)
```

Its docstring says why: the names the pipeline asks EDGAR for are exactly that dict's keys, so
anything else in the facts frame was derived — which catches `PPNR`, `CoreOperatingEarnings` and
`TangibleEquity`, all derived and all carrying no suffix, which a suffix rule calls raw.

It is presented as **a filter and a grouping, both**: a three-way radio (`All` / `Raw only` /
`Derived only`, app.py:568) narrowing the columns, and `order_fact_columns` (app.py:245) sorting
whatever survives by `(fact_base(c), fact_is_derived(t, c), c)` so a concept sits immediately before
its own derivations. `fact_base` strips `_CALC`/`_TTM`/`_QUARTERLY` repeatedly, so `Revenue` and
`Revenue_TTM` land adjacent — which is what makes the TTM derivation auditable by eye.

### 1.5 Period controls

Two, both at the top and shared by every section (app.py:566–578):

| control | widget | default |
|---|---|---|
| Show all periods | `st.checkbox` | **off** → `DEFAULT_TABLE_PERIODS = 16` (app.py:47, "4 years of quarters") |
| Facts | `st.radio`, horizontal | **All** |

Not a date range and not a count field. `periods = 10**6 if show_all else 16` — "all" is a number
large enough to mean it, so one code path serves both. When off, a caption says *"Showing the most
recent 16 periods."*

### 1.6 The snapshot's shape

`render_snapshot_section` (app.py:468) answers this in its own docstring: the frame is long with one
row per `(ticker, concept)` and **a single constant `end`**, so a ticker's slice already *is* the
transposed view. Pivoting it would produce one row and ~46 columns that scroll sideways and would add
nothing, because there is no second period to compare against. It is rendered as a
`concept` → `value` list sorted by concept, with `end` taken once from `.iloc[0]` for the caption.

---

## 2. Step 2 — design

### 2.1 Which file feeds which section

| section | frame | file | fetched |
|---|---|---|---|
| Calculated metrics, Quality flags | `metrics_long` | `tickers/{T}.json` | already, by the chart path |
| Valuation history | `valuation_history` | `tickers/{T}.json` | already |
| Current snapshot | `current_snapshot` | `tickers/{T}.json` | already |
| **Raw & derived facts** | **`facts_full`** | **`tickers/{T}.facts.json`** | **new — nothing loaded it before** |
| the raw/derived split | — | **`concept_candidates.json`** | **new** |

No sixth file was invented. Both new fetches were already provided for by the export: the per-ticker
report split `facts_full` into its own file precisely because *"a Comparison view never needs
`facts_full`"* and no chart tab does either, and the registry report's §5 recommends *"do not fetch
`concept_candidates.json` up front … lazily, on first Data / Raw Facts view."* Both are wired exactly
that way, and §4.6 measures that it worked.

Measured, so the laziness has a number on it:

| file | raw | gzipped |
|---|---:|---:|
| `tickers/MSFT.json` (four chart frames) | 124.2 kB | 23.1 kB |
| `tickers/MSFT.facts.json` | 198.9 kB | 32.1 kB |
| `concept_candidates.json` | 242.9 kB | 8.4 kB |

Opening the Data tab therefore costs about **40 kB gzipped more than the charts already cost**, once
per ticker for the facts file and once per session for the candidates.

### 2.2 Table rendering — a plain `<table>`, and the brief's estimate was seven times too large

The brief proposed *"a 610-row, 50-column frame (`facts_full` for one ticker)"* and asked for a
measurement before deciding. Measured over **all 609 tickers**:

| | |
|---|---:|
| median pivot | **72 × 34** |
| most rows | **WAT, 95 × 33** |
| most columns | **GL, 78 × 43** |
| largest by area | **BBY, 84 × 40 = 3,360 cells** |
| the default view (16 periods) | ~16 × 34 ≈ **550 cells** |

610 was the *long-frame row count* divided by nothing in particular — AAPL's `facts_full` slice has
2,357 long rows, which pivot to 75 × 35. The real worst case is **3,360 cells for the largest
section at "Show all periods"**, an order of magnitude below where virtualisation starts paying for
itself.

**Decision: a plain `<table>`, no library, no virtualisation, no pagination.** §4.8 carries the
measured render times rather than this estimate. What the plain table does get is a sticky header row
and a sticky period column, because a 43-column table has to scroll sideways and a reader who cannot
see which quarter a number belongs to is reading nothing.

### 2.3 The pivot is a second pass, and says so

`data/load.ts`'s `reconstructFrame` is reused for **fetching and reconstruction** — the new facts
file goes through the same function, so dates are parsed once, nulls are preserved in place and the
`nonfinite` sidecar is carried, with no second parser to drift.

The **pivot itself is genuinely new**, and the reason is an axis change rather than a missing helper.
The charts consume the frame concept-major: one series per panel, with the period axis handed
straight to plotly. This tab needs the transpose — rows = period, columns = concept, one cell per
pair. `data/pivot.ts` is that pass, and it is written as pure functions with no React and no DOM, for
the same reason `load.ts` has none: it runs unchanged in Node, which is what makes §4.1 possible.

### 2.4 Nulls, and a third state the reference cannot show

A null cell renders as a dimmed **`—`, centred**, where a number is right-aligned at full opacity.
Distinguishable in a column scan, which is the entire reason `dropna=False` keeps the cell.

There is a **third** state, and it is not a refinement of the second. JSON cannot carry ±inf, so the
export writes `null` in the value array and names the cell in a `nonfinite` sidecar — **44 cells
across the whole export**, all divisions by zero, on ten tickers. Drawing those as gaps would report
"no data" for exactly the places where the data is the problem. They render as **`∞` / `−∞` in the
warning colour**, with the sign in a `title`. This is *closer* to the reference than a blank would
be: Streamlit reads the parquet, which still holds the infinities, and `_format_absolute` renders
them (as `infT`, which is its own problem and item 10's).

### 2.5 The snapshot

Rendered as the reference's own docstring justifies (§1.6): a two-column `concept` / `value` table
sorted by concept, with `{n} concepts · as of {date} · one row per concept, so a profile that does
not apply is simply absent`. Not pivoted, for the reason app.py:468 gives and this build has no
reason to overturn.

---

## 3. Step 3 — what was implemented, by file

Everything is inside `frontend/`. Nothing in `main.py`, `config.py`, `figures.py`, `metrics.py`,
`parsers/`, the export or `app.py` was touched — confirmed by `git status`.

| file | new? | what |
|---|---|---|
| `src/data/pivot.ts` | new | `pivotTicker`, `headPeriods`, `selectColumns`, `allNullColumns`, `isQualityFlag`, `factBase`, `factIsDerived`, `orderFactColumns`, `filterFactColumns`. Pure, Node-runnable, no React |
| `src/data/csv.ts` | new | `pivotToCsv`, `pairsToCsv`, `downloadCsv` — the item-11 byproduct, kept deliberately small (§6) |
| `src/data/DataTable.tsx` | new | the `<table>` and the snapshot's `PairTable`; the null / infinity / number cell rendering |
| `src/data/DataTab.tsx` | new | the five sections, the two controls, the captions |
| `src/data/data-tab.css` | new | table, controls and cell styling. Defines **no** palette variables of its own — they come from `.app` in `shell.css`, so the two cannot drift |
| `src/contracts.ts` | edited | `CoreFrameName` / `FactsFrameName` split (`FrameName` is their union, so every existing consumer is unaffected), `ConceptCandidates`, `CANDIDATES_SCHEMA` |
| `src/data/load.ts` | edited | `VALUE_COLUMN.facts_full`, `parseTickerFactsFile`, `parseCandidates`, `candidatesFor`, `fetchTickerFacts`, `fetchCandidates`; `fetchTickerFrames`'s body factored into a shared `fetchTickerJson` so both per-ticker files get the same 404-versus-SPA-fallback handling |
| `src/data/DataProvider.tsx` | edited | two more caches, same promise-caching policy as the existing one |
| `src/data/DataContext.ts` | edited | `useTickerFacts`, `useConceptCandidates`, with the same stale-ticker rule `useTickerFrames` already had |
| `src/App.tsx` | edited | the placeholder replaced; `dataSeen` (four lines) |

**Nothing on the chart path changed behaviourally.** The two edited shared files gained exports and a
widened union; `fetchTickerFrames` kept its signature and semantics. §5 is the check.

### Two implementation decisions worth stating

**The tab is mounted on first open and kept mounted afterwards.** `ChartView` is mounted up front and
hidden with `hidden`, so a nine-metric selection survives a glance at another tab. The Data tab wants
the same treatment for its two controls — Streamlit's session state would have kept them — but it
must *not* be mounted up front, because that would fetch `facts_full` for a reader who only opened the
charts. `dataSeen` latches on the first visit and never clears, which buys both. It is adjusted during
render rather than in an effect: React's documented pattern for state derived from a prop-like value,
and the only one that mounts the tab in the render that first needs it rather than one render later.
A `useRef` was tried first and correctly rejected by `react-hooks/refs` — a ref read during render is
the thing refs are not for.

**A missing `concept_candidates.json` degrades, it does not block.** The facts table renders without
the split rather than refusing to draw: the numbers are the section's point and the split is an
annotation on them. That is deliberately unlike a missing `registry.json`, which decides what a chart
is even allowed to show. `candidatesFor` returns an **empty** set for a ticker with no entry, which
makes every concept read as derived — visible in the UI rather than silently wrong, and the export
validator asserts the candidates cover the universe, so that path means the export is broken.

---

## 4. Step 4 — verification

### 4.1 Content, element-wise, against the parquet — all 609 tickers

Not the sample the brief asked for. A Python reference generator imports **`app.py` itself** and
calls its own `pivot_ticker`, `is_quality_flag`, `fact_is_derived`, `order_fact_columns` and
`to_csv_text` — nothing is re-implemented on the reference side, so a drift in `app.py` becomes a
failing check rather than two copies agreeing with each other. A Node harness imports the **shipped**
`data/load.ts`, `data/pivot.ts` and `data/csv.ts` by `file://` URL and compares.

| | |
|---|---:|
| tickers | **609** |
| checks | **3,727,478** |
| **failures** | **2** (both §4.5, notation only) |
| cells compared element-wise | **1,863,398 values + 470,565 nulls + 44 infinities** |

What each check covers, per ticker:

- **the facts pivot under all three filter settings** — row count, column count, the full `end`
  sequence, the full concept sequence *after `order_fact_columns`*, and every cell;
- **calculated metrics** and **quality flags**, as the two halves of the `metrics_long` pivot;
- **valuation history**;
- **the snapshot**, its `as of` date and every `concept`/`value` pair in order;
- **`candidatesFor` against `config.get_concept_candidates(ticker)`**, as sorted key lists.

Cells are compared with `Object.is` on the double — **bit-for-bit, no tolerance**. The export carries
the shortest round-tripping repr of each float, so anything short of exact equality would be a real
defect. The brief's named edge cases are all in the 609 and all pass: AAPL (`standard`), JPM
(`financial`), O (`reit`), V / STZ / ERIE / BKR, CRWV and FIG (short history), plus NAVN and PYPL —
the two tickers whose duplicate rows exercise §1.2's aggregation rule.

### 4.2 Nulls render as nulls, and are distinguishable from zero

Counted rather than assumed, because "no failures" and "no nulls were looked at" are the same result:
**470,565 null cells** across the three pivoted sections of all 609 tickers were compared and all
stayed null — none filled, none coerced to zero, none dropped.

Distinguishability was measured on a real render, on AAPL's quality-flag table, where nulls and real
zeros sit in adjacent columns:

| | nulls | zeros | ones |
|---|---:|---:|---:|
| cells | 55 | 302 | 8 |

| | text | colour | opacity | alignment |
|---|---|---|---|---|
| a null | `—` | `rgb(156,163,175)` | **0.5** | **center** |
| a zero | `0` | `rgb(156,163,175)` | 1 | right |

**A real defect was found here and fixed.** The first version selected `.cell--null`, a bare class,
against a `.data-table td` rule that sets `text-align: right` — one class plus one type, which
outranks it. The colour applied and the centring silently did not; the browser measurement is what
caught it. The dash's colour was also changed from `--shell-line` to `--shell-text` at half opacity:
`--shell-line` is the grid-line colour, and a dash drawn in it against `--shell-bg` is very nearly
invisible. Recessive is the intent; illegible is not, because the reader has to be able to *see* that
the gap is a gap.

The **44 infinities** were exercised too. On AUR, whose `metrics_long` infinities fall inside the
default 16-period window, 14 cells render `−∞` in `rgb(229,169,74)` (`--shell-warn`) with
`title="-Infinity in the pipeline"` — three visually distinct states in one table, confirmed in a
screenshot.

### 4.3 The pivot's shape matches the reference

Included in §4.1's 3.7 M checks for every one of the 609 tickers, not two: same rows in the same
order, same columns in the same order, for every section and every filter setting. The `ends` and
`concepts` sequences are compared as joined strings, so a reordering fails as loudly as a missing
column.

### 4.4 The raw/derived split

`candidatesFor` was compared to `config.get_concept_candidates(ticker)` for all 609 tickers as sorted
key lists — **609/609 exact**. `order_fact_columns` is then checked implicitly and much more strongly
by §4.1: the facts pivot's *column sequence* is compared under `Raw only` and `Derived only` as well
as `All`, so both the membership and the `(base, derived, name)` ordering have to be right for every
ticker.

Observed on the real render for AAPL: **35 concepts All, 17 Raw only, 18 Derived only** — the two
halves partition the whole, and the grouping is visible in the screenshot (`Capex` immediately before
`Capex_TTM`, `DepreciationAndAmortization` before its `_TTM`).

### 4.5 The two failures, in full

```
FAIL FDX/facts.csv: line 1 (notation only, values equal)
FAIL MDT/facts.csv: line 1 (notation only, values equal)
```

Seven values, all in `EPS_TTM_CALC`, all in the range `[1e-6, 1e-4)`:
`1.8548117154811716e-05`, `1.6839506172839506e-05`, `1.7254980079681276e-05`, `1.5515625e-05`
(FDX) and `3.7271950935486376e-06`, `3.614233661524149e-06`, `2.7634942113967826e-06` (MDT).

Python's `repr` switches to exponent notation below `1e-4`; JavaScript's `String` switches below
`1e-7`. **The same double, written two ways** — both round-trip, no precision is lost, and the
harness itself classifies the difference by re-parsing every field and comparing numerically, which
is how the label in the message is produced rather than asserted. Scanned across the whole export
this affects **109 of 1,888,605 finite values (0.006%)**.

The rest of the CSV *is* byte-identical to pandas' `to_csv` for the other 607 tickers, including the
`.0` on integral floats that `String(0)` would otherwise drop. Chasing the exponent notation is item
11's, not this byproduct's — see §6.

### 4.6 The two new fetches are actually lazy, and actually cached

Measured from a genuinely fresh page load (a distinct query string per run, because a hash-only
navigation does not reload and leaves the previous run's resource timeline in place — which is how a
stale timeline gets read as a fresh one):

| | files fetched |
|---|---|
| load straight onto a **chart** tab | `MSFT.json` — **and nothing else** |
| then open the Data tab | `+ MSFT.facts.json`, `+ concept_candidates.json` |
| then leave to Growth and come back | **no new requests** |

So a reader who never opens this tab pays nothing for it, and one who opens it repeatedly pays once.

### 4.7 The controls, on a real render

| check | result |
|---|---|
| five sections, in pipeline order | `Raw & derived facts`, `Calculated metrics`, `Quality flags`, `Valuation history`, `Current snapshot` |
| the default is 16 periods | `16 of 75 periods · 35 concepts` (AAPL facts) |
| the null-column clause appears when it should | `… · 3 null in every period shown — kept on purpose, an empty column is a finding` |
| …and not when it should not | Valuation history, AAPL: `16 of 75 periods · 10 concepts`, no clause |
| the facts filter narrows | All 35 → Raw only 17 → Derived only 18 |
| Show all periods | AAPL 16 → 75 rows, BBY 16 → 84, WAT 16 → 95, GL 16 → 78 |
| a ticker with fewer than 16 periods | CRWV: caption reads `12 of 12 periods`, and Show all is a correct **no-op** |
| the tab follows the sidebar's ticker | AAPL → JPM: facts columns 35 → 37, snapshot rows 46 → 45, hash `#/analysis/JPM/data` |
| the CSV download | 33,065 B blob, `text/csv;charset=utf-8`, 75 rows + header, `end,Capex,Capex_TTM,…` / `2026-06-27,2455000000.0,10041000000.0,…` |

### 4.8 Render performance, and whether it needs virtualisation

Measured in a real browser from the click to the frame in which the new rows are laid out. A fixed
two-frame wait was tried first and measured the **pre-commit** state — which is exactly how a "fast"
number gets reported for a render that has not happened — so the measurement polls
`requestAnimationFrame` until the row count actually changes, then forces layout.

| ticker | pivot | DOM cells after | 16 → all | all → 16 |
|---|---|---:|---:|---:|
| **BBY** (largest by area) | 84 × 40 | 6,007 | **341.5 ms** | 62.2 ms |
| AAPL | 75 × 35 | 5,220 | 270.7 ms | 69.9 ms |
| GL (most columns) | 78 × 43 | 5,763 | 268.5 ms | — |
| WAT (most rows) | 95 × 33 | 5,459 | 270.7 ms | — |

**Acceptable, and virtualisation is not needed.** The two directions are what make that a conclusion
rather than a hope: expanding renders roughly five times the cells and costs roughly five times as
much, so the number is real work and scales with the cells — about 55 µs per cell — rather than being
a fixed scheduling floor. The largest real case in the entire universe lands at **0.34 s for an
explicit, opt-in click**, and the default view every reader actually lands on is ~550 cells and
imperceptible. The threshold where virtualisation earns its complexity is around 10,000 DOM nodes;
the worst case here is 6,007 including headers.

If a later item changes this — item 16's Raw Facts tab draws the same frame as bar panels, and item
10's formatting adds a per-cell step — the number to re-measure is in this table.

---

## 5. The three chart tabs are unchanged

`contracts.ts` and `data/load.ts` are both on the chart path — `parseTickerFile` and
`reconstructFrame` run for every figure — and both were edited this cycle, so this is a real check
rather than a formality.

The item-8 sweep was run against **two source trees**: the current one, and a copy with exactly this
cycle's edits to those two files reversed.

| | |
|---|---:|
| tickers | **41**, spanning **all 24 profiles** |
| chart × ticker × window × selection | 3 × 41 × 8 × 4 |
| figures built per tree | **3,936** |
| traces | 9,023 |
| data points | 213,205 |
| serialised bytes | 21,605,698 |
| sha256, **before** | `1987837d155d3adfc9252ccdf2406bab502dd555324fd14d113432e067f38e8a` |
| sha256, **after** | `1987837d155d3adfc9252ccdf2406bab502dd555324fd14d113432e067f38e8a` |
| **byte-identical** | **yes** |

Windows: 0, 1, 2, 3, 5, 10, 15, and `years` omitted entirely. Selections: full catalogue, the
picker's default, the first three, empty.

**This is a new baseline, not the standing `919868ca…`, and that needs saying plainly.** The earlier
hash came from a harness that lived in a scratch directory and was cleaned up, and its 39-ticker list
is only partly recorded in `frontend_years_window_report.md` — the ten window-sensitive and ten
short-history tickers are named, the remaining nineteen are described as "the established tickers and
sector aggregates from earlier cycles". A different ticker set produces a different hash for reasons
that have nothing to do with correctness, so reproducing `919868ca…` was not possible and pretending
otherwise would have been worse than saying so. The before/after comparison above answers the actual
question — *did this cycle change any figure* — more directly than a match against a historical
constant would, because both sides were built here, minutes apart, from the same data. The 41 tickers
are listed in the harness and cover all 24 profiles, which the previous set is not documented to do.

`ChartView.tsx`, `charts/panel.ts`, `charts/grid.ts`, `charts/mean.ts` and the three builders were
not opened for editing.

## 5.1 Build

`npx tsc -b`, `npx eslint .`, `npx vite build` — all clean, run from `frontend/`.

`git status` shows changes only inside `frontend/`, plus the operator's own `task_new.md` and the
reports. No scratch files were left behind; the dev server and the headless browser used for the
measurements were both stopped and confirmed down.

---

## 6. Where this stops, and who picks it up

Stated per item, including the two places the boundary is **blurred rather than clean**.

### Item 10 — display-vs-export formatting: clean boundary, nothing built

Every value is printed at full precision, via `String(v)` — the shortest string that round-trips back
to the same double, which is the same guarantee Python's `repr` gives. **This is not a shortcut
around item 10; it is the state item 10 refines.** It is also what makes §4.1 possible at all: the
brief asks for every displayed value to equal the source at full precision *"not a rounded display
value"*, and a table that had already scaled `1094170000000` to `1.09T` could not be compared that
way.

None of `format_for_display`'s three rules is implemented: no `ABSOLUTE_THRESHOLD` scaling
(T/B/M/K), no `_percent_applies`, no `{v:.4f}`. Half of that rule set would produce a table that is
wrong in a way a reader cannot see — `_percent_applies` exists precisely because reading the
registry's percent flag by name alone rendered $109 bn of revenue as `10941700000000.00%` — so it is
all or nothing, and item 10 is where it goes.

One consequence worth flagging forward: full precision is currently *more* informative than the
reference for small numbers. FDX's `EPS_TTM_CALC` of `1.85e-05` shows here as
`0.000018548117154811716`; Streamlit's `{v:.4f}` shows it as `0.0000`.

### Item 11 — CSV downloads and copy blocks: **blurred, deliberately, and here is exactly how**

A download button per section **was** built, because the section already holds the numeric pivot and
producing the file is three lines rather than a feature. It is verified (§4.5, §4.7) and handed off
unpolished. What exists: `pivotToCsv`, `pairsToCsv`, `downloadCsv`, and a `{ticker}_{slug}.csv` name
per section. What does **not** exist, all of it item 11's:

- **the copy-table expander** — `st.code` of the newest 8 periods (`DEFAULT_COPY_PERIODS`) with its
  character count in the label. Not started;
- **exponent-notation parity** with Python's `repr` (§4.5) — 109 values export-wide;
- ±inf in the CSV is written `inf`/`-inf` to match what the parquet holds and what Streamlit's own
  download therefore carries. That is a judgement made here that item 11 may want to revisit.

The one rule the byproduct does observe, because getting it wrong is the failure mode inventory §3.4
names by hand: **the CSV is produced from the numbers, never from what the table displays.** There is
no formatting step between the pivot and `pivotToCsv`. When item 10 adds one, that separation is
already in place and is what keeps the CSV carrying `1094170000000.0` instead of `"1.09B"`.

### Item 16 — Raw Facts tab: clean, and half its groundwork is done

Not built. It is a chart-shaped bar view over the same frame, not this tab's table section. What it
inherits ready-made: `fetchTickerFacts`, `useTickerFacts`, the `facts_full` reconstruction, and
`concept_candidates.json` with `candidatesFor` — which is the exact pair
`figures.available_raw_concepts(ticker, facts_full, show_derived)` needs for its
include-derived toggle.

### Item 18 — quality-flag summary: **blurred, and the blur is in the caption**

The Quality flags section shows the **per-period 0/1 values** — the raw material, which is what this
item's scope allows. The summary table (`flag` / `raised` / `periods evaluated` / `most recent`,
app.py:436) is **not** built.

Where the boundary is not clean: the reference puts the *summary* at the top level and the per-period
values inside an expander, so this build inverts their prominence — it shows the thing the reference
hides and hides nothing. It also adds one sentence the reference does not have, *"raised is 1,
evaluated-and-clear is 0, and a gap is neither"*, because a bare 0/1 grid with no summary above it is
otherwise unreadable. Item 18 should expect to add the summary **above** this table and, in doing so,
make that sentence redundant.

### Item 19 — cadence markers: clean, and enforced by the loader

Not built, and `ttm_source` is **not even reconstructed** — `load.ts`'s `reconstructFrame` reads
`end`, `concept` and the value column only. So the ᵃ/ᵐ markers and their legend are not merely absent
from the UI, the data they need has not been loaded; item 19 starts by widening the reconstruction.
`ffo_gains_source` is likewise not reconstructed, which matches `app.py` never having read it
(inventory §2.6 records it as exported-and-unused).

### Not in scope and not started

The as-of control (item 15) does not reach this tab and correctly does not appear — inventory §3.5:
`as_of` touches Valuation and Comparison only, and the data tab calls `_window_frame(..., as_of=None)`
unconditionally.

---

## 7. What to re-check by hand

The numbers above are all machine-measured, and the ones that matter — 3.7 M element-wise
comparisons over 609 tickers, byte-identical chart figures — do not need a human. Two things do:

1. **Readability at full precision.** A 40-column table of unformatted doubles is correct and wide.
   Whether it is *usable* enough to live with until item 10 lands is a judgement call, and it is
   yours. If the answer is no, item 10 moves up the order rather than this build being patched.
2. **The `—` for a null, in your own browser.** Its contrast was changed once already this cycle
   after measuring that the first choice was nearly invisible. Font rendering and the exact grey
   differ between browsers in a way that is worth seeing rather than re-deriving.
