# Valuation-History Coupling Bug: Root Cause, Fix, and Verification

## Summary

`build_valuation_history()` computed `market_cap` from EDGAR's `SharesOutstanding` fact
only. For any ticker with a complete EDGAR `SharesOutstanding` gap, `market_cap` (and
everything derived from it) came out `NaN` for the ticker's entire history — silently
blanking 8 of the function's 11 output multiples, even though those multiples' other
required inputs were present and correct. This affected **3 tickers, not 2**: V and STZ (as
originally reported) plus **ERIE**, found via the mandated scope-check and not previously
noticed. Fixed by falling back to yfinance's current share count, but only for tickers with
a *complete* EDGAR gap — verified with a full 497-ticker non-regression run showing zero
changes to any other ticker.

## Step 1 — Root cause, confirmed and traced

`build_valuation_history(facts, price_history)` (in `main.py`) pivots 13 "needed" TTM/
balance concepts into one wide dataframe (`pivot_table(index=["ticker","end"],
columns="concept", values="value")`), then computes each multiple as arithmetic on that
wide frame's columns.

**This is not a shared inner-join that drops rows.** `pivot_table` keeps every `(ticker,
end)` row that appears among the filtered facts; a concept with zero facts for a given
ticker just leaves that column `NaN` for that ticker's rows — it doesn't remove them. Read
in full, along with `add_derived_concepts()`, `calculate_all_metrics()`, `calculate_ratio()`,
and `calculate_difference()` (all in `metrics.py`/`main.py`) to confirm this precisely
before drawing any conclusion, per the task's "confirm directly, don't assume" instruction.

**The actual mechanism is a shared-derived-quantity dependency chain:**

1. `wide["market_cap"] = wide["close"] * wide["SharesOutstanding"]`. If `SharesOutstanding`
   has zero EDGAR facts for a ticker, this column is `NaN` for every row of that ticker
   (pandas: `NaN * x = NaN`), so `market_cap` is `NaN` everywhere for that ticker.
2. `wide["ev"] = wide["market_cap"] + wide["net_debt"]`. Since `market_cap` is `NaN`
   everywhere, `ev` is `NaN` everywhere too — regardless of whether `net_debt` itself
   (`LongTermDebt - CashAndEquivalents`) has real values.
3. Of the 11 output multiples, **8 use `market_cap` or `ev` as their numerator**: `pb_ratio`,
   `pfcf_ratio`, `ev_ebitda`, `ev_sales`, `p_tbv`, `p_ppnr`, `p_core_earnings`, `p_ffo`. All 8
   come out empty as a pure side effect — even though `StockholdersEquity`, `FCF_TTM`,
   `EBITDA_TTM`, `Revenue_TTM`, `TangibleEquity`, `PPNR`, `CoreOperatingEarnings`, and
   `FFO_TTM` are each independently present and fine.
4. `pe_ratio` needs `EPS_TTM_CALC`, computed upstream in `add_derived_concepts()` as
   `NetIncomeLoss_TTM / SharesOutstanding` — this is **genuinely, unavoidably** blocked by
   the same gap (no shares outstanding, no EPS), and `peg_ratio` legitimately depends on
   `pe_ratio`. These two are *correctly* supposed to stay empty.
5. `dividend_yield = DividendsPerShare_TTM / close` never touches `market_cap` or `ev` at
   all, so it was never affected by this bug either way.

**Reproduced by hand** against V's real cached EDGAR data (no assumptions, actual code run):

```
SharesOutstanding fact count for V: 0
EPS_TTM_CALC fact count for V:      0   (correctly derived-empty)

V, 75 rows in the wide intermediate:
  market_cap non-null: 0      <- confirms the full poison
  net_debt   non-null: 53     <- LongTermDebt/CashAndEquivalents were mostly fine
  ev         non-null: 0      <- poisoned by market_cap, not by net_debt
  StockholdersEquity non-null: 71   <- present, would support pb_ratio
  EBITDA_TTM          non-null: 68  <- present, would support ev_ebitda
  Revenue_TTM         non-null: 68  <- present, would support ev_sales

build_valuation_history(facts, price_history) output for V: 44 rows, ALL dividend_yield.
```

This exactly matches the last production run's actual output
(`data/valuation_history.csv`): V has 44 rows, all `dividend_yield`; STZ has zero rows at
all (STZ's `dividend_yield` is *separately* blocked by its own, already-documented,
genuinely-missing `DividendsPerShare` tag — confirmed in the prior Full Quality-Flag Sweep
task — unrelated to this bug).

## Step 2 — Scope-check: does this affect any other ticker?

Checked every one of the 13 concepts `build_valuation_history()` touches for a **complete**
gap (zero facts for the whole ticker history) across all 497 currently active tickers,
using cached EDGAR data:

| Concept | Complete-gap tickers | Multiples affected if missing | Coupling bug? |
|---|---|---|---|
| `SharesOutstanding` | **ERIE, STZ, V** (3) | 8 multiples (`market_cap`/`ev`-poisoned) | **Yes** |
| `LongTermDebt` | AES, ALGN, EXPD, GRMN, IBKR, ISRG, MPWR, PCAR, RDDT, TPL, TROW, TTD, TXT, VEEV (14) | `ev_ebitda`, `ev_sales` only | No |
| `CashAndEquivalents` | AIG, ALL, HIG, L, PGR, TRV (6) | `ev_ebitda`, `ev_sales` only | No |
| `StockholdersEquity` | none | `pb_ratio`, `p_tbv` | N/A |
| `Revenue_TTM` | none | `ev_sales`, `peg_ratio` | N/A |

**ERIE was not named in the task's original context — only V and STZ were.** It has the
identical complete `SharesOutstanding` gap (confirmed independently in the prior
Full Quality-Flag Sweep task's investigation of ERIE) and was suffering the identical
8-multiple blackout, unnoticed. This is exactly the "may silently affect other tickers"
risk flagged as a concern up front.

The `LongTermDebt`/`CashAndEquivalents` gaps were checked directly (not assumed) and
confirmed to be a *narrower, expected* pattern, not a second instance of the coupling bug:
`net_debt`/`ev` come out empty only for those two multiples specifically, because Enterprise
Value genuinely, unavoidably requires net debt by its own definition — and there is no
alternate data source for `LongTermDebt`/`CashAndEquivalents` in this codebase (unlike
`SharesOutstanding`, which has yfinance as a viable substitute already used successfully
elsewhere). `market_cap` itself remains fine for all 20 of these tickers (confirmed directly:
e.g. AES has `market_cap` non-null in 70 of 78 rows, `net_debt`/`ev` in 0 of 78). No fix
applied or needed for these 20.

## Step 3 — Fix implemented

`build_valuation_history()` now takes a third parameter, `prices` — the yfinance
current-price-and-shares dataframe already computed in both callers just before the call,
but never previously passed in. `market_cap` now uses a per-ticker fallback:

```python
shares_outstanding_count = wide.groupby("ticker")["SharesOutstanding"].transform("count")
shares_fallback = wide["ticker"].map(prices.set_index("ticker")["shares_outstanding"])
shares_for_market_cap = wide["SharesOutstanding"].where(shares_outstanding_count > 0, shares_fallback)
wide["market_cap"] = wide["close"] * shares_for_market_cap
```

- Tickers with **any** real EDGAR `SharesOutstanding` data: `shares_outstanding_count > 0`
  is `True` for every row of that ticker (a per-ticker count, not per-row), so `.where()`
  preserves the original EDGAR column exactly as before — including any isolated per-row
  gaps. Nothing changes for these tickers.
- Tickers with **zero** EDGAR `SharesOutstanding` data anywhere (ERIE, STZ, V only): every
  row falls back to yfinance's current share count, applied as a constant across that
  ticker's full price history.

This intentionally does **not** touch `pe_ratio`/`peg_ratio` (still computed purely from
`EPS_TTM_CALC`, still correctly empty for these 3 tickers — a constant current share count
cannot substitute for a historically-accurate EPS trend the way it reasonably can for a
current-price-based market-cap multiple), and does **not** touch the
`LongTermDebt`/`CashAndEquivalents` → `net_debt` → `ev_ebitda`/`ev_sales` path at all (no
available substitute data source, and no bug to fix there — see Step 2).

The fallback mirrors a pattern already used successfully elsewhere in this exact codebase:
`build_snapshot()`'s live, current-day multiples already source `market_cap` from
`load_current_prices()` (yfinance), which is why V's *current* snapshot multiples were
never affected by this bug in the first place — only the *historical* series was.

Both call sites updated: `main()` and `run_full_refresh()` now pass `prices` through to
`build_valuation_history()`.

## Step 4/5 — Verification for V, STZ, and ERIE

Real cached data run through the actual (patched) function, network-fetched yfinance price
history and current shares for all 3:

| Ticker | Fallback shares (yfinance) | Fallback price | Implied market cap |
|---|---|---|---|
| V | 1,704,112,694 | $366.27 | ~$624.2B |
| STZ | 170,752,511 | $130.38 | ~$22.3B |
| ERIE | 46,189,068 | $233.67 | ~$10.8B |

(ERIE's 46.19M figure independently corroborates the prior flag-sweep's finding that
ERIE's widely-held Class A share count is "in the tens of millions" — two unrelated data
sources, EDGAR-derived reasoning and yfinance, agreeing.)

**V**: `pe_ratio`/`peg_ratio` correctly remain empty (genuine EPS gap). `dividend_yield`
unchanged (44 rows, was never broken). `pb_ratio`, `pfcf_ratio`, `ev_ebitda`, `ev_sales`
now populate with real, plausible values (most recent: pb_ratio=14.41, pfcf_ratio=24.26,
ev_ebitda=19.05, ev_sales=12.21). `p_tbv`/`p_ffo` also now compute correctly but are hidden
from the final output regardless, by pre-existing profile design for `standard`
(`PROFILE_HIDDEN`), unrelated to this bug.

**STZ**: `pb_ratio`, `pfcf_ratio`, `ev_ebitda`, `ev_sales` now populate with real, plausible
values (most recent: pb_ratio=2.85, pfcf_ratio=12.82, ev_ebitda=10.30, ev_sales=3.71).
`dividend_yield` correctly stays empty — traced to STZ's own, separate, already-documented
genuine `DividendsPerShare` gap, not this bug and not something this fix could address.
`pe_ratio`/`peg_ratio` correctly stay empty. `p_tbv`/`p_ffo` compute correctly but are
hidden by profile design.

**ERIE** (found via the scope-check, verified with the same rigor): `pb_ratio`,
`pfcf_ratio`, `ev_sales` now populate (most recent: pb_ratio=4.88, pfcf_ratio=21.37;
ev_sales=2.14 at its last available date). `ev_ebitda`, `p_tbv`, `p_ffo` correctly remain
empty — traced precisely to ERIE's own, separate, already-documented complete
`DepreciationAndAmortization` and `Goodwill` gaps (`EBITDA_TTM`, `TangibleEquity`, and
`FFO_TTM` all require an inner merge against D&A or Goodwill in `metrics.py`'s
`calculate_difference()`, so zero facts there means zero rows for those derived concepts,
independent of this fix). `dividend_yield`, `pe_ratio`, `peg_ratio` correctly remain empty
for ERIE's own separate, already-documented reasons.

Every one of these "correctly stays empty" conclusions is traced to a specific, independent,
already-documented root cause from the prior flag-sweep task — not asserted, verified.

## Step 6 — Full-universe non-regression

`build_valuation_history()` executed before-fix (original market-cap logic, reproduced
exactly, not approximated) and after-fix (the real patched function) on the **identical**
`facts` and `price_history` for all 497 active tickers:

- **Rows before: 205,130. Rows after: 205,999.**
- **REMOVED: 0** — nothing that existed before is gone.
- **ADDED: 869** — entirely accounted for by ERIE (133: 9 `ev_sales` + 66 `pb_ratio` + 58
  `pfcf_ratio`), STZ (360: 63 `ev_ebitda` + 64 `ev_sales` + 61 `p_ffo` + 42 `p_tbv` + 67
  `pb_ratio` + 63 `pfcf_ratio`), and V (376: 52 `ev_ebitda` + 52 `ev_sales` + 68 `p_ffo` + 69
  `p_tbv` + 69 `pb_ratio` + 66 `pfcf_ratio`). 133 + 360 + 376 = 869, exact.
- **CHANGED: 0** — not one existing value differs anywhere in the universe.
- **Tickers touched: exactly 3** — ERIE, STZ, V. Every one of the other 494 active tickers
  is byte-identical before and after, including all 20 tickers identified in the Step 2
  scope-check with `LongTermDebt`/`CashAndEquivalents` gaps (confirming those were correctly
  left untouched, as intended — not a second bug to fix).

## Files changed

- `main.py`: `build_valuation_history()` signature gained a `prices` parameter; `market_cap`
  computation reworked with the per-ticker complete-gap fallback described above. Both call
  sites (`main()`, `run_full_refresh()`) updated to pass `prices` through. No other function
  touched; `EPS_TTM_CALC`, `pe_ratio`, `peg_ratio`, and the `net_debt`/`LongTermDebt`/
  `CashAndEquivalents` path are unchanged.
- No `TICKER_PROFILES` or `TICKER_CONCEPT_OVERRIDES` entries touched, no ticker
  reassigned — this fix is entirely inside the valuation-history construction logic, per
  the task's explicit constraint.

See `bugfixed_update_history.md` for the full per-ticker before/after tables and scope-check
detail.
