# META Fetch Failure + Share-Count Source Conflict + Staleness Guard + `peg_ratio` Fix

All work verified against the full active universe (498 tickers) with fresh direct SEC calls and a fresh yfinance pull. Non-regression run after each part separately.

---

# PART 1 — **RESOLVED: not a code bug. SEC-side aggregation lag.**

## Step 1.1 — Isolation

Fetched META's `companyfacts.json` directly from `https://data.sec.gov/api/xbrl/companyfacts/CIK0001326801.json` using stdlib `urllib` — deliberately *not* through this project's `requests`-based client, so no session, adapter, or cache layer of this project could influence the result.

```
HTTP status : 200
Content-Encoding: gzip      payload: 2,700,046 bytes      us-gaap tags: 456
Cache-Control / ETag / Age / X-Cache : all absent (no HTTP caching in play)

does end=2026-06-30 exist in the DIRECT response?
  RevenueFromContractWithCustomerExcludingAssessedTax : max_end=2026-03-31   present: False
  NetIncomeLoss                                       : max_end=2026-03-31   present: False
  Assets                                              : max_end=2026-03-31   present: False
  StockholdersEquity                                  : max_end=2026-03-31   present: False
```

The direct fetch **also lacks the fact**. And comparing against this project's own freshly-refetched cache:

```
cache/META_company_info.json   2,987,990 bytes   mtime 2026-08-01T07:35:42   us-gaap tags: 456
byte-identical to direct fetch: True
```

**The project's cached file is byte-for-byte identical to an independent direct fetch.** Per Step 1.1's own decision rule this is SEC-side, and Step 1.2 (code-bug hunt) does not apply. For completeness the things Step 1.2 would have looked for were checked anyway and all came back clean: the URL/CIK/endpoint are correct (`companyfacts`, CIK `0001326801`); `fetch_or_cache` does a plain `requests.get` + `raise_for_status()` with no `requests-cache`, no ETag/If-Modified-Since handling, and no exception swallowing; and the parser has no date cutoff that could drop a present fact.

## How stale the aggregation is, and confirmation the filing really exists

The submissions index confirms the user's account exactly:

```
10-Q  filed=2026-07-30  reportDate=2026-06-30  accepted=2026-07-29T22:58:51Z  acc=0001628280-26-050705
```

Against that, META's `companyfacts` payload tops out at:

```
most recent `filed` anywhere in the payload : 2026-04-30
most recent period `end`                    : 2026-03-31
today                                       : 2026-08-01
```

So the aggregation has not ingested a filing accepted **2.5 days** earlier.

## Scope — this is **not** META-specific

Checked whether other recent filers are affected, using **live** `companyfacts` calls (not the local cache) for a sample of tickers with a newer 10-Q/10-K on EDGAR:

| result | count |
|---|---|
| **SEC-SIDE LAG** — fresh fetch still missing the filed quarter | **10 / 29** |
| stale local cache only — fresh fetch has it | 19 / 29 |

Confirmed lagging: **META, V, WFC, F, D, NEE, IQV, MAS, PFG, GRMN, SWKS**.

Two things this shows that the task's framing did not anticipate:

1. **The lag is longer than "hours to about a day".** NEE filed on **2026-07-24** and its data was still absent from `companyfacts` on 2026-08-01 — **8 days**. WFC filed 07-28, F and V filed 07-29, all still missing.
2. **It is not simply time-ordered.** AMZN filed **later** than META (07-31 vs 07-30) and is already fully aggregated, as are MSFT, GOOGL and AAPL. Ingestion is evidently per-filing, not a uniform queue, so "wait N days" is not a reliable rule.

## A separate, larger finding: the local cache never expires

While scoping the above I found a second, independent cause of stale fundamentals. `fetch_or_cache()` returns the cached file whenever it exists and has **no TTL**:

```python
if os.path.exists(cache_path):
    with open(cache_path, "r") as f:
        return json.load(f)
```

Across the 498 active tickers, **152 currently hold a cached payload that predates an already-published quarter**, clustered at `cf_max_filed` of late-April/early-May 2026 — i.e. whenever those files were first fetched. The live sample above shows roughly two thirds of those (19/29) would be fixed simply by re-fetching. In day-to-day terms this is the bigger source of stale numbers than the SEC lag, and unlike the SEC lag it is entirely within this project's control.

## Step 1.3 — Recommendation (mitigation only; no large mechanism built)

1. **Ship the Part 3 staleness guard** (done in this task). It surfaces the condition regardless of which of the two causes produced it, which is the actual requirement — the danger was silence, not the lag itself.
2. **Give `fetch_or_cache` a TTL** for `*_company_info.json` (re-fetch when older than ~1 day) — or make `run_full_refresh`'s existing cache-delete the normal path. This is the single highest-value change and fixes the 152-ticker problem. *Not implemented here* — it changes fetch behaviour for every ticker and belongs to the project owner's sign-off, per Step 1.3's instruction.
3. **For the genuine SEC lag, re-check rather than wait a fixed period.** Since ingestion is not time-ordered, the reliable trigger is the comparison the guard now performs: if the submissions index reports a newer `reportDate` than the fundamentals hold, re-fetch that ticker on the next run. No retry loop or backoff machinery is warranted.

## Step 1.4 — Verify and non-regress

No fix was applied to the fetch/parse path, so there is nothing to verify or regress there: META's `2026-06-30` quarter **cannot** flow through until SEC publishes it in `companyfacts`. It is not lost — it will appear on the next refresh after ingestion. The condition is now **flagged** rather than silent (Part 3). No cached data for any ticker was modified by Part 1.

**Status: RESOLVED as diagnosed — external cause, correctly identified, mitigated by the Part 3 guard.**

---

# PART 2 — Share-count source conflict

## Step 2.1 — Full-universe scope-check

Confirmed from the code first: `build_snapshot()` derives `market_cap` from `prices["shares_outstanding"]`, which `load_current_prices()` fills from `yfinance_fetcher.get_current_price_and_shares()` → `yf.Ticker(t).info["sharesOutstanding"]`.

Compared against the EDGAR `SharesOutstanding` (most recent period) that feeds `EPS_TTM_CALC`, for all 498 tickers (495 with both sources):

```
yfinance / EDGAR ratio:   median 0.9910    5% 0.871    95% 1.005    min 0.325    max 9.915
```

**40 tickers disagree by more than ±10%.** Investigating each rather than assuming, there are **three distinct causes**, and only one is a defect:

### Cause 1 — Share-class coverage (35 tickers, EDGAR larger) — **the real inconsistency**

yfinance reports the share count of the *one class its ticker symbol refers to*; the EDGAR concept covers all classes. Proven by summing sibling tickers:

| group | yfinance sum | EDGAR total | ratio |
|---|---|---|---|
| NWSA + NWS | 360.6M + 180.6M = 541.2M | 555.7M | 0.974 |
| FOXA + FOX | 199.5M + 220.4M = 419.9M | 432.0M | 0.972 |
| GOOGL + GOOG | 5.867B + 5.527B = 11.394B | 12.309B | 0.926 |

(The GOOGL/GOOG residual is Class B, which has no ticker — so the sum *should* fall short.) The same structure explains META (Class A only: 2.205B vs 2.564B total), NKE, UPS, DELL, BF-B, HSY, EL, RL, TSN, LEN, UHS and the rest. For a whole-company market cap — and for consistency with the all-classes EPS denominator — **EDGAR is correct here**.

### Cause 2 — Weighted-average-diluted vs point-in-time-basic (systemic, ~1%) — **not a defect**

The median ratio across all 495 tickers is **0.9910**. The project's `SharesOutstanding` resolves to `WeightedAverageNumberOfDilutedSharesOutstanding` — a period average including dilution, correct for EPS — while yfinance reports actual basic shares outstanding today. These measure different things and *should* differ slightly. Deliberately left alone: "fixing" it would change nearly every ticker for no gain.

### Cause 3 — Post-filing corporate actions (5 tickers, yfinance larger) — **EDGAR is the wrong one**

| ticker | EDGAR | yfinance | ratio | verified cause |
|---|---|---|---|---|
| KLAC | 131.75M @2026-03-31 | 1,306.3M | 9.91 | **10:1 split** — DEI cover count 130.6M @2026-04-27, `yf/DEI = 0.100` exactly |
| CRWD | 257.9M @2026-04-30 | 1,018.3M | 3.95 | **4:1 split** — `yf/DEI = 0.250` exactly |
| DVN | 618.0M @2026-03-31 | 1,153.4M | 1.87 | post-filing action; DEI 621.4M @2026-04-22 |
| BKR | 806.0M **@2021-06-30** | 992.7M | 1.23 | EDGAR series ends in 2021; `yf` matches DEI to the share |
| TSLA | 3,540M @2026-06-30 | 3,949.5M | 1.12 | `yf` matches DEI (2026-07-16) **exactly**: 3,949,547,394 |

**This is precisely why "always prefer EDGAR" is not the answer** — it would have understated KLAC's market cap by 10× and CRWD's by 4×.

*(The DEI route as a "sum the class-specific tags" total was evaluated and rejected: `EntityCommonStockSharesOutstanding` returns a single collapsed value per ticker in the companyfacts API — `dei_n_classes = 1` for all 498 — and is missing for 29 tickers with cover dates as old as 2010. It is useful as a cross-check, as above, but not as a source.)*

## Step 2.2 — The fix

Deliberately **asymmetric**: prefer EDGAR only when it materially *exceeds* yfinance (the share-class direction, cause 1); keep yfinance everywhere else so causes 2 and 3 are untouched.

```python
MIN_SHARE_COUNT_DISAGREEMENT = 0.10

def resolve_snapshot_share_count(facts, prices):
    yf_shares = prices["shares_outstanding"]
    edgar_shares = prices["ticker"].map(
        get_latest_value(facts, "SharesOutstanding").set_index("ticker")["value"])
    prefer_edgar = (edgar_shares.notna() & yf_shares.notna() & (yf_shares > 0)
                    & (edgar_shares / yf_shares > 1 + MIN_SHARE_COUNT_DISAGREEMENT))
    return edgar_shares.where(prefer_edgar, yf_shares)
```

`build_snapshot()` now recomputes `market_cap = price × resolved_shares`, so every downstream snapshot multiple (`pb_ratio`, `pfcf_ttm`, `ev_ebitda`, `ev_sales`, `p_tbv`, `p_ppnr`, `p_core_earnings`) inherits the corrected count.

## Step 2.3 — Non-regression

| check | result |
|---|---|
| tickers whose share count / market_cap changes | **35 of 498** |
| changed but not in the disagreement set | **0** |
| flagged but deliberately kept on yfinance | **5** — BKR, CRWD, DVN, KLAC, TSLA (cause 3) |
| every other ticker | **unchanged** (cause-2 drift untouched) |

Internal consistency with `build_valuation_history()`'s EDGAR count (ratio → 1.0 means the snapshot and the historical series agree):

| | median ratio | tickers deviating >10% |
|---|---|---|
| before | 0.9910 | **38** |
| after | 0.9930 | **5** |

The 5 remaining are exactly the cause-3 tickers, where disagreement is *correct* — the historical series is split-adjusted internally by `normalize_split_adjusted`, while the snapshot needs today's post-split count. Every dual-class inconsistency is resolved.

---

# PART 3 — Staleness guard

## Step 3.1 — `days_since_last_filing`

Added to the snapshot as `days_since_last_filing`: days between the snapshot's as-of date and the newest fundamental period actually present for that ticker. Implemented in a new `add_staleness_fields()` applied *after* `build_snapshot()`, so no existing signature changes and `build_snapshot_as_of()` (where staleness is meaningless for a historical cutoff) is untouched.

## Step 3.2 — Threshold calibration: **~90 days is wrong, and no date-only threshold works**

Measured this project's real cadence over 31,360 period-end→first-filing pairs:

```
days from period END to the first filing reporting it
  median 36    75% 42    90% 57    95% 60
```

A quarter is ~91 days, so a perfectly healthy ticker's newest period legitimately ages to **91 + 36 = 127 days** (median) or **91 + 60 = 151 days** (95th pct) before the next one lands. A 90-day rule therefore fires during the normal upper half of every ticker's cycle:

| threshold | flags | genuinely missing a filed quarter | false positives | missed |
|---|---|---|---|---|
| >90d | 396 / 497 (79.7%) | 152 | **244** | 0 |
| >120d | 340 | 145 | 195 | 7 |
| >127d / >135d / >151d | 4 | 4 | 0 | **148 (incl. META)** |

And the decisive result: **311 tickers currently sit at exactly 123 days, of which 133 are genuinely missing an already-filed quarter and 178 are simply mid-cycle.** They are the same number. **No date threshold can separate them** — it must either flood with false positives or miss META entirely.

So the flag uses the **authoritative** comparison instead: the newest 10-Q/10-K `reportDate` from the SEC submissions index (`get_submissions` / `get_latest_filed_period`, new in `fetchers/edgar.py`) versus the newest fundamental period held. A ticker is stale iff the company has *published* something newer than we hold. The calibrated **135-day** count is retained only as an offline fallback when the index is unavailable.

`delete_cached_facts()` now also removes `{ticker}_submissions.json`, so a full refresh re-fetches the filing calendar alongside the facts and the two can never drift apart.

## Step 3.3 — Verification against META

Run against META's real cached state in the exact failure window:

```
ticker  days_since_last_filing  fundamentals_stale
META                     123.0                 1.0

  newest fundamental period held : 2026-03-31
  newest period PUBLISHED (10-Q) : 2026-06-30
  as-of date                     : 2026-08-01
  >>> FLAGGED — guard works
```

Full-universe behaviour: **154 of 498 flagged (30.9%)**. Cross-checked against the independent lag scan from Part 1 — of the 152 tickers independently confirmed to be missing a filed quarter, the number **not** flagged is **0**. (The guard finds 2 more than that scan, which only examined tickers already >100 days old.) No ticker exceeds the 135-day fallback without also being flagged, so the two paths agree.

Note this correctly flags **both** causes from Part 1 — the genuine SEC lag *and* the stale local cache — which is the desired behaviour: from the user's perspective both mean "the number on screen is older than what the company has published".

## Step 3.4 — Non-regression

| check | result |
|---|---|
| rows appended | 996 = 2 × 498 tickers |
| new concepts | `days_since_last_filing`, `fundamentals_stale` — and only these |
| pre-existing rows: keys identical | **True** |
| pre-existing rows: values identical | **True** |
| pre-existing concepts lost | **none** |
| chart generation | unaffected — neither name appears in any plot list, and both are excluded from charts by the existing concept selection |

---

# PART 4 — `peg_ratio` → `pe_to_revenue_growth`

## Step 4.1 — Decision: **rename, do not recompute** — and the evidence is decisive

The metric was named for the conventional PEG (P/E ÷ *earnings* growth) but divides by *revenue* growth. Before choosing, I measured how an earnings-based version would actually behave on this project's own data — exactly the check Step 4.1 asks for:

| candidate denominator | negative growth (PEG meaningless) | near-zero \|g\|<0.02 | **survives existing guards** | median \|growth\| |
|---|---|---|---|---|
| **revenue growth** (current) | 21.9% | 13.2% | **69.7%** | 0.078 |
| earnings growth (`NetIncomeLoss_TTM`) | **38.4%** | 5.1% | 59.0% | 0.243 |
| EPS growth (`EPS_TTM_CALC`) | 37.9% | 4.6% | 59.6% | 0.260 |

An earnings-growth PEG would be **materially worse**: nearly double the meaningless-denominator rate, ~10 percentage points fewer usable values, and 3× the volatility. It is also numerically pathological — the standard deviation of the earnings-growth series is `nan` because `NetIncomeLoss_TTM` crosses zero and produces infinities, something revenue growth never does. (The two also disagree in *sign* 34.4% of the time, so this is not a cosmetic difference.)

Recomputing to match the textbook name would therefore degrade a working metric to satisfy a label. **Renaming is the correct fix**, and it is zero-risk: values are untouched.

Chosen name: **`pe_to_revenue_growth`** — self-describing, no ambiguity with the conventional PEG.

## Step 4.2 — Implementation

- `main.py` — renamed in both `build_valuation_history()` and `build_snapshot()` (formula unchanged, guards unchanged), and in `value_cols`.
- `figures.py` — the valuation panel is now labelled `P/E ÷ Umsatzwachstum` instead of `PEG Ratio`. Rendered and visually confirmed for META and GOOGL.
- `MDs/encyclopedia.md` — the entry described it as "P/E divided by the **earnings** growth rate", i.e. it documented the metric the code never computed. Rewritten: retitled, corrected to revenue growth, with a note that the numbers did not change, the measured reason revenue growth was kept, and a new caveat that a company growing revenue while margins collapse will look cheaper here than a true PEG would suggest.
- `metrics.py` constants left as-is: `MIN_PEG_REVENUE_GROWTH` already names revenue explicitly, and `MAX_PEG_RATIO_ABS` is a generic cap.

## Step 4.3 — Non-regression (rename only ⇒ values must be *identical*)

Compared against a parameterised copy of `build_valuation_history()` running byte-identical logic under the old name:

| check | result |
|---|---|
| rows under old name vs new name | 17,276 vs 17,276 |
| rows only in old / only in new | **0 / 0** |
| **value mismatches among matched rows** | **0** |
| every *other* concept: rows | 191,136 vs 191,136 |
| every *other* concept: mismatches / unmatched | **0 / 0** |

Zero computational difference, as required for a rename.

---

## Note on a change made outside this task

While verifying Part 4 I found that `MAX_MULTIPLE` has been **removed** from `build_valuation_history()` and `MIN_VALUATION_DENOMINATOR_SCALE_RATIO` raised from `0.0005` to **`0.001`** — i.e. both halves of the previous task's Part 3 recommendation have been adopted. Nothing here reverts or re-litigates that; it is noted only because it accounts for a row-count difference (+701 rows now surviving) that an earlier draft of this report's Part 4 check initially attributed to the rename. Re-running with matched logic gave the exact 0-mismatch result above.

---

## Files changed

| File | Change |
|---|---|
| `fetchers/edgar.py` | new `get_submissions()` and `get_latest_filed_period()` (submissions index, cached) |
| `main.py` | Part 2 `MIN_SHARE_COUNT_DISAGREEMENT` + `resolve_snapshot_share_count()`, wired into `build_snapshot()`; Part 3 `STALENESS_DAYS_FALLBACK`, `add_staleness_fields()`, `load_latest_filed_periods()`, wired into both entry points, `delete_cached_facts()` extended to submissions; Part 4 rename |
| `figures.py` | valuation panel relabelled |
| `MDs/encyclopedia.md` | PEG entry corrected and retitled |

No fetch/parse logic was changed for Part 1 (none was broken). No TTL was added to `fetch_or_cache` (recommended, awaiting sign-off). No `TICKER_PROFILES` or `TICKER_CONCEPT_OVERRIDES` entry touched. No scratch scripts left behind.
