# Item 21 — Profile Coverage

`render_coverage` (app.py:676–717), ported. The second and last reference view, and the page that
makes `is_hidden` — the mechanism every chart, picker and builder has silently depended on since
item 4 — visible and auditable for the first time.

---

## 1. Step 1 — the reference, read exactly

### 1.1 Layout: **two** views, not one matrix

The inventory calls the item "the 52 × 24 matrix" and that is half of it. `render_coverage` renders,
in order:

| # | what | source |
|---|---|---|
| 1 | `st.header("Profile coverage")` and a four-sentence lede | app.py:677–683 |
| 2 | `st.selectbox("Profile", profiles, …)` | app.py:688–690 |
| 3 | a caption: `` `{profile}` shows {n} of {52} registered metrics. `` | app.py:691–692 |
| 4 | three sections, one per chart, each a subheader plus a **Shown** list and a **Hidden for this profile** list | app.py:694–703 |
| 5 | `st.divider()`, `st.subheader("Full matrix")`, a caption | app.py:704–710 |
| 6 | the matrix itself, one row per metric, one column per profile | app.py:711–717 |

The reference explains the split in its own caption (app.py:707–709), which is the best statement of
why both halves exist:

> *"The per-profile view above answers "what does this company show"; this answers "who sees this
> metric", which is the question the matrix is uniquely good at. Scrolls horizontally."*

So this is a selector-driven per-profile reading **and then** its transpose. Building only the matrix
would have dropped the half that answers the question a reader arrives with.

### 1.2 Grouping and profile order

- The three sections are `CHART_SECTIONS` again (app.py:694) — **Fundamentals, Valuation, Growth**,
  the same list and the same order item 20 established, and per-section ids come from
  `[m.id for m in config.METRICS if m.chart == chart]`, i.e. registry order.
- **But not `st.tabs`.** `render_coverage` runs the three as consecutive `st.subheader`s, unlike
  `render_encyclopedia`. The point of this page is to read a profile's whole shape in one pass, and
  the reference's container says so. The hand-off's "`.tabs`/`.tab` if grouped by chart section" was
  conditional and the condition does not hold.
- **Profiles: `sorted(visibility)`** (app.py:686) — 24, ascending by code point, `airline` first.
- **The default selection is the literal string `"standard"`**, not `registry.default_profile`:
  `index=profiles.index("standard") if "standard" in profiles else 0` (app.py:689–690). The two
  happen to agree today; the reference names the string, so the port does too.

### 1.3 The caption, and the two different denominators

```python
shown_total = sum(visibility[profile].values())                                   # app.py:691
st.caption(f"`{profile}` shows {shown_total} of {len(by_id)} registered metrics.")  # app.py:692
```

`shown_total` is a sum over **every registered metric**, not per chart, and `len(by_id)` is **all
52**. Confirmed verbatim, including the backticks around the profile name — which are markdown, so
the profile renders as a `<code>` element and not as literal backticks.

The per-section heading uses the **other** denominator:
`st.subheader(f"{title} — {len(shown)} of {len(ids)}")` (app.py:698), where `ids` is that chart's own
count — 29 / 13 / 10. The three numerators add up to the caption's; the three denominators add up to
52. Both are checked (§3.2).

### 1.4 Purely boolean — no reason strings anywhere

`PROFILE_HIDDEN` (config.py:650) is `{profile: set-of-ids}`, a bare set with no reason attached, and
`is_hidden` returns a `bool` (config.py:2155). There is nothing per-metric to show beyond
shown/hidden, and the reference shows nothing more. The *general* reason lives in the lede — *"A bank
has no inventory and a REIT is not valued on earnings"* — and that is the whole explanation the page
offers.

Worth recording, because it is exactly what a client-side re-derivation would get wrong: `is_hidden`
has **two** clauses. Direct membership in `PROFILE_HIDDEN`, and then
`_DERIVED_CONCEPT_CONSUMERS` (config.py:2076) — a derived concept is hidden only when **all** the
metrics that consume it are hidden (config.py:2162–2164). Measured across the whole matrix:

```
687 hidden (profile, metric) pairs
  613 by direct PROFILE_HIDDEN membership
   74 by the consumers rule alone   e.g. alt_asset_manager / FCF_TTM,
                                    hidden only because pfcf_ratio, fcf_margin,
                                    ev_fcf and pfcf_ex_sbc all are
```

**Those 74 are the trap.** A page that reimplemented "is this id in the profile's hidden set" would
be right 613 times and wrong 74 — and would look plausible throughout. This page reads
`profile_visibility` and computes nothing (§2.4).

### 1.5 No ticker examples

`render_coverage` never touches `TICKER_PROFILES`. The profile list stands alone. `ticker_profile`
*is* exported and typed, and it is read elsewhere (`App` uses it for the sidebar's profile caption) —
but adding "financial: JPM, BAC, …" here would be inventing a feature. Not built.

### 1.6 No filter

Item 20 has a page-level `st.text_input`; this page has none — the selectbox is the only control.
A divergence between the two reference views, carried as written.

### 1.7 The extremes, from the data

| profile | shows | sections |
|---|---:|---|
| `alt_asset_manager` | **16 of 52** | Fundamentals 5/29 · Valuation 5/13 · Growth 6/10 |
| `reit` | **16 of 52** | Fundamentals 4/29 · Valuation 5/13 · Growth 7/10 |
| `financial` | 20 of 52 | Fundamentals 9/29 · Valuation 5/13 · Growth 6/10 |
| `standard` | 25 of 52 | Fundamentals 9/29 · Valuation 9/13 · Growth 7/10 |
| `consumer_staples` | **29 of 52** | Fundamentals 13/29 · Valuation 9/13 · Growth 7/10 |

Two profiles tie for fewest (16), `consumer_staples` shows most (29), and **no profile shows more
than 56% of the registry** — which is the page's own argument made numerically.

From the transpose: `Net Interest Margin` is shown to **exactly one** profile; `Revenue growth` to
all 24; **6 of the 52 metrics are visible to every profile.**

And one structural fact that made the verification simpler rather than harder: **all 72
(profile, section) pairs have both a non-empty Shown list and a non-empty Hidden list.** So
app.py:699 and app.py:701's conditional rendering is exercised in the affirmative everywhere — the
inverse of items 18/19/20, where the interesting branches were the unreachable ones.

---

## 2. What was implemented

| file | change |
|---|---|
| `frontend/src/Coverage.tsx` | **new.** The lede, the selector, the caption, the three sections, and the matrix |
| `frontend/src/coverage.css` | **new.** The selector, the label runs, and the matrix's tick column |
| `frontend/src/App.tsx` | the item-21 `Placeholder` replaced by `<Coverage registry={registry} />` |

Nothing else. No chart, picker or builder was opened; `registry.json` is untouched; item 20's
encyclopedia is untouched.

**Data source:** `useData().registry`, already loaded at startup and already passed down by `App`.
`profile_visibility` (`Record<string, Record<string, boolean>>`) and `ticker_profile` were already
typed in `contracts.ts` from item 1 — no new parsing, no new fetch, no loading state.

**Reused rather than restated:** `.caption`; and `.table-scroll` + `.data-table` +
`.data-table__corner` from the data tab for the matrix. That last one is the substantive reuse — the
matrix is the same object as a facts table (wide, sticky header, pinned first column), and the corner
rule is exactly what stops a reader losing which metric a column of ticks belongs to. It sits outside
`.data-tab`, so `check-table-format`'s scan cannot see it (confirmed: its baseline is unmoved).

**`.tabs`/`.tab` are deliberately *not* used** — §1.2. **The 78ch reading measure is deliberately not
applied to the page** — the hand-off's warning was right, and `coverage.css` says so where it caps
only the lede and the label runs, leaving the matrix the full grid cell.

### 2.4 One source of truth, structurally

Every ✓ and every `·` on the page is `registry.profile_visibility[profile][id]` — read, never
recomputed. `Coverage.tsx` contains no `isHidden`, no hidden-set membership test and no consumers
rule; there is nothing in it that *could* disagree with the export. Given §1.4's 74 indirectly-hidden
pairs, that is not a stylistic preference.

---

## 3. Step 4 — verification

### 3.1 The export against `is_hidden` itself — 31,720/31,720

The brief asked for the matrix re-derived **directly from `config.is_hidden`, bypassing the export**.
Done, and made stronger than the export's own basis: `profile_visibility` builds each profile's row
from **one representative ticker** (config.py:2637–2640, with a docstring claiming every ticker of a
profile gives the same answer). The bypass calls `is_hidden(ticker, id)` for **every real ticker**:

```
is_hidden(ticker, id) vs exported profile_visibility:
31720/31720 over 610 tickers x 52 metrics
```

So the representative-ticker shortcut is not merely assumed here — it is confirmed across the whole
universe, and the export is confirmed against the function a second time on a wider basis than item 1
used.

### 3.2 The render against `render_coverage` — 1,876 checks, 24 profiles, 0 failures

A headless browser reads the live page and steps the selector through **all 24 profiles**, compared
against a reference dump produced by importing `app.CHART_SECTIONS` and `config.profile_visibility`
and reproducing app.py:691–717 verbatim.

```
1876/1876 coverage DOM checks pass over 24 profiles
```

Not sampled, at either level:

- **The matrix, mark by mark:** 52 metrics × 24 profiles = **1,248 individual ✓/· comparisons**, plus
  each row's label, its `chart` cell and its `profiles` count, plus the column headers in order.
- **The per-profile view, for every profile:** the caption's exact text *and* that the profile name
  renders as a `<code>` element; all three section headings with their own `{shown} of {chart total}`
  denominators; every label in the Shown list and the Hidden list, in order; and that a list is drawn
  only when it has entries.
- **Page furniture:** the header, the lede, the selector's label and its 24 options in sorted order,
  the landing selection being `standard`, the single divider, the matrix caption verbatim, and the
  matrix living inside a `.table-scroll` — which is what makes the caption's "Scrolls horizontally"
  true rather than aspirational.
- **A cross-check the reference does not state:** each profile's three section numerators sum to the
  caption's `shown_total`. The two numbers come from different code paths (app.py:691 vs :696), and
  nothing in either enforces their agreement.

**The harness is sensitive**, by mutation, each run in isolation:

| mutation | failures | what fired |
|---|---:|---|
| one profile's marks inverted (`reit`) | **52** | exactly one mark per metric, in one column |
| default selection = first profile alphabetically | **1** | the landing-selection check |
| section headings use 52 as their denominator | **72** | 24 profiles × 3 sections |

Each lands exactly where its own reasoning predicts.

**A methodological correction, recorded because it changes how to read a mutation run.** The three
mutations were first run back-to-back with no pause between editing the file and launching the
browser, and the third reported **1** failure instead of 72 — Vite's HMR had not rebuilt before the
page was read, so the harness measured the *unmutated* build and the run proved nothing. Re-run in
isolation with a pause, it reports 72. A mutation run that under-reports looks exactly like a passing
build, which makes this worth stating: **a sensitivity test needs the rebuild to have landed, and the
numbers above are all from isolated runs.**

### 3.3 Nothing else regressed

| check | result |
|---|---|
| `check-chart-width.mjs` | **36/36** |
| `check-tab-state.mjs` | **13/13** |
| `check-table-format.mjs` | **6,107/6,107** — unmoved, the matrix being outside `.data-tab` |
| item 20 encyclopedia A/B | **1,173/1,173** |
| item 19 cadence A/B | **3,654/3,654** |
| item 18 flag-summary A/B | **12,466/12,466** |
| chart-builder A/B | **23/23 digests**, identical to items 17–20's |
| `npx tsc -b` / `npx eslint .` | clean |
| `npx vite build` | `✓ built in 13.23s` |

`git status`: `App.tsx` plus the two new files, and `task_new.md` (operator-owned). Nothing outside
`frontend/`.

---

## 4. For item 22 — About

### The rebuild list is now down to the About page and two nice-to-haves

Items 20 and 21 are both built, so `App.tsx` holds exactly **one** `Placeholder` left (item 22);
items 23 and 24 — the update notice and the missing-data guard — were built with the shell.
Replacing that last placeholder empties the component's only remaining call site, and `Placeholder`
itself can go with it. Its docstring anticipated this: *"Adding item 9 should be replacing this in
one place, not inventing a slot."*

### `split_sections` is already sitting next to `render_coverage`

`app.py:720`'s `split_sections(text)` — markdown split on `## ` headings, returning `(heading, body)`
in file order, with anything before the first heading coming back as `("", intro)` — is the About
page's structure, and it exists *so that one named section can be drawn differently* (the
`disclaimer` callout, inventory §6 item 22). Port that split rather than rendering `about.md` in one
block; the docstring's reasoning is that every other section passes through untouched, so the file
stays ordinary markdown and the page order is the file's order.

### The markdown path is solved four times over

`react-markdown` is now used by `UpdateNotice`, item 19's cadence legend, and item 20's mechanism
notes and metric entries. For fetching a markdown file from `public/`, `fetchNotice` (`load.ts:194`)
is the working pattern — including its lenient failure mode.

### Its three factual claims are now all true

`content/about.md:22` promises *"Coverage gaps, derivation provenance, and data-quality flags are
shown in the Data view rather than smoothed over."* Item 9 delivered the coverage gaps, item 19 the
provenance, item 18 the flags. The sentence can be ported as written.

### Two reusable techniques, both now proven

- **Fixture-plus-hash-restore** (item 20 §3.3) for a branch live data cannot reach. This cycle needed
  no fixture — every branch on this page is exercised by the real registry (§1.7) — but the method
  stands.
- **Bypass the export and call the function** (§3.1). Wherever a page renders something the pipeline
  computes, the strongest available check is against the computing function rather than against its
  serialisation, and it is usually cheap.
