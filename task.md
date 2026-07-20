# Task: Consumer Staples Tag Coverage Scan (33 tickers)

KO is the verified reference ticker for the `consumer_staples` profile. Its full concept
set is inherited unchanged from the base `CONCEPT_CANDIDATES` (no new tags, no
`PROFILE_CONCEPT_OVERRIDES` entry needed) — the profile exists only to branch the hidden-
metric logic away from `standard`. The goal here is the same as every prior scan task:
check whether the same tag names give clean, complete coverage for the other 33
`consumer_staples` tickers, and where they don't, find and safely apply replacements —
plus resolve two open structural questions before treating the batch as done.

## Step 0 — Setup

1. Apply the already-decided config change first, before scanning anything:

```python
TICKER_PROFILES = {
    ...,
    "MO": "consumer_staples", "ADM": "consumer_staples", "BF.B": "consumer_staples",
    "BG": "consumer_staples", "CPB": "consumer_staples", "CASY": "consumer_staples",
    "CHD": "consumer_staples", "CLX": "consumer_staples", "CAG": "consumer_staples",
    "STZ": "consumer_staples", "COST": "consumer_staples", "DG": "consumer_staples",
    "DLTR": "consumer_staples", "EL": "consumer_staples", "GIS": "consumer_staples",
    "HSY": "consumer_staples", "HRL": "consumer_staples", "KVUE": "consumer_staples",
    "KDP": "consumer_staples", "KMB": "consumer_staples", "KHC": "consumer_staples",
    "KR": "consumer_staples", "MKC": "consumer_staples", "TAP": "consumer_staples",
    "MDLZ": "consumer_staples", "MNST": "consumer_staples", "PEP": "consumer_staples",
    "PM": "consumer_staples", "PG": "consumer_staples", "SJM": "consumer_staples",
    "SYY": "consumer_staples", "TGT": "consumer_staples", "TSN": "consumer_staples",
    "WMT": "consumer_staples",
}

PROFILE_HIDDEN = {
    ...,
    "consumer_staples": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "rule_of_40",
    },
}
```

2. **Ticker string check — do this before any fetching.** `BF.B` (Brown-Forman) contains a
   period. Confirm how `build_ticker_to_cik` / the SEC ticker mapping / the yfinance fetcher
   each handle this string — some sources expect `BF-B`, some expect `BF.B`, some may need
   URL-escaping. Resolve this for one ticker in isolation before including it in any batch
   run; if the mapping fails silently (returns no CIK, or a wrong one), that's worse than an
   explicit error. Report exactly what worked.

## Step 1 — Coverage scan

For each of the 33 tickers, run `check_data_quality` using `get_expected_concepts(ticker)`.
Flag anything below 50% coverage, with the standard `DividendsPerShare` non-payer exception
(check which of these 33 are genuinely non-payers before excluding — do not assume based on
company reputation alone, several staples names have paused or initiated dividends within
the tagged history).

## Step 2 — Structural question: six of these may not belong in `consumer_staples`

**COST, TGT, WMT, DG, DLTR, KR** are GICS-classified as Consumer Staples (product category),
but operationally they're merchandise retailers — real inventory, real COGS, potentially the
same working-capital dynamics already built for the `retail` profile (`Inventory`,
`CostOfRevenue`, `AccountsReceivable`, `AccountsPayable`, `inventory_turnover`, `dio`,
`dso`, `dpo`, `cash_conversion_cycle`).

For these six specifically:

1. Run the same `explore_tags.py` check used to build the `retail` profile — do
   `InventoryNet` and `CostOfGoodsAndServicesSold` (or their fallback variants) give clean,
   complete coverage for all six the same way they did for the 19 `retail` tickers?
2. **Do not reassign these six to `retail` yourself.** This is a profile-taxonomy decision
   with downstream effects (which charts they appear in, which metrics apply) that needs a
   human call, not an autonomous change. Report your findings — tag coverage results plus
   your read on whether their working-capital dynamics actually resemble the 19 `retail`
   tickers or are different enough to stay put — as a clearly separated recommendation
   section, and leave them assigned to `consumer_staples` in the actual config for now.

## Step 3 — For each flagged concept (outside the six above), search and evaluate candidates

Reuse the established methodology from every prior scan (P&C, insurance_life, retail).
No consumer-staples-specific traps are known yet — this batch was chosen precisely because
it was expected to be the cleanest. If you find a trap worth naming for future batches,
document it in the report explicitly rather than silently working around it.

## Step 4 — Mode decisions, if needed

Same authorization and same condition as every prior task: any `fallback` or
`priority_merge` migration is allowed only if the mandatory non-regression check (Step 5)
passes for every single change. Revert and log anything that fails it instead of forcing
it through.

## Step 5 — Mandatory non-regression check (same rule as every prior task, no exceptions)

1. Extract every affected concept for **all** cached tickers (KO included, as the trusted
   reference, plus every ticker from every other profile already built) under the old
   config and the new one.
2. Diff every `(ticker, concept, end)` value. Zero tolerance: any previously-populated
   value that changes or disappears means that specific addition is wrong — revert it, log
   exactly which ticker/date/concept was affected and why.
3. Only previously-null values may newly appear — report this as the expected, good
   outcome.
4. If you can't cleanly explain a discrepancy, don't proceed — log it as ambiguous rather
   than guessing which value is "correct."

## Step 6 — Coverage re-check

After all safe changes are applied, re-run `check_data_quality` on the 33 tickers. Produce
a before/after coverage table, plus a summary: fully resolved, improved-but-not-clean, and
unchanged (with the specific reason per unchanged concept).

## Output

One file, `consumer_staples_scan_report.md`: the `BF.B` ticker-handling resolution, the
scan findings, what was changed and why, the Step 2 recommendation on the six
retail-like tickers (findings only, no reassignment performed), the non-regression check
results (including anything reverted), and the before/after coverage table.

No scratch scripts left behind. Do not touch any ticker outside these 33, do not reassign
any ticker's profile, and do not touch any concept unrelated to `consumer_staples`'s metric
set.