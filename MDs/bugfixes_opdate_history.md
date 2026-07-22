# Bugfix History

A running log of bugs found, what caused them, and how they were fixed. Ordered newest first.

Most entries here share a theme: **the pipeline fails silently**. A missing tag returns an empty list, an empty list produces an empty merge, an empty merge produces an empty chart. Nothing crashes. The symptom appears several layers away from the cause, and usually looks like a plotting problem. Nearly every fix below was found by noticing that a *number* looked wrong, not by reading a stack trace.

---

## 2026-07-22 — Decumulation scope-mismatch bug, third concept: OperatingCashFlow (SATS `fcf_margin` regression)

Fixing SATS's `Revenue`/`Capex` scope-mismatch bug (previous entry) had a direct side effect:
`fcf_margin` used to come out masked for SATS 2021-2022 as an *accidental* consequence of the
broken `Revenue` feeding `apply_self_relative_scale_guard`. Checking directly (not assuming)
confirmed the guard no longer fires, and `fcf_margin` was showing real-looking but wrong values
(212%, 68%, 40%, 29%) — because it also divides by `OperatingCashFlow_TTM`, which carries the
**identical, still-unfixed** bug: SATS's raw FY2021 `OperatingCashFlow` fact is $632,226,000 as
originally filed (2022-02-24/2023-02-23) and $4,655,373,000 as restated (2024-02-29) — same
common-control-combination event, same filing date, same mechanism already fixed for `Revenue`
and `Capex`. Silently-wrong data is worse than visibly-absent data, so this was worth chasing
down rather than declaring "unaffected" as the task brief initially assumed.

### Step 1/2 — full-universe scan, both directions: 37 candidates, 5 tickers confirmed

Ran the same one-sided (backward/forward, ≥10x), sign-agnostic magnitude-gap check against
`OperatingCashFlow` project-wide (appropriate since OCF, unlike `Revenue`/`Capex`, can
legitimately be very negative in real distress — a blanket non-negativity rule would wrongly
mask genuine losses like WYNN's real COVID-19 cash burn or PG&E's real $13.5B wildfire-trust
funding outflow). Found 37 hits across 30 tickers; verifying each against the actual
restatement signature (multiple, differently-valued annual-length facts for the same date, not
magnitude alone) confirmed only 5 tickers, 6 rows share this bug:

- **SATS**: FY2021 ($632M→$4.66B) and FY2022 ($530M→$3.62B), the exact same DISH-combination
  event and filing date already fixed for `Revenue`/`Capex` — recovered via `_KNOWN_BAD_FACTS`,
  reconciling cleanly to $204M and $186M respectively, in range with the ticker's other quarters.
- **ADM, FLEX, JBL** (2016/2017 dates): each swings from a normal positive figure to several
  billion dollars *negative* at a single later filing (2019) — a different, less certain root
  cause than SATS (most plausibly a cash-flow-statement reclassification, e.g.
  supply-chain/reverse-factoring arrangements moved from operating to financing activities, an
  industry-wide practice shift for exactly this kind of manufacturer around 2018-2019; FLEX and
  JBL are both electronics manufacturing services companies, reinforcing this reading).
- **TMUS** (2011-12-31): coincides with its 2013 MetroPCS reverse-merger restructuring, the same
  2011-2013 window already flagged as a merger-integration artifact for `rule_of_40` in the
  telecom scan report.

ADM/FLEX/JBL/TMUS were masked only, not recovered — unlike SATS, none has an independent,
external cross-check confirming which annual figure is "more correct" (for the three
manufacturers, the *restated* value may well be the more compliant one, the opposite direction
of confidence from SATS's case), so no value was guessed. Added a new, sign-agnostic masking
mechanism, `_KNOWN_SCOPE_MISMATCH_OUTLIERS` in `parsers/parse_edgar.py`, alongside (not
replacing) `_KNOWN_POSITIVE_OUTLIERS` — needed because OCF's mismatches can go either direction,
unlike the purely-positive ED Capex case the existing mechanism was built for.

### Step 3 — re-verified `fcf_margin`/`rule_of_40` directly, not assumed

`fcf_margin` for SATS is now plausible across its entire cached history (2021-12-31: 212%→9.8%;
2022 Q1-Q4: 68%/40%/29%/(new)→3.9%/2.0%/1.5%/1.1%), a sensible gradual-decline story consistent
with margin compression as DISH's pay-TV base shrinks. `rule_of_40` correctly comes out masked
for all of 2022 (a genuine TTM-window transition artifact spanning the scope-change boundary,
the same mechanism already documented for TMUS/CMCSA/CHTR's own merger integrations) and shows
one expected one-year-later echo (2023-03-31: 189%, decaying naturally over the next three
quarters) — not a new problem, an inherent property of TTM/YoY math around any real scope change.

### Step 4 — full non-regression

Quarterly: 4 masked (ADM/FLEX/JBL/TMUS), 2 recovered (SATS), zero elsewhere. Annual: 0 masked, 2
recovered (same SATS rows). Every previously-shipped fix (EXC/FE/PPL, SATS's own Revenue/Capex,
ED's Capex) spot-checked byte-identical. **General lesson, worth remembering going forward:**
after any scope-mismatch fix, briefly check whether any metric depending on the fixed concept
*together with* a still-unfixed one might have been "accidentally correct" before — masking that
happens to look right can be coincidental, not diagnostic, and fixing one input can silently
reveal (or hide) a problem in another. Full detail in
`operating_cash_flow_scope_mismatch_report.md`.

---

## 2026-07-22 — Decumulation scope-mismatch bug, positive direction: SATS/EchoStar and Con Edison

The telecom/cable scan (below) found the decumulation scope-mismatch bug (previous entry) has a
mirror-image manifestation the non-negativity guard can't catch: instead of
`Q4 = smaller_restated_annual − larger_original_Q1-Q3` going negative, a scope-*increase*
produces `Q4 = larger_restated_annual − smaller_original_Q1-Q3` going implausibly large but still
positive. SATS (EchoStar)'s FY2021 Revenue got retroactively restated to the combined
DISH+EchoStar scale (~$19.82B) via GAAP's common-control-combination rules once the DISH merger
closed (Dec 31, 2023), while Q1-Q3 2021 stayed on file at EchoStar's original ~$500M/quarter
scale — `decumulate_period_values` computed Q4 2021 as ~$18.33B, wrong by ~37x, but not sign-
impossible, so it sailed past the existing guard.

### Step 1 — full-universe scan, positive direction: 56 candidates, only 2 tickers confirmed

Extended the scan to flag decumulated quarterly values ≥10x above their own backward-only *or*
forward-only neighboring-quarter median (a **one-sided** window is essential — a combined
window missed SATS entirely, since 2022's quarters are also elevated by the same restatement and
drag a combined median up enough to hide the gap). Checked `Revenue`, `Capex`, `CostOfRevenue`,
`Inventory`, `AccountsReceivable`, `AccountsPayable` project-wide: 56 hits (34 Capex, 20 Revenue,
2 AccountsReceivable), across 24 tickers. Point-in-time concepts again showed zero hits from this
mechanism (structurally can't, since they're never decumulated) — the 2 AccountsReceivable hits
(Lowe's) are real, single, never-restated reported values, not this bug.

Individually checked all 56 for the actual diagnostic signature (multiple, differently-valued,
raw annual-length facts for the same end date, i.e. an actual restatement) rather than trusting
the magnitude heuristic alone — a magnitude spike is not, by itself, proof of a bug the way a
negative value was: 49 of the 56 are genuine, single, never-restated real figures (COVID-era
cruise-line revenue swings for CCL/NCLH/RCL, GE's multi-stage Capital-exit restructuring,
MetLife's Brighthouse-spinoff-era item, assorted one-time lumpy capex) or a likely unrelated raw-
data error (GLW's $100B Capex, flagged but not fixed, no restatement present). None of these were
masked — doing so on magnitude alone would repeat the exact mistake the scale-outlier-
generalization task already proved dangerous.

### Step 2/3 — two confirmed cases, two different outcomes

**SATS**: same DISH-combination event already documented for Revenue also restated Capex for
FY2021 and FY2022 (both at the same 2024-02-29 FY2023-10-K filing date). Recovered all three
(Revenue + 2× Capex) via `_KNOWN_BAD_FACTS` — the same drop-the-restated-fact,
let-the-existing-tie-break-resolve mechanism as EXC/FE/PPL — landing cleanly back in range with
the ticker's other 2021/2022 quarters.

**ED (Consolidated Edison)**: Capex for FY2016-2019 shows the same mechanical symptom (annual
restated to a different scope than never-updated quarters) but *not* SATS's clean story — no
known ConEd M&A explains it, and the *larger* post-2018 figures ($3.6-5.2B/year) look more
consistent with ConEd's real capital-spending scale than the original ($400-850M/year) ones,
the opposite direction of confidence from SATS. Added a new, narrower mechanism,
`_KNOWN_POSITIVE_OUTLIERS` in `parsers/parse_edgar.py` — masks the derived quarterly value
directly (there's no reliable original to fall back to here), restricted to the quarterly path
only (ConEd's raw annual facts are left alone; whether they're themselves right isn't
established). Masked FY2016-2019 Capex for ED only.

### Step 4 — full non-regression, and an honest (not glossed-over) side effect

Quarterly: 4 rows masked (ED), 3 recovered (SATS), zero elsewhere. Annual: 0 masked, 3 recovered
(same SATS rows). All prior `_KNOWN_BAD_FACTS` entries and the non-negativity guard verified
byte-identical. One finding reported rather than assumed away: SATS's `fcf_margin`/`rule_of_40`
were previously masked by `apply_self_relative_scale_guard` as a **side effect** of the
now-fixed Revenue bug (the artificial $18.33B peak made real quarters look implausibly small by
comparison) — fixing Revenue removes that peak, so the guard stops firing, which uncovers a
**separate, still-open** instance of the identical scope-mismatch bug in `OperatingCashFlow`
(SATS's FY2021 OCF: $632M original → $4.66B restated, same 2024-02-29 filing) that is outside
both this task's and the prior task's checked-concept list. Not fixed — `OperatingCashFlow` was
never in scope here — flagged for a dedicated follow-up instead of silently patched or silently
ignored. Full detail in `decumulation_positive_outlier_report.md`.

---

## 2026-07-22 — Decumulation scope-mismatch bug: a defensive guard plus 12 targeted recoveries

The utilities scan (two entries below) found `decumulate_period_values` can produce
mathematically impossible negative values — `Q4 = smaller_restated_annual − larger_original_Q1-Q3`
— when a divestiture or spinoff restates a fiscal year's annual total to a smaller
post-divestiture scope while the standalone quarterly facts already on file for that year still
reflect the original, larger, pre-divestiture scope. Both sides of the subtraction are
individually accurate for their own scope; the bug is purely in mixing scopes across the
subtraction. This is a third, distinct failure class from the two scale bugs above: unlike
`SharesOutstanding`, there's no single wrong raw value to rescale; unlike BAC/ROK/STX, dropping
the bad fact doesn't always leave a clean value behind.

### Step 1 — full-universe scan: 276 instances, not just the 4 known

Scanned every cached ticker for negative decumulated-quarterly values in concepts that can never
legitimately be negative: `Revenue`, `Capex`, `CostOfRevenue`, `DepreciationAndAmortization`,
`DividendsPerShare`, `ResearchAndDevelopment`, `EarnedPremiums` (point-in-time concepts like
`Inventory`/`AccountsReceivable`/`AccountsPayable` were also checked — zero hits, since they never
pass through decumulation at all). Found **276** across 106 tickers: 105 `DepreciationAndAmortization`,
83 `Capex`, 58 `DividendsPerShare`, 22 `Revenue`, 6 `ResearchAndDevelopment`, 2 `CostOfRevenue` — far
beyond the 4 originally confirmed (EXC, PPL ×2, FE), confirming the fix needed to be broad.
`OperatingIncomeLoss`/`NetIncomeLoss`/`OperatingCashFlow`/similar concepts that can legitimately be
negative (real losses, reserve releases) were counted but never flagged.

### Step 2 — defensive guard

`_NON_NEGATIVE_FLOW_CONCEPTS` + `_mask_negative_flow_values()` in `parsers/parse_edgar.py`: masks
any negative value in the 7 flagged concepts to "no data" (row dropped), but **only for the
quarterly (decumulated) path** — never for raw annual facts. That restriction turned out to matter:
AIG's raw FY2008 `Revenues` fact is genuinely −$6.84B (its aggregate revenue tag bundles net
investment gains/losses, and 2008 was AIG's near-collapse year), which would have been wrongly
suppressed by a period-unaware guard. Verified project-wide: 0 negatives remain in the 7 concepts,
0 raw annual facts touched, legitimate-negative concepts' counts identical before/after
(NetIncomeLoss 1,836, OperatingCashFlow 1,831, OperatingIncomeLoss 1,136, etc.), and CCL/RCL/NCLH's
real COVID-era losses spot-checked byte-identical before/after.

### Step 3 — targeted recovery: 12 cases, 16 rows, extending `_KNOWN_BAD_FACTS`

For each negative instance, checked whether an earlier-filed, scope-consistent raw fact exists that
reconciles cleanly with the already-used quarters — same mechanism as BAC/ROK/STX, just more
entries. Recovered 12 `(ticker, concept, end)` cases (16 rows counting DLTR's CostOfRevenue/Capex
riding the same event as its Revenue fix), each corroborated by a real, named corporate event: EXC
(Constellation spinoff), FE (FirstEnergy Solutions bankruptcy), PPL ×2 (Talen Energy spinoff; WPD UK
sale), Agilent (Keysight spinoff), HPQ ×2 and HPE (HP/HPE split, then HPE's DXC spinoff), Fortive
(Ralliant spinoff), Jacobs (Amentum divestiture), Western Digital (SanDisk spinoff), Dollar Tree
(Family Dollar sale). Declined recovery for 10 more Revenue cases and all 246 remaining
Capex/D&A/DividendsPerShare/R&D cases where no clean single candidate existed — ADM and AIG each had
multiple non-agreeing restated values (no single "correct" one to pick), GEN's cases likely share
its already-known fiscal-stub-period artifact rather than a divestiture, FIX's ~80% two-month
restatement had no known event to corroborate it, and D&A specifically showed pervasive multi-tag
disagreement (`Depreciation` vs `AmortizationOfIntangibleAssets` vs `DepreciationDepletionAndAmortization`
reconciling to different signs) even for tickers where Revenue recovered cleanly — recovering those
would be guessing, not evidence-based recovery, so they stay masked by Step 2's guard.

### Step 4 — non-regression

Quarterly: 271,080 → 270,820 rows (260 masked, 0 newly appeared, 16 recovered) — 260+16=276,
matching Step 1 exactly. Annual: 75,134 → 75,134 rows (0 masked, 16 recovered) — confirms the
period-restricted guard touches no raw annual fact. `decumulate_period_values`,
`normalize_split_adjusted`, `_normalize_scale_outliers`, and the Tier-1 ratio guards were not
touched. Full detail in `decumulation_scope_mismatch_report.md`.

---

## 2026-07-21 — Targeted fix for BAC/Assets and ROK+STX/DividendsPerShare: a third mechanism, pinned to exact facts

The generalization attempt (previous entry) proved a generic rescale mechanism can't safely cover
the confirmed scale-mismatch cases beyond `SharesOutstanding`. This entry fixes only the three
cases that actually break a currently-visible metric today — BAC's `equity_to_assets` (`inf`) and
ROK/STX's `payout_ratio` (triple-digit-plus distortions) — with a third, deliberately narrower
mechanism: a hardcoded, per-fact drop-list.

### Why not the two existing mechanisms

`TICKER_CONCEPT_OVERRIDES` replaces a ticker's tag list for a concept — the wrong shape here, since
the tag itself is correct at every date except one restated comparative; swapping tags would lose
the tag's otherwise-good data entirely. `_normalize_scale_outliers` rescales based on a chronological
anchor — already proven unsafe to extend beyond `SharesOutstanding` (previous entry). Both bugs here
are a strictly simpler shape: one specific filing, on one specific date, reported one specific fact
at the wrong scale, and the pre-existing "later filed wins" tie-break in `extract_period_values`
picks it over the correct value still sitting in an earlier filing. The fix that matches this shape
exactly: stop that one bad fact from ever reaching the tie-break, and let the correct one win
unchanged.

### The mechanism: `_KNOWN_BAD_FACTS` in `parsers/parse_edgar.py`

A dict keyed by `(ticker, tag)`, each entry a list of `{end, filed, val}` triples individually
verified against the raw cached JSON. `_drop_known_bad_facts()` runs once per ticker in
`build_dataframe()`, before any extraction, and removes only items matching **all three** fields —
not "any zero," not "any value over N," not "any fact for this ticker/tag" — so it is structurally
incapable of touching a fact that isn't individually listed. Zero heuristics, zero inference.

### Severity check on the other 14 `DividendsPerShare` tickers

Before finalizing scope, checked whether any of AVGO, CDW, EL, HBAN, HWM, KHC, LRCX, MA, MAS, NVDA,
ROST, SYK, UHS, XYL currently produce a distorted (million-scale) value the way ROK/STX do. None
do — for every one of them, a later, correctly-scaled filing already exists and already wins the
tie-break today (confirmed by calling `extract_quarterly_values` directly against each ticker's raw
JSON). A few show small negative values from an unrelated, pre-existing decumulation quirk (mixed
annual/quarterly tagging producing an odd Q4 delta) — not this bug, not touched, left as a
documented, separate, low-priority observation. None pulled into scope.

### What's actually in the drop-list

- **BAC, `Assets`**: one fact (`2008-12-31`, filed `2011-02-25`, `val=0`) — a 2011 10-K comparative
  restatement to exactly zero, when three earlier filings consistently reported $1,817,943,000,000.
- **ROK, `CommonStockDividendsPerShareDeclared`**: 10 facts across three consecutive fiscal-2019
  10-Qs (filed 2019-01-31, 2019-04-25, 2019-07-25), each of which reported *every* dividend figure
  in that filing — both the current quarter and the prior-year comparative, both the standalone
  quarterly figure and the fiscal-YTD cumulative figure — at exactly 1,000,000x scale. Only 3 of the
  10 were currently winning the tie-break (`2017-12-31`, `2018-03-31`, `2018-06-30`); the other 7
  self-corrected via a later filing already, but were dropped anyway since they're the same
  demonstrably-bad facts and leaving them in the raw data is a latent risk for no benefit.
- **STX, `CommonStockDividendsPerShareDeclared`**: 3 facts, all from the single FY2024 10-K (filed
  2024-08-02), which reported the current and two prior fiscal years' annual dividend totals all at
  1,000,000x scale. Only 1 (`2022-07-01`) was currently winning; the other 2 (`2023-06-30`,
  `2024-06-28`) had already self-corrected via a later 10-K.

### A side effect worth naming: ROK's `2018-09-30` Q4 also self-corrected

`decumulate_period_values` derives a missing Q4 as `annual − (Q1+Q2+Q3)`. With the bad Q1/Q2/Q3
values in place, ROK's FY2018 Q4 computed as `3.51 − 3,510,000 ≈ -3,509,996.49` — an impossible
negative dividend. Dropping the three bad quarters fixes this derived value too, automatically, with
no separate entry needed in the drop-list: `0.835 + 0.835 + 0.92 = 2.59`, `3.51 − 2.59 = 0.92`, a
sane result matching the surrounding quarters. Not something the task asked for explicitly, but
confirmed correct and left in place — the same "verify, don't just accept the absence of an error"
standard used for every fix in this project.

### Non-regression

Extracted every concept for every one of 323 cached tickers, before vs. after. **6 rows changed,
all explicitly in scope, everything else byte-identical:**

| Ticker | Concept | End | Before | After |
|---|---|---|---|---|
| BAC | Assets | 2008-12-31 | 0 | $1,817,943,000,000 |
| ROK | DividendsPerShare | 2017-12-31 | 835,000 | 0.835 |
| ROK | DividendsPerShare | 2018-03-31 | 835,000 | 0.835 |
| ROK | DividendsPerShare | 2018-06-30 | 1,840,000 | 0.92 |
| ROK | DividendsPerShare | 2018-09-30 | -3,509,996.49 | 0.92 (Q4-derivation side effect, see above) |
| STX | DividendsPerShare | 2022-07-01 | 2,769,997.93 | 0.70 |

Resulting metrics confirmed sane, not just non-`inf`/non-absurd: BAC's `equity_to_assets` is now
9.7%–11.4% across 2008–2009 (in line with every other quarter in its history); ROK's `payout_ratio`
runs 0.47–1.07 through the affected window (in line with its normal 0.4–1.0 range); STX's is 0.38 at
`2022-07-01` (in line with its steady ~0.33–0.51 range in adjacent quarters). KMB's single-filing
event, the other 14 `DividendsPerShare` tickers, and the scattered `BMY`/`CHD`/`COHR`/`KDP`/`MTD`/
`ZBH`/`ANET`/`TECH` cases are confirmed untouched — they don't appear anywhere in the 6-row diff,
remaining exactly as documented in the previous entry: real, confirmed, and deliberately left
unfixed.

---

## 2026-07-21 — Scale-outlier generalization attempt: scanned project-wide, shipped nothing, reverted cleanly

The `SharesOutstanding` scale-mismatch fix (`_normalize_scale_outliers` in `parsers/parse_edgar.py`)
was checked against every concept in `CONCEPT_CANDIDATES` and every profile override, not just the
two instances (`Assets`/BAC, `DividendsPerShare`/ROK+STX) found incidentally during the ratio guard
audit. The scan found the same tag-scale-mismatch signature in 11 more concepts. None of them got
the fix. Every one was tested against real data and rejected for a concrete, demonstrated reason —
this is a full changelog entry about **why nothing shipped**, not a summary of what did.

### Step 1 — full-universe scan

Replicated `extract_period_values`'s validity filter without its tie-break, keeping every raw
`(tag, end)` collision instead of silently resolving it, across all 323 cached tickers using each
ticker's own resolved `get_concept_candidates()` (so every profile's concepts were covered, not just
the base set). Flagged any collision where two on-file values differ by a near-exact power of ten
(tight log10 residual, same sign — the same signature already confirmed for `SharesOutstanding`,
`Assets`, and `DividendsPerShare`).

After filtering out coincidental ~10x differences from real restatements (a real business change
essentially never lands on a *clean*, low-residual power-of-ten ratio — confirmed by checking sign:
several `~9-11x` "matches," like CVS 2018-06-30 and MGM 2011-12-31, had a sign flip alongside the
magnitude change, which a genuine scale bug never has), confirmed genuine bugs remained in:
`DividendsPerShare` (16 tickers — AVGO, CDW, EL, HBAN, HWM, KHC, LRCX, MA, MAS, NVDA, ROK, ROST, STX,
SYK, UHS, XYL), `DepreciationAndAmortization` (BMY, CHD, COHR, KDP, KMB), `Capex` (ACGL, KMB, NCLH),
`Goodwill` (KMB, MTD), `LongTermDebt` (KMB, ZBH), `NetIncomeLoss` (ANET, KMB), `OperatingIncomeLoss`
(KMB, TECH), `CashAndEquivalents` (KMB), `OperatingCashFlow` (KMB), `Revenue` (KMB), `StockholdersEquity`
(KMB). KMB shows up in nearly every concept for the exact same two dates (2009-03-31, 2010-03-31) —
one filing (2010-05-07, later corrected 2010-05-14) that reported nearly every dollar figure in
thousands instead of dollars, not eight separate bugs. `Assets` had zero power-of-ten matches — its
one confirmed instance (BAC) is a filer error reporting an exact `0` for a real, large, historically
consistent value, a different signature entirely (see below).

### Step 2 — the assumption checks, and why they failed

Extended `_normalize_scale_outliers` with a per-concept candidate-factor override
(`_CONCEPT_SCALE_FACTORS`, since `DividendsPerShare` needed `10x` in its factor list — the default
list starts at `100x` specifically to avoid confusing a real stock split with `SharesOutstanding`,
but several genuine `DividendsPerShare` bugs, e.g. LRCX/NVDA/MA/MAS/AVGO, are exactly `10x`) and
added all 11 concepts to `_SCALE_CORRECTED_CONCEPTS`. Ran the full non-regression diff (all
concepts, all 323 tickers, before vs. after) before drawing any conclusion — and found two distinct,
serious failure modes, not the clean generalization hoped for:

**Dollar-magnitude concepts (`Goodwill`, `CashAndEquivalents`, `Capex`, `DepreciationAndAmortization`,
`LongTermDebt`, `NetIncomeLoss`, `OperatingCashFlow`, `OperatingIncomeLoss`, `Revenue`,
`StockholdersEquity`) are exactly the risk the task asked to check for — a real, legitimate large
jump (an acquisition, a restructuring) can exceed the mechanism's `32x` gate, and once it does, the
running anchor adopts the new, larger *real* scale and starts "correcting" every earlier, smaller,
equally-real value to match it.** Caught directly, not theoretically: ALGN's real 2009-2011 Goodwill
($478,000 — genuinely small, this was a small company) got inflated to $47,800,000 (100x); AMD's real
2009-2011 Goodwill ($323M) got inflated to $32.3B — a figure larger than AMD's entire market cap at
the time. Both are legitimate historical values, both got wrongly "fixed" once a later, real, much
larger Goodwill figure (from actual subsequent acquisitions) became the anchor. 1,397 rows changed
across 11 concepts and ~40 tickers in this first pass; a meaningful fraction were confirmed wrong the
same way as ALGN/AMD.

**`DividendsPerShare`, despite passing the raw-scan signature check cleanly, fails for a completely
different reason: `decumulate_period_values`.** This concept is not point-in-time, so it's run
through the same YTD-cumulative-to-quarterly-delta decumulation as flow concepts like Revenue.
Confirmed directly for GEN (Gen Digital, formerly NortonLifeLock): its 2016 fiscal-year-end change
produced a genuine "stub period" quarterly delta of **$4.15** at `2016-04-01` — not a real dividend,
a decumulation artifact, but only about 27x away from the surrounding ~$0.15 quarters, just inside
the `32x` gate. The sweep adopted it as the new anchor, and every subsequent real, correct
$0.075–$0.125/quarter value (36 quarters running, essentially GEN's entire post-2016 history) got
"corrected" upward by 100x to $7.50–$12.50 — a dividend GEN never paid. Confirmed the same pattern
for MGM (real $0.0025/quarter inflated to $0.25) and TPR (real value inflated 1,000x). This is a
**different** anchor-poisoning failure mode than the ones already hardened against for
`SharesOutstanding` (AIG's single garbage fact, WAT's poisoned seed) — here the poisoning value isn't
an obviously-wrong outlier or a boundary seed, it's a genuine but non-representative artifact that
sits just inside the existing gate. Even narrowing the fix to *only* `DividendsPerShare` (dropping
all 10 dollar-magnitude concepts) still produced this false correction for 4 tickers.

**`Assets` was never actually correctable by this mechanism at all.** BAC's confirmed instance is a
filer reporting an exact `0` for a period that three earlier, consistent filings reported at
$1,817,943,000,000. `_normalize_scale_outliers` works by finding a multiplicative rescale factor —
there is no factor that turns `0` into `$1.8T`; the sweep's own `if not val: continue` guard treats
zero as "no data" and passes over it untouched. This needs a structurally different mechanism (reject
an implausible zero surrounded by consistent large values), not a variant of this one.

### Step 3 — nothing shipped

Given both attempts (11 concepts, then narrowed to the 2 most textbook-looking ones) produced
confirmed false corrections on real data, and per this project's standing rule (`roe`/`payout_ratio`
in the immediately preceding task, `normalize_split_adjusted`'s WAT gap before that) to log an honest
negative result rather than ship a fix that trades confirmed real bugs for newly-broken real values —
**`_SCALE_CORRECTED_CONCEPTS` was reverted to `{"SharesOutstanding"}` and the per-concept factor
addition was removed.** `parsers/parse_edgar.py` is confirmed byte-for-byte reverted to its state
before this task (`_normalize_scale_outliers`, `_sweep_scale_outliers`, `_closest_scale_factor` all
back to their original signatures, `_CONCEPT_SCALE_FACTORS` no longer exists).

### Step 4 — non-regression

Full facts extraction (every concept, every one of 323 cached tickers) before vs. after: **0 rows
changed, 0 rows added, 0 rows removed** — confirming the revert is complete and this task shipped no
behavior change of any kind. BAC's `Assets` at `2008-12-31` is still `0` (its `equity_to_assets`
still `inf`); ROK's `DividendsPerShare` at `2017-12-31`/`2018-03-31`/`2018-06-30` is still
`835,000`/`835,000`/`1,840,000` (its `payout_ratio` distortion is unchanged). Both remain confirmed,
open, unfixed — reported here rather than papered over.

### What this leaves open

`DividendsPerShare` (16 tickers, ROK/STX among them), `Assets` (1 ticker, BAC), and the 9 other
dollar-magnitude concepts (mostly the single KMB filing event plus BMY/CHD/COHR/KDP/MTD/ZBH/ANET/TECH)
all have real, confirmed instances of a tag-scale or filer-error bug. None is safe to fix with
`_normalize_scale_outliers` as it exists today. A future fix would need either a decumulation-aware
guard (skip or flag stub-period deltas before they can poison an anchor) for `DividendsPerShare`, a
real-event-aware gate (e.g. cross-checking a large jump against a real M&A/restructuring signal, or
requiring corroboration from more than one subsequent period before trusting a new anchor) for the
dollar-magnitude concepts, or a dedicated "reject an implausible instant zero" rule for `Assets` — none
of which existed going into this task and none of which this task built, consistent with its own
explicit instruction not to force a fix that can't be validated.

---

## 2026-07-21 — Tier-1 ratio guard fixes: five metrics, three mechanisms, and two deliberately-not-fixed cases

The ratio guard audit (`ratio_guard_audit_report.md`) confirmed real, current explosions in seven
metrics. This entry covers the five that got a working fix; the other two (`roe`, `payout_ratio`)
were investigated just as thoroughly and are documented below as **not fixed** — the obvious
mechanism was tested against real data and demonstrably doesn't generalize, and shipping it anyway
would have traded a small number of real explosions for a much larger number of newly-suppressed
legitimate values. Every threshold below was calibrated from where explosions actually cluster in
the full 323-ticker cache, the same discipline as every guard in this project.

### Fix 1 — `net_debt_to_ebitda`: absolute EBITDA floor (new, `min_denominator_abs=$10M`)

Unguarded; 53 confirmed explosions up to ±3,446x. Plotting caught-vs-collateral across a dollar
floor sweep showed no clean separation — a company's absolute EBITDA size just doesn't predict
whether its `net_debt_to_ebitda` reading is explosive (a mega-cap in earnings distress and a
small-cap mid-scaling both post tiny-dollar EBITDA). The curve does have a genuine elbow at $10M:
20 of 53 explosions caught (CRWD, DDOG, EFX, LYV, PANW, PODD, TTWO, EA, CIEN — all genuinely
tiny-dollar EBITDA, the classic near-zero-denominator case) for only 12 collateral rows; the next
$5M of floor buys just 2 more catches for 10 more collateral. The remaining 33 explosions (BA, WBD,
INTC, RCL, NCLH, LVS, WYNN, HLT, MAR, MAS, CAG, VTRS, STX, EL — all with EBITDA in the tens-to-
hundreds-of-millions) are a **different failure mode** — genuinely large debt against genuinely
compressed (but not tiny) earnings — that an absolute floor can't reach without masking thousands
of legitimate mid-cap ratios elsewhere. Left unaddressed, flagged for a scale-relative mechanism as
a follow-up, not force-fit into this one.

### Fix 2 — `debt_to_equity`: scale reference changed from `Revenue_TTM` to `LongTermDebt` (`roe` left unchanged)

The existing guard compared equity to Revenue — the wrong yardstick, since a company's equity can
be comfortably above 1% of revenue while still being tiny relative to its *own debt* (NCLH: equity
1.4% of revenue, 0.5% of debt). Changed `min_denominator_scale_ref` to `LongTermDebt` (the ratio's
own numerator) and recalibrated `min_denominator_scale_ratio` to **0.05** — chosen because it
reproduces the audit's own `>20x` explosion boundary exactly (`equity < 5% of debt ⟺ debt/equity >
20`), so it catches all 68 confirmed explosions with **zero collateral by construction**. As a
bonus, it also *unmasked* 5 values the old Revenue-based guard was incorrectly suppressing (e.g.
MAR 2023-03-31: debt_to_equity 0.40, an entirely normal reading, previously hidden only because
equity was small relative to Marriott's asset-light revenue, not because the ratio itself was bad).

**`roe` was left unchanged.** The obvious parallel move — reference `NetIncomeLoss_TTM` — was
tested and rejected: of the 129 remaining `roe` "explosions," 118 are positive and belong to
famous, real high-ROE buyback names (HD, MCD, ORLY, LMT, LLY, PM, LOW, CLX, KMB, GDDY, FTNT, MSI,
VRSK, MTD — a company generating strong profit against equity kept thin by decades of buybacks is
exactly what "high ROE" means, not a broken ratio). A NetIncomeLoss-based guard would suppress
nearly all of them. The 11 negative cases (NCLH, WYNN, CIEN, ADSK, QCOM, PANW) trace to real,
documented one-time events (COVID losses, ADSK's subscription-transition writedown, QCOM's 2018
Apple-dispute charge) at similarly-thin-but-real equity — mathematically symmetric with the
positive cases, so there's no principled sign-based cut either. `Assets` was checked as an
alternative reference and isn't populated outside the banking profile, so it isn't universally
usable. Conclusion: `roe`'s remaining explosions are the same "real but extreme" class as URI's
`capex_intensity` and VRTX's `rd_intensity` — confirmed real, not a guard gap, left alone.

### Fix 3 — `operating_margin` / `fcf_margin`: self-referential revenue-scale guard (new function, `apply_self_relative_scale_guard`)

New mechanism in `metrics.py`: for each `(ticker, end)`, compare `Revenue_TTM` against the max of
its own **±8-quarter centered rolling window** (not a fixed dollar floor — company sizes vary too
much — and not a whole-history max, which broke on the first real test below); mask when current
revenue is under **10%** of that window's peak. A window, not a whole-history reference, was
required specifically because of a real counter-example found during calibration: HIG's `Revenue`
tag genuinely steps down ~13x in 2018 (Talcott Resolution divestiture, a real corporate event, not
a data bug) and never recovers — a whole-history-max reference would have permanently flagged every
quarter since 2019 as "collapsed," when the post-divestiture business is simply operating at a
smaller, stable, entirely legitimate scale. A bounded window naturally stops reaching back into the
stale pre-divestiture regime once enough time has passed, catches the divestiture's own transition
quarters (2018Q4–2019, correctly ambiguous), and leaves 2021 onward alone.

Verified against every named case: CCL/NCLH/RCL's COVID quarters and VRTX's 2009–2011
pre-commercial era all land at 0.3%–9.4% of their own window peak (cleanly caught). SOFI's
fcf_margin explosion does **not** get masked, and correctly so — its ratio-to-window-max is 58%–100%
throughout; the explosion is driven by genuinely heavy cash burn against a normal, non-collapsed,
steadily-growing revenue base (real early-fintech economics, the same category as URI/VRTX, not a
denominator artifact). One incidental catch worth naming: LYV (Live Nation) 2021-03/06, a COVID
collapse that happened to fall just under the audit's original ±300% detection bar (margins of
-227%/-103%) but is the identical failure mode as the cruise lines — correctly caught by the new
guard even though it wasn't in the original flagged list.

### Fix 4 — `payout_ratio`: tested, does not generalize, **not fixed**

The same self-referential approach (compare `EPS_TTM_CALC` to its own scale) was tried across four
window sizes (±1 to ±8 quarters) and two statistics (max, median), plus a whole-history-max variant
— 12 configurations total. None separates the 42 genuine near-zero-EPS explosions (ROK's and STX's
9 rows are a `DividendsPerShare` scale bug, a different root cause, excluded from this count) from
ordinary EPS volatility: even the tightest possible threshold (0.1%) already produces more
collateral (16 rows) than catches (1), and every looser setting gets worse faster. Root cause: EPS
swings far more, and across a far wider dynamic range over a company's life, than Revenue does —
normal, healthy earnings growth alone can span 100x+ (a $0.02-EPS young company vs. its own
$2-EPS mature self), which any self-referential magnitude check mistakes for an explosion. Revenue
doesn't have this property, which is exactly why Fix 3 worked and this doesn't. `payout_ratio` keeps
its existing `require_positive_denominator`-only guard; the 42 genuine cases are reported as a
confirmed, unresolved gap for a future task with a different mechanism in mind.

### Fix 5 — `operating_leverage`: absolute output cap added (`max_abs_result=15`, new parameter on `calculate_ratio_from_dfs`), floor left at 0.02

Retightening the existing `min_denominator_abs` (revenue-growth) floor alone cannot work: eliminating
the last 21 of 125 confirmed explosions (`>20x`) this way requires raising the floor to 10%,
which masks 5,740 of 10,740 rows total — over half the universe — because 2–10% revenue growth is
completely ordinary. The real pattern (FDX, HPE, TSN: modest single-digit revenue growth divided
into operating-income growth sitting right at `calculate_growth`'s own ~200% ceiling) is a property
of the *ratio's own magnitude*, not cleanly attributable to either side alone — a 2D sweep over
both a revenue-growth floor and an operating-income-growth ceiling confirmed no combination cleanly
separates the tail either. Added `max_abs_result` to `calculate_ratio_from_dfs` and capped
`operating_leverage` at **±15** — chosen at the natural 97th–98th-percentile elbow of the real
distribution (90% of all values sit under 5.8x, 99% under 21.4x). An output cap is collateral-free
by construction: it only touches values already beyond the cap, unlike floor-tightening, which
would have masked plenty of ordinary low-growth quarters along the way.

### Non-regression (all 7 metrics, full 323-ticker cache)

Extracted all 7 metrics before/after: **0 changed values** among rows present in both (confirmed to
float precision), for every metric. Newly masked: `net_debt_to_ebitda` 32, `debt_to_equity` 68,
`operating_margin` 20, `fcf_margin` 27, `operating_leverage` 232, `roe` 0, `payout_ratio` 0 (as
expected — both left unchanged). `debt_to_equity` also newly *unmasked* 5 previously-wrongly-hidden
legitimate values (BA, LII, MAR, STX — see Fix 2). Every newly-masked row cross-checked against its
underlying facts; `capex_intensity` and `rd_intensity` (explicitly out of scope) confirmed
byte-for-byte unchanged; URI's real >100% `capex_intensity` and VRTX/REGN's `rd_intensity`
untouched. Full breakdown in `tier1_ratio_guard_fixes_report.md`.

---

## 2026-07-21 — Negative-equity-sign guard for `roe` / `debt_to_equity`: a different failure mode from near-zero

MCD's `StockholdersEquity` has been persistently, substantially negative since 2016-09-30 (as deep
as -$9.5B in mid-2020) — a large-magnitude, sustained condition, not a brief near-zero crossing
like ORLY's. The existing guard on `roe`/`debt_to_equity`
(`min_denominator_scale_ref="Revenue_TTM"`, `min_denominator_scale_ratio`) only masks when
`abs(denominator)` is *small* relative to revenue. It does nothing here, because MCD's negative
equity is large, not small. `roe` reached -675%, `debt_to_equity` around -30 — mathematically
well-defined, economically meaningless: both ratios are conventionally undefined when equity
itself is negative, independent of magnitude. Near-zero and large-negative are different failure
modes needing different conditions, and this project didn't have a guard for the second one yet.

### Scope check first: this is project-wide, not MCD-specific

Scanned every cached ticker across every profile for any period with negative `StockholdersEquity`.
**71 tickers across 11 profiles** have at least one such quarter — AZO's entire recent history
(68 quarters, -$5.2B min), BA (-$23.6B min, 34 quarters), PM (-$13.6B min, 56 quarters), HCA
(-$10.2B min, 61 quarters), DPZ (-$4.3B min, 63 quarters) among the largest. Given the scope, the
fix belongs in `main.py`'s base `roe`/`debt_to_equity` calculations, not a profile-scoped config
change — these aren't concepts a single profile owns.

### No new guard needed — an existing parameter already did this

`metrics.calculate_ratio()` already has `require_positive_denominator`, already used for
`payout_ratio`: it masks the denominator to `NaN` wherever it isn't strictly positive, before the
ratio is computed. Verified directly that this composes cleanly with the existing near-zero scale
guard (which runs afterward on the ratio Series) rather than assumed: where
`require_positive_denominator` already masked a value, the scale guard's own comparison
(`NaN < threshold`) evaluates to `False` and leaves the existing mask alone — the two guards don't
interfere, satisfying the "either condition masking is sufficient, neither replaces the other"
requirement without any new code. Added `require_positive_denominator=True` to both calls.

As a side effect this also masks exactly-zero equity (a division-by-zero, equally undefined) —
not something the task described, but clearly correct, and confirmed in the non-regression check
below as the one genuine edge case among the newly-masked values.

### Non-regression

Extracted `roe` and `debt_to_equity` for every cached ticker before and after: 0 new keys, 0
removed, **2,040 newly masked** (real value → `NaN`), 0 unexpected changes of any other kind.
Cross-checked every one of the 2,040 directly against the ticker's own raw `StockholdersEquity` at
that date: 2,039 are genuinely negative; 1 (VTRS, `debt_to_equity`, 2019-12-31) is exactly zero —
the division-by-zero case noted above, correctly masked by the same condition. No positive-equity
period changed anywhere. Full affected-ticker list in `negative_equity_guard_report.md`.

---

## 2026-07-21 — Twelfth stock-type profile: leisure batch (restaurants/hotels/cruises/casinos), and the first real use of the ticker-level override mechanism

Extended `leisure` from MCD alone to 12 tickers: SBUX, DPZ, CMG (restaurants), MAR, HLT (hotels),
CCL, RCL, NCLH (cruises), LVS, MGM, WYNN (casinos). `OperatingIncomeLoss` came back clean for all
12 (93-99%), same as MCD — checked per ticker rather than assumed, and this time the whole batch
genuinely does share the clean outcome.

### `FoodAndBeverageRevenue`: the ticker-level override mechanism's first real application

CMG's `Revenue` coverage was 53% — the base candidate tags only go back to 2016-12-31 for this
filer. The real pre-2017 tag is `FoodAndBeverageRevenue`, verified as CMG's full consolidated total
(exact match against `Revenues` at every shared date, e.g. 2016-12-31: both $3,904,384,000) — CMG
has only one revenue stream, so the tag captures all of it.

**Not safe to add profile-wide.** LVS, MGM, WYNN, and SBUX all carry this exact tag name too — and
for the casinos it's only the food & beverage *segment*, ~7-9% of total revenue (verified directly:
LVS 2009-06-30, `FoodAndBeverageRevenue` = $87M vs. consolidated Revenue = $1,059M). Same trap as
DHI/NVR's `InventoryRealEstateLandAndLandDevelopmentCosts` from the homebuilder profile — a tag
name that means the whole thing for one filer and a small component for another sharing the same
profile. This is the first case since `TICKER_CONCEPT_OVERRIDES` was built (see the entry below)
where that mechanism was actually needed for a new problem, not just applied to the case that
motivated it. Added `TICKER_CONCEPT_OVERRIDES["CMG"]["Revenue"]` with the full base tag list plus
`FoodAndBeverageRevenue`. CMG: 53% → 96%.

CCL's `Revenue` had a similar-shaped gap (68%, missing 2010-2015 entirely). Real tag:
`SalesRevenueServicesGross`, verified as CCL's full total (exact match at 2015-08-31: both
$4,883,000,000) — cruise lines have no other revenue category, so a "services" tag is their whole
business. Added as `TICKER_CONCEPT_OVERRIDES["CCL"]["Revenue"]` for consistency with the CMG case,
even though no other leisure ticker currently carries this tag. CCL: 68% → 96%.

### A guard that works, and one that's confirmed missing

Checked directly (not assumed) whether `revenue_growth`'s `min_base_ratio` guard suppresses the
nonsensical readings CCL/RCL/NCLH's COVID-era near-zero revenue would otherwise produce. It does:
`yoy_growth` correctly comes back `NaN` for all three exactly where 2022 recovery would divide
against a near-zero 2021 TTM base (e.g. RCL: $218M → $2,549M), and correctly stays visible for the
2020-2021 decline readings themselves, since those are real and meaningful, not artifacts.

`operating_margin` has no equivalent guard at all. Confirmed with real values: RCL -4,118%,
NCLH -9,510%, CCL -5,046%, all during the same COVID trough — mathematically correct, economically
meaningless. **Not fixed here** — the task asked to verify the existing guard, not build a new one
for a base metric used by every profile — but logged as a confirmed, open gap for future work.

### Scope breaks: one textbook, one different-shaped, one non-finding

- **HLT**: textbook signature — every 2015-2016 `Revenue` quarter restated on the *same* filing
  date (2017-05-24), consistent -36% to -37%. Matches Hilton's January 2017 spinoff of Park Hotels
  & Resorts (REIT) and Hilton Grand Vacations exactly.
- **LVS**: real, but a *progressive* restatement across four different filing dates
  (2021-04-23 through 2022-02-04) rather than one — each 2020 quarter's `Revenue` and
  `OperatingIncomeLoss` shrinks a bit further with each new comparative filing. Consistent with
  reclassifying the Las Vegas segment as held-for-sale ahead of the 2022 Apollo/VICI divestiture,
  not a single clean cutover.
- **MAR**: a real restatement (2017 quarters, -10% to -12%, filed in 2018) that isn't a spinoff at
  all — timing matches the 2018 ASC 606 adoption instead.
- **MGM, WYNN**: checked, no scope-break signature found in either `Revenue` or
  `OperatingIncomeLoss`, despite MGM's 2016 MGM Growth Properties REIT spinoff. A real non-finding.

### `rule_of_40`: hidden, same call as every profile but one

Computed across all 12 tickers' full history. Every median sits well under 40%; even LVS (best
case, boosted by post-COVID Macau/Singapore recovery) only clears 40% in 32% of quarters — nowhere
near the ~93%-of-quarters bar that kept TTD under consideration in the media scan. Hidden
profile-wide. CMG's real, well-known growth story doesn't change the call: median 24.8%, never
crosses 40% at all in the cached history.

### Non-regression

Confirmed by direct construction that `get_concept_candidates()` is byte-identical for all 312
previously-cached tickers (none of this task's three config changes touch any pre-existing
ticker's profile or any shared config), then verified empirically across the full universe: 0
changed, 0 removed, 51 new fills, all on `CMG|Revenue`/`CCL|Revenue`. LVS/MGM/WYNN/SBUX's own
`Revenue` — the tickers that also carry `FoodAndBeverageRevenue` but where it means something
narrower — checked explicitly and confirmed untouched.

---

## 2026-07-21 — SharesOutstanding: a new pattern class, a single filer reporting the same fact at two scales

MCD's `SharesOutstanding` alternated between ~751,900,000 and ~751.8 for the same real
figure, at different filed dates for the same reporting period — not a clean unit-conversion
factor, and not the same-name-different-scope trap (CAT/PCAR/TXT, DHI/NVR) either. Investigated
down to the mechanism rather than assumed: this is neither of the two hypotheses the task
itself raised.

### Not two tags — one tag, two scales

Checked every raw fact for `WeightedAverageNumberOfDilutedSharesOutstanding` directly. The unit
is `shares` in every single fact, before and after. The `val` field itself just changes scale:

```
end: 2021-12-31  val: 751800000   filed: 2022-02-24  (FY2021 10-K)
end: 2021-12-31  val: 751800000   filed: 2023-02-24  (FY2022 10-K, comparative)
end: 2021-12-31  val: 751.8       filed: 2024-02-22  (FY2023 10-K, comparative)
```

MCD switched, starting with filings filed in 2024, to expressing this fact in millions while
leaving the `shares` unit tag unchanged. `extract_period_values`'s existing tie-break for a
`(tag, end)` collision (`is_point_in_time` branch, same `days`: later `filed` wins) was built for
genuine restatements, where the later filing is definitionally the more accurate one. Here it
just means the *smaller, wrong-scale* number always wins once one exists, since it's always the
one most recently filed. Confirmed genuinely different in shape from every restatement pattern
logged so far: a real restatement changes a value by a modest percentage or a small integer split
ratio; this changes it by a clean power of ten, for the exact same fact.

### Systemic, not MCD-specific

Scanned every cached ticker (311, not just the 4 profiles the task asked for a sample of) for the
same signature. **41 tickers across 11 profiles** — including all four the task named (`standard`,
`financial`, `retail`, `pharma_medtech`) plus `consumer_staples`, `health_services`, `homebuilder`,
`industrials`, `insurance_pc`, `leisure`, `media` — carry at least one instance. Scale factors seen:
100x, 1,000x, 10,000x, 1,000,000x, 10,000,000x (KO, MRK, MO, TXN, GLW, L, HIG all show a clean
1,000,000x; CLX, HSY, NVDA, GRMN, TSCO, WRB and others show 1,000x; VTRS shows 10,000,000x). This
is a fallback-list problem nowhere near unique to `SharesOutstanding` in principle — it can happen
to any concept whose `val` a filer re-expresses at a different decimal scale — but `SharesOutstanding`
is the only concept where it was actually observed in this project's data.

### Fix: a general-purpose scale-outlier corrector, added once, applied narrowly

Added `_normalize_scale_outliers()` in `parsers/parse_edgar.py`, wired into `build_dataframe()` for
concepts in `_SCALE_CORRECTED_CONCEPTS` (currently just `SharesOutstanding`). Runs two chronological
sweeps (forward and backward), each keeping a running "anchor" log10 that updates to whatever value
was just accepted — a correction one step propagates as the reference for the very next step, so an
arbitrarily long run of consecutive bad-scale quarters (MCD's later history is uncorrected in *every*
filing from 2023-12-31 on — there's no competing good value left to fall back on) resolves in one
linear pass, not one pass per quarter in the run. A value is only ever scaled *up*, and only when it
sits far below (at least ~32x) its neighbors' scale; a value far *above* is left untouched and never
adopted as the anchor.

Three real failure modes surfaced and were fixed before this design was trusted, each caught by
testing against real tickers rather than assuming the design was safe:

1. **Bucket rounding picks the wrong factor at a boundary.** HIG's 2009 values (321, 325, 356 —
   meant to be ~320.8M, ~325.4M, ~356.1M) sit close enough to a rounding boundary that an earlier,
   cruder version (matching on rounded `log10` magnitude buckets) settled for a 100,000x fix instead
   of the correct 1,000,000x. Fixed by matching on continuous `log10`, picking whichever factor is
   numerically *closest*, not the first one that lands in the same bucket.
2. **A real split must never be mistaken for this bug.** TTD's 2014-2016 pre-IPO share count
   (tens of millions) is real, correct, and simply smaller than its post-2021-10-for-1-split era —
   not a scale artifact. `_SCALE_UP_FACTORS` deliberately starts at 100x, not 10x, specifically so a
   real 10-for-1 split (numerically indistinguishable from a "reported in tens" artifact by ratio
   alone) is never misfixed; no genuine artifact anywhere in this project's data needed a factor
   under 100x.
3. **A lone garbage fact must never poison the anchor.** AIG has one real XBRL fact reported at
   ~1,000,000x its true value for exactly one quarter — an unrelated, pre-existing SEC data error,
   not this project's scale-mismatch pattern. An early version let any accepted value become the new
   anchor unconditionally; that one fact turned every genuinely correct quarter afterward into an
   apparent "artifact" relative to itself, cascading the corruption through AIG's entire history.
   Fixed by only ever adopting a value as the anchor if it's within the same ~32x band as the
   current anchor — a value far outside that band is left alone and never trusted as a reference.
   WAT has the same kind of lone garbage fact at its single most recent quarter, which is the very
   first thing a backward sweep would otherwise see and seed the anchor from; the seed itself is now
   the median of the first several values in each direction, not just the first one, so a single
   boundary-adjacent garbage point can't set the anchor either.

**Verified via the elevated non-regression check the task required**: extracted every concept for
every cached ticker (311, all profiles) before and after. **0 changed, 0 removed, 162 new/corrected
values across the 41 affected tickers, 0 changes to any other ticker or concept** — the change is
purely additive (`build_dataframe`'s loop is identical for every concept except `SharesOutstanding`,
where one conditional post-processing call was added), so nothing outside `SharesOutstanding` could
regress by construction, confirmed empirically anyway.

### A related, confirmed-but-unfixed bug found along the way: `normalize_split_adjusted`

WAT's lone garbage quarter (above) isn't just an extraction-layer risk — the same failure mode
already exists, unfixed, in `metrics.py`'s `normalize_split_adjusted()`. That function anchors
each series on its single most recent value (`values.iloc[-1]`) with no plausibility check at all,
by design (see the ServiceNow entry below: a median or windowed anchor was tried once already and
rejected, because a real split's recent tail can have the *stale* pre-split value in the majority —
using anything but the literal last value broke that case). WAT's garbage last-quarter fact
(~1,000x its true value) currently gets adopted as this anchor unconditionally, then
`COMMON_SPLIT_FACTORS`' best-effort matching (no tolerance gate) rescales WAT's entire real,
multi-year share-count history to the closest available multiple of that one bad number —
confirmed directly: running the current, unmodified function against WAT's real cached data
turns its genuine ~60-100M share count into ~3-5 billion across nearly the whole series.

**Not fixed in this task.** Three different repair attempts were tried and each introduced its own
regression before being caught: a trailing-median anchor defeats the ServiceNow precedent outright
(confirmed directly against NOW's own cached data: its real recent tail has the stale, pre-split
value in the majority within a 5-quarter window, so a median anchor picks the wrong side — the
existing single-last-value design is deliberate and correct for that case, not an oversight); adding
a match-confidence tolerance to the existing single-last-value anchor is directionally correct and
does protect WAT, but the tolerance also rejects real, correct split-adjustments for tickers with
long histories and heavy accumulated buybacks (confirmed against AAPL: a genuine ×2 match against
its real anchor has ~15.4% error, only barely outside a 15% tolerance, and 154 other real tickers
shifted too) — no tolerance value tried was loose enough to keep AAPL correct and tight enough to
keep WAT protected. This needs a fix that can tell "no clean match exists because the anchor is
garbage" apart from "no clean match exists because of a decade-plus of real buybacks" — genuinely
harder than it looks, and not something to ship half-verified. Logged here as a confirmed, open,
separate bug for dedicated follow-up, per this log's own rule: an ambiguous fix that can't be
cleanly validated doesn't get shipped on a guess.

### Pattern-class note for future work

This is the first instance in this log of a fallback list correctly resolving to *one* tag whose own
reported value silently changes scale across filings — distinct from a missing tag, a same-tag-
different-scope mismatch, and a real corporate action. Worth checking proactively on other
pipeline-wide base concepts (`Revenue`, `NetIncomeLoss`) even without a visible symptom yet, since
the failure is invisible until a chart happens to make the resulting near-zero or absurdly large
value obvious — exactly how MCD's case was first noticed and none of the other 40 were, until this
task's full-universe scan.

---

## 2026-07-21 — Ticker-level concept overrides: a resolution layer below the profile

Every prior tag fix in this project lived at one of two levels: `CONCEPT_CANDIDATES` (base,
every ticker) or `PROFILE_CONCEPT_OVERRIDES` (one profile, every ticker sharing it). The
homebuilder scan surfaced a case neither level could handle: NVR's `Inventory` genuinely exists
under `InventoryRealEstateLandAndLandDevelopmentCosts`, but that exact tag name is a
**land-only component**, not the consolidated total, for DHI — which shares NVR's
`homebuilder` profile. Adding it profile-wide would have silently understated DHI's inventory
by ~50% in every gap quarter it filled (confirmed at FY2017-Q3: $4.5B vs. DHI's real $9.2B).
There was no way to give NVR this tag without exposing DHI to that risk, because the codebase
had no concept of an override that sits *below* the profile level and is invisible to every
other ticker. This is the third confirmed instance of the same pattern class — a tag name that
means one thing for one filer and a narrower thing for another — after the Kroger FIFO/LIFO
substitution (rejected outright, no fix existed) and the CAT/PCAR/TXT captive-finance overlap
check. The first two were caught-and-rejected; this one motivated building a mechanism instead,
because the safe tag genuinely exists — it just needed a narrower place to live.

### The mechanism

Added `TICKER_CONCEPT_OVERRIDES` to `config.py`, resolved in `get_concept_candidates()` after
`PROFILE_CONCEPT_OVERRIDES`:

```python
def get_concept_candidates(ticker: str) -> dict:
    profile = TICKER_PROFILES.get(ticker, DEFAULT_PROFILE)
    overrides = PROFILE_CONCEPT_OVERRIDES.get(profile, {})
    resolved = dict(CONCEPT_CANDIDATES)
    resolved.update(overrides)
    resolved.update(TICKER_CONCEPT_OVERRIDES.get(ticker, {}))
    return resolved
```

A ticker-level entry is a **complete replacement** for that ticker/concept, not merged with the
profile-level entry — same full-replacement semantics `PROFILE_CONCEPT_OVERRIDES` already has
over `CONCEPT_CANDIDATES` (the `.update()` gotcha documented in the homebuilder `LongTermDebt`
near-miss applies identically here: a ticker override must list every tag it wants, since
nothing from the profile level carries over underneath it). This is deliberate — the entire
point is isolating NVR's tag from DHI's shared profile list, so a ticker-level override must
never leak into or combine with the profile-level fallback chain for the same concept.

`get_expected_concepts()` needed **no separate change**. It already derives its concept set from
`get_concept_candidates(ticker).keys()`, and since `get_concept_candidates()` now folds in
`TICKER_CONCEPT_OVERRIDES` before returning, any ticker-level override — whether it replaces an
existing concept's tags (NVR's case) or, hypothetically, introduces a wholly new one — is
automatically visible to coverage scans with no second place to keep in sync. Two update sites
for one resolution chain is exactly the kind of drift this project avoids everywhere else; a
single merge point was preferable to threading the same lookup through both functions.

`PROFILE_EXCLUDED_CONCEPTS` was left without a ticker-level equivalent, per the task's own
default assumption — no concrete need surfaced while implementing this one case.

### Applied to NVR, and only NVR

```python
TICKER_CONCEPT_OVERRIDES = {
    "NVR": {
        "Inventory": {
            "tags": ["InventoryRealEstateLandAndLandDevelopmentCosts"],
            "point_in_time": True,
            "mode": "fallback",
        },
    },
}
```

NVR's `Inventory`: 0/69 → 57/69 quarters, 2011–2025, values $70M–$91M — matching the diagnosis
already logged in `homebuilder_scan_report.md`.

### Non-regression (elevated scope: full cached universe, every concept, every profile)

Because this changes a function every ticker's tag lookup runs through, the check covered all
311 cached tickers' full concept sets under quarterly extraction, not just `homebuilder`'s four:

- **Mechanism-only change** (empty `TICKER_CONCEPT_OVERRIDES`, resolution logic added):
  confirmed a byte-identical no-op before NVR's entry was added — `dict.update({})` is a no-op
  by construction, verified directly rather than assumed.
- **NVR's entry added**: 239,421 → 239,478 values. **0 changed, 0 removed, 57 new** — every one
  of the 57 on `NVR|Inventory`, nothing else anywhere in the universe. DHI's own 42
  `Inventory` values (and PHM's 65, LEN's 10) checked explicitly and confirmed byte-identical
  before/after, not just inferred from the aggregate diff — this was the specific risk the
  mechanism exists to prevent, so it was verified directly per the task's instruction rather
  than trusted on the strength of the isolation design alone.

## 2026-07-20 — Eleventh stock-type profile: homebuilder, replacing a profile built entirely from guessed tags

`homebuilder` is the first profile in this project where the existing `PROFILE_CONCEPT_OVERRIDES`
entry was already wrong going in — built from plausible-sounding tag names
(`InventoryRealEstate`/`RealEstateHeldforDevelopment`, `HomebuildingCostOfSales`, etc.) that were
never checked against a real filing. Running DHI against them produced near-total misses:
`AccountsPayable`/`AccountsReceivable`/`OperatingIncomeLoss`/`LongTermDebt` all 0%, `CostOfRevenue`
13%. Every one of this log's usual disciplines (check the real tag, verify magnitude at overlap
points, two-step byte-identical-then-add) applied here for the first time to a full profile
rebuild rather than a coverage gap.

### DHI's real tags, found by reading the actual filing data

- **`CostOfRevenue`**: the guessed `CostOfRealEstateRevenue`/`HomebuildingCostOfSales` only ever
  covered a narrow 2016–2019 transition window (`HomebuildingCostOfSales` doesn't even exist as a
  tag DHI has ever used). The real, dominant, modern tag is plain `CostOfRevenue` — 39 unique
  quarters, 2016–2026, not in the candidate list at all. Verified against `HomeBuildingCosts` at
  their one shared fiscal year (FY2016: $9,502.6M vs. $9,403.0M) — close but not identical, exactly
  as expected since `CostOfRevenue` is the *consolidated* total (homebuilding + financial services)
  and `HomeBuildingCosts` is the homebuilding segment alone. Confirms `CostOfRevenue` is the right
  concept-level match, not a coincidence. 13% → 54%.
- **`LongTermDebt`** (0% → 87%): DHI tags debt under `NotesPayable`, not `LongTermDebt` (which DHI
  has never used at all) — 61 quarters, 2010–2026. Added as this profile's first `LongTermDebt`
  override.
- **`AccountsReceivable`** (0% → 50%): the guessed `AccountsReceivableNetCurrent` doesn't exist for
  DHI. The real tag is `AccountsAndNotesReceivableNet` — and checked directly rather than assumed,
  per the task's explicit instruction: this is **not** the near-zero case it might look like for a
  homebuyer-mortgage-settlement business. Real values, $60M–$164M, a genuine receivable line (likely
  the financial-services/title segment or builder-to-builder land sales) that the original guess
  simply missed entirely. Same "checked, found real data, not near-zero" outcome as 6 of 7 "expected
  near-zero" cases in the original retail scan.
- **`AccountsPayable`** (0% → 50%): `AccountsPayableCurrent` doesn't exist for DHI either. Real tag:
  `AccountsPayableCurrentAndNoncurrent` ($580–634M, FY2017–19). Two other payable-adjacent tags were
  checked and rejected: `ConstructionPayableCurrentAndNoncurrent` is a genuinely separate, smaller
  liability (~$25–62M same years — a subcontractor-retention line, not overlapping AP), and
  `AccountsPayableAndAccruedLiabilitiesCurrentAndNoncurrent` is ~2.5–3x larger ($1.57–1.91B same
  years) — AP plus accrued liabilities combined, rejected as too broad, same "don't combine
  deliberately separate concepts" rule as always.
- **`Inventory`**: the guessed tag (`InventoryRealEstate`) turned out to be *correct* — confirmed
  by checking it actually resolves to real, substantial values ($3.4B–$11.6B, matching D.R. Horton's
  real balance-sheet scale), not silently resolving to nothing, per the task's explicit "verify,
  don't assume it's working just because it's not in the flagged list" instruction. The two
  additional guessed tags alongside it (`RealEstateHeldforDevelopment`,
  `InventoryRealEstateHeldforDevelopment`) don't exist for DHI at all and were dropped as dead
  weight.
- **`OperatingIncomeLoss`** (confirmed 0%, no fix): checked directly rather than assuming this is
  another instance of the by-now-eleven-times-confirmed diversified-conglomerate pattern. It isn't
  the same shape — DHI simply has no `OperatingIncomeLoss` tag under any name, likely because
  capitalized interest costs blur the operating/non-operating line enough that homebuilders commonly
  skip a discrete operating-income subtotal. Confirmed the mechanism is different even though the
  outcome (0%) looks the same as JNJ/HON's.

Applied with the two-step discipline the task explicitly called for, since this profile's overrides
had never actually been through a real non-regression check: Stage B1 (dropping the three
confirmed-dead guessed tags, no additions yet) verified byte-identical — a true no-op, since dead
tags never matched anything to begin with. Stage B2 (the real replacements above) produced 0
changed, 0 removed, 160 new fills, all DHI.

### A tag that's the right fix for two tickers and the wrong fix for two others

Extending to LEN, PHM, NVR surfaced a genuine cross-ticker naming split: DHI uses
`InventoryRealEstate`; LEN and PHM instead use `InventoryOperativeBuilders` (65/70 quarters for
PHM, 2009–2026 — a clean, near-complete match; only 12 gapped quarters for LEN's own filing
history, no better alternative found). Added as a second Inventory fallback tag — safe for DHI
(which has never used this tag name) and immediately fixed PHM's Inventory from 0% to 93%.

**A near-miss caught before it shipped**: `InventoryRealEstateLandAndLandDevelopmentCosts` looked
like NVR's answer — NVR has no `InventoryRealEstate` or `InventoryOperativeBuilders` at all, and
this tag gives 57 clean quarters, 2011–2025, with genuinely small values ($70–91M) consistent with
NVR's lot-option business model. But checked for overlap before adding it to the shared profile
list — and DHI *also* has this exact tag, where it's a **land-only component** roughly half of
`InventoryRealEstate`'s total ($4.5B vs. $9.2B at FY2017-Q3). Adding it as a profile-wide fallback
would have silently substituted a ~50%-too-low value into every one of DHI's 28 gap quarters,
looking like real data. **Not added.** This is the same shape as the CAT/PCAR/TXT captive-finance
finding and the FIFO/LIFO trap before it: a tag name that means one thing for one filer and a
narrower thing for another, caught by checking magnitude at every overlap rather than trusting a
tag name that worked once. NVR's `Inventory` stays at 0% — confirmed real, structurally different
data exists, but can't be safely wired into a profile shared with DHI/PHM without a per-ticker
override mechanism this codebase doesn't have.

### NVR: genuinely different, not broken — confirmed rather than assumed either way

The task flagged NVR as a known structural outlier (lot-option contracts instead of owned land, an
unusually asset-light balance sheet) and asked to distinguish a real business-model difference from
a missing-tag problem rather than assume either. Checked every flagged concept individually:

- **`LongTermDebt`** (3%, 2 points): `LongTermDebt` ($600M, 2013) and `SeniorNotes` ($599M, 2012)
  each appear exactly once, then never again. Consistent with NVR's real reputation as one of the
  most conservatively-financed homebuilders — essentially debt-free since the early 2010s. Confirmed
  genuine, not a gap.
- **`Inventory`** (0%, real tag exists but unshareable — see above): genuinely ~100x smaller than
  DHI/LEN/PHM's inventory scale, consistent with not owning land directly.
- **`CostOfRevenue`, `AccountsReceivable`, `AccountsPayable`, `DividendsPerShare`** (all 0%): searched
  exhaustively, no tag of any kind exists for any of the four. NVR has never paid a dividend (real,
  confirmed policy — buybacks only), and its cost-of-revenue/AR/AP presentation apparently doesn't
  use any of the standard tag names checked across this entire project so far.

### operating_margin / net_debt_to_ebitda / ev_ebitda: the health_services precedent, inverted

Checked `OperatingIncomeLoss` per ticker rather than assuming all four share DHI's outcome, per the
task's instruction — and the split is real: LEN tags it cleanly (144 raw points, not flagged at
all); DHI, PHM, and NVR all have zero. Same evidence-gathering method as the health_services
decision, opposite conclusion: there, 5 of 6 tickers were clean, so the metrics stayed visible; here
only 1 of 4 is, so **`operating_margin`/`net_debt_to_ebitda`/`ev_ebitda` are hidden profile-wide**.
`OperatingIncomeLoss` excluded from `get_expected_concepts` for the same reason `pharma_medtech`
excluded it — nothing visible depends on it for any of the four tickers once the dependent metrics
are hidden, including LEN, whose own coverage was already fine.

### A real business event correctly *not* flagged as a scope break

LEN's `InventoryOperativeBuilders` shows $20.3B (FY2024) dropping to $11.8B (FY2025), a 42% swing —
checked against the same same-filing-date-restatement detector used for HON/MMM/NWSA. It doesn't
match that signature: both values were filed for the first time in the same (most recent) 10-K, not
a later revision of a previously-different-reported figure. Consistent with a real, one-time event
— Lennar's February 2025 Millrose Properties land-banking spinoff — reflected as a normal sequential
value change, not a retroactive restatement. Correctly not flagged as a scope break; noted as
real-business-event context instead.

### Non-regression

Full before/after diff across the entire cached universe (308 → 311 tickers as DHI/LEN/PHM/NVR were
added): 0 changed, 0 removed, 2,169 new fills, all four homebuilder tickers. DHI's own facts
verified byte-identical between the Stage B2 checkpoint and the final config (confirming the later
`LongTermDebt`/`Inventory` tag additions — made for LEN/PHM/NVR's benefit — are true no-ops for DHI,
since it has never used either of the newly-added tag names).

## 2026-07-20 — Tenth stock-type profile: media, a dividend that exists but can't be extracted, and rule_of_40's one real exception

14 tickers (DIS reference + 13 new). `media` is the first new profile in this project where the
anchor ticker showed **no** `OperatingIncomeLoss` fragility at all — `operating_margin`,
`net_debt_to_ebitda`, `ev_ebitda` all came back clean for DIS, and no `PROFILE_CONCEPT_OVERRIDES`
entry was needed going in. One real problem surfaced instead: a genuine, currently-paying dividend
that the pipeline could not see.

### DIS's dividend: the data exists, the tag is right, and it's still unextractable

Disney suspended its dividend in May 2020 and resumed it in January 2024 ($0.30/share, raised
twice since to $0.75). `dividend_yield` showed zero coverage across the entire 2022–2026 window
despite this being public, confirmable, ongoing history — not an "expected suspension gap."

Checked the raw facts directly rather than guessing at a missing tag. DIS's resumed dividend *is*
tagged, under the *same* two candidate tags already in the base config
(`CommonStockDividendsPerShareDeclared`, `CommonStockDividendsPerShareCashPaid`) — the exact values
($0.30, $0.45, $0.50, $0.75) are sitting right there in the company-facts JSON. The problem is
structural: **every single one of the 19 post-2024 facts has no `start` date** — Disney switched to
tagging the dividend as a declaration-event fact (semi-annual, ~6 months apart: 2024-01-10,
2024-07-25, 2025-01-16, 2025-07-23, 2026-01-15) rather than a fiscal-period duration fact.
`extract_period_values` requires a `start` for any `point_in_time: False` concept (`if "start" in
item: ... else: continue` for duration concepts) — every one of these facts gets silently dropped
before extraction even begins.

This is the same root shape as the COO trap logged in the consumer_staples entry above (a
"declared" tag reported without duration attributes), but with an added wrinkle that rules out even
a workaround: DIS's declaration dates (Jan 10, Jul 25, ...) don't fall on fiscal quarter-ends, so
even flipping the concept to `point_in_time: True` for this profile (which *would* let the
no-start facts through, since `is_point_in_time=True` treats a missing `start` as automatically
valid) wouldn't fix the user-visible problem — the resulting `end` dates wouldn't align with the
quarter-end grid every other concept uses, so `calculate_ratio`'s inner-join merge for
`dividend_yield`/`payout_ratio` would still never find a match. **No tag or mode-level fix exists
for this without a broader "snap to nearest fiscal quarter" reconciliation step, which is out of
scope for a tag-coverage task.** Reported as a confirmed, well-understood, currently-unresolved gap
— a real dividend the pipeline structurally cannot see, not a missing tag.

### Two more confirmed instances of already-validated tags

- **Capex (EA, 4%→92%)**: `PaymentsToAcquireOtherPropertyPlantAndEquipment` — the same tag that
  fixed LLY (pharma_medtech) and ADP (industrials) — now a *third* confirmed instance, across a
  third sector. Exact match at the one overlap point (2010-06-30, $11M both tags).
- **CashAndEquivalents (FOX/FOXA, 16%→97%)**: `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents`
  — now a *fourth* confirmed instance (after TGT, GEV, CAT). Exact match at all 4 overlap dates.

Both added as a new `media`-scoped `PROFILE_CONCEPT_OVERRIDES` entry — the profile's first, per the
task's framing. Two-step discipline: Stage B1 (base-tag copies) verified byte-identical; Stage B2
produced 0 changed, 0 removed, 152 new fills across 6 tickers (EA, FOX, FOXA — targeted — plus OMC,
TKO, DIS as bonus beneficiaries of the cash tag).

### Dual-class tickers: verified identical, not assumed

FOXA/FOX and NWSA/NWS each share a single CIK (`0001754301`, `0001564708`) — confirmed the cached
`company_info.json` files are byte-identical between each pair before treating them as
interchangeable anywhere in this scan, rather than assuming from the shared-CIK fact alone.

### A scope break found where expected, and — just as informative — one that wasn't (yet)

**NWSA/NWS**: three consecutive fiscal years (FY2022, FY2023, FY2024) all restated on the same
filing date (2025-05-13) by consistent ~$1.83–1.95B deltas — News Corp's 2024 sale of Foxtel
(Australian pay-TV). Same signature discipline as the industrials entry (dollar deltas, not
percentages, to avoid false positives from routine presentation differences).

**TKO**: an unusual *positive* restatement — FY2022/2023 revenue jumped by +$1.53B/+$1.55B, filed
2025-03-19. Not a divestiture; the opposite shape, consistent with retroactive combined-entity
accounting following the September 2023 WWE/UFC merger (predecessor financials restated to reflect
the full combined entity). Named as a distinct pattern from the usual divestiture-shrink case, not
forced into the same bucket.

**WBD**: checked specifically, per the task's expectation that its 2025-announced two-company split
would show the same signature — it doesn't, not yet. `OperatingIncomeLoss` and `Revenue` are both
completely unrestated across every filing through 2026-02-27. The split was announced in 2025 but
hasn't closed; SEC filings only retroactively restate for discontinued operations after a
transaction actually completes (the same timing HON's Solstice restatement followed). A confirmed
non-finding, reported as "not yet" rather than silently assumed clean.

### rule_of_40: checked across the whole batch, not decided from DIS alone

Computed `rule_of_40` for all 13 new tickers plus DIS. Only **TTD** sits structurally near or above
the 40% line — 93% of its quarters ≥40%, minimum 37.5%, confirming the task's own hypothesis that a
higher-growth, asset-light platform would be the most plausible candidate. Every other ticker is
either consistently well below (DIS: 0% of quarters ≥40%, mean 13.9%; OMC, FOXA/FOX, NWSA/NWS all
similarly low) or swings too wildly to be structurally meaningful rather than noisy (NFLX 14%
≥40%; WBD 24% but ranging 3%–187%; TTWO 35% but ranging -62%–158%; LYV ranging -321%–175%).
**Hidden profile-wide** — same call as every other profile built so far. TTD's signal is real but
doesn't outweigh 12 other tickers' worth of noise, and `PROFILE_HIDDEN` has no per-ticker override
mechanism; documented as the one confirmed exception in `media_scan_report.md` in case a future
profile split ever separates high-growth ad-tech/platform media names from traditional media.

### Everything else: already-established patterns, not new ones

- **FOXA/FOX, NWSA/NWS — `OperatingIncomeLoss`, 0% each.** Neither tags the concept at all —
  confirmed via direct key lookup, not inferred from the coverage number. Same diversified-media
  "never tagged" shape as JNJ/ADM/EMR/etc., now confirmed a tenth-plus time.
- **FOXA/FOX — real dividend payer, never tagged per-share.** `PaymentsOfDividends` shows real,
  nonzero quarterly payments ($35–65M); no per-share tag exists anywhere. Same shape as HSY/TSN/DHR.
- **NFLX, TTD — no `Goodwill`; TTD — no `LongTermDebt` either.** Both are asset-light, minimal-M&A
  companies with no tag at all for either concept (not a `$0`-valued tag — a total absence).
  Consistent with real company history (Netflix's near-entirely-organic growth, The Trade Desk's
  minimal acquisitions and negligible debt) — same "confirmed absence, not a bug" pattern as
  GRMN/REGN.
- **EA — `LongTermDebt`, 31%.** Real debt history 2011–2017 (convertible notes), genuinely absent
  since — checked every debt-family tag EA has ever used, nothing post-2017. Not a gap, a real
  capital-structure change.
- **TKO — no `Capex` tag at all.** Consistent with its short combined history (formed September
  2023) — searched broadly (`PaymentsFor*`, `CapitalExpenditures*`), nothing found.
- **PSKY — everything thin (15–46%).** Paramount Skydance merger completed August 2025; only 13
  quarters of any kind of history exist. Same "young combined entity" shape as TKO, GEV, VLTO,
  SOLV in prior entries — not investigated ticker-by-ticker beyond confirming the short-history
  explanation covers the whole cluster.
- **TTWO — confirmed non-payer, contradicting the task's own premise.** The task's brief listed
  TTWO among "established payers" (OMC, EA, TTWO); checked directly and found no dividend tag of
  any kind for Take-Two. Reported as found, not silently corrected to match the brief's
  expectation — same discipline as the AZO/AccountsReceivable case in the retail scan.
- **TKO's one dividend data point ($3.86, FY2023)** is a predecessor-financials artifact from the
  WWE/UFC merger accounting, not an ongoing program — confirmed by checking for any subsequent
  quarter (none exist).
- **Content-asset amortization (NFLX, WBD, PSKY)**: noted but not investigated further per the
  task's own scoping — these companies capitalize large produced/licensed content libraries, which
  can make `DepreciationAndAmortization`-derived metrics (`ebitda`, `net_debt_to_ebitda`) behave
  differently than for an industrial-style company. No coverage problem found for any of the three,
  so no fix was needed; flagged as context for a future session if their EBITDA-based metrics ever
  look off.

## 2026-07-20 — An absolute-floor guard for operating_leverage, and CAT/PCAR/TXT deferred to a future captive-finance profile

Two independent fixes out of the industrials scan above, kept in separate non-regression scopes:
a guard on `operating_leverage`'s own near-zero-growth-rate explosion, and the removal of three
industrials tickers whose captive-finance subsidiaries make their consolidated figures unreliable.

### Part A — operating_leverage needed a different kind of guard than roe/debt_to_equity did

`operating_leverage = operating_income_yoy_growth / revenue_growth`. The 2026-07-15
`min_base_ratio` guard and the 2026-07-20 `MIN_DENOMINATOR_SCALE_RATIO` equity guard both compare
a *dollar* denominator against a dollar-denominated scale reference. `revenue_growth` is already a
*percentage* — there's no dollar figure to scale it against, so this needed a genuinely different
mechanism: an absolute floor on the denominator itself, not a relative-to-another-concept
comparison.

**Calibration, not guessing.** Pulled `revenue_growth` at every quarter across all 70 tickers then
still in `industrials` where `|operating_leverage| > 20` (an exploratory filter, not the final
threshold) — 165 rows. Median `|revenue_growth|` at those points was 0.53%; the worst cases (SWK's
literal `inf`/`-inf` at exactly 0.000%, MMM at 1400, RSG at -812) all sit under 1%. Extending the
filter to *every* row (not just the >20 ones) confirmed there's no clean bimodal gap the way IBM's
growth-rate case had for `min_base_ratio` — the distribution is continuous, same shape already
found for the equity guard's threshold search. Picked the threshold from the marginal-return curve
instead of a gap:

```
threshold   masked rows   catches |leverage|>20   catches |leverage|>50
1.0%        223 (7.0%)    103                     56
1.5%        332 (10.4%)   121                     60
2.0%        449 (14.0%)   135                     62
2.5%        554 (17.3%)   144                     64
3.0%        680 (21.2%)   149                     64
```

Beyond 2%, each additional 0.5pp of threshold buys almost no new extreme-value catches (2 more
`>50` cases, ever) while the masked-row count keeps climbing linearly — pure collateral damage.
**Chose 2% (`MIN_OPERATING_LEVERAGE_REVENUE_GROWTH = 0.02`)**: catches 91% of all `|leverage|>20`
cases and 97% of the truly extreme `|leverage|>50` cases, for 14% of rows masked rather than 21%.

**Implementation**: `calculate_ratio_from_dfs` gained an optional `min_denominator_abs` parameter
(off by default — same additive shape as every guard in this project) that masks the result
(`NaN`, not a dropped row) when `abs(denominator) < min_denominator_abs`. Passed only at
`operating_leverage`'s call site. Checked its two other callers before leaving them alone, per the
task's explicit instruction not to assume: `fcf_margin` divides by `Revenue_TTM` (a dollar figure
that essentially never hits zero for an operating company) and `net_debt_to_ebitda` divides by
`EBITDA_TTM` — also dollars, and where it *does* explode (Boeing, 11 quarters during the 737 MAX/
COVID era, `|net_debt_to_ebitda|` up to 94) the cause is a real earnings collapse, not a
percentage-denominator artifact. Neither shares the identical failure mode; neither was touched.

**Verified rather than assumed** the guard doesn't over-mask: HII (2014-06-30, 3.36% revenue
growth, leverage 20.0), IEX (2014-03-31, 5.84%, leverage 34.2), IR (2019-03-31, 7.05%, leverage
23.7), and GEV (2025-12-31, 8.97%, leverage 21.6) all survive untouched — real, large operating
leverage on real, measurable revenue growth stays visible, exactly the case the task's Step 3
warned against suppressing. Diffed old vs. new across the full set: 0 previously-populated values
changed, only masking occurred, 449 `(ticker, end)` pairs newly `NaN`, max `|revenue_growth|`
among them 1.99% (confirms the boundary is exact).

Of the task's own two motivating examples, both CMI quarters got masked; of CAT's two, only the
-1.39%-growth one did (the +2.47% one sits just above the 2% line and stays visible) — moot in
practice, since CAT leaves the `industrials` profile entirely in Part B below.

**Caveat, same as every threshold in this log**: empirically tuned against the current 70-ticker
`industrials` universe, not derived from a closed-form rule — may need revisiting as more tickers
are added, the same caveat carried by `min_base_ratio` and `MIN_DENOMINATOR_SCALE_RATIO`.

### Part B — CAT, PCAR, TXT removed from industrials, deferred to a future Group 5 profile

The industrials scan above flagged CAT's and PCAR's captive-finance subsidiaries (Cat Financial,
PACCAR Financial) as a likely source of consolidated-debt distortion, the same concern that kept
Ford and GM out of every profile built so far — their captive-finance arms (Ford Credit, GM
Financial) make consolidated debt/equity figures unrepresentative of the manufacturing business's
real leverage, so F/GM were earmarked for a future "Group 5: captive-finance archetype" profile
instead of being force-fit into `standard` or anywhere else. TXT (Textron Financial Corp) fits the
same shape and was flagged incidentally during the same scan.

Removed `"CAT"`, `"PCAR"`, `"TXT"` from `TICKER_PROFILES` entirely — not reassigned anywhere.
`TICKERS` in `config.py` was already just `["HON"]` (the scan's own reference ticker, not a live
production list) and never contained any of the three, so there was nothing to remove there; noted
rather than forced, since the task's premise assumed a fuller list that isn't this project's
current state. Verified via a full-universe facts diff (293 cached tickers, every profile): 0
changed, 0 removed, 0 new fills for every ticker other than the three removed — confirmed clean
end-to-end pipeline run across the remaining 67 `industrials` tickers, no crash, no orphaned
references anywhere in the codebase (grepped for `"CAT"`/`"PCAR"`/`"TXT"` outside scratch scripts).

**Group 5 backlog — captive-finance archetype tickers, no profile yet:**

| Ticker | Captive-finance subsidiary | Why it's deferred, not force-fit |
|---|---|---|
| F | Ford Credit | Consolidated debt/equity dominated by auto-lending book, not representative of the manufacturing business's real leverage |
| GM | GM Financial | Same shape as F |
| CAT | Cat Financial | Only long-term-debt tag (`LongTermDebtNoncurrent`) is annual-only for its entire 2008–2025 history and is almost certainly the full consolidated figure (~$22–38B) — industrial debt and captive-finance debt bundled with no non-dimensional way to separate them |
| PCAR | PACCAR Financial | No consolidated `LongTermDebt`-family tag exists at all, despite a large financing-receivables book (`PaymentsToAcquireFinanceReceivables`, 153 points) clearly present |
| TXT | Textron Financial Corp | No usable `Goodwill` or `LongTermDebt` tag either — same structural shape as CAT/PCAR, found incidentally during the industrials scan |

## 2026-07-20 — Ninth stock-type profile: industrials, a dead metric wired back in, and a confirmed cross-sector scope-break pattern

70 tickers (HON reference + 69 new). `industrials` reuses `standard`'s metric set and adds two new
metrics — `capex_intensity` and `operating_leverage` — built entirely from concepts already in
base `CONCEPT_CANDIDATES`; both were already implemented correctly going in (confirmed the prior
session's fix — `calculate_growth`'s missing `periods` argument and `calculate_ratio_from_dfs`'s
wrong column reference — was actually in place before touching anything).

### A metric that was computed every run and never once reached a chart

The task asked for a judgment call on whether `operating_income_yoy_growth` (the intermediate
growth rate feeding `operating_leverage`) adds standalone value once plotted. Tried to plot it —
and found it couldn't be: `calculate_all_metrics` computes `m["operating_income_growth"]` every
run, but `build_metrics_long`'s `spec` list never included it, and `figures.py`'s
`plot_fundamentals` never listed it either. The metric has been computed and silently discarded
every single run since it was added — the exact "fails silently, several layers from the cause"
pattern this whole log is about, just inside the metrics layer instead of the tag layer. Wired it
into both (`main.py`'s `spec` list, `figures.py`'s `concepts_to_plot`) so the judgment call could
actually be evaluated against real data, not guessed at.

### Once visible: it's the sane half of a routinely insane ratio

Plotted `operating_income_yoy_growth` against `operating_leverage` for six tickers. The pattern was
immediate and consistent: whenever `revenue_growth` (the ratio's denominator) sits near zero for a
quarter, `operating_leverage` explodes — CMI hit **+1039.88** one quarter and **-332.73** the next,
both attached to an `operating_income_yoy_growth` of a perfectly ordinary +113%/+139%; CAT and PH
swing similarly (CAT: +11.97 → -11.09 → +9.30 across three consecutive quarters). In every one of
these cases, `operating_income_yoy_growth` itself stayed a sane, readable percentage — it's
`operating_leverage`, not the growth rate, that's the unstable half of the pair. **Decision: keep
`operating_income_yoy_growth` visible for `industrials`** — hiding it would remove the only
context that lets a reader tell "real operating leverage story" from "ratio artifact from a
near-zero revenue-growth quarter" apart. Same near-zero-denominator failure class as the
`min_base_ratio` and `MIN_DENOMINATOR_SCALE_RATIO` guards already in this codebase — not fixed
here (out of scope for a tag-coverage task), but flagged as a real candidate for a future guard on
`operating_leverage` itself. Since the fix that wired the metric into `main.py`/`figures.py` is
global (not profile-scoped), `operating_income_yoy_growth` would otherwise have started appearing,
unfiltered, on every other profile's charts too — added it to all eight other profiles'
`PROFILE_HIDDEN` sets (alongside `capex_intensity`/`operating_leverage`, already handled there) so
only `industrials` shows it.

### Four tag fixes, three of them useful far beyond their original ticker

- **NetIncomeLoss (ITW, 0%→96%)**: ITW tags neither `NetIncomeLoss` nor
  `NetIncomeLossAvailableToCommonStockholdersBasic` — anywhere, ever. It uses `ProfitLoss` instead
  (net income including noncontrolling interest), confirmed by matching real reported figures
  ($2.1B–$3.5B, 2020–2025) rather than assumed from the tag name.
- **Capex (ADP, 0%→96%)**: same `PaymentsToAcquireOtherPropertyPlantAndEquipment` tag that fixed
  LLY's capex in the pharma_medtech entry below — confirmed useful for a second, unrelated company
  in a different sector.
- **CashAndEquivalents (GEV 0%→100%, CAT 38%→63%)**: same
  `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` tag that fixed TGT in the
  consumer_staples entry, now a *third* confirmed instance. Verified CAT's restricted-cash
  component is negligible (differences of a few million against multi-billion balances, <0.15%) at
  every overlap point before trusting it.
- **Revenue (PWR, 49%→95%)**: PWR's revenue was tagged as `SalesRevenueServicesNet` before its 2018
  ASC 606 transition, then switched to `RevenueFromContractWithCustomerExcludingAssessedTax` —
  exact match at all six overlap dates. Extends PWR's revenue history back to 2008.

All four applied as an `industrials`-scoped override (byte-identical Stage B1 first, 0 diffs; Stage
B2 additions produced 0 changed, 0 removed, 550 new fills across **30** tickers — far more than the
4 originally targeted, confirming these tags generalize across the sector rather than being
single-company quirks).

### The segment-divestiture recast trap, now confirmed a third and fourth time — and found in 9 more tickers

The prior entries logged this exact failure mode for JNJ (Kenvue) and KO (bottler refranchising).
HON's own history showed it clearly: FY2023 and FY2024 `OperatingIncomeLoss` and `Revenue` both
restated by near-identical dollar amounts (~$1.03B / ~$3.7B) in filings on the **same date**
(2026-02-17) — Honeywell's October 2025 Solstice Advanced Materials spinoff. FY2022 was never
refiled, so it sits on the pre-spinoff scope right next to two years on the post-spinoff scope — a
real discontinuity, not a bug.

Built a detector for the same signature (≥2 fiscal-year-ends restated on the same filed date, by
similar-magnitude dollar deltas — not percentage, since percentage alone conflates this with
routine gross/net presentation differences like CHRW's and CPRT's, which restate by 80%+ every
year for a decade and are a completely different, unrelated pattern) and ran it across all 69
tickers, filtered to restatements filed 2023 or later (what would actually sit in a chart someone
is looking at today). Found the pattern, beyond HON, in **MMM** (Solventum spinoff, Apr 2024),
**CARR** (Fire & Security divestitures), **DOV**, **EMR** (Climate Technologies majority stake
sale), **FTV** (Ralliant spinoff), **GE** (the three-way Aerospace/Vernova/HealthCare split — by
far the largest, ~49% of revenue), **J** (Amentum divestiture), **JCI**, and **LHX**. Two of the
task's eight named "check closely" tickers — **ITW and OTIS** — were checked directly and show
**no** scope break in their current-era `OperatingIncomeLoss` history; reported as checked-and-
clean rather than assumed clean from being merely "less complex" than GE.

### CAT and PCAR: captive-finance distortion risk, reported not fixed

Same concern as the Ford/GM captive-finance exclusion precedent. CAT's only long-term-debt tag
(`LongTermDebtNoncurrent`) is annual-only for its *entire* cached history (2008–2025, no quarterly
breakdown ever) and, at ~$22–38B, is almost certainly the full consolidated figure — Cat Financial's
receivables-backed borrowings included alongside the industrial business's own debt, with no
non-dimensional tag available to separate the two (the segment-level split CAT discloses is
dimensional, and — same limitation already logged for STZ's dual-class shares — this pipeline's use
of the plain `companyfacts` endpoint can't see dimensional facts at all). PCAR is worse: no
consolidated `LongTermDebt`-family tag exists at all despite PACCAR Financial's large financing-
receivables book being clearly present in the data. Neither ticker was reassigned — findings only,
per the task's standing rule for this category of question. Noted TXT as a related, unnamed case:
no usable `Goodwill` or `LongTermDebt` tag either, and Textron also runs a captive-finance arm
(Textron Financial Corp).

### Everything else: the OperatingIncomeLoss-fragility pattern, now confirmed for the ninth time

ADP, EMR, ETN, GE, HON, JCI, LHX, PCAR, ROK, ROL, and TXT all show `OperatingIncomeLoss` well below
50% coverage — traced individually rather than batch-assumed structural. Three distinct shapes, all
already-logged patterns rather than new ones: **never tagged at all** (ADP, EMR, PCAR — the
NKE/ADM/BG/CASY/CLX shape); **abandoned after a specific year** (GE stops in 2014, JCI stops in
2016, ETN in 2013, TXT in 2011 — the SYY/PFE D&A shape, applied here to operating income instead of
depreciation); **started only recently** (HON and ROL both begin in 2021, ROK only has 4 quarters,
all 2024–2026). None chased with a successor tag, per the task's explicit instruction for this
now-thoroughly-confirmed pattern. LMT's `DepreciationAndAmortization` (47%) is a clean instance of
the same annual-only-for-a-stretch shape as SYY and PFE — an 8-year gap (2017–2024) bounded by
otherwise-clean quarterly tagging on both sides.

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