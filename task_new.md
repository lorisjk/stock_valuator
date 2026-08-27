# Task: Display Formatting and Table Sizing — Item 10

**Read first:** `frontend_data_tab_report.md` §"Item 10" (the boundary this task starts from — it
states plainly that none of the three rules are implemented and full precision is currently *more*
informative than the reference, which is the correct interim state, not a defect), `streamlit_inventory.md`
§3.4, `frontend_chart_width_regression_report.md` (the `check-chart-width.mjs` precedent — this task
should follow the same "verify by failing" discipline for its own new check), and `app.py`'s
`format_for_display`, `ABSOLUTE_THRESHOLD` and `_percent_applies` as the reference implementation.

## Context

Two things the operator flagged directly from the built data tab:

1. **Raw numbers render unscaled** — `82300000000` instead of `82.3B`, `39544000000` instead of
   `39.5M`-or-similar. The reference already solves this (`format_for_display`); item 9 deliberately
   left it unbuilt and said so.
2. **Tables render at a fixed size regardless of content**, so a table with few rows or a narrow
   set of columns shows mostly empty space. Item 9's report flagged this too (§"conclusion",
   "correct and wide").

This task builds the display formatting split and fixes the table sizing. It does **not** touch
what data feeds the tables or what a CSV download contains.

**Explicitly NOT in this task:** no CSV/copy-block work (item 11 — if the CSV path needs a one-line
change to stay decoupled from the new display formatting, make it, but do not build item 11's
scope). No cadence markers (item 19) or quality-flag section (item 18). No changes to the three
chart builders, `panel.ts`, `grid.ts`, `mean.ts`, the pipeline, or the export. No changes to the
chart-width fix from the previous cycle — do not touch `App.tsx`'s tab-switch resize effect.

---

## Step 1 — Read the reference exactly

Report each of the following with its source line, the way the last several cycles have had to
correct assumptions about `app.py` more often than not:

1. **`ABSOLUTE_THRESHOLD` and the scaling rule** — the exact breakpoints (thousand / million /
   billion / trillion, or whatever the real cutoffs are) and the exact suffix and decimal-place
   convention for each (`format_for_display`'s output for a range of real magnitudes: hundreds,
   low-thousands, exactly-at-a-breakpoint, negative values).
2. **`_percent_applies`** — what determines whether a value in the data tab is treated as a
   percentage versus an absolute figure. The registry already carries a `percent` flag per metric
   for the chart path (established in the registry-export cycle); confirm whether the data tab's
   rule is the same flag, a different one, or a name-based heuristic — and if the latter, whether
   it is the same one that caused the earlier raw-facts percent bug (`Revenue`/`NetIncomeLoss`/
   `SharesOutstanding` colliding across chart and growth namespaces).
3. **Which columns get which treatment.** The five sections have different content — raw/derived
   facts (mixed absolute figures and ratios), metrics (mostly ratios and percentages), valuation
   (multiples), snapshot (mixed, including non-numeric fields like `days_since_last_filing`). State
   per section which columns are scaled, which are percent-formatted, and which are left as-is
   (counts, flags, dates).
4. **Per-share and small-ratio values.** Confirm the reference does not scale a P/E ratio or an EPS
   figure with the same `K`/`M`/`B` logic it applies to `debt` or `cash` — these coexist in the
   metrics and snapshot sections and a blanket scaling rule would misformat one or the other.

## Step 2 — Design the boundary between display and export

This is the one architectural decision in this task and it has already gone wrong once (the raw
facts percent bug) by conflating a metric's *chart* formatting with its *table* formatting.

1. **A single formatting function**, analogous to `format_for_display`, taking a value and whatever
   metadata it needs (percent flag, magnitude) and returning a display string. State its signature.
2. **Full precision is preserved separately.** The underlying data used for the CSV/copy path
   (owned by item 11, but currently produced by this task's pivot) must remain untouched — the
   display function wraps the render, it does not replace the stored value. Verify this by
   construction: the formatting function must take a value and return a string, never mutate the
   frame the CSV path reads.
3. **Where the percent/scale decision comes from.** Reuse the registry's `percent` field for metric
   and valuation columns, exactly as the chart path does. For raw and derived facts, which have no
   registry entry (they are not in `METRICS`), decide the rule from what Step 1.4 established, and
   state explicitly why it cannot use the same registry lookup the metrics section uses — this is
   precisely the distinction whose absence caused the earlier bug, so name it rather than
   re-deriving it silently.
4. **Table sizing.** State the fix: size to content (natural table height/row count) rather than a
   fixed container height, with a cap and scroll for genuinely large tables if one is warranted —
   measure the largest real case (`facts_full` pivot for a long-history ticker) before deciding
   whether a cap is needed at all or whether natural sizing is sufficient.

## Step 3 — Implement

Apply the formatting function to the four sections that display numeric tables (raw/derived facts,
metrics, valuation, snapshot) and the table-sizing fix to all five sections' containers.

Do not change the pivot logic, the null handling, or the raw/derived split established in item 9 —
this task changes how a cell's value is *rendered*, not which cells exist.

## Step 4 — Verify

1. **Every formatted value matches `format_for_display`'s output** for the same input, across the
   full range from Step 1.1 — not spot-checked, but for a real ticker's full facts/metrics/valuation
   tables, every displayed string compared against the reference's output for the same underlying
   value.
2. **Percent columns format as percentages and scaled columns format as `K`/`M`/`B`/`T`, and neither
   set is applied to the other** — verify explicitly on a ticker whose metrics section has both a
   ratio (e.g. `roe`) and an absolute figure (e.g. `debt`) to confirm the two get different
   treatment from the same table.
2. **The underlying data is untouched.** Confirm the frame the CSV export reads still contains full,
   unrounded precision — re-run whatever check item 11's predecessor (item 9) used for this, since
   it already established the CSV must never read from a formatted display value.
3. **Table sizing**: for a small table (few rows) and a large one (`facts_full`), confirm the
   container no longer renders fixed-height empty space for the small case, and confirm the large
   case's behaviour (natural growth, or scroll-with-cap) matches what Step 2.4 decided, with actual
   measured dimensions.
4. **The chart-width fix from the previous cycle is unaffected** — run `check-chart-width.mjs`
   (built in that cycle) and confirm 24/24 still pass. This task should not go near `App.tsx`'s
   resize effect, and this is the check that proves it didn't.
5. **The three charts are unchanged as data** — re-run the item 8 harness and confirm the standing
   sha256 baseline (`1987837d...`, per the last cycle) is unchanged.
6. `npx tsc -b`, `npx eslint .`, `npx vite build` clean. Nothing outside `frontend/` changed.

## Output

One file, `frontend_display_formatting_report.md`:

1. The Step 1 reference reading, each point with its source line.
2. The Step 2 design decisions, especially the percent/scale source for raw facts versus registry
   metrics, and the table-sizing decision with its measurement.
3. What was implemented, by file.
4. The Step 4 verification results, especially the full-range format comparison and the
   CSV-untouched confirmation.
5. Confirmation the chart-width fix and the three charts are unaffected.
6. Anything item 11 (CSV/copy blocks) should know about the boundary this task drew.

No scratch files left behind.