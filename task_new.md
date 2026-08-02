# Task: Documentation Catch-Up + Five Improvements from SoFi Analysis

Two independent workstreams. Part 0 is documentation-only (no code changes). Parts 1-5 are
five real improvements identified while analyzing SOFI. **Standing requirement as always:
nothing may regress. Non-regression after each part.**

---

## PART 0 — Catch up `bugfixed_update_history.md`

### Step 0.1 — Find the gap

Read `bugfixed_update_history.md` and identify its **last entry** (date and content). Then
determine everything that has actually changed in the codebase since that entry — check
whether prior tasks' own "add an entry" instructions were actually followed (several recent
tasks included that instruction; some entries may already be present). Build a list of what's
documented versus what's missing, don't assume either way.

### Step 0.2 — Reconstruct what happened, from the actual code and reports

For anything missing, reconstruct it accurately — from the real diffs/current code state and
the task reports already produced (`quarterly_and_growth_expansion_report.md`,
`valuation_history_coupling_fix_report.md`, `valuation_guard_and_ticker_fixes_report.md`,
`meta_fetch_and_related_fixes_report.md`, `fetch_ttl_implementation_report.md`,
`fetch_ttl_full_universe_validation_report.md`, `valuation_quality_improvements_report.md`,
`nine_improvements_report.md`, if all are available — check what actually exists), not from
memory of what was *intended*. Write each missing entry in the same style/format as the
existing history file (check the existing entries' format and match it exactly).

At minimum, confirm coverage of: the quarterly-values-alongside-TTM addition, the growth
columns on `quarterly_facts`, the `calculate_growth` date-alignment fix, the
`build_valuation_history` market-cap coupling fix, the `MAX_MULTIPLE` removal and
`MIN_DENOMINATOR_SCALE_RATIO` recalibration, the three ticker data-bug fixes (WAT partial,
ANET/SCHW/ED DEF-14A fix), the META fetch/staleness findings, the `fetch_or_cache` TTL
mechanism, the buyback-distortion flag + `tangible_book`, the harmonic-mean `avg_X_5y` +
median, the share-count source transparency fields, `ev_fcf`, and the nine-improvements batch
(symmetric share-count resolution, `history_too_short`, `fcf_exceeds_ebitda`, `sbc_ttm`/
`owner_fcf`/`pfcf_ex_sbc`, `historical_band_elevated`, `inorganic_contaminated`,
`effective_tax_rate`/`low_tax_rate_flag`) — but don't stop at this list if you find something
else changed that isn't on it.

### Step 0.3 — Verify against the file itself, not just your own list

After writing the entries, re-read the full updated file once more and confirm entries are in
correct chronological order, don't duplicate anything already present, and don't contradict
an existing entry.

---

## PART 1 — `share_count_jump_flag`: treat the jump as an edge event, invalidate both quarters

### Context

The flag currently attaches to a single quarter (whichever side of the QoQ comparison the
existing code marks). Found during a SOFI analysis: **a bad value at one edge of a jump still
enters any rolling average/historical band that includes it**, biasing the comparison
optimistic (or pessimistic) even though the flag exists. A jump is a discontinuity *between*
two quarters, not a property of one of them — both need to be treated as suspect for
aggregation purposes.

### Step 1.1 — Confirm current behavior

Check exactly which quarter the flag currently attaches to, and confirm (with a real example,
e.g. SOFI's own case if it shows this pattern) that the *other* side of the jump still
contributes normally to any rolling mean/median/band calculation.

### Step 1.2 — Extend to both adjacent quarters

Mark both quarters bracketing a flagged jump. Then trace which downstream aggregates actually
consume `SharesOutstanding`-derived quantities in a rolling/averaged way (the `avg_X_5y`
harmonic-mean/median fields from the recent task, `historical_band_elevated`'s peer/self
comparisons, anything else) and exclude both flagged quarters from those specific
calculations — not just display the flag without changing what feeds the average, since that
was the whole point of the finding.

Decide precisely what "invalidate" means for point-in-time metrics that use the same
underlying share count directly (`market_cap`, `pe_ratio`, `pb_ratio`, etc., for that single
quarter) — should the metric itself still show for that quarter (since the value may be
correct even if the QoQ delta looks abrupt) or also get masked? State the reasoning; don't
silently pick one.

### Step 1.3 — Verify against SOFI

Confirm SOFI's own flagged jump now correctly excludes both bracketing quarters from its
rolling-average calculations, and report the before/after average value to show the bias
correction is real, not just structural.

### Step 1.4 — Non-regression

Confirm only genuinely-flagged-jump periods change in the affected rolling calculations, and
report the full list.

---

## PART 2 — `shares_basis` label

### Context

Without knowing whether a resolved `SharesOutstanding` value is a period-end balance-sheet
count or a weighted-average-diluted (income-statement-style) count, `shares_delta_pct` against
yfinance (which reports a current, period-end-style count) isn't interpretable — a 6.8% delta
could be a bug or just this definitional difference. Confirmed for SOFI: it's the latter.

### Step 2.1 — Classify the actual tag behind each ticker's resolved value

For every ticker's currently-resolved `SharesOutstanding` source tag, determine whether it's a
period-end concept (e.g. `CommonStockSharesOutstanding`, `EntityCommonStockSharesOutstanding`)
or a weighted-average/diluted concept (e.g. `WeightedAverageNumberOfDilutedSharesOutstanding`,
`WeightedAverageNumberOfSharesOutstandingBasic`). Report the full distribution across all 498
active tickers — this may reveal the definitional-difference explanation applies more broadly
than just SOFI.

### Step 2.2 — Implement

Add a `shares_basis` field (`period_end` / `diluted_wavg`, or whatever clean categorical
labels fit what Step 2.1 actually finds) alongside the existing share-count fields.

### Step 2.3 — Non-regression

Purely additive — confirm no existing value changes.

---

## PART 3 — `filing_likely_overdue`: predict before the submissions index shows anything

### Context

This is different from the existing `fundamentals_stale` guard, which reacts to the
submissions index already showing a newer filing than what's cached. This flag should predict
*ahead* of that — based on each company's own historical filing cadence, whether a report is
likely overdue even before any external signal confirms it.

### Step 3.1 — Establish each ticker's typical filing lag

From each ticker's own filing history (already available via the submissions data used
elsewhere in this project), compute the typical number of days between a fiscal period end and
the corresponding filing's acceptance date. Use a per-ticker figure (median of that ticker's
own history), not a single global constant — filing lag varies by company (accelerated vs.
non-accelerated filer status, for instance).

### Step 3.2 — Implement the flag

`filing_likely_overdue = True` when: today's date exceeds (most recent known fiscal
period-end + that ticker's typical lag + a reasonable buffer), **and** no newer filing has
yet appeared in either the submissions index or `companyfacts`. Calibrate the buffer from real
data (how much does a ticker's own filing lag actually vary quarter to quarter — the buffer
should cover normal variance, not be an arbitrary round number).

### Step 3.3 — Verify

Confirm this flag would have caught META's case *before* the 10-Q was actually filed (i.e.
reconstruct the timeline and check whether the flag would have fired in the days leading up
to the actual filing, based purely on META's historical cadence) — this is the predictive
case the flag is meant to cover, distinct from `fundamentals_stale`'s reactive one.

### Step 3.4 — Non-regression

Purely additive.

---

## PART 4 — `fair_value_marks_to_tbv` for the `financial` profile

### Context

`CumulativeFairValueAdjustments / TangibleEquity` — a measure of how much of a bank's tangible
book value reflects unrealized fair-value marks (e.g. on available-for-sale securities) rather
than retained operating earnings. SOFI's is 21.4% per the motivating analysis — a real
differentiator this project doesn't currently expose.

### Step 4.1 — Check tag availability before assuming the name is real

**Do not assume `CumulativeFairValueAdjustments` is a standard, directly-usable tag** — check
directly against real `financial`-profile tickers' raw facts. It's plausible the actual
underlying data lives in AOCI (accumulated other comprehensive income) components — e.g. an
available-for-sale-securities fair-value-adjustment line within
`AccumulatedOtherComprehensiveIncomeLossNetOfTax`'s breakdown, under some other tag name
entirely. Investigate SOFI's own filings specifically first (to confirm how its 21.4% figure
was actually derived/named), then check coverage across the rest of the `financial` profile.

### Step 4.2 — Implement based on what's actually there

Build the metric from whatever tag(s) Step 4.1 confirms are real and reasonably available
across the profile. If coverage is patchy, report exactly how patchy (same discipline as the
recent SBC-tag check) and decide whether it's still worth shipping with real gaps or better
held for later.

### Step 4.3 — Verify and non-regress

Confirm SOFI reproduces ~21.4% (or close, and if not, explain the discrepancy rather than
forcing a match). Purely additive.

---

## PART 5 — `ROTCE` alongside `roe`

### Context

Return on Tangible Common Equity (`NetIncomeLoss_TTM / TangibleEquity`, using the already-
existing `TangibleEquity` concept from the `p_tbv` work) is the natural partner to `p_tbv` for
banks with meaningful goodwill, where plain `roe` (using full equity) understates true returns
on the tangible capital base.

### Step 5.1 — Implement

Add `rotce = NetIncomeLoss_TTM / TangibleEquity`, guarded the same way `roe` already is
(the existing near-zero/negative-equity guards, applied to `TangibleEquity` instead of full
`StockholdersEquity`). Decide scope: `financial` profile only, or does it make sense for
`insurance_pc`/`insurance_life` too (they also have `p_tbv`)? Check briefly and report the
reasoning rather than assuming financial-only.

### Step 5.2 — The scatter-plot idea: report, don't build

The report suggested a `p_tbv` vs. `rotce` scatter plot across all `financial`-profile tickers
as a strong feature for the future web app. **Do not build this chart in this task** — this
project's current output is per-ticker matplotlib figures, not a cross-sectional web
visualization; that's explicitly future scope. Just confirm the two underlying values
(`p_tbv`, `rotce`) are both cleanly available per ticker so such a chart is straightforward to
build later, and note this in the report.

### Step 5.3 — Non-regression

Purely additive.

---

## Final combined non-regression

Full-universe before/after across `metrics_long`, `valuation_history`, and `snapshot` for
Parts 1-5 combined. Confirm every change traces to a specific part, and Part 1's behavioral
change (excluding flagged quarters from rolling aggregates) doesn't leak into any other
metric's calculation.

## Output

One file, `sofi_driven_improvements_report.md`, covering Parts 1-5 (each with investigation,
implementation or documented non-implementation, verification, and non-regression). Part 0's
output is the updated `bugfixed_update_history.md` itself — confirm in this report what was
added to it and why.

No scratch scripts left behind.