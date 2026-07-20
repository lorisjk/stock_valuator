# Retail Tag Coverage Scan (18 tickers)

ORLY was not actually cached yet at the start of this task (neither were 17 of the 18 target
tickers — only HD was); all 19 were freshly fetched. All non-regression diffs cover every cached
ticker (145 `cache/*_company_info.json` files across every profile), not just the 18 retail
ones. `config.py` was modified; every change below was verified against the full cached universe
before being kept.

## Setup verification

Confirmed all 18 tickers plus ORLY are listed as `retail` in `TICKER_PROFILES`.
`PROFILE_EXCLUDED_CONCEPTS` has **no `"retail"` key** — unlike `insurance_pc`/`insurance_life`,
this is correct and requires no fix: the `retail` profile's overrides only ever *add* new concept
keys (`Inventory`, `CostOfRevenue`, `AccountsReceivable`, `AccountsPayable`); it never inherits
insurance-only concepts the way `get_concept_candidates` merges profile overrides on top of the
shared base. Confirmed empirically — `get_expected_concepts("ORLY")` returns exactly the 16
concepts retail tickers should have, no insurance/bank concepts leaking in.

## Step 1 — Coverage scan

Flagged concepts (excluding the expected `DividendsPerShare` non-payer cases — AZO, DECK, LULU,
ORLY, GRMN, ULTA correctly don't pay dividends):

| Ticker | Concept | Coverage |
|---|---|---|
| GPC | AccountsReceivable | 0/73 (0%) |
| GPC | OperatingIncomeLoss | 22/73 (30%) |
| LOW | AccountsReceivable | 6/75 (8%) |
| DECK | LongTermDebt | 0/70 (0%) |
| GRMN | LongTermDebt | 0/76 (0%) |
| GRMN | Goodwill | 30/76 (39%) |
| LULU | LongTermDebt | 0/69 (0%) |
| NKE | OperatingIncomeLoss | 0/74 (0%) |
| ROST | Goodwill | 6/71 (8%) |
| ROST | OperatingIncomeLoss | 9/71 (13%) |
| TJX | OperatingIncomeLoss | 21/74 (28%) |
| TJX | CostOfRevenue | 35/74 (47%) |
| TSCO | AccountsReceivable | 0/73 (0%) |
| ULTA | LongTermDebt | 2/67 (3%) |
| ULTA | Goodwill | 32/67 (48%) |
| WSM | CostOfRevenue | 7/74 (9%) |

**BBY, RL, HAS, TPR were not flagged for anything** — already ≥50% across the board.

### The AccountsReceivable exception list from the task didn't hold up — checked, not assumed

The task named ORLY, AZO, ROST, TJX, ULTA, TSCO, WSM as "expected candidates" for near-zero
`AccountsReceivable` coverage (pure consumer-cash checkout, no meaningful trade receivable line).
Checked full coverage for all 7 directly, not just the `<50%` flags:

| Ticker | AccountsReceivable coverage |
|---|---|
| ORLY | 66/71 (93%) |
| AZO | 68/73 (93%) |
| ROST | 69/71 (97%) |
| TJX | 72/74 (97%) |
| ULTA | 66/67 (99%) |
| WSM | 68/74 (92%) |
| TSCO | 0/73 (0%) |

**Only TSCO actually matches the assumed pattern.** The other six all have excellent AR coverage
— almost certainly because each of these "consumer-cash" retailers runs a real secondary B2B/
credit channel that generates genuine trade receivables (ORLY's and AZO's commercial/DIFM
programs selling to independent repair shops being the clearest case), or the tag captures
another real current-receivable category (credit-card settlement receivables, landlord
allowances) rather than nothing at all. The task's premise here doesn't match what the data
actually shows — reported as found, not forced to fit the expected narrative. TSCO alone was
investigated for a missed tag and confirmed genuinely absent (see below).

## Step 2 — Investigation findings

### Resolved: three clean, verified additions

- **GPC, AccountsReceivable**: `AccountsNotesAndLoansReceivableNetCurrent` gives full continuous
  coverage (69 points, 2008–2026, $1.2B→$2.6B — sane magnitude for a $20B+ wholesale auto-parts
  distributor). GPC is one of the task's named B2B/wholesale tickers that should have real AR —
  confirmed, and now fixed. Added as an additional fallback tag.
- **DECK, LongTermDebt**: `NotesPayable` gives clean, continuous coverage 2013–2021 (29 points),
  ending in a value that **decays smoothly to exactly $0 at 2021-03-31** — a genuine debt payoff,
  not a data cutoff. Deckers Brands is a well-known debt-free growth company; this matches. Added
  as the lowest-priority `priority_merge` source.
- **LULU, LongTermDebt**: `OtherBorrowings` exists for all 20 available quarters (2020–2026) and
  is **exactly $0 in every single one**. This is meaningfully different from no data at all — it's
  a filer-confirmed "zero borrowings" reading rather than an unknown. Added as the lowest-priority
  source; raises LULU's LongTermDebt from "no data" to "confirmed zero" for its available window.

**Cross-contamination check before adding, since `LongTermDebt` isn't overridden for `retail` at
all yet** (inherits the shared base list): created a new `retail`-specific override, verified
**byte-identical** to the base list first (Stage B1, 0 diffs across all 145 cached tickers), then
searched all 19 retail tickers for `NotesPayable`/`OtherBorrowings` before adding them. LOW also
carries a `NotesPayable` tag — checked its values against LOW's own already-good `LongTermDebt`
series: consistently ~4–5% lower than the existing tag at matching dates (a real but modest scope
difference, not a duplicate or an error). Since LOW's series has no gaps for this addition to
fill (confirmed via the non-regression diff: **zero new fills for LOW**), this posed no actual
risk — flagged here for completeness of the reasoning, not because it caused a problem.

### Confirmed structural — no viable candidate found (exhaustive search)

- **NKE, OperatingIncomeLoss**: a full raw scan of every `us-gaap` tag containing "income" in
  Nike's filings (100+ tags) turned up no operating-income concept at all — Nike's income
  statement format goes straight from expenses to a combined pretax-income line
  (`IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFrom
  EquityMethodInvestments`) without ever tagging a discrete operating-income subtotal. Not a
  missing tag — the concept itself isn't part of Nike's XBRL presentation.
- **GPC, OperatingIncomeLoss**: the existing tag stops entirely after 2016-03-31. No successor
  tag found (`GrossProfit` exists but is a different, earlier-stage concept; the only other
  candidate, `SegmentReportingInformationOperatingIncomeLoss`, only has 4 old points and per the
  task's own segment-reconciliation caution wasn't pursued further without being able to verify
  it reconciles to a consolidated total).
- **ROST, OperatingIncomeLoss** and **WSM, CostOfRevenue** and **LOW, AccountsReceivable**: all
  three show the *same* pattern — the tag only has data starting in fiscal 2024/2025, with
  nothing earlier under any name searched. Three unrelated retailers independently beginning to
  tag a previously-bundled line item at almost the same time looks like a shared external cause
  (a income-statement-disaggregation change effective around then) rather than three coincidental
  gaps — noted as a pattern, not chased down to a specific citation.
- **TJX, OperatingIncomeLoss**: stops after 2019-02-02, no successor tag found.
- **TJX, CostOfRevenue**: the existing tag (`CostOfGoodsAndServicesSold`) only starts in 2017; an
  exhaustive `"cost"` search of TJX's full tag list found no earlier COGS-family candidate at all.
- **GRMN, LongTermDebt**: no debt-balance tag exists in Garmin's filings at all (only flow tags
  like `RepaymentsOfLongTermDebt`) — consistent with Garmin's well-known debt-free capital
  structure (large net cash position, no bonds or credit facility drawn).
- **ULTA, LongTermDebt**: the only candidate, `LongTermDebtNoncurrent` (already in the base
  `sum` component), has exactly 2 data points — both $800M, both in mid-2020. This reads as a
  brief COVID-era revolver draw, repaid within months; no other debt tag exists for ULTA at any
  point. Genuinely near-debt-free, same pattern as GRMN/LULU/DECK.
- **GRMN, Goodwill**: real, continuous `Goodwill` tag but annual-only through 2021, transitioning
  to genuine quarterly tagging from 2022 onward — a filer tagging-frequency change, not a wrong
  tag. Same category as ACGL's/AIG's Goodwill in the P&C task.
- **ROST, Goodwill**: extremely thin (6 points) at a constant, trivial $2.889M, then the tag
  stops being filed entirely after 2015 — consistent with an immaterial balance the filer simply
  stopped separately disclosing once it fell below their disclosure threshold. No alternate tag
  exists.
- **ULTA, Goodwill**: real data tracking a genuine business event — a flat ~$10.9M from 2018
  through mid-2025, then a **36x jump to $392.6M at 2025-08-02** (a real acquisition, not a data
  error), just not tagged every single quarter (32/67 = 48%, just under the threshold). No
  alternate tag exists; left as-is rather than force anything.
- **TSCO, AccountsReceivable**: exhaustive narrow + broad search found nothing beyond
  `IncomeTaxReceivable`-type tags (a tax refund, not trade AR) and a one-time M&A-footnote item.
  Genuinely no trade receivable line exists — matches the task's expected pattern exactly for
  this one ticker.

## Step 3 — Config changes applied

**`AccountsReceivable`** (simple `fallback`-tag addition, no mode change): appended
`AccountsNotesAndLoansReceivableNetCurrent`.

**`LongTermDebt`** — not previously overridden for `retail` (inherited the shared base list).
Two-step `priority_merge` migration:
1. *Stage B1*: created the `retail`-specific override as an exact copy of the base `sources`
   list. Verified **byte-identical** (0 diffs, 0 new fills) across all 145 cached tickers.
2. *Stage B2*: appended `{"type": "tag", "tag": "NotesPayable"}` and
   `{"type": "tag", "tag": "OtherBorrowings"}` as the two lowest-priority sources.

**No changes**: `OperatingIncomeLoss`, `Goodwill`, `CostOfRevenue` — every flagged gap in these
three concepts was investigated and confirmed structural (no viable candidate survived
verification).

## Step 4 — Non-regression check (full 145-ticker cached universe)

- **Stage B1 (byte-identical `LongTermDebt` copy)**: 0 regressions, 0 new fills — confirmed
  inert, as intended.
- **Stage B2 + `AccountsReceivable` addition**: **0 regressions**, **118 new fills**, all landing
  exactly on the intended tickers:

```
DECK   LongTermDebt        +29
GPC    AccountsReceivable  +69
LULU   LongTermDebt        +20
```

No other ticker in any profile was touched — confirmed empirically, including the specific LOW
cross-contamination check described above (LOW got 0 new fills, exactly as predicted from its
already-complete coverage).

## Step 5 — Before/after coverage

| Ticker | Concept | Before | After | Outcome |
|---|---|---|---|---|
| GPC | AccountsReceivable | 0% | **95%** | ✅ Fully resolved |
| DECK | LongTermDebt | 0% | 41% | ⚠️ Improved, not clean — genuinely debt-free from 2021 onward; the 41% is the real ceiling, not a remaining gap |
| LULU | LongTermDebt | 0% | 29% | ⚠️ Improved, not clean — confirmed-zero debt for its whole tagged history; real data, just sparse (tag only exists 2020+) |
| LOW | AccountsReceivable | 8% | 8% | ❌ Unchanged — structural (tag only exists from FY2024 on, no predecessor found) |
| GPC | OperatingIncomeLoss | 30% | 30% | ❌ Unchanged — structural (tag discontinued after 2016, no successor) |
| NKE | OperatingIncomeLoss | 0% | 0% | ❌ Unchanged — structural (concept never tagged; confirmed via exhaustive raw scan) |
| ROST | OperatingIncomeLoss | 13% | 13% | ❌ Unchanged — structural (tag only exists from FY2024 on) |
| TJX | OperatingIncomeLoss | 28% | 28% | ❌ Unchanged — structural (tag discontinued after FY2019) |
| TJX | CostOfRevenue | 47% | 47% | ❌ Unchanged — structural (tag only exists from 2017 on) |
| WSM | CostOfRevenue | 9% | 9% | ❌ Unchanged — structural (tag only exists from FY2024 on) |
| TSCO | AccountsReceivable | 0% | 0% | ❌ Unchanged — confirmed genuine business characteristic, matches task's expected pattern |
| GRMN | LongTermDebt | 0% | 0% | ❌ Unchanged — structural (Garmin genuinely carries no debt) |
| ULTA | LongTermDebt | 3% | 3% | ❌ Unchanged — structural (one brief COVID-era revolver draw, otherwise debt-free) |
| GRMN | Goodwill | 39% | 39% | ❌ Unchanged — structural (annual-only tagging pre-2022) |
| ROST | Goodwill | 8% | 8% | ❌ Unchanged — structural (trivial, immaterial balance, disclosure stopped after 2015) |
| ULTA | Goodwill | 48% | 48% | ❌ Unchanged — structural (real data tracking a genuine 2025 acquisition, just not tagged every quarter) |

**Summary**: 1 of 16 flagged gaps fully resolved (GPC AccountsReceivable, 0%→95%). 2 improved
with genuine, verified, but inherently sparse data (DECK and LULU LongTermDebt — both real
"confirmed low/zero debt" readings, not missing data). 13 remain unchanged, every one confirmed
structural via exhaustive search (tag never existed, tag discontinued with no successor, or tag
only recently started) rather than assumed. The AccountsReceivable "expected exception" list from
the task turned out to only apply to 1 of 7 named tickers (TSCO) — reported as found, not forced.

No scratch scripts were left behind for Part A.
