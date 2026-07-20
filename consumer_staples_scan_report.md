# Consumer Staples Tag Coverage Scan

34 tickers (KO reference + 33 new): MO, ADM, BF-B, BG, CPB, CASY, CHD, CLX, KO, CAG, STZ, COST, DG,
DLTR, EL, GIS, HSY, HRL, KVUE, KDP, KMB, KHC, KR, MKC, TAP, MDLZ, MNST, PEP, PM, PG, SJM, SYY, TGT,
TSN, WMT.

(The task title and Step 5/Output text both say "33 tickers"; the task's own Step-0 config
snippet — and `config.py` as already configured before this scan started — lists 34 non-KO
tickers. Treated as the same off-by-one-in-prose pattern seen in earlier scans: reported here
rather than silently trimmed to fit the stated count. All 34 were scanned.)

## Step 0 — Setup

`TICKER_PROFILES` and `PROFILE_HIDDEN["consumer_staples"]` were already present in `config.py`
exactly as specified, before this session started — no action needed there.

### BF.B ticker resolution

Checked before any fetching, per the task's instruction. Two independent data sources, two
different failure modes:

| Source | `"BF.B"` (dot) | `"BF-B"` (hyphen) |
|---|---|---|
| SEC `company_tickers.json` / `get_cik` | `ValueError: Ticker BF.B not found in mapping.` (explicit, loud) | Resolves to CIK `0000014693` |
| `yfinance.Ticker(...).info` | Returns a dict that *looks* populated but every field (`currentPrice`, `sharesOutstanding`, ...) is silently `None` | Returns real data (`currentPrice=25.58`, `sharesOutstanding=290383416`) |

The dot form is silently wrong on the yfinance side — worse than the explicit SEC-side error, and
exactly the failure mode the task asked to guard against. **Fixed**: changed the `TICKER_PROFILES`
key from `"BF.B"` to `"BF-B"` in `config.py`, and used `"BF-B"` as the ticker string for fetching
and caching. Confirmed working end-to-end before including it in the batch fetch. No other file
referenced `"BF.B"` or `"BF-B"`, so this was a single, isolated change.

All 34 tickers' `company_info.json` were fetched/cached successfully (33 new + KO, which was
already cached; PG was also already cached from an earlier session).

## Step 1 — Coverage scan

`consumer_staples` inherits the base `CONCEPT_CANDIDATES` unchanged (12 concepts: `Revenue`,
`NetIncomeLoss`, `SharesOutstanding`, `StockholdersEquity`, `OperatingIncomeLoss`,
`OperatingCashFlow`, `Capex`, `DepreciationAndAmortization`, `LongTermDebt`, `CashAndEquivalents`,
`DividendsPerShare`, `Goodwill`) — no `PROFILE_EXCLUDED_CONCEPTS` entry exists or was needed.

17 (ticker, concept) pairs came back below the 50% threshold:

| Ticker | Concept | Count | Max | Ratio |
|---|---|---:|---:|---:|
| ADM | OperatingIncomeLoss | 0 | 73 | 0% |
| BG | OperatingIncomeLoss | 0 | 17 | 0% |
| CASY | OperatingIncomeLoss | 0 | 70 | 0% |
| CLX | OperatingIncomeLoss | 0 | 73 | 0% |
| COST | Goodwill | 12 | 74 | 16% |
| DLTR | DividendsPerShare | 0 | 70 | 0% |
| HSY | DividendsPerShare | 6 | 72 | 8% |
| KR | Capex | 35 | 74 | 47% |
| KR | OperatingCashFlow | 35 | 74 | 47% |
| KVUE | DividendsPerShare | 7 | 19 | 37% |
| MNST | DividendsPerShare | 0 | 70 | 0% |
| MNST | LongTermDebt | 5 | 70 | 7% |
| STZ | SharesOutstanding | 0 | 72 | 0% |
| STZ | DividendsPerShare | 0 | 72 | 0% |
| SYY | DepreciationAndAmortization | 35 | 73 | 48% |
| TGT | Goodwill | 17 | 74 | 23% |
| TGT | CashAndEquivalents | 18 | 74 | 24% |
| TSN | DividendsPerShare | 0 | 75 | 0% |

### DividendsPerShare non-payer check — done per-ticker, not assumed

Six tickers show 0% or thin `DividendsPerShare` coverage. Checked each individually rather than
excluding by reputation:

| Ticker | Has any per-share dividend tag? | Verdict |
|---|---|---|
| DLTR | No (`explore_tags.py DLTR dividendspershare` → no hits) | **Genuine non-payer** — Dollar Tree has never paid a dividend. Confirmed, not a gap. |
| MNST | No (same check, no hits) | **Genuine non-payer** — Monster Beverage's long-standing no-dividend policy. Confirmed. |
| HSY | Yes, `CommonStockDividendsPerShareCashPaid`, but only 10 points, all 2008–2010 | **Real payer, tag abandoned.** Nothing later exists under any per-share tag. Structural, see Step 3. |
| TSN | No per-share tag at all, only dollar-total tags (`PaymentsOfDividendsCommonStock`) | **Real payer, never tagged per-share.** Structural. |
| KVUE | Yes, `CommonStockDividendsPerShareCashPaid`, continuous from initiation | **Real payer, tag correct.** Low ratio is a young company (2023 spinoff) with a short history, not a gap. |
| STZ | No per-share tag, and also no shares-outstanding tag of any kind | **Real payer, structural — see below.** |

## Step 2 — Are COST, TGT, WMT, DG, DLTR, KR secretly retail?

Tested `retail`'s exact four working-capital tags (`Inventory`, `CostOfRevenue`,
`AccountsReceivable`, `AccountsPayable`) against all six, without reassigning anyone — this is a
taxonomy call for a human, not something changed here.

| Ticker | Inventory | CostOfRevenue | AccountsReceivable | AccountsPayable |
|---|---:|---:|---:|---:|
| COST | 96% | 100% | 96% | 96% |
| TGT | 101% | 90% | 0% | 101% |
| WMT | 101% | 100% | 101% | 101% |
| DG | 95% | 100% | 0% | 95% |
| DLTR | **0%** | 97% | 3% | 99% |
| KR | **6%** | 60% | ~100%¹ | ~100%¹ |

¹ KR's AR/AP ratios above 100% against the naive revenue-quarter denominator used for this check
are an artifact of KR's own cash-flow disclosure gap (see below) undercounting the denominator —
AR/AP are point-in-time balance-sheet facts and aren't affected by it; the true coverage is close
to complete.

**Recommendation** (findings only — `consumer_staples` assignment left unchanged for all six):

- **COST, WMT** — as clean a fit for `retail`'s current concept set as any of the 19 already-built
  `retail` tickers. No caveats.
- **TGT, DG** — clean fit modulo `AccountsReceivable` at 0%, which matches the already-established
  "pure consumer checkout, no trade receivable line" exception confirmed for several `retail`
  tickers in the prior scan (ORLY, AZO, ROST, TJX, ULTA, WSM). Not a gap, an expected pattern.
- **DLTR** — `CostOfRevenue`/`AccountsPayable` clean, `AccountsReceivable` near-zero (same expected
  pattern), but `Inventory` reads 0% under `retail`'s current tags. DLTR's actual inventory tag is
  `RetailRelatedInventoryMerchandise` (180 raw points, smooth $741M→$2.5B growth over 17 years) —
  not currently in `retail`'s candidate list. If reassigned, `retail` itself would need this tag
  added first; noted here, not acted on (out of scope for this task).
- **KR** — genuinely doesn't fit cleanly, for two independent, Kroger-specific reasons (both
  detailed below): its inventory is disclosed on a FIFO basis with a separate LIFO reserve, which
  the current `Inventory` concept model can't cleanly absorb; and its cash-flow-statement items are
  never tagged for Q1 in any given fiscal year, a gap no tag search fixes. Of the six, this is the
  one where "resembles retail's working-capital dynamics" and "fits the pipeline's current concept
  model" genuinely diverge.

### Trap found: FIFOInventoryAmount looks like a fix and isn't

KR's `Inventory` via `retail`'s tags: 6%. The obvious next candidate, `FIFOInventoryAmount`, has
excellent raw coverage (140 points) — but it measures a different number. Kroger's balance-sheet
inventory is carried at LIFO (lower than FIFO), with the LIFO reserve tagged separately
(`InventoryLIFOReserve`). Verified exactly at three overlap dates:

```
2010-01-30   FIFO = $5,705M   LIFOReserve = $770M   FIFO − Reserve = $4,935M = InventoryNet (exact)
2010-08-14   FIFO = $5,447M   LIFOReserve = $797M   FIFO − Reserve = $4,650M = InventoryNet (exact)
2010-11-06   FIFO = $6,065M   LIFOReserve = $809M   FIFO − Reserve = $5,256M = InventoryNet (exact)
```

The reserve is material (~14–16% of the FIFO figure). Using `FIFOInventoryAmount` as a fallback tag
would silently overstate KR's inventory by that much whenever it kicked in. The pipeline's `"sum"`
source type only adds tags together — there's no subtraction primitive to compose `FIFO − Reserve`
cleanly as a single concept source. **Not added.** This is the batch's named trap (task explicitly
invited flagging one): a tag with excellent coverage and a plausible-sounding name can still be
measuring an entirely different economic figure. Same family as the fair-value-vs-carrying-value
rejection rule already in place, new concrete instance.

### KR's second issue: no Q1 cash-flow disclosure, in any fiscal year

Traced `Capex`/`OperatingCashFlow`'s 47% to the raw filings rather than treating it as an
unexplained gap. Every fiscal year, KR's cash-flow tags start at a ~16-week cumulative duration
(not ~13 weeks) — there is no Q1-alone or Q1-cumulative fact anywhere in the company-facts history
for these concepts. `decumulate_period_values` can only recover one real discrete quarter per year
from that shape (H1-minus-nothing isn't computable, but 9-months-minus-H1 is), and its Q4-backsolve
needs three preceding quarters within the same year, which never exist. No alternate tag fixes
this — Kroger's own interim filings simply never include a Q1 cash-flow-statement figure for these
lines. Confirmed structural, not a tag gap.

## Step 3 — Candidate search for the remaining flagged concepts

### Fixed: TGT's CashAndEquivalents (and, as a side effect, seven other tickers')

TGT's `CashAndCashEquivalentsAtCarryingValue` data stops after FY2019. The successor tag,
`CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents`, is the market-wide
post-ASU-2016-18 replacement (folds restricted cash into the same reconciliation line; adopted
broadly across filers starting ~2018–2019). Checked for a magnitude trap before trusting it: at
every one of the three dates where TGT's old and new tags overlap, the values are **exactly
identical** — TGT's restricted cash is $0, so this is a safe like-for-like replacement here, not a
different economic figure with extra content folded in.

Added as a third fallback tag on a new `consumer_staples`-scoped `CashAndEquivalents` override
(the profile previously had no overrides at all).

### Everything else: genuinely structural, confirmed rather than assumed

No other flagged concept had a clean tag-search fix. Each was traced to the raw filing data, not
left as an unexplained low percentage:

- **ADM, BG, CASY, CLX — OperatingIncomeLoss (0% each).** Full `*income*`/`*operating*` tag dumps
  for all four show `OperatingIncomeLoss` was never tagged, by any of them, ever. Same pattern as
  NKE from the prior retail scan (income statement goes straight from expenses to pretax income,
  no discrete operating-income subtotal) — now confirmed in four more filers, making it a
  recurring, not isolated, pattern worth naming for future batches.
- **STZ — SharesOutstanding and DividendsPerShare (0% each).** No shares-outstanding tag of any
  kind (`WeightedAverageNumberOf*`, `CommonStockSharesOutstanding`), no `EarningsPerShareBasic`/
  `Diluted`, no per-share dividend tag — anywhere in the company-facts dump. Constellation Brands'
  Class A/Class B dual-class structure is the likely explanation: such filers often tag per-share
  and share-count facts only with a `ClassOfStockAxis` dimension, and SEC's `companyfacts` endpoint
  only surfaces non-dimensional (default-member) facts. This pipeline doesn't consume dimensional
  facts at all, so there's no fix available inside its current design — logged as structural, not
  forced.
- **HSY, TSN — DividendsPerShare (8%, 0%).** Both real, established dividend payers. HSY's
  `CommonStockDividendsPerShareCashPaid` has exactly 10 points, all from 2008–2010, then nothing
  ever again; TSN has no per-share tag at all, only aggregate-dollar tags. Per-share dividend
  disclosure isn't a required primary-statement XBRL element in the way EPS is — some filers simply
  never tag it, or stop.
- **KVUE — DividendsPerShare (37%).** Not a gap. Existing tag already used correctly; low ratio is
  explained entirely by KVUE's short trading history (2023 J&J spinoff, dividend initiated shortly
  after) — the full 13-point series is continuous and complete from initiation onward.
- **MNST — LongTermDebt (7%).** Monster Beverage was genuinely debt-free for nearly all of its
  public history — the tag reads a literal `$0` at 2023-12-31, with real debt appearing only from
  mid-2024. Same "no debt is not a bug" pattern already documented for GRMN/LULU in the retail
  scan.
- **COST, TGT — Goodwill (16%, 23%).** Both tag `Goodwill` at fiscal year-end only, never in an
  interim 10-Q, across their entire history (TGT: exactly one date per year, 2010–2026, no
  exceptions). A stable, permanent filer choice, not a transition or a data gap.
- **SYY — DepreciationAndAmortization (48%).** SYY tagged full quarterly D&A from FY2010–FY2015,
  then **every D&A-related tag goes annual-only for nine straight fiscal years (FY2016–FY2024)**,
  before quarterly tagging resumes in FY2025. Checked across all six candidate tags in the concept's
  `priority_merge` sources, not just the primary one — the gap is total, not a single-tag artifact.
  No fix possible; the underlying quarterly disclosure wasn't made during that window. Worth naming
  as the mirror image of the "ROST/LOW/WSM all started tagging at once" pattern from the retail
  scan: a filer that stopped, then years later resumed, tagging the same concept.

## Step 4 — Mode decisions

One change, applied with the standard two-step discipline:

- **Stage B1**: copied the base `CashAndEquivalents` tag list unchanged into a new
  `consumer_staples` override. Verified byte-identical across the full 178-ticker cached universe
  (0 changed, 0 removed, 0 new fills).
- **Stage B2**: appended `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` as a third
  fallback tag. Re-verified: 0 changed, 0 removed, 154 new fills.

No `fallback`/`priority_merge` migration was needed elsewhere — every other flagged concept was
confirmed structural (Step 3) rather than fixable by a tag or mode change.

## Step 5 — Non-regression check

Extracted every concept for all 178 cached tickers (every profile, KO included) under the config
before and after the `CashAndEquivalents` change — the only concept touched this session.

```
changed: 0
removed: 0
new fills: 154
```

All 154 new fills landed on `consumer_staples` tickers only (profile-scoped override, as
designed): TGT (+32), EL (+31), HSY (+27), SJM (+27), PG (+26), KDP (+5), KVUE (+5), BG (+1) — 8
tickers total. Zero impact on any ticker outside `consumer_staples`, and zero impact on any concept
other than `CashAndEquivalents`.

## Step 6 — Coverage re-check

| Ticker | Concept | Before | After |
|---|---|---:|---:|
| ADM | OperatingIncomeLoss | 0/73 (0%) | 0/73 (0%) — unchanged, structural |
| BG | OperatingIncomeLoss | 0/17 (0%) | 0/17 (0%) — unchanged, structural |
| CASY | OperatingIncomeLoss | 0/70 (0%) | 0/70 (0%) — unchanged, structural |
| CLX | OperatingIncomeLoss | 0/73 (0%) | 0/73 (0%) — unchanged, structural |
| COST | Goodwill | 12/74 (16%) | 12/74 (16%) — unchanged, structural |
| DLTR | DividendsPerShare | 0/70 (0%) | 0/70 (0%) — unchanged, confirmed non-payer |
| HSY | DividendsPerShare | 6/72 (8%) | 6/76 (8%) — unchanged, structural |
| KR | Capex | 35/74 (47%) | 35/74 (47%) — unchanged, structural |
| KR | OperatingCashFlow | 35/74 (47%) | 35/74 (47%) — unchanged, structural |
| KVUE | DividendsPerShare | 7/19 (37%) | 7/20 (35%) — unchanged, explained (young company) |
| MNST | DividendsPerShare | 0/70 (0%) | 0/70 (0%) — unchanged, confirmed non-payer |
| MNST | LongTermDebt | 5/70 (7%) | 5/70 (7%) — unchanged, confirmed genuine (no debt) |
| STZ | SharesOutstanding | 0/72 (0%) | 0/72 (0%) — unchanged, structural |
| STZ | DividendsPerShare | 0/72 (0%) | 0/72 (0%) — unchanged, structural |
| SYY | DepreciationAndAmortization | 35/73 (48%) | 35/73 (48%) — unchanged, structural |
| **TGT** | **CashAndEquivalents** | **18/74 (24%)** | **50/74 (68%)** — **resolved** |
| TGT | Goodwill | 17/74 (23%) | 17/74 (23%) — unchanged, structural |
| TSN | DividendsPerShare | 0/75 (0%) | 0/75 (0%) — unchanged, structural |

### Summary

- **Fully resolved**: 1 — TGT `CashAndEquivalents` (24% → 68%), plus material collateral
  improvement on 7 other tickers' `CashAndEquivalents` coverage that weren't individually flagged.
- **Improved but not clean**: 0.
- **Unchanged, confirmed structural or already-explained**: 16 (ticker, concept) pairs — 4
  never-tagged `OperatingIncomeLoss`, 2 annual-only `Goodwill`, 1 nine-year quarterly-tagging gap
  (SYY D&A), 1 dual-class-structure gap (STZ, two concepts), 2 abandoned-tag dividend gaps (HSY,
  TSN), 2 confirmed-genuine economic facts (DLTR/MNST non-payer/no-debt), 1 explained-by-history
  case (KVUE), 2 Kroger-specific disclosure gaps (Capex/OCF) — every single one traced to raw
  filing data and explained, none left as a bare percentage.

No scratch scripts were left behind. No ticker outside the 34 `consumer_staples` tickers was
touched, no ticker's profile assignment was changed, and no concept unrelated to
`consumer_staples`'s metric set was modified.
