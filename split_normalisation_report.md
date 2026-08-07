# Split Normalisation Corroboration + `share_count_jump_flag` Price Basis

Input: sections 6 and 8 of `tag_investigation_stock_sbc_report.md`, which found two defects
and deferred both. They are one failure seen from two sides — **the pipeline inferred
share-count events from the share-count series itself, with nothing independent to check
against** — and they are fixed together, because the source that tells a split apart from an
acquisition is the same source that gives the jump flag a real price.

Everything below is measured over all 501 active tickers from the local EDGAR cache, plus one
yfinance pass whose results were cached to disk so every later step is reproducible offline.

---

## 1. Step 1 inventory — what the normaliser was doing

`SharesOutstanding` holds **32,061 rows across 498 tickers**. `normalize_split_adjusted`
rescaled **8,893 of them (27.7%) across 335 tickers**, in **929 events** (maximal runs of
consecutive periods sharing one factor), a median of 26 rows per affected ticker.

> The earlier report said 8,908 rows. 15 of those have a raw value of 0 or NaN, so their
> before/after ratio is undefined rather than a rescaling; the normaliser left them alone.
> 8,893 is the corrected count.

### The mechanism was not split detection

`_normalize_series` never looked for a step. For **each value independently** it chose whichever
of `v`, `v x f`, `v / f` over `COMMON_SPLIT_FACTORS = [1,2,3,4,5,6,7,8,10,15,20,25,30,40,50]`
landed closest in log space to `values.iloc[-1]` — the newest value. It is share-count history
pulled toward today's anchor, with no notion of when a split happened or whether one had.

### Factor distribution

| factor | events | | factor | events |
|---|---:|---|---|---:|
| 0.02 | 5 | | 3 | 101 |
| 0.0667 | 5 | | 4 | 74 |
| 0.10 | 4 | | 5 | 49 |
| 0.125 | 6 | | 6 | 27 |
| 0.1429 | 1 | | 7 | 27 |
| 0.1667 | 2 | | 8 | 25 |
| 0.20 | 3 | | 10 | 38 |
| 0.25 | 13 | | 15 | 14 |
| 0.3333 | 38 | | 20 | 13 |
| 0.50 | 182 | | 25 | 6 |
| 2 | 270 | | 30 | 7 |
| | | | 40 | 11 |
| | | | 50 | 8 |

**The brief hoped the factor distribution might already separate plausible from implausible. It
cannot, and the reason matters:** every factor is `n` or `1/n` drawn from that fixed list,
because the algorithm can produce nothing else. A conventional-looking ratio is evidence of the
algorithm's vocabulary, not of a split. Every one of the 929 events looks like a textbook split
ratio and 7,357 of the underlying rows are wrong.

### Two internal falsifiers, before any external source

1. **The raw series shows no step where the factor is applied.** Comparing each event's trailing
   boundary against the raw share counts on either side: only **178 of 929 events (19%)** have a
   raw step matching the applied factor. For the other 751 the median boundary step is **1.04** —
   the series is flat and the normaliser rescales across it anyway.
2. **The factor sequence goes the wrong way in time.** A real split adjustment can only shrink as
   you move toward the present. Sorted by filing date, the old factors' magnitude **increases at
   730 steps across 307 tickers**. Sorted by period end, **260 of 335 rescaled tickers (77.6%)**
   violate it, covering 83.6% of all rescaled rows.

Neither test needs a price feed. Both were available all along.

---

## 2. Step 2 — the corroboration source

### Candidate 1: a step in `price_history` — **unusable, and worth knowing why**

The brief's instruction to establish what kind of price data is on hand before building on it was
the right call. yfinance **back-adjusts prices for splits regardless of `auto_adjust`**:

```
AAPL around its 4:1 split on 2020-08-31
  auto_adjust=True    2020-08-28  121.06     2020-08-31  125.17
  auto_adjust=False   2020-08-28  124.81     2020-08-31  129.04
  the actual unadjusted close on 2020-08-28 was 499.23  =  124.81 x 4
```

`auto_adjust` controls the *dividend* adjustment only. There is no unadjusted series to find a
step in, and the absence of a step is not a signal either, since adjusted prices are continuous
through every split by construction. This route is closed.

### Candidate 2: XBRL split elements — **insufficient coverage**

Scanning every cached CompanyFacts file for split-shaped elements:

| element | tickers (of 501) |
|---|---:|
| `StockholdersEquityNoteStockSplitConversionRatio1` | 99 |
| `StockholdersEquityNoteStockSplitConversionRatio` | 28 |
| `StockIssuedDuringPeriodSharesStockSplits` | 12 |
| `StockIssuedDuringPeriodSharesReverseStockSplits` | 3 |

At most ~120 of 501 tickers, with units ranging over `Rate`, `pure`, `Ratio`, `shares` and
`commonshares`, and the name-adjacent `DebtInstrumentConvertibleConversionRatio` families mixed
in. Too thin to corroborate 8,893 rows across 335 tickers.

### Candidate 3: the corporate-action feed — **chosen, at zero extra cost**

`yf.Ticker(t).history()` already returns a `Stock Splits` column in the same response the
pipeline fetches for prices. `get_price_history` now passes it through, so the corroboration
source costs **no additional request**. Across the universe: **372 events, 231 tickers, 0 fetch
failures.**

### But the feed alone is not enough

The `Stock Splits` column also carries **spin-off and stock-dividend price adjustments**, and
those change the price without touching the share count:

```
A     2014-11-03  1.398    Agilent spinning off Keysight
RTX   2020-04-03  1.589    Raytheon/UTC spinning off Carrier and Otis
FTV   2020-10-09  1.195    Fortive spinning off Vontier
HON   2018-10-29  1.032    a stock dividend
```

**The ratio's shape cannot separate them.** Agilent's spin-off ratio is 1.398; a 7:5 split would
be 1.400. A first attempt at a "simple fraction, far enough from 1" rule accepted FTV's 1.195 and
TT's 1.252 while rejecting Chipotle's genuine 50:1 and Google's 1.998 Class-C distribution.

### The second source: the filers corroborate themselves

A share count is stated on the share basis in force **when it was filed**. A filer that splits
restates the same period at the new basis in its next filing — so the same `end`, reported at two
filing dates straddling a real split, differs by exactly the ratio. The underlying count is
identical, so the tolerance can be tight (2% in log space).

```
CMG  2023-12-31  filed 2024-02-08 =    27,710,000  |  filed 2026-02-04 = 1,385,500,000  -> 50.0000
NFLX 2025-03-31  filed 2025-04-18 =   436,962,000  |  filed 2026-04-17 = 4,369,623,000  -> 10.0000
GOOGL 2021-12-31 filed 2022-02-02 =   662,121,000  |  filed 2023-02-03 =    13,242,000k -> 19.9994
A     -- the only >1.2x restatements Agilent ever made are 1,000,000x unit fixes.
        The Keysight spin-off left the share count untouched, exactly as it should.
```

A magnitude floor completes the rule: a split moves the count by at least a quarter, so ratios
within 20% of 1 are skipped. Below that the 2% match window is wider than the effect itself and
any small restatement would "confirm" a 1.7% stock dividend. Ignoring those leaves the count off
by that percent — an order of magnitude under the 15% the jump flag looks for.

**Result: 145 of the 372 feed events corroborated, across 104 tickers**, with ratios 1.25, 1.5,
2, 3, 4, 5, 6, 7, 10, 15, 20, 25, 50 and the reverse ratios 1/2, 1/3, 1/5, 1/8, 1/10, 0.3775.

### Validation against the required cases

| ticker | verdict | |
|---|---|---|
| **INCY** | no split corroborated | its only splits are 1997 and 2000, long before the fact window |
| **URI** | no split corroborated | United Rentals has never split; the 2012 step is the RSC Holdings issuance |
| AAPL | 2014-06-09 7:1, 2020-08-31 4:1 | |
| NVDA | 2021-07-20 4:1, 2024-06-10 10:1 | |
| TSLA | 2020-08-31 5:1, 2022-08-25 3:1 | |
| AMZN | 2022-06-06 20:1 | |
| GOOGL | 2022-07-18 20:1 | 2014 Class-C 1.998 correctly rejected |
| CMG | 2024-06-26 50:1 | |
| NFLX | 2015-07-15 7:1, 2025-11-17 10:1 | |
| BF-B | 3:2, 2:1 **and 5:4** | the 5:4 is below any shape-based rule and still corroborates |
| A, RTX, FTV, TT | rejected | spin-offs, correctly excluded |

---

## 3. Step 3 — reclassification, and the no-evidence default

Classified at row level, because the old mechanism worked per row and its "events" were an
artefact of adjacent rows landing on the same factor:

| class | rows | tickers | meaning |
|---|---:|---:|---|
| **contradicted** | **7,357** | 305 | the corroborated factor differs from the one applied |
| **corroborated** | 1,406 | 74 | the old rescaling happened to be right |
| **no evidence** | **130** | 5 | the fact was filed before the ticker's price history begins |

**82.7% of the rescalings were wrong.** The 7,357 contradicted rows form **624 events across 305
tickers** — the full list is in section 4.

### The no-evidence default, argued on the numbers

The brief was right to insist this be measured first. The class is **130 rows — 1.5% of the
rescalings and 0.41% of all 32,061 `SharesOutstanding` rows — across 5 tickers**:

| ticker | rows | why |
|---|---:|---|
| SATS | 54 | EchoStar; price history begins 2026-07-17 |
| EXE | 47 | Expand Energy, ex-Chesapeake; relisted 2021-02-10 after a 1:50 reverse split in bankruptcy |
| HWM | 25 | Howmet, ex-Arconic/Alcoa; listed 2016-11-01, after Alcoa's 1:3 reverse split |
| DELL | 2 | re-listed 2016-08-17 |
| VICI | 2 | |

**Decision: do not normalise without corroboration.** At 0.41% of rows the honest-gap default is
cheap, and the alternative is not symmetric. "Normalise anyway" would have to guess, and the
guessing is what produced 7,357 wrong values in the first place. EXE and HWM are the real cost —
genuine reverse splits whose feed coverage starts after the event — and they now leave a visible
discontinuity instead of a smoothed-over wrong number.

**The third option the brief raised — normalise but flag it — was considered and rejected as
redundant, then verified rather than assumed.** An un-normalised genuine split leaves a large
share-count step, and `share_count_jump_flag` exists to catch exactly that. Measured after the
change: **19 of the 20 pre-listing tickers now carry a `share_count_jump_flag`** (ANET, APP,
APTV, COIN, CRWD, DASH, DDOG, DELL, EXE, HOOD, HWM, IQV, IR, KHC, META, NCLH, NOW, PLTR, SATS).
The exception is **VLTO**, and for a good reason: its 18 pre-listing rows are all 246,300,000, so
there is no jump to surface. A new flag would have restated what an existing one already says.

### Where the fix lives, and why the order matters

Split normalisation moved out of `metrics.normalize_split_adjusted` (deleted, along with
`_normalize_series` and `COMMON_SPLIT_FACTORS`) into `parse_edgar._apply_split_basis`, which runs
**before** `_normalize_scale_outliers`:

> Which basis a number is on is a property of the filing; a unit-scale error is a property of how
> it was typed. In the other order the scale sweep absorbs the split with the wrong factor —
> Chipotle's pre-split count is 50x low, and the sweep, which only knows powers of ten, "fixed"
> it by 100x. That miscorrection then fed everything downstream.

That placement needs the split feed at parse time, so **the yfinance phase now runs before the
EDGAR phase** in both entry points (the report's timing sections were relabelled to match). The
extra restatement scan costs about **27s over 501 tickers** on cached facts.

The invariant the new code must satisfy — *the magnitude of the adjustment can only shrink as you
move forward in filing order* — was tested directly on the function across all 231 tickers with
feed events: **0 violations**, against 730 for the old normaliser.

---

## 4. Contradicted events

624 events, 305 tickers, 7,357 rows. All of them are now left as filed. A representative slice
(full list at `contradicted_events.csv` in the working set; the pattern is uniform):

| ticker | factor applied | first | last | rows |
|---|---:|---|---|---:|
| AAPL | 15.0 | 2007-09-29 | 2012-06-30 | 18 |
| AAPL | 3.0 | 2014-12-27 | 2019-06-29 | 18 |
| ADI | 2.0 | 2007-11-03 | 2017-04-29 | 38 |
| AFL | 0.5 | 2016-12-31 | 2019-12-31 | 13 |
| AIG | 4.0 | 2008-09-30 | 2010-12-31 | 10 |
| AIG | 0.3333 | 2012-03-31 | 2015-06-30 | 14 |
| AIG | 0.5 | 2015-09-30 | 2022-12-31 | 30 |
| AIZ | 0.5 | 2007-12-31 | 2015-03-31 | 29 |
| AJG | 2.0 | 2010-09-30 | 2018-03-31 | 31 |
| ALB | 2.0 | 2008-12-31 | 2014-12-31 | 24 |
| ALL | 0.5 | 2007-12-31 | 2017-12-31 | 40 |
| AMAT | 0.5 | 2007-10-28 | 2016-01-31 | 32 |
| **INCY** | 2.0 | 2009-12-31 | 2010-09-30 | 4 |
| **INCY** | 2.0 | 2011-03-31 | 2013-06-30 | 10 |
| **URI** | 0.5 | 2012-09-30 | 2016-03-31 | 15 |

AAPL is the instructive one: it has two *genuine* splits (7:1 and 4:1, cumulative 28x), and the
old normaliser applied 15 and then 3 — plausible numbers from its factor list, both wrong. This
is why "the fix and the non-fix look the same from a distance": the old output was neither
obviously broken nor right.

---

## 5. Step 4 — the jump flag's price basis

`implied_price = |equity / shares|` is replaced by the market close on the last trading day at or
before the quarter end, taken from the `price_history` the run already loads, matched with
`merge_asof(direction="backward", tolerance=10 days)`.

### Fallback when no price exists: none — the quarter stays flagged

Measured: **330 of 30,938 applicable quarters (1.07%) have no market price**. Restricted to what
matters, the quarters with a >15% share move: **33 of 455 (7.3%)**, on APTV, COIN, EXE, HWM, KHC,
NOW, SATS, TRGP, TTD, VICI — every one a pre-listing period.

Falling back to book value would reintroduce the defect precisely where it bites hardest: those
are the periods with the least reliable share counts and often the least meaningful equity. Not
flagging at all would hide them. **No price means no corroboration attempt, and an uncorroborated
jump is what the flag is for** — which is also what the code does naturally, since a NaN price
gives a NaN implied share count and `corroborated` stays False.

### The 0.5 threshold: kept, having checked what it does with a correct denominator

| `MIN_CORROBORATING_EQUITY_FLOW_RATIO` | flagged quarters |
|---|---:|
| 0.25 | 416 |
| **0.50** | **427** |
| 0.75 | 432 |
| 1.00 | 436 |
| 1.50 | 444 |

A 6x range of thresholds moves **28 quarters out of 30,938**. With a real price the decision is
dominated by whether an equity flow exists at all, not by where the bar sits: across quarters
with a >15% share move, the flow explains a median **0.5%** of the move and only the top decile
reaches 25%. The threshold was calibrated against a broken denominator, but it turns out not to
have been load-bearing either way, so changing it would be churn without evidence.

### Group B measured on its own

Sequenced so each change is attributable — raw jump detections, before the flag's
both-bracketing-quarters expansion:

| state | shares | price basis | flagged |
|---|---|---|---:|
| 0 — before | anchor-pull | book value | **749** |
| A | corroborated | book value | **419** |
| B — after | corroborated | market price | **427** |

Group A removes 330 spurious jumps: they were fabricated split steps, not share-count events.
Group B then moves **22 quarters**: **15 become flagged** (book value per share had spuriously
corroborated them — the original defect) and **7 become unflagged** (companies trading below book,
where book value overstated the transaction price).

---

## 6. Step 5 — non-regression

### Group A: the facts frame, all 501 tickers, all concepts

```
rows 511,464 -> 511,464   appeared=0   disappeared=0   changed=7,765
changed by concept: {'SharesOutstanding': 7,765}   across 312 tickers
```

| check | result |
|---|---|
| no fact row appeared or disappeared | ok |
| only `SharesOutstanding` changed | ok — 312 tickers, 7,765 rows |
| **anchor invariant**: newest `SharesOutstanding` unchanged for every ticker | **ok — 498 of 498** |
| newest period per ticker unchanged in both date and value | ok |
| every changed value traces to a corroborated split ratio (times a unit-scale factor) | **ok — 0 unexplained of 7,765** |
| INCY passes through unrescaled | ok — was rescaled on 14 rows |
| URI passes through unrescaled | ok — was rescaled on 15 rows |

Rows rescaled: **8,893 across 335 tickers → 3,436 across 104 tickers.** The current snapshot is
untouched, as the anchor invariant requires — verified, not assumed.

### Is the new history actually right? An independent check

The invariants above prove internal consistency; they do not prove the numbers are correct. Market
capitalisation at a checkable historical date, against the company's known value:

| ticker | date | before | **after** | actual |
|---|---|---:|---:|---|
| URI | 2013-12-31 | $4.0bn | **$8.0bn** | ~$7.5bn |
| AAPL | 2013-12-31 | $219bn | **$438bn** | ~$500bn |
| INCY | 2013-12-31 | $7.5bn | $7.5bn | ~$9bn (unchanged, already right) |
| CMG | 2013-12-31 | $16.7bn | $16.7bn | ~$16bn (unchanged, already right) |

URI was out by exactly 2x and is now right. AAPL was out by 2x and is now within the gap you
expect between a weighted-average diluted count and a period-end market cap.

### Downstream: `valuation_history` and the mean lines

```
rows 475,692 -> 475,692   comparable=273,755   changed=46,146 (16.9%)   tickers=296
```

| concept | rows changed | median \|rel\| | p90 |
|---|---:|---:|---:|
| `pfcf_ratio` | 4,569 | 0.867 | 1.000 |
| `pfcf_ex_sbc` | 3,971 | 0.857 | 1.000 |
| `p_ffo` | 5,589 | 0.667 | 1.000 |
| `pe_ratio` | 5,774 | 0.667 | 1.000 |
| `pb_ratio` | 6,057 | 0.667 | 1.000 |
| `p_tbv` | 4,476 | 0.667 | 1.000 |
| `pe_to_revenue_growth` | 3,216 | 0.667 | 1.000 |
| `ev_fcf` | 3,604 | 0.511 | 1.016 |
| `ev_ebitda` | 3,512 | 0.497 | 1.003 |
| `ev_sales` | 4,802 | 0.480 | 0.980 |
| `p_core_earnings` / `p_ppnr` | 211 / 365 | 1.000 | 1.000 |

**The mean lines the charts draw as the benchmark move materially**, which is the user-visible
consequence and the reason this was worth doing:

| rolling mean | points | changed | median \|rel\| | p90 |
|---|---:|---:|---:|---:|
| `avg_pe_5y` | 28,248 | 10,172 | 0.500 | 1.000 |
| `avg_p_ffo_5y` | 27,504 | 9,775 | 0.500 | 1.000 |
| `avg_pfcf_5y` | 25,098 | 8,727 | 0.500 | 1.000 |
| `avg_p_tbv_5y` | 23,575 | 8,957 | 0.500 | 1.000 |
| `avg_ev_ebitda_5y` | 20,588 | 6,851 | 0.387 | 0.896 |
| `avg_p_ppnr_5y` | 1,290 | 597 | 0.546 | 1.016 |
| `avg_p_core_earnings_5y` | 816 | 395 | 0.677 | 1.000 |

A third to a half of every 5-year average moved, by a median of about 50%. Anyone who read
"today's P/E vs its 5-year average" off these charts was comparing against a benchmark built on
fabricated share counts.

### End-to-end

The reordered `main()` was run for real against the network, with `DATA_DIR`/`FIGURE_DIR`
redirected to a scratch directory so the project's own 501-ticker outputs were not touched
(verified: 0 files changed under `data/` or `figures/`). It completed and wrote all four CSVs.
AAPL's oldest `SharesOutstanding` comes out at 24,900,180,000 — 889m as filed in 2007, times the
corroborated 7x and 4x — and its newest at 14,714,680,000, the untouched anchor.

---

## 7. Re-measured flags

| flag | before | after | delta |
|---|---:|---:|---:|
| `share_count_jump_flag` | 1,441 | **744** | **−697** |
| `buyback_distortion_flag` | 644 | 644 | 0 |
| `inorganic_contaminated` | 1,016 | 1,016 | 0 |
| `low_tax_rate_flag` | 4,196 | 4,196 | 0 |
| coverage flags (all concepts) | 743 | 743 | 0 |

`share_count_jump_flag` roughly halves: **697 of the 1,441 flagged quarters were the normaliser's
own fabrications being reported as data problems.**

`buyback_distortion_flag` did not move, and **cannot** — it reads `StockholdersEquity` and
`NetIncomeLoss_TTM` only, never `SharesOutstanding`. The brief asked for it specifically; the
honest answer is that it is not downstream of this change. Coverage flags are unchanged because
normalisation rescales values without adding or removing rows.

---

## 8. Deliberately not fixed

**`_normalize_scale_outliers` still guesses.** It rescales 350 `SharesOutstanding` rows across 79
tickers by powers of ten, using the same anchor-proximity idea that was just removed from split
normalisation, with no corroborating source. Running the split basis first stops it *absorbing*
splits (the CMG 100x-instead-of-50x case), but the sweep itself is unaudited. Genuine unit errors
do exist in the filings — AIG reports 130,248,736,000,000 shares for one period, Agilent reports
406 for another — so it is doing real work; how much of it is right is unmeasured.

**The 130 no-evidence rows on SATS, EXE, HWM, DELL and VICI.** EXE and HWM had genuine reverse
splits their feed coverage predates. Both now carry a `share_count_jump_flag`, so the gap is
visible rather than silent, but the underlying values remain on their pre-split basis. Closing
this needs a split feed that reaches back past a relisting.

**Merger exchange ratios accepted as splits.** WTW's 0.3775 (the 2016 Willis Towers Watson
combination) and DD's 0.3333 corroborate under the rule, because the filer really did restate the
same period by that factor. Restating history onto the current basis is arguably right for those,
but the concept being adjusted is a share *exchange*, not a split, and nothing in the code marks
the difference.

**Pre-2009 splits are unverifiable and irrelevant.** AAPL 2005, NVDA 2006/2007, RTX 2005, EMR
2006 and CMI 2008 are in the feed but corroborate against no restatement, because the fact window
starts later. They also cannot matter: every fact is filed after them, so their factor would be 1.

**`calculate_ttm` still rolls over four available rows rather than four calendar quarters** —
carried forward from the tag investigation, explicitly out of scope here, and untouched.

**`normalize_split_adjusted`'s deletion is not backward compatible.** Any caller outside this
repository that imported it will break. Inside the repository the only two call sites were
removed.

---

## Files changed

| file | change |
|---|---|
| `parsers/parse_edgar.py` | new `_restatements`, `corroborated_split_events`, `_apply_split_basis`; `build_dataframe` takes `splits=` and applies the split basis before `_normalize_scale_outliers` |
| `metrics.py` | `_normalize_series`, `normalize_split_adjusted` and `COMMON_SPLIT_FACTORS` deleted, replaced by a comment recording what they did and why |
| `fetchers/yfinance_fetcher.py` | `get_price_history` passes the `Stock Splits` column through as `stock_split`; new `split_events` helper |
| `main.py` | yfinance phase moved ahead of EDGAR in both entry points; `splits_by_ticker`; `_market_price_at`; `calculate_share_count_jump_flag(facts, price_history)` uses the market close; `calculate_all_metrics` forwards it; report timing labels reordered |
| `config.py` | the `SharesOutstanding` growth metric's formula no longer names the deleted function |
