# `fetchers/edgar.py`

## Overview

Encapsulates everything related to SEC EDGAR: HTTP access with a file cache, ticker→CIK lookup, and extraction of clean time series from raw XBRL data.

Extraction is the core of this module. SEC raw data is considerably messier than one might expect: values are reported multiple times (sometimes with different numbers), period tags are unreliable, some concepts arrive as cumulative year-to-date figures instead of individual quarters, and the same concept may appear under different tags or in different units depending on the company. This module cleans all of that up.

No other part of the project needs to know anything about the EDGAR JSON structure.

---

## Functions

| Function | Purpose | Output |
|---|---|---|
| `fetch_or_cache` | HTTP GET with a file cache and an optional max age | raw dict |
| `build_ticker_to_cik` | Raw ticker mapping → fast lookup | `{ticker: cik}` |
| `get_cik` | Ticker → 10-digit CIK | `str` |
| `get_company_info` | CompanyFacts, served from cache unless the filer is ahead of it | raw dict |
| `get_submissions` | The filing index (cached one day) | raw dict |
| `get_latest_filed_period` | Newest 10-K/10-Q `reportDate` in the index | `str \| None` |
| `newest_reported_period` | Newest 10-K/10-Q `end` inside a cached CompanyFacts | `str \| None` |
| `extract_period_values` | Raw values of a concept, filtered by period type | `list[dict]` |
| `decumulate_period_values` | Cumulative YTD values → true individual quarters | `list[dict]` |
| `extract_quarterly_values` | Public API for quarterly data | `list[dict]` |
| `extract_annual_values` | Public API for annual data | `list[dict]` |
| `extract_summed_values` | Sums multiple tags per period | `list[dict]` |

---

## The cache does not go stale silently

CompanyFacts is a large response and it changes only when the filer files. Refetching every
run is wasteful; never refetching serves last quarter's numbers forever. So
`get_company_info` keeps a **sidecar** per ticker (`cache/<T>_cache_meta.json`) holding the
newest period the cached copy contains, and compares it against the filing index:

```
cached newest_period  <  published latest reportDate   ->  refetch
```

Three properties of that check are deliberate:

- **The probe is an optimisation, never a hard dependency.** If the submissions request
  fails, `published_period` is `None`, the comparison is false, and the cache is served.
  A network problem degrades freshness, it does not break the run.
- **`last_refetch_attempt` caps it at one attempt per ticker per day**, so a filer whose
  index is ahead of its CompanyFacts (which happens for a day or two after a filing) does
  not trigger a full refetch on every run.
- **`check_staleness=False` bypasses the probe entirely** and reads the cache. That is what
  makes an offline, reproducible re-derivation possible: the same cache in, the same facts
  out, no network.

---

## The five data problems this module solves

### 1. Duplicate reports and restatements

The same period often appears multiple times — once from the original filing, once from an amendment (`10-K/A`), once as a comparative figure in a later report. The values can differ.

**Solution:** Deduplicate by `end` date, keeping the entry with the **later `filed` date** —
the most current version, which is the restatement rather than the original.

```python
if existing is None or item["filed"] > existing["filed"]:
```

The string comparison works only because EDGAR consistently uses ISO format
(`YYYY-MM-DD`).

**Point-in-time values break the tie differently.** For those the key is the `end` date
alone, and the **shorter** period wins before the later filing does: a balance-sheet figure
carried inside a year-to-date context describes the same instant as one filed in a
quarterly context, but the quarterly context is the one that dates it precisely. Filing
date only decides when the durations are equal or absent.

### 2. The `fp` field is unreliable

The obvious approach would be to filter quarters via `fp in ("Q1","Q2","Q3")` and years via `fp == "FY"`. This does not work: some companies (e.g. NVIDIA for `RevenueFromContractWithCustomerExcludingAssessedTax`) tag **virtually everything** as `FY`, including values that are clearly quarter-sized.

**Solution:** Classify by actual **period length** (`end - start`), not by `fp`:
- 80–100 days → quarter (`_QUARTER_MIN_DAYS` / `_QUARTER_MAX_DAYS`)
- 350–380 days → year

Length is computed from the data itself and cannot be mistagged.

### 52/53-week filers need a wider quarter, and it is gated on repetition

A retail-style fiscal calendar has 12-week and 16-week quarters and an occasional 53-week
year, so a real quarter can run to 111, 112, 118 or 119 days. Measured over the 622,845
differences `decumulate_period_values` forms across all 501 tickers:

```
 80..100   604,683   the calendar quarter (89-92) and the 12-week quarter (83-84)
101..105         0   empty
106..120     1,625   the 16-week (111/112) and 17-week (118/119) fiscal quarter
121..160       112   merger, spin-off, IPO and fiscal-year-change stubs
161..200     9,307   two quarters, one of the filer's points missing
```

`_LONG_QUARTER_MAX_DAYS = 120` is 17 weeks plus a day — the longest quarter any fiscal
calendar has. But the 106–120 band still mixes two populations: eight genuine 52/53-week
filers (AZO, COST, DPZ, PEP, KR, YUM, HST, MAR) and eight one-off stubs. **They are told
apart by repetition, not by length**: the eight filers produce 15–29 such periods per
concept, every stub exactly one. `_MIN_LONG_QUARTER_PERIODS = 3` keeps Marriott's and
Host's short-lived 52/53-week era and admits no stub.

This is why `_is_quarter_length` takes a `long_quarters_ok` flag rather than a fixed range:
the decision needs the whole set of candidate differences, which only
`decumulate_period_values` has.

### 3. Cumulative (YTD) instead of individual quarters

Many companies report cash flow items (operating cash flow, capex, depreciation) **cumulatively**: all periods within a fiscal year start on the same day and run for different lengths.

```
2024-09-29 → 2024-12-28   90 days   (= Q1)
2024-09-29 → 2025-03-29  181 days   (= Q1+Q2)
2024-09-29 → 2025-06-28  272 days   (= Q1+Q2+Q3)
2024-09-29 → 2025-09-27  363 days   (= full year)
```

Income statement items (revenue, operating income) usually arrive as individual quarters, each with its own `start`.

**Solution:** `decumulate_period_values` detects the case automatically from the `start` date and handles both patterns with the same logic:

- Group by `start` date
- With cumulative data, all YTD stages of a year land in **one** group → taking the difference from the previous stage yields the true quarter
- With individual quarters, each quarter has its **own** `start` → it sits alone in its group, `prev_value = 0`, and the value passes through unchanged

The same line of code works for both cases:
```python
quarter_value = v["value"] - prev_value
```

### 4. Q4 is almost never reported separately

Companies report Q1–Q3 in their 10-Qs and then the full year in the 10-K. There is no separate Q4 filing.

**Solution:** Q4 is derived.

- **Cumulative case:** Q4 falls out of the decumulation automatically (the annual value is simply the last YTD stage).
- **Individual-quarter case:** Explicit derivation `Q4 = FY − (Q1 + Q2 + Q3)`. The three quarters are found by **temporal proximity** (the last three before the fiscal year end, at most 300 days back), **not** via the `fy` tag — which is just as unreliable as `fp`.

### 5. Multiple units

A concept can have several units. EPS, for instance, lives under `USD/shares`, not `USD`. And some companies (e.g. Walmart) additionally report a dimensionless helper unit called `pure`.

**Solution:** Prioritized unit selection instead of "take the first one":

```python
preferred = ["USD", "USD/shares", "shares"]
unit_key = next((u for u in preferred if u in units), None)
```

A naive `list(units.keys())[0]` returns the `pure` values for Walmart — i.e. garbage.

---

## Period values vs. point-in-time values (`is_point_in_time`)

Two fundamentally different kinds of data in XBRL:

**Period values** (revenue, income, cash flow): have both `start` and `end`, cover a span of time. They are additive, and require decumulation and Q4 derivation.

**Point-in-time values** (equity, debt, cash): have only `end`, describe a balance sheet position at a given date. They are **not** additive — each reported value is taken as-is, with no differencing.

The flag controls both behaviors. `SharesOutstanding` is a special case: formally an average over a period, but treated as `point_in_time` because share counts must never be summed or differenced.

---

## Fallback vs. summation

Two ways to combine multiple tags into one concept:

**Fallback** (`extract_merged_values` in `parsers/parse_edgar.py`): "Take the first tag that has data for this period." For concepts that changed tags over time (e.g. revenue after the ASC 606 transition in 2018).

**Summation** (`extract_summed_values`, here): "Add all tags together." For concepts that coexist and belong together — e.g. total debt = long-term + current + convertible.

Controlled via `mode` in `CONCEPT_CANDIDATES`.

---

## Common pitfalls

**File not saved.** For cryptic `ImportError`/`AttributeError`, first check with `type file.py` (Windows) or `cat file.py` what is actually on disk. Python only sees saved files, not open editor tabs.

**Loop variable shadows a parameter.** `def get_cik(ticker, mapping): for ticker in mapping:` — the loop immediately destroys the value that was passed in.

**Module-level code instead of pure function definitions.** A function call sitting directly in `edgar.py` runs on **every import**. Fetcher files define; they do not call.

**Forgetting `os.makedirs`.** `open(path, "w")` creates the file, but not any missing parent directories.

**Guessing keys instead of checking.** `entry["cik"]` does not exist; the key is `cik_str`. Always print a sample entry first.

**Calling `.zfill()` on an `int`.** It's a string method. Convert with `str(...)` first, then `.zfill(10)`.

**Mistaking missing data for a bug.** Gaps often have a real-world explanation: Apple had no long-term debt for years, banks don't report EBITDA, NVIDIA uses different tags in certain periods. Not every gap is a code defect.