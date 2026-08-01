# Task: Give `fetch_or_cache` a Staleness-Aware Refetch (the 152-Ticker Problem)

## Context

`fetch_or_cache()` currently has no TTL at all — once `{ticker}_company_info.json` exists, it
is returned forever, regardless of how out of date it is. 152 of 498 active tickers currently
hold a cache that predates an already-published quarter. Unlike the genuine SEC-side
`companyfacts` aggregation lag (also found in the prior task, not fixable on this project's
side), this is entirely within this project's control and was flagged as the higher-value fix.

**Do not implement a naive date-based TTL** (e.g. "refetch if file older than N days"). The
prior task proved date-only thresholds cannot work here: 311 tickers sit at exactly the same
age, roughly evenly split between genuinely stale and legitimately mid-cycle, indistinguishable
by age alone. Reuse the same authoritative mechanism already built for the staleness guard
(`get_submissions()`/`get_latest_filed_period()` in `fetchers/edgar.py`) instead — compare what
the company has actually published against what the cache holds, not how old the file is.

**Standing requirement as always: nothing may regress.** Non-regression after each step.

## Step 1 — Design the mechanism

The check needs two properties that pull in opposite directions, and the design has to
satisfy both:

1. **Correctness**: a ticker whose newest cached fundamental period is older than its newest
   *published* period (per the submissions index) should get refetched.
2. **Cost**: this cannot mean calling the full `companyfacts` endpoint (a multi-MB payload)
   on every single run for every ticker just to check. The submissions index itself is a
   much smaller, cheaper call — use *that* as the cheap staleness check, and only pay for a
   full `companyfacts` refetch when it indicates the cache is actually behind.
3. **Avoid hammering SEC during a genuine aggregation lag**: if `companyfacts` is confirmed
   lagging (the META case — SEC has ingested the filing into the submissions index but not
   yet into `companyfacts`), refetching `companyfacts` on every run would repeatedly pull the
   same stale multi-MB payload for no benefit. Rate-limit *retry attempts* specifically (e.g.
   don't attempt a `companyfacts` refetch for the same ticker more than once per calendar day,
   even if the submissions check keeps indicating staleness) — separate from the submissions
   check itself, which is cheap enough to run more often.

Propose the exact mechanism (what gets cached, for how long, and what triggers what) before
implementing, and state the reasoning — this is the actual design work of this task, not a
detail to skip past.

## Step 2 — Implement

Modify `fetch_or_cache()` (or wrap it, whichever is architecturally cleaner given the existing
code) so that before returning a cached `company_info.json`, it performs the cheap
submissions-index staleness check from Step 1, and refetches `companyfacts` when warranted,
respecting the retry-rate-limit from Step 1's third property.

Make sure both existing call paths (`main()`'s ad-hoc single/few-ticker usage and
`run_full_refresh()`) go through the same logic — don't build two versions.

## Step 3 — Check the performance impact on ad-hoc usage

The ad-hoc path (`main()`, used when someone is actively testing a single ticker) needs to stay
fast. Confirm the added submissions-index check doesn't introduce a noticeable delay for the
common case (cache is actually current — the check should be cheap and fast, not a second
slow network round-trip that makes every single-ticker test sluggish). Measure it directly,
don't assume.

## Step 4 — Verify against the known 152-ticker case

Run the new mechanism against a representative sample of the 152 tickers identified as stale
in the prior task (mix of genuinely-SEC-lagging ones like META/NEE/WFC and ones where a
straightforward refetch would have fixed it). Confirm:
- The straightforwardly-stale ones get refetched and come back current.
- The genuinely-SEC-lagging ones are correctly identified as still lagging (not incorrectly
  "fixed" by a refetch that just pulls the same stale `companyfacts` payload again), and are
  not retried more than the Step 1 rate limit allows.

## Step 5 — Non-regression

1. Confirm tickers whose cache is already current are **not** unnecessarily refetched — check
   this directly (e.g. via request logging/counting), not just assumed from the design.
2. Confirm no existing cached value changes for any ticker that wasn't actually stale.
3. Full-universe run: report how many of the 498 active tickers triggered a refetch, how many
   came back current afterward, and how many remain genuinely SEC-lagged (and are now correctly
   flagged by the Part 3 staleness guard from the prior task, not silently treated as fixed).

## Step 6 — End-to-end validation on a small subset before recommending a full run

Same discipline as the original full-refresh feature build: test the complete mechanism
against a small subset of tickers first (a mix of current, straightforwardly-stale, and
SEC-lagging cases) rather than trusting it from code review alone.

## Output

One file, `fetch_ttl_implementation_report.md`: the Step 1 design and reasoning, what was
implemented, the ad-hoc performance check, the verification against known-stale tickers
(distinguishing "fixed by refetch" from "confirmed still SEC-lagging"), the full-universe
non-regression results, and the subset validation.

No scratch scripts left behind. Do not change the staleness guard's own logic (`Part 3` of the
prior task) or the share-count fix (`Part 2`) — this task only changes when/whether a refetch
happens, not how staleness is measured or reported.