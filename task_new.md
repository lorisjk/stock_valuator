# Task: Sidebar — Data Freshness, Metric Encyclopedia, Profile Coverage

**Depends on the app refinements task being complete and shipped.** Read
`app_refinements_report.md`, `metrics_registry_report.md`, `data_tab_report.md`, if not available anymore recompute them via git, and the current
`app.py`, `config.py`, `metrics.py`, `main.py` before changing anything.

## Context

The app now shows data and charts well. What a first-time visitor cannot do is answer two
questions without reading the source: **what is this number and how was it computed**, and **why
does this ticker show different metrics than that one**.

Both are core to this project's positioning. The differentiator over commercial providers is not
having the numbers — it is being able to show exactly how they were derived. An encyclopedia that
paraphrases a textbook would destroy that: it would describe metrics this pipeline does not
compute the way it describes them.

**Explicitly NOT in this task:** no Phase 4 (cross-sectional/peer scatter), no `PROFILE_HIDDEN`
structural refactor, no `V`/`STZ` `SharesOutstanding` fix, no `p_ffo`-in-snapshot fix, no changes
to chart rendering or the data tab's contents, no deployment work.

---

## Part 1 — Navigation and layout decision (make this first, everything else sits inside it)

The app is currently five tabs. This task adds four more surfaces (three encyclopedia sections
and a profile-coverage page) that are **reference material, not analysis** — a user consults them
occasionally, not per ticker.

Decide how they are reached and state the reasoning. Options include a `st.sidebar` with a
radio/selectbox switching between "Analysis" and the reference pages, Streamlit's native
multipage structure, or simply more tabs. Constraints that should drive the choice:

- Nine tabs in one row is not navigable.
- The reference pages are **ticker-independent** — putting them next to a ticker-specific tab set
  invites the reader to assume they describe the selected ticker.
- The existing prototype convention is "no multipage structure, no custom CSS". If you break that
  convention, say why it is now worth breaking.

Whatever you choose, the **ticker selector and the five existing tabs must keep working exactly
as they do today** — this is an addition, not a restructuring of the analysis view.

## Part 2 — Move the freshness information

The run timestamp from `meta.json` is currently an `st.caption`. Move it to a persistent position
(top-left / sidebar) so it is visible regardless of which tab or page is open.

Show at minimum the run date and the ticker count. Consider whether `tickers_without_data` from
`meta.json` belongs here too — it is exactly the kind of honest-coverage signal this project
surfaces elsewhere; if you include it, make sure an empty list renders as nothing rather than an
empty label.

Remove the old caption; do not leave the information in two places.

## Part 3 — Where encyclopedia content lives

Each entry needs, per metric: **what it is** (one or two sentences) and **how this pipeline
computes it** (the actual formula/inputs). Short — this is not the repo's `METRICS_REFERENCE.md`
re-hosted.

Decide where the text lives and state the reasoning. Recommended: two new optional fields on the
`Metric` dataclass (`description`, `formula`), keeping the registry as the single source of truth
the way `label`, `percent` and `ref_line` already are — adding a metric then stays one line and
cannot silently lack documentation. If that makes `config.py` unwieldy at 45 entries, a separate
module keyed by metric id is acceptable, but then state how a metric without documentation is
detected rather than silently rendering blank.

Either way: **existing `Metric` fields and every derived structure must remain byte-identical.**
New fields are optional with defaults; `FUNDAMENTALS_TO_PLOT` and friends must not change shape.

## Part 4 — Write the content, sourced from the code

**This is the part where the task fails if done carelessly.** Every formula must be derived by
**reading the actual implementation** in `metrics.py` / `main.py` / `parsers`, not from general
financial knowledge. Where this pipeline's definition differs from the conventional one, the
encyclopedia must state this pipeline's definition.

Known example to check first, as a calibration case: **`peg_ratio` is computed from revenue
growth, not earnings growth** — a conventional description would be wrong. Read the code and
confirm; find and report any other metric whose implementation departs from the textbook
definition. That list is itself a valuable output of this task.

Requirements:

1. **Name the actual inputs.** "Computed from `NetIncomeLoss_TTM` and `StockholdersEquity`" is
   useful; "net income divided by equity" is not, because it does not say which XBRL concept,
   which period basis, or which of several possible equity figures.
2. **State the period basis** — TTM, quarterly, or point-in-time — since the project computes
   both TTM and quarterly variants of many things.
3. **Growth entries share one mechanism**, so document it once and keep per-concept notes short:
   `calculate_growth` uses a 4-quarter lag, requires both the current and prior value to be
   positive, and applies a `min_base_ratio` guard (loosened by explicit override for a few
   concepts). Those guards are why a user sees gaps — that explanation belongs in the growth
   section, and it is one of the more persuasive things this app can say about itself.
4. **Valuation entries: state the price input and the mean convention.** Which price, as of when,
   and that some multiples use a harmonic rather than arithmetic mean for the reference line
   (`HARMONIC_MEAN_CONCEPTS`) — read which, don't assume. Also note the snapshot marker's
   meaning, since it now appears on these charts.
5. **Language: pick one and apply it consistently.** Recommended English, matching the registry's
   `LANGUAGE_PRIMARY` and the intended audience. Note that the app currently mixes German UI
   strings ("Keine Daten", exclusion notes) with English labels — do **not** fix that here, but
   report it as a known inconsistency so it can be handled deliberately later.
6. **Where a metric's documentation cannot be written confidently from the code, leave it empty
   and list it in the report.** An honest gap beats a plausible-sounding description of something
   the code does differently. This is the same standard applied to `label_de`.

Render the three sections (fundamentals, valuation, growth) grouped sensibly, driven by the
registry's `chart` field so a new metric appears automatically.

## Part 5 — The profile coverage page

A page showing, per profile (`standard`, `financial`, `insurance_life`, `reit`, …), which
fundamentals and valuation metrics are computed and shown.

**This must be generated from `is_hidden`, never hand-written.** A hand-maintained table would
drift from the code within one task, and the whole point is that it is authoritative. Build it by
evaluating visibility for every (profile, metric) pair.

Design points:

1. **`is_hidden` takes a ticker, not a profile.** Determine how to evaluate profile-level
   visibility — a representative ticker per profile, or a path that resolves a profile directly.
   State what you did and any caveat (e.g. `_DERIVED_CONCEPT_CONSUMERS` or ticker-level overrides
   could make one ticker unrepresentative of its profile — check whether that actually happens
   and report it).
2. **24 profiles × 45 metrics is a large matrix.** Decide the presentation: a full matrix, a
   per-profile view driven by a selector, or grouped by metric with the profiles listed. Pick
   what is actually readable and justify it.
3. **Show growth panels too** if the same generation works for them — they are registry entries
   like the others.
4. Make the profile a ticker belongs to visible somewhere in the analysis view as well, so a user
   looking at JPM can connect it to the `financial` row here.

## Part 6 — Verify

- **Nothing regressed:** the five existing tabs render as before, chart output is unchanged
  (compare `build_*` output byte-for-byte against a pre-change baseline for three tickers across
  profiles), and the derived config structures are byte-identical.
- **Encyclopedia coverage is complete or explicitly listed:** assert every registry metric either
  has documentation or appears in the report's gap list. No metric silently renders blank.
- **The coverage matrix matches `is_hidden`** — verify a sample of cells programmatically against
  `config.is_hidden` directly, including at least one metric hidden for most profiles
  (`p_ffo`-like) and one visible for nearly all. A generated table that disagrees with the
  function it claims to reflect is worse than no table.
- **A new metric flows through automatically:** temporarily add a registry entry in the
  verification run and confirm it appears in the encyclopedia and the coverage page without
  touching either. Do not leave it behind.
- **`app.py` still imports no pipeline module** and the page body runs to completion in bare mode,
  as previous tasks verified. State honestly what was not verifiable without a browser.

## Output

One file, `sidebar_encyclopedia_report.md`: the navigation decision with reasoning, where the
documentation lives and why, **the list of metrics whose implementation departs from the
conventional definition** (found in Part 4), any metric left undocumented and why, the coverage
page's generation approach and its caveats, and the Part 6 verification results.

No scratch scripts left behind.