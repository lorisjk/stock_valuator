# Display formatting and table sizing — item 10

`82300000000` now reads `82.30B`, and a two-column snapshot no longer draws itself inside a
1,189px-wide box.

Verified by comparing **4,390,657 rendered strings across all 609 tickers** against `app.py`'s own
`format_for_display`, plus **6,107 cells read back out of the real DOM** — zero differences. The
numbers behind the tables are untouched: the CSV path still round-trips **105,160 of 105,160** fields
to the exact double.

Two real defects were found by those checks rather than by reading the code, and both are described
below (§4.2, §4.6).

---

## 1. Step 1 — the reference, read from the code

### 1.1 `ABSOLUTE_THRESHOLD` and the scaling rule

| | source | value |
|---|---|---|
| `ABSOLUTE_THRESHOLD` | app.py:316 | **`1e4`** |
| `_MAGNITUDES` | app.py:312 | `((1e12,"T"), (1e9,"B"), (1e6,"M"), (1e3,"K"))`, tested in that order |
| `_format_absolute` | app.py:319 | first cutoff where `abs(value) >= cutoff` → `f"{value/cutoff:,.2f}{suffix}"`, else `f"{value:,.2f}"` |
| `_format_ratio` | app.py:328 | `f"{value*100:.2f}%"` if percent, else `f"{value:.4f}"` |
| null | app.py:320, 329 | the **empty string**, from `pd.isna` |

Run against the reference for a range of magnitudes, so the conventions are recorded rather than
inferred:

| input | `_format_absolute` | | input | `_format_absolute` |
|---:|---|---|---:|---|
| `0.5` | `0.50` | | `1e6` | `1.00M` |
| `12.5` | `12.50` | | `82_300_000_000` | **`82.30B`** |
| `999.994` | `999.99` | | `1e12` | `1.00T` |
| `999.995` | `1,000.00` | | `-1e9` | `-1.00B` |
| `1000.0` | `1.00K` | | `-1234.5` | `-1.23K` |
| `9999.99` | `10.00K` | | `-0.5` | `-0.50` |
| `1e4` | `10.00K` | | `nan` | `` (empty) |
| `999_999` | **`1,000.00K`** | | | |

Two conventions worth naming because they are easy to get wrong: **both branches carry thousands
separators and exactly two decimals**, and `_format_ratio`'s non-percent branch carries **exactly
four decimals and no separator** (`33.3333`, never `33.33`). The `1,000.00K` in the table is not a
typo — `999,999 / 1e3` is `999.999`, which rounds to `1,000.00` and keeps the `K`. It is the
reference's own output and is reproduced.

`format_for_display` (app.py:353) applies these **per column, from that column's own
`abs().max()`** (app.py:373), so one column never mixes two treatments. It runs on
`wide.head(periods)` (app.py:400, 413) — the periods *being shown*, not the whole pivot, which means
"Show all periods" can genuinely move a column between treatments. Measured: for AAPL, `Goodwill`,
`StockIssued` and `StockIssued_TTM` do exactly that.

### 1.2 `_percent_applies` — the same registry flag, plus one test

app.py:334. It is the registry's `percent` flag, **and** a `value_column` test:

```python
metric = config.METRICS_BY_ID.get(concept)
return metric is not None and metric.percent and metric.value_column == value_column
```

Not a name-based heuristic — but a bare name lookup is exactly the earlier bug. The docstring names
three colliding ids. **There are ten**, enumerated by intersecting the registry's ids with
`facts_full`'s concepts:

`CoreOperatingEarnings`, `EPS_TTM_CALC`, `FCF_TTM`, `FFO_TTM`, `NetIncomeLoss`,
`OperatingIncomeLoss_TTM`, `PPNR`, `Revenue`, `SharesOutstanding`, `StockholdersEquity`

Every one is a **growth-chart** metric with `percent=True` and `value_column="yoy_growth"`, and every
one is also a facts column holding absolute dollars or share counts. The docstring's three are the
ones that were noticed; the `value_column` test happens to cover all ten. Reading the flag by name
alone rendered $109bn of revenue as `10941700000000.00%`, and it would do the same to seven more
columns than the comment suggests.

All four data-tab sections pivot on `value` (app.py:588, 594, 608, 613, all using `pivot_ticker`'s
default), so the test is always `value_column == "value"` and no growth entry can ever match.

### 1.3 Which columns get which treatment

Measured over all 609 tickers, default 16-period view — columns per treatment:

| section | absolute | percent | ratio (4 dp) |
|---|---:|---:|---:|
| Raw & derived facts | **17,834** | **0** | 2,738 |
| Calculated metrics | 2 | 3,810 | 3,911 |
| Valuation history | 1 | 603 | 5,006 |
| Current snapshot *(per value)* | 5,481 | 764 | 18,953 |

- **Facts: never percent.** No `facts_full` concept has a registry entry describing `value`, so the
  section falls entirely through to the magnitude rule — currency and share counts scale, per-share
  figures do not.
- **Metrics: mostly the registry flag.** The 3,911 `ratio` columns are the metrics with
  `percent=False` (`debt_to_equity`, `net_debt_to_ebitda`) plus **seventeen concepts with no registry
  entry at all** — `effective_tax_rate`, `rotce`, `buyback_distortion_flag` and the fourteen
  `*_quarterly` series. Those fall through to the magnitude rule and print as `0.1730` rather than
  `17.30%`. That is the reference's behaviour, reproduced deliberately; it is arguably wrong and it
  is not this item's to change, because changing it changes both apps.
- **Valuation: multiples are ratios**, `dividend_yield` is the one percent, and
  `buyback_distortion_flag` rides along in this frame (item-9 report §1.1 records why).
- **Snapshot: all three, decided per value** (app.py:487) because one value per concept leaves no
  column to measure.

### 1.4 Per-share and small-ratio values are not scaled — confirmed

They are separated by the magnitude rule alone, with no special-casing anywhere. AAPL's facts
section puts `DividendsPerShare`, `DividendsPerShare_TTM`, `EPS_QUARTERLY_CALC` and `EPS_TTM_CALC` in
`ratio` (column maxima of 0.26, 1.05, 4.5, 8.8) while `Revenue`, `CashAndEquivalents` and
`LongTermDebt` go `absolute`. A P/E of `35.5284` and `debt` of `82.30B` coexist in the snapshot,
decided one value at a time.

---

## 2. Step 2 — the design

### 2.1 The function

```ts
formatCell(value: number | null, kind: CellFormat): string
```

with `CellFormat = "percent" | "absolute" | "ratio" | "raw"` and two deciders:

```ts
columnFormat(byId, concept, values, valueColumn = "value"): CellFormat   // app.py:371 -- per column
valueFormat (byId, concept, value,  valueColumn = "value"): CellFormat   // app.py:487 -- per value
```

`raw` is not one of `format_for_display`'s branches. It is the **quality-flag** section, which the
reference formats somewhere else entirely — `render_flag_section` (app.py:454) does
`shown.astype("Float64").astype("string")` — and which item 18 owns. Giving it a name in the type
keeps it from drifting into the other three by accident; a flag that is off still reads `0`, not
`0.0000`.

### 2.2 Full precision is preserved by construction

`formatCell` takes a `number` and returns a `string`. It cannot write anywhere. `format.ts` does not
import `Pivot` and no function in it accepts one, so there is no expression anywhere in the codebase
that could put a display string back into the data. The CSV path calls `pivotToCsv(shown)` on the
same numeric `Pivot` the table renders from, with no formatting step between. §4.5 measures that
this held.

### 2.3 Where the percent/scale decision comes from

**Metrics and valuation: the registry's `percent` field**, read from the same `registry.json` the
chart path reads — via `metricsById(registry)`, built once from `registry.metrics`. There is no
second table of per-concept formatting anywhere in the frontend, which is the thing that would go
stale.

**Raw and derived facts: the magnitude rule, and the registry lookup is not merely unnecessary there
— it is the bug.** Facts columns are XBRL concept names, and ten of those names *do* resolve in the
registry (§1.2), every one of them to a growth-chart entry with `percent=True`. So the facts section
is not a case of "no registry entry, fall back": it is a case where the entries that exist describe a
*different frame's* column. `percentApplies` is given `valueColumn = "value"` and a growth entry
carries `"yoy_growth"`, so the ten resolve to `false` and the magnitude rule takes over. Naming it
here rather than re-deriving it silently is the point: without that test, `Revenue` in the facts
table becomes a percentage of itself.

### 2.4 Table sizing — the waste was horizontal, and it was measured

The operator's report was "fixed size regardless of content". Measured at a 1600px viewport, the
vertical half was already right — CRWV's 12-row facts table drew a 458px box, not a 578px one. **The
waste was entirely horizontal**, because `.table-scroll` was a plain block and therefore always 100%
of `.content`:

| ticker / section | table width | box width | **empty box** |
|---|---:|---:|---:|
| WAT / Current snapshot | 302px | 1,189px | **887px** |
| CRWV / Current snapshot | 339px | 1,189px | **850px** |
| CRWV / Quality flags | 651px | 1,189px | 538px |
| AAPL / Quality flags | 940px | 1,189px | 249px |
| AAPL / Valuation history | 1,161px | 1,189px | 28px |

**The fix is `width: max-content; max-width: 100%`** — the box sizes to the table, and anything wider
than the column hands its overflow back to the scroll it already had.

`scrollbar-gutter: stable` goes with it and is load-bearing rather than decoration: a `max-content`
box is exactly as wide as its content, so the moment a vertical scrollbar appears it eats into that
width and a *horizontal* scrollbar appears under a table that fits perfectly well. Reserving the
gutter makes it part of what `max-content` measures. That is the whole of the 17px residual in §4.4.

**The height cap stays, and is raised from 32rem to 36rem.** Measured before deciding, as the brief
asked: the largest real case is WAT with "Show all periods", whose facts table is **3,257px** tall,
and five uncapped sections would produce a **~13,000px** page. So a cap is warranted. But 32rem
(576px) sat one pixel under the 577px a 16-row table needs, so the *default* view scrolled by a
single row for no reason; 36rem (648px) clears it. The cap now engages only when the reader has
explicitly asked for every period, or on the snapshot's 32–46 rows.

---

## 3. What was implemented, by file

| file | new? | what |
|---|---|---|
| `src/data/format.ts` | **new** | `ABSOLUTE_THRESHOLD`, `formatAbsolute`, `formatRatio`, `percentApplies`, `columnFormat`, `valueFormat`, `formatCell`, `metricsById`, and the exact fixed-point rounder |
| `src/data/DataTable.tsx` | edited | takes `formats: CellFormat[]`; `PairTable`'s rows carry their own `format`. The `String(value)` cell is gone |
| `src/data/DataTab.tsx` | edited | builds `byId` from the registry, computes each section's column formats from the **shown** rows, and the snapshot's per value |
| `src/data/pivot.ts` | edited | `columnMagnitudes` — one column's values with `Infinity` folded back in for the magnitude scan (§4.2) |
| `src/data/csv.ts` | edited | one expression: `csvNumber` keeps the sign of `-0` (§4.6) |
| `src/data/data-tab.css` | edited | `width: max-content` / `max-width: 100%` / `scrollbar-gutter: stable` on `.table-scroll`, cap 32rem → 36rem |
| `scripts/check-table-format.mjs` | **new** | the standing check (§5) |

`App.tsx` was not opened. Neither were the chart builders, `panel.ts`, `grid.ts`, `mean.ts`, the
pipeline or the export.

### The one thing worth reading the code for: matching Python's rounding

Neither obvious approach works, and both were measured over 120,022 real values plus every
`value / cutoff` quotient they produce:

| approach | mismatches vs Python | why |
|---|---:|---|
| `Number.toFixed(n)` | **24** | rounds the exact binary value — correct — but breaks a tie *away from zero* where Python breaks it *to even*. `0.125` is exactly representable: Python writes `0.12`, `toFixed(2)` writes `0.13`. Also drops the sign of `-0` |
| `Intl.NumberFormat` with `roundingMode: "halfEven"` | **363** | worse: it rounds the number's *shortest decimal representation*, not its value. The double nearest `2.675` is `2.67499999999999982…`, so Python writes `2.67` and Intl, seeing `"2.675"`, writes `2.68` |

So `fixed()` does the rounding exactly. Every finite double is `m × 2^e` for integers `m` and `e`, so
`value × 10^digits` is the exact rational `m × 10^digits / 2^-e`; BigInt division with the remainder
compared against half the divisor decides the last digit with no floating point in the path at all.
**1,080,090 strings, 0 differences** (§4.1).

---

## 4. Step 4 — verification

### 4.1 The formatter itself, against `_format_absolute` and `_format_ratio`

360,030 values — every finite value sampled from all four frames, every `value / 1e12 … 1e3`
quotient, every `value × 100`, plus the tie and boundary cases (`0.125`, `2.675`, `999.995`, `-0.0`,
`5e-324`, `Number.MAX_VALUE`) — through all three functions:

| | |
|---|---:|
| strings compared | **1,080,090** |
| **mismatches** | **0** |

The first run had exactly one, `Number.MAX_VALUE × 100`, where Python's float arithmetic overflows to
`inf` and BigInt does not. Unreachable on real data by 296 orders of magnitude, and closed anyway —
one unexplained difference is worth two lines.

### 4.2 Every displayed string, against `format_for_display` — all 609 tickers

The reference generator imports `app.py` and calls **its own** `pivot_ticker`, `format_for_display`,
`is_quality_flag`, `fact_is_derived` and `order_fact_columns`. The comparer imports the **shipped**
`load.ts`, `pivot.ts`, `format.ts` and `csv.ts` and renders each section the way `DataTab` does.

Per ticker: the facts section under all three filter settings, metrics, valuation — each at **both**
period settings (16 and all, because the treatment can move between them) — and the snapshot per
value.

| | |
|---|---:|
| tickers | **609** |
| display strings compared | **4,390,657** |
| **mismatches** | **0** |
| ±inf cells excluded (documented divergence) | 44 |

**This check found a real defect on its first run: 233 failures, all CEG.** CEG's
`EPS_QUARTERLY_CALC` and `EPS_TTM_CALC` contain ±inf. The reference reads the **parquet**, which
still holds those infinities, so `column.abs().max()` is infinite and the whole column goes
`absolute` — `9.62`. The export writes `null` plus a sidecar, so this side saw a finite maximum of
11.9, chose `ratio`, and printed `9.6250`. Not a rounding bug: **the wrong rule for the entire
column**, and only visible because the comparison was against real tables rather than sampled values.

Fixed at the source with `columnMagnitudes` (`pivot.ts`), which folds the sidecar back in for the
magnitude scan only. The cell is still drawn as an infinity and the CSV still writes `inf`; what
changed is which rule the column's *finite* values print under — which is what the reference does.

### 4.3 Percent and scale are not applied to each other

The brief asked for a table carrying both. Measured across all 609 tickers, exactly **one ticker's
metrics section carries all three treatments at once** — AUR — and one valuation section does —
DDOG. AUR's newest period:

| concept | treatment | rendered |
|---|---|---|
| `roe` | percent | `-46.08%` |
| `operating_margin` | percent | `-19400.00%` |
| `fcf_margin_quarterly` | **absolute** | `-128.00` |
| `operating_margin_quarterly` | **absolute** | `-133.00` |
| `effective_tax_rate` | ratio | *(empty — no value)* |
| `rotce` | ratio | *(empty)* |

The two `*_quarterly` columns are `absolute` for the §4.2 reason — their columns contain −inf — and
they match the reference exactly. AAPL's metrics table shows the ordinary case: `roe` at `119.91%`
next to `debt_to_equity` at `0.7654`, both from the registry's flag, in the same table. DDOG's
valuation puts `ev_ebitda` at `1.24K` next to `pe_ratio` at `544.0910`.

### 4.4 The rendered DOM, not just the module

The module could be right and the component wire it up wrongly, so the strings were read back out of
a real browser and compared against the same reference:

| | |
|---|---:|
| tickers | AAPL, JPM, AUR, DDOG, CEG, CRWV, WAT |
| DOM cells compared | **6,107** |
| **mismatches** | **0** |

### 4.5 The underlying data is untouched

Two checks, because "the values are fine" and "the CSV reads them" are different claims:

1. **Item 9's element-wise harness, re-run unchanged**: 609 tickers, **3,727,478 checks**,
   1,863,398 values + 470,565 nulls + 44 infinities — identical to the item-9 report, including the
   same two known notation-only CSV differences (FDX, MDT). The pivot and the data path did not move.
2. **Every CSV field re-parsed**: **105,160 of 105,160** round-trip to the exact double the pivot
   holds. Nothing formatted reaches the export path.

### 4.6 The second defect this cycle's checks found

`csvNumber` wrote `0.0` for a negative zero, where `repr(-0.0)` writes `-0.0`, because `String(-0)`
is `"0"`. There is **exactly one** such value in the whole export — `MAS`'s `operating_leverage` at
2025-06-30 — and it is only a sign on a zero, so nothing numeric was lost. It is fixed (one
expression), because it was the only place `csvNumber` was not the reference and because a check
found it rather than a guess. Flagged for item 11 in §6.

### 4.7 Table sizing, measured

| ticker / section | box before | box after | table | waste after |
|---|---:|---:|---:|---:|
| WAT / Current snapshot | 1,189px | **319px** | 302px | 17px |
| CRWV / Current snapshot | 1,189px | **356px** | 339px | 17px |
| CRWV / Quality flags | 1,189px | **668px** | 651px | 17px |
| AAPL / Quality flags | 1,189px | **957px** | 940px | 17px |
| AAPL / Raw & derived facts | 1,189px | 1,191px | 5,382px | scrolls |

The 17px is the reserved scrollbar gutter plus the 2px border — the price of §2.3's fix, and the
reason the snapshot scrolls vertically without also acquiring a spurious horizontal scrollbar.

Heights: AAPL's 16-row sections are **579px** and no longer scroll (they were 578px against a 576px
cap, scrolling by one row). WAT with "Show all periods" caps at 650px and scrolls, page height
4,638px against 4,278px before — the cost of raising the cap, and the alternative was ~13,000px.

### 4.8 The chart-width fix and the three charts

| check | result |
|---|---|
| `scripts/check-chart-width.mjs` | **24/24** chart renders fill their container |
| item-8 sweep, 41 tickers × 24 profiles, 3,936 figures, 213,205 points | sha256 `1987837d155d3adfc9252ccdf2406bab502dd555324fd14d113432e067f38e8a` — **unchanged from the standing baseline** |

`App.tsx` was not opened this cycle, and the width check is what proves it.

### 4.9 Build

`npx tsc -b`, `npx eslint .`, `npx vite build` — clean. `git status` shows changes only inside
`frontend/`, plus the operator's own `task_new.md` and the reports. No scratch files left behind; the
dev server and headless browser were stopped and confirmed down.

---

## 5. The standing check, verified by failing

`scripts/check-table-format.mjs`, alongside the previous cycle's width check and for the same reason:
the harness that actually proves this correct needs Python, pandas and the parquet export, and cannot
run from `frontend/`. This one can.

It asserts **shape, not value** — every cell of the four numeric sections must match one of
`format_for_display`'s three outputs (`-1,234.56K`, `-12.34%`, `-1.2345`) or be one of the three
non-values the table draws deliberately (empty, `—`, `∞`).

```
APP_URL=http://localhost:5187 node scripts/check-table-format.mjs
```

**Verified by failing**, per the width check's precedent:

| tree | result |
|---|---|
| `formatCell` reverted to item 9's `String(value)` | **1,287 / 6,107** — 4,820 failures, the first being `LongTermDebt: "82300000000"`, the operator's exact report |
| current | **6,107 / 6,107**, exit 0 |

Its limit is stated in the file: shape cannot see the wrong *rule* applied to a whole column, which
is the defect §4.2 caught. That is why this is the complement to the Python comparison, not a
replacement — the same relationship the width check has to the item-8 harness.

---

## 6. What item 11 should know about this boundary

1. **The display path cannot reach the export path, structurally.** `format.ts` neither imports
   `Pivot` nor accepts one; `formatCell` takes a number and returns a string. `pivotToCsv` reads the
   same numeric `Pivot` the table renders from. Item 11 can add copy blocks against that `Pivot`
   without going near formatting.
2. **One expression in `csv.ts` was touched** — `csvNumber` now keeps the sign of `-0` (§4.6). That
   is item 11's file; it was a one-character correctness fix surfaced by this cycle's check, not the
   start of item 11's scope.
3. **The two known CSV differences from item 9 are unchanged and still item 11's**: Python switches
   to exponent notation below `1e-4` and JavaScript below `1e-7`, so 109 of the export's 1,888,605
   finite values are written in a different notation (same double, no precision lost). FDX and MDT
   are the two tickers where this shows in a facts CSV.
4. **±inf is written `inf` / `-inf`** in the CSV, matching the parquet and Streamlit's own download,
   while the table draws `∞`. Item 11 may want to revisit that; it is a decision, not an oversight.
5. **The copy block will need `format_for_display`'s sibling decision.** app.py's copy block is
   `to_csv_text` on the numeric frame (app.py:389) — *not* formatted. Building it from the display
   strings is the failure mode inventory §3.4 names by hand.

---

## 7. What to re-check by hand

The machine checks cover every string against the reference, so what is left is judgement:

1. **Whether the reference's own rules are what you want.** They are reproduced exactly, including
   the parts that look wrong: `days_since_last_filing` renders `55.0000`, a boolean-ish
   `avg_pe_5y_diverges` renders `0.0000`, and `effective_tax_rate` renders `0.1730` rather than
   `17.30%` because it has no registry entry. Changing any of those changes both apps and is a
   pipeline-side decision (a registry entry, or a `percent` flag), not a frontend one.
2. **The table widths at your own window size.** `max-content` means a narrow table is now as wide as
   its widest cell, so the boxes are ragged down the page where they used to be flush. That is the
   intended trade and it is worth seeing before it is settled.
