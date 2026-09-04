# Growth for Every Raw Fact, and the Base-Ratio Guard Set to Zero

Three changes: growth panels for every raw fact, `min_base_ratio` set to 0 everywhere, and a
documented registry entry for each new metric. All three are done. The `> 0` condition is untouched.

**One concern, stated once and then built anyway.** `min_base_ratio` is not a separate guard from
"absurd growth" — it *is* the cap. `prev >= r × value` is algebraically `growth <= 1/r − 1`, so 0.33
was a +203% cap and 0.05 a +1,900% cap. Setting it to 0 does not loosen a filter, it removes the
ceiling: **every one of the 33,070 values it was blocking is above +200% by construction**, a quarter
are above +1,000%, and 217 of the values now drawn exceed +100,000%. **23.1% of all
(ticker, concept) growth panels now contain at least one point above +1,000%**, which on a shared
y-axis flattens everything else in that panel. That is measured, not predicted, and §5.3 is the
census. The brief asked for the number rather than the argument, so the change is in and the number
is here.

---

## 1. Step 0 — what the guard was doing

Measured on the current cached universe (609 tickers, 1,152,894 fact rows) by running
`calculate_growth` twice per concept, at today's thresholds and at 0, and diffing.

| | values |
|---|---:|
| growth values with the guard | 895,412 |
| growth values with `min_base_ratio = 0` | 928,482 |
| **suppressed by the base-ratio guard** | **33,070** (3.6%) |

### The distribution of what it was blocking

| percentile | growth |
|---|---:|
| median | 435% |
| p75 | 955% |
| p90 | 3,022% |
| p95 | 8,390% |
| p99 | 79,249% |
| max | 25,542,473,126% |

| threshold | count | share |
|---|---:|---:|
| > 100% | 33,071 | 100.0% |
| > 200% | 33,070 | 100.0% |
| > 500% | 14,493 | 43.8% |
| > 1,000% | 7,961 | 24.1% |
| > 10,000% | 1,459 | 4.4% |
| > 100,000% | 282 | 0.9% |

The "100% at >200%" line is not a coincidence and is the whole finding: the guard and the threshold
are the same object.

### The ten concepts it suppressed most

| concept | suppressed | of rows |
|---|---:|---:|
| `StockIssued` | 2,967 | 26,984 |
| `StockRepurchased` | 2,785 | 25,980 |
| `StockRepurchased_TTM` | 2,442 | 26,090 |
| `IncomeTaxExpense` | 2,136 | 35,858 |
| `StockIssued_TTM` | 1,827 | 27,226 |
| `NetIncomeLoss` | 1,698 | 36,261 |
| `IncomeTaxExpense_TTM` | 1,687 | 35,895 |
| `OperatingCashFlow` | 1,585 | 35,956 |
| `FCF_QUARTERLY` | 1,566 | 29,516 |
| `EPS_QUARTERLY_CALC` | 1,487 | 33,187 |

### The second list, as it was

`GROWTH_MIN_BASE_RATIO_OVERRIDES` (main.py:642) named **seven** concepts, each at **0.05** —
`Capex`, `CashAndEquivalents`, `Goodwill`, `Inventory`, `LongTermDebt`, `ProvisionForCreditLosses`,
`TangibleEquity` — against a default of **0.33** for everything else.

---

## 2. The new catalogue

### 2.1 The rule, from the code

`available_raw_concepts` (figures.py:1081) intersects a ticker's non-null concepts with
`get_concept_candidates(ticker)`'s **keys** — the tags the pipeline actually asks EDGAR for. Not a
suffix test; the raw-facts cycle established that a suffix rule mislabels `PPNR`,
`CoreOperatingEarnings` and `TangibleEquity`. Taking the union of those keys over all 609 tickers and
intersecting with what is in `facts_full`:

| | count |
|---|---:|
| concepts in `facts_full` | 72 |
| **raw** (a candidate key for at least one ticker) | **35** |
| derived | 37 |
| excluded outright (`_GROWTH_EXCLUDED_CONCEPTS` and their `_TTM` forms) | 4 |
| **raw and eligible** | **33** |
| of those, already registered | 4 (`Revenue`, `NetIncomeLoss`, `SharesOutstanding`, `StockholdersEquity`) |
| **newly registered** | **29** |

### 2.2 Raw only, not raw plus derived

**Decision: raw only**, plus the six already-registered derived series that have no raw counterpart
(`EPS_TTM_CALC`, `FCF_TTM`, `OperatingIncomeLoss_TTM`, `PPNR`, `CoreOperatingEarnings`, `FFO_TTM`).
Final catalogue: **39**.

Three reasons, in order of weight:

1. **A `_TTM` panel is the same quantity on a different window, and the window is what this chart
   already varies.** `Revenue` and `Revenue_TTM` growth answer one question at two smoothings; the
   years slider is the control for that.
2. **Panel count.** Raw-only gives a standard ticker 36 panels; raw+derived gives 61. At
   `_make_grid`'s 3 columns that is 12 rows against 21.
3. **`PROFILE_HIDDEN` cost** — §3: 357 entries against 1,004.

The six derived exceptions stay because removing them would be a regression, and each is a series
with no filed raw parent.

### 2.3 Panels per profile

| profile | before | after |
|---|---:|---:|
| `standard` | 7 | **36** |
| `financial` | 6 | **34** |
| `reit` | 7 | **35** |

Read off the exported `registry.json`'s `profile_visibility`, not predicted. The 3–5 that are still
hidden come from the existing `_DERIVED_CONCEPT_CONSUMERS` rule on `PPNR`, `FFO_TTM`,
`CoreOperatingEarnings` and `OperatingIncomeLoss_TTM`.

### 2.4 Concepts that can never draw

**None.** All 68 eligible concepts produce at least one growth value with the guard off. But 29
produce values for **fewer than 30 of the 609 tickers** — the sector tags:

| concept | tickers |
|---|---:|
| `CoreOperatingEarnings` | 15 |
| `BenefitsLossesAndExpenses`, `Investments` | 16 |
| `ClaimsReserve`, `EarnedPremiums`, `IncurredLosses`, `NetInvestmentIncome` | 17 |
| `NoninterestIncome`, `PPNR`, `ProvisionForCreditLosses` | 24 |
| `NoninterestExpense` | 25 |
| `Assets`, `NetInterestIncome` | 26 |
| `AccountsReceivable`, `FFO_TTM` | 28 |
| `AccountsPayable`, `CostOfRevenue` | 29 |

So no panel is *always* "No Data", but for most tickers most of these panels are. §3 is why that is
the shipped state.

---

## 3. The `PROFILE_HIDDEN` cost — measured, and not paid

Counted against `is_hidden`'s real behaviour rather than against candidate-list membership, because
the two differ: five of the raw concepts (`IncomeTaxExpense`, `PretaxIncome`, `ShareBasedCompensation`,
`StockIssued`, `StockRepurchased`) already resolve through `_DERIVED_CONCEPT_CONSUMERS`.

| | entries |
|---|---:|
| `PROFILE_HIDDEN` today | 616 |
| **raw-only catalogue would need** | **+357** → 973 (**+58%**) |
| raw+derived would need | +1,004 → 1,620 (+163%) |

**17 of the 33 raw concepts cost nothing** — every profile asks EDGAR for them. The other 16 are the
sector tags, five of them needing 23 entries each (`Assets`, `NetInterestIncome`,
`NoninterestExpense`, `NoninterestIncome`, `ProvisionForCreditLosses` are offered by exactly one
profile).

**Not added.** Per the brief's Step 2.2, the number is reported instead. The visible consequence,
recorded in `config.py` beside the entries so it is not mistaken for a bug: **a retailer's growth
chart now offers bank and insurer panels, and they draw "No Data".**

### The positive-list refactor is *not* what this number justifies

The coverage cycle's 5-against-615 comparison was for the *existing* catalogue. Re-measured for this
one:

| catalogue | negative list (hide entries) | positive list (show entries) |
|---|---:|---:|
| raw-only | **357** | 435 |
| raw+derived | 1,004 | 435 |

For raw-only the positive list is **worse**. The switch only pays if the catalogue later grows to
include the derivations. Reported so the earlier recommendation is not applied to a case it was not
measured on.

### The cheaper option, and why it needs its own cycle

`_DERIVED_CONCEPT_CONSUMERS` is not restricted to derived concepts — it already holds five raw ones —
and it is "this concept's visibility follows the metrics that consume it". All 16 costly concepts
have a natural consumer already in the registry (`NetInterestIncome` → `net_interest_margin`,
`Assets` → `roa`/`equity_to_assets`, `Inventory` → `inventory_turnover`/`dio`, `EarnedPremiums` →
`loss_ratio`/`combined_ratio`, and so on). **16 map entries instead of 357 hide entries.**

It is not done here because the blast radius is wider than the growth chart: `filter_hidden_rows`
runs over the **facts frame itself** (main.py:2269), keyed by concept, so mapping `Assets` would
strip `Assets` rows out of the export for every non-financial profile and empty those columns in the
Data tab and the Raw Facts chart. That is a deliberate change with its own verification, not a
side-effect of this one. **Recommended as the next cycle.**

---

## 4. What was changed, by file

| file | change |
|---|---|
| `metrics.py` | `calculate_growth`'s `min_base_ratio` default `0.33` → `0.0`, plus a docstring recording that the parameter is a growth cap and what the zeroing admits |
| `main.py` | all seven `GROWTH_MIN_BASE_RATIO_OVERRIDES` values `0.05` → `0.0`; the call-site fallback `0.33` → `0.0`. **Nothing deleted** — dict, keys and parameter all intact |
| `config.py` | 29 new `Metric(…, CHART_GROWTH, …)` entries, each with `label`, `description` and `formula`; `GROWTH_MECHANISM_NOTE`'s base-ratio bullet rewritten and a catalogue bullet added |
| `figures.py` | `build_growth` reads `percent` and `ref_line` from `METRICS_BY_ID` instead of hardcoding `percent=True` / `y=0` |
| `data/app/*`, `frontend/public/*` | re-exported (§5.4) |

**Nothing was deleted anywhere.** Reversing the guard is editing eight numbers.

### 4.1 The formulas, and the shared mechanism

Per-concept text is short by design: the 4-quarter lag, the `> 0` rule and the now-zero base ratio are
identical for all 39 and are documented once in `GROWTH_MECHANISM_NOTE`, which the encyclopedia
renders above the Growth entries. Each entry's `formula` says only what is specific to it — the filed
EDGAR tag, and whether it is a **period flow** ("Single quarter as filed") or a **point-in-time
balance** ("Point-in-time balance as filed"). That stock/flow split is real and is not otherwise
visible: 11 of the 29 are balance-sheet items whose "quarterly growth" means something different from
a flow's.

The mechanism note's old bullet claimed the guard "caps a reported growth rate at about +200% and
suppresses the explosions that come from a near-zero base". That is now false, so it was rewritten
rather than left — it now states the algebraic identity, the 33,070 figure, and that a lone spike in
a panel is the base rather than the business.

### 4.2 `percent` / `ref_line` declared twice — fixed, not documented around

The growth cycle flagged that `build_growth` hardcodes `percent=True` and `add_hline(y=0)` while
`METRICS` declares both, and that they would diverge the moment an entry arrived with different
values. **This task adds 29.** `build_growth` now reads `METRICS_BY_ID`, which is what
`charts/growth.ts` has done since the React port — so the two sides now agree structurally instead of
by coincidence. All 39 entries carry `percent=True, ref_line=0`, so no figure moves (§5.4).

### 4.3 Nothing left undocumented

`config.undocumented_metrics()` returns **`[]`** for all 81 metrics, and the exported
`registry.json`'s `undocumented` array is empty. Every one of the 29 is a filed EDGAR line item whose
meaning is readable off `get_concept_candidates` and the pipeline's own use of it, so there was no
case where an honest gap was the right answer.

---

## 5. Verification

### 5.1 Non-regression on the ten previously registered concepts

Row-for-row against the pre-change `facts_full.parquet` (positional, not a key join — 22
`(ticker, concept, end)` groups are duplicated in the frame):

```
rows: 1,152,894 -> 1,152,894
row-for-row identical in ticker/concept/end/value
```

| | values |
|---|---:|
| existed before | 192,700 |
| **changed** | **0** |
| **lost** | **0** |
| newly admitted | 5,387 |

**All 5,387 newly-admitted points are explained by the removed guard**, checked individually:
reconstructing `prev = value / (1 + g)` and testing it against the *old* threshold for that concept,
5,387 of 5,387 have a base the old rule rejected. By concept: `NetIncomeLoss` 1,698, `EPS_TTM_CALC`
1,164, `FCF_TTM` 1,058, `OperatingIncomeLoss_TTM` 628, `StockholdersEquity` 469, `Revenue` 192,
`SharesOutstanding` 131, `CoreOperatingEarnings` 27, `FFO_TTM` 11, `PPNR` 9.

### 5.2 The new metrics compute what they claim

300 randomly sampled growth values re-derived by hand — find the observation nearest 365.25 days
before the period end, within ±45 days, and compute `value / prev − 1`:

```
300/300 sampled values reproduce the hand computation
```

### 5.3 The extreme-value census, with the guard off

Restricted to values that are actually **drawn** (a registered concept):

| | count |
|---|---:|
| growth values in the frame | 928,480 |
| on a registered panel | 556,227 |
| **drawn values above 200%** | 23,179 (4.17%) |
| above 500% | 9,838 (1.77%) |
| above 1,000% | 5,187 (0.93%) |
| above 10,000% | 981 (0.18%) |
| above 100,000% | **217 (0.04%)** |

**23.1% of (ticker, concept) panels — 2,656 of 11,515 — now contain at least one point above
+1,000%.**

Worst offenders:

| concept | ticker | period | growth |
|---|---|---|---:|
| `EPS_TTM_CALC` | SWK | 2020-03-28 | 25,542,473,126% |
| `SharesOutstanding` | SWK | 2021-04-03 | 19,801,084,237% |
| `EPS_TTM_CALC` | SWK | 2020-06-27 | 12,783,593,089% |
| `SharesOutstanding` | SWK | 2021-07-03 | 11,392,206,797% |
| `StockholdersEquity` | TW | 2020-03-31 | 3,502,808,900% |
| `CashAndEquivalents` | SW | 2025-03-31 | 737,962,863% |
| `CashAndEquivalents` | AMCR | 2020-03-31 | 413,692,208% |
| `IncomeTaxExpense` | LUV | 2011-06-30 | 158,333,233% |
| `Capex` | SNEX | 2018-12-31 | 140,624,900% |
| `Revenue` | LUV | 2011-06-30 | 130,555,456% |

Concepts contributing the most >1,000% points: `StockRepurchased` 991, `StockIssued` 971,
`IncomeTaxExpense` 506, `NetIncomeLoss` 350, `CashAndEquivalents` 287, `OperatingCashFlow` 279.

SWK and LUV are worth naming: a single near-zero filed value in one quarter produces a
billion-percent point that dominates its panel's y-axis for all fifteen years.

### 5.4 Export, validator and frontend

**The re-export was targeted, not a full refresh.** Nothing upstream of `yoy_growth` changed — no
fetch, no parse, no derived concept, no metric — so re-fetching 609 tickers from EDGAR would
re-derive identical inputs. What was rebuilt is what the change touches, using the pipeline's own
functions and its own ordering (`add_growth_column` after `filter_hidden_rows`, main.py:2269–2278):
`facts_full.parquet`, `facts_growth.parquet`, `registry.json`, all 1,218 per-ticker files, and
`meta.json` — then mirrored into `frontend/public/`.

| | before | after |
|---|---:|---:|
| `yoy_growth` values | 895,410 | 928,480 (+33,070 — Step 0's prediction, exactly) |
| `facts_growth.parquet` rows | 242,180 | **668,049** (2.76×) |
| per-ticker bytes | 140.5 MB | 161.6 MB (+15%) |
| `registry.json` | 80.6 kB | 121.8 kB |
| registered metrics | 52 | **81** |

**`validate_export.py`: ACCEPTED, all 38 checks pass.** The row-count floors are not endangered by a
larger export — they are floors, and every frame grew or held. One check was **already failing before
this cycle** and is now fixed: `meta.schema` read `2` while `APP_EXPORT_SCHEMA` is `4` and the
validator asserts 4. The committed `meta.json` also carried neither the `registry` nor the
`per_ticker` block that schema 3 and 4 added, although `registry.json`, `concept_candidates.json` and
`tickers/` had all been on disk beside it since the per-ticker cycle. Both blocks are now written from
measured values, as `export_for_app` writes them.

Two further cross-checks on the enlarged registry:

- `registry.json` against `config.METRICS`, field by field: **411/411**.
- `is_hidden(ticker, id)` called directly against the exported `profile_visibility`:
  **49,410/49,410** over 610 tickers × 81 metrics.

**Chart-builder A/B.** On identical code, old data against new data, **only the three growth
scenarios move**; the other 20 digests are byte-identical:

```
growth:AAPL   growth:ERIE   growth:CRM
```

That isolation had to be established separately, because a first run showed all 23 moving — the cause
was the operator's commit `fc7440c`, which edited `frontend/src/charts/panel.ts` (and eight other
frontend files) between the last baseline and this cycle. Holding the code fixed and swapping only
the data is what separates the two.

**Standing checks, with a 36-panel growth chart:**

| check | result |
|---|---|
| `check-chart-width.mjs` | **36/36** |
| `check-tab-state.mjs` | **13/13** |
| `check-table-format.mjs` | **6,107/6,107** |
| `npx vite build` | `✓ built in 11.51s` |

### 5.5 The encyclopedia renders all 81

```
1575/1575 encyclopedia DOM checks pass over 9 queries x 3 tabs
```

Every one of the 29 new entries renders with its label, id, description and formula; the rewritten
mechanism note renders with its seven bullets; and the undocumented count is **0**, verified against
the page rather than assumed.

Profile coverage: **2,687/2,688**. The single failure is `dividers 2` — the operator added a
decorative `<hr>` above the page heading in commit `fc7440c`, and the check asserts the reference's
single divider (app.py:704). Cosmetic and intentional; not touched.

---

## 6. Left open

### Nothing undocumented in the encyclopedia

All 81 metrics carry a description and a formula. `undocumented_metrics()` is empty.

### Two pre-existing frontend defects, from the operator's commit, untouched

`npx eslint .` reports **4 errors**, all in files this task does not touch and all introduced in
commit `fc7440c`:

- `ChartView.tsx:197,199` — **`useState` and `useEffect` called conditionally** after an early
  return (`react-hooks/rules-of-hooks`). This is a real bug, not a style complaint: React relies on
  hook call order being identical between renders.
- `Sidebar.tsx:94` — `setState` called synchronously inside an effect body.
- `Chart.tsx:11` — an explicit `any`.

`npx tsc -b` is clean. Reported rather than fixed: they are outside this task's scope and the first
one deserves its own look.

### The recommendation, restated

**Move the 16 sector concepts into `_DERIVED_CONCEPT_CONSUMERS`** — 16 entries instead of 357 — and
verify the `filter_hidden_rows` blast radius on the Data tab and Raw Facts chart while doing it.
Until then, every profile is offered every raw-fact panel and the sector ones draw "No Data".

### And the one that follows from §5.3

If the billion-percent points are not wanted on a shared y-axis, the fix is **not** to restore
`min_base_ratio` — that is a cap on the *data*. It is a per-panel y-axis rule in the chart layer,
which leaves the value in the frame and the export honest while keeping the panel readable. That
distinction is what the guard conflated, and the numbers in §1 and §5.3 are the case for separating
them.
