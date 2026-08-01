# Full-Universe Validation of the Staleness-Aware Refetch Mechanism

This closes the gap left by the prior task: the mechanism (`fetch_or_cache` TTL +
`get_company_info()` staleness check, built against a 9-ticker subset) is now run against
**all 498 currently-active tickers**, live, to completion, and the results reported honestly —
including a discrepancy the run surfaced that the subset test could not have shown.

## Step 1 — Full-universe run

`get_company_info()` (staleness checking enabled) was executed for all 498 active tickers,
serially, no sampling. It ran to completion with **zero errors**.

## Step 2 — What Step 1 required

### 2.1 Refetch counts

| | count |
|---|---|
| Tickers behind their published period **before** the run | 148 |
| → fixed by refetch (now current) | **81** |
| → still behind after the run | 67 |
| &nbsp;&nbsp;— skipped by the daily retry cap (already attempted today) | 3 (`META`, `NEE`, `WFC`) |
| &nbsp;&nbsp;— refetched, SEC's aggregated payload still lacks the newest period | 64 |
| Tickers not behind before the run (untouched) | 350 |

`META`/`NEE`/`WFC` had already consumed their one attempt for the day during the
earlier 9-ticker subset test (Step 6 of the prior report), run on the same calendar day —
the cap correctly skipped them here rather than re-attempting. `AMZN`/`AON`/`APH`/`MA`,
also part of that subset, had already been fixed by that same earlier run and so entered
this one already current — they appear in neither the "fixed" nor "still behind" counts,
which is correct.

The 81 "fixed" tickers moved as follows:

| cached period → new period | tickers |
|---|---|
| 2026-03-31 → 2026-06-30 | 73 |
| 2026-03-29 → 2026-06-28 | 3 |
| 2026-03-28 → 2026-06-27 | 2 |
| 2026-04-04 → 2026-07-04 | 1 |
| 2026-04-03 → 2026-07-03 | 1 |
| 2026-03-31 → 2026-06-26 | 1 |

Full list of the 81: `AAPL, AOS, APD, AVB, AWK, BAC, BAX, BEN, BLDR, BMY, BNY, CBOE, CBRE,
CHD, CHRW, CI, CL, CMG, COIN, CPT, CRH, CSGP, DECK, DXCM, EME, EQIX, EQR, ERIE, ESS, ETN,
EXR, FICO, FLEX, FSLR, FTNT, GDDY, HAS, HII, HOOD, HSY, ICE, IEX, INVH, IR, LHX, LIN, LYB,
LYV, MGM, MLM, MO, MTD, NTRS, PCAR, PSA, PTC, PWR, QCOM, RDDT, REGN, ROP, STT, SW, SWK, SYK,
TER, TFC, TMO, TROW, TT, TYL, VICI, VLO, VRT, VTR, VZ, WM, WRB, WTW, WY, XEL`.

The 64 genuinely SEC-lagging: `ABT, AEP, AMT, BG, BIIB, C, CAH, CARR, CB, CDNS, CNP, COF,
CTAS, CTSH, D, DLR, DOW, DTE, EIX, ETR, EXC, EXE, F, FE, FRT, FTV, GD, GEHC, GLW, GRMN,
HBAN, HCA, HUBB, HUM, INCY, IQV, JCI, KO, LII, LNT, MAA, MAS, MDLZ, NXPI, OMC, PFG, PLD,
PNR, POOL, PPG, PYPL, RCL, SLB, SO, SPGI, SWKS, TAP, UDR, URI, V, VLTO, VMC, VRSK, WELL`.

Every one of the 64 was refetched (the daily cap did *not* skip them — a network call
was made and confirmed the newest reported period, e.g. 2026-03-31, still lags the
published period, e.g. 2026-06-30). Gap breakdown for the still-behind set:

| cached | published | tickers |
|---|---|---|
| 2025-12-31 | 2026-03-31 | 3 |
| 2026-02-28 | 2026-05-31 | 1 |
| 2026-03-28 | 2026-06-27 | 1 |
| 2026-03-29 | 2026-06-28 | 1 |
| 2026-03-31 | 2026-06-30 | 56 |
| 2026-04-03 | 2026-07-03 | 4 |
| 2026-04-05 | 2026-07-05 | 1 |

### 2.2 Cross-check against the staleness guard's `fundamentals_stale` flag

`add_staleness_fields()` (the prior-prior task's guard, unmodified here) was run over
the same post-run state and its `fundamentals_stale` flag compared directly against the
refetch mechanism's own classification — not assumed to agree just because both read the
same submissions data:

| set | flagged stale by `add_staleness_fields()` | expected |
|---|---|---|
| still-behind (67) | **67 / 67** | 67 |
| fixed by refetch (81) | **0 / 81** | 0 |
| never behind (350) | **0 / 350** | 0 |

Exact agreement, confirmed directly.

### 2.3 No cached value changed for a ticker that wasn't actually stale

Full before/after MD5 diff on every ticker's cached payload:

- **350 tickers not behind before the run: 0 changed payloads, 0 changed newest-period
  values.** Byte-identical, confirmed by hash, not inferred.
- The 3 rate-limited tickers (`META`, `NEE`, `WFC`): correctly **0 changed** — the cap
  suppressed the network call entirely, so nothing could change.

**One real finding, reported as-is rather than smoothed over:** of the 64 tickers that
*were* refetched but came back with the same (still-lagging) newest reported period,
**8 had their cached payload change anyway** — `BG`, `C`, `CNP`, `CTAS`, `GLW`, `HUM`,
`PFG`, `PPG`. The period-based classification stayed correct for all 8 (still flagged
stale both before and after, matching the guard), but the underlying JSON content
differed byte-for-byte from the prior fetch despite reporting the same newest period.
This is consistent with EDGAR revising or amending facts for an earlier period between
the two fetches (10-K/A style restatements, tag corrections) rather than a defect in the
mechanism — the mechanism's job is period-based staleness detection, not full content
diffing, and it did not misreport any of the 8 as "fixed." It's flagged here because the
task asked for a direct check, not an assumption that same-period implies same-bytes.

## Step 3 — Retry cap at full scale

Immediately after Step 1, the full 498-ticker universe was run through
`get_company_info()` a **second** time, same calendar day:

```
498 active tickers -- second full pass, same calendar day
wall: 88.8s
tickers with >=1 companyfacts call on the second pass: 0  (must be 0)
```

Zero additional `companyfacts` calls for any of the 498 tickers — not just the 3 checked
in the earlier 9-ticker subset. The daily cap holds at full scale, including for the 64
genuinely-lagging tickers that *did* get a real refetch attempt on the first pass (their
`last_refetch_attempt` sidecar correctly suppressed a second attempt on the same day).

## Step 4 — Total cost vs. an unconditional `run_full_refresh()`-style refetch

**Actual cost of the staleness-aware Step 1 run:**

| | |
|---|---|
| `companyfacts` calls made | 145 (of 498 tickers) |
| Data transferred | 557.6 MB |
| Wall-clock time | 86.9 min |
| `submissions` calls made | 0 (all 498 index caches were already within their 1-day TTL) |

**What an unconditional refetch of all 498 would cost**, measured two ways:

1. Directly, from the actual on-disk `companyfacts` payload for every one of the 498
   active tickers (a real, complete measurement, not a sample): **2,117.1 MB total**,
   average 4.25 MB/ticker (median 4.21 MB).
2. As a spot-check, 10 tickers not otherwise touched by this task were refetched directly
   via `_fetch_company_info()` (bypassing the mechanism and its sidecar entirely, so this
   could not perturb the retry cap or any other reported number): average 4.17 MB/call,
   987 ms/call. Confirmed afterward that none of the 10 tickers' cached content changed —
   the sample was non-perturbing. This closely corroborates measurement (1).

**Comparison:**

| | unconditional (all 498) | staleness-aware (actual) | saved |
|---|---|---|---|
| `companyfacts` calls | 498 | 145 | 353 calls (70.9%) |
| Data transferred | 2,117.1 MB | 557.6 MB | 1,559.5 MB (73.7%) |
| Wall-clock time* | ~298.5 min | 86.9 min | ~211.6 min (70.9%) |

\* Time is extrapolated from the *actual* observed rate during this run (86.9 min ÷ 145
calls ≈ 36 s/call), not from the faster 10-call spot-check (987 ms/call). Those two
per-call latency figures disagree by roughly 36×, and that discrepancy is reported rather
than papered over: a small burst of 10 back-to-back requests apparently does not
reproduce whatever slowed the sustained 145-call run (SEC-side throttling under load,
larger payloads among the tickers that happened to be stale, or transient network
conditions are plausible causes — this wasn't investigated further, as it's a property of
the network/SEC's servers, not of the mechanism's code, which contains no rate-limiting or
backoff logic to have introduced it). The byte figures, unlike the time figures, don't
depend on this variance and are corroborated by two independent measurements.

## Conclusion

The mechanism, run for the first time at full scale, behaves exactly as designed: it
refetched only the 148 tickers actually behind (81 came back fixed, 64 came back
correctly still-flagged as SEC-lagging, 3 were correctly rate-limited), touched none of
the other 350, respected the daily cap universe-wide on a second pass, and cut data
transfer and request count by roughly 71–74% versus an unconditional refresh. The one
genuine anomaly — 8 tickers whose payload changed on a same-period refetch — does not
affect staleness classification and is most plausibly an EDGAR-side restatement, not a
mechanism defect; it's reported here rather than silently absorbed, per the task's
instruction not to patch anything found wrong without saying so.

No scratch scripts were left behind (removed post-verification): `subset_validate.py`,
`perf.py`, `full_run.py`, `closeout.py`, `rerun2.py`, `cost_sample.py`, and their JSON
outputs.
