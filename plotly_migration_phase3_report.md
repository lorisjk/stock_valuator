# Plotly Migration — Phase 3 Report (Ticker Overlays)

**Date:** 2026-08-05
**Scope:** one new function in `figures.py` — `plot_ticker_comparison`. `config.py` and `main.py` untouched; the four existing plot functions untouched. No Phase 4 (cross-sectional/peer-percentile) capability.

**Note on the prior reports:** Phase 1's report is in the repo and was followed. Phase 2 was built and then rolled back at your request — its report no longer exists, because the conclusion it reached (Plotly's native legend already does per-trace show/hide, so `updatemenus` buttons for that purpose are pure duplication) is exactly why it was reverted. That conclusion is honored here: this phase adds **no buttons**.

---

## Step 1 — Design

### 1.1 Function shape

```python
plot_ticker_comparison(tickers, concept, data, output_path, years=5, value_column=None)
```

One trace per ticker on a single subplot. It reuses Phase 1's scaffolding directly: `_make_subplot_figure(1, 1, [concept])`, `_style_axes` (2-year date ticks, percent `tickformat`), `add_hline` for reference lines, and `_write_figure` for the HTML + JSON dual output with the same stem convention. Trace styling matches the single-ticker charts (`mode="lines + markers"`, `connectgaps=True`).

**Chart furniture is looked up, not passed in.** `_concept_plot_spec(concept)` scans `VALUATIONS_TO_PLOT`, then `FUNDAMENTALS_TO_PLOT`, then `GROWTH_PANELS` and returns `(ylabel, ref_line, percent, is_valuation, value_column)` from the same config tuples the single-ticker charts read. A caller therefore cannot produce a comparison chart whose axis label, percent formatting or reference line disagrees with the single-ticker chart for the same metric — they come from one source. An unknown concept is refused rather than guessed at.

That lookup also makes growth panels work for free: `Revenue`, `NetIncomeLoss` and `SharesOutstanding` resolve to `value_column="yoy_growth"`, `percent=True`, `ref_line=0`, which is exactly what `plot_growth` draws. `value_column` can be overridden explicitly if ever needed.

**Hover:** `hovermode="x unified"`, so one hover shows every ticker's value at that date. This is the one genuine comparison affordance added, and it is not something the legend already does.

### 1.2 / 1.3 — Scope and per-ticker visibility (these two collapse into one rule)

**Decision: any tickers may be compared; the gate is `is_hidden(ticker, concept)`, per ticker, not a profile-equality rule.** A requested ticker whose profile hides the metric is dropped from that chart.

This is an evidence-based rejection of the same-profile-only option. Measured over the 24 profiles:

| metric visible in … | examples |
|---|---|
| **24 of 24 profiles** | `roe`, `revenue_yoy_growth`, `pe_to_revenue_growth`, and all three growth panels |
| 23 | `pe_ratio`, `income_yoy_growth`, `dividend_yield` |
| 3 | `p_tbv` (`financial`, `insurance_life`, `insurance_pc`), `dio`/`dso`/`dpo` (`retail`, `consumer_staples`, `homebuilder`) |
| 1 | `p_ffo` (`reit`), `efficiency_ratio` / `p_ppnr` (`financial`), `ffo_margin` (`reit`) |

A same-profile-only rule would be **wrong in both directions**:

- **Too strict.** Six metrics are meaningful for every profile in the universe. Forbidding `revenue_yoy_growth` for a `retail` ticker against a `consumer_staples` one has no economic justification. Worse, `p_tbv` is visible for exactly `financial` + `insurance_life` + `insurance_pc` — a bank against an insurer on price-to-tangible-book is a perfectly sound comparison that a profile-equality rule would block. (Verified: `JPM`, `BAC`, `AFL` on `p_tbv` renders all three.)
- **Redundant.** For the narrow metrics, the profile system already blocks the nonsense. The brief's own example — a bank's `p_tbv` against a software company — cannot be plotted anyway, because `p_tbv` is hidden for `standard`. A second, coarser gate on top of the existing one adds nothing except false negatives.

The right granularity is the one `config.py` already uses: **metric × profile**, not profile × profile. Going behind `is_hidden` would also contradict the whole point of `PROFILE_HIDDEN` — those metrics are hidden because the number is misleading for that business model, not merely uninteresting.

**Because the rule is per ticker, 1.2's mismatch case is real and reachable, so it is handled rather than designed away.** Of the three options offered:

- *Show it anyway with a note* — rejected: it renders a number the project has already decided is misleading for that ticker.
- *Refuse the whole comparison* — rejected: it throws away four good tickers because of one bad one, and the user cannot see which one was the problem without re-reading the config.
- **Chosen: drop the ticker, and never silently.** The drop is printed to stdout *and* written onto the chart as a red annotation below the axis: `Nicht dargestellt: AAPL (für Profil 'standard' ausgeblendet)`. The HTML is then self-documenting — anyone opening the file later sees why there are two lines instead of three, without access to the console output or the config.

The same mechanism covers the second, data-driven exclusion reason: a ticker that passes `is_hidden` but has no rows for that concept is dropped with `(keine Daten)`. If **no** ticker survives, neither output file is written — consistent with Phase 1's "either both files exist or neither does" guarantee.

### 1.4 — Chart furniture in multi-ticker mode

- **Per-ticker mean lines: omitted.** Followed the brief's recommendation. Up to five horizontal red lines plus five `Ø …` labels would dominate a chart whose entire purpose is comparing the lines themselves; and a per-ticker mean is a single-ticker question, which `plot_valuation` already answers. The harmonic/arithmetic distinction (`HARMONIC_MEAN_CONCEPTS`) therefore does not apply to comparison charts at all.
- **Metric-level reference lines: kept.** `ref_line` comes from the concept, not the ticker (the 0 line for growth metrics, 1.0 for `combined_ratio`, 0.4 for `rule_of_40`), so it stays meaningful with any number of tickers.
- **Valuation window: same cutoff, same default, same parameter name.** Followed the recommendation, and enforced structurally rather than by convention: `_concept_plot_spec` reports whether the concept came from `VALUATIONS_TO_PLOT`, and only then is `pd.Timestamp.today() - pd.DateOffset(years=years)` applied — the identical expression `plot_valuation` uses. Fundamentals and growth concepts keep their full history, matching `plot_fundamentals`/`plot_growth`, which apply no cutoff. Verified numerically in Step 3.

### Ticker cap

**2 to 3 distinct tickers**, enforced; outside that range the call is refused with a message and writes nothing.

- The **upper** bound of 3 was set by you. It is enforced, not advisory: 4 tickers are now refused outright rather than silently truncated — truncation would drop data the caller asked for without saying so, which is the failure mode 1.2 exists to avoid. The color palette was narrowed to match, so palette width and cap cannot drift apart.
- The **lower** bound of 2 is a category check — one ticker is not a comparison, and `plot_fundamentals`/`plot_valuation` already serve that case better. Note this is about the *requested* count; if exclusions reduce a valid request to a single surviving line, the chart is still drawn, with the annotation explaining the rest. That asymmetry is deliberate: a caller error is refused, a data fact is reported.
- Duplicates are de-duplicated before counting, preserving first-seen order.

### Colors

Pinned palette `["#1f77b4", "#d62728", "#2ca02c"]`, indexed by the ticker's **position in the requested list**, not by its position among the survivors. So a ticker keeps its color when a *different* ticker gets excluded — the color follows what you asked for, not what happened to make it through. The first color is Phase 1's `_PRIMARY_COLOR`, so a two-ticker comparison's first line matches the single-ticker charts.

## Step 2 — What was implemented

`figures.py` gained `_concept_plot_spec`, the public `concept_source`, `plot_ticker_comparison`, the `_COMPARISON_COLORS` palette, and the `MAX_COMPARISON_TICKERS` / `MIN_COMPARISON_TICKERS` constants. `TICKER_PROFILES` and `DEFAULT_PROFILE` were added to the existing `config` import so the exclusion note can name the responsible profile. Nothing else in the file changed — the four existing plot functions are byte-identical, verified by the Step 3 regression check.

### Wiring into `main.py`

`config.COMPARISON_GROUPS` defines the groups (name, tickers, concepts), placed next to the other figure config. `main.render_comparison_charts(metrics_long, valuation_history, facts, available)` renders them and is called from **both** plot paths — `main()` (with `TICKERS`) and `run_full_refresh()` (with `active_tickers`, timed into the run's total like the per-ticker plots). Output naming: `figures/compare_<group>_<concept>.html` / `.json`.

Two routing/robustness decisions in that function:

- **Concepts are routed to the right dataframe by `figures.concept_source(concept)`**, which reads the same config lookup the chart furniture comes from — so a group can freely mix fundamentals, valuation and growth concepts (`big_banks` mixes `efficiency_ratio`/`roe` from `metrics_long` with `p_tbv` from `valuation_history`) without the caller tracking which frame holds what. An unrecognised concept is reported and skipped, not guessed.
- **A group whose tickers are not all in the current run is skipped whole**, with one consolidated summary line. Drawing a partial comparison would be wrong here: an absent ticker is a property of *the run* (`main()` currently has `TICKERS = ["BX"]`), not of the data, and `plot_ticker_comparison`'s "keine Daten" note would misattribute it to a data gap. Verified: with only `JPM`/`BAC`/`WFC` in the run, exactly the `big_banks` group renders (3 charts, 6 files) and the other seven are reported as skipped.

The eight configured groups are starter content, chosen to be real peer sets and validated against the universe before being committed — every ticker exists and is active. `payments` (V, MA, AXP) is **deliberately cross-profile**: AXP is `financial`, so `operating_margin` is hidden for it, which exercises the 1.2 exclusion path in production rather than only in tests. Edit or extend the list freely; nothing in the code depends on these particular groups.

## Step 3 — Verification

Same method as Phases 1 and 2: real pipeline (cached EDGAR facts, live yfinance prices) run in-memory in an isolated working directory with a copied cache, so the project's `data/`, `cache/` and `figures/` were untouched. Every assertion reads the written `.json` back through `plotly.io.from_json`. **All checks passed.**

**Real comparison** — `AAPL`/`MSFT`/`ADBE` on `revenue_yoy_growth`: three traces named and ordered as requested, three distinct colors, each trace's value array numerically identical to `metrics_long` (72/76/72 points), percent tickformat and the 0 reference line taken from the config tuple, every trace carrying a legend entry, **no** `updatemenus`, and no `Ø` mean-line annotations.

**Cross-profile positive case** — `JPM` + `BAC` (`financial`) + `AFL` (`insurance_life`) on `p_tbv`: all three rendered, no exclusion note. This is the comparison a same-profile-only rule would have blocked.

**Mismatched visibility (the case 1.2 exists for), tested directly on three different metrics** rather than assumed:

| chart | requested | dropped | note written onto the chart |
|---|---|---|---|
| `p_ffo` | AMT, O, **AAPL** | AAPL | `Nicht dargestellt: AAPL (für Profil 'standard' ausgeblendet)` |
| `efficiency_ratio` | JPM, BAC, **AAPL** | AAPL | same form |
| `dio` | AZO, COST, **MSFT** | MSFT | same form |

In each case the drop was independently confirmed against `config.is_hidden`, the surviving tickers kept distinct colors, and both output files were still produced. Color stability was checked explicitly: requesting `[AMT, O]` vs `[AMT, AAPL, O]` on `p_ffo` keeps AMT on `#1f77b4` while O correctly shifts `#d62728` → `#2ca02c`, proving colors track the requested position.

**Degenerate paths, each confirmed to write neither file:** metric hidden for *every* requested ticker (`AAPL`+`MSFT` on `p_ffo`), 6 tickers (over the cap), 1 ticker (under the minimum), and an unknown concept. Exactly 5 tickers is accepted and yields 5 traces; `[AAPL, AAPL, MSFT]` dedupes to two traces in order.

**Valuation window (1.4) — the decisive check:** for `JPM` and `BAC` on `pe_ratio`, the comparison chart's x-values are **element-wise identical** to the same ticker's `pe_ratio` trace in its own `plot_valuation` output (JPM 2021-09-30…2026-03-31, 19 points; BAC 2021-09-30…2026-06-30, 20 points), with identical y-values. Conversely a fundamentals metric keeps its full 72-point history with no cutoff, and `years=2` correctly narrows the window to 7 points.

**Growth concepts:** `AAPL`+`MSFT` on `Revenue` reads the `yoy_growth` column and reproduces `plot_growth`'s 72 values exactly, percent-formatted.

**No regression:** `plot_fundamentals` for AAPL still renders the same 9 panels in the same order and picked up none of the comparison-only layout settings (no `updatemenus`, no `hovermode`).

### Verification of the cap change and the wiring

Re-run against the real pipeline with all 25 group tickers loaded. **All checks passed.**

- `MAX_COMPARISON_TICKERS == 3`, palette narrowed to 3 colors, and every configured group asserted to be within the cap. Four tickers (`JPM`/`BAC`/`WFC`/`C` on `roe`) are now **refused** — that call would have been accepted under the previous cap of 5 — while three are accepted and yield three traces.
- `render_comparison_charts` produced **24 of 24** configured charts, all 48 files present and non-truncated.
- Every trace in every chart was traced back to the frame `concept_source` routed it to, confirming the mixed-frame groups resolve correctly (e.g. `big_banks/p_tbv` from `valuation_history`, `big_banks/roe` from `metrics_long`).
- The cross-profile `payments` group behaves as designed in production: `operating_margin` renders `V`/`MA` with `Nicht dargestellt: AXP (für Profil 'financial' ausgeblendet)` on the chart, while `roe` (visible in every profile) renders all three.
- Group skipping verified as described above.

### Two data facts the comparison charts surfaced

Neither is caused by this work; both were found because a comparison chart draws several tickers side by side and names what it drops.

1. **`cash_conversion_cycle` is empty for two of three discount retailers.** `DG` reports **no `AccountsReceivable` facts at all** and `DLTR` only 2, so `dso` — and therefore `cash_conversion_cycle = dio + dso − dpo` — cannot be computed (DG 0 rows, DLTR 2 rows, COST 68). That is an honest property of a business model with essentially no trade receivables, not a pipeline defect. The configured group was changed from `cash_conversion_cycle` to `dio`, where all three have full history (DG 62, DLTR 64, COST 68).

2. **Two tickers have no share count at all — a pre-existing gap with wide downstream damage.** The `payments` chart dropped `V` from `pe_ratio` with "keine Daten", which turned out not to be a windowing artifact: `V` exposes **none** of the three tags the project looks for (`WeightedAverageNumberOfDilutedSharesOutstanding`, `WeightedAverageNumberOfSharesOutstandingBasic`, `CommonStockSharesOutstanding`); its `companyfacts` carries only the dei cover-page tag `EntityCommonStockSharesOutstanding`.

   A scan of the cached `companyfacts` for **all 501 active tickers** bounds the problem exactly: **2 tickers** have none of their `SharesOutstanding` candidate tags — **`V`** (`standard`) and **`STZ`** (`consumer_staples`, which has no usable share tag at all, only stock-option-plan tags). Measured downstream damage, identical in shape for both:

   | | `SharesOutstanding` | `EPS_TTM_CALC` | `pe_ratio` | `ev_ebitda` | `pfcf_ratio` | `dividend_yield` |
   |---|---|---|---|---|---|---|
   | **V** | 0 rows | 0 rows | 75 rows, **0 non-NaN** | **0 non-NaN** | **0 non-NaN** | 44 non-NaN |
   | **STZ** | 0 rows | 0 rows | 72 rows, **0 non-NaN** | **0 non-NaN** | **0 non-NaN** | **0 non-NaN** |
   | MA (control) | 74 rows | 72 rows | 68 non-NaN | 0 non-NaN | 0 non-NaN | 42 non-NaN |

   So both tickers' P/E charts are blank, and their market caps rest entirely on the yfinance fallback. (`ev_ebitda` and `pfcf_ratio` are empty for MA too, so those two are a separate, wider issue and not attributable to the share gap.)

   This is out of scope for a rendering task and was **not** fixed here. The fix is a decision, not a patch: whether `EntityCommonStockSharesOutstanding` should become a last-resort candidate tag — it is a cover-page, point-in-time, as-of-filing-date figure rather than a period weighted average, so admitting it changes the meaning of the series and interacts with the yfinance-vs-EDGAR share resolution established in earlier cycles. Worth its own task.

No scratch scripts were left behind; the isolated verification workspaces were deleted after the run.
