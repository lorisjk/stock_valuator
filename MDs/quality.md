# `quality.py`

## Overview

A diagnostic check that runs after extraction and reports concepts that are missing or thinly populated for a given ticker.

This exists because the failure mode of this pipeline is **silent**. When a tag is missing, nothing crashes. The extraction returns an empty list, the merge finds no matching rows, the metric comes out empty, and the chart draws an axis labelled "1970". The bug surfaces three layers away from its cause, looking like a plotting problem.

The check turns that into an immediate, explicit message.

---

## Functions

| Function | Purpose |
|---|---|
| `check_data_quality` | Returns a DataFrame of problematic concepts |
| `print_data_quality` | Human-readable console output |

---

## How it works

### Coverage relative to the best-populated concept

There is no absolute expectation for how many rows a concept should have — it depends on how far back the company's filings go. What *is* meaningful is the comparison within a ticker: if `Revenue` has 71 quarters and `DepreciationAndAmortization` has 7, something is wrong with D&A specifically.

```python
counts["max_for_ticker"] = counts.groupby("ticker")["count"].transform("max")
counts["ratio"] = counts["count"] / counts["max_for_ticker"]
```

`.transform("max")` broadcasts each ticker's maximum row count back onto every row of that ticker, so the ratio can be computed column-wise. (`.max()` would collapse to one value per ticker and could not be assigned back.)

Anything below `threshold` (default 50%) is reported.

### Checking against expectations, not against what's present

The first version of this check only looked at what was already in the DataFrame. That made it blind to the worst case: a concept with **zero** rows never appears in a `groupby` result, so it could not be flagged.

This is not hypothetical. For JPM, `OperatingIncomeLoss`, `LongTermDebt` and `Capex` have no rows at all. The check reported nothing, while five of nine charts came out empty.

The fix is to pass in the expected concepts — the keys of `CONCEPT_CANDIDATES` — and explicitly synthesize a `count = 0` row for anything absent:

```python
for ticker in df["ticker"].unique():
    present = set(counts[counts["ticker"] == ticker]["concept"])
    for concept in set(expected_concepts) - present:
        missing_rows.append({"ticker": ticker, "concept": concept, "count": 0})
```

Missing concepts are marked `FEHLT` in the output, thin ones `duenn`. The distinction matters — see below.

---

## Interpreting the output

Two very different causes produce a warning, and they call for opposite responses.

### `FEHLT` / `duenn` because a tag is missing from the config

The company reports the concept, just under a tag not yet in `CONCEPT_CANDIDATES`. **This is fixable.** Find the tag and add it:

```python
for key in company_info["facts"]["us-gaap"].keys():
    if "Revenue" in key:
        print(key)
```

Examples encountered:
- Microsoft splits D&A into `Depreciation` + `AmortizationOfIntangibleAssets` instead of reporting a combined figure → solved with `mode: "fallback_sum"`
- Walmart reports EPS under two units (`pure` and `USD/shares`) → the extraction was taking the first unit blindly and reading garbage
- NVIDIA uses `PaymentsToAcquireProductiveAssets` in years where `PaymentsToAcquirePropertyPlantAndEquipment` is absent

### `FEHLT` because the concept does not apply

The company genuinely does not report the item, because its business model has no such thing. **This is not fixable, and should not be.**

JPMorgan has no operating income in the industrial sense, no capex worth speaking of, and no "long-term debt" as a burden to be minimized — debt is the raw material of a bank. Consequently EV/EBITDA, Net Debt/EBITDA, Rule of 40 and FCF margin are meaningless for it, regardless of how many tags are added.

The correct response is to accept the gap. `figures.py` renders these subplots as "keine Daten", which is the honest answer.

### `duenn` because of a genuine data gap

Sometimes the tag is right and the company simply did not report the item in every filing. Apple's D&A only appears in 10-Qs from 2017 onward (46% coverage). Nothing is broken; the history is just shorter for that concept.

---

## Where it runs

Called in `main.py` immediately after extraction:

```python
print_data_quality(facts, list(CONCEPT_CANDIDATES.keys()))
```

Best placed **before** `add_ttm_concepts`. Otherwise the derived `_TTM` concepts show up in the output as unexpected extras and inflate the row counts, making the report noisier than it needs to be.

---

## Why this is the module that makes the tool generic

Everything else in the project is written to work for any ticker. This module is what tells you whether it actually did.

Without it, adding a new company means either trusting that the tag configuration happens to cover it, or discovering the gaps one broken chart at a time. With it, adding a company produces an immediate list of what is missing and what is merely absent — which is the difference between a tool you can point at an arbitrary ticker and a tool that happens to work for three.