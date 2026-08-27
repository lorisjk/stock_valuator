# The chart width regression — found, fixed, and it was not the data tab

The chart renders at **700px inside a 1204px container** whenever you arrive at a chart tab from a
non-chart tab. Reproduced, measured, fixed in four lines of `App.tsx`, and verified over all 24
combinations of entry path × chart tab × sidebar state.

**The brief's hypothesis is wrong, and the difference matters.** Item 9 did not cause this. A tree
with item 9 reverted reproduces the defect identically, and the shortest reproduction goes through
the **Raw Facts** tab — a placeholder item 9 never touched. This is a latent defect in the shell's
hidden-mount pattern, live since tab switching was built, and the reason it survived three cycles is
that landing straight on a chart tab has always looked correct.

---

## 1. Step 1 — measurement

Same instrument as the last two cycles: headless Edge over the DevTools Protocol against a real
`npm run dev` server.

### 1.1 The chain, walked — and nothing in it is narrow

Growth tab, `#/analysis/AAPL/growth` loaded directly, window 1600 × 1100:

| level | width | `max-width` | note |
|---|---:|---|---|
| `html` / `body` / `div#root` | 1600 | `none` / `100%` | |
| `div.app` | 1600 | `none` | `display: grid`, `19rem 1fr` |
| `main.content` | 1258 | `none` | `grid-column: 2`, `min-width: 0` |
| `.tabs` / `.notice` / the chart's `<section>` | 1204 | `none` | `.content`'s content box |
| `.js-plotly-plot` | **1204** | `none` | |
| **the rendered `main-svg`** | **1204** | — | correct on this path |

`.content` is `1600 − 19rem`, and `19rem` is **342px** because `index.css` sets the root font to
18px — `rem` is always root-relative, never `.app`'s own 15px. `1600 − 342 = 1258`; minus
`padding: … 1.5rem` on each side gives `1258 − 54 = 1204`. Every number in the chain is exactly what
the CSS says it should be.

Across viewports it scales perfectly, so there is no cap anywhere:

| window | `.content` | content box = plot = svg |
|---:|---:|---:|
| 1280 | 938 | 884 |
| 1600 | 1258 | 1204 |
| 1920 | 1578 | 1524 |
| 2560 | 2218 | 2164 |

### 1.2 The baseline reconciles exactly — it was a scrollbar

The notice-width report's `1189px expanded / 1531px collapsed` did not match anything above, and the
first suspicion was that the baseline was unreproducible. It reproduces to the pixel. Adding a tall
spacer to force a vertical scrollbar on the same page:

| | content box, expanded | collapsed | scrollbar |
|---|---:|---:|---:|
| no scrollbar | 1204 | 1546 | 0px |
| **with scrollbar** | **1189** | **1531** | **15px** |

So `1189 / 1531` is the content box at a 1600px window **with a vertical scrollbar present**, which
every page that report measured had. The 15px is the scrollbar. **No level of the chain diverges from
the baseline** — the answer to Step 1.2 is that the divergence is not in the container chain at all.

### 1.3 Where it actually diverges

The divergence is one level *below* the chain the last two cycles mapped: between the container and
what plotly drew inside it. Landing on the Data tab first and then clicking Growth:

| | content box | `.js-plotly-plot` | **`main-svg`** | plotly's `_fullLayout.width` |
|---|---:|---:|---:|---:|
| while on **Data** (chart hidden) | 1189 | **0** | **700** | 700 |
| after clicking **Growth** | 1204 | 1204 | **700** ✗ | **700** ✗ |
| loading **straight onto Growth** | 1204 | 1204 | 1204 ✓ | 1204 ✓ |

The container is right and the drawing is not. That is why a container-chain walk found nothing, and
it is exactly the gap the brief names: a byte-identical figure spec rendering inside a correct box at
the wrong size.

### 1.4 Step 1.3 — is the Data tab affected?

No, and neither is any other container. The Data tab is full-width in both sidebar states (§4.2), and
the chart's *container* is full-width on every path. Only the SVG is wrong. So the cause is neither
"something item 9 added for the data tab that leaked into a shared wrapper" nor "something in the
shared shell's CSS" — it is not CSS at all.

---

## 2. Step 2 — diagnosis

### 2.1 The mechanism

**File:** `frontend/src/App.tsx`. **Element:** the `<div hidden={!isChartTab(tab)}>` that wraps
`ChartView`. **Rule:** the UA stylesheet's `[hidden] { display: none }`, combined with
react-plotly.js's resize handling.

1. `ChartView` is mounted for **every** tab and merely hidden, deliberately — the shell's module
   docstring records that unmounting would throw away a nine-metric selection because the reader
   glanced at another tab.
2. Landing on a non-chart tab therefore mounts `<Plot>` inside a `display: none` box. Its container
   measures **0**, so plotly falls back to its own default and writes `layout.width = 700`.
3. Revealing the tab removes `hidden`. The container grows to 1204px. **Nothing tells plotly.**
   `useResizeHandler` is a plain `window.addEventListener("resize", …)` — confirmed by reading
   `react-plotly.js/dist/create-plotly-component.min.js`'s `Q()` in the layout-fix cycle — not a
   `ResizeObserver` on the plot's own container, and a `hidden` attribute changing is not a window
   resize.

The SVG keeps 700px until something dispatches a real or synthetic `resize`.

### 2.2 It is not item 9 — proven, not argued

Two independent proofs, because "the only change since the last good screenshot" is a strong prior
and deserves better than a plausible story.

**Proof 1 — the artifacts of item 9 make no difference, in the live page.** Growth tab, 1600px:

| state | content box | plot | svg |
|---|---:|---:|---:|
| A. data tab never opened | 1204 | 1204 | 1204 |
| B. same, **`data-tab.css` disabled** at runtime | 1204 | 1204 | 1204 |
| C. same, after visiting Data so **`DataTab` is mounted** and hidden | 1204 | 1204 | 1204 |
| D. C, sidebar collapsed | 1546 | 1546 | 1546 |

Identical throughout. A class-name audit backs it up: every selector `data-tab.css` defines
(`.controls`, `.control`, `.section`, `.notice-inline`, `.table-scroll`, `.data-table*`, `.cell*`,
`.download`) is used only by `DataTab.tsx` / `DataTable.tsx`. `ChartView.tsx` contains **zero**
`className` attributes, so there is nothing for a stray rule to collide with. In the production
bundle `shell.css` is emitted *after* `data-tab.css`, so it wins ties as well.

**Proof 2 — a tree with item 9 reverted reproduces the defect exactly.** A copy of `frontend/` with
`DataTab.tsx`, `DataTable.tsx`, `pivot.ts`, `csv.ts` and `data-tab.css` deleted and `App.tsx`
restored to its item-9 placeholder, served on its own port:

| landing tab → Growth | pre-item-9 svg | current svg |
|---|---:|---:|
| `data` | **700** | **700** |
| `raw` (a placeholder item 9 never touched) | **700** | **700** |
| `growth` | 1204 | 1204 |

The `raw` row is the decisive one: Raw Facts is still the shell cycle's `Placeholder`, and it
reproduces the defect on both trees.

### 2.3 Why it survived three cycles

The shell-layout-fix cycle found and fixed the *sibling* of this bug — the sidebar collapsing changes
`.content`'s width through a grid reflow, and it added a synthetic `resize` on `sidebarOpen`. That
fix was correct and is still working. It just covered one of the two ways this container changes
size. The other way — a chart tab being revealed — was never on that cycle's list, because every
measurement it took loaded straight onto a chart tab, where the bug does not appear.

The check in §5 is the direct consequence.

---

## 3. What was changed

**One file, `frontend/src/App.tsx`; one effect.** The existing synthetic-resize effect now also fires
when the active tab becomes a chart tab:

```diff
-  useEffect(() => {
-    const id = requestAnimationFrame(() => window.dispatchEvent(new Event("resize")));
-    return () => cancelAnimationFrame(id);
-  }, [sidebarOpen]);
+  const activeTab = location.tab;
+  useEffect(() => {
+    if (!isChartTab(activeTab)) return;
+    const id = requestAnimationFrame(() => window.dispatchEvent(new Event("resize")));
+    return () => cancelAnimationFrame(id);
+  }, [sidebarOpen, activeTab]);
```

The comment above it was rewritten to name both reasons the container changes size rather than only
the sidebar, so the next reader does not have to rediscover the second one.

**The gate is load-bearing, not tidiness.** Firing on a switch *to* a non-chart tab would resize the
plot against a container that is still `display: none` and 0px wide — which is the failure mode, not
the fix. Effects run after commit, so when the destination is a chart tab the box is already visible
at its real width.

**Nothing else was touched.** Not `ChartView.tsx`, not `<Plot>`'s props, not `panel.ts` / `grid.ts` /
`mean.ts`, not a builder, not a stylesheet. This is a synthetic DOM event and cannot reach what
`ChartView` builds — §4.3 confirms it did not.

The durable alternative, considered and not taken: a `ResizeObserver` on the plot's container inside
`ChartView` would fix both triggers and any future one, permanently, instead of announcing each by
hand. It is the more correct mechanism. It also edits the one component on the chart path, for a
defect that a four-line change outside it demonstrably closes. If a third trigger ever appears, that
is the moment to make the change rather than to add a third dependency to this effect.

---

## 4. Verification

### 4.1 Widths restored, everywhere

Every combination of **entry path × chart tab × sidebar state** — 24 renders:

| landing tab | chart tab | expanded | collapsed |
|---|---|---|---|
| `data`, `raw`, `comparison`, `growth` | Growth, Fundamentals, Valuation | container **1204** = svg **1204** | container **1546** = svg **1546** |

**24 of 24 match**, with no exceptions and no special cases. With a scrollbar present these are 1189
and 1531 — the notice-width baseline, exactly (§1.2).

### 4.2 The Data tab is unaffected

Re-measured against what item 9 established, in both sidebar states:

| | expanded | collapsed |
|---|---:|---:|
| `.tabs` | 1189 | 1531 |
| `.data-tab` | 1189 | 1531 |
| the first table's scroll container | 1189 | 1531 |
| sections | 5 | 5 |
| facts rows × columns | 16 × 35 | 16 × 35 |
| null cells rendered | 86 | 86 |
| the null-column caption clause present | yes | yes |

Identical to the item-9 report, and full-width in both states.

### 4.3 The three charts are unchanged as data

The item-8 sweep, re-run against the current tree and the pre-cycle tree:

| | |
|---|---:|
| tickers | 41, spanning all 24 profiles |
| figures per tree | 3,936 |
| traces | 9,023 |
| data points | 213,205 |
| serialised bytes | 21,605,698 |
| sha256, both trees | `1987837d155d3adfc9252ccdf2406bab502dd555324fd14d113432e067f38e8a` |
| **byte-identical** | **yes** |

Unchanged from the item-9 report's baseline, as it must be: this cycle touched no file the sweep
loads. (That hash is this project's current baseline; the older `919868ca…` came from a scratch
harness whose ticker list is not fully recorded — see the item-9 report §5.)

### 4.4 Build

`npx tsc -b`, `npx eslint .`, `npx vite build` — all clean. `git status` shows `App.tsx` and the new
`frontend/scripts/` as this cycle's only changes; everything else listed predates it. Nothing outside
`frontend/` changed. No scratch files were left behind; both dev servers and the headless browser were
stopped and confirmed down.

---

## 5. Step 4.5 — the check that should have caught this, and it now exists

**Content-equality verification cannot catch this class of regression, and it is worth being precise
about why.** The item-8 harness compares figure *specs* — `fig.data`, `fig.layout`, every trace,
annotation, shape and axis. It never renders anything: it runs in Node, where there is no DOM, no
layout and no plotly. Its subject is *what the app decided to draw*. This bug is entirely in *what
the browser then drew it into*, and the two are independent — which is exactly why the sha256 above
is unchanged across a cycle that fixed a visible defect. Three cycles have now closed a width defect
that was found by a person looking at a screenshot.

So one was built, and it is deliberately small: **`frontend/scripts/check-chart-width.mjs`**, about
120 lines, no dependencies (Node's native `fetch` and `WebSocket`), launching its own headless
browser.

```
node scripts/check-chart-width.mjs                       # against localhost:5173
APP_URL=http://localhost:5185 node scripts/check-chart-width.mjs
```

**The invariant is not a golden pixel number**, and that is the main design decision. The last two
cycles recorded `1189 / 1531` as the baseline; those turned out to depend on a scrollbar being
present (§1.2), so asserting them would produce a false failure the first time a page got shorter.
What is invariant at any viewport, any sidebar state and either scrollbar state is:

> the plot container's width **===** the rendered `main-svg`'s width

It walks the same 24 combinations as §4.1 and exits non-zero on any mismatch.

**It was verified by failing.** A check that has never failed is not yet a check, so it was run
against the pre-fix tree as well:

| tree | result | exit |
|---|---|---:|
| pre-fix | **9 of 24 fail** — every `data` / `raw` / `comparison` entry, sidebar expanded, `container 1174px, svg 700px` | 1 |
| current | **24 of 24 pass** | 0 |

The 15 that pass on the buggy tree are all the collapsed-sidebar cases, because collapsing fires the
existing `sidebarOpen` effect and repairs the width as a side effect — which is a precise
confirmation of §2.1's mechanism, arrived at from the opposite direction.

**Deliberately not wired into `npm test` or CI.** It needs a running dev server and a real
Edge/Chrome; a check that cannot run in the environment it is attached to is worse than one that is
asked for by name. The recommendation is to run it in the same pass as `tsc` / `eslint` / `vite
build` on any cycle that touches the shell, `App.tsx`, `ChartView.tsx` or a stylesheet — it takes
about a minute.

---

## 6. What to re-check by hand

**Please open the app and click Data → Growth**, then Raw Facts → Fundamentals, at a normal window
width and with the sidebar both expanded and collapsed. That sequence is the reproduction, and it is
the one every previous cycle's verification happened to skip.

Two things this report deliberately does not claim:

1. **The `.intro` paragraph is now full width** — it was 501px (`max-width: 62ch`) when the
   notice-width cycle measured it. That rule, and `.notice__body`'s matching cap, are no longer in
   `shell.css`; the file's timestamp puts the edit shortly before this task was written, so it reads
   as your own change and was left alone. If it was not intended, say so and it is a two-line
   restoration.
2. **The `ResizeObserver` alternative** (§3) is the mechanically correct fix and was not taken. If
   the shell grows a third way to change the chart's container width — a resizable sidebar, an
   animated collapse, a print stylesheet — that is the point to switch, rather than adding another
   dependency to one effect.
