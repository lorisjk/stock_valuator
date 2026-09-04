# Task (Urgent): Snapshot Values Must Not Silently Forward-Fill Stale Derived Metrics

**Read first:** the AppLovin (`APP`) finding quoted in full below — this is the reproduction case and
the acceptance test — `ttm_window_report.md` and `annual_path_gate_report.md` (the two prior TTM
investigations; this bug is adjacent to both but is neither: it is not a window-arithmetic error and
not a missing derivation path, it is `get_latest_value` reporting a value that is real but ten
quarters old as if it were current), and the current `get_latest_value`, `build_snapshot`, and
whatever field already tracks staleness (`days_since_last_filing`, `fundamentals_stale`,
`filing_likely_overdue` — confirm these exist and what they currently check before assuming this
task starts from nothing).

## The bug, exactly as found

> `fcf_ttm = 1.057B` is the value from 2023-12-31. In the exported facts, `Capex` is empty for every
> quarter from 2024-03-31 onward, and so are `FCF_QUARTERLY` and `FCF_TTM`. The snapshot has
> forward-filled the last valid value from ten quarters ago.
>
> The consequence is severe because `market_cap` is current and the denominator is 2.5 years old:
>
> | | snapshot | correct |
> |---|---:|---:|
> | FCF TTM | $1.06B | ~$4.51B |
> | P/FCF | 101.3 | 23.8 |
> | EV/FCF | 101.7 | 23.9 |
> | `pfcf_ex_sbc` | 138.2 | 25.3 |
> | FCF yield | 1.0% | 4.2% |
>
> `OperatingCashFlow_TTM` ($4.53B) is correct — only the `Capex` tag is missing. AppLovin is now a
> pure software platform after divesting its apps business, with near-zero capex — the last reported
> quarterly figures were around $244K. The company's own reported Q2 2026 free cash flow (~$863M)
> is consistent with operating cash flow minus negligible capex, confirming the correct-column figure.
>
> **The bug is the forward-fill, not the missing tag.** A derived metric that has been `NaN` for ten
> consecutive quarters must not reappear in the current snapshot. A `max_staleness_quarters` guard
> (e.g. 1) would close this entire class of error, for every ticker, not only `APP`.

This is not a new problem class for this project — `Capex` going structurally missing while
`OperatingCashFlow` stays populated is exactly the shape of defect the split, scale, and duplicate-
period investigations have each found in a different guise: one input silently stops, a downstream
computation keeps using the last value it had, and nothing announces the substitution.

**Explicitly NOT in this task:** no changes to `calculate_ttm`'s window logic (correct, per two prior
investigations — this is not a window problem, the window correctly produces NaN; the snapshot layer
is what discards that NaN). No changes to why `Capex` stopped being tagged (a real finding — AppLovin
plausibly stopped reporting it because it is now near-zero and possibly immaterial — but that is a
tag-investigation question for a separate task, not this one). No changes to `calculate_growth` or
the growth catalogue.

---

## Step 0 — Confirm the mechanism before fixing it

1. **Read `get_latest_value` exactly.** Confirm it selects the most recent **non-null** row
   regardless of how far that row is from the most recent **period** — that is the stated bug; verify
   it from the code rather than from the report's inference.
2. **Check whether a staleness guard already exists anywhere in the snapshot path** and, if so, why
   it did not catch this case. `days_since_last_filing`/`fundamentals_stale`/`filing_likely_overdue`
   sound related — confirm what they actually measure (filing recency, not per-metric data recency)
   and confirm they are answering a different question than the one this bug needs answered. If a
   `max_staleness_quarters`-shaped guard was already attempted and abandoned, find out why before
   reimplementing it.
3. **Measure the exposure across the whole cached universe**, not just `APP`: for every metric
   `build_snapshot` reads via `get_latest_value`, how many (ticker, metric) pairs have a "latest"
   value more than N quarters older than that ticker's most recent *available* period for any other
   metric. Report the distribution of staleness gaps, the same way the TTM and decumulation cycles
   reported their span distributions before choosing a threshold — the bound should come from this
   distribution, not be assumed as "1" because the report suggested it.

## Step 1 — Decide the bound and the failure mode

1. **Set `max_staleness_quarters`** from Step 0's measured distribution — state the number and the
   evidence, following the project's established method (an empty run in the distribution, if one
   exists, is the strongest justification; if there is no clean gap, say so and argue the number on
   the actual cost/benefit rather than picking one that looks clean).
2. **Decide what a metric does when it fails the staleness check**: `None`/blank in the snapshot (the
   honest-gap default this project uses everywhere else), or blank plus a flag recording why. Given
   this project's standing preference and the precedent of `ttm_source`/`ffo_gains_source` recording
   *how* a value was derived, a `stale`/`fresh` provenance marker is likely the right shape — state
   the choice.
3. **Decide the scope**: does the guard apply to every metric `get_latest_value` touches, or only
   derived `_TTM`/computed metrics (raw point-in-time facts like `shares_outstanding` have a
   different staleness meaning than a rolling derived figure)? State the reasoning — a raw fact that
   is merely old because the filer hasn't reported again yet is a different situation from a derived
   figure whose *input* went missing while other inputs kept updating.
4. **Confirm what happens to the metrics that depend on the guarded value** — `pfcf_ratio`, `ev_fcf`,
   `pfcf_ex_sbc`, `dividend_yield`-style ratios that divide by a now-blanked figure must also blank,
   not silently divide by whatever stale number happened to survive elsewhere. Trace every consumer
   of `fcf_ttm` in the snapshot path specifically, since that is the reproduction case, and generalize
   to every other `_TTM`-derived ratio the same way.

## Step 2 — Implement

Add the guard to `get_latest_value` or wherever the snapshot's per-metric lookup happens, per Step
1's design. Do not touch the underlying TTM computation — `FCF_TTM` should still correctly be `NaN`
for the affected quarters in `metrics_long`/`valuation_history`; this fix is entirely about what the
**snapshot** does when asked for "the latest value" and finds only a stale one.

## Step 3 — Verify

1. **`APP` specifically, the reported case**: after the fix, `fcf_ttm` in the snapshot is blank (or
   flagged stale, per Step 1.2) rather than $1.057B, and every dependent ratio (`pfcf_ratio`,
   `ev_fcf`, `pfcf_ex_sbc`, dividend/FCF-yield-style metrics) is blank or correctly recomputed —
   not silently wrong. Confirm the historical `valuation_history`/`metrics_long` series for `APP` is
   **unchanged** — this fix must not touch anything except the snapshot's forward-fill behaviour.
2. **Universe-wide diff**: capture snapshot output before and after for all cached tickers; account
   for every value that goes from populated to blank (each should trace to a staleness gap exceeding
   the chosen bound) and confirm nothing that was genuinely current changes.
3. **No false positives**: a metric whose input is reported quarterly and current must not be
   blanked by the new guard — spot-check several tickers with healthy, up-to-date data across
   multiple profiles to confirm the guard does not fire on them.
4. **The chosen provenance/flag mechanism (if Step 1.2 chose one)** surfaces correctly in the data
   tab and/or snapshot section, consistent with how `ttm_source` and `ffo_gains_source` already
   surface their provenance.
5. **The frontend's snapshot marker (item 13)** respects the new blank/flagged state — a snapshot
   marker must not render using a value the pipeline itself now refuses to publish as current.
   Confirm rather than assume this composes for free.
6. **Re-measure quality flags** and report the delta — this fix should surface as fewer plausible-
   but-wrong snapshot values, and the report should state how many (ticker, metric) pairs changed
   from a stale published value to an honest gap.
7. Standing regression suite as applicable: export validator, chart-builder A/B (valuation and
   comparison, since both read snapshot-derived figures — confirm which do), `check-chart-width`,
   `check-tab-state`, `check-table-format`, `npx tsc -b`/`npx eslint .`/`npx vite build` if any
   frontend file needed a change.

## Output

One file, `snapshot_staleness_guard_report.md`:

1. Step 0's measurement: the staleness-gap distribution across the universe, and confirmation of
   what `get_latest_value` currently does and why existing flags did not catch this.
2. The Step 1 decisions: the bound with its evidence, the failure-mode/flag design, the scope, and
   the dependent-ratio tracing.
3. What was implemented, by file.
4. The Step 3 verification, especially the `APP` before/after and the universe-wide diff accounting
   for every changed value.
5. The re-measured flag delta.
6. Anything left as a follow-up — in particular, whether the same staleness question exists for
   other derived `_TTM` metrics beyond `FCF_TTM` and whether this fix generalizes to all of them or
   needs a second pass.

No scratch files left behind.