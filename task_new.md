# Task: The "No Data" Placeholder Lands on the Wrong Panel

**Read first:** `frontend_valuation_chart_report.md` — especially §4.1, which claims this was
verified — and `figures.py`'s `_annotate_no_data` and `plot_metric` as the reference. Then
`frontend/src/charts/panel.ts`.

## The observed defect

Rendering AEP's valuation chart in a browser:

- **Panel 1 (`pe_ratio`) has data *and* a red "No Data" annotation**, and its x-axis is wrecked:
  the dates render as dense vertical categorical labels instead of `%Y` ticks at a 2-year interval.
- **Panel 6 (`dividend_yield`), which genuinely has no data, shows nothing at all** — no
  annotation, no axes.

So the placeholder treatment — the annotation *and* the axis blanking that goes with it — is being
applied to the wrong subplot, and the panel that should receive it receives nothing.

**This is a recurrence.** The same class of bug hit the Streamlit implementation during the Plotly
migration, and the Phase 1 report recorded the cause: annotations in a subplot grid must be placed
either with plotly.py's `row`/`col` arguments, which resolve the reference internally, or with an
explicitly numbered domain reference. An unnumbered `"x domain"` / `"y domain"` refers to the
**first** axis regardless of which cell was intended.

**Verify the cause before fixing it.** The above is a strong hypothesis from the symptom pattern
and the project's history, not an established fact. Establish what the code actually emits.

## Part 1 — Why the verification passed

Before touching the rendering code: `frontend_valuation_chart_report.md` §4.1 states that subplot
titles, "No Data" counts, **all 196 axis objects** and every shape were compared against
`build_valuation` and found identical. That check ran and reported success while this defect was
present.

**Determine exactly what the comparison did not cover**, and report it. Candidates to check rather
than assume:

- whether annotations were compared at all, or only counted;
- whether `xref` / `yref` were among the compared fields;
- whether the axis comparison covered the properties the blanking modifies (`visible`, `showgrid`,
  `zeroline`, `type`, `dtick`, `tickformat`) or only domain and anchor;
- whether plotly.py's own output was read correctly — its annotations carry resolved references,
  and a comparison that normalised them away would match anything.

This matters more than the fix. Six further items build on this layer and will be verified the same
way; a check with a hole in it is worse than no check, because it produces a report that says the
thing works.

## Part 2 — Diagnose

Emit the figure spec for a ticker with at least one empty panel that is **not** the first one — AEP
is the observed case — and inspect what is actually produced:

1. Every annotation: its text, its `xref` and `yref`, its `x` and `y`.
2. Every axis object the placeholder path modifies.
3. The same three from `build_valuation` for the identical ticker and data.

State the difference plainly. If the hypothesis above is right, say so with the evidence; if the
cause is something else, the diagnosis is the finding.

**Also check whether the mean-line annotation has the same problem.** It is placed the same way —
top-left of its panel, via a domain reference — and the screenshot shows `Ø` labels on panels that
do have data, so it may be correct, or it may be landing on panel 1 too and merely looking
plausible there. Panel 1's `Ø (harm.) 17.0` should be checked against what `pe_ratio`'s mean
actually is.

## Part 3 — Fix

Correct the reference so each panel's furniture lands in its own cell. Two constraints:

1. **The fix belongs in the shared layer**, `charts/panel.ts` — `drawPanel` and `createGrid` are
   what items 5, 6, 12, 13 and 14 reuse. A fix applied at the valuation chart's call site would
   leave the same bug waiting for the next chart.
2. **Axis numbering in plotly is not uniform**: the first subplot's axes are `xaxis`/`yaxis` and
   are referenced as `"x"`/`"y"`, while subsequent ones are `xaxis2`, `xaxis3` and `"x2"`, `"x3"`.
   Whatever numbering helper exists must handle cell 1 correctly — that asymmetry is a likely place
   for an off-by-one to hide, and a fix that works for panels 2–13 and breaks panel 1 would look
   correct in every screenshot that has data in the first cell.

Do not restructure beyond what the fix requires.

## Part 4 — Close the verification hole

Extend the comparison so this defect could not pass again. At minimum:

- **Annotations compared field by field** against plotly.py's — text, resolved reference, position —
  not merely counted.
- **The placeholder's axis modifications** compared per axis, not just domain and anchor.
- **A ticker whose empty panel is not the first** must be in the verification set. The original set
  had empty panels but the check apparently could not tell which panel they were on; a set that
  cannot distinguish panel 1 from panel 6 is the hole.

Then re-run the full comparison from the original report and confirm the other claims still hold —
panel sets, mean values and labels, the grid, percent axes.

## Part 5 — Verify

1. **AEP renders correctly**: `pe_ratio` draws its data with a proper `%Y` x-axis and no
   placeholder; `dividend_yield` shows the red "No Data" with its own ticks and grid switched off.
2. **The spec matches `build_valuation`** for AEP, annotation by annotation and axis by axis.
3. **At least three more tickers** whose empty panels sit in different cells — including one where
   the empty panel *is* the first — produce matching specs.
4. **The tickers from the original report still match**, so the fix did not trade one defect for
   another.
5. **`npx tsc -b`, `npx eslint .` and `npx vite build`** all clean.
6. **Nothing outside `frontend/` changed** — confirm by diff.
7. State what was verified from the spec and what, if anything, was confirmed in a browser.

## Output

One file, `no_data_placeholder_fix_report.md`:

1. **Part 1: why the original verification passed** — the specific gap, named.
2. The diagnosis, with the actual emitted references against plotly.py's.
3. Whether the mean-line annotation shares the defect.
4. What was fixed and where, and why it belongs in the shared layer.
5. The extended checks, and the re-run of the original comparison.
6. The Part 5 results.

No scratch files left behind.