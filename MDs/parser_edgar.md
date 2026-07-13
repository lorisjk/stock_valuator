# `parsers/parse_edgar.py`

## Overview

The assembly layer between raw EDGAR extraction and the working DataFrame.

`fetchers/edgar.py` knows how to read **one** XBRL tag correctly. This module knows how to combine **several tags into one logical concept**, and how to turn a whole company's worth of concepts into a table.

It contains no network code and no knowledge of the EDGAR JSON structure. It works purely on the lists of `{end, value, filed}` dicts that the fetcher returns.

---

## Functions

| Function | Purpose | Output |
|---|---|---|
| `extract_merged_values` | Tries candidate tags in priority order, first hit per period wins | `list[dict]` |
| `extract_with_mode` | Dispatches to the right combination strategy based on `mode` | `list[dict]` |
| `build_dataframe` | All configured concepts for one ticker → sorted long-format table | `DataFrame` with `ticker`, `concept`, `end`, `value` |

---

## The tag problem

The same financial concept does not have one stable XBRL tag. Three distinct situations occur, and each needs different handling.

### Situation 1: tags change over time → `fallback`

Revenue was reported under `Revenues` before the ASC 606 accounting change in 2018, and under `RevenueFromContractWithCustomerExcludingAssessedTax` afterwards. During the transition, some companies reported both.

`extract_merged_values` walks the candidate list in order and keeps, for each period, the value from the **first tag that has one**:

```python
for v in values:
    if v["end"] in merged:
        continue
    merged[v["end"]] = {...}
```

Once a period is filled, later tags cannot overwrite it. This means the ordering of `tags` in the config is a priority ranking — put the current/preferred tag first, older ones after.

The result is a complete time series with no duplicates: recent years come from the new tag, older years from the old one, and transition years (where both exist) use the higher-priority tag only.

### Situation 2: tags coexist and must be added → `sum`

Total debt is not one tag. It is the sum of `LongTermDebtNoncurrent`, `LongTermDebtCurrent`, `ConvertibleDebtNoncurrent` and `ConvertibleDebtCurrent` — four positions that exist **simultaneously** and each represent part of the total.

Using fallback here would silently understate debt, because only the first tag found would be used.

### Situation 3: a total exists for some companies, but must be assembled for others → `fallback_sum`

Apple and NVIDIA report `DepreciationDepletionAndAmortization` as a single figure. Microsoft does not — it splits the number into `Depreciation` and `AmortizationOfIntangibleAssets`.

Neither pure strategy works:
- Pure `fallback` on all four tags would pick up only one component for Microsoft (understating D&A).
- Pure `sum` on all four would double-count for Apple (the total plus its own components).

`fallback_sum` resolves this: try the primary tags (the true totals) first; only if **none** of them yields any data, fall back to summing the component tags.

```python
values = extract_merged_values(us_gaap_data, cfg["tags"], ...)

if mode == "fallback_sum" and not values:
    values = extract_summed_values(us_gaap_data, cfg["fallback_sum_tags"], ...)
```

The check is deliberately strict (`not values`, i.e. completely empty). For this to work, the component tags must be listed **only** under `fallback_sum_tags`, never under `tags` — otherwise the primary lookup would find a partial component, consider itself successful, and never trigger the summation.

---

## Configuration-driven design

`build_dataframe` contains no concept-specific logic. All knowledge about which tags belong to which concept, whether it is a balance-sheet or a period value, and how multiple tags combine, lives in `CONCEPT_CANDIDATES` in `config.py`:

```python
"<logical name>": {
    "tags": [...],                    # primary candidates, in priority order
    "fallback_sum_tags": [...],       # only for mode="fallback_sum"
    "point_in_time": bool,            # True = balance sheet date, False = period
    "mode": "fallback" | "sum" | "fallback_sum",
}
```

Adding a new concept means adding a dict entry — no code changes.

---

## Sorting at the end

Python dicts preserve insertion order, and `extract_merged_values` fills its dict tag by tag. With a fallback concept, the newer tag's periods (e.g. 2018–2026) get inserted before the older tag's periods (e.g. 2008–2017). The raw output is therefore **not** chronological.

`sort_values(["ticker", "concept", "end"])` fixes this explicitly; `reset_index(drop=True)` renumbers the rows cleanly afterwards.

This looked like a bug on first inspection. It was not — every period was present exactly once, just out of order. Confirming that with an explicit duplicate check (`df.duplicated(...)`) rather than eyeballing the output is a habit worth keeping.

---

## Common pitfalls

**Losing the dict key.** When merging into a dict keyed by `end`, the date lives in the **key**, not the value. Returning `list(merged.values())` silently drops it. It has to be put back explicitly.

**Redundant inner loops.** An early version manually iterated the candidate tags inside `build_dataframe` before calling the extraction function — which already does exactly that. The manual loop also overwrote its own variable on each pass, so only the last candidate was ever checked, regardless of whether an earlier one had data.

**Using the tag name instead of the logical name.** The `concept` column must hold the stable name from the config (`"Revenue"`), not whichever tag happened to supply the data (`"SalesRevenueNet"`). Otherwise the same concept appears under different names for different tickers.

**Forgetting to pass `period` through.** `extract_summed_values` defaults to `period="annual"`. An earlier version called it from the quarterly branch without passing the parameter, so `LongTermDebt` silently came back as annual data (12 rows instead of 45) while everything else was quarterly. Nothing crashed; the downstream merge just produced almost no rows. This class of bug is why the data quality check in `quality.py` exists.