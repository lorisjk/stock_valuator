/**
 * The download button and the copy block that sit under a data-tab table.
 *
 * One component for all five sections rather than five inline pairs, which is
 * what makes the guarantee checkable in one place: **both affordances are
 * handed CSV text that was produced from the numeric pivot**, and neither this
 * file nor `csv.ts` imports `format.ts`. A section cannot accidentally hand the
 * export path a display string, because there is no display string in scope.
 *
 * The reference (`render_data_section`, app.py:426) offers a download button and
 * a `st.expander` holding an `st.code` block you select by hand. Streamlit has
 * no clipboard API, so the expander *is* its copy affordance. Here the button
 * does the copying and the disclosure is kept, for two reasons: it shows what is
 * about to be pasted, and `navigator.clipboard` does not exist outside a secure
 * context -- served over plain http from a LAN address, which is how this app is
 * developed, the disclosure is the only path that works.
 */
import { useState } from "react";
import { copyText, downloadCsv } from "./csv.ts";

export default function SectionActions({
  file,
  csv,
  copy,
}: {
  /** Download file name -- `{ticker}_{slug}.csv`, app.py:427. */
  file: string;
  /** The download's text: the periods on screen. */
  csv: string;
  /**
   * The copy block: its text and the period count for the label, or `null` for
   * a section the reference gives no copy block. Quality flags are that
   * section -- app.py:459 offers a download inside its expander and nothing
   * else -- and passing `null` states it rather than leaving it to be noticed.
   */
  copy: { text: string; periods: number | null } | null;
}) {
  const [copied, setCopied] = useState<"idle" | "ok" | "manual">("idle");

  return (
    <div className="actions">
      <button type="button" className="download" onClick={() => downloadCsv(file, csv)}>
        Download CSV
      </button>

      {copy && (
        <>
          <button
            type="button"
            className="download"
            onClick={() => {
              void copyText(copy.text).then((ok) => {
                setCopied(ok ? "ok" : "manual");
                // Long enough to read, short enough that a second copy of a
                // different section does not inherit the first one's tick.
                window.setTimeout(() => setCopied("idle"), 2500);
              });
            }}
          >
            Copy table
          </button>

          {/* app.py:432's expander label, with the same two facts in it. */}
          <details className="copy-block">
            <summary>
              {copy.periods === null
                ? `Copy table — ~${copy.text.length.toLocaleString("en-US")} characters`
                : `Copy table — ${copy.periods} periods, ~${copy.text.length.toLocaleString("en-US")} characters`}
            </summary>
            <pre>{copy.text}</pre>
          </details>

          {/* `role="status"` so the outcome is announced, not only shown. */}
          <span className="actions__status" role="status">
            {copied === "ok" && "Copied"}
            {copied === "manual" &&
              "Clipboard unavailable — open the block below and copy by hand"}
          </span>
        </>
      )}
    </div>
  );
}
