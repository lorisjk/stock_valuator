# Item 22 — The About Page

`render_about` (app.py:744–765) and `split_sections` (app.py:722–741), ported. **The last item on
the rebuild list**, and the one that empties `Placeholder`'s final call site.

---

## 1. Step 1 — the reference, read exactly

### 1.1 `split_sections`' contract

```python
def split_sections(text: str) -> list[tuple[str, str]]:      # app.py:722
    sections, heading, body = [], "", []
    for line in text.splitlines():
        if line.startswith("## "):                            # app.py:731
            if heading or any(l.strip() for l in body):       # app.py:733
                sections.append((heading, "\n".join(body).strip()))
            heading, body = line[3:].strip(), []              # app.py:735
        else:
            body.append(line)
    if heading or any(l.strip() for l in body):               # app.py:739
        sections.append((heading, "\n".join(body).strip()))
    return sections
```

- **Return shape:** a `list` of `(heading, body)` **tuples, in file order** — not a dict, so duplicate
  headings survive as separate entries and order is not at the mercy of key insertion.
- **The marker is `"## "`, with its trailing space** (app.py:731) — verified rather than assumed.
  `###` and deeper stay inside the body where markdown renders them, and a bare `##NoSpace` is not a
  heading. Both are in the edge-case table (§3.1).
- **Before the first heading:** the run comes back as `("", intro)` — but only if it has a non-blank
  line. app.py:733's guard is `heading or any(l.strip() for l in body)`, so a file that opens directly
  on `## ` emits nothing for the empty run, while a heading with an empty body **is** emitted (the
  heading alone makes it truthy).
- `heading` is `line[3:].strip()`; `body` is `"\n".join(body).strip()`.

### 1.2 The disclaimer treatment: `st.warning(body)`

```python
if heading.strip().lower() in PROMINENT_ABOUT_SECTIONS:   # app.py:763
    st.warning(body)
else:
    st.markdown(body)                                     # app.py:765
```

The difference is **which container the markdown goes into**, not what the markdown is — the same
body text, drawn as a warning callout instead of as page prose. Streamlit's `st.warning` renders its
argument as markdown, so bold and links survive either way.

The comment above the constant (app.py:75–77) is the reasoning: *"The disclaimer has to be visible
without scrolling past the introduction, and that is a rendering decision rather than something the
text can enforce about itself."*

### 1.3 `disclaimer` is genuinely the only special case

`PROMINENT_ABOUT_SECTIONS = {"disclaimer"}` (app.py:78) — a **set with exactly one member**. There is
no second branch anywhere in `render_about`: every other heading falls to `st.markdown`. Verified in
the code, and then verified in the browser (§3.2): the rendered page has exactly **1** callout and
**6** plain bodies.

The port keeps it a *set* rather than an equality against `"disclaimer"`, so the mechanism stays the
reference's and a second prominent heading remains a one-word change on both sides.

Two further conditionals sit around it and are not special cases: `if heading:` (app.py:759) draws the
subheader, and `if not body: continue` (app.py:761–762) skips an empty body — in that order, so a
heading with no text renders its heading and nothing else.

### 1.4 Page order is file order — confirmed against the current file

`split_sections` appends as it walks and `render_about` iterates the list. On today's `content/about.md`
that gives **7 sections, no `("", intro)` run** (the file opens on `## What this is`) and **no HTML
comments** to strip:

| # | heading | body |
|---|---|---:|
| 1 | What this is | 486 chars |
| 2 | **Disclaimer** ← callout | 1,229 |
| 3 | Data sources | 1,839 |
| 4 | Source code | 65 |
| 5 | Contact | 63 |
| 6 | Legal notice / Impressum | 193 |
| 7 | Privacy | 1,573 |

### 1.5 Where `about.md` comes from — and the hand-off was wrong

The reference reads `os.path.join(CONTENT_DIR, ABOUT_FILE)` (app.py:125) where
`CONTENT_DIR = <app dir>/content` (app.py:71) and `ABOUT_FILE = "about.md"` (app.py:72), through
`read_content`, which returns `""` for an absent or unreadable file rather than raising.

**The frontend had no sibling copy.** Item 21's hand-off said `about.md` was *"already at a path next
to `update_notice.md`"*; `frontend/public/` contained `update_notice.md` and nothing else. Step 1.5
asked for verification rather than assumption, and this is what it turned up. So this cycle **adds**
`frontend/public/about.md` as a byte-identical copy —
`sha256 98dfef50dcfaef690f51b58760fe921bb40f28295c88284ccefdc3735c080dc9`, confirmed equal to
`content/about.md` by `cmp`.

That follows the established pattern rather than inventing one: `frontend/public/update_notice.md` is
also a hand-made copy of `content/update_notice.md` (still byte-identical today), and **nothing in the
repo copies either** — no build step, no export script, no `main.py` hook. See §5 for the drift risk
that creates.

### 1.6 The missing-content branch

```python
if not text.strip():                                   # app.py:748
    st.warning(f"No About content found. Expected `{ABOUT_FILE}` in `{CONTENT_DIR}`. "
               "The page is text held in a file so it can be edited without changing "
               "code; create that file to fill this page in.")
    return
```

The test runs on `strip_comments(read_content(...))` (app.py:747) — comments first, emptiness second,
so a file holding nothing but `<!-- -->` instructions counts as empty. That is item 23's rule and the
same `stripComments` is reused here, because the reference reuses the same function.

The comment above it is the whole difference between this page and the notice: *"A missing About file
is a deployment mistake rather than a valid state, so unlike the notice it says so -- but it still
must not raise."*

---

## 2. Step 2 — design

### 2.1 The fetch: `fetchNotice`'s twin

`fetchAbout(base)` sits beside `fetchNotice` in `load.ts` with the same body — status guard, **content-type
guard**, `try/catch` — returning `string | null`.

"Lenient" means precisely: **any failure produces `null`, never a throw.** A 404, a network error, a
CORS refusal, and a dev server's SPA fallback (200 + `text/html`) all land in the same branch. What
differs is what the caller does with it: the notice draws nothing, About draws the deployment warning.

The content-type guard is not defensive decoration — §3.3 shows it is the branch that actually fires.

### 2.2 The split: a pure module

`shell/about.ts` — `splitSections`, `isProminent`, `PROMINENT_ABOUT_SECTIONS` — React-free and
Node-runnable, beside `notice.ts` and for the same reason: the rule can be compared against Python
directly (§3.1), which is how `mean.ts`, `select.ts` and the picker rules are all verified.

One deliberate divergence, named in the code rather than left to be found. Python's `splitlines()`
breaks on more terminators than `split("\n")`; the port reproduces `\r\n`, `\r`, `\v`, `\f`,
` `, ` ` and the dropped trailing empty field, and **does not** reproduce `\x1c`–`\x1e` and
`\x85`. Those four cannot occur in a hand-typed markdown file, and writing them into a character class
costs an `eslint no-control-regex` suppression to buy a case that does not exist.

The `\r` half is not hypothetical housekeeping: `about.md` is edited by hand, and under `split("\n")`
a CRLF save leaves a `\r` on the end of every line. Headings survive (`.slice(3).trim()`), bodies do
not — every interior line keeps its `\r`. §3.1's mutation table demonstrates exactly that.

### 2.3 The disclaimer's rendering: `.notice-inline`, widened

`.notice-inline` has been this build's `st.warning` since item 12 — the comparison tab's exclusions,
item 17's empty-panel notice, item 20's undocumented list. Reusing it keeps the disclaimer reading as
the same kind of thing rather than as a fourth invented callout.

It needed one adjustment, not a replacement: the class is `display: inline-block` and sized for a
single sentence, and the disclaimer is five paragraphs. `.about__disclaimer` overrides only the
sizing — block, full measure, roomier padding — and keeps the border, background and warn-coloured
left edge that *are* the callout's identity.

### 2.4 `Placeholder.tsx`: deleted

Its docstring made this the intended end state: *"Adding item 9 should be **replacing** this in one
place, not inventing a slot — and until then every unbuilt surface reads as deliberately pending
rather than as something that failed to load."* With item 22 built there is no unbuilt surface left,
so the component has no job.

A repo-wide search found exactly one importer (`App.tsx`) and no other reference — no harness, no
test, no dynamic import. Deleted, along with its three now-dead CSS rules in `shell.css`
(`.placeholder`, `.placeholder h2`, `.placeholder__badge`) and its half of the shared
`.notice button, .placeholder__badge` selector. `App.tsx`'s module docstring records why it is gone.

---

## 3. What was implemented, and Step 4's results

| file | change |
|---|---|
| `frontend/src/shell/about.ts` | **new.** `splitSections`, `isProminent`, `PROMINENT_ABOUT_SECTIONS`. Pure |
| `frontend/src/About.tsx` | **new.** The page: fetch-on-open, comment strip, empty branch, section loop |
| `frontend/src/about.css` | **new.** 78ch measure, section spacing, the widened callout |
| `frontend/public/about.md` | **new.** Byte-identical copy of `content/about.md` (§1.5) |
| `frontend/src/data/load.ts` | `fetchAbout`, beside `fetchNotice` |
| `frontend/src/App.tsx` | `<About />` replaces the last `Placeholder`; its import and the now-unused `VIEW_LABELS` import removed; docstring updated |
| `frontend/src/shell/Placeholder.tsx` | **deleted** |
| `frontend/src/shell/shell.css` | the three `.placeholder` rules removed |

**No change to `about.md`'s text** — see §5 for the one thing in it that is now false.

### 3.1 `splitSections` against `split_sections` — 91/91

The reference side calls `app.split_sections` and `app.strip_comments` themselves; the port side runs
`stripComments` → `splitSections` from Node over `frontend/public/about.md`. Compared: the raw and
stripped lengths, the emptiness verdict, the section count, and **every heading and every body string
character for character** — plus 16 constructed edge cases run through both implementations.

```
91/91 split/prominence checks pass (7 real sections, 16 edge cases)
```

The edge cases are where the contract actually lives: empty input, whitespace-only input, no headings,
a leading intro, a heading with no body, `###`, `##NoSpace`, a padded heading, a mixed-case heading,
consecutive headings, a trailing newline, CRLF, CR-only, and a CRLF file with multi-line bodies.

**Sensitivity, by mutation:**

| mutation | failures | what fired |
|---|---:|---|
| marker `"##"` instead of `"## "` | **4** | `##NoSpace` becomes a heading, and its body vanishes |
| `text.split("\n")` instead of the terminator set | **3** | the CR-only case, **and the CRLF-multi-line-body case** — `"line one\r\nline two"` against `"line one\nline two"`, which is §2.2's claim demonstrated rather than asserted |
| emit every section unconditionally | **54** | the guard at app.py:733/739, across the real file and most cases |
| prominence compared case-sensitively | **3** | the `## DISCLAIMER` case |

### 3.2 The rendered page — 38/38

A headless browser reads the live page and is compared against `split_sections`' output:

```
38/38 About DOM checks pass over 7 sections
```

- **Every heading exact**, in file order, all 7.
- **Every body**, normalised against an *enumerated* markdown model — the file contains exactly 1
  link, 16 `**` pairs, 10 backticks and 3 `- ` bullets, and no `###`, bare URLs, HTML or single-`*`
  emphasis. Anything it gains later that is outside that list surfaces as a mismatch instead of
  passing quietly.
- **The disclaimer is the only special case, in the browser:** exactly **1** `.about__disclaimer` and
  **6** `.about__body`, and per section the two containers are mutually exclusive — never both, never
  neither. That is Step 1.3's code reading, confirmed by rendering.
- **The markup survived the render:** 16 `<strong>` matching the 16 `**` pairs, 3 `<li>` matching the
  3 bullets, and one `<a>` with `href="https://github.com/lorisjk/stock_valuator.git"`.
- **Content fidelity:** `cmp content/about.md frontend/public/about.md` — byte-identical, and the
  hand-off's named claim renders verbatim inside the disclaimer callout: *"Coverage gaps, derivation
  provenance, and data-quality flags are shown in the Data view rather than smoothed over."*

### 3.3 The missing-file case — and it exercised the guard I expected least

`public/about.md` was moved aside, the page re-read, and the file restored.

```
status=200 type=text/html      ← what the dev server answered for /about.md
sections: 0 | callouts: 0
warning: "No About content found. Expected about.md next to the app's other public files.
          The page is text held in a file so it can be edited without changing code;
          create that file to fill this page in."
```

The server did **not** 404. It served `index.html` at 200 — the SPA fallback `fetchNotice`'s docstring
warns about — so the branch that saved the page was the **content-type guard**, not the status guard.
Without it, About would have rendered the app's own HTML as markdown. Copied-in defensiveness that
turns out to be the load-bearing line is worth recording as such.

Restored and verified by hash: `98dfef50…` before and after, and the page re-renders 38/38.

**One deliberate deviation in that message.** The reference names `CONTENT_DIR` — an absolute path on
the machine running Streamlit — which is meaningless in a browser and points at the wrong file: what
failed to load is the copy served next to the bundle, not the one in the repo. The served path is
named instead; the rest of the sentence is the reference's, word for word.

### 3.4 `Placeholder`'s removal, verified

Zero references in `src/` and `scripts/` (the only match is the sentence in `App.tsx`'s docstring
explaining the deletion), and **zero occurrences of `placeholder__badge` or `Not built yet` in the
built JS and CSS**. The remaining lowercase `placeholder` strings in the bundle are plotly's and
react-markdown's. `tsc`, `eslint` and `vite build` are clean, and every other view still renders —
§4 is that check.

---

## 4. The closing run — the whole suite, together

The rebuild list is complete. Every check from every cycle, run against one tree in one sitting:

| check | scope | result |
|---|---|---|
| `check-chart-width.mjs` | 36 renders across 4 entry tabs × 3 charts, both sidebar states, plus the raw-facts and comparison reveal cases | **36/36** |
| `check-tab-state.mjs` | routing, default tab, state persistence | **13/13** |
| `check-table-format.mjs` | 7 tickers' four numeric data-tab sections | **6,107/6,107** |
| chart-builder A/B (items 4–17) | 23 scenarios: valuation ×3 modes, fundamentals, growth, raw facts ×2, comparison ×2, over AAPL/ERIE/CRM | **23/23 digests**, identical to items 17–21 |
| item 18 — quality-flag summary | every flag row of every ticker | **12,466/12,466** over 609 tickers |
| item 19 — cadence markers | markers, legend, and the loaded column | **3,654/3,654**, 1,152,894 `ttm_source` cells |
| item 20 — encyclopedia | 9 filter queries × 3 tabs | **1,173/1,173** |
| item 21 — profile coverage | 24 profiles, 1,248 matrix marks | **1,876/1,876** |
| item 22 — About | split contract + rendered page | **91/91** and **38/38** |
| `npx tsc -b` · `npx eslint .` · `npx vite build` | — | clean · clean · `✓ built in 12.65s` |

`git status`: everything changed is under `frontend/`, plus `task_new.md` (operator-owned) and this
cycle's report files. `content/about.md` is untouched.

**The rebuild is complete and self-consistent end to end.** All 24 items are built; the 23 chart
digests have not moved since item 17; and no page recomputes anything another page already computes.

---

## 5. Two things left open, both for the operator

### `about.md`'s Cookies paragraph is now factually wrong

The Privacy section says:

> **Cookies.** One technically necessary cookie (`_streamlit_xsrf`) is set by the application
> framework to maintain the connection between your browser and the server.

That was true of the Streamlit app. **This build sets no cookie at all.** The only client-side storage
it uses is `sessionStorage`, for one key — `update_notice_dismissed` (`shell/notice.ts`) — and
`document.cookie` appears nowhere in `src/`. The rest of the section is unaffected: "no tracking, no
advertising", "no access logs", and the Session-state paragraph are all still accurate, and the last
is arguably *more* accurate now.

This is a legally-flavoured statement on a public page, so it is worth correcting rather than leaving.
**Not edited here** — the brief reserves `about.md`'s text to the operator, and the replacement wording
depends on facts only the operator has (whether the reverse proxy sets anything of its own). The
mechanical part, if it helps: the sentence can simply say no cookies are set, and the "no consent
banner" clause then follows more strongly than before.

### `public/about.md` is a hand-made copy with nothing keeping it in sync

`frontend/public/about.md` and `content/about.md` are byte-identical today because this cycle copied
one to the other. **Nothing enforces that** — no build step, no export script, no check — and the same
is already true of `update_notice.md`, which has quietly stayed in sync since the shell cycle by luck
and low edit rate.

Three ways out, cheapest first:

1. a line in the export/refresh script that copies `content/*.md` into `frontend/public/` — the
   pipeline already writes into that directory, so this is where it belongs;
2. a `check-content-sync.mjs` beside the other three checks, `cmp`-ing the pairs and exiting non-zero;
3. pointing Vite's `publicDir` at `content/` — rejected, because `public/` also holds the data export
   and the two directories have different owners.

Recommended: **(1)**, with **(2)** as the guard, because a copy step that silently stops running is
the failure this is meant to prevent. Either way it is a change to the pipeline side, which is outside
this task's scope.
