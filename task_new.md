# Task: Metric Pickers — Item 7

**Read first:** `frontend_growth_chart_report.md` §5 (five findings that bear directly on this
item, especially #4 on the Streamlit picker's defaults), `frontend_fundamentals_chart_report.md`,
`frontend_valuation_chart_report.md` §1 (the design this extends), `streamlit_inventory.md` §2.2 and
§3.1, and `app.py`'s three `st.multiselect` calls with their surrounding code.

## Context

All three charts now build from raw series, and each builder already accepts a `concepts` narrowing
list — the valuation report's §1 established `selectPanels` and the growth report verified across
six request shapes that a request only ever narrows, never widens.

**The machinery is in place; this item is the control that drives it.** That makes it smaller than
it looks, and it makes the questions mostly product questions rather than technical ones.

**Explicitly NOT in this task:** no years slider (item 8), no comparison, no snapshot marker, no
outlier masking, no data tab, no reference views. No changes to `main.py`, `config.py`,
`figures.py`, `metrics.py`, `parsers/` or the export. No Streamlit changes — including the two
latent defects named below, which are findings to reproduce-or-not, not bugs to fix in `app.py`.

---

## Step 1 — What the Streamlit version actually does

Read all three `st.multiselect` calls and report each: the label, the options, the default, the key,
and what happens when the selection is empty.

**Two of them contain a defect the growth report found**, and the brief for this item has to decide
what to do about it rather than porting it blindly:

```python
default = [i for i in ids if i in ("Revenueyoy_growth")]   # app.py:916
default = [i for i in ids if i in ("pe_ratio")]            # app.py:928
```

Those are **strings, not tuples**, so `in` is a substring test. `"Revenue" in "Revenueyoy_growth"`
is true, and so is `"pe_ratio" in "pe_ratio"` — both happen to select the intended single metric, by
coincidence rather than by expression. Confirm this reading against the code, then state what the
*intended* default set is and implement that. A rebuild that ports the coincidence would be
reproducing a bug in the name of fidelity.

Also establish: what does the fundamentals picker default to, and is it the same shape?

## Step 2 — Design

State each decision.

1. **Where the selection state lives.** One selection per chart, or one shared across all three?
   They have different catalogues and the growth report showed 19 of 24 profiles share a growth
   catalogue of 7 while valuation has 13 — a shared state would be meaningless across them. If
   per-chart, say where it sits relative to `ChartView`.
2. **What happens on ticker change.** The catalogue changes with the profile — a `standard` ticker
   offers 9 valuation metrics, a `financial` one a different 9. A selection carried across a ticker
   switch may name metrics the new ticker does not offer. Decide: reset to default, intersect with
   the new catalogue, or something else. State the reasoning; this is the decision a user notices.
3. **Empty selection.** All three builders return no figure for an empty request — the growth report
   tested this on both sides. Decide what the UI shows. Note that this is a different state from
   "this ticker has no data for any of these metrics", which is the item 17 case.
4. **Label or id in the control.** The registry carries both, and the panel titles show ids while
   the y-axes show labels (item 4's finding). Pick one for the picker and justify it — this is the
   first place a user reads a metric name outside a chart.
5. **Ordering.** The catalogue order is authoritative for rendering. Decide whether the picker
   presents metrics in that order too, and whether the selection's own order is preserved anywhere
   (it is not, in the builders — the growth report verified a reversed request comes back in
   catalogue order).

## Step 3 — Implement

Wire the three pickers to the three builders' `concepts` option. Reuse the existing registry load
and `selectPanels`; do not add a second path for computing what a ticker offers.

Note what the builders already return: the growth report records that they report the full
`offerable` list even when the request is empty or the frame is missing. Use that rather than
recomputing the option list separately — a second computation is a second thing that can drift from
`is_hidden`.

**The narrowing rule is the one hard constraint.** A picker must not be able to surface a metric
that `profile_visibility` hides for the ticker. The builders enforce this already; the picker must
not offer it in the first place, so a user never sees an option that would silently do nothing.

## Step 4 — Verify

1. **Option lists match `get_plottable_metrics`** for every (chart, ticker) pair in a set spanning
   all 24 profiles — same ids, same order. The registry export verified the underlying equivalence
   over all 1,827 pairs; this verifies the UI path reaches the same answer.
2. **A hidden metric cannot be selected**, tested directly: attempt to drive a selection containing
   an id hidden for the ticker's profile and confirm the rendered panel set is unchanged.
3. **Narrowing produces the right grid.** For several tickers, a subset selection must produce the
   panel set and the grid dimensions `_make_grid` gives for that count — 1, 2, 4, 7 and the full
   catalogue at minimum. The figures must match `build_*` called with the same `concepts` list.
4. **Empty selection** behaves as Step 2.3 designed, on all three charts.
5. **Ticker switch** behaves as Step 2.2 designed, including the case where the outgoing selection
   names a metric the incoming ticker does not offer.
6. **Items 4, 5 and 6 unchanged** — the full-catalogue path must produce byte-identical specs to the
   current baseline for all three charts.
7. `npx tsc -b`, `npx eslint .`, `npx vite build` clean. Nothing outside `frontend/` changed.

## Output

One file, `frontend_pickers_report.md`:

1. The Step 1 reading of the Streamlit defaults, including the substring defect and what the
   intended defaults are.
2. The Step 2 decisions with reasoning — especially the ticker-switch behaviour.
3. What was implemented, by file.
4. The Step 4 results, with the option-list comparison across profiles.
5. Confirmation that the three charts' full-catalogue output is unchanged.
6. Anything the reference or the existing frontend turned out to be that items 8, 12, 13, 14 and 17
   should know.

No scratch files left behind.