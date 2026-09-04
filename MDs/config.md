# `config.py`

## Overview

All configuration lives here. No other module hardcodes tickers, tag names, paths, metric
labels or chart layout.

Two things share the file, and they are independent:

1. **`CONCEPT_CANDIDATES`** and its override layers — which XBRL tags carry which logical
   concept, and how several tags combine into one.
2. **The `METRICS` registry** — every metric the project plots, with its label, formula,
   chart, and encyclopedia text. This is the single source of truth for everything
   rendered; the structures `figures.py` imports are *derived* from it at the bottom of the
   file.

Adding a concept or supporting a new company means editing (1). Adding a metric means
adding one entry to (2) and nothing else.

---

## Settings

| Name | Purpose |
|---|---|
| `TICKERS` | The **development** list — two tickers. `main()` uses it; the nightly run does not. |
| `get_active_tickers()` | The real universe (~501). This is what `run_full_refresh` iterates. |
| `EDGAR_USER_AGENT` | Required by SEC. Must contain a real name and email, or requests are rejected with 403 |
| `PERIOD` | `"quarterly"` or `"annual"` — controls the entire extraction pipeline |
| `SNAPSHOT_AS_OF_DATES` | Historical snapshot cutoffs for `main()`; empty by default |
| `CONCEPT_CANDIDATES` | Tag mapping and combination strategy per concept |
| `TTM_CONCEPTS` | Which concepts get a trailing-twelve-month series |
| `TICKER_PROFILES` / `DEFAULT_PROFILE` | Which business profile each ticker belongs to |
| `PROFILE_HIDDEN` | Per profile, which metrics are **not** shown |
| `PROFILE_CONCEPT_OVERRIDES` / `TICKER_CONCEPT_OVERRIDES` | Per-profile and per-ticker tag lists |
| `PROFILE_EXCLUDED_CONCEPTS` | Concepts a profile is not expected to report at all |
| `SEARCH_HINTS` | Keywords `quality.py` prints for a missing concept |
| `TTM_SOURCE_*` / `FFO_GAINS_*` | The provenance labels that travel with a value |
| `CACHE_DIR` / `DATA_DIR` / `FIGURE_DIR` | Output paths |

**`TICKERS` is not the universe.** It holds two tickers and exists so `main()` is a fast
development loop. Any script that measures the project must call `get_active_tickers()`.

---

## `CONCEPT_CANDIDATES`

```python
"<logical name>": {
    "tags": [...],            # priority order, or the addends when mode == "sum"
    "sources": [...],         # only when mode == "priority_merge"
    "point_in_time": bool,
    "mode": "fallback" | "priority_merge" | "sum",
    "non_negative": bool,     # priority_merge only
}
```

### `tags` — order matters

A priority ranking, not a set. For each period the extraction takes the value from the
**first tag that has one** and ignores the rest. Put the current or preferred tag first:
`RevenueFromContractWithCustomerExcludingAssessedTax` (post-2018) before `Revenues`
(pre-2018) before `SalesRevenueNet` (legacy).

### `point_in_time`

`False` — a **period** value covering a span (revenue, income, cash flow). Additive; gets
decumulated and Q4-derived.

`True` — a **balance-sheet** value at a single date (equity, debt, cash). Not additive;
taken as reported.

**`SharesOutstanding` is `True` despite being a period average.** Share counts must never
be summed across quarters (four times the real count) nor differenced (the difference
between two similar averages is meaningless). `point_in_time` bypasses both.

### The three modes that are actually used

**`fallback`** (85 entries) — first tag that has data for the period. The default when
`mode` is absent.

**`priority_merge`** (16 entries) — the general form, and the one to reach for now.
`sources` is an ordered list where each element is either

```python
{"type": "tag", "tag": "SomeTag"}
{"type": "sum", "tags": ["A", "B"], "require": "C"}      # `require` optional
```

and the **first source that reports a given period end wins**. Two things `fallback`
cannot do: a source may be a *sum of several tags* rather than one tag, and the merge is
resolved **per period end**, so a filer that reports a total in some years and only
components in others gets both. `require` narrows a summed source to the periods where a
named tag also reports, which is how a partial component set is kept from masquerading as
a total. `non_negative: True` drops negative values before merging.

**`sum`** (1 entry) — add all tags together, for parts that genuinely coexist.
`LongTermDebt` is the only one: total debt = long-term + current + convertible long-term +
convertible current. Fallback here would silently understate it.

### Two modes exist in the code and are unreachable

`extract_with_mode` still handles `fallback_then_sum` and `fallback_sum`, and **no entry in
this file uses either** — `priority_merge` supersedes both. They are dead branches, not
configuration options; earlier documentation described `fallback_sum` as the mechanism
behind `DepreciationAndAmortization`, which is no longer how that concept is assembled.

### The override layers replace, they do not merge

`get_concept_candidates(ticker)` applies base → profile → ticker, and **each layer replaces
a concept's whole entry**. A ticker override that adds one tag to a concept therefore
discards every other tag the profile listed, and pins that filer to the list as it stood
the day the override was written. Widen the profile entry instead, unless the filer really
is an exception.

---

## Profiles and `is_hidden`

A REIT is not valued on earnings and a bank has no inventory, so showing every metric for
every company would mean showing numbers that do not mean anything.

`PROFILE_HIDDEN` is a **negative** list: a metric is shown unless its profile hides it.
`is_hidden(ticker, metric)` is the single authority, and every consumer routes through it —
`figures._select_concepts`, `config.get_plottable_metrics`, `filter_hidden_rows`, and the
comparison chart's exclusion list.

`_DERIVED_CONCEPT_CONSUMERS` maps a derived concept to the profiles that consume it, so a
sector aggregate resolves to the right profiles without a hide entry per profile.
Registering the raw sector tags instead would have cost 22–23 entries each. It is also
what fixed the REIT PEG: `pe_to_revenue_growth` was not listed as a `pe_ratio` consumer, so
the reit profile published a PEG whose numerator it had itself decided was not meaningful.

`_ROW_ABOUT_SUFFIXES` is the other half of "single authority": a row can be *about* a metric
rather than be one, and a profile that hides the metric hides those too. `_quarterly` was
always there; `_age_days` and `_stale_days` joined it when the snapshot's staleness guard
started publishing them. Without the strip, 190 of that guard's 429 markers would land on
fields their own profile hides — 61 of them `avg_p_tbv_5y`, which most profiles hide outright.
Adding the two suffixes leaves `profile_visibility()` byte-identical, because that export is
keyed by metric id and no id ends in either.

---

## `TTM_CONCEPTS`

Concepts listed here get an additional `<name>_TTM` series.

Single quarters are extremely sensitive to one-off events. Microsoft's Q4 2012 was a *loss*
because of the aQuantive write-off; operating margin or ROE from that one quarter gives
values like −1100% — correct and useless. A trailing-twelve-month figure absorbs it across
three normal quarters. Every ratio metric is therefore built on `_TTM` concepts, with pure
balance-sheet ratios (`debt_to_equity`) the exception.

**Note which concepts are absent:**

- **`EPS`** — per-share. Summing four quarterly EPS figures breaks across splits, because
  EDGAR restates per-share numbers retroactively but not uniformly. `EPS_TTM_CALC` is
  computed instead as `NetIncomeLoss_TTM / SharesOutstanding`, both absolute.
- **`SharesOutstanding`** — must never be summed.
- **`StockholdersEquity`, `LongTermDebt`, `CashAndEquivalents`** — balance-sheet positions.

`DividendsPerShare` **is** in the list and has the same per-share split problem as EPS. It
stays because EDGAR has no absolute equivalent to reconstruct it from; negatives are masked
downstream.

### The provenance labels

`TTM_SOURCE_ROLLING` / `TTM_SOURCE_ANNUAL` record *how* a `_TTM` value was derived — four
quarters summed, or one 12-month fact taken as filed. A series that mixes the two is not
uniform and must not look uniform, so the label travels with the value in the facts frame's
`ttm_source` column and the app renders it as a cadence marker.

`FFO_GAINS_REPORTED` / `FFO_GAINS_IMPUTED_ZERO` do the same job for FFO's real-estate-gains
term, which is zero-filled for roughly 77% of REIT periods. See `MDs/main.md`.

---

## The `METRICS` registry

```python
Metric(id=..., label=..., chart=..., ref_line=..., percent=..., quarterly=...,
       harmonic=..., description=..., formula=...)
```

**Add a metric here and nowhere else.** Everything below `METRICS` in the file is derived:

| derived | shape | consumer |
|---|---|---|
| `FUNDAMENTALS_TO_PLOT` | `(id, label, ref_line, percent, False)` | `figures.build_fundamentals` |
| `VALUATIONS_TO_PLOT` | `(id, label, ref_line, percent)` | `figures.build_valuation` |
| `GROWTH_PANELS` | `(id, label)` | `figures.build_growth` |
| `QUARTERLY_COUNTERPART` | `{id: id_quarterly}` | the dual-line fundamentals panels |
| `HARMONIC_MEAN_CONCEPTS` | `{id, ...}` | the `avg_*_5y` means and the peer bands |
| `METRICS_BY_ID` | `{id: Metric}` | `figures._concept_plot_spec`, the encyclopedia |

The fifth element of the fundamentals 5-tuple is a constant `False`. It was a symlog flag,
no metric ever set it and nothing renders it; the tuple keeps its width so the shape stays
what `figures.py` has always unpacked.

`CHART_SPECS` declares, per chart, what an id *names* and which dataframe column holds its
values — `fundamentals`/`valuation` ids are **metric names** read from `value`, `growth`
ids are **XBRL concept names** read from `yoy_growth`. Declared once rather than repeated on
45 entries, and reachable per metric via `Metric.id_namespace` / `Metric.value_column`.

`_index_metrics` raises on a duplicate id at import, which is what makes an id globally
unique and lets `figures.concept_source` route a concept to its frame without a precedence
rule.

### Functions over the registry

| Function | Purpose |
|---|---|
| `get_plottable_metrics(chart, ticker=None)` | `(id, label)` pairs, already filtered by `is_hidden` |
| `profile_visibility(chart=None)` | `{profile: {id: bool}}`, what the coverage page draws |
| `undocumented_metrics()` | ids with no `description`/`formula`, surfaced in the encyclopedia |
| `Metric.label_for(language=...)` | a **method**, not a module function: the rendered label |

`label` is what appears on a chart and must stay byte-identical; some entries mix German
words, preserved verbatim. Relabelling is a separate job.

`description` and `formula` are optional with a `None` default, so every derived structure
keeps its shape — but optional means a new metric can arrive undocumented, which is what
`undocumented_metrics()` exists to catch. `formula` names the concepts and period basis the
pipeline **actually** uses, never the textbook definition; several deliberately differ.

---

## Adding a new ticker

Add it to the universe and run. `quality.py` reports any concept that is missing or thinly
populated for that company, with a ready-to-run `explore_tags.py` line.

Two things it may reveal:

**Missing tags** — the company uses a tag not yet listed. Find it, then add it to the
appropriate `tags` list or `sources` entry.

**Structurally absent concepts** — the company genuinely does not report the item. Banks
have no `OperatingIncomeLoss`, no `Capex` and no `LongTermDebt` in the conventional sense.
No amount of tag hunting fixes that; put the ticker on the right profile instead, and let
`PROFILE_EXCLUDED_CONCEPTS` stop the coverage warning from reporting a gap no tag can
close.
