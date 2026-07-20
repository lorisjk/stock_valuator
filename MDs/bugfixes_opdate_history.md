# Bugfix History

A running log of bugs found, what caused them, and how they were fixed. Ordered newest first.

Most entries here share a theme: **the pipeline fails silently**. A missing tag returns an empty list, an empty list produces an empty merge, an empty merge produces an empty chart. Nothing crashes. The symptom appears several layers away from the cause, and usually looks like a plotting problem. Nearly every fix below was found by noticing that a *number* looked wrong, not by reading a stack trace.

---

## 2026-07-20 — Eighth stock-type profile: health_services split out of pharma_medtech, hidden set decided from evidence rather than copied

Executed the split the pharma_medtech scan (immediately below) recommended: DGX, LH, HCA, DVA,
UHS, CVS moved out of `pharma_medtech` into a new `health_services` profile. Life-science-tools/CRO
(A, TECH, CRL, IQV, MTD, RVTY, WAT, TMO) stayed put — out of scope for this task.

### The reassignment itself had to preserve extraction, not just move a label

`health_services` started with no `PROFILE_CONCEPT_OVERRIDES` entry of its own. Since
`get_concept_candidates` resolves purely from `PROFILE_CONCEPT_OVERRIDES[profile]` — no
inheritance between profiles — leaving it empty would have silently dropped
`ResearchAndDevelopmentExpense` extraction for all 6 tickers the moment they moved, deleting
LH's 3 genuinely-real quarters of R&D data ($2.5–3M each, 2009–2010) in the process. Copied
`pharma_medtech`'s `ResearchAndDevelopment` and `Capex` overrides verbatim into a new
`health_services` entry before touching anything else, and verified the reassignment alone (before
any hidden/excluded decision) produced **zero** change across the full 225-ticker cached universe —
0 changed, 0 removed, 0 new fills. Confirms the reassignment is what it should be: a routing change,
not a data change.

### The task's own instruction not to copy wholesale turned out to matter

The brief explicitly warned against copying `pharma_medtech`'s `PROFILE_HIDDEN`/
`PROFILE_EXCLUDED_CONCEPTS` and said to verify `OperatingIncomeLoss` coverage per ticker rather than
assume all 6 share HCA's problem. Checked directly:

```
DGX    OperatingIncomeLoss: 71/71 quarters (100%), 2008–2026 continuous
LH     OperatingIncomeLoss: 71/71 quarters (100%), 2008–2026 continuous
DVA    OperatingIncomeLoss: 71 quarters, 2008–2026 continuous (effectively full — the "37" revenue-
                            quarter denominator in the raw check was itself an unrelated DVA
                            revenue-tag artifact, not an OperatingIncomeLoss problem)
UHS    OperatingIncomeLoss: 67/65 quarters (103%), 2009–2026 continuous
HCA    OperatingIncomeLoss: 0/37 quarters (0%)
```

Only HCA has the gap. `pharma_medtech` hides `operating_margin`/`net_debt_to_ebitda`/`ev_ebitda`
profile-wide because the diversified-conglomerate `OperatingIncomeLoss` fragility pattern shows up
repeatedly across that batch (JNJ, NKE, ADM, BG, CASY, CLX, GPC, TJX, ROST — a real, recurring
pattern there). Here it's 1 gap out of 6, not a pattern. **Kept these three metrics visible for
`health_services`** — the opposite call from `pharma_medtech`, made deliberately rather than by
default. HCA itself: confirmed via a live `calculate_all_metrics` run that its failure mode is
`n=0` (empty merge, no rows) for all three metrics, not a wrong number — the same "fails silently,
produces nothing rather than garbage" behavior this whole log is built around, not new risk.
Verified DGX/LH/DVA/UHS/CVS's `operating_margin` values are real and sane (1.5%–15.1%, CVS's 1.5%
consistent with its already-known low-margin retail/PBM mix from the pharma_medtech scan) and that
`DepreciationAndAmortization` — excluded for `pharma_medtech` only because it fed the now-hidden
EBITDA chain there — correctly stays *un*-excluded here, since that same chain is visible for this
profile.

`rd_intensity`: confirmed R&D intensity is ~0% for all 6 (real business characteristic, matching
the CRL/IQV "service provider, not innovator" finding from the pharma_medtech entry) and that
`ResearchAndDevelopment` has exactly one consumer anywhere in the codebase (`rd_intensity` itself,
confirmed by grep across `main.py`/`metrics.py`/`figures.py`) — hidden and excluded together, same
"nothing visible depends on it" reasoning as every other exclusion in this project.

### Non-regression

Full before/after diff across all 225 cached tickers, run after every config change (reassignment
+ hidden/excluded decisions): 0 changed, 0 removed, 0 new fills — confirms the entire split changed
*visibility* only, exactly as the brief required. Spot-checked `metrics_long` directly for all 6
tickers plus two `pharma_medtech` references (JNJ, MDT): `rd_intensity` correctly empty for the 6
and present for JNJ/MDT; `operating_margin`/`net_debt_to_ebitda` correctly populated with sane
values for 5 of 6 and empty for HCA; both correctly empty for JNJ/MDT (untouched, still hidden
under `pharma_medtech`).

## 2026-07-20 — Seventh stock-type profile: pharma_medtech, and a net-vs-gross capex substitution caught and reverted

48 tickers (JNJ reference + 47 new). `pharma_medtech` reuses `standard`'s whole metric set,
excludes `OperatingIncomeLoss` outright (JNJ's own is structurally thin/discontinued, and with
`operating_margin`/`net_debt_to_ebitda`/`ev_ebitda` all hidden for the profile, nothing visible
depends on it), and adds one new concept/metric pair: `ResearchAndDevelopment` → `rd_intensity`.
Both were already built and verified correct going into this session; the work here was scaling
tag coverage to the other 47 names and resolving two structural questions the brief left open.

### DepreciationAndAmortization: the same reasoning as OperatingIncomeLoss, checked rather than assumed

The brief asked explicitly to verify D&A sits in the same position as `OperatingIncomeLoss` before
excluding it too — only feeding the already-hidden `EBITDA_TTM` chain (`net_debt_to_ebitda`,
`ev_ebitda`), with no other visible metric or chart touching it. Traced every consumer: `ebitda`
in `calculate_all_metrics` is D&A's only use, and both of *its* consumers are hidden for this
profile; `figures.py` only ever plots `metrics_long`/`valuation_history` concepts (never raw facts
directly), and neither plot list references D&A or anything derived from it outside the EBITDA
chain. Confirmed, not assumed — excluded via `PROFILE_EXCLUDED_CONCEPTS["pharma_medtech"]`.

### The one real fix: LLY's capex tag switch, right as the GLP-1 buildout needed it most

LLY's `Capex` was 16% (12/74) — `PaymentsToAcquireProductiveAssets` only has data for FY2018–2022,
nothing before or after. The raw tag dump showed `PaymentsToAcquireOtherPropertyPlantAndEquipment`
spanning 2007–2026 continuously — checked for a magnitude trap before trusting it (an "Other"-
prefixed tag is exactly the pattern this project already treats with suspicion): at all three dates
where the two tags overlap (2022 Q1–Q3), the values match **exactly**. Added as a third fallback
tag on a new `pharma_medtech`-scoped `Capex` override (byte-identical-copy-first discipline: Stage
B1 zero diffs). The 14 new quarters it recovers are exactly LLY's current manufacturing capex ramp
— $500M/quarter in early 2023 growing to $2.5B/quarter by late 2025, tracking the real, well-known
GLP-1 capacity buildout. Coverage: 16% → 35% (still below the 50% line, but the added history is
the economically important part — the recent ramp — not padding from old, low-relevance quarters).

### A second candidate tag looked fine on inspection and broke on the broad check — reverted

WAT's `Capex` was 2% (2/96). The obvious next tag, `PaymentsForProceedsFromProductiveAssets`,
has 67 unique dates for WAT spanning 2008–2025 — checked at the three dates where it overlaps
WAT's existing tag: two exact matches, one off by ~1%, good enough to look like a safe substitute.
Added to the same shared `pharma_medtech` `Capex` override (there's no per-ticker override
mechanism in this codebase, only per-profile — a tag added for one ticker's gap is live for all 48).
The mandatory non-regression check, run across the *whole* cached universe rather than just the
tickers it was meant to fix, caught what the narrow WAT-only check couldn't: for **LLY**, this same
tag produced a genuinely nonsensical **negative** capex value (-$220.9M at 2008-09-30). The tag name
says exactly why — "Payments **for**, and proceeds **from**, productive assets" is a *net* figure
(capex minus disposal proceeds), not gross capex. WAT's disposals happened to be small enough at
the three checked dates that net ≈ gross there; LLY's weren't, in a quarter with a real one-time
divestiture. Same rejection rule as every "different economic basis" trap in this log (fair-value
vs. carrying-value, FIFO vs. LIFO) — a *shared* tag that verifies cleanly against one ticker's
narrow overlap window is not the same claim as verifying it against the concept it's supposed to
represent. **Reverted.** WAT's `Capex` gap (2%) stays open and structural — no clean fix found.

### Everything else: structural, confirmed by inspection rather than left as a bare percentage

- **A dozen-plus growth-stage names with `DividendsPerShare`/`LongTermDebt` at or near 0%** (ALGN,
  BIIB, BSX, CRL, DHR¹, DVA, DXCM, EW, IDXX, ISRG, MTD, PODD, SOLV, VEEV, VRTX, WAT for dividends;
  ALGN, ISRG, VEEV for debt) — checked each rather than batch-assumed. Three (BSX, DVA, ISRG) have
  an aggregate `PaymentsOfDividends`-family tag reporting a literal `$0` for most periods,
  confirming genuine non-payer status directly rather than inferring it from tag absence; ISRG
  shows one isolated $8M distribution in mid-2024 that reverts to $0 in 2025 — a one-time item, not
  an ongoing per-share program. ¹DHR is a real, longstanding payer (`PaymentsOfDividends` exists
  and is nonzero) that has simply never tagged a per-share figure — same "abandoned/never-tagged
  per-share dividend" pattern as HSY/TSN from the 2026-07-20 consumer_staples entry, now confirmed
  in a fourth filer.
- **REGN — `Goodwill`, 0%.** No `Goodwill` tag anywhere in the company-facts dump, only
  `IntangibleAssetsNetExcludingGoodwill` (which, by its own name, explicitly isn't it). Consistent
  with Regeneron's real acquisition history — overwhelmingly organic growth, no major M&A — a
  genuine "no goodwill" balance sheet, same "confirmed absence, not a bug" pattern as GRMN's debt.
- **COO — `DividendsPerShare`, 20%, and a new tagging-convention trap.** COO's primary dividend tag
  has 145 raw points, but most (58 of them) carry **no `start` date at all** — an instant-style
  fact for what should be a duration concept — and get silently dropped by
  `extract_period_values`'s `"start" in item` check. Of the remainder, most use a narrow
  declaration-to-record-date window (~30 days) rather than a fiscal-period duration, which fails
  the 80–380-day quarterly validity range and gets dropped too. The handful that do show up as
  quarterly data are the coincidental few with both a `start` date and a long-enough window. The
  underlying value ($0.03/share, stable for years) is correct; the pipeline's duration-based
  extraction just can't reconstruct a clean quarterly series from this particular tagging
  convention. New pattern, distinct from every previously-logged dividend gap (abandoned tag,
  dual-class, young-company, genuine non-payer) — worth naming for future batches.
- **BSX — `NetIncomeLoss`, 42%.** A ~7-year gap (2011–2017) where *neither* candidate tag
  (`NetIncomeLoss`, `NetIncomeLossAvailableToCommonStockholdersBasic`) has any data at all — the
  first time this severe a gap has shown up in a universal, non-profile-specific base concept this
  project tracks. No substitute found; `IncomeLossFromContinuingOperationsBeforeIncomeTaxes...` is
  a different (pre-tax) income-statement level and was rejected on that basis, same rule as always.
- **HCA — `Goodwill`, 6%; IDXX — `LongTermDebt`, 46%.** Both show the same "real tag, but annual-
  only for part of history" shape already logged for TGT/COST/SYY in the consumer_staples entry
  above — HCA tags `Goodwill` only around its 2011 post-LBO re-IPO window and then stops; IDXX has
  only fiscal-year-end `LongTermDebt` before 2019, with `LongTermDebtNoncurrent` picking up cleanly
  from 2019 onward. Structural, not fixable by more tag search.
- **VRTX — `LongTermDebt`, 4%.** A genuine trap avoided rather than a gap left unfixed:
  `ConvertibleSubordinatedDebtNoncurrent` has 27 points covering 2010–2013, but checked against
  `LongTermDebt` at the three dates where both exist, the values don't match ($400M vs. $105M) —
  two real, *concurrent*, non-equivalent debt tranches, not alternates. Adding it as a fallback
  would silently pick whichever tranche happened to be tagged for a given date rather than the
  total. Not added; VRTX has been close to debt-free since ~2013 regardless.
- **CRL, IQV — `ResearchAndDevelopment`, 0% each — two more expected-zero cases beyond the brief's
  named six.** Neither is a health-services name (the brief's DGX/LH/HCA/DVA/UHS/CVS group); both
  are CROs (contract research organizations). CRL has no R&D-expense tag at all. IQV has one, but
  only 9 points (2011–2014, values in the low millions — immaterial next to IQVIA's actual revenue)
  before it was abandoned. Consistent with the CRO business model: the research they perform is
  billed as service revenue with a cost-of-revenue counterpart, not booked as the company's own
  R&D expense. Confirmed, not assumed — same discipline as the brief's own six.
- **The rest of the named six (DGX, LH, HCA, DVA, UHS, CVS) plus LH's thin 4%** — verified directly
  rather than waved through. All five 0%-coverage names have no R&D-expense tag whatsoever, exactly
  as expected. LH's 3 non-zero points (2009–2010, $2.5–3M/quarter, since abandoned) are real but
  immaterial next to Labcorp's revenue — not "unexpectedly high," so the brief's second-look
  trigger didn't fire.
- **Segment-reconciliation caution (ABT, DHR, BDX, TMO, BAX)** — none of the five needed a
  segment-level reconstruction for any flagged concept this session (their only flagged item, DHR's
  `DividendsPerShare`, turned out to be the abandoned-tag pattern above, unrelated to segments), so
  the caution wasn't triggered. Noted rather than silently skipped.

### Step 2: does the 14-ticker life-science-tools/diagnostics subset actually belong here?

Compared revenue growth, operating margin, and R&D intensity (TTM, computed directly from cached
data) against the seven named core references (JNJ, LLY, MRK, PFE, ABT, MDT, SYK) — no reassignment
performed, config left as-is, per the brief.

**Life science tools/CRO (A, TECH, CRL, IQV, MTD, RVTY, WAT, TMO)**: revenue growth (4.3–10.7% mean)
and volatility sit comfortably inside the core group's own range (3.7–8.6% mean, 4.5–27.6% stdev) —
nothing distinctive there. R&D intensity is the real signal: 3.6–8.7% across the group, versus
14.1–25.2% for the pure-pharma core names (LLY, MRK, PFE, JNJ) — though notably *close* to the
medtech core names' own 6.3–8.1% (MDT, SYK). The group also isn't internally homogeneous: TECH/WAT
run 27–28% operating margins (medtech-instrument-like), while the two CROs in the group (CRL 11%,
IQV 10%) run service-business margins and have no R&D tag at all (see above) — a bigger gap from
the "tools" half of their own bucket than from core medtech.

**Health services/diagnostics (DGX, LH, HCA, DVA, UHS, CVS)**: R&D intensity is essentially zero
across the board (confirmed in Step 1) — a real structural difference, not sampling noise. Margins
run lower and more service/facility-driven (11.6–16.4%) than core pharma/medtech's 13.8–24.2%
range, and CVS's 4.8% sits well below anything in the core group, reflecting its retail/PBM-heavy
mix. LH's revenue growth stdev (39.6%) is an outlier even within this group — a real, known
artifact of 2020–2021 COVID-testing revenue swings, not a data problem.

**Recommendation** (findings only, no config change): health-services/diagnostics is the stronger
candidate for eventually splitting out — the zero-R&D pattern is structural, not just numerically
low, and CVS's margin profile is qualitatively different from anything else in the profile. Life-
science-tools/CRO is more borderline — revenue dynamics look like core pharma/medtech fine, but the
group is itself split between instrument-makers (medtech-like) and CROs (their own thing); if this
gets revisited, splitting the two CROs (CRL, IQV) out specifically looks more justified than moving
all eight.

### Non-regression, Step 5

Full before/after diff across all 225 cached tickers (every profile) for the concept actually
changed (`Capex`): 0 changed, 0 removed, 14 new fills, all on LLY. (The rejected
`PaymentsForProceedsFromProductiveAssets` addition was caught and backed out before this final
diff — see above.) `DepreciationAndAmortization`'s exclusion touches only the coverage-check
whitelist (`get_expected_concepts`), not extraction, so no facts diff applies to it.

## 2026-07-20 — Sixth stock-type profile: consumer_staples, and a rejected FIFO/LIFO substitution

The `consumer_staples` profile (34 tickers, KO as reference) reuses `standard`'s entire concept set
unchanged — the profile exists purely to branch hidden-metric logic away from `standard`, no
`PROFILE_CONCEPT_OVERRIDES` entry was needed going in. Scoped as "the cleanest batch yet," and it
mostly was — one clean fix, one flagged ticker's own taxonomy sitting on the wrong side of a
methodology line, and a wall of genuinely structural gaps.

### BF.B: two data sources, two different silent-failure modes

Brown-Forman's ticker string needed resolving before any fetching. SEC's `company_tickers.json`
keys it `BF-B` (hyphen); the `TICKER_PROFILES` entry as drafted used `BF.B` (dot). Neither data
source accepts the dot form, and they fail differently: `get_cik("BF.B", ...)` raises an explicit
`ValueError` (loud, safe), but `yfinance.Ticker("BF.B").info` returns a *populated-looking* dict
where every field (`currentPrice`, `sharesOutstanding`, ...) is silently `None` — exactly the
"worse than an explicit error" case the brief warned about. Fixed by using `BF-B` as the ticker
string everywhere (`TICKER_PROFILES` key, cache filename, fetch calls) — confirmed working end to
end (CIK `0000014693`, live price via yfinance) before including it in the batch.

### The one clean fix: a cash tag that helped six tickers beyond the one that was flagged

Only `TGT`'s `CashAndEquivalents` was flagged outright (18/74, 24%), but the raw tag data pointed
at a broader gap: TGT stops populating `CashAndCashEquivalentsAtCarryingValue` after FY2019 and
switches to `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` — the post-ASU-2016-18
tag that folds restricted cash into the same reconciliation line, adopted market-wide around
2018–2019. Checked for a magnitude trap before trusting it (restricted cash could inflate the
figure): at every one of the three dates where old and new tags overlap for TGT, the values are
**exactly identical** — TGT's restricted cash is $0, so the new tag is a safe superset here, not a
different economic figure. Added as a third fallback tag on a `consumer_staples`-scoped
`CashAndEquivalents` override (byte-identical-copy-first discipline: Stage B1 zero diffs, Stage B2
154 new fills, 0 changed, 0 removed, across the full 178-ticker cached universe). The fill landed
on eight tickers, not one — `TGT` (+32), `EL` (+31), `HSY` (+27), `SJM` (+27), `PG` (+26), `KDP`
(+5), `KVUE` (+5), `BG` (+1) — all `consumer_staples`, confirming the profile scoping held and the
gap was an industry-wide tag migration rather than a TGT-specific quirk.

### A trap worth naming: FIFO/LIFO substitution looks like a fix and isn't

Kroger's `Inventory` coverage (checked as part of the Step 2 retail-likeness investigation below)
was 6% under the current `retail`-style candidate tags. The obvious next tag, `FIFOInventoryAmount`
(140 raw points, excellent coverage), is *not* the same figure as `InventoryNet` — Kroger discloses
inventory on a FIFO basis with a separately-tagged LIFO reserve, and the balance sheet carrying
value is FIFO minus the reserve. Verified exactly at every overlap date:
`FIFOInventoryAmount(2010-01-30) − InventoryLIFOReserve(2010-01-30) = InventoryNet(2010-01-30)` to
the dollar, and the same held at the two other overlap dates checked. The reserve is material
(~14–16% of the FIFO figure) — using `FIFOInventoryAmount` as a fallback would silently overstate
Kroger's inventory by that much whenever it kicks in. `extract_summed_values`'s `"sum"` source type
only adds; there's no subtraction primitive to compose `FIFO − Reserve` cleanly. **Not added.**
Logged as the batch's headline trap: a tag with excellent coverage and a plausible name can still
be measuring a different number entirely — same family as the fair-value-vs-carrying-value
rejection pattern, new instance.

### Step 2: are COST/TGT/WMT/DG/DLTR/KR secretly retail?

GICS classifies these six as Consumer Staples; operationally they're merchandise retailers. Tested
`retail`'s four working-capital tags against all six without reassigning anyone (a taxonomy call
left for a human). Findings, most to least clean:

- **COST, WMT** — 96–101% coverage on all four tags. Look exactly like the 19 already-built
  `retail` tickers.
- **TGT, DG** — 90–101% on `Inventory`/`CostOfRevenue`/`AccountsPayable`; `AccountsReceivable` at
  0%, same "pure consumer checkout, no trade receivable line" pattern already confirmed for
  several `retail` tickers in the 2026-07-19 entry — expected, not a gap.
- **DLTR** — `CostOfRevenue`/`AccountsPayable` clean, `AccountsReceivable` near-zero (same
  pattern), but `Inventory` at 0% under `retail`'s current tags. DLTR's real tag is
  `RetailRelatedInventoryMerchandise` (180 raw points, smooth $741M→$2.5B growth) — not in
  `retail`'s candidate list today. If reassigned, `retail` itself would need a small tag addition
  first; noted, not acted on.
- **KR** — the outlier. `AccountsReceivable`/`AccountsPayable` look fine once corrected for a
  Kroger-specific artifact (see below); `Inventory` needs the FIFO/LIFO fix that doesn't exist (see
  above); `CostOfRevenue` at 60% shares the same root cause as the `Capex`/`OperatingCashFlow` gap.

Recommendation only, no config change: COST and WMT are as clean a `retail` fit as any of the
current 19; TGT and DG fit modulo the already-expected AR exception; DLTR fits but needs one more
tag first; KR's inventory accounting genuinely doesn't map onto the current retail concept model
without a subtraction primitive the pipeline doesn't have.

### A second Kroger-specific artifact: no Q1 cash-flow disclosure, ever

`KR`'s `Capex` and `OperatingCashFlow` sit at 47% — traced to the raw filings, not just the merged
output. Every fiscal year, Kroger's cash-flow-statement tags start at a ~16-week (not ~13-week)
cumulative duration — there is no Q1-alone or Q1-cumulative fact for these concepts anywhere in the
company-facts history. `decumulate_period_values` can only recover one genuine discrete quarter per
year from this shape (the H1→9-month difference), and its Q4-backsolve needs three preceding
quarters it never has. No alternate tag fixes this: Kroger's own interim filings simply don't
disclose a Q1 cash-flow statement figure for these lines. Confirmed structural.

### Everything else: genuinely structural, confirmed rather than assumed

- **`ADM`, `BG`, `CASY`, `CLX` — `OperatingIncomeLoss`, 0%.** None of the four have ever tagged
  `OperatingIncomeLoss` (confirmed via a full `*income*`/`*operating*` tag dump for each) — same
  "no discrete operating-income subtotal in the income statement" pattern as NKE in the
  2026-07-20 retail entry above, now confirmed in four more filers. Worth naming as a
  consumer-staples-relevant recurrence, not a one-off.
- **`STZ` — `SharesOutstanding` and `DividendsPerShare`, both 0%.** No
  `WeightedAverageNumberOf*SharesOutstanding`, no `CommonStockSharesOutstanding`, no
  `EarningsPerShareBasic/Diluted`, no per-share dividend tag — anywhere in the company-facts dump.
  Constellation Brands' Class A/Class B dual-class structure is the likely cause: filers with
  multiple share classes often tag per-share and share-count concepts only with a
  `ClassOfStockAxis` dimension, and SEC's non-dimensional `companyfacts` view excludes anything
  that's never reported as a plain default-member fact. No fix available inside this pipeline
  (it doesn't consume dimensional facts at all).
- **`HSY`, `TSN` — `DividendsPerShare`, 8% and 0%.** Both are real, long-standing dividend payers;
  neither tags a per-share figure in any of the modern (post-2010) filings checked — HSY's own
  `CommonStockDividendsPerShareCashPaid` tag has exactly 10 points, all from 2008–2010, then
  nothing ever again. Per-share dividend disclosure is optional prose/table content in many
  filings, not a required primary-statement XBRL element — some filers simply never tag it.
- **`KVUE` — `DividendsPerShare`, 35%.** Not a gap: KVUE spun off from J&J in mid-2023 and the
  first dividend followed shortly after. The existing tag (`CommonStockDividendsPerShareCashPaid`)
  is already being used correctly; the low ratio is just a young company with a short history,
  confirmed by inspecting the full 13-point series (continuous and complete from initiation
  onward).
- **`MNST` — `LongTermDebt`, 7%.** Monster Beverage was a genuinely debt-free company for most of
  its public history — `LongTermDebt` tags a literal `$0` at 2023-12-31, then real debt appears
  from mid-2024 onward. Same "no debt is not a bug" pattern as GRMN/Reddit in the 2026-07-20 retail
  entry — confirmed, not fixed.
- **`COST`, `TGT` — `Goodwill`, 16% and 23%.** Both tag `Goodwill` at fiscal year-end only, never
  in an interim 10-Q, across their entire cached history (TGT: 17 dates, one per year, 2010–2026
  without exception). A stable, deliberate filer choice for an immaterial-and-usually-unchanged
  balance-sheet line, not a transition or a gap — same underlying cause as the "static value not
  re-tagged" issue documented earlier in this project, just permanent here rather than temporary.
- **`SYY` — `DepreciationAndAmortization`, 48%.** The most surprising one: SYY tagged full
  quarterly D&A (`Depreciation`, `AmortizationOfIntangibleAssets`, `DepreciationAndAmortization`)
  from FY2010 through FY2015, then **every one of those tags goes annual-only for FY2016–FY2024** —
  nine straight fiscal years with zero quarterly duration facts for any D&A-related concept, before
  quarterly tagging resumes in FY2025. Checked across all six candidate tags, not just the primary
  one — the gap is total, not a single-tag artifact. No substitute exists because the underlying
  quarterly disclosure wasn't made. Worth naming alongside the ROST/LOW/WSM "all started at once"
  pattern as its mirror image: a filer that *stopped*, then *resumed*, tagging the same concept
  years apart, with no tag-search fix possible either way.

### Non-regression, Step 5

Full before/after diff across all 178 cached tickers (every profile, not just `consumer_staples`),
for the one concept actually touched (`CashAndEquivalents`): 0 changed, 0 removed, 154 new fills,
all eight affected tickers within `consumer_staples`. No other concept was modified this session, so
no other diff was needed.

## 2026-07-20 — Fifth stock-type profile: retail, and a generic denominator-near-zero guard

Two independent pieces of work, kept deliberately separate (different files, different
non-regression checks): extending the `retail` profile's tag coverage to 18 more tickers, and a
generic fix for a `StockholdersEquity`-denominator explosion bug found in ORLY while doing so —
the fix turned out to reach far beyond retail.

### Retail: nine fundamentals stay the same, four new balance-sheet concepts

`retail` reuses `standard`'s whole metric set unchanged and adds four working-capital concepts on
top — `Inventory` (`InventoryNet`), `CostOfRevenue` (`CostOfGoodsAndServicesSold`),
`AccountsReceivable` (`AccountsReceivableNetCurrent`), `AccountsPayable`
(`AccountsPayableCurrent`) — feeding five new fundamentals: inventory turnover, DIO, DSO, DPO,
cash conversion cycle. ORLY-verified before scaling to AZO, BBY, GPC, HD, LOW, LULU, NKE, POOL,
RL, ROST, TJX, TSCO, ULTA, WSM, DECK, TPR, HAS, GRMN (19 tickers total, only HD previously
cached — the other 18, ORLY included, were fetched fresh this session).

### A named assumption that didn't survive contact with the data

The task brief named ORLY, AZO, ROST, TJX, ULTA, TSCO, WSM as "expected" near-zero
`AccountsReceivable` cases (pure consumer-cash checkout, no trade receivable line). Checked
directly rather than taken on faith: **six of the seven have excellent AR coverage (92–99%)** —
almost certainly real commercial/professional-account receivables (ORLY's and AZO's DIFM/commercial
programs selling to independent repair shops being the clearest case) rather than nothing. Only
TSCO actually matches the assumed pattern, confirmed via exhaustive tag search (nothing beyond a
tax-receivable tag and a one-time M&A footnote item). Reported as found, not forced to fit the
brief's expectation.

### Three clean fixes, and a lot of confirmed structural gaps

GPC's `AccountsReceivable` (0%→95%, via `AccountsNotesAndLoansReceivableNetCurrent` — a combined
accounts+notes+loans line typical of wholesale distributors) and DECK's / LULU's `LongTermDebt`
(both 0%→real-but-sparse, via `NotesPayable` and `OtherBorrowings` respectively — LULU's tag is
notably always exactly $0, a confirmed "no debt" reading rather than an unknown). `LongTermDebt`
wasn't previously overridable for `retail` at all; migrated to a profile-specific `priority_merge`
override with the usual byte-identical-copy-first discipline (0 diffs across all 145 cached
tickers before the two new tags were appended).

Everything else flagged (13 of 16 gaps) turned out structural on inspection: NKE has never tagged
a discrete operating-income concept at all (confirmed via a full raw scan of every "income" tag in
its filings — the income statement goes straight from expenses to pretax income); GPC and TJX
both discontinued their `OperatingIncomeLoss`/COGS tags mid-history with no successor found;
ROST, LOW, and WSM all *started* tagging a previously-bundled line (operating income, AR, COGS
respectively) at almost exactly the same point in FY2024/2025 — three unrelated companies
independently beginning disclosure at the same time reads as a shared external cause (a
disaggregation-of-expenses change around then) rather than three coincidental gaps, though not
chased down to a specific citation. GRMN, ULTA carry essentially no debt (Garmin: no debt tag
exists at all; ULTA: one $800M COVID-era revolver draw, repaid within months) — same "no debt is
not a bug" pattern as Reddit. 0 regressions, 118 new data points, across the full cached universe.

### The equity-denominator bug: found while building ORLY, fixed generically

ORLY's `roe` and `debt_to_equity` explode to nonsense (-27,999% / -591x) at 2021-03-31, where
`StockholdersEquity` crosses to -$6.977M against $12.2B of TTM revenue — the same failure mode as
the growth-rate near-zero-base bug from 2026-07-15, this time in a ratio *denominator* rather than
a growth *base*. Generalized rather than patched locally, since the task brief was explicit that
any profile with a `StockholdersEquity`/`TangibleEquity`-denominator ratio is exposed:

```python
MIN_DENOMINATOR_SCALE_RATIO = 0.01

def apply_denominator_scale_guard(ratio, denominator, scale_reference, min_denominator_scale_ratio):
    too_small = denominator.abs() < min_denominator_scale_ratio * scale_reference.abs()
    too_small = too_small & scale_reference.notna()
    return ratio.where(~too_small)
```

`Revenue_TTM` as the scale reference (present in every profile, unlike `Assets`). Wired into
`calculate_ratio` as two new optional parameters (off by default, same additive shape as
`min_base_ratio`), applied to `roe`, `debt_to_equity`, and `build_snapshot`'s `pb_ratio`/`p_tbv`.

### AZO checked, not assumed — and turned out to be a different phenomenon

The brief asked to confirm whether AZO (same aggressive-buyback reputation) shows the same
pattern. It doesn't: AZO's equity has been **continuously, stably negative since 2009** — a
large, deliberate, permanent capital-structure choice, not a brief crossing-through-zero like
ORLY's. AZO's smallest-ever `|equity|/revenue` is 6.35%, more than 6x above the chosen threshold;
its ROE/D-E stay bounded (roughly -0.5 to -2, -1.7 to -6.6) even though equity is negative
throughout. The guard correctly leaves all of AZO's history untouched — verified, not inferred
from the "similar company" framing.

### The threshold problem was bigger than ORLY vs. AZO

Running the same equity/revenue computation across all 145 cached tickers surfaced that near-zero
or negative `StockholdersEquity` relative to revenue is a **common pattern in `standard`-profile
names with long buyback histories** — CDW, HD, HPQ, DELL, MSI, MCHP, CIEN, STX, VRSN, GDDY, IT,
GEN, AMD, FTNT all show it, confirming the brief's "not retail-specific" framing empirically. This
also killed the hope of an IBM-style clean bimodal gap (that growth-rate fix's separation doesn't
exist here — the distribution is continuous). `0.01` was chosen as a deliberately conservative
threshold: it catches every value with genuinely extreme (`|roe|`/`|debt_to_equity|` in the high
single digits to several hundred) resulting ratios, while sitting 6x below AZO's smallest
legitimate value and >26x below the smallest already-validated financial/insurance equity/revenue
ratio anywhere in the cached universe (ALL, 26.1%). A few of ORLY's own milder elevated quarters
(e.g. 2021-09-30 at roe=-14.5, ratio=1.09%) are deliberately left unmasked rather than chasing a
looser threshold that would sweep into the broad thin-but-stable tech population.

### A bug in the guard's first version, caught by its own non-regression check

The first implementation treated a missing scale reference (`Revenue_TTM` unavailable for that
date) as "can't verify → mask." This silently masked 144 previously-clean values, including
**Goldman Sachs' entire 2009–2012 ROE series (13%–21%, completely sane)** — not because GS's
equity was ever small, but because `Revenue_TTM` has its own unrelated coverage gaps for that era
(the same class of bank-Revenue-tag issue documented in the 2026-07-17 entry). Caught by the
"diff against the old logic across the full cached universe" check before being kept, same
discipline as every fix in this log. Fixed: a missing scale reference now means "can't judge,
don't mask" rather than "mask" — `too_small = too_small & scale_reference.notna()`. Final result:
0 unexplained changes, 37 intentionally masked `(ticker, end)` ROE/D-E pairs (all `standard`
profile plus ORLY), every one genuinely extreme, zero `financial`/`insurance_pc`/`insurance_life`
tickers touched.

### Deliberately left alone

`build_valuation_history`'s time-series `pb_ratio`/`p_tbv` (as opposed to `build_snapshot`'s
single-latest-value versions) have the identical exposure and were not fixed — the task scoped
the guard to "snapshot-level" specifically. Flagged as a known, parallel gap rather than silently
patched or silently ignored, same "narrower-scope tradeoff, documented" call as the `peg_ratio`
fix's simplified growth calc from the 2026-07-18 entry.

## 2026-07-19 — Fourth stock-type profile: insurance_life, and a new architecture limit surfaced

Following `insurance_pc`, life/annuity insurers were split off as their own profile from the
start rather than merged in — MET, PRU, AFL, PFG, GL (five names; ERIE and AIZ were routed to
`standard`/`insurance_pc` respectively at classification time, since Erie Indemnity is a fee-based
management company with no underwriting risk of its own, and Assurant is now predominantly
specialty P&C after selling its life block years ago).

### Same nine-fundamental / five-valuation shape, reusing insurance_pc's exact concept names

The key design choice: `insurance_life`'s raw concepts share identical names with
`insurance_pc`'s (`EarnedPremiums`, `IncurredLosses`, `BenefitsLossesAndExpenses`,
`NetInvestmentIncome`, `Investments`, `ClaimsReserve`, `RealizedInvestmentGains`) even where the
underlying tags differ. This let every metric formula (Combined/Loss/Expense Ratio, Net
Investment Yield, Reserve Growth, P/Core Earnings) transfer to Life without writing a single new
line of calculation code — only the profile's tag overlay changed. Verified end-to-end on GL
before scaling: Combined Ratio computed from `BenefitsLossesAndExpenses/EarnedPremiums` matched
GL's real reported ratios almost exactly (95.4%, 95.4%, 95.7% for FY2022–24) and, notably, came
out far more stable year-to-year than P&C's — expected, since life/health claims are actuarially
predictable in a way catastrophe-exposed P&C claims aren't. Net Investment Yield ran structurally
higher than P&C (5.8% vs. TRV's ~4%), consistent with life insurers running longer-duration
portfolios against long-duration liabilities. `DepreciationAndAmortization` and
`CashAndEquivalents` are excluded for this profile (same reasoning as `insurance_pc` — neither
concept nor any metric depending on it applies structurally); notably `Capex` and
`OperatingIncomeLoss`, both excluded for P&C, were *not* flagged for GL, confirming the two
sub-profiles genuinely needed independent exclusion lists rather than a shared one.

### One real difference from P&C: RealizedInvestmentGains needed a genuine two-tag sum for GL

TRV had a single clean tag for realized investment gains/losses. GL does not — its current gains
are split across `GainLossOnSaleOfInvestments` (the dominant figure) and
`GainLossOnSaleOfOtherInvestments` (a small, genuinely separate line, likely real estate/equity-
method investments), both continuously present with clearly different, non-duplicate values —
confirmed additive, not the same fact under two names, before summing. `mode: "sum"` was
sufficient (no overlap risk, unlike the debt cases that needed `priority_merge`).

### LDTI (ASU 2018-12) restatement confirmed as a real, recurring pattern, not noise

Anticipated before scanning (long-duration contract accounting changed materially in 2023) and
then verified directly in raw `filed` timestamps across GL, PRU, and PFG: the same reporting
period's `LiabilityForFuturePolicyBenefits` value gets refiled at a materially different number
after the transition (GL's 2021-12-31 figure moved from $16.0B to $24.5B between filings; PRU's
2022-12-31 moved from $281.2B to $261.8B) — a genuine same-fact basis revision, not a data error
or two competing facts. The pipeline's existing "latest `filed` wins" tie-break already handles
this correctly by construction; no code change was needed, only correct recognition of the
pattern before treating a value jump as a bug.

### Second Claude Code scan-and-apply run for this profile, same non-regression discipline

3 of 10 flagged gaps resolved cleanly (AFL LongTermDebt via `NotesPayable`; AFL and PFG
`RealizedInvestmentGains` via `GainLossOnInvestments`, migrated to `priority_merge` with the
usual two-stage byte-identical-then-extend discipline). 0 regressions across the full 127-ticker
cached universe. MET required no changes at all.

### The interesting result: a candidate was found and *correctly rejected* for architectural reasons

PRU has an excellent, fully continuous `RealizedInvestmentGainsLosses` tag that would resolve its
gap outright — but that exact tag name, checked against GL at all 29 overlapping dates, disagreed
with GL's already-verified total by up to an order of magnitude (e.g. $240K vs. -$26.1M at one
date). This isn't an ambiguous edge case — it's conclusive evidence the same tag name means a
different reporting scope for GL than for PRU. Since `PROFILE_CONCEPT_OVERRIDES` only supports
profile-wide tag lists, not per-ticker exceptions within a profile, there is currently no way to
give PRU this tag without also silently exposing GL to it (or building a per-ticker override
layer, which doesn't exist yet). Correctly left unresolved and documented rather than forced —
the same "empirical proof over stated confidence" discipline that caught the debt-merge bug
in an earlier session, this time working preventively instead of after the fact.

### Deliberately left alone

AFL's `Investments` has no consolidated tag at all (only fragmented components) — same "not
worth a fragile multi-tag reconstruction" call as Micron's lease amortization. AFL's and PRU's
annual-only `Goodwill` tagging is the same filer-frequency limit already logged for ACGL/AIG.
PFG's and PRU's `ClaimsReserve` gap has a fuller alternative tag
(`LiabilityForFuturePolicyBenefitsAndUnpaidClaimsAndClaimsAdjustmentExpense`) but its margin over
the narrower reference definition was inconsistent (~1%–13% across dates) rather than a clean,
explainable constant — left unresolved rather than silently redefining what `ClaimsReserve` means
for two tickers. PFG additionally has one genuine, unexplained single-quarter gap
(`LiabilityForFuturePolicyBenefits` at 2021-12-31) inside otherwise-complete annual data — flagged
as-is, not guessed at.

### Open, going into future sessions

The PRU case is the first time this session hit a limitation worth naming explicitly: a **per-
ticker override mechanism within a profile** doesn't exist yet — only profile-level overlays. This
wasn't needed for any prior fix (bank/tech tag differences were always profile-wide), but it's
now a concrete, documented gap rather than a hypothetical one. Not building it now — same
"dedicated session, not bundled into this one" call as the earlier point-in-time forward-fill
question — but it's the natural next architecture item once enough of these single-ticker
exceptions accumulate to justify it.

## 2026-07-18 — Third stock-type profile: insurance_pc (P&C insurers), split cleanly from insurance_life

Following the financials (banks) and tech profiles, insurance was next — but "insurance" in
GICS Financials is itself three different businesses that don't share economics: P&C/multiline
(short-tail, annually-repriced, underwriting-driven), life/annuities (long-tail, spread-driven,
closer to a bank than to a P&C insurer), and brokers (MMC, AON, AJG, BRO, WTW — carry no
underwriting risk at all, economically a service business). Brokers were deliberately left on
the `standard` profile rather than mis-filed, same logic as keeping Visa/Mastercard out of
`financial` earlier. `insurance_pc` and `insurance_life` were split into two profiles from the
start (not merged-then-split later) — eleven P&C names (TRV, CB, PGR, ALL, AIG, WRB, CINF, ACGL,
HIG, L, EG) and seven life/annuity names (MET, PRU, AFL, PFG, GL, AIZ, ERIE) — with `insurance_life`
built empty for now, ready for its own metric definitions when that profile is tackled directly.

### Why P&C needs its own metric vocabulary

The central discovery, mirroring the bank NIM/efficiency-ratio work: P&C's defining ratios
don't exist as single XBRL tags. **Combined Ratio has no tag at all** — verified by search, not
assumed — so it's built like PPNR was for banks: `BenefitsLossesAndExpenses_TTM /
EarnedPremiums_TTM`, validated against TRV's own reported combined ratios (98.4%, 99.3%, 100.6%,
95.9% for 2021–2024 — matches real disclosed figures almost to the point). Loss Ratio and
Expense Ratio decompose it (`IncurredLosses_TTM / EarnedPremiums_TTM`, and Expense Ratio as the
pure residual `combined − loss` — no separate underwriting-expense tag needed at all, since the
only candidate found, `AmortizationOfDeferredAcquisitionCostsDAC`, stopped being tagged in 2010
and would've been useless anyway).

Nine fundamentals for `insurance_pc`: revenue/income growth, ROE, payout (inherited) + Combined
Ratio, Loss Ratio, Expense Ratio, Net Investment Yield (`NetInvestmentIncome_TTM / Investments`),
Reserve Growth (YoY change in `LiabilityForClaimsAndClaimsAdjustmentExpense` — a credit-quality-style
early-warning signal, same role the provision ratio plays for banks). Five valuation metrics, not a
forced six: P/E, P/TBV (replaces P/B, `Goodwill` moved from the `financial` override into the base
config since it's a universal GAAP concept, not bank-specific — available to every profile now),
Dividend Yield, PEG, and P/Core Operating Earnings (`market_cap / (NetIncome_TTM −
RealizedInvestmentGains_TTM)` — strips out realized investment gains/losses, which are market noise,
not underwriting performance; the insurance analogue to PPNR). New raw concepts: `EarnedPremiums`
(`PremiumsEarnedNet`), `IncurredLosses` (`PolicyholderBenefitsAndClaimsIncurredNet`),
`BenefitsLossesAndExpenses`, `NetInvestmentIncome`, `Investments`, `ClaimsReserve`, and
`RealizedInvestmentGains` — all TRV-verified before scaling, same discipline as JPM for banks.

### Two long-standing pipeline gaps surfaced and fixed along the way, unrelated to insurance itself

`peg_ratio` had silently never existed in `build_valuation_history` — it was only ever computed
in `build_snapshot`, so every profile's valuation *chart* (not just insurance's) had shown "keine
Daten" for PEG since the feature was built, unnoticed until insurance's chart made it obvious.
Fixed by computing `revenue_yoy_growth` directly inside `build_valuation_history`
(`wide.groupby("ticker")["Revenue_TTM"].pct_change(periods=4)`) — a simplified version without the
`min_base_ratio` near-zero-base guard from the July growth-rate fix, accepted as a deliberate,
narrower-scope tradeoff for chart display only. Separately, `check_data_quality` was still being
called with a single ticker's expected-concepts list for the whole batch (`TICKERS[0]`) — harmless
with one ticker, silently wrong the moment a second profile entered the same run (TRV's insurance
concepts were being checked against MSFT). Fixed by moving the whole function to a per-ticker
expected-concepts dict, closing a gap flagged as a known limitation weeks earlier and left
unaddressed until it actually broke.

### Second successful Claude Code scan-and-apply run, same non-regression discipline

Scanned the remaining 10 `insurance_pc` tickers against the TRV-verified pattern, authorized to
apply `priority_merge` mode migrations directly if needed (expected, since several concepts
needed genuine `sum` combinations of coexisting debt instruments — EG's `SeniorNotes` +
`NotesPayable`, WRB's `NotesPayable` + `SubordinatedDebt`). Every change diffed against the full
122-ticker cached universe, TRV included as the reference that must never move. One candidate
tag was added, then caught and reverted mid-task: a realized-gains component that looked fine for
L (no baseline to check against) turned out, once cross-checked against AIG's known total, to be
off by more than 10x — a partial component silently masquerading as the total. Final result: **0
regressions, 569 new data points, 9 of 22 flagged gaps fully resolved**, the rest documented with
a specific, verified reason (annual-only tagging confirmed via raw `fp`/`start` fields, sign
mismatches at the only overlap point, order-of-magnitude component checks) rather than a vague
"structural gap."

### Deliberately left alone

Four RealizedInvestmentGains/BenefitsLossesAndExpenses gaps (ACGL, AIG, CB, WRB) would need a
full itemized multi-era tag reconstruction to close safely — same "not worth the fragility" call
as Micron's lease amortization and JPM's minor intangibles. AIG's and ACGL's annual-only
`Goodwill` tagging is a filer limitation, not fixable by tag substitution; the general fix (forward-
filling point-in-time values between annual reports) would be a pipeline-wide architecture change
affecting every profile's balance-sheet concepts, not an insurance-specific patch — flagged for a
dedicated session, not bundled into this one.

## 2026-07-17 — Claude Code as a tag-discovery scout, and a real architecture bug it caught

The financials work (2026-07-16) proved the tag-hunting method — search, verify magnitude/overlap,
decide fallback vs. sum — but doing it ticker-by-ticker doesn't scale to the S&P 500. Today's shift:
delegate the *mechanical* search-and-screen work to a Claude Code agent, while keeping every config
change gated behind an explicit, empirically-verified non-regression check before it's trusted.

### The workflow, in three escalating rounds

**Pilot (15 mixed tickers).** First test of whether an agent could apply the same judgment used
manually all session — reject `LiabilitiesAndStockholdersEquity` (balance-sheet total, not equity),
reject `NonoperatingIncomeExpense` for `OperatingIncomeLoss` (the literal opposite concept, despite
passing every mechanical filter), flag but don't blindly add anything that overlaps an existing tag
with *different* values. It did. It also found that `SEARCH_HINTS` using bare words like `"sales"`,
`"debt"`, `"loss"` were substring-matching into unrelated tag families (`AvailableForSaleSecurities`
alone accounted for most of the noise) — hints were narrowed before scaling up.

**Run 2 (92 tickers — the full S&P Tech + true-Banks universe).** 53 of 92 came back clean. The
dominant remaining gap: `LongTermDebtAndCapitalLeaseObligations*`, a real, larger figure (debt +
finance leases) that consistently overlapped the existing `LongTermDebt` tags with *different*
values across ~18 tickers — correctly left as "needs a human mode decision," not auto-appended.

**Apply pass — and the bug.** Instructed to append the safe findings, with one hard rule: *a fix
for one ticker must never change a value for an already-working one.* The agent tested every
addition individually against all 92 tickers before keeping it, and found that reasoning supplied
in the task brief — "appending a tag at the end of `tags` is safe because first-match-wins" — was
incomplete. `fallback_then_sum` let *any* tag in `tags` unconditionally beat the `sum_tags` result,
regardless of where in `tags` it sat; position only mattered relative to other tags, not to sums.
Appending the lease tags "last" still silently overwrote dates that were correctly served by summing
`LongTermDebtNoncurrent + LongTermDebtCurrent` (caught: AMD's debt at one date shifting from
2,019,000,000 to 2,037,000,000 with no visible warning). 331 regressions were found this way, before
anything was kept — only 3 of the ~10 proposed additions survived. This is the payoff of insisting
on empirical diffing over trusting the stated reasoning, mine included.

### The real fix: one merge mechanism instead of two special-cased, buggy ones

`fallback_then_sum` (tags-always-beat-sums) and `fallback_sum` (fallback only fires if the *entire*
primary series is empty, an all-or-nothing-per-ticker gate that structurally blocked six D&A-thin
banks from ever using their configured fallback tags) turned out to be the same underlying flaw in
two disguises: neither was a true single-tier, per-date priority list.

Replaced both with one new mode, `priority_merge`. A concept declares an ordered `sources` list —
each entry either `{"type": "tag", "tag": "..."}` or `{"type": "sum", "tags": [...]}` — and
extraction is a single per-date pass: first source in the list with a value for a given date wins,
full stop, with sums treated as an ordinary entry rather than a special second tier.

```python
"LongTermDebt": {
    "sources": [
        {"type": "tag", "tag": "LongTermDebt"},
        # ...existing tags in their existing order...
        {"type": "sum", "tags": ["LongTermDebtNoncurrent", "LongTermDebtCurrent", "NotesPayableCurrent"]},
        {"type": "tag", "tag": "LongTermDebtAndCapitalLeaseObligations"},
        {"type": "tag", "tag": "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities"},
    ],
    "mode": "priority_merge",
},
```

Migrated with a two-step discipline: first a pure restructuring with zero new tags, required to
prove byte-identical output against the old modes across all 111 cached tickers (it was, for
`LongTermDebt`; for `DepreciationAndAmortization` it wasn't — 493 previously-unreachable values
appeared with nothing changed or removed, which is the all-or-nothing gate finally being gone, not
a defect, and was reported as such rather than forced to match the old, buggy behavior). Only after
that proof did the previously-blocked tags get added, this time genuinely safe by construction
because a per-date merge with explicit priority can't overwrite anything above it in the list.
Zero regressions on the second pass either — nothing had to be reverted this time.

### Net result

- **9 of the 36 still-open tickers fully resolved** (ACN, APH, INTC, JBL, MU, NXPI, TER, TRMB, BAC),
  several more meaningfully improved (GLW LongTermDebt 20%→97%, KEYS/MTB D&A into the 90s%).
- **1,196 new data points** recovered across `LongTermDebt` and `DepreciationAndAmortization`,
  zero previously-correct values touched, at any stage.
- `fallback_then_sum` and `fallback_sum` are no longer used anywhere in `config.py`; the old code
  paths were left in place (unused, not deleted — no reason to remove working dead code) in case a
  future concept genuinely wants that simpler, two-tier shape.
- Sector coverage: **~92 of ~504 S&P 500 constituents (~20%) now have systematically vetted tag
  configs** — the full Information Technology sector plus true depository banks, split out from
  insurers and capital-markets/payments names (which don't fit either existing profile and were
  deliberately left unscanned this round rather than mis-filed).

### Open, going into next session

Three threads handed to a follow-up Claude Code task, same non-regression discipline: (1) confirm
no other concept has the same architecture symptom under a different mode name, (2) a further tag
search for the 11 tech tickers whose `LongTermDebt` gap survived even the lease-tag addition, and
(3) bank `Revenue` for TFC/FITB/HBAN/RF/BNY/MTB/SYF — where no single tag has ever covered the
total, so the candidate fix is a genuine `{"type": "sum"}` of net-interest-income + noninterest-
income, validated against a working bank (JPM) before being trusted on the broken ones.

Longer-term: the GICS sectors scanned so far (Tech, Banks) were the two profiles that already
existed. The next several sessions' decisions are squarely about the sectors that don't fit either
— insurers (own economics: premiums, combined ratio, float, no NIM), capital-markets/payments names
(economically closer to tech than to banks — Visa, Mastercard, the exchanges, asset managers), and
eventually Consumer Staples/Healthcare/Industrials, none of which have been profiled at all yet.
Each will likely need its own profile, its own metric registry entries, and its own round of this
same scout → apply → verify cycle.

## 2026-07-16 — Stock-type profiles: making financials analysable (JPM as first bank)

The largest single addition so far. Until now the whole tool was implicitly tuned for
tech/growth stocks; financials (banks) produced either nonsense (a `debt_to_equity` of 9 for a
deposit-funded bank) or empty metrics. The goal: JPM analysable as richly as MSFT, without
touching how tech tickers behave, and built as a clean foundation for the eventual frontend
(where a user picks any ticker). Chosen approach: per-ticker profile ("Weg B"), full metric
set per profile ("Stufe 2").

Two problems had to be kept separate throughout: (1) *different tags* — banks tag the same
concept differently (solvable with the existing tag-list machinery); (2) *different metrics* —
some ratios don't exist or mean something else for a bank (EV/EBITDA, debt_to_equity, FCF are
meaningless; NIM, ROA, efficiency ratio, P/TBV take their place). Most naive tools only solve
(1) and then emit a technically-computed but economically-meaningless number.

### Architecture: three declarative layers, one visibility source of truth

Deliberately declarative rather than scattered `if profile == "financial"` checks, so the
frontend can later toggle profiles without rewrites.

- **`TICKER_PROFILES`** maps ticker → profile (`"JPM": "financial"`), default `"standard"`.
- **Visibility** — `PROFILE_HIDDEN` lists, per profile, which metric/chart columns to blank.
  Symmetric: `financial` hides the tech metrics (ev_ebitda, debt_to_equity, fcf_margin,
  rule_of_40, pb_ratio, …); `standard` hides the bank metrics (nim, efficiency_ratio, roa,
  equity_to_assets, provision_ratio, p_tbv, p_ppnr). A single `is_hidden(ticker, metric)`
  function is the only place that knows the logic, imported by every output stage.
  **Philosophy 1 chosen**: everything is always *computed*, only *display* is filtered — so a
  future "show JPM with standard metrics" toggle needs no recompute. Applied at every output:
  snapshot (`apply_profile_filter`), both chart sets (filter `concepts_to_plot`), and the
  long-format CSVs (`filter_hidden_rows`). Raw `quarterly_facts` deliberately NOT filtered —
  raw balance-sheet values stay complete even when the derived ratio is hidden.
- **Concept overrides** — `PROFILE_CONCEPT_OVERRIDES` + `get_concept_candidates(ticker)` layer
  profile-specific concept configs over the shared base via `.update()` (same base+overlay
  pattern as `fallback_then_sum`). Base config (tech) untouched; banks only override/add.

### Bank concepts added (all as `financial` overrides, verified per ticker)

- **Revenue** → `RevenuesNetOfInterestExpense` (JPM's total net revenue; the standard tags
  only caught the contract-with-customer slice, hence the original 36% coverage and a
  *negative* PEG from a broken yoy_growth). Fixing this alone flipped PEG from −6.9 to +4.8.
- **Assets** → `Assets` (total assets, feeds NIM, ROA, equity/assets).
- **NetInterestIncome** → `InterestIncomeExpenseNet` (duration, into `TTM_CONCEPTS`).
- **NoninterestExpense** → `NoninterestExpense` (duration, TTM).
- **NoninterestIncome** → `NoninterestIncome` (duration, TTM; for PPNR).
- **Goodwill** → `Goodwill`. Other intangibles (finite/indefinite/other) checked and
  *deliberately dropped* — fragmented tags, gaps, and only low-single-digit billions vs. a
  ~50bn goodwill on a ~4tn balance sheet. Same "marginal, not worth the fragility" call as the
  Micron lease-amortization decision. TBV = Equity − Goodwill.
- **ProvisionForCreditLosses** → `ProvisionForLoanLeaseAndOtherLosses` (continuous 2007→2026;
  two shorter competing tags rejected). Negative values in 2021 are real — post-COVID reserve
  releases, not a bug.

### The 9 + 6 → 9 + 4 metric set for banks

Fundamentals (9): revenue growth, income growth, ROE, payout (inherited) + **NIM**
(NetInterestIncome_TTM / Assets), **efficiency ratio** (NoninterestExpense_TTM / Revenue_TTM),
**ROA** (NetIncome_TTM / Assets), **equity/assets** (leverage inverse), **provision/revenue**.

Valuation — honestly 4, not a forced 6: **P/E**, **P/TBV** (replaces P/B for banks via
`PROFILE_HIDDEN`), **dividend yield**, **P/PPNR** (market_cap / (NII + NonII − NonExp) — the
Fed-stress-test pre-provision-net-revenue, the clean bank analogue to EV/EBITDA without the
EV problem). The last two slots left *empty on purpose*: EV-multiples are conceptually broken
for banks (deposits are the raw material, not a financing layer), and bank FCF is ill-defined.
Two empty slots is more honest than two misleading numbers.

Sanity checks all held: NIM ~1.4–2.6%, efficiency ~52–55%, ROA ~1.2%, equity/assets ~7.4%
(≈13.5x leverage, normal for a trading-heavy megabank), P/TBV 2.95 > P/B 2.53 (goodwill effect),
P/PPNR avg 7.6 < P/E avg 10.4 (pre-provision, pre-tax → larger denominator).

### Two follow-on fixes

**Dynamic chart grid.** The fixed 3×3 / 2×3 grids left empty boxes once metrics vary per
profile (banks: 4 valuation charts in a 2×3 = two blanks). Added `_make_grid(n)` (ceil-division
to rows×cols) and blank-axis cleanup for leftover cells. Fundamentals stayed 3×3 only by
coincidence (14 − 5 hidden = 9); now it's robustly derived, not lucky.

**Data-quality for profiles.** Banks kept warning on `Capex` / `OperatingIncomeLoss` /
`LongTermDebt` / `CashAndEquivalents` — concepts that are structurally irrelevant for banks but
still expected. Added `PROFILE_EXCLUDED_CONCEPTS` + `get_expected_concepts(ticker)`. Two subtle
bugs found while wiring it: (1) `print_data_quality` was still called with
`get_concept_candidates().keys()` instead of the pruned `get_expected_concepts()`; (2) more
importantly, `check_data_quality` builds its counts from what's *actually in facts*, so the
expected-list was only an *additive* list (what's missing), not a whitelist — `LongTermDebt`
was still loaded and thus still counted. Fixed by intersecting up front:
`df = df[df["concept"].isin(expected_concepts)]`. Side effect (intended): derived concepts
(Revenue_TTM, PPNR, TangibleEquity, …) are also excluded from coverage warnings — correct, since
those are validated via end-metric plausibility, not coverage. `SEARCH_HINTS` extended for all
new bank concepts so a future thin bank concept gets a proper explore_tags suggestion.

### Known debt carried forward (not done today)

`build_snapshot` still pulls each metric out of the metrics dict by hand (one `get_latest_row`
+ merge line per metric) — increasingly tedious with every bank metric, and worse once
consumer-staples / healthcare profiles arrive. Flagged for a refactor: have `build_snapshot`
consume the metrics dict generically. Consumer staples and healthcare profiles still
unverified (expected to be much closer to tech than banks are).

## 2026-07-16 — New feature: `build_snapshot_as_of` (retroactive snapshots)

Follows the manual MU backtest (ignoring the last N rows of each series to see whether the
framework would have flagged it as undervalued a year ago). Automates that instead of redoing it
by hand per ticker.

### Approach: filter inputs, reuse the existing pipeline

`calculate_ttm` / `calculate_growth` / `calculate_rolling_average` already only look backward
(rolling window, `.shift(periods)`), so no metric-calculation logic needed to change. Filtering
`facts`, `metrics`, and `rolling_pe` to `end <= cutoff_date` *before* handing them to the existing
`get_latest_value` / `get_latest_row` (both already `idxmax` on `end`) reproduces "latest known
value as of the cutoff" for free. `build_snapshot` itself is untouched — it just receives
pre-cut inputs plus a historical price instead of the live one.

```python
def build_snapshot_as_of(cutoff_date, facts, metrics, price_history, rolling_pe):
    cutoff_date = pd.Timestamp(cutoff_date)
    facts_cut = facts[facts["end"] <= cutoff_date]
    metrics_cut = {k: df[df["end"] <= cutoff_date] for k, df in metrics.items()}
    rolling_pe_cut = rolling_pe[rolling_pe["end"] <= cutoff_date]
    prices_cut = get_price_as_of(price_history, cutoff_date)
    ...
    return build_snapshot(facts_cut, metrics_cut, prices_cut, rolling_pe_cut)
```

`get_price_as_of` does the same thing for the price series: filter to `date <= cutoff`, take the
latest row per ticker.

Wired into `main()` via a new `SNAPSHOT_AS_OF_DATES` list in `config.py` (empty by default, so a
normal run is unaffected). Each date produces `snapshot_asof_{date}.csv` alongside the regular
snapshot.

### Known limitation, accepted deliberately

This is "latest value under today's data", not "what an analyst could actually have known on that
date." SEC restatements retroactively update comparative periods in the newest filing (see the
2026-07-13 ServiceNow split note) — old 10-Qs keep their pre-restatement values, but this
snapshot pulls from the current `facts` DataFrame, which reflects whatever value survived
deduplication (generally the latest filed, i.e. restated, one). True point-in-time would require
threading `filed` through `build_dataframe` (currently dropped) and filtering on `filed <= cutoff`
instead of `end <= cutoff` — meaningfully more work, not done here. Same category of trade-off as
`MAX_MULTIPLE`: pragmatic, not principled, documented rather than solved.

**Verified:** MU as-of 2025-08-28 (pe_ttm 16.0, ev_ebitda 7.7, peg 0.33) vs. current (pe_ttm 20.5,
ev_ebitda 14.7, peg 0.12) — matches the manual backtest from the prior session.

## 2026-07-16 — New mode `fallback_then_sum`: resolves the AAPL debt gap left open by the last fix

The previous entry's accepted trade-off ("a future company with genuinely separate debt across
multiple tags would only get the first tag") turned out not to be hypothetical. AAPL's aggregate
`LongTermDebt` tag has a six-year gap (2015-03-28 → 2021-09-25) — exactly the era of Apple's bond
issuance for buybacks — while `LongTermDebtNoncurrent` / `LongTermDebtCurrent` are gapless
throughout. Under plain `fallback`, that whole window silently dropped the current portion
(e.g. 13.5bn missing at 2019-06-29).

### The fix: per-date aggregate-first, component-sum-as-gap-filler

New mode in `extract_with_mode`:

```python
if mode == "fallback_then_sum":
    aggregate_values = extract_merged_values(us_gaap_data, cfg["tags"], period=period, is_point_in_time=is_point_in_time)
    component_values = extract_summed_values(us_gaap_data, cfg["sum_tags"], is_point_in_time=is_point_in_time, period=period)

    merged = {v["end"]: v for v in component_values}
    merged.update({v["end"]: v for v in aggregate_values})

    return sorted(merged.values(), key=lambda v: v["end"])
```

Component sums go in first, aggregates overwrite via `.update()` — so for any date where a clean
aggregate exists it always wins, and the summed components only fill dates where none of the
aggregate tags have a value. This is the same discriminant as `fallback_sum`, just evaluated
per-date instead of globally (the global all-or-nothing check would have missed AAPL entirely,
since the aggregate tags aren't *fully* empty, just gapped).

### Config split: two lists, and which tags go where matters

```python
"LongTermDebt": {
    "tags": ["LongTermDebt", "DebtLongtermAndShorttermCombinedAmount", "LongTermNotesAndLoans",
             "ConvertibleLongTermNotesPayable", "ConvertibleDebtNoncurrent",
             "ConvertibleDebtCurrent", "ConvertibleNotesPayableCurrent"],
    "sum_tags": ["LongTermDebtNoncurrent", "LongTermDebtCurrent", "NotesPayableCurrent"],
    "point_in_time": True,
    "mode": "fallback_then_sum",
},
```

Convertible tags stay in `tags` (fallback), not `sum_tags` — at NOW they carry the *entire* debt
alone under one name; summing them with anything reintroduces the double-count from the last fix.
Only the genuinely non-overlapping Noncurrent/Current/NotesPayableCurrent triplet goes in
`sum_tags`.

### Verified

- **AAPL** 2019-06-29 now reads 98,465M (= 84,936M Noncurrent + 13,529M Current, matches exactly);
  2021-09-25 reads the raw aggregate 118,700M again once it resumes — confirming aggregate wins
  over sum at the handoff point.
- **NOW** 2020-12-31 back to 1,640M (not the previous double-counted 3,280M); Convertible tag
  values pass through untouched, confirming no regression on the ticker the last fix protected.

## 2026-07-15 — LongTermDebt: sum → fallback, fixing MU, a latent NOW double-count, and ORCL

Onboarding **MU** surfaced a `LongTermDebt` coverage gap that, when chased down, revealed the
`sum` mode was the wrong tool for all of these tickers — and had been silently double-counting
**NOW** since well before this session. One config change (`sum` → `fallback`) fixed three
tickers at once. Adding **ORCL** then required extending the tag list for a different reporting
vocabulary.

### MU: components stop in 2013, aggregate takes over

`LongTermDebtNoncurrent` / `LongTermDebtCurrent` both end at 2013-05-30. From 2020 on, Micron
reports only the bare aggregate `LongTermDebt` — which the config's `sum` list did not include,
so the entire relevant era (2020–2025, debt rising 6→12bn through the memory-capex cycle) was
missing. In the 2010–2013 overlap the bare `LongTermDebt` equals `Noncurrent + Current` exactly
(e.g. 2012-08-30: 3,038M + 224M = 3,262M), so it is the same debt reported as an aggregate.

### The real discovery: `sum` was double-counting NOW

Checking whether a `fallback_sum` approach would break NOW/Meta instead revealed that NOW's
existing debt series was already wrong. NOW reports the same convertible note under *both*
`ConvertibleLongTermNotesPayable` and `LongTermDebtNoncurrent` in the 2019–2021 window, and the
`sum` mode added both:

```
2019-12-31   1,442,630,000   (should be ~694M — doubled)
2020-12-31   3,280,000,000   (should be ~1,640M — doubled)
2021-03-31   1,611,000,000   (correct again — only one tag present)
```

The original ServiceNow verification missed this because it only checked the *current edge*
(~1.49bn, where only one tag is present) against a known figure — not the middle of the series.
Lesson: "the latest value is right" does not mean "the series is right".

### Why fallback fixes all three

Laying the three tickers side by side, each reports its *entire* debt in a single consolidated
tag — nothing actually needs summing:

- **Meta** → `LongTermDebtNoncurrent` (real bonds; bare `LongTermDebt` present too, identical)
- **NOW** → `ConvertibleLongTermNotesPayable` (no bare `LongTermDebt` at all)
- **MU** → bare `LongTermDebt` (aggregate)

`fallback` takes the first tag with a value per date and never sums, so overlap-driven
double-counting is structurally impossible. Switched `mode: "sum"` → `"fallback"` with a
priority-ordered tag list (aggregate first, components last). Verified across MU/NOW/Meta run
together: NOW's 2019–2021 window now shows ~694M / ~1,640M, MU is continuous 2020–2025, Meta
unchanged.

**Trade-off accepted:** `fallback` swaps the double-count risk of `sum` for an *under*-count risk —
a future company with genuinely separate, non-overlapping debt across multiple tags (real bonds
*and* separate convertibles, both to be added) would only get the first tag. None of the current
tickers are like this, but it's the assumption the fix rests on.

### ORCL: a different tagging vocabulary

Oracle came in at 39% debt coverage — it uses none of the existing tag families. It reports under
`LongTermNotesAndLoans` / `LongTermNotesPayable` (identical, 85,297M = long-term only),
`NotesPayableCurrent` (7,271M = short-term), and `DebtLongtermAndShorttermCombinedAmount`
(92,568M). The arithmetic confirms the structure: 85,297 + 7,271 = 92,568, so the Combined tag is
the clean long+short aggregate — exactly what we want, and the same tag that had been the winner
for SoFi earlier.

Added `DebtLongtermAndShorttermCombinedAmount` and `LongTermNotesAndLoans` to the fallback list
(Combined second, right after bare `LongTermDebt`; `LongTermNotesPayable` omitted as a duplicate
of `LongTermNotesAndLoans`). ORCL now runs continuously ~2015→2026, ending ~129bn (the AI
data-centre debt build).

**Two consistency notes carried forward, not resolved:**

- `DebtLongtermAndShorttermCombinedAmount` is long+short; the bare `LongTermDebt` used for MU/Meta
  may be long-only. Small divergence (~8% for ORCL) but the concept is not perfectly uniform across
  tickers — same category as the OperatingIncomeLoss / lease-inclusion definition calls.
- Because the Combined tag is now generic, **SoFi's debt will populate** on its next run — the value
  we had deliberately left empty because deposit-funded neobank debt is ambiguous. Not broken, just
  to be read with care if SoFi is revisited.

## 2026-07-15 — Growth rates unreadable on near-zero base (IBM, CRM, NOW)

`income_yoy_growth` produced meaningless spikes across three tickers: CRM hit +3131%,
+830%, +1888% in its 2012–2021 near-zero-profit era; IBM showed +448%/+346%/+316% during
the Kyndryl-spinoff quarters; NOW spiked in 2023 as it first turned profitable. Same
category as the ServiceNow `avg_pe_5y` and Amazon P/E cases — a ratio whose denominator is
technically positive but negligibly small stops conveying information.

### The existing guard was half the fix

`calculate_growth` already masked negative bases:

```python
filtered_df["prev_value"] = filtered_df["prev_value"].where(filtered_df["prev_value"] > 0)
```

This catches sign flips (negative → positive base, where the growth rate is even directionally
wrong) but does nothing for a base that is positive yet tiny. `150M / 5M − 1 = +2900%` passes
straight through.

### The discriminant: base must be substantial *relative to* the current value

An absolute floor (`prev_value > 100M`) was rejected — arbitrary, and doesn't scale across
company sizes. The relative test scales automatically and matches the real failure mode: a
growth rate is only meaningful when *both* endpoints have a sensible magnitude.

```python
def calculate_growth(df, concept, periods, result_name, min_base_ratio=0.33):
    ...
    filtered_df["prev_value"] = filtered_df.groupby("ticker")["value"].shift(periods)

    valid_base = (
        (filtered_df["prev_value"] > 0)
        & (filtered_df["value"] > 0)
        & (filtered_df["prev_value"] >= min_base_ratio * filtered_df["value"])
    )
    filtered_df["prev_value"] = filtered_df["prev_value"].where(valid_base)

    filtered_df[result_name] = filtered_df["value"] / filtered_df["prev_value"] - 1
```

Three conditions: base positive (as before), current value positive (new — a negative current
value produces a nonsense rate the old code let through), and base ≥ 33% of the current value.

### Tuning `min_base_ratio` from the data, not from theory

The threshold was read off the real split between artefacts and genuine values, the same way
`normalize_split_adjusted` reads split factors off the data rather than assuming them.

IBM gave the cleanest separation:

```
keep  2026-03  +96%  → base/value ≈ 0.51
keep  2025-12  +76%  → base/value ≈ 0.57
kill  2023-09  +448% → base/value ≈ 0.18
kill  2024-03  +346% → base/value ≈ 0.22
```

Any threshold in 0.25–0.45 separates these. 0.33 sits mid-gap with margin on both sides.

Verified across all three problem tickers:

- **IBM** — Kyndryl-era spikes (2023-09 → 2024-06) gone; real recovery at the recent edge
  (+76%, +96%) kept; the 2018-12 +52% borderline (ratio ≈ 0.66) correctly survives.
- **NOW** — 2023 near-zero spikes gone; genuine strong jumps 2021-12 (+94%, ratio ≈ 0.52) and
  2023-03 (+79%, ratio ≈ 0.56) kept; recent edge intact.
- **CRM** — the absurd 30×-type values removed. A few borderline values survive (2023-07 +194%,
  ratio ≈ 0.34, just over the line). Unlike IBM, CRM's near-zero era spans a whole decade, so
  the artefact/genuine gap is not perfectly clean — no single threshold separates it exactly.
  Accepted deliberately: the survivors are no longer *absurd*, only *to be read with care*,
  which is true of any growth rate off a near-zero base regardless of filter.

`calculate_all_metrics` calls `calculate_growth` without the parameter — the default handles it,
no call-site change needed.

### Follow-on: reverted the growth chart from symlog to linear

The `income_yoy_growth` panel in `figures.py` had been on a symlog y-axis purely to keep the
extreme spikes on-scale. With the spikes now filtered at the source, the axis is back to plain
linear — the chart shows the real range without compression, and there is nothing left that
needs taming.

**Pragmatic threshold, not a principled one** — same spirit as `MAX_MULTIPLE = 200`. It removes
the values that break the scale and accepts that "mathematically valid but economically
meaningless" is ultimately a reading-the-chart judgement no parameter fully captures."

## 2026-07-15 — Google: two "not a bug" cases (SharesOutstanding, D&A)

Two separate investigations while onboarding **GOOG**, both resolving the same way: EDGAR
simply has fewer quarters of data for the concept than expected. No code changes required
for either.

### SharesOutstanding: correctly deduplicated, remaining gap is real

The quality check flagged 13 of 26 possible quarters for `SharesOutstanding`. The 26→13
halving itself was correct (annual and quarterly facts deduplicating as designed) — the
open question was whether the *remaining* 13 were a genuine data gap or a bug.

`explore_tags.py GOOG sharesoutstanding` surfaced `CommonStockSharesOutstanding`, an
`instant` concept (actual share count at a balance-sheet date) as opposed to the two
existing tags, which are both `duration` averages:

```python
"SharesOutstanding": {
    "tags": [
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "WeightedAverageNumberOfSharesOutstandingBasic",
        "CommonStockSharesOutstanding",   # added
    ],
    "point_in_time": True,
    "mode": "fallback",
},
```

Checked the transition point for a discontinuity, since mixing an instant value into a
weighted-average series could show up as an artificial jump:

```
2015-12-31  13,746,960,000   ← CommonStockSharesOutstanding (fallback)
2016-03-31  13,735,840,000   ← WeightedAverageNumberOfDilutedSharesOutstanding
```

Difference: ~11M on a base of 13.7bn (<0.1%). No jump. `extract_merged_values` already
merges per-date across the tag list (not per-series), so this fallback only ever fires for
the individual dates that are missing — the same mechanism already in place for
Diluted → Basic.

**Result:** tag added, gap closed back to 2014. No tracking of "which tag won" was added —
considered, but the per-date merge already bounds the risk, and no discontinuity showed up
in the one case that could have produced one.

### DepreciationAndAmortization: 13 quarters is correct, not a coverage bug

`fallback_sum` (`Depreciation` + `AmortizationOfIntangibleAssets`) produced only 13 rows,
starting exactly at 2023-03-31, despite both tags being present. Looked like the
all-or-nothing check in `extract_with_mode` (`if mode == "fallback_sum" and not values`)
might be swallowing a partial main-tag result — but the three main tags
(`DepreciationDepletionAndAmortization`, `DepreciationAndAmortization`,
`DepreciationAmortizationAndAccretionNet`) are `NICHT VORHANDEN` for GOOG entirely, so that
code path was never in play.

Raw `Depreciation` facts show why the fallback still stops at 2023:

```
2021-01-01 → 2021-12-31   annual only, no matching quarter start
2022-01-01 → 2022-12-31   annual only, no matching quarter start
2023-01-01 → 2023-03-31   first quarterly entry
```

The `quarter_starts` discriminant in `decumulate_period_values` (from the 2026-07-13 Amazon
fix) requires at least one real quarter sharing a fiscal year's start date before it will
decumulate that year's annual figure. 2021 and 2022 have none — Google only began
quarterly-granular `Depreciation` disclosure in Q1 2023. The filter is doing exactly what
it was built to do.

Quarter count checks out exactly: 4 (2023) + 4 (2024) + 4 (2025) + 1 (2026 Q1) = 13.

**Considered and rejected:** adding `FinanceLeaseRightOfUseAssetAmortization` as a
`fallback_sum_tags` entry.

- Earliest entry is `2022-01-01 → 2022-12-31`, itself annual-only with no matching quarter
  start — would not close the 2021/2022 gap either.
- Magnitude is marginal: ~413M vs. 15,311M `Depreciation` for FY2024, ~2.7%.
- Open conceptual question, not just a data question: whether finance-lease amortization
  belongs in this project's EBITDA definition at all (same category of decision as the
  Meta lease-exclusion call on 2026-07-13). Not resolved here — no clear win to justify
  answering it under time pressure for a <3% effect.

**No fix applied.** GOOG simply discloses `Depreciation` annually-only before 2023, same
category as the Reddit and Meta "not a bug" entries above.

## 2026-07-14 — Apple: missing D&A tag

`DepreciationAndAmortization` coverage for AAPL was 46% (34 of 74 quarters). The existing tags (`DepreciationDepletionAndAmortization`, `DepreciationAndAmortization`) only start in 2015.

`explore_tags.py AAPL depreciation amortization` found `DepreciationAmortizationAndAccretionNet` — a tag none of the other five tickers use.

Checked the date ranges before adding it, to rule out overlap-driven double counting:

```
DepreciationAmortizationAndAccretionNet:  2007 – 2018   (old tag)
DepreciationDepletionAndAmortization:     2015 – 2026   (current tag)
```

A clean tag transition with a multi-year overlap. Added to `tags`, after the current tag, so the newer figure wins during the overlap:

```python
"tags": [
    "DepreciationDepletionAndAmortization",
    "DepreciationAndAmortization",
    "DepreciationAmortizationAndAccretionNet",
],
```

Coverage now extends back to 2007. EV/EBITDA for AAPL is available for the full history instead of only the last ~9 years.

---

## 2026-07-14 — Reddit: no debt is not a bug

Adding **RDDT** flagged `LongTermDebt` as missing (0 of 15 quarters). Unlike Meta or ServiceNow, this is not a missing tag.

`explore_tags.py RDDT debt notes borrowings` returned only `AvailableForSaleDebt...` tags — securities Reddit *holds* as part of its cash investments, not debt it *owes*. None of the usual liability tags (`LongTermDebtNoncurrent`, `NotesPayable`, `ConvertibleDebt`) exist at all.

`explore_tags.py RDDT lease` confirmed Reddit does carry `OperatingLeaseLiability` (office/datacenter leases), but no interest-bearing financial debt. Reddit went public in 2024 and appears to carry no bonds or credit facilities — plausible for a company funded by its own IPO.

**No fix applied.** This surfaces a limitation of an existing decision rather than a new bug.

The Meta entry (2026-07-13) deliberately excluded lease liabilities from `LongTermDebt`, for consistency: the concept should mean the same thing — interest-bearing financial debt — for every ticker. At Meta this was a minor simplification, because Meta also carries real bonds; leases were a small addition either way.

For Reddit the same convention has a sharper consequence: `LongTermDebt` will read as permanently zero, and `debt_to_equity` / `net_debt_to_ebitda` will imply "debt-free" even though Reddit's operating lease liabilities are non-trivial. That is a true statement about *financial* debt and a misleading one about total obligations, depending on which question is being asked.

Kept the convention as-is rather than special-casing it. Any ticker whose only liabilities are leases will show the same pattern — worth recognizing on sight rather than re-investigating each time.

## 2026-07-13 (update) — Tag discovery tooling

Not a bug. A workflow that was being done by hand, six times, made repeatable.

### The problem

Every time the data quality check flagged a missing or thin concept, the next step was identical: comment a debug block into `load_facts()`, run the whole pipeline, read the tag list, comment it out again.

```python
if ticker == "AMZN":
    for key in company_info["facts"]["us-gaap"].keys():
        if "Depreciation" in key or "Amortization" in key:
            print(key)
```

Six tickers, six variations of the same three lines. The pattern was stable enough to extract.

### `search_tags()` in `quality.py`

```python
def search_tags(company_info: dict, keywords: list[str]) -> list[str]:
    lower_cased_keywords = [word.lower() for word in keywords]
    tags = []

    for key in company_info["facts"]["us-gaap"].keys():
        key_lower = key.lower()
        if any(word in key_lower for word in lower_cased_keywords):
            tags.append(key)

    tags.sort()
    return tags
```

Case-insensitive on both sides — `"debt"` has to match `ConvertibleDebtNoncurrent`. The **original** tag name goes into the result list, not the lowercased comparison string: the point of the search is to get a name that can be pasted into `CONCEPT_CANDIDATES`.

`any(...)` rather than an inner loop with `break`, so a tag matching several keywords (`DepreciationAndAmortization` against `["depreciation", "amortization"]`) is only appended once.

### `explore_tags.py`

A standalone script, not part of the pipeline:

```bash
python explore_tags.py AMZN depreciation amortization
```

**Deliberately not interactive.** The original idea was to have the quality check prompt for keywords when it detects a problem. Rejected for two reasons:

- **It blocks.** Any unattended run (cron, CI, or just walking away from the terminal) would hang on `input()` forever.
- **It mixes modes.** `main.py` is a batch program: data in, charts out. Tag discovery is a diagnostic — done once, deliberately, *after* something has gone wrong.

Command-line arguments give the same convenience without either problem.

### `SEARCH_HINTS` in `config.py`

Closes the loop. The quality report now emits the command it wants you to run:

```
FEHLT  AMZN   DividendsPerShare                  0 von  77 (0%)
       → python explore_tags.py AMZN dividendspershare
```

The hints map each concept to the keywords that have historically found it:

```python
SEARCH_HINTS = {
    "LongTermDebt": ["debt", "notes", "borrowings"],
    "DepreciationAndAmortization": ["depreciation", "amortization"],
    "Capex": ["acquire", "propertyplant"],
    ...
}
```

`print_data_quality` takes them as a parameter rather than importing them, so `quality.py` stays independent of the project config — the same rule that applies to `expected_concepts`.

### Known limitation

The suggestion fires on every warning, including the ones that aren't problems. Amazon doesn't pay a dividend, so `DividendsPerShare` at 0% is correct — but the report still offers to go looking for a tag.

Suppressing those would mean maintaining a list of known-absent concepts per ticker. Not done, on purpose: a silenced warning is a warning that won't fire when it *is* real for the next ticker. The cost of the false positive is one glance.

## 2026-07-13 (later) — Amazon

Adding **AMZN** produced a P/E of 216 (real value ~30) and a five-year average P/E of **−41.6**. A negative average P/E is not a number that can exist.

The data quality check reported three concepts missing entirely:

```
FEHLT  AMZN   OperatingCashFlow             0 von 77 (0%)
FEHLT  AMZN   Capex                         0 von 77 (0%)
duenn  AMZN   DepreciationAndAmortization   9 von 77 (12%)
```

But the tags themselves were all present in the EDGAR data and all already configured. The extraction was silently dropping everything.

### The root cause: an end date does not identify a period

Amazon reports **three different period types in parallel** for the same concept:

```
2025-01-01 -> 2025-06-30   180 days   YTD (cumulative)
2025-04-01 -> 2025-06-30    90 days   the actual quarter
2024-07-01 -> 2025-06-30   364 days   a rolling twelve-month window
```

All three end on 30 June 2025. All three are legitimate, distinct facts.

`extract_period_values` deduplicated by `end` date alone:

```python
values[end_date] = {...}   # later filed date wins
```

So of the three, only one survived — and systematically the wrong one, because the rolling window appears in later filings and therefore wins the `filed` comparison.

The result: after extraction, **every single entry had annual length**. Not one real quarter made it through. `decumulate_period_values` then had nothing to work with and returned an empty list. Downstream, FCF, EBITDA and every dependent ratio were built on nothing.

This bug had existed since the original quarterly conversion. It never caused harm because AAPL, MSFT, NVDA, WMT, JPM and NOW happen not to report overlapping period types. Amazon does.

**Fix**

Deduplicate by `(end, days_diff)` instead of `end`:

```python
key = (end_date, days_diff) if not is_point_in_time else end_date
```

Point-in-time values keep `end` alone as the key — a balance sheet date has no duration, so there is nothing to disambiguate.

Length distribution for the same concept, before and after:

```
before:  {364: 54, 365: 19}                              ← no quarters at all
after:   {89: 14, 90: 22, 91: 18, 180: 13, 181: 5,
          272: 13, 273: 5, 364: 54, 365: 19}             ← 54 real quarters
```

### The second problem: rolling twelve-month windows

With deduplication fixed, the rolling windows now survive extraction — and immediately break `decumulate_period_values`, which groups by `start` date.

A rolling window like `2025-04-01 → 2026-03-31` shares its `start` with the real quarter `2025-04-01 → 2025-06-30`. The function sees two entries in one `start` group, assumes they are cumulative stages, and computes `148,531 − 32,515 = 116,016` as a "quarterly value". Nonsense.

They also fall inside the 350–380 day band and get treated as annual values, poisoning the Q4 derivation as well.

**Fix**

Discard them before grouping. The discriminant is generic and needs no knowledge of the fiscal calendar:

> **A real fiscal year starts where a quarter starts.** Q1 shares its `start` date with the full year. A rolling window does not.

```python
quarter_starts = set()
for v in entries:
    days = (date.fromisoformat(v["end"]) - date.fromisoformat(v["start"])).days
    if 80 <= days <= 100:
        quarter_starts.add(v["start"])

cleaned = []
for v in entries:
    days = (date.fromisoformat(v["end"]) - date.fromisoformat(v["start"])).days
    if 350 <= days <= 380 and v["start"] not in quarter_starts:
        continue
    cleaned.append(v)
```

Companies that do not report rolling windows are unaffected — their annual values always start where Q1 starts.

**Result**

| | before | after |
|---|---|---|
| P/E | 215.1 | **29.6** |
| avg P/E (5y) | −41.6 | **36.1** |
| EV/EBITDA | 20.5 | **17.2** |
| PEG | 15.1 | **2.08** |

---

## 2026-07-13 — Meta

### Missing debt tag variant

`LongTermDebt` came in at 35% coverage. Meta uses `NotesPayableCurrent` for the short-term portion of its bonds, which was not in the tag list.

**Fix:** added `NotesPayableCurrent` to the `LongTermDebt` summation list.

**Deliberately not added:** the bare `LongTermDebt` tag, which Meta also reports as a combined figure. With `mode: "sum"` it would be added to its own components and double the debt.

**Also deliberately excluded:** `FinanceLeaseLiability` and `OperatingLeaseLiability`. Meta carries substantial data-centre leases. Whether leases count as "debt" is a matter of analytical convention, not a data problem — for consistency across tickers, `LongTermDebt` here means interest-bearing financial debt only.

### Not a bug

`DividendsPerShare` at 15% coverage (9 of 62 quarters) is correct. Meta only started paying a dividend in Q1 2024.

Also verified as real: debt jumping from 28.8bn to 58.7bn in a single quarter. That is Meta's October 2025 bond issue — 30bn, the largest corporate bond in US history, to fund AI infrastructure.

---

## 2026-07-13 — ServiceNow

Four distinct bugs, all surfaced by the same ticker.

### 1. Missing concept crashes `build_valuation_history`

**Symptom**
```
KeyError: 'DividendsPerShare_TTM'
```

**Cause**
ServiceNow pays no dividend, so `DividendsPerShare` has zero rows. `pivot_table` only creates columns for concepts that have data — so the column did not exist at all, rather than existing and being full of `NaN`.

This would have happened for any missing concept.

**Fix**
Fill missing columns with `pd.NA` after the pivot:

```python
for concept in needed:
    if concept not in wide.columns:
        wide[concept] = pd.NA
```

The affected multiple becomes `NaN`, gets removed by the final `dropna`, and the chart correctly shows "keine Daten".

---

### 2. Debt understated — missing tag variants

**Symptom**
`LongTermDebt` at 17% coverage (11 of 63 rows).

**Cause**
ServiceNow names its convertible notes `ConvertibleLongTermNotesPayable` / `ConvertibleNotesPayableCurrent` — not `ConvertibleDebtNoncurrent` / `ConvertibleDebtCurrent`, the only convertible tags in the config.

**Fix**
Added both tags to the `LongTermDebt` summation list. Verified afterwards that the total lands at ~1.49bn, matching ServiceNow's actual debt — no double counting from overlapping tag families.

**Note:** `mode: "sum"` always carries double-counting risk when adding tag variants. Check the magnitude against a known figure before trusting it.

---

### 3. Share count oscillating between two bases (stock split)

**Symptom**

```
2023-09   205,194,000
2023-12 1,027,953,000   ← ×5
2024-03   207,684,000
2024-12 1,042,113,000   ← ×5
2025-03 1,046,852,000   ← ×5
2025-06   209,343,000
```

Downstream this broke market cap, and with it P/B, P/FCF, EV/Sales and EV/EBITDA. The raw `EPS` concept also went **negative while net income was positive**, which is impossible.

**Cause**

ServiceNow executed a **5:1 stock split in 2025**. The raw filings show it plainly:

```
val:   208,423,000   filed: 2025-01-30   (FY2024 10-K)
val: 1,042,113,000   filed: 2026-01-29   (FY2025 10-K, restating FY2024)
```

Same period, same form, same unit — two different values. The later one is the correct, split-adjusted restatement.

The deduplication logic was working correctly. The problem is that EDGAR only restates the periods that appear as **comparatives** in the newest filing. Everything older keeps its pre-split values from the original 10-Qs. The series ends up with two incompatible bases interleaved.

The negative EPS came from the same source: `decumulate_period_values` subtracting three pre-split quarters from a post-split annual figure.

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

**Consequence:** the raw `EPS` concept is no longer needed. `EPS_TTM_CALC = NetIncomeLoss_TTM / SharesOutstanding` uses two split-consistent absolute quantities. Removed `EPS` from `CONCEPT_CANDIDATES`.

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

**Trade-off:** young companies now get a "5-year average" based on fewer than 20 quarters. More useful than no value at all, but it should be read with that in mind.

**Result:** `avg_pe_5y` for NOW went `NaN` → `247` → **104.9**, which is a usable reference.

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

---

## Pattern

Seven tickers, seven different failure modes. Almost none of them crashed; all of them produced plausible-looking wrong numbers.

What consistently worked:

1. **Notice that a number is impossible**, not merely surprising. A negative average P/E. A negative EPS with positive net income. A share count that quintuples and then reverts.
2. **Look at the raw filings**, not the derived DataFrame. Every one of these bugs was visible in the EDGAR JSON and invisible in pandas.
3. **Find the discriminant.** Every successful fix here rests on one structural property that separates good data from bad — period length, start-date alignment, proximity to a split factor. Heuristics applied to the *output* (outlier filters, thresholds) mostly failed. Rules derived from the *structure of the input* held.