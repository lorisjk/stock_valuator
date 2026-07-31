# Bugfix: Valuation-History Market-Cap Coupling (SharesOutstanding gap silently blanked 8 of 11 valuation multiples)

## Root cause

`build_valuation_history()` (`main.py`) computes `market_cap` internally as
`wide["close"] * wide["SharesOutstanding"]`, sourcing `SharesOutstanding` exclusively from
EDGAR's XBRL facts — the same `facts` dataframe every other concept in the function comes
from. `ev` is then computed as `market_cap + net_debt`.

For a ticker whose EDGAR `SharesOutstanding` series is completely empty (a confirmed,
genuine, unfixable EDGAR-side gap — see the prior Full Quality-Flag Sweep task for V, STZ,
and ERIE specifically), `wide["SharesOutstanding"]` is `NaN` for literally every row of that
ticker. Because `NaN * anything = NaN` and `NaN + anything = NaN` in pandas arithmetic, this
makes `market_cap` `NaN` for every row, which in turn makes `ev` `NaN` for every row too —
regardless of whether `net_debt` itself has real values.

Of the 11 output multiples, **8 use `market_cap` or `ev` as their numerator**: `pb_ratio`,
`pfcf_ratio`, `ev_ebitda`, `ev_sales`, `p_tbv`, `p_ppnr`, `p_core_earnings`, `p_ffo`. All 8
came out empty for such a ticker, even though every one of their *other* required inputs
(`StockholdersEquity`, `FCF_TTM`, `EBITDA_TTM`, `Revenue_TTM`, `TangibleEquity`, `PPNR`,
`CoreOperatingEarnings`, `FFO_TTM`, `LongTermDebt`, `CashAndEquivalents`) was present and
healthy. Only `pe_ratio` (needs `EPS_TTM_CALC`, itself computed upstream in
`add_derived_concepts()` as `NetIncomeLoss_TTM / SharesOutstanding` — genuinely,
unavoidably blocked by the same EDGAR gap) and `peg_ratio` (depends on `pe_ratio`) are
*supposed* to stay empty for such a ticker. `dividend_yield` never touches `market_cap` or
`ev` at all and was never affected either way.

This is **not** a "shared merge that drops rows" in the literal sense (the `pivot_table`
that builds `wide` does not drop a ticker's rows for a missing concept — it keeps them with
`NaN` in that one cell). The actual mechanism is a **shared-derived-quantity dependency
chain**: one upstream concept (`SharesOutstanding`) feeds a single intermediate quantity
(`market_cap` → `ev`) that most of the downstream multiples depend on as their numerator, so
a complete gap in that one upstream concept silently poisons every multiple sharing that
intermediate quantity, via ordinary NaN propagation through arithmetic — even multiples
whose other inputs are completely fine.

Reproduced by hand against real cached data (see the fix report for full detail): for V,
`market_cap` was non-null in **0 of 75** rows before the fix, and `ev` in **0 of 75**, even
though `StockholdersEquity` (71/75), `EBITDA_TTM` (68/75), and `Revenue_TTM` (68/75) were all
present. The last production run's `data/valuation_history.csv` independently confirmed
this: V had exactly 44 rows, all `dividend_yield`, and STZ had zero rows at all.

## Scope-check (Step 2)

Checked every concept `build_valuation_history()` touches for a **complete** (ticker-wide)
gap across all 497 active tickers, using cached EDGAR facts (no live fetch needed):

| Concept | Tickers with a complete gap | Cascade if missing | Is this the coupling bug? |
|---|---|---|---|
| `SharesOutstanding` | **ERIE, STZ, V** (3) | `market_cap` → `ev` → 8 multiples wiped | **Yes — the bug.** A yfinance fallback exists and is already used successfully elsewhere in this codebase (`load_current_prices()`). |
| `LongTermDebt` | AES, ALGN, EXPD, GRMN, IBKR, ISRG, MPWR, PCAR, RDDT, TPL, TROW, TTD, TXT, VEEV (14) | `net_debt` → `ev` → only `ev_ebitda`/`ev_sales` blocked | No — expected. Enterprise value genuinely requires net debt by definition; no substitute data source exists for `LongTermDebt`. |
| `CashAndEquivalents` | AIG, ALL, HIG, L, PGR, TRV (6) | same as `LongTermDebt` | No — expected, same reasoning. (All 6 are insurers; large insurers commonly don't report a plain "cash and equivalents" line the way industrials do.) |
| `StockholdersEquity` | none (0) | would block `pb_ratio` + `p_tbv` | N/A — no ticker affected. |
| `Revenue_TTM` | none (0) | would block `ev_sales` + `peg_ratio` | N/A — no ticker affected. |

**ERIE was not mentioned in the task's original context (which only named V and STZ) — it
has the identical complete `SharesOutstanding` gap and was suffering the identical
8-multiple blackout, unnoticed.** This is exactly the "may silently affect other tickers"
risk the task asked to check for.

Verified directly (not just by concept-count) that `LongTermDebt`/`CashAndEquivalents`
gaps only block `ev_ebitda`/`ev_sales` and nothing else, confirming these are the multiples'
own genuine, correct data requirement, not a false coupling: for AES/ALGN/AIG,
`market_cap` was non-null for the great majority of rows (`SharesOutstanding` present),
while `net_debt`/`ev` were 0/N non-null (blocked only by their own missing input) — a
narrow, single-purpose, *expected* gap, structurally different from ERIE/STZ/V's
`market_cap`-poisoning blackout.

## The fix

`build_valuation_history()` now takes a third parameter, `prices` (the yfinance
current-price-and-shares dataframe, already computed in both callers before the call —
`load_current_prices()` in `main()`, `pd.DataFrame(current_price_rows)` in
`run_full_refresh()` — just never previously passed in).

`market_cap` is now computed from a per-ticker fallback-aware share count:

```python
shares_outstanding_count = wide.groupby("ticker")["SharesOutstanding"].transform("count")
shares_fallback = wide["ticker"].map(prices.set_index("ticker")["shares_outstanding"])
shares_for_market_cap = wide["SharesOutstanding"].where(shares_outstanding_count > 0, shares_fallback)
wide["market_cap"] = wide["close"] * shares_for_market_cap
```

- Where a ticker has **any** real EDGAR `SharesOutstanding` data, `shares_outstanding_count
  > 0` is `True` for every row of that ticker (it's a per-ticker, not per-row, count), so
  `.where()` keeps the original EDGAR value untouched — including any per-row `NaN`s for
  ordinary, isolated data gaps. **No ticker with partial coverage is affected in any way.**
- Where a ticker has **zero** EDGAR `SharesOutstanding` data anywhere in its history (only
  ERIE, STZ, V today), every row falls back to yfinance's current share count, applied as a
  constant across that ticker's whole price history.

This is a deliberate approximation, not a historically-accurate reconstruction: yfinance
only exposes a single *current* share count (no historical time series), so it's applied
uniformly to every historical date for the 3 affected tickers. This is materially better
than 100% empty, and is the same trade-off `build_snapshot()`'s current-snapshot path
already makes implicitly (its `market_cap` comes from `load_current_prices()`, i.e.
yfinance, and was never affected by this bug in the first place — confirming the fallback
mirrors an already-correct, already-used pattern in this exact codebase rather than
introducing a new one). `EPS_TTM_CALC` (and therefore `pe_ratio`/`peg_ratio`) is completely
untouched by this change — it is still computed purely from EDGAR facts upstream in
`add_derived_concepts()`, so it correctly, deliberately remains empty for ERIE/STZ/V, since
a constant current share count would not give an accurate *historical* EPS trend the way it
can for a *current* market-cap-based multiple.

Both call sites (`main()`, `run_full_refresh()`) updated to pass `prices` through.

## Before/after for every affected ticker

Computed values shown are what `build_valuation_history()` now returns internally; the
"visible" column accounts for `filter_hidden_rows()` — `p_tbv`, `p_ppnr`, `p_core_earnings`,
and `p_ffo` are hidden by profile design for both `standard` (V, ERIE) and
`consumer_staples` (STZ), independently of this bug, so those two concepts compute
correctly but were never going to appear in the saved CSV/plots either way.

### V (profile: standard)

| Concept | Rows before | Rows after | Visible after `filter_hidden_rows`? |
|---|---|---|---|
| `dividend_yield` | 44 | 44 | Yes (unchanged — never affected by this bug) |
| `pb_ratio` | 0 | 69 | **Yes — newly visible** |
| `pfcf_ratio` | 0 | 66 | **Yes — newly visible** |
| `ev_ebitda` | 0 | 52 | **Yes — newly visible** |
| `ev_sales` | 0 | 52 | **Yes — newly visible** |
| `p_tbv` | 0 | 69 | No (hidden for `standard`, unrelated to this fix) |
| `p_ffo` | 0 | 68 | No (hidden for `standard`, unrelated to this fix) |
| `pe_ratio` | 0 | 0 | Correctly stays empty (genuine `EPS_TTM_CALC` gap) |
| `peg_ratio` | 0 | 0 | Correctly stays empty (depends on `pe_ratio`) |
| `p_ppnr`, `p_core_earnings` | 0 | 0 | Correctly stays empty (bank/insurance-only concepts, not applicable to V regardless) |

Sample real value at the most recent date (2026-03-31): `pb_ratio` = 14.41, `pfcf_ratio` =
24.26, `ev_ebitda` = 19.05, `ev_sales` = 12.21 — all plausible for Visa's real scale and
margin profile.

### STZ (profile: consumer_staples)

| Concept | Rows before | Rows after | Visible after `filter_hidden_rows`? |
|---|---|---|---|
| `pb_ratio` | 0 | 67 | **Yes — newly visible** |
| `pfcf_ratio` | 0 | 63 | **Yes — newly visible** |
| `ev_ebitda` | 0 | 63 | **Yes — newly visible** |
| `ev_sales` | 0 | 64 | **Yes — newly visible** |
| `p_tbv` | 0 | 42 | No (hidden for `consumer_staples`, unrelated to this fix) |
| `p_ffo` | 0 | 61 | No (hidden for `consumer_staples`, unrelated to this fix) |
| `dividend_yield` | 0 | 0 | Correctly stays empty — STZ's own `DividendsPerShare` tag is genuinely, separately missing from EDGAR (confirmed in the prior Full Quality-Flag Sweep task); unrelated to this bug and not fixable by it |
| `pe_ratio`, `peg_ratio` | 0 | 0 | Correctly stays empty (genuine `EPS_TTM_CALC` gap) |
| `p_ppnr`, `p_core_earnings` | 0 | 0 | Correctly stays empty (not applicable to STZ) |

Sample real value at the most recent date (2026-05-31): `pb_ratio` = 2.85, `pfcf_ratio` =
12.82, `ev_ebitda` = 10.30, `ev_sales` = 3.71 — all plausible for Constellation Brands.

### ERIE (profile: standard) — found via the scope-check, not named in the original task

| Concept | Rows before | Rows after | Visible after `filter_hidden_rows`? |
|---|---|---|---|
| `pb_ratio` | 0 | 66 | **Yes — newly visible** |
| `pfcf_ratio` | 0 | 58 | **Yes — newly visible** |
| `ev_sales` | 0 | 9 | **Yes — newly visible** (thin: only 9 dates, because `net_debt` itself is only available where ERIE's own, separately-documented partial `LongTermDebt` coverage exists — 25/67 periods per the prior flag sweep) |
| `ev_ebitda` | 0 | 0 | Correctly stays empty — traces to ERIE's own, separately-documented complete `DepreciationAndAmortization` gap (`EBITDA_TTM` needs D&A via an inner merge in `calculate_difference()`; zero D&A facts means zero `EBITDA_TTM` rows), not this bug |
| `p_tbv`, `p_ffo` | 0 | 0 | Correctly stays empty — both trace to ERIE's own, separately-documented complete `Goodwill`/D&A gaps (`TangibleEquity` and `FFO_TTM` both require D&A/Goodwill via inner merges); also hidden for `standard` regardless |
| `dividend_yield` | 0 | 0 | Correctly stays empty — ERIE's own `DividendsPerShare` tag is genuinely, separately missing (confirmed in the prior flag sweep) |
| `pe_ratio`, `peg_ratio` | 0 | 0 | Correctly stays empty (genuine `EPS_TTM_CALC` gap — ERIE's `SharesOutstanding` gap, same root cause as V/STZ) |

Sample real value at the most recent date (2026-03-31): `pb_ratio` = 4.88, `pfcf_ratio` =
21.37. `ev_sales` = 2.14 at its last available date (2018-12-31).

## Non-regression (Step 6)

`build_valuation_history()` run before-fix and after-fix on the **identical** `facts` and
`price_history` for all 497 active tickers (the before/after difference isolated to the
fix's own code change, nothing else):

- **REMOVED: 0** rows.
- **ADDED: 869** rows, entirely accounted for by the tables above (ERIE 133 + STZ 360 + V
  376 = 869).
- **CHANGED: 0** rows — not a single existing value was altered anywhere in the universe.
- **Tickers touched: exactly 3** — ERIE, STZ, V. No other ticker among the other 494 active
  tickers changed in any way, including the 20 tickers with `LongTermDebt`/
  `CashAndEquivalents` gaps identified in the scope-check (confirming those gaps are
  correctly left alone, as intended).
