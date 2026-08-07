# Task: App Refinements — Tab Order, Format Bug, Growth Expansion, Snapshot-in-Chart

**Depends on the data inspection layer being complete and shipped.** Read `data_tab_report.md`,
`metrics_registry_report.md`, `app_export_layer_report.md` and the current `app.py`, `figures.py`,
`config.py`, `main.py` before changing anything.

This task has four independent parts, ordered by risk. **Parts 1 and 2 are small and should be
finished and verified before starting 3 and 4.** Parts 3 and 4 both touch `config.py` and
`figures.py`, which have been stable for several tasks — treat them accordingly.

**Explicitly NOT in this task:** no Phase 4 (cross-sectional/peer scatter), no `PROFILE_HIDDEN`
structural refactor, no `SharesOutstanding` fix for `V`/`STZ`, no deployment work, no restyling
beyond what each part requires.

---

## Part 1 — Reorder the tabs

The data tab is currently last. Move it first, so the app opens on the data and the charts follow.
This is a presentation change only: no change to what each tab renders, no change to which tab is
selected by default beyond it now being the data tab.

Confirm nothing depends on tab order (e.g. index-based `st.tabs` unpacking elsewhere in the file).

---

## Part 2 — Fix the percent-formatting bug in the facts table

**Symptom:** in the raw facts table, `Revenue` and `SharesOutstanding` render as percentages
(e.g. an absolute dollar figure shown as `9,400,000,000.00%`) instead of scaled absolute values.

**Diagnosed cause — verify this before fixing, don't take it on faith.** `format_for_display`
resolves `percent` from `config.METRICS_BY_ID[concept].percent` as its first rule. The three
`CHART_GROWTH` registry entries are keyed by **XBRL concept name** — `Revenue`, `NetIncomeLoss`,
`SharesOutstanding` — and carry `percent=True`, correctly, because the growth charts plot YoY
percentages. The facts frame contains columns with those same three names holding **absolute
values**. The registry lookup therefore returns the growth metric's formatting for the raw fact.
`NetIncomeLoss` should be affected identically — check it and say so either way.

**The fix must address the namespace collision, not just the three symptoms.** A hardcoded
exception list for these three names would break again the moment a growth metric is added in
Part 3. The registry already distinguishes namespaces (`CHART_SPECS[...]["id_namespace"]` is
`"metric"` for fundamentals/valuation and `"xbrl_concept"` for growth) and each `Metric` exposes
`value_column`. Use that structure: the registry's `percent` flag describes a metric in the
**metric frames**, and must not be applied to a concept read from the **facts frame**.

Decide and state how the formatter learns which frame it is formatting (an explicit argument at
the call site is likely cleanest — the caller always knows). Facts columns then fall through to
the existing magnitude-based rule, which already renders `Assets` as `4.90T` correctly.

Verify with real values, comparing displayed strings against the source: `Revenue`,
`NetIncomeLoss` and `SharesOutstanding` in the facts table render as scaled absolutes; the same
three concepts still render as percentages in the **growth chart** axis; and metrics whose
registry `percent` flag is genuinely correct (e.g. `operating_margin`, `roe`) are unaffected in
the metrics table. Include a per-share concept (`EPS_TTM_CALC`) to confirm the magnitude fallback
still gives it decimals rather than a scaled unit.

---

## Part 3 — Expand growth coverage

**The problem:** the pipeline computes `yoy_growth` for far more concepts than it plots. The facts
frame carries 69 concepts with a `yoy_growth` column, and the growth chart shows **three**
(`Revenue`, `NetIncomeLoss`, `SharesOutstanding`). Growth in EPS, FCF, operating income, equity
and the sector-specific aggregates is computed and then discarded at render time.

### Step 3.1 — Survey what is actually available and reliable

Before proposing anything, measure across a real multi-profile ticker set (at minimum one
`standard`, one `financial`, one `insurance`, one `reit`, one retail/`industrial`):

- For every concept in the facts frame, how many tickers have usable `yoy_growth` (non-null
  count, and how far back the series runs).
- Which concepts are **TTM** vs. **quarterly** vs. raw — growth on a raw quarterly figure is
  seasonal noise for most businesses, growth on a `_TTM` series is the meaningful comparison.
  State this explicitly per candidate rather than treating all concepts alike.
- Which concepts produce **structurally unstable growth**: a series that crosses zero makes
  percentage growth meaningless or explosive (`NetIncomeLoss` for a company with a loss quarter,
  `FCF` likewise). Identify which candidates have this property and how often it actually bites
  in the real data — this is the single most likely way an expanded growth chart produces a
  plausible-looking but worthless panel.

Report the survey as a table. **Confirmed-not-suitable is a fully successful outcome for a
candidate** — this project prefers an honest gap to a forced panel.

### Step 3.2 — Propose the expansion, with per-profile assignment

Propose which concepts become growth panels, and for which profiles. Growth panels are not
universal: a bank's meaningful growth series is not a software company's. Concretely worth
evaluating (not a mandate — evaluate against Step 3.1's data):

- `EPS_TTM_CALC` growth — explicitly requested, and likely the single most useful addition
- `FCF_TTM`, `OperatingCashFlow_TTM`, `OperatingIncomeLoss_TTM` growth
- `StockholdersEquity` growth (already a `GROWTH_BASE_PANELS` name — see the note below)
- sector aggregates for `financial` / `insurance` / `reit` profiles

**Note the dead-code precedent.** `config.py` contains `GROWTH_BASE_PANELS`, `GROWTH_PROFILE_EXTRA`
and `get_growth_panels()` — a per-profile growth panel mechanism with **zero consumers**, confirmed
in the Phase 1 report. It names concepts like `fcf_growth` and `nii_growth`, i.e. someone already
sketched this expansion. Read it, say what it intended, and state explicitly whether your design
supersedes it (in which case propose deleting it) or revives it. Do not leave a third parallel
mechanism behind.

### Step 3.3 — Implement via the registry

New growth panels are new `METRICS` entries with `chart=CHART_GROWTH`. That is the whole point of
the registry — adding a metric should be one line.

Two constraints:

1. **Per-profile visibility runs through `is_hidden`, as everywhere else.** Do not build a second
   visibility mechanism for growth.
2. **Report the `PROFILE_HIDDEN` cost.** It is a negative list: every growth metric that applies to
   only some profiles needs hide entries for all the others. Count how many entries your proposal
   adds. If it adds a disproportionate number, **say so and flag it** — that is direct evidence for
   the known "negative list will not scale" problem, and a measured number is more useful than the
   general worry. Do not refactor `PROFILE_HIDDEN` here; report the number.

New growth panels appear in both the growth chart and the data tab automatically if both read the
registry. Confirm that they do, and fix the one that does not rather than special-casing.

### Step 3.4 — Verify

- Non-regression: the three existing growth panels render byte-identically for a ticker whose
  profile gains no new panels.
- Each new panel renders real data for the profiles it targets, and is correctly absent for the
  profiles it does not.
- At least one new panel checked numerically against the source frame's `yoy_growth` values.
- The data tab picks up the new concepts without a change there.

---

## Part 4 — The current snapshot as the final point in valuation charts

**Goal:** the user should see the current multiple against its own history without leaving the
chart — `build_snapshot()` already computes it, and `valuation_history` ends at the last period
end, so the most decision-relevant number is currently the one that is missing from the picture.

This is the most design-sensitive part of the task. Get the following right.

### 4.1 — The snapshot point must not enter the mean

`build_valuation` draws a mean line (harmonic for `HARMONIC_MEAN_CONCEPTS`, arithmetic otherwise)
over the plotted series. **The mean is the historical benchmark the current value is judged
against.** If the snapshot point is folded into the same series, it contaminates the very
comparison the feature exists to enable.

Implement it so the mean is computed over the historical series only, and prove it numerically:
the mean line's value and label must be **identical** with and without the snapshot point.

### 4.2 — It must be visually distinguishable from a filed period

A snapshot point is a different kind of observation: current market price against the latest
available fundamentals, not a value at a completed fiscal period end. Render it so a reader cannot
mistake it for a filed data point (separate trace with its own marker style and legend entry is the
obvious approach — state what you chose). Its hover text should say what it is and carry its
as-of date.

### 4.3 — Concept alignment must be verified, not assumed

Confirm that the snapshot frame's concept names match `valuation_history`'s for the plotted
multiples (`pe_ratio`, `p_tbv`, `p_ffo`, `ev_ebitda`, `dividend_yield`, …). The data-tab report
found the snapshot carries 76 concepts across 8 tickers including non-valuation ones like
`shares_basis`. Report the actual overlap. Any valuation concept **without** a snapshot
counterpart simply gets no extra point — that panel renders exactly as today.

### 4.4 — Interaction with `as_of`

`build_valuation` accepts `as_of` for historical windows. The snapshot is as of the pipeline run
date. Appending a run-date point to a chart windowed to a past date would show the user data that
date could not have known — the exact error `as_of` exists to prevent.

Decide and state the rule; the recommended one is: **suppress the snapshot point whenever `as_of`
is set to a date earlier than the snapshot's own date.** Verify it.

### 4.5 — Where the data comes from

`build_valuation`'s signature currently takes `valuation_history`. Decide how the snapshot reaches
it — an optional `snapshot: pd.DataFrame | None = None` parameter is the natural shape, keeping the
default behaviour (no parameter → no extra point → today's output exactly). State the choice, and
update both callers: `app.py`, which has the snapshot frame loaded already, and `main.py`'s
pipeline path, where you should decide whether the written chart files include the point (they are
snapshots of a moment either way — say what you chose and why).

### 4.6 — Comparison charts

`build_ticker_comparison` also plots valuation concepts. State whether the snapshot point applies
there too. Implementing it is optional; **deciding and stating it is not** — leaving the two chart
types silently inconsistent is the failure mode here.

### 4.7 — Verify

- Mean line identical with and without the snapshot point (4.1), numerically, for both a harmonic
  and an arithmetic concept.
- The extra point's value equals the snapshot frame's value for that ticker/concept, and its x
  position is the snapshot date.
- A valuation concept absent from the snapshot renders unchanged versus today.
- `as_of` suppression behaves as designed.
- Default call (no snapshot passed) produces **byte-identical** output to before this part, for
  three tickers across profiles.

---

## Output

One file, `app_refinements_report.md`, with a section per part:
1. The tab reorder and what you confirmed did not depend on order.
2. The percent bug: confirmation of the diagnosed cause (including `NetIncomeLoss`), the
   namespace-aware fix, and the verification.
3. The growth survey table, the expansion proposal with per-profile reasoning, what was
   implemented, the `PROFILE_HIDDEN` entry count, the verdict on `GROWTH_BASE_PANELS` /
   `get_growth_panels()`, and any candidate you rejected with the reason.
4. The snapshot-point design decisions (4.1–4.6) with reasoning, and the verification results
   including the mean-line invariance proof.

No scratch scripts left behind.