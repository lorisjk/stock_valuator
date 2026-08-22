# The per-ticker JSON export

**Date:** 2026-08-22
**Touched:** `main.py` (the per-ticker export, its wiring into `export_for_app`, one parameter on
`_write_json_atomic`, schema bump), `.github/scripts/validate_export.py` (new checks),
`MDs/bugfixes_opdate_history.md`.
**`config.py`, `figures.py` and `app.py` are unmodified** — confirmed by an empty
`git diff HEAD -- config.py figures.py app.py`.

The six parquet frames are 22.3 MB on disk and **309 MB as JSON**, which no browser can be handed.
The export now also writes **1,218 per-ticker files, 140.5 MB raw / 21.7 MB gzipped**, and one
ticker's complete payload is **230.7 kB raw / 34.9 kB gzipped**.

---

## 1. Step 1 — the shape, each decision on a number

### 1.1 One file per ticker, or one per frame? — **two**

The inventory proposed five (`facts`, `metrics`, `valuation`, `growth`, `snapshot`). Measured over
all 609 tickers, the totals are indistinguishable — **151.0 MB in one file each versus 150.9 MB in
five** — so this is not a size question at all. It is a question of what a view has to fetch before
it can paint.

| frame | raw / ticker | gzip / ticker | read by |
|---|---:|---:|---|
| `facts_full` | 142.7 kB | **20.9 kB** | Raw Facts, Data — 2 of 6 tabs |
| `metrics_long` | 45.7 kB | 6.5 kB | Fundamentals, Data, Comparison |
| `valuation_history` | 24.7 kB | 3.7 kB | Valuation, Data, Comparison |
| `facts_growth` | 19.4 kB | 3.5 kB | Growth, Comparison |
| `current_snapshot` | 1.9 kB | 0.6 kB | Valuation, Data |

**`facts_full` is 62% of the payload and the only frame worth splitting off.** The other four
together are **14.0 kB gzipped** — separating them would triple the file count to save under 10 kB
on a first paint, and would turn one fetch into four for a Data tab that needs all of them anyway.

So: **`{TICKER}.json`** carrying the four chart frames, and **`{TICKER}.facts.json`** carrying
`facts_full`. **1,218 files.** The split earns its keep three more times:

- a **Comparison** view never needs `facts_full` — `concept_source` routes only to
  fundamentals / valuation / growth — so the core file *is* the comparison payload (§2);
- on a night without new filings, **`facts_full` does not change at all**, so 62% of the bytes
  cost the deploy branch nothing (§5);
- all four chart tabs are served by one **14 kB** fetch, and switching between them costs nothing.

### 1.2 Orientation — column-major, and the smaller-looking option was worse

Measured on AAPL's slice, with the constant `ticker` column dropped:

| orientation | raw | gzip |
|---|---:|---:|
| records — `[{concept: …, value: …}, …]` | 580 kB | — |
| **`{columns, data}` — column-major** | **324 kB** | **52.3 kB** |
| nested by concept | 236 kB | 54.3 kB |
| nested by concept + shared date table | 191 kB | 53.8 kB |

Records lose immediately: repeating four key names on every row costs 256 kB. The interesting
result is the other end — **the nesting that is 1.7× smaller raw is 4% *larger* gzipped**, because
gzip already removes the repetition the nesting was hand-removing. Anything served over HTTP is
served compressed, so the raw column is the wrong one to optimise.

Two further reasons the nested forms were rejected:

1. **They cannot reproduce the parquet's row order.** `valuation_history` is stored date-major:
   352,622 contiguous blocks for 5,610 distinct (ticker, concept) groups — almost fully
   interleaved. Concept-major would have to re-sort, and **110 groups across the frames are not
   even ascending in `end`**, so no sort recovers the original.
2. Column-major reconstructs the slice row for row with no ordering assumption at all, which is
   what makes the Step 4 equality check possible.

### 1.3 Does the parquet export stay? — **yes, both are written**

Streamlit reads parquet and will keep running for months. `export_for_app` writes the frames, the
registry and the per-ticker JSON **in one call, from the same in-memory frames**, so they cannot
describe different runs — the per-ticker files are sliced from exactly the objects that were just
written to parquet. `meta.json` is still written last and now covers all three populations.

### 1.4 Numeric precision — full, and checked as text

Python's `json` serialises a float with `repr()`, which since 3.1 is the **shortest string that
round-trips to the same double**. So the JSON carries the value, not a rendering of it — the data
tab's display-versus-export distinction is preserved by construction, since nothing here formats
anything.

Verified two ways: `assert_frame_equal(..., check_exact=True)` on every slice (§4.1), and, because
that could in principle pass on a coincidence, a direct comparison of `repr(exported)` against
`repr(original)` for **463,069 float values across 80 tickers — 0 differ**.

**The one thing JSON cannot carry is ±inf, and the data has 44.** `Infinity` is not valid JSON;
Python emits it by default and `JSON.parse` rejects it, so a naive export would have produced
files no browser could read. Where they occur:

| frame | concepts | count |
|---|---|---:|
| `facts_full` | `EPS_QUARTERLY_CALC` (13), `EPS_TTM_CALC` (9) | 22 |
| `metrics_long` | `operating_margin_quarterly` (11), `fcf_margin_quarterly` (11) | 22 |

All are divisions by zero, on 10 tickers (CEG, CRWD, ICE, PINS, EXE, FANG, DDOG, AUR, APLD, QRVO).
The value array gets `null` there — which is what a chart would draw anyway — and the true value
goes in a `nonfinite` sidecar keyed by row index:

```json
"nonfinite": {"value": {"178": "-Infinity"}}
```

A consumer that ignores the sidecar sees a gap; one that reads it recovers the value exactly. The
parquet still holds the infinities, so **Streamlit is unaffected**.

### 1.5 Dates — `YYYY-MM-DD`

Every `end` value in all five frames is midnight — **0 rows carry a time component** — because
these are period ends, not timestamps. The bare date is therefore lossless and a third the width of
a full ISO stamp. Formatted once per frame with `.dt.strftime`, not per ticker, which is where the
time would otherwise go.

Verified on all **2,344,025** exported values: every one parses back and equals the original
`datetime64`, min `2005-03-31` and max `2026-08-21` included (§4.3).

### 1.6 Nulls — `null`, in place

A null is the difference between a coverage gap and a zero, and there are a lot of them:
`valuation_history` is 33.5% null, `facts_growth` 20.4%, `metrics_long` 9.2%. They are never
dropped, coerced or filled — the column keeps its full length and carries `null` at that position,
so row *n* of every column still belongs to row *n* of the slice.

Checked as a total across the whole export: **262,724 JSON nulls = 262,680 parquet NaN + 44
non-finite**. The two object columns (`ttm_source`, `ffo_gains_source`) are handled the same way;
`ffo_gains_source` is null on 1,151,118 of 1,152,894 rows.

### 1.7 The file format

```json
{"schema": 1,
 "ticker": "AAPL",
 "frames": {"metrics_long": {"columns": ["end", "value", "concept"],
                             "data": [[…], […], […]],
                             "nonfinite": {"value": {"178": "-Infinity"}}}}}
```

`columns` is the parquet's column list minus `ticker`, in the parquet's order. `nonfinite` is
omitted when empty. **No timestamp inside**, deliberately — see §5.

Written **compact** (`separators=(",", ":")`), unlike the registry files, which are indented
because people read them. Indenting these instead costs **63 MB per run** (214 MB against 140 MB)
on a branch that keeps every night's commit.

---

## 2. Step 2 — the comparison axis: **not built, and here is the number**

The Comparison view needs one concept across N tickers, which the per-ticker shape serves with N
fetches. The alternative is a concept-major file per concept.

| | gzipped |
|---|---:|
| concept-major file, mean over the 13 valuation concepts | **186 kB** |
| largest (`pe_ratio`) | 327 kB |
| one ticker's core file | **14.0 kB** |
| `figures.SUGGESTED_MAX_COMPARISON_TICKERS` | **3** |
| three core files | **42 kB** |

**Break-even is 13 tickers** — more than four times the suggested maximum, and the app's own
caption tells the user that three "stay comfortably readable". Below that, per-ticker fetches win
outright, and they win by more than the arithmetic suggests: the comparison tickers are the ones
the user has been browsing, so their core files are already in cache, while a concept file is a
cold 186 kB fetched again for every concept they switch to.

The cost side is not free either: 13 concept files would add **12.3 MB to every nightly commit**,
and a second axis is a second thing that can silently disagree with the first.

**Verdict: not built.** If the comparison view ever grows past ~13 tickers, the number to re-check
is in this table.

---

## 3. Step 3 — what was implemented, and where

All in `main.py`, in the block above `export_for_app`:

| name | what it does |
|---|---|
| `TICKER_EXPORT_SCHEMA = 1`, `TICKER_EXPORT_SUBDIR = "tickers"` | the contract's version and location |
| `TICKER_CORE_FRAMES`, `TICKER_FACTS_FRAMES` | which frame goes in which file |
| `_columnar(sub) -> dict` | one slice as `{columns, data[, nonfinite]}` |
| `_ticker_slices(frame) -> dict` | `{ticker: slice}` with `end` already ISO, formatted once per frame |
| `export_per_ticker(frames, tickers, out_dir) -> dict` | writes both files per ticker, returns the inventory |

`_write_json_atomic` gained one parameter, `indent`, defaulting to `1` so the registry export is
unchanged; the per-ticker files pass `indent=None`.

`export_for_app` calls `export_per_ticker` **after the frames and the registry, before
`meta.json`** — the invariant that `meta.json`'s presence means the whole export is on disk now
covers all three populations. The frames handed to it are the same objects written to parquet in
the same call.

`meta.json` gains a `per_ticker` block, in the registry block's shape — named counts, not a "rows"
count for something that has no rows:

```json
"per_ticker": {"schema": 1, "directory": "tickers", "tickers": 609, "files": 1218,
               "bytes": 140501901, "core_frames": [...], "facts_frames": ["facts_full"]}
```

`APP_EXPORT_SCHEMA` goes **3 → 4**; `validate_export.py`'s `EXPECTED_SCHEMA` moves with it.

### The validator, and the check that was thrown away

Row-count floors are right here in a way they were not for the registry — per-ticker files **do**
grow with new quarters — but a floor per file across 1,218 files is not a table anyone reads. What
was added:

- **one population floor** on total bytes (90% of a measured 140,501,901);
- **a per-file minimum** of 4,096 B, half the smallest measured file, because a present-but-empty
  file is exactly what a population total hides;
- **exact file coverage**: two files per universe ticker, none missing, none for a ticker outside
  the universe;
- **every file opened** — parses, right schema, right ticker, all five frames present, column names
  equal to the parquet's, and every column's length equal to that ticker's parquet row count. That
  last one is the only check that catches a misalignment;
- **row accounting**: exported rows plus rows belonging to tickers outside the universe must equal
  the parquet's total.

**A sampled version of the deep check was written first and discarded.** It opened 8 tickers spread
across the alphabet, and it **passed 8 of 12 deliberate corruptions** — a wrong ticker name, a
missing frame, a one-row misalignment, a corrupt file — because none of them happened to land on a
sampled ticker. Opening all 1,218 costs **1.9 s** (the whole validator runs in 3.6 s) against a
~40 min pipeline run. That is not a trade worth making, and the rejected sample is recorded in the
script's comments so it does not get reinvented.

---

## 4. Step 4 — verification

**22 checks, all passing**, plus **12 negative tests on the validator, all rejecting.** Written
into a scratch directory; `data/app/` was left exactly as published.

### 4.1 The decisive check: round-trip equality, every slice

Not the sample the brief asked for — **all 609 tickers × 5 frames = 3,045 slices**. Each JSON block
was reconstructed into a DataFrame (applying the frame's dtypes, re-inserting `ticker`, folding the
`nonfinite` sidecar back in) and compared with
`assert_frame_equal(check_exact=True, check_dtype=True)`.

**3,045 / 3,045 element-wise equal** — same rows in the same order, same columns, same values
bit-for-bit, same nulls in the same positions, same dtypes.

The edge cases the brief named are all in the universe and all passed:

| ticker | why it was named |
|---|---|
| AAPL | `standard` |
| JPM | `financial` |
| O | `reit` |
| V, STZ, ERIE | no per-share data (`SharesOutstanding` empty) |
| BKR | thin per-share data |
| CRWV, FIG | short history |

### 4.2 Coverage

| check | result |
|---|---|
| exactly two files per universe ticker | ✓ 1,218 for 609 |
| no file for a ticker outside the universe | ✓ 0 strays |
| every ticker has rows in all five frames | ✓ — no ticker needed a file omitted |
| every file names its own ticker and `schema: 1` | ✓ |
| no `.tmp` files left behind | ✓ |

**One finding.** `current_snapshot.parquet` holds **4 rows for EA** — `price`,
`shares_outstanding`, `market_cap`, `shares_source_is_edgar` — but EA is not in the universe (it
produced no metrics, valuation or growth; it was taken private, per the 2026-08-19 entry). Those 4
rows are therefore not exported, which is correct: the app's picker reads the universe, so a file
for EA could never be fetched. The validator asserts exactly this rather than assuming it — every
unexported row must belong to a ticker the universe does not list.

### 4.3 Dates, nulls, precision

| check | result |
|---|---|
| every exported date parses and equals the original `datetime64` | ✓ **2,344,025 values** |
| earliest and latest survive exactly | ✓ 2005-03-31 … 2026-08-21 |
| every date is a bare 10-character `YYYY-MM-DD`; 0 timestamps in the source | ✓ |
| nulls survive in place, not dropped or filled | ✓ EXE: 584 nulls of 770 valuation rows, positions preserved |
| null totals across the whole export | ✓ 262,724 = 262,680 NaN + 44 non-finite |
| ±inf carried in the sidecar, not lost | ✓ 44 values across 10 (ticker, frame) slices |
| no bare `Infinity` / `NaN` token in any file | ✓ — `JSON.parse` would reject one |
| float `repr` byte-identical after the round-trip | ✓ 463,069 values, 0 differ |

### 4.4 Nothing else changed

- **`config.py`, `figures.py`, `app.py`: empty `git diff HEAD`.**
- All six parquet frames **content-identical** (`DataFrame.equals`) to the published export.
- **Byte-identical across two runs of the new code**: 6/6 parquet files and **1,218/1,218 JSON
  files**.

*The caveat the registry report recorded still applies and is worth restating separately, because
the two claims are different.* Content equality holds against the published `data/app/`. Byte
equality holds **within one environment**: the published parquet files were written by CI with
`parquet-cpp-arrow 25.0.1` and this machine has `pyarrow 24.0.0`, so a local rewrite differs
byte-wise for a reason that has nothing to do with this change. The JSON files have no such
dependency — they are byte-identical across runs by construction, which is the property §5 rests
on.

### 4.5 The validator, exercised in both directions

Against the freshly written export: **38 checks, ACCEPTED, exit 0, 3.6 s.**

Then 12 mutations, all rejected:

| mutation | rejected by |
|---|---|
| the whole `tickers/` directory gone | `tickers/ present` |
| a ticker loses its core file / its facts file | `per-ticker files`, `no ticker missing a file`, `every per-ticker file` |
| a file for a ticker not in the universe | `no file for a ticker outside the universe` |
| a file truncated to a stub | `no truncated per-ticker file` |
| 400 files truncated | `per-ticker bytes`, `no truncated per-ticker file`, `every per-ticker file` |
| a per-ticker schema mismatch | `every per-ticker file` |
| a file names the wrong ticker | `every per-ticker file` |
| a frame block missing | `every per-ticker file` |
| one column one row short (misalignment) | `every per-ticker file`, `per-ticker rows account for the parquet` |
| column names not matching the parquet | `every per-ticker file` |
| a file corrupt | `every per-ticker file` |

**12 / 12** — against 6/12 for the sampled version of the same checks.

---

## 5. Step 5 — the totals, and what they cost the nightly

### On disk

| | files | raw | gzipped |
|---|---:|---:|---:|
| `{TICKER}.json` (core) | 609 | 53.6 MB | 8.5 MB |
| `{TICKER}.facts.json` | 609 | 86.9 MB | 12.7 MB |
| **per-ticker total** | **1,218** | **140.5 MB** | **21.7 MB** |
| existing parquet, for scale | 6 | 22.3 MB | — |

Per ticker, mean: **230.7 kB raw, 34.9 kB gzipped** (core 88.0 / 14.0, facts 142.7 / 20.9).
AAPL, a long-history mega-cap, is above it: **116.0 kB / 20.3 kB** core and **186.0 kB / 30.1 kB**
facts. The inventory's estimate was ~650 kB raw / ~120 kB gzipped for a ticker; the column-major
shape and the dropped `ticker` column account for the difference.

### Runtime

`export_per_ticker` alone: **14.2 s**. `export_for_app` end to end: **45.8 s**, against a measured
~40 min pipeline run — **under 2%**.

### The deploy branch

The per-ticker files carry **no timestamp**, so a ticker whose data did not change produces a
byte-identical file and git stores nothing new for it. Measured over five simulated **price-only**
nights (`current_snapshot` values moved for every ticker, `valuation_history`'s newest date per
(ticker, concept) moved, the EDGAR side held fixed), committing into a real repository with
incremental `git gc`:

| population | files changed per night | packed growth per night |
|---|---:|---:|
| parquet + `meta.json` (today) | 3 | **+0.23 MB** |
| per-ticker JSON | **609** — and **0 facts files** | **+6.9 MB** |
| everything together | 613 | +7.0 MB |

**The facts files, 62% of the bytes, do not change on a night without filings.** They change when a
ticker files, which for any one ticker is once a quarter, so their contribution averages out to a
fraction of the core files'.

So the branch's nightly growth goes from **~0.23 MB to ~7.0 MB, about 210 MB a month**, flattened
by the same manual orphan reset the workflow already schedules roughly monthly. Two things worth
recording alongside that:

- **The workflow's standing "~18.8 MB of parquet a night, ~560 MB a month" is pessimistic.** It
  assumes the whole directory is new each night; git dedupes the four parquet files that did not
  change, and the measured cost on a price-only night is 0.23 MB. A filing-heavy night is larger.
- An aggressive repack collapses the JSON almost completely. In a separate two-night trial, the
  JSON population's loose objects came to 21.8 MB after night one and 31.7 MB after night two;
  `git gc --aggressive` then packed the whole repository to **21.9 MB** — the second night's 9.9 MB
  of loose objects delta-compressed down to roughly 0.1 MB. JSON delta-compresses; parquet, being
  already compressed, does not. The monthly reset is therefore worth more now than it was before.

---

## 6. Deliberately omitted, with reasons

| omitted | why |
|---|---|
| **`universe.json`** | Not needed. `registry.json` already carries `ticker_profile` for all 609 tickers, and `ticker` + `profile` are the **only two of `universe.parquet`'s five columns the app reads** (app.py:851–852). The ticker list is already available as JSON. |
| **`by-concept/{concept}.json`** | §2 — measured, break-even is 13 tickers against a suggested maximum of 3. |
| **`n_metrics` / `n_valuation` / `n_growth`** | Exported in `universe.parquet` and read by nothing, per the inventory's §2.7. Copying dead columns into a new contract is how they become permanent. |
| **A `facts_growth` block in `.facts.json`** | It belongs to the Growth chart, not the Raw Facts tab, and it is 3.5 kB gzipped. It stays in the core file. |
| **Splitting the four core frames further** | §1.1 — under 10 kB gzipped saved per view, at 3× the file count. |
| **A timestamp inside each per-ticker file** | It would make all 1,218 files differ every night, which is the entire cost the design avoids. `meta.json` carries the run's time, once. |
| **Gzipping the files at export time** | The host does this — GitHub Pages, any CDN, Streamlit's own server. Pre-compressing would double the file count and pin a compression choice into the repository. |
| **Removing anything from the parquet export** | Explicitly out of scope, and Streamlit reads it. Both are written from the same frames in the same call. |

---

## 7. Noticed, not acted on

- **EA has 4 `current_snapshot` rows and no universe entry** (§4.2) — including a live price of
  $209.70, which is odd for a company that filed `15-12G` on 2026-08-14. Recorded; the SATS
  decision from earlier cycles still governs it.
- **`_write_json_atomic`'s `indent` default stays `1`**, so the registry files are unchanged. If
  the registry ever grows past a size where a human stops reading it, that default is the knob.
- The `nonfinite` sidecar's keys are strings because JSON object keys must be. A consumer has to
  `parseInt` them. An array of `[index, value]` pairs would avoid that; it was not worth diverging
  from the obvious shape for 44 values.
- **`validate_export.py`'s `BASELINE` still reads 501 tickers** while the universe is 610 — carried
  forward from the previous report, still not this task's to change.

No scratch scripts were left behind.
