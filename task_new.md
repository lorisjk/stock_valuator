# Task: Nine Data-Quality/Metric Improvements from External Review

Nine independent items, each investigated against real cached data before implementing.
**Explicit permission and instruction, per the project owner's own framing: implement what
works cleanly with this project's real data; for anything that doesn't, report exactly why
and leave it undone rather than forcing an approximation.** This is not a soft suggestion —
treat "confirmed infeasible, here's why" as a fully successful outcome for that item, the same
way REIT's AFFO/NAV or Same-Store-Sales were correctly left unbuilt elsewhere in this project.

**Standing requirement as always: nothing may regress. Non-regression after each part.**

---

## PART 1 — Extend the share-count resolution to catch large *negative* deltas (KLAC/CRWD/DVN)

### Context

The existing dual-class/stale-share resolution only switches to EDGAR when
`edgar/yfinance > 1.10` (EDGAR larger). KLAC, CRWD, and DVN show the opposite: yfinance
overstates by 9.9x, 4.0x, and 1.9x respectively (confirmed in the prior task's `shares_delta_pct`
scan) — `market_cap` and everything derived from it is very likely wrong for these three right
now.

### Step 1.1 — Scope-check before fixing

Using the already-built `shares_delta_pct` field, check the full distribution of *negative*
deltas (yfinance larger than EDGAR) across all 498 active tickers, not just the three named.
Report the full list of tickers beyond some reasonable cutoff — don't assume KLAC/CRWD/DVN are
the only ones.

### Step 1.2 — Design and implement the symmetric extension

Extend the resolution rule to also prefer EDGAR when `yfinance/edgar` exceeds a threshold in
the same spirit as the existing `1.10`, calibrated from where the real negative-delta
distribution actually separates "real dual-class disagreement" from "normal small drift" —
don't just reuse `1.10` inverted without checking it fits this direction too.

### Step 1.3 — Verify and non-regress

Confirm KLAC/CRWD/DVN's `market_cap`-derived metrics are now sane (compare before/after
`pe_ratio`/`pb_ratio`/`ev_ebitda` against each company's real known scale). Full-universe
non-regression: only tickers flagged in 1.1 should change.

---

## PART 2 — `debt_inferred_zero`: infer zero debt only where the evidence actually supports it

### Context

A ticker with `Liabilities`/`StockholdersEquity` present but no `LongTermDebt` tag at all
currently blocks the entire EV family. Some of these are genuinely debt-free (this project has
already independently confirmed real zero-debt cases: GRMN, LULU, DECK — each verified through
tag-level investigation, not assumed). The request is to generalize this into an automatic
"debt = 0, flagged" inference — but this must not be done blindly, since "no debt tag" can also
just mean "untagged," not "actually zero."

### Step 2.1 — Investigate before generalizing

For every currently-active ticker with 0% `LongTermDebt` coverage, check for corroborating
evidence of genuine zero debt — e.g. a `Liabilities` breakdown that doesn't leave room for debt,
or a debt-adjacent flow tag (`RepaymentsOfDebt`, `ProceedsFromIssuanceOfDebt`) that's also
completely absent (consistent with never having debt, versus present-but-the-balance-tag-missing,
which would suggest a real balance exists but isn't tagged). Report, per ticker, which case
applies.

### Step 2.2 — Implement only where safe

If a reasonably reliable evidentiary pattern emerges (e.g. "no debt tag AND no debt-flow tags
at all" reliably means real zero, verified against the already-confirmed GRMN/LULU/DECK cases
as a sanity check), implement `debt_inferred_zero` as a flagged, zero-valued `LongTermDebt`
for tickers matching that pattern. If the evidence is mixed or unreliable for a meaningful
share of candidates, **do not implement a blanket rule** — report the findings and, if useful,
suggest which specific tickers could get a `TICKER_CONCEPT_OVERRIDES`-style individual
treatment instead (the same targeted-over-generic principle used for `_KNOWN_BAD_FACTS`
throughout this project).

### Step 2.3 — Non-regression

If implemented: confirm only tickers matching the verified pattern change, and confirm the
already-known-debt-free tickers (GRMN, LULU, DECK) are handled consistently with how they're
already documented.

---

## PART 3 — Dual-class share count: sum across classes instead of picking one

### Context

The current `SharesOutstanding` resolution picks one tag/class rather than summing all
outstanding share classes (`CommonStockSharesOutstanding` reported per-class for companies
like META, GOOGL, BRK, FOX). This is a different failure mode from Parts 1/2 — not a wrong
source, but an incomplete one.

### Step 3.1 — Investigate the real tag structure

For META, GOOGL, BRK, FOX/FOXA, and RDDT specifically, pull the raw share-count tags and
determine whether each class is tagged separately (e.g. `CommonClassACommonStockSharesOutstanding`,
`CommonClassBCommonStockSharesOutstanding`) in a way that can be reliably summed, or whether the
tagging is inconsistent enough (missing classes in some periods, dimensional facts that don't
resolve cleanly) that summing would itself introduce error. Report per ticker.

### Step 3.2 — Implement where the tags support it cleanly

Where summing is reliable, implement it (a `PROFILE_CONCEPT_OVERRIDES`/base-concept change
depending on how broad the pattern turns out to be — decide from Step 3.1's evidence, not
before it). Where it isn't reliable for a given ticker, leave that ticker on the existing
single-source resolution and say so explicitly.

### Step 3.3 — The QoQ share-count guard (>15% without a corroborating event)

Add a check: flag (don't necessarily mask, this is informational the same way
`buyback_distortion_flag` is) any ticker/period where `SharesOutstanding` changes >15%
quarter-over-quarter with no corroborating buyback (`PaymentsForRepurchaseOfCommonStock`) or
issuance (`ProceedsFromIssuanceOfCommonStock`) event of comparable magnitude in the same
period. Calibrate the 15% threshold against real data the same way every other guard in this
project has been calibrated — check whether RDDT, META, GOOGL, BRK actually clear this bar,
rather than assuming they do because the report claimed it.

### Step 3.4 — Non-regression

Full-universe check for both 3.2 and 3.3's changes.

---

## PART 4 — `history_too_short` flag

### Context

The rolling 5-year average fields (`avg_pe_5y` and its six siblings, from the recent harmonic-
mean task) compute a formally valid number even when a ticker has very few actual quarters of
history (e.g. RDDT, recently IPO'd) — the number exists but isn't meaningful.

### Step 4.1 — Implement

Flag any `avg_X_5y`/`_median` field where the underlying window had fewer than ~12 valid
(non-masked) quarters — calibrate the exact cutoff if the evidence suggests 12 isn't quite
right, but it's a reasonable starting hypothesis. Verify RDDT is correctly flagged.

### Step 4.2 — Non-regression

Purely additive (new flag field per existing `avg_X_5y` field) — confirm no existing value
changes.

---

## PART 5 — `FCF_TTM > EBITDA_TTM` flag

### Context

When trailing FCF exceeds EBITDA, that's a signal worth surfacing — it usually means non-cash
add-backs (stock-based compensation being the most common) or working-capital swings are
inflating cash generation beyond what the operating result alone would suggest.

### Step 5.1 — Investigate before asserting a cause

Check NOW specifically (named in the report) and a handful of other tickers where this
condition holds. **Don't assume the cause is stock-based compensation without checking** —
verify whether SBC add-backs, working-capital changes, or something else is actually driving
the gap in each case, since a flag that always says "SBC-driven" would be wrong whenever the
real driver is something else (e.g. a large deferred-revenue build in a subscription business).

### Step 5.2 — Implement as a flag, named accurately

Based on 5.1's findings, implement the flag with a name/description that matches what's
actually verified, not a presumed cause — e.g. a neutral `fcf_exceeds_ebitda` flag, with the
SBC hypothesis only asserted where it's actually confirmed to be the driver for that ticker
(if that's feasible to check cheaply; if not, keep the flag purely descriptive).

### Step 5.3 — Non-regression

Purely additive.

---

## PART 6 — `sbc_ttm`, `owner_fcf`, `pfcf_ex_sbc`

### Step 6.1 — Check tag availability before building anything

Search for a usable `ShareBasedCompensation`-style cash-flow-statement tag across a sample of
tickers spanning several profiles (not just software names) — confirm how broadly and
reliably it's tagged before committing to build derived metrics on top of it.

### Step 6.2 — Implement if the evidence supports it

If broadly available: add `sbc_ttm` as a TTM concept, `owner_fcf = FCF_TTM - sbc_ttm`, and
`pfcf_ex_sbc = market_cap / owner_fcf` (guarded the same way `pfcf_ratio` already is). If
coverage is patchy, report exactly how patchy and let that inform whether it's worth shipping
as-is (with real gaps) or holding for a future task.

### Step 6.3 — Verify and non-regress

Verify against a real software ticker (NOW, CRM, or similar) that `pfcf_ex_sbc` tells a
meaningfully different story than `pfcf_ratio` — report both side by side.

---

## PART 7 — `historical_band_elevated`: percentile context relative to peers

### Context

This is the most architecturally novel item — nothing in this project currently computes a
cross-sectional peer comparison (every existing guard/flag is about a single ticker's own
history). This needs a design step before implementation.

### Step 7.1 — Design

Propose how "peer" is defined (the existing `PROFILE_HIDDEN`/`TICKER_PROFILES` assignment is
the natural candidate — a ticker's peers are its profile-mates) and how the sector median is
computed (same-period cross-sectional median across the profile, or each peer's own 5-year
average, aggregated). State the reasoning, since this is a real design choice, not a detail.

### Step 7.2 — Implement, or report why not

If a clean, low-risk implementation path exists within this task's scope, build it as a flag:
when a ticker's own 5-year minimum for a multiple is still above the profile's cross-sectional
median for that multiple, flag that "near its own historical low" isn't a value signal for
this ticker right now. If this turns out to need more architecture than fits cleanly here
(e.g. because cross-sectional data isn't readily available in the right shape), report that
clearly rather than forcing a partial version.

### Step 7.3 — Non-regression

If implemented: purely additive, confirm no existing value changes.

---

## PART 8 — Goodwill-delta flag (`inorganic_contaminated`)

### Step 8.1 — Implement

Mirror the `buyback_distortion_flag` mechanism: flag periods where `Goodwill` grows >20%
quarter-over-quarter (calibrate if the evidence suggests otherwise), marking growth-rate
metrics computed across that period as potentially inorganic-contaminated (M&A-driven rather
than organic). Verify NOW and CRM (named in the report) both get flagged where expected.

### Step 8.2 — Non-regression

Purely additive, same discipline as Part 1 of the buyback-flag task.

---

## PART 9 — Effective tax rate + NOL flag

### Step 9.1 — Implement

`effective_tax_rate = IncomeTaxExpenseBenefit_TTM / IncomeLossBeforeIncomeTaxes_TTM` (confirm
both tags' actual availability before assuming — check coverage across a sample of profiles).
Flag when the rate is below ~10% (calibrate if evidence suggests a different cutoff), as a
signal of NOL-driven or otherwise abnormally low tax expense, common for recently-profitable
young companies.

### Step 9.2 — Verify and non-regress

Verify against at least one recently-profitable young company (a `marketplace` or `standard`
tech name, if a good real example exists in the cache). Purely additive.

---

## Final combined non-regression

After all nine parts (or however many end up implemented — some may be correctly left as
"investigated, not safely implementable"), run one full-universe before/after diff across
`metrics_long`, `valuation_history`, and `snapshot`. Confirm every change/addition traces to a
specific part, and nothing implemented in an earlier part was disturbed by a later one.

## Output

One file, `nine_improvements_report.md`, one section per part, each stating clearly:
investigated, implemented (with verification), or **confirmed not safely implementable with
this project's real data (with the specific evidence for why)**. Treat the third outcome as a
complete, successful answer for that part — do not force any of the nine to a lower-quality
implementation just to have shipped something.

No scratch scripts left behind.