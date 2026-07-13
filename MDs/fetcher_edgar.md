# `fetchers/edgar.py`

## Overview

Encapsulates everything related to SEC EDGAR: HTTP access with a file cache, ticker→CIK lookup, and extraction of clean time series from raw XBRL data.

Extraction is the core of this module. SEC raw data is considerably messier than one might expect: values are reported multiple times (sometimes with different numbers), period tags are unreliable, some concepts arrive as cumulative year-to-date figures instead of individual quarters, and the same concept may appear under different tags or in different units depending on the company. This module cleans all of that up.

No other part of the project needs to know anything about the EDGAR JSON structure.

---

## Functions

| Function | Purpose | Output |
|---|---|---|
| `fetch_or_cache` | HTTP GET with file cache | raw dict |
| `build_ticker_to_cik` | Raw ticker mapping → fast lookup | `{ticker: cik}` |
| `get_cik` | Ticker → 10-digit CIK | `str` |
| `get_company_info` | CompanyFacts (all XBRL data for a company) | raw dict |
| `extract_period_values` | Raw values of a concept, filtered by period type | `list[dict]` |
| `decumulate_period_values` | Cumulative YTD values → true individual quarters | `list[dict]` |
| `extract_quarterly_values` | Public API for quarterly data | `list[dict]` |
| `extract_annual_values` | Public API for annual data | `list[dict]` |
| `extract_summed_values` | Sums multiple tags per period | `list[dict]` |

---

## The five data problems this module solves

### 1. Duplicate reports and restatements

The same period often appears multiple times — once from the original filing, once from an amendment (`10-K/A`), once as a comparative figure in a later report. The values can differ.

**Solution:** Deduplicate by `end` date, keeping the entry with the **later `filed` date** (that's the most current version).

```python
if existing is None or item["filed"] > existing["filed"]:
```

The string comparison works here only because EDGAR consistently uses ISO format (`YYYY-MM-DD`).

### 2. The `fp` field is unreliable

The obvious approach would be to filter quarters via `fp in ("Q1","Q2","Q3")` and years via `fp == "FY"`. This does not work: some companies (e.g. NVIDIA for `RevenueFromContractWithCustomerExcludingAssessedTax`) tag **virtually everything** as `FY`, including values that are clearly quarter-sized.

**Solution:** Classify by actual **period length** (`end - start`), not by `fp`:
- ~80–100 days → quarter
- ~350–380 days → year

Length is computed from the data itself and cannot be mistagged.

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