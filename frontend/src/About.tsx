/**
 * The About page — `render_about` (app.py:744), and the last item on the
 * rebuild list.
 *
 * All the rules are in `shell/about.ts` and `shell/notice.ts`; this is the page
 * they decide the shape of. Three behaviours come off the reference and each is
 * easy to lose:
 *
 * 1. **Comments are stripped before the emptiness test.** `render_about` reads
 *    `strip_comments(read_content(ABOUT_FILE))` and tests *that* (app.py:747),
 *    so a file holding nothing but its `<!-- -->` editing instructions counts as
 *    empty. `stripComments` is item 23's, reused unchanged — the two pages share
 *    one implementation because the reference shares one function.
 * 2. **Absent is an error here, unlike the notice.** Same lenient fetch, opposite
 *    reading: app.py:749 calls a missing About file *"a deployment mistake rather
 *    than a valid state, so unlike the notice it says so -- but it still must not
 *    raise."*
 * 3. **A heading with an empty body draws its heading and nothing else**
 *    (app.py:759-762): `if heading: st.subheader(heading)` comes *before*
 *    `if not body: continue`, so the heading survives an empty section.
 *
 * **Fetched when the view opens, not at startup.** `about.md` is 5.6 kB that
 * three of the four views never need, and the reference re-reads it on every
 * rerun precisely because it is *"a few kilobytes read once per rerun"*
 * (app.py:117-119). A view switch unmounts this component, so a second visit
 * re-fetches — which is the reference's behaviour too, and it means an operator
 * editing the file sees the edit on the next visit rather than on the next
 * reload.
 */
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { fetchAbout } from "./data/load.ts";
import { isProminent, splitSections } from "./shell/about.ts";
import { stripComments } from "./shell/notice.ts";
import "./about.css";

export default function About() {
  const [raw, setRaw] = useState<string | null | undefined>(undefined);

  useEffect(() => {
    let live = true;
    void fetchAbout().then((text) => {
      if (live) setRaw(text);
    });
    return () => {
      live = false;
    };
  }, []);

  // Distinct from `null`: nothing has come back yet, which is not the same as
  // "there is nothing there". Drawing the deployment warning while the fetch is
  // still in flight would accuse the operator of a mistake for one frame.
  if (raw === undefined) return <p className="caption">Loading…</p>;

  const text = raw === null ? "" : stripComments(raw);

  if (text.trim() === "") {
    return (
      <section className="about">
        <h2>About</h2>
        {/*
         * app.py:751-755, with one deliberate change. The reference names
         * `CONTENT_DIR` -- an absolute path on the machine running Streamlit --
         * which is meaningless to a browser and would be misleading here: the
         * file this page failed to load is the one served next to the bundle,
         * not the one in the repo's `content/`. The served path is named
         * instead, and the rest of the sentence is the reference's.
         */}
        <p className="notice-inline" role="status">
          No About content found. Expected <code>about.md</code> next to the app&apos;s other public
          files. The page is text held in a file so it can be edited without changing code; create
          that file to fill this page in.
        </p>
      </section>
    );
  }

  return (
    <section className="about">
      <hr />
      <h2>About</h2>
      {splitSections(text).map(({ heading, body }, index) => (
        // The heading is unique in this file and is the natural key, but nothing
        // guarantees an operator will not write two `## Contact`s -- so the index
        // rides along. Sections are never reordered, so it is a stable key.
        <section className="about__section" key={`${index}-${heading}`}>
          {heading !== "" && <h3>{heading}</h3>}
          {body !== "" &&
            (isProminent(heading) ? (
              /*
               * `st.warning(body)` (app.py:764). The callout, and the whole
               * reason `split_sections` exists: app.py:76 -- "The disclaimer has
               * to be visible without scrolling past the introduction, and that
               * is a rendering decision rather than something the text can
               * enforce about itself."
               *
               * `.notice-inline` is this build's `st.warning` since item 12, so
               * the disclaimer reads the same as the comparison tab's exclusions
               * and the encyclopedia's undocumented list. It is widened here
               * because it wraps paragraphs rather than the single sentence that
               * class was sized for.
               */
              <div className="notice-inline about__disclaimer" role="note">
                <ReactMarkdown>{body}</ReactMarkdown>
              </div>
            ) : (
              <div className="about__body">
                <ReactMarkdown>{body}</ReactMarkdown>
              </div>
            ))}
        </section>
      ))}
    </section>
  );
}
