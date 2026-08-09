# Task: Final Consistency Items

**Read first:** `annual_path_gate_report.md` §7 (Parts A and E come from there),
`alignment_and_defaults_report.md` "Deliberately not fixed" (Parts B, C and D),
`product_cleanup_report.md` (Part C's measurement), `rolling_window_report.md` (Part A's
methodological model), and `bugfixed_update_history.md`.

## Context

After ten investigations the data layer has **no known structural defect**. What remains is a set of
items each previous task recorded and deliberately left standing, because fixing them inside a task
about something else would have made that task's diff unattributable.

They are small, they are independent, and none of them currently falsifies a displayed number in the
way the shipped fixes did. They are worth doing because each is a place where the pipeline is
internally inconsistent with itself.

**Four change groups (A–D), each with its own diff. Part E is an evaluation, not necessarily a
change.**

**Explicitly NOT in this task:** no coverage-flag semantics (that is its own task and it changes the
meaning of every flag), no `calculate_ttm` / `calculate_rolling_harmonic_stats` /
`decumulate_period_values` / `extract_period_values` / `annual_ttm_values` changes (all shipped and
evidence-backed), no tag work, no UI or chart changes, no new metrics.

**Methodological constraint, established in `product_cleanup_report.md`:** `get_price_history` is not
bit-reproducible across calls (two consecutive AAPL fetches differed by up to 9.155e-05). Every
before/after comparison must run from **one price capture**.

---

## Part A — `apply_self_relative_scale_guard`'s 17-row window

The last member of a family this project has now fixed three times: `calculate_ttm` (4 rows),
`calculate_rolling_harmonic_stats` (20 rows), and `pct_change` (4 rows) all counted **rows** where
they meant **calendar time**. This guard uses a **17-row centred window** — roughly four years either
side, on a series with no gaps, and something else entirely on a series with them.

It differs from the three in one way that matters: the window is **centred**, so it looks forward as
well as back. State what that implies for the rule before designing it.

Follow the method that produced the other three bounds:

1. **Measure the span distribution** of every 17-row window the guard currently forms, across all 501
   tickers and every concept it covers. Report it around each cluster and identify the **empty
   runs**, if any. Note that the rolling-window task found *no* empty run for its five-year window
   and explained structurally why — check whether the same reasoning applies here before assuming a
   threshold exists to find.
2. **Report the tail**: how many windows span materially more than the intended period, on how many
   tickers and concepts.
3. **Decide the rule** — date-filter (take what falls inside the intended span) or mask (keep the row
   window, reject it when its span is wrong). The rolling-window task chose date-filtering because
   the quantity really was "the last five years"; decide what the quantity is here and let that
   decide. A centred window may need both halves bounded separately.
4. **Minimum observation count**: a centred date window can have very few neighbours near the series
   ends. Decide what the guard does then, and keep it coherent with however the rolling stats already
   express "not enough history" rather than inventing a second notion.

## Part B — `calculate_peer_band_flags` anchors on `pd.Timestamp.today()`

Its five-year peer window is anchored on the run date rather than on the data. Two consequences:

1. **The flags are not reproducible.** The same cached facts re-run a month later give different
   flags, because the window moved and the data did not.
2. **It ignores `as_of`.** `build_valuation` takes an `as_of` anchor precisely so a historical view
   shows what that date could have known; the peer bands attached to that view are still computed
   from a window ending today.

Fix it the way `build_valuation` was fixed: an `as_of: pd.Timestamp | None = None` parameter, `None`
keeping today's behaviour, a supplied date anchoring the window there. Reuse the existing windowing
helper rather than writing a second copy of the arithmetic — the rolling-window task consolidated two
divergent revenue-growth computations for exactly this reason.

Then decide and state: **does the app pass its `as_of` through to these flags?** The snapshot and the
valuation charts already honour it; leaving the peer bands anchored on today would make one part of
an as-of view silently current. Note the cross-ticker property the gate report found — a peer band
flag depends on other tickers' data, so this is the one flag where one ticker's window choice moves
another ticker's output.

## Part C — The two scale-guard constants

`build_snapshot` passes **0.01** and `build_valuation_history` passes **0.001** for `pb_ratio` and
`p_tbv` — a factor of ten. So for those two multiples, the snapshot marker and the historical line
are not strictly the same quantity, and a value can be guarded out of one and published in the other.

The three concepts added by the product-cleanup task deliberately use the history constant, so the
inconsistency is confined to these two.

1. **Measure the disagreement**: how many (ticker, period) pairs would be guarded under one constant
   and not the other, and what those values look like.
2. **Decide which is right** and unify. Argue it on the measurement, not on which is stricter — the
   alignment task's Part B showed that the unguarded population there was systematically *tamer* than
   the guarded one, so intuition about strictness is not reliable here.
3. Verify that after unification the snapshot marker and the history line agree on every published
   point for both multiples.

## Part D — `get_latest_value` returns the newest row even when its value is null

Measured in `product_cleanup_report.md`:

```
AVB  p_ffo inputs:  NaN at 2026-06-30, NaN at 2026-03-31, a real value at 2025-09-30
                    -> no snapshot p_ffo, though one is available three quarters back
```

This affects **every snapshot input**, not only `p_ffo`.

The fix is obvious and the danger is in the obvious version of it: skipping nulls without a bound
would silently resurrect a value from years ago and present it as current.

1. **Measure the exposure**: across all concepts the snapshot reads, how many tickers have a null
   newest row with a real value behind it, and **how far behind**. Report the distribution of that
   distance — it is what the bound should come from.
2. **Decide the staleness bound** and state it. Consider whether the snapshot should also *record*
   the value's date when it is not the newest period, so a consumer can see it — the project already
   surfaces `ttm_source` and `ffo_gains_source` for exactly this kind of "here is how this number was
   obtained" signal, and a snapshot value from three quarters back is a fact about the value.
3. Verify AVB specifically, and confirm no value older than the bound is published.

## Part E — Class 4's interior holes: evaluate, then recommend

The gate task left **1,550 genuine interior holes across 719 (ticker, concept) pairs** — AMZN
`StockRepurchased` 15, LUV `ShareBasedCompensation` 10, CNP `StockIssued` 9, ETR `Capex` 9,
PFE/SYY `DepreciationAndAmortization` 9 — because reaching them needs per-date machinery whose cost it
measured: a tie-break at **81,505 collision dates**, and **11,460 pre-quarterly annual points**
admitted alongside unless separately excluded.

**This part is an evaluation. Do not implement unless the evidence clearly supports it.**

1. Re-measure the three populations (interior holes, pre-history, collisions) against the current
   code, since the gate has changed since they were counted.
2. Determine whether a rule can reach the 1,550 **without** admitting the 11,460 and **without** a
   tie-break at the 81,505 — for instance by restricting to dates strictly interior to the rolling
   path's span and unreached by it. State whether such a rule exists and what it would cost.
3. **State the recommendation and the reasoning.** "Confirmed not worth the mechanism" is a fully
   successful outcome here — the value is 1,550 rows against a frame of 512,000, and the property
   being risked is the per-series disjointness guarantee that the gate task showed is load-bearing
   (two paths concatenate rather than merge; a collision produces duplicate rows that `pivot_table`
   averages silently).
4. If and only if a rule exists that preserves disjointness structurally rather than by tie-break,
   implement it as a fifth change group with its own diff and the same verification as the rest.

---

## Verification, per change group

1. Capture a before-state across all cached tickers: base facts, all `_TTM` concepts, `metrics_long`,
   every `valuation_history` multiple, every `avg_*_5y` line and its `_n`, and the snapshot.
2. Diff after each group; account for every appeared, changed and disappeared value, with the
   expected footprint stated up front.
3. **Anchor and snapshot invariants**: newest value per ticker/concept unchanged, or any exception
   named and justified. This has held 0/0 for ten tasks; Part D changes snapshot values **by design**,
   so state that expected exception up front rather than reporting it as a surprise.
4. **Report the mean-line effect per line.** Running series: TTM ~25%, rolling-window 11–15%,
   duplicate-ends 2–5%, alignment 0–3.7%, FFO gains 0.6–1.5%, annual-gate 0–0.07%.
5. **Independent plausibility check** for any group that changes values — the established pattern is
   checking against something the filer published or a reconstruction sharing no code with the
   pipeline.
6. Re-measure all quality flags and report the delta per flag. Note from the gate report that
   coverage flags count **base concepts before `add_derived_concepts` runs**, so do not expect
   derived-value recoveries to clear them.

## Record

Update `bugfixed_update_history.md` per convention, including Part A's bound with the evidence it came
from, Part C's constant decision, Part D's staleness bound, and Part E's recommendation.

## Output

One file, `final_consistency_report.md`, with a section per part: the measurements, the decision with
reasoning and the alternative's failure mode, what was implemented, and the per-group diff. Plus the
mean-line effect, the flag deltas, Part E's recommendation, and anything deliberately not fixed.

No scratch scripts left behind.