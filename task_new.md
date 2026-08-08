# Task: The `annual_ttm_values` Gate — Event-Driven Concepts Falling Between Two Paths

**Read first:** `ffo_gains_report.md` §1.3–1.4 and §8 (the direct input — the defect was diagnosed
there and deliberately left standing), `ttm_window_report.md` (Part 2 built the annual path and the
disjointness property this task revisits), `alignment_and_defaults_report.md`, and the current
`annual_ttm_values`, `calculate_ttm` and `extract_with_mode` code.

## Context

The TTM task added a second derivation path: where a filer reports a concept **only** at 12-month
duration, `<concept>_TTM` is set directly from the annual fact, because a 12-month value at a fiscal
year end *is* the trailing-twelve-month value at that date. The two paths were made disjoint by
construction, so no value could ever be written twice:

```python
    if quarterly_values:
        return []
```

That gate is too coarse. It asks whether *any* quarterly value exists, not whether the quarterly path
can actually produce anything. The FFO investigation found the consequence:

```
CPT  GainLossOnSaleOfProperties   13 FY facts,  5 quarterly values
     quarterly ends: 2014-12-31  2015-03-31  2015-12-31  2016-06-30  2016-09-30
                     steps  90, 275, 182, 92
     -> calculate_ttm refuses every window (correctly)
     -> annual_ttm_values returns [] because quarterly_values is non-empty
     -> 13 usable annual facts produce nothing
```

Five scattered values that cannot form a window disable the path that could have used thirteen that
can. The filer falls between the two paths and gets nothing.

**The mechanism is general, not FFO-specific.** Any concept reported **on occurrence** rather than
every period is exposed: property disposals, asset impairments, restructuring charges, legal
settlements, one-off gains. A filer tags it in the quarters it happens and omits it otherwise, so
consecutive-quarter runs are rare, while the annual figure is reported every year.

This is why the fix was excluded from the FFO task: it changes behaviour that **all 25
`TTM_CONCEPTS` share**, so it moves every thin concept in the frame at once and needs its own diff.

**Explicitly NOT in this task:** no changes to `calculate_ttm`'s window bounds (shipped,
evidence-backed), no changes to `decumulate_period_values` or `extract_period_values`, no tag work of
any kind, no `apply_self_relative_scale_guard` / `calculate_peer_band_flags` / scale-guard-constant /
`get_latest_value` fixes (all recorded, all separate), no UI or chart changes, no new metrics.

---

## Step 1 — Measure the population before designing anything

Across all 501 cached tickers and all 25 `TTM_CONCEPTS`, classify every (ticker, concept) pair:

| class | quarterly path | annual path | current outcome |
|---|---|---|---|
| **1** | produces TTM values | disabled by the gate | fine — quarterly is authoritative |
| **2** | produces **no** TTM values, but quarterly values exist | disabled by the gate | **the defect** |
| **3** | no quarterly values at all | runs | fine — the annual path already covers it |
| **4** | produces some TTM values, with gaps the annual path could fill | disabled by the gate | **the open design question** |

Report counts per class, per concept, and the tickers in class 2.

**Class 4 is the decision this task turns on** and must be measured separately from class 2. Class 2
is unambiguous — the quarterly path yields nothing, so nothing can be overwritten. Class 4 is a
filer whose quarterly path works for some years and not others, where the annual path would fill the
holes and the two paths would then coexist on one series. That is exactly the overlap the original
gate was built to prevent.

Also report: for class 2 and class 4, **how many annual facts are being discarded** — the size of the
prize.

## Step 2 — Decide the gate, and preserve the property that mattered

The original gate's purpose was that no value is ever written twice by two mechanisms. **That
property must survive.** What can change is how it is achieved: today it is enforced by a coarse
precondition; it could instead be enforced per date.

Candidate rules, to argue on the Step 1 numbers:

1. **Gate on the quarterly path's output, not its input** — run the annual path when the quarterly
   path produced no TTM values, regardless of how many quarterly facts exist. Fixes class 2, leaves
   class 4 alone. Minimal, and the disjointness stays whole-series.
2. **Gate per date** — the annual path supplies a date only if the quarterly path did not. Fixes
   class 2 and class 4, and disjointness becomes a per-date guarantee rather than a structural one.
3. **Something narrower**, if the measurement suggests it.

State the choice with reasoning and the failure mode of the alternatives. Two things to weigh
explicitly:

- **Mixed-provenance series.** Under rule 2 a single series carries values derived two different
  ways. The `ttm_source` column already exists precisely so that is visible rather than silent —
  check that it is populated correctly on every value either rule produces, and say so.
- **Cadence honesty.** An annual-derived value sits at a fiscal year end and says nothing about the
  intervening quarters. Filling a hole in an otherwise quarterly series with one annual point
  produces a series whose *spacing* is uneven in a way the values do not advertise. Decide whether
  that is acceptable and why. The TTM task's position was that a series should show the disclosure
  cadence rather than interpolate; check whether rule 2 is consistent with that.

Whichever rule is chosen, **verify no value is written by both paths** — a direct check, not an
argument from construction, since the construction is what is being changed.

## Step 3 — Implement

Apply the rule. Keep `annual_ttm_values`' contract otherwise, and keep `ttm_source` accurate for
every value it produces.

## Step 4 — Non-regression, all 501 tickers

Same discipline as the previous nine tasks, and note the constraint established in
`product_cleanup_report.md`: **`get_price_history` is not bit-reproducible across calls**, so the
before- and after-states must be computed from one price capture.

This change is **additive by intent** — it should recover TTM values, not alter existing ones.

1. Capture a before-state across all cached tickers: base facts, all `_TTM` concepts, `ttm_source`,
   `metrics_long`, every `valuation_history` multiple, every `avg_*_5y` line and its `_n`, and the
   snapshot.
2. Diff and account for every appeared, **changed** and disappeared value:
   - **Appeared** is the intended effect.
   - **Changed** needs individual justification. Under rule 1 no existing value should change at all;
     under rule 2 a changed value would mean the annual path wrote over a date the quarterly path
     already held, which is the property that must not break.
   - **Disappeared** should not happen.
3. **Anchor and snapshot invariants.** Note the precedent from the FFO task: a newest *date* moving
   **forward** because a series gained recent reach is the intended effect and is reported as such,
   not as a breach. A newest *value* changing under an unchanged date is not.
4. **Report the mean-line effect per line.** Running series: TTM ~25%, rolling-window 11–15%,
   duplicate-ends 2–5%, alignment 0–3.7%, FFO gains 0.6–1.5%.
5. **Report which concepts moved and by how much.** This touches all 25 `TTM_CONCEPTS`, so a
   per-concept breakdown is the honest summary — a change concentrated in two event-driven concepts
   is a different outcome from one spread across all of them, and the report should say which it is.
6. **Independent plausibility check.** The FFO task's method is directly reusable and is the right
   one here: a recovered annual-derived TTM value must equal the filer's own 12-month fact for that
   fiscal year — and where a filer reports both, four quarterly values must sum to it. State what you
   used and the reconciliation rate.
7. Re-measure all quality flags and report the delta per concept. Coverage flags should improve for
   the class-2 pairs; report by how much.

## Step 5 — Record

Update `bugfixed_update_history.md` per convention, including the class 1–4 counts, the gate rule,
and how disjointness is now guaranteed.

## Output

One file, `annual_path_gate_report.md`:

1. The Step 1 classification with counts per class and per concept, the class-2 ticker list, and the
   number of annual facts currently discarded.
2. The gate rule chosen with reasoning, the failure mode of the alternatives, and the position taken
   on mixed-provenance series and cadence honesty.
3. The direct verification that no value is written by both paths.
4. The diff with every appeared/changed/disappeared value accounted for, the invariants, the
   per-concept breakdown, and the mean-line effect.
5. The independent reconciliation and its rate.
6. Re-measured flag counts.
7. Anything deliberately not fixed, with reasoning.

No scratch scripts left behind.