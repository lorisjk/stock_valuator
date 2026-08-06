# Data Inspection Layer — Export Completion + App Data Tab

**Date:** 2026-08-06
**Touched:** `main.py` (export layer), `app.py` (pivot helper + data tab + one bug fix).
**`figures.py` and `config.py` are unmodified — SHA-256 before and after, not memory:**

```
6015CDE0…14CA89  figures.py   (identical before and after)
F588C13F…C0F89D  config.py    (identical before and after)
```

**184 verification checks, all passing** (39 export · 114 pivot/format/flags · 31 page + refresh).

---

## 1. Step 1.1 — the snapshot frame's actual shape

Measured on a real 8-ticker run, not assumed:

| property | value |
|---|---|
| shape | **292 × 4** |
| columns | `ticker`, `end`, `concept`, `value` |
| dtypes | `object`, **`datetime64[ns]`**, `object`, `float64` |
| **long or wide** | **long** — the identical schema to `metrics_long` and `valuation_history` |
| rows per ticker | **not one** — 24 to 41, one row per `(ticker, concept)`, verified unique |
| distinct concepts | 76 across 8 tickers |
| `end` | **a single constant value** (the as-of date), the same for every row |
| nulls | **zero** — `build_snapshot` ends with `dropna(subset=["value"])` |
| index | default `RangeIndex` |

Three consequences that shaped the rest of the work:

1. **`end` is not a period end.** It is the snapshot timestamp. There is no time series here and nothing to compare across periods.
2. **The frame is sparse by profile**, and that is the point: AMT (`reit`) carries 24 concepts, BAC/JPM/AZO 41. A concept that does not apply is simply absent, which is exactly the coverage story this tab exists to tell.
3. **The snapshot needs no pivot** (see §4).

One trap this surfaced, which mattered later: `shares_basis` is 0/1-valued but is **not** a flag — it is a code from `SHARES_BASIS_CODES` (`diluted_wavg` = 0.0, `period_end` = 1.0). Any purely data-driven "binary means flag" rule misclassifies it.

## 2. Step 1 — the export

`export_for_app()` now writes seven artefacts. The five that existed are byte-for-byte unchanged — asserted, including that `universe.parquet` keeps its exact column list.

| file | contents | rows | size (8 tickers) |
|---|---|---|---|
| `metrics_long.parquet` | unchanged | 8,711 | 64,524 B |
| `valuation_history.parquet` | unchanged | 4,566 | 37,260 B |
| `facts_growth.parquet` | unchanged (3 growth concepts, 4 columns) | 1,705 | 19,903 B |
| **`facts_full.parquet`** | **new** — the whole facts frame, all 69 concepts, all 5 columns | 18,120 | **229,525 B** |
| **`current_snapshot.parquet`** | **new** — the snapshot frame | 292 | **5,966 B** |
| `universe.parquet` | unchanged | 8 | 3,583 B |
| `meta.json` | row counts now cover all six frames | — | 438 B |

`APP_EXPORT_SCHEMA` bumped **1 → 2**, since the file set changed. Write-to-temp-then-`os.replace` per file and *meta.json last* are both kept; asserted that no `.tmp` survives.

`snapshot` is a **required** parameter, not optional. One caller exists, and an optional one would let a caller silently produce an export the app then rejects.

### The duplication between `facts_growth` and `facts_full` is deliberate

They come from the same source frame and are both written on purpose, with a clean division of labour:

- **`facts_growth` serves the charts.** `build_growth` can only ever draw the three `CHART_GROWTH` concepts, so 1,705 rows is everything it can use — **10.6× smaller** than the full frame, verified as a strict subset.
- **`facts_full` serves inspection.** Its value is precisely what the narrowing removes: `Revenue` sitting next to `Revenue_TTM`, `NetIncomeLoss` next to `EPS_TTM_CALC`. That pairing is what makes the TTM derivation auditable, and it is the whole reason this tab exists.

Merging them would either bloat every chart load 10× or blind the data tab. Keeping both costs 19,903 B.

### Requirement 3 — is the export really post-`filter_hidden_rows`? Verified, not assumed

The precondition is asserted against `config.is_hidden` first, then checked in the exported files, for two `financial` and two `reit` tickers across all four frames — **16 checks, no leakage**:

| ticker | profile | facts | metrics | valuation | snapshot |
|---|---|---|---|---|---|
| JPM | financial | 37 concepts, 0 leaked | 18, 0 | 6, 0 | 41, 0 |
| BAC | financial | 37, 0 | 18, 0 | 6, 0 | 41, 0 |
| AMT | reit | 30, 0 | 12, 0 | 7, 0 | 24, 0 |
| O | reit | 27, 0 | 11, 0 | 7, 0 | 25, 0 |

A clean pass here could mean "the filter works" or "there was nothing to filter", so the same frames were checked **before** filtering to prove the test is not vacuous: JPM loses 3 metrics / 4 facts / 8 snapshot / 8 valuation concepts, AMT loses 13 / 8 / 27 / 7. AMT's snapshot drops 27 concepts — the filter is doing substantial work, and the data tab shows none of it.

### Requirement 4 — file size and the full-universe extrapolation

| file | 8 tickers | per ticker | linear → 501 tickers |
|---|---|---|---|
| `facts_full.parquet` | 229,525 B | 28,691 B | **13.7 MB** |
| `metrics_long.parquet` | 64,524 B | 8,066 B | 3.9 MB |
| `valuation_history.parquet` | 37,260 B | 4,658 B | 2.2 MB |
| `facts_growth.parquet` | 19,903 B | 2,488 B | 1.2 MB |
| `current_snapshot.parquet` | 5,966 B | 746 B | 0.4 MB |
| **total export** | 361,199 B | 45,150 B | **21.6 MB** |

**This is not a problem to ship, and 13.7 MB is an upper bound.** Parquet dictionary-encodes the repeated `ticker`/`concept` strings, so the per-ticker cost falls as the universe grows — measured rather than asserted:

| tickers | bytes/ticker | implied at 501 |
|---|---|---|
| 1 | 34,619 | 16.5 MB |
| 2 | 31,564 | 15.1 MB |
| 4 | 30,565 | 14.6 MB |
| 8 | 28,691 | **13.7 MB** |

Monotonically declining, so the real 501-ticker file lands **below** 13.7 MB. For scale, the same 8 tickers' `quarterly_facts.csv` is 1,034,781 B — the Parquet is **4.5× smaller** than the CSV the pipeline already writes. Nothing was trimmed.

## 3. Step 2 — the pivot helper

`pivot_ticker(frame, ticker, value_column="value")` → rows = period end, columns = concept.

1. **Newest first** (`sort_index(ascending=False)`).
2. **Missing values stay missing.** `pivot_table(..., aggfunc="first", dropna=False)`. `dropna=False` is load-bearing: the default drops all-null columns, and an all-null column is a finding, not noise. Nothing is filled, nothing is dropped.
3. **Empty ticker returns an empty frame**, never raises — checked for an unknown ticker, an empty source frame, and empty input to the formatter.

### Display formatting vs. export precision — how they are kept apart

**Structurally, not by convention.** `pivot_ticker` returns numbers. `format_for_display` returns a *separate frame of strings* that is only ever passed to `st.dataframe`. Downloads and copy blocks call `to_csv_text` on the **numeric** frame. There is no code path where a rounded value reaches an export.

Telling an absolute from a ratio, in precedence order:

1. **`config.METRICS_BY_ID[concept].percent is True`** → rendered as `25.34%`. This covers the metric frames, as the brief noted.
2. **Facts are the separate case** — no registry entry exists for `Revenue` or `Assets`. The fallback is the **column's own maximum magnitude**: at or above 10,000 the column is absolute and gets a scaled unit (`4.90T`, `22.04B`, `2.36B`); below it, four decimals.

The magnitude rule is decided **per column, from that column's max**, so one column never mixes two treatments. It also handles the awkward facts cases without a per-concept table that would go stale: `EPS_TTM_CALC` and `DividendsPerShare_TTM` are per-share amounts that fall below the threshold and correctly render as `5.9000`, while `Assets` renders as `4.90T` — from the same rule, no special-casing.

Verified end to end: `Assets` = `4900475000000.0` displays as `4.90T` (so the two genuinely differ) while the same value appears **verbatim** in the CSV.

> **Worth knowing for anyone re-reading these CSVs:** the written text carries the full 17-significant-digit repr, but `pd.read_csv`'s *default* float parser is fast rather than exact and drops the last digit (`0.21116706399164278` → `0.2111670639916427`). Use `float_precision="round_trip"`. The loss is in the reader, never in the file — asserted both by round-trip comparison and by checking that every source float's exact repr appears in the CSV characters.

## 4. Step 3 — the data tab

A fifth top-level tab, four sections in pipeline order: **Raw & derived facts → Calculated metrics → Quality flags → Valuation history → Current snapshot.**

### Identifying flags — what `config.py` and `quality.py` actually offer: nothing

Both were checked first, as the brief asked:

- **`quality.py`** exposes only `check_data_quality`, `print_data_quality`, `search_tags`. Its "flags" (`collect_flags`) are a **completely different thing** — EDGAR *coverage* warnings (`ticker`/`concept`/`count`/`ratio`) that feed the run report and never reach `metrics_long`.
- **`config.py`** contains no flag-related name at all (`[n for n in dir(config) if "FLAG" in n.upper()]` → `[]`), and `Metric` has no `flag` field.
- **"Absent from `METRICS`" is not a flag test.** `METRICS` does exclude all five flags — but it also excludes `rotce`, `effective_tax_rate` and the nine `*_quarterly` series. It catches **16** concepts of which only 5 are flags.

**So a name-based rule was the only option, and I am saying that plainly.** It lives in exactly one place, `app.py`'s `is_quality_flag`:

```python
QUALITY_FLAG_CONCEPTS = {"fcf_exceeds_ebitda", "inorganic_contaminated"}
def is_quality_flag(concept): return concept.endswith("_flag") or concept in QUALITY_FLAG_CONCEPTS
```

**A `_flag` suffix match alone would have been wrong, not merely inelegant** — it catches 3 of 5 and misses `fcf_exceeds_ebitda` and `inorganic_contaminated`. Hence the explicit pair; the suffix then widens the set on its own if the pipeline gains another `*_flag`.

The rule is **validated against the data**: it agrees exactly with "every non-null value is in {0,1}" across `metrics_long` — `{buyback_distortion_flag, fcf_exceeds_ebitda, inorganic_contaminated, low_tax_rate_flag, share_count_jump_flag}`, no false positives among the other 35 concepts. The data test is *not* used as the rule, because it misfires elsewhere: it would classify the snapshot's `shares_basis` as a flag when it is a code.

**Presentation.** Flags get a summary — *how often, and how recently* — rather than a column of zeros wedged between two ratios:

| flag | raised | periods evaluated | most recent |
|---|---|---|---|

The per-period 0/1 values remain available in an expander, with their own download.

> **Recommended follow-up (not done — `config.py` had to stay unmodified):** a `QUALITY_FLAGS` set, or a `flag: bool` field on `Metric`, belongs in `config.py` next to the registry. It would replace the name rule with a real one and put it beside the metrics it describes.

### Distinguishing raw from derived — a structural rule, better than the suffixes

The brief suggested the `_TTM`/`_QUARTERLY`/`_CALC` suffixes. **They are not sufficient**: `PPNR`, `CoreOperatingEarnings` and `TangibleEquity` are derived and carry no suffix, so a suffix rule calls all three raw. (`main.py` half-acknowledges this already with `_TTM_LIKE_NAMES`.)

`config.py` does offer a structural answer, and `app.py` already imports it:

```python
def fact_is_derived(ticker, concept):
    return concept not in config.get_concept_candidates(ticker)
```

The names the pipeline asks EDGAR for are exactly that dict's keys, so anything else in the facts frame was computed. Verified across all 8 tickers: the structural rule **never contradicts** the suffix rule (no suffixed concept is called raw), and it is **strictly better** where the unsuffixed derivations exist — JPM/BAC gain `PPNR` + `TangibleEquity`, AFL gains `CoreOperatingEarnings` + `TangibleEquity`.

Made visible two ways: a **filter** (All / Raw only / Derived only) and **column ordering by base concept, raw before its own derivations**, so `Revenue` and `Revenue_TTM` are adjacent — asserted for all 8 tickers, and asserted to be a pure permutation that loses no column.

### Limits and defaults chosen

| control | default | opt-out |
|---|---|---|
| table periods | **16** (4 years of quarters) | "Show all periods" checkbox |
| copy-block periods | **8** (2 years) | — deliberately fixed and smaller |
| facts filter | All | Raw only / Derived only |

Measured copy-block sizes, stated in the UI per section (`~4,242 characters`):

| ticker | section | copy (8) | table (16) | all periods |
|---|---|---|---|---|
| AAPL | facts | 4,242 | 7,926 | 33,228 (75) |
| AAPL | metrics | 2,604 | 4,870 | 19,345 (73) |
| JPM | facts | 4,646 | 8,567 | 34,640 (74) |
| JPM | valuation | 966 | 1,804 | 7,174 (74) |

The full facts table at 33k characters is past comfortable pasting; at 8 periods every section stays under 5k.

**Per-section download** (`st.download_button`) produces the filtered, single-ticker table as `AAPL_facts.csv`, `AAPL_metrics.csv`, `AAPL_flags.csv`, `AAPL_valuation.csv`, `AAPL_snapshot.csv` — the table as filtered on screen, at full precision.

### The snapshot section — why no pivot

From §1: the frame is long, one row per `(ticker, concept)`, with a single constant `end`. **The ticker's slice is already a concept/value list — that *is* the transposed view**, so it is rendered directly.

Pivoting it would produce a table of **one row and ~40 columns** that scrolls sideways, and would add nothing, because there is no second period to compare against. The decision follows from the measured shape rather than from the guess in the brief, which anticipated the same answer for a different reason.

Each table also reports **how many of its columns are null in every period shown**, labelled as a finding rather than hidden — the real data has genuine cases: **AZO's `debt_to_equity`, `roe` and `rotce` are null in all 72 periods**, because AutoZone's equity is negative and the ratio guards require a positive denominator. That empty column is a true statement about the business, and it is exactly what this tab is for.

Consistent with the existing prototype: no custom CSS, no multi-page structure, `@st.cache_data` on the loaders only — **never on rendered output**.

## 5. Step 4 — verification

Run against a scratch export built from pickled frames, so yfinance re-adjusting its back history between pulls cannot manufacture a false diff. **All 184 checks pass.**

### Export round-trip
Both new files read back with **dtypes preserved column by column**, `end` as **`datetime64[ns]`**, and contents `.equals()` the in-memory frames they came from. Row counts match `meta.json`.

### The pivot is correct, checked against the source frame
For **JPM (`financial`)**, **AMT (`reit`)** and AAPL, across facts / metrics / valuation:

- **shape == the ticker's distinct period count × distinct concept count** — JPM facts 74×37, JPM metrics 72×18, AMT facts 74×30, AAPL metrics 73×19.
- **12 individually sampled cells per frame** compared against the long rows they came from — no mismatches.
- **The reverse direction too:** every non-null cell round-trips back to exactly one long row (JPM facts 2,382 cells ↔ 2,382 non-null rows; AMT facts 1,977 ↔ 1,977).
- Newest period first; column set equals the ticker's concept set.

### Nulls survive the pivot
A pivot null has two distinct causes and both had to survive. AAPL `rotce` is a column with 38 nulls = 73 periods − 35 values (**52%**, matching the brief's figure — the nulls there come from *absent periods*). The identity `nulls == periods − non-null rows` was then asserted for **every column of every one of the 8 tickers** — no exceptions. A row that exists *with* a null value (58 such `(ticker, concept)` pairs) stays a null cell rather than being dropped, and a synthetic all-null concept survives as an all-null column.

### Downloads carry full precision
Compared against the **source frame**, not the screen: 236 values across three JPM sections, **max absolute difference 0.0**. Stronger still, every source float's exact repr appears verbatim in the CSV characters — independent of any reader.

### Hidden metrics do not appear
Precondition asserted against `config.is_hidden` first (`is_hidden("JPM","ffo_margin")`, `is_hidden("AMT","pe_ratio")`, `is_hidden("O","ev_ebitda")`, …), then the rendered tables checked: **12 table checks across JPM / AMT / O × facts / metrics / valuation / snapshot, zero leakage.**

### `app.py`
- **Imports checked by AST**: `config`, `figures`, `json`, `os`, `pandas`, `streamlit` — **no pipeline module**.
- **The whole page body runs in bare mode** with the new tab: `app.main()` completes, and `render_data_tab` was then exercised across **all 48 combinations** (8 tickers × show-all on/off × 3 fact filters) without raising.
- Absent-ticker paths checked for all three section renderers.

**One real bug found and fixed while verifying this.** The missing-export branch ended in `st.stop()`, which only raises inside a script run — headlessly the page fell straight through into a `FileNotFoundError`. It now does `st.stop()` **and** `return`, so the branch is explicit and testable. Confirmed against the project's own currently-stale export: it returns cleanly, naming the two missing files.

### Nothing regressed
- **Chart figures compared against the `.json` the pipeline itself wrote on 2026-08-05**, not against remembered numbers: AAPL/JPM/AMT `build_fundamentals` and `build_growth` are all **byte-identical** (50,191 / 52,374 / 25,630 and 18,966 / 18,876 / 18,821 B). `build_valuation` is deliberately excluded — it reads price history, which yfinance has moved since, so a difference there would be evidence of nothing.
- **`run_full_refresh()` ran end to end** on the 8-ticker set in an isolated working directory: all seven export artefacts, `schema: 2`, meta covering six frames, the four CSVs still written, 48 figure files still written, no `.tmp` left. The project's own `data/`, `figures/`, `cache/` and `full_refresh_report.md` were **not touched** — asserted by mtime and by file absence.
- **`figures.py` and `config.py` SHA-256 identical** before and after.

### One environmental finding, pre-existing

**Importing `streamlit` swaps plotly's default template from `plotly` to `streamlit`** (it registers and selects its own), which changes every serialised figure in that process by a constant **−3,224 B**. This briefly looked like a regression until the delta turned out to be identical across three tickers and two chart types. It is **not** caused by this task — `app.py` has imported streamlit since the previous task and `figures.py` is hash-identical — and it is desirable: the app's charts follow the app's theme. It does mean an app-rendered figure will never be byte-equal to the pipeline's saved `.json`; with the template pinned back they are identical, and the `data` traces are identical either way. Both were asserted.

### What was not verified, honestly

**Nothing was viewed in a browser.** The real server was started (`streamlit run app.py --server.headless`), stayed alive, answered `/_stcore/health` with `200 ok`, and served a 10,951-byte index with a clean log — but layout, column widths on a 37-column facts table, whether `st.dataframe`'s horizontal scroll is usable at that width, expander behaviour, and the copy button on `st.code` are all unverified. What is verified is that the page code runs to completion and every number it renders, downloads or copies is correct.

## 6. One thing you need to do

**The project's `data/app/` is now stale** — it holds the 5-file schema-1 export from the 2026-08-05 run and lacks `facts_full.parquet` and `current_snapshot.parquet`. The app detects this and shows the error naming both files plus the command; it does not crash. I deliberately did **not** overwrite your `data/app/` with my isolated test run's output, because that would replace pipeline output with something you did not ask for and give `meta.json` a `run_start` you never ran.

Re-run the export to use the tab:

```
python -c "from main import run_full_refresh; run_full_refresh()"
```

Still open from earlier tasks, unchanged: the `V`/`STZ` missing-`SharesOutstanding` finding, the `main()` vs `run_full_refresh()` drift items (NaN-drop before the CSV write, sorting, as-of snapshots), and moving `APP_EXPORT_DIR` into `config.py` to remove the path duplication between `main.py` and `app.py`.

No scratch scripts were left behind.
