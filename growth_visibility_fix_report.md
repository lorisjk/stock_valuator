# Profile Visibility for the Expanded Growth Catalogue

Fixed. `is_hidden` now answers correctly for all 39 growth concepts, **357** (profile, concept)
pairs stopped being offered, and **zero** dead growth panels remain anywhere in the universe.

The fix is **one rule in `config.py` and no new entries** — not the 357 `PROFILE_HIDDEN` entries the
brief priced, not the 16 `_DERIVED_CONCEPT_CONSUMERS` entries the previous cycle recommended, and
not a positive list. §2 has the four costings and why this one won.

Two things the measurement turned up that the brief did not anticipate:

- **The previous cycle's stated blocker is empty in fact.** `growth_expansion_report.md` deferred
  the cheap fix because *"`filter_hidden_rows` runs over the facts frame itself, so mapping `Assets`
  would strip `Assets` rows out of the export … and empty those columns in the Data tab."* Measured:
  hiding all 357 pairs strips **0 rows** from all four frames. Those rows do not exist — the
  pipeline never fetched them. The concern was right in principle and null in practice, and it
  applies equally to *every* mechanism, so it was never a reason to prefer one over another.
- **The same bug exists on the fundamentals chart, on 6 pairs** — `consumer_staples` is offered five
  working-capital metrics it can never produce, and `retail` is offered `rd_intensity` while the two
  profiles that *do* file R&D have it hidden. Found while testing the consumer-inference mechanism,
  which those 6 pairs are exactly what breaks. **Not fixed** — the brief forbids it. §5.

---

## 1. Step 1 — the measurement

Source: the shipped export (`data/app/facts_full.parquet`, 1,152,894 rows, 609 tickers, 24 profiles),
which carries both growth columns since the QoQ cycle. For each of the 24 × 39 = **936** pairs: what
fraction of that profile's tickers ever produce a value for that concept.

Measured twice — on the **raw fact** and on the **growth value** — because they can disagree: a
concept a filer reports every quarter can still yield no growth if it never has two positive values
in a row (`NetIncomeLoss` for a chronically loss-making profile would look "unavailable" on the
growth measure and must not be hidden). They do not disagree here: **both measures give the identical
357 pairs**, with an empty symmetric difference. So the distinction did not have to be adjudicated,
and the report states it because it could have been.

### 1.1 The distribution decides the threshold

Over the 856 pairs not already hidden by the existing rules:

| fraction of a profile's tickers that ever produce the concept | pairs |
|---|---:|
| **exactly 0%** | **357** |
| 0 – 5% | **0** |
| 5 – 10% | 2 |
| 10 – 20% | 4 |
| 20 – 50% | 15 |
| 50 – 90% | 52 |
| 90 – 100% | 426 |

**There is no middle.** 357 pairs sit at exactly zero and the next lowest is **7.69%**
(`financial` / `OperatingIncomeLoss` — 2 of 26 banks). Any threshold in the open interval
(0%, 7.69%] selects the identical 357 pairs, so the brief's suggested 5% and a strict 0% are the
same instrument here and no number had to be argued for.

**The threshold used is 0%** — "no ticker of this profile has ever produced this concept" — chosen
because the gap makes it free and because it is the only threshold that cannot hide a *thin* pair by
accident. The two pairs a 10% threshold would have wrongly hidden are worth naming, since 10% is the
sort of round number that gets picked:

| pair | tickers with data | why it must stay |
|---|---:|---|
| `financial` / `OperatingIncomeLoss` | 2 of 26 | two banks do file an operating-income line |
| `health_services` / `ResearchAndDevelopment` | 1 of 11 | one health-services filer does report R&D |

### 1.2 The 357 pairs are 16 concepts, and every one is a sector tag

| concept | hidden for | still visible for |
|---|---:|---|
| `Assets`, `NetInterestIncome`, `NoninterestIncome`, `NoninterestExpense`, `ProvisionForCreditLosses` | 23 each | `financial` |
| `AccountsPayable`, `AccountsReceivable`, `CostOfRevenue`, `Inventory` | 22 each | `homebuilder`, `retail` |
| `BenefitsLossesAndExpenses`, `ClaimsReserve`, `EarnedPremiums`, `IncurredLosses`, `Investments`, `NetInvestmentIncome` | 22 each | `insurance_life`, `insurance_pc` |
| `ResearchAndDevelopment` | 22 | `health_services`, `pharma_medtech` |

**The other 23 concepts cost nothing** — every profile fetches them, and every one produces data
somewhere. 80 pairs were already hidden by the existing rules (`PPNR`, `FFO_TTM`,
`CoreOperatingEarnings`, `FCF_TTM`, `EPS_TTM_CALC`, `OperatingIncomeLoss_TTM`,
`ShareBasedCompensation` through `_DERIVED_CONCEPT_CONSUMERS`); those are untouched.

### 1.3 The count, against the existing structure

| | entries |
|---|---:|
| `PROFILE_HIDDEN` today | **616** |
| pairs needing a hide | **357** |
| a negative list would take it to | 973 (**+58%**) |

This is the number `growth_expansion_report.md` §3 flagged as a risk before the catalogue shipped.
**It reproduces exactly** — the estimate was right, and re-measuring against the shipped export
rather than trusting it cost one script.

---

## 2. Step 2 — the mechanism

Four candidates, all priced, and one thing that turned out **not** to discriminate between them.

### 2.0 The blast radius is the same for every mechanism, and it is zero

Every mechanism routes through `is_hidden`, and `filter_hidden_rows` (main.py:2273) calls
`is_hidden` per row over the facts frame. So the export consequence is identical whichever
structure expresses the rule — it is a property of *hiding these pairs at all*, not of how.

Measured, with all 357 hidden:

| frame | rows before | rows after | removed |
|---|---:|---:|---:|
| `facts_full` | 1,152,894 | 1,152,894 | **0** |
| `metrics_long` | 571,114 | 571,114 | **0** |
| `valuation_history` | 352,639 | 352,639 | **0** |
| `current_snapshot` | 25,202 | 25,202 | **0** |

Zero, and necessarily so: a pair at 0% availability has no rows to strip. Their `_TTM` and
`_QUARTERLY` siblings are likewise **0 rows**. The Data tab and the Raw Facts chart lose nothing —
verified directly in §4.7.

### 2.1 Negative list — extend `PROFILE_HIDDEN`

**357 entries, 616 → 973.** Mechanically consistent with every other metric, and rejected on two
counts beyond the count itself:

- It would restate by hand what `PROFILE_CONCEPT_OVERRIDES` already says. The 16 concepts are hidden
  for a profile precisely because that profile's candidate list does not contain them.
- It goes stale silently. Widen a profile's candidate list and 22 hide entries are now wrong, with
  nothing to notice.

### 2.2 `_DERIVED_CONCEPT_CONSUMERS`-style inference — **tested, and it does not hold**

The previous cycle recommended this ("16 map entries instead of 357"). The brief asks to *confirm the
relationship actually holds* before relying on it. It does not.

Tested against the most generous consumer set the registry can offer for each of the 16 (if even
that fails, no narrower set can succeed), over all 16 × 24 pairs:

```
exact for 11 of 16 concepts;  pairs the rule gets wrong: 7
```

| concept | consumers | want hidden | rule gives | wrong |
|---|---|---:|---:|---|
| `Assets` | `roa`, `equity_to_assets` | 23 | 23 | — |
| `NetInterestIncome` | `net_interest_margin`, `p_ppnr` | 23 | 23 | — |
| `NoninterestIncome` / `NoninterestExpense` | `efficiency_ratio`, `p_ppnr` | 23 | 23 | — |
| `ProvisionForCreditLosses` | `provision_ratio` | 23 | 23 | — |
| the six insurance tags | `loss_ratio`, `combined_ratio`, `net_investment_yield`, `reserve_growth` | 22 | 22 | — |
| **`AccountsPayable`** | `dpo`, `cash_conversion_cycle` | 22 | 21 | leaves `consumer_staples` dead |
| **`AccountsReceivable`** | `dso`, `cash_conversion_cycle` | 22 | 21 | leaves `consumer_staples` dead |
| **`Inventory`** | `inventory_turnover`, `dio`, … | 22 | 21 | leaves `consumer_staples` dead |
| **`CostOfRevenue`** | `inventory_turnover`, `dio` | 22 | 21 | leaves `consumer_staples` dead |
| **`ResearchAndDevelopment`** | `rd_intensity` | 22 | 23 | **over**-hides `health_services` + `pharma_medtech`, leaves `retail` dead |

The `ResearchAndDevelopment` row is the fatal one: the rule hides R&D growth for the two profiles
that *do* file R&D and shows it for the one that does not — exactly backwards, and a `PROFILE_HIDDEN`
entry cannot repair an over-hide.

**The consumer rule is not broken; it is faithful.** All 7 failures trace to 6 pre-existing wrong
entries in the *fundamentals* catalogue (§5). Inference from a correlate inherits the correlate's
bugs, which is the general lesson and the reason the chosen mechanism infers from the cause instead.

Salvaging it would cost 15 map entries + 4 `consumer_staples` hides + 22 `ResearchAndDevelopment`
hides = **41 entries**, and would still be wrong the moment `rd_intensity`'s visibility is corrected.

### 2.3 A positive list scoped to growth

**499 entries** (the pairs that stay visible), *plus* a new structure to hold them and a second
branch in `is_hidden`. Worse than the negative list's 357 on this catalogue — which reproduces
`growth_expansion_report.md` §3's finding and, as it warned, is the opposite of what the coverage
cycle's 5-against-615 comparison suggested. That comparison was measured on the old 10-concept
catalogue and does not transfer.

**Recommendation on the negative-vs-positive question, with the evidence attached: do not switch.**
357 < 499 for this catalogue, and the chosen mechanism costs 0, so the positive list is now second
*and* third best. It would only pay if the catalogue grew to include the `_TTM`/`_QUARTERLY`
derivations, where the negative list costs 1,004 against the positive list's 435. No project-wide
refactor was performed, per the brief.

### 2.4 **Chosen: derive availability from the candidate list**

A growth id names an XBRL concept, and a concept the pipeline never asks EDGAR for cannot produce a
value for that profile — not thinly, not for one filer, ever. `get_concept_candidates` already knows
which. So the rule is *"a growth panel is offered when the pipeline fetches its concept"*, and it
needs no list at all.

**Measured, not assumed.** Candidate membership against "this profile ever produces a value", over
all 24 profiles × 33 fetched growth concepts:

| | no data | has data |
|---|---:|---:|
| **not a candidate** | 431 | **0** |
| **a candidate** | 6 | 429 |

Zero false positives. The 6 residual "candidate but no data" are all
`ShareBasedCompensation`, already hidden by the existing consumer rule.

The scope is clean and is not a judgement call: of the 39 growth ids, **33 appear in some candidate
layer and 6 appear in none** — `EPS_TTM_CALC`, `FCF_TTM`, `OperatingIncomeLoss_TTM`, `PPNR`,
`CoreOperatingEarnings`, `FFO_TTM`, exactly the six the pipeline *computes* rather than fetches.
Those six keep resolving through `_DERIVED_CONCEPT_CONSUMERS` and are excluded from the new rule; a
naive unscoped test would hide all six for every profile (verified — mutation M2, §4.8).

| mechanism | entries | exact? |
|---|---:|---|
| A negative list | 357 (+58% on `PROFILE_HIDDEN`) | yes, until an override changes |
| B consumer inference | 16 | **no — 7 pairs wrong** |
| B′ inference + patches | 41 | yes, until `rd_intensity` is fixed |
| C positive list | 499 + a new structure | yes |
| **D candidate rule** | **0** | **yes** |

It is also the rule `figures.available_raw_concepts` (figures.py:1113) already applies to the Raw
Facts chart. The two now agree **by construction** instead of by coincidence.

### 2.5 One thing the rule had to give up: the per-ticker layer

`get_concept_candidates` resolves three layers — base, profile override, **ticker** override. The
new rule deliberately resolves only the first two.

`profile_visibility()` states the invariant this preserves: *"is_hidden takes a ticker, but it uses
that ticker only to look up its profile … there is no per-ticker override in that path."* The
registry exports **one visibility row per profile** on the strength of that sentence. An `is_hidden`
that could answer differently for two tickers of one profile would not make that export incomplete —
it would make it **wrong**, silently, for every ticker that is not the representative.

Caught by measurement, not by reading: the first implementation resolved per ticker, and **NVR** —
which overrides `Inventory` while falling through to `standard`, a profile that does not fetch it —
diverged from every other `standard` ticker. NVR is not in `TICKER_PROFILES` and so is not in the
universe at all, but the shape is the point: a ticker needing a concept its profile does not fetch
needs a *profile*, and the override is a workaround for a missing one. Resolving per profile hides
that panel rather than publishing an export-contradicting one, and the raw fact is still on the Raw
Facts chart, which is per ticker and does read the third layer.

Verified after the change: **0 (profile, metric) pairs where two tickers of one profile disagree**,
across all 609 × 81.

---

## 3. Step 3 — what was implemented

**`config.py` only. No frontend file needed a change** — the frontend reads
`registry.profile_visibility`, which `build_registry` generates straight from `is_hidden`, so the
picker, the builder, the encyclopedia and the coverage page all inherit the fix without an edit. The
regenerated export is data, not code.

| file | change |
|---|---|
| `config.py` | `from functools import lru_cache` |
| `config.py` | new `_candidate_concepts(profile)` — base + profile candidate layers, cached |
| `config.py` | new `_fetched_growth_concepts()` — the 33 growth ids that name a fetched concept, cached |
| `config.py` | `is_hidden` gains one branch between the explicit list and the consumer rule |
| `data/app/*`, `frontend/public/*` | regenerated export (registry + frames + 1,218 per-ticker files) |

The branch itself:

```python
if metric_name in _fetched_growth_concepts() and metric_name not in _candidate_concepts(profile):
    return True
```

It can only ever return `True`, so it composes with the two existing rules without reordering them.

**`lru_cache` on both.** `filter_hidden_rows` calls `is_hidden` once per row — 1.15M rows on the
current export. Measured on a 120,000-row slice:

| | time |
|---|---:|
| without the rule (pre-fix) | 1.62 s |
| **with the rule, cached (as shipped)** | **1.64 s** |
| with the rule, candidate set rebuilt per call | 1.90 s |

So the rule costs about **1%** and the cache saves about **14%** of that path — modest, and stated
as measured rather than as a headline. Both caches key on module-level constants; the docstring
records that anything mutating `CONCEPT_CANDIDATES`, `PROFILE_CONCEPT_OVERRIDES` or `METRICS` at
runtime must call `.cache_clear()`.

---

## 4. Step 4 — verification

### 4.1 The picker offers exactly what `is_hidden` allows

Read out of a real browser (headless Edge over CDP), five profiles including `financial`:

| ticker | profile | options offered | `is_hidden` allows |
|---|---|---:|---:|
| JPM | `financial` | 23 | 23 |
| TGT | `retail` | 24 | 24 |
| AAPL | `standard` | 20 | 20 |
| ERIE | `standard` | 20 | 20 |
| PLD | `reit` | 19 | 19 |

Ids **and** labels compared in order, not just counts, and the intersection with the hidden set is
empty for every one. **66/66 checks pass** across this and §4.4.

### 4.2 The builder enforces it independently of the picker

`_select_concepts` was handed requests the picker can never produce, for 49 tickers (one per profile
plus all 26 `financial` tickers):

- request **all 39** → returns exactly the visible set, never more
- request **only the hidden ids** → returns `[]`
- `build_growth(ticker, …, concepts=[<a hidden id>])` → returns `None`, drawing nothing

**245/245 pass.** The reference prints its reason per drop, e.g.
`[figures] JPM: requested concepts not plottable -- Inventory (not shown for this profile), …`.

### 4.3 Both modes respect the same list

Verified rather than assumed: every builder check above was run in **both** `yoy_growth` and
`qoq_growth`, and `build_growth(JPM, concepts=[hidden])` returns `None` in each. JPM draws 20 traces
in YoY and 20 in QoQ off the identical 23-id catalogue; `Inventory` appears in neither. Visibility is
one question per concept, and the mode never reaches `_select_concepts` — it selects a *column* after
the panels are chosen.

### 4.4 The coverage page and the encyclopedia

Read from the rendered page, all 24 profiles, before against after:

| profile | shown | | profile | shown |
|---|---|---|---|---|
| 17 profiles (`standard`, `industrials`, `utilities`, `reit`, …) | 36→20, 35→19 (**−16**) | | `homebuilder`, `retail` | 36 → 24 (**−12**) |
| `health_services`, `pharma_medtech` | 36 → 21 (**−15**) | | `financial` | 34 → 23 (**−11**) |
| | | | `insurance_life`, `insurance_pc` | 35 → 25 (**−10**) |
| **TOTAL** | **856 → 499, exactly −357** | | | |

Each profile's delta equals the number of concepts hidden for it, and the total equals §1's count.
The "Hidden for this profile" list on the page grew by the same amount for every profile.

**The encyclopedia does not move, and should not.** It still lists all 39 growth entries: it is
ticker-independent and filters by chart and query only, never by profile (app.py:641). Verified as
39 on the rendered page rather than assumed.

### 4.5 The full cross-check — every pair, not a sample

```
609 tickers x 81 metrics = 49,329 pairs:  49,329/49,329 pass
```

For each of the 33 fetched growth ids, `is_hidden` must be `True` exactly when the profile never
produces it; for the 6 derived ids and all 42 non-growth metrics, the answer must be **byte-identical
to before**. 9,338 (ticker, concept) pairs are newly hidden.

And the registry against `is_hidden`, ticker by ticker rather than by representative:

```
registry vs is_hidden, all 49,329 (ticker, metric) pairs: 49,329/49,329 agree
```

**No regression on what stays:** the count of offered-but-permanently-empty growth panels goes
**357 → 0**, and no pair that can produce a value was hidden — that is the same 49,329-pair check
read in the other direction, since a wrongly-hidden pair fails it identically.

### 4.6 `financial` / `Inventory`, the reported case

`is_hidden(t, "Inventory")` is `True` for **all 26** `financial` tickers — AXP BAC BNY C CFG COF FITB
GS HBAN HOOD IBKR JPM KEY MS MTB NTRS PNC RF RJF SCHW SOFI STT SYF TFC USB WFC. The panel is absent
from JPM's rendered picker, `build_growth` refuses a direct request for it in both modes, and the
comparison chart now excludes it with a reason:

```
[ticker_comparison] Inventory: not shown -- JPM (for profile 'financial' not shown),
                                            AAPL (for profile 'standard' not shown)
```

### 4.7 Nothing else moved

**Export:** `validate_export.py` → **ACCEPTED, all 41 checks pass**. Zero rows removed from all four
frames (§2.0); both growth columns **bit-identical** over all 1,152,894 rows after recomputation.

**Registry diff, before → after:**

| | result |
|---|---|
| non-growth (profile, metric) visibility changes | **0** |
| metric entries (labels, descriptions, formulas) | byte-identical |
| `charts` block, `notes`, `undocumented` | identical |
| growth visibility | 856 → 499 |

**Chart-builder A/B** — same code, two registries, 26 scenarios:

```
12 of 26 moved -- all 12 growth (6 tickers x 2 modes)
fundamentals x6, valuation x6, comparison x2: byte-identical
```

**Cross-implementation A/B** on the new export — all four Python builders against their TypeScript
ports: **1,170/1,170 checks, 16,375 data points**.

**Raw Facts chart:** untouched by construction — it reads `facts_full` (0 rows removed) intersected
with `get_concept_candidates(ticker)` and never consults `is_hidden`. Confirmed per ticker: of the
concepts it offers, **0** are newly hidden.

**Standing suite — 32/32:**

| check | result |
|---|---|
| `check-chart-width` | growth YoY/QoQ 24 panels, fundamentals 11, valuation 9 — plot 1087px in a 1087px host, doc 1570/1570, **0 panels overflowing**, no pinned width |
| `check-tab-state` | opens on YoY; JPM offers 23; mode+window survive a tab round-trip; picker re-migrates to TGT's 24 on a ticker switch; title follows |
| `check-table-format` | data and Raw Facts render 8 tables / 1,135 cells / 109 row headers |

**Toolchain:** `npx tsc -b` clean, `npx vite build` ✓ built in 12.02s, `npx eslint .` — the same **4
pre-existing errors** documented in `qoq_growth_report.md` §6.10 (`Chart.tsx` `no-explicit-any`,
`ChartView.tsx` ×2 conditional hooks from the operator's fullscreen block, `Sidebar.tsx`
set-state-in-effect). **No frontend file was changed this cycle**, so none of them can be new.

### 4.8 Sensitivity — the cross-check can fail

A harness that cannot fail proves nothing. Three mutations, run against the 23,751-pair growth
cross-check:

| mutation | failures |
|---|---:|
| as shipped | **0** |
| M1 — `Inventory` dropped from the rule's scope | 579 |
| M2 — the 6 derived ids wrongly inside the scope | 1,793 |
| M3 — profile overrides ignored, base candidate layer only | 406 |
| restored | **0** |

M1 initially reported **0**, because the first version of the harness read the expected scope back
out of the live function — so the expectation moved with the mutation. Pinning the scope once, from
the shipped rule, exposes it. Recorded because an under-reporting harness looks exactly like a
passing one.

---

## 5. Follow-ups

1. **The identical bug exists on the fundamentals chart, on 6 pairs. Not fixed** — the brief says
   *"No changes to fundamentals or valuation's existing `PROFILE_HIDDEN` entries."* Measured the same
   way (visible pairs that never produce a value, over 395 fundamentals+valuation pairs):

   | metric | profile | tickers | with data |
   |---|---|---:|---:|
   | `cash_conversion_cycle`, `dio`, `dpo`, `dso`, `inventory_turnover` | `consumer_staples` | 31 | **0** each |
   | `rd_intensity` | `retail` | 28 | **0** |

   The rest of that catalogue is clean — the next lowest is 12.5%, the same bimodal shape as §1.1.
   Two distinct faults: `consumer_staples` is offered five working-capital metrics whose inputs it
   does not fetch, and `rd_intensity` is shown to `retail` while hidden from `health_services` and
   `pharma_medtech`, which looks like a transposed entry. The second is the more serious — it is not
   only a dead panel but a *missing* one, and `PROFILE_HIDDEN` being a negative list means the fix is
   deleting two entries and adding one.

   **This task is scoped strictly to the 39-concept growth expansion.** Fixing those 6 would also
   make the §2.2 consumer mechanism exact, which is a reason to do it in its own cycle rather than a
   reason to fold it into this one.

2. **`NVR`'s `TICKER_CONCEPT_OVERRIDES` entry is a profile in disguise** (§2.5). It adds `Inventory`
   to a ticker resolving to `standard`; it reads like a homebuilder. NVR is not in `TICKER_PROFILES`
   so nothing is broken today, but the next such override on a ticker that *is* in the universe would
   silently get a hidden growth panel. A `TICKER_PROFILES` entry is the fix; an assertion that no
   ticker override adds a growth concept beyond its profile would surface the next one.

3. **`PROFILE_EXCLUDED_CONCEPTS` is nearly inert.** 30 entries, and it is subtracted only inside
   `get_expected_concepts` — which feeds the data-quality report and nothing else. Measured: 94
   (profile, concept) pairs have data despite `expected=False`. It was a candidate scoping mechanism
   for this fix and was rejected for exactly that reason; whether it should still exist is its own
   question.

4. **`is_hidden` now has three rules and no test asserting they compose.** They do compose today
   because all three can only return `True`, so order is irrelevant — but that is a property worth
   pinning rather than rediscovering. The 49,329-pair cross-check is the closest thing and it lives
   in a scratch harness, not in the repo.

---

## 6. One mistake of mine, for the record

The first version of the sensitivity harness computed its expectation from the live
`_fetched_growth_concepts()`, so mutation M1 moved the answer and the expectation together and
reported a clean 0/23,751. The rule was correct; the harness was blind. Fixed by pinning the scope
once before mutating — and it is the same failure mode the QoQ cycle's batched-mutation runs had,
where an under-reporting harness is indistinguishable from a passing one.
