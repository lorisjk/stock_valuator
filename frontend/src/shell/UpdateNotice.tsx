/**
 * The dismissible update notice — item 23. All the rules are in `notice.ts`;
 * this is the box they decide whether to draw.
 *
 * Rendered via react-markdown, so bold text and links in the operator's
 * update text (update_notice.md) render as real HTML instead of literal
 * `**text**` / `[label](url)`.
 */
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { dismissNotice, noticeToShow } from "./notice.ts";


export default function UpdateNotice({ raw }: { raw: string | null }) {
  const store = typeof sessionStorage === "undefined" ? null : sessionStorage;
  const [dismissed, setDismissed] = useState(() => noticeToShow(raw, store) === null);
  if (dismissed) return null;
  const text = noticeToShow(raw, store);
  if (text === null) return null;

  return (
    <aside className="notice">
      <div className="notice__body">
        <ReactMarkdown>{text}</ReactMarkdown>
      </div>
      <button
        type="button"
        onClick={() => {
          dismissNotice(store);
          setDismissed(true);
        }}
      >
        Dismiss
      </button>
    </aside>
  );
}
