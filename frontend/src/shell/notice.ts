/**
 * The update notice's rules, as pure functions -- rebuild-list item 23.
 *
 * Three behaviours come off `app.py` and all three are easy to lose in a
 * rewrite:
 *
 *   1. **HTML comments are stripped before the emptiness test.** The content
 *      file carries its own editing instructions in `<!-- -->`, and
 *      `strip_comments` (app.py:131) exists so that a file holding *only* those
 *      instructions counts as empty. Testing emptiness first would draw a box
 *      containing nothing.
 *   2. **Empty means draw nothing, not draw an empty box.** Missing file, empty
 *      file and instructions-only file all land in the same branch
 *      (app.py:802-806).
 *   3. **Dismissal lasts a browser session.** `st.session_state` is per-session
 *      and per-tab, so `sessionStorage` is the exact equivalent --
 *      `localStorage` would outlive it and a notice dismissed in March would
 *      still be dismissed in June, including a *different* notice.
 *
 * The Dismiss button's `on_click` callback (app.py:769) is Streamlit plumbing
 * with no React analogue, as the inventory notes -- setting state in a click
 * handler re-renders before paint here.
 */

/** app.py:84 -- the same key, so the two apps agree on what "dismissed" means. */
export const NOTICE_DISMISSED_KEY = "update_notice_dismissed";

/**
 * `strip_comments` (app.py:131-152): markdown with `<!-- ... -->` removed.
 *
 * An unterminated `<!--` swallows the rest of the file, which is what the
 * Python does -- `rest.find("-->")` returning -1 ends the loop with everything
 * after the opener dropped. Reproduced rather than improved: a half-written
 * comment should hide the text it was half-wrapping, not print it.
 */
export function stripComments(text: string): string {
  const out: string[] = [];
  let rest = text;
  for (;;) {
    const start = rest.indexOf("<!--");
    if (start === -1) {
      out.push(rest);
      return out.join("");
    }
    out.push(rest.slice(0, start));
    const end = rest.indexOf("-->", start);
    if (end === -1) return out.join("");
    rest = rest.slice(end + 3);
  }
}

/** The text the notice would show, or "" when there is nothing to say. */
export const noticeText = (raw: string | null) => (raw === null ? "" : stripComments(raw).trim());

/** Minimal storage shape, so the rule is testable without a browser. */
export interface SessionStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export const isNoticeDismissed = (store: SessionStore | null): boolean =>
  store?.getItem(NOTICE_DISMISSED_KEY) === "1";

export const dismissNotice = (store: SessionStore | null): void => {
  store?.setItem(NOTICE_DISMISSED_KEY, "1");
};

/**
 * The whole decision in one place: draw the notice, or draw nothing.
 *
 * Order matches app.py exactly -- the dismissal flag is checked *before* the
 * content is read, so a dismissed notice costs no fetch and no parse.
 */
export function noticeToShow(raw: string | null, store: SessionStore | null): string | null {
  if (isNoticeDismissed(store)) return null;
  const text = noticeText(raw);
  return text === "" ? null : text;
}
