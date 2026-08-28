# CSV downloads and copy blocks — item 11

All five sections download, four of them copy, and every byte is now **identical to the reference's
own output** — including the 109 values whose notation item 9 measured, flagged and left for this
item.

**14,007 CSV comparisons across all 609 tickers, 0 differences of any kind.** 2,399,488 numeric
fields exact, **544,252 nulls all rendered as empty fields**, 54 infinities. Verified again in a real
browser by intercepting the actual download blobs and reading the actual clipboard.

Two corrections to the brief's premises and one bug I introduced and caught are in §2 and §5.5.

---

## 1. Step 1 — the reference

### 1.1 What each section offers

| section | download | copy block | source |
|---|---|---|---|
| Raw & derived facts | ✓ `{ticker}_facts.csv` | ✓ 8 periods | app.py:426, 431 |
| Calculated metrics | ✓ `{ticker}_metrics.csv` | ✓ 8 periods | same helper |
| **Quality flags** | ✓ `{ticker}_flags.csv`, **inside the "Per-period flag values" expander** | **none** | app.py:459 |
| Valuation history | ✓ `{ticker}_valuation.csv` | ✓ 8 periods | same helper |
| Current snapshot | ✓ `{ticker}_snapshot.csv` | ✓ **whole table** | app.py:496, 499 |

So it does vary by section, in both directions: the flags section is the only one with **no copy
block at all**, and the snapshot is the only one whose copy block is **not truncated**.

### 1.2 The copy block's format — CSV text, same producer as the download

`to_csv_text` (app.py:385) for both, rendered with `st.code(text, language="text")` (app.py:433).
Not Markdown, not a fenced table, not a different serialisation. "LLM-friendly" describes the
delivery — a monospaced block you select and paste — not a separate format. The one thing that
differs from the download is the **row count**, never the content of a row.

### 1.3 The copy block's limit — 8 periods, and from the *whole* pivot

```python
copied = wide.head(copy_periods)          # app.py:431, copy_periods = DEFAULT_COPY_PERIODS = 8
```

Two details that are easy to miss and both matter:

- **`DEFAULT_COPY_PERIODS = 8` against `DEFAULT_TABLE_PERIODS = 16`** (app.py:47-48). The comment
  there is the reasoning: *"the copy block is deliberately smaller, because a full facts table pasted
  into a chat is already near the practical limit and the recent periods are what a question is
  usually about."*
- **It reads `wide`, not `shown`.** The download takes `wide.head(periods)` where `periods` follows
  the "Show all periods" checkbox; the copy block takes `wide.head(8)` unconditionally. So the
  checkbox reaches the table and the download and **not** the copy block. That is a deliberate
  asymmetry, and §5.4 shows it reproduced.

The snapshot's copy block has no limit (app.py:499) because there is nothing to limit: one row per
concept, one constant `end`, no second period.

### 1.4 The filename convention

`f"{ticker}_{slug}.csv"` — app.py:427, and app.py:461/497 for the two hand-written ones. Ticker and
section slug, **no date**, no ISO stamp, no run identifier. Slugs: `facts`, `metrics`, `flags`,
`valuation`, `snapshot`.

### 1.5 What item 9 actually built — the brief's premise is off by four

The brief says *"Item 9 built a CSV download for one section as a byproduct."* It built **five**, one
per section, and its own report says so ("A download button per section **was** built"). All five
filenames already matched §1.4 exactly, and all five already took `head(periods)`. What item 9 did
*not* build was any copy block, which is the real gap this item fills.

---

## 2. Step 2 — verifying item 9's CSV before extending it

Not assumed correct because it existed. Three checks:

**Is the CSV still produced from the numbers, after item 10 put a formatting layer in between?**
Yes, and structurally rather than by inspection: `csv.ts` does not import `format.ts`, `format.ts`
does not import `Pivot` and no function in it accepts one, and `DataTab` passes `pivotToCsv` the same
numeric `Pivot` it passes the table. Item 10's own harness re-run here confirms it end to end —
**105,160 of 105,160 CSV fields round-trip to the exact double**.

**Is the precision right against the parquet?** Yes for values, **no for notation**. The first run of
this item's comparison found **19 differences across 34 tickers**, every one classified by the
harness itself as notation-only by re-parsing both sides. They are the 109 values item 9 measured:
Python's `repr` switches to exponent form below `1e-4`, JavaScript's `String` below `1e-7`, so
`1.4383458646616541e-05` was being written `0.000014383458646616541`. Same double, no precision lost,
**not byte-identical to the reference** — which item 9 explicitly handed to this item.

**Do the filenames and structure match?** Yes, all five, unchanged.

So this item inherited a CSV that was correct in value and wrong in spelling, and one that was
missing its copy block entirely. Both are fixed below.

---

## 3. Step 3 — design

### 3.1 One utility, five call sites

`pivotToCsv` already served four sections and `pairsToCsv` the snapshot. The snapshot **does** need
the second function, and minimally: it is a `concept,value` list rather than an `end` + concepts
grid, because item 9's design decision (following app.py:483) is that the snapshot's slice already
*is* the transposed view. The reference does the same thing — `table.to_csv` on a concept-indexed
frame rather than `to_csv_text` on a pivot — so the difference is the reference's, not an invention.
Both share `csvNumber`, so there is exactly one place a value becomes text.

What was **not** one thing before: the buttons. `Section` had one, and the flags and snapshot
sections had inline copies. All five now go through `SectionActions`, which is what makes the
guarantee checkable in one place — neither that component nor `csv.ts` imports `format.ts`, so a
section cannot hand the export path a display string because there is no display string in scope.

### 3.2 The copy block — CSV text, 8 periods, no opt-out

Format and truncation are the reference's (§1.2, §1.3): CSV text, `DEFAULT_COPY_PERIODS = 8`, taken
from the whole pivot so the "Show all periods" checkbox does not reach it.

**The brief suggests a "recent window with an opt-out" and the reference deliberately has none**, so
this is stated rather than quietly resolved: the opt-out already exists and it is the **Download**
button, which does follow the checkbox. Measured across all 609 tickers, that is the difference the
split is buying:

| | median | max |
|---|---:|---:|
| copy block (8 periods) — facts | 3,831 | **5,117** chars |
| copy block — metrics | 2,090 | 3,086 |
| copy block — valuation | 1,188 | 1,618 |
| copy block — snapshot (whole) | 1,229 | 1,447 |
| download, 16 periods — facts | 7,071 | 9,208 |
| **download, Show all periods — facts** | 26,634 | **36,969** |

The worst copy block in the universe is ~5.1 kB, roughly 1,300 tokens — a sane paste. The worst
download is 7× that, which is fine for a file and is exactly what the reference declines to put in a
code block. If a copy-everything affordance is wanted later it is one argument, but it would be a
divergence from the reference and is not made silently here.

**No copy block for the quality flags**, because the reference has none (app.py:459 offers a download
inside its expander and nothing else). Passing `copy={null}` states it in the code rather than
leaving its absence to be noticed, and that section is item 18's in any case.

### 3.3 Where the copy affordance lives

A **"Copy table" button** beside "Download CSV", using `navigator.clipboard.writeText`, with a
transient `role="status"` message: `Copied` on success, and on failure *"Clipboard unavailable — open
the block below and copy by hand"*.

The failure branch is not defensive padding. **`navigator.clipboard` does not exist outside a secure
context**, and this app is routinely served over plain http from a LAN address in development, where
the missing-API case is the normal case. `copyText` resolves `false` rather than throwing, and the
caller says what to do instead of claiming a success that did not happen.

The reference's own affordance — an expander holding the text — is kept as a `<details>` alongside
the button, carrying app.py:432's label verbatim (`Copy table — 8 periods, ~4,242 characters`). It
does two jobs: it shows what is about to be pasted, and it is what makes the clipboard-unavailable
message a real fallback rather than a dead end.

---

## 4. What was implemented, by file

| file | new? | what |
|---|---|---|
| `src/data/SectionActions.tsx` | **new** | the download button, the copy button, the disclosure and the status line — one component, five call sites |
| `src/data/csv.ts` | edited | `DEFAULT_COPY_PERIODS`, `copyText`, and `csvNumber` rewritten as Python's `repr` (§5.1) |
| `src/data/DataTab.tsx` | edited | each section's copy text (`headPeriods(pivot, 8)` from the whole pivot); the three inline button copies replaced by `SectionActions` |
| `src/data/data-tab.css` | edited | `.actions`, `.actions__status`, `.copy-block` and its `<pre>` — including the `min-width: 0` in §5.5 |

Nothing else was opened: not the pivot, not `format.ts`, not `App.tsx`, not the chart builders,
`panel.ts`, `grid.ts`, `mean.ts`, the pipeline or the export. `git status` confirms the change set is
those four files.

### `csvNumber` is now Python's `repr`

Three things had to be right, and `String(value)` is none of them:

1. **The digits** — `repr` is the shortest round-tripping string, which is exactly what
   `toExponential()` with no argument yields.
2. **The notation** — Python goes exponential when the decimal-point position satisfies
   `decpt <= -4 || decpt > 16`; JavaScript switches at `1e-7` and `1e21`. Confirmed against the
   reference at all four boundaries: `1e-4` → `0.0001`, `1e-5` → `1e-05`, `1e15` →
   `1000000000000000.0`, `1e16` → `1e+16`. The exponential form carries a signed, zero-padded,
   at-least-two-digit exponent and no forced `.0` on a single-digit mantissa.
3. **The trailing `.0` and the sign of `-0`** — `repr(0.0)` is `"0.0"`, `repr(-0.0)` is `"-0.0"`,
   and `String()` gives `"0"` for both.

---

## 5. Step 5 — verification

### 5.1 `csvNumber` against `repr`, on every value in the export

Not a sample: **every finite value in all four frames**, plus the boundary and tie cases.

| | |
|---|---:|
| values compared | **1,888,631** |
| **mismatches** | **0** |

### 5.2 All five CSVs and all four copy blocks, all 609 tickers

The reference generator imports `app.py` and calls its own `to_csv_text`, `pivot_ticker`,
`is_quality_flag` and `order_fact_columns`. The comparer imports the shipped `load.ts`, `pivot.ts`
and `csv.ts` and builds each section's text the way `DataTab` does — at **both** period settings for
the downloads, and at 8 periods for the copy blocks.

| | |
|---|---:|
| tickers | **609** |
| comparisons (download × 5 × 2 settings, copy × 5, filenames) | **14,007** |
| **real value differences** | **0** |
| **notation-only differences** | **0** *(19 before §4's fix)* |
| **file-name mismatches** | **0** |

Every field was also re-parsed against the pivot it came from:

| | |
|---|---:|
| numeric fields, exact against the stored double | **2,399,488** |
| **null fields rendered as an empty field** | **544,252 of 544,252** |
| ±inf fields written `inf` / `-inf` | 54 |

### 5.3 Nulls are empty, not `null`, `NaN` or `0`

That is the 544,252 above, and it is a positive count rather than an absence of failures: the audit
walks every cell the pivot says is null and asserts the CSV field is exactly `""`. A gap survives the
pivot (item 9), the display (item 10) and now the export.

### 5.4 The real browser: actual blobs, actual clipboard

Intercepting `URL.createObjectURL` and `HTMLAnchorElement.prototype.click` to capture what the
download buttons genuinely produce, and reading the clipboard back after clicking Copy — across
AAPL, JPM, O, BKR, CRWV, **V, STZ, ERIE** (the no-per-share-data tickers) :

| | |
|---|---:|
| download blobs intercepted | **40** |
| byte-mismatches against the reference | **0** |
| filenames wrong | **0 of 40** |
| copy-block checks (including "flags must have none") | **40** |
| wrong | **0** |

The clipboard readback needed `Browser.grantPermissions` — the `NotAllowedError` in the first run was
the *read*, not the write under test — and comes back with CRLF, because Windows normalises line
endings on the way onto the clipboard. The disclosure's text is compared **unnormalised** and matches
byte for byte, so what the app produced and what the clipboard received are both accounted for.

Sizes and labels, AAPL: facts `Copy table — 8 periods, ~4,242 characters`, metrics `~2,362`,
valuation `~1,583`, snapshot `Copy table — ~1,303 characters` (no period count, §1.3). Status reads
`Copied`.

**The copy block is invariant under "Show all periods"**, as §1.3 requires — AAPL's four copy blocks
are byte-identical with the checkbox off and on (4,242 / 2,362 / 1,583 / 1,303), while the downloads
move to 33,065 / 17,703 / 2,208 / 11,365 / 1,303.

### 5.5 A bug I introduced, caught, and fixed

The first screenshot of an open copy block showed a horizontal scrollbar across the whole page.
Measured: opening the copy blocks took the document's scroll width from **1,555px to 5,131px** at a
1,570px viewport.

`.copy-block` is a flex item, and a flex item defaults to `min-width: auto` — which refuses to shrink
below its content's min-content width. The `<pre>` inside carries `white-space: pre`, whose
min-content width is its **longest line**. So the disclosure grew to the width of the widest CSV row
and dragged the page with it. This is the same failure the shell's `.content { min-width: 0 }`
prevents one level up.

Fixed with `min-width: 0` on `.copy-block`; the `<pre>` keeps its own `overflow: auto`, so long lines
still scroll inside the block. **Verified by failing**, per the standing discipline: with the line
removed the page scrolls horizontally (1,555 → 5,131px), with it restored it does not, in both
states, at full width.

### 5.6 Nothing else moved

| check | result |
|---|---|
| `scripts/check-chart-width.mjs` | **24/24** chart renders fill their container |
| `scripts/check-table-format.mjs` (item 10's) | **6,107/6,107** cells carry a display format |
| item 10's display harness, re-run | 609 tickers, **4,390,657** strings, **0 failures** |
| item-8 chart sweep, 3,936 figures, 213,205 points | sha256 `1987837d155d3adfc9252ccdf2406bab502dd555324fd14d113432e067f38e8a` — **unchanged** |

`npx tsc -b`, `npx eslint .`, `npx vite build` — clean. `git status` shows four files, all inside
`frontend/`, plus the operator's own `task_new.md` and this report. No scratch files left behind; the
dev server and headless browser were stopped and confirmed down.

---

## 6. Notes for what comes next

- **The display/export split held under its first real load.** Item 10 built it so a cell's rendered
  string and its stored value were two different things reachable from the same place; this item
  exercised that for 14,007 CSVs and 40 real download blobs, and the numbers never once leaked into
  the strings or vice versa. The screenshot in the scratch pass shows it plainly: the table reads
  `0.7654` and `29.28%` while the copy block under it reads `0.7654389880952381` and
  `0.2927940568480987`.
- **`csvNumber` is now a general-purpose Python-`repr` implementation**, verified on 1,888,631
  values. Item 19's cadence markers and item 18's flag summary do not need it, but anything that ever
  has to serialise a float the way pandas does should call it rather than write a second one.
- **The quality-flag section still has no copy block**, deliberately (§3.2). If item 18 adds its
  summary table, that is the moment to decide whether the section deserves one — it would be a
  divergence from the reference either way, and worth making on purpose.
- **A copy-everything affordance is one argument away** (`headPeriods(pivot, periods)` instead of
  `DEFAULT_COPY_PERIODS`) if the 8-period bound turns out to be too tight in practice.

## 7. What to re-check by hand

**Click Copy table and paste it somewhere.** The clipboard was verified through the DevTools
Protocol with permissions granted, which is not quite the same as a browser you clicked yourself —
and if you run the app over http from a LAN address rather than localhost, the button will
deliberately tell you the clipboard is unavailable and point at the block below. That path is worth
seeing once, because it is the one a second machine on your network will get.
