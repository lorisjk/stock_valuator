# Quarter-over-Quarter Growth, Alongside YoY

The growth chart now draws either series and a control on the tab switches between them. The
pipeline computes both, the registry describes both, and the 39-concept catalogue is untouched.

**Two of the brief's premises did not survive measurement, and both mattered.**

1. *"QoQ will be more volatile still, and this task needs its own measurement of how much."* It is
   **less** volatile by the standard-deviation method the brief named: the median panel's QoQ
   standard deviation is **0.58×** its YoY one, and QoQ is the more volatile of the two on only
   **22.5%** of panels. A quarter-to-quarter change is measured over a shorter interval, so it is a
   smaller number and its dispersion follows. What a reader actually has to be warned about is not
   variance, it is a **pattern** — see §1.2.
2. *"the extreme-value share may be larger than the 23.1% already measured for YoY."* It is
   **smaller**: 19.6% of QoQ panels carry a point above +1,000% against YoY's 23.1%, and QoQ is
   below YoY at every threshold. §1.3 has the mechanism.

Both numbers are in `GROWTH_MECHANISM_NOTE`, stated as measured rather than as expected.

---

## 1. Step 0 — the measurements

Source: `data/app/facts_full.parquet`, 1,152,894 rows, 609 tickers. QoQ computed with the same
`calculate_growth` and the same per-concept `min_base_ratio` (0 everywhere), `periods=1`.

Coverage first: **556,227** YoY values on registered panels against **579,724** QoQ ones — QoQ has
**4.2% more**, not fewer, because a 91-day reach finds a neighbour more often than a 365-day reach
finds one.

### 1.1 Volatility — the standard-deviation ratio

The duplicate-removal report's method: per `(ticker, concept)` series with at least 8 observations
carrying both values, `std(qoq) / std(yoy)`. **10,743 pairs**, 539,489 paired observations.

| statistic | QoQ / YoY std |
|---|---:|
| 10th percentile | 0.247 |
| 25th | 0.407 |
| **median** | **0.580** |
| 75th | 0.941 |
| 90th | 1.629 |
| share of pairs where QoQ is the more volatile | **22.5%** |

The mean is 33.4 and is not a useful number — a handful of near-zero YoY denominators dominate it.
The median is the one to quote.

**Only two of the 39 concepts have a median ratio above 1:**

| concept | median | | concept | median |
|---|---:|---|---|---:|
| `CostOfRevenue` | **1.62** | | `OperatingIncomeLoss_TTM` | 0.33 |
| `OperatingCashFlow` | **1.35** | | `PPNR` | 0.34 |
| `StockIssued` | 0.89 | | `EPS_TTM_CALC` | 0.35 |
| `IncomeTaxExpense` | 0.88 | | `FFO_TTM` | 0.37 |
| `NetIncomeLoss` | 0.84 | | `FCF_TTM` | 0.38 |
| `Revenue` | 0.60 | | `StockholdersEquity` | 0.45 |

The `_TTM` series sit at the bottom of the table, which is the duplicate-removal report's finding
seen from the other side: a rolling four-quarter sum is smooth, so its 1-quarter difference is very
small next to its 4-quarter one.

### 1.2 The seasonal sawtooth — what actually needs saying

The right instrument is not dispersion, it is **periodicity**: the spread, in percentage points,
between a panel's best and worst *calendar quarter* median. Seasonality cancels in YoY, so the YoY
figure is the control.

**10,328 panels measured.** Median amplitude **13.32 pp QoQ against 8.92 pp YoY** (1.49×), and QoQ's
amplitude exceeds YoY's on **58.2%** of panels. By profile:

| profile | QoQ | YoY | ratio | | profile | QoQ | YoY | ratio |
|---|---:|---:|---:|---|---|---:|---:|---:|
| `utilities` | 28.3 pp | 6.9 pp | **4.09** | | `pharma_medtech` | 13.0 | 8.7 | 1.50 |
| `retail` | 23.5 | 6.0 | **3.94** | | `financial` | 6.6 | 5.2 | 1.27 |
| `railroads` | 14.6 | 4.8 | **3.06** | | `insurance_pc` | 6.9 | 5.9 | 1.17 |
| `consumer_staples` | 18.3 | 6.8 | 2.68 | | `standard` | 12.8 | 11.7 | 1.09 |
| `homebuilder` | 25.2 | 10.3 | 2.45 | | `reit` | 5.7 | 6.4 | 0.89 |
| `leisure` | 18.5 | 7.9 | 2.36 | | `energy` | 13.9 | 17.6 | 0.79 |

The brief predicted `retail`, `leisure` and `homebuilder`; all three are near the top. `utilities`
was not predicted and is the worst of all — a heating and cooling load is as seasonal as a Christmas
quarter. `reit` and `energy` fall *below* 1, which is the honest other half: a REIT's rent roll and
an oil producer's price exposure are not calendar-driven, and for those the QoQ panel is the quieter
of the two.

**Three worked examples** — median growth by calendar quarter, whole history:

| | Q1 | Q2 | Q3 | Q4 | amplitude |
|---|---:|---:|---:|---:|---:|
| **DECK** Revenue, QoQ | −51.9% | −24.7% | **+115.8%** | +63.4% | **167.7 pp** |
| DECK Revenue, YoY | +10.4% | +13.1% | +12.1% | +7.8% | 5.3 pp |
| **POOL** Revenue, QoQ | +19.4% | **+84.3%** | −24.2% | −34.1% | **118.4 pp** |
| POOL Revenue, YoY | +8.5% | +7.3% | +7.3% | +10.3% | 3.0 pp |
| **CCL** Revenue, QoQ | −2.0% | +3.4% | **+36.6%** | −22.8% | **59.4 pp** |
| CCL Revenue, YoY | +6.1% | +6.5% | +5.8% | +6.3% | 0.7 pp |

DECK is the cleanest case in the universe: a **32×** amplitude ratio. A reader meeting that panel
without the caption would see a business that halves and doubles every year; what it actually shows
is that people buy boots in autumn. `POOL` is the same shape in the opposite phase — pools are bought
in spring.

This is the finding the frontend caption and the mechanism note carry, and it is why the caption
exists at all.

### 1.3 The extreme-value census, re-run for QoQ

Restricted to values that are actually drawn (a registered concept), guard off:

| threshold | YoY | QoQ |
|---|---:|---:|
| drawn values | 556,227 | 579,724 |
| above +200% | 23,179 (4.17%) | **18,082 (3.12%)** |
| above +500% | 9,838 (1.77%) | 8,080 (1.39%) |
| above +1,000% | 5,187 (0.93%) | 4,440 (0.77%) |
| above +10,000% | 981 (0.18%) | 839 (0.14%) |
| above +100,000% | 217 (0.04%) | 186 (0.03%) |
| **panels with ≥1 point above +1,000%** | **2,656 of 11,515 (23.1%)** | **2,269 of 11,559 (19.6%)** |

Smaller on every line. The brief's reasoning — *"QoQ's smaller base-to-base gap means a near-zero
prior quarter is more common"* — inverts the mechanism. A blow-up needs a **tiny base**, and how many
tiny values a series contains is a property of the series, not of the lag. What the lag decides is
*what the tiny value gets compared against*: YoY pairs a near-zero quarter with a normal quarter a
year away, while QoQ pairs it with its immediate neighbour, which is more often near-zero too — and
a ratio of two small numbers is ordinary.

The worst offenders are the same filings either way (`EPS_TTM_CALC` SWK 2020-03-28 at
+18,117,640,216%; `SharesOutstanding` SWK; `StockholdersEquity` TW).

### 1.4 One thing the brief did not ask about: the tolerance scales too

`calculate_growth` derives both its offset and its tolerance from `periods`:

```python
target_offset = pd.to_timedelta(periods * 365.25 / 4, unit="D")
tolerance     = pd.to_timedelta(periods * GROWTH_PERIOD_TOLERANCE_DAYS_PER_4Q / 4, unit="D")
```

At `periods=1` that is **91.31 ± 11.25 days**, a window of 80.1–102.6. Measured over all 656,212
consecutive observation gaps in the growth frame: **97.46% fall inside it**. 15,826 gaps are longer
than 102.6 days, of which 2,987 are 355–375 days — an annual filing cadence.

Consequence, recorded because it shows up as blank panels: **94 of 11,837 series (0.8%) publish only
annually and therefore have no QoQ value at all** (376 YoY values against 79 QoQ across those
series). That is the absence of a preceding quarter, not a dropped value, and a panel drawing
"No Data" in QoQ while drawing a line in YoY is correct. It is in the mechanism note.

---

## 2. Step 1 — the pipeline

### 2.1 The storage shape: a second column

**Decided: a second column, `qoq_growth`, beside `yoy_growth` on the same rows.** The brief guessed
this was "the more mechanical extension" and asked whether that holds once the actual storage is
read. It does — and for a stronger reason than mechanics, because the alternative breaks four
consumers.

`yoy_growth` is not a value in a long frame; it is a **column merged onto the facts frame on
`(ticker, concept, end)`** (`main.add_growth_column`), and that key being unique is load-bearing:

| consumer | what a second *row* per concept would have needed |
|---|---|
| `filter_hidden_rows` (main.py:2273) | filters the facts frame by `concept`; a cadence discriminator would have to be threaded through it |
| `pivot_ticker` (app.py:177) | pivots to `index=end, columns=concept`; two rows per cell means `pivot_table` silently averages them |
| `cadence_markers` (app.py:257) | reads one `ttm_source` per cell |
| `validate_export`'s row floors | measured against the current row counts; every one would need re-baselining |

A column changes none of them. `facts_growth` stays **668,049 rows** and every floor in
`validate_export.py` stays valid — which is most of why the shape was chosen, not merely a
convenience.

Implementation: `add_growth_column` loops over `config.GROWTH_PERIODS` (`{"yoy_growth": 4,
"qoq_growth": 1}`), running the loop that was already there once per mode. `GROWTH_PERIODS` is
derived from `config.GROWTH_MODES`, so the pipeline and the registry cannot declare different modes.

**Cost:** `add_growth_column` goes from **11.0 s to 21.0 s** on the 609-ticker frame, and produces
**no extra rows** (1,152,894 before and after). Export size in §2.3.

### 2.2 The guards apply identically — verified, not assumed

Three separate pieces of evidence.

**Read off the source.** In `calculate_growth`'s body the token `periods` appears on exactly **two
lines** — the offset and the tolerance — and there are **zero** `if`/`elif` branches on it. Neither
guard can differ because neither guard can see it.

**The `> 0` condition, measured on `NetIncomeLoss`** (36,261 rows, 4,470 of them ≤ 0):

| | rows | value ≤ 0 | …of those with a growth value | growth ≤ −100% |
|---|---:|---:|---:|---:|
| YoY | 36,261 | 4,470 | **0** | **0** |
| QoQ | 36,261 | 4,470 | **0** | **0** |

**`min_base_ratio` as a cap, measured on `Capex` at r = 0.33** (a +203.03% cap, by
`growth ≤ 1/r − 1`):

| | values, guard off | guard on | suppressed | min suppressed | max kept |
|---|---:|---:|---:|---:|---:|
| YoY | 29,441 | 28,422 | 1,019 | +203.10% | +202.82% |
| QoQ | 30,659 | 30,040 | 619 | +204.11% | +203.03% |

The cap lands in exactly the same place on both paths. Its value is unchanged at **0** everywhere, as
the brief requires.

### 2.3 The export

`facts_growth` now carries `["ticker", "concept", "end", "yoy_growth", "qoq_growth"]`, written from
`GROWTH_PERIODS` rather than a repeated literal. `registry.json`'s `charts.growth` gains
`value_columns` and `modes`.

Two schema versions bumped, both deliberately fatal rather than additive:

- `REGISTRY_SCHEMA` **1 → 2** — a build that reads the mode control off this block would otherwise
  offer one mode silently against an older registry, and half a control is worse than a refused
  bundle.
- `TICKER_EXPORT_SCHEMA` **1 → 2** — a reader that expects `qoq_growth` and does not get it draws an
  empty chart in QoQ mode with no way to say why.

`.github/scripts/validate_export.py`'s two expectations were bumped to match, and **three checks
added** (§6.6).

**Export cost of the second column**, measured by stripping it back out and re-encoding both sides:

| | raw | gzipped |
|---|---:|---:|
| `tickers/{T}.json` (the chart payload, read on every growth tab) | +11.8 MB | **+5.0 MB** |
| `tickers/{T}.facts.json` (`facts_full`'s copy) | +20.2 MB | **+8.4 MB** |
| total | +31.9 MB (+19.8%) | +13.4 MB (+51.7%) |

The first is the price of the toggle being instant rather than a network round-trip behind a radio
button — about **8 kB gzipped per ticker** — and is stated as such in `load.ts`. The second is **63%
of the cost and nothing reads it**: `facts_full` already carried `yoy_growth` unread (the data tab
pivots on `value`), and `qoq_growth` rides along because that frame is exported whole. Left alone
deliberately — trimming it is a decision about `facts_full`'s contract, not about QoQ — and recorded
as a follow-up in §7 with the number attached.

---

## 3. Step 2 — the registry

### 3.1 The id/label scheme: a mode is a column, not 39 more metrics

**Decided: one shared catalogue of 39, with the mode as a chart-level property.** The alternative —
39 `_qoq` ids — was rejected on four counts:

- It doubles the catalogue to 78, and every one of the **24 profiles' visibility rows** with it.
- It puts `Revenue` and `Revenue_qoq` in the same picker, where they are one panel measured two ways,
  not two panels.
- It contradicts the reference. `calculate_growth` already took `periods`, and
  `figures.build_growth` already took `growth_column: str = "yoy_growth"` — **the reference models
  the mode as a column and always did.** This task passes a second value to a parameter that has been
  there the whole time.
- The toggle would have to rewrite the *selection* rather than the *column*, so a user who had picked
  six panels would lose the picks on every switch.

The registry shape (`config.GROWTH_MODES`, exported verbatim into `charts.growth.modes`):

```json
{ "key": "yoy", "column": "yoy_growth", "periods": 4,
  "label": "Year over year", "short": "YoY", "description": "…" }
```

`value_column` stays singular and stays `yoy_growth`. Its one consumer is `_percent_applies`
(app.py:334 / `data/format.ts`), which asks *"does this metric's percent flag describe the column I
am formatting?"* and is only ever asked about `value`. Widening it to a set would change a contract
the frontend types as a literal union, to fix a problem no caller has. `value_columns` is the
additive answer.

### 3.2 The labels had to change, and that is the one breaking edit

**38 of the 39 growth labels ended in `", YoY)"`** — `"Revenue growth (Quartal, YoY)"`, `"EPS Growth
(TTM, YoY)"`, and so on. Those strings are the panel y-axis titles and the picker's option text. They
were true of the only column that existed and are false the instant the control is touched.

All 38 now end at the window: `"Revenue growth (Quartal)"`, `"EPS Growth (TTM)"`. What stays is the
**window of the underlying series** — `(Quartal)` against `(TTM)` — which is a property of the
concept and does not move with the mode. The mode is named **once**, on the control and in the figure
title, instead of 39 times in axis labels that cannot be kept honest.

`config.py`'s `Metric.label` comment says the label *"must stay byte-identical"*. This breaks that for
the growth chart, knowingly: the alternative is 38 labels that lie in one of the two modes.
Fundamentals and valuation labels are untouched — §6.9 proves it.

### 3.3 Descriptions and formulas

Scanned all 39 for mode-specific language. **Exactly one was wrong** — `Revenue`, the only entry that
had ever spelled the lag out:

| | before | after |
|---|---|---|
| description | "Sales in this quarter against the same quarter a year earlier." | "Sales in this quarter against the earlier quarter the chart's mode selects — four quarters back, or the one immediately before." |
| formula | "Single quarter as filed, against the quarter ~365 days earlier." | "Single quarter as filed. The lag is the mode's, not this metric's; see the growth mechanism note." |

`NetIncomeLoss`'s description was softened the same way. The other 37 describe the *underlying
series* and are mode-neutral already — which is the existing design working: the lag was always
documented once, in the shared note, and only one entry had duplicated it.

### 3.4 The mechanism note

`GROWTH_MECHANISM_NOTE`'s first bullet was `"**4-quarter lag.**"`. It is now four bullets, and the
count goes 7 → 10. The new text, in full:

> - **Two lags, one computation.** The chart's mode control switches which of two columns is drawn.
>   **YoY** compares each period against the observation closest to 365 days earlier (tolerance ±45
>   days), so a quarterly series is compared like for like — Q3 against Q3 — and seasonality cancels.
>   **QoQ** compares it against the one closest to 91 days earlier (tolerance ±11 days). Both are
>   `calculate_growth` with a different `periods` argument and are subject to every guard below
>   identically; nothing else differs.
> - **QoQ is not seasonally adjusted.** This is the one thing to know before reading it. A seasonal
>   filer shows a regular yearly cycle in QoQ that is the calendar rather than the business: measured
>   across this universe, the spread between a panel's best and worst calendar quarter is a median
>   13.3 pp in QoQ against 8.9 pp in YoY, and 24 pp against 6 pp for retailers specifically. DECK's
>   quarterly revenue growth runs −52%, −25%, +116%, +63% around the year while its YoY growth never
>   leaves +8% to +13%. Both are correct; only one of them is about the business.
> - **QoQ is not the noisier series, despite that.** A quarter-to-quarter change is measured over a
>   shorter interval, so it is smaller: the median panel's QoQ standard deviation is **0.58×** its
>   YoY one, and QoQ is the more volatile of the two on only 22.5% of panels. The sawtooth above is a
>   *pattern*, not extra variance.
> - **Annual-cadence series have no QoQ at all.** A filer publishing an item once a year leaves no
>   observation inside the 91 ± 11 day window, so those panels are blank in QoQ and populated in YoY.
>   94 of 11,837 series in this export (0.8%). That is the absence of a preceding quarter, not a
>   dropped value.

The minimum-base bullet also gained the §1.3 census, because it had described the YoY extreme-value
share as though it were the only one.

---

## 4. Step 3 — the toggle

### 4.1 Scope: one control for the chart

**Global, and here is the reasoning rather than the assumption.** The mode is a property of the
*measurement*, not of the concept — `calculate_growth` takes the same `periods` for all 39 — so a
per-panel control is 39 copies of one boolean. It is also the shape of the data: `facts_growth` holds
two columns over **one row set**, so a global switch re-reads one array where a per-panel switch
would re-read a different array per panel to no end. And a grid whose panels were half YoY and half
QoQ has no readable shared meaning; the chart is "growth", singular.

### 4.2 The control

`frontend/src/GrowthModeControl.tsx` + `growth-mode.css`. Radios, not a checkbox: a checkbox has a
default state and an exceptional one, and QoQ is not an exception to YoY — both are ordinary ways to
read the same series. Rendered as `role="radiogroup"` on a `<div>` rather than a `<fieldset>`,
because a `<legend>` does not participate in its parent's flex box consistently across browsers; the
grouping and the accessible name are identical either way.

Placement: **above the chart, below the window slider**, which is where `app.py:942` puts the masking
toggle and for the reason recorded there — a control that changes what is drawn belongs where the
reader meets it before the drawing. It renders **outside** the `result` branches, so it does not
vanish when the picker is cleared; a control that disappears looks like a bug.

The caption is the point of the control, not decoration:

> Each period against the one immediately before it. **Not seasonally adjusted**: a seasonal business
> shows a regular yearly cycle here that is the calendar, not the trend.

It comes off the registry (`config.GROWTH_MODES[*].description`), so the caption, the mechanism note
and the pipeline cannot say different things. YoY's reads *"Each period against the observation
closest to four quarters earlier. Like for like — Q3 against Q3 — so seasonality cancels."*

State lives in `ChartView` as `growthMode: string | undefined`. `undefined` means "the user has not
chosen", which resolves to the registry's first mode inside the builder — storing the resolved key
would give the registry's declaration order a second, silent owner. The control reads its value from
state and not from `result.mode`, because `result` is `null` while a ticker's frames are in flight
and the control would otherwise snap to the default for a frame.

### 4.3 Interaction with the window and the masking machinery — confirmed from the code

| machinery | applies to growth? | evidence |
|---|---|---|
| **years window** | yes, and mode-independent | `_window_frame` filters on `end` and never looks at `growth_column`; in the port, `seriesFor` resolves rows and `valuesFrom` re-reads a column over those same rows. **One row set, two columns.** |
| **mean line** | never | `build_growth` does not call `plot_metric` at all, so it has no `show_mean` to pass. Only `build_valuation` sets it (figures.py:753). |
| **outlier masking** | never | `build_growth` takes no `mask_outliers`. `ChartView` passes `mask` to all three builders and only the valuation one reads it. |

So there is **one** implementation path for both modes, not two — which is what Step 3.3 asked to
confirm. Verified at runtime as well: with the window at 7 years, switching mode leaves the slider at
7, and switching tabs leaves the mode at QoQ (§6.8).

### 4.4 The tab label

**`"Growth (YoY)"` → `"Growth"`**, in `app.py`'s `CHART_LABELS` and in the two places the port mirrors
it. The mode moved *into* the figure title, which can follow it: `Growth (YoY) AAPL` /
`Growth (QoQ) AAPL`, read off the same `GROWTH_MODES` table on both sides.

A side effect worth recording: the reference kept **two** spellings — `CHART_LABELS`'
`"Growth (YoY)"` for the Analysis tab and `CHART_SECTIONS`' `"Growth"` for the encyclopedia — and
`Encyclopedia.tsx` carried a comment about the discrepancy. They agree now.

---

## 5. Step 4 — every "YoY" reference

Grepped `yoy`, `YoY`, `year-over-year`, `year over year` across `frontend/src`, `*.py`, `*.md` and
`frontend/public`. Every hit, with the decision:

### 5.1 Changed

| site | was | now | why |
|---|---|---|---|
| `app.py:41` `CHART_LABELS["growth"]` | `"Growth (YoY)"` | `"Growth"` | the tab cannot name a mode the reader chooses |
| `shell/navigation.ts:52` `TAB_LABELS.growth` | `"Growth (YoY)"` | `"Growth"` | mirrors `CHART_LABELS` |
| `ComparisonView.tsx:38` `CHART_LABELS.growth` | `"Growth (YoY)"` | `"Growth"` | the comparison picker's option prefix, same source |
| `figures.py:697` figure title | `f"Growth (YoY) {ticker}"` | `f"Growth ({mode_label}) {ticker}"` | the title *can* follow the mode, so it does |
| `charts/growth.ts:122` figure title | `` `Growth (YoY) ${ticker}` `` | `` `Growth (${mode.short}) ${ticker}` `` | same, off the same table |
| **38 growth metric labels** | `"… (Quartal, YoY)"` | `"… (Quartal)"` | §3.2 |
| `Revenue` description + formula | named the 365-day lag | defers to the mode | §3.3 |
| `NetIncomeLoss` description | "the same quarter a year earlier" | "the earlier quarter the mode selects" | §3.3 |
| `app.py:92` / `Encyclopedia.tsx:57` section blurb | "Year-over-year change in the underlying filed figures." | "Change in the underlying filed figures, year over year or quarter over quarter." | it introduces the whole group |
| `GROWTH_MECHANISM_NOTE`'s "4-quarter lag" bullet | one lag | both lags, plus three new bullets | §3.4 |
| `README.md:90` tab table | `Growth (YoY) \| year-over-year change…` | `Growth \| change…, year over year or quarter over quarter (a control on the tab)` | it documents the tab |
| doc comments in `contracts.ts`, `navigation.ts`, `Encyclopedia.tsx`, `growth.ts`, `load.ts` | asserted the single mode | describe both | comments that were true and are not |

### 5.2 Kept as YoY, deliberately

| site | what it is | why it stays |
|---|---|---|
| `revenue_yoy_growth`, `income_yoy_growth`, `operating_income_yoy_growth` | **fundamentals** metric ids | a different chart, out of scope, and genuinely YoY: `calculate_growth(facts, "Revenue_TTM", 4, …)` with a literal 4 |
| their formula texts ("…, 4-quarter lag") | fundamentals encyclopedia entries | accurate — those three have one lag and no control |
| `charts/defaults.ts:33` `fundamentals: "revenue_yoy_growth"` | the fundamentals default | a fundamentals id |
| `claims_reserve_growth`, `pe_to_revenue_growth` formula texts | fundamentals / valuation | same |
| `yoy_growth` as a **column name** (`VALUE_COLUMN`, `GROWTH_COLUMN`, `CHART_SPECS.value_column`) | the YoY column, which is still exactly that | renaming it `growth` would make the *other* column the odd one |
| `data/shareHistory.ts:17` | a comment about a share-count heuristic | unrelated to the chart |

### 5.3 One thing found and not changed

`current_snapshot` carries a **concept literally named `yoy_growth`** (`main.py:1249`, feeding the
PEG calculation at `main.py:1326`). It renders in the data tab as a bare row label `yoy_growth`,
which is now ambiguous next to a chart with two modes. It is YoY-specific by construction, and
renaming it would ripple through `build_snapshot`, the data tab and the CSVs — a rename, not a QoQ
change. Recorded in §7.

### 5.4 The encyclopedia's growth section

All 39 entries verified against the rendered page rather than against the registry: §6.7,
**136/136**.

---

## 6. Step 5 — verification

### 6.1 QoQ matches a hand computation

`step5_hand.py` re-derives QoQ from the raw facts **without `merge_asof`**: for each sampled row it
scans the concept's own observations, takes the one nearest to `end − 91.3125 days` within ±11.25,
and applies both guards by hand. 400 rows sampled across 10 concepts.

```
400/400 sampled values reproduce the hand computation
```

The worked example, AAPL Revenue — and it is a seasonal one, which is the point:

| period | value | hand `(v−prev)/prev` | pipeline QoQ | pipeline YoY |
|---|---:|---:|---:|---:|
| 2024-12-28 | 124,300,000,000 | | +30.94% | +3.95% |
| 2025-03-29 | 95,359,000,000 | −23.28% | **−23.28%** | +5.08% |
| 2025-06-28 | 94,036,000,000 | −1.39% | **−1.39%** | +9.63% |
| 2025-09-27 | 102,466,000,000 | +8.96% | **+8.96%** | +7.94% |
| 2025-12-27 | 143,756,000,000 | +40.30% | **+40.30%** | +15.65% |
| 2026-03-28 | 111,184,000,000 | −22.66% | **−22.66%** | +16.60% |
| 2026-06-27 | 109,417,000,000 | −1.59% | **−1.59%** | +16.36% |

Even Apple sawtooths: +40% into the December quarter, −23% out of it, against a YoY line sitting flat
at +16%.

### 6.2 YoY is unchanged — the whole universe, element for element

The existing `yoy_growth` column was held back before `add_growth_column` ran and compared against
the recomputed one across every row of the facts frame:

```
rows compared      : 1,152,894
non-null before    : 928,480
non-null after     : 928,480
bit-identical      : 1,152,894
DIFFERING          : 0
```

**Zero.** Bit-identical, not within-tolerance — the same code path produced the same floats.

### 6.3 The toggle redraws every panel, checked against the pipeline

Two independent comparisons.

**`build_growth` (Python) against `buildGrowth` (TypeScript), both modes, 7 tickers:**

```
910/910 checks pass across 14 scenarios, 15,684 data points
panels whose y differs between modes: 140; identical: 0
```

Titles, heights, y-axis labels, trace names, x arrays and y arrays. (`width` is excluded: the port
omits it by design so the figure is responsive.) Every one of the 140 panels draws different data in
the two modes — a comparison where the modes agreed would prove nothing.

**The rendered page** (headless Edge over CDP, raw `textContent` and `gd.data` read out of plotly),
DECK and AAPL with all 36 panels selected, toggled YoY → QoQ → YoY:

```
406/406 checks pass; 4,850 data points compared element-wise
```

Each trace was checked twice: against the Python builder's figure, **and** straight against
`facts_growth.parquet`'s own `yoy_growth` / `qoq_growth` column, bypassing both builders.

**Sensitivity.** The harness must be able to fail. Mutating one line of `growth.ts` —
`valuesFrom(frame, series, "yoy_growth")` instead of `mode.column`, i.e. a control that draws but
does nothing — takes it from 406/406 to **318/406**, with 88 failures naming the panels:

```
FAIL DECK/qoq/Revenue y: got [0.4911…, 0.4039…] want [1.6867…, 0.4573…]
```

Restored and re-verified afterwards.

Builder defaults, checked separately: `buildGrowth` with **no** `mode` is byte-identical to
`mode: "yoy"` (same sha256), an **unknown** mode falls back to the first declared one rather than
throwing, and the panel list is identical in both modes (36 for DECK) — the mode changes the column,
never the selection.

### 6.4 The seasonal case renders as predicted

Measured off the **drawn** trace, not the parquet — DECK Revenue as it appears on screen, 15-year
window:

| | Q1 | Q2 | Q3 | Q4 | amplitude |
|---|---:|---:|---:|---:|---:|
| YoY | +9.6% | +13.1% | +9.1% | +7.8% | **5.3 pp** |
| QoQ | −51.4% | −28.2% | +115.8% | +63.5% | **167.2 pp** |

167.2 pp on screen against 167.7 pp over the full history — the difference is the window. AAPL, on
the same screen: 2.9 pp YoY, 71.3 pp QoQ.

And the caption is **on the same screen as the chart**, in both modes, with the right emphasis —
checked as rendered text and as `<strong>` contents, not as a source string:

```
Each period against the one immediately before it. Not seasonally adjusted: a seasonal
business shows a regular yearly cycle here that is the calendar, not the trend.
```

### 6.5 The tab label, and nothing stale left

Read out of the DOM:

```
["Data", "Raw Facts", "Growth", "Fundamentals", "Valuation", "Comparison"]
```

No remaining "YoY" in any user-visible string. Every surviving `yoy` in `frontend/src` is a column
name, a fundamentals metric id, a `GrowthMode` field, or a comment explaining one of those.

### 6.6 Export and registry

`validate_export.py`: **ACCEPTED, all 41 checks pass** (38 before, +3 new).

The brief asked whether any validator check assumes a single growth value per concept. **None did** —
the frames are gated by row floors and the registry by structure, and the column shape leaves both
untouched (`facts_growth` is 668,049 rows before and after). But that is also the gap: a *missing
mode* is a missing **column**, which no row floor can see. Three checks added, reading the expected
columns off `registry.json`'s own `modes` block rather than a list repeated in the validator:

```
facts_growth carries every declared growth mode  PASS  ['qoq_growth', 'yoy_growth']  ['yoy_growth', 'qoq_growth']
facts_growth `yoy_growth` non-null               PASS  556,227  > 0
facts_growth `qoq_growth` non-null               PASS  579,724  > 0
```

`registry.json` carries `charts.growth.value_columns = ["yoy_growth", "qoq_growth"]` and both mode
blocks; `meta.json` records `registry.schema 2` and `per_ticker.schema 2`.

### 6.7 The encyclopedia

All 39 growth entries read out of the rendered Growth group:

```
136/136 encyclopedia checks pass (39 growth entries x 3 fields, 10 note bullets, 7 phrases)
```

Every label, description and formula present; all 10 mechanism-note bullets render as `<li>`s (10 in
config, 10 on the page); the four new bullet headings and the three measured numbers (`0.58x`,
`13.3 pp`, `19.6%`) all appear; no growth label names a mode.

### 6.8 Standing checks

`check-chart-width.mjs`, `check-tab-state.mjs` and `check-table-format.mjs` were scratch harnesses
from earlier cycles and were not preserved. The first two were **rebuilt**, because this task can
plausibly break them; the third was not, and that is stated rather than glossed — see below.

**check-chart-width (rebuilt), 33/33 together with tab-state:**

| chart | panels | plot px | host px | doc scroll / client | overflowing |
|---|---:|---:|---:|---|---:|
| growth, YoY | 36 | 1087 | 1087 | 1570 / 1570 | 0 |
| growth, QoQ | 36 | 1087 | 1087 | 1570 / 1570 | 0 |
| fundamentals | 11 | 1087 | 1087 | 1570 / 1570 | 0 |
| valuation | 9 | 1087 | 1087 | 1570 / 1570 | 0 |

No figure pins a width, no panel escapes its host, the page never scrolls horizontally.

**check-tab-state (rebuilt):**

| step | mode | years | control | title |
|---|---|---|---|---|
| growth, fresh page load | `yoy` | 15 | yes | `Growth (YoY) DECK` |
| set QoQ + 7 years | `qoq` | 7 | yes | `Growth (QoQ) DECK` |
| → fundamentals tab | — | 15 | **no** | `Fundamentals DECK` |
| → back to growth | `qoq` | **7** | yes | `Growth (QoQ) DECK` |
| → ticker AAPL | `qoq` | 7 | yes | `Growth (QoQ) AAPL` |
| → back to YoY | `yoy` | 7 | yes | `Growth (YoY) AAPL` |

The mode survives a tab round-trip and a ticker switch; the window is untouched by the mode and
fundamentals keeps its own; no mode control leaks onto the other charts.

**check-table-format: not re-run.** Its harness is gone and this task changes no table. What was
checked instead, positively: the data and Raw Facts tabs render 6 tables / 1,085 cells / 117 row
headers, **no `qoq_growth` appears anywhere in either**, and no consumer in the frontend reads
`Frame.columns` for rendering — so the extra column in `facts_full`'s export cannot reach a table.

### 6.9 The other three charts are unchanged

Two independent arguments.

**Cross-implementation A/B, now:** `build_fundamentals` / `build_valuation` /
`build_ticker_comparison` against their TypeScript ports, 3 tickers —

```
246/246 checks pass, 2,309 data points
```

including the comparison chart's exclusion list (`[["ERIE", "No Data"]]` on both sides).

**Registry diff against `HEAD`** (which spans this cycle *and* the previous one):

| | result |
|---|---|
| fundamentals metrics | **29, 0 changed**; chart spec byte-identical |
| valuation metrics | **13, 0 changed**; chart spec byte-identical |
| growth metrics | 39, **9 changed — only `label` / `description` / `formula`** |
| growth chart spec | gained exactly `{modes, value_columns}` |
| `ticker_profile`, `quarterly_counterpart`, `harmonic_mean_concepts` | identical |
| `notes.valuation_mechanism` | identical |
| `undocumented` | `[]` → `[]` |

### 6.10 Toolchain

```
npx tsc -b       clean
npx vite build   ✓ built in 11.15s
npx eslint .     4 errors — all four pre-existing at HEAD, none in code this task touched
```

The four: `Chart.tsx:11` (`no-explicit-any`), `ChartView.tsx` ×2 (`rules-of-hooks` — the operator's
fullscreen `useState`/`useEffect` sit **after** the `if (!build) return` early return; confirmed
present at `HEAD` at lines 185/197, this task only moved the line numbers), and `Sidebar.tsx:94`
(`set-state-in-effect`). Left alone: all four are operator code, and fixing the hook order means
moving their block.

---

## 7. Follow-ups, deliberately left

1. **`facts_full`'s copy of both growth columns is 8.4 MB gzipped that nothing reads** (§2.3). The
   data tab pivots `facts_full` on `value`; neither growth column is read from it. Dropping both from
   that one export recovers 63% of this task's payload cost. Left because it is a decision about
   `facts_full`'s contract — *"the facts frame as computed"* — and `yoy_growth` has been riding along
   unread since long before this task.
2. **A per-panel y-axis rule is still the right fix for absurd values, and still absent.** The
   previous cycle concluded it and §1.3 does not change it. QoQ has slightly fewer blow-ups than YoY,
   so the toggle neither helps nor hurts: one +14,302% point still flattens the other 57 in its
   panel, in either mode.
3. **`current_snapshot`'s `yoy_growth` concept** (§5.3) now reads ambiguously as a bare row label. A
   rename, with its own blast radius through `build_snapshot`, the PEG calculation, the data tab and
   the CSVs.
4. **`MDs/encyclopedia.md:745`** still reads `## Operating Income Growth (YoY)`. `MDs/` is
   hand-written reference documentation for the pipeline and no previous cycle has updated it (the
   last one added 29 metrics without touching it), so it is drifting for a reason that predates this
   task and should be refreshed as one job rather than one heading at a time.
5. **`app.py:904`'s substring bug**, reported by the duplicate-removal cycle and still open:
   `default = [i for i in ids if i in ("revenue_yoy_growth")]` is a string, not a tuple, so `in` is a
   substring test. It works by luck. The port already carries the corrected intent
   (`charts/defaults.ts`).
6. **The QoQ mode is not in the URL.** `#/analysis/AAPL/growth` restores the tab and the ticker but
   not the mode, so a shared link always opens on YoY. The window slider and the picker have the same
   gap, so this is the existing design rather than a new hole — but a mode is more consequential to
   share than a window, and it is now the strongest case for putting chart state in the hash.

---

## 8. Two mistakes of mine, for the record

Both were my *expectation models*, not the port — the renders were correct each time.

- The mode control's option text is `<input/>{" "}Year over year <span>(YoY)</span>`, so
  `textContent` opens with the JSX separator space. My check compared without it and reported four
  failures against a correct render. The `{" "}` is the same spelling `OutlierControls` uses.
- My first encyclopedia capture scored 2/134, because the page is three tabbed groups and only the
  active one is in the DOM — I had captured Fundamentals and compared it against the growth
  catalogue. Clicking through to Growth first gives 136/136.

The one real defect the harnesses caught was in a harness itself: a comment containing backticks,
written inside a template literal, terminated the literal (`SyntaxError: Unexpected identifier
'subplot'`). Third instance of that family across these cycles.
