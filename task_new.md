# Task: Plotly Migration — Phase 1 (Core Per-Ticker Chart Migration) — REV 2

## Goal

Replace matplotlib with Plotly for this project's three chart-producing functions
(`plot_fundamentals`, `plot_growth`, `plot_valuation`, and the `plot_metric`/`plot_metric_dual`
helpers they use) — same data, same per-ticker scope as today, but interactive (native
Plotly zoom/pan/hover, and legend-click-to-toggle a trace), and outputting **both** a
standalone self-contained HTML file and a JSON representation per chart (the JSON is for the
future web app to render client-side with `plotly.js`; the HTML is for viewing today without
one).

**This phase changes only the rendering backend. It must not change what gets plotted or
why.** Every existing config-driven selection/hiding decision
(`is_hidden`, `FUNDAMENTALS_TO_PLOT`, `VALUATIONS_TO_PLOT`, `GROWTH_PANELS`,
`QUARTERLY_COUNTERPART`, `HARMONIC_MEAN_CONCEPTS`) stays exactly as it is in `config.py` —
this task reads that config, it does not modify it.

**Secondary motivation (state it, honor it):** the current `figures.py` uses global pyplot
state (`plt.subplots(...)` / `plt.close(fig)`), which is not thread-safe and blocks the web
migration. The Plotly version must construct plain figure objects with **no module-level or
global mutable state**, so the functions are safe to call from multiple threads/requests.

**Standing requirement as always: nothing may regress** in the sense of "what gets shown" —
verify that programmatically (compare the set of concepts/panels rendered against what the
current matplotlib version would render for the same ticker/data), not by eyeballing images.

## Step 1 — Read the current implementation fully before changing anything

Read `figures.py` in full and `config.py`'s relevant sections in full
(`FUNDAMENTALS_TO_PLOT`, `VALUATIONS_TO_PLOT`, `GROWTH_PANELS`, `QUARTERLY_COUNTERPART`,
`HARMONIC_MEAN_CONCEPTS`, `is_hidden`). Also grep every caller of
`plot_fundamentals`/`plot_growth`/`plot_valuation` in `main.py` (both the ad-hoc path and
`run_full_refresh()`) to confirm exactly how `output_path` is currently constructed and used,
since this task needs to produce two files per chart instead of one.

**Known fact — do not get this wrong:** `plot_growth` is driven by the **static
`GROWTH_PANELS` list** (three concept-level panels: `"Revenue"`, `"NetIncomeLoss"`,
`"SharesOutstanding"`, plotted from the `facts` dataframe's `yoy_growth` column).
`get_growth_panels()` / `GROWTH_BASE_PANELS` / `GROWTH_PROFILE_EXTRA` are **not imported by
`figures.py` at all**. Grep for their actual consumer(s) elsewhere in the project so you know
what they drive — but do not verify `plot_growth`'s panel set against `get_growth_panels()`;
that would be verifying against the wrong list.

**Known fact — `is_hidden` namespaces:** `is_hidden(ticker, name)` is called with two
different kinds of names: metric names like `"roe"`/`"fcf_margin"` (fundamentals/valuation
paths) and capitalized concept names like `"Revenue"` (growth path). It also internally
strips a `_quarterly` suffix and applies derived-concept-consumer logic. The migration must
pass through the **exact same strings** the current code passes — no normalization, no
lowercasing, no renaming.

## Step 2 — Design decisions to make explicit before implementing

State your approach for each of these (they're real design choices, not implementation
details to skip past):

1. **File naming for the dual output.** Given the current single `output_path` parameter,
   decide how the HTML and JSON outputs are named/organized (e.g. same stem, `.html`/`.json`
   extensions) and whether the function signature needs to change to reflect this, or whether
   a single `output_path` (treated as a stem) is cleaner. Note that current callers likely
   pass a `.png` path — decide and document how that's handled at the call sites.
2. **Subplot grid equivalent.** Match `_make_grid`'s row/column logic using Plotly's
   `make_subplots`, preserving the same layout behavior. Plotly has no `ax.axis("off")` for
   unused trailing grid cells — prefer simply not creating trailing empty subplots over
   creating-then-hiding them.
3. **`symlog`.** Confirmed current state: **no metric in `FUNDAMENTALS_TO_PLOT` sets the
   symlog flag** (every 5th tuple element is `False`), and `plot_valuation` never passes it.
   The decision therefore reduces to: (a) drop the `symlog` parameter entirely (simpler,
   honest — nothing uses it), or (b) keep the parameter for signature parity with a
   documented plan (e.g. log-modulus transform) should it ever be enabled. Pick one, state
   it in the report, and do not spend effort implementing a symlog rendering path that
   nothing exercises.
4. **"Keine Daten" placeholder.** Plotly equivalent of the current `ax.text(...)` box — a
   Plotly annotation on an otherwise-empty subplot, styled consistently with the current red
   "keine Daten" treatment.
5. **Percent formatting, reference lines (`axhline`), and the harmonic/arithmetic mean
   legend label.** Map each to its Plotly equivalent (`tickformat`, `add_hline` or shapes,
   and a legend entry or annotation for the mean line) — confirm the mean-line calculation
   itself (`harmonic_mean` from `metrics.py`) is reused unchanged, not reimplemented. Note:
   `add_hline`/shapes don't produce legend entries by default — if the current mean-line
   label (e.g. `Ø (harm.) 23.4`) is conveyed via legend today, decide how it's conveyed in
   Plotly (legend-carrying line trace vs. annotation) and keep the displayed number
   identical.
6. **`plot_metric_dual`'s TTM+quarterly overlay.** For Phase 1, preserve the current behavior
   (both series always visible, distinguished by line weight/opacity) as two Plotly traces on
   the same subplot — the button-based toggle between them is explicitly Phase 2's job, not
   this one.
7. **`plot_growth`'s degenerate cases (currently underspecified in the code — define them
   explicitly):**
   - If `growth_column not in facts.columns`, the current code silently `return`s and
     **produces no file at all**. In the dual-output world, decide the behavior (skip both
     files consistently and log a warning is acceptable; producing one of the two files is
     not) and document it — callers and the future web app must be able to rely on
     "either both files exist or neither does".
   - `plot_growth` does **not** use `_make_grid`; if every panel were hidden for a ticker,
     `plt.subplots(1, 0)` would crash today. Define the zero-panel behavior for the Plotly
     version (skip-with-warning or placeholder figure — pick one, apply it consistently
     across all three plot functions).

## Step 3 — Implement

Build the Plotly versions of `plot_metric`, `plot_metric_dual`, `plot_fundamentals`,
`plot_growth`, and `plot_valuation`, following the design decisions from Step 2. Keep the same
function names and call signatures where reasonably possible so `main.py`'s callers need
minimal changes — but do change what's necessary for the dual-output requirement, and update
every caller found in Step 1 accordingly.

No global state: no module-level figure registries, no reliance on any Plotly/pyplot global —
each function builds, writes, and returns/discards its own figure object.

Remove the matplotlib import and usage from `figures.py` once the migration is complete —
confirm no other file in the project still depends on the matplotlib-based versions before
removing them (grep, don't assume).

## Step 4 — Verify programmatically, not visually

For at least three tickers spanning different profiles (pick ones with meaningfully different
hidden-metric sets, e.g. one `standard`, one `financial` or `insurance_pc` with many standard
metrics hidden, and one `reit`), confirm:
- The set of panels/concepts actually rendered in the new Plotly output matches exactly what
  `is_hidden()` + `FUNDAMENTALS_TO_PLOT` / `VALUATIONS_TO_PLOT` / **`GROWTH_PANELS`** (not
  `get_growth_panels()`) says should be shown — compare programmatically (e.g. inspect
  `fig.data`/subplot titles against the expected list), not by looking at a picture.
- Both the HTML and JSON outputs are actually produced, are non-empty, and the JSON is valid
  and parses back into a structure describing the same figure (e.g. via
  `plotly.io.from_json` and re-checking the trace/subplot count).
- Reference lines, percent formatting, and mean-line labels appear with the correct values
  (spot-check actual numbers against the source dataframe for a couple of panels — including
  at least one harmonic-mean multiple from `HARMONIC_MEAN_CONCEPTS` and one arithmetic-mean
  one, since both paths exist).
- The `plot_growth` degenerate-case behavior from Step 2.7 behaves as designed (test it,
  e.g. by passing a dataframe without the growth column).

There is no symlog verification case — no current metric uses it (see Step 2.3).

## Output

One file, `plotly_migration_phase1_report.md`: the design decisions from Step 2 (with
reasoning, especially for the symlog keep-or-drop call and the degenerate-case behavior),
what was implemented, the verification results from Step 4, and confirmation of what was
removed (matplotlib usage) and why it was safe to remove.

No scratch scripts left behind. Do not touch `config.py`'s plotting-selection logic, and do
not implement any Phase 2/3/4 capability (toggle buttons, ticker overlays, or cross-sectional
plots) in this task — this is the rendering-backend swap only.