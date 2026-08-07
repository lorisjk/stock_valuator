# App Refinements — Tab Order, Format Bug, Growth Expansion, Snapshot-in-Chart

**Date:** 2026-08-06
**Touched:** `app.py` (Parts 1, 2, 4), `config.py` (Part 3), `main.py` (Parts 3, 4), `figures.py` (Parts 3, 4).
**234 verification checks, all passing** — 51 Parts 1–2 · 51 Part 3 · 87 Part 4 · 30 cross-part · 15 pipeline.

Parts 1 and 2 were finished and verified before 3 and 4 were started, as instructed.

---

## Part 1 — Tab order

`Data` moved from last to first; the other four keep their relative order. One line changed.

**What I confirmed does not depend on tab order:**

- There is **exactly one `st.tabs` call** in the file (AST, not text search).
- Its result is **tuple-unpacked into five names**, never indexed — no `tabs[0]`, and nothing subscripts a tab variable anywhere in the module.
- Each of the five names is used **exactly once**, as a context manager.
- The `with` blocks fill *named containers*, so their order in the source is independent of render order — only the label list decides. I moved the `with tab_data:` block up anyway so reading order matches display order, and verified the page still renders identically.

Nothing else in the file, the pipeline, or the export references tabs.

## Part 2 — The percent-formatting bug

### The diagnosis is confirmed — measured, not taken on faith

| evidence | result |
|---|---|
| the three `CHART_GROWTH` entries | `Revenue`, `NetIncomeLoss`, `SharesOutstanding` — all `percent=True`, `id_namespace=xbrl_concept`, `value_column=yoy_growth` |
| the same names in the facts frame | all three present, holding absolute values (AAPL `Revenue` = 109,417,000,000.0) |
| what the formatter produced | `Revenue` → `10941700000000.00%`, `SharesOutstanding` → `1471467600000.00%` |
| **`NetIncomeLoss`** | **affected identically** — 29,789,000,000.0 → `2978900000000.00%` |
| `Assets`, `EPS_TTM_CALC` | no registry entry → magnitude rule → correct already |

So the cause is exactly as diagnosed: the registry lookup returned the *growth metric's* formatting for a *raw fact* of the same name.

### The fix — and why the obvious version of it would not have worked

**A namespace test alone does not fix this.** The facts frame's columns *are* XBRL concept names — precisely the namespace those three growth entries live in — so matching `id_namespace` would have said "apply" and kept the bug. Verified for all three.

What separates them is `value_column`: a growth entry describes `yoy_growth` and never `value`. That is now the single rule, in one helper:

```python
def _percent_applies(concept: str, value_column: str) -> bool:
    metric = config.METRICS_BY_ID.get(concept)
    return metric is not None and metric.percent and metric.value_column == value_column
```

`format_for_display(wide, value_column="value")` takes the column explicitly — the caller always knows it, and `render_data_section` passes it through. Facts columns fall through to the magnitude rule.

**This is safe because registry ids are globally unique across namespaces** (45 metrics, 45 distinct ids, enforced at import by `_index_metrics`), so one `value_column` test is unambiguous. A hardcoded three-name exception list would have broken the moment Part 3 registered seven more growth metrics — including `StockholdersEquity`, which is also a facts column holding an absolute.

**A second latent copy of the same bug was removed.** `render_snapshot_section` had its own inline `METRICS_BY_ID[...].percent` lookup. It now calls the same helper. Asserted: `.percent` and `METRICS_BY_ID` each appear exactly **once** in `app.py`.

### Verification

| check | result |
|---|---|
| `Revenue` / `NetIncomeLoss` / `SharesOutstanding` in the facts table, 3 tickers | scaled absolutes — `109.42B`, `29.79B`, `14.71B`, `2.72B`, `859.50M`, … |
| `EPS_TTM_CALC`, `DividendsPerShare_TTM` | `8.7620`, `1.0500` — magnitude fallback still gives decimals, not a scaled unit |
| `Assets`, `Revenue_TTM` | `4.90T`, `466.82B` — unchanged |
| `operating_margin`, `roe`, `roa`, `efficiency_ratio`, `fcf_margin` in the metrics table | still percentages, and equal to `value*100` exactly (`33.17%`, `119.91%`, `16.17%`, `1.20%`) |
| `debt_to_equity`, `net_debt_to_ebitda`, `dio` | still non-percent |
| `dividend_yield` / `pe_ratio` / `ev_sales` in valuation | `0.37%` / `32.3876` / `9.0366` — percent exactly as registered |
| **the same frame pivoted on `yoy_growth`** | `Revenue` → `16.36%`, `NetIncomeLoss` → `27.12%`, `SharesOutstanding` → `-1.56%` — the growth entries *do* apply there |
| the **growth chart** y axes | every populated panel still uses `.1~%`, all three tickers |

## Part 3 — Growth expansion

### Step 3.1 — Survey

Measured across 8 tickers spanning 5 profiles (`standard` ×2, `financial` ×2, `insurance_life`, `reit` ×2, `retail`).

**The task's premise needs one correction, and it changes the whole design.** `main.growth_concepts()` excluded any name containing `_TTM`, plus `PPNR` and `CoreOperatingEarnings`. So of the 69 facts concepts, only 38 ever received a `yoy_growth` value — and **every TTM concept had exactly zero**:

```
Revenue_TTM 0 · FCF_TTM 0 · EPS_TTM_CALC 0 · OperatingIncomeLoss_TTM 0
OperatingCashFlow_TTM 0 · NetInterestIncome_TTM 0 · FFO_TTM 0 · EarnedPremiums_TTM 0
```

`EPS_TTM_CALC` growth — "explicitly requested, likely the single most useful addition" — did not exist. It was not computed and discarded at render time; it was never computed. The same holds for FCF, operating income and every sector aggregate in TTM form. Only their **raw quarterly** counterparts existed.

**Availability of what did exist (top of 38):**

| concept | kind | tickers w/ growth | survival | median n | earliest | \|g\|>500% |
|---|---|---|---|---|---|---|
| SharesOutstanding | raw quarterly | 8 | 95% | 69 | 2008-06 | 0 |
| CashAndEquivalents | raw quarterly | 8 | 94% | 70 | 2007-09 | 8 |
| Revenue | raw quarterly | 8 | 93% | 67 | 2008-09 | 0 |
| NetIncomeLoss | raw quarterly | 8 | 87% | 62 | 2008-09 | 0 |
| StockholdersEquity | raw quarterly | 8 | 83% | 69 | 2007-09 | 0 |
| OperatingCashFlow | raw quarterly | 8 | 79% | 66 | 2009-09 | 0 |
| EPS_QUARTERLY_CALC | quarterly-derived | 6 | 87% | 62 | 2009-06 | 0 |
| OperatingIncomeLoss | raw quarterly | 5 | 93% | 67 | 2009-06 | 0 |
| NetInterestIncome | raw quarterly | 2 (financial) | 94% | 67 | 2009-06 | 0 |
| FFO_QUARTERLY | quarterly-derived | 2 (reit) | 91% | 63 | 2009-06 | 0 |
| EarnedPremiums | raw quarterly | 1 (insurance) | 94% | 67 | 2009-06 | 0 |

**TTM vs. quarterly, stated per candidate rather than assumed.** Two corrections to the brief's framing:

1. **Raw quarterly growth here is *not* seasonal noise.** `calculate_growth` uses a **4-quarter lag**, so it compares Q3 against Q3. That is why the three existing panels work. The real difference is amplitude, not seasonality.
2. It is still measurably noisier. Head-to-head standard deviation of the growth series, same ticker, raw ÷ TTM:

   | pair | range across tickers |
   |---|---|
   | `Revenue` → `Revenue_TTM` | 0.94× – **2.23×** |
   | `FCF_QUARTERLY` → `FCF_TTM` | 1.47× – **2.17×** |
   | `FFO_QUARTERLY` → `FFO_TTM` | 1.33× – **2.00×** |
   | `EPS_QUARTERLY_CALC` → `EPS_TTM_CALC` | 0.71× – 1.33× |
   | `OperatingIncomeLoss` → `..._TTM` | 1.19× – 2.00× |

   Mostly 1.1–2.2× noisier. **Reported honestly: three cases invert** — MSFT `NetIncomeLoss` (0.71×), O `Revenue` (0.94×), BAC `NetIncomeLoss` (0.99×) — so "TTM is always smoother" would be an overstatement.

**Zero-crossing: the risk is real but the pipeline already handles it, and the failure mode is the opposite of the one the brief expected.** `calculate_growth` requires `value > 0` **and** `prev_value > 0` **and** `prev_value >= min_base_ratio * value`. Verified across all 9,301 growth values: **0 were computed from a non-positive level**. A loss quarter therefore produces no number at all. So an expanded chart cannot produce an *explosive* panel — it can produce a **gappy** one, which is why "survival rate" is the column that matters above. (11 values exceed 500%, all in `CashAndEquivalents` and `ProvisionForCreditLosses`, both of which carry a loosened `min_base_ratio` of 0.05 by explicit override — max observed 14.3×, well inside that 19× cap.)

**Rejected candidates, with reasons:**

| candidate | verdict |
|---|---|
| `Revenue_TTM` | rejected — duplicates the existing raw `Revenue` panel; two revenue-growth panels side by side is noise, not information |
| `NetInterestIncome_TTM` | rejected in favour of `PPNR` — would cost **23** `PROFILE_HIDDEN` entries (below) |
| `EarnedPremiums_TTM`, `NetInvestmentIncome_TTM` | rejected in favour of `CoreOperatingEarnings` — 22 entries each |
| `NoninterestIncome_TTM`, `CostOfRevenue_TTM` | rejected — 23 and 22 entries |
| `CashAndEquivalents` | rejected — 94% survival but the loosened base ratio lets it reach 14× growth; a cash balance's percentage change is not a business signal |
| `OperatingCashFlow_TTM` | rejected — thin exactly where it would be new (BAC 31, JPM 26 obs vs 63–65 elsewhere); `FCF_TTM` covers the same ground better |

### Step 3.2 — Proposal, and the `PROFILE_HIDDEN` cost

**The decisive finding: the sector aggregates are free.** `is_hidden` resolves *derived* concepts through `_DERIVED_CONCEPT_CONSUMERS`, which already maps them to exactly the right profiles:

| concept | visible in | cost | vs. the raw alternative |
|---|---|---|---|
| `PPNR` | **1/24** — `financial` | **0 entries** | `NetInterestIncome_TTM` = 23 entries |
| `FFO_TTM` | **1/24** — `reit` | **0 entries** | — |
| `CoreOperatingEarnings` | **2/24** — `insurance_pc`, `insurance_life` | **0 entries** | `EarnedPremiums_TTM` = 22 entries |
| `EPS_TTM_CALC` | 23/24 (auto-hidden for `reit`, valued on FFO not EPS) | **0 entries** | — |
| `FCF_TTM` | 20/24 | **0 entries** | — |

These are also the *right* metrics: PPNR is the bank aggregate, FFO the REIT headline, core operating earnings the insurance figure ex realized gains. Choosing them is not a workaround — it is the same answer arrived at from two directions.

**Final set: 7 new panels, `PROFILE_HIDDEN` cost = 1 entry.**

| panel | label | targets |
|---|---|---|
| `EPS_TTM_CALC` | EPS Growth (TTM, YoY) | all but reit |
| `FCF_TTM` | Free Cash Flow Growth (TTM, YoY) | 20 profiles |
| `OperatingIncomeLoss_TTM` | Operating Income Growth (TTM, YoY) | all but financial |
| `StockholdersEquity` | Equity Growth (Quartal, YoY) | all |
| `PPNR` | PPNR Growth (TTM, YoY) | financial |
| `CoreOperatingEarnings` | Core Operating Earnings Growth (TTM, YoY) | insurance ×2 |
| `FFO_TTM` | FFO Growth (TTM, YoY) | reit |

The one entry is `OperatingIncomeLoss_TTM` hidden for `financial`: banks do not file an operating-income line, so the panel would be permanently empty for a whole profile rather than merely sparse (0 of 2 financial tickers have any value). **Only `financial` is listed** — `captive_finance` and `alt_asset_manager` were not tested and keep the panel rather than being hidden on a guess.

Result: **7 panels per profile, 6 for `financial`**, and no profile-wide empty panel. Per-ticker gaps remain and are left visible — O has no `FCF_TTM` or `OperatingIncomeLoss_TTM` while AMT (same profile) has both, which is a ticker fact, not a profile rule.

**Measured evidence for the "negative list will not scale" problem, as requested:** `PROFILE_HIDDEN` holds **615 entries across 24 profiles today** (min 20, max 32, mean 25.6). Adopting the raw sector tags instead of the derived aggregates would have added **112 entries — an 18% increase for five panels**. The design avoids that, but the number is the point: a positive per-profile list would have cost 5. Not refactored here, as instructed.

### Step 3.3 — Implementation

- **`config.py`:** 7 `Metric(..., CHART_GROWTH, ..., 0, percent=True)` lines. One line each, as intended.
- **`main.py`:** `growth_concepts()` no longer excludes `_TTM`. Cost measured: **+0.44 s per run** (0.64 → 1.08 s for that step) and **+6,303 growth values with zero extra rows** — only fewer NaNs in a column that already existed. Verified: every previously-computed value is **unchanged** (9,301 compared). The two one-off items (`GainLossOnSaleOfProperties`, `RealizedInvestmentGains`) stay excluded, now including their `_TTM` forms.
- **`figures.py`:** `build_growth` now wraps at `_make_grid`'s 3 columns like every other chart. Seven panels in one row would have been a 3500×360 px figure; it is now 1500×1080. **For ≤3 panels the grid is still 1×n at the identical pixel size**, which is why the non-regression below is byte-exact.
- **Per-profile visibility runs entirely through `is_hidden`.** No second mechanism.

**`GROWTH_BASE_PANELS` / `GROWTH_PROFILE_EXTRA` / `get_growth_panels()` — deleted.** They named 15 concepts (`fcf_growth`, `nii_growth`, `ffo_growth`, `equity_growth`, …) of which **not one** existed as a facts concept, a metrics concept, or a registry id — an invented naming scheme never wired to data, with zero consumers (re-confirmed by grep). Their intent was exactly this feature: per-profile growth panels, sector-aware. My design supersedes it — real concept names, visibility via `is_hidden` — so leaving it would have been the third parallel mechanism the brief warned against. A comment records what stood there and why it went.

*Worth noting for a future task:* their approach was a **positive** per-profile list, which is the shape that scales; `PROFILE_HIDDEN`'s negative list is the one that does not. The sketch had the better data structure and the wrong names.

### Step 3.4 — Verification

- **Non-regression, byte-exact:** for all 8 tickers, `build_growth(..., concepts=[the original three])` is **byte-identical** to the `.json` the pipeline wrote before this change (18,966 / 18,876 / 18,821 / 18,792 / 18,886 / 19,295 / 17,426 / 18,940 B). `_make_grid` confirmed to keep 1–3 panels at the old geometry.
- **Each new panel has data exactly where expected and nowhere else** — asserted set-equality per concept: `PPNR` = {BAC, JPM}, `FFO_TTM` = {AMT, O}, `CoreOperatingEarnings` = {AFL}, `EPS_TTM_CALC` = the six non-REITs. Also asserted: no concept ever has data while hidden.
- **Correctly absent:** `PPNR` visible in exactly `{financial}`, `FFO_TTM` in exactly `{reit}`, `CoreOperatingEarnings` in exactly `{insurance_life, insurance_pc}`, across all 24 profiles.
- **Numeric check against the source frame:** JPM `PPNR`, AMT `FFO_TTM` and AAPL `EPS_TTM_CALC` — plotted y equals the source `yoy_growth` value for value, and x equals the source period ends, point for point (71/71/72 points; first values 0.380231, 0.027891, 0.770750).
- **The data tab and the export pick it up with no change there** — both read the registry, as designed. In a real `run_full_refresh()`, `facts_growth.parquet` widened **automatically from 3 concepts / 1,705 rows to 10 concepts / 3,685 rows**, and the app's growth picker offers exactly the visible registry panels per ticker (AAPL 7, JPM 6, AMT 7). Nothing was special-cased.

## Part 4 — The snapshot as the final point in valuation charts

### 4.1 — The mean must not move

**Structural, not conventional.** The snapshot is a **separate trace**, added after the mean is computed, and it never enters `filtered` — the frame the mean is taken over. There is no ordering to get wrong.

Proved numerically: for all **8 tickers**, the mean-line labels and every mean/reference line's y-value are **identical** with and without the snapshot. Checked for both kinds explicitly — harmonic (`pe_ratio` `Ø (harm.) 29.0`, `p_tbv` `Ø (harm.) 1.8`) and arithmetic (`ev_sales` `Ø 7.8`, `pe_to_revenue_growth` `Ø 2.0`) — each with the point confirmed present, so the invariance is not the trivial result of nothing being added.

### 4.2 — Visually distinguishable

A separate `go.Scatter` trace, `mode="markers"`, **green diamond** (`#2ca02c`, size 11, white border): not the series blue, and deliberately not red, which is already the mean and reference line. Hover reads *"Snapshot (aktueller Kurs, letzte Fundamentaldaten) · Stand: 06.08.2026 · Value: …"* — what it is, plus its as-of date.

`legendgroup="snapshot"` with `showlegend` on the first marker only, so N panels produce **one** legend entry, not N. Verified: 7 markers → 1 legend entry for AAPL, 5 → 1 for JPM/AFL/AZO.

The app adds a caption explaining the marker, since a green diamond is not self-explanatory.

### 4.3 — Concept alignment, measured

**10 of 13 valuation panels have a snapshot counterpart.** The three without: `ev_fcf`, `pfcf_ex_sbc`, `p_ffo` — `build_snapshot` simply never computes them. Those panels render **byte-identically** with and without the snapshot; asserted for AAPL `ev_fcf`, AAPL `pfcf_ex_sbc`, AMT and O `p_ffo`.

> **Worth flagging:** `p_ffo` is the REIT headline multiple, and it is the one REIT panel that gets no current point, while `p_tbv`, `p_ppnr` and `p_core_earnings` all do. That is a pre-existing gap in `build_snapshot`, not something this part should close — reporting it rather than fixing it, per 4.3.

The snapshot's `end` is the run date (2026-08-06); histories end 2026-03-31 to 2026-06-30, so the marker sits 1–4 months right of the last filed period and reads clearly as separate.

### 4.4 — Interaction with `as_of`

**Rule adopted, as recommended: the point is suppressed whenever `as_of` is earlier than the snapshot's own date.** Appending a run-date value to a window that ends earlier would put data on the chart that the chosen date could not have known — the exact error `as_of` exists to prevent.

Verified for two tickers across five cases: `as_of=None` → shown; one day before → suppressed; **exactly the snapshot date → shown** (the boundary is inclusive); 30 days after → shown; `2020-06-30` → suppressed. And a suppressed point leaves the figure **byte-identical** to the no-snapshot call (AAPL 23,278 B, JPM 16,138 B, AMT 17,867 B).

### 4.5 — Where the data comes from

`build_valuation(..., snapshot: pd.DataFrame | None = None)` — optional, defaulting to None, so omitting it reproduces today's output exactly.

Both callers updated:
- **`app.py`** passes the already-loaded snapshot frame.
- **`main.py`'s pipeline passes it too**, so the written `.html`/`.json` carry the point. Reasoning: those files are written in the same run that computed the snapshot, so the marker is exactly as fresh as the rest of the chart, and someone opening the standalone HTML sees what the app shows. Confirmed in a real run — AAPL's written figure has 7 markers, JPM's 5, one legend entry each.

### 4.6 — Comparison charts: decided, and deliberately not implemented

**`build_ticker_comparison` gets no snapshot point.** Same reasoning that already excludes per-ticker mean lines: N markers, one per ticker, all at the same x just past the last filed period, would cluster into what reads as a vertical spike rather than N separate current values. And the comparison chart answers *"how have these moved relative to each other"*, where the shape of the history is the content — the current level side by side is what the snapshot table shows better.

Recorded in the function's own docstring so the two chart types are not silently inconsistent, and asserted in the tests (no snapshot trace, no `snapshot` parameter, docstring states it).

### 4.7 — Verification

Beyond 4.1/4.3/4.4 above:

- **The point's value and position:** for AAPL/JPM/AFL/AZO, one marker per panel that has a snapshot value (7/5/5/5, matching the expected count exactly), every marker's y equal to the snapshot frame's value, every marker's x equal to the snapshot date.
- **Default call unchanged:** `snapshot=None` is byte-identical to omitting the parameter, for 6 tickers. Against the pipeline's saved `.json` the comparison is structural (same trace count, layout keys and subplot titles) — a literal byte comparison is not available there because `valuation_history` depends on live prices that have moved since that file was written, and I would rather say so than dress a structural match up as byte equality.
- **The strongest proof that the `plot_metric` change is inert:** `build_fundamentals` calls the *same* `plot_metric`, and its inputs are price-independent — all **8** fundamentals figures are **byte-identical** to the saved `.json` (50,191 / 52,374 / 25,630 / 41,961 / 52,126 / 53,647 / 21,663 / 49,809 B). That tests the new parameters directly, without the price problem.
- **No lone marker:** a panel with no history draws no snapshot point either — a single point is not a chart.

## Cross-cutting verification

- **`run_full_refresh()` end to end**, isolated, 8 tickers: all seven export artefacts, `facts_growth` widened automatically to 10 concepts, `facts_full` carrying 15,627 growth values, 48 figure files, four CSVs, no `.tmp`. **1,055 project files checked by mtime — this run wrote nothing into the project's `data/`, `figures/` or `full_refresh_report.md`.**
- **The app**: `main()` runs to completion with Data first; `render_data_tab` exercised for all 8 tickers; the real server starts headless, answers `/_stcore/health` with `200 ok`, serves a 10,951-byte index, clean log.

**Not verified, honestly:** nothing was viewed in a browser. The green diamond's contrast against the blue series, whether a 3×3 growth grid is comfortable at real container widths, and whether the single snapshot legend entry lands where a reader expects are all unconfirmed. What is verified is that every number plotted, and every number excluded from the mean, is correct.

## One thing you should know

Your `data/app/` and `figures/` were regenerated at 10:20 today from a **partially updated** code state: `facts_growth.parquet` still has 3 concepts, the growth figures 3 panels, and the valuation figures no snapshot marker. Nothing is broken — the app runs against it — but none of Part 3's or Part 4's output is in it. A re-run picks all of it up:

```
python -c "from main import run_full_refresh; run_full_refresh()"
```

Still open from earlier tasks, untouched here: the `V`/`STZ` missing-`SharesOutstanding` finding, the `main()` vs `run_full_refresh()` drift items, `APP_EXPORT_DIR` belonging in `config.py`, and now `p_ffo` missing from `build_snapshot`.

No scratch scripts were left behind.
