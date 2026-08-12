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
| `print_data_quality` | Human-readable console output, **or** structured collection |
| `search_tags` | Every `us-gaap` tag whose name contains one of the given keywords |

### `expected_concepts` is a dict, despite the annotation

`print_data_quality(df, expected_concepts: list[str], ...)` is annotated as a list and is
called with a **dict** — `{ticker: [concept, ...]}`, built by
`config.get_expected_concepts(ticker)`. `check_data_quality` reads it as
`expected_concepts_by_ticker.get(ticker, [])`, which is correct; only the annotation on
the printing wrapper is stale. Expectations are per ticker because they depend on the
profile: a bank is not expected to report `Capex`.

### `collect_flags` short-circuits the printing

Passing a list to `collect_flags` makes the function append one dict per problem and
**return before printing anything**. That is how `run_full_refresh` gathers the coverage
warnings for its run report while keeping the console quiet. The two modes are mutually
exclusive by construction — there is no way to get both.

`search_hints` (from `config.SEARCH_HINTS`) is carried through either way: in printing
mode it renders a ready-to-run `python explore_tags.py TICKER keyword...` line under each
warning, and in collection mode it lands in the `hint` field.

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

Missing concepts are marked `MISSING ` in the output, thin ones `thin `. The distinction matters — see below.

---

## Interpreting the output

Two very different causes produce a warning, and they call for opposite responses.

### `MISSING` / `thin` because a tag is missing from the config

The company reports the concept, just under a tag not yet in `CONCEPT_CANDIDATES`. **This is fixable.** Find the tag and add it:

```python
for key in company_info["facts"]["us-gaap"].keys():
    if "Revenue" in key:
        print(key)
```

Examples encountered:
- Microsoft splits D&A into `Depreciation` + `AmortizationOfIntangibleAssets` instead of reporting a combined figure → solved by listing both under one concept's `tags`
- Walmart reports EPS under two units (`pure` and `USD/shares`) → the extraction was taking the first unit blindly and reading garbage
- NVIDIA uses `PaymentsToAcquireProductiveAssets` in years where `PaymentsToAcquirePropertyPlantAndEquipment` is absent

### `MISSING` because the concept does not apply

The company genuinely does not report the item, because its business model has no such thing. **This is not fixable, and should not be.**

JPMorgan has no operating income in the industrial sense, no capex worth speaking of, and no "long-term debt" as a burden to be minimized — debt is the raw material of a bank. Consequently EV/EBITDA, Net Debt/EBITDA, Rule of 40 and FCF margin are meaningless for it, regardless of how many tags are added.

The correct response is to accept the gap. Where the profile does not already hide the metric, `figures.py` renders the panel as "No Data", which is the honest answer.

### `thin` because of a genuine data gap

Sometimes the tag is right and the company simply did not report the item in every filing. Apple's D&A only appears in 10-Qs from 2017 onward (46% coverage). Nothing is broken; the history is just shorter for that concept.

---

## Where it runs

Called in `main()` and in `run_full_refresh()` immediately after extraction:

```python
expected_by_ticker = {ticker: get_expected_concepts(ticker) for ticker in active_tickers}
print_data_quality(facts, expected_by_ticker, SEARCH_HINTS, collect_flags=quality_flags)
```

Placed **before** `add_derived_concepts`, and that position has a consequence beyond
tidiness. It was chosen so the derived `_TTM` concepts do not show up as unexpected extras
and inflate the row counts — but it also means **a coverage warning counts base-concept
rows only**. Recovering a `_TTM` series downstream (the annual-fact path, for instance)
cannot clear a flag here, because the flag was never about the derived series. Expect the
counts to be unmoved by any change that only adds derived values.

---

## Why this is the module that makes the tool generic

Everything else in the project is written to work for any ticker. This module is what tells you whether it actually did.

Without it, adding a new company means either trusting that the tag configuration happens to cover it, or discovering the gaps one broken chart at a time. With it, adding a company produces an immediate list of what is missing and what is merely absent — which is the difference between a tool you can point at an arbitrary ticker and a tool that happens to work for three.