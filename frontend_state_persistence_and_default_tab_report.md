# Comparison state persistence + default landing tab

Two shell defects, reported directly by the operator, diagnosed before being fixed. Both are real,
both are one-line causes with slightly more than one-line fixes, and one of the two premises in the
brief needed correcting.

---

## 1. Step 1 — the diagnosis

### 1.1 Where `ChartView`'s state lives, and why it survives

The brief suggested looking for "a `Map` keyed by tab, state lifted to a parent that outlives the
tab switch, or something else". It is **none of those, and this matters for the fix.**

`ChartView` holds its state in two plain `useState` hooks *inside itself* — [ChartView.tsx:90](frontend/src/ChartView.tsx#L90)
and [ChartView.tsx:98](frontend/src/ChartView.tsx#L98):

```ts
const [picked, setPicked] = useState<Partial<Record<ChartId, readonly string[]>>>({});
const [windowYears, setWindowYears] = useState<Partial<Record<ChartId, number>>>({});
```

Those *are* keyed by `ChartId`, which is what item 7's report describes — but that keying only
explains why Growth, Fundamentals and Valuation each keep their own selection **while `ChartView` is
alive**. It explains nothing about surviving a switch to a non-chart tab. Nothing is lifted; there
is no store; `Workspace` never sees the selection.

What makes it survive is the *mount lifetime*, one line in `App.tsx`:

```tsx
<div hidden={!isChartTab(tab)}>
  <ChartView … />
</div>
```

`ChartView` is mounted for **every** tab and merely hidden, which the chart-width regression report
already established independently (it is why a `<Plot>` could mount inside a `display: none` box and
fall back to `layout.width = 700`). So the mechanism is: *state local to the component, component
never unmounted*.

### 1.2 Where `ComparisonView`'s state lives

Exactly the same place — three `useState` hooks inside the component
([ComparisonView.tsx:70,76,80](frontend/src/ComparisonView.tsx#L70)): the concept, the ticker set,
the window.

**So the two views do not differ in where state lives at all.** Item 12's report line "Selection
state lives in `ComparisonView`" and item 7's "state lives per chart tab" describe the same design.
The brief's step 1.1 asked me to confirm the mechanisms differ before assuming it — they don't, and
that is the finding: the *only* difference is mount lifetime.

### 1.3 The direct cause

`App.tsx` had **two mounting rules and no way to see they were two**:

| tab | how it was rendered | state on tab switch |
|---|---|---|
| growth / fundamentals / valuation | `<div hidden={!isChartTab(tab)}><ChartView/></div>` | kept |
| data | `{dataSeen && <div hidden={tab !== "data"}><DataTab/></div>}` | kept (latched mount) |
| raw | `{tab === "raw" && <Placeholder/>}` | n/a — no state yet |
| **comparison** | `{tab === "comparison" && <ComparisonView/>}` | **discarded** |

React drops a component's `useState` when it unmounts and re-runs the initialisers on the way back.
`ComparisonView`'s initialiser reseeds the ticker set from the shell's ticker, so returning to the
tab did not merely reset to a default — it silently re-derived the set from wherever the sidebar
happened to be pointing.

This was **measured, not read.** Before any fix, the new harness reported:

```
FAIL comparison after a round trip via fundamentals:
  was  {"metric":"pe_to_revenue_growth","picked":["A ×pharma_medtech","AAOI ×standard"],"years":"7"}
  is now {"metric":"revenue_yoy_growth","picked":["AAPL ×standard","A ×pharma_medtech","AAOI ×standard"],"years":"15"}
```

All three pieces of state gone, and `AAPL` — which had been removed from the set — back.

### 1.4 Which other views are affected

Audited by driving the page, not by reading:

- **Data (item 9): not affected.** Its `showAll` and `factFilter` survived a round trip through
  Fundamentals. The `dataSeen` latch was already doing the job.
- **Chart tabs: not affected.** The window value and the metric checkboxes survived a round trip
  through Data. Item 7's claim holds; it is now asserted rather than trusted.
- **Raw Facts (item 16): not built.** It is a stateless `Placeholder`, so there was nothing to lose
  — but it was rendered with the same conditional pattern, so item 16 would have inherited the
  defect the moment it grew its include-derived toggle.

So this is **a shell-wide pattern gap that has bitten exactly one tab so far**, and per the brief's
own step 1.4 the fix belongs at the shell level rather than in `ComparisonView`.

### 1.5 One correction to the brief's second premise

> The operator's own read is that this is because Valuation was built first (item 4) and whatever
> set the initial route was never revisited.

**Half right, and the half that is wrong is the interesting half.** `DEFAULT_LOCATION` and the
`TABS` array were written in the *same commit*, in the same file, forty lines apart — the shell
cycle, not item 4. Git cannot separate them, so this is from the code itself:

- `TABS` ([navigation.ts:46](frontend/src/shell/navigation.ts#L46)) has always been Data-first, with
  the reason recorded above it: *"the app opens on what was extracted, and the charts follow"*. That
  comment is still accurate and was simply never wired to the default.
- `DEFAULT_LOCATION` said `valuation` because, when the shell was built, **the valuation chart was
  the only tab that existed** — the other five were `Placeholder`s. A default pointing at a
  placeholder would have opened the app on "Not built yet". So it was a reasonable choice at the
  time that stopped being one, rather than an oversight from the start. Nothing revisited it as
  items 9 and 12 filled the slots, which is the operator's read and is correct.

---

## 2. Defect 1 — what changed

### 2.1 One mounting rule, applied once

New file, [frontend/src/shell/TabPanel.tsx](frontend/src/shell/TabPanel.tsx) — the whole of it:

```tsx
export default function TabPanel({ id, active, children }) {
  const [seen, setSeen] = useState(active === id);
  if (!seen && active === id) setSeen(true);
  if (!seen) return null;
  return <div hidden={active !== id}>{children}</div>;
}
```

`App.tsx` now renders `data`, `raw` and `comparison` through it. The `dataSeen` boolean and its
comment are gone — the latch moved into the component that needs it, so there is one rule instead of
three ad-hoc ones, and `raw` goes through the same slot even though it holds no state yet, so item 16
inherits the rule rather than rediscovering it.

Three properties carried over deliberately from what `DataTab` was already doing:

- **`hidden`, not a CSS class** — the platform's own "not currently relevant", so it takes the
  accessibility tree and find-in-page with it and no stylesheet has to agree.
- **Lazy first mount.** Mounting all six tabs on load would fetch `facts_full` and one core file per
  comparison ticker for someone who only opened a chart. Measured below: it still does not.
- **The latch is adjusted during render**, not in an effect. That is React's documented pattern for
  state derived from a prop, and it is what mounts the tab in the render that first needs it instead
  of one render later — one render later is exactly when a `<Plot>` inside would measure a hidden
  container.

`ComparisonView` itself is unchanged apart from its docstring, which claimed *"changing the shell's
ticker afterwards does not disturb a set the reader has edited"*. That claim held only until the
first tab switch; it is now true, and the docstring says which cycle made it so.

### 2.2 The resize-on-mount interaction — it is **not** naturally covered

The brief asked whether extending hidden-mounting to non-chart views needs treatment for anything
that measures its container on mount, "or whether it is naturally covered by the same effect if
`isChartTab` is defined narrowly". **It is not covered, and `isChartTab` being narrow is exactly why.**

The comparison chart's figure was never at risk while the tab was conditionally rendered: it mounted
at the instant it became visible, so it always measured a real container. Keeping it mounted between
visits puts it in precisely the position `ChartView` has always been in — and the sidebar variant is
the one that bites. Collapse the sidebar while Comparison is hidden and nothing tells the figure the
page grew, because the shell's synthetic resize was gated on `isChartTab(activeTab)`, and
`"comparison"` is not a chart tab.

So the gate is now `tabDrawsFigure` ([navigation.ts:77](frontend/src/shell/navigation.ts#L77)):

```ts
export const tabDrawsFigure = (tab: TabId) => isChartTab(tab) || tab === "comparison";
```

A separate predicate rather than a wider `isChartTab`, because `isChartTab` answers *"is this tab a
`ChartView` with a different `chart` prop"* — it picks the component and the `chart` prop, and
widening it would hand `ChartView` a fourth chart id it has no builder for. The two questions
happened to have the same answer until this cycle.

**Verified by failing.** With the gate reverted to `isChartTab` and everything else in place, the
extended width harness reports:

```
FAIL comparison -> Growth (YoY) -> comparison, sidebar collapsed: container 1501px, svg 1159px
FAIL comparison -> Fundamentals -> comparison, sidebar collapsed: container 1501px, svg 1159px
FAIL comparison -> Valuation  -> comparison, sidebar collapsed: container 1501px, svg 1159px
27/30
```

342px of empty container — the regression this cycle would have shipped silently. The
sidebar-*expanded* round trips pass either way, which is the expected asymmetry: nothing changes the
container width while the figure is hidden, so there is nothing to announce.

---

## 3. Defect 2 — what changed

One value, [navigation.ts:105](frontend/src/shell/navigation.ts#L105):

```ts
export const DEFAULT_LOCATION: Location = { view: "analysis", tab: "data", ticker: null };
```

with the history from §1.5 recorded above it, so the next cycle does not have to re-derive why it
said `valuation`.

**Direct-link navigation is unaffected, and this is structural rather than lucky.** `parseHash`
reaches `DEFAULT_LOCATION.tab` on exactly two paths — the hash names no tab, or names one that is
not in `TABS`. An explicit `#/analysis/AAPL/valuation` never touches it. All six tabs were checked
by link (§4.2).

`DEFAULT_LOCATION.tab` is also read at [navigation.ts:130](frontend/src/shell/navigation.ts#L130)
for non-Analysis views, where the tab is a carried placeholder the URL cannot express anyway. One
visible consequence: reload on `#/about`, then click Analysis, and you now land on Data rather than
Valuation — which is the intended change, arriving by a second route.

### 3.1 The cost, stated

Landing on Data means the fresh load now pulls two files it previously deferred. Measured on the
default route:

| | files | gzipped |
|---|---:|---:|
| old default (`/valuation`) | registry, universe, meta, one ticker core | ~33.2 kB |
| new default (`/data`) | + `concept_candidates.json` + `{T}.facts.json` | ~62.7 kB |

**+29.5 kB gzipped on a cold first paint** (7.8 kB candidates + 21.7 kB `facts_full`). That follows
directly from the instruction and is not an argument against it — the Data tab is what the app is
*for* — but it is a real number and it belongs in the record rather than in a surprise later.

---

## 4. Step 4 — verification

### 4.1 A new standing check

[frontend/scripts/check-tab-state.mjs](frontend/scripts/check-tab-state.mjs), same shape as
`check-chart-width.mjs`: its own headless browser, non-zero exit on a mismatch, not wired into CI
because it needs a running dev server.

It exists because the three existing harnesses **structurally cannot** answer either question. The
item-8 harness and item 12's comparison harness compare *figure specs* built in Node, where there
are no tabs and nothing is ever unmounted; `check-chart-width` drives a real browser but only reads a
width. State surviving a tab switch is a property of the React tree's mount lifetime, visible only
from a page being clicked around.

The invariant is `fingerprint(tab) after leaving and returning === fingerprint(tab) before`, plus the
default route.

**Proven by failing, before the fix: `8/13`** — the four default-route checks and the comparison
round trip, with the diff quoted in §1.3. After the fix: **`13/13`.**

### 4.2 Defect 1, per affected view

| tab | disturbed to | via | result |
|---|---|---|---|
| **comparison** | last metric in the catalogue, first ticker removed, window 7 | Fundamentals | unchanged |
| **data** | "Show all periods" on, fact filter → third option | Fundamentals | unchanged |
| **fundamentals** (control) | window 6, first metric unticked | Data | unchanged |

The chart tab is in the sweep on purpose: item 7's report says its state already survives, and this
asserts it rather than trusting it.

### 4.3 Defect 2

| route | lands on |
|---|---|
| no hash at all | Data ✓ |
| `#/analysis/AAPL` | Data ✓ |
| `#/analysis/AAPL/` | Data ✓ |
| `#/analysis/AAPL/nonsense` | Data ✓ |
| `#/analysis/AAPL/{data,raw,growth,fundamentals,valuation,comparison}` | each its own tab ✓ (6/6) |

### 4.4 The chart-width fix

`check-chart-width.mjs` → **30/30**, up from 24.

The original 24 (4 landing tabs × 3 chart tabs × 2 sidebar states) are **unchanged and all still
pass** — hidden-mounting more views does not disturb any of them, because they all measure
`ChartView`'s figure and `ChartView`'s mounting did not change.

Two additions to the harness:

1. **Six new comparison round trips** (3 chart tabs × 2 sidebar states), for the case §2.2 describes.
2. **The measurement is now scoped.** It read `document.querySelector('.js-plotly-plot')` — the first
   plot in the DOM. A page can now hold two, since Comparison stays mounted after its first visit.
   `ChartView`'s still renders first so the unscoped selector still happened to find it, which is
   exactly the kind of accident a check should not rest on. The chart sweep now takes the plot *not*
   inside `.comparison`, and the comparison sweep takes the one that is.

### 4.5 The three charts and the comparison chart are unchanged as data

The item-8 and item-12 harnesses were scratch harnesses in their own cycles — only
`check-chart-width` and `check-table-format` persist — so rather than reconstruct them (and risk a
false alarm from a reconstructed enumeration order producing a different hash for identical
figures), I checked the strictly stronger property: **can any file the builders read have changed at
all.** The builders are pure and do no I/O, so a byte-identical import closure means byte-identical
figures by construction.

The closure of `charts/{fundamentals,growth,valuation,comparison}.ts` is 9 modules —
`grid.ts`, `mean.ts`, `panel.ts`, `select.ts`, `contracts.ts` and the four entry points — and hashes
to:

```
sha256 cf74741e4a190480cdf2b64226387434afe13fef87ed9f1b27ab2c852e771c59
```

recorded here as a baseline the next cycle can diff against directly. This cycle touched **five
files**, all inside `frontend/`, and none of them is in that closure:

```
M frontend/src/App.tsx
M frontend/src/shell/navigation.ts
M frontend/src/ComparisonView.tsx        (docstring only)
M frontend/scripts/check-chart-width.mjs
? frontend/src/shell/TabPanel.tsx        (new)
```

`check-table-format.mjs` was run as a live cross-check on the Data tab, which now mounts through a
new code path: **6,107/6,107 cells carry a display format**, identical to item 10's figure.

### 4.6 Fetch behaviour, measured

The lazy first mount is the property most at risk when a latch is rewritten, so it was measured
rather than assumed. Distinct export files fetched, driving the page:

| step | files added |
|---|---|
| land on Valuation | registry, universe, meta, `AAPL.json` — **no `facts_full`, no candidates** |
| → Growth → Fundamentals | none |
| → Comparison (first visit) | `A.json`, `AAOI.json` |
| → Fundamentals → Comparison | **none** |
| → Data (first visit) | `AAPL.facts.json`, `concept_candidates.json` |

Both heavy files are still deferred to the first visit of the tab that needs them, and the
leave-and-return that used to remount `ComparisonView` now refetches nothing — the persistence gain
showing up on the network as well as on screen.

*(The dev server also serves `registry`/`universe`/`meta` twice on load: React 19 StrictMode's
double-invoked effects, second one from cache, present before this cycle and unrelated to it.)*

### 4.7 Build

`npx tsc -b`, `npx eslint .`, `npx vite build` — all clean. Nothing outside `frontend/` changed. No
scratch files left in the repo.

---

## 5. What this leaves for later

- **Item 16 (Raw Facts)** gets persistence for free: it is already in a `TabPanel`, so its
  include-derived toggle will survive a tab switch without anyone thinking about it.
- **A fourth figure-bearing tab** must be added to `tabDrawsFigure`, not to `isChartTab`. The
  distinction is documented at the predicate and the failure mode is one collapsed sidebar away.
- **Item 15's as-of control** is unaffected by all of this; it still attaches at
  `ComparisonOptions.anchor`, as item 12's report §6 records.
- **State still is not in the URL.** A shared link carries view, ticker and tab; it does not carry a
  ticker set or a metric selection. That trade is recorded in `navigation.ts`'s own docstring and is
  unchanged — this cycle made the state survive *within* a session, not across a link.
