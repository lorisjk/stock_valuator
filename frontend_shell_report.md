# The application shell

Sidebar, four views, six Analysis tabs, the update notice (item 23) and the missing-data guard
(item 24). The three charts move into it unchanged — **byte-identical over 2,808 figures**.

---

## 1. The reference structure

### 1.1 The sidebar (app.py:852-877)

Three blocks in a fixed order, separated by dividers:

| # | element | source | note |
|---:|---|---|---|
| 1 | freshness | `render_freshness(meta)`, app.py:619 | *"in the sidebar so it survives every tab and page switch"* |
| 2 | `st.divider()` | app.py:855 | |
| 3 | view radio | app.py:856 | `key="view"` |
| 4 | `st.divider()` | app.py:857 | |
| 5 | **Analysis only**: `st.header("Ticker")`, the selectbox, the profile caption, the as-of checkbox | app.py:858-872 | |
| 5′ | **other views**: one caption saying why there is nothing to select |  app.py:874-875 | |

The freshness block is three lines — run date, `n of m tickers produced data`, `period` — plus a
fourth **only when `tickers_without_data` is non-empty**, with the reference's own reason attached:
*"an empty list must render as nothing, not an empty label"* (app.py:627).

**Collapse is not configured.** `st.set_page_config(page_title="Kyhestlo", page_icon="▪",
layout="wide")` (app.py:816) passes no `initial_sidebar_state`, so it is Streamlit's default
`"auto"` — expanded on a wide viewport, collapsed on a narrow one, with a built-in toggle.

### 1.2 The view radio (app.py:61-65)

Four options, `VIEW_ANALYSIS` first and therefore the default:

| id | label | renders |
|---|---|---|
| `analysis` | Analysis | `render_analysis(ticker, as_of, tickers, profiles)` |
| `encyclopedia` | Metric encyclopedia | `render_encyclopedia()` (app.py:632) |
| `coverage` | Profile coverage | `render_coverage()` |
| `about` | About | `render_about()` |

The three reference views `return` immediately after rendering (app.py:877-885), so Analysis is the
fall-through rather than a branch.

### 1.3 The Analysis tabs (app.py:894-896)

Six, in this order: **Data, Raw Facts, Growth (YoY), Fundamentals, Valuation, Comparison.** Data
first, with the reason in a comment: *"the app opens on what was extracted, and the charts follow"*.
The comment also notes that the `with` blocks appear in a different source order and that only the
list decides.

**Three of the six labels are derived**, from `CHART_LABELS` (app.py:38) — which is defined in
`app.py`, not `config.py`, so it is not registry-backed. `"Data"` and `"Raw Facts"` are literals at
the call site.

One small inconsistency worth recording: `CHART_LABELS` carries a fourth entry,
`"raw_facts": "Raw facts"` with a lowercase f, and the tab list does **not** use it — it hardcodes
`"Raw Facts"`. The reference disagrees with itself about the capitalisation; the rebuild follows
the tab list, because that is the one that renders.

### 1.4 The update notice (app.py:785-814)

Verified against the code, as asked, and the inventory §2.7 is accurate:

- **Content** comes from `content/update_notice.md` via `read_content` (app.py:114), which returns
  `""` for an absent or unreadable file *deliberately*, so "nothing to say" needs no special case.
- **`strip_comments` runs before the emptiness test** (app.py:802). The file carries its editing
  instructions in `<!-- -->`, and the ordering is what makes an instructions-only file count as
  empty. Testing emptiness first would draw a box containing nothing.
- **Empty → draw nothing**, not an empty box (app.py:803-806).
- **Dismissal** sets `st.session_state["update_notice_dismissed"]` (app.py:84) from the button's
  `on_click` callback. Lifetime: **the browser session.**
- The `on_click` rather than `if st.button(...)` is load-bearing *in Streamlit* and is explained at
  length at app.py:769-781 — callbacks run before the script body re-runs, so the `if` form would
  leave the notice on screen until an unrelated rerun. **This is Streamlit plumbing with no React
  analogue**, exactly as the inventory says.

The current file's stripped content is one paragraph about a raw-facts bug fix plus a repo link.

### 1.5 The missing-data guard (app.py:819-833)

`missing_files()` (app.py:97) checks seven names — the union of `FRAME_FILES` and `DATA_FILES` plus
`universe.parquet` and `meta.json` — against the local filesystem. If any is absent: one `st.error`
naming them and the re-run command, then `st.stop()`. **Nothing else renders**, notice included.

Both the `st.stop()` and the following `return` are deliberate, with the reason in a comment:
`st.stop()` does not raise outside a script run, so without the `return` a headless exercise of
that path falls through into a `FileNotFoundError`.

### 1.6 Where the ticker selector sits — and where it does not

**Below the view radio, inside the sidebar, and only in the Analysis view.** The `else` branch is
explicit about why (app.py:872-875):

> *"The ticker controls are deliberately absent here: these pages describe the pipeline, not a
> company, and a visible selector would imply otherwise."*

So the brief's Step 3.2 constraint is not an improvement on the reference — it *is* the reference.

---

## 2. Design

### 2.1 Two levels of navigation, and both go in the URL

**The location lives in the URL hash**: `#/analysis/AAPL/growth`. Three parts — view, ticker, tab —
parsed and formatted by pure functions in `shell/navigation.ts`.

The brief calls the decision cheap now and expensive later, and that is right: retrofitting it means
touching every component that holds a piece of the location. Doing it now cost two functions and a
`hashchange` listener.

**Hash rather than path**, because `load.ts` already documents the reason: a dev or preview server
answers an unknown path with `index.html` rather than a 404. A path-based route needs server
rewrites to survive a refresh on a static host; a hash needs none.

**What is not in the URL: the metric selection and the window.** They are per-chart and
high-cardinality — a 13-metric fundamentals selection plus three window values would turn a
shareable link into a paragraph. What would have to change to add them: they live inside
`ChartView`'s state today, so they would have to be lifted into the shell first, and then
`parseHash`/`formatHash` would need a query-string-ish tail. The lift is the expensive half, and
§2.2 explains why it was not done.

**Unknown parts fall back rather than throw.** A hand-edited or stale hash lands on a sensible
default. One exception: a *ticker* that is not in the bundle is kept, not replaced — the per-ticker
fetch is what knows whether a ticker exists and already has a message for the answer, and silently
rewriting the URL someone shared would be worse than a clear "not bundled".

### 2.2 What survives a switch

| switch | ticker | metric selections | window values |
|---|---|---|---|
| chart tab ↔ chart tab | kept | **kept** | **kept** |
| chart tab ↔ Data / Raw Facts / Comparison | kept | **kept** | **kept** |
| view ↔ view | dropped (by design, §1.6) | dropped | dropped |

The first row is free: the three chart tabs are **one `ChartView` with a different `chart` prop**,
which is what it was built for in item 5, and its state is already keyed by chart.

The second row cost one attribute. `ChartView` stays mounted and is hidden with `hidden` when a
non-chart tab is active, rather than being unmounted. Unmounting would throw away a nine-metric
selection because the reader glanced at the Data tab — and Streamlit's `session_state` would have
kept it, so that would be a regression against the reference, not a simplification.

The alternative was lifting the selection and window state into the shell, which **would have
changed `ChartView`'s props** — the one thing this item was told not to do. The cost of the choice
actually made is one plotly figure staying in the DOM while another tab is shown. If item 9's data
tab turns out heavy enough that this matters, lifting is the escape hatch and this paragraph is the
note saying so.

The third row is the reference's own boundary: leaving Analysis in `app.py` removes the ticker
controls entirely, so there is nothing to preserve.

This extends the pickers report's principle rather than replacing it — the shell holds the raw
location and the components derive from it, exactly as `ChartView` holds the raw pick and derives
the effective selection.

### 2.3 Collapse

A toggle button and a CSS grid that goes from `19rem 1fr` to `0 1fr`, plus a `max-width: 860px`
media query that turns the sidebar into a fixed overlay. That mirrors Streamlit's default `"auto"`
— a manual toggle plus automatic collapse on small screens.

Stated plainly: **this is not verified.** Whether the breakpoint is right, whether the overlay needs
a scrim, and whether the toggle is reachable at every width are DOM facts. The charts are already
responsive (`useResizeHandler`, and the builders pass no `width`), so the sidebar was the only fixed
thing in the layout.

### 2.4 Placeholders

One `<Placeholder>` component, used for all six unbuilt surfaces, showing the title, a badge reading
**"Not built yet — rebuild-list item N"**, and one sentence on what will live there. Uniform on
purpose: adding item 9 is replacing a placeholder in one place, not inventing a slot. The item
number is shown because the rebuild list is the shared vocabulary for what is missing.

### 2.5 Language — English

Inventory §5 settles it: *"there is no German in the user-facing app."* Every caption, label and
button in `app.py`, every chart string in `figures.py`, and every metric label in `config.py` is
English. The shell's new text is English to match.

Two inconsistencies this leaves, for whoever settles item 22:

1. **Some registry labels mix German words** — `"Revenue growth (Quartal, YoY)"`,
   `"Net Income Growth (Quartal, YoY)"`, `"Equity Growth (Quartal, YoY)"`. These are `config.py`
   data, they render on the y-axis and in the picker, and they are carried verbatim because
   relabelling is a `config.py` change this item excludes.
2. **`content/about.md` and `content/update_notice.md` are operator-authored** and are data, not
   code — the inventory explicitly does not check their language. Item 22 renders the first of
   them and is where the question of what language operator content is written in has to be asked.

The three remaining `WARNUNG:` prints in `main.py` are pipeline console output and never reach
either app.

---

## 3. What was implemented

| file | what |
|---|---|
| `src/shell/navigation.ts` | **new** — `VIEWS`, `TABS`, labels, `parseHash`/`formatHash`, `withView`/`withTab`/`withTicker`. Pure |
| `src/shell/notice.ts` | **new** — `stripComments`, `noticeText`, `noticeToShow`, the dismissal rule over an injectable store. Pure |
| `src/shell/guard.ts` | **new** — `diagnose(error, what)` → headline, remedy, and whether it is a normal dev state. Pure |
| `src/shell/Sidebar.tsx` | **new** — freshness, view radio, ticker (Analysis only) |
| `src/shell/Freshness.tsx` | **new** — `render_freshness`, including the conditional fourth line |
| `src/shell/UpdateNotice.tsx` | **new** — the box the rules decide to draw |
| `src/shell/GuardScreen.tsx` | **new** — the screen that replaces the app |
| `src/shell/Placeholder.tsx` | **new** — the one unbuilt-surface treatment |
| `src/shell/shell.css` | **new** — layout and palette |
| `src/App.tsx` | rewritten: `main()` + `render_analysis()` as one component |
| `src/contracts.ts` | `Meta`, `META_SCHEMA` |
| `src/data/load.ts` | `fetchMeta`, `fetchNotice` — additive |
| `src/data/DataProvider.tsx`, `DataContext.ts` | carry `meta` and `notice`, neither able to fail the app |
| `frontend/public/update_notice.md` | a copy of `content/update_notice.md` — see §4 |

**`ChartView` was not changed.** Its props, its state and its build call are exactly as item 8 left
them; the shell wraps it. `panel.ts` and the three builders were not touched either.

### The palette

`shell.css` takes its five colours from the charts rather than from the scaffold's stylesheet: the
working tree's `panel.ts` sets `paper_bgcolor`/`plot_bgcolor` to `#16171d`, tick text to `#9ca3af`,
titles to `#f3f4f6` and grid lines to `#2e303a`. A light shell around dark figures would read as a
rendering failure. That is a duplication and it is labelled as one in the file — those literals are
inline in `panel.ts`, are not exported, and that file is in-flight work this item does not touch.

---

## 4. The notice and the guard

### 4.1 The notice (item 23)

All three reference behaviours reproduced, each as a pure function:

| behaviour | where | how it is checked |
|---|---|---|
| comments stripped **before** the emptiness test | `noticeToShow` | an instructions-only file returns `null` |
| empty → nothing, not an empty box | `noticeToShow` | missing / empty / instructions-only all return `null` |
| dismissal lasts a session | `dismissNotice` | `sessionStorage`, under app.py's own key |

`sessionStorage` rather than `localStorage` is the substantive choice: `st.session_state` is
per-session and per-tab, so `localStorage` would outlive it — and a notice dismissed in March would
still be dismissed in June, including a *different* notice.

`stripComments` reproduces one behaviour that looks like a bug and is not: an unterminated `<!--`
swallows the rest of the file, because `rest.find("-->")` returning `-1` ends the Python loop with
everything after the opener dropped. A half-written comment should hide the text it was half
wrapping rather than print it.

**Rendered as plain text, not markdown.** There is no markdown renderer in this bundle, and adding
a dependency to format a two-sentence announcement is not worth it — so the current file's
`[Repo](…)` shows literally. Said here rather than hidden: item 22's About page is a whole document
in markdown and is where that decision has to be made properly.

**The content file is duplicated.** The browser cannot read `content/update_notice.md`, so a copy
now sits in `frontend/public/`. That is a second source of truth and the build or deploy step should
own the copy. Item 22 hits the same thing with `content/about.md`.

### 4.2 The guard (item 24)

The frontend's failure modes are not Streamlit's — `app.py` checks seven files on disk and a file
is either there or not; a browser fetches at runtime. `diagnose` produces a different sentence for
each, because each has a different fix:

| kind | trigger | normal in dev? | what it says |
|---|---|---|---|
| `missing` | `MissingTickerFile` | **yes** | names the ticker and the exact file to copy into `frontend/public/tickers/` |
| `schema` | `SchemaMismatch` | no | names both versions and notes the two files are written by the same run, so one is stale, not both |
| `malformed` | a JSON syntax error mentioning `<` | **yes** | says a dev server answered with `index.html`, which usually means the file is not in `public/` at all |
| `network` | a 4xx/5xx or `Failed to fetch` | **yes** | the re-run-the-pipeline command |
| `unknown` | anything else | no | says the message below is all that is known |

**The dev-bundle 404 is presented as a normal state**, not a fault: `frontend/public/tickers/`
carries a subset while the published export carries all 609, so "copy one more file" and "your
export is broken" are different days and get different words.

**Schema handling is deliberately asymmetric.** The registry and the per-ticker files are
*interpreted*, so a version this build cannot read is fatal. `meta.json` feeds one caption, so a
mismatch there is flagged in the sidebar and the app keeps running.

That is not hypothetical. **The export currently in `data/app/` and `frontend/public/` declares
`meta.json` schema 2 while `main.py` writes `APP_EXPORT_SCHEMA = 4`**, and that `meta.json` has
neither the `registry` nor the `per_ticker` block the exporter now writes into it — while
`registry.json` sitting beside it was generated a day later. So the invariant that `meta.json` is
written last and its presence means the whole export is on disk **does not currently hold in this
bundle.** Enforcing `META_SCHEMA` the way the other two are enforced would have replaced the working
app with an error screen; flagging it in the freshness block says the same thing without doing that.

---

## 5. Verification

### 5.1 The charts are unchanged — byte-identical

The item-8 sweep re-run against two source trees: the current one, and a reconstructed pre-cycle
tree (`contracts.ts` and `data/load.ts` restored from `HEAD`, `shell/` removed). Both were exercised
over **39 tickers spanning all 24 profiles × 3 charts × 8 windows (0, 1, 2, 3, 5, 10, 15, omitted) ×
4 selection shapes** (full catalogue, picker default, first three, empty).

| | |
|---|---:|
| figures built per tree | **2,808** |
| traces | 8,695 |
| data points | 204,067 |
| serialised bytes | 20,347,001 |
| sha256 | `919868ca5e63c299d6bc778ed8252b66040ddc6cf962764569f6e4f985c30ee9` |
| **byte-identical** | **yes** |

This is the check that mattered, and it was not a formality: `contracts.ts` and `data/load.ts` are
both on the chart path — `parseTickerFile` and `reconstructFrame` run on every figure — and both
were edited this cycle. The identical hash is what says those edits were additive.

### 5.2–5.4 The shell's logic — 137 checks, all passing

| area | checks | what |
|---|---:|---|
| routing | 88 | `parseHash` on empty / bare / full / unknown-view / unknown-tab / no-ticker / percent-encoded input; **a full round trip over every (view, tab, ticker) the app can be in**; `withView`/`withTab`/`withTicker`; tab and view order against app.py; `CHART_LABELS` carried verbatim |
| the notice | 17 | `stripComments` on none / one / multiline / two / **unterminated**; instructions-only → empty; missing file → empty; dismissal sets app.py's key; a fresh session shows it again; no storage at all still renders; and the **actual bundled file** strips to non-empty content with its instructions gone |
| the guard | 32 | all five branches by kind, each with a headline and a remedy; `expectedInDev` true for a missing ticker file and false for a schema mismatch; the missing-ticker remedy names the file to copy; the schema remedy names both versions |

**The round-trip test found a real defect in my own code.** `formatHash` writes `#/analysis//valuation`
when no ticker is chosen, and `parseHash` was dropping empty segments with `.filter(Boolean)` — so
`#/analysis//data` parsed back as *ticker `DATA`*. The hash is positional, so empty segments have to
be kept; fixed, and the reasoning is now in the function's docstring next to the test that would
catch a regression.

### 5.5 Build

`npx tsc -b`, `npx eslint .`, `npx vite build` — all clean. Nothing outside `frontend/` changed.

### 5.6 What would need a browser

Everything visual, and it is a real fraction of this item:

- **The sidebar collapse and the 860px breakpoint.** Untested. Whether the overlay needs a scrim,
  whether the toggle stays reachable, whether `19rem` is right — all unknown.
- **Whether 609 options in a native `<select>` are usable.** The reference does exactly this and
  Streamlit's selectbox is a searchable custom widget, while a native `<select>` is not. This is
  the most likely thing to need changing after someone opens it, and it is a deliberate
  reproduction of the reference's *structure* rather than of its widget.
- **Whether the shell palette actually matches the rendered figures.** The five colours were read
  out of `panel.ts`, not seen next to a chart.
- **Keyboard and screen-reader behaviour of the tab bar.** It is a `<nav>` of buttons with
  `aria-current`, not an ARIA tablist with arrow-key navigation.
- **That the hidden `ChartView` really is inert.** `hidden` on the wrapper keeps it mounted; whether
  plotly does layout work on a hidden container is not something Node can answer.

---

## 6. What items 9, 16, 20, 21 and 22 should know about the slot

1. **The slot is a `<Placeholder>` and replacing it is a one-line edit in `App.tsx`.** Every unbuilt
   surface is the same component with a different title, item number and sentence. Item 9 replaces
   the `tab === "data"` branch; 16 the `tab === "raw"` branch; 20, 21 and 22 the three view
   branches. Nothing else in the shell needs to know.

2. **Items 20, 21 and 22 must not take a ticker, and the shell cannot pass them one.**
   `isTickerView` is true only for `analysis`, `withView` nulls the ticker on the way out, and
   `formatHash` cannot even express `#/about/AAPL`. That is the reference's own rule (app.py:872)
   made structural rather than conventional.

3. **Item 9 gets the frames the same way the charts do.** `useTickerFrames(ticker)` from
   `DataContext`, which shares one promise per ticker with `ChartView` — so opening the Data tab
   after a chart costs no fetch. The data tab needs `facts_full`, which is in `TICKER_FACTS_FRAMES`
   and therefore in the **separate** `{TICKER}.facts.json` file, not the core one; `FrameName`
   currently lists only the four core frames and will need extending.

4. **Item 9's tab is the one that decides whether keeping `ChartView` mounted stays acceptable.**
   §2.2 explains the trade. If the data tab is heavy, lift the selection and window state out of
   `ChartView` into the shell and unmount instead — and that lift is also what item 1's URL
   question needs (§2.1), so the two arrive together.

5. **Item 22 owns two unfinished decisions**, both flagged in §4.1: operator content is currently
   *copied* into `frontend/public/` rather than built there, and it renders as plain text because
   there is no markdown renderer. An About page is a whole document and will need both settled.

6. **Item 20 (encyclopedia) has everything it needs in the registry already.** `description`,
   `formula`, `label`, `documented` and the `undocumented` list are all in `registry.json`, and
   `notes.growth_mechanism` / `notes.valuation_mechanism` carry the two long-form explanations.
   No new export work — the registry export was built for this.

7. **Item 21 (profile coverage) likewise**: `profile_visibility` is the full 52 × 24 matrix, already
   verified against `get_plottable_metrics` over all 1,827 (chart, ticker) pairs in the registry
   export report and again over 99 option lists in the pickers report.

8. **`meta.json` in the bundle is stale** (§4.2) — schema 2 against the pipeline's 4, missing the
   `registry` and `per_ticker` blocks. Anything that wants to trust `meta.json` as the "everything
   is on disk" marker should re-run the export first.

No scratch files were left behind.
