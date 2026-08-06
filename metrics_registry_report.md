# `METRICS` Registry — Report

**Date:** 2026-08-05
**Touched:** `config.py` (registry + derived layer + accessor) and `figures.py` (`_concept_plot_spec` only, plus two names added to its existing `config` import). No Streamlit code, no Phase 4, no change to `PROFILE_HIDDEN` / `is_hidden` / `_DERIVED_CONCEPT_CONSUMERS`, no new metrics, no relabelling, no `SharesOutstanding` fix. **No consumer outside `_concept_plot_spec` was migrated.**

---

## Step 1 — Registry shape

### The entry type

```python
@dataclass(frozen=True)
class Metric:
    id: str
    chart: str                       # CHART_FUNDAMENTALS | CHART_VALUATION | CHART_GROWTH
    label: str                       # the string rendered today, byte-identical
    ref_line: float | int | None = None
    percent: bool = False
    quarterly: bool = False          # a <id>_quarterly series exists
    harmonic: bool = False           # mean line uses the harmonic mean
    label_de: str | None = None
```

**Frozen dataclass, not `TypedDict` or a plain dict.** The brief asked for whatever fails loudest on a missing or typo'd field, and only the dataclass fails at all *at runtime*:

| mistake | plain dict | `TypedDict` | frozen dataclass |
|---|---|---|---|
| missing `label` | `.get("label")` → `None` → blank axis at render | type-checker only | `TypeError: missing 1 required positional argument: 'label'` at import |
| typo `refline=0` | silently a new key, `ref_line` stays `None` | type-checker only | `TypeError: unexpected keyword argument 'refline'. Did you mean 'ref_line'?` |
| mutated at runtime | allowed | allowed | `FrozenInstanceError` |

All four behaviours are demonstrated in the verification. `frozen=True` also means a consumer cannot accidentally edit the catalogue that every chart is built from.

**`chart` replaces "which list is it in"**, with module constants (`CHART_FUNDAMENTALS`, `CHART_VALUATION`, `CHART_GROWTH`) so a typo'd chart name is caught by the index builder rather than silently producing an entry that no derivation ever picks up.

### Id namespace and value column

Declared once in `CHART_SPECS`, reachable per metric as a property:

```python
CHART_SPECS = {
    CHART_FUNDAMENTALS: {"id_namespace": "metric",       "value_column": "value"},
    CHART_VALUATION:    {"id_namespace": "metric",       "value_column": "value"},
    CHART_GROWTH:       {"id_namespace": "xbrl_concept", "value_column": "yoy_growth"},
}
```

This is the namespace difference the brief flagged: fundamentals and valuation ids are *metric names* (`fcf_margin`, `pe_ratio`), growth ids are *XBRL concept names* (`Revenue`, `NetIncomeLoss`, `SharesOutstanding`). Today that fact is invisible — it is implied by list membership and re-derived inside `_concept_plot_spec`, which hardcodes `"yoy_growth"` in its growth branch. Now `METRICS_BY_ID["Revenue"].id_namespace == "xbrl_concept"` and `.value_column == "yoy_growth"` are answerable without knowing anything about lists, so a picker can label the growth chart's options correctly instead of hardcoding the distinction into widget code.

It is declared per *chart* rather than per *metric* deliberately: repeating the same two strings on 45 entries invites exactly the drift this task exists to remove, and the property keeps per-metric access.

### Labels and language

`label` is the primary language (`LANGUAGE_PRIMARY = "en"`) and holds **byte-identical** today's strings — including their inconsistencies, which are preserved verbatim because relabelling is out of scope: `"dividend yield"` stays lowercase, and the three growth labels keep their German `"Quartal"` (`"Revenue growth (Quartal, YoY)"`).

`label_de` is the optional second language, and **every entry has it as `None`.** There is no existing German label set in the project to carry over, and the brief is explicit that an empty field is honest where a machine translation is not. The mechanism is built and proven; the content is a separate decision.

```python
def label_for(self, language: str = LANGUAGE_PRIMARY) -> str:
    if language != LANGUAGE_PRIMARY:
        translated = getattr(self, f"label_{language}", None)
        if translated:
            return translated
    return self.label
```

A consumer requests a language by string. A missing translation — whether the field is `None` or the language has no field at all (`"fr"`) — **falls back to the primary label, never to an empty string**, so a missing translation can never blank an axis title. `getattr` rather than a dict lookup means adding `label_fr` later needs no change here.

### `quarterly` and `harmonic` as properties, not separate structures

Both replace a side structure keyed by metric name, and both derivations are exact rather than approximate, which the baseline confirmed before I relied on it:

- every `QUARTERLY_COUNTERPART` key is in `FUNDAMENTALS_TO_PLOT`, and **every value is exactly `<id>_quarterly`** — no irregular entry, so a boolean plus one f-string reproduces the dict exactly;
- every `HARMONIC_MEAN_CONCEPTS` member is in `VALUATIONS_TO_PLOT` — so a boolean on the metric reproduces the set.

### The legacy `symlog` flag: not in the registry

No metric ever set it (all 29 fundamentals entries carry `False`) and nothing renders it — `build_fundamentals` unpacks it into `_symlog` and discards it. Putting a constant into the source of truth would suggest it means something. The derived `FUNDAMENTALS_TO_PLOT` supplies the `False` positionally, so the 5-tuple shape every consumer expects is unchanged.

## Step 2 — Derived compatibility layer

The five names still exist in `config.py`; they are now generated:

```python
FUNDAMENTALS_TO_PLOT  = [(m.id, m.label, m.ref_line, m.percent, False) for m in _metrics_for(CHART_FUNDAMENTALS)]
VALUATIONS_TO_PLOT    = [(m.id, m.label, m.ref_line, m.percent)        for m in _metrics_for(CHART_VALUATION)]
GROWTH_PANELS         = [(m.id, m.label)                              for m in _metrics_for(CHART_GROWTH)]
QUARTERLY_COUNTERPART = {m.id: f"{m.id}_quarterly" for m in METRICS if m.quarterly}
HARMONIC_MEAN_CONCEPTS = {m.id for m in METRICS if m.harmonic}
```

`_metrics_for` preserves `METRICS` order, and `METRICS` lists the entries grouped by chart in exactly today's order — so panel order is unchanged by construction. Every consumer (`figures.py`, and `main.py`, which imports `HARMONIC_MEAN_CONCEPTS` and uses it in four places) keeps working untouched, and correctness reduces to one provable claim: the derived structures equal the pre-change literals. That claim is checked against a **pickled capture of the actual objects** taken before the edit, not a retyped copy.

### Step 2 finding: no id appears in two charts

**45 metrics, 45 unique ids** (29 fundamentals + 13 valuation + 3 growth), verified both in the baseline (against the old literals) and after (against the registry). Two consequences:

1. `_concept_plot_spec`'s valuation-before-fundamentals scan order was **moot** — it could never have resolved a conflict because none exists. Replacing it with a flat dict lookup therefore cannot change any answer, and the report says so rather than preserving a precedence that decides nothing.
2. A single `METRICS_BY_ID` index is well-defined, and `_index_metrics` now *enforces* uniqueness: a future duplicate raises at import naming both charts, instead of one entry silently shadowing the other.

## Step 3 — `_concept_plot_spec` as a registry lookup

```python
metric = METRICS_BY_ID.get(concept)
if metric is None:
    return None
return (metric.chart, metric.label, metric.ref_line, metric.percent,
        metric.chart == CHART_VALUATION, metric.value_column)
```

Same tuple shape, same values, so `concept_source`, `build_ticker_comparison` and their callers needed no change. The growth branch's previously hardcoded `0`, `True` and `"yoy_growth"` now come from the registry — the three growth entries carry `ref_line=0, percent=True` to match what `build_growth` actually draws, and `value_column` comes from `CHART_SPECS`. `figures.py` gained exactly two imported names (`METRICS_BY_ID`, `CHART_VALUATION`); the direction `figures` → `config` is intact and `config.py` imports nothing from `figures.py`.

## Step 4 — The accessor

```python
get_plottable_metrics(chart, ticker=None, language=LANGUAGE_PRIMARY) -> list[tuple[str, str]]
```

Returns `(id, label)` pairs in panel order. Lives in `config.py` next to `is_hidden`, so the dependency direction is unchanged. An unknown `chart` raises `ValueError` listing the valid ones — a picker asking for a chart type that does not exist is a programming error, unlike a metric hidden for a ticker, which is normal.

**`is_hidden` stays authoritative.** With a ticker, entries it hides are filtered out; without one, the full catalogue comes back. This is the same narrowing-only rule the figure builders follow, and it matters because it closes the loop: a picker cannot offer a metric that `build_fundamentals` would then silently drop. Verified for AAPL (29 → 9 entries) and JPM, in both cases against `is_hidden`'s own answer rather than a hardcoded expectation, with the precondition (`efficiency_ratio` hidden for AAPL, `fcf_margin` for JPM) asserted first.

## Step 5 — Verification

Baseline captured **before any edit**: the five literals pickled as objects, `_concept_plot_spec` output for all 45 ids plus three non-ids, and figure JSON for 8 tickers × 4 calls plus 8 comparison calls — together with the pickled `metrics_long` / `valuation_history` / `facts_out`, so the post-change run compares code and not data. **All checks passed.**

**Derived structures equal the pre-change literals.** All five: same type, same length, `==` equal, and element-wise identical under a recursive comparison that checks `type()` and `repr()` at every leaf — so `0` vs `0.0` and `None` vs `0` could not slip through. Specifically confirmed: `ref_line` reprs are exactly `{None, 0, 0.4, 1.0}`, the `0`s are still `int` (not `float`, not `bool`), entries are tuples not lists, `HARMONIC_MEAN_CONCEPTS` is still a `set`, `QUARTERLY_COUNTERPART` still a `dict` with identical key order.

**`_concept_plot_spec` returns identical tuples** for all 48 probes (every id in all three catalogues, plus `not_a_concept`, `""`, and `roe_quarterly` — a quarterly counterpart name is not itself a registry id and still returns `None`). `concept_source` unchanged.

**Byte-identical figures:** all **32 per-ticker figures** (8 tickers × fundamentals/valuation/growth/narrowed-fundamentals) and all **8 comparison figures** including the `as_of` variants. The three profiles the brief named:

| ticker | profile | fundamentals | valuation | growth |
|---|---|---|---|---|
| AAPL | `standard` | 50,191 B ✓ | 23,281 B ✓ | 18,966 B ✓ |
| JPM | `financial` | 52,374 B ✓ | 15,701 B ✓ | 18,876 B ✓ |
| AMT | `reit` | 25,630 B ✓ | 16,144 B ✓ | 18,821 B ✓ |

(MSFT, BAC, AFL, O and AZO likewise.)

**Accessor:** full catalogue without a ticker matches `FUNDAMENTALS_TO_PLOT` / `VALUATIONS_TO_PLOT` / `GROWTH_PANELS` pair-for-pair; narrowing verified for two tickers; `language="de"` with no translations populated returns the primary labels rather than blanks; a synthetic `Metric` with `label_de` set returns the translation for `"de"`, the primary for `"en"` and the primary for an unknown `"fr"`.

**Import-time integrity, demonstrated rather than asserted** (each in a subprocess, nothing broken left behind):

| provoked mistake | result |
|---|---|
| duplicate id `roe` | `ValueError: METRICS: duplicate id 'roe' (charts 'fundamentals' and 'valuation')` |
| `chart="not_a_chart"` | `ValueError: ... unknown chart 'not_a_chart'; expected one of [...]` |
| omitted `label` | `TypeError: Metric.__init__() missing 1 required positional argument: 'label'` |
| typo `refline=0` | `TypeError: ... unexpected keyword argument 'refline'. Did you mean 'ref_line'?` |
| mutating a registry entry | `FrozenInstanceError` |

**Nothing else regressed:** `main`, `figures`, `config`, `metrics`, `quality` and `parsers.parse_edgar` all import, `main()` and `run_full_refresh()` remain callable, and `main.py`'s `HARMONIC_MEAN_CONCEPTS` consumer still sees the same seven concepts. No name was removed, so no consumer needed updating — the grep confirms the only references to the five structures outside `config.py` are `figures.py`'s import and `main.py`'s `HARMONIC_MEAN_CONCEPTS`, both unchanged.

### What adding a metric costs now

One `Metric(...)` line in `METRICS`, instead of touching up to four structures and remembering which. `figures.py` needs no change at all — the sixth reconstruction of the association is gone.

No scratch scripts were left behind; the isolated baseline/verification workspace was deleted after the run.
