# Bugfix History

A running log of bugs found, what caused them, and how they were fixed. Ordered newest first.

Most entries here share a theme: **the pipeline fails silently**. A missing tag returns an empty list, an empty list produces an empty merge, an empty merge produces an empty chart. Nothing crashes. The symptom appears several layers away from the cause, and usually looks like a plotting problem. Nearly every fix below was found by noticing that a *number* looked wrong, not by reading a stack trace.

---

## 2026-07-16 — New mode `fallback_then_sum`: resolves the AAPL debt gap left open by the last fix

The previous entry's accepted trade-off ("a future company with genuinely separate debt across
multiple tags would only get the first tag") turned out not to be hypothetical. AAPL's aggregate
`LongTermDebt` tag has a six-year gap (2015-03-28 → 2021-09-25) — exactly the era of Apple's bond
issuance for buybacks — while `LongTermDebtNoncurrent` / `LongTermDebtCurrent` are gapless
throughout. Under plain `fallback`, that whole window silently dropped the current portion
(e.g. 13.5bn missing at 2019-06-29).

### The fix: per-date aggregate-first, component-sum-as-gap-filler

New mode in `extract_with_mode`:

```python
if mode == "fallback_then_sum":
    aggregate_values = extract_merged_values(us_gaap_data, cfg["tags"], period=period, is_point_in_time=is_point_in_time)
    component_values = extract_summed_values(us_gaap_data, cfg["sum_tags"], is_point_in_time=is_point_in_time, period=period)

    merged = {v["end"]: v for v in component_values}
    merged.update({v["end"]: v for v in aggregate_values})

    return sorted(merged.values(), key=lambda v: v["end"])
```

Component sums go in first, aggregates overwrite via `.update()` — so for any date where a clean
aggregate exists it always wins, and the summed components only fill dates where none of the
aggregate tags have a value. This is the same discriminant as `fallback_sum`, just evaluated
per-date instead of globally (the global all-or-nothing check would have missed AAPL entirely,
since the aggregate tags aren't *fully* empty, just gapped).

### Config split: two lists, and which tags go where matters

```python
"LongTermDebt": {
    "tags": ["LongTermDebt", "DebtLongtermAndShorttermCombinedAmount", "LongTermNotesAndLoans",
             "ConvertibleLongTermNotesPayable", "ConvertibleDebtNoncurrent",
             "ConvertibleDebtCurrent", "ConvertibleNotesPayableCurrent"],
    "sum_tags": ["LongTermDebtNoncurrent", "LongTermDebtCurrent", "NotesPayableCurrent"],
    "point_in_time": True,
    "mode": "fallback_then_sum",
},
```

Convertible tags stay in `tags` (fallback), not `sum_tags` — at NOW they carry the *entire* debt
alone under one name; summing them with anything reintroduces the double-count from the last fix.
Only the genuinely non-overlapping Noncurrent/Current/NotesPayableCurrent triplet goes in
`sum_tags`.

### Verified

- **AAPL** 2019-06-29 now reads 98,465M (= 84,936M Noncurrent + 13,529M Current, matches exactly);
  2021-09-25 reads the raw aggregate 118,700M again once it resumes — confirming aggregate wins
  over sum at the handoff point.
- **NOW** 2020-12-31 back to 1,640M (not the previous double-counted 3,280M); Convertible tag
  values pass through untouched, confirming no regression on the ticker the last fix protected.

## 2026-07-15 — LongTermDebt: sum → fallback, fixing MU, a latent NOW double-count, and ORCL

Onboarding **MU** surfaced a `LongTermDebt` coverage gap that, when chased down, revealed the
`sum` mode was the wrong tool for all of these tickers — and had been silently double-counting
**NOW** since well before this session. One config change (`sum` → `fallback`) fixed three
tickers at once. Adding **ORCL** then required extending the tag list for a different reporting
vocabulary.

### MU: components stop in 2013, aggregate takes over

`LongTermDebtNoncurrent` / `LongTermDebtCurrent` both end at 2013-05-30. From 2020 on, Micron
reports only the bare aggregate `LongTermDebt` — which the config's `sum` list did not include,
so the entire relevant era (2020–2025, debt rising 6→12bn through the memory-capex cycle) was
missing. In the 2010–2013 overlap the bare `LongTermDebt` equals `Noncurrent + Current` exactly
(e.g. 2012-08-30: 3,038M + 224M = 3,262M), so it is the same debt reported as an aggregate.

### The real discovery: `sum` was double-counting NOW

Checking whether a `fallback_sum` approach would break NOW/Meta instead revealed that NOW's
existing debt series was already wrong. NOW reports the same convertible note under *both*
`ConvertibleLongTermNotesPayable` and `LongTermDebtNoncurrent` in the 2019–2021 window, and the
`sum` mode added both:

```
2019-12-31   1,442,630,000   (should be ~694M — doubled)
2020-12-31   3,280,000,000   (should be ~1,640M — doubled)
2021-03-31   1,611,000,000   (correct again — only one tag present)
```

The original ServiceNow verification missed this because it only checked the *current edge*
(~1.49bn, where only one tag is present) against a known figure — not the middle of the series.
Lesson: "the latest value is right" does not mean "the series is right".

### Why fallback fixes all three

Laying the three tickers side by side, each reports its *entire* debt in a single consolidated
tag — nothing actually needs summing:

- **Meta** → `LongTermDebtNoncurrent` (real bonds; bare `LongTermDebt` present too, identical)
- **NOW** → `ConvertibleLongTermNotesPayable` (no bare `LongTermDebt` at all)
- **MU** → bare `LongTermDebt` (aggregate)

`fallback` takes the first tag with a value per date and never sums, so overlap-driven
double-counting is structurally impossible. Switched `mode: "sum"` → `"fallback"` with a
priority-ordered tag list (aggregate first, components last). Verified across MU/NOW/Meta run
together: NOW's 2019–2021 window now shows ~694M / ~1,640M, MU is continuous 2020–2025, Meta
unchanged.

**Trade-off accepted:** `fallback` swaps the double-count risk of `sum` for an *under*-count risk —
a future company with genuinely separate, non-overlapping debt across multiple tags (real bonds
*and* separate convertibles, both to be added) would only get the first tag. None of the current
tickers are like this, but it's the assumption the fix rests on.

### ORCL: a different tagging vocabulary

Oracle came in at 39% debt coverage — it uses none of the existing tag families. It reports under
`LongTermNotesAndLoans` / `LongTermNotesPayable` (identical, 85,297M = long-term only),
`NotesPayableCurrent` (7,271M = short-term), and `DebtLongtermAndShorttermCombinedAmount`
(92,568M). The arithmetic confirms the structure: 85,297 + 7,271 = 92,568, so the Combined tag is
the clean long+short aggregate — exactly what we want, and the same tag that had been the winner
for SoFi earlier.

Added `DebtLongtermAndShorttermCombinedAmount` and `LongTermNotesAndLoans` to the fallback list
(Combined second, right after bare `LongTermDebt`; `LongTermNotesPayable` omitted as a duplicate
of `LongTermNotesAndLoans`). ORCL now runs continuously ~2015→2026, ending ~129bn (the AI
data-centre debt build).

**Two consistency notes carried forward, not resolved:**

- `DebtLongtermAndShorttermCombinedAmount` is long+short; the bare `LongTermDebt` used for MU/Meta
  may be long-only. Small divergence (~8% for ORCL) but the concept is not perfectly uniform across
  tickers — same category as the OperatingIncomeLoss / lease-inclusion definition calls.
- Because the Combined tag is now generic, **SoFi's debt will populate** on its next run — the value
  we had deliberately left empty because deposit-funded neobank debt is ambiguous. Not broken, just
  to be read with care if SoFi is revisited.

## 2026-07-15 — Growth rates unreadable on near-zero base (IBM, CRM, NOW)

`income_yoy_growth` produced meaningless spikes across three tickers: CRM hit +3131%,
+830%, +1888% in its 2012–2021 near-zero-profit era; IBM showed +448%/+346%/+316% during
the Kyndryl-spinoff quarters; NOW spiked in 2023 as it first turned profitable. Same
category as the ServiceNow `avg_pe_5y` and Amazon P/E cases — a ratio whose denominator is
technically positive but negligibly small stops conveying information.

### The existing guard was half the fix

`calculate_growth` already masked negative bases:

```python
filtered_df["prev_value"] = filtered_df["prev_value"].where(filtered_df["prev_value"] > 0)
```

This catches sign flips (negative → positive base, where the growth rate is even directionally
wrong) but does nothing for a base that is positive yet tiny. `150M / 5M − 1 = +2900%` passes
straight through.

### The discriminant: base must be substantial *relative to* the current value

An absolute floor (`prev_value > 100M`) was rejected — arbitrary, and doesn't scale across
company sizes. The relative test scales automatically and matches the real failure mode: a
growth rate is only meaningful when *both* endpoints have a sensible magnitude.

```python
def calculate_growth(df, concept, periods, result_name, min_base_ratio=0.33):
    ...
    filtered_df["prev_value"] = filtered_df.groupby("ticker")["value"].shift(periods)

    valid_base = (
        (filtered_df["prev_value"] > 0)
        & (filtered_df["value"] > 0)
        & (filtered_df["prev_value"] >= min_base_ratio * filtered_df["value"])
    )
    filtered_df["prev_value"] = filtered_df["prev_value"].where(valid_base)

    filtered_df[result_name] = filtered_df["value"] / filtered_df["prev_value"] - 1
```

Three conditions: base positive (as before), current value positive (new — a negative current
value produces a nonsense rate the old code let through), and base ≥ 33% of the current value.

### Tuning `min_base_ratio` from the data, not from theory

The threshold was read off the real split between artefacts and genuine values, the same way
`normalize_split_adjusted` reads split factors off the data rather than assuming them.

IBM gave the cleanest separation:

```
keep  2026-03  +96%  → base/value ≈ 0.51
keep  2025-12  +76%  → base/value ≈ 0.57
kill  2023-09  +448% → base/value ≈ 0.18
kill  2024-03  +346% → base/value ≈ 0.22
```

Any threshold in 0.25–0.45 separates these. 0.33 sits mid-gap with margin on both sides.

Verified across all three problem tickers:

- **IBM** — Kyndryl-era spikes (2023-09 → 2024-06) gone; real recovery at the recent edge
  (+76%, +96%) kept; the 2018-12 +52% borderline (ratio ≈ 0.66) correctly survives.
- **NOW** — 2023 near-zero spikes gone; genuine strong jumps 2021-12 (+94%, ratio ≈ 0.52) and
  2023-03 (+79%, ratio ≈ 0.56) kept; recent edge intact.
- **CRM** — the absurd 30×-type values removed. A few borderline values survive (2023-07 +194%,
  ratio ≈ 0.34, just over the line). Unlike IBM, CRM's near-zero era spans a whole decade, so
  the artefact/genuine gap is not perfectly clean — no single threshold separates it exactly.
  Accepted deliberately: the survivors are no longer *absurd*, only *to be read with care*,
  which is true of any growth rate off a near-zero base regardless of filter.

`calculate_all_metrics` calls `calculate_growth` without the parameter — the default handles it,
no call-site change needed.

### Follow-on: reverted the growth chart from symlog to linear

The `income_yoy_growth` panel in `figures.py` had been on a symlog y-axis purely to keep the
extreme spikes on-scale. With the spikes now filtered at the source, the axis is back to plain
linear — the chart shows the real range without compression, and there is nothing left that
needs taming.

**Pragmatic threshold, not a principled one** — same spirit as `MAX_MULTIPLE = 200`. It removes
the values that break the scale and accepts that "mathematically valid but economically
meaningless" is ultimately a reading-the-chart judgement no parameter fully captures."

## 2026-07-15 — Google: two "not a bug" cases (SharesOutstanding, D&A)

Two separate investigations while onboarding **GOOG**, both resolving the same way: EDGAR
simply has fewer quarters of data for the concept than expected. No code changes required
for either.

### SharesOutstanding: correctly deduplicated, remaining gap is real

The quality check flagged 13 of 26 possible quarters for `SharesOutstanding`. The 26→13
halving itself was correct (annual and quarterly facts deduplicating as designed) — the
open question was whether the *remaining* 13 were a genuine data gap or a bug.

`explore_tags.py GOOG sharesoutstanding` surfaced `CommonStockSharesOutstanding`, an
`instant` concept (actual share count at a balance-sheet date) as opposed to the two
existing tags, which are both `duration` averages:

```python
"SharesOutstanding": {
    "tags": [
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "WeightedAverageNumberOfSharesOutstandingBasic",
        "CommonStockSharesOutstanding",   # added
    ],
    "point_in_time": True,
    "mode": "fallback",
},
```

Checked the transition point for a discontinuity, since mixing an instant value into a
weighted-average series could show up as an artificial jump:

```
2015-12-31  13,746,960,000   ← CommonStockSharesOutstanding (fallback)
2016-03-31  13,735,840,000   ← WeightedAverageNumberOfDilutedSharesOutstanding
```

Difference: ~11M on a base of 13.7bn (<0.1%). No jump. `extract_merged_values` already
merges per-date across the tag list (not per-series), so this fallback only ever fires for
the individual dates that are missing — the same mechanism already in place for
Diluted → Basic.

**Result:** tag added, gap closed back to 2014. No tracking of "which tag won" was added —
considered, but the per-date merge already bounds the risk, and no discontinuity showed up
in the one case that could have produced one.

### DepreciationAndAmortization: 13 quarters is correct, not a coverage bug

`fallback_sum` (`Depreciation` + `AmortizationOfIntangibleAssets`) produced only 13 rows,
starting exactly at 2023-03-31, despite both tags being present. Looked like the
all-or-nothing check in `extract_with_mode` (`if mode == "fallback_sum" and not values`)
might be swallowing a partial main-tag result — but the three main tags
(`DepreciationDepletionAndAmortization`, `DepreciationAndAmortization`,
`DepreciationAmortizationAndAccretionNet`) are `NICHT VORHANDEN` for GOOG entirely, so that
code path was never in play.

Raw `Depreciation` facts show why the fallback still stops at 2023:

```
2021-01-01 → 2021-12-31   annual only, no matching quarter start
2022-01-01 → 2022-12-31   annual only, no matching quarter start
2023-01-01 → 2023-03-31   first quarterly entry
```

The `quarter_starts` discriminant in `decumulate_period_values` (from the 2026-07-13 Amazon
fix) requires at least one real quarter sharing a fiscal year's start date before it will
decumulate that year's annual figure. 2021 and 2022 have none — Google only began
quarterly-granular `Depreciation` disclosure in Q1 2023. The filter is doing exactly what
it was built to do.

Quarter count checks out exactly: 4 (2023) + 4 (2024) + 4 (2025) + 1 (2026 Q1) = 13.

**Considered and rejected:** adding `FinanceLeaseRightOfUseAssetAmortization` as a
`fallback_sum_tags` entry.

- Earliest entry is `2022-01-01 → 2022-12-31`, itself annual-only with no matching quarter
  start — would not close the 2021/2022 gap either.
- Magnitude is marginal: ~413M vs. 15,311M `Depreciation` for FY2024, ~2.7%.
- Open conceptual question, not just a data question: whether finance-lease amortization
  belongs in this project's EBITDA definition at all (same category of decision as the
  Meta lease-exclusion call on 2026-07-13). Not resolved here — no clear win to justify
  answering it under time pressure for a <3% effect.

**No fix applied.** GOOG simply discloses `Depreciation` annually-only before 2023, same
category as the Reddit and Meta "not a bug" entries above.

## 2026-07-14 — Apple: missing D&A tag

`DepreciationAndAmortization` coverage for AAPL was 46% (34 of 74 quarters). The existing tags (`DepreciationDepletionAndAmortization`, `DepreciationAndAmortization`) only start in 2015.

`explore_tags.py AAPL depreciation amortization` found `DepreciationAmortizationAndAccretionNet` — a tag none of the other five tickers use.

Checked the date ranges before adding it, to rule out overlap-driven double counting:

```
DepreciationAmortizationAndAccretionNet:  2007 – 2018   (old tag)
DepreciationDepletionAndAmortization:     2015 – 2026   (current tag)
```

A clean tag transition with a multi-year overlap. Added to `tags`, after the current tag, so the newer figure wins during the overlap:

```python
"tags": [
    "DepreciationDepletionAndAmortization",
    "DepreciationAndAmortization",
    "DepreciationAmortizationAndAccretionNet",
],
```

Coverage now extends back to 2007. EV/EBITDA for AAPL is available for the full history instead of only the last ~9 years.

---

## 2026-07-14 — Reddit: no debt is not a bug

Adding **RDDT** flagged `LongTermDebt` as missing (0 of 15 quarters). Unlike Meta or ServiceNow, this is not a missing tag.

`explore_tags.py RDDT debt notes borrowings` returned only `AvailableForSaleDebt...` tags — securities Reddit *holds* as part of its cash investments, not debt it *owes*. None of the usual liability tags (`LongTermDebtNoncurrent`, `NotesPayable`, `ConvertibleDebt`) exist at all.

`explore_tags.py RDDT lease` confirmed Reddit does carry `OperatingLeaseLiability` (office/datacenter leases), but no interest-bearing financial debt. Reddit went public in 2024 and appears to carry no bonds or credit facilities — plausible for a company funded by its own IPO.

**No fix applied.** This surfaces a limitation of an existing decision rather than a new bug.

The Meta entry (2026-07-13) deliberately excluded lease liabilities from `LongTermDebt`, for consistency: the concept should mean the same thing — interest-bearing financial debt — for every ticker. At Meta this was a minor simplification, because Meta also carries real bonds; leases were a small addition either way.

For Reddit the same convention has a sharper consequence: `LongTermDebt` will read as permanently zero, and `debt_to_equity` / `net_debt_to_ebitda` will imply "debt-free" even though Reddit's operating lease liabilities are non-trivial. That is a true statement about *financial* debt and a misleading one about total obligations, depending on which question is being asked.

Kept the convention as-is rather than special-casing it. Any ticker whose only liabilities are leases will show the same pattern — worth recognizing on sight rather than re-investigating each time.

## 2026-07-13 (update) — Tag discovery tooling

Not a bug. A workflow that was being done by hand, six times, made repeatable.

### The problem

Every time the data quality check flagged a missing or thin concept, the next step was identical: comment a debug block into `load_facts()`, run the whole pipeline, read the tag list, comment it out again.

```python
if ticker == "AMZN":
    for key in company_info["facts"]["us-gaap"].keys():
        if "Depreciation" in key or "Amortization" in key:
            print(key)
```

Six tickers, six variations of the same three lines. The pattern was stable enough to extract.

### `search_tags()` in `quality.py`

```python
def search_tags(company_info: dict, keywords: list[str]) -> list[str]:
    lower_cased_keywords = [word.lower() for word in keywords]
    tags = []

    for key in company_info["facts"]["us-gaap"].keys():
        key_lower = key.lower()
        if any(word in key_lower for word in lower_cased_keywords):
            tags.append(key)

    tags.sort()
    return tags
```

Case-insensitive on both sides — `"debt"` has to match `ConvertibleDebtNoncurrent`. The **original** tag name goes into the result list, not the lowercased comparison string: the point of the search is to get a name that can be pasted into `CONCEPT_CANDIDATES`.

`any(...)` rather than an inner loop with `break`, so a tag matching several keywords (`DepreciationAndAmortization` against `["depreciation", "amortization"]`) is only appended once.

### `explore_tags.py`

A standalone script, not part of the pipeline:

```bash
python explore_tags.py AMZN depreciation amortization
```

**Deliberately not interactive.** The original idea was to have the quality check prompt for keywords when it detects a problem. Rejected for two reasons:

- **It blocks.** Any unattended run (cron, CI, or just walking away from the terminal) would hang on `input()` forever.
- **It mixes modes.** `main.py` is a batch program: data in, charts out. Tag discovery is a diagnostic — done once, deliberately, *after* something has gone wrong.

Command-line arguments give the same convenience without either problem.

### `SEARCH_HINTS` in `config.py`

Closes the loop. The quality report now emits the command it wants you to run:

```
FEHLT  AMZN   DividendsPerShare                  0 von  77 (0%)
       → python explore_tags.py AMZN dividendspershare
```

The hints map each concept to the keywords that have historically found it:

```python
SEARCH_HINTS = {
    "LongTermDebt": ["debt", "notes", "borrowings"],
    "DepreciationAndAmortization": ["depreciation", "amortization"],
    "Capex": ["acquire", "propertyplant"],
    ...
}
```

`print_data_quality` takes them as a parameter rather than importing them, so `quality.py` stays independent of the project config — the same rule that applies to `expected_concepts`.

### Known limitation

The suggestion fires on every warning, including the ones that aren't problems. Amazon doesn't pay a dividend, so `DividendsPerShare` at 0% is correct — but the report still offers to go looking for a tag.

Suppressing those would mean maintaining a list of known-absent concepts per ticker. Not done, on purpose: a silenced warning is a warning that won't fire when it *is* real for the next ticker. The cost of the false positive is one glance.

## 2026-07-13 (later) — Amazon

Adding **AMZN** produced a P/E of 216 (real value ~30) and a five-year average P/E of **−41.6**. A negative average P/E is not a number that can exist.

The data quality check reported three concepts missing entirely:

```
FEHLT  AMZN   OperatingCashFlow             0 von 77 (0%)
FEHLT  AMZN   Capex                         0 von 77 (0%)
duenn  AMZN   DepreciationAndAmortization   9 von 77 (12%)
```

But the tags themselves were all present in the EDGAR data and all already configured. The extraction was silently dropping everything.

### The root cause: an end date does not identify a period

Amazon reports **three different period types in parallel** for the same concept:

```
2025-01-01 -> 2025-06-30   180 days   YTD (cumulative)
2025-04-01 -> 2025-06-30    90 days   the actual quarter
2024-07-01 -> 2025-06-30   364 days   a rolling twelve-month window
```

All three end on 30 June 2025. All three are legitimate, distinct facts.

`extract_period_values` deduplicated by `end` date alone:

```python
values[end_date] = {...}   # later filed date wins
```

So of the three, only one survived — and systematically the wrong one, because the rolling window appears in later filings and therefore wins the `filed` comparison.

The result: after extraction, **every single entry had annual length**. Not one real quarter made it through. `decumulate_period_values` then had nothing to work with and returned an empty list. Downstream, FCF, EBITDA and every dependent ratio were built on nothing.

This bug had existed since the original quarterly conversion. It never caused harm because AAPL, MSFT, NVDA, WMT, JPM and NOW happen not to report overlapping period types. Amazon does.

**Fix**

Deduplicate by `(end, days_diff)` instead of `end`:

```python
key = (end_date, days_diff) if not is_point_in_time else end_date
```

Point-in-time values keep `end` alone as the key — a balance sheet date has no duration, so there is nothing to disambiguate.

Length distribution for the same concept, before and after:

```
before:  {364: 54, 365: 19}                              ← no quarters at all
after:   {89: 14, 90: 22, 91: 18, 180: 13, 181: 5,
          272: 13, 273: 5, 364: 54, 365: 19}             ← 54 real quarters
```

### The second problem: rolling twelve-month windows

With deduplication fixed, the rolling windows now survive extraction — and immediately break `decumulate_period_values`, which groups by `start` date.

A rolling window like `2025-04-01 → 2026-03-31` shares its `start` with the real quarter `2025-04-01 → 2025-06-30`. The function sees two entries in one `start` group, assumes they are cumulative stages, and computes `148,531 − 32,515 = 116,016` as a "quarterly value". Nonsense.

They also fall inside the 350–380 day band and get treated as annual values, poisoning the Q4 derivation as well.

**Fix**

Discard them before grouping. The discriminant is generic and needs no knowledge of the fiscal calendar:

> **A real fiscal year starts where a quarter starts.** Q1 shares its `start` date with the full year. A rolling window does not.

```python
quarter_starts = set()
for v in entries:
    days = (date.fromisoformat(v["end"]) - date.fromisoformat(v["start"])).days
    if 80 <= days <= 100:
        quarter_starts.add(v["start"])

cleaned = []
for v in entries:
    days = (date.fromisoformat(v["end"]) - date.fromisoformat(v["start"])).days
    if 350 <= days <= 380 and v["start"] not in quarter_starts:
        continue
    cleaned.append(v)
```

Companies that do not report rolling windows are unaffected — their annual values always start where Q1 starts.

**Result**

| | before | after |
|---|---|---|
| P/E | 215.1 | **29.6** |
| avg P/E (5y) | −41.6 | **36.1** |
| EV/EBITDA | 20.5 | **17.2** |
| PEG | 15.1 | **2.08** |

---

## 2026-07-13 — Meta

### Missing debt tag variant

`LongTermDebt` came in at 35% coverage. Meta uses `NotesPayableCurrent` for the short-term portion of its bonds, which was not in the tag list.

**Fix:** added `NotesPayableCurrent` to the `LongTermDebt` summation list.

**Deliberately not added:** the bare `LongTermDebt` tag, which Meta also reports as a combined figure. With `mode: "sum"` it would be added to its own components and double the debt.

**Also deliberately excluded:** `FinanceLeaseLiability` and `OperatingLeaseLiability`. Meta carries substantial data-centre leases. Whether leases count as "debt" is a matter of analytical convention, not a data problem — for consistency across tickers, `LongTermDebt` here means interest-bearing financial debt only.

### Not a bug

`DividendsPerShare` at 15% coverage (9 of 62 quarters) is correct. Meta only started paying a dividend in Q1 2024.

Also verified as real: debt jumping from 28.8bn to 58.7bn in a single quarter. That is Meta's October 2025 bond issue — 30bn, the largest corporate bond in US history, to fund AI infrastructure.

---

## 2026-07-13 — ServiceNow

Four distinct bugs, all surfaced by the same ticker.

### 1. Missing concept crashes `build_valuation_history`

**Symptom**
```
KeyError: 'DividendsPerShare_TTM'
```

**Cause**
ServiceNow pays no dividend, so `DividendsPerShare` has zero rows. `pivot_table` only creates columns for concepts that have data — so the column did not exist at all, rather than existing and being full of `NaN`.

This would have happened for any missing concept.

**Fix**
Fill missing columns with `pd.NA` after the pivot:

```python
for concept in needed:
    if concept not in wide.columns:
        wide[concept] = pd.NA
```

The affected multiple becomes `NaN`, gets removed by the final `dropna`, and the chart correctly shows "keine Daten".

---

### 2. Debt understated — missing tag variants

**Symptom**
`LongTermDebt` at 17% coverage (11 of 63 rows).

**Cause**
ServiceNow names its convertible notes `ConvertibleLongTermNotesPayable` / `ConvertibleNotesPayableCurrent` — not `ConvertibleDebtNoncurrent` / `ConvertibleDebtCurrent`, the only convertible tags in the config.

**Fix**
Added both tags to the `LongTermDebt` summation list. Verified afterwards that the total lands at ~1.49bn, matching ServiceNow's actual debt — no double counting from overlapping tag families.

**Note:** `mode: "sum"` always carries double-counting risk when adding tag variants. Check the magnitude against a known figure before trusting it.

---

### 3. Share count oscillating between two bases (stock split)

**Symptom**

```
2023-09   205,194,000
2023-12 1,027,953,000   ← ×5
2024-03   207,684,000
2024-12 1,042,113,000   ← ×5
2025-03 1,046,852,000   ← ×5
2025-06   209,343,000
```

Downstream this broke market cap, and with it P/B, P/FCF, EV/Sales and EV/EBITDA. The raw `EPS` concept also went **negative while net income was positive**, which is impossible.

**Cause**

ServiceNow executed a **5:1 stock split in 2025**. The raw filings show it plainly:

```
val:   208,423,000   filed: 2025-01-30   (FY2024 10-K)
val: 1,042,113,000   filed: 2026-01-29   (FY2025 10-K, restating FY2024)
```

Same period, same form, same unit — two different values. The later one is the correct, split-adjusted restatement.

The deduplication logic was working correctly. The problem is that EDGAR only restates the periods that appear as **comparatives** in the newest filing. Everything older keeps its pre-split values from the original 10-Qs. The series ends up with two incompatible bases interleaved.

The negative EPS came from the same source: `decumulate_period_values` subtracting three pre-split quarters from a post-split annual figure.

**Two false starts, worth recording:**

- **Outlier filter (rolling median).** Discarded. It cannot distinguish a data error from a real split, and at ServiceNow the "wrong" values are in the *majority* at the recent end of the series — so the median locks onto them. Worse: it would have thrown away the *correct* restated values and kept the stale ones.
- **Deriving share count as `NetIncome / EPS`.** Circular. `EPS_TTM_CALC` is computed as `NetIncome / SharesOutstanding`; deriving shares from EPS just recovers the original corrupted EPS.

**Fix**

`normalize_split_adjusted()` in `metrics.py`. It rescales the entire series onto the basis of the **most recent** value — which always comes from the newest filing, and therefore matches the fully split-adjusted price series from yfinance.

For each value, it tests a list of common split factors (2, 3, 4, 5, 10, …) and picks the one that brings it closest to the anchor:

```python
anchor = values.iloc[-1]
for f in COMMON_SPLIT_FACTORS:
    for candidate in (v * f, v / f):
        err = abs(np.log(candidate / anchor))
```

The logarithm makes ×5 and ÷5 symmetric. Factor 1 is in the list, so a ticker with no split passes through untouched.

This works because a real share count moves by a few percent per quarter (buybacks, option exercises) but never by 400%. Any jump of a clean factor is a basis change, not a business event.

**Consequence:** the raw `EPS` concept is no longer needed. `EPS_TTM_CALC = NetIncomeLoss_TTM / SharesOutstanding` uses two split-consistent absolute quantities. Removed `EPS` from `CONCEPT_CANDIDATES`.

**Known limitation:** the method assumes the true share count does not change by more than roughly ±50% across the series. A company that has bought back most of its shares over a very long history could have an early value misread as a split.

---

### 4. `avg_pe_5y` meaningless (247) — near-zero denominators

**Symptom**

After fixing the split issue, the P/E series was smooth but the five-year average came out at **247** — useless as a reference line.

**Cause**

ServiceNow only became profitable around 2019. In those quarters, `NetIncomeLoss_TTM` was barely above zero, so P/E exploded:

```
2019-06   21,732
2019-09    1,427
2021-03      660
2022-06      525
```

The existing `.where(EPS > 0)` mask only catches *negative* earnings. It does nothing for earnings that are positive but negligible.

A P/E of 500 is not "very expensive". It means the company barely earns anything, and the metric has stopped conveying information about valuation.

**Fix**

Cap all valuation multiples at 200 in `build_valuation_history` and `calculate_historical_pe`:

```python
MAX_MULTIPLE = 200
for col in ["pe_ratio", "pb_ratio", "pfcf_ratio", "ev_ebitda", "ev_sales"]:
    wide[col] = wide[col].where(wide[col] <= MAX_MULTIPLE)
```

`dividend_yield` is excluded — it has no meaningful upper bound in that range.

This is a pragmatic threshold, not a principled one. The defensible version would mask based on the *denominator* (e.g. discard P/E when net margin < 1%), but the outcome is nearly identical and the added complexity isn't worth it.

**Follow-on fix:** `calculate_rolling_average` returned `NaN` for the whole window as soon as a single masked value fell inside it — pandas' default `min_periods` equals the window size. Set `min_periods=1` so the average is computed from whatever valid values exist.

**Trade-off:** young companies now get a "5-year average" based on fewer than 20 quarters. More useful than no value at all, but it should be read with that in mind.

**Result:** `avg_pe_5y` for NOW went `NaN` → `247` → **104.9**, which is a usable reference.

---

## Earlier fixes

Documented inline in the module docs rather than here, because they shaped the architecture rather than patching it:

| Bug | Module doc |
|---|---|
| The `fp` field mislabels quarters as `FY` | `edgar_doc.md` |
| Cash flow items reported cumulatively (YTD) | `edgar_doc.md` |
| Q4 never filed separately | `edgar_doc.md` |
| Multiple units per concept (`pure` vs `USD/shares`) | `edgar_doc.md` |
| Tag changes over time (ASC 606) | `parse_edgar_doc.md` |
| D&A split into components at Microsoft | `parse_edgar_doc.md` |
| `period` parameter not passed through in `sum` mode | `parse_edgar_doc.md` |
| Single quarters distorted by one-off events | `metrics_doc.md` |
| Growth rates exploding on negative base | `metrics_doc.md` |
| Missing concepts invisible to the quality check | `quality_doc.md` |

---

## Pattern

Seven tickers, seven different failure modes. Almost none of them crashed; all of them produced plausible-looking wrong numbers.

What consistently worked:

1. **Notice that a number is impossible**, not merely surprising. A negative average P/E. A negative EPS with positive net income. A share count that quintuples and then reverts.
2. **Look at the raw filings**, not the derived DataFrame. Every one of these bugs was visible in the EDGAR JSON and invisible in pandas.
3. **Find the discriminant.** Every successful fix here rests on one structural property that separates good data from bad — period length, start-date alignment, proximity to a split factor. Heuristics applied to the *output* (outlier filters, thresholds) mostly failed. Rules derived from the *structure of the input* held.