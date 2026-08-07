# Sidebar — Data Freshness, Metric Encyclopedia, Profile Coverage

**Date:** 2026-08-07
**Touched:** `config.py` (two optional `Metric` fields + documentation + two accessors), `app.py` (sidebar navigation, freshness, two reference pages).
**`figures.py` and `main.py` are unmodified** — SHA-256 identical to their pre-task values (`341B2C76…`, `FD2B1B2C…`).
**78 verification checks, all passing.**

> **Note on the dependency reading.** `app_refinements_report.md`, `data_tab_report.md` and `metrics_registry_report.md` are no longer in the repo, and the project is not a git repository (`fatal: not a git repository`), so they could not be recovered that way. `MDs/bugfixes_opdate_history.md` carries the substantive findings of all three, and the current `app.py` / `config.py` / `metrics.py` / `main.py` were read in full. Nothing in this task rested on the missing files.

---

## Part 1 — Navigation decision

**Chosen: a sidebar radio switching the whole main area between `Analysis`, `Metric encyclopedia` and `Profile coverage`.** One file, no `pages/` directory, no custom CSS.

| option | why not |
|---|---|
| four more tabs (nine total) | the brief's own constraint, and correct — nine tabs in a row is a scroll strip, not navigation |
| Streamlit native multipage (`pages/`) | breaks the prototype's "no multipage structure" convention *and* would split `app.py` into a package, with the ticker selection needing to travel through `session_state` between pages. Real cost, no benefit here |
| **sidebar radio** | keeps one file, keeps the convention, and is the only option that solves the ticker-independence problem structurally |

**The deciding reason is ticker-independence, not tab count.** The reference pages describe the pipeline, not a company. Putting them beside a ticker-specific tab set invites exactly the misreading the brief warns about. So the view switch also **hides the ticker and as-of controls** when a reference page is open, and puts a caption in their place: *"Reference pages describe the pipeline itself and do not depend on the selected ticker."* There is then nothing on screen to misattribute — a stronger guarantee than a disclaimer next to a live selector.

**The analysis view is untouched.** Same five tabs, `Data` still first, same order, same widgets — asserted by AST: the analysis tab list is still an explicit five-element literal beginning with `'Data'`. The existing body moved verbatim into `render_analysis(...)`; nothing inside it changed.

*Convention check:* no CSS was added and no `pages/` directory exists — both asserted.

## Part 2 — Freshness

Moved from an `st.caption` under the title into `render_freshness(meta)` at the **top of the sidebar**, above the view switch, so it is visible on every tab and every page:

```
Data as of 2026-08-06
8 of 8 tickers produced data
period `quarterly`
```

`tickers_without_data` **is** included — it is the same honest-coverage signal the data tab and the comparison warnings already surface, and a run where two tickers silently produced nothing is exactly when you want to know. It renders as a second line **only when the list is non-empty**; an empty list produces no element at all, not an empty label. Both branches are exercised in verification.

The old caption is gone — asserted that neither `"Data exported"` nor `"No data in this run"` appears anywhere in `app.py`, and that `tickers_with_data` is referenced in exactly one place.

**One thing I did not remove.** That caption also carried a sentence describing what the pipeline does ("fetches SEC EDGAR 10k and 10q filings… as pure as possible"). That is positioning, not freshness, so it stays under the title. The task said not to leave *the information* in two places; the run timestamp and counts now exist in exactly one.

## Part 3 — Where the documentation lives

**Two optional fields on the `Metric` dataclass**, as recommended: `description` and `formula`, both `str | None = None`, plus a `documented` property.

The argument for the alternative — a separate module keyed by id — is that 52 entries × 6 lines makes the registry long, and it does: the `METRICS` block grew from ~65 to ~330 lines. I still kept it inline, for one reason that survives scrutiny: **the registry is where someone adds a metric**, and documentation that lives elsewhere is documentation that gets skipped.

But the brief's stated benefit of inline — "cannot silently lack documentation" — **is not actually true**, and I would rather say so than rely on it. The fields are optional with `None` defaults (they have to be, or every derived structure changes shape), so a new metric can arrive undocumented from either location. The guarantee has to come from a check, not a filename:

```python
def undocumented_metrics() -> list[str]:
    return [m.id for m in METRICS if not m.documented]
```

The encyclopedia calls it and shows a warning listing the gaps; an individual entry without documentation renders *"Not documented yet"* rather than a blank section; and verification asserts against it. That is what makes the coverage claim real.

**Existing fields and every derived structure are unchanged** — `FUNDAMENTALS_TO_PLOT` is still 29 five-tuples with the constant `False` in position 5, `VALUATIONS_TO_PLOT` still 13 four-tuples, `GROWTH_PANELS` still 10 pairs, `QUARTERLY_COUNTERPART` still 11 entries, `HARMONIC_MEAN_CONCEPTS` unchanged. All asserted.

## Part 4 — Content, sourced from the code

All 52 entries documented; **the gap list is empty**. Every formula was derived by reading `metrics.py`, `main.py` (`add_derived_concepts`, `calculate_all_metrics`, `build_valuation_history`, `build_snapshot`) and `config.py`'s concept mappings.

Shared mechanisms are documented once rather than repeated: `GROWTH_MECHANISM_NOTE` (the 4-quarter lag, the positive-values requirement, the `min_base_ratio` guard and its seven loosened concepts, TTM vs. quarterly) and `VALUATION_MECHANISM_NOTE` (which price, how market cap and EV are built, the harmonic-vs-arithmetic mean convention read from the registry, the snapshot marker, the 0.1%-of-revenue denominator guard).

### The calibration case, confirmed — and it is worse than advertised

**`pe_to_revenue_growth` departs from the textbook PEG twice, not once.**

1. It divides by **revenue** growth, not earnings growth — as the brief said.
2. That growth rate is **not the pipeline's own `calculate_growth`**. `build_valuation_history` computes it inline as `wide.groupby("ticker")["Revenue_TTM"].pct_change(periods=4)`. So this single number skips the positive-value requirement and the `min_base_ratio` guard that every other growth figure in the project passes through, and instead gets its own rules: growth must exceed 2%, results beyond ±30 are dropped. A user comparing this panel against the Revenue growth panel is looking at two differently-computed numbers.

### Every other departure from the conventional definition

| metric(s) | what this pipeline does | conventional definition |
|---|---|---|
| `pe_ratio` (and `payout_ratio`) | EPS is **computed**: `NetIncomeLoss_TTM / SharesOutstanding`, share count normally the diluted weighted average | reported diluted EPS |
| `pb_ratio` | additionally **blanked when TangibleEquity < 0** | no such rule |
| `ev_fcf`, `ev_ebitda`, `ev_sales` | EV = market cap + **LongTermDebt** − cash | total debt incl. short-term, plus minority interest and preferred |
| `debt_to_equity` | **long-term debt only** | total debt, or total liabilities |
| `p_tbv` | subtracts **only Goodwill** | subtracts all intangibles |
| `p_ffo`, `ffo_margin`, `FFO_TTM` growth | adds back **total D&A** | NAREIT: real-estate depreciation only |
| `net_interest_margin` | ÷ **total Assets**, period-end | ÷ average **earning** assets |
| `provision_ratio` | ÷ **Revenue** | ÷ average loans |
| `roe`, `roa`, `equity_to_assets`, `inventory_turnover`, `dio`, `dso`, `dpo` | **period-end** balances | period **average** balances |
| `expense_ratio` | `combined_ratio − loss_ratio`, by subtraction | reported underwriting expenses ÷ premiums |
| `combined_ratio` | one `BenefitsLossesAndExpenses` tag ÷ earned premiums | losses and expenses summed separately |
| `p_core_earnings` | net income − realised investment gains, nothing else | varies, usually more adjustments |
| `rule_of_40` | revenue growth + **FCF** margin | often EBITDA margin |
| `ev_ebitda` | EBITDA = operating income + D&A | equivalent, but never touches net income/interest/tax |
| all growth panels | **declines to produce a value** when either side is ≤ 0, or the base is under 33% of the current value | computes it and returns a meaningless or explosive number |
| `revenue_yoy_growth`, `efficiency_ratio` (`financial` profile) | `Revenue` maps to **RevenuesNetOfInterestExpense** | gross revenue — though for the efficiency ratio this makes it *closer* to the conventional bank measure, not further |
| `SharesOutstanding` growth | passes through `normalize_split_adjusted`, which rescales history toward the latest value using common split factors | no analogue — a data-cleaning step |

That table is, as the brief anticipated, one of the more valuable outputs here: two-thirds of these would be silently mis-described by a competent finance textbook.

### One dead input found while reading

**`RealEstateDepreciation` is fetched, TTM'd, and never used.** It is in `TTM_CONCEPTS`, so `RealEstateDepreciation_TTM` is computed every run — and `grep` finds **zero consumers** in `main.py`, `metrics.py` and `figures.py`. It is precisely the input NAREIT FFO requires, and FFO is built from total D&A instead. Reported, not fixed: changing the FFO definition is a modelling decision, not a documentation task.

### Nothing was left undocumented — with one honest caveat

The gap list is empty, but the confidence is not uniform. **The formulas name the pipeline's internal concept names** (`Revenue_TTM`, `Assets`, `Investments`, `ClaimsReserve`), which is the correct level: that is the vocabulary the code uses. **Which XBRL tag each of those resolves to is profile-dependent** — `get_concept_candidates(ticker)` layers `PROFILE_CONCEPT_OVERRIDES` and `TICKER_CONCEPT_OVERRIDES` over the base map, so `Revenue` for a bank is a different tag than for a retailer. Where that changes the meaning I said so inline (`Revenue` → `RevenuesNetOfInterestExpense` for `financial`); I did not enumerate every profile's tag list per metric, and the encyclopedia does not claim to.

### Language

**English throughout**, matching `LANGUAGE_PRIMARY`. The known inconsistency is now narrower than the brief describes, because `figures.py`'s German UI strings were translated between the last run and now. What remains:

- **Three registry labels still contain "Quartal"**: `Revenue growth (Quartal, YoY)`, `Net Income Growth (Quartal, YoY)`, `Equity Growth (Quartal, YoY)`. These are rendered onto charts and must stay byte-identical, so they were not touched. `GROWTH_MECHANISM_NOTE` refers to *Quartal* deliberately, so the explanation matches the label the reader sees.
- **`main.py` console output**: `"WARNUNG: Duplikate gefunden!"` (two places).
- **German code comments** in `figures.py`.

Not fixed here, as instructed.

## Part 5 — The profile coverage page

**Generated from `config.is_hidden` on every render**, via a new `config.profile_visibility()` returning `{profile: {metric_id: visible}}`. Nothing is hand-written.

### Design point 1 — `is_hidden` takes a ticker, and that turns out not to matter

`is_hidden(ticker, metric)` uses the ticker **only** to look up `TICKER_PROFILES[ticker]`; everything after that (`PROFILE_HIDDEN`, `_DERIVED_CONCEPT_CONSUMERS`) is keyed by profile, with no per-ticker override in that path. So a representative real ticker per profile is used.

I checked whether that is actually safe rather than assuming it: **all 501 profiled tickers × 52 metrics were evaluated, and no ticker disagrees with its profile's representative — zero disagreements.** A synthetic ticker name would *not* work: it is absent from `TICKER_PROFILES` and would silently resolve to `DEFAULT_PROFILE`. That is noted in the function's docstring so the next person does not try it.

### Design point 2 — presentation of a 52 × 24 matrix

**Both views, because they answer different questions:**

- **A profile selector** (default `standard`) showing that profile's metrics split into *Shown* / *Hidden for this profile*, grouped by chart. This answers *"why does JPM show different metrics than AAPL"* — the question a user actually arrives with, and the one Part 5.4 asks to make connectable.
- **Below it, the full matrix**: 52 rows × 24 profile columns of ✓/·, plus a "visible in N profiles" count, in a horizontally scrolling `st.dataframe`. This answers the inverse — *"who sees this metric"* — which the matrix is uniquely good at and the per-profile view cannot show at all.

A single view would have forced one of those questions to be unanswerable; the matrix alone would be authoritative but unreadable as a first impression.

### Design point 3 — growth panels included

Yes, and with no extra work: `profile_visibility()` iterates `METRICS`, so all three chart types are covered by the same generation. The per-profile view groups by `chart`, which puts growth in its own section automatically.

### Design point 4 — profile visible in the analysis view

The sidebar already showed `Profile: \`financial\``. It now also points at the page: *"see **Profile coverage** for what this profile shows and hides"*, and the ticker selector still renders each option as `JPM — financial`.

## Part 6 — Verification

**78 checks, all passing.**

### Nothing regressed — and the honest version of that claim

`figures/` was written by the 2026-08-06 19:22 run and `data/app/` holds that same run's frames, so those are the exact pre-change inputs. Rebuilding gives byte-identical output for 9 of 24 figures — and **the other 15 differ only because `figures.py`'s German UI strings were translated between that run and now** (`Quartal` → `quarterly`, `Keine Daten` → `No Data`, `Snapshot (aktuell)` → `Snapshot (current value)`, `Stand:` → `Date:`).

Rather than wave that away, the check parses both documents, collects **every differing leaf value**, and asserts that each one is explained by applying that enumerated translation list — so a genuine label, order, or numeric change would still surface. Result: **0 unexplained leaf differences across all 24 figures** (8 tickers × fundamentals, growth, valuation). Valuation is compared with `as_of` pinned to the run date, because `build_valuation`'s window is anchored on `today()` and today is a day later.

Derived config structures asserted unchanged in shape and content (above).

### Encyclopedia coverage

- Every one of the 52 registry metrics is documented; gap list empty.
- Every fundamentals/valuation formula **names concrete inputs in backticks** and **states its period basis**. This check found five real omissions on the first run — `rule_of_40`, `expense_ratio`, `operating_leverage`, `pb_ratio`, `p_tbv` had no period basis stated — which were then fixed rather than the check relaxed.
- Growth formulas are exempted from the "names another concept" rule only where the id *is* the concept, and their shared mechanism note is asserted to cover the lag, the positivity requirement, the minimum base and the TTM distinction.
- The harmonic set in the note is asserted to equal `{m.id for m in METRICS if m.harmonic}`, so the documentation cannot drift from the registry.

### The coverage matrix matches `is_hidden`

All **24 × 52 = 1,248 cells** re-checked against `config.is_hidden` directly, not against the generator's own output — 0 mismatches. Plus targeted counts including the extremes the brief asked for: `p_ffo`, `p_ppnr`, `PPNR`, `FFO_TTM` visible in **1 of 24**; `revenue_yoy_growth`, `Revenue`, `SharesOutstanding` in **24 of 24**; `pe_ratio` in 23.

### A new metric flows through automatically

A probe `Metric` was appended to `METRICS` during the run: `undocumented_metrics()` detected it, the coverage matrix picked it up across all 24 profiles, the encyclopedia's fundamentals section included it, and it rendered as *undocumented* rather than blank — none of which required touching either page. Removed afterwards, and asserted removed.

### `app.py`

- **Imports no pipeline module** (AST): `config`, `figures`, `json`, `os`, `pandas`, `streamlit`.
- **The page body runs to completion in bare mode in all three views**, plus both freshness branches and both reference pages called directly.
- **The real server** starts headless, answers `/_stcore/health` with `200 ok`, serves a 10,951-byte index, clean log.

### What was not verified

**Nothing was viewed in a browser.** Whether the sidebar is too crowded with freshness + view switch + ticker controls stacked, whether a 24-column matrix scrolls usably, whether the encyclopedia's filter box is discoverable, and how the three encyclopedia tabs read at real widths are all unconfirmed. What is verified is that every formula shown is the one the code implements, and that the coverage table agrees with `is_hidden` cell for cell.

---

Still open from earlier tasks, untouched here: `V`/`STZ` missing `SharesOutstanding`, `p_ffo` missing from `build_snapshot`, the `main()` vs `run_full_refresh()` drift items, `APP_EXPORT_DIR` belonging in `config.py`, and now the unused `RealEstateDepreciation` and the two remaining German console strings.

No scratch scripts were left behind.
