# Task: Row-Based Windows — `calculate_rolling_harmonic_stats` and `pct_change`

**Read first:** `duplicate_period_ends_report.md` (section 6's first two entries are the direct
input, and the TSLA case in section 4 is the cleanest demonstration), `ttm_window_report.md`
(section 1 is the methodological model — this task is the same fix one layer up), and the current
`calculate_rolling_harmonic_stats`, `build_valuation_history` and the `pct_change` call sites.

## Context

The TTM task established that a rolling window counted in **rows** rather than **calendar time**
silently produces a value that is not what its name claims. It fixed `calculate_ttm`. Two more
places carry the same defect, and both feed things the app puts in front of a user as its central
claim.

### 1. The five-year mean lines

`calculate_rolling_harmonic_stats` uses a **20-row** window. On a series with any hole, twenty rows
span more than five years, and the "five-year average" is an average over whatever period those
rows happen to cover.

The duplicate-period-ends task produced the clean demonstration, because it removed rows without
changing any value:

```
TSLA  lost exactly one row (SharesOutstanding 2021-12-30, twin at 2021-12-31 survived)
      no TSLA value changed
      avg_p_ffo_5y_n   19 -> 20 observations
      avg_p_ffo_5y     68.67 -> 70.73
```

Across that task's diff, **2–5% of all mean-line points moved** for this reason alone. These lines
are the reference the valuation charts draw and the snapshot marker is compared against — "current
multiple versus its own five-year history" is the product's core proposition, and the denominator
of that comparison is currently not a five-year history.

### 2. The growth comparisons

`wide.groupby("ticker")["Revenue_TTM"].pct_change(periods=4)` has **two** defects in one call:

- **It counts rows.** Four rows back is four quarters back only if no quarter is missing. Every one
  of the 90 changed values in the duplicate-ends diff ran through this path.
- **`fill_method="ffill"` is pandas' default**, so a hole is silently bridged by the previous value
  and the comparison base is a date other than the one intended. The decumulation report recorded
  this; the TTM report traced 26 appeared and 121 changed `pe_to_revenue_growth` values to it.

The second is also the source of the `FutureWarning` the pipeline currently emits.

Both feed `pe_to_revenue_growth` and all seven growth panels, and interact with
`MIN_PEG_REVENUE_GROWTH` — the TTM and decumulation reports each traced a blanked or unblanked PEG
value to a growth figure moving across the 2% floor because its base shifted.

**Explicitly NOT in this task:** no `calculate_ttm` changes (shipped, evidence-backed), no
`extract_period_values` / `decumulate_period_values` changes (both shipped), no split/scale/tag
work, no `apply_denominator_scale_guard` or `ffo.fillna(0)` fix (those are a different species —
"a missing default treated as a pass" — and get their own task), no coverage-flag semantics, no UI
or chart changes, no new metrics.

---

## Part 1 — The rolling window

### Step 1.1 — Measure the span distribution

Follow the TTM task's method exactly, one layer up. For every 20-row window
`calculate_rolling_harmonic_stats` currently forms, across all 501 tickers and every concept it
covers, measure the **elapsed time between the first and last row**.

Report the distribution day by day around each cluster, and identify the **empty runs** bracketing
the legitimate region. For twenty consecutive calendar quarters the span between outer end dates is
nineteen quarters ≈ 1,734 days, not 1,826 — state the expected figure from the arithmetic before
looking, so the measurement can confirm or contradict it rather than being fitted to it.

Report the tail: how many windows currently span materially more than five years, on how many
tickers and concepts. That is the size of the defect.

### Step 1.2 — Decide the rule

A five-year window differs from the TTM window in one important way: **a TTM window must contain
exactly four quarters, but a five-year window does not need exactly twenty observations.** A ticker
with a genuine gap should still get a mean over the observations it does have within the window —
just not over observations from outside it.

So there are two candidate shapes, and the choice must be stated:

1. **Filter by date, keep whatever falls inside** — take all observations within five years of the
   window's end date, however many that is. Natural, and it composes with the existing `_n` and
   short-history machinery.
2. **Keep the row window but mask it when its span is wrong** — the TTM task's shape.

Recommended: option 1, because the quantity being computed is genuinely "the average over the last
five years", not "the average of twenty observations". But state the reasoning and the failure mode
either way.

Whichever is chosen, decide and state:

- **The minimum observation count** for a mean to be published at all. The snapshot already carries
  `avg_*_5y_n` and short-history flags — read what those currently mean and keep them coherent
  rather than introducing a second, parallel notion of "not enough history".
- **The window's anchor.** Five years back from the row's own date, or from a fixed reference. The
  former is what a rolling mean means.
- Whether the harmonic/arithmetic split (`HARMONIC_MEAN_CONCEPTS`) is affected at all — it should
  not be, but confirm rather than assume.

### Step 1.3 — Verify the arithmetic independently

For several tickers, recompute a mean by hand from the calendar-filtered series and compare against
the function's output. Internal consistency proves the code does what it says; this proves the
window contains what it claims.

Include TSLA specifically — the reported 68.67 → 70.73 move should resolve to whichever value the
correct window produces, and the report should say which and why.

## Part 2 — The growth comparison

### Step 2.1 — Fix both defects together

They are in the same call and fixing one without the other leaves the same class of error in place.

- Replace the row-offset comparison with a **date-based** one: the value four quarters back by
  calendar, not four rows back. Reuse the tolerance logic established in the TTM task rather than
  inventing a second convention — state which bounds you use and why they are the right ones for a
  four-quarter lag between *observation dates* (which is a different measurement from the TTM
  window's span between the outer rows of a four-row window; be explicit about which quantity you
  are bounding).
- Set `fill_method=None` explicitly, or drop `pct_change` in favour of the date-based lookup, so a
  hole produces no growth figure rather than a silently bridged one. Confirm the `FutureWarning`
  is gone.

### Step 2.2 — Report the coverage cost

Growth values will disappear where the base is genuinely missing. Report, per concept and per
ticker, how many — and check the interaction with `MIN_PEG_REVENUE_GROWTH`: a growth figure that
moves across the 2% floor changes whether PEG is published, and both previous reports traced values
to exactly that. Report the PEG delta separately from the growth delta.

## Part 3 — Non-regression, all 501 tickers

Apply Part 1 and Part 2 as **separate change groups**, diffing after each. They both move the same
downstream quantities, and a combined diff would be unattributable.

For each group:

1. Capture a before-state across all cached tickers: base facts, `_TTM` concepts, `metrics_long`,
   every `valuation_history` multiple, **every `avg_*_5y` line and its `_n` companion**, and the
   snapshot.
2. Diff and account for every appeared, changed and disappeared value.
   - Part 1 should change **no base fact and no single-period multiple** — only the rolling
     aggregates and anything downstream of them. If a base value moves, something is wrong.
   - Part 2's disappearances are the intended effect where a base is missing; changes need
     justification.
3. **Anchor and snapshot invariants**, per the precedent now established over seven tasks: the
   newest value per ticker/concept unchanged, or any exception named. Note that this task changes
   snapshot `avg_*` fields **by design** — that is the point — so state the expected exception up
   front rather than reporting it as a surprise.
4. **Report the mean-line effect plainly and prominently.** The TTM task moved ~25% of points, the
   decumulation task 0.2–0.6%, the duplicate-ends task 2–5%. State where this one lands, per line.
   This is the number that matters most in this task, because these lines *are* the benchmark.
5. **Independent plausibility check**: for several tickers, verify that the new five-year mean is
   computed over observations that actually fall within five years — list the observation dates for
   one window and confirm the span.
6. Re-measure all quality flags and report the delta.

## Part 4 — Record

Update `bugfixed_update_history.md` per convention, including the window rule, the minimum-count
decision, and the growth-lag convention.

## Output

One file, `rolling_window_report.md`:

1. The Part 1.1 span distribution, expected figure stated before measuring, empty runs, and the
   size of the tail.
2. The window rule chosen with reasoning and the failure mode of the alternative, plus the
   minimum-count decision and how it composes with the existing `_n` and short-history fields.
3. The Part 2 fix, the tolerance convention used, and confirmation the `FutureWarning` is gone.
4. The two diffs, separately, with every appeared/changed/disappeared value accounted for.
5. **The per-line mean-line effect**, stated plainly.
6. The independent checks, including TSLA.
7. Re-measured flag counts.
8. Anything deliberately not fixed, with reasoning.

No scratch scripts left behind.