# The update notice was width-capped by its own rule, not the subtitle's

The previous cycle's container tree stopped at `.intro` and `.tabs`/the chart; it never measured
`.notice` at all, so the notice box inheriting a `62ch`-shaped constraint went unnoticed. It turned
out not to be inheritance — the notice had its own, separate `62ch` rule that happened to compute
to the exact same pixel width as the subtitle's, which is what made a screenshot alone look like one
rule serving two elements.

---

## 1. Measurement, before touching anything

Same instrument as the previous cycle: headless Edge over the DevTools Protocol, driving the real
`npm run dev` server, 1600px viewport, a real ticker's real render.

| element | computed width | `max-width` (computed) |
|---|---:|---|
| `.content` | 1189px | `none` |
| **`.notice`** | **501.328px** | **501.328px** |
| `.notice__body` | 406px | `none` |
| the Dismiss button | 77px | `none` |
| `p.intro` | 501.328px | 501.328px |
| `.tabs` | 1189px | `none` |
| the chart's section | 1189px | `none` |

**The exact rule, before it was touched:** `frontend/src/shell/shell.css`, the `.notice` block —

```css
.notice {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  border: 1px solid var(--shell-line);
  border-radius: 6px;
  background: var(--shell-panel);
  padding: 0.75rem 1rem;
  margin: 0.8rem 0;
  max-width: 62ch;          /* <- this line */
}
```

**Confirmed independent of `.intro`, not shared or inherited**, by walking the real ancestor chain
from `.notice` up to `.content`: `.content` and `.app` both compute `max-width: none`. `.notice` is
not selected by `.intro`, and no common ancestor carries a cap. The `501.328px` match is a
coincidence of value, not a shared mechanism — both rules independently resolve `62ch` in the same
`.app` font context (`font: 15px/1.5 ...`), so the same character count produces the same pixel
figure on both elements. The brief's warning that this could be "its own, coincidentally similar
value" rather than a shared rule is exactly what measuring found — it was not assumed.

**The Dismiss button is inside the capped box**, confirmed by its own rect: at `left:812, right:889`
against the box's `right:908` — pulled in with the text, not pinned to a fixed position independent
of it, exactly as the screenshot suggested and exactly as `UpdateNotice.tsx`'s markup predicts
(`<aside class="notice"><div class="notice__body">…</div><button>…</button></aside>` — both are
direct children of the one flex box that carried the cap).

---

## 2. What was changed

One file: `frontend/src/shell/shell.css`. `.intro`'s rule and value are untouched — grep confirms
`max-width: 62ch` still appears exactly once outside the notice block, on `.intro`, unchanged.

1. **`.notice` lost its `max-width: 62ch`.** The box itself — border, background, padding — now
   spans `.content`'s full available width, exactly like `.tabs` and the chart's section below it
   (neither of which ever had a width rule; they simply are plain flex/block children with nothing
   constraining them, which is what `.notice` now also is).

2. **`.notice__body` gained its own `max-width: 62ch`.** This is the refinement the brief allows for
   explicitly, and it is not speculative: the current notice content
   (`content/update_notice.md`, copied into `frontend/public/`) has a 143-character line with no
   source line break —

   > *"Caught a bug in raw facts; annotat_no_data wasnt implemented in the raw facts pipeline. Now
   > fixed, figures without data behave as expected now."*

   At the box's new ~1200–1500px width that line would render unwrapped, as one very long line with
   a large empty gap to its right before the Dismiss button. `62ch` — the same reading-width value
   `.intro` uses, reused here because this text is prose in exactly the same sense the subtitle is —
   keeps it readable regardless of how wide the surrounding callout grows. `flex: 1` still applies
   and does not conflict: flexbox clamps a flex item's final size to its `max-width`, so the body
   grows to fill the row up to 62ch and then stops, rather than fighting the cap.

3. **The Dismiss button was given `margin-left: auto`.** At the old 62ch box, the button's position
   immediately after the text and the button's position at the box's right edge were the same
   position, by coincidence. Decoupling the box from the text left a real gap between them once the
   box grew, and without an explicit rule the button would have simply sat wherever flexbox's
   default alignment left it — immediately after the (now much narrower relative to the box) text,
   with a large dead stripe of border/background to its right and no logical reason for the button
   to be positioned there instead of at the edge. `margin-left: auto` on a flex item pushes it to the
   end of the flex container, which is the standard placement for an action button in a full-width
   banner and was stated as a decision rather than left as whatever fell out of the change.

Both new rules carry a comment explaining the reasoning, so the next reader does not have to
re-derive it from a screenshot.

---

## 3. Verification

### 3.1 Before and after, same instrument

| | before | after |
|---|---:|---:|
| `.notice` computed width, expanded (1600px viewport) | 501px | **1189px** |
| `.notice` computed width, collapsed | 501px | **1531px** |
| `.notice__body` computed width, expanded | 406px | 501px *(now the cap itself, not a fraction of a smaller box)* |
| Dismiss button position, expanded | `right: 889` (box `right: 908`) | `right: 1539` (box `right: 1558`) — at the edge |
| `p.intro` computed width, expanded | 501.328px | **501.328px — unchanged** |
| `p.intro` computed width, collapsed | 501.328px | **501.328px — unchanged** |

The subtitle's width did not move by a fraction of a pixel in either sidebar state — the check that
confirms the two elements were actually decoupled, not both accidentally widened together.

`.notice` now matches `.content`, `.tabs` and the chart's section exactly in both sidebar states
(1189px expanded, 1531px collapsed), the same numbers the previous cycle established for those
other elements.

### 3.2 No collapse regression

`.notice` is not a grid child — it sits inside `.content`, one level below the grid the previous
cycle's `grid-column` fix addressed — so it was never exposed to Defect A's mechanism (an
auto-placed grid item losing its column when a sibling goes `display: none`). Measured directly
anyway, since the brief asked for it explicitly: collapsed-state width is **1531px**, not 0px. A
screenshot of the real collapsed render confirms it visually — full-width box, wrapped text, Dismiss
at the far right, no reflow.

### 3.3 The Dismiss button, functionally

Clicked (not simulated) on the real render at the new width:

| step | result |
|---|---|
| notice present before click | `true` |
| `sessionStorage["update_notice_dismissed"]` before | `null` |
| notice present after click | `false` |
| `sessionStorage["update_notice_dismissed"]` after | `"1"` |
| notice present after a full page reload, same session | `false` |

Dismissal and its session-length persistence — both established in the shell cycle — are unaffected
by the width change, as expected: nothing about `notice.ts`'s logic was touched.

### 3.4 The three charts, as data

The item-8 harness (2,808 figures: 39 tickers × 3 charts × 8 window settings × 4 selection shapes)
was re-run against the current tree.

| | |
|---|---:|
| figures | 2,808 |
| traces | 8,695 |
| points | 204,067 |
| sha256 | `919868ca5e63c299d6bc778ed8252b66040ddc6cf962764569f6e4f985c30ee9` |
| **matches the standing baseline from the last two cycles** | **yes** |

Expected rather than merely hoped for: this fix is entirely inside `shell.css`, which nothing on the
figure-building path (`data/load.ts`, `charts/*`) imports.

### 3.5 Build

`npx tsc -b`, `npx eslint .`, `npx vite build` — all clean, run from `frontend/` after confirming the
working directory (the first attempt was run from the repo root by mistake and failed to resolve
`index.html`; re-run from the correct directory succeeded). `git status` shows only files inside
`frontend/` changed, plus the operator's own `task_new.md` and this report.

### 3.6 What to re-check

This task exists because a prior "verified" layout fix missed an element the report's own container
tree simply didn't include. The same caution applies here with more reason, not less: **please
reload the app in a real browser and look at the notice box yourself** — at a normal window width,
with the sidebar both expanded and collapsed, and by actually clicking Dismiss — before treating this
as closed. Font rendering and exact line-wrap points at `62ch` can shift by a word or two between
browsers in a way that is only worth seeing, not worth re-deriving numerically.

No scratch files were left behind; the temporary dev server and headless-browser session used for
measurement were both stopped.
