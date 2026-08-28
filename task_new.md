# Task: The Empty-Panel Notice — Item 17

**Read first:** `frontend_raw_facts_chart_report.md` §5.2 (the open question this task must resolve
first: is the reference's notice valuation-only by design or by omission, given the raw facts chart
produces "No Data" panels just as routinely), `frontend_as_of_control_report.md` §4.6 (the empty-
result case at an extreme `as_of` — 295 "No Data" panels in one sweep, the closest existing measurement
of how bad this gets), `frontend_data_tab_report.md` (the data tab's own null-column caption — a
related but distinct feature; confirm the boundary before assuming this task extends it),
`streamlit_inventory.md` §2.2 and §3.3, and `app.py`'s empty-panel notice code (likely near
`empty_valuation_panels` or similar, per the raw-facts report's naming) as the reference.

## Context

Every chart in this frontend already has a per-panel "No Data" placeholder (the bare-axis-id
mechanism from the placeholder-fix cycle, structurally sound and unchanged since). What's missing is
a **chart-level** summary: when several panels in a grid are empty — a narrow years window, a ticker
with sparse data, an aggressive `as_of` — the reference apparently tells the reader that at the chart
level, not just leaves them to notice several red "No Data" boxes on their own.

**This task starts with a scope question the last cycle raised and did not answer**: is this
valuation-only in the reference, or does it belong wherever multi-panel grids exist? Answer this from
the code before designing anything — the raw facts chart's 202 empty panels in one verification sweep
is a real signal that the reference might already handle this generally, or might have a real gap
this task should document rather than silently extend past what `app.py` does.

**Explicitly NOT in this task:** no changes to the per-panel "No Data" placeholder mechanism itself
(structurally correct, verified across six chart types now). No changes to the data tab's null-column
caption (a different feature — confirm and respect the boundary). No changes to outlier masking,
the snapshot marker, or the as-of control's own logic. No changes to `panel.ts`'s core drawing
functions beyond what's needed to read/report emptiness, which likely already exists (`PanelSpec.empty`
per item 4's original design).

---

## Step 1 — Resolve the scope question first

1. **Does `app.py` have this notice at all, and if so, where** — search for it near the valuation
   tab, and confirm whether the fundamentals, growth, comparison, or raw facts tabs have anything
   equivalent. State the exact scope as the reference actually ships it, not as the inventory
   summarized it.
2. **If it is valuation-only by explicit design**, find the reasoning (a comment, a docstring) —
   the raw-facts report speculated this might be deliberate; confirm or refute.
3. **If it is valuation-only with no stated reason**, that is the "omission" case the last cycle
   flagged. State plainly whether you think it should extend to other charts and why, but **do not
   extend it beyond the reference without saying so explicitly and treating it as a deviation** —
   this project's standing discipline is to port the reference faithfully and flag disagreements,
   not to silently improve on it.
4. **The exact trigger and content**, wherever it appears: a count threshold (any empty panel, or
   only when more than N are empty), the message text, and whether it differentiates *why* panels
   are empty (narrow window vs. no data at all vs. `as_of` set) or reports a flat count.

## Step 2 — Design

1. **Where this task's changes go**, based on Step 1's scope finding — likely only the valuation
   chart's view component, possibly the comparison chart if Step 1 finds it in scope there too.
2. **The data source for the notice**: `PanelSpec.empty` (or equivalent) already exists per-panel
   in the shared layer per item 4's design; this notice is very likely just a `filter` + `count`
   over the already-built panel specs, not a new computation. Confirm this is sufficient before
   building anything that re-derives emptiness independently — a second emptiness computation that
   could disagree with the panels actually drawn would repeat exactly the failure mode
   `outlier_report`'s co-derivation was built to prevent (item 14, figures.py's own comment: "the
   control could name points the chart does not draw, or miss ones it does").
3. **Interaction with the years window and as-of**: since both can independently make panels empty
   (item 8, item 15), confirm the notice recomputes correctly as either control moves, using the
   same "state holds raw intent, effective value is derived" pattern established since the pickers
   cycle.

## Step 3 — Implement

Add the notice, matching Step 1's exact scope, trigger, and message.

## Step 4 — Verify

1. **Against the reference, exactly**: for a sample of tickers/windows/as-of settings producing a
   range of empty-panel counts (zero, a few, many — reuse the as-of report's extreme
   `as_of = 1990-01-01` case for the "many" end), confirm the notice's presence/absence and its exact
   text matches `app.py`'s output.
2. **The notice tracks the actual drawn panels**, not a separately-computed count: pick a scenario,
   verify the reported count equals the number of "No Data" panels actually rendered in that figure,
   for several tickers.
3. **It updates correctly** as the years slider and the as-of control move independently, without a
   page reload or stale count.
4. **Scope discipline**: if Step 1 found this valuation-only in the reference, confirm the notice
   does **not** appear on fundamentals, growth, comparison, or raw facts — even in scenarios (like
   the raw facts chart's 202-empty-panel sweep from the last cycle) where it would seem useful. If
   you deviated from the reference's scope, this check instead confirms the deviation was applied
   consistently and is documented, not silently inconsistent.
5. **Nothing else regressed**: `check-chart-width`, `check-tab-state`, `check-table-format` at their
   current baselines (36/36, 13/13, 6,107/6,107 per the last cycle), and A/B sweeps against the
   established item 8/11/12/13/14/15/16 baselines (reverted-tree method).
6. `npx tsc -b`, `npx eslint .`, `npx vite build` clean. Nothing outside `frontend/` changed.

## Output

One file, `frontend_empty_panel_notice_report.md`:

1. The Step 1 scope resolution — exactly where the reference has this, with source lines, and the
   explicit decision on whether this port matches that scope or deviates (with reasoning, if so).
2. The Step 2 design decisions, especially confirming the notice derives from existing panel specs
   rather than a second computation.
3. What was implemented, by file.
4. The Step 4 verification results, especially the count-matches-drawn-panels check.
5. Anything item 18 (quality-flag summary) or item 19 (cadence markers) should know.

No scratch files left behind.