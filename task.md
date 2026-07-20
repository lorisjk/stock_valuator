# Task: Split `health_services` Out of `pharma_medtech` (6 tickers)

The pharma/medtech scan recommended splitting DGX, LH, HCA, DVA, UHS, CVS into their own
profile — R&D intensity is essentially zero across all six (a genuine business-model
difference, not a data gap), and margin structure (CVS in particular) looks qualitatively
different from core pharma/medtech. This task executes that split. Life-science-tools/CRO
(A, TECH, CRL, IQV, MTD, RVTY, WAT, TMO) stays in `pharma_medtech` — out of scope here.

## Step 1 — Create the profile and reassign the tickers

```python
TICKER_PROFILES = {
    ...,
    # remove DGX, LH, HCA, DVA, UHS, CVS from pharma_medtech, add here instead:
    "DGX": "health_services",
    "LH": "health_services",
    "HCA": "health_services",
    "DVA": "health_services",
    "UHS": "health_services",
    "CVS": "health_services",
}
```

`health_services` has no `PROFILE_CONCEPT_OVERRIDES` entry of its own yet — same starting
point as `consumer_staples` had relative to `standard`: it inherits the shared base
`CONCEPT_CANDIDATES` plus, for now, whatever `pharma_medtech` added
(`ResearchAndDevelopment`). Whether that inheritance makes sense is exactly what Step 2
checks.

## Step 2 — Decide the hidden/excluded set from evidence, not by copying pharma_medtech

**Do not copy `pharma_medtech`'s `PROFILE_HIDDEN` / `PROFILE_EXCLUDED_CONCEPTS` entries
wholesale.** Verify each of the following independently for these 6 tickers specifically:

1. **`rd_intensity`**: the scan already confirmed R&D intensity is ~0% for all six (real
   business characteristic, not missing data). Hide `rd_intensity` for `health_services`,
   and exclude `ResearchAndDevelopment` from `get_expected_concepts` for this profile —
   same reasoning as the `OperatingIncomeLoss`/`Goodwill` exclusions elsewhere: if no
   visible metric depends on the concept, don't let `check_data_quality` flag a gap nothing
   uses. Confirm nothing else in `metrics.py` touches `ResearchAndDevelopment` before
   excluding it.
2. **`operating_margin` / `net_debt_to_ebitda` / `ev_ebitda`**: `pharma_medtech` hides these
   because of the diversified-conglomerate `OperatingIncomeLoss` fragility pattern. The scan
   only directly confirmed this pattern for HCA among these 6 (via the Step 2 comparison
   table's `OperatingIncomeLoss` n/a). **Check `OperatingIncomeLoss` coverage for DGX, LH,
   DVA, UHS, CVS independently** — don't assume they share HCA's problem just because they
   were grouped together for the R&D comparison. If a given ticker's `OperatingIncomeLoss`
   is actually clean, its `operating_margin`/`net_debt_to_ebitda`/`ev_ebitda` should stay
   visible rather than being hidden on the strength of someone else's data gap.
   - If coverage is mixed across the 6 (some clean, some not), report this explicitly rather
     than picking one blanket answer — a profile-level hide/show decision has to apply to
     all 6, so state the trade-off you're making either way (e.g. "hiding it because 4 of 6
     are broken, even though 2 would have shown clean data" or vice versa).
3. Keep the same bank/insurance/retail/`rule_of_40` hides as `pharma_medtech` (those reasons
   — irrelevant metric categories — apply here too, this isn't in question).

## Step 3 — Mandatory non-regression check (same rule as every prior task, no exceptions)

1. Extract every concept touched by this change (at minimum `ResearchAndDevelopment`, and
   `OperatingIncomeLoss`/`DepreciationAndAmortization` if you end up excluding either) for
   **all** cached tickers under the config before and after the split.
2. Diff every `(ticker, concept, end)` value. Zero tolerance: the reassignment and any
   exclusion changes must not alter or remove a single previously-populated value for any
   ticker in any profile, including the 6 being moved. A profile reassignment changing which
   metrics are *hidden* is expected and fine; changing what values are *computed* is not —
   if you see the latter, stop and report it as a bug in the reassignment logic, not this
   ticker's data.
3. Confirm `metrics_long.csv` and the snapshot output for the 6 tickers still contain
   correct values for every metric that remains visible under `health_services` — only the
   *visibility*, not the underlying computation, should change.

## Output

One file, `health_services_split_report.md`: what was changed (`TICKER_PROFILES`,
`PROFILE_HIDDEN`, `PROFILE_EXCLUDED_CONCEPTS` diffs), the per-ticker `OperatingIncomeLoss`
coverage findings from Step 2 and the resulting hide/show decision with its stated
trade-off, and the non-regression check results.

No scratch scripts left behind. Do not touch any ticker outside these 6, do not touch
`pharma_medtech`'s remaining 41 tickers or its own hidden/excluded config, and do not touch
life-science-tools/CRO (A, TECH, CRL, IQV, MTD, RVTY, WAT, TMO) in any way.