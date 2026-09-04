/**
 * The About page's rules, as pure functions — rebuild-list item 22, the last one.
 *
 * `split_sections` (app.py:722) is the whole design of the page and its docstring
 * says why it exists at all:
 *
 * > *"Splitting rather than rendering the file in one block is what lets one
 * > named section be drawn differently; every other section is passed through
 * > untouched, so the file stays ordinary markdown and the page order is the
 * > file's order."*
 *
 * So the split is not a parser — it is the minimum needed to lift **one** heading
 * out of the flow. Everything else about the file stays markdown's problem, which
 * is why `body` is handed to a markdown renderer whole rather than walked.
 *
 * Pure and React-free, like `notice.ts` next to it, so the rule can be compared
 * against Python from Node.
 */

/**
 * `PROMINENT_ABOUT_SECTIONS` (app.py:78) — *"The one heading `render_about` lifts
 * out of the flow and draws as a callout."*
 *
 * A **set with one member**, and both halves of that matter. It is one today, so
 * `disclaimer` is genuinely the only special case and the port has no second
 * branch to hide. It is a *set*, so the test is membership rather than an
 * equality against a literal, and adding a second prominent heading stays a
 * one-word change on both sides.
 *
 * Matched against `heading.strip().toLowerCase()` (app.py:763), so `## Disclaimer`
 * and `## DISCLAIMER` both hit it.
 */
export const PROMINENT_ABOUT_SECTIONS: ReadonlySet<string> = new Set(["disclaimer"]);

export interface AboutSection {
  /** `""` for the run of text before the first `## ` heading. */
  heading: string;
  /** The section's markdown, stripped. Can be `""` for a heading with no text. */
  body: string;
}

/**
 * Python's `str.splitlines()`, which is **not** `split("\n")`.
 *
 * Two differences are reproduced and one is deliberately not.
 *
 * **Reproduced:** `\r\n` counts as one break, a lone `\r` counts as a break, and
 * a single trailing empty field is dropped -- so `"a\n"` splits to `["a"]`, not
 * `["a", ""]`. The `\r` handling is the part that can actually bite. `about.md`
 * is plain LF today but is edited by hand, and under a plain `split("\n")` a CRLF
 * save would leave a `\r` on the end of every line. Headings survive that --
 * `line.slice(3).trim()` removes it -- but bodies do not: every line inside a
 * section would keep a trailing `\r`, where markdown's whitespace-sensitive
 * constructs (hard breaks, fences, list continuation) stop behaving. Splitting on
 * the terminator instead means the question never arises.
 *
 * **Not reproduced:** `splitlines()` also breaks on `\x1c`-`\x1e` and `\x85`.
 * Those four cannot occur in a markdown file someone types, and writing them into
 * a character class costs an `eslint no-control-regex` suppression to buy a case
 * that does not exist. `\v`, `\f`, `\u2028` and `\u2029` are kept because they
 * cost nothing. The divergence is named here rather than left to be discovered.
 */
const LINE_BREAK = /\r\n|[\n\r\v\f\u2028\u2029]/;

function splitLines(text: string): string[] {
  if (text === "") return [];
  const lines = text.split(LINE_BREAK);
  if (lines[lines.length - 1] === "") lines.pop();
  return lines;
}

/**
 * `split_sections(text)` (app.py:722), line for line.
 *
 * Three details are the reference's and are easy to lose:
 *
 * 1. **The marker is `"## "` with its trailing space** — a level-2 heading and
 *    nothing else. `###` and deeper stay inside the body, where markdown renders
 *    them; a bare `##` with no space is not a heading here either.
 * 2. **A section is emitted only when it has a heading or a non-blank body**
 *    (app.py:733/739). That is what drops the empty run before a file that opens
 *    on `## `, while keeping a heading whose body is empty — the heading itself
 *    makes the pair worth emitting.
 * 3. **`heading` is `line[3:].strip()` and `body` is the joined lines
 *    `.strip()`** — so the blank line conventionally left under a heading is not
 *    part of the body.
 */
export function splitSections(text: string): AboutSection[] {
  const sections: AboutSection[] = [];
  let heading = "";
  let body: string[] = [];
  const flush = () => {
    if (heading !== "" || body.some((line) => line.trim() !== "")) {
      sections.push({ heading, body: body.join("\n").trim() });
    }
  };

  for (const line of splitLines(text)) {
    if (line.startsWith("## ")) {
      flush();
      heading = line.slice(3).trim();
      body = [];
    } else {
      body.push(line);
    }
  }
  flush();
  return sections;
}

/** app.py:763 — does this heading get the callout rather than plain markdown? */
export const isProminent = (heading: string) =>
  PROMINENT_ABOUT_SECTIONS.has(heading.trim().toLowerCase());
