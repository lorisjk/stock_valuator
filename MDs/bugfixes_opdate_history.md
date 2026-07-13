# Bugfix History

A running log of bugs found, what caused them, and how they were fixed. Ordered newest first.

Most entries here share a theme: **the pipeline fails silently**. A missing tag returns an empty list, an empty list produces an empty merge, an empty merge produces an empty chart. Nothing crashes. The symptom appears several layers away from the cause, and usually looks like a plotting problem. Nearly every fix below was found by noticing that a *number* looked wrong, not by reading a stack trace.

---

## 2026-07-13 (later) — Amazon

Adding **AMZN** produced a P/E of 216 (real value ~30) and a five-year average P/E of **−41.6**. A negative average P/E is not a number that can exist.

The data quality check reported three concepts missing entirely:

```
FEHLT  AMZN   OperatingCashFlow             0 von 77 (0%)
FEHLT  AMZN   Capex                         0 von 77 (0%)
duenn  AMZN   DepreciationAndAmortization   9 von 77 (12%)
```

But the tags themselves were all present in the EDGAR data and all already configured. The extraction was silently dropping everything.

### The root cause: an end date does not identify a period

Amazon reports **three different period types in parallel** for the same concept:

```
2025-01-01 -> 2025-06-30   180 days   YTD (cumulative)
2025-04-01 -> 2025-06-30    90 days   the actual quarter
2024-07-01 -> 2025-06-30   364 days   a rolling twelve-month window
```

All three end on 30 June 2025. All three are legitimate, distinct facts.

`extract_period_values` deduplicated by `end` date alone:

```python
values[end_date] = {...}   # later filed date wins
```

So of the three, only one survived — and systematically the wrong one, because the rolling window appears in later filings and therefore wins the `filed` comparison.

The result: after extraction, **every single entry had annual length**. Not one real quarter made it through. `decumulate_period_values` then had nothing to work with and returned an empty list. Downstream, FCF, EBITDA and every dependent ratio were built on nothing.

This bug had existed since the original quarterly conversion. It never caused harm because AAPL, MSFT, NVDA, WMT, JPM and NOW happen not to report overlapping period types. Amazon does.

**Fix**

Deduplicate by `(end, days_diff)` instead of `end`:

```python
key = (end_date, days_diff) if not is_point_in_time else end_date
```

Point-in-time values keep `end` alone as the key — a balance sheet date has no duration, so there is nothing to disambiguate.

Length distribution for the same concept, before and after:

```
before:  {364: 54, 365: 19}                              ← no quarters at all
after:   {89: 14, 90: 22, 91: 18, 180: 13, 181: 5,
          272: 13, 273: 5, 364: 54, 365: 19}             ← 54 real quarters
```

### The second problem: rolling twelve-month windows

With deduplication fixed, the rolling windows now survive extraction — and immediately break `decumulate_period_values`, which groups by `start` date.

A rolling window like `2025-04-01 → 2026-03-31` shares its `start` with the real quarter `2025-04-01 → 2025-06-30`. The function sees two entries in one `start` group, assumes they are cumulative stages, and computes `148,531 − 32,515 = 116,016` as a "quarterly value". Nonsense.

They also fall inside the 350–380 day band and get treated as annual values, poisoning the Q4 derivation as well.

**Fix**

Discard them before grouping. The discriminant is generic and needs no knowledge of the fiscal calendar:

> **A real fiscal year starts where a quarter starts.** Q1 shares its `start` date with the full year. A rolling window does not.

```python
quarter_starts = set()
for v in entries:
    days = (date.fromisoformat(v["end"]) - date.fromisoformat(v["start"])).days
    if 80 <= days <= 100:
        quarter_starts.add(v["start"])

cleaned = []
for v in entries:
    days = (date.fromisoformat(v["end"]) - date.fromisoformat(v["start"])).days
    if 350 <= days <= 380 and v["start"] not in quarter_starts:
        continue
    cleaned.append(v)
```

Companies that do not report rolling windows are unaffected — their annual values always start where Q1 starts.

**Result**

| | before | after |
|---|---|---|
| P/E | 215.1 | **29.6** |
| avg P/E (5y) | −41.6 | **36.1** |
| EV/EBITDA | 20.5 | **17.2** |
| PEG | 15.1 | **2.08** |

---

## 2026-07-13 — Meta

### Missing debt tag variant

`LongTermDebt` came in at 35% coverage. Meta uses `NotesPayableCurrent` for the short-term portion of its bonds, which was not in the tag list.

**Fix:** added `NotesPayableCurrent` to the `LongTermDebt` summation list.

**Deliberately not added:** the bare `LongTermDebt` tag, which Meta also reports as a combined figure. With `mode: "sum"` it would be added to its own components and double the debt.

**Also deliberately excluded:** `FinanceLeaseLiability` and `OperatingLeaseLiability`. Meta carries substantial data-centre leases. Whether leases count as "debt" is a matter of analytical convention, not a data problem — for consistency across tickers, `LongTermDebt` here means interest-bearing financial debt only.

### Not a bug

`DividendsPerShare` at 15% coverage (9 of 62 quarters) is correct. Meta only started paying a dividend in Q1 2024.

Also verified as real: debt jumping from 28.8bn to 58.7bn in a single quarter. That is Meta's October 2025 bond issue — 30bn, the largest corporate bond in US history, to fund AI infrastructure.

---

## 2026-07-13 — ServiceNow

Four distinct bugs, all surfaced by the same ticker.

### 1. Missing concept crashes `build_valuation_history`

**Symptom**
```
KeyError: 'DividendsPerShare_TTM'
```

**Cause**
ServiceNow pays no dividend, so `DividendsPerShare` has zero rows. `pivot_table` only creates columns for concepts that have data — so the column did not exist at all, rather than existing and being full of `NaN`.

This would have happened for any missing concept.

**Fix**
Fill missing columns with `pd.NA` after the pivot:

```python
for concept in needed:
    if concept not in wide.columns:
        wide[concept] = pd.NA
```

The affected multiple becomes `NaN`, gets removed by the final `dropna`, and the chart correctly shows "keine Daten".

---

### 2. Debt understated — missing tag variants

**Symptom**
`LongTermDebt` at 17% coverage (11 of 63 rows).

**Cause**
ServiceNow names its convertible notes `ConvertibleLongTermNotesPayable` / `ConvertibleNotesPayableCurrent` — not `ConvertibleDebtNoncurrent` / `ConvertibleDebtCurrent`, the only convertible tags in the config.

**Fix**
Added both tags to the `LongTermDebt` summation list. Verified afterwards that the total lands at ~1.49bn, matching ServiceNow's actual debt — no double counting from overlapping tag families.

**Note:** `mode: "sum"` always carries double-counting risk when adding tag variants. Check the magnitude against a known figure before trusting it.

---

### 3. Share count oscillating between two bases (stock split)

**Symptom**

```
2023-09   205,194,000
2023-12 1,027,953,000   ← ×5
2024-03   207,684,000
2024-12 1,042,113,000   ← ×5
2025-03 1,046,852,000   ← ×5
2025-06   209,343,000
```

Downstream this broke market cap, and with it P/B, P/FCF, EV/Sales and EV/EBITDA. The raw `EPS` concept also went **negative while net income was positive**, which is impossible.

**Cause**

ServiceNow executed a **5:1 stock split in 2025**. The raw filings show it plainly:

```
val:   208,423,000   filed: 2025-01-30   (FY2024 10-K)
val: 1,042,113,000   filed: 2026-01-29   (FY2025 10-K, restating FY2024)
```

Same period, same form, same unit — two different values. The later one is the correct, split-adjusted restatement.

The deduplication logic was working correctly. The problem is that EDGAR only restates the periods that appear as **comparatives** in the newest filing. Everything older keeps its pre-split values from the original 10-Qs. The series ends up with two incompatible bases interleaved.

The negative EPS came from the same source: `decumulate_period_values` subtracting three pre-split quarters from a post-split annual figure.

**Two false starts, worth recording:**

- **Outlier filter (rolling median).** Discarded. It cannot distinguish a data error from a real split, and at ServiceNow the "wrong" values are in the *majority* at the recent end of the series — so the median locks onto them. Worse: it would have thrown away the *correct* restated values and kept the stale ones.
- **Deriving share count as `NetIncome / EPS`.** Circular. `EPS_TTM_CALC` is computed as `NetIncome / SharesOutstanding`; deriving shares from EPS just recovers the original corrupted EPS.

**Fix**

`normalize_split_adjusted()` in `metrics.py`. It rescales the entire series onto the basis of the **most recent** value — which always comes from the newest filing, and therefore matches the fully split-adjusted price series from yfinance.

For each value, it tests a list of common split factors (2, 3, 4, 5, 10, …) and picks the one that brings it closest to the anchor:

```python
anchor = values.iloc[-1]
for f in COMMON_SPLIT_FACTORS:
    for candidate in (v * f, v / f):
        err = abs(np.log(candidate / anchor))
```

The logarithm makes ×5 and ÷5 symmetric. Factor 1 is in the list, so a ticker with no split passes through untouched.

This works because a real share count moves by a few percent per quarter (buybacks, option exercises) but never by 400%. Any jump of a clean factor is a basis change, not a business event.

**Consequence:** the raw `EPS` concept is no longer needed. `EPS_TTM_CALC = NetIncomeLoss_TTM / SharesOutstanding` uses two split-consistent absolute quantities. Removed `EPS` from `CONCEPT_CANDIDATES`.

**Known limitation:** the method assumes the true share count does not change by more than roughly ±50% across the series. A company that has bought back most of its shares over a very long history could have an early value misread as a split.

---

### 4. `avg_pe_5y` meaningless (247) — near-zero denominators

**Symptom**

After fixing the split issue, the P/E series was smooth but the five-year average came out at **247** — useless as a reference line.

**Cause**

ServiceNow only became profitable around 2019. In those quarters, `NetIncomeLoss_TTM` was barely above zero, so P/E exploded:

```
2019-06   21,732
2019-09    1,427
2021-03      660
2022-06      525
```

The existing `.where(EPS > 0)` mask only catches *negative* earnings. It does nothing for earnings that are positive but negligible.

A P/E of 500 is not "very expensive". It means the company barely earns anything, and the metric has stopped conveying information about valuation.

**Fix**

Cap all valuation multiples at 200 in `build_valuation_history` and `calculate_historical_pe`:

```python
MAX_MULTIPLE = 200
for col in ["pe_ratio", "pb_ratio", "pfcf_ratio", "ev_ebitda", "ev_sales"]:
    wide[col] = wide[col].where(wide[col] <= MAX_MULTIPLE)
```

`dividend_yield` is excluded — it has no meaningful upper bound in that range.

This is a pragmatic threshold, not a principled one. The defensible version would mask based on the *denominator* (e.g. discard P/E when net margin < 1%), but the outcome is nearly identical and the added complexity isn't worth it.

**Follow-on fix:** `calculate_rolling_average` returned `NaN` for the whole window as soon as a single masked value fell inside it — pandas' default `min_periods` equals the window size. Set `min_periods=1` so the average is computed from whatever valid values exist.

**Trade-off:** young companies now get a "5-year average" based on fewer than 20 quarters. More useful than no value at all, but it should be read with that in mind.

**Result:** `avg_pe_5y` for NOW went `NaN` → `247` → **104.9**, which is a usable reference.

---

## Earlier fixes

Documented inline in the module docs rather than here, because they shaped the architecture rather than patching it:

| Bug | Module doc |
|---|---|
| The `fp` field mislabels quarters as `FY` | `edgar_doc.md` |
| Cash flow items reported cumulatively (YTD) | `edgar_doc.md` |
| Q4 never filed separately | `edgar_doc.md` |
| Multiple units per concept (`pure` vs `USD/shares`) | `edgar_doc.md` |
| Tag changes over time (ASC 606) | `parse_edgar_doc.md` |
| D&A split into components at Microsoft | `parse_edgar_doc.md` |
| `period` parameter not passed through in `sum` mode | `parse_edgar_doc.md` |
| Single quarters distorted by one-off events | `metrics_doc.md` |
| Growth rates exploding on negative base | `metrics_doc.md` |
| Missing concepts invisible to the quality check | `quality_doc.md` |

---

## Pattern

Seven tickers, seven different failure modes. Almost none of them crashed; all of them produced plausible-looking wrong numbers.

What consistently worked:

1. **Notice that a number is impossible**, not merely surprising. A negative average P/E. A negative EPS with positive net income. A share count that quintuples and then reverts.
2. **Look at the raw filings**, not the derived DataFrame. Every one of these bugs was visible in the EDGAR JSON and invisible in pandas.
3. **Find the discriminant.** Every successful fix here rests on one structural property that separates good data from bad — period length, start-date alignment, proximity to a split factor. Heuristics applied to the *output* (outlier filters, thresholds) mostly failed. Rules derived from the *structure of the input* held.