# Task: Full-Refresh Pipeline Mode — Timing Report + Consolidated Quality-Flag Document

## Goal

Implement a full-refresh capability that the user triggers by running `main.py` (no other
manual steps): delete all cached company facts, re-fetch everything from EDGAR and yfinance
for every currently-active ticker, recompute all metrics, regenerate all plots — and produce
one document reporting (1) how long each of the three phases took and (2) every data-quality
flag that would normally print to the terminal, collected and organized instead of printed.

**This is a feature-build task, not a diagnostic scan.** Read the existing `main.py`,
`figures.py`, `quality.py`, and the EDGAR/yfinance fetching code directly before making any
change — don't guess at function names or existing structure.

## Step 0 — Refactor `build_snapshot()` to long format

Before any of the full-refresh work below, change how the snapshot is built. Currently
`build_snapshot()` produces a wide table (one row per ticker, one column per metric), which
this project has already identified as having an unstable schema: `apply_profile_filter` drops
columns dynamically based on which tickers happen to be present in a given run, so the same
metric can appear or disappear from the output depending on run composition — the planned fix,
noted earlier in this project's own roadmap, was to store snapshots in long format and apply
visibility filtering at read time instead.

Implement that now: rework `build_snapshot()` to produce the **same long shape as
`metrics_long`** — one row per `(ticker, concept/metric, value)` — but containing the **latest
row only** of every fundamental metric and every valuation metric for each ticker, not the
full time series.

**Reuse the existing helpers rather than reimplementing them** — this project already has
`get_latest_row` (used throughout `build_snapshot()` today to pull the most recent value per
metric) and a long-format conversion utility (`to_long_format` or equivalent, used for
`metrics_long`). Find both in the actual codebase and compose them: take every fundamental and
valuation metric, run each through `get_latest_row`, and assemble the results the same way
`build_metrics_long` already assembles its rows — do not write a new bespoke long-format
builder if the existing one can be reused directly.

Apply the same `is_hidden()`/profile-visibility filtering used for `metrics_long` at read time
(when the snapshot is consumed/output), not by dropping columns during construction — this is
the actual fix for the schema-instability problem, not just a format change for its own sake.

**Non-regression for this step specifically**: confirm the new long-format snapshot contains
exactly the same latest-value data as the old wide snapshot did for every ticker/metric
combination that was previously populated (reshaped, not changed) — diff the two
representations against each other (old wide snapshot pivoted to long vs. new long snapshot
directly) rather than assuming the refactor preserved every value correctly.

Since this changes the snapshot's shape, check for and update any downstream code that reads
`build_snapshot()`'s output expecting the old wide format (e.g. anything indexing it by column
name) — grep for actual usages rather than assuming there are none.

## Step 1 — Confirm the active ticker set

`TICKER_PROFILES` contains both active and commented-out entries (the established convention
in this project: a commented-out line with a reason is a deliberate "known broken, don't run
this one" marker, e.g. `#"CVNA": "retail", doesnt work`). The full refresh must run against
**only the active (non-commented) entries** — parse `config.py` correctly for this rather than
assuming every key is active. Confirm the resulting count and report it.

## Step 2 — Implement the delete-and-refetch step

1. Delete every cached `{TICKER}_company_info.json` (confirm the exact cache path/naming
   convention from the actual code, don't assume). Log what was deleted (count, and the list)
   into the report — this is a destructive step and should be auditable.
2. Re-fetch each active ticker's SEC EDGAR company facts from scratch. Respect the existing
   rate-limiting/User-Agent conventions already in this project's EDGAR client — do not bypass
   or loosen them to go faster.
3. Re-fetch each active ticker's yfinance price/shares-outstanding/market-cap data from
   scratch.

## Step 3 — Add three-phase timing instrumentation

Wrap each of the following phases separately, per ticker and in aggregate:
1. **EDGAR fetch** — time to retrieve and cache each ticker's company facts.
2. **yfinance fetch** — time to retrieve each ticker's price/market data.
3. **Calculate + plot** — time to run `calculate_all_metrics`, `build_metrics_long`,
   `build_valuation_history`, and generate both figures for each ticker.

Record enough detail to produce, in the final report:
- Total wall-clock time per phase across the whole run.
- Average time per ticker per phase.
- The slowest 10 tickers per phase (useful for spotting an outlier — e.g. a ticker whose EDGAR
  fetch is unusually slow might indicate a retry loop or a rate-limit backoff being hit).

Use whatever timing mechanism is idiomatic for the existing codebase (e.g. `time.perf_counter`)
— don't introduce a new dependency for this.

## Step 4 — Redirect quality flags to the report instead of printing

`quality.py`'s `check_data_quality` (or wherever the below-threshold flag output currently
prints to the terminal) needs to be collected into a structured list instead of printed,
**for this full-refresh run specifically** — do not remove or break the existing
print-to-terminal behavior used during normal ad-hoc single/few-ticker runs. Implement this as
a mode/parameter (e.g. a `collect_flags` list passed in, or a return value used instead of a
print) so the two call paths (normal ad-hoc use vs. full-refresh mode) both work correctly
afterward — confirm the ad-hoc path still prints as before once this is done.

Organize the collected flags in the report sensibly (e.g. grouped by profile, then by ticker,
sorted alphabetically) rather than as one flat dump in whatever order they happened to be
generated.

## Step 5 — Generate the report document

One output file (e.g. `full_refresh_report.md`, or whatever format is consistent with this
project's other generated reports) containing:
1. Run metadata: start/end timestamp, total active tickers processed, total wall-clock time.
2. Timing section: the three phases' totals, per-ticker averages, and slowest-10 lists from
   Step 3.
3. Quality-flags section: every flag collected in Step 4, organized as described.

## Step 6 — Wire this into `main.py` so running it "just happens"

Modify `main.py` so that executing it performs this entire full-refresh sequence — the user
wants to run it with no other manual steps. Confirm you're not breaking any other existing
entry point or import this project relies on (e.g. if other scripts import functions from
`main.py`, importing it should not have the side effect of triggering a full refresh — only
running it directly should). Check how `main.py` is currently structured (e.g. an
`if __name__ == "__main__":` guard or equivalent) before deciding where this logic belongs.

## Step 7 — Validate against a small subset before recommending a full run

Given this is a destructive, long-running operation (deletes all cache, re-fetches ~500
tickers' worth of EDGAR + yfinance data), **test the full mechanism end-to-end against a small
subset first** (e.g. 3-5 tickers, temporarily) rather than validating only by code review.
Confirm:
- The delete step only removes what it should.
- Both fetch phases complete and populate the cache correctly.
- Timing numbers are sane (non-zero, non-absurd).
- The quality-flags report section is populated correctly and the terminal stays quiet for
  those tickers during this mode.
- Re-running normal ad-hoc usage (a single ticker, outside full-refresh mode) still prints
  quality flags to the terminal as before — confirm this explicitly, since Step 4's change
  touches shared code.

Report the subset test results in the output document as proof the mechanism works, separate
from an actual full run (which the user will trigger themselves afterward).

## What this task does NOT do

- Does not actually run the full ~500-ticker refresh — that's the user's own subsequent action
  once this is built and validated on the subset.
- Does not change any metric calculation logic, any guard, any profile assignment, or any tag
  configuration — this is purely an orchestration/instrumentation/reporting feature.

## Output

One file, `full_refresh_implementation_report.md`: what was implemented in `main.py`/
`quality.py`/wherever else was touched, the exact report-document format produced, the Step 7
subset-validation results (including confirmation the ad-hoc terminal-printing path still
works), and a clear note that the full run itself is the user's next manual action.

No scratch scripts left behind (other than the small subset-test artifacts, which should be
cleaned up after validation, with their results already captured in the report).