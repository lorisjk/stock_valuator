# Task: `calculate_ttm` — Calendar-Aware Windows + Annual-Fact TTM Path

**Read first:** `tag_investigation_stock_sbc_report.md` (sections 6 and 8 are the direct input),
`bugfixed_update_history.md`, `METRICS_REFERENCE.md`, and the current `calculate_ttm`,
`decumulate_period_values` and `build_dataframe` code.

## Context

`calculate_ttm` is `.rolling(window=4).sum()` **over the rows present in the series**, not over
calendar quarters. On a sparse concept it therefore sums the last four *available* values, which
may span several years, and labels the result "trailing twelve months".

This was discovered as a side effect during the tag investigation: filling gaps in
`ShareBasedCompensation` **changed** existing `owner_fcf` values for 20 tickers, 15 of which were
never flagged — because adding data re-anchored the rolling window at nearer dates. One example
from that report:

```
SRE gained the 8 consecutive quarters 2016-03-31 … 2017-12-31,
    which had been an unbroken two-year hole between 2015-12-31 and 2018-03-31.
```

Before the fill, SRE's "TTM" at points in that hole summed values spanning years. The number was
wrong, produced no error, and fed `pfcf_ex_sbc` and every valuation denominator built on a `_TTM`
concept.

The defect affects **every thin concept**, not only the ones recently touched. Its failure mode is
the one this project treats as most dangerous: a plausible number rather than an exception.

A second, related finding from the same report: **31 flagged (ticker, concept) pairs are
"annual-only"** — the filer discloses the item once a year at 12-month duration, so
`decumulate_period_values` has nothing to decumulate and a quarterly pipeline gets zero. Eight of
the 21 flagged utilities' `ShareBasedCompensation` cases are this. Example:

```
NEE  AllocatedShareBasedCompensationExpense: 48 facts, durations {12 months: 48}
     annual values = 21, quarterly values = 0
```

These two things belong in one task because **a 12-month fact at a fiscal year end is, by
definition, exactly the trailing-twelve-months value at that date** — not an approximation of it.
Part 1 removes TTM values that were never really TTM; Part 2 adds TTM values that were there all
along in a form the TTM layer did not read.

**Explicitly NOT in this task:** no split-normalisation or `share_count_jump_flag` work (separate
task), no further tag work, no new concepts or metrics, no `PROFILE_HIDDEN` refactor, no UI or
chart changes.

---

## Part 1 — Make the window calendar-aware

### Step 1.1 — Measure the actual span distribution first

Before choosing any threshold, measure across all cached tickers and all `_TTM` concepts: for
every window the current implementation forms, the **elapsed time between the first and fourth
row** in it.

Report the distribution. The expectation is a dense cluster near 365 days (52/53-week filers and
shifted fiscal year ends spread it somewhat), a gap, then a tail of windows spanning multiple
years. **The threshold should come out of that gap, not out of a round number.** If there is no
clean gap, say so — that is a finding, and the threshold then has to be argued differently.

Also report, per concept, how many currently-produced TTM values fall in the tail. That number is
the coverage cost of the fix and must be known before it is applied.

### Step 1.2 — Implement and state the threshold

Mask windows whose span exceeds the threshold, so an out-of-range window yields **no value**
rather than a wrong one. State the tolerance chosen and the evidence for it, and handle the
52/53-week and shifted-fiscal-year cases explicitly — a fix that silently drops legitimate retail
filers' TTM values has traded one defect for another.

Decide and state whether the threshold is global or per-concept. Prefer global unless the
measurement shows a concept that genuinely cannot use it.

### Step 1.3 — Report what disappears

Per concept and per ticker: how many TTM values the mask removes, and spot-check several against
the source rows to confirm they were genuinely spanning more than a year. Removing a correct
value would be a regression; removing a wrong one is the point.

## Part 2 — Derive TTM directly from annual facts

### Step 2.1 — Establish the boundary against `decumulate_period_values` first

This is the part most likely to go wrong. `decumulate_period_values` already derives Q4 as
FY minus Q1+Q2+Q3 for filers that report year-to-date cumulatively — so for those filers a
12-month fact is already consumed as an intermediate step.

**Determine precisely which cases Part 2 applies to** and confirm it against real data before
implementing: the target is the filer whose facts for a concept are **exclusively** 12-month
duration, where nothing can be decumulated. Report how you distinguish the two cases in code, and
verify no ticker/concept is handled by both paths. Two paths that can both write the same
`_TTM` value at the same date is the failure this step exists to prevent.

### Step 2.2 — Implement

Where a concept has a 12-month fact at a period end, set `<concept>_TTM` at that date directly
from it. Between fiscal year ends the value stays NaN — the disclosure cadence is annual, and the
series should say so rather than interpolate.

Verify against the known cases: NEE should gain 21 `ShareBasedCompensation_TTM` points where it
had none, and the other annual-only tickers listed in the tag report should behave equivalently.

### Step 2.3 — Mark provenance

Where a ticker reports partly quarterly and partly annually, `_TTM` values now arise two ways.
Carry the provenance (a column, a flag, or whatever fits the existing frame conventions) so a
series that looks uniform is not silently mixed.

Decide whether this provenance surfaces in the app's data tab. Recommended: yes — it is exactly
the kind of "here is how this number was derived" signal this project exists to show — but
implementing the UI side is optional; **stating the decision is not.**

### Step 2.4 — Consider the coverage threshold interaction

Some of the 31 annual-only pairs may now clear or change their quality flags. Report which, and
whether the 50% coverage threshold still means what it should for a concept whose disclosure is
legitimately annual. **Do not change the threshold logic in this task** — report the finding.

---

## Part 3 — Non-regression, as two separate change groups

Part 1 removes values and Part 2 adds them. If applied together the diffs cancel and become
uninterpretable, so **measure each separately**, in this order: Part 1, diff, Part 2, diff.

For each group, following the convention established in the tag investigation:

1. Capture a before-state across **all** cached tickers — every `_TTM` concept, plus the
   downstream quantities that consume them: `owner_fcf`, `pfcf_ex_sbc`, every valuation multiple
   whose denominator is a `_TTM` concept, and the growth panels added recently (several are built
   on `_TTM` series).
2. Diff after, and account for **every** difference: appeared, changed, disappeared. In Part 1
   disappearances are the intended effect and changes need justification; in Part 2 appearances
   are the intended effect and changes need justification.
3. Report the effect on `valuation_history` mean lines — those are the benchmark the app's charts
   compare today's multiple against, so a changed history moves the reference a user reads.
4. Re-measure the quality flags across all 501 tickers and report the delta per concept.
5. Verify the specific cases named above: SRE and the other 19 tickers whose `owner_fcf` moved in
   the tag investigation should now behave correctly; NEE and the annual-only list should gain
   values.

## Part 4 — Record

Update `bugfixed_update_history.md` per convention, including the threshold and its evidence, and
the boundary rule between the two TTM derivation paths.

## Output

One file, `ttm_window_report.md`:

1. The Part 1.1 span distribution, the gap (or its absence), and the threshold with its evidence.
2. What Part 1 removed, per concept, with spot-checks proving the removed values genuinely spanned
   more than a year.
3. The Part 2.1 boundary rule against `decumulate_period_values`, and the confirmation that no
   ticker/concept is handled by both paths.
4. What Part 2 added, including NEE and the annual-only list.
5. The provenance mechanism and the decision on surfacing it in the app.
6. Both diffs, separately, with every appeared/changed/disappeared value accounted for, plus the
   valuation-history mean-line effect.
7. Re-measured flag counts and the annual-only coverage-threshold finding.
8. Anything deliberately not fixed, with reasoning.

No scratch scripts left behind.