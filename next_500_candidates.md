# Candidate list: the next 500 US companies, with proposed profiles

**Status: a proposal, not a change.** No file in the repository was modified to produce this.
`config.py` is untouched, no pipeline was run over a new ticker, no tag work was done, and
this document is the only new file. Every number below is measured, and the measurement
scripts were run outside the repository and deleted.

Measured 2026-08-18. Prices are Yahoo's last close at the time of the run
(2026-08-17 close); the existing universe's market caps are the ones already in
`data/current_snapshot.csv`, dated 2026-08-14.

---

## 0. What came out

| | |
|---|---|
| candidate pool considered | 10,383 symbols / 7,988 CIKs in `company_tickers.json` |
| survivors of every exclusion | **1,571 companies** |
| proposed list | the **top 500** by market capitalisation |
| where the list starts | SHOP, $191bn |
| where it ends | **CROX (Crocs), $6.23bn** |
| smallest company already in the universe | **CE, $4.92bn** |
| SIC-to-profile mapping agreement with the hand-assigned 500 | **443 / 500 = 88.6%** |
| candidates needing a human decision | **125 of 500** |
| new profiles invented | none |

Three things are worth reading before the tables.

**The next 500 is not below the current 500 — it sits alongside it.** Every one of the
proposed 500 is larger than the smallest company already in the universe, and 20 of them
are larger than the universe's *median* ($45.9bn). Only one existing member (CE) falls
below the proposed cutoff. Section 8 explains why, and it is not an error in the ranking.

**The mapping's 88.6% is a ceiling imposed by SIC, not a tuning target.** Of the 57
disagreements, 51 are SIC codes where the existing universe itself splits two or three ways,
and 6 are codes with a single universe member. There is **not one case** where two or more
universe members agree on a profile and the mapping says something else. That is the check
that matters, and the mapping passes it outright.

**Reading the output found defects that validating against the 500 could not.** The universe
occupies 183 SIC codes; the candidates occupy 308. Four range rules were wrong in codes the
universe simply does not use — patent licensors and mineral royalty companies were being
called REITs. Section 4.3 lists them. This is the whole argument for Step 4 existing.

---

## 1. The funnel

Each row is what survived, with the method that removed the rest.

| stage | left | removed, and how |
|---|---:|---|
| `company_tickers.json` symbols | 10,383 | fetched 2026-08-18 |
| distinct CIKs behind them | 7,988 | 1,443 CIKs carry more than one symbol |
| has any recent `us-gaap` `Assets` / `StockholdersEquity` / revenue datapoint | 6,227 | **&minus;1,761.** XBRL *frames* for four instantaneous quarters and two annual periods. A CIK with no datapoint in any of them is an IFRS-only filer, an ETF, a trust, a shell, or a registrant too new to have filed. |
| passes the size gate: assets &ge; $100M **or** revenue &ge; $50M **or** equity &ge; $50M | 4,961 | **&minus;1,266.** All 496 resolvable universe CIKs survive this gate — see 1.1. |
| has a priceable common ticker (one CIK &rarr; one ticker) | 4,674 | **&minus;287** with no traded common line. Share-class rule in 1.2. |
| not already in the universe | 4,184 | **&minus;490** of the 496 distinct companies behind the 500 universe tickers (six had no priceable line) |
| shortlisted for a `submissions.json` lookup | 2,000 | top 2,000 by the stage-1 market cap; #2,000 is $1.00bn |
| &minus; foreign private issuers | 1,652 | **&minus;348.** Files 20-F, 40-F or 6-K and has **never** filed a 10-K. |
| &minus; residual `entityType != "operating"` | 1,652 | **&minus;0.** Already fully covered by the form test — see 1.3. |
| &minus; funds, trusts, SPACs, BDCs, commodity ETPs | 1,609 | **&minus;43.** Investment-company forms or a pooled-vehicle SIC — see 1.4. |
| &minus; filers with no 10-K yet | 1,571 | **&minus;38.** IPO or spin-off inside the last year; 10-Qs only. |

### 1.1 Why a coarse gate, and what it can miss

The pool is 7,988 CIKs and the precise size measure costs a request each. So the gate is
deliberately generous: it keeps anything with $100M of assets *or* $50M of revenue *or*
$50M of equity, which is roughly two orders of magnitude below where the cutoff lands.

The check that it is not binding: **all 496 universe CIKs that resolve survive it**, at every
threshold I tried down to $50M/$25M. That is a weak test on its own — the universe is all
large — so here is the stronger one. The shortlist boundary sits at $1.00bn on the stage-1
estimate and the cutoff at $6.23bn, so a company would have to be understated by **6.2&times;**
to be wrongly excluded. Across all 1,571 survivors where both measures exist, **the largest
understatement observed is 4.25&times;** (BLLN, $1.04bn estimated against $4.43bn actual), and
only three exceed 3&times;. Nothing observed comes close to 6.2&times;.

That is an empirical bound on 1,571 companies, not a proof. A company with a $6bn market cap,
under $100M of assets, under $50M of revenue and under $50M of equity would be missed. I could
not construct one.

### 1.2 Share classes: one CIK, one ticker

**Rule: one CIK contributes exactly one ticker, and it is the class with the highest
10-day dollar trading volume.** Volume is objective, needs no name parsing, and picks the
class a price-history pipeline can actually follow. It also disposes of preferred lines,
warrants and units without a rule about them: `BAC-PK` does not out-trade `BAC`.

430 symbols were dropped up front by suffix (`-P<letter>` preferred, `-WS`/`-WT`/`-U`/`-R`)
purely to avoid spending price requests on them; the volume rule would have discarded them anyway.

**The existing universe does not follow this rule, and the inconsistency is pre-existing.**
Three CIKs appear twice in `TICKER_PROFILES`:

| CIK | tickers in the universe |
|---|---|
| 0001754301 | `FOX` and `FOXA` |
| 0001652044 | `GOOG` and `GOOGL` |
| 0001564708 | `NWS` and `NWSA` |

So the universe is 500 tickers but **496 companies** — 499 of the 500 symbols resolve to a CIK (see 9 for the one that no longer does), and three CIKs are counted twice. Elsewhere it takes one class only —
`LEN` without `LEN-B`, `TAP` without `TAP-A`, `BF-B` without `BF-A`. The three duplicates are
exactly the three dual-class pairs the S&P 500 index itself lists as separate constituents,
so the universe is consistent with the *index*, not with a rule of its own. I did not
propagate that: admitting both classes would put two near-identical entries in the app for
one set of financial statements. If the operator prefers index consistency, the change is
local — `bycik` in the candidate build picks one ticker per CIK and could pick all common classes.

### 1.3 Foreign private issuers

**Test: the company has filed a 20-F, 40-F or 6-K and has never filed a 10-K.** Taken from
the form list in `submissions.json`, which is the record of what the company actually filed —
not inferred from name or country. It removed **348** of 2,000.

`entityType == "other"` in the same file turns out to identify the same companies: of the 260
non-operating entities in the shortlist, **260 were already caught by the form test**, and the
form test caught three more that EDGAR still labels `operating`. The form test strictly
dominates, so the `entityType` step removes nothing. I left it in the funnel to show that.

**47 survivors are non-US companies that do file 10-Ks** — Shopify, Enbridge, Canadian Pacific,
Celestica, Teva, Waste Connections, Flutter, CNH and others. They are not excluded, because
the pipeline reads 10-K and 10-Q and these companies file exactly that. But "the next tier of
**US** companies" does not describe them, so they are listed for a decision in section 6.

### 1.4 Funds, trusts, SPACs and BDCs

Two signals, and deliberately **no name matching**:

1. the company files an investment-company form — `N-2`, `N-54A`, `N-CSR`, `N-PORT`, `497`,
   `24F-2NT`. This is the only thing that separates a BDC from an operating lender: Ares
   Capital, Blue Owl, Golub, FS KKR, Hercules, Sixth Street and Goldman Sachs BDC all file a
   10-K like anyone else, and all file an N-2.
2. the SIC code is `6221`, `6726` or `6770`. In this pool `6221` — nominally "commodity
   contracts brokers & dealers" — holds the physical-metal and crypto ETPs: GLD, IAU, SLV,
   IBIT, FBTC, GBTC and eighteen others. `6770` is blank checks.

**A name-based rule was tried first and was wrong.** Matching `/TRUST|FUND|ETF/` on the company
name removed 22 legitimate operating companies: 20 REITs (Vornado, Medical Properties, Empire
State Realty, Kite Realty, First Industrial and others), a bank (Community Trust Bancorp) and
a data-centre operator (Blackstone Digital Infrastructure). A REIT is legally a trust and
usually says so in its name, so the signal is inverted for the largest affected group. The rule
was replaced, not patched.

One documented exception: **UROY (Uranium Royalty Corp)** carries SIC 6221 but is an operating
royalty company, so it is exempted by name and kept.

---

## 2. The ranking measure, and what it cost

**The measure is market capitalisation, in two stages.**

Market cap, not revenue. The existing universe is the S&P 500, which is selected on market
cap; continuing the list on revenue would produce a different universe, pulling in low-margin
distributors and grocers while dropping high-multiple biotech and software. For an application
whose entire subject is valuation multiples, ranking the universe by a measure the multiples
are not taken against would be strange.

### Stage 1 — coarse, EDGAR-first, 39 requests for the whole pool

Market cap is shares &times; price. **Shares came from EDGAR**, via the XBRL frames API: one
request returns every filer reporting a concept in one period, so 39 requests covered the
entire 7,988-CIK pool. Sources were tried newest-first: `dei:EntityCommonStockSharesOutstanding`,
then `us-gaap:CommonStockSharesOutstanding`, then `WeightedAverageNumberOfDilutedSharesOutstanding`,
then `CommonStockSharesIssued`. Price came from Yahoo.

Validating the share counts alone against the project's own snapshot for the 500:

| | |
|---|---|
| median EDGAR / snapshot share ratio | **1.000** |
| within &plusmn;5% | 483 / 495 = **97.6%** |
| worst | PCG 1.217 (preferred included), ALB 0.866 |

And the resulting market caps against `data/current_snapshot.csv`:

| | |
|---|---|
| companies compared | 493 |
| median ratio | **1.0003** |
| within &plusmn;10% | **99.2%** |
| within &plusmn;25% | **100.0%** |

That is an unusually clean result, and it is also **misleading about the candidate pool**,
which is the point of stage 2.

### Stage 2 — precise, per company, on the 1,571 survivors

The stage-1 estimate breaks on companies the S&P 500 does not contain. Reading the top 50
(section 8) showed it immediately: Taboola at $1,180bn, Akari Therapeutics at $690bn,
Repay Holdings at $305bn. Three distinct defects, none of which the 500-company validation
could have exposed:

| defect | what happens | examples |
|---|---|---|
| **unit scaling** | the filer tags a share count in thousands against the `shares` unit, so the frame value is 1,000&times; too large | TBLA (&times;1,123), RPAY (&times;1,048), MODD (&times;1,051) |
| **ADR ratio** | EDGAR reports *ordinary* shares; the price is per *ADS*, and one ADS is many ordinaries | AKTX (&times;52,451 — 91.6bn ordinaries at a $7.54 ADS price), ONC (&times;12.5), ZLAB (&times;10.1) |
| **dual class understated** | only one class is reported in the frame | HEI ($20.7bn estimated, $51.9bn actual), OWL, VNOM |

So stage 2 takes an independent market cap per survivor from Yahoo — 1,574 requests, six of
which returned nothing. Agreement between the two stages across 1,565 companies:

| | |
|---|---|
| within &plusmn;10% | **95.2%** |
| within &plusmn;25% | 97.1% |
| within 2&times; | 98.1% |
| **outside 2&times;** | **29 companies** |

**The final ranking uses the stage-2 measure**, with the stage-1 estimate kept as the
cross-check that produced the table above. Six companies with no stage-2 value fall back to
the estimate and are marked in the table.

### Request count

| target | requests | against |
|---|---:|---|
| SEC — `company_tickers.json` + XBRL frames | **39** | SEC's published 10 req/s; the client paced at ~9/s |
| SEC — `submissions.json` | **2,148** | same limit; 2,000 distinct CIKs, 148 re-requests after a local file error of mine |
| **SEC total** | **2,187** | ~6 minutes of wall clock at the paced rate |
| Yahoo — stage-1 prices | ~7,600 | 6,037 tickers, plus four retry passes after rate limiting |
| Yahoo — stage-2 market caps | 1,574 | paced at 0.15s, zero failures |
| **Yahoo total** | **~9,200** | no published limit; rate limiting hit hard at 150 concurrent and stopped at 60 |

One correction to an assumption I started with: `yf.download()` with a list of tickers is
**not** a batched endpoint. `yfinance.multi` calls `Ticker(t).history()` once per ticker on a
thread pool, so a "batch" of 150 is 150 concurrent requests — which is exactly why the later
batches returned `YFRateLimitError` naming individual symbols. Reducing the batch to 60 with a
3-second pause between batches converged in four passes. Had I known, stage 1 would have been
paced from the start. This is the terms-of-use exposure the brief flags: ~9,200 Yahoo requests
against a service with no stated allowance, for a survey that is run once.

### What the ranking revealed incidentally

The brief asks for candidates with no usable facts. The gate is built on facts, so nothing
reached the shortlist empty. What did show up instead: **46 companies whose stage-1 and
stage-2 market caps disagree by more than 25%**, and the 29 that disagree by more than 2&times;
are all filers with a genuine data defect — a unit-scaled share count, an ADR ratio, or a
share class missing from the frame. Every one of those is a company whose fundamentals the
pipeline would also read wrong. They are flagged in the table and are the natural first
candidates for the per-category work.

---

## 3. The SIC-to-profile mapping

`submissions.json` carries `sic` and `sicDescription`, and the pipeline already fetches that
file, so no new source was needed. The mapping is an ordered rule list: **exact codes win,
then ranges in order, first match wins, then `standard`**.

The exact codes exist because a SIC range drawn around a real industry boundary cuts across
this project's profiles in a handful of places — pharma sits inside chemicals, medical devices
sit inside instruments, refiners sit inside petroleum, exchanges sit inside brokers.

### 3.1 Exact codes

| SIC | profile | why |
|---|---|---|
| `1040` | `materials_integrated` | universe: materials_integrated x1 |
| `1311` | `energy` | universe: energy x4, energy_integrated x2 |
| `1381` | `energy` | no universe member |
| `1389` | `energy` | universe: energy_integrated x1, energy x1 |
| `2833` | `pharma_medtech` | no universe member |
| `2834` | `pharma_medtech` | universe: pharma_medtech x11 |
| `2835` | `pharma_medtech` | universe: pharma_medtech x1 |
| `2836` | `pharma_medtech` | universe: pharma_medtech x4 |
| `2840` | `consumer_staples` | universe: consumer_staples x2, materials x1 |
| `2842` | `consumer_staples` | universe: consumer_staples x1 |
| `2844` | `consumer_staples` | universe: consumer_staples x3 |
| `2870` | `materials` | universe: materials x2 |
| `2911` | `energy_integrated` | universe: energy_integrated x4, energy x2 |
| `3021` | `retail` | universe: retail x2 |
| `3100` | `retail` | universe: retail x1 |
| `3140` | `retail` | no universe member |
| `3357` | `standard` | universe: standard x1 |
| `3533` | `energy_integrated` | universe: energy_integrated x1 |
| `3559` | `standard` | universe: standard x1 |
| `3670` | `industrials` | universe: industrials x1 |
| `3679` | `industrials` | universe: industrials x1 |
| `3690` | `industrials` | no universe member |
| `3826` | `pharma_medtech` | universe: pharma_medtech x4 |
| `3827` | `standard` | universe: standard x2 |
| `4400` | `leisure` | universe: leisure x3 |
| `4412` | `industrials` | no universe member |
| `4424` | `industrials` | no universe member |
| `4432` | `industrials` | no universe member |
| `4512` | `airline` | universe: airline x3 |
| `4513` | `industrials` | universe: industrials x1 |
| `4522` | `airline` | no universe member |
| `4700` | `marketplace` | universe: marketplace x2 |
| `4731` | `industrials` | universe: industrials x2 |
| `4812` | `telecom_cable` | universe: telecom_cable x1 |
| `4813` | `telecom_cable` | universe: telecom_cable x2 |
| `4832` | `media` | no universe member |
| `4833` | `media` | universe: media x3 |
| `4841` | `telecom_cable` | universe: telecom_cable x2, media x1 |
| `4899` | `telecom_cable` | no universe member |
| `4922` | `energy` | universe: energy x3 |
| `4923` | `energy` | universe: energy x1 |
| `4924` | `utilities` | universe: utilities x1 |
| `4953` | `industrials` | universe: industrials x2 |
| `4955` | `industrials` | no universe member |
| `4959` | `industrials` | no universe member |
| `5013` | `retail` | universe: retail x1 |
| `5047` | `retail` | universe: retail x1 |
| `5065` | `standard` | universe: standard x1 |
| `5090` | `retail` | universe: retail x1 |
| `5122` | `retail` | universe: retail x3 |
| `5411` | `consumer_staples` | universe: consumer_staples x1 |
| `5412` | `consumer_staples` | no universe member |
| `5810` | `leisure` | universe: leisure x1 |
| `5812` | `leisure` | universe: leisure x4 |
| `5813` | `leisure` | no universe member |
| `5912` | `health_services` | universe: health_services x1 |
| `5961` | `standard` | universe: standard x2 |
| `6200` | `standard` | universe: standard x4 |
| `6211` | `financial` | universe: financial x6, standard x1 |
| `6282` | `standard` | universe: standard x4, alt_asset_manager x4 |
| `6324` | `health_services` | universe: health_services x5 |
| `6411` | `standard` | universe: standard x6 |
| `6500` | `standard` | universe: standard x1 |
| `6510` | `reit` | universe: reit x1 |
| `6512` | `reit` | no universe member |
| `6519` | `reit` | no universe member |
| `6531` | `standard` | no universe member |
| `6552` | `homebuilder` | no universe member |
| `6792` | `energy` | universe: energy x1 |
| `6794` | `standard` | no universe member |
| `6795` | `materials` | no universe member |
| `6798` | `reit` | universe: reit x28 |
| `6799` | `standard` | no universe member |
| `7011` | `leisure` | universe: leisure x5 |
| `7340` | `industrials` | universe: industrials x1, marketplace x1 |
| `7350` | `industrials` | no universe member |
| `7352` | `industrials` | no universe member |
| `7353` | `industrials` | no universe member |
| `7359` | `industrials` | universe: industrials x1 |
| `7381` | `industrials` | universe: industrials x1 |
| `7841` | `media` | universe: media x1 |
| `7948` | `leisure` | no universe member |
| `7996` | `leisure` | no universe member |
| `7997` | `leisure` | no universe member |
| `8700` | `industrials` | universe: industrials x1 |
| `8711` | `industrials` | no universe member |
| `8731` | `pharma_medtech` | universe: pharma_medtech x3 |
| `8734` | `industrials` | no universe member |
| `8741` | `standard` | universe: standard x1 |
| `8742` | `standard` | no universe member |

### 3.2 Ranges, scanned in order

| SIC range | profile | universe members in range |
|---|---|---|
| `0100`-`0999` | `consumer_staples` | 1 |
| `1000`-`1099` | `materials` | 1 |
| `1200`-`1299` | `materials` | 0 |
| `1300`-`1399` | `energy` | 0 |
| `1400`-`1499` | `materials` | 2 |
| `1520`-`1599` | `homebuilder` | 2 |
| `1600`-`1799` | `industrials` | 4 |
| `2000`-`2199` | `consumer_staples` | 21 |
| `2200`-`2399` | `retail` | 3 |
| `2400`-`2499` | `materials` | 0 |
| `2500`-`2599` | `industrials` | 0 |
| `2600`-`2699` | `materials` | 5 |
| `2700`-`2799` | `media` | 2 |
| `2800`-`2899` | `materials` | 9 |
| `2900`-`2999` | `energy_integrated` | 0 |
| `3000`-`3099` | `materials` | 0 |
| `3200`-`3299` | `materials` | 1 |
| `3300`-`3399` | `materials` | 3 |
| `3400`-`3499` | `industrials` | 6 |
| `3500`-`3569` | `industrials` | 11 |
| `3570`-`3579` | `standard` | 15 |
| `3580`-`3599` | `industrials` | 4 |
| `3600`-`3629` | `industrials` | 5 |
| `3630`-`3639` | `industrials` | 1 |
| `3640`-`3659` | `industrials` | 0 |
| `3660`-`3699` | `standard` | 23 |
| `3700`-`3799` | `industrials` | 14 |
| `3800`-`3825` | `industrials` | 12 |
| `3826`-`3826` | `pharma_medtech` | 0 |
| `3827`-`3839` | `industrials` | 3 |
| `3840`-`3859` | `pharma_medtech` | 18 |
| `3860`-`3899` | `industrials` | 0 |
| `3900`-`3949` | `retail` | 1 |
| `3950`-`3999` | `materials` | 1 |
| `4000`-`4099` | `railroads` | 3 |
| `4100`-`4199` | `industrials` | 0 |
| `4200`-`4299` | `industrials` | 3 |
| `4400`-`4499` | `industrials` | 0 |
| `4500`-`4599` | `airline` | 0 |
| `4600`-`4699` | `energy` | 0 |
| `4700`-`4799` | `industrials` | 0 |
| `4800`-`4899` | `telecom_cable` | 0 |
| `4900`-`4999` | `utilities` | 30 |
| `5000`-`5099` | `industrials` | 1 |
| `5100`-`5199` | `consumer_staples` | 2 |
| `5200`-`5999` | `retail` | 20 |
| `6000`-`6199` | `financial` | 21 |
| `6200`-`6299` | `financial` | 0 |
| `6300`-`6329` | `insurance_life` | 5 |
| `6330`-`6399` | `insurance_pc` | 12 |
| `6400`-`6499` | `standard` | 0 |
| `6500`-`6599` | `reit` | 0 |
| `6700`-`6799` | `reit` | 0 |
| `7000`-`7099` | `leisure` | 0 |
| `7200`-`7299` | `standard` | 0 |
| `7300`-`7319` | `media` | 1 |
| `7320`-`7369` | `standard` | 3 |
| `7370`-`7399` | `standard` | 50 |
| `7500`-`7599` | `industrials` | 0 |
| `7600`-`7699` | `industrials` | 0 |
| `7800`-`7899` | `media` | 0 |
| `7900`-`7999` | `media` | 3 |
| `8000`-`8099` | `health_services` | 5 |
| `8100`-`8199` | `standard` | 0 |
| `8200`-`8299` | `standard` | 0 |
| `8300`-`8399` | `health_services` | 0 |
| `8400`-`8699` | `standard` | 0 |
| `8700`-`8799` | `standard` | 0 |
| `9900`-`9999` | `standard` | 0 |

### 3.3 Confidence

Confidence is derived from evidence, not asserted:

| level | condition | top 500 |
|---|---|---:|
| **high** | the exact SIC has &ge;2 members in the existing universe and *all* of them carry the proposed profile | 211 |
| **medium** | the SIC has one universe member carrying the proposed profile, or a &gt;50% plurality, or the range rule fired on a SIC no universe member uses | 253 |
| **low** | universe members with this SIC disagree with the proposal, or nothing matched and it fell back to `standard` | 36 |

A "medium" from an unoccupied SIC is a different thing from a "medium" backed by one ticker,
and both are weaker than "high". The `evidence` column in the working data records which of
the three it was for every candidate.

---

## 4. Validation against the existing 500

The mapping was run over all 500 tickers in `TICKER_PROFILES` and compared to the
hand-assigned profile. SIC codes came from the pipeline's own `cache/*_submissions.json`,
so this cost zero requests.

**443 / 500 = 88.6% agreement.**

| rule kind | n | agree |
|---|---:|---|
| exact code | 173 | 92.5% |
| range | 327 | 86.5% |

### 4.1 The check that actually matters

The headline number is easy to inflate by adding one exact code per disagreement, which would
be memorising the answer sheet. So the mapping was held to a stricter test:

> **Is there any SIC code where two or more universe members agree on a profile and the
> mapping says something else?**

**No — zero such codes.** Every one of the 57 disagreements is either a SIC code where the
universe itself splits (51 tickers, 30 distinct codes) or a code with exactly one universe
member (6 tickers). Fitting the second group would be fitting individual tickers.

Five corrections *were* made during validation, and each is justified by the business the SIC
describes rather than by the ticker that revealed it:

| SIC | was | now | reason |
|---|---|---|---|
| `6282` Investment Advice | `financial` | `standard` | `financial` is the **bank** profile and turns on interest income. The universe puts four of these on `standard` and four on `alt_asset_manager`; `financial` matches neither. Every 6282 candidate is flagged for a decision. |
| `3670`, `3679` Electronic components | `standard` | `industrials` | The 3660&ndash;3699 range exists for semiconductors and communications equipment. These two codes hold electrical gear (HUBB, VRT). |
| `7359` Equipment rental | `standard` | `industrials` | Renting industrial equipment is an industrial business (URI). |
| `7381` Guard & armored car services | `standard` | `industrials` | Facility services (ALLE). |
| `7340` Services to dwellings | `standard` | `industrials` | Building services. ABNB also sits here, which is an EDGAR classification oddity, not a signal. |

### 4.2 Every disagreement

| ticker | SIC | description | hand-assigned | mapping says | why they differ |
|---|---|---|---|---|---|
| CTVA | `0100` | Agricultural Production-Crops | `materials` | `consumer_staples` | only member of this SIC; fitting it would be memorising one ticker |
| DVN | `1311` | Crude Petroleum & Natural Gas | `energy_integrated` | `energy` | SIC is mixed in the universe: energy x4, energy_integrated x2 |
| OXY | `1311` | Crude Petroleum & Natural Gas | `energy_integrated` | `energy` | SIC is mixed in the universe: energy x4, energy_integrated x2 |
| SLB | `1389` | Oil & Gas Field Services, NEC | `energy_integrated` | `energy` | SIC is mixed in the universe: energy_integrated x1, energy x1 |
| CTAS | `2320` | Men's & Boys' Furnishgs, Work Clothg, & Allied Garments | `industrials` | `retail` | SIC is mixed in the universe: retail x1, industrials x1 |
| IP | `2621` | Paper Mills | `materials_integrated` | `materials` | only member of this SIC; fitting it would be memorising one ticker |
| AVY | `2670` | Converted Paper & Paperboard Prods (No Contaners/Boxes) | `materials_integrated` | `materials` | SIC is mixed in the universe: consumer_staples x1, materials_integrated x1 |
| KMB | `2670` | Converted Paper & Paperboard Prods (No Contaners/Boxes) | `consumer_staples` | `materials` | SIC is mixed in the universe: consumer_staples x1, materials_integrated x1 |
| DD | `2821` | Plastic Materials, Synth Resins & Nonvulcan Elastomers | `materials_integrated` | `materials` | SIC is mixed in the universe: materials_integrated x2, materials x1 |
| DOW | `2821` | Plastic Materials, Synth Resins & Nonvulcan Elastomers | `materials_integrated` | `materials` | SIC is mixed in the universe: materials_integrated x2, materials x1 |
| ECL | `2840` | Soap, Detergents, Cleang Preparations, Perfumes, Cosmetics | `materials` | `consumer_staples` | SIC is mixed in the universe: consumer_staples x2, materials x1 |
| MPC | `2911` | Petroleum Refining | `energy` | `energy_integrated` | SIC is mixed in the universe: energy_integrated x4, energy x2 |
| VLO | `2911` | Petroleum Refining | `energy` | `energy_integrated` | SIC is mixed in the universe: energy_integrated x4, energy x2 |
| NUE | `3312` | Steel Works, Blast Furnaces & Rolling Mills (Coke Ovens) | `materials_integrated` | `materials` | SIC is mixed in the universe: materials_integrated x1, materials x1 |
| HWM | `3350` | Rolling Drawing & Extruding of  Nonferrous Metals | `industrials` | `materials` | only member of this SIC; fitting it would be memorising one ticker |
| BALL | `3411` | Metal Cans | `materials_integrated` | `industrials` | only member of this SIC; fitting it would be memorising one ticker |
| CAT | `3531` | Construction Machinery & Equip | `captive_finance` | `industrials` | only member of this SIC; fitting it would be memorising one ticker |
| ZBRA | `3560` | General Industrial Machinery & Equipment | `standard` | `industrials` | SIC is mixed in the universe: industrials x2, standard x1 |
| F | `3711` | Motor Vehicles & Passenger Car Bodies | `captive_finance` | `industrials` | SIC is mixed in the universe: captive_finance x3, industrials x1 |
| GM | `3711` | Motor Vehicles & Passenger Car Bodies | `captive_finance` | `industrials` | SIC is mixed in the universe: captive_finance x3, industrials x1 |
| PCAR | `3711` | Motor Vehicles & Passenger Car Bodies | `captive_finance` | `industrials` | SIC is mixed in the universe: captive_finance x3, industrials x1 |
| TXT | `3720` | Aircraft & Parts | `captive_finance` | `industrials` | only member of this SIC; fitting it would be memorising one ticker |
| GRMN | `3812` | Search, Detection, Navigation, Guidance, Aeronautical Sys | `retail` | `industrials` | SIC is mixed in the universe: industrials x2, retail x1, standard x1 |
| TDY | `3812` | Search, Detection, Navigation, Guidance, Aeronautical Sys | `standard` | `industrials` | SIC is mixed in the universe: industrials x2, retail x1, standard x1 |
| DHR | `3823` | Industrial Instruments For Measurement, Display, and Control | `pharma_medtech` | `industrials` | SIC is mixed in the universe: industrials x2, standard x2, pharma_medtech x1 |
| KEYS | `3823` | Industrial Instruments For Measurement, Display, and Control | `standard` | `industrials` | SIC is mixed in the universe: industrials x2, standard x2, pharma_medtech x1 |
| ROP | `3823` | Industrial Instruments For Measurement, Display, and Control | `standard` | `industrials` | SIC is mixed in the universe: industrials x2, standard x2, pharma_medtech x1 |
| TER | `3825` | Instruments For Meas & Testing of  Electricity & Elec Signals | `standard` | `industrials` | SIC is mixed in the universe: industrials x1, standard x1 |
| TMO | `3829` | Measuring & Controlling Devices, NEC | `pharma_medtech` | `industrials` | SIC is mixed in the universe: pharma_medtech x1, industrials x1, standard x1 |
| TRMB | `3829` | Measuring & Controlling Devices, NEC | `standard` | `industrials` | SIC is mixed in the universe: pharma_medtech x1, industrials x1, standard x1 |
| MMM | `3841` | Surgical & Medical Instruments & Apparatus | `industrials` | `pharma_medtech` | SIC is mixed in the universe: pharma_medtech x9, industrials x1 |
| WBD | `4841` | Cable & Other Pay Television Services | `media` | `telecom_cable` | SIC is mixed in the universe: telecom_cable x2, media x1 |
| DPZ | `5140` | Wholesale-Groceries & Related Products | `leisure` | `consumer_staples` | SIC is mixed in the universe: consumer_staples x1, leisure x1 |
| FAST | `5200` | Retail-Building Materials, Hardware, Garden Supply | `industrials` | `retail` | SIC is mixed in the universe: retail x1, industrials x1, materials_integrated x1 |
| SHW | `5200` | Retail-Building Materials, Hardware, Garden Supply | `materials_integrated` | `retail` | SIC is mixed in the universe: retail x1, industrials x1, materials_integrated x1 |
| BLDR | `5211` | Retail-Lumber & Other Building Materials Dealers | `industrials` | `retail` | SIC is mixed in the universe: retail x2, industrials x1 |
| CASY | `5500` | Retail-Auto Dealers & Gasoline Stations | `consumer_staples` | `retail` | SIC is mixed in the universe: consumer_staples x1, industrials x1 |
| CPRT | `5500` | Retail-Auto Dealers & Gasoline Stations | `industrials` | `retail` | SIC is mixed in the universe: consumer_staples x1, industrials x1 |
| COIN | `6199` | Finance Services | `standard` | `financial` | SIC is mixed in the universe: financial x3, standard x1 |
| BLK | `6211` | Security Brokers, Dealers & Flotation Companies | `standard` | `financial` | SIC is mixed in the universe: financial x6, standard x1 |
| APO | `6282` | Investment Advice | `alt_asset_manager` | `standard` | SIC is mixed in the universe: standard x4, alt_asset_manager x4 |
| ARES | `6282` | Investment Advice | `alt_asset_manager` | `standard` | SIC is mixed in the universe: standard x4, alt_asset_manager x4 |
| BX | `6282` | Investment Advice | `alt_asset_manager` | `standard` | SIC is mixed in the universe: standard x4, alt_asset_manager x4 |
| KKR | `6282` | Investment Advice | `alt_asset_manager` | `standard` | SIC is mixed in the universe: standard x4, alt_asset_manager x4 |
| EFX | `7320` | Services-Consumer Credit Reporting, Collection Agencies | `industrials` | `standard` | SIC is mixed in the universe: standard x2, industrials x1 |
| ABNB | `7340` | Services-To Dwellings & Other Buildings | `marketplace` | `industrials` | SIC is mixed in the universe: industrials x1, marketplace x1 |
| TTD | `7370` | Services-Computer Programming, Data Processing, Etc. | `media` | `standard` | SIC is mixed in the universe: standard x5, media x1 |
| EA | `7372` | Services-Prepackaged Software | `media` | `standard` | SIC is mixed in the universe: standard x16, media x2, pharma_medtech x1 |
| TTWO | `7372` | Services-Prepackaged Software | `media` | `standard` | SIC is mixed in the universe: standard x16, media x2, pharma_medtech x1 |
| VEEV | `7372` | Services-Prepackaged Software | `pharma_medtech` | `standard` | SIC is mixed in the universe: standard x16, media x2, pharma_medtech x1 |
| LDOS | `7373` | Services-Computer Integrated Systems Design | `industrials` | `standard` | SIC is mixed in the universe: standard x2, industrials x1 |
| ADP | `7374` | Services-Computer Processing & Data Preparation | `industrials` | `standard` | SIC is mixed in the universe: industrials x2, standard x2 |
| VRSK | `7374` | Services-Computer Processing & Data Preparation | `industrials` | `standard` | SIC is mixed in the universe: industrials x2, standard x2 |
| BR | `7389` | Services-Business Services, NEC | `industrials` | `standard` | SIC is mixed in the universe: standard x12, marketplace x3, industrials x1 |
| DASH | `7389` | Services-Business Services, NEC | `marketplace` | `standard` | SIC is mixed in the universe: standard x12, marketplace x3, industrials x1 |
| EBAY | `7389` | Services-Business Services, NEC | `marketplace` | `standard` | SIC is mixed in the universe: standard x12, marketplace x3, industrials x1 |
| UBER | `7389` | Services-Business Services, NEC | `marketplace` | `standard` | SIC is mixed in the universe: standard x12, marketplace x3, industrials x1 |


The pattern is consistent: SIC sees *what a company makes*, and several of this project's
profiles encode *how a company is financed or how its statements are shaped*. `captive_finance`
is a judgement about whether a manufacturer runs a lending arm — CAT, F, GM, PCAR and TXT are
indistinguishable from any other machinery or vehicle maker by SIC. `alt_asset_manager` is a
judgement about fee structure inside a single code shared with traditional managers.
**The mapping cannot produce either profile, and no candidate is proposed for either one.**
That is a stated limitation, not an oversight; both sets have to be picked by hand.

### 4.3 Four defects the validation could not reach

The existing 500 occupy **183** SIC codes. The 1,571 candidates occupy **308**. Validation is
blind to the 125 codes the universe does not use, and reading the candidate output found four
range rules that were wrong there:

| SIC | description | was | now | found via |
|---|---|---|---|---|
| `6794` | Patent Owners & Lessors | `reit` | `standard` | IDCC, DLB, APPS proposed as REITs — the 6700&ndash;6799 range was drawn around 6798 |
| `6795` | Mineral Royalty Traders | `reit` | `materials` | RGLD (Royal Gold), SSRM |
| `6799` | Investors, NEC | `reit` | `standard` | HASI, an operating specialty lender |
| `4955` | Hazardous Waste Management | `utilities` | `industrials` | CLH (Clean Harbors); 4953 refuse systems is already `industrials` |

Four more were adjusted the same way, all in unoccupied codes: `3690` misc electrical machinery
(ENS, NOVT) from `standard` to `industrials`; `7350`&ndash;`7353` equipment rental to `industrials`;
`7948`/`7996`/`7997` racing, amusement parks and sports clubs (CHDN, LTH) from `media` to
`leisure`; `8711`/`8734` engineering and testing services (ACM, TTEK, ULS) from `standard` to
`industrials`.

**None of these changed the 88.6%** — by construction, since no universe member carries them.
An automated check cannot find this class of error; only reading the output can.

---

## 5. The candidate table

### 5.1 Summary by proposed profile

| proposed profile | n | high | medium | low | needs a decision | size range |
|---|---:|---:|---:|---:|---:|---|
| `standard` | 112 | 35 | 66 | 11 | 67 | $6.23&ndash;191 bn |
| `industrials` | 95 | 13 | 70 | 12 | 14 | $6.38&ndash;68.38 bn |
| `pharma_medtech` | 58 | 53 | 5 | 0 | 4 | $6.34&ndash;45.44 bn |
| `financial` | 45 | 25 | 20 | 0 | 14 | $6.32&ndash;41.06 bn |
| `materials` | 29 | 3 | 21 | 5 | 5 | $6.30&ndash;162 bn |
| `reit` | 26 | 26 | 0 | 0 | 0 | $6.44&ndash;17.61 bn |
| `energy` | 24 | 7 | 17 | 0 | 10 | $6.35&ndash;110 bn |
| `retail` | 20 | 5 | 8 | 7 | 7 | $6.23&ndash;77.07 bn |
| `utilities` | 13 | 7 | 6 | 0 | 0 | $7.01&ndash;55.13 bn |
| `leisure` | 12 | 9 | 3 | 0 | 0 | $6.25&ndash;26.91 bn |
| `insurance_pc` | 12 | 7 | 5 | 0 | 0 | $6.24&ndash;22.29 bn |
| `health_services` | 11 | 5 | 6 | 0 | 0 | $6.68&ndash;45.29 bn |
| `consumer_staples` | 10 | 2 | 7 | 1 | 1 | $6.53&ndash;23.50 bn |
| `insurance_life` | 7 | 7 | 0 | 0 | 0 | $8.55&ndash;16.13 bn |
| `telecom_cable` | 6 | 1 | 5 | 0 | 1 | $6.79&ndash;26.87 bn |
| `energy_integrated` | 5 | 0 | 5 | 0 | 2 | $6.67&ndash;67.07 bn |
| `homebuilder` | 5 | 0 | 5 | 0 | 0 | $6.47&ndash;24.48 bn |
| `media` | 5 | 2 | 3 | 0 | 0 | $9.72&ndash;12.56 bn |
| `marketplace` | 2 | 2 | 0 | 0 | 0 | $6.38&ndash;24.70 bn |
| `railroads` | 1 | 1 | 0 | 0 | 0 | $82.56&ndash;82.56 bn |
| `materials_integrated` | 1 | 0 | 1 | 0 | 0 | $19.85&ndash;19.85 bn |
| `airline` | 1 | 1 | 0 | 0 | 0 | $9.55&ndash;9.55 bn |
| **total** | **500** | **211** | **253** | **36** | **125** | |


Two existing profiles get no candidates at all: **`alt_asset_manager`** and
**`captive_finance`**, for the reason in 4.2 — SIC cannot see either distinction. There are
certainly candidates that belong on them (TPG, Blue Owl and Carlyle for the first; several
vehicle and machinery makers for the second), and they are in the list under `standard` and
`industrials` respectively, flagged.

### 5.2 The 500, grouped by proposed profile

Largest first within each group. `needs a decision` marks the candidates in section 6;
`n 10-Ks` marks companies with two or fewer annual reports, where history will be short
whatever profile is chosen.

#### `standard` &mdash; 112 candidates ($6.23 bn to $191 bn)

| # | ticker | company | CIK | market cap $bn | SIC | conf. | note |
|---:|---|---|---|---:|---|---|---|
| 1 | SHOP | SHOPIFY INC. | 0001594805 | $191 | `7372` | medium | needs a decision; 2 10-Ks |
| 3 | SNOW | Snowflake Inc. | 0001640147 | $114 | `7372` | medium | needs a decision |
| 5 | NET | Cloudflare, Inc. | 0001477333 | $109 | `7372` | medium | needs a decision |
| 6 | MELI | MERCADOLIBRE INC | 0001099590 | $90.62 | `7389` | medium | needs a decision |
| 14 | CRWV | CoreWeave, Inc. | 0001769628 | $58.46 | `7372` | medium | needs a decision; 1 10-K |
| 15 | ALAB | Astera Labs, Inc. | 0001736297 | $55.54 | `3674` | high | 2 10-Ks |
| 17 | CRDO | Credo Technology Group Holding Ltd | 0001807794 | $52.74 | `3674` | high |  |
| 23 | CLS | CELESTICA INC | 0001030894 | $42.93 | `3672` | high | 2 10-Ks |
| 28 | TEAM | Atlassian Corp | 0001650372 | $40.08 | `7372` | medium | needs a decision; 2 10-Ks |
| 29 | P | Everpure, Inc. | 0001474432 | $38.89 | `3572` | high |  |
| 31 | UI | Ubiquiti Inc. | 0001511737 | $35.32 | `3663` | high |  |
| 32 | MDB | MongoDB, Inc. | 0001441816 | $35.29 | `7372` | medium | needs a decision |
| 33 | TWLO | TWILIO INC | 0001447669 | $35.11 | `7372` | medium | needs a decision |
| 39 | ZM | Zoom Communications, Inc. | 0001585521 | $30.95 | `7370` | medium | needs a decision |
| 42 | ZS | Zscaler, Inc. | 0001713683 | $29.83 | `7371` | high |  |
| 44 | LPLA | LPL Financial Holdings Inc. | 0001397911 | $28.99 | `6200` | high |  |
| 46 | CPNG | Coupang, Inc. | 0001834584 | $28.26 | `5961` | high |  |
| 48 | RBLX | Roblox Corp | 0001315098 | $27.10 | `7372` | medium | needs a decision |
| 58 | MTSI | MACOM Technology Solutions Holdings, Inc. | 0001493594 | $25.01 | `3674` | high |  |
| 62 | OKTA | Okta, Inc. | 0001660134 | $24.90 | `7372` | medium | needs a decision |
| 69 | IOT | Samsara Inc. | 0001642896 | $22.73 | `7373` | medium | needs a decision |
| 70 | SITM | SITIME Corp | 0001451809 | $22.54 | `3674` | high |  |
| 72 | TW | Tradeweb Markets Inc. | 0001758730 | $22.19 | `6200` | high |  |
| 81 | FN | Fabrinet | 0001408710 | $21.45 | `3661` | medium |  |
| 86 | RBRK | Rubrik, Inc. | 0001943896 | $20.79 | `7372` | medium | needs a decision; 2 10-Ks |
| 90 | U | Unity Software Inc. | 0001810806 | $20.00 | `7372` | medium | needs a decision |
| 91 | TPG | TPG Inc. | 0001880661 | $19.91 | `6282` | low | needs a decision |
| 93 | TOST | Toast, Inc. | 0001650164 | $19.84 | `7374` | low | needs a decision |
| 96 | IONQ | IonQ, Inc. | 0001824920 | $18.98 | `7373` | medium | needs a decision |
| 98 | LSCC | LATTICE SEMICONDUCTOR CORP | 0000855658 | $18.84 | `3674` | high |  |
| 99 | SSNC | SS&C Technologies Holdings Inc | 0001402436 | $18.73 | `7372` | medium | needs a decision |
| 103 | OWL | BLUE OWL CAPITAL INC. | 0001823945 | $18.18 | `6282` | low | needs a decision |
| 105 | NTNX | Nutanix, Inc. | 0001618732 | $17.75 | `7372` | medium | needs a decision |
| 111 | CG | Carlyle Group Inc. | 0001527166 | $17.30 | `6282` | low | needs a decision |
| 115 | JLL | JONES LANG LASALLE INC | 0001037976 | $17.04 | `6531` | medium |  |
| 119 | FLUT | Flutter Entertainment plc | 0001635327 | $16.73 | `7370` | medium | needs a decision |
| 130 | DOCN | DigitalOcean Holdings, Inc. | 0001582961 | $15.91 | `7370` | medium | needs a decision |
| 139 | AMKR | AMKOR TECHNOLOGY, INC. | 0001047127 | $15.23 | `3674` | high |  |
| 140 | RBA | RB GLOBAL INC. | 0001046102 | $15.21 | `7389` | medium | needs a decision |
| 141 | TRU | TransUnion | 0001552033 | $15.08 | `7320` | medium | needs a decision |
| 142 | NXT | Nextpower Inc. | 0001852131 | $15.03 | `3674` | high |  |
| 143 | TTMI | TTM TECHNOLOGIES INC | 0001116942 | $14.85 | `3672` | high |  |
| 150 | LOGI | LOGITECH INTERNATIONAL S.A. | 0001032975 | $14.48 | `3577` | high |  |
| 151 | SMTC | SEMTECH CORP | 0000088941 | $14.37 | `3674` | high |  |
| 152 | CACI | CACI INTERNATIONAL INC /DE/ | 0000016058 | $14.35 | `7373` | medium | needs a decision |
| 155 | GWRE | Guidewire Software, Inc. | 0001528396 | $14.32 | `7372` | medium | needs a decision |
| 158 | W | Wayfair Inc. | 0001616707 | $14.12 | `5961` | high |  |
| 161 | AUR | Aurora Innovation, Inc. | 0001828108 | $13.97 | `7373` | medium | needs a decision |
| 163 | EQH | Equitable Holdings, Inc. | 0001333986 | $13.95 | `6411` | high |  |
| 165 | DT | Dynatrace, Inc. | 0001773383 | $13.76 | `7372` | medium | needs a decision |
| 171 | FIG | Figma, Inc. | 0001579878 | $13.32 | `7372` | medium | needs a decision; 1 10-K |
| 178 | AAOI | APPLIED OPTOELECTRONICS, INC. | 0001158114 | $13.10 | `3674` | high |  |
| 179 | PINS | PINTEREST, INC. | 0001506293 | $13.06 | `7370` | medium | needs a decision |
| 216 | FROG | JFrog Ltd | 0001800667 | $11.67 | `7372` | medium | needs a decision |
| 217 | EVR | Evercore Inc. | 0001360901 | $11.66 | `6282` | low | needs a decision |
| 218 | SANM | SANMINA CORP | 0000897723 | $11.63 | `3672` | high |  |
| 222 | MANH | MANHATTAN ASSOCIATES INC | 0001056696 | $11.46 | `7372` | medium | needs a decision |
| 224 | DOCU | DOCUSIGN, INC. | 0001261333 | $11.42 | `7372` | medium | needs a decision |
| 225 | VIAV | VIAVI SOLUTIONS INC. | 0000912093 | $11.41 | `3674` | high |  |
| 227 | CART | Maplebear Inc. | 0001579091 | $11.31 | `7389` | medium | needs a decision |
| 231 | SCI | SERVICE CORP INTERNATIONAL | 0000089089 | $11.25 | `7200` | medium |  |
| 232 | ARW | ARROW ELECTRONICS, INC. | 0000007536 | $11.22 | `5065` | medium |  |
| 240 | RMBS | RAMBUS INC | 0000917273 | $10.91 | `3674` | high |  |
| 244 | FORM | FORMFACTOR INC | 0001039399 | $10.79 | `3674` | high |  |
| 249 | HUBS | HUBSPOT INC | 0001404655 | $10.73 | `7372` | medium | needs a decision |
| 254 | SAIL | SailPoint, Inc. | 0002030781 | $10.54 | `7372` | medium | needs a decision; 2 10-Ks |
| 259 | BSY | BENTLEY SYSTEMS INC | 0001031308 | $10.49 | `7372` | medium | needs a decision |
| 279 | AMG | AFFILIATED MANAGERS GROUP, INC. | 0001004434 | $9.81 | `6282` | low | needs a decision |
| 285 | PAYC | Paycom Software, Inc. | 0001590955 | $9.65 | `7372` | medium | needs a decision |
| 291 | COMP | Compass, Inc. | 0001563190 | $9.51 | `6531` | medium |  |
| 312 | CHWY | Chewy, Inc. | 0001766502 | $9.06 | `5961` | high |  |
| 316 | BAH | Booz Allen Hamilton Holding Corp | 0001443646 | $9.02 | `8742` | medium |  |
| 318 | IDCC | InterDigital, Inc. | 0001405495 | $8.99 | `6794` | medium |  |
| 319 | APLD | Applied Digital Corp. | 0001144879 | $8.98 | `7374` | low | needs a decision |
| 326 | PCOR | PROCORE TECHNOLOGIES, INC. | 0001611052 | $8.87 | `7372` | medium | needs a decision |
| 334 | SNAP | Snap Inc | 0001564408 | $8.76 | `7370` | medium | needs a decision |
| 335 | HLI | HOULIHAN LOKEY, INC. | 0001302215 | $8.75 | `6282` | low | needs a decision |
| 337 | PL | Planet Labs PBC | 0001836833 | $8.69 | `3663` | high |  |
| 339 | MTCH | Match Group, Inc. | 0000891103 | $8.68 | `7370` | medium | needs a decision |
| 340 | ESTC | Elastic N.V. | 0001707753 | $8.67 | `7372` | medium | needs a decision |
| 343 | HQY | HEALTHEQUITY, INC. | 0001428336 | $8.56 | `7389` | medium | needs a decision |
| 346 | QRVO | Qorvo, Inc. | 0001604778 | $8.47 | `3674` | high |  |
| 349 | TTAN | ServiceTitan, Inc. | 0001638826 | $8.43 | `7372` | medium | needs a decision; 2 10-Ks |
| 359 | PATH | UiPath, Inc. | 0001734722 | $8.28 | `7372` | medium | needs a decision |
| 360 | SNEX | StoneX Group Inc. | 0000913760 | $8.28 | `6200` | high |  |
| 364 | ALGM | ALLEGRO MICROSYSTEMS, INC. | 0000866291 | $8.25 | `3674` | high |  |
| 369 | AVT | AVNET INC | 0000008858 | $8.09 | `5065` | medium |  |
| 370 | PCTY | Paylocity Holding Corp | 0001591698 | $8.05 | `7372` | medium | needs a decision |
| 376 | ESE | ESCO TECHNOLOGIES INC | 0000866706 | $7.98 | `3669` | medium |  |
| 380 | MBLY | Mobileye Global Inc. | 0001910139 | $7.85 | `7372` | medium | needs a decision |
| 387 | MORN | Morningstar, Inc. | 0001289419 | $7.76 | `6282` | low | needs a decision |
| 393 | MXL | MAXLINEAR, INC | 0001288469 | $7.69 | `3674` | high |  |
| 395 | Z | ZILLOW GROUP, INC. | 0001617640 | $7.58 | `7389` | medium | needs a decision |
| 405 | S | SentinelOne, Inc. | 0001583708 | $7.48 | `7372` | medium | needs a decision |
| 409 | TRNO | Terreno Realty Corp | 0001476150 | $7.43 | `6500` | medium |  |
| 410 | LNWO | Light & Wonder, Inc. | 0000750004 | $7.42 | `7373` | medium | needs a decision |
| 414 | SLAB | SILICON LABORATORIES INC. | 0001038074 | $7.32 | `3674` | high |  |
| 415 | PLXS | PLEXUS CORP | 0000785786 | $7.31 | `3672` | high |  |
| 416 | VCTR | Victory Capital Holdings, Inc. | 0001570827 | $7.31 | `6282` | low | needs a decision |
| 417 | NAVN | Navan, Inc. | 0001639723 | $7.30 | `7372` | medium | needs a decision; 1 10-K |
| 424 | DBX | DROPBOX, INC. | 0001467623 | $7.26 | `7372` | medium | needs a decision |
| 425 | ZETA | Zeta Global Holdings Corp. | 0001851003 | $7.24 | `7372` | medium | needs a decision |
| 428 | ETSY | ETSY INC | 0001370637 | $7.20 | `7389` | medium | needs a decision |
| 433 | HNGE | Hinge Health, Inc. | 0001673743 | $7.09 | `7374` | low | needs a decision; 1 10-K |
| 442 | APPF | APPFOLIO INC | 0001433195 | $6.94 | `7372` | medium | needs a decision |
| 448 | ACT | Enact Holdings, Inc. | 0001823529 | $6.84 | `6411` | high |  |
| 449 | GTLB | Gitlab Inc. | 0001653482 | $6.84 | `7372` | medium | needs a decision |
| 475 | LYFT | Lyft, Inc. | 0001759509 | $6.52 | `7389` | medium | needs a decision |
| 482 | WEX | WEX Inc. | 0001309108 | $6.44 | `7389` | medium | needs a decision |
| 492 | QLYS | QUALYS, INC. | 0001107843 | $6.34 | `7372` | medium | needs a decision |
| 496 | AXTI | AXT INC | 0001051627 | $6.29 | `3674` | high |  |
| 499 | RGTI | Rigetti Computing, Inc. | 0001838359 | $6.23 | `7371` | high |  |

#### `industrials` &mdash; 95 candidates ($6.38 bn to $68.38 bn)

| # | ticker | company | CIK | market cap $bn | SIC | conf. | note |
|---:|---|---|---|---:|---|---|---|
| 11 | BE | Bloom Energy Corp | 0001664703 | $68.38 | `3620` | medium |  |
| 18 | RKLB | Rocket Lab Corp | 0001819994 | $52.47 | `3760` | medium |  |
| 19 | HEI | HEICO CORP | 0000046619 | $51.88 | `3724` | high |  |
| 20 | FERG | Ferguson Enterprises Inc. /DE/ | 0002011641 | $47.39 | `5070` | medium | 2 10-Ks |
| 25 | WCN | Waste Connections, Inc. | 0001318220 | $41.51 | `4953` | high |  |
| 35 | SUNB | Sunbelt Rentals Holdings, Inc. | 0002083785 | $34.08 | `7359` | medium | 1 10-K |
| 45 | NVT | nVent Electric plc | 0001720635 | $28.68 | `3550` | medium |  |
| 54 | SN | SharkNinja, Inc. | 0001957132 | $25.99 | `3630` | medium | 1 10-K |
| 56 | CW | CURTISS WRIGHT CORP | 0000026324 | $25.71 | `3590` | medium |  |
| 65 | MTZ | MASTEC INC | 0000015615 | $24.29 | `1623` | medium |  |
| 68 | FTAI | FTAI Aviation Ltd. | 0001590364 | $23.36 | `7350` | medium |  |
| 73 | WWD | Woodward, Inc. | 0000108312 | $21.87 | `3620` | medium |  |
| 74 | RS | RELIANCE, INC. | 0000861884 | $21.85 | `5051` | medium |  |
| 77 | MKSI | MKS INC | 0001049502 | $21.69 | `3823` | low | needs a decision |
| 78 | RIVN | Rivian Automotive, Inc. / DE | 0001874178 | $21.53 | `3711` | low | needs a decision |
| 79 | FDXF | FedEx Freight Holding Company, Inc. | 0002082247 | $21.50 | `4513` | medium | 1 10-K |
| 80 | ONTO | ONTO INNOVATION INC. | 0000704532 | $21.46 | `3829` | low | needs a decision |
| 85 | SNX | TD SYNNEX CORP | 0001177394 | $21.10 | `5045` | medium |  |
| 94 | ITT | ITT INC. | 0000216228 | $19.75 | `3561` | high |  |
| 95 | APG | APi Group Corp | 0001796209 | $19.33 | `7340` | low | needs a decision |
| 102 | STRL | STERLING INFRASTRUCTURE, INC. | 0000874238 | $18.47 | `1600` | medium |  |
| 104 | WCC | WESCO INTERNATIONAL INC | 0000929008 | $18.18 | `5063` | medium |  |
| 108 | RBC | RBC Bearings INC | 0001324948 | $17.65 | `3562` | medium |  |
| 112 | CLH | CLEAN HARBORS INC | 0000822818 | $17.21 | `4955` | medium |  |
| 121 | CNH | CNH Industrial N.V. | 0001567094 | $16.55 | `3531` | low | needs a decision |
| 131 | IESC | IES Holdings, Inc. | 0001048268 | $15.82 | `1731` | high |  |
| 132 | BWXT | BWX Technologies, Inc. | 0001486957 | $15.72 | `3510` | medium |  |
| 135 | LECO | LINCOLN ELECTRIC HOLDINGS INC | 0000059527 | $15.59 | `3540` | medium |  |
| 136 | ULS | UL Solutions Inc. | 0001901440 | $15.57 | `8734` | medium | 2 10-Ks |
| 148 | QXO | QXO, Inc. | 0001236275 | $14.50 | `5030` | medium |  |
| 157 | BWA | BORGWARNER INC | 0000908255 | $14.24 | `3714` | medium |  |
| 160 | MOG-A | MOOG INC. | 0000067887 | $14.11 | `3590` | medium |  |
| 162 | AEIS | ADVANCED ENERGY INDUSTRIES INC | 0000927003 | $13.96 | `3679` | medium |  |
| 166 | SGI | SOMNIGROUP INTERNATIONAL INC. | 0001206264 | $13.68 | `2510` | medium |  |
| 174 | GGG | GRACO INC | 0000042888 | $13.21 | `3561` | high |  |
| 177 | AIT | APPLIED INDUSTRIAL TECHNOLOGIES INC | 0000109563 | $13.17 | `5080` | medium |  |
| 180 | DY | DYCOM INDUSTRIES INC | 0000067215 | $13.00 | `1623` | medium |  |
| 185 | WSO | WATSCO INC | 0000105016 | $12.86 | `5070` | medium |  |
| 186 | WTS | WATTS WATER TECHNOLOGIES INC | 0000795403 | $12.86 | `3490` | medium |  |
| 192 | CCK | CROWN HOLDINGS, INC. | 0001219601 | $12.64 | `3411` | low | needs a decision |
| 193 | CR | Crane Co | 0001944013 | $12.63 | `3490` | medium |  |
| 203 | DRS | Leonardo DRS, Inc. | 0001833756 | $12.10 | `3812` | low | needs a decision |
| 207 | LFUS | LITTELFUSE INC /DE | 0000889331 | $11.98 | `3613` | medium |  |
| 211 | KTOS | KRATOS DEFENSE & SECURITY SOLUTIONS, INC. | 0001069258 | $11.88 | `3760` | medium |  |
| 212 | KNX | Knight-Swift Transportation Holdings Inc. | 0001492691 | $11.85 | `4213` | high |  |
| 215 | VICR | VICOR CORP | 0000751978 | $11.69 | `3679` | medium |  |
| 219 | RRX | REGAL REXNORD CORP | 0000082811 | $11.62 | `3569` | medium |  |
| 221 | MOD | MODINE MANUFACTURING CO | 0000067347 | $11.51 | `3714` | medium |  |
| 234 | CGNX | COGNEX CORP | 0000851205 | $11.20 | `3823` | low | needs a decision |
| 237 | DCI | DONALDSON Co INC | 0000029644 | $10.97 | `3564` | medium |  |
| 241 | SPXC | SPX Technologies, Inc. | 0000088205 | $10.90 | `3540` | medium |  |
| 245 | AYI | ACUITY INC. (DE) | 0001144215 | $10.79 | `3640` | medium |  |
| 258 | ALSN | Allison Transmission Holdings Inc | 0001411207 | $10.50 | `3714` | medium |  |
| 265 | FLS | FLOWSERVE CORP | 0000030625 | $10.29 | `3561` | high |  |
| 266 | SAIA | SAIA INC | 0001177702 | $10.28 | `4213` | high |  |
| 271 | R | RYDER SYSTEM INC | 0000085961 | $10.15 | `7510` | medium |  |
| 280 | VMI | VALMONT INDUSTRIES INC | 0000102729 | $9.78 | `3440` | medium |  |
| 292 | OSK | OSHKOSH CORP | 0000775158 | $9.51 | `3711` | low | needs a decision |
| 296 | TTC | TORO CO | 0000737758 | $9.28 | `3524` | medium |  |
| 297 | TKR | TIMKEN CO | 0000098362 | $9.28 | `3562` | medium |  |
| 303 | AVAV | AeroVironment Inc | 0001368622 | $9.21 | `3721` | medium |  |
| 305 | TTEK | TETRA TECH INC | 0000831641 | $9.17 | `8711` | medium |  |
| 311 | SARO | StandardAero, Inc. | 0002025410 | $9.06 | `3724` | high | 2 10-Ks |
| 328 | ALV | AUTOLIV INC | 0001034670 | $8.84 | `3714` | medium |  |
| 345 | CNM | Core & Main, Inc. | 0001856525 | $8.49 | `5099` | medium |  |
| 354 | ZWS | Zurn Elkay Water Solutions Corp | 0001439288 | $8.34 | `3560` | medium | needs a decision |
| 356 | LEA | LEAR CORP | 0000842162 | $8.31 | `3714` | medium |  |
| 361 | AGX | ARGAN INC | 0000100591 | $8.26 | `1700` | medium |  |
| 365 | KRMN | Karman Holdings Inc. | 0002040127 | $8.19 | `3728` | medium | 2 10-Ks |
| 372 | SSD | Simpson Manufacturing Co., Inc. | 0000920371 | $8.03 | `3420` | high |  |
| 374 | ACM | AECOM | 0000868857 | $8.01 | `8711` | medium |  |
| 377 | POWL | POWELL INDUSTRIES INC | 0000080420 | $7.97 | `3613` | medium |  |
| 378 | RAL | Ralliant Corp | 0002041385 | $7.96 | `3823` | low | needs a decision; 1 10-K |
| 381 | JOBY | Joby Aviation, Inc. | 0001819848 | $7.82 | `3721` | medium |  |
| 391 | FSS | FEDERAL SIGNAL CORP /DE/ | 0000277509 | $7.70 | `3711` | low | needs a decision |
| 392 | TEX | TEREX CORP | 0000097216 | $7.70 | `3537` | medium |  |
| 398 | LGN | Legence Corp. | 0002052568 | $7.57 | `1700` | medium | 1 10-K |
| 412 | FLR | FLUOR CORP | 0001124198 | $7.32 | `1600` | medium |  |
| 418 | ENS | EnerSys | 0001289308 | $7.30 | `3690` | medium |  |
| 420 | LOAR | Loar Holdings Inc. | 0002000178 | $7.29 | `3728` | medium | 2 10-Ks |
| 423 | AAON | AAON, INC. | 0000824142 | $7.26 | `3585` | high |  |
| 429 | GTES | Gates Industrial Corp Ltd. | 0001718512 | $7.12 | `3560` | medium | needs a decision |
| 430 | ACA | Arcosa, Inc. | 0001739445 | $7.12 | `3440` | medium |  |
| 440 | AGCO | AGCO CORP /DE | 0000880266 | $6.99 | `3523` | medium |  |
| 441 | MSM | MSC INDUSTRIAL DIRECT CO INC | 0001003078 | $6.96 | `5084` | medium |  |
| 450 | ROAD | Construction Partners, Inc. | 0001718227 | $6.84 | `1600` | medium |  |
| 452 | VSEC | VSE CORP | 0000102752 | $6.83 | `8711` | medium |  |
| 453 | MRCY | MERCURY SYSTEMS INC | 0001049521 | $6.81 | `3670` | medium |  |
| 460 | ST | Sensata Technologies Holding plc | 0001477294 | $6.68 | `3823` | low | needs a decision |
| 472 | LSTR | LANDSTAR SYSTEM INC | 0000853816 | $6.56 | `4213` | high |  |
| 479 | INGM | Ingram Micro Holding Corp | 0001897762 | $6.46 | `5045` | medium | 2 10-Ks |
| 481 | LKQ | LKQ CORP | 0001065696 | $6.44 | `5010` | medium |  |
| 486 | MWH | SOLV Energy, Inc. | 0002065636 | $6.39 | `1600` | medium | 1 10-K |
| 487 | SNDR | Schneider National, Inc. | 0001692063 | $6.38 | `4213` | high |  |
| 488 | NOVT | NOVANTA INC | 0001076930 | $6.38 | `3690` | medium |  |

#### `pharma_medtech` &mdash; 58 candidates ($6.34 bn to $45.44 bn)

| # | ticker | company | CIK | market cap $bn | SIC | conf. | note |
|---:|---|---|---|---:|---|---|---|
| 21 | RVMD | Revolution Medicines, Inc. | 0001628171 | $45.44 | `2836` | high |  |
| 24 | TEVA | TEVA PHARMACEUTICAL INDUSTRIES LTD | 0000818686 | $42.49 | `2834` | high |  |
| 27 | ONC | BeOne Medicines Ltd. | 0001651308 | $41.01 | `2834` | high |  |
| 40 | MDLN | Medline Inc. | 0002046386 | $30.60 | `3841` | medium | needs a decision; 1 10-K |
| 41 | ALNY | ALNYLAM PHARMACEUTICALS, INC. | 0001178670 | $30.05 | `2834` | high |  |
| 43 | ILMN | ILLUMINA, INC. | 0001110803 | $29.16 | `3826` | high |  |
| 47 | INSM | INSMED Inc | 0001104506 | $28.02 | `2834` | high |  |
| 52 | RPRX | Royalty Pharma plc | 0001802768 | $26.47 | `2834` | high |  |
| 53 | ROIV | Roivant Sciences Ltd. | 0001635088 | $26.18 | `2834` | high |  |
| 55 | MRNA | Moderna, Inc. | 0001682852 | $25.73 | `2836` | high |  |
| 75 | UTHR | UNITED THERAPEUTICS Corp | 0001082554 | $21.81 | `2834` | high |  |
| 120 | MEDP | Medpace Holdings, Inc. | 0001668397 | $16.67 | `8731` | high |  |
| 127 | JAZZ | Jazz Pharmaceuticals plc | 0001232524 | $16.12 | `2834` | high |  |
| 133 | NBIX | NEUROCRINE BIOSCIENCES INC | 0000914475 | $15.70 | `2836` | high |  |
| 134 | BBIO | BridgeBio Pharma, Inc. | 0001743881 | $15.62 | `2834` | high |  |
| 182 | EXEL | EXELIXIS, INC. | 0000939767 | $12.96 | `2836` | high |  |
| 183 | BMRN | BIOMARIN PHARMACEUTICAL INC | 0001048477 | $12.90 | `2834` | high |  |
| 184 | PEN | Penumbra Inc | 0001321732 | $12.89 | `3841` | medium | needs a decision |
| 189 | CORT | CORCEPT THERAPEUTICS INC | 0001088856 | $12.67 | `2834` | high |  |
| 197 | ARWR | ARROWHEAD PHARMACEUTICALS, INC. | 0000879407 | $12.53 | `2834` | high |  |
| 202 | MDGL | MADRIGAL PHARMACEUTICALS, INC. | 0001157601 | $12.13 | `2834` | high |  |
| 213 | ELAN | Elanco Animal Health Inc | 0001739104 | $11.79 | `2834` | high |  |
| 214 | HALO | HALOZYME THERAPEUTICS, INC. | 0001159036 | $11.69 | `2836` | high |  |
| 223 | GMED | GLOBUS MEDICAL INC | 0001237831 | $11.43 | `3841` | medium | needs a decision |
| 226 | AXSM | Axsome Therapeutics, Inc. | 0001579428 | $11.33 | `2834` | high |  |
| 238 | GKOS | GLAUKOS Corp | 0001192448 | $10.95 | `3841` | medium | needs a decision |
| 253 | CYTK | CYTOKINETICS INC | 0001061983 | $10.55 | `2834` | high |  |
| 257 | PRAX | Praxis Precision Medicines, Inc. | 0001689548 | $10.51 | `2834` | high |  |
| 267 | PTGX | Protagonist Therapeutics, Inc | 0001377121 | $10.26 | `2834` | high |  |
| 269 | SMMT | Summit Therapeutics Inc. | 0001599298 | $10.20 | `2834` | high |  |
| 270 | APGE | Apogee Therapeutics, Inc. | 0001974640 | $10.19 | `2836` | high |  |
| 274 | KYMR | Kymera Therapeutics, Inc. | 0001815442 | $9.99 | `2836` | high |  |
| 275 | KRYS | Krystal Biotech, Inc. | 0001711279 | $9.94 | `2836` | high |  |
| 282 | IONS | IONIS PHARMACEUTICALS INC | 0000874015 | $9.74 | `2834` | high |  |
| 289 | RGEN | REPLIGEN CORP | 0000730272 | $9.54 | `2836` | high |  |
| 293 | BIO | BIO-RAD LABORATORIES, INC. | 0000012208 | $9.50 | `3826` | high |  |
| 302 | SYRE | Spyre Therapeutics, Inc. | 0001636282 | $9.22 | `2834` | high |  |
| 309 | AVTR | Avantor, Inc. | 0001722482 | $9.13 | `3826` | high |  |
| 314 | IMVT | Immunovant, Inc. | 0001764013 | $9.03 | `2836` | high |  |
| 317 | CRNX | Crinetics Pharmaceuticals, Inc. | 0001658247 | $8.99 | `2834` | high |  |
| 320 | PCVX | Vaxcyte, Inc. | 0001649094 | $8.96 | `2836` | high |  |
| 331 | BRKR | BRUKER CORP | 0001109354 | $8.79 | `3826` | high |  |
| 350 | IBRX | ImmunityBio, Inc. | 0001326110 | $8.39 | `2836` | high |  |
| 353 | ALKS | Alkermes plc. | 0001520262 | $8.36 | `2834` | high |  |
| 379 | RYTM | RHYTHM PHARMACEUTICALS, INC. | 0001649904 | $7.95 | `2834` | high |  |
| 383 | TWST | Twist Bioscience Corp | 0001581280 | $7.80 | `2836` | high |  |
| 399 | TXG | 10x Genomics, Inc. | 0001770787 | $7.56 | `3826` | high |  |
| 400 | TGTX | TG THERAPEUTICS, INC. | 0001001316 | $7.54 | `2834` | high |  |
| 407 | ORKA | Oruka Therapeutics, Inc. | 0000907654 | $7.46 | `2834` | high |  |
| 419 | MSA | MSA Safety Inc | 0000066570 | $7.30 | `3842` | high |  |
| 444 | LQDA | Liquidia Corp | 0001819576 | $6.91 | `2834` | high |  |
| 451 | CGON | CG Oncology, Inc. | 0001991792 | $6.84 | `2836` | high |  |
| 466 | LNTH | Lantheus Holdings, Inc. | 0001521036 | $6.59 | `2835` | medium |  |
| 468 | COGT | Cogent Biosciences, Inc. | 0001622229 | $6.57 | `2834` | high |  |
| 483 | DNTH | Dianthus Therapeutics, Inc. /DE/ | 0001690585 | $6.42 | `2834` | high |  |
| 484 | AMRX | Amneal Pharmaceuticals, Inc. | 0001723128 | $6.42 | `2834` | high |  |
| 485 | ERAS | Erasca, Inc. | 0001761918 | $6.39 | `2834` | high |  |
| 493 | SRRK | Scholar Rock Holding Corp | 0001727196 | $6.34 | `2836` | high |  |

#### `financial` &mdash; 45 candidates ($6.32 bn to $41.06 bn)

| # | ticker | company | CIK | market cap $bn | SIC | conf. | note |
|---:|---|---|---|---:|---|---|---|
| 26 | RKT | Rocket Companies, Inc. | 0001805284 | $41.06 | `6162` | medium |  |
| 30 | MSTR | Strategy Inc | 0001050446 | $38.81 | `6199` | medium | needs a decision |
| 57 | FCNCA | FIRST CITIZENS BANCSHARES INC /DE/ | 0000798941 | $25.39 | `6022` | high |  |
| 60 | AFRM | Affirm Holdings, Inc. | 0001820953 | $24.96 | `6141` | medium |  |
| 97 | CRCL | Circle Internet Group, Inc. | 0001876042 | $18.94 | `6199` | medium | needs a decision; 1 10-K |
| 101 | EWBC | EAST WEST BANCORP INC | 0001069157 | $18.57 | `6022` | high |  |
| 125 | PNFP | Pinnacle Financial Partners, Inc. | 0002082866 | $16.22 | `6021` | high | 1 10-K |
| 129 | IREN | IREN Ltd | 0001878848 | $16.05 | `6199` | medium | needs a decision; 1 10-K |
| 172 | ALLY | Ally Financial Inc. | 0000040729 | $13.27 | `6022` | high |  |
| 187 | WBS | WEBSTER FINANCIAL CORP | 0000801337 | $12.75 | `6021` | high |  |
| 188 | SF | STIFEL FINANCIAL CORP | 0000720672 | $12.68 | `6211` | medium | needs a decision |
| 190 | SEIC | SEI INVESTMENTS CO | 0000350894 | $12.66 | `6211` | medium | needs a decision |
| 195 | JEF | Jefferies Financial Group Inc. | 0000096223 | $12.58 | `6211` | medium | needs a decision; 1 10-K |
| 198 | FHN | FIRST HORIZON CORP | 0000036966 | $12.33 | `6021` | high |  |
| 210 | CHYM | Chime Financial, Inc. | 0001795586 | $11.91 | `6199` | medium | needs a decision; 1 10-K |
| 220 | UMBF | UMB FINANCIAL CORP | 0000101382 | $11.54 | `6021` | high |  |
| 228 | BMNR | BITMINE IMMERSION TECHNOLOGIES, INC. | 0001829311 | $11.30 | `6199` | medium | needs a decision |
| 230 | BPOP | POPULAR, INC. | 0000763901 | $11.28 | `6022` | high |  |
| 242 | WTFC | WINTRUST FINANCIAL CORP | 0001015328 | $10.86 | `6022` | high |  |
| 243 | HUT | Hut 8 Corp. | 0001964789 | $10.85 | `6199` | medium | needs a decision; 2 10-Ks |
| 248 | SSB | SouthState Bank Corp | 0000764038 | $10.75 | `6022` | high |  |
| 260 | ZION | ZIONS BANCORPORATION, NATIONAL ASSOCIATION /UT/ | 0000109380 | $10.45 | `6021` | high |  |
| 261 | CFR | CULLEN/FROST BANKERS, INC. | 0000039263 | $10.45 | `6021` | high |  |
| 264 | ONB | OLD NATIONAL BANCORP /IN/ | 0000707179 | $10.36 | `6021` | high |  |
| 286 | FRHC | Freedom Holding Corp. | 0000924805 | $9.60 | `6211` | medium | needs a decision |
| 307 | COLB | COLUMBIA BANKING SYSTEM, INC. | 0000887343 | $9.15 | `6022` | high |  |
| 321 | PB | PROSPERITY BANCSHARES INC | 0001068851 | $8.95 | `6022` | high |  |
| 322 | WAL | WESTERN ALLIANCE BANCORPORATION | 0001212545 | $8.92 | `6022` | high |  |
| 327 | BOKF | BOK FINANCIAL CORP | 0000875357 | $8.85 | `6021` | high |  |
| 333 | WULF | TERAWULF INC. | 0001083301 | $8.78 | `6199` | medium | needs a decision |
| 341 | CBSH | COMMERCE BANCSHARES INC /MO/ | 0000022356 | $8.56 | `6022` | high |  |
| 362 | VLY | VALLEY NATIONAL BANCORP | 0000714310 | $8.26 | `6021` | high |  |
| 373 | FIGR | Figure Technology Solutions, Inc. | 0002064124 | $8.02 | `6163` | medium | 1 10-K |
| 385 | CBC | Central Bancompany, Inc. | 0002065601 | $7.80 | `6022` | high | 1 10-K |
| 394 | CIFR | Cipher Digital Inc. | 0001819989 | $7.68 | `6199` | medium | needs a decision |
| 402 | RIOT | Riot Platforms, Inc. | 0001167419 | $7.52 | `6199` | medium | needs a decision |
| 404 | OMF | OneMain Holdings, Inc. | 0001584207 | $7.49 | `6141` | medium |  |
| 431 | FNMA | FEDERAL NATIONAL MORTGAGE ASSOCIATION FANNIE MAE | 0000310522 | $7.10 | `6111` | medium | 2 10-Ks |
| 445 | FNB | FNB CORP/PA/ | 0000037808 | $6.91 | `6021` | high |  |
| 456 | WBHC | WILSON BANK HOLDING CO | 0000885275 | $6.76 | `6021` | high |  |
| 464 | UBSI | UNITED BANKSHARES INC/WV | 0000729986 | $6.67 | `6022` | high |  |
| 469 | ENVA | Enova International, Inc. | 0001529864 | $6.57 | `6141` | medium |  |
| 477 | CORZ | Core Scientific, Inc./tx | 0001839341 | $6.47 | `6199` | medium | needs a decision |
| 478 | GBCI | GLACIER BANCORP, INC. | 0000868671 | $6.46 | `6022` | high |  |
| 494 | HWC | HANCOCK WHITNEY CORP | 0000750577 | $6.32 | `6022` | high |  |

#### `materials` &mdash; 29 candidates ($6.30 bn to $162 bn)

| # | ticker | company | CIK | market cap $bn | SIC | conf. | note |
|---:|---|---|---|---:|---|---|---|
| 2 | SCCO | SOUTHERN COPPER CORP/ | 0001001838 | $162 | `1000` | medium |  |
| 37 | ATI | ATI INC | 0001018963 | $31.56 | `3317` | medium |  |
| 49 | CRS | CARPENTER TECHNOLOGY CORP | 0000017843 | $26.95 | `3312` | low | needs a decision |
| 59 | AMRZ | Amrize Ltd | 0002035989 | $25.01 | `3241` | medium | 1 10-K |
| 61 | ENTG | ENTEGRIS INC | 0001101302 | $24.92 | `3089` | medium |  |
| 89 | RGLD | ROYAL GOLD INC | 0000085535 | $20.05 | `6795` | medium |  |
| 106 | JHX | James Hardie Industries plc | 0001159152 | $17.67 | `3272` | medium | 1 10-K |
| 146 | MLI | MUELLER INDUSTRIES INC | 0000089439 | $14.74 | `3350` | low | needs a decision |
| 153 | RPM | RPM INTERNATIONAL INC/DE/ | 0000110621 | $14.33 | `2851` | medium |  |
| 154 | CSL | CARLISLE COMPANIES INC | 0000790051 | $14.32 | `3060` | medium |  |
| 167 | AA | Alcoa Corp | 0001675149 | $13.65 | `3334` | medium |  |
| 191 | HL | HECLA MINING CO/DE/ | 0000719413 | $12.64 | `1400` | high |  |
| 200 | OC | Owens Corning | 0001370946 | $12.16 | `3290` | medium |  |
| 236 | WMS | ADVANCED DRAINAGE SYSTEMS, INC. | 0001604028 | $11.16 | `3086` | medium |  |
| 262 | MP | MP Materials Corp. / DE | 0001801368 | $10.42 | `1000` | medium |  |
| 273 | WLK | WESTLAKE CORP | 0001262823 | $9.99 | `2860` | high |  |
| 276 | SOLS | Solstice Advanced Materials Inc. | 0002064953 | $9.94 | `2800` | medium | 1 10-K |
| 287 | ESI | Element Solutions Inc | 0001590714 | $9.56 | `2890` | medium |  |
| 336 | NEU | NEWMARKET CORP | 0001282637 | $8.75 | `2860` | high |  |
| 347 | EMN | EASTMAN CHEMICAL CO | 0000915389 | $8.46 | `2821` | low | needs a decision |
| 351 | ATR | APTARGROUP, INC. | 0000896622 | $8.38 | `3089` | medium |  |
| 371 | CMC | COMMERCIAL METALS Co | 0000022444 | $8.05 | `3312` | low | needs a decision |
| 384 | HXL | HEXCEL CORP /DE/ | 0000717605 | $7.80 | `2821` | low | needs a decision |
| 389 | AXTA | Axalta Coating Systems Ltd. | 0001616862 | $7.73 | `2851` | medium |  |
| 397 | AWI | ARMSTRONG WORLD INDUSTRIES INC | 0000007431 | $7.57 | `3089` | medium |  |
| 411 | NPO | Enpro Inc. | 0001164863 | $7.33 | `3050` | medium |  |
| 435 | CLF | CLEVELAND-CLIFFS INC. | 0000764065 | $7.02 | `1000` | medium |  |
| 459 | SSRM | SSR MINING INC. | 0000921638 | $6.68 | `6795` | medium |  |
| 495 | EXP | EAGLE MATERIALS INC | 0000918646 | $6.30 | `3241` | medium |  |

#### `reit` &mdash; 26 candidates ($6.44 bn to $17.61 bn)

| # | ticker | company | CIK | market cap $bn | SIC | conf. | note |
|---:|---|---|---|---:|---|---|---|
| 109 | NLY | ANNALY CAPITAL MANAGEMENT INC | 0001043219 | $17.61 | `6798` | high |  |
| 123 | WPC | W. P. Carey Inc. | 0001025378 | $16.29 | `6798` | high |  |
| 138 | LAMR | LAMAR ADVERTISING CO/NEW | 0001090425 | $15.47 | `6798` | high |  |
| 145 | SUI | SUN COMMUNITIES INC | 0000912593 | $14.78 | `6798` | high |  |
| 159 | OHI | OMEGA HEALTHCARE INVESTORS INC | 0000888491 | $14.11 | `6798` | high |  |
| 181 | AGNC | AGNC Investment Corp. | 0001423689 | $12.98 | `6798` | high |  |
| 194 | ELS | EQUITY LIFESTYLE PROPERTIES INC | 0000895417 | $12.59 | `6798` | high |  |
| 199 | GLPI | Gaming & Leisure Properties, Inc. | 0001575965 | $12.29 | `6798` | high |  |
| 204 | AMH | American Homes 4 Rent | 0001562401 | $12.10 | `6798` | high |  |
| 209 | AHR | American Healthcare REIT, Inc. | 0001632970 | $11.92 | `6798` | high |  |
| 239 | EGP | EASTGROUP PROPERTIES INC | 0000049600 | $10.95 | `6798` | high |  |
| 295 | LINE | Lineage, Inc. | 0001868159 | $9.29 | `6798` | high | 2 10-Ks |
| 298 | CUBE | CubeSmart | 0001298675 | $9.28 | `6798` | high |  |
| 299 | CTRE | CareTrust REIT, Inc. | 0001590717 | $9.28 | `6798` | high |  |
| 300 | ADC | AGREE REALTY CORP | 0000917251 | $9.27 | `6798` | high |  |
| 308 | BRX | Brixmor Property Group Inc. | 0001581068 | $9.13 | `6798` | high |  |
| 332 | NNN | NNN REIT, INC. | 0000751364 | $8.78 | `6798` | high |  |
| 342 | RHP | Ryman Hospitality Properties, Inc. | 0001040829 | $8.56 | `6798` | high |  |
| 355 | FR | FIRST INDUSTRIAL REALTY TRUST INC | 0000921825 | $8.34 | `6798` | high |  |
| 375 | REXR | Rexford Industrial Realty, Inc. | 0001571283 | $8.00 | `6798` | high |  |
| 432 | STAG | STAG Industrial, Inc. | 0001479094 | $7.10 | `6798` | high |  |
| 434 | VNO | VORNADO REALTY TRUST | 0000899689 | $7.08 | `6798` | high |  |
| 439 | MAC | MACERICH CO | 0000912242 | $6.99 | `6798` | high |  |
| 457 | EPRT | ESSENTIAL PROPERTIES REALTY TRUST, INC. | 0001728951 | $6.73 | `6798` | high |  |
| 470 | HR | Healthcare Realty Trust Inc | 0001360604 | $6.56 | `6798` | high |  |
| 480 | RYN | RAYONIER INC | 0000052827 | $6.44 | `6798` | high |  |

#### `energy` &mdash; 24 candidates ($6.35 bn to $110 bn)

| # | ticker | company | CIK | market cap $bn | SIC | conf. | note |
|---:|---|---|---|---:|---|---|---|
| 4 | ENB | ENBRIDGE INC | 0000895728 | $110 | `4610` | medium |  |
| 7 | EPD | ENTERPRISE PRODUCTS PARTNERS L.P. | 0001061219 | $83.38 | `4922` | high |  |
| 10 | ET | Energy Transfer LP | 0001276187 | $72.10 | `4922` | high |  |
| 13 | MPLX | MPLX LP | 0001552000 | $59.90 | `4610` | medium |  |
| 87 | SOCGP | SOUTHERN CALIFORNIA GAS CO | 0000092108 | $20.34 | `4922` | high |  |
| 88 | WES | Western Midstream Partners, LP | 0001423902 | $20.08 | `4922` | high |  |
| 100 | PR | Permian Resources Corp | 0001658566 | $18.58 | `1311` | medium | needs a decision |
| 107 | OVV | Ovintiv Inc. | 0001792580 | $17.66 | `1311` | medium | needs a decision |
| 116 | DINO | HF Sinclair Corp | 0001915657 | $16.89 | `4610` | medium |  |
| 118 | PAA | PLAINS ALL AMERICAN PIPELINE LP | 0001070423 | $16.76 | `4610` | medium |  |
| 137 | VNOM | Viper Energy, Inc. | 0002074176 | $15.50 | `1311` | medium | needs a decision; 1 10-K |
| 147 | APA | APA Corp | 0001841666 | $14.57 | `1311` | medium | needs a decision; in the exclusion record |
| 164 | DTM | DT Midstream, Inc. | 0001842022 | $13.77 | `4922` | high |  |
| 235 | AR | ANTERO RESOURCES Corp | 0001433270 | $11.19 | `1311` | medium | needs a decision |
| 256 | AM | Antero Midstream Corp | 0001623925 | $10.51 | `4922` | high |  |
| 304 | RRC | RANGE RESOURCES CORP | 0000315852 | $9.20 | `1311` | medium | needs a decision |
| 348 | SM | SM Energy Co | 0000893538 | $8.44 | `1311` | medium | needs a decision |
| 382 | CHRD | Chord Energy Corp | 0001486159 | $7.82 | `1311` | medium | needs a decision |
| 427 | NE | Noble Corp plc | 0001895262 | $7.21 | `1381` | medium |  |
| 443 | MTDR | Matador Resources Co | 0001520006 | $6.92 | `1311` | medium | needs a decision |
| 462 | KGS | Kodiak Gas Services, Inc. | 0001767042 | $6.67 | `4922` | high |  |
| 465 | SWX | Southwest Gas Holdings, Inc. | 0001692115 | $6.61 | `4923` | medium |  |
| 473 | RIG | Transocean Ltd. | 0001451505 | $6.56 | `1381` | medium |  |
| 491 | MGY | Magnolia Oil & Gas Corp | 0001698990 | $6.35 | `1311` | medium | needs a decision |

#### `retail` &mdash; 20 candidates ($6.23 bn to $77.07 bn)

| # | ticker | company | CIK | market cap $bn | SIC | conf. | note |
|---:|---|---|---|---:|---|---|---|
| 9 | CVNA | CARVANA CO. | 0001690820 | $77.07 | `5500` | low | needs a decision; in the exclusion record |
| 84 | BURL | Burlington Stores, Inc. | 0001579298 | $21.20 | `5311` | medium |  |
| 110 | DKS | DICK'S SPORTING GOODS, INC. | 0001089063 | $17.56 | `5940` | medium |  |
| 156 | PAG | PENSKE AUTOMOTIVE GROUP, INC. | 0001019849 | $14.31 | `5500` | low | needs a decision |
| 175 | FIVE | FIVE BELOW, INC | 0001177609 | $13.19 | `5331` | high |  |
| 205 | BJ | BJ's Wholesale Club Holdings, Inc. | 0001531152 | $12.06 | `5331` | high |  |
| 246 | MUSA | Murphy USA Inc. | 0001573516 | $10.77 | `5500` | low | needs a decision |
| 294 | FCFS | FirstCash Holdings, Inc. | 0000840489 | $9.38 | `5900` | medium |  |
| 306 | MHK | MOHAWK INDUSTRIES INC | 0000851968 | $9.17 | `2273` | medium |  |
| 313 | DDS | DILLARD'S, INC. | 0000028917 | $9.05 | `5311` | medium |  |
| 323 | RUSHA | RUSH ENTERPRISES INC \TX\ | 0001012019 | $8.90 | `5500` | low | needs a decision |
| 338 | LEVI | LEVI STRAUSS & CO | 0000094845 | $8.69 | `2300` | medium |  |
| 357 | KMX | CARMAX INC | 0001170010 | $8.31 | `5500` | low | needs a decision |
| 363 | GME | GameStop Corp. | 0001326380 | $8.26 | `5734` | medium |  |
| 368 | LAD | LITHIA MOTORS INC | 0001023128 | $8.12 | `5500` | low | needs a decision |
| 422 | GAP | GAP INC | 0000039911 | $7.26 | `5651` | high |  |
| 455 | AN | AUTONATION, INC. | 0000350698 | $6.78 | `5500` | low | needs a decision |
| 458 | VSXY | Victoria's Secret & Co. | 0001856437 | $6.69 | `5621` | medium |  |
| 471 | URBN | URBAN OUTFITTERS INC | 0000912615 | $6.56 | `5651` | high |  |
| 500 | CROX | Crocs, Inc. | 0001334036 | $6.23 | `3021` | high |  |

#### `utilities` &mdash; 13 candidates ($7.01 bn to $55.13 bn)

| # | ticker | company | CIK | market cap $bn | SIC | conf. | note |
|---:|---|---|---|---:|---|---|---|
| 16 | LNG | Cheniere Energy, Inc. | 0000003570 | $55.13 | `4924` | medium |  |
| 34 | VG | Venture Global, Inc. | 0002007855 | $34.38 | `4924` | medium | 2 10-Ks |
| 36 | CQP | Cheniere Energy Partners, L.P. | 0001383650 | $32.74 | `4924` | medium |  |
| 114 | TLN | Talen Energy Corp | 0001622536 | $17.10 | `4911` | high |  |
| 229 | WTRG | Essential Utilities, Inc. | 0000078128 | $11.29 | `4941` | medium |  |
| 281 | OGE | OGE ENERGY CORP. | 0001021635 | $9.78 | `4911` | high |  |
| 301 | EAI | ENTERGY ARKANSAS, LLC | 0000007323 | $9.24 | `4911` | high |  |
| 366 | IDA | IDACORP INC | 0001057877 | $8.18 | `4911` | high |  |
| 367 | OKLO | Oklo Inc. | 0001849056 | $8.16 | `4911` | high |  |
| 386 | NFG | NATIONAL FUEL GAS CO | 0000070145 | $7.78 | `4924` | medium |  |
| 401 | UGI | UGI CORP /PA/ | 0000884614 | $7.53 | `4932` | medium |  |
| 437 | CWEN | Clearway Energy, Inc. | 0001567683 | $7.01 | `4911` | high |  |
| 438 | ORA | ORMAT TECHNOLOGIES, INC. | 0001296445 | $7.01 | `4911` | high |  |

#### `leisure` &mdash; 12 candidates ($6.25 bn to $26.91 bn)

| # | ticker | company | CIK | market cap $bn | SIC | conf. | note |
|---:|---|---|---|---:|---|---|---|
| 50 | QSR | Restaurant Brands International Inc. | 0001618756 | $26.91 | `5812` | high |  |
| 113 | H | Hyatt Hotels Corp | 0001468174 | $17.11 | `7011` | high |  |
| 124 | ARMK | Aramark | 0001584509 | $16.25 | `5812` | high |  |
| 128 | YUMC | Yum China Holdings, Inc. | 0001673358 | $16.10 | `5812` | high |  |
| 170 | TXRH | Texas Roadhouse, Inc. | 0001289460 | $13.42 | `5812` | high |  |
| 263 | EAT | BRINKER INTERNATIONAL, INC | 0000703351 | $10.37 | `5812` | high |  |
| 272 | LTH | Life Time Group Holdings, Inc. | 0001869198 | $10.13 | `7997` | medium |  |
| 330 | BROS | Dutch Bros Inc. | 0001866581 | $8.81 | `5810` | medium |  |
| 358 | CAVA | CAVA GROUP, INC. | 0001639438 | $8.30 | `5812` | high |  |
| 408 | KEX | KIRBY CORP | 0000056047 | $7.45 | `4400` | high |  |
| 467 | MATX | Matson, Inc. | 0000003453 | $6.58 | `4400` | high |  |
| 497 | CHDN | Churchill Downs Inc | 0000020212 | $6.25 | `7948` | medium |  |

#### `insurance_pc` &mdash; 12 candidates ($6.24 bn to $22.29 bn)

| # | ticker | company | CIK | market cap $bn | SIC | conf. | note |
|---:|---|---|---|---:|---|---|---|
| 71 | MKL | MARKEL GROUP INC. | 0001096343 | $22.29 | `6331` | high |  |
| 169 | CNA | CNA FINANCIAL CORP | 0000021175 | $13.53 | `6331` | high |  |
| 173 | RNR | RENAISSANCERE HOLDINGS LTD | 0000913144 | $13.23 | `6331` | high |  |
| 176 | FNF | Fidelity National Financial, Inc. | 0001331875 | $13.18 | `6361` | medium |  |
| 201 | AFG | AMERICAN FINANCIAL GROUP INC | 0001042046 | $12.16 | `6331` | high |  |
| 268 | ORI | OLD REPUBLIC INTERNATIONAL CORP | 0000074260 | $10.26 | `6351` | medium |  |
| 352 | KNSL | Kinsale Capital Group, Inc. | 0001669162 | $8.36 | `6331` | high |  |
| 388 | THG | HANOVER INSURANCE GROUP, INC. | 0000944695 | $7.73 | `6331` | high |  |
| 406 | FAF | First American Financial Corp | 0001472787 | $7.47 | `6361` | medium |  |
| 421 | AXS | AXIS CAPITAL HOLDINGS LTD | 0001214816 | $7.29 | `6331` | high |  |
| 489 | MTG | MGIC INVESTMENT CORP | 0000876437 | $6.38 | `6351` | medium |  |
| 498 | ESNT | Essent Group Ltd. | 0001448893 | $6.24 | `6351` | medium |  |

#### `health_services` &mdash; 11 candidates ($6.68 bn to $45.29 bn)

| # | ticker | company | CIK | market cap $bn | SIC | conf. | note |
|---:|---|---|---|---:|---|---|---|
| 22 | NTRA | Natera, Inc. | 0001604821 | $45.29 | `8071` | high |  |
| 76 | GH | Guardant Health, Inc. | 0001576280 | $21.70 | `8071` | high |  |
| 83 | THC | TENET HEALTHCARE CORP | 0000070318 | $21.30 | `8062` | high |  |
| 206 | EHC | Encompass Health Corp | 0000785161 | $12.03 | `8060` | medium |  |
| 208 | BTSG | BrightSpring Health Services, Inc. | 0001865782 | $11.95 | `8082` | medium |  |
| 251 | MOH | MOLINA HEALTHCARE, INC. | 0001179929 | $10.60 | `6324` | high |  |
| 252 | ENSG | ENSIGN GROUP, INC | 0001125376 | $10.58 | `8051` | medium |  |
| 283 | OSCR | Oscar Health, Inc. | 0001568651 | $9.74 | `6324` | high |  |
| 436 | PACS | PACS Group, Inc. | 0002001184 | $7.02 | `8051` | medium | 2 10-Ks |
| 446 | CHE | CHEMED CORP | 0000019584 | $6.86 | `8082` | medium |  |
| 461 | HIMS | Hims & Hers Health, Inc. | 0001773751 | $6.68 | `8011` | medium |  |

#### `consumer_staples` &mdash; 10 candidates ($6.53 bn to $23.50 bn)

| # | ticker | company | CIK | market cap $bn | SIC | conf. | note |
|---:|---|---|---|---:|---|---|---|
| 67 | USFD | US Foods Holding Corp. | 0001665918 | $23.50 | `5140` | low | needs a decision |
| 122 | PFGC | Performance Food Group Co | 0001618673 | $16.44 | `5141` | medium |  |
| 250 | DAR | DARLING INGREDIENTS INC. | 0000916540 | $10.68 | `2070` | high |  |
| 325 | SFD | SMITHFIELD FOODS INC | 0000091388 | $8.90 | `2011` | medium |  |
| 329 | PRMB | Primo Brands Corp | 0002042694 | $8.82 | `2080` | high | 2 10-Ks |
| 396 | CELH | Celsius Holdings, Inc. | 0001341766 | $7.58 | `2086` | medium |  |
| 403 | SFM | Sprouts Farmers Market, Inc. | 0001575515 | $7.52 | `5411` | medium |  |
| 426 | LW | Lamb Weston Holdings, Inc. | 0001679273 | $7.22 | `2030` | medium |  |
| 447 | PPC | PILGRIMS PRIDE CORP | 0000802481 | $6.85 | `2015` | medium |  |
| 474 | INGR | Ingredion Inc | 0001046257 | $6.53 | `2040` | medium |  |

#### `insurance_life` &mdash; 7 candidates ($8.55 bn to $16.13 bn)

| # | ticker | company | CIK | market cap $bn | SIC | conf. | note |
|---:|---|---|---|---:|---|---|---|
| 126 | RGA | REINSURANCE GROUP OF AMERICA INC | 0000898174 | $16.13 | `6311` | high |  |
| 144 | CRBG | Corebridge Financial, Inc. | 0001889539 | $14.79 | `6311` | high |  |
| 149 | UNM | Unum Group | 0000005513 | $14.49 | `6321` | high |  |
| 290 | PRI | Primerica, Inc. | 0001475922 | $9.54 | `6311` | high |  |
| 310 | VOYA | Voya Financial, Inc. | 0001535929 | $9.07 | `6311` | high |  |
| 315 | JXN | Jackson Financial Inc. | 0001822993 | $9.02 | `6311` | high |  |
| 344 | LNC | LINCOLN NATIONAL CORP | 0000059558 | $8.55 | `6311` | high |  |

#### `telecom_cable` &mdash; 6 candidates ($6.79 bn to $26.87 bn)

| # | ticker | company | CIK | market cap $bn | SIC | conf. | note |
|---:|---|---|---|---:|---|---|---|
| 51 | ECHO | EchoStar CORP | 0001415404 | $26.87 | `4899` | medium | in the exclusion record |
| 66 | ROKU | ROKU, INC | 0001428439 | $23.50 | `4841` | medium | needs a decision |
| 82 | ASTS | AST SpaceMobile, Inc. | 0001780312 | $21.33 | `4899` | medium |  |
| 233 | VSAT | VIASAT INC | 0000797721 | $11.21 | `4899` | medium |  |
| 247 | GSAT | Globalstar, Inc. | 0001366868 | $10.76 | `4899` | medium |  |
| 454 | LUMN | Lumen Technologies, Inc. | 0000018926 | $6.79 | `4813` | high |  |

#### `energy_integrated` &mdash; 5 candidates ($6.67 bn to $67.07 bn)

| # | ticker | company | CIK | market cap $bn | SIC | conf. | note |
|---:|---|---|---|---:|---|---|---|
| 12 | IMO | IMPERIAL OIL LTD | 0000049938 | $67.07 | `2911` | medium | needs a decision |
| 38 | FTI | TechnipFMC plc | 0001681459 | $31.30 | `3533` | medium |  |
| 324 | PBF | PBF Energy Inc. | 0001534504 | $8.90 | `2911` | medium | needs a decision |
| 390 | NOV | NOV Inc. | 0001021860 | $7.70 | `3533` | medium |  |
| 463 | WFRD | Weatherford International plc | 0001603923 | $6.67 | `3533` | medium |  |

#### `homebuilder` &mdash; 5 candidates ($6.47 bn to $24.48 bn)

| # | ticker | company | CIK | market cap $bn | SIC | conf. | note |
|---:|---|---|---|---:|---|---|---|
| 64 | PHM | PULTEGROUP INC/MI/ | 0000822416 | $24.48 | `1531` | medium | in the exclusion record |
| 117 | NVR | NVR INC | 0000906163 | $16.79 | `1531` | medium | in the exclusion record |
| 168 | TOL | Toll Brothers, Inc. | 0000794170 | $13.60 | `1531` | medium |  |
| 413 | ECG | Everus Construction Group, Inc. | 0002015845 | $7.32 | `1531` | medium | 2 10-Ks |
| 476 | IBP | Installed Building Products, Inc. | 0001580905 | $6.47 | `1520` | medium |  |

#### `media` &mdash; 5 candidates ($9.72 bn to $12.56 bn)

| # | ticker | company | CIK | market cap $bn | SIC | conf. | note |
|---:|---|---|---|---:|---|---|---|
| 196 | DKNG | DraftKings Inc. | 0001883685 | $12.56 | `7990` | medium |  |
| 255 | NYT | NEW YORK TIMES CO | 0000071691 | $10.53 | `2711` | high |  |
| 277 | MSGS | Madison Square Garden Sports Corp. | 0001636519 | $9.92 | `7990` | medium |  |
| 278 | SIRI | SIRIUS XM HOLDINGS INC. | 0000908937 | $9.82 | `4832` | medium |  |
| 284 | LLYVK | Liberty Live Holdings, Inc. | 0002078416 | $9.72 | `7900` | high | 1 10-K |

#### `marketplace` &mdash; 2 candidates ($6.38 bn to $24.70 bn)

| # | ticker | company | CIK | market cap $bn | SIC | conf. | note |
|---:|---|---|---|---:|---|---|---|
| 63 | XPO | XPO, Inc. | 0001166003 | $24.70 | `4700` | high |  |
| 490 | GATX | GATX CORP | 0000040211 | $6.38 | `4700` | high |  |

#### `railroads` &mdash; 1 candidates ($82.56 bn to $82.56 bn)

| # | ticker | company | CIK | market cap $bn | SIC | conf. | note |
|---:|---|---|---|---:|---|---|---|
| 8 | CP | CANADIAN PACIFIC KANSAS CITY LTD/CN | 0000016875 | $82.56 | `4011` | high |  |

#### `materials_integrated` &mdash; 1 candidates ($19.85 bn to $19.85 bn)

| # | ticker | company | CIK | market cap $bn | SIC | conf. | note |
|---:|---|---|---|---:|---|---|---|
| 92 | CDE | Coeur Mining, Inc. | 0000215466 | $19.85 | `1040` | medium |  |

#### `airline` &mdash; 1 candidates ($9.55 bn to $9.55 bn)

| # | ticker | company | CIK | market cap $bn | SIC | conf. | note |
|---:|---|---|---|---:|---|---|---|
| 288 | AAL | American Airlines Group Inc. | 0000006201 | $9.55 | `4512` | high |  |


---

## 6. The needs-a-human-decision list

**125 of the 500.** Three sources: SIC codes the universe itself splits, low-confidence
assignments, and structural categories SIC cannot see at all. The last group is the
interesting one.

### 6.1 SIC codes where the universe splits

The mapping picks the plurality and flags the candidate. These are not mapping errors —
they are codes where SIC does not carry the distinction the profile encodes.

| SIC | description | candidates | how the universe splits | assigned | example tickers |
|---|---|---:|---|---|---|
| `7372` | Services-Prepackaged Software | 36 | standard x16, media x2, pharma_medtech x1 | `standard` | SHOP, SNOW, NET, CRWV, TEAM, MDB |
| `6199` | Finance Services | 10 | financial x3, standard x1 | `financial` | MSTR, CRCL, IREN, CHYM, BMNR, HUT |
| `1311` | Crude Petroleum & Natural Gas | 10 | energy x4, energy_integrated x2 | `energy` | PR, OVV, VNOM, APA, AR, RRC |
| `7389` | Services-Business Services, NEC | 8 | standard x12, marketplace x3, industrials x1 | `standard` | MELI, RBA, CART, HQY, Z, ETSY |
| `6282` | Investment Advice | 8 | standard x4, alt_asset_manager x4 | `standard` | TPG, OWL, CG, EVR, AMG, HLI |
| `5500` | Retail-Auto Dealers & Gasoline Stations | 7 | consumer_staples x1, industrials x1 | `retail` | CVNA, PAG, MUSA, RUSHA, KMX, LAD |
| `7370` | Services-Computer Programming, Data Processing, Etc. | 6 | standard x5, media x1 | `standard` | ZM, FLUT, DOCN, PINS, SNAP, MTCH |
| `7373` | Services-Computer Integrated Systems Design | 5 | standard x2, industrials x1 | `standard` | IOT, IONQ, CACI, AUR, LNWO |
| `3841` | Surgical & Medical Instruments & Apparatus | 4 | pharma_medtech x9, industrials x1 | `pharma_medtech` | MDLN, PEN, GMED, GKOS |
| `3823` | Industrial Instruments For Measurement, Display, and Control | 4 | industrials x2, standard x2, pharma_medtech x1 | `industrials` | MKSI, CGNX, RAL, ST |
| `6211` | Security Brokers, Dealers & Flotation Companies | 4 | financial x6, standard x1 | `financial` | SF, SEIC, JEF, FRHC |
| `3711` | Motor Vehicles & Passenger Car Bodies | 3 | captive_finance x3, industrials x1 | `industrials` | RIVN, OSK, FSS |
| `7374` | Services-Computer Processing & Data Preparation | 3 | industrials x2, standard x2 | `standard` | TOST, APLD, HNGE |
| `2911` | Petroleum Refining | 2 | energy_integrated x4, energy x2 | `energy_integrated` | IMO, PBF |
| `3312` | Steel Works, Blast Furnaces & Rolling Mills (Coke Ovens) | 2 | materials_integrated x1, materials x1 | `materials` | CRS, CMC |
| `2821` | Plastic Materials, Synth Resins & Nonvulcan Elastomers | 2 | materials_integrated x2, materials x1 | `materials` | EMN, HXL |
| `3560` | General Industrial Machinery & Equipment | 2 | industrials x2, standard x1 | `industrials` | ZWS, GTES |
| `4841` | Cable & Other Pay Television Services | 1 | telecom_cable x2, media x1 | `telecom_cable` | ROKU |
| `5140` | Wholesale-Groceries & Related Products | 1 | consumer_staples x1, leisure x1 | `consumer_staples` | USFD |
| `3829` | Measuring & Controlling Devices, NEC | 1 | pharma_medtech x1, industrials x1, standard x1 | `industrials` | ONTO |
| `7340` | Services-To Dwellings & Other Buildings | 1 | industrials x1, marketplace x1 | `industrials` | APG |
| `7320` | Services-Consumer Credit Reporting, Collection Agencies | 1 | standard x2, industrials x1 | `standard` | TRU |
| `3812` | Search, Detection, Navigation, Guidance, Aeronautical Sys | 1 | industrials x2, retail x1, standard x1 | `industrials` | DRS |


### 6.2 Structural categories SIC cannot see

**A digital-asset cluster that fits none of the 24 profiles.** SIC `6199` "Finance Services"
holds 10 candidates in the top 500, and **eight of them are bitcoin miners or digital-asset
treasury companies**: MSTR (#30), IREN (#129), BMNR (#228), HUT (#243), WULF (#333),
CIFR (#394), RIOT (#402), CORZ (#477) — with MARA (#804), CLSK (#904) and GLXY (#732) below
the cut, and APLD (#319) landing on `standard` from a different code. The mapping proposes
`financial` for them, which is the **bank** profile: it turns on interest income and net
interest margin. A company whose balance sheet is bitcoin and whose income statement is
electricity and hosting fees has neither. The other two 6199 candidates, CRCL (Circle) and
CHYM (Chime), are a stablecoin issuer and a neobank — also not banks in the profile's sense.

This is the cluster the brief asks about: **it fits none of the existing 24.** I am not
proposing a new profile, because that decision carries its own `PROFILE_HIDDEN` and
`PROFILE_CONCEPT_OVERRIDES` consequences. The finding is that admitting these twelve on
`financial` would produce twelve entries with an empty or meaningless financial panel.

**Mortgage REITs on an FFO profile.** NLY (Annaly) and AGNC both carry SIC `6798` and are
therefore proposed as `reit` with *high* confidence — 28 universe members share that code and
all 28 are `reit`. But the `reit` profile is built on FFO, which adds back real-estate
depreciation. A mortgage REIT owns loans and securities, not depreciable buildings; its FFO
is its net income, and the profile's central metric says nothing. The confidence score is
correct about the evidence and wrong about the company, which is exactly why this list exists.

**Master limited partnerships.** Six in the top 500: EPD (#7, $83bn), ET (#10), MPLX (#13),
CQP (#36), WES, PAA. They file 10-Ks with real financials, so nothing excludes them, but they
issue *units* rather than shares, distribute rather than pay dividends, and report per-unit
figures that are not EPS. Whether the `energy` profile's per-share metrics mean anything for
them is a judgement about the profile, not about SIC.

**Non-US companies that file 10-Ks.** 14 in the top 500 — SHOP, ENB, CP, CLS, TEVA, WCN, SN,
JHX, FLUT, CNH, IREN, SMMT, FRHC, SSRM (47 across all 1,571 survivors). Mechanically fine:
they file exactly what the pipeline reads. But "the next tier of **US** companies" does not
describe them, and admitting them is a scope decision.

**LNG exporters classed as gas utilities.** SIC `4924` "Natural Gas Distribution" produces
`utilities` for LNG (#16, Cheniere), VG (#34, Venture Global) and CQP (#36). Cheniere is a
liquefaction and export business on long-term contracts, not a rate-regulated distributor.
The fourth 4924 candidate, NFG, genuinely is a utility. One code, two businesses.

**Wholesale distributors.** 13 candidates in `5000`&ndash;`5099` are proposed as `industrials`
(FERG, RS, SNX, WCC, QXO, AIT, WSO, ARW, CNM, AVT, MSM, INGM, LKQ). The universe is itself
split here: `5000` is `industrials` (1 member) while `5013`, `5047`, `5090` and `5122` are all
`retail` (6 members). Distribution is one business; the universe treats it as two.

**A controlled company with almost no float.** SCCO (#2, $162bn) is ~89% owned by Grupo México.
The market cap is correct and the investable company is a tenth of it. Nothing in the pipeline
is wrong; it is worth knowing before it appears second in a peer comparison.

---

## 7. Candidates in the exclusion record

The brief expects the exclusion record to be commented-out entries in `TICKER_PROFILES`.
**There are none** — `grep -E '^\s*#\s*"[A-Z.-]{1,6}"\s*:' config.py` returns nothing. The
record exists, but as prose comments, and it does not work the way the comments imply.

Four tickers are described in `config.py` as staying on the **default profile**:

> `# CVNA is deliberately not on the retail profile: it was tried and the profile produced nothing usable for it.`
> `# PHM and NVR were tried on a homebuilder profile and it fitted both poorly; they stay on the default profile until that set is re-derived.`
> `# APA is deliberately not on the energy profile: it reports no Revenue, so the profile's revenue-based metrics would all be empty.`

**None of the four is in `TICKER_PROFILES`, so none of them is in the universe.**
`get_active_tickers()` returns `sorted(TICKER_PROFILES.keys())` and nothing else — there is no
mechanism by which a ticker absent from that dict receives `DEFAULT_PROFILE`. "They stay on the
default profile" reads as *still included, on `standard`*; the actual effect is *excluded*.
Whether that was the intent is the operator's call, but the comment and the behaviour disagree,
and someone re-deriving the homebuilder set from that comment would go looking for two tickers
that are not there.

All five appear in the candidate list:

| rank | ticker | company | market cap | proposed | recorded reason |
|---:|---|---|---:|---|---|
| 9 | CVNA | Carvana Co. | $77.1bn | `retail` (low) | "was tried and the profile produced nothing usable for it" — and the mapping proposes the same `retail` profile again, from SIC 5500, at *low* confidence |
| 51 | ECHO | EchoStar Corp | $26.9bn | `telecom_cable` | successor to the removed SATS; `config.py` calls adding it "a separate decision" |
| 64 | PHM | PulteGroup | $24.5bn | `homebuilder` | "tried on a homebuilder profile and it fitted both poorly" — the mapping proposes `homebuilder` again, from SIC 1531 |
| 117 | NVR | NVR Inc | $16.8bn | `homebuilder` | same |
| 147 | APA | APA Corp | $14.6bn | `energy` | "reports no Revenue, so the profile's revenue-based metrics would all be empty" |

Three of the five are proposed for **the same profile that was already tried and rejected**.
That is the mapping working correctly and being wrong: SIC says PulteGroup builds houses, and
the recorded objection is about how the profile's metrics behaved, which SIC cannot know.
If these enter the universe they should enter on `standard`, or the profiles should be
re-derived first.

**SATS** does not appear: the symbol no longer trades and is absent from `company_tickers.json`,
so it never entered the pool. The removal recorded on 2026-08-14 is holding.

---

## 8. Reading the top 50, and where the cutoff lands

### 8.1 The top 50

| # | ticker | company | market cap | SIC | proposed profile | conf. | 10-Ks |
|---:|---|---|---:|---|---|---|---:|
| 1 | SHOP | Shopify Inc. | $191bn | `7372` Services-Prepackaged Software | `standard` | medium | 2 |
| 2 | SCCO | Southern Copper Corp/ | $162bn | `1000` Metal Mining | `materials` | medium | 19 |
| 3 | SNOW | Snowflake Inc. | $114bn | `7372` Services-Prepackaged Software | `standard` | medium | 5 |
| 4 | ENB | Enbridge Inc | $110bn | `4610` Pipe Lines (No Natural Gas) | `energy` | medium | 9 |
| 5 | NET | Cloudflare, Inc. | $109bn | `7372` Services-Prepackaged Software | `standard` | medium | 6 |
| 6 | MELI | Mercadolibre Inc | $90.62bn | `7389` Services-Business Services, NEC | `standard` | medium | 19 |
| 7 | EPD | Enterprise Products Partners L.P. | $83.38bn | `4922` Natural Gas Transmission | `energy` | high | 13 |
| 8 | CP | Canadian Pacific Kansas City Ltd/Cn | $82.56bn | `4011` Railroads, Line-Haul Operating | `railroads` | high | 11 |
| 9 | CVNA | Carvana Co. | $77.07bn | `5500` Retail-Auto Dealers & Gasoline Stations | `retail` | low | 3 |
| 10 | ET | Energy Transfer LP | $72.10bn | `4922` Natural Gas Transmission | `energy` | high | 15 |
| 11 | BE | Bloom Energy Corp | $68.38bn | `3620` Electrical Industrial Apparatus | `industrials` | medium | 8 |
| 12 | IMO | Imperial Oil Ltd | $67.07bn | `2911` Petroleum Refining | `energy_integrated` | medium | 25 |
| 13 | MPLX | Mplx Lp | $59.90bn | `4610` Pipe Lines (No Natural Gas) | `energy` | medium | 10 |
| 14 | CRWV | CoreWeave, Inc. | $58.46bn | `7372` Services-Prepackaged Software | `standard` | medium | 1 |
| 15 | ALAB | Astera Labs, Inc. | $55.54bn | `3674` Semiconductors & Related Devices | `standard` | high | 2 |
| 16 | LNG | Cheniere Energy, Inc. | $55.13bn | `4924` Natural Gas Distribution | `utilities` | medium | 11 |
| 17 | CRDO | Credo Technology Group Holding Ltd | $52.74bn | `3674` Semiconductors & Related Devices | `standard` | high | 5 |
| 18 | RKLB | Rocket Lab Corp | $52.47bn | `3760` Guided Missiles & Space Vehicles & Parts | `industrials` | medium | 6 |
| 19 | HEI | Heico Corp | $51.88bn | `3724` Aircraft Engines & Engine Parts | `industrials` | high | 17 |
| 20 | FERG | Ferguson Enterprises Inc. /DE/ | $47.39bn | `5070` Wholesale-Hardware & Plumbing & Heating Equipment & Supplies | `industrials` | medium | 2 |
| 21 | RVMD | Revolution Medicines, Inc. | $45.44bn | `2836` Biological Products, (No Diagnostic Substances) | `pharma_medtech` | high | 7 |
| 22 | NTRA | Natera, Inc. | $45.29bn | `8071` Services-Medical Laboratories | `health_services` | high | 4 |
| 23 | CLS | Celestica Inc | $42.93bn | `3672` Printed Circuit Boards | `standard` | high | 2 |
| 24 | TEVA | Teva Pharmaceutical Industries Ltd | $42.49bn | `2834` Pharmaceutical Preparations | `pharma_medtech` | high | 9 |
| 25 | WCN | Waste Connections, Inc. | $41.51bn | `4953` Refuse Systems | `industrials` | high | 10 |
| 26 | RKT | Rocket Companies, Inc. | $41.06bn | `6162` Mortgage Bankers & Loan Correspondents | `financial` | medium | 6 |
| 27 | ONC | BeOne Medicines Ltd. | $41.01bn | `2834` Pharmaceutical Preparations | `pharma_medtech` | high | 8 |
| 28 | TEAM | Atlassian Corp | $40.08bn | `7372` Services-Prepackaged Software | `standard` | medium | 2 |
| 29 | P | Everpure, Inc. | $38.89bn | `3572` Computer Storage Devices | `standard` | high | 11 |
| 30 | MSTR | Strategy Inc | $38.81bn | `6199` Finance Services | `financial` | medium | 6 |
| 31 | UI | Ubiquiti Inc. | $35.32bn | `3663` Radio & Tv Broadcasting & Communications Equipment | `standard` | high | 14 |
| 32 | MDB | MongoDB, Inc. | $35.29bn | `7372` Services-Prepackaged Software | `standard` | medium | 7 |
| 33 | TWLO | Twilio Inc | $35.11bn | `7372` Services-Prepackaged Software | `standard` | medium | 7 |
| 34 | VG | Venture Global, Inc. | $34.38bn | `4924` Natural Gas Distribution | `utilities` | medium | 2 |
| 35 | SUNB | Sunbelt Rentals Holdings, Inc. | $34.08bn | `7359` Services-Equipment Rental & Leasing, NEC | `industrials` | medium | 1 |
| 36 | CQP | Cheniere Energy Partners, L.P. | $32.74bn | `4924` Natural Gas Distribution | `utilities` | medium | 19 |
| 37 | ATI | Ati Inc | $31.56bn | `3317` Steel Pipe & Tubes | `materials` | medium | 12 |
| 38 | FTI | TechnipFMC plc | $31.30bn | `3533` Oil & Gas Field Machinery & Equipment | `energy_integrated` | medium | 10 |
| 39 | ZM | Zoom Communications, Inc. | $30.95bn | `7370` Services-Computer Programming, Data Processing, Etc. | `standard` | medium | 7 |
| 40 | MDLN | Medline Inc. | $30.60bn | `3841` Surgical & Medical Instruments & Apparatus | `pharma_medtech` | medium | 1 |
| 41 | ALNY | Alnylam Pharmaceuticals, Inc. | $30.05bn | `2834` Pharmaceutical Preparations | `pharma_medtech` | high | 12 |
| 42 | ZS | Zscaler, Inc. | $29.83bn | `7371` Services-Computer Programming Services | `standard` | high | 8 |
| 43 | ILMN | Illumina, Inc. | $29.16bn | `3826` Laboratory Analytical Instruments | `pharma_medtech` | high | 8 |
| 44 | LPLA | LPL Financial Holdings Inc. | $28.99bn | `6200` Security & Commodity Brokers, Dealers, Exchanges & Services | `standard` | high | 10 |
| 45 | NVT | nVent Electric plc | $28.68bn | `3550` Special Industry Machinery (No Metalworking Machinery) | `industrials` | medium | 8 |
| 46 | CPNG | Coupang, Inc. | $28.26bn | `5961` Retail-Catalog & Mail-Order Houses | `standard` | high | 5 |
| 47 | INSM | INSMED Inc | $28.02bn | `2834` Pharmaceutical Preparations | `pharma_medtech` | high | 9 |
| 48 | RBLX | Roblox Corp | $27.10bn | `7372` Services-Prepackaged Software | `standard` | medium | 4 |
| 49 | CRS | Carpenter Technology Corp | $26.95bn | `3312` Steel Works, Blast Furnaces & Rolling Mills (Coke Ovens) | `materials` | low | 13 |
| 50 | QSR | Restaurant Brands International Inc. | $26.91bn | `5812` Retail-Eating  Places | `leisure` | high | 8 |


### 8.2 What is right, and what I would question

Nothing structurally wrong survived to this table: **no ETF, no foreign private issuer, no
double-counted share class, no fund.** The first pass of this table had all four, and fixing
them is what sections 1.4, 2 and 4.3 are about.

Points I would raise with the operator:

- **#29 `P` "Everpure, Inc."** is **Pure Storage**, renamed and re-tickered from PSTG.
  `formerNames` in `submissions.json` reads `PURE Storage, Inc.` &rarr; `Pure Storage, Inc.`
  &rarr; `Os76, Inc.`. Fine as a candidate; worth noticing that a top-30 name changed both its
  identity and its symbol, which is the same class of event as the SATS/ECHO and XOM cases
  already in `ticker_resolution_report.md`.
- **Six of the top 40 are recent listings** — CRWV (#14, 1 10-K), SUNB (#35, 1), MDLN (#40, 1),
  FERG (#20, 2), VG (#34, 2), TEAM (#28, 2). Large, real, and with too little filed history
  for a 15-year chart.
- **#2 SCCO** — the float issue in 6.2.
- **#7, #10, #13, #36** are the MLPs.
- **#4, #8, #12, #23, #24, #25** are non-US 10-K filers.
- **#9 CVNA** is in the exclusion record and is proposed for the profile that was rejected.
- **#16 LNG, #34 VG, #36 CQP** are the LNG exporters called `utilities`.
- **#30 MSTR** heads the digital-asset cluster.

The one entry I cannot place from the data alone is **#11 BE (Bloom Energy, $68bn)** at SIC
`3620` — plausible as `industrials`, but a fuel-cell manufacturer at that valuation is worth
a look before it lands in an industrials peer group.

### 8.3 Where the cutoff lands, and the overlap

| | |
|---|---|
| candidate #500 | **CROX (Crocs), $6.231bn** |
| candidate #501 | HOMB, $6.224bn — the boundary is not a gap, it is a continuum |
| smallest company already in the universe | **CE, $4.92bn** |
| universe members below the candidate cutoff | **1 of 500** (CE) |
| candidates above the smallest universe member | **500 of 500** |
| candidates above the universe *median* ($45.9bn) | **20** |

**The overlap is the finding.** "The next 500 by size" turns out to be almost entirely *above*
the bottom of the current universe, not below it, and twenty candidates outrank half of it.
Shopify at $191bn would be a top-40 name in the existing universe; Southern Copper at $162bn,
Enbridge at $111bn and Cloudflare at $109bn would all be top-50.

That is not an error in the ranking, and it is worth stating plainly: **the S&P 500 is not a
market-cap ranking.** It applies a US-domicile requirement (which excludes Shopify, Enbridge,
Canadian Pacific), a public-float requirement (which excludes Southern Copper at ~11% float),
a positive-earnings requirement, and a committee's sector-balance judgement. Everything large
that those criteria exclude lands in this list. So the proposed 500 is better described as
*"the largest US-listed 10-K filers that the S&P 500 does not contain"* than as *"companies
smaller than the current universe"*, and roughly the first fifty of them are large-cap
companies by any measure.

The practical consequence: doubling the universe this way does **not** mean doubling it with
small caps. The size distribution of the combined 1,000 would be smoother than the current
one, not shifted down.

---

## 9. Found, and deliberately not acted on

**`config.py` was not touched.** No profile assignment, no `CIK_OVERRIDES` entry, no
`PROFILE_HIDDEN` line. The four comment-record tickers were not added, removed or re-worded.

**ExxonMobil's successor registrant is now visible in the data.** CIK `0002115436`,
"ExxonMobil Holdings Corp", SIC 2911, appears in the pool with a stage-1 market cap of $658bn,
**zero 10-Ks and a 10-Q filed 2026-08-03**. It is excluded from the candidate list by the
"no 10-K yet" rule, correctly. But it confirms what `ticker_resolution_report.md` recorded as
a stopgap: the `CIK_OVERRIDES` pin on `0000034088` holds the universe on the predecessor, and
the successor is where new filings are now going. The report's own note — revisit before XOM
is more than two quarters behind — has a date attached to it now: the successor has filed one
10-Q and will file its first 10-K in early 2027. I did not change the override; that is the
carried-forward item, not this task.

**Electronic Arts has left `company_tickers.json`, and it is still in the universe.** This
surfaced from the funnel: 499 of the 500 universe symbols resolve to a CIK, and the one that
does not is **`EA`**. It is not a lookup quirk. EA's own `submissions.json` (CIK `0000712515`)
shows a **`25-NSE` filed 2026-08-04** (removal from listing) and a **`15-12G` filed 2026-08-14**
(termination of registration), after a run of S-8 deregistrations on 2026-08-04 and a
`SCHEDULE 13D/A` on 2026-08-05 — the signature of a completed take-private. Yahoo serves five
price rows for the last month, the newest dated **2026-08-10 at $209.70**, and
`data/current_snapshot.csv` from the 2026-08-14 run records exactly that stale $209.70 and a
$52.9bn market cap.

This is the SATS pattern again, one week later, on a member ten times the size. Two things
follow, and neither is this task's to do:

- The nightly run will now report it rather than fail on it. `main.resolve_cik_mapping()`
  raises for an unresolvable ticker, `run_full_refresh` catches it into `unresolved_tickers`,
  prints `WARNUNG: 1 von 500 Tickern nicht auflösbar: EA`, and
  `write_full_refresh_report` puts it under "Unresolvable tickers". That is cycle 30's work
  doing precisely what it was built for, on a case it did not know about.
- EA needs the SATS decision: remove it from `TICKER_PROFILES` with the reason recorded, rather
  than pin a `CIK_OVERRIDES` entry that would keep a delisted symbol in the universe on a
  frozen price. I did not make that change — `config.py` is out of scope here.

**A 1,000&times; unit-scaling defect in `WeightedAverageNumberOfDilutedSharesOutstanding`.**
TBLA, RPAY and MODD tag share counts in thousands against the `shares` unit. The pipeline uses
yfinance for share counts, so it is not currently exposed — but the same filers' *other*
tagged values are worth suspicion if any of them are admitted. Not investigated further; that
is per-category work.

**The three duplicated CIKs in the current universe** (FOX/FOXA, GOOG/GOOGL, NWS/NWSA) were
found while deriving the share-class rule. They are pre-existing and deliberate-looking, and
correcting them is not this task's scope.

**No new profile was created**, and no candidate was assigned one that does not exist. The
digital-asset cluster in 6.2 is reported as a gap, not filled.

**Data quality was not assessed.** The brief excludes it and it is the next effort: whether a
candidate's XBRL is dense enough to populate its proposed profile is a per-category question,
and the grouped table in 5.2 is ordered to be worked through that way. What I *can* say is
that the 29 companies whose two market-cap measures disagree by more than 2&times; have a
demonstrated tagging defect, and are a sensible place for that work to start.

**Nothing was left behind.** All scripts, caches and intermediate CSVs were written outside the
repository and deleted. This file is the only addition.
