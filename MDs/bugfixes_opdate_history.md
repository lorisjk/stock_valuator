# Bugfix History

A running log of bugs found, what caused them, and how they were fixed. Ordered newest first.

Most entries here share a theme: **the pipeline fails silently**. A missing tag returns an empty list, an empty list produces an empty merge, an empty merge produces an empty chart. Nothing crashes. The symptom appears several layers away from the cause, and usually looks like a plotting problem. Nearly every fix below was found by noticing that a *number* looked wrong, not by reading a stack trace.

---

## 2026-08-22 — Per-ticker JSON: two files, not five, and the comparison axis is not needed

The six parquet frames are 309 MB as JSON. The export now also writes
**`data/app/tickers/{TICKER}.json`** (the four chart frames) and
**`{TICKER}.facts.json`** — 1,218 files, **140.5 MB raw, 21.7 MB gzipped**, written by
`export_for_app` before `meta.json`. Per-ticker schema **1**; export schema **3 → 4**. Full
derivation in `per_ticker_export_report.md`.

**Two files rather than the five the inventory proposed, on the measurement.** `facts_full` is
**62%** of a ticker's payload and only two of the six tabs read it; the other four frames together
are **14.0 kB gzipped**, so splitting them as well would have tripled the file count to save under
10 kB on a first paint. The split that was kept pays for itself twice: a comparison never needs
`.facts.json` either, so the core file *is* the comparison payload.

**Column-major, and the alternative that looked better was worse.** Records
(`[{concept: …, value: …}]`) are 580 kB for AAPL; `{columns, data}` is **324 kB**. Nesting by
concept is smaller again raw (236 kB) but **larger gzipped** (54.3 kB against 52.3 kB) — and it
cannot reproduce the parquet's row order, because `valuation_history` is stored date-major and its
(ticker, concept) groups are interleaved, with 110 groups across the frames not even ascending in
`end`. Column-major reconstructs the slice row for row without sorting anything.

**JSON cannot carry ±inf, and the data has 44 of them.** `Infinity` is not valid JSON and
`JSON.parse` rejects it, so the value array gets `null` — what a chart would draw anyway — and the
true value is recorded in a `nonfinite` sidecar keyed by row index. They come from division by
zero: `EPS_TTM_CALC` / `EPS_QUARTERLY_CALC` on 7 tickers, `operating_margin_quarterly` /
`fcf_margin_quarterly` on 3. **The parquet keeps them, so Streamlit is unaffected.**

**Dates are `YYYY-MM-DD`.** Every `end` value in all five frames is midnight — these are period
ends, not timestamps — so the bare date is lossless and a third the width of a full ISO stamp.
Verified across all 2,344,025 exported values including the earliest (2005-03-31) and latest
(2026-08-21).

**Per-ticker files carry no timestamp, deliberately.** A ticker whose data did not change produces
a byte-identical file, so the nightly commit stores nothing for it. Measured over five simulated
price-only nights: **613 files change, 609 of them core and zero of them facts.** The deploy branch
grows **+6.9 MB/night** for the JSON against **+0.23 MB/night** for the parquet — git dedupes the
four unchanged parquet files, so the workflow's standing "~18.8 MB a night" is itself pessimistic
on a night without filings. About **210 MB/month**, flattened by the same monthly orphan reset.

**The comparison axis was measured and rejected.** A concept-major file averages **186 kB gzipped**
(`pe_ratio` the largest at 327 kB). `SUGGESTED_MAX_COMPARISON_TICKERS` is **3**, and three core
files are **42 kB** — already cached if the user browsed those tickers. Break-even is **13
tickers**, more than four times the suggested maximum, and the axis would add 13 files and 12.3 MB
to every nightly commit. Not built.

**Round-trip verified on all 3,045 (ticker, frame) slices, not a sample** — `assert_frame_equal`
with `check_exact=True` and dtypes, including AAPL, JPM, O, V/STZ/ERIE/BKR and CRWV/FIG. Float
`repr` is byte-identical after the round-trip across 463,069 sampled values.

**A sampled validator check was written first and thrown away.** It passed eight of twelve
deliberate corruptions because none of them landed on a sampled ticker. All 1,218 files are opened
and checked against the parquet slice they were cut from instead: **1.9 s**, 3.6 s for the whole
validator. 12/12 mutations now rejected.

**Found and recorded, not fixed:** `current_snapshot.parquet` holds 4 rows for **EA**, which is not
in the universe (it produced no metrics, valuation or growth), so the per-ticker export does not
carry them. The validator asserts exactly this — every unexported row belongs to a ticker the
universe does not list.

**`config.py`, `figures.py` and `app.py` are untouched.** The six parquet frames come back
content-identical and byte-identical across two runs, and so do all 1,218 JSON files.
`export_for_app` now takes **45.8 s** end to end against a ~40 min pipeline run.

---

## 2026-08-22 — The config registry is exported as JSON, and profile beats ticker by 6.6x

`streamlit_inventory.md` §1.5 called the missing registry export "the single biggest gap in the
current export": `app.py` imports `config.py` and calls into it at runtime for every picker label,
axis label, reference line, percent flag and the whole encyclopedia. A browser cannot. The export
now writes **`registry.json`** (83.4 kB raw, **11.7 kB gzipped**) and **`concept_candidates.json`**
(242.9 kB raw, **7.8 kB gzipped**) alongside the six parquet frames, from `export_for_app`, before
`meta.json`. Registry schema **1**; export schema **2 → 3**, because `meta.json` gained a
`registry` block and the directory gained two files. Full derivation in
`registry_export_report.md`.

**The size question the brief posed had a measurable answer, and it went the cheap way twice.**
Exporting `get_plottable_metrics(chart, ticker)` for 609 tickers × 3 charts inlines to **274 kB**;
exporting `profile_visibility()` plus each ticker's profile is **42 kB — 6.6× smaller**. The
substitution is only legitimate if the two agree, so it was checked for **all 1,827 (chart,
ticker) pairs**: same ids, same order, same labels, **1,827/1,827 identical**. That is not luck.
`is_hidden` looks the ticker up in `TICKER_PROFILES` and then consults `PROFILE_HIDDEN` and
`_DERIVED_CONCEPT_CONSUMERS`, both keyed by profile; there is no per-ticker branch in that path.
The same argument applies to `get_concept_candidates`, where ticker overrides *do* exist — but
they produce only **39 distinct resolved dicts across 609 tickers**, so storing the variants once
and indexing into them is **2,837 kB → 243 kB, 11.7×**.

**The id-namespace trap is now impossible to walk into from the export.** Every metric carries
`id_namespace` and `value_column` explicitly, and the `charts` block carries them per chart. Ten
registry ids are also `facts_full` concept names — `Revenue`, `NetIncomeLoss`,
`SharesOutstanding`, `EPS_TTM_CALC`, `FCF_TTM`, `FFO_TTM`, `OperatingIncomeLoss_TTM`, `PPNR`,
`CoreOperatingEarnings`, `StockholdersEquity` — and **all ten declare `value_column:
"yoy_growth"`**, so no id in the export both sets `percent` and claims to describe the facts
frame's `value` column. That is the `10941700000000.00%` bug closed off at the contract rather
than re-argued in the frontend.

**`METRICS` fields are exported via `dataclasses.asdict`, not a hand-written list**, plus the
three computed properties. A field added to `Metric` therefore reaches the frontend
automatically instead of being silently dropped — which is the failure this project keeps
producing and the reason the registry task made `METRICS` the single source of truth in the first
place. All 10 fields and 3 properties round-trip, values equal to the live objects, `ref_line`'s
`int` 0 versus `float` 0.4 distinction intact.

**The validator gained 10 structural checks, not a row floor.** These files describe `config.py`,
not the filings: their sizes do not drift with new quarters, so a 90% floor would detect nothing.
What matters is that they still answer the question the app asks — every universe ticker
resolvable to a profile whose visibility row covers every metric, every candidate index resolving,
every metric carrying the fields a frontend formats on. **11 deliberate mutations were rejected,
each by the intended check.**

**Found and recorded, not fixed:** `TICKER_CONCEPT_OVERRIDES["ARE"]` is an empty dict — a no-op
that resolves to the `reit` baseline. 33 universe tickers have an override entry; only 32 change
anything.

**`config.py`, `figures.py` and `app.py` are untouched** (empty `git diff`). The six parquet
frames come back content-identical and byte-identical across two runs of the new code. *Harness
note: the published `data/app/*.parquet` differ byte-wise from a local rewrite because CI writes
with `parquet-cpp-arrow 25.0.1` and this machine has pyarrow 24.0.0 — pre-existing, and why
`DataFrame.equals` is the right comparison there and byte equality is the right one within one
environment.*

---

## 2026-08-19 — Empty valuation panels now say why, and the premise needed fixing first

The brief was that V, STZ, ERIE and BKR "render no valuation metrics at all". **They do not.**
V has **456** non-null valuation values across seven multiples spanning 2008-2026; STZ 418, ERIE
203. `pb_ratio`, `pfcf_ratio`, `ev_sales`, `ev_ebitda` and `ev_fcf` all work, because they come
from market capitalisation rather than the EDGAR `SharesOutstanding` series. What is blank is the
per-share family -- `pe_ratio`, `pe_to_revenue_growth`, and `dividend_yield` for three of them --
because `EPS_TTM_CALC` is `NetIncomeLoss_TTM / SharesOutstanding`. Full derivation in
`empty_valuation_notice_report.md`.

**The reader still saw exactly what the brief described, for a reason the brief did not name:
the valuation tab defaults to `pe_ratio`.** And a blank panel is not the "no data" message --
`build_valuation` returns a figure as long as *any* selected concept has data, so `render()`'s
`empty_message` never fires and the reader gets an axis grid with no line, under a working
current multiple.

**No count-based threshold can detect this, measured.** Across the 471 tickers where `pe_ratio`
is plottable, the thinnest ticker that **produces** one has **3** `EPS_TTM_CALC` points, and the
one with the most that produces **none** has **70**. The distributions overlap completely, so the
rule is the direct test instead: does the slice the panel would draw contain a non-null value.

**Six tickers have a blank `pe_ratio`, not four, with four different causes:** V/STZ/ERIE (0
shares, 0 EPS -- the settled case), BKR (2/2, thin), PSKY (7 shares but 2 EPS -- a different link
in the chain), and **EA (70/70/72 and not one non-null value in any real multiple)**. EA was taken
private -- `25-NSE` 2026-08-04, `15-12G` 2026-08-14 -- and this export ran 2026-08-16, so its
fundamentals are complete and its price side is gone. EA is why the notice states the symptom
unconditionally and the cause only where it can prove it.

**Scope forced the wording.** 170 of 500 tickers have at least one empty panel and **97 of those
are `dividend_yield` on a company that pays no dividend** -- a true statement about the business.
The first draft said "this is a gap in the source data"; that would have been wrong for the
largest group, so the unconditional text is now "Nothing was hidden or filtered -- the value is
absent from the source data", with the share-count explanation appended only for the three
tickers where `SharesOutstanding` is genuinely empty.

**Checked and already correct, so unchanged:** the snapshot marker does not strand a lone green
diamond on V's empty `pe_ratio` -- the figure has zero traces, because `build_snapshot` omits
`pe_ratio` for V for the same reason. And the data tab already surfaces the empty multiple, since
`pivot_ticker` passes `dropna=False` and the caption counts all-null columns. Its blind spot is
the *input*: V has zero `SharesOutstanding` rows, and a concept with no rows never becomes a
column. Recorded, not fixed.

**The comparison tab said "No Data"** while the new notice said something else. `figures.py` was
out of scope, so the fact stays there and the wording moved to the app, which translates it and
appends the same conditional clause.

**Only `app.py` changed.** Chart output verified identical to `HEAD:figures.py` across 11 cases in
a process that never imports streamlit. *Harness note: extracting `HEAD:figures.py` with
`subprocess.run(text=True)` decodes git's bytes as cp1252 and mangles the `Ø` in the mean-line
label, making nine byte-identical figures look different.*

---

## 2026-08-19 — The `dei` share-count fallback, twice rejected, now rejected with a number

Revisited because the argument had changed, not because the earlier calls were wrong. Both
prior rejections (2026-08-03 Plotly Phase 3, and the dual-class review) turned on the same
correct point -- `dei:EntityCommonStockSharesOutstanding` is a cover-page count as of the
filing date, not a period weighted average. What was new was that the provenance machinery
(`ttm_source`, `ffo_gains_source`) now exists, so "supply it and mark it" was available for
the first time. Full derivation in `dei_shares_fallback_report.md`.

**Threshold fixed before measuring** (median |dei/us-gaap - 1| <= 2%, p90 <= 5%, chosen as
half of the existing `MIN_SHARE_COUNT_DISAGREEMENT = 0.10` line). **Measured across 27,887
comparable quarters on 545 tickers: median 1.19%, p90 5.20% -- FAIL.** Excluding a class of
decimal-scaling defect the guard does not cover, p90 is 4.90%; that pass is not claimed,
because building the guard is a prerequisite rather than a footnote. The disagreement is also
**one-directional** -- median per-ticker level bias **-1.03%** -- which makes it a different
quantity rather than a noisier one. Split by basis, the `dei` value is within **0.04%** of a
point-in-time `CommonStockSharesOutstanding` and **1.21%** off a weighted average, which is
exactly the stated objection, now quantified.

**The decisive finding was not the threshold: it was that the premise is wrong.** The brief
named V, STZ, ERIE and BKR. `EntityCommonStockSharesOutstanding` **does not exist** in STZ's
or ERIE's `dei` namespace; **V has exactly two facts**, dated 2009-11-13 and 2010-01-27; and
**BKR was never a full failure** -- it has two `us-gaap` values and `dei` reaches back only to
2023-02. Confirmed at the source, not just in the cache: SEC `companyconcept` returns **404**
for `us-gaap/CommonStockSharesOutstanding` on all three and for
`dei/EntityCommonStockSharesOutstanding` on STZ and ERIE.

**Root cause identified, and it is not a tag gap.** V and STZ are missing the share count
**and** `EarningsPerShareBasic`/`Diluted` **together** -- the whole per-share layer. That is
the signature of dimensional tagging: `companyfacts` returns only non-dimensional facts, the
same mechanism already recorded for share classes. These three are class **C** in both
namespaces, and no tag anywhere fixes them. The real route is the `frames` API, dimensional
`companyconcept`, or the R-files -- a fetch-layer change, carried forward.

**Also measured and also rejected:** `NetIncomeLoss / EarningsPerShareDiluted` reconstructs
the filer's own weighted average and is materially better centred (median **0.49%**, signed
bias **+0.03%** against `dei`'s -1.01%) -- but EPS is reported to two decimals, so the implied
count has precision `0.005/|EPS|`, i.e. +/-10% at EPS 0.05. BKR is the worst case for it: its
quarterly EPS runs -0.02 to +0.37 and the derived series swings +/-20% a quarter. It also
derives **0** quarters for V, STZ and ERIE, which have no EPS either.

**Independent check, which the rejection does not contradict:** BKR's latest `dei` cover-page
count is **992,674,071** and the yfinance count the pipeline already uses is **992,674,071** --
ratio 1.0000. The `dei` data is correct. It is the wrong quantity for this series, absent for
the tickers that need it, and unvalidatable for the one that would use it (BKR has **zero**
quarters where a `us-gaap` and a `dei` value coexist).

**Nothing was changed.** `CONCEPT_CANDIDATES["SharesOutstanding"]` is untouched and the parser
still reads only the `us-gaap` namespace, so no `dei` value can reach any series by any path.

---

## 2026-08-19 — 112 candidate tickers surveyed; the fix was to add almost nothing

First per-category pass over `next_500_candidates.md`: the 112 proposed `standard` tickers,
added provisionally to `TICKER_PROFILES` so they could be fetched at all. Full derivation in
`standard_candidates_tag_report.md`.

**274 flags across 107 of 112 tickers -- 2.45 per ticker against the universe's 1.47 -- and
92.3% of them are not fixable by any tag.** Class A 21, class B 128, class C 125. The single
largest group is `DividendsPerShare` at 89 flags and **0% actionable**: 80 of those filers carry
no dividend-family tag of any kind, because they have never declared a dividend. `StockRepurchased`
comes out 0 of 54, reconfirming the 0 of 126 from the `StockIssued`/SBC investigation on a
disjoint population. Read the other way, `ShareBasedCompensation` is **twelve points better**
in the candidates than in the universe -- the tag appended in July is how software companies
tag SBC.

**Not one candidate tag survived as a global `CONCEPT_CANDIDATES` addition, and that is the
main result.** All ten were measured against the existing 500 first. `LineOfCredit`: 173
existing holders, median ratio to their current long-term debt **0.002**, 756 values it would
have injected. `DebtInstrumentCarryingAmount` looks safe at 53.7% identical and a median ratio
of 1.008, and would still have put $7.05bn of debt on BALL where the pipeline has $2m -- it is
a per-instrument footnote tag that equals the total only for single-instrument filers.
`ProfitLoss` flips sign on ACGL, because it includes noncontrolling interests where
`NetIncomeLoss` excludes them. **`sum` versus `fallback` never arose**: the question is upstream
of the mode, because none of these belongs in a shared list in either mode.

**Seven per-ticker `TICKER_CONCEPT_OVERRIDES` applied**, each verified on the filer's own data:
`ProfitLoss` for GWRE/MORN/SMTC (identical on 8/8, 30/30 and 33/33 overlapping quarters, the
existing KEYS precedent); `SeniorNotes` for GWRE and `LineOfCredit` for MORN (identical on 5/5
and 12/12); `DebtInstrumentCarryingAmount` for RGTI and APPF (matching each filer's own
separately tagged maturity schedule, exactly and within 2.0%). Rejected with evidence:
restricted cash for SITM/NAVN (+96.99% on NAVN), `LineOfCredit` for SNEX (-70%) and MELI
(-99.99%), FN and AXTI (fail against their own maturity schedules), EVR (36 ends, no
overlapping quarter and no schedule -- unverifiable, left open), and TRNO's 64-quarter `Capex`
find, which is a profile decision wearing a tag decision's clothes.

**A deleted value that is correct.** GWRE `LongTermDebt` 2022-07-31 disappears, because
`SeniorNotes` brings in 2022-08-01 and `merge_duplicate_period_ends` keeps the later of two
ends within seven days. They are different measurements: four years of accretion at
$2.9-3.7M/quarter, then **+$37.25M in one day**, then $422-432K/quarter. Guidewire adopted
**ASU 2020-06** on the first day of FY2023 and reclassified the equity-conversion component
into debt. Keeping the later end gives 27 points on one accounting basis instead of 28 with a
$37M discontinuity.

**Non-regression:** the existing 500 are **0 appeared, 0 changed, 0 disappeared** on both base
facts (incl. `_TTM`) and `metrics_long`, 733 flags before and after, zero new flags. Anchor
invariant 0 backward moves, now 0/0 for twelve tasks. All 27 changed candidate values are
`NaN -> a number`. Candidate flags 274 -> 269; GWRE and APPF `LongTermDebt` improve (9 ends to
27, +2) without clearing, because the flag measures coverage.

**Also found:** none of the 112 has the 1,000x unit-scaling defect that TBLA/RPAY/MODD show --
all 112 parse a `SharesOutstanding` series, zero flags, implied prices $5.27 to $1,787. The two
survey-flagged tickers in this category (OWL, MBLY) were dual-class understatement in the
survey's own frames-based estimator, which the pipeline never touches. And SHOP, the largest
candidate, is class B on **twelve** concepts: it filed 40-F under IFRS until recently, so its
us-gaap record is the thinnest in the category despite 13.5 years of price history.

---

## 2026-08-18 — One unresolvable ticker killed the whole run, and a stale cache hid it

The first CI run of the nightly workflow died after ~5 minutes on
`ValueError: Ticker AEP not found in mapping.` Two independent defects, and a third found while
fixing them. Full derivation in `ticker_resolution_report.md`.

**1 — `get_cik` raising aborted `run_full_refresh`.** 500 tickers that resolve perfectly well
were never processed because one did not. The tolerance already existed elsewhere in the same
file -- `load_filing_cadences` and `load_latest_filed_periods` have caught this since they were
written -- but the two loops that build the actual data did not. `get_cik` **keeps its
contract** and still raises; only `run_full_refresh` catches, because it is the one loop
sweeping the whole universe. `load_facts` deliberately still dies: it is the ad-hoc path over a
two-ticker list, where silently dropping half the request and reporting success is worse than a
traceback. The skip is recorded in three places -- a `[skip]` line, a section directly under the
run report's metadata, and `meta.json`'s existing `tickers_without_data`, which needs no schema
change because a skipped ticker produces no rows and lands there by construction.

**2 — the mapping cache never expired.** `fetch_or_cache` has supported `max_age_days` all
along and **all four `company_tickers.json` call sites omitted it**, so a cache file was read
forever. The local copy was 37 days old with 10,407 entries; CI fetched 10,396. That is why the
CI crash was not reproducible locally -- the two sides were resolving against different files.
Now `max_age_days=1`, and the four duplicated blocks are one `resolve_cik_mapping()`:
duplication was the mechanism by which they drifted apart on exactly one argument, so removing
it is the structural half of the fix. `explore_tags.py` and the CI preflight go through the same
function, because **a diagnostic that resolves tickers differently from the pipeline cannot
reproduce the pipeline's bugs** -- which is precisely what happened here.

**3 — XOM's CIK changed, and fixing defect 2 would have amputated it.** Not in the brief; found
by diffing the two mappings. ExxonMobil re-domiciled to Texas and `company_tickers.json` now
points XOM at CIK `0002115436` ("ExxonMobil Holdings Corp") instead of `0000034088`. Measured
through the real parser, not by tag count:

| | old `0000034088` | new `0002115436` |
|---|---:|---:|
| parsed rows | 905 | 30 |
| concepts | 14 | 10 |
| period range | 2006–2026 | 2024–2026 |

`Capex`, `OperatingCashFlow`, `StockIssued` and `StockRepurchased` vanish entirely, taking FCF
and with it `pfcf_ratio`, `ev_fcf`, `pfcf_ex_sbc` and `fcf_margin`. **No error would have been
raised**: the ticker resolves fine, it just resolves to eighteen months of a company that has
twenty years. Pinned via `CIK_OVERRIDES` as a **stopgap** -- the old registrant's facts stop at
2026-03-31 and will not advance, so this trades a growing lag for the history. The real fix is
reading both CIKs and merging, which is a fetch/parse-layer change.

**A cache-shadowing hazard worth knowing:** `get_company_info` caches by *ticker*, not by CIK,
so with a warm cache a changed CIK is invisible -- the old file is served. Only a cold cache
exposes it, which is why this surfaced in CI and not locally, and why the XOM measurement had
to fetch both CIKs directly rather than go through the cache.

**`SATS` removed from the universe, and it is not the same case as AEP.** The brief assumed the
other differing tickers would be mapping lag. It is not: EDGAR's submissions file for CIK
`0001415404` reports the ticker as **ECHO**, and yfinance serves SATS **one** price row ending
2026-07-17 against 4,683 for ECHO. An override would have kept a dead symbol alive. Its data was
already hollow -- 720 `valuation_history` rows and **zero** non-null values across all ten
valuation concepts inside the five-year window -- which is why removing it moved no peer band.

**Two guards added.** `build_ticker_to_cik` now refuses a mapping under 8,000 entries (the file
has 10,396; it moved 268 out and 257 in over 37 days, so churn cannot reach the floor but a
truncated download or a schema change would). And `resolve_cik_mapping` audits `CIK_OVERRIDES`
on every run, printing whether each entry is still needed, has become **redundant** because the
file caught up, or is **contested** because the file now says something different -- because an
override nobody revisits is the next stale cache.

**Non-regression:** before/after from one price capture and one warm cache, all 501 tickers,
six frames. **Zero appeared, zero changed, zero disappeared for every ticker except SATS.**

---

## 2026-08-17 — Four consistency items, and the one that turned out to falsify a chart

The items every recent task recorded and left standing, because fixing them inside a task about
something else would have made that diff unattributable. Full derivation in
`final_consistency_report.md`.

**A — `apply_self_relative_scale_guard` counted rows where it meant days.** The last member of
the family `calculate_ttm`, `calculate_rolling_harmonic_stats` and `pct_change` belonged to: a
17-row centred window, which is eight quarters either side only on a series with no hole. The
modal span of the 37,891 full windows is exactly 1,461 days; the tail reaches **4,475 — twelve
years**. Now `[end - 730d, end + 730d]`.

There is no empty run to derive a threshold from, for the same structural reason the five-year
window had none: a span is a sum of quarter-steps, so its support is a lattice with ~91-day
spacing and every gap is that spacing. **The change moved no value, and the reason is the
finding**: the two rules disagree about the reference on 25% of rows -- the row window reaches
further back and sees a maximum larger by 2.4% at the median and up to 5.9x -- but the guard
fires at a factor of ten, so no row crosses it either way. Fourteen rows sit within
[0.10, 0.15) of the threshold; that is the headroom the "no change" result has. The window
stays **centred**, so the guard remains non-causal by decision: the quantity is the scale of
the business around that period, and a backward-only reference would judge a company's early
years against nothing.

**B — `calculate_peer_band_flags` anchored on `pd.Timestamp.today()`.** The same cached data
re-run with only the run date moved a year forward flips **35 of 2,106 flags and drops 16**.
Now takes `as_of`, and windows through the new `within_avg_5y_window`, which uses
`AVG_5Y_WINDOW` -- the second divergent copy of a windowing rule this project has had to
consolidate, after the two revenue-growth computations. Both forms land on the same cutoff this
run date, so the diff is zero; the point is that the next run agrees with this one. The app
cannot pass its `as_of` through (it reads precomputed frames) and `build_snapshot_as_of` emits
no band flags at all, so no as-of view was silently current.

**C — the two scale-guard constants, and a bigger defect underneath them.** `build_snapshot`
guarded `pb_ratio` and `p_tbv` at 0.01 while `build_valuation_history` guards the same two at
0.001. Unified to 0.001, argued on the measurement rather than on strictness: 0.01 is the
*metrics* constant, inherited from before the valuation one existed, and it misclassifies --
Cencora reports $3.05bn of equity on $332.8bn of revenue, 0.92%, for a P/B of 20.0, an ordinary
multiple inside the population 0.01 passes (p99 = 29.3).

Measuring the two expressions side by side turned up what the brief had not named: **the
snapshot had no positivity mask on the denominator, so 111 of 458 published `p_tbv` markers
were negative** (min -201.30), sitting on charts whose line is blank at that period by
construction. That was the larger half of the disagreement and is fixed with it. Three more
multiples still have it -- `pe_ratio` 25, `pfcf_ratio` 40, `ev_ebitda` 7 -- and are recorded as
the next task.

**D — `get_latest_value` returned the newest row even when it was null.** AvalonBay's `FFO_TTM`
is NaN at its two newest periods and 1.60bn at 2025-09-30, so a REIT had no `p_ffo`; 83
(ticker, concept) pairs on 69 tickers were in that state, 49 of them `DividendsPerShare_TTM`.
The bound is **365 days** and it is definitional: a TTM figure covers twelve months, so a value
more than four quarters behind the concept's newest row describes a year that no longer
overlaps the current one. The measured distances corroborate it without being what chose it --
they form a quarterly lattice that stops at 365 and does not resume until 546, so every bound
in [365, 545] admits the identical 37 pairs. The distances run to **5,021 days**, which is why
the unbounded version of this fix is worse than the bug.

The age is measured **inside the series**, so it does not duplicate `days_since_last_filing`,
and it is published as `<field>_age_days` -- the same "how was this number obtained" signal
`ttm_source` and `ffo_gains_source` carry. AVB's `p_ffo` is now 16.7186, which is
26,781,757,961 / 1,601,911,000 exactly.

**E — class 4's interior holes: confirmed not worth the mechanism.** Re-measured against the
current gate: 1,653 interior holes on 812 pairs, against 11,493 pre-history dates and 82,434
collisions. A rule reaching the interior without a tie-break does exist, and measuring it was
kinder than expected -- **zero collisions**, because the post-mask date set is a strict subset
of the pre-mask one (1,290 dates lost, 0 gained). It still loses: it reaches only 1,413 of the
holes, 0.28% of the frame, and it demotes the disjointness guarantee from structural to
empirical while making `ttm_source` a per-value rather than per-series property.

**A correction to the gate's own safety argument, found while checking this.** The annual-gate
entry claims masks "can only break a window, never create one". That is not true: removing a
row widens a step, and a widened step can move *into* the valid band from below -- rows at days
0, 45, 91, 182, 273 form no TTM window, and removing the day-45 row produces one. The
conclusion still holds over all 501 tickers (0 cases), but by measurement rather than by that
argument.

**Diff, all 501 tickers from one price capture: 107 snapshot values appeared, 112 disappeared,
and nothing else in the project moved.** Base facts, facts, `metrics_long`,
`valuation_history` and all seven `avg_*_5y` lines are identical from before to after -- the
first task in the running series with a mean-line effect of exactly 0.000%. Anchors 18,877 with
0 moved and 0 changed; quality flags 734 -> 734; peer bands 2,106 with 0 flipped.

---

## 2026-08-16 — The annual-path gate: event-driven concepts falling between two paths

The FFO task diagnosed this and left it standing because it changes behaviour all 25 `TTM_CONCEPTS`
share. Full derivation in `annual_path_gate_report.md`.

**The gate asked the wrong question.** `annual_ttm_values` ran only `if not quarterly_values` --
whether any quarterly fact exists -- rather than whether the quarterly path can produce anything. For
a concept reported **on occurrence** rather than every period, a handful of scattered facts that can
never form a four-consecutive-quarter window disabled the annual facts that could have produced
values. It now gates on the quarterly path's **output**: run when the rolling path yields no TTM
value for that series at all.

**Classification over 501 tickers x 25 concepts, 6,035 pairs with data:**

```
class 1  rolling works, annual adds no new date         105 pairs   66 tickers
class 2  quarterly facts exist, no TTM produced          77 pairs   57 tickers   343 annual facts  <- the defect
class 3  no quarterly facts, annual path already runs     64 pairs   60 tickers
class 4  rolling works partly, annual could fill       5,789 pairs  500 tickers
```

Class 2 sits exactly where the mechanism predicts: `StockRepurchased` 17, `StockIssued` 16,
`DividendsPerShare` 14, `ShareBasedCompensation` 8. **BDX has 55 quarterly `DividendsPerShare` values
and no TTM value at all** -- a dividend is declared when the board declares one -- with 16 annual
facts discarded; CAH 53 and 18; EXPD 28 and 19.

**Class 4 was the decision, and locating its dates settled it against per-date gating.** Of its
14,137 annual facts at dates the rolling path never reaches, **81.1% precede its first value** --
annual-only XBRL history from before quarterly tagging -- only **11.0% are interior holes**, and
8.0% follow its last. Meanwhile **81,505 annual facts land on dates the rolling path already holds**.
Gating per date would prepend a decade of annual points to otherwise-quarterly series and turn a
structural guarantee into a tie-break exercised 81,505 times.

**The guarantee is load-bearing, verified rather than assumed.** The two paths are *concatenated*,
not merged: a constructed collision returns two rows at one `(ticker, concept, end)` -- one
`annual_fact`, one `quarterly_rolling` -- which `pivot_table` would silently average into a number
neither path computed. So relaxing the gate without a collision rule would corrupt facts, and the
per-series form keeps disjointness structural: a series is wholly rolling-derived or wholly
annual-derived, and `ttm_source` stays a per-series constant.

**One deliberate imprecision, safe in one direction only.** The gate is evaluated on the pre-mask
quarterly values, since that is where `annual_ttm_values` is called, while `calculate_ttm` later sees
them after `_mask_negative_flow_values` and its siblings. Those masks only remove rows, which can only
widen steps and so only *break* a window, never create one -- a window absent at the gate cannot
appear later, so both paths can never reach the same date. The reverse costs a recovery, not a
collision.

---

## 2026-08-15 — FFO's gains term: the tag list, and why the three "extraction failures" were not

The alignment task left `FFO_TTM` zero-filling its gains term for 77% of REIT periods and named the
tag list as the real fix. This is that work. Full derivation in `ffo_gains_report.md`.

**Part A's premise was wrong, and the diagnosis is worth keeping.** CPT, IRM and MAA were recorded as
having a queried tag present that "still yields no `_TTM` value". Extraction is fine — CPT gets 5
quarterly values, IRM 3, MAA 4. **The value is lost at `calculate_ttm`, correctly**: their quarterly
ends are 90/275/182/92 days apart (CPT), 457/92 (IRM), 91/92/1278 (MAA), so no four-consecutive-quarter
window exists. `GainLossOnSaleOfProperties` is **event-driven, not periodic** — a REIT tags a gain in
the quarters it sells something — so a TTM window is available only to filers who happen to sell four
quarters running.

**And the annual fallback is switched off by the very values that are too sparse to use.**
`annual_ttm_values` returns `[]` as soon as the quarterly path produced anything; CPT has **13 FY
facts** and five scattered quarterly ones, so it falls between the two paths. The TTM report's "disjoint
by construction" here produces a gap rather than an overlap. **Reported, not fixed** — widening that
gate is shared behaviour all 25 `TTM_CONCEPTS` depend on, and it would move every thin concept at once.
It needs its own diff. What actually rescues the three is the tag list: CPT 0 → 10 TTM values, MAA
0 → 26, IRM 0 → 5.

**The tag survey read all 29 REITs' raw facts, not a sample**: 19 disposal-gain tags exist, of which
2 were queried. Two corrections to the alignment report's starting list — **SPG's unqueried tag is a
single fact** (true that it is unqueried, useless that it is), and **`GainLossOnSaleOfPropertiesNetOfTax`,
already queried, appears in no REIT at all.**

**Eight tags added, `mode: fallback` kept, and the ordering carries the argument.** Fallback takes the
first tag reporting a period end and never sums, which is what keeps BXP's 75 pre-tax and 7
net-of-tax facts for one gain from being added together, and keeps `...PropertyPlantEquipment` — placed
last — from ever overriding a property-scoped value. Net-of-tax before pre-tax, because FFO starts
from net income. Sign convention checked on every tag: all gain-positive, 0.5–11% negative, matching
the two existing ones.

**The two largest candidates were rejected, and they were larger than everything accepted combined.**
`GainLossOnDispositionOfAssets` and `...Assets1` would have added **+145 TTM values of a possible
+350**. Where a filer reports both them and a property-scoped tag for the same period they disagree
35-to-11 and 20-to-12, and the disagreements are not small: **AVB's 2011 property gain is 294.8m
against 13.7m of "assets"; PLD's 2018 Q1 is 656.9m against 195.1m.** That some filers (CPT, KIM) use
`...Assets1` as a near-synonym makes it worse, not better — a tag meaning the property gain for one
filer and something else for another cannot be added globally. Also rejected: the
discontinued-operations family (23 REITs, 998 facts — the largest unqueried tag in the survey, and it
measures the disposal of a *business*: CCI's 77 entries are its fiber-segment sale), equity-method
disposals, disposal groups, and `...PropertiesApplicableIncomeTaxes`, which is the tax and not the gain.

**Two one-off ticker overrides were folded in.** FRT and ARE each carried a `GainLossOnSaleOfProperties`
override adding a single tag the profile list now has. A ticker override *replaces* the profile entry,
so leaving them would have pinned those two filers to the old, narrower list.

**Class B/C, confirmed from raw facts — a permanent record so the next investigation does not redo it:**

- **VICI — class C.** No gain/loss-on-disposal tag of any kind. 2017 spin-off, triple-net leased.
- **CCI — class B.** 77 facts, all discontinued-operations: the fiber/small-cell business sale, not
  depreciable real property.
- **AMT — class B.** Three facts of `GainLossOnDispositionOfOtherAssets`, named as not-property.
- **SBAC — class B in effect.** Four PP&E facts and eleven `...Assets1`; yields one quarterly value.
- **SPG — class B in effect.** One unqueried fact.

**`ffo_gains_source` keeps its two labels.** A third for "confirmed genuine absence" was rejected
because the label is computed per row at runtime while class B/C is a per-ticker judgement from
reading raw facts — the pipeline cannot re-derive it and could never notice it going stale. The
evidence belongs in this entry instead, which is where it now is.

---

## 2026-08-14 — Cross-concept row alignment, and the two remaining silent defaults

Four independent change groups, diffed separately, all computed from **one price capture** (the
product-cleanup task established `get_price_history` is not bit-reproducible across calls). Full
derivation in `alignment_and_defaults_report.md`.

**A — a pivot row is not a quarter, and now it is.** `build_valuation_history` joined fourteen
concepts on an exact end date, so a filer that ends one concept's period a few days from another's
got the quarter twice, each row half empty and priced at its own close — **193 pairs across 102
tickers**, `StockholdersEquity` (70) and `CashAndEquivalents` (64) leading, but `Revenue_TTM` the
straggler in 32, so a two-concept fix would have missed a third of it. Different population from the
one `merge_duplicate_period_ends` handles: those are twins *within* a concept, these are one quarter
split *across* concepts, which a per-concept pass cannot see.

**No empty run here either** — the gaps decay 124/22/16/11/9/9/2 from one day to seven with a
one-day hole at 8 — so the duplicate-ends bound is reused rather than a second one invented: seven
days, because a fiscal end is the chosen weekday nearest the month end. What measurement *could*
settle it did: clustering at 7 days yields **193 clusters of exactly two dates, none spanning more
than 7, zero chains**.

**Two measurements decided the open questions rather than judgement.** 0 of the 193 pairs share a
concept, so the merge is lossless by construction — 1,423 values read back out of merged rows, 0
mismatches. And **no ticker has its newest pivot row inside a cluster**, which silences the anchor
argument that decided the duplicate-ends task and leaves the canonical date to be chosen on where the
quarter is: **majority, ties to the later**. "Later always" would have relabelled 142 of 193 quarters
by the position of a single balance-sheet item.

**Fixed in the pivot, not the parser** — the facts frame keeps every date as filed, because CAT
really did tag `StockholdersEquity` at 2017-01-01. Honest caveat: the split is not purely a pivot
artefact (228 such pairs exist across all concepts, 193 of them visible in the pivot), so the "it is
only a join artefact" argument is weaker than it looks; what makes the pivot the right place is that
in the facts frame both rows are *correct*.

**Result: pivot rows 33,913 → 33,720 (exactly −193), 0 fact values changed, 0 multiples changed,
anchor 0/0/0, every quality flag unchanged** — and **232 multiples appear** that the split had made
incomputable (`ev_sales` 99, `ev_fcf` 59, `pb_ratio` 58, `ev_ebitda` 49). Three keys had to be
snapped together, not one: the first run **lost 53 `buyback_distortion_flag` values** because that
merge is keyed on the facts frame's dates, caught by the diff.

**B — the line the brief pointed at was a no-op.** `& scale_reference.notna()` does nothing:
`5.0 < NaN` is already False, so a missing reference already passed. Verified byte-identical output
with and without it. The measurement then inverted the expected trade-off: ~6,700 values reach a
guarded metric with no reference, and they are **tamer than the guarded population** (median
`pe_ratio` 17.2 against 18.7, max 1,783 against 25,466), so "treat as failing" would have deleted the
better-behaved half.

**So neither blank nor pass: fill the reference.** Every missing reference is a *per-period hole* —
all 501 tickers report `Revenue_TTM` somewhere — and a scale guard asks an order-of-magnitude
question a neighbouring period answers. `fill_scale_reference` carries it forward then backward; the
guard then evaluates and **blanks 27 of ~6,700 (0.4%)**, every one an extreme: VLO's 1,093% effective
tax rate (the species the TTM report traced), ATO's 8,199% ROE and 812 P/B, MRSH's 3,098% ROTCE,
VLO's 1,193 P/FCF-ex-SBC. Nothing changed value; only guarded metrics moved.

**C — confirmed not resolvable, and the raw facts make it worse than unresolvable.** The gains term
is present in only **427 of ~1,836** REIT FFO periods, so 77% of REIT FFO rests on the zero-fill. Of
those 427, **only 10 are zero** — a filer with no disposals omits the tag rather than tagging zero —
and the gaps track XBRL tagging practice, not disposal activity (ARE tags from 2013, EQR from 2014,
O from 2017; all sold property before that). Of the twelve REITs that never produce the term, **ten
use a `us-gaap` disposal-gain tag the pipeline does not query** (SPG `…BeforeApplicableIncomeTaxes`,
HST, VTR, WY, AMT, EQIX, SBAC) and three (CPT, IRM, MAA) have a queried tag present that still yields
nothing; only CCI and VICI have no such tag at all. Where measurable the term moves FFO by a median
**13.5%**.

**Blanking would delete 77% of REIT FFO and `p_ffo` for twelve REITs over a tag list this task
excludes**, so the value stands and the assumption is labelled — `ffo_gains_source`
(`reported` / `imputed_zero`), the same instrument as `ttm_source`. **0 values changed**; the facts
frame gains a column. The check against the REITs' own published FFO is unavailable: FFO lives in a
company extension namespace the SEC `companyfacts` API does not return (verified across 15 REITs).
The real fix, with its evidence, is recorded for the tag task.

**D.1 was not a judgement about REIT economics.** `is_hidden` already resolves `eps_ttm`, `pe_ttm`,
`EPS_TTM_CALC` and all five `avg_pe_5y` fields to hidden for REITs through
`_DERIVED_CONCEPT_CONSUMERS`; `pe_to_revenue_growth` was the single missing entry, so the profile
published a PEG whose numerator it had ruled out. `reit` is the only profile hiding `pe_ratio`, so
the one-line entry cannot reach elsewhere. **D.2**: `calculate_rolling_average` had zero call sites
and still carried the row-count window the rolling-window task replaced — removed.

---

## 2026-08-13 — Product-side cleanup: `ttm_source` rendering, `write_charts`, `p_ffo` snapshot

Three independent product items, no parse-layer change. Full detail in `product_cleanup_report.md`.

**`ttm_source` now renders, marked per column rather than per cell — because provenance does not
vary within a column.** 5,836 `(ticker, concept)` series carry a `ttm_source` and **0 carry both
labels**, which follows from `calculate_ttm` and `annual_ttm_values` being disjoint by construction.
So a one-character header marker (`ᵃ`) plus a legend naming the concepts in full, rather than a
per-cell suffix that would cost readability in every row of an already 37-column table. The mixed
case is still computed rather than assumed away, and flips the marker to `ᵐ` when injected. Derived
TTMs (`FCF_TTM`, `EBITDA_TTM`, `FFO_TTM`, `EPS_TTM_CALC`) stay unmarked — their `ttm_source` set is
empty and inventing a marker would assert something the pipeline never established.

**The brief's verification ticker does not work, and that is the finding.** NEE
`ShareBasedCompensation_TTM` has 18 annual values in the pipeline and **zero** in
`facts_full.parquet`: the TTM report counted on the unfiltered frame, the export is written after
`filter_hidden_rows`, and the `utilities` profile hides the concept. DAL/COP/OXY (18 each), MCD
`PretaxIncome_TTM` (18) and L `DepreciationAndAmortization_TTM` (19) are the working substitutes.

**`write_charts` replaces a commented-out `write_html` call, with defaults split by entry point:**
`run_full_refresh(write_charts=False)` because the app renders from `data/app/*.parquet` and never
opens a chart file, `main(write_charts=True)` because looking at output is why that entry point
exists. HTML and JSON get **different** switches, not one: measured, JSON is 16–53 KB per chart and
HTML 4.87–4.91 MB — **155×**, ~7.4 GB across a full run. The run report now prints
"Plot: **skipped**" instead of a 0.0s total that would read as "plotting was free".

**Byte-identical exports needed the flag isolated, and the reason is worth recording: the pipeline
is not bit-reproducible across runs.** Two full runs differed on `current_snapshot` and
`valuation_history` (861 of 1,697 rows, all at the last ulp) — because two consecutive
`get_price_history("AAPL")` calls return closes differing by up to **9.155e-05**. With one fetch and
one calculation, all six exports are byte-identical with and without plotting, and the plot loop
provably does not mutate any frame it reads.

**`p_ffo` is now in `build_snapshot`, and nothing had been missing.** Re-measured against the current
registry: 10 of 13 valuation panels had a snapshot counterpart, the three without still exactly
`ev_fcf`, `pfcf_ex_sbc`, `p_ffo`. `FFO_TTM` is added by `add_derived_concepts` long before
`build_snapshot` and is present for **29 of 29 REITs** — it was simply never added. All three
implemented, mirroring `build_valuation_history`'s expressions including the scale guard, so the
marker and the line are the same quantity: **13 of 13**. Hand-checked: AMT 16.1842 and O 16.3412 from
price × shares ÷ `FFO_TTM`, exact. ARE (negative FFO) and AVB (trailing NaN rows) correctly get no
marker.

**Left standing:** `get_latest_value` returns the newest *row* even when its value is NaN (AVB's
case, general to every snapshot input); the snapshot guards `pb_ratio`/`p_tbv` at 0.01 while the
history guards them at 0.001, so for those two the marker and the line are not strictly the same
quantity; `app.py` reaches `metrics` through `figures.py:13`, so "imports no pipeline module" is not
literally true; 24 stale `.html` and 995 stale `.png` files in `figures/`; and `MDs/figures.md` still
describes a matplotlib/PNG implementation that no longer exists.

---

## 2026-08-12 — Row-based windows, one layer up: the five-year means and the growth comparison

The TTM task established that a window counted in rows rather than calendar time yields a number
that is not what its name says, and fixed `calculate_ttm`. Two places still carried it, both
feeding what the app puts in front of a user as its central claim. Fixed as two separate change
groups with a diff after each. Full derivation in `rolling_window_report.md`.

**The five-year mean was a mean over 1,735 days only when nothing was wrong.** Twenty consecutive
quarters span nineteen quarter-steps — 1,734.9 days between the outer end dates, stated from the
arithmetic before measuring and confirmed by the mode (1,734/1,735/1,736 = 72.9% of windows). Over
the 23,734 windows the valuation history forms, **12.3% reached back more than five years — EXE to
11.25 — and 8.8% covered less than 4.65. 21% were not five-year windows.**

**There is no empty run here either, and this time it decides the rule rather than merely being
reported.** Between 1,600 and 2,600 days the distribution is a continuum with forty-five holes of
3–29 days; nothing brackets the legitimate region, because a five-year window is broken by whatever
gaps a ten-year history happens to contain and those come in every size. So the fix defines the
window directly — `AVG_5Y_WINDOW = "1826D"`, every observation in `(end − 1826 days, end]` — rather
than masking a row window against a threshold that could not have been derived.

**The short windows were the surprise, and they have their own cause: a pivot row is not a quarter.**
`build_valuation_history` creates a row wherever any of the fourteen needed concepts reported, and a
filer can end one concept's period a day from another's — CAT tags `StockholdersEquity` at
2017-01-01 and nine other concepts at 2016-12-31; WAT splits 2025-06-28 and 2025-06-30. **193 such
rows across 102 tickers.** This is a different population from the duplicated period ends fixed
yesterday — those were within a concept, these are across concepts — and it made Waters' twenty-row
window cover 1,095 days, three years sold as five.

**`min_periods=1` and `MIN_AVG_5Y_OBSERVATIONS = 12` are unchanged, deliberately.** A five-year
window with a gap in it is still five years; `_n` reports what was available and
`avg_*_5y_history_too_short` already means "not enough history". Adding a hard cut-off would have
been a second, parallel notion of the same thing.

**Part 1 moved 11–15% of the points on six of the seven mean lines** (`avg_p_ppnr_5y` 15.5%,
`avg_pe_5y` 12.2%, `avg_p_tbv_5y` 12.0%, `avg_p_ffo_5y` 11.8%, `avg_pfcf_5y` 11.2%,
`avg_ev_ebitda_5y` 11.1%; `avg_p_core_earnings_5y` 2.9%, 15 insurers with unbroken histories) —
between the TTM task's ~25% and the duplicate-ends task's 2–5%. **And nothing else moved at all:
0 base facts, 0 facts, 0 metrics_long, 0 single-period multiples, 0 anchor moves.** HBAN's
`avg_pe_5y` at 2018-03-31 goes 7.68 → 8.36 by dropping four quarters of 2012; WAT's at 2021-12-31
goes 26.93 → 33.21 by gaining eight it should always have had.

**TSLA resolves to 70.73.** The duplicate-ends task moved it 68.67 → 70.73 with no TSLA value
changing; the correct calendar window produces 70.7318, so that move was the correction. TSLA does
not move in this diff — the point is that it can no longer move for that reason.

**Part 2: `Revenue_TTM.pct_change(periods=4)` had two defects and was also a second implementation.**
It counted rows — 787 growth values on 130 tickers had a base that was not four quarters old, and
almost all of them were too *recent* (673 at three quarters), the extra-row population again — and
pandas' `fill_method="ffill"` default bridged a missing base on 845 values across 157 tickers.
`metrics["revenue_growth"]` has done this by date since 2026-07-27, so the Revenue growth panel and
the snapshot's PEG were already correct and only the history's copy was not. Replaced with a call to
`calculate_growth`, reusing its ±45-day tolerance (which bounds the lag between two observation
dates, 365.2 days — *not* the TTM window's 273.9-day span between the outer rows of a four-row
window).

**Part 2 touched exactly one concept:** `pe_to_revenue_growth`, 23 appeared / 232 changed / 179
disappeared over 122 tickers, one ticker (VTRS) losing it entirely; 0 changes everywhere else,
including `metrics_long` — the confirmation that the panel was already right. The growth delta and
the PEG delta are far apart (742 vs 179) because growth only reaches PEG where a `pe_ratio` exists
and the figure clears the 2% floor; **359 values crossed that floor downward, 28 upward.**
CIEN 2020-05-02 is the clean case: four rows back was 184 days — two quarters — so a 2.3% half-year
change was published as annual growth; by date the base is 364 days back and the figure is 17.6%,
moving PEG 9.59 → 1.27.

**Verified against an implementation sharing no code:** a naive per-ticker loop recomputed the
harmonic mean, median and count for **all 232,365 rows with 0 mismatches**, which also discharges
the positional-alignment assumption `groupby(...).rolling(on=...)` forces. The two PEG series now
reconcile exactly — rebuilding the history's PEG from the panel's growth gave 229 disagreements
before and **0** after. The `FutureWarning` the pipeline emitted was measured with the same
instrument before (1) and after (0). Coverage flags 737 → 737, `share_count_jump_flag` 718 → 718,
`buyback_distortion_flag` 635 → 635.

**Left standing, and now the only place this defect can surface: the 193 cross-concept extra rows
themselves.** Both consumers count days now, so neither is affected, but a ticker still gets two
`pe_ratio` points a day apart for one quarter, priced at two different closes. That needs a
cross-concept end alignment in the parser and its own diff.

---

## 2026-08-11 — One quarter, two calendars, two rows: the duplicated period ends

`extract_period_values` keys on `(end, days)` and `decumulate_period_values` on `end`, so a filer
that tags one reporting period twice — once on its fiscal end, once on the calendar end — got two
rows. The same quarter appeared twice in the data tab, and `calculate_ttm`'s step rule correctly
refused every window that stepped across the pair. Full derivation in
`duplicate_period_ends_report.md`.

**There is no empty run this time, and that is the finding.** The gap distribution over 503,581
consecutive period pairs is a continuum — 1 day (334), 2 (136), 3 (114), then a scatter — with a
second population at **28–31 days (240 pairs)** that is a month apart and genuinely different
dates. The only empty runs between 1 and 120 days are 67–68 and 99–109. So unlike the TTM and
decumulation windows, the bound had to be argued from the mechanism: **a 52/53-week period end is
the chosen weekday nearest the month end and can sit at most six days from it, so seven days.** The
data agrees — 435 of the 461 value-identical pairs are at a gap of ≤ 7 and the next is at 9.

**Value agreement is the wrong test, in both directions.** It admits mergers and spin-offs (VTRS
0 → 2,619m, JCI 0 of 46 pairs identical) and it rejects real duplicates, because the twins' values
*should* differ by the calendar offset: Motorola's 2010 Q2 is 1,936m ending 2010-06-30 and 1,869m
ending 2010-07-03 — **3.5% apart, which is exactly three days out of ninety**. Structural signals
fail too: "same start" catches 139 of 400 duplicates with 32 false positives, and 197 duplicates
have neither the same start nor an aligned shift, because both ends move under the two calendars.

**The rule: ends within 7 days are one period, the later one survives.** The step-ladder test is
neutral — 419 of 452 windows are quarter-length either way — so the deciding argument is the anchor
invariant: keeping the later end can only leave a series' newest period where it is or move it
forward, never back.

**The fix lives in `build_dataframe` after `extract_with_mode`, not in the `(end, days)` key.**
Changing the key does not work, for a measurable reason: **decumulation regenerates the twin.**
Waters tags the same quarter as `2024-03-31 → 2024-06-29` and `2024-04-01 → 2024-06-30`; different
starts put them in different year-to-date groups and each emits a quarter at its own end. Placing
the pass after the tag merge also catches twins contributed by different tags, and leaves the key's
shorter-duration-wins preference — load-bearing for point-in-time concepts, per the decumulation
report's COST case — untouched and verified unchanged.

**721 rows removed, 0 added, and not one fact value changed.** The population is wider than the TTM
report's narrower measurement suggested: **136 tickers, not 33**, split almost evenly between
duration concepts (234 pairs) and point-in-time ones (190) — `CashAndEquivalents` 110 rows,
`StockholdersEquity` 94, `Revenue` 84, `SharesOutstanding` 76. Every removed row has a surviving
partner within 7 days; 433 carried an identical value, and the largest disagreements are
pre-combination placeholders the merge deletes (VTRS 0 → 2,948m, ROP 138.8m → 13,476m).

Downstream: **1,091 `_TTM` values appear** — the recovered windows, WAT 244, CIEN 114, TER 78,
DE 78 — and 1,222 rows disappear, accounting exactly as 720 base rows plus 502 derived ones. All
90 changed values in metrics and valuation history are **row-position-dependent quantities**
(`pct_change` over rows and the flags built on it); nothing computed from a single period moved.
Quarter pairs ≤ 7 days apart go **740 → 0**.

**Two anchor exceptions, both named.** Eleven newest dates move *forward* — Waters' whole trailing
block gains three quarters of reach, from 2025-06-28 to 2026-04-04. Two move backwards: Johnson
Controls' `EBITDA_QUARTERLY` and `EBITDA_TTM`, because JCI tagged both calendars for D&A but not
for operating income during the Tyco transition, so keeping the later end put the two on different
calendars and the join broke. No value was lost; 2 of ~33,000 pairs.

**Rolling five-year means moved 2–5% of points per line**, and the mechanism is worth naming:
`calculate_rolling_harmonic_stats` uses a **20-row** window, not 20 calendar quarters — the same
row-versus-calendar weakness the TTM task fixed in `calculate_ttm`, still standing here. TSLA lost
exactly one row and no values, and its `avg_p_ffo_5y` still moved 68.67 → 70.73 because the window
gained an observation. Recorded, not fixed.

**Corroborated against the filers' own annual facts** — a separate filing, not built from the four
quarters: of 28 recovered `Revenue_TTM` values landing on a fiscal year end, **22 are within 0.1%
and 16 exact to the dollar**. The three misses are the Motorola Mobility separation (annual fact
restated to continuing operations) and a Ciena 53-week year.

Flags: `share_count_jump_flag` 734 → 718 (the 16 that go were created by a twin's share-count
offset reading as a jump), coverage flags 741 → 737.

---

## 2026-08-10 — Kroger's Q1 is 16 weeks, and the decumulator threw it away every year

`decumulate_period_values` accepted a derived quarter only when the year-to-date difference fell
in **80–100 days**. That window encodes a 13-week calendar. The previous task's calendar-aware TTM
window then refused to sum across the resulting holes, and Kroger — an S&P 500 constituent — went
to **zero valuation multiples**: no P/E, no EV/EBITDA, no P/FCF, nothing. Full derivation in
`decumulation_window_report.md`.

**Measured first, over all 622,845 differences the function forms across 501 tickers:**

```
  ≤0            0     1–20        223   duplicated period ends
  80–100  604,683     101–105       0   empty
  106–120   1,588     121–160     129   merger / spin-off / IPO / fiscal-year stubs
  161–200   9,307     201+      6,801   two and three quarters
```

The clusters, checked against the filers rather than assumed: **83–84** the 12-week quarter,
**89–92** the calendar quarter, **97–98** the 14-week quarter of a 53-week year, **111–112** the
16-week quarter, **118–119** the 17-week quarter of a 53-week year.

**The 16-week quarter sits in two different places, and only one was being rescued.** For PEP,
AZO, COST, DPZ and YUM it is Q4, whose 112-day difference was rejected — but the value survived
via the `annual − (Q1+Q2+Q3)` fallback. For Kroger it is **Q1**, and there is no fallback for Q1.

**Length alone cannot draw the line.** A 17-week quarter is 119 days; a four-month transition stub
(CTVA after the DowDuPont split, PSKY after the merger, MOS at its fiscal-year change) is 121. The
gap at 120 is one day wide — luck, not evidence. What separates them is **repetition**: counted
per (ticker, concept), the eight 52/53-week filers produce 15–29 such periods and every stub
produces exactly one. So the rule is a length band plus a recurrence test for the ambiguous part
of it:

```python
_QUARTER_MIN_DAYS = 80
_QUARTER_MAX_DAYS = 100          # accepted unconditionally, as before
_LONG_QUARTER_MAX_DAYS = 120     # 17 weeks plus a day
_MIN_LONG_QUARTER_PERIODS = 3    # a long quarter must be part of the filer's calendar
```

The same 80–100 assumption sat in `extract_period_values`' point-in-time branch and is now the
same constant — a weighted-average share count carries the duration it averages, so Kroger's Q1
share counts were rejected there too.

**Kroger, before → after:** Revenue quarters 48 → 71, OperatingCashFlow 35 → 70, `Revenue_TTM`
**0 → 66**, `pe_ratio` **0 → 63**, `ev_ebitda` **0 → 66**. Its quarters now tile the fiscal year
exactly — 112 + 84 + 84 + 84 = 364 days — and sum to $147.1bn against ~$147bn of annual sales.

**Diff across all 501 tickers: 1,492 facts appeared, 532 changed, 0 disappeared.** Every appeared
value is Kroger's, plus JBHT's 2013 Q4 dividend; **no ticker outside the eight 52/53-week filers
changed a single value**; 364 of the 532 changes are rounding, because the direct year-to-date
difference now replaces a three-term subtraction of independently rounded figures. The material
ones are Q4 corrections that were plainly wrong before: YUM's 2015 Q4 operating income
**−78m → 441m**, Domino's 2012 Q4 repurchase **−40.2m → +35.8m**, Domino's 2023 Q4 SBC
**24.1m → 7.1m**. Kroger's 2025 Q4 repurchase **5,038m → 4,031m** looks like a regression and is
the opposite: 5,038m was the *whole year's* treasury purchases tagged into one quarter under a
fallback tag, and the recovered ladder puts the cash-flow tag back in charge.

One value disappeared — HST's `pe_to_revenue_growth` at 2013-12-31, whose revenue growth fell from
2.10% to 1.67% and crossed `MIN_PEG_REVENUE_GROWTH`. The anchor invariant holds with one named
exception: Kroger's newest period moved *forward* to 2026-05-23, because its most recent quarter
was one of the missing ones.

**Corroborated against facts the recovery never touched:** each recovered Kroger Q1 compared with
`FY − (Q2+Q3+Q4)` built from discrete quarterly facts — **95 of 121 exact to the cent**, 97 within
0.1%. The residuals are the 53-week fiscal year and 10-Q-to-10-K restatements.

Rolling five-year means moved 0.2–0.6% of points per line (`avg_p_ffo_5y` 163 of 27,781), against
roughly a quarter of them in the TTM task. Coverage flags 743 → 741: KR/Capex and
KR/OperatingCashFlow cleared. Kroger's other concepts were never flagged — 48 of 74 quarters is
65%, comfortably above the threshold, which is exactly why nothing announced that a fifth of its
history was missing.

**Not fixed, recorded:** the 300 quarter pairs less than 11 days apart (33 tickers tag the same
period twice; neutral here, 300 before and after, but the fix belongs in `extract_period_values`'
`(end, days)` key); 11 long quarters on thin HST and MAR concepts that the per-concept recurrence
gate cannot distinguish from a stub; and the 121–160 day transition stubs, which are rejected
rather than represented.

---

## 2026-08-09 — "Trailing twelve months" now has to be twelve months, and annual-only filers finally have one

`calculate_ttm` was `.rolling(window=4).sum()` over the rows present in a series. Four rows are
four quarters only if the series has no hole; on a thin concept they can span years. The result
was labelled TTM, raised no error, and fed every valuation denominator. Full derivation in
`ttm_window_report.md`.

**The threshold came out of the data, not out of a round number.** Measuring the span
(`end[i] − end[i−3]`) of all **333,737** windows across 501 tickers and 24 concepts gives a dense
core at 273–275 (91.9%), shoulders at 280 and 287 for 52/53-week filers, a tail to 304 for
fiscal-year-end changes — and then **nothing at all between 305 and 362**, before the 365 cluster
where a quarter has been skipped. Both bounds are the midpoint of an empty run:

```
_TTM_WINDOW_MIN_DAYS = 248   # empty run 246..250
_TTM_WINDOW_MAX_DAYS = 333   # empty run 305..362
_TTM_STEP_MIN_DAYS   = 76    # empty run 73..80    (step between adjacent rows)
_TTM_STEP_MAX_DAYS   = 137   # empty run 122..152
```

The step rule exists because a window can have the right total length while double-counting one
quarter and skipping another — DHR 2009-07-03 has steps 189/88/**3** and a span of 280. The span
band alone would keep all 51 of those.

**4.38% of windows fail (14,615), removing 19,094 facts values** — 14,615 base plus 4,479 derived,
which adds up exactly. 495 of 501 tickers lose something; six lose nothing. **Kroger loses all
501**, correctly: its Q1 is 16 weeks, `decumulate_period_values` only emits a quarter for an 80–100
day year-to-date difference, so KR's Q1 is discarded every single year and every "TTM" it had
covered fifteen months. 486 of 501 tickers have at least one 180–200 day step.

**Part 2 reads what was always there.** A 12-month fact at a fiscal year end *is* the TTM value at
that date. `parse_edgar.annual_ttm_values` takes it directly — but only for a `(ticker, concept)`
whose quarterly extraction produced **nothing at all**. That is the boundary against
`decumulate_period_values`, and it makes the two paths disjoint by construction: a pair with no
quarterly rows contributes nothing for the rolling window to roll over, so neither path can reach
a date the other writes. Confirmed: **0 duplicates on `(ticker, concept, end)`, 0 series carrying
both provenance labels.** Measured target set: **64 pairs, 60 tickers, 658 annual values**; NEE
goes from 0 to 18 `ShareBasedCompensation_TTM` points. Part 2's diff is **778 appeared, 0 changed,
0 disappeared** in facts and the same shape in metrics and valuation history.

The rule is written on the extractor's output, not on raw fact durations — six pairs (ADM, C, EXC,
KHC, OTIS, TKO) have half-year and nine-month facts but still nothing decumulable, and a
duration-based rule would have excluded them wrongly.

**Provenance travels with the value:** a `ttm_source` column, `quarterly_rolling` (319,122) or
`annual_fact` (658), `None` where a masked window left no number. Decision: it *should* surface in
the app's data tab; not implemented here because the task excluded UI work, but the column already
reaches `facts_full.parquet`, so that is a rendering change only.

**Downstream, this is the largest move any of these tasks has produced.** Roughly a quarter of the
historical five-year mean lines shift — `avg_p_ffo_5y` 7,859 of 28,347, `avg_pfcf_5y` 6,477,
`avg_pe_5y` 5,859, `avg_ev_ebitda_5y` 4,925 — because they were averaging multiples whose
denominators were not twelve-month figures. `avg_p_tbv_5y` moves 85 of 24,418, which is the
control: tangible book value has no TTM denominator. Flags: `low_tax_rate_flag` 4,196 → 4,060,
`fcf_exceeds_ebitda` 1,984 → 1,821, `buyback_distortion_flag` 644 → 633, coverage flags unchanged
at 743.

**Three pre-existing defects that the diff exposed and this task did not fix**, all recorded in the
report: `apply_denominator_scale_guard` treats a *missing* scale reference as "large enough" (four
metric values reappeared, one a 274% effective tax rate); `pct_change(periods=4)` on `Revenue_TTM`
uses pandas' `ffill` default, so a hole is silently bridged; and `ffo["gains"].fillna(0)` reads a
missing gains term as a zero gain — all 94 changed facts values run through it.

**Coverage flags do not move, and that is the finding.** `check_data_quality` counts base-concept
rows before the TTM layer, so 60 of the 64 annual-only pairs keep a `MISSING 0 of 75` flag while
the pipeline now reads every value the filer publishes. A quarterly coverage ratio does not mean
what the threshold assumes for an annual-cadence disclosure. Logic unchanged, per the task.

---

## 2026-08-08 — Directional scale detection: a P/B of 3,377 removed, and the cross-concept scope answered with a measurement

The scale audit left two gaps: the sweep is upward-only, and its evidence is symmetric. Both are
closed. Detail in `directional_scale_detection_report.md`.

**Scope verdict: this is a `SharesOutstanding` problem, and the data says so rather than the five
known cases.** The within-accession cross-tag test finds 4,501 power-of-ten disagreements across
18 concepts, and almost none are scale errors — they are `LongTermDebtCurrent` against
`LongTermDebt`, `AmortizationOfIntangibleAssets` against `DepreciationDepletionAndAmortization`:
components against totals that happen to sit ~10x apart. The **discriminator is measurable**: a
scale error is the same number re-typed, so its ratio's deviation from the exact power of ten is
only the two tags' real difference. `SharesOutstanding` has a median deviation of **0.0026**;
every other concept sits at 0.012–0.018, uniform noise. It is also the only concept in the
registry whose candidate tags are synonyms, which is why it is the only one where the test can
speak at all.

**A first pass keyed cells on `(accn, start, end)` and missed Sherwin-Williams entirely** —
`CommonStockSharesOutstanding` is an instant fact, the weighted-average tags are durations, so
the two never met. Re-keyed on `(accn, end)`: 244 cells on 68 tickers, every one exactly 10^3 or
10^6.

**The symmetric EPS test made directional**, by comparing each of net income, shares and EPS
against its *own* series' magnitude. Of 40 surviving inconsistencies: **6 share count, 1 net
income (CTVA), 2 whole-filing scalings (ATO, LUV), 31 neither** — confirming the audit's read of
HAL/HIG/CTVA/TMO, whose share counts are correct. Three of the six are already fixed by the
upward sweep, leaving exactly the five named periods. The test rediscovers them and finds nothing
else.

**"Use the sibling tag directly" was implemented first and was wrong.** SHW's accession carries
`CommonStockSharesOutstanding = 122,814,241` next to a mis-scaled
`WeightedAverageNumberOfDilutedSharesOutstanding = 130,924,690,000` — but the sibling is the
*period-end* count, 6.2% below the diluted weighted average the series is built from and that the
filing's own EPS demands (615,578,000 / 4.70 = 130,974,043). Substituting it would drop a silent
measurement step into the middle of the history. **The rule takes only the exponent** and divides
in place, keeping the tag's own measure. Repaired value lands **0.04%** from what the filer's EPS
implies.

**Treatment differs by class.** Sibling establishes the exponent -> rescale in place (SHW x2).
No sibling but series and EPS both convict -> **drop the row** (AIG, ARE, TFC): 130,248,736,000,000
shares is not a better input than a gap. Suspected but unproven -> leave as filed; **no case
reached that branch**.

**Thresholds measured and left alone.** Across `_GATE_LOG_GAP` 1.0–2.5 and `_MATCH_TOLERANCE`
0.2–1.0, the accepted set moves **7 rows out of 32,061** (262–269) while the gate absorbs the
variation by rejecting 0–10. Not load-bearing once proposals are corroborated.

**This one reaches the charts, unlike the previous task.** 2 values changed and 3 dropped, and
downstream: **SHW's `pb_ratio` goes 3,376.87 -> 3.38 and `p_tbv` 7,641.69 -> 7.64**; TFC's
`pb_ratio` of 497.27 and ARE's of 848.17 disappear; TFC's `payout_ratio_quarterly` of 586.75
goes; `avg_p_tbv_5y` moves at 20 points, `avg_pe_5y` and `avg_p_ffo_5y` at 19 each.
`share_count_jump_flag` 744 -> 734 — the flag had been correctly firing on the discontinuities
these rows created. Anchor invariant holds for all 498 tickers, **0 values touched by both the
sweep and the repair**, and Agilent's 406 and the rest of the no-evidence class are untouched.

---

## 2026-08-07 (final) — `_normalize_scale_outliers` audited: 96% right, ten rows corrupting one ticker, and the opposite default from the split fix

The split task left this function as the last component choosing a numeric correction with
nothing independent to check against. Audited across all 501 tickers. Detail in
`scale_outlier_audit_report.md`.

**It runs on exactly one concept** (`_SCALE_CORRECTED_CONCEPTS = {"SharesOutstanding"}`) and on
**279 rows across 70 tickers** — not the 350/79 the split report quoted, because that figure
predates the ordering fix shipped in the same task; applying the split basis first removed 71
Chipotle rows the sweep used to "correct" by 100x when the real gap was a 50x split.

**It is upward-only by construction** (`if own_log > anchor_log: continue`), so Agilent's 406 is
in scope and **AIG's 130-trillion row never was**. The factor distribution is uninformative for
the same reason the split factors were — every factor is a power of ten because the candidate
list contains nothing else.

**One correction to how it was characterised:** it is *not* the same anchor-proximity idea as the
deleted split normaliser. That one compared every value to the newest value; this one re-anchors
on each accepted value, so it compares against running neighbours, runs forward and backward, and
requires agreement. It is a local outlier detector, and the audit result reflects that.

**Corroboration used two sources, both from inside the filings.** The companyfacts API carries no
`decimals` attribute and the unit key is `shares` either way, so the fact's own metadata is a dead
end — recorded so nobody tries again. What works: the same period restated at a power-of-ten
ratio, and `net income / shares = reported EPS` **keyed on `(accn, start, end)`**. Getting that
key wrong twice was instructive — matching by period across filings invented a 25x "error" on
NVDA that was really a 2009-basis EPS against a split-restated share count, and matching by
accession alone paired quarterly income with year-to-date EPS and smeared the implied error over
2.2–2.9 instead of landing on 3.0.

**Result: 253 corroborated, 10 contradicted, 16 no evidence — 96% right where testable.** All ten
contradicted rows are **EXE**: Chesapeake's 1:200 reverse split of December 2020 restated its
history to ~9.8m shares, which against a 1.4bn series looks like an outlier, and the sweep
multiplied ten quarters by 100. Same ticker the split task classified as no-evidence, because its
price history starts after the reverse split — one missing feed, two mechanisms misled.

**No-evidence default: keep rescaling — the opposite of the split task's, argued on numbers.**
The split normaliser was 17% right where testable, so its untested cases were probably wrong;
this one is 96% right, so suspending it would trade 15 correct corrections for 1. The asymmetry
points the same way: an uncorrected unit error is **loud** (Agilent at 406 shares implies a
$16,000 market cap), while a wrong split factor was quiet. **Drop-instead-of-correct was
considered and rejected with a reason worth keeping**: `NI/shares ≠ EPS` is symmetric and does not
say which number is wrong — 47 periods across 12 tickers show a ≥100x inconsistency after the
pipeline and most of them (HAL, HIG, CTVA, TMO) have correct share counts and a differently-scaled
net income. A rule built on it would delete more good data than bad.

**Effect, reported without inflation.** 10 `SharesOutstanding` values and 10 `EPS_TTM_CALC` values
change; **`metrics_long`, `valuation_history` and all five flag counts are unchanged**, because
EXE has no price history before 2021 so those quarters had no multiples to begin with. The
independent check is decisive though: EXE's FY2020 `EPS_TTM_CALC` goes **−9.96 → −996.01** against
Chesapeake's filed **−998.26**. Anchor invariant holds for all 498 tickers, 0 rows appeared or
disappeared.

**Carried forward with a concrete starting point:** five periods on AIG, SHW, TFC and ARE hold
share counts provably 1,000x+ too large and pass straight through, since the sweep cannot look
downward. Sherwin-Williams shows the detector that would catch them — **the same accession**
reports `WeightedAverageNumberOfDilutedSharesOutstanding = 130,924,690,000` and
`CommonStockSharesOutstanding = 122,814,241`. A within-accession disagreement names *which* tag is
wrong, which is exactly what dropping or correcting downward requires and what the EPS identity
cannot supply.

---

## 2026-08-07 (last) — Split normalisation was inventing splits: 7,357 of 8,893 rescalings were wrong, and every historical multiple with them

The tag investigation deferred two defects. Chased down, they are one failure: **the pipeline
inferred share-count events from the share-count series itself, with nothing independent to check
against.** Full detail in `split_normalisation_report.md`.

**`_normalize_series` was never split detection.** For each value independently it picked
whichever of `v`, `v*f`, `v/f` over a fixed factor list landed closest to the newest value —
history pulled toward today's anchor. Two internal tests, both available all along, falsify it
without any external source: only **178 of 929 rescaling events** have a raw step at the boundary
matching the factor applied (median step for the rest: **1.04**, a flat series), and the factor
sequence, which for a real split adjustment can only shrink toward the present, **increases at
730 steps across 307 tickers**.

**The factor distribution proves nothing, and that is the trap.** All 929 events carry textbook
split ratios (2, 3, 1/2, 10, ...) because the algorithm can produce nothing else. A plausible
ratio is evidence of the algorithm's vocabulary, not of a split.

**Corroboration needed two sources, not one.** yfinance **back-adjusts prices for splits
regardless of `auto_adjust`** — AAPL's 2020-08-28 close comes back as 124.81, which is 499.23/4 —
so there is no price step to find, in either direction. The `Stock Splits` column in the same
response is the usable feed (372 events, 231 tickers, zero extra requests), but it also carries
spin-off and stock-dividend ratios, and **the ratio's shape cannot separate them**: Agilent's
Keysight spin-off is 1.398 and a 7:5 split would be 1.400. The second source is the filers
themselves — the same period reported at two filing dates straddling a real split differs by
exactly the ratio, because the underlying count is identical. CMG 50.0000, NFLX 10.0000, GOOGL
19.9994; Agilent's only >1.2x restatements are 1,000,000x unit fixes, the spin-off leaving the
share count untouched. **145 of 372 feed events corroborate.**

**Reclassified: 7,357 rows contradicted (305 tickers), 1,406 corroborated, 130 no evidence.**
AAPL is the instructive case — two genuine splits, cumulative 28x, and the old code applied 15
then 3. Neither obviously broken nor right.

**No-evidence default: do not normalise** — 130 rows is 0.41% of all share-count rows, on 5
tickers (SATS, EXE, HWM, DELL, VICI), so the honest gap is cheap, and the alternative is more
guessing. The brief's third option, flag-instead-of-fix, was **rejected as redundant and then
verified**: 19 of the 20 pre-listing tickers now carry a `share_count_jump_flag` on their own.
VLTO is the exception because its pre-listing rows are flat — no jump to surface.

**Order matters and was the subtle part.** The fix lives in `parse_edgar._apply_split_basis` and
runs **before** `_normalize_scale_outliers`: which basis a number is on is a property of the
filing, a unit-scale error is a property of how it was typed. Reversed, the scale sweep absorbs
the split with the wrong factor — Chipotle's pre-split count is 50x low and the sweep, knowing
only powers of ten, "fixed" it by 100x. That needs the feed at parse time, so **the yfinance
phase now runs before the EDGAR phase**.

**`share_count_jump_flag` now prices in dollars, not book value.** Book value per share collapses
to cents when equity is near zero or negative, at which point any cash flow "corroborates" any
move. Fallback when no price exists: **none — the quarter stays flagged**, which costs 33 of 455
big-move quarters, all pre-listing, exactly where book value would have been least trustworthy.
The 0.5 threshold is kept: on a correct denominator, 0.25 through 1.5 moves 28 quarters out of
30,938, so it was never load-bearing.

**Blast radius, measured.** 7,765 share-count values changed on 312 tickers, 0 rows added or
lost, **the anchor invariant holds for all 498 tickers** and every change traces to a corroborated
ratio (0 unexplained). Downstream, **46,146 of 273,755 valuation-history rows (16.9%) changed**,
and a third to a half of every 5-year rolling mean moved by a median ~50% — the line the charts
draw as "the benchmark". Independent check: URI's 2013 market cap goes 4.0bn → **8.0bn** against
an actual ~7.5bn; AAPL's 219bn → **438bn** against ~500bn. `share_count_jump_flag` falls
**1,441 → 744**: 697 flagged quarters were the normaliser's own fabrications reported as data
problems. `buyback_distortion_flag` is unchanged at 644 and *cannot* move — it reads equity and
net income, never the share count.

---

## 2026-08-07 (later) — `StockIssued` / `StockRepurchased` / `ShareBasedCompensation`: 574 flags investigated, 257 closed, 246 confirmed unclosable

The 501-ticker refresh produced 1,000 quality flags, **574 of them from three concepts across
427 tickers**. Every flagged (ticker, concept) pair was checked against that ticker's own cached
CompanyFacts. Full detail in `tag_investigation_stock_sbc_report.md`.

**The classification is the deliverable, more than the fixes:**

| concept | A tag gap | B genuine absence | C structurally unavailable |
|---|---:|---:|---:|
| `StockIssued` | 302 | 55 | 10 |
| `ShareBasedCompensation` | 26 | 47 | 8 |
| `StockRepurchased` | **0** | 111 | 15 |

**43% of the 574 flags cannot be closed by any tag change**, and `StockRepurchased` is 0/126
actionable. That was worth measuring rather than assuming: the fix and the non-fix look identical
from a flag count. Companies report a repurchase line in a median **29.6%** of the quarters in
which they report operating cash flow, because in the other 70% they bought nothing back and XBRL
does not tag an absent line. The class-C list reads like the answer you would guess if you knew
the companies — TSLA, DDOG, FSLR, VICI, FRT, LNT — and AEP/BXP/DLR carry only *preferred*
redemptions.

**The one tag that would have "fixed" 44 `StockRepurchased` flags was rejected.**
`PaymentsRelatedToTaxWithholdingForShareBasedCompensation` is, by its own element description,
"cash outflow to satisfy **grantee's tax withholding obligation**" — a payment to a tax
authority. Under `fallback` it would populate exactly the quarters with no buyback, and it runs
at a **median 2.9%** of the repurchase figure, far too small to ever corroborate anything for
`share_count_jump_flag`, its only consumer. Flags removed, no answer improved, concept meaning
split in two.

**`StockIssued`'s candidate list only knew about capital-raising issuance.** All three existing
tags describe a company *selling shares to raise money*, which a mature S&P 500 industrial never
does — hence 192 flags reading `MISSING`, 0 of ~75 quarters. What those companies do every
quarter is issue shares through option exercises and ESPP, on their own cash-flow line. Seven
tags appended (aggregate before component), `StockIssued` flags **367 → 123**, `MISSING` 192 → 27.

**`ShareBasedCompensation` in utilities was not a different tag — it is annual-only disclosure.**
18 of the 21 flagged utilities cannot be fixed. NEE, AEP, PEG and ES all carry
`AllocatedShareBasedCompensationExpense`, and **every fact under it has a 12-month duration**:
there is nothing for `decumulate_period_values` to decumulate, so a quarterly pipeline gets zero,
and 21 annual values against a 74-quarter denominator is permanently 28%. The 3 real gaps (ED,
EIX, SO) tag the amount in the equity statement instead;
`AdjustmentsToAdditionalPaidInCapitalSharebasedCompensationRequisiteServicePeriodRecognitionValue`
appended, SO goes 0 → 45 quarters.

**`sum` vs `fallback`: `fallback` both times, and the double-count is real, not hypothetical.**
Where a filer reports both the aggregate `…IncludingStockOptions` tag and the component
`ProceedsFromStockOptionsExercised`, **60 of 145 co-reported quarters carry an identical value**
(ABNB 2023-09-30: 14,000,000 under both). `sum` would report exactly double. Accepted in exchange:
`fallback` undercounts by a median 8.1% where a filer genuinely reports two separate lines. Same
trade as `LongTermDebt` in July, same reason — an undercount degrades gracefully.

**Non-regression, all 501 tickers, per change group:** +13,868 values then +905, and **0 changed,
0 disappeared** both times. Append-only on a `fallback` list can only fill empty dates, and that
was confirmed rather than argued. Total flags **1,000 → 743**; no concept outside the three moved.
The A/B/C classification predicted exactly which 257 pairs would clear — 0 mismatches over 574.

**Two adjacent defects surfaced and are deliberately left for a future task.** The four
`share_count_jump_flag` quarters that stopped firing (INCY, URI) are *not* an improvement: both
"jumps" are artefacts of `normalize_split_adjusted` inventing splits that never happened (INCY
doubled before 2013-09-30; URI halved from 2012-09-30, reading the RSC Holdings share issuance as
a 1:2 split), and both now clear a corroboration test only because `implied_price` is book value
per share — $0.19 and **negative** equity giving $0.27 — so any cash flow at all "explains" any
share count. Separately, `calculate_ttm` rolls over four *available rows*, not four calendar
quarters, so a sparse `_TTM` can silently span years; that is why filling SBC gaps moved
`owner_fcf` for 15 tickers that were never flagged.

---

## 2026-08-07 — Sidebar navigation, a metric encyclopedia written from the code, and a generated coverage matrix

Reference pages reached from a **sidebar view switch**, not more tabs. Tab count was
the stated constraint but not the deciding one: the reference pages are
ticker-independent, so the switch also **hides the ticker controls** when one is
open. Nothing on screen to misattribute beats a disclaimer next to a live selector.
Details in `sidebar_encyclopedia_report.md`.

Documentation lives on the `Metric` dataclass (`description`, `formula`, both
optional). **The usual argument for that — "then a metric cannot silently lack
documentation" — is false**, and worth not relying on: the fields must default to
None or every derived structure changes shape, so a new metric arrives undocumented
from any location. The guarantee comes from `undocumented_metrics()`, which the app
renders as a warning and the tests assert against.

**Every formula was read off the implementation, and two-thirds of the metrics would
be mis-described by a textbook.** The calibration case is worse than expected:
`pe_to_revenue_growth` departs from a conventional PEG **twice** — it divides by
revenue growth rather than earnings growth, *and* that growth rate is computed inline
in `build_valuation_history` as `Revenue_TTM.pct_change(4)`, skipping the
positive-value and `min_base_ratio` guards every other growth figure passes through.
The Revenue growth panel and this panel are two differently-computed numbers.

Other departures found (full table in the report): EV excludes short-term debt,
minority interest and preferred; `debt_to_equity` uses long-term debt only; `p_tbv`
subtracts only goodwill; FFO adds back **total** D&A rather than real-estate
depreciation; `net_interest_margin` divides by total assets; `provision_ratio` by
revenue; seven ratios use period-end rather than average balances; `pb_ratio` is
additionally blanked when tangible equity is negative; EPS is computed from
`NetIncomeLoss_TTM / SharesOutstanding`, not reported diluted EPS.

**Dead input found:** `RealEstateDepreciation` is fetched and TTM'd every run and has
**zero consumers** — it is exactly the input NAREIT FFO needs, and FFO is built from
total D&A instead. Reported, not changed: that is a modelling decision.

The coverage page is generated from `is_hidden`. Checking rather than assuming that a
representative ticker per profile is valid: `is_hidden` uses the ticker only to look
up its profile, and **all 501 tickers × 52 metrics agree with their profile's
representative, zero disagreements**. A synthetic ticker name would *not* work — it
resolves to DEFAULT_PROFILE silently.

**Non-regression, stated honestly.** Only 9 of 24 rebuilt figures are byte-identical
to the baseline; the other 15 differ because `figures.py`'s German UI strings were
translated in between. Rather than assert that, the check collects **every differing
leaf value** and requires each to be explained by an enumerated translation list — so
a genuine label or numeric change would still surface. Result: 0 unexplained
differences. The "formula states its period basis" assertion also caught five real
omissions in my own documentation, which were fixed rather than the check relaxed.

---

## 2026-08-06 (later) — App refinements: a namespace collision, growth ×3, and the current multiple on the chart

Four independent changes. Details in `app_refinements_report.md`.

**The percent bug: two registry namespaces, one name.** The facts table rendered
`Revenue` as `10941700000000.00%`. Cause confirmed: `Revenue`, `NetIncomeLoss` and
`SharesOutstanding` are registered as `CHART_GROWTH` metrics with `percent=True` —
correct, the growth chart plots YoY percentages — and the facts frame has columns
with those same three names holding absolute dollars. `NetIncomeLoss` was affected
identically.

**Matching on `id_namespace` would not have fixed it**, which is the trap worth
remembering: the facts frame's columns *are* XBRL concept names, i.e. exactly the
namespace those entries live in, so a namespace test says "apply" and keeps the bug.
`value_column` is what separates them — a growth entry describes `yoy_growth` and
never `value`. Safe as a single test because registry ids are globally unique
(`_index_metrics` raises on a duplicate at import). A hardcoded three-name exception
would have broken the same day, when the growth expansion registered
`StockholdersEquity` — also a facts column holding an absolute.

**Growth: 3 panels → 10, and the brief's premise was wrong.** `growth_concepts()`
excluded every `_TTM` name, so `EPS_TTM_CALC`, `FCF_TTM`, `FFO_TTM` and every sector
aggregate had **zero** growth values — not computed and discarded, never computed.
Lifting the exclusion costs +0.44s per run and **no extra rows**, only fewer NaNs in
an existing column. Worth it: measured head to head, a raw quarterly growth series is
1.1–2.2× more volatile than its TTM counterpart (three of ~40 pairs invert, so
"always smoother" would be an overstatement).

Two findings that shaped the design:

1. **Zero-crossing is already handled, and the failure mode is the opposite of the
   expected one.** `calculate_growth` requires `value > 0` *and* `prev_value > 0`;
   0 of 9,301 growth values came from a non-positive level. So an expanded chart
   cannot produce an explosive panel — it produces a **gappy** one. Survival rate,
   not outlier count, is the number to look at.
2. **The sector aggregates are free.** `is_hidden` already resolves derived concepts
   through `_DERIVED_CONCEPT_CONSUMERS`: `PPNR` → financial only, `FFO_TTM` → reit
   only, `CoreOperatingEarnings` → the two insurance profiles, at **0**
   `PROFILE_HIDDEN` entries. Registering the raw sector tags instead
   (`NetInterestIncome_TTM`, `EarnedPremiums_TTM`, …) would have cost 22–23 each,
   112 in total — an 18% increase on the 615 entries that exist today. Total cost of
   the shipped design: **1 entry**. That number is the concrete evidence for the
   known "negative list will not scale" problem.

`build_growth` now wraps at `_make_grid`'s 3 columns — seven panels in one row was a
3500px-wide figure. For ≤3 panels the grid is still 1×n at the identical pixel size,
so the three original panels stay byte-identical.

Deleted `GROWTH_BASE_PANELS` / `GROWTH_PROFILE_EXTRA` / `get_growth_panels()`: 15
invented concept names (`fcf_growth`, `nii_growth`, …), none of which existed in any
frame or the registry, zero consumers. Their *intent* was this feature and their data
structure — a positive per-profile list — was the better one; the names were the
problem.

**The current multiple now appears on the valuation charts** as a green diamond at the
run date. It is a separate trace added after the mean is computed and never enters the
series the mean is taken over — structural, not an ordering convention — proved by
mean labels and line values being identical with and without it for all 8 tickers, for
both the harmonic and the arithmetic case. Suppressed when `as_of` predates it, since
appending a run-date point to an earlier window shows data that date could not have
known. 10 of 13 valuation panels have a snapshot counterpart; `ev_fcf`, `pfcf_ex_sbc`
and `p_ffo` have none and render unchanged — note that `p_ffo` is the REIT headline
multiple, a pre-existing gap in `build_snapshot`. Comparison charts deliberately do
**not** get the point (n markers at the same x read as a spike); recorded in the
docstring so the two chart types are not silently inconsistent.

---

## 2026-08-06 — Data inspection layer: the export completes, the app gets a Data tab

The charts could not show the data behind them. `export_for_app()` now also writes
`facts_full.parquet` (all 69 concepts, not the 3 the growth chart draws) and
`current_snapshot.parquet`, and `app.py` gained a Data tab that walks the chain from
raw filing facts to the final snapshot as downloadable tables. Schema 1 → 2.

**The snapshot frame was measured, not assumed:** it is **long** — `ticker`, `end`,
`concept`, `value`, one row per `(ticker, concept)`, 24–41 concepts per ticker by
profile, with a single **constant** `end` (the as-of date, not a period end). So the
snapshot section renders concept/value directly: that already *is* the transposed
view, and pivoting would give one row × 40 columns with nothing to compare it to.

**Two classification rules, both of which the obvious version gets wrong:**

1. **Flags.** Neither `config.py` nor `quality.py` has a registry — `quality.py`'s
   "flags" are unrelated EDGAR *coverage* warnings, and "absent from `METRICS`"
   catches 16 concepts of which only 5 are flags (it also excludes `rotce`,
   `effective_tax_rate` and the nine `*_quarterly`). A `_flag` suffix match alone is
   **wrong, not just inelegant**: it misses `fcf_exceeds_ebitda` and
   `inorganic_contaminated`. So the rule is name-based, lives in one place, and is
   validated against the data — it agrees exactly with "every value in {0,1}" across
   `metrics_long`. The data test is not *used* as the rule because it misfires
   elsewhere: the snapshot's `shares_basis` is 0/1 but is a code, not a flag.
2. **Raw vs derived facts.** The `_TTM`/`_QUARTERLY`/`_CALC` suffixes are not
   sufficient — `PPNR`, `CoreOperatingEarnings` and `TangibleEquity` are derived and
   carry none. The structural rule is exact: a concept is raw iff it is a key of
   `get_concept_candidates(ticker)`, since those are the names actually requested
   from EDGAR. Never contradicts the suffix rule, strictly better where those three
   appear.

**Display formatting is separated from export precision structurally**, not by
convention: the pivot returns numbers, `format_for_display` returns a *separate*
string frame used only by `st.dataframe`, and downloads read the numeric frame.
`percent` from the registry covers the metric frames; facts fall back to the
column's own magnitude, which puts `Assets` at `4.90T` and leaves
`DividendsPerShare_TTM` at `5.9000` without a per-concept table that would go stale.

**Fixed while verifying:** the missing-export branch ended in `st.stop()`, which only
raises inside a script run — headlessly the page fell through into a
`FileNotFoundError`. Now `st.stop()` **and** `return`.

**Two traps worth remembering.** `pivot_table`'s default `dropna=True` silently drops
all-null columns; here an all-null column is the finding (AZO's `roe`, `rotce` and
`debt_to_equity` are null in all 72 periods because its equity is negative), so
`dropna=False` is load-bearing. And **importing `streamlit` swaps plotly's default
template**, shrinking every serialised figure by a constant 3,224 B — which looks
exactly like a regression until you notice the delta is identical across every
ticker and chart type.

Size: `facts_full.parquet` is 13.7 MB extrapolated to 501 tickers, and that is an
upper bound — measured bytes/ticker falls from 34,619 at one ticker to 28,691 at
eight as Parquet's dictionary encoding amortises. Full detail in
`data_tab_report.md`.

---

## 2026-08-05 — Export layer + Streamlit prototype: the batch/read split goes live

`main.export_for_app()` writes the frontend's inputs at the end of
`run_full_refresh()`, and a new `app.py` reads only those files — no pipeline
computation in the request path. `figures.py` and `config.py` unmodified,
verified by SHA-256 before and after rather than by memory.

**Parquet, not CSV**, and the verification is the argument: for AAPL/JPM/AMT the
figures built from the Parquet round-trip are **byte-identical** to those built
from the in-memory frames — including the `as_of` and narrowed-`concepts` calls,
which are exactly the paths that break if `end` stops being a real datetime.
`facts_growth.parquet` is narrowed by rows as well as columns (18,120 -> 1,705,
10.6x) because `GROWTH_PANELS` provably bounds what `build_growth` can draw; the
concept list is derived from `config.METRICS` so a new growth panel widens it
automatically. Files are written temp-then-`os.replace` (atomic per file) with
`meta.json` last; the residual cross-file window is documented, not hidden.
`universe.parquet` lists tickers that **produced data**, not
`get_active_tickers()` — which returns `sorted(TICKER_PROFILES)` and so cannot
tell "asked for" from "worked". The ad-hoc `main()` path deliberately does not
export: it runs on `config.TICKERS` and would replace a 501-ticker export with
two.

**Audit findings (reported, mostly not fixed).** `main()` and
`run_full_refresh()` have drifted six ways; three are behaviour questions rather
than dead code and were left for a decision: `main()` drops NaN rows before
writing `valuation_history.csv` while the full refresh does not, `main()` sorts
the frames before writing and the full refresh does not, and the
`SNAPSHOT_AS_OF_DATES` loop exists only on the ad-hoc path. Also confirmed:
**no code anywhere reads a project CSV back** — they are human-facing only.
Fixed exactly one unambiguously stale thing: the run report said "Plot (per
ticker, both figures)" when there have been three charts per ticker for some
time.

One deliberate deviation from the brief: it asked for
`st.plotly_chart(use_container_width=True)`, but on Streamlit 1.61 that
parameter is past its stated removal date of 2025-12-31 and warns on every
chart, so `width="stretch"` is used instead (`streamlit>=1.50` pinned).
Details in `app_export_layer_report.md`.

---

## 2026-08-05 — METRICS registry: one source of truth for the plotting spec

A metric's properties lived in five separate structures in `config.py`
(`FUNDAMENTALS_TO_PLOT`, `VALUATIONS_TO_PLOT`, `GROWTH_PANELS`,
`QUARTERLY_COUNTERPART`, `HARMONIC_MEAN_CONCEPTS`), with `figures.py`
reconstructing the association a sixth time in `_concept_plot_spec`. Adding a
metric meant touching up to four of them. Now there is one `METRICS` list of 45
frozen `Metric` dataclasses, and the five names are **derived** from it — so
every consumer keeps working unchanged and correctness reduces to one provable
claim: the derived structures equal the pre-change literals. Verified against a
pickled capture of the actual objects, element-wise including `type()` and
`repr()` at every leaf, so `0` vs `0.0` and `None` vs `0` could not slip through.

Frozen dataclass over dict/TypedDict because it is the only option that fails at
*runtime*: a missing field is a `TypeError` at import, a typo'd field name is a
`TypeError` naming the correct spelling, and entries cannot be mutated. Duplicate
ids and unknown chart names raise from `_index_metrics` at import. The legacy
`symlog` flag deliberately did **not** enter the registry (no metric ever set it,
nothing renders it); the derived 5-tuple supplies its constant `False`
positionally.

Structural finding: **no id appears in two charts** (45 unique across 29+13+3),
so `_concept_plot_spec`'s valuation-before-fundamentals scan order was moot and
its replacement by a flat `METRICS_BY_ID` lookup cannot change any answer.
Also confirmed before relying on it: every `QUARTERLY_COUNTERPART` value is
exactly `<id>_quarterly` and every `HARMONIC_MEAN_CONCEPTS` member is a valuation
id, so both collapse to booleans on the metric without special cases.

New: `CHART_SPECS` makes the id namespace explicit (fundamentals/valuation ids
are metric names read from `value`; growth ids are XBRL concept names read from
`yoy_growth`) — previously only implied by list membership and hardcoded inside
`_concept_plot_spec`. `Metric.label_for(language)` adds room for a second
language with fallback to the primary label, never to an empty string; no German
labels were invented, the field is present and unpopulated.
`config.get_plottable_metrics(chart, ticker, language)` gives a frontend picker
its options, already narrowed by `is_hidden` when a ticker is supplied, so a
picker cannot offer a metric the chart would then drop.

All 32 per-ticker and 8 comparison figures byte-identical. Details in
`metrics_registry_report.md`.

---

## 2026-08-05 — Figure builders parametrized: panel selection, sizing, as-of window

Three decisions the builders used to make internally are now caller-supplied,
each unblocking a planned frontend feature. `figures.py` only; `main.py`
untouched, its six call sites pass none of the new parameters.

**Panel selection** (`concepts=None`) narrows what is drawn. The rule lives in
one shared `_select_concepts` helper, and `is_hidden` stays authoritative *by
construction*: the catalogue is visibility-filtered first and the caller's list
only intersects what survives, so there is no path by which a requested name
reaches the render loop unchecked. Unknown or hidden requests are ignored with a
printed note rather than refused — a UI hands one selection to several tickers
and a concept fine for one is routinely hidden for another (`fcf_margin` is
visible for `standard`, hidden for `financial`), so refusing would turn normal
operation into an error. Order follows the config catalogue, never the caller's
list, so panel order is stable however the UI sends it. The grid re-tiles for
free (9 panels 3x3 -> 3 panels 1x3, no trailing cells).

**Sizing** via `width`/`height` parameters. Needed three states — unchanged,
omit the key, use this number — and `None` had to mean "omit" (that is what
`use_container_width` requires), so "unchanged" is a named `KEEP` sentinel.

**`as_of`** anchors the valuation window, shared by `build_valuation` and
`build_ticker_comparison` through one `_window_frame` helper. A supplied `as_of`
bounds the window **above** as well: one-sided filtering would answer
"everything since that date" instead of "the last N years as of that date" and
show data the chosen date could not have known — the opposite of what an as-of
view is for. The upper bound is applied only when `as_of` is given.

Also removed the unused `datetime` import; kept `_make_grid`'s unreachable
`n == 0` branch as a documented defensive no-op (without it `cols` becomes 0 and
the next line raises `ZeroDivisionError`).

**Non-regression proved by byte comparison against a baseline captured before
the edits** (with the dataframes pickled, so yfinance re-adjustment cannot
create a false positive): all 21 per-ticker figures and all 4 comparison figures
byte-identical. A first run failed on the comparisons only — `data` and `layout`
compared equal at identical length, the difference was purely serialised key
*order* after `width`/`height` moved to the end of the layout dict. Fixed by
restoring the original keyword position (splatting `_size(...)` in place) rather
than by weakening the claim. Details in `figures_parametrization_report.md`.

---

## 2026-08-05 — Comparison cleanup: batch pre-rendering removed, build/write split introduced

Phase 3's comparison *rendering* was right; its *batch pre-rendering of fixed
peer groups* was wired for a world without a frontend. Removed
`config.COMPARISON_GROUPS` and `main.render_comparison_charts` with both call
sites, the timing entry, and two now-dead imports — six touchpoints, found by
grep rather than by assuming the two call sites were all. Nothing in the project
ever read a figure file back, so existing `figures/compare_*` files just go
stale (same treatment Phase 1 gave the old PNGs).

Introduced the **`build_*` returns a figure / `plot_*` writes it** convention and
applied it to all four chart functions. The split was mechanical for every one
of them — each built a figure through one linear path and handed it to
`_write_figure` as its last statement — so all were cut rather than proposed;
`plot_metric`/`plot_metric_dual` need no split, they mutate a figure passed in.
Proof the wrappers add nothing: `build_*(...).to_json()` is **byte-identical**
to the file `plot_*` writes, for 9 ticker x chart combinations.

Exclusion information now reaches callers through three channels from one
computation: the returned `excluded` list (Python callers), `fig.layout.meta`
(survives `to_json`, so a JS consumer of the `.json` gets it), and the existing
red on-chart annotation (standalone HTML readers). The returned tuple has to be
primary because in the degenerate case there is no figure to hang meta on —
`build_ticker_comparison` returns `(None, excluded)`, where a non-empty
`excluded` means "everything was dropped" (a data outcome) and an empty one
means "the request was rejected" (unknown concept, fewer than 2 tickers).

Dropped the hard `MAX_COMPARISON_TICKERS` refusal from the rendering layer — a
readability limit belongs in the UI picker, and a hard refusal deep in rendering
turns a UI mistake into a missing chart. Kept as advisory
`SUGGESTED_MAX_COMPARISON_TICKERS = 3` (renamed so nobody re-adds enforcement
against it), kept the enforced minimum of 2, and widened the palette 3 -> 10 so
palette width cannot silently become the real cap; the first three colors are
unchanged and indexing still wraps rather than raising. Details in
`comparison_cleanup_report.md`.

---

## 2026-08-05 — Plotly migration Phase 3: multi-ticker comparison charts

New `plot_ticker_comparison(tickers, concept, data, output_path, years=5)` in
`figures.py` — one metric, one line per ticker, 2-5 tickers, reusing Phase 1's
scaffolding and dual HTML+JSON output. `config.py`, `main.py` and the four
existing plot functions untouched. No buttons: Plotly's legend already does
per-trace show/hide, which is why Phase 2's `updatemenus` were rolled back.

The load-bearing decision was **scope**: comparisons are allowed across
profiles, gated per ticker by `is_hidden(ticker, concept)` rather than by a
same-profile rule. The measurement that settled it — six metrics (`roe`,
`revenue_yoy_growth`, `pe_to_revenue_growth`, all three growth panels) are
visible in **all 24** profiles, so a profile-equality rule would block sound
comparisons; and `p_tbv` is visible in exactly `financial` + `insurance_life` +
`insurance_pc`, so it would also block bank-vs-insurer, which is meaningful.
Meanwhile for narrow metrics (`p_ffo` 1 profile, `efficiency_ratio` 1, `dio` 3)
`is_hidden` already blocks the nonsense. The right granularity is metric x
profile, which `config.py` already encodes — a second, coarser gate would only
add false negatives.

Consequently the visibility-mismatch case is real, and a hidden ticker is
**dropped but never silently**: printed *and* written onto the chart as a red
annotation naming the responsible profile, so the HTML stays self-documenting
without console output. Chart furniture (ylabel, ref line, percent, and whether
the 5-year valuation cutoff applies) is looked up from the same config tuples
the single-ticker charts read, so a comparison chart cannot drift from them —
verified element-wise: `pe_ratio` for JPM/BAC has x-values identical to their
own `plot_valuation` traces, while fundamentals metrics keep full history.
Per-ticker mean lines omitted; metric-level ref lines kept.

Wired into `main.py` via `config.COMPARISON_GROUPS` (8 starter peer groups, cap
3 tickers each) and `render_comparison_charts()`, called from both `main()` and
`run_full_refresh()`; concepts route to the right dataframe through
`figures.concept_source()`, and a group with a ticker missing from the run is
skipped whole rather than drawn partially.

**Two pre-existing data gaps surfaced by the comparison charts** (found because
a comparison names what it drops, not fixed here): `DG` reports no
`AccountsReceivable` facts at all and `DLTR` only 2, so `cash_conversion_cycle`
is empty for both — the configured chart was moved to `dio`. And a scan of all
501 cached `companyfacts` payloads found **2 tickers with none of the three
`SharesOutstanding` candidate tags**: `V` (only the dei cover-page tag
`EntityCommonStockSharesOutstanding`) and `STZ` (no usable share tag at all).
Both have 0 rows for `SharesOutstanding` and `EPS_TTM_CALC`, and 0 non-NaN
`pe_ratio` / `ev_ebitda` / `pfcf_ratio` — blank P/E charts and a market cap
resting entirely on the yfinance fallback. Admitting
`EntityCommonStockSharesOutstanding` as a last-resort tag would change the
series from a period weighted average to an as-of-filing point-in-time figure
and interacts with the yfinance-vs-EDGAR share resolution, so it needs its own
task. Details in `plotly_migration_phase3_report.md`.

---

## 2026-08-03 — Plotly migration Phase 1: rendering backend swapped, selection logic untouched

`figures.py` rewritten from matplotlib to Plotly. Same five functions (`plot_metric`,
`plot_metric_dual`, `plot_fundamentals`, `plot_growth`, `plot_valuation`), same
config-driven panel selection (`is_hidden`, `FUNDAMENTALS_TO_PLOT`,
`VALUATIONS_TO_PLOT`, `GROWTH_PANELS` — `config.py` untouched), but each chart now
writes a self-contained interactive `.html` plus a `.json` figure spec (for the
future web app) instead of a `.png`. `output_path` is treated as a stem; the six
call sites in `main.py` now pass extension-less stems, and a legacy `.png`/`.html`/
`.json` extension is stripped defensively. The dead `symlog` parameter was dropped
(no metric sets the flag; the 5th `FUNDAMENTALS_TO_PLOT` tuple element is unpacked
and discarded). Global pyplot state (`plt.subplots`/`plt.close`) is gone — the
functions build plain `go.Figure` objects and are thread-safe. Degenerate cases now
defined: missing growth column or zero visible panels → warning, **neither** output
file written (verified no active ticker of 501 hits zero panels). One Plotly 6.9
trap found: `add_hline(annotation_text=..., row=, col=)` is a silent no-op — mean
lines are drawn as `add_hline` + separate domain-coordinate annotation instead.
Verified programmatically for AAPL (standard), JPM (financial), O (reit): panel
sets identical to the matplotlib-era selection, trace values byte-identical to the
source dataframes, harmonic/arithmetic mean labels reproduce `metrics.harmonic_mean`
/`Series.mean` exactly. `matplotlib` removed from `requirements.txt` in favor of
`plotly>=6.0`. Full details in `plotly_migration_phase1_report.md`.

---

## 2026-08-02 — Nine external-review improvements: seven built, one refused on evidence, one premise disproven — plus a share-count audit bug the work exposed

A nine-item batch from an external review. Seven implemented, one deliberately not
implemented, one found unnecessary because its premise did not survive the raw
data. Every item was checked against real cached facts before any code was written.

**Symmetric share-count resolution (implemented).** The existing rule only switched
to EDGAR when `edgar/yfinance > 1.10`; three tickers had the opposite failure, with
yfinance overstating by near-integer factors: KLAC **9.91x** (131.75M vs 1,306.3M),
CRWD **3.95x**, DVN **1.87x**. The negative-delta distribution has **no separation
at 1.10** — ratios run 9.91, 3.95, 1.87 | 1.23, 1.12, 1.09, 1.06 ... continuously
down to 1.0 — so `MIN_YF_SHARE_OVERSTATEMENT = 1.50` was placed in the only wide
gap rather than reusing 1.10 inverted. A second condition was forced by the data:
**BKR's newest `SharesOutstanding` fact is 2021-06-30 while its newest fact of any
kind is 2026-06-30, a 1,826-day lag** — there yfinance is right and EDGAR is five
years stale, so preferring EDGAR would have made `market_cap` worse.
`MAX_EDGAR_SHARE_LAG_DAYS = 200` (measured against the ticker's own newest fact,
not today's date, so a wholly SEC-lagged payload isn't punished twice). Result:
KLAC's market cap corrected from a nonsensical **$238.8B to $24.1B**, `pb_ratio`
40.96 -> 4.13, `ev_ebitda` 340.00 -> 39.45; CRWD $194.3B -> $49.2B; DVN $52.1B ->
$27.9B. TSLA (1.12x, not near an integer factor) and BKR correctly left on yfinance.

**A pre-existing bug the switch exposed.** `build_snapshot()` called
`_resolve_share_sources()` a second time against `snap` *after* overwriting
`snap["shares_outstanding"]` with the resolved count — so for any ticker that
actually switched, the audit columns compared EDGAR against EDGAR. This means the
previous task's reported finding "0 tickers cross the 10% switch threshold" was an
artifact: **35 tickers were already resolving to EDGAR** via the original
dual-class rule (ABNB, AOS, APP, BF-B, C, COIN, DD, DDOG, DELL, EL, FOX, FOXA, GOOG,
GOOGL, HOOD, HSY, LEN, LITE, META, NKE, NWS, NWSA, PLTR, RDDT, RL, SATS, TAP, TKO,
TSN, TTD, UHS, UPS, WDAY, WDC, XYZ) with true deltas of 10.2-15.7% misreported as
0.0%. Fixed by resolving once off the untouched `prices` and reusing the result.

**`debt_inferred_zero`: not implemented, on evidence.** 15 of 498 tickers have no
resolvable `LongTermDebt` balance tag. The proposed rule ("no debt tag AND no
debt-flow tags ⇒ real zero") was to be validated against the already-confirmed
GRMN/LULU/DECK cases — **all three fail it**: GRMN has `RepaymentsOfLongTermDebt`,
LULU has `ShortTermBorrowings`/`OtherBorrowings`/`LineOfCreditFacilityAmountOutstanding`,
and DECK has four such tags and isn't even a candidate (it resolves a balance). A
looser rule that admitted them would sweep in **GM ($219B total liabilities, six
`LongTermDebtMaturitiesRepaymentsOfPrincipal` tags)** and TXT — a catastrophic
false "zero debt". Only 3 of 15 (VEEV, ISRG, MPWR) have clean evidence; recommended
as targeted `TICKER_CONCEPT_OVERRIDES`, not shipped as a blanket rule.

**Dual-class share summing: unnecessary, premise disproven.** The review assumed
per-class tags (`CommonClassACommonStockSharesOutstanding`) needing summation.
**No class-specific share tag exists in any cached payload** — the SEC
`companyfacts` endpoint returns only consolidated, non-dimensional facts; per-class
values live in XBRL dimensions it does not expose. The resolved values are already
all-class totals (GOOGL `CommonStockSharesOutstanding` = 12,230,000,000 ≈ A+B+C;
META basic weighted-average = 2,534,000,000 ≈ A+B). BRK is not in the active
universe at all. Separately noted, not fixed: **FOX/FOXA are two tickers on one CIK
with identical payloads, and their only `dei:EntityCommonStockSharesOutstanding`
fact is a garbage value of `1`** from a 2019 10-Q.

**Six flags/metrics added**, each threshold calibrated against the real
distribution rather than assumed:

- `share_count_jump_flag` (>15% QoQ share change with no buyback/issuance of
  comparable size). |QoQ change| runs median 0.48%, p90 3.3%, p95 6.6%, **p97
  12.7%** — 15% sits just above p97, 763 of 30,706 periods flagged. Checked rather
  than assumed whether the named tickers clear it: RDDT 6 (IPO window), META 3
  (2012-13 IPO era), FOX/FOXA 1 each, **GOOGL 0** — the review's implication that
  GOOGL would was wrong. Coverage caveat handled explicitly:
  `PaymentsForRepurchaseOfCommonStock` covers 96.2% of tickers but
  `ProceedsFromIssuanceOfCommonStock` only **54.6%**, so a missing issuance tag is
  treated as "no corroboration available" rather than "no issuance happened".
- `avg_X_5y_history_too_short` (<12 valid observations in the rolling window).
  `calculate_rolling_harmonic_stats` now also emits `_n`, necessary because
  `min_periods=1` lets a "5-year average" come from a single quarter. Cutoff 12
  confirmed against real data: valid `pe_ratio` quarters run median 19, p10 13,
  p5 10 — 12 sits just below p10. 18 of 493 tickers flagged, every one genuinely
  young or newly separated (RDDT 6 quarters, CRWD 4, GEV/SOLV/SW/VLTO spin-offs,
  Q/PSKY/SNDK 1 each). Scope noted honestly: it catches short history, **not**
  "long history with sparse recent data" (BA has 3 valid P/E quarters in 5 years
  because loss quarters are masked, yet its window still fills from older rows).
- `fcf_exceeds_ebitda` — named for the observation, not a cause, **because the
  presumed cause was checked and disproven**. SBC covers anywhere from **54%**
  (FTNT) to **674%** (CSCO) of the FCF−EBITDA gap: 104% NOW, 153% CRM, 118% ADSK,
  326% FFIV, 443% ADBE, 68% EA. For FTNT/EA it is insufficient (working capital
  does the rest); for CSCO/ADBE/FFIV it massively exceeds the gap, meaning the gap
  is a small net residual of large offsetting effects. The population isn't even
  purely software — CNC, MCK, CAH (negative-working-capital distributors) are among
  the most frequent. A flag asserting "SBC-driven" would have been wrong.
- `sbc_ttm` / `owner_fcf` / `pfcf_ex_sbc`. Tag coverage checked first: **98.2%** of
  tickers have a usable SBC tag (87.8% plain `ShareBasedCompensation`); weakest
  profiles `energy_integrated` 75%, `materials_integrated` 87.5%. Realised coverage
  415 tickers vs 457 for `pfcf_ratio`. Tells a genuinely different story — DDOG
  40.6 -> **155.0 (3.82x)**, NOW 22.4 -> 42.9 (1.91x), PANW 1.78x — while KO
  (1.02x) confirms it collapses to `pfcf_ratio` where SBC is immaterial.
- `<multiple>_band_elevated` — the project's **first cross-sectional (peer)
  comparison**; every prior guard was about a single ticker's own history. Peer =
  profile-mate, reusing `TICKER_PROFILES` rather than inventing a second notion of
  comparability; profiles under `MIN_PEER_GROUP_SIZE = 5` are skipped entirely
  (`alt_asset_manager` has 1, `homebuilder` 2, `airline` 3 — a "median" there is
  noise). The peer median is over each peer's own latest value, not a strict
  same-date cross-section, because fiscal calendars differ within every profile.
- `inorganic_contaminated` (Goodwill >20% QoQ). Goodwill QoQ change is median
  **exactly 0.000** (static between deals), p90 4.6%, p95 14.5%, p97 30.7% — 20%
  sits between p95 and p97, 1,006 of 24,919 periods across 361 tickers. NOW (10
  periods) and CRM (9) both flagged as expected.
- `effective_tax_rate` + `low_tax_rate_flag`. Tags checked first:
  `IncomeTaxExpenseBenefit` 99.4%, some pretax tag 99.0%. Requires a **positive**
  pretax denominator (a loss quarter's tax benefit over negative pretax income
  gives an arithmetically positive ratio meaning the opposite of a low burden).
  Correctness check: observed median **22.5%** against a 21% US statutory rate.
  60 tickers currently below 10%, the extreme end exactly the intended NOL
  population — AXON −86%, UBER −76%, AES −71% (valuation-allowance releases).

Non-regression, all 498 tickers: `metrics_long` **0 changed / 0 removed**
(+128,227 added), `valuation_history` **0 changed / 0 removed** (+19,711
`pfcf_ex_sbc`), `snapshot` 97 changed / 0 removed / +4,419. All 97 reconcile
exactly: 38 `shares_source_is_edgar` + 35 `shares_delta_pct` (the audit bug fix
above) + 8 concepts x KLAC/CRWD/DVN. The baseline for this diff had to be produced
by **reconstructing the pre-task sources into a separate package** (an early
background run had picked up half-finished edits); each reverted hunk was asserted
to apply exactly once, and the reconstruction was validated by reproducing the
prior task's known-good `metrics_long` row count of 535,874 exactly.

---

## 2026-08-01 — Valuation quality: buyback-distortion flag, tangible-book P/B hide, harmonic-mean 5y averages, share-count transparency, and ev_fcf

Four independent improvements, each calibrated against real data first.

**Buyback-distortion flag.** `pb_ratio`/`roe` distort when a profitable company
shrinks its own equity base via buybacks, before the existing near-zero/negative
guards have to mask anything. `MIN_BUYBACK_EQUITY_QOQ_DECLINE = 0.15` calibrated
from the real distribution (profitable, both-quarters-positive periods: p97 13.3%,
p99 28.3%) against the named names' own history (ORLY p90 33.4%, MCD 17.4%, HD
27.7%, LOW 19.8%). **AZO correctly never qualifies** — its equity has been
continuously negative since 2009, so it never has two positive quarters to compare.
641 flagged `(ticker, end)` pairs across 221 tickers; ORLY 7 periods, MCD 4, HD 10,
LOW 5.

This one **deliberately flags rather than masks**, breaking the project's
otherwise-universal convention, and the departure is the point: unlike the
near-zero-equity cases the existing guards hide, a buyback-driven decline produces
a mathematically valid and *informative* ratio for exactly the high-quality
compounders where an investor most wants to see it. Precedent already in the
codebase: `fundamentals_stale` is a value-triggered flag alongside its data, not a
mask of it. Verified the flag does not suppress: ORLY's flagged 2017-06-30 still
shows `pb_ratio = 15.3`.

**`tangible_book` turned out to already exist.** Checked project-wide before
building: **no intangibles-net-of-goodwill concept exists anywhere** in
`CONCEPT_CANDIDATES` — every "Intangible" hit is an amortization *expense* tag, not
a balance-sheet stock. So the documented fallback applies, and it is exactly the
existing `TangibleEquity` (= `StockholdersEquity − Goodwill`) already feeding
`p_tbv`. No second, parallel field was built. What *was* missing: `p_tbv` masks on
non-positive tangible equity but the ordinary `pb_ratio` had no equivalent guard,
so a negative tangible book silently produced an undefined P/B. Now masked in both
`build_valuation_history()` and `build_snapshot()`. All five named tickers
currently have negative tangible equity and lose their `pb_ratio` — **HD is the
clearest argument for the fix: −$8.6B tangible equity was producing a
plausible-looking `pb_ratio = 23.9`** that gave no hint anything was wrong.

**Harmonic-mean 5-year averages.** `plot_metric`'s `show_mean` arithmetically
averaged the ratio itself, which overweights near-zero-denominator spikes. Scope
was measured, not assumed, across 10 candidate multiples: in scope are `pe_ratio`
(median divergence 9.9%), `pfcf_ratio` (11.6%), `p_tbv` (9.9%), `p_ffo` (6.3%),
`ev_ebitda` (4.0%), `p_ppnr`, `p_core_earnings`. Excluded with evidence:
`ev_sales` (3.2% — revenue never approaches zero), `dividend_yield` (already a
yield; its large figures are float noise from comparing two near-zero numbers for
non-payers like NVDA), and `pe_to_revenue_growth` (a ratio-of-ratios with its own
guards, where 1/x isn't a meaningful yield).

`calculate_historical_pe()` was **replaced** by
`calculate_rolling_multiple_averages()`, which sources each series from
`build_valuation_history()`'s already-guarded output instead of recomputing raw
ratios — the old function had its own ad-hoc `pe_ratio` recompute with **no
positive-denominator guard at all**, which is why BKR's `avg_pe_5y` was **−215.6**,
a negative "average P/E". `avg_pe_5y` generalized to seven fields via
`AVG_5Y_FIELD_NAMES`, each with a `_median` sibling and a `_diverges` flag
(`MIN_AVG_5Y_DIVERGENCE = 0.20`, ~p90 of the observed |harmonic−median|/median
distribution). Verified on real cases: MCHP (thin earnings, P/E 15.9-152.4)
arithmetic 41.6 vs harmonic **26.6**; KO (stable, 20.8-28.4) 23.86 vs 23.71, a
0.6% difference confirming the two agree where there's nothing to correct.

**Share-count source transparency.** `shares_source_is_edgar` and
`shares_delta_pct` added, both built from a single shared `_resolve_share_sources()`
so the audit columns cannot drift from the resolution itself. Emitted as 1.0/0.0
rather than a string because the long format's single numeric `value` column would
otherwise become `object` dtype on reload and break every downstream consumer —
the same encoding `fundamentals_stale` already uses. (The reported distribution
from this task was later found to be corrupted by a second-call bug; see the
2026-08-02 entry.)

**`ev_fcf`** added alongside `pfcf_ratio`, guarded on `FCF_TTM`'s own scale exactly
as `ev_ebitda` is on `EBITDA_TTM`. Hiding was decided per profile from real FCF
signs rather than copying `pfcf_ratio`'s hide list: `utilities` FCF is negative in
**61.4%** of quarters (hidden), `financial`/`insurance_*` already hide every
EV-based multiple (hidden), but **`reit` is a deliberate exception — REIT FCF is
usually positive (median 0% negative quarters per ticker, 11 of 17 never
negative)**, so the sign-based justification simply doesn't hold there. Adding
`ev_fcf` as a third, unhidden consumer of `FCF_TTM` correctly flips `FCF_TTM` back
to visible for `reit` (644 rows across 17 tickers that `filter_hidden_rows()`
previously dropped) — a deliberate, verified side effect, with
`is_hidden("JPM", "FCF_TTM")` unchanged at `True`.

Non-regression, all 498 tickers: `metrics_long` 507,044 unchanged / 0 changed;
`valuation_history` 204,262 unchanged / 0 changed, 4,756 `pb_ratio` rows removed
(all the negative-tangible-book hide); `snapshot` 11,865 unchanged, 491 changed
(all `avg_pe_5y`, the arithmetic->harmonic fix), 112 removed (111 `pb_ratio` + BKR's
bogus negative average). **0 unexpected changes anywhere.** A bug in this task's
own first implementation was caught by its verification and fixed before shipping:
`calculate_buyback_distortion_flag()` combined a fresh boolean mask with a column
from a `pd.merge()` result using `&`, and pandas' index-based alignment against the
merge's fresh RangeIndex silently zeroed it (ORLY showed 0 flagged instead of 7).

---

## 2026-08-01 — Full-universe validation of the staleness-aware refetch: 148 tickers behind, 81 fixed, 64 confirmed SEC-lagging

The mechanism built the previous day, run for the first time across all 498 active
tickers rather than a 9-ticker subset.

**Results.** 148 tickers were behind their published period; **81 fixed by
refetch** (73 moving 2026-03-31 -> 2026-06-30), 64 refetched but confirmed the
SEC's aggregated payload still lacks the newest published period, 3 (META, NEE,
WFC) correctly skipped by the daily retry cap having already been attempted that
day. 350 untouched tickers: **0 changed payloads, 0 changed periods**, confirmed
by MD5, not inferred.

**Cross-checked directly** rather than assumed from shared inputs: the 67
still-behind tickers are flagged by `add_staleness_fields()`'s own
`fundamentals_stale` in **67/67** cases, the 81 fixed in **0/81**, the 350 never
behind in **0/350** — exact agreement.

**Retry cap at full scale.** A second full pass over all 498 immediately after
produced **0 additional `companyfacts` calls** in 88.8s — the cap holds
universe-wide, not just for the 3 tickers checked in the subset.

**Cost.** 145 calls / 557.6 MB / 86.9 min, against 2,117.1 MB for an unconditional
refresh of all 498 (measured two independent ways: the full on-disk sum, and a
10-ticker direct sample at 4.17 MB/call that left no side effects) — a **73.7% data
and 70.9% request saving**. The two per-call latency figures disagree by ~36x
(36 s/call sustained vs 987 ms/call in a short burst); reported rather than papered
over, and attributed to network/SEC-side behaviour since the mechanism contains no
rate-limiting or backoff of its own.

**One anomaly reported, not smoothed over**: 8 of the 64 still-lagging tickers (BG,
C, CNP, CTAS, GLW, HUM, PFG, PPG) had their cached payload change byte-for-byte on
refetch despite reporting the same newest period — consistent with EDGAR revising
earlier-period facts, and harmless to the period-based staleness classification,
but surfaced because the check was run directly rather than assumed.

---

## 2026-07-31 — `fetch_or_cache` had no TTL at all: a staleness-aware refetch built on the submissions index, not a date threshold

`fetch_or_cache()` was a pure `os.path.exists` check — once a `companyfacts`
payload was cached it was **never** refetched, so 152 tickers sat on stale
fundamentals indefinitely. A naive date-based TTL was explicitly rejected and
proven impossible on this data: 311 tickers sit at exactly 123 days since their
last filing, of which 133 are genuinely stale and 178 merely mid-cycle — **the same
number on both sides of any threshold**, so no date cutoff separates them.

**Design: cheap probe, content-based decision.** Three artifacts with three
policies. The expensive payload (`companyfacts`, median 4.18 MB) never expires on
age. The cheap probe (`submissions`, median 0.18 MB — **4.2%** of the payload)
carries the only time-based expiry, `SUBMISSIONS_MAX_AGE_DAYS = 1`, via a new
opt-in `max_age_days` parameter that defaults to `None` so every existing caller
keeps its original behaviour. A tiny sidecar (`{ticker}_cache_meta.json`) holds the
derived `newest_period` plus a `last_refetch_attempt` ledger, so the freshness
check never has to load the 4 MB payload. The refetch decision is therefore
**content-based** (has the company published a period newer than what's cached?),
never age-based; the 1-day expiry sits only on the probe.

The retry attempt is recorded **before** the request, so a failure still counts
against the daily cap — bounding the SEC-aggregation-lag case to one wasted request
per ticker per day instead of one per run. The probe is an optimisation, never a
hard dependency: if it throws, the cache is served.

Measured cost of the new check in the common (already-current) case: **median −0.1
ms added latency, worst case +4.7 ms, 0 network calls**. When the probe's daily
cache has expired it costs ~941 ms for one 0.20 MB round-trip — real, not zero, and
reported as such.

Subset validation was run **before** any full-universe run: AMZN/AON/APH/MA moved
2026-03-31 -> 2026-06-30 (fixed), META/NEE/WFC correctly stayed behind rather than
being falsely marked fixed, MSFT/GOOGL were untouched with no attempt recorded, and
an immediate second run made **0 `companyfacts` calls**. `delete_cached_facts()`
extended so a full refresh removes all three artifacts.

---

## 2026-07-31 — META's missing quarter was never a code bug: SEC-side aggregation lag, plus a share-count source conflict and a PEG rename

**META.** The missing 2026-06-30 quarter was proven **not** to be a fetch or parse
defect: refetching via stdlib `urllib`, bypassing the project's `requests` client
entirely, returned a payload **byte-identical** to the cache. The 10-Q had been
accepted by EDGAR but not yet aggregated into `companyfacts` — and ingestion is not
time-ordered (AMZN filed later than META yet was aggregated first), with observed
lag up to ≥8 days. Nothing to fix in this project's code.

**Staleness guard.** Since no date threshold can separate stale from mid-cycle (see
the TTL entry), a `fundamentals_stale` flag was built on the authoritative
submissions index instead: `get_submissions()` / `get_latest_filed_period()` read
the newest `reportDate` across 10-Q/10-K forms, and a ticker is stale when its
published period exceeds its newest cached fact. `STALENESS_DAYS_FALLBACK = 135`
covers tickers with no submissions entry, so the date-based answer remains as a
fallback rather than the primary signal.

**Share-count source conflict.** EDGAR and yfinance disagreed for 40 tickers.
Rejected the obvious "always prefer EDGAR" fix after finding **three distinct
causes**, including genuine splits proven by `dei/yf` ratios of exactly `0.100` and
`0.250`. The shipped rule is deliberately asymmetric —
`MIN_SHARE_COUNT_DISAGREEMENT = 0.10`, EDGAR preferred only when materially
*larger* — because the failure being corrected is a stale pre-split EDGAR count.
(The opposite direction went unhandled until 2026-08-02.)

**`peg_ratio` renamed to `pe_to_revenue_growth`.** The metric divides P/E by
*revenue* growth, not earnings growth, so the name was simply wrong. Recomputing it
against earnings growth was tested and rejected on measurement: it is strictly
worse (38.4% vs 21.9% negative denominators, and `std = nan` from infinities).
Renamed in `build_valuation_history()`, `build_snapshot()`, and the encyclopedia.
**Known gap, still open:** `VALUATIONS_TO_PLOT` in `config.py` was missed and still
lists `("peg_ratio", "PEG Ratio Revenue", ...)`, a concept the pipeline no longer
produces — so that valuation panel renders "keine Daten" for every ticker. Found
during the 2026-08-02 documentation audit; not fixed there because that task was
documentation-only.

---

## 2026-07-30 — Denominator guard wired into `build_valuation_history`, six ticker data bugs, and `MAX_MULTIPLE` removed

**The guard was never wired in.** `apply_denominator_scale_guard` protected
`roe`/`debt_to_equity`/`build_snapshot`'s ratios but **not**
`build_valuation_history()`, so the historical valuation multiples had no
scale-sanity protection at all. Now applied to `pe_ratio`, `pb_ratio`,
`pfcf_ratio`, `ev_ebitda`, `p_tbv`, `p_ppnr`, `p_core_earnings`, `p_ffo`.

**Threshold recalibrated, and a proposed value rejected on measurement.**
`MIN_VALUATION_DENOMINATOR_SCALE_RATIO = 0.001`, far below the 0.01 used for
`roe`. A 0.01 threshold was measured and rejected: it would delete **1,031 real,
ordinary multiples** belonging to thin-margin distributors, because market cap
tracks earnings rather than revenue, so a legitimately small earnings-to-revenue
ratio is normal there rather than a data defect. (An earlier draft of the code
comment asserted a different figure before the measurement was run; it was
corrected to the measured 1,031 rather than left as written.)

**`MAX_MULTIPLE` removed.** The blunt absolute cap became redundant once the
scale guard was wired in, and was removed rather than kept as a second, unrelated
mechanism doing overlapping work.

**Six ticker data bugs**, all fixed via the existing targeted `_KNOWN_BAD_FACTS`
drop-list rather than any generic rule — 39 facts across 10 `(ticker, tag)` keys:

- **WAT** (partial): a units-mismatched share-count fact anchored
  `normalize_split_adjusted()`, which keys off `values.iloc[-1]`, rescaling the
  whole series by **50x**. Dropping the bad facts fixes the 50x error; a residual
  **2x** remains and was deliberately left, because it is a real merger-driven
  share issuance that the split-detection logic misreads as a split — fixing that
  would require reworking `normalize_split_adjusted()` generically, out of scope.
- **NTRS**: the same pattern on both share tags (3 facts each).
- **ANET / SCHW / ED**: `NetIncomeLoss` values reported in $-millions/thousands in
  **DEF 14A proxy statements**, which beat the 10-K because `extract_period_values`
  keeps the latest-filed fact per `(end, days)` key. Root cause diagnosed on ANET,
  then checked universe-wide before choosing a fix: **141 tickers have DEF 14A
  facts and only 3 are units-mismatched**, which is what justified a targeted
  15-fact drop-list over a blanket "ignore DEF 14A" rule.
- **ICE / SW / AMCR**: bad `StockholdersEquity` facts (14 total).

---

## 2026-07-30 — `build_valuation_history` used one current share count for all of history

`build_valuation_history()` computed `market_cap` from a single share count
applied across every historical period, so every historical valuation multiple was
priced with today's share count. Fixed to use each period's own `SharesOutstanding`,
falling back to the current count only for tickers with no historical share data at
all (`shares_outstanding_count > 0` deciding per ticker, not per row).

---

## 2026-07-30 — Quarterly values alongside TTM, and growth columns on every non-TTM concept

**Quarterly counterparts.** Every TTM-only concept hid single-quarter inflections
until they had worked through a trailing-twelve-month sum.
`add_quarterly_derived_concepts()` and `calculate_quarterly_metrics()` mirror the
existing TTM derivation chain exactly, built from the already-quarterly base
concepts instead of their `_TTM` versions. Purely additive: every concept added
carries a `_QUARTERLY` name and nothing touches or replaces a TTM concept.
`plot_metric_dual()` renders TTM and quarterly on one axis, wired via
`QUARTERLY_COUNTERPART`, and quarterly concepts inherit their TTM sibling's
visibility through `_DERIVED_CONCEPT_CONSUMERS` so a hidden metric cannot leak back
in through its new quarterly twin.

**Broad growth.** `add_growth_column()` / `growth_concepts()` attach a
`yoy_growth` column (`GROWTH_COLUMN`) to every non-TTM, non-derived concept in
`facts`, rather than the four hand-picked series that had growth before.
`GROWTH_MIN_BASE_RATIO_OVERRIDES` loosens the base-ratio guard to 0.05 for seven
genuinely lumpy balance-sheet concepts (`Capex`, `Goodwill`, `CashAndEquivalents`,
`Inventory`, `LongTermDebt`, `ProvisionForCreditLosses`, `TangibleEquity`) where the
default 0.33 would suppress real movement. Three universal panels
(`GROWTH_PANELS`) are rendered by `plot_growth()`.

---

## 2026-07-29 — Hidden-metric TTM leaks project-wide (facts.csv + snapshot columns), and a peg_ratio ordering bug that let a 13.6-million P/E through

Two-part task. Part A: a hidden ratio (e.g. `pe_ratio` for `reit`) doesn't stop its
raw/TTM inputs from being written out on their own. Part B: `peg_ratio` had no
guard and wasn't even wired into plotting.

**Part A.** Seven concepts exist only to feed a hidden-able ratio and are never
independently displayed: `EPS_TTM_CALC` (-> `pe_ratio`, and -- found only by
grepping every occurrence, not from the task's own example -- `payout_ratio`
too), `TangibleEquity` (-> `p_tbv`), `PPNR` (-> `p_ppnr`), `CoreOperatingEarnings`
(-> `p_core_earnings`), `FFO_TTM` (-> `p_ffo`, `ffo_margin`), `FCF_TTM` (->
`pfcf_ratio`, `fcf_margin`), `EBITDA_TTM` (-> `ev_ebitda`, `net_debt_to_ebitda`).
Two leak sites, found by enumerating every concept/column name in every output
and cross-checking against the full union of `PROFILE_HIDDEN` keys rather than
assuming only the named REIT/pe_ratio case existed:

1. `data/{period}_facts.csv` was written with **no profile filtering at all** --
   `metrics_long`/`valuation_history` already went through `filter_hidden_rows()`
   before their own `.to_csv()`, but `facts` itself never did.
2. `build_snapshot()`'s `apply_profile_filter()` already loops every column
   through `is_hidden()` -- the mechanism was there -- but several of its own
   column names don't match the canonical ones: `pe_ttm` (alias of `pe_ratio`)
   was hidden in **zero** profiles; `pfcf_ttm` (alias of `pfcf_ratio`) was
   already hand-added to 3 profiles' hidden sets but missing `reit` and
   `utilities`, where `pfcf_ratio` is *also* hidden -- concrete evidence that
   hand-duplicating a ratio's name into `PROFILE_HIDDEN` drifts out of sync,
   the same failure mode the `p_ffo` audit found earlier in this project.

The fix couldn't just add more literal names (that's the pattern that already
drifted once) or blanket-hide a concept whenever *any* one of its consumers is
hidden (utilities hides `pfcf_ratio` but not `fcf_margin`, so the raw `FCF_TTM`
figure must stay visible there even though the `pfcf_ttm` *alias* of
`pfcf_ratio` must not; retail has the same asymmetry between `ev_ebitda` and
`net_debt_to_ebitda`). Extended `is_hidden()` with a `_DERIVED_CONCEPT_CONSUMERS`
map (each concept -> every metric that actually consumes it, verified by grep)
and a concept is hidden only when **all** its consumers are hidden. This fixed
`apply_profile_filter()` for free (zero changes needed there) and needed exactly
one added line, `facts = filter_hidden_rows(facts)`, before `facts.to_csv()`.

Non-regression across all 499 cached tickers: **59,047 rows removed, every one
from the 7 named concepts, 0 from anything else**; `metrics_long` byte-identical
under old vs. new `is_hidden()`. `PPNR`/`CoreOperatingEarnings` showed exactly 0
rows removed -- not a fix gap, confirmed: their own source data only ever
populates in the profiles where those two ratios are already visible, so there
was nothing to leak in the cached data to begin with.

**Part B.** Characterizing `peg_ratio` against real data (24,312 valid pairs
across all 499 tickers) found the sign-flip case the task hypothesized -- 5,306
negative values, **100% from negative revenue growth, 0% from negative pe_ratio**
(which is already structurally non-negative in `build_valuation_history`) -- and
found something the task didn't hypothesize: an **ordering bug**. `peg_ratio` was
computed from `pe_ratio` *before* the existing `MAX_MULTIPLE=200` exclusion ran on
it, so `pe_ratio`'s own safeguard never protected `peg_ratio` at all. Traced to
its root cause: `ANET`'s trailing-twelve-month net income at 2021-12-31 summed to
**$841** (three profitable quarters of ~$180-224M nearly exactly offset by a
-$601.6M one-time charge) -- technically positive, so `pe_ratio_raw` came out to
**13,635,224**. `ED`, `SCHW`, `WAT` and others showed the identical pattern at
other dates (375 rows had `pe_ratio_raw > 200` project-wide). Fixed by moving the
`pe_ratio` exclusion before `peg_ratio`'s computation -- reusing the existing
safeguard instead of adding a parallel one -- which alone drops `ANET`'s worst
reading from 13.6 million to 4.28.

On top of that: a growth floor of 2% (independently re-derived from `peg_ratio`'s
own distribution -- collateral cost stays low, 58 of 11,383 otherwise-plausible
readings, up to the 2% mark before rising sharply at 3%+ -- it just happens to
numerically match `MIN_OPERATING_LEVERAGE_REVENUE_GROWTH`) plus a final cap of 30
(99.5th percentile of the post-floor distribution is ~22, cap removes only 37 of
17,089, 0.22%). A **second, separate gap** was found in `build_snapshot()`'s own
independent `peg_ratio` computation: unlike `build_valuation_history`'s
`pe_ratio`, `snap["pe_ttm"]` has no positivity guard upstream, so a negative
trailing EPS survived the growth-only guard untouched (verified with a synthetic
case: `pe_ttm=-15`, `growth=10%` produced `peg=-1.5`, unmasked). Fixed by requiring
`pe_ttm > 0` explicitly in that path too.

Non-regression: all 10 other valuation ratios (`pe_ratio` through `p_ffo`) are
byte-identical old vs. new; `peg_ratio` itself masks 7,598 of 24,650 rows and
changes **0** of the rows that survive in both. Added `peg_ratio` to
`plot_valuation()`'s `concepts_to_plot` (it was computed but never wired into any
chart) and confirmed it renders against real `AAPL` data. Full detail in
`hidden_ttm_leak_and_peg_guard_report.md`.

---

## 2026-07-29 — MS/SOFI/UNH reassignment verified: SOFI had a real SPAC-merger scope break producing equity_to_assets = -815.7 and roa = -28%

Verified the `standard` -> `financial`/`health_services` reassignment for MS, SOFI,
UNH with a real coverage check and metric spot-check, not just the tag-signature
match that justified the reassignment itself.

**MS: clean.** Two small negative-metric quarters (net_interest_margin at
2012-Q3/Q4, provision_ratio in 7 quarters across 2014-2021) were checked rather
than assumed benign — both are real, smooth, small (a temporary funding-cost
quarter; loan-loss reserve releases in good credit years), not scale/tag defects.

**UNH: the reassignment's own premise didn't hold up.** Diffing
`PROFILE_HIDDEN["standard"]` against `PROFILE_HIDDEN["health_services"]` directly
in `config.py` (not from memory) shows `health_services`'s hidden set is a
**strict superset** of `standard`'s -- moving UNH reveals **zero** newly-visible
metrics. The only effect is that `rule_of_40` becomes newly **hidden**. The
reassignment is still correct (it changes concept *resolution*, not metric
visibility -- health_services applies its own Capex/R&D overrides), just not for
the reason it was framed around.

**SOFI: a real, previously-undetected SPAC-merger scope break.** SoFi went public
via SPAC merger (June 2021); its CIK is the former SPAC shell
(Social Capital Hedosophia Holdings Corp V). `Assets` at 2020-09-30 resolved to
**$466,179** and at 2021-03-31 to **$805,817,385** -- the SPAC's own trust-account
assets, not SoFi's real balance sheet (~$7-8B at neighboring dates). Confirmed via
same-CIK filing history: `StockholdersEquity` already resolves correctly at every
date because a post-merger restatement was filed for every StockholdersEquity
end-date, but **no restated Assets value was ever filed for these two specific
interim quarters** -- 10-Qs only restate the current quarter-end and prior fiscal
year-end. A permanent SEC-record gap, not a resolution-order bug. Left unmasked,
this produced `equity_to_assets = -815.7` at 2020-09-30 and `roa = -28.0%` at
2021-03-31. Fixed via the existing `_KNOWN_SCOPE_MISMATCH_OUTLIERS` mechanism
(the same one already used for Ford's LongTermDebt) -- masking, not substitution,
since no correct value exists anywhere in the filing history for these dates.

Also fixed: `ProvisionForCreditLosses` coverage was 7.1% (2 of 28 quarters) because
SoFi tags its provision as `FinancingReceivableExcludingAccruedInterestCreditLossExpenseReversal`,
not any of the base `financial` profile's three candidate tags. Verified before
trusting it: the one date where both the old and new tag report a value
(2022-03-31) match **exactly** ($12,961,000) -- confirming same concept, different
tag name, not a coincidence. Appended via `TICKER_CONCEPT_OVERRIDES["SOFI"]`,
scoped to SOFI only since this tag name is not expected to generalize to MS, GS, or
any other `financial` ticker. Coverage rose 7.1% -> 71.4%.

**Verdict: SOFI is a clean fit for `financial`, not a partial one** -- the initial
concern (fintech/neobank vs. traditional bank) does not survive the coverage check
once the tag gap is fixed. `DividendsPerShare` at 32.1% is not a fit problem: no
per-share tag beyond two that report $0.0 in all 9 resolved quarters, and the only
cash-dividend tag present is preferred-stock-specific. SoFi has never paid a common
dividend -- the standard non-payer exception, verified directly rather than assumed.

Non-regression, task scope (MS/SOFI/UNH): 0 changed for MS and UNH; SOFI shows
exactly 2 disappeared (masked Assets) + 18 new (ProvisionForCreditLosses) and
nothing else. Full-universe diff also caught an **unrelated, out-of-scope
change**: `CVNA` has been commented out of `TICKER_PROFILES`
(`#"CVNA": "retail", doesnt work`) by an edit external to this task, so it now
falls back to `standard` and its retail-specific concepts (AccountsPayable,
AccountsReceivable, Inventory, CostOfRevenue -- 150 values) stopped resolving,
with 5 LongTermDebt values changing under the new profile path. Not reverted --
out of scope for this task -- but noted here since the mandatory full-universe
diff would otherwise look like an unexplained regression. Full detail in
`ms_sofi_unh_reassignment_verification_report.md`.

---

## 2026-07-29 — Retroactive scan of the 58 reconciliation tickers: TROW's D&A was wrong by 150-250x, and coverage% could not see it

The reconciliation task added 58 tickers on a quick resolution probe. This pass
applied the full per-batch discipline to all of them, grouped by profile. **3 of 58
needed a real fix**; the rest were confirmed structural, confirmed non-payers, or
logged ambiguous.

**The lesson worth keeping: a coverage percentage is blind to a concept that
resolves to the *wrong tag*.** TROW's `DepreciationAndAmortization` showed as a mild
"36%" — but the values it *did* produce were **$100,000-$200,000 per quarter when
actual depreciation was $15.3M-$25.1M**, off by 150-250x. Root cause: T. Rowe tags
depreciation as `DepreciationNonproduction`, which is not in the base D&A list, so
the priority list fell through to `AmortizationOfIntangibleAssets` — a trivial line
for this company. Confirmed by same-date identity: where
`DepreciationDepletionAndAmortization` does resolve (2021 Q1-Q3) it equals
`DepreciationNonproduction` **exactly** ($49.0M / $50.4M / $51.7M).

Because of that, a **plausibility sweep** was added to the method: median D&A and
median Capex against median Revenue across the whole batch. It flagged 4 tickers.
Three were fine on inspection (COIN and APP are genuinely asset-light; VICI's Capex
is excluded by the `reit` profile anyway) and one was a real defect — **CVNA's D&A
at 0.18% of revenue**, resolving to intangible amortization. Unlike TROW, Carvana
files **no depreciation flow tag at all**, so there is nothing to substitute.
Escalated as needing a decision rather than left as a silent gap.

Other two fixes: **FIS** `Revenue` 49%->95% (pre-ASC-606 `SalesRevenueServicesNet`
missing; verified by reconstructing FY2009 $3.735B / FY2019 $10.333B / FY2020
$12.553B against reported figures, with a continuous seam). **ERIE** `Capex`
49%->94% (tag switch in 2018; the two tags agree **to the dollar** on all three
overlapping quarters).

**Eight candidate fixes were rejected on evidence** — this was most of the work:

- **AMP** `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` is
  **2.14-2.39x** larger than the carrying-value tag on overlapping dates. Splicing
  would fabricate a 2.2x jump. Notable because the *same* fix was correctly applied
  to **CAT** in the captive-finance batch — there the ratio is **exactly 1.00 across
  20 overlapping dates**. Same tag, opposite verdict, decided by data.
- **AJG/AMP** `CostsAndExpenses` as a route to operating income: for AJG,
  `Revenue - CostsAndExpenses` equals reported **pretax** income with a **$0
  difference in 45 of 46 periods** — it includes interest expense.
- **RJF** `NoninterestIncomeOtherOperatingIncome` is ~**1%** of the real
  `NoninterestIncome` ($18M vs $1,688M) — the TROW failure mode exactly.
- **RJF/IBKR** `RevenuesNetOfInterestExpense` — different aggregate, ~12% high.
- **ARE** `GainLossOnSaleOfPropertiesNetOfApplicableIncomeTaxes` had *zero* overlap
  with the resolving tag, so it looked like a free 40%->68% win — but its range is
  $0-$1.86M against the gross tag's -$435k-$619.9M (~300x mismatch); it is the
  taxable-REIT-subsidiary slice. Logged ambiguous, not taken.
- **CI** `PaymentsForProceedsFromProductiveAssets` — exact duplicate, adds 0 periods.
- **CVNA** `FinanceLeaseRightOfUseAssetAmortization` — a lease component, not D&A.
- **FISV** `AmortizationOfAcquiredIntangibleAssets` — would extend coverage while
  propagating a known understatement (amortization is only 62-79% of true D&A).

**Two findings worth remembering beyond this batch.** First, `OperatingIncomeLoss`
is genuinely absent for **AJG, BRO, AMP and CTVA** — insurance brokers and Corteva
do not report an operating-income subtotal at all, so this is not the
diversified-conglomerate tag fragility seen elsewhere. Second, a 0%
`DividendsPerShare` is **not** always the non-payer exception: **ERIE** and **VRT**
both pay real dividends (ERIE up to $272.9M) but file no per-share tag, and for
ERIE it cannot even be derived because `SharesOutstanding` is absent too. 13 of the
batch *were* verified as genuine non-payers.

Before accepting any "structurally absent" verdict, the cached facts were checked
for company-extension taxonomies — only standard namespaces exist (`us-gaap`, `dei`,
`srt`, `invest`, `ffd`) and none carries the missing concepts.

Non-regression, all 499 cached tickers: **21 changed (all TROW, all corrections),
0 disappeared, 91 new** (FIS 34, ERIE 30, TROW 27). Only 3 tickers appear in the
diff. All three fixes went through `TICKER_CONCEPT_OVERRIDES`, which cannot reach
another ticker — so cross-group contamination is structurally impossible as well as
empirically confirmed (Groups 2-11 each returned 0/0/0). Full detail in
`retroactive_new_ticker_scan_report.md`.

---

## 2026-07-28 — Ticker universe reconciliation: 79 implicit `standard` assignments made explicit, 58 missing S&P 500 members added, 13 left unassigned on purpose

Not a bugfix — a coverage/bookkeeping pass — but it surfaced enough that is worth
recording, and the non-regression discipline was the same as every batch scan.

**Part A.** 441 cached tickers, 358 assigned, so **85 were resolving to
`DEFAULT_PROFILE` by fallback** with no way to tell "deliberately standard" from
"never assigned". 79 were made explicit. The interesting part is the **six that
were not**, each caught by checking the tag signature rather than the name:

- **MS** carries all 7 bank tags checked — *the identical set to GS*, already
  `financial`. A bank sitting unassigned.
- **SOFI** carries 4 of 7 including `Deposits`.
- **UNH** carries `PremiumsEarnedNet` / `PolicyholderBenefitsAndClaimsIncurredNet`
  / `LiabilityForFuturePolicyBenefits` — the same signature CVS has post-Aetna.
- **APA / NVR / PHM** were already deliberately commented out of `energy` and
  `homebuilder`. Writing `"APA": "standard"` would have *erased* that signal.
  (APA's config comment "HAS NO REVENUE" was confirmed against the data: it has
  neither `Revenues` nor `RevenueFromContractWithCustomerExcludingAssessedTax`.)

Part A non-regression was **provably inert**: 331,856 values before, 331,856
after, 0 changed / 0 disappeared / 0 new. The default-fallback path and the
explicit-assignment path are confirmed identical.

**Part B — two methodology lessons worth keeping.**

*Don't let a summariser produce a reference list.* The first attempt to read the
S&P 500 constituents through a summarising fetch **truncated mid-alphabet at
`MET`** and mixed real symbols with invented ones. Parsing the raw wikitext
directly gave 503 rows / 503 unique symbols with per-sector counts summing exactly
to 503. Everything downstream depended on that list being right.

*Cross-check symbols against SEC's own map before believing a gap.* All 67
candidate-missing symbols were validated against the cached
`company_tickers.json`. All 67 resolved — including several that looked like
errors but are real recent renames (`MRSH`←MMC, `XYZ`←SQ) or 2026 spinoffs
(`HONA`, `FDXF`). More importantly it caught the reverse case: **`ECHO` resolves
to CIK 1415404, which is already cached as `SATS`** — a rename, not a gap. Adding
it would have double-cached one registrant under two symbols. Real gap: **66, not
67.** The same check proved `SATS` is *not* index drift, unlike CAG/CPB/POOL/CE
which genuinely left the index in June 2026.

**58 assigned, 8 left unassigned.** Assignment was decided by building the
dataframe under each *candidate* profile and counting what actually populates, not
by GICS label. Three calls worth recording:

- **Healthcare distributors (CAH, COR, MCK, HSIC) → `retail`**, not
  `health_services`. They run on ~1% operating margins where the business *is*
  working capital, and `retail` is the only profile that keeps
  `dio`/`dpo`/`dso`/`cash_conversion_cycle`/`inventory_turnover` visible —
  `health_services` hides all five. All four resolve 15/15 under `retail`.
- **HOOD → `financial` even though `standard` scored higher** (9/13 vs 10/12).
  `standard` would actively show leverage metrics off a broker balance sheet
  dominated by customer payables; `financial` merely leaves `efficiency_ratio` and
  `provision_ratio` blank. **A blank metric beats a misleading one.**
- **SNA → `industrials`, not `captive_finance`**, despite Snap-on Credit: it
  resolves identically (11/12) under all three candidates and `LongTermDebt`
  resolves cleanly, which is the quirk `captive_finance` exists for. Same
  reasoning kept **TSLA** out of `captive_finance` — no finance-company balance
  sheet on the scale of GM Financial / Ford Credit.

**The 8 left unassigned are the actual finding** — they map the categories the
project still lacks. `BX`/`KKR`/`APO`/`ARES` were flagged on hard data: quarterly
revenue swings of **538× / 30× / 16× / 124×** against 1.5–5× for genuine fee
businesses (BLK, CME, AON, AMP, SPGI, TROW), because reported revenue includes
performance allocations and consolidated-fund results — and KKR/APO additionally
consolidate life insurers (Global Atlantic, Athene). `BRK-B` fits nothing (best is
`standard` at 10/12, missing `LongTermDebt` for a company carrying ~$120B of it).
`MRNA` → the in-construction `biotech` profile; `INCY` was tested against the same
bar and *does* fit `pharma_medtech`. `HONA`/`FDXF` have **0 us-gaap tags** — valid
but empty companyfacts documents, nothing to profile yet.

Part B non-regression: **0 changed, 0 disappeared**, 39,023 new values landing on
exactly the 58 new tickers and none on a previously-cached one. `TICKER_PROFILES`
was additionally parsed with `ast` to confirm **no duplicate keys** (495 literal,
495 unique) — a silent override would have been invisible to a value diff whenever
the two entries happened to agree.

Universe went 441→499 cached, 358→495 assigned, 437→490 of 503 index members
covered. Full detail in `ticker_universe_reconciliation_report.md`.

---

## 2026-07-28 — Airline batch scan (DAL, UAL + LUV): the "ASC 842" premise didn't hold up, real cause was COVID-era debt issuance; rule_of_40 hidden profile-wide

Fifteenth stock-type profile batch. `airline` runs entirely on the base tag set (no profile or
ticker overrides existed or were needed). The task's own stated premise for the reference ticker's
`debt_to_equity` jump was checked against real data before being extended to DAL/UAL — **and it
didn't hold, for any of the three tickers, including LUV itself.**

### The ASC 842 explanation was wrong

LUV's `debt_to_equity` does jump (0.19 → 0.82 → 1.14 across 2019-Q4 to 2020-Q4), but two things rule
out "operating lease liabilities coming onto the balance sheet" as the cause: (1)
`OperatingLeaseLiability*` tags aren't part of the `LongTermDebt` candidate list in this pipeline at
all, and were flat-to-declining across the window regardless ($978M → $936M → $1.49B); (2) the
timing is wrong for ASC 842 — that standard took effect 2019-01-01, but LUV's own ratio was *lower*
at 2019-12-31 than at 2018-12-31, with the entire jump concentrated in a single quarter, **Q2 2020**.
The actual driver is `LongTermDebtAndCapitalLeaseObligations` itself jumping $2.29B → $8.91B in that
one quarter — Southwest's real COVID-era convertible-notes offering and credit-facility drawdowns.
DAL and UAL show the identical mechanism (flat lease-liability tags, real debt tags jumping in 2020,
DAL peaking Q2-Q3 and UAL concentrated in Q3 consistent with CARES Act PSP loan timing) — a real,
correctly-resolved, industry-wide COVID financing event, not an accounting-standard scope break.

### Other findings

No loyalty-program revenue/income scope-break signature for DAL or UAL — expected, since DAL's
SkyMiles-collateralized bonds and UAL's MileagePlus-collateralized term loan were both debt-side
financings (part of the same 2020 debt increase above), not revenue transactions. `OperatingIncomeLoss`
fragility checked independently despite DAL/UAL's more complex segment structures: all three clean
(95-99%). DAL's near-zero-but-positive equity in 2021-Q1/Q2 ($482M/$1.28B against ~$26-28B debt)
correctly triggered the `MIN_DEBT_TO_EQUITY_SCALE_RATIO` guard (ratio ~1.9%, below the 5% floor),
masking what would otherwise be a meaningless 50x+ ratio — confirmed working as intended under real
COVID-scale stress. A genuine, isolated scope break found: DAL `NetIncomeLoss` 2017-12-31 restated
$572M → $299M (91%), with `Revenue`/`OperatingIncomeLoss` unchanged — matches the industry-wide TCJA
Dec-2017 SAB 118 deferred-tax remeasurement finalization, already correctly resolved by "later filed
wins." An unfiltered first pass at this scan produced dozens of false NetIncomeLoss "restatement"
hits that were actually YTD-cumulative vs. discrete facts sharing an end date — discarded once
correctly restricted to true quarterly-length (80-100 day) facts. LUV's negative-FCF condition
(2022-Q4 to present, tied to 737 MAX delays and LUV's 2025 operating changes) is confirmed
**LUV-specific**, not shared: DAL and UAL both had a real COVID-era negative-FCF stretch that has
since fully recovered to strongly positive FCF. `rule_of_40` hidden profile-wide: all three tickers
share the identical above-40% pattern — a 2021-Q4 to 2023 cluster (up to ~178%) driven by
revenue_growth measured off the COVID-collapsed base, against single-digit-to-low-teens medians.

Non-regression across all 441 cached tickers: **0 previously-populated values changed**, 0
disappeared, 1,516 new values (all in DAL/UAL, brand-new tickers), LUV's own values byte-identical
before and after.

---

## 2026-07-28 — Captive-finance batch scan (GM, CAT, PCAR, TXT + F): Ford's debt override was never actually applied, three distinct debt-tag patterns found, CAT cash gap fixed

Fourteenth stock-type profile batch. The premise to check was whether the four new tickers share
Ford's post-2018 consolidated-debt breakdown. **They do not** — three genuinely different patterns
emerged, and only one of the four needed any change.

### Two corrections to the reference ticker's own state

The brief described F's `LongTermDebt` override as already applied. It was **not in `config.py`** —
F was resolving through the base list, which produced only three values ($600M/$470M/$291M) for a
company carrying $100-155B, because `DebtAndCapitalLeaseObligations` is not a member of the base
list. Second, applying the override exactly as specified does **not** produce the described "honest
gap from 2018": the tag keeps being filed after its scope narrows, so it yields the real 2008-2017
series *plus* three implausibly small values. Those three periods were masked explicitly via
`_KNOWN_SCOPE_MISMATCH_OUTLIERS[("F","LongTermDebt")]` — the mechanism already used for this exact
"same tag, silently changed scope" class. F now has 36 clean points, $95.1B-$154.3B, 2008-2017.

### Three debt-tag patterns

- **Pattern A (F only)** — tag exists but changes scope mid-series; use it, mask the broken periods.
- **Pattern B (GM, CAT)** — clean consolidated tag throughout, **no override added**. GM resolves via
  `LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities` ($47.5B→$131.8B, 2014-2025); CAT
  resolves via the base list's `require`-guarded sum on `LongTermDebtNoncurrent` ($20.4B-$30.7B,
  2008-2025) — a direct benefit of the previous task's `require` fix. Both annual-only (23%), which
  is a filing-cadence limitation, not a tagging bug.
- **Pattern C (PCAR, TXT)** — a pattern the brief did not anticipate: **no consolidated debt balance
  tag exists at all** in us-gaap, only flow and disclosure items. PCAR's `NotesPayable` ($0.19B vs
  PACCAR Financial's ~$10B+ book, ~2% of true scale) was **rejected on scale-sanity grounds** rather
  than used — the `OtherNotesPayable`/O trap exactly. TXT's maturity-ladder tags would require
  reconstructing debt rather than reading it. Both left as honest 0% gaps.

### Other findings

`CAT` `CashAndEquivalents` 38% → 63%, by adding `CashCashEquivalentsRestrictedCashAndRestrictedCash
Equivalents` as a last-resort fallback — scale-verified first: across all 20 overlapping dates the
two tags differ by 0.03%-0.23%, so CAT's restricted cash is immaterial. `OperatingIncomeLoss` splits
three ways (GM 97% and CAT 91% clean; F's 42% is a start-date limitation, not corruption; PCAR has
**no such tag at all** and TXT tags it twice) — the nearby
`IncomeLossFromContinuingOperationsBeforeIncomeTaxes*` was rejected because pre-tax income sits after
interest expense, which is a large operating input for a finance arm. GM's 2009 bankruptcy needs no
guard or scope-break handling: "New GM" is a separate registrant, so the series begins cleanly at the
new entity rather than jumping a mid-series break. Ford's payout-ratio spike is **real and
arithmetically correct** — 5,111% at 2019-12-31 (not 2020), from $0.60 DPS held flat against FY2019
EPS of $0.0117 after a large pension remeasurement charge; 2020 correctly reads NaN via the existing
`require_positive_denominator` guard. GM's 2017 Opel/Vauxhall and CAT's 2015 reclassification
restatements are already resolved correctly by "later filed wins". `rule_of_40` hidden profile-wide:
only 9 of 304 quarters clear 40%, all in two cyclical rebound windows (CAT/PCAR 2011-12, GM 2021).

Non-regression across all 438 cached tickers: **0 previously-populated values changed**, 55 appeared
(CAT cash 19, F debt 36), 3 disappeared (exactly the intentionally-masked Ford values), 436 of 438
tickers completely untouched.

---

## 2026-07-28 — Base `LongTermDebt` priority fix: current-portion contamination corrected across 58 tickers, negative-value guard added

Implements the fix for the exposure scoped in the previous entry. **The literal plan ("move the
three vulnerable sources to the end of the priority list") was tested against real data first and
rejected — it caused regressions on ~30 tickers.** The three sources are not equivalent.

### Why the blanket reorder was wrong

Demoting all three below the combined-debt tags changed 782 values across 73 tickers, but **35 of
those tickers had values go DOWN** — which a fix that only promotes complete-debt tags should never
do. Root cause: the `sum(LongTermDebtNoncurrent, LongTermDebtCurrent, NotesPayableCurrent)` source
is only broken when `LongTermDebtNoncurrent` is *absent*. When it is present the sum equals
noncurrent + current maturities = total debt, which is **more** complete than
`LongTermDebtAndCapitalLeaseObligations` (noncurrent-only). Demoting it therefore understated debt
for CARR, ALB, AVGO, XOM and ~30 others. The two `Convertible*Current` tags are different — they are
current-portion-only in every period, so demoting *those* is unambiguously right.

### What shipped instead

1. `ConvertibleDebtCurrent` and `ConvertibleNotesPayableCurrent` moved to the literal end of the list
   (this is the mechanism that hit BKNG).
2. The sum **kept its original priority** but gained a new opt-in `"require"` key naming its principal
   component: it now only contributes for periods where `LongTermDebtNoncurrent` actually has data,
   so degraded periods fall through to the combined-debt tags instead of being claimed by a partial
   sum. Implemented in `extract_priority_merge`; affects no other concept.

Non-zero decreases went from ~30 tickers to **zero**.

**Second defect found along the way:** the old sum also **double-counted** when a filer tagged the
same amount under two component tags — OMC 2015-06-30 had `LongTermDebtCurrent` and
`NotesPayableCurrent` both at 1,005,100,000, summed to 2,010,200,000 (~2.8x its real debt).

### Negative-value guard

Traced to raw facts first: the negatives are **filer sign errors in the source XBRL**, not a
pipeline subtraction. DD and NSC are negative on the *top-priority* tag (outside the positions the
original scan examined), with a correctly-signed value at the same date and near-identical magnitude
(DD: −12,635,000,000 vs +12,624,000,000). So the guard skips negative readings **per source during
the merge** (opt-in `"non_negative": True` on the concept) rather than masking the final value —
recovering 8 of 9 negatives from a real same-date tag instead of discarding them. FE, GNRC, DD, NSC
all corrected; only **ETR** is masked, because every one of its sources is negative at that date and
there is nothing valid to promote. A narrow post-resolution `_mask_negative_balance_values` net was
added as defence-in-depth, kept separate from the flow-concept guard (balance levels are invalid
negative in either period mode) — its concept set must stay narrow, since `StockholdersEquity` *is*
legitimately negative for real companies.

### Impact

424 values corrected upward across 41 tickers; 124 contaminated values masked; **0 non-zero
decreases, 0 values invented, 0 negatives remaining** across all 436 cached tickers. 58 tickers
affected, 378 completely untouched. Derived metrics (`debt_to_equity`, `net_debt`,
`net_debt_to_ebitda`) changed for zero tickers beyond those whose `LongTermDebt` changed. The
103-ticker flagged list was regenerated from scratch and reproduced exactly; 54 changed, 49 were
unchanged as predicted. Four tickers changed from *outside* the flagged list (BALL, NSC, INTU, RMD) —
each investigated and confirmed a correct outcome, showing the original scan **undercounted**: its
neighbour-ratio heuristic is blind when consecutive quarters are both contaminated (BALL) or when the
bad value is close in scale to its neighbours (INTU, RMD).

---

## 2026-07-28 — p_ffo hidden project-wide (18 profiles) + LongTermDebtCurrent base-list exposure scoped to 103 tickers (diagnosis only)

Follow-up to the marketplace scan's two flagged findings.

**Part A, fixed:** `p_ffo` was only hidden for `standard` and `marketplace` in `PROFILE_HIDDEN`,
while `ffo_margin` was correctly hidden everywhere non-`reit`. Re-grepping found the real count
was 18 profiles missing it, not 17 as the marketplace report said — that report's own scan missed
`insurance_pc`/`insurance_life` because they're declared as `"insurance_pc":{` (no space), which
didn't match the grep pattern used at the time. Added `p_ffo` to all 18. Non-regression: verified
via a reconstructed before/after diff (stripping `p_ffo` from every profile and comparing) that
zero other metrics changed visibility anywhere.

**Part B, diagnosis only, no fix:** Scanned all 365 cached tickers that resolve `LongTermDebt` via
the base `CONCEPT_CANDIDATES` list (i.e. excluding the 5 profiles and 9 tickers that already
override it) for the same signature that caused BKNG's bug — a current-portion-only source
(`ConvertibleDebtCurrent`, `ConvertibleNotesPayableCurrent`, or the `LongTermDebtNoncurrent`+
`LongTermDebtCurrent`+`NotesPayableCurrent` sum) winning a period with an implausibly small value.
**103 tickers across 14 profiles hit it at least once** (374 quarter-level hits total). For 37 of
those, direct same-date proof exists: a much larger value sits at a lower-priority tag
(`LongTermDebtAndCapitalLeaseObligations` or similar) for the exact same quarter, unused — the
same smoking-gun pattern as BKNG, just automatically confirmable rather than needing a manual
raw-fact pull. 3 more (`ATO`, `ETR`, `EXC`) show the same isolated-stark-dip-with-consistent-
neighbors pattern without an available shadow tag. Also surfaced a distinct, more severe variant:
`FE`, `GNRC`, and `ETR` show structurally impossible **negative** resolved debt values at the
contaminated quarters, not just undersized ones. The remaining 63 tickers are genuinely ambiguous
(could be real temporary paydowns before refinancing) and need individual review. No code or
config changed for Part B — scope-only, matching the discipline used for the `SharesOutstanding`
scale bug and the decumulation scope-mismatch bugs before any project-wide fix was attempted.

---

## 2026-07-28 — Marketplace tag coverage scan (4 tickers): BKNG LongTermDebt current-portion contamination, ABNB DepreciationAndAmortization tag gap, base LongTermDebtCurrent exposure flagged project-wide

Thirteenth stock-type profile batch, EBAY + BKNG/EXPE/DASH/ABNB. EBAY's own prior fixes
(`LongTermDebt` current-portion contamination, `DividendsPerShare` hide) were actively
re-verified against each new ticker rather than assumed inherited from the profile config.

### BKNG: LongTermDebt current-portion contamination (single quarter)

Same failure class as EBAY's original fix, reached through a different tag. At 2020-12-31, BKNG's
plain `LongTermDebt` tag has a one-quarter gap; `ConvertibleDebtCurrent` (data only at 2019-12-31
and 2020-12-31) sits ahead of the `LongTermDebtNoncurrent`+`LongTermDebtCurrent` sum in the base
`priority_merge` chain and claims the period with just its own $985M current-portion value, vs.
flanking quarters of $10.8B/$13.8B. Raw facts confirmed the true total ($12.014B = $11.029B
noncurrent + $985M current) sitting one priority position lower, unused. Fixed via a `BKNG`
`TICKER_CONCEPT_OVERRIDES` entry dropping `ConvertibleDebtCurrent`/`NotesPayableCurrent` and
keeping direct tag → noncurrent+current sum. Every other of BKNG's 48 quarters unchanged.

### ABNB: DepreciationAndAmortization — 0% coverage, wrong tag family entirely

None of the base D&A tags (`DepreciationDepletionAndAmortization`, `Depreciation`,
`AmortizationOfIntangibleAssets`, etc.) have any quarterly-length facts for ABNB — only annual,
and only through FY2022. The real quarterly data lives under `OtherDepreciationAndAmortization`
(YTD-cumulative, decumulates cleanly), covering 2020-Q1 through 2025-Q1. Added as a fallback via
`TICKER_CONCEPT_OVERRIDES`: 0% → 78% coverage. 2025-Q2 onward remains a genuine gap — ABNB appears
to have stopped breaking out this cash-flow line at all in recent 10-Qs; left unfixed.

### Project-wide finding, reported not fixed: base LongTermDebt list includes LongTermDebtCurrent

The base `CONCEPT_CANDIDATES["LongTermDebt"]` `priority_merge` chain includes a
`{"type": "sum", "tags": ["LongTermDebtNoncurrent", "LongTermDebtCurrent", "NotesPayableCurrent"]}`
source at priority position 8 — meaning any ticker on the base (non-overridden) list can suffer
the same one-quarter current-portion contamination BKNG just had, wherever its own higher-priority
tags have a gap. Confirmed in scope only, not fixed project-wide — flagged for a dedicated
follow-up task since it could affect already-shipped tickers in other profiles.

### Other findings (investigated, no fix needed or out of scope)

`p_ffo` missing from `PROFILE_HIDDEN` in 17 of 19 non-REIT profiles (only `standard` and
`marketplace` include it, unlike `ffo_margin` which is correctly hidden everywhere) — pre-existing,
flagged for follow-up. `dividend_yield`/`payout_ratio` are not actually present in `PROFILE_HIDDEN`
for any profile; their hidden appearance for non-payers is a data-driven `NaN` fallout, not a
config decision. EXPE has a clean, fully working dividend-per-share tag (unlike EBAY) — noted as a
stronger future candidate if the hide decision is ever reconsidered per-ticker. EXPE's 2010-2011
`OperatingIncomeLoss` restatements (real TripAdvisor spinoff, Dec 2011) are already correctly
resolved by the existing "later filed wins" rule, no fix needed. ABNB's `Capex` tag stops entirely
after 2023-Q3 (real disclosure change, affects `fcf`/`fcf_margin`/`rule_of_40` coverage from then
on) and its `Goodwill` tag goes annual-only starting FY2023 — both logged as real, unfixable gaps.
`rule_of_40` computed across full history for all 5 tickers: BKNG (84% of quarters above 40%),
DASH (89%), and ABNB (100% of its valid quarters) all show sustained above-40% readings, so
`rule_of_40` was left visible for the `marketplace` profile rather than hidden.

Full non-regression across all 436 cached tickers (432 pre-existing + 4 new): zero errors, zero
change to any pre-existing ticker (both new overrides are additive dict entries under previously
unused keys), EBAY's own prior fix reconfirmed unchanged.

---

## 2026-07-27 — REIT tag coverage scan (27 tickers): Revenue lease/contract-revenue split (11 tickers), LongTermDebt tag drift (7 tickers), 5 more decumulation "implausibly-small-Q4" cases

Twelfth stock-type profile batch, O + 26 new. Ticker list verified against XLRE's live holdings
(which track the S&P 500 Real Estate sector exactly) — WPC, NNN, and CUBE confirmed as S&P
MidCap 400, not S&P 500, and dropped. Three independent, previously-uncataloged bug classes found
and fixed, none named in the task brief.

### Revenue: lease income vs. contract-with-customer income (11 tickers)

`RevenueFromContractWithCustomerExcludingAssessedTax` (first in the base `Revenue` fallback list)
is structurally the wrong first choice for real estate: rental income is **lease** revenue under
ASC 842, not **contract-with-customer** revenue under ASC 606. For any REIT that separately tags a
small non-lease revenue stream under this element, the fallback silently locked onto that tiny
sliver instead of the correct, much larger total (`Revenues`) — confirmed for **EXR, AMT, CCI,
SBAC, AVB, ESS, INVH, UDR, DOC** (ratios of the correct-to-wrong value ranged 3.8x to 540x; AVB's
own case: RCWC showed $7.7M vs. real $3.04B FY2025 revenue). Reordered `PROFILE_CONCEPT_OVERRIDES
["reit"]["Revenue"]` to put `Revenues` first — a profile-wide fix since the ASC 842/606 distinction
is a real-estate-sector-wide accounting fact, not a filer-specific quirk.

**CPT (Camden Property Trust)** hit an even stealthier variant: CPT's own `Revenues` tag doesn't
exist at all, so the RCWC-first bug wasn't visible to the RCWC-vs-Revenues comparison method used
for the other 9 (nothing to compare against). CPT's own RCWC tag was itself retroactively restated
from real values (FY2018: $954.5M) down to a tiny sliver (FY2018: $7.2M) once CPT adopted ASC 842
in 2019 — its real revenue moved to a dedicated `OperatingLeaseLeaseIncome` tag entirely outside the
standard Revenue candidate list. Added a CPT-specific override combining `OperatingLeaseLeaseIncome`
(2017-2026) with `RealEstateRevenueNet` (2009-2018, CPT's pre-ASC-842 tag) for full correct coverage.

### LongTermDebt: tag drift and abandonment across REIT sub-types (7 tickers + profile-wide)

The `reit` profile's `LongTermDebt` list (`NotesPayable`, `LongTermDebtNoncurrent`) was too narrow —
16 of 27 tickers showed below-50% coverage, several at literally 0%. Added the base `LongTermDebt`
tag profile-wide (fixes 12 tickers directly: AMT, BXP, CCI, DOC, EQIX, ESS, INVH, PLD, SPG, UDR,
VTR, WELL, CPT — later 3 of these needed a further ticker-specific fix, see below). Confirmed safe
via the same scale-sanity discipline that caught O's `OtherNotesPayable` error: cross-checked every
ticker's resolved value against every plausible alternative debt-balance tag before trusting it.

Five tickers needed ticker-specific overrides, each independently verified against known company
scale before use:
- **DLR, BXP**: base `LongTermDebt` tag was abandoned early (DLR stops 2012, BXP stops 2021) in
  favor of `SeniorNotes` (DLR) or a sum of `SecuredDebt` + `SeniorNotes` (BXP, since BXP tags these
  as two separate components that must be added — neither alone is total debt).
- **AMT, CCI**: base `LongTermDebt` tag is sparse/abandoned; `LongTermDebtAndCapitalLeaseObligations`
  has full history at the correct scale for both.
- **EXR**: `NotesPayable` (already first-priority) is real but abandoned after 2021 at ~$5.4B, well
  below EXR's current ~$9.4B scale; `SeniorNotes` is the correct, currently-used tag.
- **FRT**: `NotesPayable` is not total debt at all for this ticker — a confirmed small sub-component
  (~$1.0-1.4B vs. real ~$4.3-5.0B) that happened to have near-complete quarterly coverage, silently
  winning every interim quarter. FRT's correct tags (`LongTermDebt`/`DebtAndCapitalLeaseObligations`)
  are annual-only (no quarterly facts exist at all for this ticker) — since `NotesPayable` is
  confirmed wrong rather than merely incomplete, dropped it entirely per the "mask rather than show
  a plausible-but-wrong value" rule; FRT's `LongTermDebt` is now correct at each fiscal year-end and
  empty for interim quarters (a real reporting-granularity limit, not a bug).
- DLR's remaining ~48% coverage (a genuine 2013-2018 gap where neither `SeniorNotes` nor the base
  tag has any data) is a confirmed, unfixable historical gap, not a further tag issue.

### Five more "implausibly-small-Q4" decumulation cases (EQR, KIM, UDR, WELL, AMT)

Found via a systematic V-shape-dip scan across the whole batch's Revenue series (a quarter
implausibly low relative to both neighbors) — the same "implausibly small positive" bug class as
OXY/DD/IP, each an independent real corporate event, none previously known to this project:
- **EQR**: FY2009 and FY2010 both restated down across multiple filings, reflecting EQR's large
  2009-2011 apartment-portfolio disposition program. Recovered both years to their original,
  scope-consistent annual values (Q4-2009: $141.5M → $464.4M; Q4-2010: $137.3M → $454.3M).
- **KIM**: FY2012 restated down across two filings (Kimco's ongoing shopping-center disposition
  program). Recovered Q4-2012 from $128.9M to $257.9M.
- **UDR**: FY2010 restated down across three filings. Recovered Q4-2010 from $84.2M to $205.7M.
- **WELL** (then Health Care REIT): FY2010 restated down across an unusually long chain of nine
  sequential filings (2011-2013), reflecting WELL's active joint-venture deconsolidation program of
  that era. Recovered Q4-2010 from $103.6M to $214.8M (independently matching a by-hand estimate of
  ~$212.5M from the original annual figure).
- **AMT**: FY2022 restated down in the FY2024 10-K, reflecting AMT's 2025 divestiture of its India
  tower business. Recovered Q4-2022 from $1,639M to $2,705M.

### Other findings (investigated, no fix applied)

- **Towers/data-centers structural question (Step 1)**: checked whether D&A intensity or FFO margin
  look structurally different for AMT/CCI/SBAC/EQIX/DLR vs. traditional property REITs. D&A
  intensity is actually comparable (~22-36% both groups); FFO margins for towers/data-centers run
  slightly *lower*, not inflated — arguing against the concern that equipment D&A overstates FFO
  for these names. CCI's FFO briefly went negative in late 2024, confirmed as a real event (Fiber/
  Small Cells divestiture impairment), not a data issue. Reported as a nuanced, not-clearly-conclusive
  finding; no reassignment made.
- **`GainLossOnSaleOfProperties`**: confirmed structurally absent for towers/data-centers (AMT, CCI,
  EQIX, SBAC — consistent with a business model that rarely sells individual properties). Searched
  exhaustively for HST, SPG, VTR, WY; found only sparse, abandoned one-off tag variants — confirmed
  unfixable, not a coverage bug.
- **MAA's 2014-Q2 through 2017-Q4 Revenue gap** (1,552 days): confirmed no standard `us-gaap` tag
  captures this window at all; likely a company-specific XBRL extension tag from MAA's 2013 Colonial
  Properties merger integration, outside what this pipeline can access. Confirmed unfixable.
- **DLR, SBAC**: no per-share `DividendsPerShare` tag exists at all (same pattern as CE in materials)
  — confirmed unfixable tag gaps, not real non-payer status.
- **Non-pure-play REITs (WELL, VTR, HST)**: FFO margins are stable and plausible (28-31% recent
  range for all three) post-fixes; no distortion found from mixed operating-business economics.

Non-regression: full before/after across all 432 cached tickers (both periods) — changes confined
entirely to the 25 REIT tickers touched by this task's fixes (O itself, the pre-existing reference
ticker, shows **zero** changes, confirming no previously-shipped value was disturbed). Full detail
in `reit_scan_report.md`.

## 2026-07-27 — New bug class: positional vs. date-based period alignment in `calculate_growth` (project-wide)

A structurally different bug from everything logged above — not a bad tag, not a scope mismatch, not
a scale error. `calculate_growth` computed its "prior period" comparison **positionally**
(`groupby("ticker")["value"].shift(periods)` on a date-sorted series), silently assuming every ticker's
concept series has exactly one row per quarter with no gaps. Any missing quarter — for any reason —
shifts every subsequent comparison by one slot, comparing against whatever row happens to land 4
positions back, however distant in time that actually is. No existing guard catches this:
`min_base_ratio` only protects against a small-but-present base value, and the wrong-period base here
is neither small nor implausible in isolation — it's simply the wrong date.

**Root cause confirmed and reproduced by hand**: O's `Revenue_TTM` has a genuine 5-year reporting gap
(2012-03-31 → 2017-03-31, `Revenues` untagged 2013-2016). At 2017-12-31, `.shift(4)` reaches back to
2012-03-31 (the 4th *row*, not the 4th *quarter*): $1,215,768,000 / $433,743,000 − 1 = **180.3%**,
matching the flagged figure exactly. The bug's actual footprint is wider than a single point, though:
**all four quarters immediately following any gap** are corrupted at progressively decreasing severity,
because the positional shift only "catches up" to true 4-quarters-back alignment exactly `periods`
quarters after the gap ends (confirmed on O: 2017-Q1 67.9% → 2017-Q2 108.0% → 2017-Q3 145.0% → 2017-Q4
180.3%, then correct again from 2018-Q1 onward).

**Full-universe scope scan** (all 4 `calculate_growth` callers: `revenue_growth`/`Revenue_TTM`,
`income_growth`/`NetIncomeLoss_TTM`, `reserve_growth`/`ClaimsReserve`, `operating_income_growth`/
`OperatingIncomeLoss_TTM`) found the true scope is **larger than an "obvious spike" heuristic would
catch** — exactly the concern the task raised. A naive large-gap heuristic (>1.5x expected spacing)
found only 227 hits across 49 tickers; the actual, precise before/after diff (comparing the old
positional output against the new date-based output row by row) found **1,140 `(ticker, metric, end)`
triples across 98 tickers** — including subtle cases (e.g. ACN 2012: 12.6% reported vs. 18.2% real) that
don't look wrong on their own and would never have been flagged for manual review. Of the 1,140: 215
newly masked (real gap, no valid comparison exists), 874 recomputed to a different, correct value, and
51 newly *unmasked* — cases where the old positional bug compared against an implausible row that
failed the `min_base_ratio`/positive-value guards, while the date-correct comparison passes cleanly
(a genuine recovery, not a new mask). One recurring structural case worth flagging specifically: **KR
(Kroger) is missing its fiscal Q1 every single year for its entire multi-decade history** — not a
one-time gap. The date-based fix cures this completely rather than just masking it, since Q2/Q3/Q4 are
each still genuinely ~365 days from their own prior-year same quarter; only the never-populated Q1
correctly returns no value.

**Fix**: implemented once, inside `calculate_growth` itself (`metrics.py`), so all four current callers
(and any future one) get it automatically — not a per-ticker or per-concept patch, since this is a
structural property of the function, not a tag-specific data error. Replaced the positional
`.shift(periods)` with a date-based nearest-match lookup (`pd.merge_asof`, grouped by ticker, matching
each row against the closest available row to `end − periods×365.25/4 days`), returning `NaN` when
nothing exists within tolerance rather than silently accepting whatever the next available row is.

**Tolerance calibrated from real project-wide data**, not assumed: the full population of
position-4-apart date gaps across every cached ticker/concept clusters overwhelmingly (96%+) at
360-380 days, with a clean, nearly-empty band from 380-430 days (only 8 pairs total), then a second,
unrelated cluster at 430-470 days that turned out to be a **project-wide XBRL-mandatory-tagging
phase-in edge effect concentrated in 2008-2010** (many tickers' first 1-2 available quarters sit oddly
spaced before regular quarterly cadence begins) — correctly excluded, since there genuinely is no
reliable year-ago comparison for a ticker's first few quarters. Set the tolerance at **±45 days** (for
`periods=4`; scaled proportionally as `periods × 45/4` for generality), landing cleanly inside the
empty band and excluding both the XBRL-edge cluster and every genuine gap.

**Over-masking check**: of the task-named irregular-fiscal-calendar retailers (HD, LOW, TJX, ROST, BBY,
WSM, ULTA), HD/ROST/WSM/ULTA showed **zero change** (their calendars are already regular enough). BBY,
LOW, and TJX did change — each confirmed, by inspecting raw quarterly dates directly, to be a **genuine
fix**: BBY has a real inserted stub quarter in 2011 (a ~63-day then ~28-day span breaking the normal
~91-day cadence); LOW's `NetIncomeLoss_TTM` has a real 2012-2013 gap independent of its (fully populated)
`Revenue_TTM`; TJX's `NetIncomeLoss_TTM` has a real ~189-day gap that Revenue_TTM doesn't share — a
reminder that gaps must be checked per concept, not assumed to align with Revenue's own coverage.

**Non-regression**: full before/after across all 406 cached tickers, all four `calculate_growth`
callers: 72,608 total rows, exactly 1,140 changed (matching the scope scan precisely), 71,468
unchanged. Spot-checked known gap-free tickers (AAPL, MSFT, JNJ, PG) directly: **zero changes**,
confirming the fix is provably inert in the non-gap case. Downstream consumer `operating_leverage`
(which divides `operating_income_growth` by `revenue_growth`) correctly propagates the fix: 301 of
20,029 rows changed across 45 tickers — an expected consequence of correcting its two upstream inputs,
not a new issue. Full detail in `growth_period_alignment_report.md`.

## 2026-07-27 — `materials` split into `materials` / `materials_integrated` by `OperatingIncomeLoss` coverage, `rule_of_40` hidden

Follow-up to the materials scan, mirroring the `energy`/`energy_integrated` precedent exactly. Split
`TICKER_PROFILES` into `materials_integrated` (8 tickers: NEM, DOW, DD, AVY, SHW, IP, BALL, NUE — keeps
`OperatingIncomeLoss` excluded and `operating_margin`/`net_debt_to_ebitda`/`ev_ebitda` hidden) and
`materials` (the remaining 16: LIN, APD, ECL, FCX, LYB, PPG, ALB, CE, IFF, MLM, VMC, STLD, PKG, AMCR,
CF, MOS — now shows all three). `PROFILE_HIDDEN["materials"]` un-hiding the 3 metrics and hiding
`rule_of_40` had already been applied to `config.py` externally before this task started (confirmed by
inspection, treated as ground truth per standing instruction); this task added the
`materials_integrated` profile and the `PROFILE_EXCLUDED_CONCEPTS["materials_integrated"] =
{"OperatingIncomeLoss"}` entry (a genuinely new exclusion — unlike `energy`, `materials` never excluded
anything pre-split, so there was nothing to carry forward for this key).

**Correction to the prior scan report's own tally, caught during this task's "verify, don't just copy
the conclusion" step:** the scan report's Step-5 coverage table correctly listed NUE at 0%
`OperatingIncomeLoss` coverage (identical, always-absent pattern to NEM/DOW/DD/AVY), but its summary
prose undercounted the fragile group as "7 of 24" and omitted NUE from the always-absent list — an
error in that report's own writing, not a data issue. This task's brief inherited the undercount (its
Step-1 code block listed only 7 tickers to move). Re-verified NUE's coverage directly (0/75, never
populated, no ambiguity) and moved it to `materials_integrated` as well — 8 tickers, not 7.

Verified byte-identical for all 8 `materials_integrated` tickers: `PROFILE_HIDDEN` and
`get_concept_candidates()` (which together determine every actual computed/displayed value) match
their pre-split `materials` behavior exactly; only `PROFILE_EXCLUDED_CONCEPTS` differs, which is the
intended, new correction (nothing computational). Coverage re-check for the 16 remaining `materials`
tickers confirms only two already-known, confirmed-real gaps remain (CE `DividendsPerShare` — no tag
exists at all; FCX `Goodwill` — real 2014 writeoff) — NUE's removal cleared its 0% flag from this list.
Spot-checked real `operating_margin`/`net_debt_to_ebitda` values for all 16 — all meaningful, no
degenerate or barely-there charts (e.g. LIN 26.5% margin/1.35x leverage, MLM 23.1%/2.37x, STLD 9.1%/
1.57x).

Non-regression: full before/after across all 405 cached tickers, both periods — 0 removed/added/
changed (expected, since this task only touches `config.py`, not `parsers/parse_edgar.py`). Full detail
in `materials_profile_split_report.md`.

## 2026-07-27 — Materials tag coverage scan (24 tickers): MOS dividend scale bug, DD/IP decumulation fixes (4 quarters, 3 separate real events)

Eleventh stock-type profile batch, LIN + 23 new. Coverage came back clean overall (only
`OperatingIncomeLoss` at a few tickers and one dividend gap below 50%), but the scan surfaced four
independent, real bugs — none named in the task brief, all found by checking real filings rather than
trusting chart shape or raw coverage ratios.

**LIN's 2019 scope break, confirmed properly.** The ~125% FY2019 revenue jump is real: Praxair was
named the accounting acquirer for the Oct 31, 2018 Linde/Praxair "merger of equals" (ASC 805), so
pre-merger quarters are Praxair-only and the step-up lands exactly at the close date (Q3 2018 $3.008B
→ Q4 2018 $5.801B revenue, confirmed via the same-tag method, not a restatement — FY2018's competing
filed values differ by only 0.4%, ruling out a scope-mismatch bug). Real, clean, no fix needed.

**MOS: a filer-side scale error, same class as the ROK/STX DividendsPerShare fixes.** Mosaic's Q3-2025
and Q1-2026 10-Qs tagged `CommonStockDividendsPerShareCashPaid` at ~1,000,000x the real value (220000
instead of $0.22), corroborated by the correctly-tagged neighboring quarters ($0.22 each) and the
FY2025 10-K's annual total ($0.88 = 4×$0.22). No competing correctly-scaled value exists for either
period, so per the established "prefer masking over guessing" rule, dropped rather than corrected —
this also removed a corrupted YTD fact that was silently breaking the Q4-2025 decumulation (already
caught by the non-negative-flow guard, but for the wrong underlying reason).

**DD and IP: four more instances of the decumulation scope-mismatch bug's "implausibly small positive"
symptom** (the class first found in OXY/OxyChem), each tied to a distinct, real, verified corporate
event:
- **DD (DuPont) Q4-2020**: FY2020 Revenue restated from $14,338M to $11,128M starting with the FY2022
  10-K (filed 2023-02-15), reflecting the Nov-2022 Mobility & Materials divestiture to Celanese. Q1-Q3
  2020 quarterly facts were locked into 10-Qs filed in 2021 — before the deal was even announced (Feb
  2022) — so decumulating them against the smaller restated annual produced an implausible $540M Q4
  (vs ~$3.2-3.7B/qtr neighbors). Recovered to $3,750M by dropping the mismatched-scope annual fact —
  independently corroborated by DD's own directly-filed Q4-2020 value under the immediately-prior
  restatement layer (N&B-excluded only), which matches exactly.
- **IP (International Paper) Q4-2019 and Q4-2020**: both restated smaller starting with the FY2021
  10-K (filed 2022-02-18), reflecting the Oct-2021 Sylvamo (printing papers) spinoff. Same mechanism —
  pre-spinoff quarterly facts vs. post-spinoff annual — produced $1,439M (2019) and $2,224M (2020)
  against ~$5.0-5.9B/qtr neighbors. Recovered to $5,498M and $5,239M respectively.
- **IP Q4-2023**: restated smaller starting with the FY2025 10-K (filed 2026-02-27), reflecting the
  Global Cellulose Fibers business sale (announced 2025-08-21, closing 2026-01-23 to American
  Industrial Partners) — GAAP requires reclassifying to discontinued operations as soon as a sale is
  probable, which is why the FY2023/2024 comparatives were restated before the deal even closed.
  Produced an implausible $1,718M vs ~$4.6-5.0B/qtr neighbors; recovered to $4,601M. (FY2024 itself
  needed no fix — its quarterly facts were already filed after the restatement took effect and
  reconcile cleanly on their own.)

All four recoveries used the established `_KNOWN_BAD_FACTS` drop-the-mismatched-fact mechanism, each
verified against a real, dateable corporate event before touching anything, per the same evidentiary
standard as every prior fix in this class (EXC/FE/PPL, SATS, OXY/OxyChem).

**DOW and AMCR/Berry Global checked and found clean.** DOW's own historicals (a genuinely new spinoff
entity, not a restated-in-place registrant like DD) show no multi-value restatement signature at all —
quarterly and annual reconcile without incident. AMCR's Q2-2025 step-up (Berry Global merger, completed
Apr 30, 2025) is a real, clean scope increase with no decumulation artifact, plus a fiscal-year-end
transition visible in the annual periods (noise, not a bug).

**`OperatingIncomeLoss` coverage split, mirroring the energy precedent.** 7 of 24 tickers (29%) show
the same fragility energy's supermajors did: NEM, DOW, DD, AVY are permanently at 0% coverage;
SHW, IP, and BALL have decent historical coverage (68-84%) but have gone completely dark for the last
1.5-2 years (last data 2024-Q3/Q1, 6-8 of the last 8 quarters missing) — the same "recency, not raw
ratio" finding as DVN/SLB/BKR in energy. The other 17 tickers are clean and current through 2026-Q1/Q2.
Recommended (not implemented, per this task's scope) as a candidate for a future `materials`/
`materials_integrated`-style split.

Non-regression across all 405 cached tickers (381 existing + 24 materials): only DD, IP, and MOS
changed — exactly the confirmed fixes, nothing else. Full detail in `materials_scan_report.md`.

## 2026-07-26 — Backlog cleanup: net_debt_to_ebitda relative guard, GLW $100B capex typo, FIX period-tagging error

Three independent, previously-logged items, each with a different root cause.

### Part A — `net_debt_to_ebitda`: the 33 explosions the absolute floor couldn't reach

The Tier-1 guard task caught 20 of 53 confirmed `net_debt_to_ebitda` explosions with an absolute
EBITDA floor (`min_denominator_abs=$10M`); 33 remained. Re-derived them (|ratio|>60 reproduces the
prior task's 53-case set exactly, of which 19 are now floor-masked and 33 are unguarded). Confirmed
they are genuinely "small-EBITDA-relative-to-scale," not near-zero: median |EBITDA| is $111M (well
above the $10M floor, which is why it misses them) but tiny against multi-billion net debt. These are
EBITDA-*collapse* quarters (WDC memory downturn, BA 737-MAX crisis, INTC's 2024-25 trough, the
COVID cruise/casino names, WBD's merger-year D&A) — not permanently-thin-margin businesses.

Evaluated both scale references the task named. **Revenue_TTM fails**: real thin-margin, high-revenue
businesses (VLO refining at ~0.8% EBITDA/rev with a perfectly sane 3.8x ratio, HAL, HPQ) have the same
low EBITDA/revenue as the explosions, so any Revenue-relative threshold that catches all 33 also masks
~260 legitimate readings. **net_debt is the data-supported reference** — but since net_debt is the
ratio's own numerator, "mask when |EBITDA| < k·|net_debt|" is algebraically "mask when |ratio| > 1/k",
i.e. a magnitude cap. Rather than add a redundant parameter that disguises that, implemented it
honestly via the existing `max_abs_result` on the `net_debt_to_ebitda` call
(`MAX_NET_DEBT_TO_EBITDA_ABS = 60`). This is the only choice that cannot over-mask a genuinely
low-leverage thin-margin business (its ratio is small, so it is never touched).

Calibration: the 52 explosions all sit at |ratio| ≥ 61.06 (EBITDA/net_debt ≤ 0.0164); the next-highest
reading is 56.16 — a clean gap with nothing in between. A cap of 60 lands in that gap, catches exactly
the confirmed explosions, and leaves the grey zone (|ratio| 20-56, mostly the *same* pathology at lower
magnitude) untouched, honoring the task's "only the confirmed-explosion cases newly mask" rule. Full
before/after across the universe: **33 newly masked, 0 values changed, 0 newly unmasked**; VLO/HAL/HPQ
and levered utilities D/KMI/WMB (5-8x) all survive with real values. The grey zone (20-56) shows the
same thin-EBITDA artifact and is a candidate for a future, separately-scoped tightening — deliberately
left alone here.

### Part B — GLW Q1-2011 capex reported as exactly $100,000,000,000

Corning's `PaymentsToAcquireProductiveAssets` for 2011-Q1 is a single fact of exactly $100B — ~200x
GLW's entire annual capex (~$1-2B) and larger than its 2011 total revenue (~$7.9B). A directly-filed
data-entry error in the original 10-Q with **no correcting filing anywhere** — a different evidentiary
situation from every prior `_KNOWN_BAD_FACTS` case, which all had a competing correct value to fall
back to. The true scale cannot be inferred with confidence (÷1000→$100M, ÷100→$1B, neither matching
GLW's real ~$450M Q1 scale, and the next fact in the tag is 2019 so there is no in-window neighbor to
reconcile against). Per the "prefer masking over guessing" rule, added it to `_KNOWN_BAD_FACTS`; since
it is the only fact for that period, the drop leaves no replacement — the $100B point simply
disappears, GLW's other capex points untouched.

### Part C — FIX (Comfort Systems USA): a period-tagging error, not a corporate event

The ~80% two-month restatement flagged (and masked, unexplained) in the decumulation scan is FIX's
FY2025 revenue: $9,101,641,000 in the 10-K (filed 2026-02-19) vs $1,831,286,000 refiled 2.1 months
later (2026-04-23). Not a divestiture — a period-tagging error: the Q1-2026 10-Q stamped its prior-year
Q1-2025 comparatives with `end=2025-12-31` instead of `end=2025-03-31`. The mislabeled value is exactly
FIX's real Q1-2025 revenue, and the identical error hit every income-statement line filed that day
(Revenues, OperatingIncomeLoss, GrossProfit, CostOfRevenue, SG&A, Depreciation…). Because "later filed
wins," the mislabeled FY figures beat the correct 10-K values, collapsing FY2025 Revenue to $1.83B and
FY2025 OperatingIncomeLoss to $209M (real: $1.31B), pushing Q4-2025 revenue negative (masked) and
Q4-2025 operating income to a *visible* wrong −$679M. Dropped the two mislabeled facts via
`_KNOWN_BAD_FACTS` (`(FIX,"Revenues")`, `(FIX,"OperatingIncomeLoss")` at end=2025-12-31, filed
2026-04-23); the correct 10-K values win again — FY2025 Revenue $9.1B, OpInc $1.31B, Q4 revenue
$2.646B, Q4 OpInc $426.7M, all clean. Separately noted (not fixed — different root cause, out of
scope): FIX's quarterly D&A carries a pre-existing tag-definition inconsistency (quarterly YTD D&A
facts sum to more than the annual D&A), which masks Q4 D&A independently of this tagging error.

### Combined non-regression

One full-universe before/after across all 381 cached tickers, both periods. Raw-fact level: only GLW
(1 removed) and FIX (1 added, 3 changed) touched — exactly the Part B/C facts, nothing else.
Metric level: `net_debt_to_ebitda` shows exactly 33 newly masked (19 tickers) with 0 other value
changes. No cross-contamination between the three parts. Full detail in `backlog_cleanup_report.md`.

## 2026-07-26 — `energy` split into `energy` / `energy_integrated` by `OperatingIncomeLoss` coverage

The energy scan's finding that `OperatingIncomeLoss` absence is a supermajor/diversified-conglomerate
pattern (XOM, CVX, COP, OXY, PSX at 0%), not sector-wide, meant `operating_margin`, `net_debt_to_ebitda`,
and `ev_ebitda` were being hidden profile-wide for all 19 energy tickers to accommodate 5 — the same
kind of all-or-nothing tradeoff resolved twice before by the same per-ticker evidence-gathering method
(`health_services`: 5 of 6 clean → stayed visible; `homebuilder`: 1 of 4 clean → hidden profile-wide).
Energy is the first case where the split isn't lopsided enough to resolve either way profile-wide, so
it's the first time this project actually forks a profile in two over this decision, rather than just
picking hide-all or show-all.

Re-checked coverage per ticker rather than assuming the remaining 14 (post-APA-removal) share one
outcome. Two clearly separate groups emerged, but not the ones originally assumed:

- **Structurally absent (supermajor/diversified-conglomerate reason), unchanged from the scan report:**
  XOM, CVX, COP, OXY, PSX — 0% coverage, no `OperatingIncomeLoss` tag at all.
- **Present overall but currently dead — a distinct reason, same practical outcome:** DVN (19/74 =
  26%, tag stops entirely after 2017-09-30 — 8.5 years stale), SLB (37/74 = 50% overall, but missing
  for all of the last 8 quarters — 2 years stale as of 2026-03-31), BKR (33/41 = 80% overall, but
  missing for 5 of the last 8 quarters — stale since 2024-12-31). All three would show
  `operating_margin`/`net_debt_to_ebitda`/`ev_ebitda` populated for old history and then blank for
  every recent quarter — worse than never showing it, since it reads as a broken chart rather than an
  absent one. The raw coverage ratio alone (BKR's 80%) would have hidden this; only checking recency
  of the gap (last-8-quarters check) surfaced it.
- **Genuinely clean, current, and un-hidden:** EOG, FANG, EQT, EXE, WMB, OKE, KMI, TRGP, MPC, VLO, HAL
  — 93-100% coverage, zero gaps among the last 8 quarters each. Spot-checked real computed values
  (EOG ~30% operating margin, WMB ~27-29% consistent with a pipeline business, MPC ~4-7% consistent
  with thin refining margins, FANG's real Q4 2025 dip traced to a genuine one-time -$2.78B operating
  charge, not a guard artifact) — all real, meaningful, non-degenerate numbers.

Split `energy` into two profiles: `energy_integrated` (XOM, CVX, COP, OXY, PSX, DVN, SLB, BKR — 8
tickers, keeps `OperatingIncomeLoss` excluded and the 3 ratios hidden, byte-identical to every one of
these 8 tickers' pre-split behavior, verified directly) and `energy` (the remaining 11, now with
`OperatingIncomeLoss` no longer excluded and the 3 ratios un-hidden). `PROFILE_CONCEPT_OVERRIDES`
copied as-is for `energy_integrated` (same `Capex`/`CashAndEquivalents` fallback tags) since nothing
about those overrides is tied to which of the two hidden-metric buckets a ticker falls into.

Non-regression: full before/after diff across all 381 cached tickers, 370,852 rows both times, 0
removed / 0 added / 0 changed — confirming the split is purely a profile-label and hidden-set change
with zero effect on any extracted value, for the 8 `energy_integrated` tickers or any of the other 373.

## 2026-07-26 — Decumulation scope-mismatch bug, third symptom: implausibly-small positive (OXY/OxyChem)

The energy tag coverage scan, checking OXY's 2024 CrownRock acquisition for a scope-break
signature, found a *different*, unnamed 2025 event instead: Occidental sold its OxyChem
chemicals business to Berkshire Hathaway in 2025. FY2023 and FY2024 Revenue got restated down
(FY2023: $28,325M → $23,230M; FY2024: $27,413M → $22,710M, both restated in the FY2025 10-K
filed 2026-02-18) while Q1-Q3 of both years — sourced from already-filed, never-updated 10-Qs —
stayed at the original, OxyChem-included scale. `decumulate_period_values` then computed Q4 as
`smaller_restated_annual − larger_original_Q1-Q3` for both years, landing on an implausibly
*small* (not negative, not oversized) Q4: $2.243B and $2.157B for FY2023/2024, respectively,
against Q1-Q3 ranges of $6.6-7.3B.

This is a **third manifestation** of the same root cause already fixed twice before (negative,
for divestitures large enough to flip sign; oversized-positive, for SATS's DISH combination) —
not yet cataloged, since the OxyChem exclusion (~20-25% of total revenue) wasn't large enough to
push Q4 negative, just small enough to look wrong relative to neighbors. Caught by chance during
a targeted investigation, not by either of the two existing automated scans (a >=10x-gap
heuristic wouldn't have flagged a ~3x shrink) — worth remembering that the existing scan
toolkit still has this gap; a targeted, evidence-based check (same-tag restatement + Q1-Q3
reconciliation) caught it where magnitude-based scanning alone would not have.

Recovered FY2023 and FY2024 via the existing `_KNOWN_BAD_FACTS` mechanism (drop the restated
fact, let the original win) — Q4 2023 recovers to $7,338M, Q4 2024 to $6,860M, both cleanly
in range with the surrounding quarters. FY2025 has no earlier comparator (first-ever filing of
that year), so its equally-small Q4 ($1,658M) was masked only, via a new
`("OXY", "Revenue")` entry in `_KNOWN_SCOPE_MISMATCH_OUTLIERS` (the sign-agnostic mechanism
built for SATS's `OperatingCashFlow` fix, reused here for its "any implausible magnitude"
generality rather than its original negative-direction use case).

Also investigated, during the same scan, several other real energy-sector corporate
restructurings for the same signature — ConocoPhillips/Phillips 66 (2012 spinoff), Williams/WPX
Energy (2012 spinoff), Devon Energy's multi-year 2016-2019 divestiture program, and Chesapeake's
2019 distress-era restatement — all confirmed as genuine same-tag restatements via direct
inspection, but none crossed the established ~10x actionable-artifact threshold in the derived
quarterly series (max found: 4.3x for Devon). Left unmasked, consistent with the standing
"don't force a fix past its evidence standard" discipline. Full detail in
`energy_scan_report.md`.

---

## 2026-07-22 — Decumulation scope-mismatch bug, third concept: OperatingCashFlow (SATS `fcf_margin` regression)

Fixing SATS's `Revenue`/`Capex` scope-mismatch bug (previous entry) had a direct side effect:
`fcf_margin` used to come out masked for SATS 2021-2022 as an *accidental* consequence of the
broken `Revenue` feeding `apply_self_relative_scale_guard`. Checking directly (not assuming)
confirmed the guard no longer fires, and `fcf_margin` was showing real-looking but wrong values
(212%, 68%, 40%, 29%) — because it also divides by `OperatingCashFlow_TTM`, which carries the
**identical, still-unfixed** bug: SATS's raw FY2021 `OperatingCashFlow` fact is $632,226,000 as
originally filed (2022-02-24/2023-02-23) and $4,655,373,000 as restated (2024-02-29) — same
common-control-combination event, same filing date, same mechanism already fixed for `Revenue`
and `Capex`. Silently-wrong data is worse than visibly-absent data, so this was worth chasing
down rather than declaring "unaffected" as the task brief initially assumed.

### Step 1/2 — full-universe scan, both directions: 37 candidates, 5 tickers confirmed

Ran the same one-sided (backward/forward, ≥10x), sign-agnostic magnitude-gap check against
`OperatingCashFlow` project-wide (appropriate since OCF, unlike `Revenue`/`Capex`, can
legitimately be very negative in real distress — a blanket non-negativity rule would wrongly
mask genuine losses like WYNN's real COVID-19 cash burn or PG&E's real $13.5B wildfire-trust
funding outflow). Found 37 hits across 30 tickers; verifying each against the actual
restatement signature (multiple, differently-valued annual-length facts for the same date, not
magnitude alone) confirmed only 5 tickers, 6 rows share this bug:

- **SATS**: FY2021 ($632M→$4.66B) and FY2022 ($530M→$3.62B), the exact same DISH-combination
  event and filing date already fixed for `Revenue`/`Capex` — recovered via `_KNOWN_BAD_FACTS`,
  reconciling cleanly to $204M and $186M respectively, in range with the ticker's other quarters.
- **ADM, FLEX, JBL** (2016/2017 dates): each swings from a normal positive figure to several
  billion dollars *negative* at a single later filing (2019) — a different, less certain root
  cause than SATS (most plausibly a cash-flow-statement reclassification, e.g.
  supply-chain/reverse-factoring arrangements moved from operating to financing activities, an
  industry-wide practice shift for exactly this kind of manufacturer around 2018-2019; FLEX and
  JBL are both electronics manufacturing services companies, reinforcing this reading).
- **TMUS** (2011-12-31): coincides with its 2013 MetroPCS reverse-merger restructuring, the same
  2011-2013 window already flagged as a merger-integration artifact for `rule_of_40` in the
  telecom scan report.

ADM/FLEX/JBL/TMUS were masked only, not recovered — unlike SATS, none has an independent,
external cross-check confirming which annual figure is "more correct" (for the three
manufacturers, the *restated* value may well be the more compliant one, the opposite direction
of confidence from SATS's case), so no value was guessed. Added a new, sign-agnostic masking
mechanism, `_KNOWN_SCOPE_MISMATCH_OUTLIERS` in `parsers/parse_edgar.py`, alongside (not
replacing) `_KNOWN_POSITIVE_OUTLIERS` — needed because OCF's mismatches can go either direction,
unlike the purely-positive ED Capex case the existing mechanism was built for.

### Step 3 — re-verified `fcf_margin`/`rule_of_40` directly, not assumed

`fcf_margin` for SATS is now plausible across its entire cached history (2021-12-31: 212%→9.8%;
2022 Q1-Q4: 68%/40%/29%/(new)→3.9%/2.0%/1.5%/1.1%), a sensible gradual-decline story consistent
with margin compression as DISH's pay-TV base shrinks. `rule_of_40` correctly comes out masked
for all of 2022 (a genuine TTM-window transition artifact spanning the scope-change boundary,
the same mechanism already documented for TMUS/CMCSA/CHTR's own merger integrations) and shows
one expected one-year-later echo (2023-03-31: 189%, decaying naturally over the next three
quarters) — not a new problem, an inherent property of TTM/YoY math around any real scope change.

### Step 4 — full non-regression

Quarterly: 4 masked (ADM/FLEX/JBL/TMUS), 2 recovered (SATS), zero elsewhere. Annual: 0 masked, 2
recovered (same SATS rows). Every previously-shipped fix (EXC/FE/PPL, SATS's own Revenue/Capex,
ED's Capex) spot-checked byte-identical. **General lesson, worth remembering going forward:**
after any scope-mismatch fix, briefly check whether any metric depending on the fixed concept
*together with* a still-unfixed one might have been "accidentally correct" before — masking that
happens to look right can be coincidental, not diagnostic, and fixing one input can silently
reveal (or hide) a problem in another. Full detail in
`operating_cash_flow_scope_mismatch_report.md`.

---

## 2026-07-22 — Decumulation scope-mismatch bug, positive direction: SATS/EchoStar and Con Edison

The telecom/cable scan (below) found the decumulation scope-mismatch bug (previous entry) has a
mirror-image manifestation the non-negativity guard can't catch: instead of
`Q4 = smaller_restated_annual − larger_original_Q1-Q3` going negative, a scope-*increase*
produces `Q4 = larger_restated_annual − smaller_original_Q1-Q3` going implausibly large but still
positive. SATS (EchoStar)'s FY2021 Revenue got retroactively restated to the combined
DISH+EchoStar scale (~$19.82B) via GAAP's common-control-combination rules once the DISH merger
closed (Dec 31, 2023), while Q1-Q3 2021 stayed on file at EchoStar's original ~$500M/quarter
scale — `decumulate_period_values` computed Q4 2021 as ~$18.33B, wrong by ~37x, but not sign-
impossible, so it sailed past the existing guard.

### Step 1 — full-universe scan, positive direction: 56 candidates, only 2 tickers confirmed

Extended the scan to flag decumulated quarterly values ≥10x above their own backward-only *or*
forward-only neighboring-quarter median (a **one-sided** window is essential — a combined
window missed SATS entirely, since 2022's quarters are also elevated by the same restatement and
drag a combined median up enough to hide the gap). Checked `Revenue`, `Capex`, `CostOfRevenue`,
`Inventory`, `AccountsReceivable`, `AccountsPayable` project-wide: 56 hits (34 Capex, 20 Revenue,
2 AccountsReceivable), across 24 tickers. Point-in-time concepts again showed zero hits from this
mechanism (structurally can't, since they're never decumulated) — the 2 AccountsReceivable hits
(Lowe's) are real, single, never-restated reported values, not this bug.

Individually checked all 56 for the actual diagnostic signature (multiple, differently-valued,
raw annual-length facts for the same end date, i.e. an actual restatement) rather than trusting
the magnitude heuristic alone — a magnitude spike is not, by itself, proof of a bug the way a
negative value was: 49 of the 56 are genuine, single, never-restated real figures (COVID-era
cruise-line revenue swings for CCL/NCLH/RCL, GE's multi-stage Capital-exit restructuring,
MetLife's Brighthouse-spinoff-era item, assorted one-time lumpy capex) or a likely unrelated raw-
data error (GLW's $100B Capex, flagged but not fixed, no restatement present). None of these were
masked — doing so on magnitude alone would repeat the exact mistake the scale-outlier-
generalization task already proved dangerous.

### Step 2/3 — two confirmed cases, two different outcomes

**SATS**: same DISH-combination event already documented for Revenue also restated Capex for
FY2021 and FY2022 (both at the same 2024-02-29 FY2023-10-K filing date). Recovered all three
(Revenue + 2× Capex) via `_KNOWN_BAD_FACTS` — the same drop-the-restated-fact,
let-the-existing-tie-break-resolve mechanism as EXC/FE/PPL — landing cleanly back in range with
the ticker's other 2021/2022 quarters.

**ED (Consolidated Edison)**: Capex for FY2016-2019 shows the same mechanical symptom (annual
restated to a different scope than never-updated quarters) but *not* SATS's clean story — no
known ConEd M&A explains it, and the *larger* post-2018 figures ($3.6-5.2B/year) look more
consistent with ConEd's real capital-spending scale than the original ($400-850M/year) ones,
the opposite direction of confidence from SATS. Added a new, narrower mechanism,
`_KNOWN_POSITIVE_OUTLIERS` in `parsers/parse_edgar.py` — masks the derived quarterly value
directly (there's no reliable original to fall back to here), restricted to the quarterly path
only (ConEd's raw annual facts are left alone; whether they're themselves right isn't
established). Masked FY2016-2019 Capex for ED only.

### Step 4 — full non-regression, and an honest (not glossed-over) side effect

Quarterly: 4 rows masked (ED), 3 recovered (SATS), zero elsewhere. Annual: 0 masked, 3 recovered
(same SATS rows). All prior `_KNOWN_BAD_FACTS` entries and the non-negativity guard verified
byte-identical. One finding reported rather than assumed away: SATS's `fcf_margin`/`rule_of_40`
were previously masked by `apply_self_relative_scale_guard` as a **side effect** of the
now-fixed Revenue bug (the artificial $18.33B peak made real quarters look implausibly small by
comparison) — fixing Revenue removes that peak, so the guard stops firing, which uncovers a
**separate, still-open** instance of the identical scope-mismatch bug in `OperatingCashFlow`
(SATS's FY2021 OCF: $632M original → $4.66B restated, same 2024-02-29 filing) that is outside
both this task's and the prior task's checked-concept list. Not fixed — `OperatingCashFlow` was
never in scope here — flagged for a dedicated follow-up instead of silently patched or silently
ignored. Full detail in `decumulation_positive_outlier_report.md`.

---

## 2026-07-22 — Decumulation scope-mismatch bug: a defensive guard plus 12 targeted recoveries

The utilities scan (two entries below) found `decumulate_period_values` can produce
mathematically impossible negative values — `Q4 = smaller_restated_annual − larger_original_Q1-Q3`
— when a divestiture or spinoff restates a fiscal year's annual total to a smaller
post-divestiture scope while the standalone quarterly facts already on file for that year still
reflect the original, larger, pre-divestiture scope. Both sides of the subtraction are
individually accurate for their own scope; the bug is purely in mixing scopes across the
subtraction. This is a third, distinct failure class from the two scale bugs above: unlike
`SharesOutstanding`, there's no single wrong raw value to rescale; unlike BAC/ROK/STX, dropping
the bad fact doesn't always leave a clean value behind.

### Step 1 — full-universe scan: 276 instances, not just the 4 known

Scanned every cached ticker for negative decumulated-quarterly values in concepts that can never
legitimately be negative: `Revenue`, `Capex`, `CostOfRevenue`, `DepreciationAndAmortization`,
`DividendsPerShare`, `ResearchAndDevelopment`, `EarnedPremiums` (point-in-time concepts like
`Inventory`/`AccountsReceivable`/`AccountsPayable` were also checked — zero hits, since they never
pass through decumulation at all). Found **276** across 106 tickers: 105 `DepreciationAndAmortization`,
83 `Capex`, 58 `DividendsPerShare`, 22 `Revenue`, 6 `ResearchAndDevelopment`, 2 `CostOfRevenue` — far
beyond the 4 originally confirmed (EXC, PPL ×2, FE), confirming the fix needed to be broad.
`OperatingIncomeLoss`/`NetIncomeLoss`/`OperatingCashFlow`/similar concepts that can legitimately be
negative (real losses, reserve releases) were counted but never flagged.

### Step 2 — defensive guard

`_NON_NEGATIVE_FLOW_CONCEPTS` + `_mask_negative_flow_values()` in `parsers/parse_edgar.py`: masks
any negative value in the 7 flagged concepts to "no data" (row dropped), but **only for the
quarterly (decumulated) path** — never for raw annual facts. That restriction turned out to matter:
AIG's raw FY2008 `Revenues` fact is genuinely −$6.84B (its aggregate revenue tag bundles net
investment gains/losses, and 2008 was AIG's near-collapse year), which would have been wrongly
suppressed by a period-unaware guard. Verified project-wide: 0 negatives remain in the 7 concepts,
0 raw annual facts touched, legitimate-negative concepts' counts identical before/after
(NetIncomeLoss 1,836, OperatingCashFlow 1,831, OperatingIncomeLoss 1,136, etc.), and CCL/RCL/NCLH's
real COVID-era losses spot-checked byte-identical before/after.

### Step 3 — targeted recovery: 12 cases, 16 rows, extending `_KNOWN_BAD_FACTS`

For each negative instance, checked whether an earlier-filed, scope-consistent raw fact exists that
reconciles cleanly with the already-used quarters — same mechanism as BAC/ROK/STX, just more
entries. Recovered 12 `(ticker, concept, end)` cases (16 rows counting DLTR's CostOfRevenue/Capex
riding the same event as its Revenue fix), each corroborated by a real, named corporate event: EXC
(Constellation spinoff), FE (FirstEnergy Solutions bankruptcy), PPL ×2 (Talen Energy spinoff; WPD UK
sale), Agilent (Keysight spinoff), HPQ ×2 and HPE (HP/HPE split, then HPE's DXC spinoff), Fortive
(Ralliant spinoff), Jacobs (Amentum divestiture), Western Digital (SanDisk spinoff), Dollar Tree
(Family Dollar sale). Declined recovery for 10 more Revenue cases and all 246 remaining
Capex/D&A/DividendsPerShare/R&D cases where no clean single candidate existed — ADM and AIG each had
multiple non-agreeing restated values (no single "correct" one to pick), GEN's cases likely share
its already-known fiscal-stub-period artifact rather than a divestiture, FIX's ~80% two-month
restatement had no known event to corroborate it, and D&A specifically showed pervasive multi-tag
disagreement (`Depreciation` vs `AmortizationOfIntangibleAssets` vs `DepreciationDepletionAndAmortization`
reconciling to different signs) even for tickers where Revenue recovered cleanly — recovering those
would be guessing, not evidence-based recovery, so they stay masked by Step 2's guard.

### Step 4 — non-regression

Quarterly: 271,080 → 270,820 rows (260 masked, 0 newly appeared, 16 recovered) — 260+16=276,
matching Step 1 exactly. Annual: 75,134 → 75,134 rows (0 masked, 16 recovered) — confirms the
period-restricted guard touches no raw annual fact. `decumulate_period_values`,
`normalize_split_adjusted`, `_normalize_scale_outliers`, and the Tier-1 ratio guards were not
touched. Full detail in `decumulation_scope_mismatch_report.md`.

---

## 2026-07-21 — Targeted fix for BAC/Assets and ROK+STX/DividendsPerShare: a third mechanism, pinned to exact facts

The generalization attempt (previous entry) proved a generic rescale mechanism can't safely cover
the confirmed scale-mismatch cases beyond `SharesOutstanding`. This entry fixes only the three
cases that actually break a currently-visible metric today — BAC's `equity_to_assets` (`inf`) and
ROK/STX's `payout_ratio` (triple-digit-plus distortions) — with a third, deliberately narrower
mechanism: a hardcoded, per-fact drop-list.

### Why not the two existing mechanisms

`TICKER_CONCEPT_OVERRIDES` replaces a ticker's tag list for a concept — the wrong shape here, since
the tag itself is correct at every date except one restated comparative; swapping tags would lose
the tag's otherwise-good data entirely. `_normalize_scale_outliers` rescales based on a chronological
anchor — already proven unsafe to extend beyond `SharesOutstanding` (previous entry). Both bugs here
are a strictly simpler shape: one specific filing, on one specific date, reported one specific fact
at the wrong scale, and the pre-existing "later filed wins" tie-break in `extract_period_values`
picks it over the correct value still sitting in an earlier filing. The fix that matches this shape
exactly: stop that one bad fact from ever reaching the tie-break, and let the correct one win
unchanged.

### The mechanism: `_KNOWN_BAD_FACTS` in `parsers/parse_edgar.py`

A dict keyed by `(ticker, tag)`, each entry a list of `{end, filed, val}` triples individually
verified against the raw cached JSON. `_drop_known_bad_facts()` runs once per ticker in
`build_dataframe()`, before any extraction, and removes only items matching **all three** fields —
not "any zero," not "any value over N," not "any fact for this ticker/tag" — so it is structurally
incapable of touching a fact that isn't individually listed. Zero heuristics, zero inference.

### Severity check on the other 14 `DividendsPerShare` tickers

Before finalizing scope, checked whether any of AVGO, CDW, EL, HBAN, HWM, KHC, LRCX, MA, MAS, NVDA,
ROST, SYK, UHS, XYL currently produce a distorted (million-scale) value the way ROK/STX do. None
do — for every one of them, a later, correctly-scaled filing already exists and already wins the
tie-break today (confirmed by calling `extract_quarterly_values` directly against each ticker's raw
JSON). A few show small negative values from an unrelated, pre-existing decumulation quirk (mixed
annual/quarterly tagging producing an odd Q4 delta) — not this bug, not touched, left as a
documented, separate, low-priority observation. None pulled into scope.

### What's actually in the drop-list

- **BAC, `Assets`**: one fact (`2008-12-31`, filed `2011-02-25`, `val=0`) — a 2011 10-K comparative
  restatement to exactly zero, when three earlier filings consistently reported $1,817,943,000,000.
- **ROK, `CommonStockDividendsPerShareDeclared`**: 10 facts across three consecutive fiscal-2019
  10-Qs (filed 2019-01-31, 2019-04-25, 2019-07-25), each of which reported *every* dividend figure
  in that filing — both the current quarter and the prior-year comparative, both the standalone
  quarterly figure and the fiscal-YTD cumulative figure — at exactly 1,000,000x scale. Only 3 of the
  10 were currently winning the tie-break (`2017-12-31`, `2018-03-31`, `2018-06-30`); the other 7
  self-corrected via a later filing already, but were dropped anyway since they're the same
  demonstrably-bad facts and leaving them in the raw data is a latent risk for no benefit.
- **STX, `CommonStockDividendsPerShareDeclared`**: 3 facts, all from the single FY2024 10-K (filed
  2024-08-02), which reported the current and two prior fiscal years' annual dividend totals all at
  1,000,000x scale. Only 1 (`2022-07-01`) was currently winning; the other 2 (`2023-06-30`,
  `2024-06-28`) had already self-corrected via a later 10-K.

### A side effect worth naming: ROK's `2018-09-30` Q4 also self-corrected

`decumulate_period_values` derives a missing Q4 as `annual − (Q1+Q2+Q3)`. With the bad Q1/Q2/Q3
values in place, ROK's FY2018 Q4 computed as `3.51 − 3,510,000 ≈ -3,509,996.49` — an impossible
negative dividend. Dropping the three bad quarters fixes this derived value too, automatically, with
no separate entry needed in the drop-list: `0.835 + 0.835 + 0.92 = 2.59`, `3.51 − 2.59 = 0.92`, a
sane result matching the surrounding quarters. Not something the task asked for explicitly, but
confirmed correct and left in place — the same "verify, don't just accept the absence of an error"
standard used for every fix in this project.

### Non-regression

Extracted every concept for every one of 323 cached tickers, before vs. after. **6 rows changed,
all explicitly in scope, everything else byte-identical:**

| Ticker | Concept | End | Before | After |
|---|---|---|---|---|
| BAC | Assets | 2008-12-31 | 0 | $1,817,943,000,000 |
| ROK | DividendsPerShare | 2017-12-31 | 835,000 | 0.835 |
| ROK | DividendsPerShare | 2018-03-31 | 835,000 | 0.835 |
| ROK | DividendsPerShare | 2018-06-30 | 1,840,000 | 0.92 |
| ROK | DividendsPerShare | 2018-09-30 | -3,509,996.49 | 0.92 (Q4-derivation side effect, see above) |
| STX | DividendsPerShare | 2022-07-01 | 2,769,997.93 | 0.70 |

Resulting metrics confirmed sane, not just non-`inf`/non-absurd: BAC's `equity_to_assets` is now
9.7%–11.4% across 2008–2009 (in line with every other quarter in its history); ROK's `payout_ratio`
runs 0.47–1.07 through the affected window (in line with its normal 0.4–1.0 range); STX's is 0.38 at
`2022-07-01` (in line with its steady ~0.33–0.51 range in adjacent quarters). KMB's single-filing
event, the other 14 `DividendsPerShare` tickers, and the scattered `BMY`/`CHD`/`COHR`/`KDP`/`MTD`/
`ZBH`/`ANET`/`TECH` cases are confirmed untouched — they don't appear anywhere in the 6-row diff,
remaining exactly as documented in the previous entry: real, confirmed, and deliberately left
unfixed.

---

## 2026-07-21 — Scale-outlier generalization attempt: scanned project-wide, shipped nothing, reverted cleanly

The `SharesOutstanding` scale-mismatch fix (`_normalize_scale_outliers` in `parsers/parse_edgar.py`)
was checked against every concept in `CONCEPT_CANDIDATES` and every profile override, not just the
two instances (`Assets`/BAC, `DividendsPerShare`/ROK+STX) found incidentally during the ratio guard
audit. The scan found the same tag-scale-mismatch signature in 11 more concepts. None of them got
the fix. Every one was tested against real data and rejected for a concrete, demonstrated reason —
this is a full changelog entry about **why nothing shipped**, not a summary of what did.

### Step 1 — full-universe scan

Replicated `extract_period_values`'s validity filter without its tie-break, keeping every raw
`(tag, end)` collision instead of silently resolving it, across all 323 cached tickers using each
ticker's own resolved `get_concept_candidates()` (so every profile's concepts were covered, not just
the base set). Flagged any collision where two on-file values differ by a near-exact power of ten
(tight log10 residual, same sign — the same signature already confirmed for `SharesOutstanding`,
`Assets`, and `DividendsPerShare`).

After filtering out coincidental ~10x differences from real restatements (a real business change
essentially never lands on a *clean*, low-residual power-of-ten ratio — confirmed by checking sign:
several `~9-11x` "matches," like CVS 2018-06-30 and MGM 2011-12-31, had a sign flip alongside the
magnitude change, which a genuine scale bug never has), confirmed genuine bugs remained in:
`DividendsPerShare` (16 tickers — AVGO, CDW, EL, HBAN, HWM, KHC, LRCX, MA, MAS, NVDA, ROK, ROST, STX,
SYK, UHS, XYL), `DepreciationAndAmortization` (BMY, CHD, COHR, KDP, KMB), `Capex` (ACGL, KMB, NCLH),
`Goodwill` (KMB, MTD), `LongTermDebt` (KMB, ZBH), `NetIncomeLoss` (ANET, KMB), `OperatingIncomeLoss`
(KMB, TECH), `CashAndEquivalents` (KMB), `OperatingCashFlow` (KMB), `Revenue` (KMB), `StockholdersEquity`
(KMB). KMB shows up in nearly every concept for the exact same two dates (2009-03-31, 2010-03-31) —
one filing (2010-05-07, later corrected 2010-05-14) that reported nearly every dollar figure in
thousands instead of dollars, not eight separate bugs. `Assets` had zero power-of-ten matches — its
one confirmed instance (BAC) is a filer error reporting an exact `0` for a real, large, historically
consistent value, a different signature entirely (see below).

### Step 2 — the assumption checks, and why they failed

Extended `_normalize_scale_outliers` with a per-concept candidate-factor override
(`_CONCEPT_SCALE_FACTORS`, since `DividendsPerShare` needed `10x` in its factor list — the default
list starts at `100x` specifically to avoid confusing a real stock split with `SharesOutstanding`,
but several genuine `DividendsPerShare` bugs, e.g. LRCX/NVDA/MA/MAS/AVGO, are exactly `10x`) and
added all 11 concepts to `_SCALE_CORRECTED_CONCEPTS`. Ran the full non-regression diff (all
concepts, all 323 tickers, before vs. after) before drawing any conclusion — and found two distinct,
serious failure modes, not the clean generalization hoped for:

**Dollar-magnitude concepts (`Goodwill`, `CashAndEquivalents`, `Capex`, `DepreciationAndAmortization`,
`LongTermDebt`, `NetIncomeLoss`, `OperatingCashFlow`, `OperatingIncomeLoss`, `Revenue`,
`StockholdersEquity`) are exactly the risk the task asked to check for — a real, legitimate large
jump (an acquisition, a restructuring) can exceed the mechanism's `32x` gate, and once it does, the
running anchor adopts the new, larger *real* scale and starts "correcting" every earlier, smaller,
equally-real value to match it.** Caught directly, not theoretically: ALGN's real 2009-2011 Goodwill
($478,000 — genuinely small, this was a small company) got inflated to $47,800,000 (100x); AMD's real
2009-2011 Goodwill ($323M) got inflated to $32.3B — a figure larger than AMD's entire market cap at
the time. Both are legitimate historical values, both got wrongly "fixed" once a later, real, much
larger Goodwill figure (from actual subsequent acquisitions) became the anchor. 1,397 rows changed
across 11 concepts and ~40 tickers in this first pass; a meaningful fraction were confirmed wrong the
same way as ALGN/AMD.

**`DividendsPerShare`, despite passing the raw-scan signature check cleanly, fails for a completely
different reason: `decumulate_period_values`.** This concept is not point-in-time, so it's run
through the same YTD-cumulative-to-quarterly-delta decumulation as flow concepts like Revenue.
Confirmed directly for GEN (Gen Digital, formerly NortonLifeLock): its 2016 fiscal-year-end change
produced a genuine "stub period" quarterly delta of **$4.15** at `2016-04-01` — not a real dividend,
a decumulation artifact, but only about 27x away from the surrounding ~$0.15 quarters, just inside
the `32x` gate. The sweep adopted it as the new anchor, and every subsequent real, correct
$0.075–$0.125/quarter value (36 quarters running, essentially GEN's entire post-2016 history) got
"corrected" upward by 100x to $7.50–$12.50 — a dividend GEN never paid. Confirmed the same pattern
for MGM (real $0.0025/quarter inflated to $0.25) and TPR (real value inflated 1,000x). This is a
**different** anchor-poisoning failure mode than the ones already hardened against for
`SharesOutstanding` (AIG's single garbage fact, WAT's poisoned seed) — here the poisoning value isn't
an obviously-wrong outlier or a boundary seed, it's a genuine but non-representative artifact that
sits just inside the existing gate. Even narrowing the fix to *only* `DividendsPerShare` (dropping
all 10 dollar-magnitude concepts) still produced this false correction for 4 tickers.

**`Assets` was never actually correctable by this mechanism at all.** BAC's confirmed instance is a
filer reporting an exact `0` for a period that three earlier, consistent filings reported at
$1,817,943,000,000. `_normalize_scale_outliers` works by finding a multiplicative rescale factor —
there is no factor that turns `0` into `$1.8T`; the sweep's own `if not val: continue` guard treats
zero as "no data" and passes over it untouched. This needs a structurally different mechanism (reject
an implausible zero surrounded by consistent large values), not a variant of this one.

### Step 3 — nothing shipped

Given both attempts (11 concepts, then narrowed to the 2 most textbook-looking ones) produced
confirmed false corrections on real data, and per this project's standing rule (`roe`/`payout_ratio`
in the immediately preceding task, `normalize_split_adjusted`'s WAT gap before that) to log an honest
negative result rather than ship a fix that trades confirmed real bugs for newly-broken real values —
**`_SCALE_CORRECTED_CONCEPTS` was reverted to `{"SharesOutstanding"}` and the per-concept factor
addition was removed.** `parsers/parse_edgar.py` is confirmed byte-for-byte reverted to its state
before this task (`_normalize_scale_outliers`, `_sweep_scale_outliers`, `_closest_scale_factor` all
back to their original signatures, `_CONCEPT_SCALE_FACTORS` no longer exists).

### Step 4 — non-regression

Full facts extraction (every concept, every one of 323 cached tickers) before vs. after: **0 rows
changed, 0 rows added, 0 rows removed** — confirming the revert is complete and this task shipped no
behavior change of any kind. BAC's `Assets` at `2008-12-31` is still `0` (its `equity_to_assets`
still `inf`); ROK's `DividendsPerShare` at `2017-12-31`/`2018-03-31`/`2018-06-30` is still
`835,000`/`835,000`/`1,840,000` (its `payout_ratio` distortion is unchanged). Both remain confirmed,
open, unfixed — reported here rather than papered over.

### What this leaves open

`DividendsPerShare` (16 tickers, ROK/STX among them), `Assets` (1 ticker, BAC), and the 9 other
dollar-magnitude concepts (mostly the single KMB filing event plus BMY/CHD/COHR/KDP/MTD/ZBH/ANET/TECH)
all have real, confirmed instances of a tag-scale or filer-error bug. None is safe to fix with
`_normalize_scale_outliers` as it exists today. A future fix would need either a decumulation-aware
guard (skip or flag stub-period deltas before they can poison an anchor) for `DividendsPerShare`, a
real-event-aware gate (e.g. cross-checking a large jump against a real M&A/restructuring signal, or
requiring corroboration from more than one subsequent period before trusting a new anchor) for the
dollar-magnitude concepts, or a dedicated "reject an implausible instant zero" rule for `Assets` — none
of which existed going into this task and none of which this task built, consistent with its own
explicit instruction not to force a fix that can't be validated.

---

## 2026-07-21 — Tier-1 ratio guard fixes: five metrics, three mechanisms, and two deliberately-not-fixed cases

The ratio guard audit (`ratio_guard_audit_report.md`) confirmed real, current explosions in seven
metrics. This entry covers the five that got a working fix; the other two (`roe`, `payout_ratio`)
were investigated just as thoroughly and are documented below as **not fixed** — the obvious
mechanism was tested against real data and demonstrably doesn't generalize, and shipping it anyway
would have traded a small number of real explosions for a much larger number of newly-suppressed
legitimate values. Every threshold below was calibrated from where explosions actually cluster in
the full 323-ticker cache, the same discipline as every guard in this project.

### Fix 1 — `net_debt_to_ebitda`: absolute EBITDA floor (new, `min_denominator_abs=$10M`)

Unguarded; 53 confirmed explosions up to ±3,446x. Plotting caught-vs-collateral across a dollar
floor sweep showed no clean separation — a company's absolute EBITDA size just doesn't predict
whether its `net_debt_to_ebitda` reading is explosive (a mega-cap in earnings distress and a
small-cap mid-scaling both post tiny-dollar EBITDA). The curve does have a genuine elbow at $10M:
20 of 53 explosions caught (CRWD, DDOG, EFX, LYV, PANW, PODD, TTWO, EA, CIEN — all genuinely
tiny-dollar EBITDA, the classic near-zero-denominator case) for only 12 collateral rows; the next
$5M of floor buys just 2 more catches for 10 more collateral. The remaining 33 explosions (BA, WBD,
INTC, RCL, NCLH, LVS, WYNN, HLT, MAR, MAS, CAG, VTRS, STX, EL — all with EBITDA in the tens-to-
hundreds-of-millions) are a **different failure mode** — genuinely large debt against genuinely
compressed (but not tiny) earnings — that an absolute floor can't reach without masking thousands
of legitimate mid-cap ratios elsewhere. Left unaddressed, flagged for a scale-relative mechanism as
a follow-up, not force-fit into this one.

### Fix 2 — `debt_to_equity`: scale reference changed from `Revenue_TTM` to `LongTermDebt` (`roe` left unchanged)

The existing guard compared equity to Revenue — the wrong yardstick, since a company's equity can
be comfortably above 1% of revenue while still being tiny relative to its *own debt* (NCLH: equity
1.4% of revenue, 0.5% of debt). Changed `min_denominator_scale_ref` to `LongTermDebt` (the ratio's
own numerator) and recalibrated `min_denominator_scale_ratio` to **0.05** — chosen because it
reproduces the audit's own `>20x` explosion boundary exactly (`equity < 5% of debt ⟺ debt/equity >
20`), so it catches all 68 confirmed explosions with **zero collateral by construction**. As a
bonus, it also *unmasked* 5 values the old Revenue-based guard was incorrectly suppressing (e.g.
MAR 2023-03-31: debt_to_equity 0.40, an entirely normal reading, previously hidden only because
equity was small relative to Marriott's asset-light revenue, not because the ratio itself was bad).

**`roe` was left unchanged.** The obvious parallel move — reference `NetIncomeLoss_TTM` — was
tested and rejected: of the 129 remaining `roe` "explosions," 118 are positive and belong to
famous, real high-ROE buyback names (HD, MCD, ORLY, LMT, LLY, PM, LOW, CLX, KMB, GDDY, FTNT, MSI,
VRSK, MTD — a company generating strong profit against equity kept thin by decades of buybacks is
exactly what "high ROE" means, not a broken ratio). A NetIncomeLoss-based guard would suppress
nearly all of them. The 11 negative cases (NCLH, WYNN, CIEN, ADSK, QCOM, PANW) trace to real,
documented one-time events (COVID losses, ADSK's subscription-transition writedown, QCOM's 2018
Apple-dispute charge) at similarly-thin-but-real equity — mathematically symmetric with the
positive cases, so there's no principled sign-based cut either. `Assets` was checked as an
alternative reference and isn't populated outside the banking profile, so it isn't universally
usable. Conclusion: `roe`'s remaining explosions are the same "real but extreme" class as URI's
`capex_intensity` and VRTX's `rd_intensity` — confirmed real, not a guard gap, left alone.

### Fix 3 — `operating_margin` / `fcf_margin`: self-referential revenue-scale guard (new function, `apply_self_relative_scale_guard`)

New mechanism in `metrics.py`: for each `(ticker, end)`, compare `Revenue_TTM` against the max of
its own **±8-quarter centered rolling window** (not a fixed dollar floor — company sizes vary too
much — and not a whole-history max, which broke on the first real test below); mask when current
revenue is under **10%** of that window's peak. A window, not a whole-history reference, was
required specifically because of a real counter-example found during calibration: HIG's `Revenue`
tag genuinely steps down ~13x in 2018 (Talcott Resolution divestiture, a real corporate event, not
a data bug) and never recovers — a whole-history-max reference would have permanently flagged every
quarter since 2019 as "collapsed," when the post-divestiture business is simply operating at a
smaller, stable, entirely legitimate scale. A bounded window naturally stops reaching back into the
stale pre-divestiture regime once enough time has passed, catches the divestiture's own transition
quarters (2018Q4–2019, correctly ambiguous), and leaves 2021 onward alone.

Verified against every named case: CCL/NCLH/RCL's COVID quarters and VRTX's 2009–2011
pre-commercial era all land at 0.3%–9.4% of their own window peak (cleanly caught). SOFI's
fcf_margin explosion does **not** get masked, and correctly so — its ratio-to-window-max is 58%–100%
throughout; the explosion is driven by genuinely heavy cash burn against a normal, non-collapsed,
steadily-growing revenue base (real early-fintech economics, the same category as URI/VRTX, not a
denominator artifact). One incidental catch worth naming: LYV (Live Nation) 2021-03/06, a COVID
collapse that happened to fall just under the audit's original ±300% detection bar (margins of
-227%/-103%) but is the identical failure mode as the cruise lines — correctly caught by the new
guard even though it wasn't in the original flagged list.

### Fix 4 — `payout_ratio`: tested, does not generalize, **not fixed**

The same self-referential approach (compare `EPS_TTM_CALC` to its own scale) was tried across four
window sizes (±1 to ±8 quarters) and two statistics (max, median), plus a whole-history-max variant
— 12 configurations total. None separates the 42 genuine near-zero-EPS explosions (ROK's and STX's
9 rows are a `DividendsPerShare` scale bug, a different root cause, excluded from this count) from
ordinary EPS volatility: even the tightest possible threshold (0.1%) already produces more
collateral (16 rows) than catches (1), and every looser setting gets worse faster. Root cause: EPS
swings far more, and across a far wider dynamic range over a company's life, than Revenue does —
normal, healthy earnings growth alone can span 100x+ (a $0.02-EPS young company vs. its own
$2-EPS mature self), which any self-referential magnitude check mistakes for an explosion. Revenue
doesn't have this property, which is exactly why Fix 3 worked and this doesn't. `payout_ratio` keeps
its existing `require_positive_denominator`-only guard; the 42 genuine cases are reported as a
confirmed, unresolved gap for a future task with a different mechanism in mind.

### Fix 5 — `operating_leverage`: absolute output cap added (`max_abs_result=15`, new parameter on `calculate_ratio_from_dfs`), floor left at 0.02

Retightening the existing `min_denominator_abs` (revenue-growth) floor alone cannot work: eliminating
the last 21 of 125 confirmed explosions (`>20x`) this way requires raising the floor to 10%,
which masks 5,740 of 10,740 rows total — over half the universe — because 2–10% revenue growth is
completely ordinary. The real pattern (FDX, HPE, TSN: modest single-digit revenue growth divided
into operating-income growth sitting right at `calculate_growth`'s own ~200% ceiling) is a property
of the *ratio's own magnitude*, not cleanly attributable to either side alone — a 2D sweep over
both a revenue-growth floor and an operating-income-growth ceiling confirmed no combination cleanly
separates the tail either. Added `max_abs_result` to `calculate_ratio_from_dfs` and capped
`operating_leverage` at **±15** — chosen at the natural 97th–98th-percentile elbow of the real
distribution (90% of all values sit under 5.8x, 99% under 21.4x). An output cap is collateral-free
by construction: it only touches values already beyond the cap, unlike floor-tightening, which
would have masked plenty of ordinary low-growth quarters along the way.

### Non-regression (all 7 metrics, full 323-ticker cache)

Extracted all 7 metrics before/after: **0 changed values** among rows present in both (confirmed to
float precision), for every metric. Newly masked: `net_debt_to_ebitda` 32, `debt_to_equity` 68,
`operating_margin` 20, `fcf_margin` 27, `operating_leverage` 232, `roe` 0, `payout_ratio` 0 (as
expected — both left unchanged). `debt_to_equity` also newly *unmasked* 5 previously-wrongly-hidden
legitimate values (BA, LII, MAR, STX — see Fix 2). Every newly-masked row cross-checked against its
underlying facts; `capex_intensity` and `rd_intensity` (explicitly out of scope) confirmed
byte-for-byte unchanged; URI's real >100% `capex_intensity` and VRTX/REGN's `rd_intensity`
untouched. Full breakdown in `tier1_ratio_guard_fixes_report.md`.

---

## 2026-07-21 — Negative-equity-sign guard for `roe` / `debt_to_equity`: a different failure mode from near-zero

MCD's `StockholdersEquity` has been persistently, substantially negative since 2016-09-30 (as deep
as -$9.5B in mid-2020) — a large-magnitude, sustained condition, not a brief near-zero crossing
like ORLY's. The existing guard on `roe`/`debt_to_equity`
(`min_denominator_scale_ref="Revenue_TTM"`, `min_denominator_scale_ratio`) only masks when
`abs(denominator)` is *small* relative to revenue. It does nothing here, because MCD's negative
equity is large, not small. `roe` reached -675%, `debt_to_equity` around -30 — mathematically
well-defined, economically meaningless: both ratios are conventionally undefined when equity
itself is negative, independent of magnitude. Near-zero and large-negative are different failure
modes needing different conditions, and this project didn't have a guard for the second one yet.

### Scope check first: this is project-wide, not MCD-specific

Scanned every cached ticker across every profile for any period with negative `StockholdersEquity`.
**71 tickers across 11 profiles** have at least one such quarter — AZO's entire recent history
(68 quarters, -$5.2B min), BA (-$23.6B min, 34 quarters), PM (-$13.6B min, 56 quarters), HCA
(-$10.2B min, 61 quarters), DPZ (-$4.3B min, 63 quarters) among the largest. Given the scope, the
fix belongs in `main.py`'s base `roe`/`debt_to_equity` calculations, not a profile-scoped config
change — these aren't concepts a single profile owns.

### No new guard needed — an existing parameter already did this

`metrics.calculate_ratio()` already has `require_positive_denominator`, already used for
`payout_ratio`: it masks the denominator to `NaN` wherever it isn't strictly positive, before the
ratio is computed. Verified directly that this composes cleanly with the existing near-zero scale
guard (which runs afterward on the ratio Series) rather than assumed: where
`require_positive_denominator` already masked a value, the scale guard's own comparison
(`NaN < threshold`) evaluates to `False` and leaves the existing mask alone — the two guards don't
interfere, satisfying the "either condition masking is sufficient, neither replaces the other"
requirement without any new code. Added `require_positive_denominator=True` to both calls.

As a side effect this also masks exactly-zero equity (a division-by-zero, equally undefined) —
not something the task described, but clearly correct, and confirmed in the non-regression check
below as the one genuine edge case among the newly-masked values.

### Non-regression

Extracted `roe` and `debt_to_equity` for every cached ticker before and after: 0 new keys, 0
removed, **2,040 newly masked** (real value → `NaN`), 0 unexpected changes of any other kind.
Cross-checked every one of the 2,040 directly against the ticker's own raw `StockholdersEquity` at
that date: 2,039 are genuinely negative; 1 (VTRS, `debt_to_equity`, 2019-12-31) is exactly zero —
the division-by-zero case noted above, correctly masked by the same condition. No positive-equity
period changed anywhere. Full affected-ticker list in `negative_equity_guard_report.md`.

---

## 2026-07-21 — Twelfth stock-type profile: leisure batch (restaurants/hotels/cruises/casinos), and the first real use of the ticker-level override mechanism

Extended `leisure` from MCD alone to 12 tickers: SBUX, DPZ, CMG (restaurants), MAR, HLT (hotels),
CCL, RCL, NCLH (cruises), LVS, MGM, WYNN (casinos). `OperatingIncomeLoss` came back clean for all
12 (93-99%), same as MCD — checked per ticker rather than assumed, and this time the whole batch
genuinely does share the clean outcome.

### `FoodAndBeverageRevenue`: the ticker-level override mechanism's first real application

CMG's `Revenue` coverage was 53% — the base candidate tags only go back to 2016-12-31 for this
filer. The real pre-2017 tag is `FoodAndBeverageRevenue`, verified as CMG's full consolidated total
(exact match against `Revenues` at every shared date, e.g. 2016-12-31: both $3,904,384,000) — CMG
has only one revenue stream, so the tag captures all of it.

**Not safe to add profile-wide.** LVS, MGM, WYNN, and SBUX all carry this exact tag name too — and
for the casinos it's only the food & beverage *segment*, ~7-9% of total revenue (verified directly:
LVS 2009-06-30, `FoodAndBeverageRevenue` = $87M vs. consolidated Revenue = $1,059M). Same trap as
DHI/NVR's `InventoryRealEstateLandAndLandDevelopmentCosts` from the homebuilder profile — a tag
name that means the whole thing for one filer and a small component for another sharing the same
profile. This is the first case since `TICKER_CONCEPT_OVERRIDES` was built (see the entry below)
where that mechanism was actually needed for a new problem, not just applied to the case that
motivated it. Added `TICKER_CONCEPT_OVERRIDES["CMG"]["Revenue"]` with the full base tag list plus
`FoodAndBeverageRevenue`. CMG: 53% → 96%.

CCL's `Revenue` had a similar-shaped gap (68%, missing 2010-2015 entirely). Real tag:
`SalesRevenueServicesGross`, verified as CCL's full total (exact match at 2015-08-31: both
$4,883,000,000) — cruise lines have no other revenue category, so a "services" tag is their whole
business. Added as `TICKER_CONCEPT_OVERRIDES["CCL"]["Revenue"]` for consistency with the CMG case,
even though no other leisure ticker currently carries this tag. CCL: 68% → 96%.

### A guard that works, and one that's confirmed missing

Checked directly (not assumed) whether `revenue_growth`'s `min_base_ratio` guard suppresses the
nonsensical readings CCL/RCL/NCLH's COVID-era near-zero revenue would otherwise produce. It does:
`yoy_growth` correctly comes back `NaN` for all three exactly where 2022 recovery would divide
against a near-zero 2021 TTM base (e.g. RCL: $218M → $2,549M), and correctly stays visible for the
2020-2021 decline readings themselves, since those are real and meaningful, not artifacts.

`operating_margin` has no equivalent guard at all. Confirmed with real values: RCL -4,118%,
NCLH -9,510%, CCL -5,046%, all during the same COVID trough — mathematically correct, economically
meaningless. **Not fixed here** — the task asked to verify the existing guard, not build a new one
for a base metric used by every profile — but logged as a confirmed, open gap for future work.

### Scope breaks: one textbook, one different-shaped, one non-finding

- **HLT**: textbook signature — every 2015-2016 `Revenue` quarter restated on the *same* filing
  date (2017-05-24), consistent -36% to -37%. Matches Hilton's January 2017 spinoff of Park Hotels
  & Resorts (REIT) and Hilton Grand Vacations exactly.
- **LVS**: real, but a *progressive* restatement across four different filing dates
  (2021-04-23 through 2022-02-04) rather than one — each 2020 quarter's `Revenue` and
  `OperatingIncomeLoss` shrinks a bit further with each new comparative filing. Consistent with
  reclassifying the Las Vegas segment as held-for-sale ahead of the 2022 Apollo/VICI divestiture,
  not a single clean cutover.
- **MAR**: a real restatement (2017 quarters, -10% to -12%, filed in 2018) that isn't a spinoff at
  all — timing matches the 2018 ASC 606 adoption instead.
- **MGM, WYNN**: checked, no scope-break signature found in either `Revenue` or
  `OperatingIncomeLoss`, despite MGM's 2016 MGM Growth Properties REIT spinoff. A real non-finding.

### `rule_of_40`: hidden, same call as every profile but one

Computed across all 12 tickers' full history. Every median sits well under 40%; even LVS (best
case, boosted by post-COVID Macau/Singapore recovery) only clears 40% in 32% of quarters — nowhere
near the ~93%-of-quarters bar that kept TTD under consideration in the media scan. Hidden
profile-wide. CMG's real, well-known growth story doesn't change the call: median 24.8%, never
crosses 40% at all in the cached history.

### Non-regression

Confirmed by direct construction that `get_concept_candidates()` is byte-identical for all 312
previously-cached tickers (none of this task's three config changes touch any pre-existing
ticker's profile or any shared config), then verified empirically across the full universe: 0
changed, 0 removed, 51 new fills, all on `CMG|Revenue`/`CCL|Revenue`. LVS/MGM/WYNN/SBUX's own
`Revenue` — the tickers that also carry `FoodAndBeverageRevenue` but where it means something
narrower — checked explicitly and confirmed untouched.

---

## 2026-07-21 — SharesOutstanding: a new pattern class, a single filer reporting the same fact at two scales

MCD's `SharesOutstanding` alternated between ~751,900,000 and ~751.8 for the same real
figure, at different filed dates for the same reporting period — not a clean unit-conversion
factor, and not the same-name-different-scope trap (CAT/PCAR/TXT, DHI/NVR) either. Investigated
down to the mechanism rather than assumed: this is neither of the two hypotheses the task
itself raised.

### Not two tags — one tag, two scales

Checked every raw fact for `WeightedAverageNumberOfDilutedSharesOutstanding` directly. The unit
is `shares` in every single fact, before and after. The `val` field itself just changes scale:

```
end: 2021-12-31  val: 751800000   filed: 2022-02-24  (FY2021 10-K)
end: 2021-12-31  val: 751800000   filed: 2023-02-24  (FY2022 10-K, comparative)
end: 2021-12-31  val: 751.8       filed: 2024-02-22  (FY2023 10-K, comparative)
```

MCD switched, starting with filings filed in 2024, to expressing this fact in millions while
leaving the `shares` unit tag unchanged. `extract_period_values`'s existing tie-break for a
`(tag, end)` collision (`is_point_in_time` branch, same `days`: later `filed` wins) was built for
genuine restatements, where the later filing is definitionally the more accurate one. Here it
just means the *smaller, wrong-scale* number always wins once one exists, since it's always the
one most recently filed. Confirmed genuinely different in shape from every restatement pattern
logged so far: a real restatement changes a value by a modest percentage or a small integer split
ratio; this changes it by a clean power of ten, for the exact same fact.

### Systemic, not MCD-specific

Scanned every cached ticker (311, not just the 4 profiles the task asked for a sample of) for the
same signature. **41 tickers across 11 profiles** — including all four the task named (`standard`,
`financial`, `retail`, `pharma_medtech`) plus `consumer_staples`, `health_services`, `homebuilder`,
`industrials`, `insurance_pc`, `leisure`, `media` — carry at least one instance. Scale factors seen:
100x, 1,000x, 10,000x, 1,000,000x, 10,000,000x (KO, MRK, MO, TXN, GLW, L, HIG all show a clean
1,000,000x; CLX, HSY, NVDA, GRMN, TSCO, WRB and others show 1,000x; VTRS shows 10,000,000x). This
is a fallback-list problem nowhere near unique to `SharesOutstanding` in principle — it can happen
to any concept whose `val` a filer re-expresses at a different decimal scale — but `SharesOutstanding`
is the only concept where it was actually observed in this project's data.

### Fix: a general-purpose scale-outlier corrector, added once, applied narrowly

Added `_normalize_scale_outliers()` in `parsers/parse_edgar.py`, wired into `build_dataframe()` for
concepts in `_SCALE_CORRECTED_CONCEPTS` (currently just `SharesOutstanding`). Runs two chronological
sweeps (forward and backward), each keeping a running "anchor" log10 that updates to whatever value
was just accepted — a correction one step propagates as the reference for the very next step, so an
arbitrarily long run of consecutive bad-scale quarters (MCD's later history is uncorrected in *every*
filing from 2023-12-31 on — there's no competing good value left to fall back on) resolves in one
linear pass, not one pass per quarter in the run. A value is only ever scaled *up*, and only when it
sits far below (at least ~32x) its neighbors' scale; a value far *above* is left untouched and never
adopted as the anchor.

Three real failure modes surfaced and were fixed before this design was trusted, each caught by
testing against real tickers rather than assuming the design was safe:

1. **Bucket rounding picks the wrong factor at a boundary.** HIG's 2009 values (321, 325, 356 —
   meant to be ~320.8M, ~325.4M, ~356.1M) sit close enough to a rounding boundary that an earlier,
   cruder version (matching on rounded `log10` magnitude buckets) settled for a 100,000x fix instead
   of the correct 1,000,000x. Fixed by matching on continuous `log10`, picking whichever factor is
   numerically *closest*, not the first one that lands in the same bucket.
2. **A real split must never be mistaken for this bug.** TTD's 2014-2016 pre-IPO share count
   (tens of millions) is real, correct, and simply smaller than its post-2021-10-for-1-split era —
   not a scale artifact. `_SCALE_UP_FACTORS` deliberately starts at 100x, not 10x, specifically so a
   real 10-for-1 split (numerically indistinguishable from a "reported in tens" artifact by ratio
   alone) is never misfixed; no genuine artifact anywhere in this project's data needed a factor
   under 100x.
3. **A lone garbage fact must never poison the anchor.** AIG has one real XBRL fact reported at
   ~1,000,000x its true value for exactly one quarter — an unrelated, pre-existing SEC data error,
   not this project's scale-mismatch pattern. An early version let any accepted value become the new
   anchor unconditionally; that one fact turned every genuinely correct quarter afterward into an
   apparent "artifact" relative to itself, cascading the corruption through AIG's entire history.
   Fixed by only ever adopting a value as the anchor if it's within the same ~32x band as the
   current anchor — a value far outside that band is left alone and never trusted as a reference.
   WAT has the same kind of lone garbage fact at its single most recent quarter, which is the very
   first thing a backward sweep would otherwise see and seed the anchor from; the seed itself is now
   the median of the first several values in each direction, not just the first one, so a single
   boundary-adjacent garbage point can't set the anchor either.

**Verified via the elevated non-regression check the task required**: extracted every concept for
every cached ticker (311, all profiles) before and after. **0 changed, 0 removed, 162 new/corrected
values across the 41 affected tickers, 0 changes to any other ticker or concept** — the change is
purely additive (`build_dataframe`'s loop is identical for every concept except `SharesOutstanding`,
where one conditional post-processing call was added), so nothing outside `SharesOutstanding` could
regress by construction, confirmed empirically anyway.

### A related, confirmed-but-unfixed bug found along the way: `normalize_split_adjusted`

WAT's lone garbage quarter (above) isn't just an extraction-layer risk — the same failure mode
already exists, unfixed, in `metrics.py`'s `normalize_split_adjusted()`. That function anchors
each series on its single most recent value (`values.iloc[-1]`) with no plausibility check at all,
by design (see the ServiceNow entry below: a median or windowed anchor was tried once already and
rejected, because a real split's recent tail can have the *stale* pre-split value in the majority —
using anything but the literal last value broke that case). WAT's garbage last-quarter fact
(~1,000x its true value) currently gets adopted as this anchor unconditionally, then
`COMMON_SPLIT_FACTORS`' best-effort matching (no tolerance gate) rescales WAT's entire real,
multi-year share-count history to the closest available multiple of that one bad number —
confirmed directly: running the current, unmodified function against WAT's real cached data
turns its genuine ~60-100M share count into ~3-5 billion across nearly the whole series.

**Not fixed in this task.** Three different repair attempts were tried and each introduced its own
regression before being caught: a trailing-median anchor defeats the ServiceNow precedent outright
(confirmed directly against NOW's own cached data: its real recent tail has the stale, pre-split
value in the majority within a 5-quarter window, so a median anchor picks the wrong side — the
existing single-last-value design is deliberate and correct for that case, not an oversight); adding
a match-confidence tolerance to the existing single-last-value anchor is directionally correct and
does protect WAT, but the tolerance also rejects real, correct split-adjustments for tickers with
long histories and heavy accumulated buybacks (confirmed against AAPL: a genuine ×2 match against
its real anchor has ~15.4% error, only barely outside a 15% tolerance, and 154 other real tickers
shifted too) — no tolerance value tried was loose enough to keep AAPL correct and tight enough to
keep WAT protected. This needs a fix that can tell "no clean match exists because the anchor is
garbage" apart from "no clean match exists because of a decade-plus of real buybacks" — genuinely
harder than it looks, and not something to ship half-verified. Logged here as a confirmed, open,
separate bug for dedicated follow-up, per this log's own rule: an ambiguous fix that can't be
cleanly validated doesn't get shipped on a guess.

### Pattern-class note for future work

This is the first instance in this log of a fallback list correctly resolving to *one* tag whose own
reported value silently changes scale across filings — distinct from a missing tag, a same-tag-
different-scope mismatch, and a real corporate action. Worth checking proactively on other
pipeline-wide base concepts (`Revenue`, `NetIncomeLoss`) even without a visible symptom yet, since
the failure is invisible until a chart happens to make the resulting near-zero or absurdly large
value obvious — exactly how MCD's case was first noticed and none of the other 40 were, until this
task's full-universe scan.

---

## 2026-07-21 — Ticker-level concept overrides: a resolution layer below the profile

Every prior tag fix in this project lived at one of two levels: `CONCEPT_CANDIDATES` (base,
every ticker) or `PROFILE_CONCEPT_OVERRIDES` (one profile, every ticker sharing it). The
homebuilder scan surfaced a case neither level could handle: NVR's `Inventory` genuinely exists
under `InventoryRealEstateLandAndLandDevelopmentCosts`, but that exact tag name is a
**land-only component**, not the consolidated total, for DHI — which shares NVR's
`homebuilder` profile. Adding it profile-wide would have silently understated DHI's inventory
by ~50% in every gap quarter it filled (confirmed at FY2017-Q3: $4.5B vs. DHI's real $9.2B).
There was no way to give NVR this tag without exposing DHI to that risk, because the codebase
had no concept of an override that sits *below* the profile level and is invisible to every
other ticker. This is the third confirmed instance of the same pattern class — a tag name that
means one thing for one filer and a narrower thing for another — after the Kroger FIFO/LIFO
substitution (rejected outright, no fix existed) and the CAT/PCAR/TXT captive-finance overlap
check. The first two were caught-and-rejected; this one motivated building a mechanism instead,
because the safe tag genuinely exists — it just needed a narrower place to live.

### The mechanism

Added `TICKER_CONCEPT_OVERRIDES` to `config.py`, resolved in `get_concept_candidates()` after
`PROFILE_CONCEPT_OVERRIDES`:

```python
def get_concept_candidates(ticker: str) -> dict:
    profile = TICKER_PROFILES.get(ticker, DEFAULT_PROFILE)
    overrides = PROFILE_CONCEPT_OVERRIDES.get(profile, {})
    resolved = dict(CONCEPT_CANDIDATES)
    resolved.update(overrides)
    resolved.update(TICKER_CONCEPT_OVERRIDES.get(ticker, {}))
    return resolved
```

A ticker-level entry is a **complete replacement** for that ticker/concept, not merged with the
profile-level entry — same full-replacement semantics `PROFILE_CONCEPT_OVERRIDES` already has
over `CONCEPT_CANDIDATES` (the `.update()` gotcha documented in the homebuilder `LongTermDebt`
near-miss applies identically here: a ticker override must list every tag it wants, since
nothing from the profile level carries over underneath it). This is deliberate — the entire
point is isolating NVR's tag from DHI's shared profile list, so a ticker-level override must
never leak into or combine with the profile-level fallback chain for the same concept.

`get_expected_concepts()` needed **no separate change**. It already derives its concept set from
`get_concept_candidates(ticker).keys()`, and since `get_concept_candidates()` now folds in
`TICKER_CONCEPT_OVERRIDES` before returning, any ticker-level override — whether it replaces an
existing concept's tags (NVR's case) or, hypothetically, introduces a wholly new one — is
automatically visible to coverage scans with no second place to keep in sync. Two update sites
for one resolution chain is exactly the kind of drift this project avoids everywhere else; a
single merge point was preferable to threading the same lookup through both functions.

`PROFILE_EXCLUDED_CONCEPTS` was left without a ticker-level equivalent, per the task's own
default assumption — no concrete need surfaced while implementing this one case.

### Applied to NVR, and only NVR

```python
TICKER_CONCEPT_OVERRIDES = {
    "NVR": {
        "Inventory": {
            "tags": ["InventoryRealEstateLandAndLandDevelopmentCosts"],
            "point_in_time": True,
            "mode": "fallback",
        },
    },
}
```

NVR's `Inventory`: 0/69 → 57/69 quarters, 2011–2025, values $70M–$91M — matching the diagnosis
already logged in `homebuilder_scan_report.md`.

### Non-regression (elevated scope: full cached universe, every concept, every profile)

Because this changes a function every ticker's tag lookup runs through, the check covered all
311 cached tickers' full concept sets under quarterly extraction, not just `homebuilder`'s four:

- **Mechanism-only change** (empty `TICKER_CONCEPT_OVERRIDES`, resolution logic added):
  confirmed a byte-identical no-op before NVR's entry was added — `dict.update({})` is a no-op
  by construction, verified directly rather than assumed.
- **NVR's entry added**: 239,421 → 239,478 values. **0 changed, 0 removed, 57 new** — every one
  of the 57 on `NVR|Inventory`, nothing else anywhere in the universe. DHI's own 42
  `Inventory` values (and PHM's 65, LEN's 10) checked explicitly and confirmed byte-identical
  before/after, not just inferred from the aggregate diff — this was the specific risk the
  mechanism exists to prevent, so it was verified directly per the task's instruction rather
  than trusted on the strength of the isolation design alone.

## 2026-07-20 — Eleventh stock-type profile: homebuilder, replacing a profile built entirely from guessed tags

`homebuilder` is the first profile in this project where the existing `PROFILE_CONCEPT_OVERRIDES`
entry was already wrong going in — built from plausible-sounding tag names
(`InventoryRealEstate`/`RealEstateHeldforDevelopment`, `HomebuildingCostOfSales`, etc.) that were
never checked against a real filing. Running DHI against them produced near-total misses:
`AccountsPayable`/`AccountsReceivable`/`OperatingIncomeLoss`/`LongTermDebt` all 0%, `CostOfRevenue`
13%. Every one of this log's usual disciplines (check the real tag, verify magnitude at overlap
points, two-step byte-identical-then-add) applied here for the first time to a full profile
rebuild rather than a coverage gap.

### DHI's real tags, found by reading the actual filing data

- **`CostOfRevenue`**: the guessed `CostOfRealEstateRevenue`/`HomebuildingCostOfSales` only ever
  covered a narrow 2016–2019 transition window (`HomebuildingCostOfSales` doesn't even exist as a
  tag DHI has ever used). The real, dominant, modern tag is plain `CostOfRevenue` — 39 unique
  quarters, 2016–2026, not in the candidate list at all. Verified against `HomeBuildingCosts` at
  their one shared fiscal year (FY2016: $9,502.6M vs. $9,403.0M) — close but not identical, exactly
  as expected since `CostOfRevenue` is the *consolidated* total (homebuilding + financial services)
  and `HomeBuildingCosts` is the homebuilding segment alone. Confirms `CostOfRevenue` is the right
  concept-level match, not a coincidence. 13% → 54%.
- **`LongTermDebt`** (0% → 87%): DHI tags debt under `NotesPayable`, not `LongTermDebt` (which DHI
  has never used at all) — 61 quarters, 2010–2026. Added as this profile's first `LongTermDebt`
  override.
- **`AccountsReceivable`** (0% → 50%): the guessed `AccountsReceivableNetCurrent` doesn't exist for
  DHI. The real tag is `AccountsAndNotesReceivableNet` — and checked directly rather than assumed,
  per the task's explicit instruction: this is **not** the near-zero case it might look like for a
  homebuyer-mortgage-settlement business. Real values, $60M–$164M, a genuine receivable line (likely
  the financial-services/title segment or builder-to-builder land sales) that the original guess
  simply missed entirely. Same "checked, found real data, not near-zero" outcome as 6 of 7 "expected
  near-zero" cases in the original retail scan.
- **`AccountsPayable`** (0% → 50%): `AccountsPayableCurrent` doesn't exist for DHI either. Real tag:
  `AccountsPayableCurrentAndNoncurrent` ($580–634M, FY2017–19). Two other payable-adjacent tags were
  checked and rejected: `ConstructionPayableCurrentAndNoncurrent` is a genuinely separate, smaller
  liability (~$25–62M same years — a subcontractor-retention line, not overlapping AP), and
  `AccountsPayableAndAccruedLiabilitiesCurrentAndNoncurrent` is ~2.5–3x larger ($1.57–1.91B same
  years) — AP plus accrued liabilities combined, rejected as too broad, same "don't combine
  deliberately separate concepts" rule as always.
- **`Inventory`**: the guessed tag (`InventoryRealEstate`) turned out to be *correct* — confirmed
  by checking it actually resolves to real, substantial values ($3.4B–$11.6B, matching D.R. Horton's
  real balance-sheet scale), not silently resolving to nothing, per the task's explicit "verify,
  don't assume it's working just because it's not in the flagged list" instruction. The two
  additional guessed tags alongside it (`RealEstateHeldforDevelopment`,
  `InventoryRealEstateHeldforDevelopment`) don't exist for DHI at all and were dropped as dead
  weight.
- **`OperatingIncomeLoss`** (confirmed 0%, no fix): checked directly rather than assuming this is
  another instance of the by-now-eleven-times-confirmed diversified-conglomerate pattern. It isn't
  the same shape — DHI simply has no `OperatingIncomeLoss` tag under any name, likely because
  capitalized interest costs blur the operating/non-operating line enough that homebuilders commonly
  skip a discrete operating-income subtotal. Confirmed the mechanism is different even though the
  outcome (0%) looks the same as JNJ/HON's.

Applied with the two-step discipline the task explicitly called for, since this profile's overrides
had never actually been through a real non-regression check: Stage B1 (dropping the three
confirmed-dead guessed tags, no additions yet) verified byte-identical — a true no-op, since dead
tags never matched anything to begin with. Stage B2 (the real replacements above) produced 0
changed, 0 removed, 160 new fills, all DHI.

### A tag that's the right fix for two tickers and the wrong fix for two others

Extending to LEN, PHM, NVR surfaced a genuine cross-ticker naming split: DHI uses
`InventoryRealEstate`; LEN and PHM instead use `InventoryOperativeBuilders` (65/70 quarters for
PHM, 2009–2026 — a clean, near-complete match; only 12 gapped quarters for LEN's own filing
history, no better alternative found). Added as a second Inventory fallback tag — safe for DHI
(which has never used this tag name) and immediately fixed PHM's Inventory from 0% to 93%.

**A near-miss caught before it shipped**: `InventoryRealEstateLandAndLandDevelopmentCosts` looked
like NVR's answer — NVR has no `InventoryRealEstate` or `InventoryOperativeBuilders` at all, and
this tag gives 57 clean quarters, 2011–2025, with genuinely small values ($70–91M) consistent with
NVR's lot-option business model. But checked for overlap before adding it to the shared profile
list — and DHI *also* has this exact tag, where it's a **land-only component** roughly half of
`InventoryRealEstate`'s total ($4.5B vs. $9.2B at FY2017-Q3). Adding it as a profile-wide fallback
would have silently substituted a ~50%-too-low value into every one of DHI's 28 gap quarters,
looking like real data. **Not added.** This is the same shape as the CAT/PCAR/TXT captive-finance
finding and the FIFO/LIFO trap before it: a tag name that means one thing for one filer and a
narrower thing for another, caught by checking magnitude at every overlap rather than trusting a
tag name that worked once. NVR's `Inventory` stays at 0% — confirmed real, structurally different
data exists, but can't be safely wired into a profile shared with DHI/PHM without a per-ticker
override mechanism this codebase doesn't have.

### NVR: genuinely different, not broken — confirmed rather than assumed either way

The task flagged NVR as a known structural outlier (lot-option contracts instead of owned land, an
unusually asset-light balance sheet) and asked to distinguish a real business-model difference from
a missing-tag problem rather than assume either. Checked every flagged concept individually:

- **`LongTermDebt`** (3%, 2 points): `LongTermDebt` ($600M, 2013) and `SeniorNotes` ($599M, 2012)
  each appear exactly once, then never again. Consistent with NVR's real reputation as one of the
  most conservatively-financed homebuilders — essentially debt-free since the early 2010s. Confirmed
  genuine, not a gap.
- **`Inventory`** (0%, real tag exists but unshareable — see above): genuinely ~100x smaller than
  DHI/LEN/PHM's inventory scale, consistent with not owning land directly.
- **`CostOfRevenue`, `AccountsReceivable`, `AccountsPayable`, `DividendsPerShare`** (all 0%): searched
  exhaustively, no tag of any kind exists for any of the four. NVR has never paid a dividend (real,
  confirmed policy — buybacks only), and its cost-of-revenue/AR/AP presentation apparently doesn't
  use any of the standard tag names checked across this entire project so far.

### operating_margin / net_debt_to_ebitda / ev_ebitda: the health_services precedent, inverted

Checked `OperatingIncomeLoss` per ticker rather than assuming all four share DHI's outcome, per the
task's instruction — and the split is real: LEN tags it cleanly (144 raw points, not flagged at
all); DHI, PHM, and NVR all have zero. Same evidence-gathering method as the health_services
decision, opposite conclusion: there, 5 of 6 tickers were clean, so the metrics stayed visible; here
only 1 of 4 is, so **`operating_margin`/`net_debt_to_ebitda`/`ev_ebitda` are hidden profile-wide**.
`OperatingIncomeLoss` excluded from `get_expected_concepts` for the same reason `pharma_medtech`
excluded it — nothing visible depends on it for any of the four tickers once the dependent metrics
are hidden, including LEN, whose own coverage was already fine.

### A real business event correctly *not* flagged as a scope break

LEN's `InventoryOperativeBuilders` shows $20.3B (FY2024) dropping to $11.8B (FY2025), a 42% swing —
checked against the same same-filing-date-restatement detector used for HON/MMM/NWSA. It doesn't
match that signature: both values were filed for the first time in the same (most recent) 10-K, not
a later revision of a previously-different-reported figure. Consistent with a real, one-time event
— Lennar's February 2025 Millrose Properties land-banking spinoff — reflected as a normal sequential
value change, not a retroactive restatement. Correctly not flagged as a scope break; noted as
real-business-event context instead.

### Non-regression

Full before/after diff across the entire cached universe (308 → 311 tickers as DHI/LEN/PHM/NVR were
added): 0 changed, 0 removed, 2,169 new fills, all four homebuilder tickers. DHI's own facts
verified byte-identical between the Stage B2 checkpoint and the final config (confirming the later
`LongTermDebt`/`Inventory` tag additions — made for LEN/PHM/NVR's benefit — are true no-ops for DHI,
since it has never used either of the newly-added tag names).

## 2026-07-20 — Tenth stock-type profile: media, a dividend that exists but can't be extracted, and rule_of_40's one real exception

14 tickers (DIS reference + 13 new). `media` is the first new profile in this project where the
anchor ticker showed **no** `OperatingIncomeLoss` fragility at all — `operating_margin`,
`net_debt_to_ebitda`, `ev_ebitda` all came back clean for DIS, and no `PROFILE_CONCEPT_OVERRIDES`
entry was needed going in. One real problem surfaced instead: a genuine, currently-paying dividend
that the pipeline could not see.

### DIS's dividend: the data exists, the tag is right, and it's still unextractable

Disney suspended its dividend in May 2020 and resumed it in January 2024 ($0.30/share, raised
twice since to $0.75). `dividend_yield` showed zero coverage across the entire 2022–2026 window
despite this being public, confirmable, ongoing history — not an "expected suspension gap."

Checked the raw facts directly rather than guessing at a missing tag. DIS's resumed dividend *is*
tagged, under the *same* two candidate tags already in the base config
(`CommonStockDividendsPerShareDeclared`, `CommonStockDividendsPerShareCashPaid`) — the exact values
($0.30, $0.45, $0.50, $0.75) are sitting right there in the company-facts JSON. The problem is
structural: **every single one of the 19 post-2024 facts has no `start` date** — Disney switched to
tagging the dividend as a declaration-event fact (semi-annual, ~6 months apart: 2024-01-10,
2024-07-25, 2025-01-16, 2025-07-23, 2026-01-15) rather than a fiscal-period duration fact.
`extract_period_values` requires a `start` for any `point_in_time: False` concept (`if "start" in
item: ... else: continue` for duration concepts) — every one of these facts gets silently dropped
before extraction even begins.

This is the same root shape as the COO trap logged in the consumer_staples entry above (a
"declared" tag reported without duration attributes), but with an added wrinkle that rules out even
a workaround: DIS's declaration dates (Jan 10, Jul 25, ...) don't fall on fiscal quarter-ends, so
even flipping the concept to `point_in_time: True` for this profile (which *would* let the
no-start facts through, since `is_point_in_time=True` treats a missing `start` as automatically
valid) wouldn't fix the user-visible problem — the resulting `end` dates wouldn't align with the
quarter-end grid every other concept uses, so `calculate_ratio`'s inner-join merge for
`dividend_yield`/`payout_ratio` would still never find a match. **No tag or mode-level fix exists
for this without a broader "snap to nearest fiscal quarter" reconciliation step, which is out of
scope for a tag-coverage task.** Reported as a confirmed, well-understood, currently-unresolved gap
— a real dividend the pipeline structurally cannot see, not a missing tag.

### Two more confirmed instances of already-validated tags

- **Capex (EA, 4%→92%)**: `PaymentsToAcquireOtherPropertyPlantAndEquipment` — the same tag that
  fixed LLY (pharma_medtech) and ADP (industrials) — now a *third* confirmed instance, across a
  third sector. Exact match at the one overlap point (2010-06-30, $11M both tags).
- **CashAndEquivalents (FOX/FOXA, 16%→97%)**: `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents`
  — now a *fourth* confirmed instance (after TGT, GEV, CAT). Exact match at all 4 overlap dates.

Both added as a new `media`-scoped `PROFILE_CONCEPT_OVERRIDES` entry — the profile's first, per the
task's framing. Two-step discipline: Stage B1 (base-tag copies) verified byte-identical; Stage B2
produced 0 changed, 0 removed, 152 new fills across 6 tickers (EA, FOX, FOXA — targeted — plus OMC,
TKO, DIS as bonus beneficiaries of the cash tag).

### Dual-class tickers: verified identical, not assumed

FOXA/FOX and NWSA/NWS each share a single CIK (`0001754301`, `0001564708`) — confirmed the cached
`company_info.json` files are byte-identical between each pair before treating them as
interchangeable anywhere in this scan, rather than assuming from the shared-CIK fact alone.

### A scope break found where expected, and — just as informative — one that wasn't (yet)

**NWSA/NWS**: three consecutive fiscal years (FY2022, FY2023, FY2024) all restated on the same
filing date (2025-05-13) by consistent ~$1.83–1.95B deltas — News Corp's 2024 sale of Foxtel
(Australian pay-TV). Same signature discipline as the industrials entry (dollar deltas, not
percentages, to avoid false positives from routine presentation differences).

**TKO**: an unusual *positive* restatement — FY2022/2023 revenue jumped by +$1.53B/+$1.55B, filed
2025-03-19. Not a divestiture; the opposite shape, consistent with retroactive combined-entity
accounting following the September 2023 WWE/UFC merger (predecessor financials restated to reflect
the full combined entity). Named as a distinct pattern from the usual divestiture-shrink case, not
forced into the same bucket.

**WBD**: checked specifically, per the task's expectation that its 2025-announced two-company split
would show the same signature — it doesn't, not yet. `OperatingIncomeLoss` and `Revenue` are both
completely unrestated across every filing through 2026-02-27. The split was announced in 2025 but
hasn't closed; SEC filings only retroactively restate for discontinued operations after a
transaction actually completes (the same timing HON's Solstice restatement followed). A confirmed
non-finding, reported as "not yet" rather than silently assumed clean.

### rule_of_40: checked across the whole batch, not decided from DIS alone

Computed `rule_of_40` for all 13 new tickers plus DIS. Only **TTD** sits structurally near or above
the 40% line — 93% of its quarters ≥40%, minimum 37.5%, confirming the task's own hypothesis that a
higher-growth, asset-light platform would be the most plausible candidate. Every other ticker is
either consistently well below (DIS: 0% of quarters ≥40%, mean 13.9%; OMC, FOXA/FOX, NWSA/NWS all
similarly low) or swings too wildly to be structurally meaningful rather than noisy (NFLX 14%
≥40%; WBD 24% but ranging 3%–187%; TTWO 35% but ranging -62%–158%; LYV ranging -321%–175%).
**Hidden profile-wide** — same call as every other profile built so far. TTD's signal is real but
doesn't outweigh 12 other tickers' worth of noise, and `PROFILE_HIDDEN` has no per-ticker override
mechanism; documented as the one confirmed exception in `media_scan_report.md` in case a future
profile split ever separates high-growth ad-tech/platform media names from traditional media.

### Everything else: already-established patterns, not new ones

- **FOXA/FOX, NWSA/NWS — `OperatingIncomeLoss`, 0% each.** Neither tags the concept at all —
  confirmed via direct key lookup, not inferred from the coverage number. Same diversified-media
  "never tagged" shape as JNJ/ADM/EMR/etc., now confirmed a tenth-plus time.
- **FOXA/FOX — real dividend payer, never tagged per-share.** `PaymentsOfDividends` shows real,
  nonzero quarterly payments ($35–65M); no per-share tag exists anywhere. Same shape as HSY/TSN/DHR.
- **NFLX, TTD — no `Goodwill`; TTD — no `LongTermDebt` either.** Both are asset-light, minimal-M&A
  companies with no tag at all for either concept (not a `$0`-valued tag — a total absence).
  Consistent with real company history (Netflix's near-entirely-organic growth, The Trade Desk's
  minimal acquisitions and negligible debt) — same "confirmed absence, not a bug" pattern as
  GRMN/REGN.
- **EA — `LongTermDebt`, 31%.** Real debt history 2011–2017 (convertible notes), genuinely absent
  since — checked every debt-family tag EA has ever used, nothing post-2017. Not a gap, a real
  capital-structure change.
- **TKO — no `Capex` tag at all.** Consistent with its short combined history (formed September
  2023) — searched broadly (`PaymentsFor*`, `CapitalExpenditures*`), nothing found.
- **PSKY — everything thin (15–46%).** Paramount Skydance merger completed August 2025; only 13
  quarters of any kind of history exist. Same "young combined entity" shape as TKO, GEV, VLTO,
  SOLV in prior entries — not investigated ticker-by-ticker beyond confirming the short-history
  explanation covers the whole cluster.
- **TTWO — confirmed non-payer, contradicting the task's own premise.** The task's brief listed
  TTWO among "established payers" (OMC, EA, TTWO); checked directly and found no dividend tag of
  any kind for Take-Two. Reported as found, not silently corrected to match the brief's
  expectation — same discipline as the AZO/AccountsReceivable case in the retail scan.
- **TKO's one dividend data point ($3.86, FY2023)** is a predecessor-financials artifact from the
  WWE/UFC merger accounting, not an ongoing program — confirmed by checking for any subsequent
  quarter (none exist).
- **Content-asset amortization (NFLX, WBD, PSKY)**: noted but not investigated further per the
  task's own scoping — these companies capitalize large produced/licensed content libraries, which
  can make `DepreciationAndAmortization`-derived metrics (`ebitda`, `net_debt_to_ebitda`) behave
  differently than for an industrial-style company. No coverage problem found for any of the three,
  so no fix was needed; flagged as context for a future session if their EBITDA-based metrics ever
  look off.

## 2026-07-20 — An absolute-floor guard for operating_leverage, and CAT/PCAR/TXT deferred to a future captive-finance profile

Two independent fixes out of the industrials scan above, kept in separate non-regression scopes:
a guard on `operating_leverage`'s own near-zero-growth-rate explosion, and the removal of three
industrials tickers whose captive-finance subsidiaries make their consolidated figures unreliable.

### Part A — operating_leverage needed a different kind of guard than roe/debt_to_equity did

`operating_leverage = operating_income_yoy_growth / revenue_growth`. The 2026-07-15
`min_base_ratio` guard and the 2026-07-20 `MIN_DENOMINATOR_SCALE_RATIO` equity guard both compare
a *dollar* denominator against a dollar-denominated scale reference. `revenue_growth` is already a
*percentage* — there's no dollar figure to scale it against, so this needed a genuinely different
mechanism: an absolute floor on the denominator itself, not a relative-to-another-concept
comparison.

**Calibration, not guessing.** Pulled `revenue_growth` at every quarter across all 70 tickers then
still in `industrials` where `|operating_leverage| > 20` (an exploratory filter, not the final
threshold) — 165 rows. Median `|revenue_growth|` at those points was 0.53%; the worst cases (SWK's
literal `inf`/`-inf` at exactly 0.000%, MMM at 1400, RSG at -812) all sit under 1%. Extending the
filter to *every* row (not just the >20 ones) confirmed there's no clean bimodal gap the way IBM's
growth-rate case had for `min_base_ratio` — the distribution is continuous, same shape already
found for the equity guard's threshold search. Picked the threshold from the marginal-return curve
instead of a gap:

```
threshold   masked rows   catches |leverage|>20   catches |leverage|>50
1.0%        223 (7.0%)    103                     56
1.5%        332 (10.4%)   121                     60
2.0%        449 (14.0%)   135                     62
2.5%        554 (17.3%)   144                     64
3.0%        680 (21.2%)   149                     64
```

Beyond 2%, each additional 0.5pp of threshold buys almost no new extreme-value catches (2 more
`>50` cases, ever) while the masked-row count keeps climbing linearly — pure collateral damage.
**Chose 2% (`MIN_OPERATING_LEVERAGE_REVENUE_GROWTH = 0.02`)**: catches 91% of all `|leverage|>20`
cases and 97% of the truly extreme `|leverage|>50` cases, for 14% of rows masked rather than 21%.

**Implementation**: `calculate_ratio_from_dfs` gained an optional `min_denominator_abs` parameter
(off by default — same additive shape as every guard in this project) that masks the result
(`NaN`, not a dropped row) when `abs(denominator) < min_denominator_abs`. Passed only at
`operating_leverage`'s call site. Checked its two other callers before leaving them alone, per the
task's explicit instruction not to assume: `fcf_margin` divides by `Revenue_TTM` (a dollar figure
that essentially never hits zero for an operating company) and `net_debt_to_ebitda` divides by
`EBITDA_TTM` — also dollars, and where it *does* explode (Boeing, 11 quarters during the 737 MAX/
COVID era, `|net_debt_to_ebitda|` up to 94) the cause is a real earnings collapse, not a
percentage-denominator artifact. Neither shares the identical failure mode; neither was touched.

**Verified rather than assumed** the guard doesn't over-mask: HII (2014-06-30, 3.36% revenue
growth, leverage 20.0), IEX (2014-03-31, 5.84%, leverage 34.2), IR (2019-03-31, 7.05%, leverage
23.7), and GEV (2025-12-31, 8.97%, leverage 21.6) all survive untouched — real, large operating
leverage on real, measurable revenue growth stays visible, exactly the case the task's Step 3
warned against suppressing. Diffed old vs. new across the full set: 0 previously-populated values
changed, only masking occurred, 449 `(ticker, end)` pairs newly `NaN`, max `|revenue_growth|`
among them 1.99% (confirms the boundary is exact).

Of the task's own two motivating examples, both CMI quarters got masked; of CAT's two, only the
-1.39%-growth one did (the +2.47% one sits just above the 2% line and stays visible) — moot in
practice, since CAT leaves the `industrials` profile entirely in Part B below.

**Caveat, same as every threshold in this log**: empirically tuned against the current 70-ticker
`industrials` universe, not derived from a closed-form rule — may need revisiting as more tickers
are added, the same caveat carried by `min_base_ratio` and `MIN_DENOMINATOR_SCALE_RATIO`.

### Part B — CAT, PCAR, TXT removed from industrials, deferred to a future Group 5 profile

The industrials scan above flagged CAT's and PCAR's captive-finance subsidiaries (Cat Financial,
PACCAR Financial) as a likely source of consolidated-debt distortion, the same concern that kept
Ford and GM out of every profile built so far — their captive-finance arms (Ford Credit, GM
Financial) make consolidated debt/equity figures unrepresentative of the manufacturing business's
real leverage, so F/GM were earmarked for a future "Group 5: captive-finance archetype" profile
instead of being force-fit into `standard` or anywhere else. TXT (Textron Financial Corp) fits the
same shape and was flagged incidentally during the same scan.

Removed `"CAT"`, `"PCAR"`, `"TXT"` from `TICKER_PROFILES` entirely — not reassigned anywhere.
`TICKERS` in `config.py` was already just `["HON"]` (the scan's own reference ticker, not a live
production list) and never contained any of the three, so there was nothing to remove there; noted
rather than forced, since the task's premise assumed a fuller list that isn't this project's
current state. Verified via a full-universe facts diff (293 cached tickers, every profile): 0
changed, 0 removed, 0 new fills for every ticker other than the three removed — confirmed clean
end-to-end pipeline run across the remaining 67 `industrials` tickers, no crash, no orphaned
references anywhere in the codebase (grepped for `"CAT"`/`"PCAR"`/`"TXT"` outside scratch scripts).

**Group 5 backlog — captive-finance archetype tickers, no profile yet:**

| Ticker | Captive-finance subsidiary | Why it's deferred, not force-fit |
|---|---|---|
| F | Ford Credit | Consolidated debt/equity dominated by auto-lending book, not representative of the manufacturing business's real leverage |
| GM | GM Financial | Same shape as F |
| CAT | Cat Financial | Only long-term-debt tag (`LongTermDebtNoncurrent`) is annual-only for its entire 2008–2025 history and is almost certainly the full consolidated figure (~$22–38B) — industrial debt and captive-finance debt bundled with no non-dimensional way to separate them |
| PCAR | PACCAR Financial | No consolidated `LongTermDebt`-family tag exists at all, despite a large financing-receivables book (`PaymentsToAcquireFinanceReceivables`, 153 points) clearly present |
| TXT | Textron Financial Corp | No usable `Goodwill` or `LongTermDebt` tag either — same structural shape as CAT/PCAR, found incidentally during the industrials scan |

## 2026-07-20 — Ninth stock-type profile: industrials, a dead metric wired back in, and a confirmed cross-sector scope-break pattern

70 tickers (HON reference + 69 new). `industrials` reuses `standard`'s metric set and adds two new
metrics — `capex_intensity` and `operating_leverage` — built entirely from concepts already in
base `CONCEPT_CANDIDATES`; both were already implemented correctly going in (confirmed the prior
session's fix — `calculate_growth`'s missing `periods` argument and `calculate_ratio_from_dfs`'s
wrong column reference — was actually in place before touching anything).

### A metric that was computed every run and never once reached a chart

The task asked for a judgment call on whether `operating_income_yoy_growth` (the intermediate
growth rate feeding `operating_leverage`) adds standalone value once plotted. Tried to plot it —
and found it couldn't be: `calculate_all_metrics` computes `m["operating_income_growth"]` every
run, but `build_metrics_long`'s `spec` list never included it, and `figures.py`'s
`plot_fundamentals` never listed it either. The metric has been computed and silently discarded
every single run since it was added — the exact "fails silently, several layers from the cause"
pattern this whole log is about, just inside the metrics layer instead of the tag layer. Wired it
into both (`main.py`'s `spec` list, `figures.py`'s `concepts_to_plot`) so the judgment call could
actually be evaluated against real data, not guessed at.

### Once visible: it's the sane half of a routinely insane ratio

Plotted `operating_income_yoy_growth` against `operating_leverage` for six tickers. The pattern was
immediate and consistent: whenever `revenue_growth` (the ratio's denominator) sits near zero for a
quarter, `operating_leverage` explodes — CMI hit **+1039.88** one quarter and **-332.73** the next,
both attached to an `operating_income_yoy_growth` of a perfectly ordinary +113%/+139%; CAT and PH
swing similarly (CAT: +11.97 → -11.09 → +9.30 across three consecutive quarters). In every one of
these cases, `operating_income_yoy_growth` itself stayed a sane, readable percentage — it's
`operating_leverage`, not the growth rate, that's the unstable half of the pair. **Decision: keep
`operating_income_yoy_growth` visible for `industrials`** — hiding it would remove the only
context that lets a reader tell "real operating leverage story" from "ratio artifact from a
near-zero revenue-growth quarter" apart. Same near-zero-denominator failure class as the
`min_base_ratio` and `MIN_DENOMINATOR_SCALE_RATIO` guards already in this codebase — not fixed
here (out of scope for a tag-coverage task), but flagged as a real candidate for a future guard on
`operating_leverage` itself. Since the fix that wired the metric into `main.py`/`figures.py` is
global (not profile-scoped), `operating_income_yoy_growth` would otherwise have started appearing,
unfiltered, on every other profile's charts too — added it to all eight other profiles'
`PROFILE_HIDDEN` sets (alongside `capex_intensity`/`operating_leverage`, already handled there) so
only `industrials` shows it.

### Four tag fixes, three of them useful far beyond their original ticker

- **NetIncomeLoss (ITW, 0%→96%)**: ITW tags neither `NetIncomeLoss` nor
  `NetIncomeLossAvailableToCommonStockholdersBasic` — anywhere, ever. It uses `ProfitLoss` instead
  (net income including noncontrolling interest), confirmed by matching real reported figures
  ($2.1B–$3.5B, 2020–2025) rather than assumed from the tag name.
- **Capex (ADP, 0%→96%)**: same `PaymentsToAcquireOtherPropertyPlantAndEquipment` tag that fixed
  LLY's capex in the pharma_medtech entry below — confirmed useful for a second, unrelated company
  in a different sector.
- **CashAndEquivalents (GEV 0%→100%, CAT 38%→63%)**: same
  `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` tag that fixed TGT in the
  consumer_staples entry, now a *third* confirmed instance. Verified CAT's restricted-cash
  component is negligible (differences of a few million against multi-billion balances, <0.15%) at
  every overlap point before trusting it.
- **Revenue (PWR, 49%→95%)**: PWR's revenue was tagged as `SalesRevenueServicesNet` before its 2018
  ASC 606 transition, then switched to `RevenueFromContractWithCustomerExcludingAssessedTax` —
  exact match at all six overlap dates. Extends PWR's revenue history back to 2008.

All four applied as an `industrials`-scoped override (byte-identical Stage B1 first, 0 diffs; Stage
B2 additions produced 0 changed, 0 removed, 550 new fills across **30** tickers — far more than the
4 originally targeted, confirming these tags generalize across the sector rather than being
single-company quirks).

### The segment-divestiture recast trap, now confirmed a third and fourth time — and found in 9 more tickers

The prior entries logged this exact failure mode for JNJ (Kenvue) and KO (bottler refranchising).
HON's own history showed it clearly: FY2023 and FY2024 `OperatingIncomeLoss` and `Revenue` both
restated by near-identical dollar amounts (~$1.03B / ~$3.7B) in filings on the **same date**
(2026-02-17) — Honeywell's October 2025 Solstice Advanced Materials spinoff. FY2022 was never
refiled, so it sits on the pre-spinoff scope right next to two years on the post-spinoff scope — a
real discontinuity, not a bug.

Built a detector for the same signature (≥2 fiscal-year-ends restated on the same filed date, by
similar-magnitude dollar deltas — not percentage, since percentage alone conflates this with
routine gross/net presentation differences like CHRW's and CPRT's, which restate by 80%+ every
year for a decade and are a completely different, unrelated pattern) and ran it across all 69
tickers, filtered to restatements filed 2023 or later (what would actually sit in a chart someone
is looking at today). Found the pattern, beyond HON, in **MMM** (Solventum spinoff, Apr 2024),
**CARR** (Fire & Security divestitures), **DOV**, **EMR** (Climate Technologies majority stake
sale), **FTV** (Ralliant spinoff), **GE** (the three-way Aerospace/Vernova/HealthCare split — by
far the largest, ~49% of revenue), **J** (Amentum divestiture), **JCI**, and **LHX**. Two of the
task's eight named "check closely" tickers — **ITW and OTIS** — were checked directly and show
**no** scope break in their current-era `OperatingIncomeLoss` history; reported as checked-and-
clean rather than assumed clean from being merely "less complex" than GE.

### CAT and PCAR: captive-finance distortion risk, reported not fixed

Same concern as the Ford/GM captive-finance exclusion precedent. CAT's only long-term-debt tag
(`LongTermDebtNoncurrent`) is annual-only for its *entire* cached history (2008–2025, no quarterly
breakdown ever) and, at ~$22–38B, is almost certainly the full consolidated figure — Cat Financial's
receivables-backed borrowings included alongside the industrial business's own debt, with no
non-dimensional tag available to separate the two (the segment-level split CAT discloses is
dimensional, and — same limitation already logged for STZ's dual-class shares — this pipeline's use
of the plain `companyfacts` endpoint can't see dimensional facts at all). PCAR is worse: no
consolidated `LongTermDebt`-family tag exists at all despite PACCAR Financial's large financing-
receivables book being clearly present in the data. Neither ticker was reassigned — findings only,
per the task's standing rule for this category of question. Noted TXT as a related, unnamed case:
no usable `Goodwill` or `LongTermDebt` tag either, and Textron also runs a captive-finance arm
(Textron Financial Corp).

### Everything else: the OperatingIncomeLoss-fragility pattern, now confirmed for the ninth time

ADP, EMR, ETN, GE, HON, JCI, LHX, PCAR, ROK, ROL, and TXT all show `OperatingIncomeLoss` well below
50% coverage — traced individually rather than batch-assumed structural. Three distinct shapes, all
already-logged patterns rather than new ones: **never tagged at all** (ADP, EMR, PCAR — the
NKE/ADM/BG/CASY/CLX shape); **abandoned after a specific year** (GE stops in 2014, JCI stops in
2016, ETN in 2013, TXT in 2011 — the SYY/PFE D&A shape, applied here to operating income instead of
depreciation); **started only recently** (HON and ROL both begin in 2021, ROK only has 4 quarters,
all 2024–2026). None chased with a successor tag, per the task's explicit instruction for this
now-thoroughly-confirmed pattern. LMT's `DepreciationAndAmortization` (47%) is a clean instance of
the same annual-only-for-a-stretch shape as SYY and PFE — an 8-year gap (2017–2024) bounded by
otherwise-clean quarterly tagging on both sides.

## 2026-07-20 — Eighth stock-type profile: health_services split out of pharma_medtech, hidden set decided from evidence rather than copied

Executed the split the pharma_medtech scan (immediately below) recommended: DGX, LH, HCA, DVA,
UHS, CVS moved out of `pharma_medtech` into a new `health_services` profile. Life-science-tools/CRO
(A, TECH, CRL, IQV, MTD, RVTY, WAT, TMO) stayed put — out of scope for this task.

### The reassignment itself had to preserve extraction, not just move a label

`health_services` started with no `PROFILE_CONCEPT_OVERRIDES` entry of its own. Since
`get_concept_candidates` resolves purely from `PROFILE_CONCEPT_OVERRIDES[profile]` — no
inheritance between profiles — leaving it empty would have silently dropped
`ResearchAndDevelopmentExpense` extraction for all 6 tickers the moment they moved, deleting
LH's 3 genuinely-real quarters of R&D data ($2.5–3M each, 2009–2010) in the process. Copied
`pharma_medtech`'s `ResearchAndDevelopment` and `Capex` overrides verbatim into a new
`health_services` entry before touching anything else, and verified the reassignment alone (before
any hidden/excluded decision) produced **zero** change across the full 225-ticker cached universe —
0 changed, 0 removed, 0 new fills. Confirms the reassignment is what it should be: a routing change,
not a data change.

### The task's own instruction not to copy wholesale turned out to matter

The brief explicitly warned against copying `pharma_medtech`'s `PROFILE_HIDDEN`/
`PROFILE_EXCLUDED_CONCEPTS` and said to verify `OperatingIncomeLoss` coverage per ticker rather than
assume all 6 share HCA's problem. Checked directly:

```
DGX    OperatingIncomeLoss: 71/71 quarters (100%), 2008–2026 continuous
LH     OperatingIncomeLoss: 71/71 quarters (100%), 2008–2026 continuous
DVA    OperatingIncomeLoss: 71 quarters, 2008–2026 continuous (effectively full — the "37" revenue-
                            quarter denominator in the raw check was itself an unrelated DVA
                            revenue-tag artifact, not an OperatingIncomeLoss problem)
UHS    OperatingIncomeLoss: 67/65 quarters (103%), 2009–2026 continuous
HCA    OperatingIncomeLoss: 0/37 quarters (0%)
```

Only HCA has the gap. `pharma_medtech` hides `operating_margin`/`net_debt_to_ebitda`/`ev_ebitda`
profile-wide because the diversified-conglomerate `OperatingIncomeLoss` fragility pattern shows up
repeatedly across that batch (JNJ, NKE, ADM, BG, CASY, CLX, GPC, TJX, ROST — a real, recurring
pattern there). Here it's 1 gap out of 6, not a pattern. **Kept these three metrics visible for
`health_services`** — the opposite call from `pharma_medtech`, made deliberately rather than by
default. HCA itself: confirmed via a live `calculate_all_metrics` run that its failure mode is
`n=0` (empty merge, no rows) for all three metrics, not a wrong number — the same "fails silently,
produces nothing rather than garbage" behavior this whole log is built around, not new risk.
Verified DGX/LH/DVA/UHS/CVS's `operating_margin` values are real and sane (1.5%–15.1%, CVS's 1.5%
consistent with its already-known low-margin retail/PBM mix from the pharma_medtech scan) and that
`DepreciationAndAmortization` — excluded for `pharma_medtech` only because it fed the now-hidden
EBITDA chain there — correctly stays *un*-excluded here, since that same chain is visible for this
profile.

`rd_intensity`: confirmed R&D intensity is ~0% for all 6 (real business characteristic, matching
the CRL/IQV "service provider, not innovator" finding from the pharma_medtech entry) and that
`ResearchAndDevelopment` has exactly one consumer anywhere in the codebase (`rd_intensity` itself,
confirmed by grep across `main.py`/`metrics.py`/`figures.py`) — hidden and excluded together, same
"nothing visible depends on it" reasoning as every other exclusion in this project.

### Non-regression

Full before/after diff across all 225 cached tickers, run after every config change (reassignment
+ hidden/excluded decisions): 0 changed, 0 removed, 0 new fills — confirms the entire split changed
*visibility* only, exactly as the brief required. Spot-checked `metrics_long` directly for all 6
tickers plus two `pharma_medtech` references (JNJ, MDT): `rd_intensity` correctly empty for the 6
and present for JNJ/MDT; `operating_margin`/`net_debt_to_ebitda` correctly populated with sane
values for 5 of 6 and empty for HCA; both correctly empty for JNJ/MDT (untouched, still hidden
under `pharma_medtech`).

## 2026-07-20 — Seventh stock-type profile: pharma_medtech, and a net-vs-gross capex substitution caught and reverted

48 tickers (JNJ reference + 47 new). `pharma_medtech` reuses `standard`'s whole metric set,
excludes `OperatingIncomeLoss` outright (JNJ's own is structurally thin/discontinued, and with
`operating_margin`/`net_debt_to_ebitda`/`ev_ebitda` all hidden for the profile, nothing visible
depends on it), and adds one new concept/metric pair: `ResearchAndDevelopment` → `rd_intensity`.
Both were already built and verified correct going into this session; the work here was scaling
tag coverage to the other 47 names and resolving two structural questions the brief left open.

### DepreciationAndAmortization: the same reasoning as OperatingIncomeLoss, checked rather than assumed

The brief asked explicitly to verify D&A sits in the same position as `OperatingIncomeLoss` before
excluding it too — only feeding the already-hidden `EBITDA_TTM` chain (`net_debt_to_ebitda`,
`ev_ebitda`), with no other visible metric or chart touching it. Traced every consumer: `ebitda`
in `calculate_all_metrics` is D&A's only use, and both of *its* consumers are hidden for this
profile; `figures.py` only ever plots `metrics_long`/`valuation_history` concepts (never raw facts
directly), and neither plot list references D&A or anything derived from it outside the EBITDA
chain. Confirmed, not assumed — excluded via `PROFILE_EXCLUDED_CONCEPTS["pharma_medtech"]`.

### The one real fix: LLY's capex tag switch, right as the GLP-1 buildout needed it most

LLY's `Capex` was 16% (12/74) — `PaymentsToAcquireProductiveAssets` only has data for FY2018–2022,
nothing before or after. The raw tag dump showed `PaymentsToAcquireOtherPropertyPlantAndEquipment`
spanning 2007–2026 continuously — checked for a magnitude trap before trusting it (an "Other"-
prefixed tag is exactly the pattern this project already treats with suspicion): at all three dates
where the two tags overlap (2022 Q1–Q3), the values match **exactly**. Added as a third fallback
tag on a new `pharma_medtech`-scoped `Capex` override (byte-identical-copy-first discipline: Stage
B1 zero diffs). The 14 new quarters it recovers are exactly LLY's current manufacturing capex ramp
— $500M/quarter in early 2023 growing to $2.5B/quarter by late 2025, tracking the real, well-known
GLP-1 capacity buildout. Coverage: 16% → 35% (still below the 50% line, but the added history is
the economically important part — the recent ramp — not padding from old, low-relevance quarters).

### A second candidate tag looked fine on inspection and broke on the broad check — reverted

WAT's `Capex` was 2% (2/96). The obvious next tag, `PaymentsForProceedsFromProductiveAssets`,
has 67 unique dates for WAT spanning 2008–2025 — checked at the three dates where it overlaps
WAT's existing tag: two exact matches, one off by ~1%, good enough to look like a safe substitute.
Added to the same shared `pharma_medtech` `Capex` override (there's no per-ticker override
mechanism in this codebase, only per-profile — a tag added for one ticker's gap is live for all 48).
The mandatory non-regression check, run across the *whole* cached universe rather than just the
tickers it was meant to fix, caught what the narrow WAT-only check couldn't: for **LLY**, this same
tag produced a genuinely nonsensical **negative** capex value (-$220.9M at 2008-09-30). The tag name
says exactly why — "Payments **for**, and proceeds **from**, productive assets" is a *net* figure
(capex minus disposal proceeds), not gross capex. WAT's disposals happened to be small enough at
the three checked dates that net ≈ gross there; LLY's weren't, in a quarter with a real one-time
divestiture. Same rejection rule as every "different economic basis" trap in this log (fair-value
vs. carrying-value, FIFO vs. LIFO) — a *shared* tag that verifies cleanly against one ticker's
narrow overlap window is not the same claim as verifying it against the concept it's supposed to
represent. **Reverted.** WAT's `Capex` gap (2%) stays open and structural — no clean fix found.

### Everything else: structural, confirmed by inspection rather than left as a bare percentage

- **A dozen-plus growth-stage names with `DividendsPerShare`/`LongTermDebt` at or near 0%** (ALGN,
  BIIB, BSX, CRL, DHR¹, DVA, DXCM, EW, IDXX, ISRG, MTD, PODD, SOLV, VEEV, VRTX, WAT for dividends;
  ALGN, ISRG, VEEV for debt) — checked each rather than batch-assumed. Three (BSX, DVA, ISRG) have
  an aggregate `PaymentsOfDividends`-family tag reporting a literal `$0` for most periods,
  confirming genuine non-payer status directly rather than inferring it from tag absence; ISRG
  shows one isolated $8M distribution in mid-2024 that reverts to $0 in 2025 — a one-time item, not
  an ongoing per-share program. ¹DHR is a real, longstanding payer (`PaymentsOfDividends` exists
  and is nonzero) that has simply never tagged a per-share figure — same "abandoned/never-tagged
  per-share dividend" pattern as HSY/TSN from the 2026-07-20 consumer_staples entry, now confirmed
  in a fourth filer.
- **REGN — `Goodwill`, 0%.** No `Goodwill` tag anywhere in the company-facts dump, only
  `IntangibleAssetsNetExcludingGoodwill` (which, by its own name, explicitly isn't it). Consistent
  with Regeneron's real acquisition history — overwhelmingly organic growth, no major M&A — a
  genuine "no goodwill" balance sheet, same "confirmed absence, not a bug" pattern as GRMN's debt.
- **COO — `DividendsPerShare`, 20%, and a new tagging-convention trap.** COO's primary dividend tag
  has 145 raw points, but most (58 of them) carry **no `start` date at all** — an instant-style
  fact for what should be a duration concept — and get silently dropped by
  `extract_period_values`'s `"start" in item` check. Of the remainder, most use a narrow
  declaration-to-record-date window (~30 days) rather than a fiscal-period duration, which fails
  the 80–380-day quarterly validity range and gets dropped too. The handful that do show up as
  quarterly data are the coincidental few with both a `start` date and a long-enough window. The
  underlying value ($0.03/share, stable for years) is correct; the pipeline's duration-based
  extraction just can't reconstruct a clean quarterly series from this particular tagging
  convention. New pattern, distinct from every previously-logged dividend gap (abandoned tag,
  dual-class, young-company, genuine non-payer) — worth naming for future batches.
- **BSX — `NetIncomeLoss`, 42%.** A ~7-year gap (2011–2017) where *neither* candidate tag
  (`NetIncomeLoss`, `NetIncomeLossAvailableToCommonStockholdersBasic`) has any data at all — the
  first time this severe a gap has shown up in a universal, non-profile-specific base concept this
  project tracks. No substitute found; `IncomeLossFromContinuingOperationsBeforeIncomeTaxes...` is
  a different (pre-tax) income-statement level and was rejected on that basis, same rule as always.
- **HCA — `Goodwill`, 6%; IDXX — `LongTermDebt`, 46%.** Both show the same "real tag, but annual-
  only for part of history" shape already logged for TGT/COST/SYY in the consumer_staples entry
  above — HCA tags `Goodwill` only around its 2011 post-LBO re-IPO window and then stops; IDXX has
  only fiscal-year-end `LongTermDebt` before 2019, with `LongTermDebtNoncurrent` picking up cleanly
  from 2019 onward. Structural, not fixable by more tag search.
- **VRTX — `LongTermDebt`, 4%.** A genuine trap avoided rather than a gap left unfixed:
  `ConvertibleSubordinatedDebtNoncurrent` has 27 points covering 2010–2013, but checked against
  `LongTermDebt` at the three dates where both exist, the values don't match ($400M vs. $105M) —
  two real, *concurrent*, non-equivalent debt tranches, not alternates. Adding it as a fallback
  would silently pick whichever tranche happened to be tagged for a given date rather than the
  total. Not added; VRTX has been close to debt-free since ~2013 regardless.
- **CRL, IQV — `ResearchAndDevelopment`, 0% each — two more expected-zero cases beyond the brief's
  named six.** Neither is a health-services name (the brief's DGX/LH/HCA/DVA/UHS/CVS group); both
  are CROs (contract research organizations). CRL has no R&D-expense tag at all. IQV has one, but
  only 9 points (2011–2014, values in the low millions — immaterial next to IQVIA's actual revenue)
  before it was abandoned. Consistent with the CRO business model: the research they perform is
  billed as service revenue with a cost-of-revenue counterpart, not booked as the company's own
  R&D expense. Confirmed, not assumed — same discipline as the brief's own six.
- **The rest of the named six (DGX, LH, HCA, DVA, UHS, CVS) plus LH's thin 4%** — verified directly
  rather than waved through. All five 0%-coverage names have no R&D-expense tag whatsoever, exactly
  as expected. LH's 3 non-zero points (2009–2010, $2.5–3M/quarter, since abandoned) are real but
  immaterial next to Labcorp's revenue — not "unexpectedly high," so the brief's second-look
  trigger didn't fire.
- **Segment-reconciliation caution (ABT, DHR, BDX, TMO, BAX)** — none of the five needed a
  segment-level reconstruction for any flagged concept this session (their only flagged item, DHR's
  `DividendsPerShare`, turned out to be the abandoned-tag pattern above, unrelated to segments), so
  the caution wasn't triggered. Noted rather than silently skipped.

### Step 2: does the 14-ticker life-science-tools/diagnostics subset actually belong here?

Compared revenue growth, operating margin, and R&D intensity (TTM, computed directly from cached
data) against the seven named core references (JNJ, LLY, MRK, PFE, ABT, MDT, SYK) — no reassignment
performed, config left as-is, per the brief.

**Life science tools/CRO (A, TECH, CRL, IQV, MTD, RVTY, WAT, TMO)**: revenue growth (4.3–10.7% mean)
and volatility sit comfortably inside the core group's own range (3.7–8.6% mean, 4.5–27.6% stdev) —
nothing distinctive there. R&D intensity is the real signal: 3.6–8.7% across the group, versus
14.1–25.2% for the pure-pharma core names (LLY, MRK, PFE, JNJ) — though notably *close* to the
medtech core names' own 6.3–8.1% (MDT, SYK). The group also isn't internally homogeneous: TECH/WAT
run 27–28% operating margins (medtech-instrument-like), while the two CROs in the group (CRL 11%,
IQV 10%) run service-business margins and have no R&D tag at all (see above) — a bigger gap from
the "tools" half of their own bucket than from core medtech.

**Health services/diagnostics (DGX, LH, HCA, DVA, UHS, CVS)**: R&D intensity is essentially zero
across the board (confirmed in Step 1) — a real structural difference, not sampling noise. Margins
run lower and more service/facility-driven (11.6–16.4%) than core pharma/medtech's 13.8–24.2%
range, and CVS's 4.8% sits well below anything in the core group, reflecting its retail/PBM-heavy
mix. LH's revenue growth stdev (39.6%) is an outlier even within this group — a real, known
artifact of 2020–2021 COVID-testing revenue swings, not a data problem.

**Recommendation** (findings only, no config change): health-services/diagnostics is the stronger
candidate for eventually splitting out — the zero-R&D pattern is structural, not just numerically
low, and CVS's margin profile is qualitatively different from anything else in the profile. Life-
science-tools/CRO is more borderline — revenue dynamics look like core pharma/medtech fine, but the
group is itself split between instrument-makers (medtech-like) and CROs (their own thing); if this
gets revisited, splitting the two CROs (CRL, IQV) out specifically looks more justified than moving
all eight.

### Non-regression, Step 5

Full before/after diff across all 225 cached tickers (every profile) for the concept actually
changed (`Capex`): 0 changed, 0 removed, 14 new fills, all on LLY. (The rejected
`PaymentsForProceedsFromProductiveAssets` addition was caught and backed out before this final
diff — see above.) `DepreciationAndAmortization`'s exclusion touches only the coverage-check
whitelist (`get_expected_concepts`), not extraction, so no facts diff applies to it.

## 2026-07-20 — Sixth stock-type profile: consumer_staples, and a rejected FIFO/LIFO substitution

The `consumer_staples` profile (34 tickers, KO as reference) reuses `standard`'s entire concept set
unchanged — the profile exists purely to branch hidden-metric logic away from `standard`, no
`PROFILE_CONCEPT_OVERRIDES` entry was needed going in. Scoped as "the cleanest batch yet," and it
mostly was — one clean fix, one flagged ticker's own taxonomy sitting on the wrong side of a
methodology line, and a wall of genuinely structural gaps.

### BF.B: two data sources, two different silent-failure modes

Brown-Forman's ticker string needed resolving before any fetching. SEC's `company_tickers.json`
keys it `BF-B` (hyphen); the `TICKER_PROFILES` entry as drafted used `BF.B` (dot). Neither data
source accepts the dot form, and they fail differently: `get_cik("BF.B", ...)` raises an explicit
`ValueError` (loud, safe), but `yfinance.Ticker("BF.B").info` returns a *populated-looking* dict
where every field (`currentPrice`, `sharesOutstanding`, ...) is silently `None` — exactly the
"worse than an explicit error" case the brief warned about. Fixed by using `BF-B` as the ticker
string everywhere (`TICKER_PROFILES` key, cache filename, fetch calls) — confirmed working end to
end (CIK `0000014693`, live price via yfinance) before including it in the batch.

### The one clean fix: a cash tag that helped six tickers beyond the one that was flagged

Only `TGT`'s `CashAndEquivalents` was flagged outright (18/74, 24%), but the raw tag data pointed
at a broader gap: TGT stops populating `CashAndCashEquivalentsAtCarryingValue` after FY2019 and
switches to `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` — the post-ASU-2016-18
tag that folds restricted cash into the same reconciliation line, adopted market-wide around
2018–2019. Checked for a magnitude trap before trusting it (restricted cash could inflate the
figure): at every one of the three dates where old and new tags overlap for TGT, the values are
**exactly identical** — TGT's restricted cash is $0, so the new tag is a safe superset here, not a
different economic figure. Added as a third fallback tag on a `consumer_staples`-scoped
`CashAndEquivalents` override (byte-identical-copy-first discipline: Stage B1 zero diffs, Stage B2
154 new fills, 0 changed, 0 removed, across the full 178-ticker cached universe). The fill landed
on eight tickers, not one — `TGT` (+32), `EL` (+31), `HSY` (+27), `SJM` (+27), `PG` (+26), `KDP`
(+5), `KVUE` (+5), `BG` (+1) — all `consumer_staples`, confirming the profile scoping held and the
gap was an industry-wide tag migration rather than a TGT-specific quirk.

### A trap worth naming: FIFO/LIFO substitution looks like a fix and isn't

Kroger's `Inventory` coverage (checked as part of the Step 2 retail-likeness investigation below)
was 6% under the current `retail`-style candidate tags. The obvious next tag, `FIFOInventoryAmount`
(140 raw points, excellent coverage), is *not* the same figure as `InventoryNet` — Kroger discloses
inventory on a FIFO basis with a separately-tagged LIFO reserve, and the balance sheet carrying
value is FIFO minus the reserve. Verified exactly at every overlap date:
`FIFOInventoryAmount(2010-01-30) − InventoryLIFOReserve(2010-01-30) = InventoryNet(2010-01-30)` to
the dollar, and the same held at the two other overlap dates checked. The reserve is material
(~14–16% of the FIFO figure) — using `FIFOInventoryAmount` as a fallback would silently overstate
Kroger's inventory by that much whenever it kicks in. `extract_summed_values`'s `"sum"` source type
only adds; there's no subtraction primitive to compose `FIFO − Reserve` cleanly. **Not added.**
Logged as the batch's headline trap: a tag with excellent coverage and a plausible name can still
be measuring a different number entirely — same family as the fair-value-vs-carrying-value
rejection pattern, new instance.

### Step 2: are COST/TGT/WMT/DG/DLTR/KR secretly retail?

GICS classifies these six as Consumer Staples; operationally they're merchandise retailers. Tested
`retail`'s four working-capital tags against all six without reassigning anyone (a taxonomy call
left for a human). Findings, most to least clean:

- **COST, WMT** — 96–101% coverage on all four tags. Look exactly like the 19 already-built
  `retail` tickers.
- **TGT, DG** — 90–101% on `Inventory`/`CostOfRevenue`/`AccountsPayable`; `AccountsReceivable` at
  0%, same "pure consumer checkout, no trade receivable line" pattern already confirmed for
  several `retail` tickers in the 2026-07-19 entry — expected, not a gap.
- **DLTR** — `CostOfRevenue`/`AccountsPayable` clean, `AccountsReceivable` near-zero (same
  pattern), but `Inventory` at 0% under `retail`'s current tags. DLTR's real tag is
  `RetailRelatedInventoryMerchandise` (180 raw points, smooth $741M→$2.5B growth) — not in
  `retail`'s candidate list today. If reassigned, `retail` itself would need a small tag addition
  first; noted, not acted on.
- **KR** — the outlier. `AccountsReceivable`/`AccountsPayable` look fine once corrected for a
  Kroger-specific artifact (see below); `Inventory` needs the FIFO/LIFO fix that doesn't exist (see
  above); `CostOfRevenue` at 60% shares the same root cause as the `Capex`/`OperatingCashFlow` gap.

Recommendation only, no config change: COST and WMT are as clean a `retail` fit as any of the
current 19; TGT and DG fit modulo the already-expected AR exception; DLTR fits but needs one more
tag first; KR's inventory accounting genuinely doesn't map onto the current retail concept model
without a subtraction primitive the pipeline doesn't have.

### A second Kroger-specific artifact: no Q1 cash-flow disclosure, ever

`KR`'s `Capex` and `OperatingCashFlow` sit at 47% — traced to the raw filings, not just the merged
output. Every fiscal year, Kroger's cash-flow-statement tags start at a ~16-week (not ~13-week)
cumulative duration — there is no Q1-alone or Q1-cumulative fact for these concepts anywhere in the
company-facts history. `decumulate_period_values` can only recover one genuine discrete quarter per
year from this shape (the H1→9-month difference), and its Q4-backsolve needs three preceding
quarters it never has. No alternate tag fixes this: Kroger's own interim filings simply don't
disclose a Q1 cash-flow statement figure for these lines. Confirmed structural.

### Everything else: genuinely structural, confirmed rather than assumed

- **`ADM`, `BG`, `CASY`, `CLX` — `OperatingIncomeLoss`, 0%.** None of the four have ever tagged
  `OperatingIncomeLoss` (confirmed via a full `*income*`/`*operating*` tag dump for each) — same
  "no discrete operating-income subtotal in the income statement" pattern as NKE in the
  2026-07-20 retail entry above, now confirmed in four more filers. Worth naming as a
  consumer-staples-relevant recurrence, not a one-off.
- **`STZ` — `SharesOutstanding` and `DividendsPerShare`, both 0%.** No
  `WeightedAverageNumberOf*SharesOutstanding`, no `CommonStockSharesOutstanding`, no
  `EarningsPerShareBasic/Diluted`, no per-share dividend tag — anywhere in the company-facts dump.
  Constellation Brands' Class A/Class B dual-class structure is the likely cause: filers with
  multiple share classes often tag per-share and share-count concepts only with a
  `ClassOfStockAxis` dimension, and SEC's non-dimensional `companyfacts` view excludes anything
  that's never reported as a plain default-member fact. No fix available inside this pipeline
  (it doesn't consume dimensional facts at all).
- **`HSY`, `TSN` — `DividendsPerShare`, 8% and 0%.** Both are real, long-standing dividend payers;
  neither tags a per-share figure in any of the modern (post-2010) filings checked — HSY's own
  `CommonStockDividendsPerShareCashPaid` tag has exactly 10 points, all from 2008–2010, then
  nothing ever again. Per-share dividend disclosure is optional prose/table content in many
  filings, not a required primary-statement XBRL element — some filers simply never tag it.
- **`KVUE` — `DividendsPerShare`, 35%.** Not a gap: KVUE spun off from J&J in mid-2023 and the
  first dividend followed shortly after. The existing tag (`CommonStockDividendsPerShareCashPaid`)
  is already being used correctly; the low ratio is just a young company with a short history,
  confirmed by inspecting the full 13-point series (continuous and complete from initiation
  onward).
- **`MNST` — `LongTermDebt`, 7%.** Monster Beverage was a genuinely debt-free company for most of
  its public history — `LongTermDebt` tags a literal `$0` at 2023-12-31, then real debt appears
  from mid-2024 onward. Same "no debt is not a bug" pattern as GRMN/Reddit in the 2026-07-20 retail
  entry — confirmed, not fixed.
- **`COST`, `TGT` — `Goodwill`, 16% and 23%.** Both tag `Goodwill` at fiscal year-end only, never
  in an interim 10-Q, across their entire cached history (TGT: 17 dates, one per year, 2010–2026
  without exception). A stable, deliberate filer choice for an immaterial-and-usually-unchanged
  balance-sheet line, not a transition or a gap — same underlying cause as the "static value not
  re-tagged" issue documented earlier in this project, just permanent here rather than temporary.
- **`SYY` — `DepreciationAndAmortization`, 48%.** The most surprising one: SYY tagged full
  quarterly D&A (`Depreciation`, `AmortizationOfIntangibleAssets`, `DepreciationAndAmortization`)
  from FY2010 through FY2015, then **every one of those tags goes annual-only for FY2016–FY2024** —
  nine straight fiscal years with zero quarterly duration facts for any D&A-related concept, before
  quarterly tagging resumes in FY2025. Checked across all six candidate tags, not just the primary
  one — the gap is total, not a single-tag artifact. No substitute exists because the underlying
  quarterly disclosure wasn't made. Worth naming alongside the ROST/LOW/WSM "all started at once"
  pattern as its mirror image: a filer that *stopped*, then *resumed*, tagging the same concept
  years apart, with no tag-search fix possible either way.

### Non-regression, Step 5

Full before/after diff across all 178 cached tickers (every profile, not just `consumer_staples`),
for the one concept actually touched (`CashAndEquivalents`): 0 changed, 0 removed, 154 new fills,
all eight affected tickers within `consumer_staples`. No other concept was modified this session, so
no other diff was needed.

## 2026-07-20 — Fifth stock-type profile: retail, and a generic denominator-near-zero guard

Two independent pieces of work, kept deliberately separate (different files, different
non-regression checks): extending the `retail` profile's tag coverage to 18 more tickers, and a
generic fix for a `StockholdersEquity`-denominator explosion bug found in ORLY while doing so —
the fix turned out to reach far beyond retail.

### Retail: nine fundamentals stay the same, four new balance-sheet concepts

`retail` reuses `standard`'s whole metric set unchanged and adds four working-capital concepts on
top — `Inventory` (`InventoryNet`), `CostOfRevenue` (`CostOfGoodsAndServicesSold`),
`AccountsReceivable` (`AccountsReceivableNetCurrent`), `AccountsPayable`
(`AccountsPayableCurrent`) — feeding five new fundamentals: inventory turnover, DIO, DSO, DPO,
cash conversion cycle. ORLY-verified before scaling to AZO, BBY, GPC, HD, LOW, LULU, NKE, POOL,
RL, ROST, TJX, TSCO, ULTA, WSM, DECK, TPR, HAS, GRMN (19 tickers total, only HD previously
cached — the other 18, ORLY included, were fetched fresh this session).

### A named assumption that didn't survive contact with the data

The task brief named ORLY, AZO, ROST, TJX, ULTA, TSCO, WSM as "expected" near-zero
`AccountsReceivable` cases (pure consumer-cash checkout, no trade receivable line). Checked
directly rather than taken on faith: **six of the seven have excellent AR coverage (92–99%)** —
almost certainly real commercial/professional-account receivables (ORLY's and AZO's DIFM/commercial
programs selling to independent repair shops being the clearest case) rather than nothing. Only
TSCO actually matches the assumed pattern, confirmed via exhaustive tag search (nothing beyond a
tax-receivable tag and a one-time M&A footnote item). Reported as found, not forced to fit the
brief's expectation.

### Three clean fixes, and a lot of confirmed structural gaps

GPC's `AccountsReceivable` (0%→95%, via `AccountsNotesAndLoansReceivableNetCurrent` — a combined
accounts+notes+loans line typical of wholesale distributors) and DECK's / LULU's `LongTermDebt`
(both 0%→real-but-sparse, via `NotesPayable` and `OtherBorrowings` respectively — LULU's tag is
notably always exactly $0, a confirmed "no debt" reading rather than an unknown). `LongTermDebt`
wasn't previously overridable for `retail` at all; migrated to a profile-specific `priority_merge`
override with the usual byte-identical-copy-first discipline (0 diffs across all 145 cached
tickers before the two new tags were appended).

Everything else flagged (13 of 16 gaps) turned out structural on inspection: NKE has never tagged
a discrete operating-income concept at all (confirmed via a full raw scan of every "income" tag in
its filings — the income statement goes straight from expenses to pretax income); GPC and TJX
both discontinued their `OperatingIncomeLoss`/COGS tags mid-history with no successor found;
ROST, LOW, and WSM all *started* tagging a previously-bundled line (operating income, AR, COGS
respectively) at almost exactly the same point in FY2024/2025 — three unrelated companies
independently beginning disclosure at the same time reads as a shared external cause (a
disaggregation-of-expenses change around then) rather than three coincidental gaps, though not
chased down to a specific citation. GRMN, ULTA carry essentially no debt (Garmin: no debt tag
exists at all; ULTA: one $800M COVID-era revolver draw, repaid within months) — same "no debt is
not a bug" pattern as Reddit. 0 regressions, 118 new data points, across the full cached universe.

### The equity-denominator bug: found while building ORLY, fixed generically

ORLY's `roe` and `debt_to_equity` explode to nonsense (-27,999% / -591x) at 2021-03-31, where
`StockholdersEquity` crosses to -$6.977M against $12.2B of TTM revenue — the same failure mode as
the growth-rate near-zero-base bug from 2026-07-15, this time in a ratio *denominator* rather than
a growth *base*. Generalized rather than patched locally, since the task brief was explicit that
any profile with a `StockholdersEquity`/`TangibleEquity`-denominator ratio is exposed:

```python
MIN_DENOMINATOR_SCALE_RATIO = 0.01

def apply_denominator_scale_guard(ratio, denominator, scale_reference, min_denominator_scale_ratio):
    too_small = denominator.abs() < min_denominator_scale_ratio * scale_reference.abs()
    too_small = too_small & scale_reference.notna()
    return ratio.where(~too_small)
```

`Revenue_TTM` as the scale reference (present in every profile, unlike `Assets`). Wired into
`calculate_ratio` as two new optional parameters (off by default, same additive shape as
`min_base_ratio`), applied to `roe`, `debt_to_equity`, and `build_snapshot`'s `pb_ratio`/`p_tbv`.

### AZO checked, not assumed — and turned out to be a different phenomenon

The brief asked to confirm whether AZO (same aggressive-buyback reputation) shows the same
pattern. It doesn't: AZO's equity has been **continuously, stably negative since 2009** — a
large, deliberate, permanent capital-structure choice, not a brief crossing-through-zero like
ORLY's. AZO's smallest-ever `|equity|/revenue` is 6.35%, more than 6x above the chosen threshold;
its ROE/D-E stay bounded (roughly -0.5 to -2, -1.7 to -6.6) even though equity is negative
throughout. The guard correctly leaves all of AZO's history untouched — verified, not inferred
from the "similar company" framing.

### The threshold problem was bigger than ORLY vs. AZO

Running the same equity/revenue computation across all 145 cached tickers surfaced that near-zero
or negative `StockholdersEquity` relative to revenue is a **common pattern in `standard`-profile
names with long buyback histories** — CDW, HD, HPQ, DELL, MSI, MCHP, CIEN, STX, VRSN, GDDY, IT,
GEN, AMD, FTNT all show it, confirming the brief's "not retail-specific" framing empirically. This
also killed the hope of an IBM-style clean bimodal gap (that growth-rate fix's separation doesn't
exist here — the distribution is continuous). `0.01` was chosen as a deliberately conservative
threshold: it catches every value with genuinely extreme (`|roe|`/`|debt_to_equity|` in the high
single digits to several hundred) resulting ratios, while sitting 6x below AZO's smallest
legitimate value and >26x below the smallest already-validated financial/insurance equity/revenue
ratio anywhere in the cached universe (ALL, 26.1%). A few of ORLY's own milder elevated quarters
(e.g. 2021-09-30 at roe=-14.5, ratio=1.09%) are deliberately left unmasked rather than chasing a
looser threshold that would sweep into the broad thin-but-stable tech population.

### A bug in the guard's first version, caught by its own non-regression check

The first implementation treated a missing scale reference (`Revenue_TTM` unavailable for that
date) as "can't verify → mask." This silently masked 144 previously-clean values, including
**Goldman Sachs' entire 2009–2012 ROE series (13%–21%, completely sane)** — not because GS's
equity was ever small, but because `Revenue_TTM` has its own unrelated coverage gaps for that era
(the same class of bank-Revenue-tag issue documented in the 2026-07-17 entry). Caught by the
"diff against the old logic across the full cached universe" check before being kept, same
discipline as every fix in this log. Fixed: a missing scale reference now means "can't judge,
don't mask" rather than "mask" — `too_small = too_small & scale_reference.notna()`. Final result:
0 unexplained changes, 37 intentionally masked `(ticker, end)` ROE/D-E pairs (all `standard`
profile plus ORLY), every one genuinely extreme, zero `financial`/`insurance_pc`/`insurance_life`
tickers touched.

### Deliberately left alone

`build_valuation_history`'s time-series `pb_ratio`/`p_tbv` (as opposed to `build_snapshot`'s
single-latest-value versions) have the identical exposure and were not fixed — the task scoped
the guard to "snapshot-level" specifically. Flagged as a known, parallel gap rather than silently
patched or silently ignored, same "narrower-scope tradeoff, documented" call as the `peg_ratio`
fix's simplified growth calc from the 2026-07-18 entry.

## 2026-07-19 — Fourth stock-type profile: insurance_life, and a new architecture limit surfaced

Following `insurance_pc`, life/annuity insurers were split off as their own profile from the
start rather than merged in — MET, PRU, AFL, PFG, GL (five names; ERIE and AIZ were routed to
`standard`/`insurance_pc` respectively at classification time, since Erie Indemnity is a fee-based
management company with no underwriting risk of its own, and Assurant is now predominantly
specialty P&C after selling its life block years ago).

### Same nine-fundamental / five-valuation shape, reusing insurance_pc's exact concept names

The key design choice: `insurance_life`'s raw concepts share identical names with
`insurance_pc`'s (`EarnedPremiums`, `IncurredLosses`, `BenefitsLossesAndExpenses`,
`NetInvestmentIncome`, `Investments`, `ClaimsReserve`, `RealizedInvestmentGains`) even where the
underlying tags differ. This let every metric formula (Combined/Loss/Expense Ratio, Net
Investment Yield, Reserve Growth, P/Core Earnings) transfer to Life without writing a single new
line of calculation code — only the profile's tag overlay changed. Verified end-to-end on GL
before scaling: Combined Ratio computed from `BenefitsLossesAndExpenses/EarnedPremiums` matched
GL's real reported ratios almost exactly (95.4%, 95.4%, 95.7% for FY2022–24) and, notably, came
out far more stable year-to-year than P&C's — expected, since life/health claims are actuarially
predictable in a way catastrophe-exposed P&C claims aren't. Net Investment Yield ran structurally
higher than P&C (5.8% vs. TRV's ~4%), consistent with life insurers running longer-duration
portfolios against long-duration liabilities. `DepreciationAndAmortization` and
`CashAndEquivalents` are excluded for this profile (same reasoning as `insurance_pc` — neither
concept nor any metric depending on it applies structurally); notably `Capex` and
`OperatingIncomeLoss`, both excluded for P&C, were *not* flagged for GL, confirming the two
sub-profiles genuinely needed independent exclusion lists rather than a shared one.

### One real difference from P&C: RealizedInvestmentGains needed a genuine two-tag sum for GL

TRV had a single clean tag for realized investment gains/losses. GL does not — its current gains
are split across `GainLossOnSaleOfInvestments` (the dominant figure) and
`GainLossOnSaleOfOtherInvestments` (a small, genuinely separate line, likely real estate/equity-
method investments), both continuously present with clearly different, non-duplicate values —
confirmed additive, not the same fact under two names, before summing. `mode: "sum"` was
sufficient (no overlap risk, unlike the debt cases that needed `priority_merge`).

### LDTI (ASU 2018-12) restatement confirmed as a real, recurring pattern, not noise

Anticipated before scanning (long-duration contract accounting changed materially in 2023) and
then verified directly in raw `filed` timestamps across GL, PRU, and PFG: the same reporting
period's `LiabilityForFuturePolicyBenefits` value gets refiled at a materially different number
after the transition (GL's 2021-12-31 figure moved from $16.0B to $24.5B between filings; PRU's
2022-12-31 moved from $281.2B to $261.8B) — a genuine same-fact basis revision, not a data error
or two competing facts. The pipeline's existing "latest `filed` wins" tie-break already handles
this correctly by construction; no code change was needed, only correct recognition of the
pattern before treating a value jump as a bug.

### Second Claude Code scan-and-apply run for this profile, same non-regression discipline

3 of 10 flagged gaps resolved cleanly (AFL LongTermDebt via `NotesPayable`; AFL and PFG
`RealizedInvestmentGains` via `GainLossOnInvestments`, migrated to `priority_merge` with the
usual two-stage byte-identical-then-extend discipline). 0 regressions across the full 127-ticker
cached universe. MET required no changes at all.

### The interesting result: a candidate was found and *correctly rejected* for architectural reasons

PRU has an excellent, fully continuous `RealizedInvestmentGainsLosses` tag that would resolve its
gap outright — but that exact tag name, checked against GL at all 29 overlapping dates, disagreed
with GL's already-verified total by up to an order of magnitude (e.g. $240K vs. -$26.1M at one
date). This isn't an ambiguous edge case — it's conclusive evidence the same tag name means a
different reporting scope for GL than for PRU. Since `PROFILE_CONCEPT_OVERRIDES` only supports
profile-wide tag lists, not per-ticker exceptions within a profile, there is currently no way to
give PRU this tag without also silently exposing GL to it (or building a per-ticker override
layer, which doesn't exist yet). Correctly left unresolved and documented rather than forced —
the same "empirical proof over stated confidence" discipline that caught the debt-merge bug
in an earlier session, this time working preventively instead of after the fact.

### Deliberately left alone

AFL's `Investments` has no consolidated tag at all (only fragmented components) — same "not
worth a fragile multi-tag reconstruction" call as Micron's lease amortization. AFL's and PRU's
annual-only `Goodwill` tagging is the same filer-frequency limit already logged for ACGL/AIG.
PFG's and PRU's `ClaimsReserve` gap has a fuller alternative tag
(`LiabilityForFuturePolicyBenefitsAndUnpaidClaimsAndClaimsAdjustmentExpense`) but its margin over
the narrower reference definition was inconsistent (~1%–13% across dates) rather than a clean,
explainable constant — left unresolved rather than silently redefining what `ClaimsReserve` means
for two tickers. PFG additionally has one genuine, unexplained single-quarter gap
(`LiabilityForFuturePolicyBenefits` at 2021-12-31) inside otherwise-complete annual data — flagged
as-is, not guessed at.

### Open, going into future sessions

The PRU case is the first time this session hit a limitation worth naming explicitly: a **per-
ticker override mechanism within a profile** doesn't exist yet — only profile-level overlays. This
wasn't needed for any prior fix (bank/tech tag differences were always profile-wide), but it's
now a concrete, documented gap rather than a hypothetical one. Not building it now — same
"dedicated session, not bundled into this one" call as the earlier point-in-time forward-fill
question — but it's the natural next architecture item once enough of these single-ticker
exceptions accumulate to justify it.

## 2026-07-18 — Third stock-type profile: insurance_pc (P&C insurers), split cleanly from insurance_life

Following the financials (banks) and tech profiles, insurance was next — but "insurance" in
GICS Financials is itself three different businesses that don't share economics: P&C/multiline
(short-tail, annually-repriced, underwriting-driven), life/annuities (long-tail, spread-driven,
closer to a bank than to a P&C insurer), and brokers (MMC, AON, AJG, BRO, WTW — carry no
underwriting risk at all, economically a service business). Brokers were deliberately left on
the `standard` profile rather than mis-filed, same logic as keeping Visa/Mastercard out of
`financial` earlier. `insurance_pc` and `insurance_life` were split into two profiles from the
start (not merged-then-split later) — eleven P&C names (TRV, CB, PGR, ALL, AIG, WRB, CINF, ACGL,
HIG, L, EG) and seven life/annuity names (MET, PRU, AFL, PFG, GL, AIZ, ERIE) — with `insurance_life`
built empty for now, ready for its own metric definitions when that profile is tackled directly.

### Why P&C needs its own metric vocabulary

The central discovery, mirroring the bank NIM/efficiency-ratio work: P&C's defining ratios
don't exist as single XBRL tags. **Combined Ratio has no tag at all** — verified by search, not
assumed — so it's built like PPNR was for banks: `BenefitsLossesAndExpenses_TTM /
EarnedPremiums_TTM`, validated against TRV's own reported combined ratios (98.4%, 99.3%, 100.6%,
95.9% for 2021–2024 — matches real disclosed figures almost to the point). Loss Ratio and
Expense Ratio decompose it (`IncurredLosses_TTM / EarnedPremiums_TTM`, and Expense Ratio as the
pure residual `combined − loss` — no separate underwriting-expense tag needed at all, since the
only candidate found, `AmortizationOfDeferredAcquisitionCostsDAC`, stopped being tagged in 2010
and would've been useless anyway).

Nine fundamentals for `insurance_pc`: revenue/income growth, ROE, payout (inherited) + Combined
Ratio, Loss Ratio, Expense Ratio, Net Investment Yield (`NetInvestmentIncome_TTM / Investments`),
Reserve Growth (YoY change in `LiabilityForClaimsAndClaimsAdjustmentExpense` — a credit-quality-style
early-warning signal, same role the provision ratio plays for banks). Five valuation metrics, not a
forced six: P/E, P/TBV (replaces P/B, `Goodwill` moved from the `financial` override into the base
config since it's a universal GAAP concept, not bank-specific — available to every profile now),
Dividend Yield, PEG, and P/Core Operating Earnings (`market_cap / (NetIncome_TTM −
RealizedInvestmentGains_TTM)` — strips out realized investment gains/losses, which are market noise,
not underwriting performance; the insurance analogue to PPNR). New raw concepts: `EarnedPremiums`
(`PremiumsEarnedNet`), `IncurredLosses` (`PolicyholderBenefitsAndClaimsIncurredNet`),
`BenefitsLossesAndExpenses`, `NetInvestmentIncome`, `Investments`, `ClaimsReserve`, and
`RealizedInvestmentGains` — all TRV-verified before scaling, same discipline as JPM for banks.

### Two long-standing pipeline gaps surfaced and fixed along the way, unrelated to insurance itself

`peg_ratio` had silently never existed in `build_valuation_history` — it was only ever computed
in `build_snapshot`, so every profile's valuation *chart* (not just insurance's) had shown "keine
Daten" for PEG since the feature was built, unnoticed until insurance's chart made it obvious.
Fixed by computing `revenue_yoy_growth` directly inside `build_valuation_history`
(`wide.groupby("ticker")["Revenue_TTM"].pct_change(periods=4)`) — a simplified version without the
`min_base_ratio` near-zero-base guard from the July growth-rate fix, accepted as a deliberate,
narrower-scope tradeoff for chart display only. Separately, `check_data_quality` was still being
called with a single ticker's expected-concepts list for the whole batch (`TICKERS[0]`) — harmless
with one ticker, silently wrong the moment a second profile entered the same run (TRV's insurance
concepts were being checked against MSFT). Fixed by moving the whole function to a per-ticker
expected-concepts dict, closing a gap flagged as a known limitation weeks earlier and left
unaddressed until it actually broke.

### Second successful Claude Code scan-and-apply run, same non-regression discipline

Scanned the remaining 10 `insurance_pc` tickers against the TRV-verified pattern, authorized to
apply `priority_merge` mode migrations directly if needed (expected, since several concepts
needed genuine `sum` combinations of coexisting debt instruments — EG's `SeniorNotes` +
`NotesPayable`, WRB's `NotesPayable` + `SubordinatedDebt`). Every change diffed against the full
122-ticker cached universe, TRV included as the reference that must never move. One candidate
tag was added, then caught and reverted mid-task: a realized-gains component that looked fine for
L (no baseline to check against) turned out, once cross-checked against AIG's known total, to be
off by more than 10x — a partial component silently masquerading as the total. Final result: **0
regressions, 569 new data points, 9 of 22 flagged gaps fully resolved**, the rest documented with
a specific, verified reason (annual-only tagging confirmed via raw `fp`/`start` fields, sign
mismatches at the only overlap point, order-of-magnitude component checks) rather than a vague
"structural gap."

### Deliberately left alone

Four RealizedInvestmentGains/BenefitsLossesAndExpenses gaps (ACGL, AIG, CB, WRB) would need a
full itemized multi-era tag reconstruction to close safely — same "not worth the fragility" call
as Micron's lease amortization and JPM's minor intangibles. AIG's and ACGL's annual-only
`Goodwill` tagging is a filer limitation, not fixable by tag substitution; the general fix (forward-
filling point-in-time values between annual reports) would be a pipeline-wide architecture change
affecting every profile's balance-sheet concepts, not an insurance-specific patch — flagged for a
dedicated session, not bundled into this one.

## 2026-07-17 — Claude Code as a tag-discovery scout, and a real architecture bug it caught

The financials work (2026-07-16) proved the tag-hunting method — search, verify magnitude/overlap,
decide fallback vs. sum — but doing it ticker-by-ticker doesn't scale to the S&P 500. Today's shift:
delegate the *mechanical* search-and-screen work to a Claude Code agent, while keeping every config
change gated behind an explicit, empirically-verified non-regression check before it's trusted.

### The workflow, in three escalating rounds

**Pilot (15 mixed tickers).** First test of whether an agent could apply the same judgment used
manually all session — reject `LiabilitiesAndStockholdersEquity` (balance-sheet total, not equity),
reject `NonoperatingIncomeExpense` for `OperatingIncomeLoss` (the literal opposite concept, despite
passing every mechanical filter), flag but don't blindly add anything that overlaps an existing tag
with *different* values. It did. It also found that `SEARCH_HINTS` using bare words like `"sales"`,
`"debt"`, `"loss"` were substring-matching into unrelated tag families (`AvailableForSaleSecurities`
alone accounted for most of the noise) — hints were narrowed before scaling up.

**Run 2 (92 tickers — the full S&P Tech + true-Banks universe).** 53 of 92 came back clean. The
dominant remaining gap: `LongTermDebtAndCapitalLeaseObligations*`, a real, larger figure (debt +
finance leases) that consistently overlapped the existing `LongTermDebt` tags with *different*
values across ~18 tickers — correctly left as "needs a human mode decision," not auto-appended.

**Apply pass — and the bug.** Instructed to append the safe findings, with one hard rule: *a fix
for one ticker must never change a value for an already-working one.* The agent tested every
addition individually against all 92 tickers before keeping it, and found that reasoning supplied
in the task brief — "appending a tag at the end of `tags` is safe because first-match-wins" — was
incomplete. `fallback_then_sum` let *any* tag in `tags` unconditionally beat the `sum_tags` result,
regardless of where in `tags` it sat; position only mattered relative to other tags, not to sums.
Appending the lease tags "last" still silently overwrote dates that were correctly served by summing
`LongTermDebtNoncurrent + LongTermDebtCurrent` (caught: AMD's debt at one date shifting from
2,019,000,000 to 2,037,000,000 with no visible warning). 331 regressions were found this way, before
anything was kept — only 3 of the ~10 proposed additions survived. This is the payoff of insisting
on empirical diffing over trusting the stated reasoning, mine included.

### The real fix: one merge mechanism instead of two special-cased, buggy ones

`fallback_then_sum` (tags-always-beat-sums) and `fallback_sum` (fallback only fires if the *entire*
primary series is empty, an all-or-nothing-per-ticker gate that structurally blocked six D&A-thin
banks from ever using their configured fallback tags) turned out to be the same underlying flaw in
two disguises: neither was a true single-tier, per-date priority list.

Replaced both with one new mode, `priority_merge`. A concept declares an ordered `sources` list —
each entry either `{"type": "tag", "tag": "..."}` or `{"type": "sum", "tags": [...]}` — and
extraction is a single per-date pass: first source in the list with a value for a given date wins,
full stop, with sums treated as an ordinary entry rather than a special second tier.

```python
"LongTermDebt": {
    "sources": [
        {"type": "tag", "tag": "LongTermDebt"},
        # ...existing tags in their existing order...
        {"type": "sum", "tags": ["LongTermDebtNoncurrent", "LongTermDebtCurrent", "NotesPayableCurrent"]},
        {"type": "tag", "tag": "LongTermDebtAndCapitalLeaseObligations"},
        {"type": "tag", "tag": "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities"},
    ],
    "mode": "priority_merge",
},
```

Migrated with a two-step discipline: first a pure restructuring with zero new tags, required to
prove byte-identical output against the old modes across all 111 cached tickers (it was, for
`LongTermDebt`; for `DepreciationAndAmortization` it wasn't — 493 previously-unreachable values
appeared with nothing changed or removed, which is the all-or-nothing gate finally being gone, not
a defect, and was reported as such rather than forced to match the old, buggy behavior). Only after
that proof did the previously-blocked tags get added, this time genuinely safe by construction
because a per-date merge with explicit priority can't overwrite anything above it in the list.
Zero regressions on the second pass either — nothing had to be reverted this time.

### Net result

- **9 of the 36 still-open tickers fully resolved** (ACN, APH, INTC, JBL, MU, NXPI, TER, TRMB, BAC),
  several more meaningfully improved (GLW LongTermDebt 20%→97%, KEYS/MTB D&A into the 90s%).
- **1,196 new data points** recovered across `LongTermDebt` and `DepreciationAndAmortization`,
  zero previously-correct values touched, at any stage.
- `fallback_then_sum` and `fallback_sum` are no longer used anywhere in `config.py`; the old code
  paths were left in place (unused, not deleted — no reason to remove working dead code) in case a
  future concept genuinely wants that simpler, two-tier shape.
- Sector coverage: **~92 of ~504 S&P 500 constituents (~20%) now have systematically vetted tag
  configs** — the full Information Technology sector plus true depository banks, split out from
  insurers and capital-markets/payments names (which don't fit either existing profile and were
  deliberately left unscanned this round rather than mis-filed).

### Open, going into next session

Three threads handed to a follow-up Claude Code task, same non-regression discipline: (1) confirm
no other concept has the same architecture symptom under a different mode name, (2) a further tag
search for the 11 tech tickers whose `LongTermDebt` gap survived even the lease-tag addition, and
(3) bank `Revenue` for TFC/FITB/HBAN/RF/BNY/MTB/SYF — where no single tag has ever covered the
total, so the candidate fix is a genuine `{"type": "sum"}` of net-interest-income + noninterest-
income, validated against a working bank (JPM) before being trusted on the broken ones.

Longer-term: the GICS sectors scanned so far (Tech, Banks) were the two profiles that already
existed. The next several sessions' decisions are squarely about the sectors that don't fit either
— insurers (own economics: premiums, combined ratio, float, no NIM), capital-markets/payments names
(economically closer to tech than to banks — Visa, Mastercard, the exchanges, asset managers), and
eventually Consumer Staples/Healthcare/Industrials, none of which have been profiled at all yet.
Each will likely need its own profile, its own metric registry entries, and its own round of this
same scout → apply → verify cycle.

## 2026-07-16 — Stock-type profiles: making financials analysable (JPM as first bank)

The largest single addition so far. Until now the whole tool was implicitly tuned for
tech/growth stocks; financials (banks) produced either nonsense (a `debt_to_equity` of 9 for a
deposit-funded bank) or empty metrics. The goal: JPM analysable as richly as MSFT, without
touching how tech tickers behave, and built as a clean foundation for the eventual frontend
(where a user picks any ticker). Chosen approach: per-ticker profile ("Weg B"), full metric
set per profile ("Stufe 2").

Two problems had to be kept separate throughout: (1) *different tags* — banks tag the same
concept differently (solvable with the existing tag-list machinery); (2) *different metrics* —
some ratios don't exist or mean something else for a bank (EV/EBITDA, debt_to_equity, FCF are
meaningless; NIM, ROA, efficiency ratio, P/TBV take their place). Most naive tools only solve
(1) and then emit a technically-computed but economically-meaningless number.

### Architecture: three declarative layers, one visibility source of truth

Deliberately declarative rather than scattered `if profile == "financial"` checks, so the
frontend can later toggle profiles without rewrites.

- **`TICKER_PROFILES`** maps ticker → profile (`"JPM": "financial"`), default `"standard"`.
- **Visibility** — `PROFILE_HIDDEN` lists, per profile, which metric/chart columns to blank.
  Symmetric: `financial` hides the tech metrics (ev_ebitda, debt_to_equity, fcf_margin,
  rule_of_40, pb_ratio, …); `standard` hides the bank metrics (nim, efficiency_ratio, roa,
  equity_to_assets, provision_ratio, p_tbv, p_ppnr). A single `is_hidden(ticker, metric)`
  function is the only place that knows the logic, imported by every output stage.
  **Philosophy 1 chosen**: everything is always *computed*, only *display* is filtered — so a
  future "show JPM with standard metrics" toggle needs no recompute. Applied at every output:
  snapshot (`apply_profile_filter`), both chart sets (filter `concepts_to_plot`), and the
  long-format CSVs (`filter_hidden_rows`). Raw `quarterly_facts` deliberately NOT filtered —
  raw balance-sheet values stay complete even when the derived ratio is hidden.
- **Concept overrides** — `PROFILE_CONCEPT_OVERRIDES` + `get_concept_candidates(ticker)` layer
  profile-specific concept configs over the shared base via `.update()` (same base+overlay
  pattern as `fallback_then_sum`). Base config (tech) untouched; banks only override/add.

### Bank concepts added (all as `financial` overrides, verified per ticker)

- **Revenue** → `RevenuesNetOfInterestExpense` (JPM's total net revenue; the standard tags
  only caught the contract-with-customer slice, hence the original 36% coverage and a
  *negative* PEG from a broken yoy_growth). Fixing this alone flipped PEG from −6.9 to +4.8.
- **Assets** → `Assets` (total assets, feeds NIM, ROA, equity/assets).
- **NetInterestIncome** → `InterestIncomeExpenseNet` (duration, into `TTM_CONCEPTS`).
- **NoninterestExpense** → `NoninterestExpense` (duration, TTM).
- **NoninterestIncome** → `NoninterestIncome` (duration, TTM; for PPNR).
- **Goodwill** → `Goodwill`. Other intangibles (finite/indefinite/other) checked and
  *deliberately dropped* — fragmented tags, gaps, and only low-single-digit billions vs. a
  ~50bn goodwill on a ~4tn balance sheet. Same "marginal, not worth the fragility" call as the
  Micron lease-amortization decision. TBV = Equity − Goodwill.
- **ProvisionForCreditLosses** → `ProvisionForLoanLeaseAndOtherLosses` (continuous 2007→2026;
  two shorter competing tags rejected). Negative values in 2021 are real — post-COVID reserve
  releases, not a bug.

### The 9 + 6 → 9 + 4 metric set for banks

Fundamentals (9): revenue growth, income growth, ROE, payout (inherited) + **NIM**
(NetInterestIncome_TTM / Assets), **efficiency ratio** (NoninterestExpense_TTM / Revenue_TTM),
**ROA** (NetIncome_TTM / Assets), **equity/assets** (leverage inverse), **provision/revenue**.

Valuation — honestly 4, not a forced 6: **P/E**, **P/TBV** (replaces P/B for banks via
`PROFILE_HIDDEN`), **dividend yield**, **P/PPNR** (market_cap / (NII + NonII − NonExp) — the
Fed-stress-test pre-provision-net-revenue, the clean bank analogue to EV/EBITDA without the
EV problem). The last two slots left *empty on purpose*: EV-multiples are conceptually broken
for banks (deposits are the raw material, not a financing layer), and bank FCF is ill-defined.
Two empty slots is more honest than two misleading numbers.

Sanity checks all held: NIM ~1.4–2.6%, efficiency ~52–55%, ROA ~1.2%, equity/assets ~7.4%
(≈13.5x leverage, normal for a trading-heavy megabank), P/TBV 2.95 > P/B 2.53 (goodwill effect),
P/PPNR avg 7.6 < P/E avg 10.4 (pre-provision, pre-tax → larger denominator).

### Two follow-on fixes

**Dynamic chart grid.** The fixed 3×3 / 2×3 grids left empty boxes once metrics vary per
profile (banks: 4 valuation charts in a 2×3 = two blanks). Added `_make_grid(n)` (ceil-division
to rows×cols) and blank-axis cleanup for leftover cells. Fundamentals stayed 3×3 only by
coincidence (14 − 5 hidden = 9); now it's robustly derived, not lucky.

**Data-quality for profiles.** Banks kept warning on `Capex` / `OperatingIncomeLoss` /
`LongTermDebt` / `CashAndEquivalents` — concepts that are structurally irrelevant for banks but
still expected. Added `PROFILE_EXCLUDED_CONCEPTS` + `get_expected_concepts(ticker)`. Two subtle
bugs found while wiring it: (1) `print_data_quality` was still called with
`get_concept_candidates().keys()` instead of the pruned `get_expected_concepts()`; (2) more
importantly, `check_data_quality` builds its counts from what's *actually in facts*, so the
expected-list was only an *additive* list (what's missing), not a whitelist — `LongTermDebt`
was still loaded and thus still counted. Fixed by intersecting up front:
`df = df[df["concept"].isin(expected_concepts)]`. Side effect (intended): derived concepts
(Revenue_TTM, PPNR, TangibleEquity, …) are also excluded from coverage warnings — correct, since
those are validated via end-metric plausibility, not coverage. `SEARCH_HINTS` extended for all
new bank concepts so a future thin bank concept gets a proper explore_tags suggestion.

### Known debt carried forward (not done today)

`build_snapshot` still pulls each metric out of the metrics dict by hand (one `get_latest_row`
+ merge line per metric) — increasingly tedious with every bank metric, and worse once
consumer-staples / healthcare profiles arrive. Flagged for a refactor: have `build_snapshot`
consume the metrics dict generically. Consumer staples and healthcare profiles still
unverified (expected to be much closer to tech than banks are).

## 2026-07-16 — New feature: `build_snapshot_as_of` (retroactive snapshots)

Follows the manual MU backtest (ignoring the last N rows of each series to see whether the
framework would have flagged it as undervalued a year ago). Automates that instead of redoing it
by hand per ticker.

### Approach: filter inputs, reuse the existing pipeline

`calculate_ttm` / `calculate_growth` / `calculate_rolling_average` already only look backward
(rolling window, `.shift(periods)`), so no metric-calculation logic needed to change. Filtering
`facts`, `metrics`, and `rolling_pe` to `end <= cutoff_date` *before* handing them to the existing
`get_latest_value` / `get_latest_row` (both already `idxmax` on `end`) reproduces "latest known
value as of the cutoff" for free. `build_snapshot` itself is untouched — it just receives
pre-cut inputs plus a historical price instead of the live one.

```python
def build_snapshot_as_of(cutoff_date, facts, metrics, price_history, rolling_pe):
    cutoff_date = pd.Timestamp(cutoff_date)
    facts_cut = facts[facts["end"] <= cutoff_date]
    metrics_cut = {k: df[df["end"] <= cutoff_date] for k, df in metrics.items()}
    rolling_pe_cut = rolling_pe[rolling_pe["end"] <= cutoff_date]
    prices_cut = get_price_as_of(price_history, cutoff_date)
    ...
    return build_snapshot(facts_cut, metrics_cut, prices_cut, rolling_pe_cut)
```

`get_price_as_of` does the same thing for the price series: filter to `date <= cutoff`, take the
latest row per ticker.

Wired into `main()` via a new `SNAPSHOT_AS_OF_DATES` list in `config.py` (empty by default, so a
normal run is unaffected). Each date produces `snapshot_asof_{date}.csv` alongside the regular
snapshot.

### Known limitation, accepted deliberately

This is "latest value under today's data", not "what an analyst could actually have known on that
date." SEC restatements retroactively update comparative periods in the newest filing (see the
2026-07-13 ServiceNow split note) — old 10-Qs keep their pre-restatement values, but this
snapshot pulls from the current `facts` DataFrame, which reflects whatever value survived
deduplication (generally the latest filed, i.e. restated, one). True point-in-time would require
threading `filed` through `build_dataframe` (currently dropped) and filtering on `filed <= cutoff`
instead of `end <= cutoff` — meaningfully more work, not done here. Same category of trade-off as
`MAX_MULTIPLE`: pragmatic, not principled, documented rather than solved.

**Verified:** MU as-of 2025-08-28 (pe_ttm 16.0, ev_ebitda 7.7, peg 0.33) vs. current (pe_ttm 20.5,
ev_ebitda 14.7, peg 0.12) — matches the manual backtest from the prior session.

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