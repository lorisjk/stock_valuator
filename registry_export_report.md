# Exporting the config registry as JSON

**Date:** 2026-08-22
**Touched:** `main.py` (registry export + wiring into `export_for_app` + schema bump),
`.github/scripts/validate_export.py` (10 new checks), `MDs/bugfixes_opdate_history.md`.
**`config.py`, `figures.py` and `app.py` are unmodified** — confirmed by an empty
`git diff HEAD -- config.py figures.py app.py`, not by memory.

`streamlit_inventory.md` §1.5 named this the single biggest gap in the export: `app.py` imports
`config.py` and calls into it at runtime, and a browser cannot. Two files now carry it —
**`registry.json`, 83.4 kB raw / 11.7 kB gzipped**, and **`concept_candidates.json`, 242.9 kB raw
/ 7.8 kB gzipped**.

---

## 1. Step 1 — the specification, reconciled against the code

Every row of §1.5 was checked against `config.py` as it stands, and `app.py` was grepped for every
`config.` reference. **Nothing the inventory named has disappeared.** Two things it named are not
read by `app.py` at all (they are `figures.py`'s), and five things `app.py` reads are missing from
the table.

### What §1.5 named, and where it actually is read

| §1.5 row | still exists | read by `app.py` | read by `figures.py` |
|---|---|---|---|
| `METRICS` registry | ✓ 52 entries | ✓ 4 sites (encyclopedia, coverage page) | ✓ via `METRICS_BY_ID` |
| `get_plottable_metrics(chart, ticker)` | ✓ | ✓ app.py:171, app.py:1026 | — |
| `profile_visibility()` | ✓ | ✓ app.py:687 | — |
| `get_concept_candidates(ticker)` | ✓ | ✓ app.py:227 | ✓ |
| `is_hidden(ticker, metric)` | ✓ | **no direct call** — reached through `get_plottable_metrics` | ✓ `_select_concepts` |
| `GROWTH_MECHANISM_NOTE` / `VALUATION_MECHANISM_NOTE` | ✓ | ✓ app.py:650, 653 | — |
| `HARMONIC_MEAN_CONCEPTS` | ✓ 7 concepts | **no** | ✓ (and `main.py`) |
| `QUARTERLY_COUNTERPART` | ✓ 11 entries | **no** | ✓ |
| `content/about.md`, `content/update_notice.md` | ✓ (files, not `config.py`) | ✓ | — |

The two "no" rows are not table errors — they are read by the module that draws the charts rather
than the one that lays out the page, and a frontend that replaces both needs them either way. They
are exported.

### What the table missed

Five things the table does not list — the first three read by `app.py` directly, the last two
needed by a rebuild even though `app.py` never touches them:

1. **`undocumented_metrics()`** (app.py:639). The encyclopedia opens with a warning listing
   registry ids that lack a `description` or a `formula`. Currently **0** — but the point of the
   function is that it stays honest when someone adds a metric, and a frontend that omits it
   silently loses that.
2. **`CHART_FUNDAMENTALS` / `CHART_VALUATION` / `CHART_GROWTH`** (app.py:87–89) and the order they
   appear in `CHART_SECTIONS`. The chart ids are part of the contract: the export keys `charts`
   and every metric's `chart` field on them.
3. **`METRICS_BY_ID`** (app.py:350), the index `_percent_applies` resolves through.
   `_index_metrics` raises at import on a duplicate, so ids are globally unique and a frontend can
   safely build the same flat index from the exported list.
4. **Three `Metric` fields the table's enumeration omitted** — `quarterly`, `label_de`, and the
   `id_namespace` property (the table lists `value_column` but not its sibling). Plus
   `LANGUAGE_PRIMARY` and `label_for()`, the language-fallback rule. `app.py` reads none of
   these; `figures.py` derives the dual-trace treatment from `quarterly` via
   `QUARTERLY_COUNTERPART`, and §3.2 of the inventory turns on `id_namespace`.
5. **`DEFAULT_PROFILE` and `TICKER_PROFILES`**, imported by `figures.py`. Needed to resolve a
   ticker to a profile — which, as §2 shows, is what makes the export small.

`config.DATA_DIR` (app.py:19, 22) is also read but is a filesystem path, not registry content.

---

## 2. Step 2 — the export shape, decided by measurement

### 2.1 Per-ticker versus per-profile: the size question

The brief asked whether `get_plottable_metrics(chart, ticker)` should be inlined for every ticker,
or reconstructed by the frontend from `profile_visibility()` plus each ticker's profile — and
warned that §3.1's "`is_hidden` is applied twice" might mean profile alone does not determine
visibility.

**It does.** `is_hidden` uses its `ticker` argument for exactly one thing: a lookup in
`TICKER_PROFILES`. Everything after that consults `PROFILE_HIDDEN` and `_DERIVED_CONCEPT_CONSUMERS`,
both keyed by profile. There is no per-ticker branch in that path, and no per-ticker override
structure feeding it. The "applied twice" of §3.1 is about *where* the filter runs — once in the
picker, once inside the builder — not about it consulting anything beyond the profile.

Measured rather than argued, over the whole universe:

| | inlined per ticker | via profile | ratio |
|---|---:|---:|---:|
| visibility (609 tickers × 3 charts) | 274,363 B | 41,772 B | **6.6×** |
| disagreements between the two | **0 of 1,827 (chart, ticker) pairs** | | |

**Per profile it is.** The equivalence is not assumed — Step 4 re-derives all 1,827 lists from the
JSON and compares them to `config.get_plottable_metrics`, ids, order and labels.

### 2.2 The same question for `get_concept_candidates`, with a different answer

Here per-ticker overrides genuinely exist (`TICKER_CONCEPT_OVERRIDES`, 34 entries, 33 of them for
universe tickers), so profile alone is *not* sufficient. But the resolved dicts collapse anyway:

| | size | count |
|---|---:|---:|
| inlined per ticker | 2,837,172 B | 609 dicts |
| deduplicated variants + index | 242,897 B | **39 variants** |
| | **11.7×** | |

577 of 609 tickers resolve to their profile's baseline verbatim. Variants are stored once and each
ticker points at one by index — lossless, and verified per ticker in Step 4.

**Incidental finding, recorded not fixed:** `TICKER_CONCEPT_OVERRIDES["ARE"]` is an empty dict.
33 universe tickers have an override entry; only **32** change anything.

### 2.3 One file or two

Split, because the two halves are needed by different views and differ by 3× in size:

| file | raw | gzip | needed by |
|---|---:|---:|---|
| `registry.json` | 83,427 B | 11,694 B | every view — pickers, axis labels, reference lines, percent formatting, encyclopedia, coverage page |
| `concept_candidates.json` | 242,897 B | 7,780 B | Data tab and Raw Facts tab only (the raw-versus-derived split) |

`registry.json` alone is what a frontend needs on load; `concept_candidates.json` can wait until
someone opens the Data tab. Bundling them would make the first paint fetch 3× more than it needs.

`registry.json`'s own breakdown: `profile_visibility` 32.9 kB (39%), `metrics` 27.6 kB (33%),
`ticker_profile` 14.0 kB (17%), `notes` 3.9 kB (5%), `charts` 1.4 kB (2%).

### 2.4 The id-namespace split

`id_namespace` and `value_column` are exported **twice on purpose** — once per chart in the
`charts` block, and once flattened onto every metric — so neither a chart-major nor a
metric-major consumer has to join to get them. Step 4 checks they agree.

This is what makes the trap in §3.2 unreachable from the export. Ten registry ids are also
`facts_full` concept names:

```
CoreOperatingEarnings  EPS_TTM_CALC  FCF_TTM  FFO_TTM  NetIncomeLoss
OperatingIncomeLoss_TTM  PPNR  Revenue  SharesOutstanding  StockholdersEquity
```

**All ten declare `value_column: "yoy_growth"`.** So no id in the export both sets `percent: true`
and claims to describe the facts frame's `value` column, and a frontend applying `_percent_applies`'
rule — match on `value_column`, not on the name — cannot render Apple's $109 bn revenue as
`10941700000000.00%`.

### 2.5 Which `Metric` fields go out

**All of them, derived from `dataclasses.asdict`** rather than a hand-written field list, plus the
three computed properties added explicitly (`documented`, `id_namespace`, `value_column` are not
fields). A field added to `Metric` later therefore reaches the frontend automatically instead of
being dropped until someone notices a blank label — which is exactly the "a missing field means a
re-export later" the brief wanted avoided.

10 fields: `id`, `chart`, `label`, `ref_line`, `percent`, `quarterly`, `harmonic`, `label_de`,
`description`, `formula`. 3 properties: `documented`, `id_namespace`, `value_column`. 13 keys per
metric, 52 metrics.

`label_de` is exported despite being `None` on all 52 entries — the mechanism exists and a
consumer implementing the fallback rule needs to see the field, not infer its absence.

### 2.6 Schema version

`REGISTRY_SCHEMA = 1` on **both** files, so either can be validated alone. `APP_EXPORT_SCHEMA`
goes **2 → 3**: `meta.json` gained a `registry` block and the directory gained two files, which is
precisely what an export schema version is for. `validate_export.py`'s `EXPECTED_SCHEMA` moves
with it.

---

## 3. Step 3 — what was implemented, and where

All of it in `main.py`, in the block immediately above `export_for_app`:

| name | what it does |
|---|---|
| `REGISTRY_SCHEMA = 1`, `REGISTRY_FILE`, `CANDIDATES_FILE` | the contract's version and filenames |
| `_write_json_atomic(payload, path) -> int` | temp file + `os.replace`, the same convention as `_write_parquet_atomic`; returns bytes written |
| `_metric_entry(metric) -> dict` | `dataclasses.asdict` + the three properties |
| `build_registry(tickers) -> dict` | the whole registry payload |
| `build_concept_candidates(tickers) -> dict` | variants + `ticker_variant` index |
| `export_registry(tickers, out_dir) -> dict` | writes both files, returns the inventory |

`export_for_app` calls `export_registry(produced, out_dir)` **after the six parquet frames and
before `meta.json`**, so `meta.json`'s presence still means the entire export — frames and
registry alike — is already on disk. That invariant is what the existing convention buys, and the
new files sit inside it rather than beside it.

**`config.py` is the source, not a second copy.** Everything is obtained by calling
`profile_visibility()`, `get_concept_candidates()`, `undocumented_metrics()`, and by iterating
`METRICS`, `CHART_SPECS`, `QUARTERLY_COUNTERPART` and `HARMONIC_MEAN_CONCEPTS`. **No value is
restated as a literal anywhere in the new code.** Step 4 asserts equality against the live objects
for every one of them, so a drift would be a failing check rather than a silent divergence.

`meta.json` gains a `registry` block:

```json
"registry": {
 "schema": 1, "metrics": 52, "profiles": 24, "tickers": 609,
 "candidate_variants": 39,
 "bytes": {"registry.json": 83427, "concept_candidates.json": 242897}
}
```

Deliberately **not** folded into `meta["rows"]`: `rows` is a parquet row count and neither JSON
file has rows. Named counts say what they mean; a "row count" for `registry.json` would not.

### The validator

10 new checks in `.github/scripts/validate_export.py`, in the same `Checks` shape as the existing
ones — **but not row floors.** These files describe `config.py`, not the filings: their sizes do
not grow with new quarters, so a 90%-of-baseline floor would detect nothing real. What is checked
instead is that they still answer the question the app asks of them:

- both files parse as JSON; `registry.schema == 1`;
- every metric carries `id`, `chart`, `label`, `percent`, `ref_line`, `id_namespace`,
  `value_column` — the last two because without them the percent trap reopens;
- every metric's `chart` is declared in `charts`;
- **every ticker resolves to a profile that has a visibility row**, and every row covers every
  metric — this is the substitution from §2.1, checked structurally;
- the registry and the candidates both cover every ticker in `universe.parquet`;
- every `ticker_variant` index points at a variant that exists.

---

## 4. Step 4 — verification

**46 checks, all passing**, plus **11 negative tests on the validator, all rejecting.** The export
under test was written into a scratch directory; `data/app/` was left exactly as published.

### 4.1 The decisive check: round-trip equivalence, all tickers

For **every one of the 609 universe tickers × 3 charts = 1,827 pairs**, the metric list
reconstructed from `registry.json` — `[id for id in charts[chart].metric_ids if
profile_visibility[ticker_profile[ticker]][id]]` — was compared to
`config.get_plottable_metrics(chart, ticker)`.

| | result |
|---|---|
| same ids, same order | **1,827 / 1,827** |
| same labels | **1,827 / 1,827** |
| tickers covered | 609 / 609 |

Not a sample. **The export is a complete substitute for calling into `config`.**

### 4.2 The rest

| check | result |
|---|---|
| `profile_visibility()` identical | ✓ 24 profiles × 52 metrics, exact dict equality |
| every profile in `TICKER_PROFILES` has a row | ✓ 24 |
| `ticker_profile` agrees with `universe.parquet`'s `profile` column | ✓ 609 rows |
| `get_concept_candidates(ticker)` round-trips | ✓ **609 / 609**, deep equality |
| no JSON-lossy types in the candidates (a tuple or set would not survive) | ✓ |
| dedup lossless — every ticker indexed, no orphan variant | ✓ 39 variants, indices 0…38 all used |
| the three dual-namespace ids are `growth` / `xbrl_concept` / `yoy_growth` / `percent` | ✓ 3/3 |
| every registry id that is also a `facts_full` concept declares `value_column != "value"` | ✓ 10/10 |
| no id both sets `percent` and describes the facts `value` column | ✓ 0 |
| every metric's `value_column` / `id_namespace` matches its chart's | ✓ 52 |
| every `Metric` dataclass field exported | ✓ 10/10 |
| every `Metric` property exported | ✓ 3/3 |
| no exported key unaccounted for | ✓ 13 keys exactly |
| exported values equal the live objects | ✓ 52 × 13 |
| metric list order == `METRICS` order; each chart's `metric_ids` == catalogue order | ✓ 52 / 29 / 13 / 10 |
| `quarterly_counterpart`, `harmonic_mean_concepts` identical, and consistent with the per-metric flags | ✓ 11, 7 |
| mechanism notes byte-identical | ✓ 2,332 + 1,478 chars |
| `undocumented`, `language_primary`, `default_profile` identical | ✓ 0, `en`, `standard` |
| `ref_line`'s `int` 0 vs `float` 0.4 distinction survives JSON | ✓ |
| both files carry `schema: 1`; `meta.schema == 3` | ✓ |
| no `.tmp` files left behind; `meta.json` is the newest file in the directory | ✓ |

### 4.3 Nothing else changed

- **`config.py`, `figures.py`, `app.py`: empty `git diff HEAD`.**
- All six parquet frames come back **content-identical** (`DataFrame.equals`) to the published
  export, and **byte-identical across two runs of the new code** (6/6).
- `registry.json` is byte-identical across two runs apart from its `generated_at` stamp;
  `concept_candidates.json` is byte-identical outright.

*One honest caveat on "byte-identical".* The published `data/app/*.parquet` differ byte-wise from a
local rewrite of the same frames. The cause is environmental and pre-existing: those files were
written by CI with `parquet-cpp-arrow 25.0.1`, and this machine has `pyarrow 24.0.0`. Content
equality is exact, and byte equality holds within one environment — which is why the check is
stated as both, rather than as one claim that would be false for the wrong reason.

No full pipeline run was performed, so the price-capture constraint from `product_cleanup_report.md`
never came into play: the verification re-exports the *already-captured* frames, so there is no
second price capture to disagree with the first. This is the stronger comparison anyway — the
input frames are held fixed, so any difference would be attributable to the code alone.

### 4.4 The validator, exercised in both directions

Run against the freshly written scratch export: **31 checks, ACCEPTED, exit 0.**

Then 11 deliberate mutations, each rejected by exactly the intended check:

| mutation | rejected by |
|---|---|
| `registry.json` missing | `registry.json readable` |
| `concept_candidates.json` missing | `concept_candidates.json readable` |
| `registry.json` corrupt (`{not json`) | `registry.json readable` |
| `schema` set to 99 | `registry.schema` |
| a metric loses `value_column` | `registry metric fields` |
| a metric points at an undeclared chart | `every metric's chart is declared` |
| a ticker resolves to an unknown profile | `every ticker resolves to a profile` |
| a profile row misses a metric | `every profile covers every metric` |
| a universe ticker absent from `ticker_profile` | `registry covers the universe` |
| a `ticker_variant` index dangles | `candidate variants resolve` |
| a universe ticker has no candidate entry | `candidates cover the universe` |

**11 / 11.**

---

## 5. File sizes, and what they mean for a frontend

| file | raw | gzipped | when fetched |
|---|---:|---:|---|
| `registry.json` | 83,427 B (81.5 kB) | **11,694 B (11.4 kB)** | on load, once |
| `concept_candidates.json` | 242,897 B (237 kB) | **7,780 B (7.6 kB)** | lazily, on first Data / Raw Facts view |

Both compress extraordinarily well — `concept_candidates.json` by **31×**, because 39 variants of
a ~20-concept dict share almost every tag list. **Served with gzip, the entire config contract is
19 kB.** For comparison, `streamlit_inventory.md` §1.3 measured a single ticker's chart data at
~120 kB gzipped. The registry is a sixth of one ticker's payload.

Practical consequences:

- **Fetch `registry.json` on load and keep it.** It is smaller than the first ticker's data, it is
  needed before any picker can render, and it changes only when `config.py` does.
- **Cache it against `meta.registry.schema`**, not against a timestamp. The frontend is developed
  against this contract; a schema bump is the signal to reload, and a mismatch should surface as a
  clear message rather than a missing label.
- **Do not fetch `concept_candidates.json` up front.** It is 3× the registry raw, it is needed by
  two of the six analysis tabs and none of the three reference views, and deferring it costs
  nothing once the raw/derived split is behind a tab click.
- **Do not rebuild `get_plottable_metrics` per ticker in a build step.** It is 6.6× larger and
  provably equivalent to the two-line lookup.

The published `data/app/` still holds the schema-2 export (written 2026-08-16, before this change)
and does not yet contain the two files; the next pipeline run writes them. Nothing regresses in the
meantime — `validate_export.py` gates a *fresh* run, and its existing `export age < 6 h` check
already rejects that directory on age alone.

---

## 6. Deliberately omitted, with reasons

| omitted | why |
|---|---|
| **`content/about.md`, `content/update_notice.md`** | Named in §1.5, but they are not in `config.py` and they are already static markdown. A frontend can serve or fetch them verbatim; copying them into a JSON payload would create exactly the second copy this task exists to avoid. |
| **`METRICS_BY_ID`** | `_index_metrics` raises at import on a duplicate id, so the 52 ids are globally unique and a frontend builds the same flat index from the `metrics` list in one line. Exporting the index too would double the largest block for nothing. |
| **`PROFILE_HIDDEN`, `_DERIVED_CONCEPT_CONSUMERS`** | These are `is_hidden`'s *inputs*. `profile_visibility` is its *output*, already resolved, and re-implementing the derived-consumer logic in TypeScript is a second source of truth waiting to drift. |
| **`CONCEPT_CANDIDATES`, `PROFILE_CONCEPT_OVERRIDES`, `TICKER_CONCEPT_OVERRIDES` separately** | Same reasoning: `get_concept_candidates` already resolves the three layers, and each layer *replaces* a concept's whole entry rather than merging — a subtlety a re-implementation would get wrong. Only the resolved result ships. |
| **`label_for()`'s fallback logic** | The rule is one line and the data it needs (`label`, `label_de`, `language_primary`) is all exported. Shipping the resolved label per language would need a language chosen at export time, which is the wrong end. |
| **`TICKERS`, `SNAPSHOT_AS_OF_DATES`, `SEARCH_HINTS`, `CIK_OVERRIDES`, `TTM_CONCEPTS`, `PROFILE_EXCLUDED_CONCEPTS`, `DATA_DIR` / `CACHE_DIR` / `FIGURE_DIR`** | Pipeline configuration. Nothing in `app.py` or `figures.py` reads them for rendering; `DATA_DIR` is a server-side path the browser has no use for. |
| **`n_metrics` / `n_valuation` / `n_growth`** | Already in `universe.parquet`; §2.7 of the inventory records that nothing reads them. Not this task's problem either way. |

---

## 7. Noticed, not acted on

Per the brief's scope — recorded here, unchanged in the code:

- **`TICKER_CONCEPT_OVERRIDES["ARE"] = {}`** is a no-op that resolves to the `reit` baseline. It
  costs one of the 39 variants and nothing else.
- **`EA` is the one profiled ticker with no data** (610 profiled, 609 in the universe), consistent
  with its take-private recorded in the 2026-08-19 changelog entry. `ticker_profile` is keyed on
  the 609 that produced data, so a frontend cannot offer a ticker with no frames.
- **`main.py`'s `APP_EXPORT_DIR` and `app.py`'s independently derived path** are still the
  duplication `app_export_layer_report.md` flagged; the natural home is `config.py`. The two new
  files inherit it.
- **`validate_export.py`'s `BASELINE` still reads 501 tickers** while the universe is 610. The
  floors pass with room to spare, so nothing is broken — but the baseline no longer describes the
  run it claims to, and re-judging a threshold against a stale measurement is exactly what the
  comment above it warns against.

No scratch scripts were left behind.
