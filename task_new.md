# Task: Wire Denominator Guard into `build_valuation_history` + Fix 6 Ticker Data Bugs + Re-assess MAX_MULTIPLE

## Context

Part C of `quarterly_and_growth_expansion_report.md` established two things that change the
picture on `MAX_MULTIPLE`:

1. **The specific denominator guards are not wired into `build_valuation_history()` at all.**
   All nine capped multiples (`pe_ratio`, `pb_ratio`, `pfcf_ratio`, `ev_ebitda`, `ev_sales`,
   `p_tbv`, `p_ppnr`, `p_core_earnings`, `p_ffo`) use raw pandas division on the pivoted
   frame with only a bare `.where(x > 0)` positivity filter — none call `calculate_ratio()`,
   which is where `require_positive_denominator`/`min_denominator_scale_ref`/
   `min_denominator_abs` actually live. `build_snapshot()`'s equivalent `pb_ratio`/`p_tbv`
   *do* call `apply_denominator_scale_guard()`; the historical series does not. So the
   blanket cap is currently the only protection there, not a redundant extra net.
2. **The artifact population clipped by the cap concentrates in six tickers with confirmed,
   specific data bugs** — not random noise: WAT (234 of 1,024 clipped rows), ANET (16), SW
   (4), NTRS (2), ICE (2), AMCR (2), plus ~112 near-zero-denominator rows spread across
   otherwise-normal large caps.

This task does the two precise fixes, then re-measures whether the cap is still earning its
keep. **Standing requirement, as always: nothing may regress.** Non-regression after each
part separately.

---

## PART 1 — Wire `apply_denominator_scale_guard()` into `build_valuation_history()`

### Step 1.1 — Confirm the current state and the guard's existing usage

Read `build_valuation_history()` and `build_snapshot()` side by side. Confirm exactly how
`apply_denominator_scale_guard()` is already called in `build_snapshot()` (which multiples,
which scale reference, which threshold) so the historical version mirrors the established,
already-calibrated usage rather than inventing a new pattern.

### Step 1.2 — Apply the guard to the nine multiples

Wire the guard into each of the nine capped multiples in `build_valuation_history()`, using
`Revenue_TTM` as the scale reference and the existing `MIN_DENOMINATOR_SCALE_RATIO = 0.01`
unless Step 1.3 shows that threshold is wrong for this context.

Be careful about which denominator each multiple actually divides by (it differs per
multiple: `StockholdersEquity` for `pb_ratio`, `TangibleEquity` for `p_tbv`, `FCF_TTM` for
`pfcf_ratio`, `EBITDA_TTM` for `ev_ebitda`, `PPNR` for `p_ppnr`, etc.) — apply the guard to
each one's own real denominator, not a single shared column.

**`ev_sales` needs explicit thought before you wire anything**: its denominator *is*
`Revenue_TTM`, so guarding it against a `Revenue_TTM`-based scale reference is circular and
meaningless. Decide what (if anything) is appropriate there and state your reasoning — a
concept that is its own scale reference may simply not need this guard, which is a fine
answer if that's what the analysis shows.

### Step 1.3 — Verify the guard does not over-mask (the critical check)

This is the risk that matters most: the guard will now mask values that currently display.
Some of those are the artifacts we want gone — but some could be **real, extreme-but-genuine
values** of exactly the kind the `MAX_MULTIPLE` investigation already identified as the
majority population (652 of 1,024 clipped rows were real: AMZN's near-zero-GAAP-earnings
growth years, high-growth SaaS names with thin GAAP profits, pandemic-era cruise lines,
REITs with structurally thin GAAP net income).

For every value the new guard would mask:
1. Count them, per multiple and per ticker.
2. Classify a representative sample using the same real-vs-artifact method as the Part C
   investigation (check the implied denominator against `Revenue_TTM`, and check the ticker's
   raw facts directly where a data bug is suspected).
3. **If the guard masks a meaningful number of confirmed-real values, do not ship it at
   `0.01` — recalibrate** using the marginal-return/clean-gap method used for every prior
   guard in this project, and report the calibration evidence. A guard that removes real
   information about genuinely unprofitable-but-real companies is not an improvement over the
   blunt cap.

Specifically confirm that the well-known real cases from Part C survive: AMZN's 2011-2015
thin-earnings years, the high-growth SaaS cohort (CRM, WDAY, NOW, PANW, DDOG, FTNT, CRWD),
TSLA/PLTR's pre-profitability phases, and NCLH/CCL's 2020-2021 revenue collapse.

### Step 1.4 — Non-regression for Part 1

Full-universe before/after on every valuation multiple. Report every newly-masked
`(ticker, concept, end)` triple, grouped by ticker. Confirm zero values *changed* (the guard
can only mask, never alter) and zero previously-masked values reappeared.

---

## PART 2 — Fix the six confirmed ticker data bugs

Each of the six has a different root cause and needs its own diagnosis before any fix. **Do
not assume the same mechanism applies to all six.**

### Step 2.1 — WAT: diagnose the source before attempting a fix

WAT's `SharesOutstanding` reads 3-5 billion for essentially its whole history (real: tens of
millions), spiking to 59.7B and 82.1B in two quarters. Part C's report hypothesized this
traces to `normalize_split_adjusted()`'s poisoned-anchor vulnerability — a known, previously
investigated bug where the function anchors on `values.iloc[-1]` unconditionally, and WAT's
own last-quarter fact is garbage, so the whole series gets rescaled to match it.

**This distinction determines whether a fix is even possible here:**
- If the raw EDGAR facts for WAT's `SharesOutstanding` are **correct** and
  `normalize_split_adjusted()` is mangling them → this is *not* fixable via
  `_KNOWN_BAD_FACTS`/`TICKER_CONCEPT_OVERRIDES`. It needs the underlying anchor logic fixed,
  and **three prior repair attempts on that function already failed** (a trailing-median
  anchor broke NOW's documented comparative-restatement case; a match-confidence tolerance
  broke AAPL and ~154 other tickers). Do not attempt a fourth generic repair in this task —
  report the finding and leave it, consistent with the existing decision to keep WAT parked.
- If the raw facts themselves contain specific bad values (e.g. the 59.7B/82.1B spikes are
  genuinely in the filings) → those specific facts are fixable via `_KNOWN_BAD_FACTS`, the
  same targeted mechanism used for BKR and WDAY. Fix those, and report whether doing so is
  enough on its own to bring WAT's series back to a sane scale, or whether the underlying
  ~50x baseline error persists independently.

Pull WAT's raw `SharesOutstanding` facts directly and determine which case applies before
touching anything.

**Note**: WAT is currently commented out of `TICKER_PROFILES` as a known-broken ticker. If
this task makes WAT fully sane, say so explicitly — un-commenting it becomes a decision for
the project owner, not something to do here.

### Step 2.2 — ANET, NTRS: `SharesOutstanding` outliers at specific dates

Both show implausible share counts at identifiable dates (ANET at several fiscal-year-ends
2021-2025; NTRS at 2008-12-31). Pull the raw facts, confirm the exact `(end, filed, val)`
triples that are wrong, verify against the ticker's real share count scale, and fix via
`_KNOWN_BAD_FACTS` — the same individually-listed, zero-inference mechanism already used for
BKR, WDAY, GLW, BAC, ROK, STX.

Check whether ANET's fiscal-year-end pattern suggests a systematic cause (e.g. a
different tag or a dimensional fact winning at year-ends specifically) rather than isolated
bad values — if so, a `TICKER_CONCEPT_OVERRIDES` entry may be the better fix than listing
individual facts. Decide from the evidence.

### Step 2.3 — ICE, SW, AMCR: `StockholdersEquity` scale errors

All three report `StockholdersEquity` in literal dollars where the rest of the series is in
full units ($10 for ICE, $107-$14,446 for SW, $96-$130 for AMCR, against $13-22B market
caps). This is the same scale-error class already handled elsewhere in this project.

Determine per ticker whether this is:
- A specific bad fact (fix via `_KNOWN_BAD_FACTS`), or
- A tag-scale mismatch across filings (the `SharesOutstanding`/`Assets`/`DividendsPerShare`
  pattern — check whether `_normalize_scale_outliers()` could cover `StockholdersEquity`,
  but **only if** the same assumption-checks that governed adding a concept to
  `_SCALE_CORRECTED_CONCEPTS` still hold; the prior generalization attempt for that mechanism
  failed on dollar-magnitude concepts precisely because real large jumps are indistinguishable
  from artifacts, so be skeptical here and prefer the targeted drop-list unless the evidence
  is strong).

### Step 2.4 — Non-regression for Part 2

Full-universe. Only the six named tickers may change, and only at the specific dates fixed.
Confirm the corrected values are *sane* (report actual before/after numbers and check them
against each company's real known scale), not merely different.

---

## PART 3 — Re-measure `MAX_MULTIPLE` with both fixes in place

### Step 3.1 — Re-run the Part C measurement

With Parts 1 and 2 shipped, repeat the exact Part C analysis: how many rows does
`MAX_MULTIPLE = 400` still clip, and what is the real-vs-artifact split now?

### Step 3.2 — Recommend, with evidence

- If the remaining clipped population is now overwhelmingly real → recommend removing the cap
  (or raising it beyond any value in the real population, with the number derived from the
  data).
- If artifacts remain → identify what still produces them and recommend the next precise fix
  rather than keeping the cap as a catch-all.

**Do not implement the cap change in this task** — report the evidence and recommendation, as
with the original Part C. The point of this task is to make the cap's removal *safe*, then
hand the decision over with fresh numbers.

---

---

## PART 4 — Correct the growth architecture: a column on `quarterly_facts`, not rows in `metrics_long`

**This part is independent of Parts 1-3** (different subject, different files) and corrects a
misunderstanding in the *previous* task's Part B, which has already shipped.

### What was built vs. what was actually wanted

The previous task built 33 growth series as **separate metric rows in `metrics_long.csv`**,
computed on the metric layer. That was based on a misreading of the intent.

**What is actually wanted**: year-over-year growth computed on the **raw extracted concepts in
`quarterly_facts.csv`** — the raw data layer, not the metric layer — and added as an
**additional column alongside `value` in that same file**, so each row reads:

```
ticker,concept,end,value,<growth column>
TSLA,Capex,2011-03-31,20476000.0,<yoy % vs 2010-03-31>
```

(current header is exactly `ticker,concept,end,value` — a 5th column is the change.)

Then: **plot the three most important growth series**, not all of them.

### Step 4.1 — Redirect the previous implementation

Remove the 33 growth series from `metrics_long` (the `calculate_broad_growth` output and its
`build_metrics_long()` wiring) — this is a **deliberate, requested removal**, not a
regression, and should be reported as such. Also remove the `plot_growth` figure and
`config.get_growth_panels()`/`GROWTH_BASE_PANELS`/`GROWTH_PROFILE_EXTRA` if they exist solely
to serve it, unless Step 4.4 concludes some of that per-profile selection logic is worth
reusing for the new, much smaller plot selection.

**Preserve the per-concept `min_base_ratio` calibration work from the previous task** — the
empirical finding that `0.33` over-masks lumpy/event-driven concepts (`CashAndEquivalents`,
`Goodwill`, `LongTermDebt`, `Capex`, `ProvisionForCreditLosses`, `Inventory` → recalibrated to
`0.05`) is still valid and directly applicable here. Do not redo that analysis from scratch;
carry it forward, and extend it to any concept newly in scope that wasn't covered before,
using the same method.

### Step 4.2 — Compute growth per `(ticker, concept)` on the raw facts

Use the existing `calculate_growth()` (which, since the period-alignment fix, matches the
prior-year row **by date** within tolerance rather than by row position — important here,
since raw concepts have more reporting gaps than the metric layer does).

Two questions to resolve from the data before implementing, not after:

1. **Which concepts get a growth value?** `quarterly_facts.csv` contains plain quarterly
   concepts, `_TTM` concepts, and (since the previous task) the new `_QUARTERLY` derived
   concepts. Decide whether growth is computed for all of them or only a subset, and report
   the reasoning. Note specifically: `Revenue_TTM` growth is already `revenue_yoy_growth` in
   `metrics_long` — computing it again here would duplicate the same number in two places
   under two names. Flag any such overlap and decide deliberately whether that's acceptable
   (same value, different file, arguably fine) or whether the `_TTM` rows should be excluded
   here. Don't let it happen silently either way.
2. **Point-in-time concepts** (`StockholdersEquity`, `Inventory`, `LongTermDebt`,
   `SharesOutstanding`, `Goodwill`, `CashAndEquivalents`...): growth is meaningful for these
   (dilution/buybacks, book-value growth, stock build, debt raises) — include them unless a
   specific one turns out not to be, in which case say which and why.

### Step 4.3 — Add as a column, without breaking anything that reads the file

Add the growth value as a new column in `quarterly_facts.csv`. Name it clearly and
consistently with this project's existing conventions.

**Before shipping**: grep for every reader of `quarterly_facts.csv` / the
`f"{PERIOD}_facts.csv"` output (and anything that reads the same in-memory dataframe
downstream) and confirm none of them break on an extra column — in particular anything that
indexes positionally, does `pd.read_csv(...).values`, or asserts a column count. Report what
you found and checked, even if the answer is "nothing reads it positionally."

Rows where growth can't be computed (no prior-year match within tolerance, or masked by
`min_base_ratio`) get an empty/`NaN` cell — **not a dropped row**. The `value` column and the
row set must be completely unchanged.

### Step 4.4 — Plot the three most important growth series

Propose which three, with reasoning. Consider whether the right three are universal (e.g.
revenue, earnings, and one capital-structure line) or profile-dependent (a bank's three most
important growth lines aren't a REIT's). Either answer is fine if it's argued from what a
reader of the chart actually needs — but keep it to **three**, per the explicit instruction,
not "three plus a few extras."

State where they render: a small dedicated figure, or added to an existing chart. Whichever
keeps the existing charts' layouts unchanged is preferred, consistent with how Part A of the
previous task handled this.

### Step 4.5 — Non-regression for Part 4

- `quarterly_facts.csv`: **same rows, same `value` column, byte-identical** — only a new
  column added. Verify across the full active universe.
- `metrics_long.csv`: the 33 growth rows from the previous task are gone (expected,
  deliberate); **everything else byte-identical**, including the four original growth series
  (`revenue_yoy_growth`, `income_yoy_growth`, `operating_income_yoy_growth`, `reserve_growth`),
  which were never part of the removed set and must remain untouched.
- The 11 quarterly ratio metrics and 6 quarterly derived concepts from the previous task's
  Part A are **not** in scope here and must remain exactly as they are.

---

## Output

One file, `valuation_guard_and_ticker_fixes_report.md`, in four parts:
- **1**: the guard wiring (including the `ev_sales` reasoning), the over-masking verification
  with its sample classification and any recalibration evidence, and the full newly-masked
  list.
- **2**: per-ticker diagnosis and fix (or documented non-fix, especially for WAT), with real
  before/after values checked against each company's known scale.
- **3**: the re-measured real-vs-artifact split and the recommendation.
- **4**: what was removed from `metrics_long`, which concepts got a growth column and why,
  the duplicate-with-`revenue_yoy_growth` decision, the downstream-reader check, the three
  chosen plots with reasoning, and Part 4's non-regression.

No scratch scripts left behind. Do not implement Part 3's recommendation, do not attempt a
generic repair of `normalize_split_adjusted()`, and do not un-comment any parked ticker.