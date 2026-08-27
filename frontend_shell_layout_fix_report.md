# Shell layout bugs: collapse reflow and full-width content

Both named defects, plus a third one the investigation surfaced that explains the "chart doesn't
grow" half of Defect B more precisely than the CSS candidates in the brief. All three root causes
were confirmed by **measuring a real, running instance of the app in a real browser** — headless
Edge driven over the DevTools Protocol, no synthetic stand-in — before anything was changed, and
the same instrument re-confirmed each fix afterward.

---

## 1. The container tree

From `#root` down to the plot, as rendered (not as guessed):

```
#root                         display: flex; flex-direction: column
                               width: 100% (the operator's fix already in place)
└─ div.app                    display: grid; grid-template-columns: 19rem 1fr
                               (.app--collapsed → 0 1fr when the sidebar is hidden)
   ├─ aside.sidebar            [.sidebar--closed → display: none, when collapsed]
   │  └─ div.sidebar__inner    position: sticky
   │     └─ button.sidebar__close   the "×" — the collapse control
   └─ main.content            padding: 1rem 1.5rem 4rem; min-width: 0
      ├─ header.content__head  display: flex
      ├─ p.intro               max-width: 62ch   <- the subtitle
      ├─ nav.tabs               display: flex; flex-wrap: wrap
      └─ div[hidden?]           plain block, no CSS of its own
         └─ section (ChartView) plain block, no CSS of its own
            └─ div.js-plotly-plot   style={{width:"100%", height:<layout.height>}}
               └─ svg.main-svg      sized by Plotly's own JS, not by CSS
```

`App.css` (184 lines of Vite-scaffold hero/next-steps/docs styling) is **not imported anywhere** —
grepped for `App.css` across every `.tsx` file, one hit, in nothing that renders. It is inert and
was not touched. The live stylesheets are `index.css` (global reset + `#root`) and
`shell/shell.css` (everything shown above).

Every `display`/`width`/`min-width` value above is a real `getComputedStyle` reading from a live
render, not a reading of the source, and the "no CSS of its own" annotations were confirmed the
same way: `<div hidden>` and `<section>` in `ChartView.tsx` carry no `className`, so their layout
is whatever a plain block element with `width: auto` computes to.

---

## 2. Defect B, diagnosed before A as instructed

Measured on a real render at 1600px viewport, sidebar expanded, before any fix:

| element | computed width | rule in force |
|---|---:|---|
| `.content` | **1189px** | `1fr` grid track, correctly filling the remaining space |
| `.js-plotly-plot` (the div `<Plot>` mounts into) | **1189px** | inline `style={{width:"100%"}}` from `ChartView.tsx:180`, resolving against `.content` |
| `svg.main-svg` (Plotly's own rendered chart) | **1189px** | matches its container |
| `p.intro` | **501px** | `shell.css`'s `.intro { max-width: 62ch; }` |

**The chart's container was not broken.** All three candidates the brief lists — a content wrapper
missing `width: 100%`/`flex: 1`, the Plot's own container lacking an explicit width source, a
leftover `max-width` on the chart side — were checked against the real tree and none apply: `.content`
already stretches correctly in the grid's `1fr` track, and `<Plot style={{width:"100%"}}>` already
gives it an explicit source that resolves correctly. Re-tested at 1000px and 1800px, and across a
live resize (1000px → 1800px with a real `resize` event), the chart tracked the container exactly
(633px → 1389px) both times. There is no missing width rule here.

**The subtitle's cap is the third candidate — and it is not a leftover.** `.intro { max-width: 62ch;
}` is a rule I wrote in the previous cycle when the shell was built, not a scaffold remnant that
survived the `#root` cleanup by accident. It had no comment explaining the choice, which is why it
reads as accidental — that is now fixed (§4). 62ch is one of the two things this cycle needed to
settle, and both check out: it renders at 501px on a 1600px viewport, comfortably inside the
"well short of 1126px" guidance and inside the usual 60–75-character prose-readability range, and
it is completely unrelated to the `#root` width — it constrains the paragraph's own box regardless
of how wide `.content` is.

**So the two symptoms bundled into "Defect B" have different explanations.** The subtitle is
working as designed. The chart's *container* is also working as designed in the state actually
tested (expanded, at rest). What *is* broken is a third thing, found while tracing why a chart's
own SVG might not track a change that isn't a window resize:

> **`react-plotly.js`'s `useResizeHandler` only listens for a native `resize` event on `window`.**
> Read from `node_modules/react-plotly.js/dist/create-plotly-component.min.js`, the function that
> wires it up (`Q`, in the bundle's minified source) does exactly one thing when the prop is set:
> `window.addEventListener("resize", () => Plotly.Plots.resize(el))`. There is no `ResizeObserver`
> on the plot's own container anywhere in the library.

That is the *stale default* the brief's second candidate anticipates, just not from a missing width
rule — from a resize signal that only fires for one specific cause (the OS window changing size) and
silently does nothing for every other reason a container's width can change, including a sibling
grid column collapsing. Measured directly: clicking the sidebar's collapse control grows `.content`
from 1189px to 1531px correctly, and the `<div class="js-plotly-plot">` wrapper follows it (it is a
plain CSS width, so it has no choice) — but `svg.main-svg`, whose size is set by Plotly's own JS,
**stayed at 1189px**, unchanged, until something fired a `window` `resize` event. This is very
likely what the operator's "chart similarly does not grow" screenshot shows, taken after some
interaction rather than on first paint — the container is fine, the number Plotly last computed is
not.

---

## 3. Defect A and the click target, diagnosed

### 3.1 The standing hypothesis was wrong, and the real mechanism is CSS Grid, not Flexbox

The brief's hypothesis — a flex child missing `min-width: 0`, refusing to shrink below its
intrinsic content width — doesn't apply: **`.app` is `display: grid`, not `display: flex`.** There
is no flex container between the sidebar and the content at all.

The actual mechanism, confirmed by isolating it down to two nodes and nothing else:

```html
<style>.app{display:grid;grid-template-columns:19rem 1fr} .hidden{display:none}</style>
<div class="app">
  <aside class="hidden">SIDE</aside>
  <main>CONTENT</main>
</div>
```

With the aside `display: none`, `<main>`'s measured width is **304px** — exactly `19rem`, the
*first* track — not the remaining space in the second. **A grid item with `display: none` is
removed from the grid's item list entirely; it does not reserve its column position for the items
that come after it.** CSS Grid's auto-placement algorithm assigns tracks to items in document order
among the items that still generate boxes, so once the sidebar stops generating one, `.content`
becomes the *first* auto-placed item and lands in column 1 — whatever that column's width happens to
be. In the real app that width is `19rem` normally and `0` under `.app--collapsed`, which is why the
symptom appears specifically *after* collapsing rather than at rest: collapsing does two things at
once — it removes the sidebar's box (triggering the mis-placement) and it also zeroes column 1's
track size (turning that mis-placement into a literal 0px width instead of a merely-wrong 304px
one).

Confirmed on the real app before any fix, sidebar collapsed, 1600px viewport:

| element | computed width |
|---|---:|
| `.content` | **0px** |
| `p.intro` | **0px** |
| the chart's section | **0px** |
| `.js-plotly-plot` | **0px** |

Zero, not "narrow" — which is exactly "each word on its own line": a block box with 0 available
width still lays out one word per line rather than erroring, because words cannot be split.

### 3.2 What collapse actually does

`display: none` on the `<aside>`, via the `.sidebar--closed` class the `Sidebar` component adds
when its `open` prop is false — confirmed by reading `Sidebar.tsx` and `shell.css` together, not
assumed. Simultaneously, `.app--collapsed` changes `grid-template-columns` from `19rem 1fr` to
`0 1fr`. Both are real, and the second one is *not* the bug — a 0-width first track is exactly what
a collapsed sidebar should produce, and does no harm once `.content` is pinned to the second track
instead of drifting into whichever one happens to be empty.

### 3.3 The click target

Measured directly rather than estimated: `getBoundingClientRect()` on the real `.sidebar__close`
button, in the expanded state, before any fix: **26 × 25px**, with `getComputedStyle(...).padding`
reading **`1px 6px`** — a value the stylesheet never sets. `.sidebar__close` declares no `padding`,
`width`, or `height` at all; the entire box comes from the browser's default `<button>` user-agent
padding plus the "×" glyph's own font metrics at `font-size: 1.3rem`. That is comfortably over the
brief's ~24×24px floor in absolute terms, but it is sized by accident — nothing in the rule set
guarantees it, and a different UA stylesheet, a CSS reset applied elsewhere, or a font substitution
would shrink it with nothing here to stop that. That fragility, not the raw pixel count, is the
defect: a hit area with no explicit floor.

---

## 4. What was changed

All three fixes are in `frontend/src/shell/shell.css`; one additional fix is in `frontend/src/App.tsx`
for the reason in §2. No chart builder, `panel.ts`, `grid.ts`, or `mean.ts` was touched.

| defect | file | change |
|---|---|---|
| A — collapse reflow | `shell.css` | `.sidebar { grid-column: 1; }` and `.content { grid-column: 2; }` — explicit placement, independent of which items currently generate a box |
| B — subtitle cap | `shell.css` | no value change; added the comment explaining the 62ch choice and confirming the chart carries no such cap |
| B — chart stale-SVG | `App.tsx` | a `useEffect` keyed on `sidebarOpen` that dispatches a synthetic `window` `resize` event one animation frame after the toggle, reaching `useResizeHandler`'s existing listener without touching `ChartView`, `<Plot>`, or the figure spec |
| click target | `shell.css` | `.sidebar__close` given explicit `width: 28px; height: 28px; padding: 0;` with `display: inline-flex; align-items: center; justify-content: center;` to keep the glyph centered in the fixed box |

**On the subtitle's max-width, explicitly, as asked:** kept at `62ch` (~500px on a 1600px viewport).
That is a deliberate readability choice, not an oversight — a prose line at 1400+px is not more
readable than one wrapped at a sane width, and 62ch sits well inside the standard 60–75-character
guidance and well short of the old 1126px cap. The chart, the tabs, and everything else in
`.content` carry no such cap and use the full column width; only this one paragraph is capped, on
purpose, and the reason is now in the stylesheet next to the rule rather than only in this report.

---

## 5. Verification

### 5.1 Reproduced first, with numbers — before any change

| | expanded | collapsed |
|---|---:|---:|
| `.content` computed width | 1189px | **0px** |
| `p.intro` computed width | 501px | 0px |
| chart section computed width | 1189px | 0px |
| `.js-plotly-plot` computed width | 1189px | 0px |
| `svg.main-svg` width | 1189px | 1189px *(stale — the container was 0px)* |
| `.sidebar__close` hit area | 26×25px | — |

### 5.2 Confirmed after the fix — same instrument, same real app

| | expanded | collapsed | after re-expanding |
|---|---:|---:|---:|
| `.content` computed width | 1189px | **1531px** | 1189px |
| `p.intro` computed width | 501px | 501px | 501px |
| chart section computed width | 1189px | **1531px** | 1189px |
| `.js-plotly-plot` computed width | 1189px | **1531px** | 1189px |
| `svg.main-svg` width | 1189px | **1531px** | 1189px |
| `.sidebar__close` hit area | **28×28px** | — | — |

Every collapsed-state width now matches `.app`'s available space (1585px viewport minus 48px
padding minus a couple of rounding pixels ≈ 1531px) instead of 0, the Plotly SVG's own rendered
width now tracks the container instead of staying stale, the round trip (expand → collapse →
re-expand) returns to the exact original 1189px with nothing left over, and the subtitle's 501px is
unchanged in every state — confirming its cap is independent of the sidebar, as designed.

Two screenshots taken of the real running app (1500×950 viewport) confirm this visually: the
collapsed screenshot shows the paragraph and the chart both filling the freed width with normal text
wrapping, not one word per line; a cropped, upscaled close button shows the "×" centered in its
enlarged box.

### 5.3 The three charts, as data — unaffected

The item-8 harness (every chart, every window setting 0/1/2/3/5/10/15/omitted, four selection
shapes, 39 tickers spanning all 24 profiles) was re-run against the current tree and against a
reconstructed pre-fix tree (this cycle's `App.tsx` change reverted; the CSS files this harness never
touches were left as-is either way, since nothing in `charts/*` or `data/load.ts` imports CSS).

| | |
|---|---:|
| figures | 2,808 |
| traces | 8,695 |
| data points | 204,067 |
| serialised bytes | 20,347,001 |
| sha256 | `919868ca5e63c299d6bc778ed8252b66040ddc6cf962764569f6e4f985c30ee9` |
| **byte-identical to the pre-fix tree** | **yes** |

The same sha256 as the last two cycles' baseline. This is expected rather than merely hoped for:
`specs.ts` imports only `data/load.ts` and `charts/*`, and this cycle's changes are in `shell.css`
(never imported by that path) and in `App.tsx` (never imported by it either — `ChartView.tsx`,
which *is* on that path, was not touched). A container width fix and a synthetic resize dispatch
have no route to the figure spec at all; the byte identity confirms that route doesn't exist rather
than merely that it wasn't exercised.

### 5.4 Build

`npx tsc -b`, `npx eslint .`, `npx vite build` — all clean. `git status` after the fix shows only
files inside `frontend/`; nothing else changed.

### 5.5 What this verification is and is not

Unusually for this project, most of the numeric claims above **were** checked in a real browser —
Edge, headless, driven over the DevTools Protocol against the actual `npm run dev` server with a
real ticker's real chart, clicking the actual collapse button rather than simulating the click. That
was necessary here specifically because layout bugs live in the DOM and CSS in a way a Node-side
figure-spec comparison cannot see, and the brief asked for exactly this rigor.

What is still **not** checked, and needs the operator's own eyes:

- **The overall visual result on the operator's own machine, browser and monitor.** Font rendering,
  DPI scaling, and the exact Edge/Chrome version can all shift a few pixels; the mechanism fixed
  here is structural (grid placement, an explicit hit-area, a resize signal) and will hold across
  those variations, but "does it look right" is inherently a human judgement.
- **The sub-860px responsive breakpoint** (the sidebar-as-overlay behavior noted as untested in the
  shell report) — not touched this cycle and not re-checked.
- **Keyboard/focus behavior of the enlarged close button** — it is still a plain `<button>`, so
  focus and Enter/Space activation should be unaffected, but this was not separately tested.
- **Whether the one-frame delay before the synthetic resize dispatch (`requestAnimationFrame`) is
  imperceptible or produces a visible one-frame flash of the stale chart size.** The measured
  numbers confirm the *end state* is correct within ~500ms; whether the transition itself looks
  smooth during the collapse animation (there is currently no CSS transition on the grid columns,
  so this is likely an instant snap either way) was not assessed frame-by-frame.

**Please re-check in a real browser before treating this as closed** — reproduce the collapse click
and the subtitle/chart appearance at a normal window width, on your own machine, the way the
original screenshots were taken.

No scratch files were left behind; the temporary headless-browser session and dev server used for
measurement were both stopped.
