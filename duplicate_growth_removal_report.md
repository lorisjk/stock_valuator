# Duplicate Growth Panels in Fundamentals — Nothing Removed

**The premise does not hold, and Step 1.2 is the step that says so.** The brief's own words: *"If the
fundamentals-chart versions differ in any way (different window default, different concept source),
that is a finding, not a rubber stamp — report it before removing anything."*

They differ, and not marginally: **the two fundamentals entries are TTM growth; the growth-chart
panels are single-quarter growth.** They agree on **0.02%** and **0.03%** of comparable observations.
So the removal would not de-duplicate anything — it would delete the trailing-twelve-month growth
view from the app, because `Revenue_TTM` and `NetIncomeLoss_TTM` are deliberately **not** in the
39-concept growth catalogue.

Nothing was changed. Everything the removal *would* need is audited below, so the change is one
command away if you want it anyway — §6 has the exact edit list and §5 what it costs.

---

## 1. The two entries, as they actually are

The brief guessed `net_income_yoy_growth`. The real ids, from `config.METRICS`:

**`revenue_yoy_growth`** (config.py:2276)
```python
Metric("revenue_yoy_growth", CHART_FUNDAMENTALS, "Revenue growth", 0, percent=True,
       description="How much larger trailing-twelve-month sales are than a year ago. "
                   "The top line, and the number hardest to influence through accounting choices.",
       formula="calculate_growth on `Revenue_TTM`, 4-quarter lag. `Revenue` is mapped "
               "per profile -- for `financial` it is RevenuesNetOfInterestExpense, not gross revenue.")
```

**`income_yoy_growth`** (config.py:2281)
```python
Metric("income_yoy_growth", CHART_FUNDAMENTALS, "Income growth", 0, percent=True,
       description="The same year-over-year comparison applied to profit after everything.",
       formula="calculate_growth on `NetIncomeLoss_TTM`, 4-quarter lag.")
```

Both `chart: fundamentals`, `ref_line: 0`, `percent: true`, `id_namespace: metric`,
`value_column: value`. Both documented. The fundamentals report's id-namespace observation is
confirmed: they are growth-shaped metrics living in the fundamentals catalogue.

## 1.2 They are not duplicates — measured

Computed on the exported frames: `metrics_long`'s `revenue_yoy_growth` / `income_yoy_growth` against
`facts_full`'s `yoy_growth` for the raw concept (what the growth chart draws) **and** for the `_TTM`
concept (what the formula says they use).

| fundamentals metric | vs growth panel | vs `_TTM` growth |
|---|---|---|
| `revenue_yoy_growth` | `Revenue` — 30,649 comparable pairs, **5 identical (0.02%)**, median \|diff\| **3.98 pp** | `Revenue_TTM` — 30,656 pairs, **30,656 identical (100.00%)** |
| `income_yoy_growth` | `NetIncomeLoss` — 22,233 pairs, **7 identical (0.03%)**, median \|diff\| **20.39 pp** | `NetIncomeLoss_TTM` — 23,705 pairs, **23,705 identical (100.00%)** |

The 100% columns settle where each series comes from. AAPL, most recent eight periods, the two
side by side:

| period end | `revenue_yoy_growth` (TTM) | growth panel `Revenue` (Quartal) |
|---|---:|---:|
| 2024-09-28 | 2.02% | 6.07% |
| 2024-12-28 | 2.61% | 3.95% |
| 2025-03-29 | 4.91% | 5.08% |
| 2025-06-28 | 5.97% | 9.63% |
| 2025-09-27 | 6.43% | 7.94% |
| 2025-12-27 | 10.07% | 15.65% |
| 2026-03-28 | 12.76% | 16.60% |
| 2026-06-27 | 14.24% | 16.36% |

Two different readings of the same business, and the pipeline's own docstring says which is which:
`growth_concepts` (main.py:655) records that *"a TTM series is the more meaningful YoY comparison:
measured on this ticker set its growth rate is 1.1-2.2x less volatile than the same concept's raw
quarterly counterpart."*

### Why the growth chart does not already carry the TTM versions

Last cycle registered growth panels for **raw facts only** — `growth_expansion_report.md` §2.2, whose
reasoning was that a `_TTM` panel is the same quantity at a different smoothing and the years slider
already varies that, plus a panel count of 36 against 61. `Revenue_TTM` and `NetIncomeLoss_TTM` are
therefore **not registered anywhere as growth panels**. Removing these two fundamentals entries would
take the TTM growth series out of the app entirely, leaving only the noisier quarterly one.

**That is the finding.** Whatever the right catalogue is, "these two duplicate the growth chart" is
not the reason to act.

## 1.3 Every reference, and what each would do

Searched across `*.py`, `*.ts`, `*.tsx`, `*.mjs/mts`, `*.json`, `*.md` (excluding `node_modules`,
`dist` and the generated ticker exports).

| # | reference | effect of removal |
|---|---|---|
| 1 | **`app.py:904`** — `default = [i for i in ids if i in ("revenue_yoy_growth")]`, the Streamlit fundamentals picker's default selection | **breaks**: the default becomes empty and the tab opens on *"Nothing selected"* |
| 2 | **`frontend/src/charts/defaults.ts:33`** — `fundamentals: "revenue_yoy_growth"` (`PREFERRED_DEFAULT`) | **breaks**: the React fundamentals chart's default panel |
| 3 | **`config.py:895`** — `PROFILE_HIDDEN["reit"]` contains `"income_yoy_growth"` | **dangles**: a hide entry for a metric that no longer exists |
| 4 | **`config.py:2316`** — `rule_of_40`'s formula text: *"`revenue_yoy_growth` + `fcf_margin`"* | **dangles**: the encyclopedia would cite a metric it no longer lists |
| 5 | **`config.py:2385`** — `operating_leverage`'s formula text: *"`operating_income_yoy_growth` / `revenue_yoy_growth`"* | **dangles**, same |
| 6 | `main.py:711-712` — `build_metrics_long`'s spec emits both concepts into `metrics_long` | rows keep exporting (≈70k) with nothing drawing them; they stay visible in the Data tab's *Calculated metrics* table |
| 7 | `main.py:513` `rule_of_40`, `main.py:571` `operating_leverage` | **unaffected** — both read `m["revenue_growth"]`, the DataFrame, not the registry id |
| 8 | `main.py:994,1000,1050-1051` — `pe_to_revenue_growth` | **unaffected** — `build_valuation_history` computes its own `revenue_yoy_growth` column internally |
| 9 | `MDs/encyclopedia.md`, `MDs/main.md`, `MDs/bugfixes_opdate_history.md` | prose references; `MDs/encyclopedia.md:751,759,763` explicitly instructs the reader to *"always read next to `revenue_yoy_growth`"* |
| 10 | `frontend/src/data/pivot.ts:56` | a comment using the id as a sort-order example; harmless |

**Two live defaults break.** Neither is mentioned in the brief, and each would leave its chart opening
empty.

## 1.4 `PROFILE_HIDDEN` and `_DERIVED_CONCEPT_CONSUMERS`

- **`PROFILE_HIDDEN`**: exactly one entry — `"income_yoy_growth"` in the **`reit`** profile
  (config.py:895). `revenue_yoy_growth` appears in none.
- **`_DERIVED_CONCEPT_CONSUMERS`**: **no** entry names either id, as key or as consumer.

---

## 2. What was removed

**Nothing.** §1.2 is the gate the brief set, and it did not open.

---

## 3. Step 3 — the mechanism holds, verified rather than assumed

Both reference views derive from the registry **live**, so a removal needs no frontend edit. Read off
the current code rather than the earlier reports:

- **Encyclopedia** — `Encyclopedia.tsx:124`: `registry.metrics.filter((m) => m.chart === spec.chart)`.
  No cached list. No absolute count anywhere on the page: the only numbers it prints are inside the
  mechanism notes' prose.
- **Profile coverage** — `Coverage.tsx:88` `registry.metrics.filter(...)` for the per-section lists,
  `Coverage.tsx:126` and `:151` `{registry.metrics.length}` for both denominators, and
  `registry.profile_visibility[p][metric.id]` for every mark. All live.
- **Comparison picker** — `figures.py`'s `_concept_plot_spec` resolves against `METRICS_BY_ID`, and
  the React side reads `registry.metrics`; the fundamentals-prefixed options are the registry's
  fundamentals entries, so they would drop out with no edit.

So Step 3's premise is correct. The numbers it would produce:

| | now | after removal |
|---|---:|---:|
| `METRICS` total | **81** | 79 |
| fundamentals entries | **29** | 27 |
| coverage caption denominator (`{n} of 81`) | 81 | 79 |
| matrix caption (`81 metrics × 24 profiles`) | 81 | 79 |
| `standard` shows | 54 of 81 | 52 of 79 |
| `financial` shows | 48 of 81 | 46 of 79 |
| `reit` shows | 44 of 81 | 43 of 79 (it already hides `income_yoy_growth`) |

## 4. Step 4 — what was verified

Since nothing changed, the verification that applies is the part that establishes the current state:

- **The duplicate test** (§1.2) — 52,882 comparable observations across both pairs, from the exported
  frames.
- **The reference audit** (§1.3, §1.4) — ten reference sites, of which two are live defaults and one
  is a `PROFILE_HIDDEN` entry.
- **The derivation mechanism** (§3) — read from `Encyclopedia.tsx` and `Coverage.tsx` directly.
- **The growth chart is untouched** — trivially, and that is the point: it still draws `Revenue` and
  `NetIncomeLoss` as the raw quarterly panels `growth_expansion_report.md` established, and neither
  `Revenue_TTM` nor `NetIncomeLoss_TTM` is registered.

`config.py`, `main.py`, `metrics.py`, `figures.py`, `app.py`, every frontend file and every exported
artefact are byte-unchanged this cycle. No build, no re-export and no regression suite was run,
because there is nothing to regress — the last cycle's results stand as recorded.

---

## 5. If you want the removal anyway

The exact edit list, in dependency order:

1. `config.py:2276-2280` — delete the `revenue_yoy_growth` entry.
2. `config.py:2281-2283` — delete the `income_yoy_growth` entry.
3. `config.py:895` — delete `"income_yoy_growth"` from `PROFILE_HIDDEN["reit"]`.
4. `app.py:904` — pick a new fundamentals default (`operating_margin` is the natural one).
5. `frontend/src/charts/defaults.ts:33` — same, and the two must agree.
6. `config.py:2316` and `:2385` — reword `rule_of_40`'s and `operating_leverage`'s formulas so they
   do not cite a metric the encyclopedia no longer lists.
7. Re-export (`registry.json` + the 1,218 per-ticker files) and re-run the check suite.

**But the better version of the same intent** — if what you want is one growth chart and no
growth-shaped entries in fundamentals — is to *move* rather than delete: register `Revenue_TTM` and
`NetIncomeLoss_TTM` as growth panels, then remove the fundamentals entries. That consolidates both
readings onto the growth chart, keeps the TTM series, and fixes the id-namespace confusion. It costs
2 growth entries and 0 new `PROFILE_HIDDEN` entries (both concepts are universal). It is out of this
task's scope — the brief forbids touching the growth catalogue — so it is a proposal, not a change.

---

## 6. Out of scope, found and not fixed

**`app.py:904` is a latent bug.**

```python
default = [i for i in ids if i in ("revenue_yoy_growth")]
```

`("revenue_yoy_growth")` is a **string**, not a tuple — the parentheses do nothing without a trailing
comma. So `i in (...)` is a *substring* test, not membership. It happens to select the right single id
today because no other fundamentals id is a substring of `"revenue_yoy_growth"`, but it would also
match a future id like `"revenue"` or `"growth"`, and it silently matches nothing if the id is
renamed. The React side (`defaults.ts`) does a plain equality and is not affected. One character
fixes it (`("revenue_yoy_growth",)`); not touched, because this task's scope is the registry.

**`MDs/encyclopedia.md` would go stale on removal.** Three passages (lines 724, 751, 759–763) tell the
reader to read `operating_leverage` and `rd_intensity` *"next to `revenue_yoy_growth`"* — advice that
depends on the panel existing. Those files are the operator's, and they are prose rather than
configuration, so they are named here rather than edited.

**`metrics_long` would keep exporting ~70k rows of two unrendered concepts.** `build_metrics_long`'s
spec (main.py:711-712) is independent of `METRICS`, and `filter_hidden_rows` would not drop them
(neither id would be in `PROFILE_HIDDEN` any more, and neither is in `_DERIVED_CONCEPT_CONSUMERS`).
They would still appear in the Data tab's *Calculated metrics* table — which is arguably correct, the
tab shows what the pipeline computed — but it is worth knowing that removing the registry entries does
not remove the data.
