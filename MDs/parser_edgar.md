# `parsers/parse_edgar.py`

## Overview

The assembly layer between raw EDGAR extraction and the working DataFrame.

`fetchers/edgar.py` knows how to read **one** XBRL tag correctly. This module knows how to
combine several tags into one logical concept, how to repair the two kinds of corruption a
share-count series suffers, and how to turn a whole company's worth of concepts into a
table.

It contains no network code. It works on the lists of `{end, value, filed}` dicts the
fetcher returns, plus the corporate-action feed that rides along with the price history.

---

## Functions

| Function | Purpose |
|---|---|
| `extract_merged_values` | candidate tags in priority order, first hit per period wins |
| `extract_priority_merge` | ordered *sources*, where a source may itself be a sum |
| `extract_with_mode` | dispatches on `mode` |
| `merge_duplicate_period_ends` | one period tagged under two calendars becomes one row |
| `corroborated_split_events` / `_apply_split_basis` | put a share-count history on the current split basis |
| `_corroborated_scale_correction` / `_directional_scale_repair` | repair unit-scale typos, with evidence |
| `_drop_known_bad_facts` | remove named filing errors before anything reads them |
| `_mask_*` | blank values that cannot be right for a concept of that kind |
| `annual_ttm_values` / `_forms_no_ttm_window` | the second TTM path, and its gate |
| `build_dataframe` | all configured concepts for one ticker → sorted long table |

---

## The tag problem

The same financial concept does not have one stable XBRL tag.

### Tags change over time → `fallback`

Revenue was `Revenues` before ASC 606 in 2018 and
`RevenueFromContractWithCustomerExcludingAssessedTax` afterwards; during the transition
some companies reported both. `extract_merged_values` walks the candidate list in order
and keeps, per period, the value from the **first tag that has one**. Once a period is
filled, later tags cannot overwrite it — which is what makes the config's `tags` order a
priority ranking.

### Tags coexist and must be added → `sum`

Total debt is `LongTermDebtNoncurrent` + `LongTermDebtCurrent` +
`ConvertibleDebtNoncurrent` + `ConvertibleDebtCurrent`, four positions that exist
simultaneously. Fallback here would silently understate it. `LongTermDebt` is the only
concept using this mode.

### Neither is enough → `priority_merge`

The general form, and where new work should go. `sources` is an ordered list; each element
is either a single tag or a **sum of tags**, and the first source that reports a given
period end wins:

```python
{"type": "tag", "tag": "SomeTotalTag"}
{"type": "sum", "tags": ["ComponentA", "ComponentB"], "require": "ComponentA"}
```

Two things plain fallback cannot express: a source may be an aggregate assembled from
several tags, and the contest is resolved **per period end** rather than per series. A
filer that reports a total in some years and only components in others gets both, correctly
labelled, from one entry.

`require` narrows a summed source to the periods where a named tag also reports, which
stops a partially-populated component set from masquerading as a total.
`non_negative: True` drops negative values before merging.

### Two modes exist in the code and nothing uses them

`extract_with_mode` still branches on `fallback_then_sum` and `fallback_sum`. **No entry in
`config.py` sets either** — `priority_merge` replaced both. They are unreachable branches,
and earlier documentation that described `fallback_sum` as the mechanism behind
`DepreciationAndAmortization` no longer matches the config.

---

## Duplicate period ends

`merge_duplicate_period_ends` collapses two values whose ends lie within
**`_DUPLICATE_END_MAX_GAP = 7` days** of each other into the later one.

The mechanism the bound comes from: a fiscal period end is the chosen weekday nearest the
month end, so it sits at most six days from it. One reporting period tagged under two
calendars — a fiscal end from the year-to-date ladder and a calendar end from a discrete
quarterly fact — is one period, and leaving both makes a four-row TTM window straddle three
real quarters.

It runs **after the tag merge and after decumulation**, because either step can regenerate
a twin the other dropped.

---

## Share counts: two different corruptions, in a fixed order

`_SCALE_CORRECTED_CONCEPTS = {"SharesOutstanding"}`. Only this concept goes through the
repair chain, and the order inside it is load-bearing.

### 1. Split basis, from the corporate-action feed

A share count is stated on the basis in force when it was **filed**, so a filer that splits
restates the same period at the new basis in its next filing. `_restatements` finds every
period a filer reported twice; `corroborated_split_events` keeps only the feed's split
events that one of those restatements confirms — the same period at two filing dates
straddling a real split differs by *exactly* the ratio, so `_SPLIT_MATCH_TOLERANCE = 0.02`
in log space can be tight.

Two guards worth knowing:

- **Below `_MIN_SPLIT_LOG_MAGNITUDE = ln(1.2)` the event is ignored.** A stock dividend of
  a percent or two is narrower than the 2% match tolerance itself, so any small restatement
  would "confirm" it. Ignoring those leaves the count off by that percent — an order of
  magnitude below the 15% the jump flag looks for.
- **A spin-off never corroborates**, because it changes the price and not the share count.
  That distinction cannot be made from the ratio's shape: Agilent's Keysight spin-off is
  1.398 and a 7:5 split would be 1.4. Only the filer's own restatement can tell them apart.

`_apply_split_basis` then multiplies each value by the ratios of every confirmed split
filed after it. With no corroboration the factor is 1 and nothing moves.

### 2. Unit-scale repair, with corroboration

Some filers type a share count in the wrong unit. `_sweep_scale_outliers` finds values a
whole power of ten away from their neighbours; `_corroborated_scale_correction` only
applies a correction where the filer's own EPS and net income agree that the corrected
value is the right one (`_SCALE_EVIDENCE_TOLERANCE = 0.35` in log10 — a scale error is a
whole power of ten, so the gate can be loose without being wrong).

The sweep only ever *raises* a value. `_directional_scale_repair` reaches the ones that are
too large, which the sweep cannot see, using a sibling share tag as the magnitude witness
(`_SIBLING_MIN_LOG = 0.7`, about 5x — the share tags differ by a few percent, never by
this). Where a sibling establishes the magnitude the value is **rescaled in place** rather
than adopted: the sibling is a different measure of the share count (period-end rather than
weighted-average diluted), and swapping it in would put a 5–7% measurement step into the
middle of the series.

### The order is the point

**Split basis first, unit scale second.** Which basis a number is on is a property of the
filing; a scale error is a property of how it was typed. Reversed, the scale sweep absorbs
the split with the wrong factor — Chipotle's pre-split count is 50x low, and the sweep,
which only knows powers of ten, "fixes" it by 100x.

---

## Masks and known-bad facts

`_drop_known_bad_facts` removes named `(ticker, tag, end)` facts before anything reads
them. **Every entry in `_KNOWN_BAD_FACTS` names one specific filing error** — not a
heuristic, not a threshold. Do not generalise them into a rule; the point is that each was
checked against the filing.

Four masks then run on the extracted values, in `build_dataframe`:

| mask | what it blanks |
|---|---|
| `_mask_negative_flow_values` | a negative value on a flow concept that cannot be negative |
| `_mask_negative_balance_values` | the same for balance-sheet concepts |
| `_mask_known_positive_outliers` | named per-ticker outliers |
| `_mask_known_scope_mismatch_outliers` | named values tagged at the wrong scope |

They are applied to the quarterly path only. The annual-fact path skips them deliberately:
they guard decumulation artefacts, and an as-filed 12-month fact was never decumulated.

---

## The second TTM path, and why the two must stay disjoint

A 12-month fact at a fiscal year end **is** the trailing-twelve-month value at that date,
not an approximation of it. For a filer that discloses an item only once a year the
quarterly path has nothing to difference, so the rolling window has no rows at all.
`annual_ttm_values` takes such facts directly.

**The gate is on the quarterly path's *output*, not its input.** The older test was "does
any quarterly fact exist", which is too coarse for a concept reported *on occurrence*: BDX
tags 55 quarterly `DividendsPerShare` values that never form four consecutive quarters, and
their mere existence disabled the annual facts that would have produced values.
`_forms_no_ttm_window` runs `calculate_ttm` and asks whether it yields anything.

**The two paths concatenate, they do not merge.** A date reached by both would produce two
rows at one `(ticker, concept, end)` key, and `pivot_table` would silently average them
into a number neither path computed. The per-series gate is what keeps them disjoint
structurally — a series is wholly rolling-derived or wholly annual-derived — and
`ttm_source` is therefore a per-series constant. Any change here has to preserve that.

**One deliberate imprecision, and its stated justification is incomplete.** The gate is
evaluated on the *pre-mask* values, since that is where `annual_ttm_values` is called,
while `calculate_ttm` later sees them after the masks. The code comment argues this is safe
because masks only remove rows and so can only break a window, never create one. **That
reasoning does not hold**: removing a row widens the step between its neighbours, and a
widened step can move *into* the valid band from below — rows at days 0, 45, 91, 182, 273
form no window, and removing the day-45 row produces one. The conclusion still holds
empirically (measured over all 501 tickers and 25 concepts: zero cases, and no post-mask
series reaches a date its pre-mask self did not), but it holds by measurement, not by that
argument.

---

## `build_dataframe`

No concept-specific logic. For each concept in `get_concept_candidates(ticker)`:

1. `extract_with_mode` → `merge_duplicate_period_ends`
2. the annual-TTM path, **before** the `if not values: continue` skip — an empty quarterly
   extraction is exactly the case that path exists for
3. split basis → scale correction → directional repair (share counts only)
4. the four masks
5. rows appended with the **logical** concept name and a `ttm_source` of `None`

Finally `sort_values(["ticker", "concept", "end"])`. Python dicts preserve insertion order
and `extract_merged_values` fills tag by tag, so a fallback concept emits the newer tag's
periods before the older tag's — the raw output is not chronological. Every period is
present exactly once; confirming that with an explicit `duplicated()` check rather than
eyeballing is a habit worth keeping.

---

## Common pitfalls

**Losing the dict key.** When merging into a dict keyed by `end`, the date lives in the
**key**. Returning `list(merged.values())` silently drops it.

**Using the tag name instead of the logical name.** The `concept` column must hold the
stable config name (`"Revenue"`), not whichever tag supplied the data (`"SalesRevenueNet"`),
or the same concept appears under different names for different tickers.

**Forgetting to pass `period` through.** `extract_summed_values` defaults to
`period="annual"`. An earlier version called it from the quarterly branch without the
parameter, so `LongTermDebt` came back annual (12 rows instead of 45) while everything else
was quarterly. Nothing crashed; the downstream merge just produced almost nothing. That
class of bug is why `quality.py` exists.
