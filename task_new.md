# Task: Product-Side Cleanup — `ttm_source` Rendering, `write_charts` Flag, `p_ffo` Snapshot

**Read first:** `ttm_window_report.md` (section 5 for `ttm_source`), `app_refinements_report.md`
(section 4 for the snapshot concept overlap), the most recent `full_refresh_report.md`, and the
current `app.py`, `main.py`, `figures.py`, `metrics.py`.

## Context

Three small, independent items that have accumulated across recent tasks. None is a data-
correctness defect; they touch the app and the pipeline's runtime, not the parse layer, so they can
run alongside the data-layer work without competing for the same diffs.

Each part is independent — implement and verify them separately.

**Explicitly NOT in this task:** no parse-layer changes (no `extract_period_values`,
`decumulate_period_values`, `calculate_ttm`, split or scale work), no coverage-flag semantics, no
new metrics, no chart rendering changes beyond what Part 3 requires.

---

## Part 1 — Render `ttm_source` in the data tab

The TTM task added a `ttm_source` column carrying each `_TTM` value's derivation
(`quarterly_rolling` vs. `annual_fact`), and verified it survives `filter_hidden_rows`,
`add_growth_column` and the export into `facts_full.parquet` — which the data tab already reads.
The column is currently inert: `pivot_ticker` pivots on `values="value"` and ignores it.

The reason this matters: an annual-cadence series renders as a sparse line and is **visually
indistinguishable from a series with missing data**. One is complete coverage of what the filer
publishes; the other is a gap. The data tab exists to make exactly that distinction visible.

Requirements:

1. Surface the provenance next to the `_TTM` value it describes. The pivot's shape is
   rows = period, columns = concept, so decide how a per-cell attribute is shown without doubling
   the table's width — options include a suffix or marker on the value, a separate legend listing
   which concepts are annual-cadence for this ticker, or a toggle. Pick one and justify it against
   the table's readability, which the data-tab report already flagged as tight at 37 columns.
2. Rows with no value carry `ttm_source = None` by design — the column never asserts a provenance
   for a value that does not exist. Do not render anything for those.
3. Derived TTMs (`FCF_TTM`, `EBITDA_TTM`, `FFO_TTM`, `EPS_TTM_CALC`) carry `None` because they are
   added downstream; their provenance is their inputs'. Decide whether to leave them unmarked or to
   derive a marker, and state the choice — inventing one risks asserting something the pipeline has
   not established.
4. Add a short explanation to the encyclopedia's growth or valuation section covering what an
   annual-cadence series means, consistent with the "how this pipeline computes it" standard
   applied there.

Verify against a ticker known to have annual-only values — **NEE `ShareBasedCompensation_TTM`
(18 annual values)** — and one with a purely rolling series, and confirm the two look different in
the UI.

## Part 2 — Make chart file writing optional

The most recent full refresh spent **732.9s of 2118.7s (34.6%)** plotting, at ~1.46s/ticker for
1,503 chart files that nothing reads: the app renders from Parquet, and HTML writing was already
commented out manually at some point.

Add a parameter (e.g. `write_charts: bool`) rather than leaving it commented out — a commented line
is lost the next time someone wants to look at a chart file.

Decide and state:

1. **The default.** The nightly pipeline does not need the files; a developer inspecting output
   does. Pick the default that makes the common case cheap and say why.
2. **HTML and JSON separately, or together.** HTML is ~5MB per chart (~7.5GB per full run); JSON is
   ~20–50KB and is the interface a future JS frontend would consume. They may warrant different
   defaults — the Phase 1 "both files or neither" guarantee applies to a single chart's pair, not
   to the decision of whether to write charts at all. State how you keep that guarantee intact.
3. Confirm the run report's timing section still reports something meaningful when plotting is
   skipped, rather than a misleading zero or a missing phase.

Verify: a run with charts disabled produces no chart files and the same `data/app/` exports as a
run with them enabled — byte-identical Parquet output, since the export path is independent of
plotting. Report the measured runtime difference.

## Part 3 — `p_ffo` in `build_snapshot`

The app refinements task found that 10 of 13 valuation panels have a snapshot counterpart; the
three without are `ev_fcf`, `pfcf_ex_sbc` and **`p_ffo`**. The last is the notable one: a REIT gets
a current-value marker on `p_tbv` but not on the multiple that actually matters for REITs.

1. **Confirm the gap first** — re-check which valuation concepts `build_snapshot` produces against
   the current registry, since the metric set has changed since that report. Report the current
   overlap rather than assuming the three named are still the three.
2. Determine why `p_ffo` is absent — whether its inputs are unavailable at snapshot time or it was
   simply never added. If an input is genuinely missing, that is a finding and the honest answer may
   be that it cannot be built; say so rather than approximating.
3. If it can be built, add it, using the same definition `build_valuation_history` uses so the
   snapshot marker and the historical series are the same quantity. Note that FFO is built as
   `NetIncomeLoss_TTM + DepreciationAndAmortization_TTM − GainLossOnSaleOfProperties_TTM` with a
   `fillna(0)` on the gains term — a pre-existing issue recorded in the TTM report. **Do not fix
   that here**, but do not let the snapshot and the history diverge on it either: use the same
   expression, and note the dependency.
4. Consider `ev_fcf` and `pfcf_ex_sbc` on the same footing and report whether they are buildable;
   implementing them is optional, reporting the verdict is not.

Verify on a real REIT (AMT, O) that the snapshot value appears, is numerically consistent with the
most recent `valuation_history` point given the newer price, and renders as the snapshot marker on
the chart.

## Verification, all parts

- `figures.py` and `config.py` unmodified except where Part 1 or 3 genuinely requires it (confirm
  by diff).
- The existing chart output is unchanged when charts are written (compare `build_*` output
  byte-for-byte against a pre-change baseline for three tickers across profiles).
- `main()` and `run_full_refresh()` both run end to end.
- `app.py` still imports no pipeline module, and the page body runs to completion in bare mode.
- State honestly what could not be verified without a browser.

## Output

One file, `product_cleanup_report.md`, with a section per part: what was decided and why, what was
implemented, the verification results, and the measured runtime difference for Part 2.

No scratch scripts left behind.