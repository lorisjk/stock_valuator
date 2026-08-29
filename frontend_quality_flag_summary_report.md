# Item 18 — The Quality-Flag Summary

`app.py`'s `render_flag_section` (app.py:436), ported. One new module, one new table component, one
section rewired, and one deliberate change of prominence in a section item 9 had already half-built.

---

## 1. Step 1 — what "quality-flag summary" means in the reference

### 1.1 Every place `app.py` surfaces a quality flag

Five, found by reading every use of `is_quality_flag` and every mention of the flag concepts:

| # | where | what it is | source |
|---|---|---|---|
| 1 | **Calculated metrics** table | flags **removed** from it, so a 0/1 column never sits between two ratios | app.py:596–598 |
| 2 | **Quality flags** section — the summary | `st.dataframe` indexed by `flag`, columns `raised` / `periods evaluated` / `most recent` | app.py:445–456 |
| 3 | **Quality flags** section — the expander | `st.expander("Per-period flag values")`: `wide.head(periods)` as strings, plus a **Download CSV** *inside* it | app.py:457–464 |
| 4 | **Valuation history** table | `buyback_distortion_flag` appears as an ordinary column — `is_quality_flag` is applied to `metrics_long` **only** | app.py:608; confirmed: it is one of `valuation_history`'s concepts for all 609 tickers |
| 5 | the empty-frame branch | `st.info("No quality flags recorded for this ticker.")` | app.py:443–444 |

Item 18 is #2. It is the only one of the five that was not already built, and the inventory names it
in exactly those words: *"Quality-flag section with its summary table"*, depending on item 9
(inventory §6, Expected). §2.3's Data-tab table says the same thing in one line: *"own presentation:
per flag, `raised` / `periods evaluated` / `most recent`; per-period values in an expander."*

**Nothing else in the app touches a flag.** No sidebar text, no badge, no aggregate count across
tickers, no staleness treatment (§2.6 records that the staleness fields get none either). Searching
`app.py` for `flag` returns nothing outside these five and the unrelated `_percent_applies` and
update-notice-dismissal uses.

### 1.2 The scope test — what does the text *assert*?

Item 17's test, reused: read the claim, not the call site.

`render_flag_section`'s docstring makes the claim explicitly (app.py:438–441):

> *"A flag is the pipeline saying where it is unsure, and a column of zeros between two ratios buries
> exactly that. **The summary answers the question a 0/1 column makes you reconstruct by eye: how
> often, and how recently.**"*

"How often" and "how recently" are both statements about **one ticker's filed history**. Neither is
sayable about a flag in general. So the summary is per-ticker and belongs where the ticker's data
lives — the Data tab, next to the grid it summarises. That is where the reference puts it, and the
About page independently says the same in prose (`content/about.md:22`: *"Coverage gaps, derivation
provenance, and data-quality flags are shown **in the Data view**"*), which is a third witness and
will matter for item 22.

### 1.3 The second candidate location does not exist in the reference

The brief flagged this as sharper than item 17's question: a per-flag catalogue entry (*what does
`share_count_jump_flag` mean?*) would be encyclopedia-adjacent and would belong to items 20/21.
**There is no such entry anywhere in the reference**, and this is structural rather than an oversight:

- `render_encyclopedia` (app.py:632) iterates `config.METRICS` filtered by `m.chart`. Measured
  against the exported registry: **0 of 52 registered metrics is a quality flag.** A flag has no
  registry entry, therefore no `label`, no `description`, no `formula` and no `chart` — so it cannot
  appear in the encyclopedia even in principle.
- `quality.py`'s "flags" are a different thing entirely: `check_data_quality` / `print_data_quality`
  collect EDGAR **coverage warnings** during a pipeline run and print them. They never reach any
  exported frame. app.py:200–207 records exactly this, which is why `is_quality_flag` is name-based
  and lives in one place on each side.
- The total prose the reference offers about what a flag *means* is the section caption:
  **"Distortion of data."** (app.py:606). Four words, already ported by item 9.

So the answer is **per-ticker only**. The catalogue half of the question resolves to "the reference
does not have one", not to "defer it to items 20/21" — those build the encyclopedia from
`config.METRICS`, and adding flags to it would be inventing a feature rather than porting one.

### 1.4 The flag list, confirmed from the export

Ticker-scoped and period-scoped: a flag is a `concept` in `metrics_long` with one value per period
`end`, exactly like a metric. Not concept-scoped, and the reference shows **all** of them — there is
no curated subset.

| flag | tickers carrying it | periods raised, all tickers |
|---|---:|---:|
| `buyback_distortion_flag` | 605 | 679 |
| `share_count_jump_flag` | 605 | 1,045 |
| `low_tax_rate_flag` | 576 | 4,671 |
| `inorganic_contaminated` | 556 | 1,226 |
| `fcf_exceeds_ebitda` | 470 | 2,724 |

Five concepts, 143,774 flag rows across the export, **every value exactly `0.0` or `1.0`** — no
nulls, no `±inf`. Two of the five carry no `_flag` suffix, which is why `QUALITY_FLAG_CONCEPTS`
exists on both sides.

A sixth appearance: `buyback_distortion_flag` is also a concept of `valuation_history` (all 609
tickers), where the reference does **not** filter it — it renders as a column of the Valuation
history table. Item 9 already reproduces that. Unchanged here, and correct: the filter is applied to
`metrics_long` alone (app.py:596).

Flags per ticker: **5 for 427 tickers, 4 for 137, 3 for 39, 2 for 6.** **No ticker has zero** — so
branch #5, `"No quality flags recorded for this ticker."`, is **unreachable on today's export**. It
is kept (item 9 already had it) because the condition is real — `wide.empty` is true whenever a
ticker's `metrics_long` carries no flag concept — not because it fires.

### 1.5 Threshold and grouping

**No threshold.** Every flag column present for the ticker gets a row, whether it was ever raised or
not: **1,196 of the 2,812 summary rows across all 609 tickers (42.5%) show an em dash** under "most
recent", meaning evaluated and never raised. That is not noise — a flag checked 68 times and never
raised is the reassuring case, and hiding it would leave the reader unable to tell it from a flag
that was never checked at all.

**No grouping, and no gloss.** One flat table, columns in `wide.columns` order — pandas' pivot order,
ascending by code point.

### 1.6 Prior art in the frontend (item 9)

Item 9 built the section and **explicitly deferred this item**, naming it in `DataTab.tsx`'s own
docstring. What existed before this cycle:

- the split (flags out of Calculated metrics) — correct;
- the `"Distortion of data."` caption — correct;
- the `"No quality flags recorded"` branch — correct;
- the **per-period 0/1 grid at the top level**, with a download beside it.

What did not exist: the summary table. And the item-9 report was precise about the consequence, in a
hand-off this cycle simply executed:

> *"the reference puts the summary at the top level and the per-period values inside an expander, so
> this build inverts their prominence — it shows the thing the reference hides and hides nothing. It
> also adds one sentence the reference does not have, "raised is 1, evaluated-and-clear is 0, and a
> gap is neither" … Item 18 should expect to add the summary **above** this table and, in doing so,
> make that sentence redundant."*

So this item is **not** redundant with item 9, and it is not purely additive either: it corrects a
prominence inversion item 9 knowingly left behind.

---

## 2. Step 2 — design

### 2.1 One input, and it is the object already on screen

Item 17's §2.2 discipline: a summary that recomputes its own source can disagree with what it
summarises, and the only structural fix is for there to be one source.

`DataTab` already builds `flagsPivot` — `selectColumns(metricsPivot, …filter(isQualityFlag))` — and
renders `headPeriods(flagsPivot, periods)` as the grid. `flagSummary` takes **that same pivot** and
returns rows. Nothing re-reads `metrics_long`, nothing re-pivots, and there is no second definition
of "which columns are flags". The summary and the grid cannot disagree about which flags exist or
what a cell holds, because they are two readings of one array.

### 2.2 Over every period, not the periods on screen

`render_flag_section` builds `rows` from `wide` and applies `.head(periods)` **only inside the
expander** (app.py:458). So "Show all periods" moves the grid and leaves the summary alone.

That is not a pedantic detail. Measured: **584 of 609 tickers** would produce a different summary if
it were computed over the default 16-period slice instead of the full history — for CRM the
difference is **74 raised periods**. Getting this backwards would make `raised` a statement about the
current scroll position rather than about the company.

### 2.3 Three tables, not one generalised one

`flagSummary`'s rows are two counts and a date. They are not measured quantities and they go nowhere
near `format.ts` — handing them to `DataTable` would mean inventing a `CellFormat` that prints a
date, which is how a formatting layer starts growing cases unrelated to the rule it exists to apply.
So `FlagSummaryTable` joins `DataTable` and `PairTable` as a third shape in the same file, and
`format.ts` is untouched by this cycle.

### 2.4 Prominence, and the sentence that goes away

The grid moves into a `<details>` labelled **"Per-period flag values"** — the reference's expander
label verbatim — and the **Download CSV** moves inside with it, where app.py:462 puts it. The
download still carries the numeric grid rather than the summary: the periods are the exportable
thing, and the summary is derivable from them.

Item 9's invented sentence — *"raised is 1, evaluated-and-clear is 0, and a gap is neither"* — is
**removed**. It existed because a bare 0/1 grid with nothing above it is unreadable; the row above it
now says `raised` and `periods evaluated` in words, so the sentence is doing no work the reference's
own table does not do better. No copy block is added, matching app.py:459.

---

## 3. What was implemented

| file | change |
|---|---|
| `frontend/src/data/flags.ts` | **new.** `FlagSummaryRow`, `flagSummary(pivot)`. Pure, React-free, Node-runnable — which is what makes §4.1 possible |
| `frontend/src/data/DataTable.tsx` | **new export** `FlagSummaryTable`. `DataTable` and `PairTable` untouched |
| `frontend/src/data/DataTab.tsx` | one `useMemo` for the rows; the Quality-flags section rewritten — summary at the top, grid and download inside `<details>`; the invented caption removed; the file docstring's item-18 deferral replaced with what actually happened |
| `frontend/src/data/data-tab.css` | `.flag-periods` (the disclosure) and `.data-table--flags` (a 34rem minimum, so three narrow columns do not strand the flag names across a wide viewport) |

Nothing else. `format.ts`, `pivot.ts`, `csv.ts`, `SectionActions.tsx`, every chart module and the
whole shell are unchanged — see §4.4.

**What was deliberately not implemented:** no flag description, gloss or catalogue anywhere (§1.3 —
the reference has none); no aggregate across tickers; no sidebar badge; no change to the Valuation
history table's `buyback_distortion_flag` column (§1.4).

---

## 4. Step 4 — verification

### 4.1 Against the reference, exactly — 12,466 checks, 609 tickers, 0 failures

The reference side runs `app.py`'s **own** `pivot_ticker` and `is_quality_flag` (imported, not
retyped) over `metrics_long.parquet`, and reproduces app.py:445–453's row loop verbatim. The port
side runs `parseTickerFile` → `pivotTicker` → `selectColumns` → `flagSummary` from Node over the
**exported JSON**, so the comparison covers the export and the port together.

Every field of every row of every ticker: `flag`, `raised`, `periods evaluated`, `most recent`, plus
the empty-branch decision and the row count.

```
12466/12466 checks pass over 609 tickers
```

Spread: 21 tickers with nothing raised at all, through the median, up to **CRM with 91 raised
periods** (also SNPS 85, GDDY 77, PCTY 77, FTNT 67, LSCC 67). Both the 2-flag tickers and the 5-flag
tickers are in it, because the sweep is every ticker.

**The harness is sensitive**, proved by mutation rather than asserted:

| mutation | result |
|---|---|
| drop `dropna()` — every period counts as evaluated | **2,697 failures** |
| `most recent` takes the oldest raised period instead of the newest | **1,298 failures** |
| `value === 1` → truthiness (`value !== 0`) | **passes** — which confirms rather than undermines: the code comment claims the two agree on today's data, and this is that claim measured |

The `dropna()` mutation's size is worth reading twice: **1,998 of 2,812 summary rows (71%)** have an
`evaluated` count below their own ticker's maximum. AAPL's `inorganic_contaminated` reads `8 / 34`
where its other four flags read `/ 68` and `/ 72` — the denominator is the point of showing it.

### 4.2 On a real render — 975 checks, 25 tickers, 0 failures

A headless browser over 25 tickers spanning the whole spread (2-flag through 5-flag, zero-raised
through CRM), comparing the **rendered table text** against the same reference JSON, in both the
default and "Show all periods" states:

```
975/975 DOM checks pass over 25 tickers
```

Covered per ticker: the four column headings verbatim (`flag`, `raised`, `periods evaluated`,
`most recent`); every cell of every row; the disclosure's label (`Per-period flag values`) and its
**closed** default state (`checkVisibility() === false` for the grid inside it); the download being
inside the disclosure; and the absence of item 9's removed sentence.

**The §2.2 invariant, on a real render:** toggling "Show all periods" takes the grid from 16 rows to
73 (AAPL) / 72 (CRM) / 24 (ACT) / 58 (ZTS) and leaves **every summary cell byte-identical**.

### 4.3 No duplicated computation

Structural rather than measured, and that is the stronger form: `flagSummary` takes a `Pivot` and
`DataTab` passes it the same `flagsPivot` binding the grid is rendered from. There is no second
selection, no second pivot, and `flags.ts` imports nothing but the `Pivot` type.

### 4.4 Nothing else regressed

| check | result |
|---|---|
| `check-chart-width.mjs` | **36/36** chart renders fill their container |
| `check-tab-state.mjs` | **13/13** tab-state and default-route checks |
| `check-table-format.mjs` | **6,107/6,107** cells carry a display format — the same baseline. Its `NUMERIC_SECTIONS = [0, 1, 3, 4]` skips the flags section by index and still does; the section now holds two tables and the count is unmoved |
| `npx tsc -b` | clean |
| `npx eslint .` | clean |
| `npx vite build` | `✓ built in 10.93s` |

**A/B over the chart builders — 23 scenarios, all identical.** Rather than trusting remembered
digests, the tree was actually reverted: the three modified files restored from `HEAD` and `flags.ts`
moved away, the sweep re-run, then the changes restored and re-run again. Scenarios: valuation
(plain, masked, back-dated to 2023-06-30), fundamentals, growth, raw facts (with and without derived
concepts) for AAPL / ERIE / CRM, plus two comparison charts.

```
before == after   23/23 digests
```

That sweep is **sensitive too**: changing `MAX_COLS` from 3 to 2 in `charts/grid.ts` moves **12 of
the 23** — every multi-panel figure — so an unchanged digest means something.

`git status`: the only modified paths are the four files in §3, plus `task_new.md` (operator-owned).
Nothing outside `frontend/` was touched.

---

## 5. For items 19, 20/21 and 22

### Item 19 — cadence markers: the Data tab's shape is now final, and one thing moved under you

The Quality-flags section is the **third** `.section` in the tab (index 2) and now contains **two
tables**. Any harness that reaches a section's table with `section.querySelector('table')` gets the
**summary** there, not the grid. `check-table-format.mjs` is unaffected because it skips index 2 by
design, but item 19's markers land on the *facts* table's column headers, and a new DOM harness
should scope to `.flag-periods .data-table` when it means the grid.

Otherwise item 19 is untouched by this cycle and its item-9 hand-off still holds verbatim:
`ttm_source` is **not reconstructed** by `load.ts`, so item 19 starts by widening
`reconstructFrame` — the markers are not merely unrendered, their input is not loaded.

### Items 20/21 — the encyclopedia will not carry the flags, and §1.3 is the reason

Do **not** add flag entries to the encyclopedia to "complete" this item. `render_encyclopedia`
iterates `config.METRICS` filtered by `m.chart`, and **0 of 52 registered metrics is a quality
flag** — a flag has no registry entry at all, so the reference cannot show one and neither should the
port. The reference's entire prose about what a flag means is the four-word caption
`"Distortion of data."`, already in place. If a gloss is ever wanted, it is a **new feature** and
belongs in a brief that says so.

Item 21 (profile coverage) is likewise clear: `profile_visibility()` is keyed by registry id, and
flags have none.

### Item 22 — the About page already points at this section

`content/about.md:22` says *"Coverage gaps, derivation provenance, and data-quality flags are shown
in the Data view rather than smoothed over."* When item 22 ports that page, the sentence is now true
of the built app in the strong sense — the flags are shown *and* summarised there. It was already
true in the weak sense after item 9.

### One finding left in place, because the brief excluded it

The per-period grid renders a raised flag as **`1`**; the reference renders **`1.0`**.
`render_flag_section` does `shown.astype("Float64").astype("string")` (app.py:453), which yields
`"1.0"` / `"0.0"`; `formatCell(value, "raw")` does `String(value)`, which yields `"1"` / `"0"`.
Confirmed on both sides — pandas directly, and the rendered DOM (CRM's newest grid row reads
`['1','1','0','0','0']`).

This is a genuine mismatch with the reference, in the section item 18 now owns, and it is **one
branch** in `format.ts`. It is not changed because the brief excludes it in terms: *"no changes to
the data tab's raw flag columns (items 9–11, already correct if they render flags as-is)"* — and they
do render as-is. Flagging rather than fixing is the standing discipline here; the fix is a
one-decimal change to the `"raw"` branch and touches nothing else, whenever someone wants it.

### Two measurements worth not re-deriving

- **No ticker on the current export has zero flag columns**, so `"No quality flags recorded for this
  ticker."` is unreachable today. The branch is real (`wide.empty`) and is kept; a harness that wants
  to exercise it will need a synthetic frame.
- **All 143,774 flag cells are exactly `0.0` or `1.0`** — never null, never `±inf`. `flagSummary`
  handles a `±inf` cell anyway (evaluated, not raised, which is what `dropna()` does with an
  infinity), and that branch is deliberately untaken rather than absent.
