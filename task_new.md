# Task: Buyback-Distortion Flag + Harmonic-Mean P/E Average + Share-Count Transparency + `ev_fcf`

Four independent improvements to valuation quality. Each gets its own investigation, fix, and
non-regression check. **Standing requirement as always: nothing may regress.**

---

## PART 1 — Buyback-distortion flag + tangible book value

### Context

A company running aggressive buybacks can shrink `StockholdersEquity` sharply quarter over
quarter while remaining profitable — `pb_ratio` and `roe` become distorted in exactly the way
already documented for ORLY/AZO/MCD (a small-but-positive or negative equity base against a
normal numerator). The existing equity guards catch the extreme (near-zero/negative) cases;
this adds a softer, earlier signal: flag it before the guard has to mask anything outright.

### Step 1.1 — Detect the pattern

Add a check: `StockholdersEquity` QoQ decline of more than ~15-20% **combined with** positive
`NetIncomeLoss_TTM` in the same period (the combination matters — a declining equity base
alongside real losses is a different, already-understood story; this flag is specifically for
"profitable company shrinking its own equity base via buybacks"). Calibrate the exact
threshold from real data (the same marginal-return method used for every prior guard in this
project) rather than shipping 15% or 20% as a guess — check where confirmed buyback-heavy
names (ORLY, AZO, MCD, HD, LOW) actually sit and where the threshold cleanly separates them
from normal QoQ equity noise.

### Step 1.2 — Suppress or asterisk `pb_ratio`/`roe` when flagged

Decide between suppression (mask to NaN, consistent with how every other guard in this
project works) and an asterisk/flag column (keep the value visible but marked). Recommend
one, with reasoning — note that this project's established convention has consistently been
to mask rather than annotate (every guard so far hides the number rather than showing a
flagged version of it), so deviating from that here should be a deliberate, justified choice,
not a default.

### Step 1.3 — `tangible_book` field, and hide `pb_ratio` when negative

**Before implementing, check whether a usable "intangible assets" concept already exists** in
this project's extracted concepts (something like `IntangibleAssetsNetExcludingGoodwill` or
similar) — don't assume one is available. If a clean, broadly-available tag exists, build
`tangible_book = StockholdersEquity - Goodwill - Intangibles`. If no reliable intangibles
concept exists project-wide (check directly, the same tag-research discipline used
throughout this project — a spot-check across a handful of profiles, not just one ticker), a
documented simplification of `tangible_book = StockholdersEquity - Goodwill` (Goodwill alone,
already a base concept) is an acceptable fallback — this project already made an analogous
simplification for FFO (reusing generic `DepreciationAndAmortization` instead of building a
real-estate-specific tag). State clearly which version was built and why.

When `tangible_book` is negative, hide `pb_ratio` entirely for that ticker/period (a negative
tangible book value makes P/B on a tangible basis undefined, not just distorted) —
data-triggered visibility, the same class of mechanism as `PROFILE_HIDDEN` but triggered by a
computed value rather than a sector assignment. Note: `p_tbv` (price/tangible book value)
already exists in this codebase — check its current formula and confirm this new
`tangible_book` field is consistent with (or replaces) whatever `p_tbv` already computes,
rather than building a second, parallel, possibly-inconsistent version of the same idea.

### Step 1.4 — Non-regression for Part 1

Full-universe before/after. Report every newly-flagged/masked `(ticker, end)` pair for the
buyback-distortion signal and for the negative-`tangible_book` `pb_ratio` hide, separately.
Confirm no other value changes.

---

## PART 2 — `avg_pe_5y` should be a harmonic mean, not an arithmetic mean

### Context

The 5-year average reference line shown on valuation charts (`show_mean=True` in
`plot_metric`, currently `filtered["value"].mean()`) arithmetically averages the ratio itself.
For P/E specifically, this overweights periods where earnings approached zero (a near-zero
denominator inflates P/E toward infinity, and an arithmetic mean of the ratio is dominated by
those spikes). The statistically correct construction is the mean of the **earnings yield**
(1/P/E) across the window, inverted back to a P/E — the harmonic mean of the P/E series.

### Step 2.1 — Confirm scope

Find every place this project computes and displays an average-of-a-ratio reference line
(`show_mean=True` calls in `figures.py`, and any other place an average valuation multiple is
computed, e.g. a snapshot-level "5-year average P/E" field if one exists separately). Report
the full list — this may be broader than just the `pe_ratio` chart.

### Step 2.2 — Decide which multiples need the harmonic-mean fix

The user's report specifically names P/E; the same distortion is plausible for any multiple
whose denominator can approach zero (`pfcf_ratio` when FCF is thin, `ev_ebitda` when EBITDA
is thin). Check whether the same skew shows up materially for these too using real cached
data (compare the arithmetic vs. harmonic mean for a sample of tickers per multiple, look at
how much they diverge) before deciding scope — don't assume it generalizes, and don't assume
it's P/E-only either. Report the evidence either way.

### Step 2.3 — Implement

For each multiple in scope: compute the harmonic mean (`n / sum(1/x)`, excluding non-positive
values from the sum the same way the existing guards already exclude them elsewhere) instead
of the arithmetic mean, as the reference line value. **Also compute and emit the median**
alongside the harmonic mean (e.g. `avg_pe_5y_median` or the equivalent naming per multiple),
and flag when the mean and median diverge meaningfully (calibrate what counts as meaningful
from real data, don't guess a percentage).

### Step 2.4 — Verify against real cases

Confirm the fix changes the reference line sensibly for at least one ticker with a
known thin-earnings period in its 5-year window (check the actual before/after reference
value) and confirm a "normal", stable-earnings ticker's reference line barely moves (harmonic
and arithmetic mean should be close when the series doesn't have extreme low points).

### Step 2.5 — Non-regression for Part 2

Confirm every other chart/metric is unaffected — this only touches the reference-line
calculation for the multiples in scope. Report before/after reference values for every active
ticker for the affected multiple(s).

---

## PART 3 — Share-count consistency: explicit source tracking

### Context

The recent dual-class share-count fix (Part 2 of the META task) resolved *which* share count
`build_snapshot()`/`build_valuation_history()` use for `market_cap` versus `EPS_TTM_CALC`, but
did so silently — there's no visibility into which source won for a given ticker, or how far
apart the two sources actually sit even in already-resolved cases. This is the same failure
mode, applied more broadly: pick one count per snapshot for both `market_cap` and EPS, or make
the discrepancy visible if not.

### Step 3.1 — Add a `shares_source` column

For every ticker in the snapshot, record which source actually supplied the share count used
for `market_cap` (`edgar` or `yfinance`, matching whatever the Part 2 fix's resolution logic
actually decides) — a simple, auditable label, not a new resolution mechanism (that already
exists from the META task).

### Step 3.2 — Add a `shares_delta_pct` guard/field

Compute the percentage difference between the EDGAR share count (used for `EPS_TTM_CALC`) and
the yfinance share count (used for `market_cap` when they differ), for every ticker, not just
the ones already flagged as dual-class. Report the full distribution — this may surface
tickers with a real, meaningful discrepancy that weren't caught by the dual-class-specific
check, the same "scope-check broader than the named examples" discipline used throughout this
project.

Decide whether this should also drive a visibility decision (e.g. hide/flag `pe_ratio` or
`market_cap`-derived metrics when the delta exceeds some threshold) or remain purely
informational for now — report the evidence and recommend, consistent with how every other
structural finding in this project has been handled (report and let the project owner decide
if it's a bigger call).

### Step 3.3 — Non-regression for Part 3

Purely additive (new columns) — confirm no existing value changes.

---

## PART 4 — `ev_fcf`: a leverage-aware FCF multiple alongside `pfcf_ratio`

### Context

`pfcf_ratio` (price ÷ FCF) ignores capital structure — for a ticker whose net debt changes
sign or whose ND/EBITDA crosses a meaningful threshold, price-to-FCF alone can be misleading
in the same way P/E alone is misleading without also looking at EV/EBITDA. `ev_fcf` (Enterprise
Value ÷ FCF) is the capital-structure-aware counterpart, and it's cheap to add — `ev` and `fcf`
already exist as intermediate values in this codebase.

### Step 4.1 — Implement

Add `ev_fcf = ev / fcf` (or `wide["ev"] / wide["fcf"]`, matching however `ev_ebitda`/`ev_sales`
are already built) to `build_valuation_history()`. Apply the same denominator scale guard
already wired in for the other EV-based multiples in the recent valuation-guard fix — use
`fcf`'s own scale-sanity check the same way `ev_ebitda` guards against thin `EBITDA_TTM`.

### Step 4.2 — Hiding consistency

Some profiles already hide `pfcf_ratio` because FCF is structurally negative for that sector
(e.g. `utilities`, per the earlier profile work). Decide whether `ev_fcf` should be hidden
alongside `pfcf_ratio` in those same profiles for the same reason, or whether it behaves
differently enough (EV changes with net debt, FCF's sign issue is independent of that) to
warrant separate treatment. Check a couple of the affected profiles' real data before
deciding — don't assume the hide list should just be copied over mechanically.

### Step 4.3 — Add to plotting

Wire `ev_fcf` into `plot_valuation()`'s `concepts_to_plot`, next to `pfcf_ratio`, following the
existing tuple format.

### Step 4.4 — Verify against a real leverage-change case

Confirm `ev_fcf` and `pfcf_ratio` genuinely diverge (tell a different story) for a ticker whose
net debt has changed meaningfully over its cached history — report both series side by side
for at least one such ticker as proof the new metric adds real information, not a redundant
copy of `pfcf_ratio` scaled by a near-constant factor.

### Step 4.5 — Non-regression for Part 4

Confirm `pfcf_ratio` and every other existing multiple are completely unchanged; `ev_fcf` is a
pure addition.

---

## Output

One file, `valuation_quality_improvements_report.md`, in four parts, each with its
investigation, implementation, verification against a real case, and non-regression results.

No scratch scripts left behind. Do not implement any project-wide visibility-threshold
decision that Part 3 identifies as needing a bigger call — report and recommend, per this
project's standing practice for structural questions.