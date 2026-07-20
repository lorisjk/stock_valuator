# Task: Pharma/Medtech Tag Coverage Scan (47 tickers)

JNJ is the verified reference ticker for the `pharma_medtech` profile. Its one new concept
(`ResearchAndDevelopment`, tags `ResearchAndDevelopmentExpense` /
`ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost`) and one new metric
(`rd_intensity`) are built and confirmed correct. JNJ also surfaced a known, now-mitigated
issue — `OperatingIncomeLoss` is structurally thin/discontinued for JNJ, which cascades into
`net_debt_to_ebitda` and `ev_ebitda` (both depend on `EBITDA_TTM = OperatingIncomeLoss_TTM +
D&A_TTM`). All three are already hidden for this profile — see Step 0. The goal here is the
same as every prior scan task: check whether the same tag names give clean, complete
coverage for the other 47 `pharma_medtech` tickers, and resolve one open structural question
about a subset that may not belong in this profile at all.

## Step 0 — Setup

Apply the already-decided config changes first, before scanning anything:

```python
TICKER_PROFILES = {
    ...,
    "ABT": "pharma_medtech", "ABBV": "pharma_medtech", "A": "pharma_medtech",
    "ALGN": "pharma_medtech", "AMGN": "pharma_medtech", "BAX": "pharma_medtech",
    "BDX": "pharma_medtech", "TECH": "pharma_medtech", "BIIB": "pharma_medtech",
    "BSX": "pharma_medtech", "BMY": "pharma_medtech", "CRL": "pharma_medtech",
    "COO": "pharma_medtech", "DHR": "pharma_medtech", "DVA": "pharma_medtech",
    "DXCM": "pharma_medtech", "EW": "pharma_medtech", "GEHC": "pharma_medtech",
    "GILD": "pharma_medtech", "HCA": "pharma_medtech", "IDXX": "pharma_medtech",
    "PODD": "pharma_medtech", "IQV": "pharma_medtech", "ISRG": "pharma_medtech",
    "LH": "pharma_medtech", "LLY": "pharma_medtech", "MDT": "pharma_medtech",
    "MRK": "pharma_medtech", "MTD": "pharma_medtech", "PFE": "pharma_medtech",
    "REGN": "pharma_medtech", "RMD": "pharma_medtech", "RVTY": "pharma_medtech",
    "SOLV": "pharma_medtech", "STE": "pharma_medtech", "SYK": "pharma_medtech",
    "TMO": "pharma_medtech", "UHS": "pharma_medtech", "VEEV": "pharma_medtech",
    "VTRS": "pharma_medtech", "VRTX": "pharma_medtech", "WAT": "pharma_medtech",
    "WST": "pharma_medtech", "ZBH": "pharma_medtech", "ZTS": "pharma_medtech",
    "CVS": "pharma_medtech", "DGX": "pharma_medtech",
}

PROFILE_EXCLUDED_CONCEPTS = {
    ...,
    "pharma_medtech": {"OperatingIncomeLoss"},
    # same reasoning as "retail" excluding Goodwill: with operating_margin,
    # net_debt_to_ebitda, and ev_ebitda all hidden below, no visible metric in this
    # profile depends on OperatingIncomeLoss anymore — excluding it stops
    # check_data_quality from flagging a gap nothing actually uses.
    # NOTE: verify DepreciationAndAmortization isn't in the same position (only
    # feeds the same now-hidden EBITDA chain) before excluding it too — check
    # whether any other visible metric touches it first. If none do, exclude it
    # the same way and say so in the report; if something does, leave it in.
}

PROFILE_HIDDEN = {
    ...,
    "pharma_medtech": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "rule_of_40",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "operating_margin", "net_debt_to_ebitda", "ev_ebitda",
    },
}
```

**Confirm MRNA and INCY are NOT in this list.** Both are flagged Group 5 candidates
(pre-profit / high earnings volatility biotech) from the original sector categorization and
are explicitly out of scope for this batch.

## Step 1 — Coverage scan

For each of the 47 tickers, run `check_data_quality` using `get_expected_concepts(ticker)`.
Flag anything below 50% coverage, with these expected exceptions — check each directly
rather than assuming, same discipline as the retail AccountsReceivable check:

- `DividendsPerShare` — standard non-payer exception, verify per ticker rather than assume.
- `ResearchAndDevelopment` at or near 0% for the health-services/diagnostics names in this
  batch: **DGX, LH, HCA, DVA, UHS, CVS**. These aren't innovation-driven pharma/medtech —
  they're service providers, and near-zero R&D is a real business characteristic, not a
  missed tag. If any of these six show unexpectedly high R&D coverage, that's worth a second
  look (could mean the tag is capturing something else), not an automatic pass.

## Step 2 — Structural question: does the life-science-tools/diagnostics subset actually fit here?

**A, TECH, CRL, IQV, MTD, RVTY, WAT, TMO** (life science tools/CRO) and **DGX, LH, HCA, DVA,
UHS, CVS** (diagnostics/health services) were folded into `pharma_medtech` provisionally —
their revenue/margin structure was assumed close enough to pharma/medtech to not need a
separate profile yet, but this was never verified against real data.

1. For all 14, compare their revenue growth, margin stability, and (per Step 1) R&D profile
   against the core pharma/medtech names (JNJ, LLY, MRK, PFE, ABT, MDT, SYK...).
2. **Do not reassign any of these to a new profile yourself.** Same rule as the
   consumer_staples task: report your findings as a clearly separated recommendation
   section — which of the 14, if any, look different enough (in metric behavior or
   available tags) to warrant their own profile later — and leave them assigned to
   `pharma_medtech` in the actual config for now.

## Step 3 — For each flagged concept, search and evaluate candidates

Reuse the established methodology from every prior scan. One specific trap carried over
from JNJ:

- **Diversified-conglomerate `OperatingIncomeLoss` fragility is now a confirmed recurring
  pattern** (JNJ here; NKE/ADM/BG/CASY/CLX never tag it; GPC/TJX/ROST discontinue it). Since
  this concept is now excluded for the whole profile (Step 0), do not spend time hunting for
  a successor tag or a segment-based reconstruction for it anywhere in this batch — it's
  already handled by exclusion, not something to fix per ticker.
- **Segment reporting caution for large diversified names** (ABT, DHR, BDX, TMO, BAX in
  particular run multiple distinct business lines): same rule as MET/PRU/GPC before — verify
  a segment-level sum actually reconciles to a consolidated figure before treating it as
  equivalent to a clean consolidated tag.

## Step 4 — Mode decisions, if needed

Same authorization and same condition as every prior task: any `fallback` or
`priority_merge` migration is allowed only if the mandatory non-regression check (Step 5)
passes for every single change. Revert and log anything that fails it instead of forcing
it through.

## Step 5 — Mandatory non-regression check (same rule as every prior task, no exceptions)

1. Extract every affected concept for **all** cached tickers (JNJ included, as the trusted
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

After all safe changes are applied, re-run `check_data_quality` on the 47 tickers. Produce
a before/after coverage table, plus a summary: fully resolved, improved-but-not-clean, and
unchanged (with the specific reason per unchanged concept, including the expected R&D
exceptions from Step 1).

## Output

One file, `pharma_medtech_scan_report.md`: the scan findings, what was changed and why
(including whether `DepreciationAndAmortization` was also excluded and why/why not), the
Step 2 recommendation on the 14 life-science-tools/diagnostics tickers (findings only, no
reassignment performed), the non-regression check results (including anything reverted),
and the before/after coverage table.

No scratch scripts left behind. Do not touch any ticker outside these 47, do not reassign
any ticker's profile, and do not touch any concept unrelated to `pharma_medtech`'s metric
set.