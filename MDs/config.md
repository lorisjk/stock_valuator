# `config.py`

## Overview

All configuration lives here. No other module hardcodes tickers, tag names, or paths.

The centrepiece is `CONCEPT_CANDIDATES`, which maps each logical financial concept to the XBRL tags that might carry it, and specifies how to combine them. Adding a concept or supporting a new company means editing this dict — not the extraction code.

---

## Settings

| Name | Purpose |
|---|---|
| `TICKERS` | Which companies to analyze |
| `EDGAR_USER_AGENT` | Required by SEC. Must contain a real name and email, or requests are rejected with 403 |
| `PERIOD` | `"quarterly"` or `"annual"` — controls the entire extraction pipeline |
| `CONCEPT_CANDIDATES` | Tag mapping and combination strategy per concept |
| `TTM_CONCEPTS` | Which concepts get a trailing-twelve-month series |
| `CACHE_DIR` / `DATA_DIR` / `FIGURE_DIR` | Output paths |

---

## `CONCEPT_CANDIDATES`

Each entry has this shape:

```python
"<logical name>": {
    "tags": [...],                    # primary candidates, in priority order
    "fallback_sum_tags": [...],       # only when mode == "fallback_sum"
    "point_in_time": bool,
    "mode": "fallback" | "sum" | "fallback_sum",
}
```

### `tags` — order matters

The list is a priority ranking, not a set. For each period, the extraction takes the value from the **first tag that has one** and ignores the rest.

Put the current or preferred tag first. Example: `RevenueFromContractWithCustomerExcludingAssessedTax` (post-2018 standard) before `Revenues` (pre-2018) before `SalesRevenueNet` (legacy).

### `point_in_time`

`False` — a **period** value covering a span of time (revenue, income, cash flow). Additive. Gets decumulated and Q4-derived.

`True` — a **balance sheet** value at a single date (equity, debt, cash). Not additive. Taken as reported, with no differencing.

**`SharesOutstanding` is set to `True` despite being a period average.** This is deliberate. Share counts must never be summed across quarters (you'd get four times the real count) nor differenced (the difference between two similar averages is meaningless). Marking it `point_in_time` bypasses both operations and takes each reported value as-is, which is the desired behavior.

### `mode`

**`fallback`** — take the first tag that has data. For concepts whose tag changed over time.

**`sum`** — add all tags together. For concepts that genuinely consist of multiple coexisting parts. `LongTermDebt` is the only one: total debt = long-term + current + convertible long-term + convertible current.

**`fallback_sum`** — try the totals first; if none of them yields any data, sum the components instead. Only `DepreciationAndAmortization` needs this: Apple and NVIDIA report a single `DepreciationDepletionAndAmortization` figure, Microsoft splits it into `Depreciation` and `AmortizationOfIntangibleAssets`.

The component tags must appear **only** under `fallback_sum_tags`, never under `tags`. Otherwise the primary lookup would find one component, consider the job done, and never sum the rest — which is exactly what happened with Microsoft before this mode existed (7 rows instead of 71).

---

## `TTM_CONCEPTS`

Concepts listed here get an additional `<name>_TTM` series: a rolling four-quarter sum.

Why this matters: single quarters are extremely sensitive to one-off events. Microsoft's Q4 2012 was a *loss* because of the aQuantive goodwill write-off. Computing operating margin, ROE or growth from that one quarter produces values like -1100% — mathematically correct, analytically useless. A trailing-twelve-month figure absorbs the shock across three normal quarters.

All ratio metrics in the project are therefore built on `_TTM` concepts, not on raw quarters. Pure balance-sheet ratios (`debt_to_equity`) are the exception — there is nothing to sum.

**Note which concepts are absent from this list:**

- **`EPS`** — a per-share value. Summing four quarterly EPS figures breaks across stock splits, because EDGAR restates per-share numbers retroactively but not uniformly across filings. Instead, `EPS_TTM_CALC` is computed in `main.py` as `NetIncomeLoss_TTM / SharesOutstanding`. Both inputs are absolute figures, so splits cannot corrupt them.
- **`SharesOutstanding`** — must never be summed (see above).
- **`StockholdersEquity`, `LongTermDebt`, `CashAndEquivalents`** — balance sheet positions. A TTM sum of four quarterly equity balances would be nonsense.

`DividendsPerShare` **is** in the list, and technically has the same per-share split problem as EPS. It stays because there is no absolute equivalent in EDGAR to reconstruct it from. Negative values (an artifact of the split issue) are masked out downstream in `build_valuation_history`.

---

## Adding a new ticker

Add it to `TICKERS` and run. The data quality check in `quality.py` will report any concept that is missing or thinly populated for that company.

Two things it may reveal:

**Missing tags** — the company uses a tag not yet in `CONCEPT_CANDIDATES`. Find it by listing the available keys:

```python
for key in company_info["facts"]["us-gaap"].keys():
    if "Revenue" in key:
        print(key)
```

Then add it to the appropriate `tags` list.

**Structurally absent concepts** — the company genuinely does not report the item. Banks (e.g. JPM) have no `OperatingIncomeLoss`, no `Capex`, and no `LongTermDebt` in the conventional sense. Their debt is their product, not a liability to be minimized. No amount of tag hunting will fix that; the affected metrics (EV/EBITDA, Net Debt/EBITDA, Rule of 40) simply do not apply to financial companies.