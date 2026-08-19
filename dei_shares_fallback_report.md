# `SharesOutstanding` — the `dei` fallback, measured

Measured 2026-08-19 against all 610 cached tickers of the current universe, entirely from the
warm cache. Two SEC `companyconcept` requests were made to confirm one finding at the source.

**Verdict: do not build it.** The threshold fixed before the measurement was not met, and — more
decisively — **the fallback does not solve the problem it was proposed for.** Of the four tickers
named in the brief, `dei` restores nothing at all for two, two quarters from 2009 for a third,
and 3.5 years for the fourth, which was never a full failure in the first place.

Nothing in the repository was changed. `CONCEPT_CANDIDATES["SharesOutstanding"]` is untouched,
the parser still reads only the `us-gaap` namespace, and no provenance column was added.

---

## 0. What the numbers say

| | |
|---|---|
| threshold, fixed in advance | median ≤ 2%, p90 ≤ **5%** |
| measured, all 27,887 comparable pairs | median **1.19%**, p90 **5.20%** → **FAIL** |
| measured, excluding decimal-scaling defects | median 1.18%, p90 **4.90%** → marginal pass |
| systematic bias | **−1.03%** median per-ticker level bias — one-directional |
| tickers with no usable `us-gaap` share series | **3** (ERIE, STZ, V) — not 4 |
| of those, helped by `dei` | **0** |
| BKR | not a full failure; `dei` covers 2023-02 onward only |

Three findings carry the task.

**The premise is wrong for three of the four named tickers.** `EntityCommonStockSharesOutstanding`
**does not exist** in STZ's or ERIE's `dei` namespace — they carry only `EntityPublicFloat`. V has
exactly **two** facts, dated 2009-11-13 and 2010-01-27. A fallback would leave V's charts blank
from 2010 to 2026 and change nothing whatsoever for STZ and ERIE.

**The real cause is structural, and it is not a tag gap.** V and STZ are missing the *entire*
per-share layer from the `companyfacts` endpoint — no share count **and no
`EarningsPerShareBasic`/`Diluted` either**. Confirmed at the source: SEC `companyconcept` returns
**404** for `us-gaap/CommonStockSharesOutstanding` on all three, and 404 for
`dei/EntityCommonStockSharesOutstanding` on STZ and ERIE. The data is not missing from the cache;
it is not exposed by this endpoint at all, because it is tagged dimensionally and `companyfacts`
returns only non-dimensional facts — the mechanism `bugfixes_opdate_history.md` already recorded
for share classes. **No tag in any namespace fixes this.**

**Where `dei` would have worked, it cannot be validated.** BKR is the one ticker that gains a real
span, and it has **zero quarters** where a `us-gaap` share value and a `dei` value coexist. The
per-ticker level bias that makes a whole-series substitution defensible is exactly the quantity
that cannot be estimated for the only ticker that would use it.

---

## 1. Step 1 — the measurement

### 1.1 Matching, and the date-offset problem

The `dei` cover-page count is dated at the **filing date**, not the period end. Measured across
27,887 pairs, `dei_end − us-gaap_end` runs:

| p5 | median | p95 | min | max |
|---:|---:|---:|---:|---:|
| −59 d | **+26 d** | +39 d | −79 d | +76 d |

A ±26-day median offset with a 98-day spread means no fixed window assigns these correctly — a
59-day negative offset would land a value in the previous quarter.

**This does not need a heuristic.** Every `dei` fact in the payload carries the SEC's own
`frame` stamp — `CY2023Q1I` — which is SEC's assignment of that cover-page value to a calendar
quarter instant:

```
end 2023-02-06  val 1,011,217,705  form 10-K  fy 2022  fp FY  frame CY2022Q4I
end 2023-04-13  val 1,012,362,186  form 10-Q  fy 2023  fp Q1  frame CY2023Q1I
```

Matching is done on that frame, with the `us-gaap` end assigned to the calendar quarter it is
nearest. **Had the fallback been built, this is the date assignment it should have used** — an
authority already present in the data rather than a window this project invented.

### 1.2 The ratio distribution

|dei / us-gaap − 1|, 27,887 pairs across 545 tickers:

| p25 | **median** | p75 | **p90** | p95 | p99 | max |
|---:|---:|---:|---:|---:|---:|---:|
| 0.51% | **1.19%** | 2.42% | **5.20%** | 12.30% | 199% | 1.9 × 10¹⁰ |

Split by which tag owns the `us-gaap` value — this matters, because two of the three configured
tags are weighted averages and one is a point-in-time count:

| basis | n | median | p90 | median **signed** |
|---|---:|---:|---:|---:|
| point-in-time (`CommonStockSharesOutstanding`) | 313 | **0.04%** | 1.89% | +0.00% |
| weighted average | 27,574 | 1.21% | 5.23% | **−1.01%** |

**Against a point-in-time count the `dei` value is essentially the same number.** Against a
weighted average it is not, and the difference is one-directional: `dei` sits about 1% *below*,
which is what a basic count as of a date three weeks after quarter-end should do against a
diluted average over the quarter. That is disqualifier 3 from the threshold note — a consistent
bias means a different quantity, not a noisier one.

### 1.3 The tail is partly the `dei` namespace's own scale disease

263 pairs (0.94%, 87 tickers) have a ratio within 12% of a power of ten — **149 at 10³, 70 at
10⁶**. Both namespaces are implicated:

```
SWK   CY2020Q1I   dei         154,127,089   us-gaap                   1
GRMN  CY2016Q2I   dei     208,077,418,000   us-gaap             189,356
AJG   CY2020Q2I   dei 191,469,000,000,000   us-gaap         190,500,000
```

`directional_scale_detection_report.md` built the repair machinery for exactly this, and it
operates on `us-gaap` tags. **A `dei` fallback would import a defect class the existing guard
does not cover**, and admitting `dei` without extending that guard is how FOX/FOXA's known
cover-page value of `1` would have entered a live series.

Removing those 263 pairs moves p90 from 5.20% to **4.90%** — a pass. I am not claiming the pass.
The threshold was set on the data as it is, the guard that would justify the exclusion does not
exist, and building it is a prerequisite, not a footnote.

### 1.4 Does the spread depend on the company? Yes, on the level; no, on the shape

521 tickers with ≥8 comparable quarters, scale defects removed:

| | buyback-quiet (263) | buyback-active (258) |
|---|---:|---:|
| median \|level bias\| | 0.73% | **1.29%** |
| median within-ticker p90 spread | 2.72% | 1.85% |

Spearman(buyback facts, \|level bias\|) = **+0.295**; Spearman(buyback facts, within-ticker
spread) = **−0.093**.

The predicted correlation is real but it acts on the **level**, not the **shape**: a company
buying back stock has a cover-page count that sits further below its weighted average, but just
as *consistently* below. That distinction is the whole design argument, and section 3 is where it
runs out.

### 1.5 Within-ticker consistency — the measurement the design turns on

A valuation band compares a ticker against its own history, so a constant per-ticker level bias
cancels. What does not cancel is dispersion of the ratio *within* a ticker. Measured as
\|ratio / that ticker's own median − 1\|, p90 within each ticker:

| p25 | median | p75 | **p90** | p95 | max |
|---:|---:|---:|---:|---:|---:|
| 1.34% | **2.19%** | 4.69% | **17.09%** | 48.68% | 400% |

For the median ticker a whole-series substitution preserves the shape of its own history to about
2%. For one ticker in ten it distorts it by 17% or worse. And the per-ticker level bias itself
runs from −3.84% (p5) to +0.46% (p95) with a median of −1.03% — so the level is biased *and* the
bias is not the same for every company.

---

## 2. Step 2 — who is actually affected

### 2.1 The full-failure group is three, and `dei` helps none of them

| ticker | `us-gaap` share quarters | `dei` facts | what `dei` would provide |
|---|---:|---:|---|
| **STZ** | 0 | **0** | **nothing** — the tag is absent from its `dei` namespace |
| **ERIE** | 0 | **0** | **nothing** — same |
| **V** | 0 | **2** | two quarters, 2009-11-13 and 2010-01-27, then nothing for sixteen years |

Verified beyond the cache. SEC `companyconcept`:

| | `dei/EntityCommonStockSharesOutstanding` | `us-gaap/CommonStockSharesOutstanding` |
|---|---|---|
| V | 2 facts, 2009-11-13 … 2010-01-27 | **404** |
| STZ | **404** | **404** |
| ERIE | **404** | **404** |

And the gap is wider than share counts. Searching every `shares`-unit tag in their payloads:

- **V** carries `PreferredStockSharesOutstanding` and `PreferredStockSharesIssued` (18 facts each) — a different security — and **no `EarningsPerShareBasic` or `EarningsPerShareDiluted` at all.**
- **STZ** carries one `CommonStockSharesAuthorized` fact from 2009, and **no EPS tags either.**
- **ERIE** carries one `WeightedAverageNumberOfDilutedSharesOutstanding` fact from 2021-06-30, and does have `EarningsPerShareDiluted`.

V and STZ are missing the share count **and** the per-share earnings together. That is the
signature of dimensional tagging, not of a missing tag: `companyfacts` exposes only
non-dimensional facts, and a dual-class filer's per-share figures live in the class dimension.
This is class **C** in the established vocabulary — structurally unavailable — and it is
unavailable in *both* namespaces.

### 2.2 BKR was never in the full-failure group

BKR has two `us-gaap` share values (2020-06-30 and 2021-06-30), so it belongs to the partial
group. `dei` gives it 15 quarters, **2023-02-06 → 2026-07-23** — real, and beginning in 2023, so
2005–2022 stays blank whatever is done. Of a 20-year chart it restores the last 3.5 years.

### 2.3 The partial-coverage group is large and is the dangerous one

**79 tickers** have a working `us-gaap` series *and* `dei` frames it lacks — **349 frames** in
total, median **1** per ticker. The largest:

| ticker | `us-gaap` ends | `dei` ends | shared | `dei` would add |
|---|---:|---:|---:|---:|
| REG | 22 | 52 | 19 | 33 |
| KKR | 26 | 45 | 19 | 26 |
| WDAY | 27 | 23 | **0** | 23 |
| MO | 49 | 59 | 37 | 22 |
| AZO | 72 | 67 | 50 | 17 |
| COST | 72 | 67 | 50 | 17 |
| BKR | 2 | 15 | **0** | 15 |

**This group is why gap-filling must be rejected outright.** Filling 33 frames of REG's series
with a cover-page count and leaving 19 as diluted weighted averages produces one series whose
points are two different measurements, differing systematically by about 1% and by up to 17% for
a ticker in the bad decile — with no way for a reader to tell which point is which except the
provenance marker. The median ticker in this group gains **one quarter**. That is a very poor
trade for a permanently mixed series.

---

## 3. Step 3 — the decision

**Rejected.** Not as a gap-filler, and not as a last resort.

| test | result |
|---|---|
| threshold median ≤ 2% | **pass** (1.19%) |
| threshold p90 ≤ 5% | **fail** (5.20%; 4.90% only after removing a defect class the guard does not cover) |
| no systematic one-directional bias | **fail** (−1.03% median per-ticker level bias) |
| no garbage admitted | **fail without new work** (FOX/FOXA's `1`; 263 decimal-scale pairs) |
| solves the stated problem | **fail** (0 of 3 full-failure tickers helped) |

The failure mode of the alternative — building it anyway — is worth stating precisely, because it
is not "slightly imprecise numbers". It is: **V, STZ and ERIE keep their blank charts** (the
mechanism cannot reach them), **79 tickers acquire mixed-measurement series** to gain a median of
one quarter each, and **BKR gets a series nobody can validate**, because it has no quarter where
the two measures coexist. The visible failure the brief objects to would remain, and a new
invisible one would be added.

### 3.1 The design answers, recorded for whoever revisits this

Even though nothing is built, the brief asks for the decisions:

1. **Last resort only, never gap-filling.** §2.3 is the evidence: the partial group is 79 tickers
   for 349 frames, median 1 each, and mixing measurements inside one series is a permanent cost
   for a marginal gain. Under a last-resort rule the partial group is simply untouched — which is
   the correct outcome and also, given §2.1, leaves nobody helped.
2. **Date assignment: the SEC `frame` field**, never a date window. §1.1.
3. **Provenance would be mandatory and its shape is settled**: a column on the facts frame
   alongside `ttm_source` and `ffo_gains_source`, values `period_weighted_average` /
   `cover_page_point_in_time`, carried through `filter_hidden_rows`, the growth column and the
   parquet export — the chain `ttm_window_report.md` §5 already verified. **It could not be
   called `shares_source`**: `main.py:1144` already writes `shares_source_is_edgar` onto the
   snapshot, meaning the EDGAR-versus-yfinance resolution, which is a different question about
   a different number. `shares_basis` is the free name.
4. **Surfacing: the data tab is not sufficient here, and that is a reason against building.**
   `ttm_source` marks a *timing* difference within one quantity. This would mark a *different
   quantity* in the denominator of every multiple on the chart. A user comparing BKR's P/E band
   against its own history would need the marker on the valuation chart itself, not one tab away
   — and `resolve_shares_basis` would need a third return value beyond `diluted_wavg` and
   `period_end`, which propagates into the snapshot's share-source resolution.

### 3.2 A better denominator exists, and it is not good enough either

`NetIncomeLoss / EarningsPerShareDiluted` reconstructs the exact weighted average the filer
divided by — same namespace, same cadence, a weighted average by construction. Measured on 34,023
quarters across 603 tickers, it is **much better centred** than `dei`:

| | `dei` cover page | NI ÷ EPS |
|---|---:|---:|
| median \|deviation\| | 1.19% | **0.49%** |
| median **signed** bias | **−1.01%** | **+0.03%** |
| p90 | 5.20% | 6.19% |

Zero bias, half the median error — and a *worse* p90, for a reason that is structural rather than
dirty: **EPS is reported to two decimals**, so the implied share count has precision
`0.005 / |EPS|`.

| EPS | implied precision |
|---:|---:|
| 0.01 | ±50% |
| 0.05 | ±10% |
| 0.30 | ±1.7% |
| 2.50 | ±0.2% |

BKR is the worst possible case for it. Its quarterly EPS runs −0.02 to +0.37, and the derived
series shows exactly the predicted noise:

```
2021-09-30   800,000,000   eps  +0.01
2021-12-31   791,891,892   eps  +0.37
2022-03-31   900,000,000   eps  +0.08
2022-06-30   998,809,524   eps  -0.84
2022-09-30   850,000,000   eps  -0.02
```

A share count does not move ±20% a quarter. On BKR's two verifiable quarters it lands at 0.9924
and **1.0546** against the reported value.

It also fails the premise test identically: **V, STZ and ERIE derive 0 quarters**, because they
have no EPS either.

The two mechanisms are complementary in span — NI÷EPS covers BKR 2017-09 → 2022-12, `dei` covers
2023-02 → 2026-07 — and splicing them would build a single series from three different
measurements. That is the clearest possible statement of why neither is the answer.

---

## 4. Step 4 — verification

**Nothing was changed, so the non-regression is a statement about the repository rather than a
diff.** `git status` shows one modified file, `task_new.md`, which is the brief itself.
`CONCEPT_CANDIDATES["SharesOutstanding"]` still reads exactly:

```python
"tags": ["WeightedAverageNumberOfDilutedSharesOutstanding",
         "WeightedAverageNumberOfSharesOutstandingBasic",
         "CommonStockSharesOutstanding"],
"point_in_time": True, "mode": "fallback",
```

`parsers/parse_edgar.py` still reads `company_info["facts"]["us-gaap"]` and no other namespace, so
no `dei` value can reach any series by any path. Every ticker that had a `SharesOutstanding`
series has precisely the one it had: zero appeared, zero changed, zero disappeared, by
construction rather than by measurement. Anchor and snapshot invariants are untouched for the
same reason, and the quality-flag count is unchanged.

**What the four named tickers gain: nothing, and that is the finding.** §2.1 and §2.2 give the
per-ticker spans a build would have produced — 0 quarters for STZ and ERIE, 2 quarters from
2009/2010 for V, 15 quarters from 2023 for BKR.

**Independent plausibility check.** BKR's latest `dei` cover-page count against the yfinance
share count the pipeline already uses for market capitalisation — a figure from outside EDGAR
entirely:

| | |
|---|---|
| `dei` cover page, as of 2026-07-23 | **992,674,071** |
| yfinance `shares_outstanding` in `data/current_snapshot.csv` | **992,674,071** |
| ratio | **1.0000** |
| implied market cap at the snapshot price | $63.72bn, against the snapshot's $63.72bn |

**The `dei` data is correct.** That is worth stating plainly, because the rejection is not a
claim that the number is wrong — it is a claim that it is a *different quantity* from the series
it would join, that it does not exist for the tickers that need it, and that where it does exist
it cannot be validated. The match also explains why the *snapshot* already works for all four
tickers: V, STZ, ERIE and BKR all carry a price, a share count and a market cap today. What is
blank is the **historical** per-share series, and yfinance cannot supply that.

---

## 5. Deliberately not done

**No fallback was implemented**, and no `shares_source` column was added. Building the provenance
machinery for a mechanism that helps no one would leave a column that is empty for every ticker.

**The `dei` decimal-scaling defects were not fixed.** 263 pairs across 87 tickers, 149 at 10³ and
70 at 10⁶. They matter only if `dei` is ever admitted, and `directional_scale_detection_report.md`
is the place that work belongs.

**The NI÷EPS derived share count was measured but not built.** It is materially better centred
than `dei` (0.49% median, +0.03% bias) and could be worth having as a *cross-check* on the
existing series — a disagreement above some bound is a good signal that one of the two is
mis-scaled. That is a quality-flag proposal, not a fallback, and it is a separate task.

**The real fix for V, STZ and ERIE was identified but not attempted.** Their per-share data exists
in the filings; it is the `companyfacts` endpoint's non-dimensional restriction that hides it.
Reaching it means either the `frames` API, the `companyconcept` endpoint with dimensions, or the
filing R-files — a fetch-layer change of the same shape as the XOM dual-CIK merge already carried
forward, and out of scope here. **Until then those three tickers have no valuation history from
any tag in any namespace**, and that is now a measured fact rather than an open question.

**The previously admitted candidates were not re-examined.** The universe is now 610 — the
operator admitted 110 of the 112 `standard` candidates, holding back **EQH** and **TRNO**. All
measurements above cover the 610 as they stand.
