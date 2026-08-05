# Task: Parametrize the Figure Builders for an Interactive Caller

**Depends on the comparison-cleanup task being complete and shipped** — `figures.py` already has
the `build_*` / `plot_*` split (`build_fundamentals`, `build_growth`, `build_valuation`,
`build_ticker_comparison` plus their file-writing wrappers). Read `comparison_cleanup_report.md`
and the current `figures.py` in full before changing anything.

## Context — why this task exists

The builders return figure objects now, but they still make three decisions internally that an
interactive caller needs to make from the outside: **which panels to draw**, **how wide the
figure is**, and **what "today" means for the valuation window**. Each of these blocks a
concretely planned feature:

| internal decision today | blocked feature |
|---|---|
| panel list computed from `is_hidden` + config only | user unchecks metrics in the UI and the grid re-tiles to use the freed space |
| `width=500*cols` hardcoded in `update_layout` | responsive rendering via `st.plotly_chart(fig, use_container_width=True)` |
| `pd.Timestamp.today()` as the valuation cutoff anchor | user-selectable as-of date (`build_snapshot_as_of`), where the window must run from the chosen date, not from today |

This task makes those three parameters, and does nothing else of substance.

**Explicitly NOT in this task:** no Streamlit code, no Streamlit import in `figures.py`, no Phase 4
(cross-sectional/peer plots), no change to `config.py`'s selection logic, no fix for the
`V`/`STZ` missing-`SharesOutstanding` finding. `figures.py` stays a pure rendering module.

**Standing requirement:** default behaviour must not change. Every existing caller passes none of
the new parameters, and must produce byte-identical output to what it produces today. Prove that,
don't assert it (Step 4).

## Step 1 — Explicit panel selection

Add an optional parameter to `build_fundamentals`, `build_growth` and `build_valuation` letting
the caller restrict which panels are drawn — e.g. `concepts: list[str] | None = None`, where
`None` means "everything the config says is visible" (today's behaviour, unchanged).

Design points to decide and state:

1. **`is_hidden` stays authoritative.** An explicit list is a *narrowing* filter applied on top of
   the existing visibility rule, never a way around it: a caller asking for a concept that
   `is_hidden` hides for that ticker must not get it. State how you enforce this and make sure the
   same rule holds in all three builders.
2. **Unknown or already-hidden entries in the caller's list.** Decide the behaviour (ignore
   silently, ignore with a printed note, or refuse the call) and apply it consistently. Note that
   a UI-driven caller will routinely pass concepts that are fine for one ticker and hidden for
   another — so refusing outright is probably wrong; say what you chose and why.
3. **Ordering.** Decide whether the rendered order follows the config list order (recommended —
   it keeps a chart's panel order stable no matter what order the UI hands over) or the caller's
   list order. State the choice.
4. **Empty result.** A caller narrowing down to nothing (or to only hidden concepts) must hit the
   existing "nothing to build" path and get `None`, with the wrapper still writing neither file.

The grid must re-tile automatically: `_make_grid` already derives rows/cols from the panel count,
so a reduced list should produce a tighter grid with no extra work. Confirm that it does.

`build_ticker_comparison` is out of scope here — it already takes its concept explicitly.

## Step 2 — Make figure sizing controllable

All three per-ticker builders currently hardcode `width=500*cols` and a per-chart row height;
`build_ticker_comparison` hardcodes `width=900, height=520`. A fixed `width` in the layout fights
`use_container_width=True` in a web frontend.

Make width and height controllable, defaulting to exactly today's values so file output is
unchanged. Decide and state the shape: explicit `width`/`height` parameters, or a single flag
meaning "let the container decide the width" that omits `width` from the layout. Whichever you
pick, it must be possible for a caller to get a figure with **no** `width` set in
`layout` — that is the case the web frontend needs — and the report should show the produced
layout for both the default and the responsive call.

## Step 3 — Anchor the valuation window to a caller-supplied date

`build_valuation` and `build_ticker_comparison` both compute
`pd.Timestamp.today() - pd.DateOffset(years=years)`. Add an `as_of: pd.Timestamp | None = None`
parameter to both: `None` keeps today's behaviour (anchor on `pd.Timestamp.today()`), a supplied
date anchors the window on that date instead.

Two things to get right:

1. **The cutoff and the upper bound.** Today the filter is one-sided (`end >= cutoff`), which is
   fine when the anchor is today because no data lies in the future. With a historical `as_of`,
   a one-sided filter would still show data *after* the chosen date, which defeats the purpose.
   Decide whether supplying `as_of` should also bound the window above (`end <= as_of`) —
   recommended: yes — and state the reasoning, since this is the difference between "the last 5
   years as of that date" and "everything since that date".
2. **One expression, two call sites.** `build_valuation` and `build_ticker_comparison` must use
   the same windowing logic, not two copies that can drift. Factor it into a small helper if that
   is the clean way to guarantee it.

The wrappers `plot_valuation` / `plot_ticker_comparison` should pass the parameter through.

## Step 4 — Housekeeping (small, verify anyway)

- Remove the unused `from datetime import datetime` import (line ~14) — confirm by grep that
  nothing in the file uses it.
- `_make_grid`'s `n == 0` branch is unreachable now that every builder guards on an empty panel
  list before calling it. Either remove the branch or leave it with a comment saying it is a
  defensive no-op — state which and why. Do not change the non-zero logic.

## Step 5 — Verify

- **Default-path non-regression, the decisive check:** for at least three tickers spanning
  different profiles (e.g. one `standard`, one `financial`, one `reit`), all three chart types,
  confirm that calling each builder **with no new parameters** produces output byte-identical to
  what it produced before this task (compare `fig.to_json()` against a baseline captured before
  the change). Same for `build_ticker_comparison` on a real comparison.
- **Panel narrowing works and the grid re-tiles:** pick a ticker with many visible fundamentals
  panels, request a subset, and confirm the rendered subplot titles equal the expected narrowed
  set, that the grid dimensions match `_make_grid(len(subset))`, and that no trailing empty cells
  were created.
- **`is_hidden` cannot be bypassed:** request a concept that is hidden for the ticker's profile
  (e.g. `p_ffo` for a `standard` ticker, `efficiency_ratio` for a non-`financial` one) and confirm
  it is not rendered, and that the Step 1.2 behaviour you chose is what actually happens.
- **Narrowing to nothing** returns `None` and the wrapper writes neither file.
- **Responsive sizing:** confirm a figure can be produced with no `width` key in its layout, and
  that the default call still carries exactly today's width/height values.
- **`as_of` window:** for a real ticker, confirm that a historical `as_of` produces a strictly
  different, correctly bounded x-range than the default call (check the actual first and last
  x-values against the expected window, both bounds), that `as_of=None` reproduces today's
  x-range exactly, and that `build_valuation` and `build_ticker_comparison` agree on the same
  window for the same metric/ticker/date.

## Output

One file, `figures_parametrization_report.md`: the design decisions from Steps 1–3 with
reasoning (especially the unknown/hidden-entry handling and the `as_of` upper-bound question),
what was implemented, the housekeeping verdict from Step 4, and the Step 5 verification results
including the byte-identical default-path evidence.

No scratch scripts left behind.