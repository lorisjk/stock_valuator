# Split `health_services` Out of `pharma_medtech`

## Summary

Moved DGX, LH, HCA, DVA, UHS, CVS from `pharma_medtech` into a new `health_services` profile, per
the pharma/medtech scan's recommendation. Life-science-tools/CRO (A, TECH, CRL, IQV, MTD, RVTY,
WAT, TMO) is untouched, still in `pharma_medtech`. `pharma_medtech` itself now has 42 tickers
(48 − 6); `health_services` has 6.

## Step 1 — Profile creation and reassignment

`TICKER_PROFILES`: the 6 tickers moved from `"pharma_medtech"` to `"health_services"`.

**`health_services` needed its own `PROFILE_CONCEPT_OVERRIDES` entry immediately, not "for now
inherited."** `get_concept_candidates` resolves overrides purely by
`PROFILE_CONCEPT_OVERRIDES.get(profile, {})` — there is no cross-profile inheritance in this
codebase. Leaving `health_services` without an entry would have silently stopped
`ResearchAndDevelopmentExpense` extraction for all 6 tickers the moment they moved (the concept
only exists as a candidate via `pharma_medtech`'s override), deleting LH's 3 real quarters of R&D
data in the process — a genuine regression, not a visibility change. Copied `pharma_medtech`'s
`ResearchAndDevelopment` and `Capex` overrides verbatim into a new `health_services` entry before
touching anything else. Verified: the reassignment plus this copy, on its own, produces **zero**
change in extracted facts across the full 225-ticker cached universe (0 changed, 0 removed, 0 new
fills) — confirmed before any hidden/excluded decision was made, isolating "did the reassignment
itself break anything" from "what should be hidden now."

## Step 2 — Hidden/excluded set, decided from evidence

### rd_intensity / ResearchAndDevelopment

Confirmed (not assumed) that `ResearchAndDevelopment` has exactly one consumer anywhere in the
codebase — `rd_intensity`'s calculation in `main.py`, nothing in `metrics.py` or `figures.py`
touches it otherwise. R&D intensity is confirmed ~0% for all 6 tickers (from the pharma_medtech
scan, and consistent with DGX/HCA/DVA/UHS/CVS having no R&D tag at all and LH's tag being real but
immaterial). **Hidden `rd_intensity`, excluded `ResearchAndDevelopment`** — same "nothing visible
depends on it" reasoning as every other exclusion in this project.

### OperatingIncomeLoss / operating_margin / net_debt_to_ebitda / ev_ebitda — checked per ticker, not copied

The brief explicitly warned not to assume all 6 share HCA's `OperatingIncomeLoss` gap just because
they were grouped together in the pharma_medtech scan's R&D comparison table. Checked directly:

| Ticker | OperatingIncomeLoss coverage | Verdict |
|---|---|---|
| DGX | 71/71 quarters (100%), 2008–2026 continuous | Clean |
| LH | 71/71 quarters (100%), 2008–2026 continuous | Clean |
| DVA | 71 quarters, 2008–2026 continuous | Clean — a naive revenue-quarter ratio showed 192%, but that's a mismatched-denominator artifact from an unrelated DVA revenue-tag quirk, not an OperatingIncomeLoss problem; the concept itself has full, continuous coverage |
| UHS | 67/65 quarters (103%), 2009–2026 continuous | Clean |
| **HCA** | **0/37 quarters (0%)** | **Broken** — no `OperatingIncomeLoss` tag data at all |

**5 of 6 tickers have clean, complete coverage. Only HCA has the gap.**

`pharma_medtech` hides `operating_margin`/`net_debt_to_ebitda`/`ev_ebitda` profile-wide because the
diversified-conglomerate `OperatingIncomeLoss`-fragility pattern is a *recurring* one there — JNJ,
NKE, ADM, BG, CASY, CLX, GPC, TJX, ROST all show some version of it. That justification doesn't
transfer here: it's 1 gap in 6, not a pattern.

**Decision: kept `operating_margin`, `net_debt_to_ebitda`, and `ev_ebitda` visible for
`health_services`** — the opposite call from `pharma_medtech`, made deliberately from this
evidence rather than by default inheritance.

**Trade-off, stated explicitly**: HCA will show no data for these three metrics — confirmed via a
live `calculate_all_metrics` run that its failure mode is an empty result set (`n=0` rows), not a
wrong or misleading number, consistent with this pipeline's established "fails silently, produces
nothing rather than garbage" behavior. The alternative (hiding for the whole profile) would throw
away genuinely correct, useful data for DGX, LH, DVA, UHS, and CVS — verified their `operating_margin`
values are real and sane (1.5%–15.1% range; CVS's 1.5% is consistent with its already-known
low-margin retail/PBM mix from the pharma_medtech scan) — just to avoid one blank chart for HCA.
Keeping the metrics visible is the better trade-off given 5-of-6 clean data; if HCA's own
`OperatingIncomeLoss` gap gets fixed in a future session, no further profile-config change would be
needed.

**Implication for `DepreciationAndAmortization`, followed through even though not explicitly
asked**: `pharma_medtech` excludes it only because it feeds the now-hidden `EBITDA_TTM` chain
(`net_debt_to_ebitda`, `ev_ebitda`) there. Since those two metrics are visible for
`health_services`, D&A now feeds a visible metric for this profile too — correctly **not**
excluded, unlike `pharma_medtech`.

### Kept unchanged from pharma_medtech (not in question, per the brief)

`net_interest_margin`, `efficiency_ratio`, `p_tbv`, `roa`, `equity_to_assets`,
`provision_ratio`, `p_ppnr`, `combined_ratio`, `loss_ratio`, `expense_ratio`,
`net_investment_yield`, `reserve_growth`, `p_core_earnings`, `rule_of_40`, `inventory_turnover`,
`dio`, `dso`, `dpo`, `cash_conversion_cycle` — all hidden, same bank/insurance/retail-metric
irrelevance reasoning as every non-financial/insurance/retail profile in this project.

## Step 3 — Non-regression check

Full before/after diff across all 225 cached tickers (every profile), run twice: once immediately
after the reassignment + copied overrides (before any hidden/excluded decision), and once after
the full final config. Both: **0 changed, 0 removed, 0 new fills.**

Directly verified `metrics_long` output (via a live `calculate_all_metrics` run, not just the raw
facts diff) for all 6 moved tickers plus two `pharma_medtech` references (JNJ, MDT):

| Ticker | rd_intensity (n) | operating_margin (n, latest) | net_debt_to_ebitda (n, latest) |
|---|---:|---|---|
| DGX | 0 (hidden) | 71, 14.3% | 68, 0.05x |
| LH | 0 (hidden) | 71, 10.2% | 68, 2.52x |
| HCA | 0 (hidden) | 0 (empty — confirmed gap, not garbage) | 0 (empty) |
| DVA | 0 (hidden) | 37, 15.1% | 66, 3.52x |
| UHS | 0 (hidden) | 65, 11.5% | 64, 1.72x |
| CVS | 0 (hidden) | 71, 1.5% | 60, 4.84x |
| JNJ (pharma_medtech, control) | 71, 15.5% | 0 (still hidden) | 0 (still hidden) |
| MDT (pharma_medtech, control) | 48, 7.9% | 0 (still hidden) | 0 (still hidden) |

Confirms: only visibility changed for the 6 moved tickers; the underlying computed values (where
visible) are real and correct; `pharma_medtech`'s remaining 42 tickers are completely unaffected.

No scratch scripts were left behind. No ticker outside the 6 was touched, `pharma_medtech`'s
remaining 42 tickers (the brief's own text says "41" — 48 originally minus the 6 moved is 42;
noted rather than silently matched to the brief's count) and its own hidden/excluded config were
not modified, and life-science-tools/CRO (A, TECH, CRL, IQV, MTD, RVTY, WAT, TMO) was not touched
in any way.
