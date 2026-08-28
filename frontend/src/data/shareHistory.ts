/**
 * `share_history_absent` (app.py:526), as a pure function over `facts_full`.
 *
 * Its own module rather than a helper beside the notice that uses it, for the
 * reason every rule module in this port is its own module: it is a claim about
 * the data that can be checked from Node, and the notice is the only thing that
 * would otherwise be able to check it.
 */
import type { Frame } from "../contracts.ts";

/**
 * `share_history_absent` (app.py:526): no `SharesOutstanding` value at all.
 *
 * Reads `facts_full`, the same frame the reference reads. A cheaper proxy was
 * measured and rejected: `facts_growth` carries `SharesOutstanding` too, and its
 * emptiness agrees with this on all 609 bundled tickers — but only because no
 * ticker in the export has *exactly one* filed value, where a YoY series would
 * be empty and the raw history would not. That is precisely the thin-versus-
 * absent distinction the docstring exists to protect, so agreeing today is not
 * the same as being the same rule.
 *
 * `null` while the frame is in flight, so the caller can render the sentence
 * that always holds and append this one when it is known.
 */
export function shareHistoryAbsent(facts: Frame | null): boolean | null {
  if (facts === null) return null;
  for (let i = 0; i < facts.rowCount; i += 1) {
    if (facts.concept[i] === "SharesOutstanding" && facts.value[i] !== null) return false;
  }
  return true;
}
