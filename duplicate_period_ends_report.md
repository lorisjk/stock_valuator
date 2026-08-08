# Duplicated Period Ends — the `(end, days)` Key

**Task:** a filer that tags one reporting period twice, a few days apart, gets two rows.
`extract_period_values` keys on `(end, days)` and `decumulate_period_values` keys on `end`, so both
survive: the same quarter appears twice in the data tab, and `calculate_ttm`'s step rule correctly
refuses every window that steps across the pair.

Measured over all 501 cached tickers: **503,581 consecutive period pairs** across 35 concepts.
Every figure below comes from the local cache through the pipeline's own functions; no refresh was
run.

---

## 1. The duplicate population

### 1.1 The gap distribution — and there is no empty run

```
   1   334  ############################################################
   2   136  ########################
   3   114  ####################
   4    46  ########
   5    23  ####
   6    52  #########
   7    15  ##
   8     1
   9     9  #
  10     3
  ...
  27    16  ##
  28    70  ############
  29    12  ##
  30    72  ############
  31    86  ###############
  32    10  #
  ...
```

**The only empty runs between 1 and 120 days are 67–68 (2 wide) and 99–109 (11 wide)** — both far
above the population. Unlike the TTM window and the decumulation window, **the threshold cannot
come from a gap in the distribution.** That is the finding, and it forced the rule to be justified
differently.

What the distribution does show is a **second population at 28–31 days (240 pairs)** — periods a
month apart, which are genuinely different dates (KDP's 2015-12-04 and 2015-12-31, MTB's 2011-05-31
and 2011-06-30, fiscal-year changes and acquisition stubs). Any threshold must stay well below it.

**The bound comes from the mechanism instead.** A 52/53-week filer's period ends on a chosen weekday
nearest the month end, so a fiscal end can sit at most **six days** from the corresponding calendar
end. Seven days covers the mechanism with a day to spare and leaves the 28–31 day population
untouched. The data agrees: 435 of the 461 value-identical pairs fall at a gap of ≤ 7, and the next
one is at 9.

### 1.2 How often the two values agree — and why that is the wrong test

At gap ≤ 7 there are **720 pairs**:

```
  identical to the cent      435   (60.4%)
  within 0.1%                 22
  differ by more             263
```

The three examples in the task brief are identical to the cent, which suggests value agreement as
the discriminator. **Measured, it fails in both directions.**

It admits things it should not: at gap ≤ 30 only 47.9% agree, and the disagreements include
VTRS 0 → 2,619m, MTB 0 → 3,524m, JCI 0 of 46 pairs identical — Viatris' formation, M&T's
acquisition, Johnson Controls' Tyco merger. Those are not duplicates.

And it rejects things it should not, which is the more interesting half:

```
MSI Revenue   2010-04-01 -> 2010-06-30    1,936,000,000
              2010-04-04 -> 2010-07-03    1,869,000,000     3.5% apart
```

That is one quarter under two calendars, offset by three days. **Three days out of ninety is 3.3%
— the difference is exactly the offset**, not evidence of two periods. The same shape appears in
WAT (0.17%), LMT (0.3%), TER, CAH, CAG, DHR. A value tolerance tight enough to exclude the mergers
would leave half the duplicates in place.

Structural signals fare no better. Tested at fact level over 1,101 near-end pairs: **"same start"**
identifies 139 of 400 duplicates and produces 32 false positives; **"start shifted by the same
amount as the end"** adds 64. **197 duplicates have neither**, because both ends move under the two
calendars:

```
CHD  Revenue  2010-07-01 -> 2010-09-30  (91d)   and  2010-07-03 -> 2010-10-01  (90d)
CIEN Revenue  2019-11-01 -> 2020-01-31  (91d)   and  2019-11-03 -> 2020-02-01  (90d)
```

### 1.3 What distinguishes the two ends: nothing systematic

Neither end is systematically the filer's real boundary. Accenture's fiscal Q2 2012 ended on the
**leap day, 2012-02-29** — the later twin. Waters' fiscal Q2 2024 ended Saturday **2024-06-29** —
the earlier twin. Across the 457 pairs the later end is a calendar month end 183 times and the
earlier end 238 times.

The step-ladder test is equally mute. Measuring the step into and out of each twin:

```
  keep the EARLIER end:  step in quarter-length 419/452   step out 429/457
  keep the LATER end:    step in quarter-length 419/452   step out 429/457
```

Identical, because most gaps are 1–3 days and both choices leave a 90-ish day step.

### 1.4 The coverage prize

```
  TTM windows formed:                              334,291
  rejected by the calendar test today:              14,135
  rejected AND containing a step of <= 7 days:         960     over 32 tickers
```

WAT 218, CIEN 107, DE 69, JCI 66, TER 63, MSI 37, TSN 36, ON 34, TAP 34, LMT 30, J 28, KDP 27.

---

## 2. The merge rule

> Within one `(ticker, concept)` series, period ends **within 7 days of each other** are one
> period. **The later end survives**, with its own value.

### Which end, and why the later one

The ladder test is neutral (419/452 either way), so the decision falls to a property the ladder
cannot see: **the anchor invariant**, which has held through six tasks. Keeping the later end can
only leave a series' newest period where it is or move it forward; keeping the earlier end can move
it backwards. That is the whole argument, and it is the reason the choice is not arbitrary.

*Failure mode:* the surviving end is sometimes the calendar end where the fiscal end was the real
boundary (Waters). Measured consequence: none on the step ladder — WAT's steps run 88–94 days
afterwards, all comfortably inside `calculate_ttm`'s 76–137 band. A second consequence did appear
and is named in section 4: two concepts of the same ticker can end up on different calendars if
only one of them carries the twin.

### Which value, and what to do when they differ

The surviving end keeps its own value. Since the disagreement between twins **is** the calendar
offset, picking the later end's value is picking the value that belongs to the later end — not a
choice between two candidates for the same number.

Where the difference is large, the merge is an improvement rather than a risk. Every one of the 721
removed rows was checked against its survivor:

```
  removed rows with a survivor within 7 days:  721 of 721
  identical value                              433
  within 1%                                    494
  removed value was exactly 0                   12
```

The largest disagreements are pre-combination placeholders that the merge deletes:

```
VTRS  Revenue             2020-09-27          0  ->  2020-09-30   2,948,100,000
JCI   StockRepurchased    2016-06-24          0  ->  2016-06-30     475,000,000
VLTO  SharesOutstanding   2022-10-25          0  ->  2022-10-26     246,300,000
ROP   Goodwill            2021-12-30  138,800,000 -> 2021-12-31  13,476,300,000
```

*Failure mode:* if a filer ever tagged two genuinely distinct periods 7 days apart, the earlier
would be dropped. No such case was found; the nearest genuine pairs sit at 28–31 days.

### Where the fix lives, and why not in the key

**In `parse_edgar.build_dataframe`, immediately after `extract_with_mode`** — not in the
`(end, days)` key.

Changing the key was the first design and it does not work, for a measurable reason: **decumulation
regenerates the twin.** Waters tags the same quarter as `2024-03-31 → 2024-06-29` and
`2024-04-01 → 2024-06-30`. Those have different starts, so `decumulate_period_values` puts them in
different year-to-date groups and each emits a quarter at its own end. Collapsing them inside
`extract_period_values` leaves the fiscal end arriving from the year-to-date ladder and the
calendar end from the discrete quarterly fact — two rows again.

Placing the pass after `extract_with_mode` also puts it after the tag merge, so a twin contributed
by one tag and its partner by another are caught too. And it leaves `extract_period_values`
untouched, which matters: the decumulation report established that the key's
shorter-duration-wins preference is load-bearing (the COST `SharesOutstanding` case). **That block
is unchanged and its behaviour is unchanged** — COST's fiscal-year-end share counts are identical
before and after.

### Point-in-time versus duration

The pass runs on the final per-concept series, where every entry is already one `(end, value)` row
regardless of how it was produced, so both paths are handled by the same code and **a merged
instant cannot acquire a duration** — there is no duration to acquire at that point. The population
splits almost evenly: of the 439 value-identical pairs at gap ≤ 10, **234 are duration concepts and
190 point-in-time**. Weighted-average share counts (`SharesOutstanding`, 76 rows removed) and
balance items (`CashAndEquivalents` 110, `StockholdersEquity` 94, `Goodwill` 45) are as affected as
the flows.

---

## 3. What was implemented

`parsers/parse_edgar.py`: `merge_duplicate_period_ends(values)`, one linear pass over the
end-sorted series keeping the later of any two ends within `_DUPLICATE_END_MAX_GAP = 7` days,
applied to every concept's values and to the annual-fact TTM path. Nothing else changed.

Behaviour on the edge cases, checked directly:

```
  six ends 2024-03-30/31, 06-29/30, 09-28, 12-31   ->  03-31, 06-30, 09-28, 12-31
  a chain of three within 7 days (ADI 01-29/02-01/02-04) ->  02-04
  a month apart (2015-12-04, 2015-12-31)           ->  both kept
  empty and single-element series                  ->  returned unchanged
```

---

## 4. Non-regression, all 501 tickers

### Base facts

```
512,799 -> 512,078 rows     removed 721     added 0
```

**721 removed, every one mapped to a specific merged pair with a surviving partner within 7 days.**
The population is wider than the task's brief suggested — **136 tickers, not 33** (the 33 came from
the TTM report's narrower measurement over TTM concepts only):

| removals per ticker | tickers |
|---|---:|
| 1 | 58 |
| 2 | 26 |
| 3–5 | 31 |
| 6–10 | 6 |
| 11–25 | 8 |
| 26–50 | 5 |
| 51+ | 2 (WAT 109, CIEN 51) |

By concept: CashAndEquivalents 110, StockholdersEquity 94, Revenue 84, NetIncomeLoss 79,
SharesOutstanding 76, OperatingIncomeLoss 52, Goodwill 45, PretaxIncome 38, IncomeTaxExpense 31,
LongTermDebt 24, DepreciationAndAmortization 17, ResearchAndDevelopment 14, and eight more.

### The full frame

| frame | appeared | changed | disappeared |
|---|---:|---:|---:|
| facts | 1,091 | **0** | 1,222 |
| metrics_long | 1,918 | 28 | 841 |
| valuation_history | 600 | 62 | 540 |
| snapshot | 18 | 56 | **0** |
| duplicates on `(ticker, concept, end)` | — | — | **0** |

**Not one fact value changed.** The 1,222 disappearances account exactly:

```
   720  base-concept rows (the merged twins)
 +   502  derived rows that stood on them
        TangibleEquity 96, EPS_QUARTERLY_CALC 78, EPS_TTM_CALC 41, FFO_QUARTERLY 40,
        Revenue_TTM 35, NetIncomeLoss_TTM 35, EBITDA_QUARTERLY 30, OperatingIncomeLoss_TTM 24,
        PretaxIncome_TTM 19, IncomeTaxExpense_TTM 17, FFO_TTM 13, EBITDA_TTM 12,
        FCF_QUARTERLY 9, and nine more
 = 1,222
```

(The 721st removed base row is an annual-fact `_TTM` row, which appears among the derived counts.)

**The 1,091 appeared are all `_TTM` and derived — the recovered windows:** Revenue_TTM 159,
NetIncomeLoss_TTM 153, EPS_TTM_CALC 133, FFO_TTM 110, OperatingIncomeLoss_TTM 104,
PretaxIncome_TTM 79, EBITDA_TTM 73, IncomeTaxExpense_TTM 68, and nine more. By ticker: WAT 244,
CIEN 114, TER 78, DE 78, JCI 61, ON 47, KDP 39, FDS 36, CHD 35.

### Every changed value, justified

**All 90 changed values (28 metrics + 62 valuation) are row-position-dependent quantities**, and
nothing else changed:

| changed | count | why |
|---|---:|---|
| pe_to_revenue_growth | 57 | `Revenue_TTM.pct_change(4)` counts **rows**, so removing one shifts the comparison base |
| share_count_jump_flag | 9 | compares consecutive rows |
| buyback_distortion_flag | 5 + 5 | derived from the same row comparison |
| revenue / income / operating_income_yoy_growth | 7 | `pct_change` over rows |
| rule_of_40, operating_leverage, reserve_growth | 7 | built on those growth figures |

No base fact, no margin, no multiple computed from a single period moved.

### Rolling five-year means

| line | n | changed | appeared | disappeared |
|---|---:|---:|---:|---:|
| avg_p_tbv_5y | 24,409 | 1,290 | 20 | 59 |
| avg_ev_ebitda_5y | 20,868 | 1,129 | 33 | 69 |
| avg_pe_5y | 28,248 | 959 | 58 | 57 |
| avg_p_ffo_5y | 27,847 | 848 | 34 | 47 |
| avg_pfcf_5y | 25,508 | 570 | 18 | 42 |
| avg_p_ppnr_5y, avg_p_core_earnings_5y | 2,124 | 0 | 0 | 0 |

**2–5% of points per line** — between the decumulation task (0.2–0.6%) and the TTM task (~25%).

The mechanism is worth naming because it is not the one you would guess. `calculate_rolling_harmonic_stats`
uses a **20-row** window, not 20 calendar quarters — the same row-versus-calendar weakness that the
TTM task fixed in `calculate_ttm` and that still stands here. Removing a duplicate row therefore
shifts which observations fall inside a ticker's window even when none of its values changed. TSLA
is the clean illustration: it lost exactly one row (`SharesOutstanding` 2021-12-30, whose twin at
2021-12-31 survived), no TSLA value changed, and its `avg_p_ffo_5y_n` went from 19 to 20
observations, moving the mean from 68.67 to 70.73.

### Snapshot and the anchor invariant

```
snapshot:  appeared 18   changed 56   disappeared 0
```

All 56 changes are `avg_*_5y` fields, through the row-window mechanism above.

```
newest value moved under an unchanged date:   0
newest date moved:                           13     (11 forward, 2 backwards)
```

**Eleven forward, and they are the point of the exercise.** Waters' whole trailing block moves from
2025-06-28 to **2026-04-04** — nine `_TTM` concepts gaining three quarters of reach. Viatris'
`EPS_TTM_CALC` moves from 2020-03-29 (value 0.0) to 2020-09-30 (0.475).

**Two backwards, and they are a real cost — named rather than smoothed over.** Johnson Controls'
`EBITDA_QUARTERLY` moves from 2016-06-24 back to 2015-09-25, and `EBITDA_TTM` from 2015-12-25 to
2015-09-25. The mechanism:

```
JCI OperatingIncomeLoss    ends at ... 2015-12-25, 2016-03-25, 2016-06-24   (old fiscal calendar)
JCI D&A            before  ends at ... 2015-12-25 AND 2015-12-31, 2016-03-25 AND 2016-03-31, ...
                   after   ends at ... 2015-12-31, 2016-03-31, 2016-06-30   (later end kept)
```

Johnson Controls moved to calendar quarter ends after the Tyco merger and tagged both calendars for
a while — but only for D&A, not for operating income. Keeping the later end put D&A on the new
calendar while operating income stayed on the old one, so `EBITDA = OperatingIncomeLoss + D&A` no
longer joins at those three dates. No value was lost; the join broke. It affects 2 of roughly
33,000 `(ticker, concept)` pairs, and the alternative rule (keep the earlier end) would break the
same join at the other end of the transition.

### Duplicates removed

```
                          before   after
exact (ticker, concept, end) duplicates      0       0
quarter pairs <= 7 days apart              740       0
quarter pairs <= 11 days apart              755      15
quarter pairs <= 30 days apart              963     243
```

**740 → 0.** The decumulation report's baseline was 300 before and 300 after over a narrower
sample; the full frame carries 740, and none remain. The 15 surviving pairs at 8–11 days and the
243 at 12–30 are the deliberately untouched population — fiscal-year changes and acquisition stubs,
a month apart.

### Independent plausibility check

A recovered `Revenue_TTM` that lands on a fiscal year end can be compared with the filer's **own
annual fact** for that year — a separate filing, not built from the four quarters and untouched by
the merge.

```
recovered Revenue_TTM values landing on a fiscal year end with an annual fact:  28
  within 0.1% : 22        exact to the dollar : 16        worse than 1% : 3
```

```
WAT  2024-12-31   2,958,387,000   vs   2,958,387,000    exact
WAT  2022-12-31   2,971,956,000   vs   2,971,956,000    exact
TSN  2010-10-02  28,430,000,000   vs  28,430,000,000    exact
TAP  2010-12-31   3,254,400,000   vs   3,254,400,000    exact
ON   2011-12-31   3,442,300,000   vs   3,442,300,000    exact
CAH  2011-06-30 102,644,300,000   vs 102,644,000,000    0.0003%
LMT  2010-12-31  45,772,000,000   vs  45,671,000,000    0.22%
```

The three misses are scope mismatches, not merge artefacts: **MSI 2009 and 2010** (13.48bn and
7.17bn of summed quarters against annual facts of 6.95bn and 7.62bn) bracket the 2011 Motorola
Mobility separation, where the annual fact is a continuing-operations restatement and the quarters
are as originally reported; **CIEN 2018-11-03** (8.2%) is a 53-week fiscal year, whose annual fact
contains a week no four quarters can.

### Flags

| flag | before | after | Δ |
|---|---:|---:|---:|
| share_count_jump_flag | 734 | 718 | **−16** |
| buyback_distortion_flag | 637 | 635 | −2 |
| inorganic_contaminated | 1,016 | 1,017 | +1 |
| low_tax_rate_flag | 4,070 | 4,077 | +7 |
| fcf_exceeds_ebitda | 1,835 | 1,835 | 0 |
| coverage flags (`quality.py`) | 741 | **737** | **−4** |

The 16 share-count jump flags that go are the ones a duplicate created: two rows a day apart with
share counts that differ by the twin's offset read as a jump. The four cleared coverage flags are
CIEN/StockRepurchased, GEV/ShareBasedCompensation, NUE/StockRepurchased and VTRS/StockRepurchased.

---

## 5. The named cases

```
ACN Revenue            before  72 rows   steps <= 7d: 1   step range   1..92
                       after   71 rows   steps <= 7d: 0   step range  90..92
ACN SharesOutstanding  before  73 rows   steps <= 7d: 1
                       after   72 rows   steps <= 7d: 0

WAT Revenue            before  86 rows   steps <= 7d: 15  step range   1..189
                       after   71 rows   steps <= 7d: 0   step range  88..189
WAT OperatingIncomeLoss before 85 rows   steps <= 7d: 14
                       after   71 rows   steps <= 7d: 0

ADI SharesOutstanding  before  74 rows   steps <= 7d: 1
                       after   73 rows   steps <= 7d: 0
```

Waters afterwards, one row per period and a regular ladder:

```
       end        value  step
2024-03-30  636,839,000    —
2024-06-30  708,529,000   92
2024-09-30  740,305,000   92
2024-12-31  872,714,000   92
2025-03-29  662,000,000   88
2025-06-30  771,332,000   93
2025-09-30  799,887,000   92
2025-12-31  932,362,000   92
2026-04-04 1,267,000,000  94
```

The surviving 189-day step in WAT's history is a genuinely missing quarter, not a duplicate, and is
correctly still refused by the TTM window.

**ADI's `Revenue` was never affected** — 71 rows before and after, steps 91–182. Its duplicate was
in `SharesOutstanding`, where 2011-01-29 and 2011-02-04 carried the identical 308,848,000. The
brief's ADI example is a share-count pair, not a revenue pair.

---

## 6. Deliberately not fixed

**`calculate_rolling_harmonic_stats` uses a 20-row window, not 20 calendar quarters.** This is the
same defect the TTM task fixed in `calculate_ttm` and it is why removing a duplicate row moves a
five-year mean for a ticker whose values did not change (TSLA above). It affects every `avg_*_5y`
line the charts compare against. Fixing it means a calendar test on the rolling window, which is a
change of the same size as the TTM task and deserves its own diff.

**`pct_change(periods=4)` counts rows.** Every one of the 90 changed values in this diff runs
through it. The decumulation report already recorded the related `fill_method="ffill"` default;
the row-versus-calendar basis is the other half of the same problem.

**The two backwards anchor moves (JCI `EBITDA_QUARTERLY`, `EBITDA_TTM`).** Fixing them means
choosing the surviving end per *ticker* rather than per concept, so that two concepts of the same
filer never land on different calendars. That needs cross-concept state in a per-concept pass, for
2 pairs of roughly 33,000.

**The 8–30 day near pairs (258 remaining).** Fiscal-year changes, acquisition stubs and
transition periods — genuinely different dates that happen to be close. They are not duplicates and
the pipeline shows both, which is correct; what it does not do is mark them as transition periods.
That is a data-model question, like the 121–160 day stubs recorded in the decumulation report.

**The `(end, days)` key itself is unchanged**, deliberately: the shorter-duration-wins preference it
encodes is load-bearing for point-in-time concepts, and the merge is achievable without touching it.

**Everything outside the merge**, per the task's scope: no change to `decumulate_period_values`'
quarter-length rule, none to `calculate_ttm`'s bounds, no split/scale/tag work, no
`apply_denominator_scale_guard` / `pct_change` / `fillna` fixes, no coverage-flag semantics, no UI
or chart changes, no new metrics.

---

## Files changed

| file | change |
|---|---|
| `parsers/parse_edgar.py` | `_DUPLICATE_END_MAX_GAP`; new `merge_duplicate_period_ends`; applied in `build_dataframe` after `extract_with_mode` and in `annual_ttm_values` |
| `duplicate_period_ends_report.md` | this file |
| `MDs/bugfixes_opdate_history.md` | entry per convention |

`data/` and `figures/` untouched.

### Verification performed

```
[ok ] quarter pairs <= 7 days apart          740 -> 0
[ok ] exact (ticker, concept, end) duplicates  0 -> 0
[ok ] rows added to the base facts frame       0
[ok ] removed rows with a surviving partner  721 of 721
[ok ] fact values changed                      0
[ok ] every changed value is row-position dependent   90 of 90
[ok ] disappearances accounted                720 base + 502 derived = 1,222
[ok ] newest value moved under an unchanged date      0
[ok ] newest date moved backwards              2, both named and explained
[ok ] COST SharesOutstanding at fiscal year ends      unchanged (the key's preference intact)
[ok ] recovered TTM against the filer's annual fact   22 of 28 within 0.1%
```

**Not verified:** no full refresh was run. Every figure comes from the local companyfacts cache and
a single yfinance price capture, driven through the pipeline's own functions.
