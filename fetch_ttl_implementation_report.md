# Staleness-Aware Refetch for `fetch_or_cache` — the 152-Ticker Problem

## Step 1 — Design

### The constraint that rules out the obvious approach

`fetch_or_cache()` returned any existing `{ticker}_company_info.json` forever. The naive fix — expire the file after N days — was ruled out before design started, on evidence from the prior task: **311 of 498 tickers sit at exactly the same data age (123 days), split roughly evenly between genuinely stale (133) and legitimately mid-cycle (178)**. Age does not separate them at any threshold. The decision has to come from what the company has actually *published*.

### The cost asymmetry that shapes the design

Measured directly across the existing cache before choosing anything:

| artifact | median size | total across 498 tickers |
|---|---|---|
| `{ticker}_company_info.json` (companyfacts) | **4.18 MB** | 2.12 GB |
| `{ticker}_submissions.json` (submissions index) | **0.18 MB** | 101 MB |

The submissions index is **4.2%** of the payload — ~24× cheaper — and it already contains the authoritative answer (`get_latest_filed_period()`, built in the prior task). That makes it the natural probe, exactly as the task prescribes.

Local parse costs, measured on META: `companyfacts` `json.load` **95 ms**, the newest-period scan over its facts **15 ms**, `submissions` `json.load` **38 ms**.

### The mechanism: three artifacts, three different expiry policies

| artifact | expiry | role |
|---|---|---|
| `{ticker}_submissions.json` | **1 day** (`SUBMISSIONS_MAX_AGE_DAYS`) | the cheap staleness probe |
| `{ticker}_company_info.json` | **never on age** | refetched only when the probe says the cache is behind |
| `{ticker}_cache_meta.json` | never | tiny sidecar: `newest_period` + `last_refetch_attempt` |

Reasoning for each:

- **The 1-day expiry is on the probe, not on the decision.** This is deliberately not the forbidden date-based TTL: no file is refetched because it is old. The submissions index is refreshed daily so that our knowledge of *what has been published* stays current, and the actual refetch decision is then a content comparison. Applying an age rule to a 0.18 MB index is cheap; applying one to a 4.18 MB payload is what the evidence rules out.

- **The sidecar exists to keep the probe off the expensive path.** Without it, answering "what period does my cache hold?" means loading and scanning 4.18 MB every run. With it, the check reads a few hundred bytes, and the big file is loaded only to be returned — which the caller needed anyway. This is why the added latency comes out at noise level (Step 3).

- **The daily retry cap is a separate concern from the probe.** When SEC has ingested a filing into the submissions index but not yet into `companyfacts` — the META case, a genuine aggregation lag of up to 8 days — the probe correctly and *persistently* reports "behind", while a refetch keeps pulling the same stale multi-MB payload. Capping refetch **attempts** at one per ticker per calendar day bounds that to one wasted request per day instead of one per run, while leaving the cheap probe free to run as often as it likes. The attempt date is recorded *before* the request, so a failed fetch (rate limit, 403, timeout) also counts against the cap rather than retrying in a loop.

### Flow

```
get_company_info(ticker, cik, user_agent):
  no cached companyfacts        -> fetch, write sidecar, return
  cached, check_staleness=False -> return cache unchanged (used only for benchmarking)
  cached:
     cached_period  <- sidecar, or derived once from the payload and stored
     published      <- get_latest_filed_period(get_submissions(...))   # 1-day cache
     if published > cached_period and last_refetch_attempt != today:
         record attempt; refetch companyfacts; update sidecar; return fresh
     return cache
```

If the probe raises for any reason it is swallowed and the cache is served: the probe is an optimisation, never a hard dependency.

## Step 2 — Implementation

All changes are in `fetchers/edgar.py`, except one line in `main.py`:

- `fetch_or_cache()` gained an **opt-in** `max_age_days: int | None = None`. Defaulting to `None` preserves the original cache-forever behaviour for every existing caller (the ticker mapping, and companyfacts itself), so nothing else in the project changes behaviour.
- `newest_reported_period(company_info)` — newest period end in a payload, counted over **10-Q/10-K facts only**. Restricting by form makes it directly comparable to `get_latest_filed_period()`, which reads the same two form types out of the submissions index, and it ignores 8-K/S-1 and forward-dated disclosure ends that would otherwise make a stale cache look current.
- `_read_cache_meta` / `_write_cache_meta` / `_cache_meta_path` — the sidecar.
- `_fetch_company_info` — the unconditional fetch-and-write, split out so the caching policy lives in one place.
- `get_company_info()` — rewritten with the flow above.
- `main.py`'s `delete_cached_facts()` now also removes `{ticker}_cache_meta.json`, so a full refresh cannot leave a sidecar describing a payload that no longer exists.

**One implementation, both call paths.** Verified by grep rather than assumed — every caller goes through `get_company_info`: `main.py:80` (ad-hoc `load_facts`), `main.py:1025` (`run_full_refresh`), and `explore_tags.py:24`. The only place a `companyfacts` URL is constructed anywhere in the project is inside `_fetch_company_info`, so nothing can bypass the policy.

A useful side-effect: the staleness *guard* from the prior task (`load_latest_filed_periods`) and the refetch *decision* now read the same 1-day-cached submissions files, so what gets flagged and what gets refetched can never disagree.

**Explicitly unchanged**, per the task's closing constraint: the staleness guard's own logic (`add_staleness_fields`, `STALENESS_DAYS_FALLBACK`) and the share-count fix (`resolve_snapshot_share_count`) were not touched. This task changes only *when a refetch happens*, not how staleness is measured or reported.

## Step 3 — Ad-hoc performance impact (measured, not assumed)

Benchmarked `get_company_info` with the check on versus off (`check_staleness=False` reproduces the old behaviour exactly), 5 repetitions each, on tickers whose cache is **current** — the common ad-hoc case:

| ticker | old (no check) | new (with check) | added | network calls |
|---|---|---|---|---|
| MSFT | 183.2 ms | 177.8 ms | −5.5 ms | 0 |
| GOOGL | 94.2 ms | 93.0 ms | −1.2 ms | 0 |
| AMZN | 133.5 ms | 135.1 ms | +1.6 ms | 0 |
| AON | 144.3 ms | 144.1 ms | −0.2 ms | 0 |
| APH | 101.7 ms | 106.3 ms | +4.7 ms | 0 |
| MA | 125.2 ms | 125.2 ms | −0.0 ms | 0 |

**Median added latency: −0.1 ms; worst case +4.7 ms — below measurement noise against a 95–183 ms baseline, with zero network calls.** The sidecar keeps the probe off the expensive path, and the submissions index is served from its local cache inside the 1-day window.

The one case that does cost something: when the submissions cache has expired, the probe makes a single small round-trip. Measured by forcing expiry on MSFT: **941 ms total, 1 network call, 0.20 MB** — against 5.41 MB for the companyfacts payload it avoids fetching. That is the once-per-ticker-per-day cost, and it is roughly a third of what a single companyfacts refetch costs (~2.5 s, measured in Step 6).

*(Honest note: ~0.9 s is not invisible if it lands on an interactive single-ticker test. It happens at most once per day per ticker, and it replaces a decision that was previously simply wrong, so the trade is worth it — but it is a real cost, not zero.)*

## Step 6 — Subset validation (run **before** the full-universe run)

Following the same discipline as the original full-refresh build, the complete mechanism was tested on a 9-ticker mix first: 3 confirmed SEC-lagging, 4 straightforwardly stale, 2 already current.

**Before:** all 7 stale tickers cached `2026-03-31` against a published `2026-06-30`; MSFT and GOOGL already at `2026-06-30`.

**Run 1** — 7 companyfacts refetches (31.2 MB), 0 submissions network calls (served from the 1-day cache), 17.4 s wall:

| ticker | before | after | published | outcome |
|---|---|---|---|---|
| META | 2026-03-31 | 2026-03-31 | 2026-06-30 | still behind → **confirmed SEC-lagging** |
| NEE | 2026-03-31 | 2026-03-31 | 2026-06-30 | still behind → **confirmed SEC-lagging** |
| WFC | 2026-03-31 | 2026-03-31 | 2026-06-30 | still behind → **confirmed SEC-lagging** |
| AMZN | 2026-03-31 | **2026-06-30** | 2026-06-30 | **fixed by refetch** |
| AON | 2026-03-31 | **2026-06-30** | 2026-06-30 | **fixed by refetch** |
| APH | 2026-03-31 | **2026-06-30** | 2026-06-30 | **fixed by refetch** |
| MA | 2026-03-31 | **2026-06-30** | 2026-06-30 | **fixed by refetch** |
| MSFT | 2026-06-30 | 2026-06-30 | 2026-06-30 | already current — **no refetch** |
| GOOGL | 2026-06-30 | 2026-06-30 | 2026-06-30 | already current — **no refetch** |

Both required distinctions hold: the straightforwardly-stale ones came back current, and the SEC-lagging ones were **not** falsely reported as fixed — their cached period is unchanged because the fresh payload genuinely still lacks the quarter.

**Run 2, immediately after** — the retry cap under test:

```
[run 2] companyfacts calls=0   submissions calls=0   wall: 1.4s
>>> companyfacts refetches on run 2: 0   (daily cap holds)
```

Zero repeat requests for the three still-lagging tickers, confirming the cap prevents re-pulling the same stale multi-MB payload. The sidecars also show the intended asymmetry: the 7 attempted tickers carry `last_refetch_attempt: 2026-08-01`, while MSFT and GOOGL carry `None` — no attempt was made, so none was recorded.
