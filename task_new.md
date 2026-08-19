# Task: Explain Empty Valuation Charts

**Read first:** `dei_shares_fallback_report.md` (the measurement this rests on — §2.1 and §4 in
particular), `data_tab_report.md` (the provenance and coverage-surfacing conventions),
`app_refinements_report.md` §4 (the snapshot marker, which is why the snapshot works when the
chart does not), and the current `app.py` valuation tab and data tab.

## Context

Four tickers in the universe render **no valuation metrics at all** — V, STZ, ERIE and BKR. Every
multiple is blank across their whole history, and the user is given no reason.

The cause is measured and settled: **no usable `SharesOutstanding` series exists in the
`us-gaap` namespace**, and every valuation multiple needs one in the denominator. The fallback
investigation established that nothing repairs it at the tag level — for V and STZ the entire
per-share layer is absent from the `companyfacts` endpoint, including EPS, which is the signature
of dimensional tagging that the endpoint does not expose.

**The confusing part for a user is that the snapshot still works.** All four carry a current
price, share count and market cap, because those come from market data. What is missing is the
*historical* series. A user sees a current multiple at the top and an empty chart underneath, with
nothing connecting the two.

**Explicitly NOT in this task:** no fetch-layer work to reach dimensional facts (recorded as the
real fix, out of scope), no `dei` fallback (rejected with evidence), no tag changes, no pipeline or
parse-layer changes, no new metrics, no changes to what is exported.

---

## Step 1 — Detect from the data, not from a list

**Do not hardcode the four tickers.** The universe just grew from 500 to 610, and more candidates
will follow; a maintained list would be stale within a category. The condition is derivable: a
ticker whose `SharesOutstanding` series is absent or too short to produce a valuation series.

Decide and state:

1. **What exactly is tested** — the absence of `SharesOutstanding` in the facts frame, an empty
   `valuation_history` slice, or both. They are not identical: a ticker could have shares and still
   have no multiples for a different reason, and the notice must not claim a cause it has not
   established.
2. **The threshold.** BKR has two share values and produces nothing; a ticker with a handful might
   produce a stub. Measure how many share-count points are actually needed before any multiple
   appears, and derive the threshold from that rather than picking a number.
3. **Whether a partial case exists in the current universe** — a ticker with a short but non-empty
   valuation history caused by thin share data. Report whether any exist. If none do, build for the
   empty case only and say so; do not build a second message for a case that has no instances.

Report which tickers the rule identifies. If it finds more than the four known ones, that is a
finding — say which and verify each is the same cause.

## Step 2 — The message

One variant, since Step 1's expectation is that all current cases are the same.

**Say what is observable, and be careful about the cause.** "No share-count history is available
for this ticker" is verifiable from the data. "Because of dimensional tagging" is the explanation
from the fallback investigation — demonstrated for V and STZ, but the app cannot establish it for
an arbitrary future ticker. State the symptom as fact; offer the likely cause as a likely cause, or
leave it out.

The message must cover three things:

1. **What is missing** — the share-count history, and that every multiple needs it as a
   denominator.
2. **Why the snapshot still works** — current figures come from market data, which has no
   historical equivalent for this purpose. Without this the user reasonably concludes the tool is
   broken rather than the data absent.
3. **That it is a data gap, not a filter** — nothing was hidden or discarded; the SEC's structured
   data does not expose it. This is the project's own standing distinction between an honest gap
   and a suppressed value, and it should read that way.

Keep it short. This is a notice, not an essay.

## Step 3 — Where it appears

**The valuation tab**, in place of the empty chart. That is where the user is when the question
arises.

**The data tab** as well, if it fits the existing coverage presentation — that tab already shows
quality flags and provenance markers, and "this concept has no series" belongs in the same family.
Decide whether it needs its own treatment there or is already visible through the existing
null-column display, and say which.

Also decide:

- **The comparison tab.** A ticker with no valuation history in a multi-ticker comparison is
  already handled by `build_ticker_comparison`'s `excluded` return. Check what reason it currently
  gives and whether it should say the same thing as the new notice — two different explanations of
  the same fact in two places is the failure to avoid.
- **The snapshot marker.** These tickers have a current value, so a marker could render on an
  otherwise empty chart. Confirm what actually happens today and whether it is coherent.

## Step 4 — Verify

1. **The rule identifies exactly the tickers it should**, and no others. Assert against the actual
   frames, not against a list.
2. **A ticker with a working valuation history is unaffected** — no notice, no layout change.
   Check three across different profiles.
3. **The notice renders** for the affected tickers and reads correctly.
4. **Nothing else changed**: `figures.py`, `config.py` and the pipeline are untouched (confirm by
   diff); chart output for unaffected tickers is byte-identical to before; `app.py` still imports
   no pipeline module beyond the existing `figures → metrics` path.
5. State honestly what could not be verified without a browser.

## Output

One file, `empty_valuation_notice_report.md`: the detection rule with its threshold and the
evidence for it, which tickers it identifies, the message text and the reasoning behind what it
does and does not claim, where it appears and the decisions on the comparison tab and snapshot
marker, and the Step 4 verification.

No scratch scripts left behind.