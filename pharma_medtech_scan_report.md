# Pharma/Medtech Tag Coverage Scan

48 tickers (JNJ reference + 47 new): JNJ, ABT, ABBV, A, ALGN, AMGN, BAX, BDX, TECH, BIIB, BSX, BMY,
CRL, COO, DHR, DVA, DXCM, EW, GEHC, GILD, HCA, IDXX, PODD, IQV, ISRG, LH, LLY, MDT, MRK, MTD, PFE,
REGN, RMD, RVTY, SOLV, STE, SYK, TMO, UHS, VEEV, VTRS, VRTX, WAT, WST, ZBH, ZTS, CVS, DGX.

MRNA and INCY confirmed absent from `TICKER_PROFILES` — correctly out of scope for this batch.

## Step 0 — Setup

Applied the already-decided config: `TICKER_PROFILES` (47 tickers → `pharma_medtech`, JNJ already
present), `PROFILE_EXCLUDED_CONCEPTS["pharma_medtech"] = {"OperatingIncomeLoss"}`, and
`PROFILE_HIDDEN["pharma_medtech"]` were all already staged in `config.py`. Added the 47 tickers to
`TICKER_PROFILES` myself (only JNJ was present going in). Fetched/cached all 47 new tickers'
`company_info.json` (JNJ itself also needed fetching — not yet cached despite being the reference).

## Step 1 — Coverage scan

`pharma_medtech`'s expected concepts (base set minus the excluded `OperatingIncomeLoss`):
`Capex`, `CashAndEquivalents`, `DividendsPerShare`, `Goodwill`, `LongTermDebt`, `NetIncomeLoss`,
`OperatingCashFlow`, `ResearchAndDevelopment`, `Revenue`, `SharesOutstanding`, `StockholdersEquity`.

37 (ticker, concept) pairs came back below 50%:

| Ticker | Concept | Count | Max | Ratio |
|---|---|---:|---:|---:|
| ALGN | LongTermDebt | 0 | 70 | 0% |
| ALGN | DividendsPerShare | 0 | 70 | 0% |
| BIIB | DividendsPerShare | 0 | 73 | 0% |
| BSX | DividendsPerShare | 0 | 74 | 0% |
| BSX | NetIncomeLoss | 31 | 74 | 42% |
| COO | DividendsPerShare | 14 | 70 | 20% |
| CRL | ResearchAndDevelopment | 0 | 70 | 0% |
| CRL | DividendsPerShare | 0 | 70 | 0% |
| CVS | ResearchAndDevelopment | 0 | 74 | 0% |
| DGX | ResearchAndDevelopment | 0 | 74 | 0% |
| DHR | DividendsPerShare | 0 | 73 | 0% |
| DVA | ResearchAndDevelopment | 0 | 74 | 0% |
| DVA | DividendsPerShare | 0 | 74 | 0% |
| DXCM | DividendsPerShare | 0 | 66 | 0% |
| EW | DividendsPerShare | 0 | 70 | 0% |
| HCA | ResearchAndDevelopment | 0 | 67 | 0% |
| HCA | Goodwill | 4 | 67 | 6% |
| IDXX | DividendsPerShare | 0 | 70 | 0% |
| IDXX | LongTermDebt | 32 | 70 | 46% |
| IQV | ResearchAndDevelopment | 0 | 59 | 0% |
| IQV | DividendsPerShare | 0 | 59 | 0% |
| ISRG | LongTermDebt | 0 | 74 | 0% |
| ISRG | DividendsPerShare | 0 | 74 | 0% |
| LH | ResearchAndDevelopment | 3 | 74 | 4% |
| LH | DividendsPerShare | 7 | 74 | 9% |
| LLY | Capex | 12 | 74 | 16% |
| MTD | DividendsPerShare | 0 | 69 | 0% |
| PFE | DepreciationAndAmortization | 36 | 75 | 48% |
| PODD | DividendsPerShare | 0 | 65 | 0% |
| REGN | Goodwill | 0 | 70 | 0% |
| REGN | DividendsPerShare | 5 | 70 | 7% |
| SOLV | DividendsPerShare | 0 | 15 | 0% |
| UHS | ResearchAndDevelopment | 0 | 70 | 0% |
| VEEV | LongTermDebt | 0 | 59 | 0% |
| VEEV | DividendsPerShare | 0 | 59 | 0% |
| VRTX | DividendsPerShare | 0 | 71 | 0% |
| VRTX | LongTermDebt | 3 | 71 | 4% |
| WAT | DividendsPerShare | 0 | 96 | 0% |
| WAT | Capex | 2 | 96 | 2% |

### DividendsPerShare — checked per ticker, not batch-assumed

| Ticker | Any dividend tag at all? | Verdict |
|---|---|---|
| ALGN, BIIB, CRL, DXCM, EW, IDXX, MTD, PODD, SOLV, VEEV, VRTX, WAT | No | Genuine non-payer (growth-stage names, consistent with known no-dividend policies) |
| BSX, DVA | Yes, `PaymentsOfDividends`-family, but **literal $0** every period | Genuine non-payer, confirmed directly rather than inferred from tag absence |
| ISRG | Yes, one $8M distribution mid-2024, reverts to $0 in 2025 | One-time item, not an ongoing per-share program — not a gap |
| DHR | Yes, `PaymentsOfDividends` nonzero, but no per-share tag ever | Real payer, never tagged per-share — structural (4th filer with this exact pattern this session) |
| LH | Yes, `CommonStockDividendsPerShareCashPaid`, but only annual for FY2022–2023 | Real payer; the 7 quarters shown are the complete genuinely-disclosed set — structural |
| KVUE-style young company: REGN | Yes, `CommonStockDividendsPerShareDeclared`, continuous since initiation | Real payer, correctly extracted — REGN's first-ever dividend was 2025; 5 quarters is the complete history, not a gap |
| COO | Yes, 145 raw points, but only 20% survive extraction | New trap — see Step 3 |

### ResearchAndDevelopment — checked per ticker, including two beyond the named six

The brief named DGX, LH, HCA, DVA, UHS, CVS as expected near-zero (health-services, not
innovation-driven). All six confirmed directly: five have no R&D tag at all; LH's 3 points
(2009–2010, $2.5–3M/quarter) are real but immaterial, not "unexpectedly high" — the brief's
second-look trigger didn't fire for any of them.

Two more turned up with the same near-zero pattern for a related but distinct reason: **CRL and
IQV**, both CROs (contract research organizations). Neither tags R&D expense as a discrete line —
CRL has no tag at all; IQV has a small, abandoned one (9 points, 2011–2014, low millions,
immaterial next to IQVIA's actual revenue). Consistent with the CRO business model: research
performed for clients is billed as service revenue with a cost-of-revenue counterpart, not booked
as the company's own R&D expense.

## Step 2 — Does the life-science-tools/diagnostics subset actually belong in pharma_medtech?

Compared revenue growth, operating margin, and R&D intensity (TTM, computed directly from cached
quarterly data) for all 14 provisional tickers against the seven core references (JNJ, LLY, MRK,
PFE, ABT, MDT, SYK). No reassignment performed — findings only, per the brief.

| Group | Ticker | Rev. growth (mean / stdev) | Op. margin (mean) | R&D intensity (mean) |
|---|---|---|---:|---:|
| Core | JNJ | 2.8% / 6.4% | 24.2% | 14.1% |
| Core | LLY | 7.7% / 13.9% | n/a¹ | 23.4% |
| Core | MRK | 7.5% / 20.4% | n/a¹ | 25.2% |
| Core | PFE | 4.6% / 27.6% | n/a¹ | 19.8% |
| Core | ABT | 3.7% / 15.0% | 13.8% | 7.1% |
| Core | MDT | 7.4% / 14.4% | 17.9% | 8.1% |
| Core | SYK | 8.6% / 4.5% | 18.1% | 6.3% |
| Tools/CRO | A | 6.0% / 24.2% | 16.0% | 8.7% |
| Tools/CRO | TECH | 10.7% / 7.7% | 28.2% | 8.7% |
| Tools/CRO | CRL | 9.0% / 8.4% | 11.1% | n/a (no tag) |
| Tools/CRO | IQV | 10.4% / 11.6% | 10.0% | n/a (abandoned tag) |
| Tools/CRO | MTD | 4.4% / 5.9% | n/a¹ | 4.8% |
| Tools/CRO | RVTY | 4.4% / 13.7% | 13.8% | 6.2% |
| Tools/CRO | WAT | 4.3% / 6.7% | 27.8% | 5.8% |
| Tools/CRO | TMO | 10.2% / 10.0% | 15.5% | 3.6% |
| Health svcs | DGX | 2.8% / 9.8% | 16.4% | n/a |
| Health svcs | LH | 12.7% / 39.6%² | 14.0% | ~0% |
| Health svcs | HCA | 7.1% / 3.7% | n/a¹ | n/a |
| Health svcs | DVA | 2.6% / 2.5% | 14.1% | n/a |
| Health svcs | UHS | 7.4% / 3.7% | 11.6% | n/a |
| Health svcs | CVS | 9.5% / 6.1% | 4.8% | n/a |

¹ Same `OperatingIncomeLoss` thin/discontinued-tag pattern already confirmed for JNJ — not unique
to it, also affects MRK, PFE, LLY, HCA, MTD (already excluded profile-wide, so not a new finding,
just visible here as "n/a" while computing this comparison independently of the profile config).
² A real, known artifact of 2020–2021 COVID-testing revenue swings, not a data problem.

**Findings**:

- **Life science tools/CRO (A, TECH, CRL, IQV, MTD, RVTY, WAT, TMO)**: revenue growth and
  volatility sit comfortably inside the core group's own range — nothing distinctive there. R&D
  intensity (3.6–8.7%) is well below the pure-pharma core names (14.1–25.2%) but close to the
  medtech core names (6.3–8.1%). The group isn't internally homogeneous either: TECH/WAT run
  medtech-instrument-like margins (27–28%), while CRL/IQV run CRO/service-business margins (10–11%)
  with no R&D tag at all — a bigger internal gap than either sub-group's gap from core medtech.
- **Health services/diagnostics (DGX, LH, HCA, DVA, UHS, CVS)**: R&D intensity is essentially zero
  across the board — structural, not sampling noise. Margins run lower (11.6–16.4%, CVS at 4.8%)
  than core pharma/medtech (13.8–24.2%), reflecting service/facility/retail-driven economics rather
  than product margins.

**Recommendation** (no config change made): health-services/diagnostics looks like the stronger
candidate for eventually splitting into its own profile — the zero-R&D pattern is a genuine
business-model difference, and CVS's margin profile in particular is qualitatively unlike anything
else in `pharma_medtech`. Life-science-tools/CRO is more borderline — revenue dynamics fit fine,
but if this group is revisited, splitting out the two CROs (CRL, IQV) specifically looks better
justified than moving all eight tools/CRO names together.

## Step 3 — Candidate search for flagged concepts

### Fixed: LLY's Capex, right as it matters most

`PaymentsToAcquireProductiveAssets` only has data for FY2018–2022. Raw tag search found
`PaymentsToAcquireOtherPropertyPlantAndEquipment` spanning 2007–2026 continuously. Checked for a
magnitude trap before trusting an "Other"-prefixed tag: at all three overlap dates (2022 Q1–Q3),
values match **exactly**. Added as a third fallback tag on a new `pharma_medtech`-scoped `Capex`
override. The 14 newly-recovered quarters are exactly LLY's current manufacturing capex ramp —
$500M/quarter in early 2023 rising to $2.5B/quarter by late 2025 — tracking the real, well-known
GLP-1 capacity buildout. Coverage: 16% → 35%.

### A second capex candidate looked safe narrowly and broke on the full non-regression check

WAT's `Capex` was 2%. The next candidate, `PaymentsForProceedsFromProductiveAssets`, has 67 unique
dates for WAT (2008–2025) and checked out at its three overlap points with WAT's existing tag (two
exact matches, one within ~1%). Added to the same shared override — and since this codebase has no
per-ticker override mechanism, only per-profile, the tag went live for all 48 `pharma_medtech`
tickers at once. **The mandatory Step 5 non-regression check, run across the whole cached universe
rather than just WAT, caught what the narrow verification couldn't**: for LLY, this exact same tag
produced a nonsensical **negative** capex value (-$220.9M at 2008-09-30). The tag name explains why
— "payments **for**, and proceeds **from**, productive assets" is a *net* figure (capex minus
disposal proceeds), not gross capex. WAT's disposals happened to be small at the three checked
dates; LLY had a real divestiture in a quarter the narrow check never looked at. Same "different
economic basis" rejection rule as every prior fair-value/carrying-value or FIFO/LIFO trap in this
project. **Reverted.** WAT's `Capex` gap (2%) stays open — no clean fix found; documented rather
than forced.

### Everything else: structural, traced rather than left as a bare percentage

- **REGN — Goodwill, 0%.** No `Goodwill` tag anywhere in the filings; only
  `IntangibleAssetsNetExcludingGoodwill`, which by its own name excludes it. Consistent with
  Regeneron's real acquisition history (overwhelmingly organic growth) — a genuine "no goodwill"
  balance sheet, same category as GRMN's confirmed "no debt" from the retail scan.
- **COO — DividendsPerShare, 20% — new trap.** 145 raw points on the primary tag, but 58 have no
  `start` date at all (an instant-style fact for a duration concept, silently dropped by
  `extract_period_values`), and most of the rest use a ~30-day declaration-to-record-date window
  that fails the 80–380-day quarterly validity check. The value itself ($0.03/share, stable for
  years) is correct; the tagging convention just doesn't fit this pipeline's duration-based
  extraction. New pattern, distinct from every dividend gap logged so far.
- **BSX — NetIncomeLoss, 42%.** A ~7-year gap (2011–2017) where neither candidate tag has any data
  — the most severe gap found yet in a universal base concept. No substitute: the only alternative
  found (`IncomeLossFromContinuingOperationsBeforeIncomeTaxes...`) is a different, pre-tax
  income-statement level, rejected on that basis.
- **HCA — Goodwill (6%); IDXX — LongTermDebt (46%).** Both "real tag, annual-only for part of
  history" — HCA around its 2011 post-LBO re-IPO window only; IDXX pre-2019 only, with
  `LongTermDebtNoncurrent` covering cleanly from 2019 on. Same shape as TGT/COST/SYY from the
  consumer_staples scan.
- **VRTX — LongTermDebt, 4% — a trap avoided.** `ConvertibleSubordinatedDebtNoncurrent` has 27
  points (2010–2013) but doesn't match `LongTermDebt` at the three dates both exist ($400M vs.
  $105M) — two real, concurrent, non-equivalent debt tranches, not alternates. Not added.
- **Segment-reconciliation caution (ABT, DHR, BDX, TMO, BAX)** — none needed a segment-based
  reconstruction this session (their only flagged item, DHR's dividend gap, was the
  never-tagged-per-share pattern, unrelated to segments). Caution noted as not triggered, not
  silently skipped.
- **DepreciationAndAmortization exclusion, resolved.** Traced every consumer: D&A only feeds
  `EBITDA_TTM`, whose only consumers (`net_debt_to_ebitda`, `ev_ebitda`) are already hidden for
  this profile; `figures.py` never plots raw facts, only `metrics_long`/`valuation_history`
  concepts, and neither references D&A outside the EBITDA chain. Excluded via
  `PROFILE_EXCLUDED_CONCEPTS`, same reasoning as `OperatingIncomeLoss`.

## Step 4 — Mode decisions

One change kept, one change reverted, both via the standard two-step discipline:

- **Kept**: `pharma_medtech`-scoped `Capex` override — Stage B1 (base 2 tags, byte-identical, 0
  diffs) → Stage B2 (added `PaymentsToAcquireOtherPropertyPlantAndEquipment`, 14 new fills, 0
  changed, 0 removed).
- **Reverted**: `PaymentsForProceedsFromProductiveAssets` — added in the same Stage B2 pass, caught
  by the Step 5 full-universe diff producing a nonsensical negative value for LLY, removed before
  finalizing.
- **Excluded concept** (not a tag/mode change, no diff needed): `DepreciationAndAmortization` added
  to `PROFILE_EXCLUDED_CONCEPTS["pharma_medtech"]`.

## Step 5 — Non-regression check

Extracted every concept for all 225 cached tickers (every profile, JNJ included) under the config
before and after, for the one concept actually changed (`Capex`):

```
changed: 0
removed: 0
new fills: 14   (all on LLY)
```

The rejected `PaymentsForProceedsFromProductiveAssets` addition was caught and backed out before
this final diff — see Step 3. `DepreciationAndAmortization`'s exclusion only touches
`get_expected_concepts` (the coverage-check whitelist), not extraction, so no facts diff applies.

## Step 6 — Coverage re-check

| Ticker | Concept | Before | After |
|---|---|---:|---:|
| ALGN | LongTermDebt | 0/70 (0%) | 0/70 (0%) — unchanged, confirmed no debt |
| ALGN | DividendsPerShare | 0/70 (0%) | 0/70 (0%) — unchanged, confirmed non-payer |
| BIIB | DividendsPerShare | 0/73 (0%) | 0/73 (0%) — unchanged, confirmed non-payer |
| BSX | DividendsPerShare | 0/74 (0%) | 0/74 (0%) — unchanged, confirmed non-payer ($0 tag) |
| BSX | NetIncomeLoss | 31/74 (42%) | 31/74 (42%) — unchanged, structural (7-yr tagging gap) |
| COO | DividendsPerShare | 14/70 (20%) | 14/70 (20%) — unchanged, new trap (see Step 3) |
| CRL | ResearchAndDevelopment | 0/70 (0%) | 0/70 (0%) — unchanged, confirmed (CRO, no R&D tag) |
| CRL | DividendsPerShare | 0/70 (0%) | 0/70 (0%) — unchanged, confirmed non-payer |
| CVS | ResearchAndDevelopment | 0/74 (0%) | 0/74 (0%) — unchanged, expected (health services) |
| DGX | ResearchAndDevelopment | 0/74 (0%) | 0/74 (0%) — unchanged, expected (health services) |
| DHR | DividendsPerShare | 0/73 (0%) | 0/73 (0%) — unchanged, structural (never tagged per-share) |
| DVA | ResearchAndDevelopment | 0/74 (0%) | 0/74 (0%) — unchanged, expected (health services) |
| DVA | DividendsPerShare | 0/74 (0%) | 0/74 (0%) — unchanged, confirmed non-payer ($0 tag) |
| DXCM | DividendsPerShare | 0/66 (0%) | 0/66 (0%) — unchanged, confirmed non-payer |
| EW | DividendsPerShare | 0/70 (0%) | 0/70 (0%) — unchanged, confirmed non-payer |
| HCA | ResearchAndDevelopment | 0/67 (0%) | 0/67 (0%) — unchanged, expected (health services) |
| HCA | Goodwill | 4/67 (6%) | 4/67 (6%) — unchanged, structural (annual-only, brief window) |
| IDXX | DividendsPerShare | 0/70 (0%) | 0/70 (0%) — unchanged, confirmed non-payer |
| IDXX | LongTermDebt | 32/70 (46%) | 32/70 (46%) — unchanged, structural (annual-only pre-2019) |
| IQV | ResearchAndDevelopment | 0/59 (0%) | 0/59 (0%) — unchanged, confirmed (CRO, abandoned tag) |
| IQV | DividendsPerShare | 0/59 (0%) | 0/59 (0%) — unchanged, confirmed non-payer |
| ISRG | LongTermDebt | 0/74 (0%) | 0/74 (0%) — unchanged, confirmed no debt |
| ISRG | DividendsPerShare | 0/74 (0%) | 0/74 (0%) — unchanged, one-time item, not a program |
| LH | ResearchAndDevelopment | 3/74 (4%) | 3/74 (4%) — unchanged, expected & confirmed not-high |
| LH | DividendsPerShare | 7/74 (9%) | 7/74 (9%) — unchanged, structural (annual-only pre-2024) |
| **LLY** | **Capex** | **12/74 (16%)** | **26/74 (35%)** — **improved, GLP-1-era capex recovered** |
| MTD | DividendsPerShare | 0/69 (0%) | 0/69 (0%) — unchanged, confirmed non-payer |
| PFE | DepreciationAndAmortization | 36/75 (48%) | excluded — no visible metric depends on it |
| PODD | DividendsPerShare | 0/65 (0%) | 0/65 (0%) — unchanged, confirmed non-payer |
| REGN | Goodwill | 0/70 (0%) | 0/70 (0%) — unchanged, confirmed genuine (no M&A history) |
| REGN | DividendsPerShare | 5/70 (7%) | 5/70 (7%) — unchanged, explained (2025 initiation) |
| SOLV | DividendsPerShare | 0/15 (0%) | 0/15 (0%) — unchanged, confirmed non-payer |
| UHS | ResearchAndDevelopment | 0/70 (0%) | 0/70 (0%) — unchanged, expected (health services) |
| VEEV | LongTermDebt | 0/59 (0%) | 0/59 (0%) — unchanged, confirmed no debt |
| VEEV | DividendsPerShare | 0/59 (0%) | 0/59 (0%) — unchanged, confirmed non-payer |
| VRTX | DividendsPerShare | 0/71 (0%) | 0/71 (0%) — unchanged, confirmed non-payer |
| VRTX | LongTermDebt | 3/71 (4%) | 3/71 (4%) — unchanged, trap avoided (non-equivalent tag) |
| WAT | DividendsPerShare | 0/96 (0%) | 0/96 (0%) — unchanged, confirmed non-payer |
| WAT | Capex | 2/96 (2%) | 2/96 (2%) — unchanged, candidate fix reverted (net-vs-gross) |

### Summary

- **Fully resolved**: 0 (crossed the 50% line).
- **Improved but not clean**: 1 — LLY `Capex` (16% → 35%); the added history is the economically
  important recent capex ramp, not padding.
- **Excluded from the coverage check entirely** (confirmed no visible metric depends on it): 1 —
  PFE's `DepreciationAndAmortization` (and, structurally, the whole profile's D&A).
- **Unchanged, confirmed structural or already-explained**: 35 (ticker, concept) pairs — 20+
  confirmed genuine non-payers/no-debt companies, 3 abandoned-tag dividend gaps (DHR, and per the
  consumer_staples precedent HSY/TSN), 1 new tagging-convention trap (COO), 1 severe base-concept
  gap (BSX NetIncomeLoss), 2 annual-only-for-part-of-history gaps (HCA Goodwill, IDXX LongTermDebt),
  1 non-equivalent-tag trap avoided (VRTX LongTermDebt), 1 confirmed-genuine "no goodwill" case
  (REGN), 2 confirmed CRO-pattern R&D gaps beyond the named six (CRL, IQV), 1 explained-by-recency
  case (REGN dividends), and 1 net-vs-gross trap caught and reverted (WAT Capex) — every single one
  traced to raw filing data, none left as a bare percentage.

No scratch scripts were left behind. No ticker outside the 48 `pharma_medtech` tickers was touched,
no ticker's profile assignment was changed, and no concept unrelated to `pharma_medtech`'s metric
set was modified.
