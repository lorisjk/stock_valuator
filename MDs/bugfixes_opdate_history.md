# Bugfix History

A running log of bugs found, what caused them, and how they were fixed. Ordered newest first.

Most entries here share a theme: **the pipeline fails silently**. A missing tag returns an empty list, an empty list produces an empty merge, an empty merge produces an empty chart. Nothing crashes. The symptom appears several layers away from the cause, and usually looks like a plotting problem. Every fix below was found by noticing that a *number* looked wrong, not by reading a stack trace.

---

## 2026-07-13

Triggered by adding **ServiceNow (NOW)** as a test ticker. Four distinct bugs, all surfaced by the same company.

### 1. Missing concept crashes `build_valuation_history`

**Symptom**
```
KeyError: 'DividendsPerShare_TTM'
```

**Cause**
ServiceNow pays no dividend, so `DividendsPerShare` has zero rows in `facts`. `pivot_table` only creates columns for concepts that actually have data — so the column did not exist at all, rather than existing and being full of `NaN`. The subsequent `wide["DividendsPerShare_TTM"]` then failed.

This would have happened for any missing concept, not just dividends.

**Fix**
Fill missing columns with `pd.NA` after the pivot:

```python
for concept in needed:
    if concept not in wide.columns:
        wide[concept] = pd.NA
```

The affected multiple becomes `NaN`, gets removed by the final `dropna`, and the chart correctly shows "keine Daten". A company that pays no dividend has no dividend yield — that is the right answer, not an error.

---

### 2. Debt understated — missing tag variants

**Symptom**
Data quality check reported `LongTermDebt` at 17% coverage (11 of 63 rows).

**Cause**
ServiceNow finances itself partly through convertible notes and names them `ConvertibleLongTermNotesPayable` / `ConvertibleNotesPayableCurrent` — not `ConvertibleDebtNoncurrent` / `ConvertibleDebtCurrent`, which were the only convertible tags in the config.

**Fix**
Added both tags to the `LongTermDebt` summation list in `config.py`.

Verified afterwards that the total lands at ~1.49bn, matching ServiceNow's actual debt — no double counting from the two tag families overlapping.

**Note:** `mode: "sum"` always carries double-counting risk when adding tag variants. Check the resulting magnitude against a known figure before trusting it.

---

### 3. Share count oscillating between two bases (stock split)

**Symptom**
`SharesOutstanding` for NOW alternated wildly:

```
2023-06   204,690,000
2023-09   205,194,000
2023-12 1,027,953,000   ← ×5
2024-03   207,684,000
2024-06   207,740,000
2024-09   208,004,000
2024-12 1,042,113,000   ← ×5
2025-03 1,046,852,000   ← ×5
2025-06   209,343,000
...
```

Downstream, this broke market cap, and with it P/B, P/FCF, EV/Sales and EV/EBITDA — all of which zigzagged by a factor of five between adjacent quarters. `EPS` (the raw EDGAR concept) also went **negative while net income was positive**, which is impossible.

**Cause**
ServiceNow executed a **5:1 stock split in 2025**. The raw filings show this clearly:

```
val:   208,423,000   filed: 2025-01-30   (FY2024 10-K)
val: 1,042,113,000   filed: 2026-01-29   (FY2025 10-K, restating FY2024)
```

Same period, same form, same unit — two different values. The later one is the **correct, split-adjusted** restatement.

The deduplication logic (`later filed date wins`) was working correctly. The problem is that EDGAR only restates the periods that appear as **comparatives** in the newest filing. Everything older keeps its pre-split values from the original 10-Qs. The result is a time series with two incompatible bases interleaved.

The negative EPS came from the same source: `decumulate_period_values` was subtracting three pre-split quarters from a post-split annual figure.

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

**Consequence:** the raw `EPS` concept is no longer needed at all. `EPS_TTM_CALC = NetIncomeLoss_TTM / SharesOutstanding` now uses two split-consistent absolute quantities. Removed `EPS` from `CONCEPT_CANDIDATES`.

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

**Trade-off:** young companies now get a "5-year average" based on fewer than 20 quarters. That is more useful than no value at all, but it should be read with that in mind.

---

### Result

`avg_pe_5y` for NOW went from `NaN` → `247` → **104.9**, which is a usable reference. Current P/E of 63.7 reads as roughly 40% below the company's own five-year average — which is the comparison the entire tool exists to produce.

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