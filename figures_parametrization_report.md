# Figure-Builder Parametrization — Report

**Date:** 2026-08-05
**Touched:** `figures.py` only. No Streamlit code or import, no Phase 4, no `config.py` change, no `SharesOutstanding` fix. `main.py` untouched — its six call sites pass none of the new parameters.

---

## Step 1 — Explicit panel selection

All three per-ticker builders gained `concepts: list[str] | None = None`, `None` meaning "everything the config shows" (today's behaviour). The wrappers `plot_fundamentals` / `plot_growth` / `plot_valuation` pass it through.

The whole selection rule lives in one helper, `_select_concepts(ticker, catalogue, requested)`, shared by all three — the catalogues (`FUNDAMENTALS_TO_PLOT`, `VALUATIONS_TO_PLOT`, `GROWTH_PANELS`) all have the concept name as the tuple's first element, so one implementation covers them and the rule cannot drift between builders.

**1.1 `is_hidden` stays authoritative — enforced by construction, not by a check.** The helper filters the catalogue through `is_hidden` *first* and then intersects with the caller's list:

```python
visible  = [c for c in catalogue if not is_hidden(ticker, c[0])]
selected = [c for c in visible if c[0] in set(requested)]
```

An explicit request can only ever *narrow* `visible`; there is no code path where a requested name reaches the render loop without having passed `is_hidden`. That is stronger than validating the caller's list, because it stays true no matter what the caller sends.

**1.2 Unknown or hidden entries: ignored, with a printed note.** Not refused. A UI hands one metric selection to several tickers, and a concept that is fine for one is routinely hidden for another — `fcf_margin` is visible for `standard` and hidden for `financial`, `p_ffo` is visible only for `reit`. Refusing would make a normal cross-ticker comparison an error the user has to resolve. Silence would be worse than the note, though: a user who ticks a box and sees no panel deserves a reason. The note distinguishes the two causes, since they call for different reactions:

```
[figures] AAPL: angeforderte Konzepte nicht darstellbar -- p_ffo (für dieses Profil ausgeblendet)
[figures] AAPL: angeforderte Konzepte nicht darstellbar -- does_not_exist (unbekannt)
```

**1.3 Ordering follows the config catalogue, not the caller's list.** A chart's panel order is then stable regardless of the order a UI happens to send — checkbox order, click order, or a set with no order at all would otherwise reshuffle the grid between renders of the same selection. Verified: requesting `["debt_to_equity", "revenue_yoy_growth", "operating_margin"]` renders `["revenue_yoy_growth", "operating_margin", "debt_to_equity"]`.

**1.4 Narrowing to nothing** falls into each builder's existing "no visible panels" guard and returns `None`; the wrappers still write neither file. Nothing new was added for this — the empty list simply reaches the guard that was already there.

**Grid re-tiling needs no new code, confirmed.** `_make_grid` derives rows/cols from the panel count, and `_make_subplot_figure` emits `None` specs for cells past the panel count, so a shorter list produces a tighter grid with no trailing empty cells. AAPL's fundamentals go 9 panels / 3×3 → 3 panels / 1×3, and 1/4/7 panels give 1×1, 2×3, 3×3 with exactly 1, 4 and 7 axes.

`build_ticker_comparison` was left alone here — it already takes its single concept explicitly.

## Step 2 — Controllable sizing

Shape chosen: **explicit `width` / `height` parameters on all four builders**, not a boolean "responsive" flag. A flag can only express one alternative to the default; parameters cover the responsive case *and* a caller that wants a specific size, with no extra API.

The problem this creates is that three states are needed — "unchanged", "omit the key", "use this number" — and `None` is already taken by the second one, which is the case the frontend needs. So there is a named sentinel:

```python
KEEP = _Keep()          # repr: <unchanged>
width: int | None = KEEP
```

| call | resulting layout |
|---|---|
| `build_fundamentals(t, df)` | `width=1500, height=990` (= 500·cols, 330·rows, exactly today) |
| `build_fundamentals(t, df, width=None)` | **no `width` key**, `height=990` |
| `build_fundamentals(t, df, width=None, height=None)` | neither key present |
| `build_fundamentals(t, df, width=1234, height=567)` | `width=1234, height=567` |

`_size(width, height, default_width, default_height)` returns just the size fragment, which each builder splats into its `update_layout(...)` call **in the original keyword position**:

```python
fig.update_layout(
    title_text=f"Fundamentals {ticker}",
    **_size(width, height, 500 * cols, 330 * rows),
    legend=dict(font=dict(size=9)),
)
```

That positional detail is not cosmetic — see the verification section; an earlier version that merged the size into a layout dict produced structurally identical but **not byte-identical** JSON, which would have broken the standing requirement.

`build_ticker_comparison` gets the same two parameters, defaulting to its historical 900×520, and keeps `meta`, `hovermode` and `margin` intact when resized.

## Step 3 — `as_of`-anchored valuation window

`build_valuation` and `build_ticker_comparison` both take `as_of: pd.Timestamp | None = None`; `plot_valuation` and `plot_ticker_comparison` pass it through.

**3.1 A supplied `as_of` bounds the window above as well.** Today's one-sided `end >= cutoff` is correct only because the anchor is today and no data lies in the future. With a historical anchor the same filter would answer *"everything since 2015-06-30"* instead of *"the five years as of 2020-06-30"* — it would show the user data the chosen date could not have known, which is precisely what an as-of view exists to exclude. This matters concretely: the feature pairs with `build_snapshot_as_of`, whose entire purpose is reconstructing what was visible at a past date. So `as_of` closes both ends.

The upper bound is applied **only when `as_of` is given**, not unconditionally as `end <= today`. Adding it to the default path would be a behaviour change for no benefit, and the byte-identity requirement would catch it.

**3.2 One expression, both call sites.** Factored into `_window_frame(frame, years, as_of)`, which both builders call. There is no second copy of the windowing arithmetic to drift.

```python
anchor = pd.Timestamp.today() if as_of is None else pd.Timestamp(as_of)
windowed = frame[frame["end"] >= anchor - pd.DateOffset(years=years)]
if as_of is not None:
    windowed = windowed[windowed["end"] <= anchor]
```

`build_ticker_comparison` still applies the window only to valuation concepts (`_concept_plot_spec` decides), so `as_of` is inert for fundamentals and growth concepts, which were never windowed.

## Step 4 — Housekeeping

- **`from datetime import datetime` removed.** Grep confirmed one occurrence in the file — the import itself — and the verification asserts the string `datetime` now appears nowhere in `figures.py`.
- **`_make_grid`'s `n == 0` branch: kept, with a comment marking it a defensive no-op.** It is unreachable today (every builder returns early on an empty panel list, and Step 1's narrowing-to-nothing case reaches that same guard). It was kept rather than deleted because the failure it prevents is silent and ugly: without it, `cols = min(max_cols, 0)` is `0` and `rows = -(-n // cols)` raises `ZeroDivisionError` — a poor thing to hand a future caller for the sake of removing two lines. The non-zero logic was not touched, and is re-asserted for n = 1, 3, 4, 9, 13.

## Step 5 — Verification

A **baseline was captured before any edit**: every figure's `to_json()` for 7 tickers × 3 chart types plus 4 comparisons, together with the pickled `metrics_long` / `valuation_history` / `facts_out`. The verification reuses those exact frames, so any difference is attributable to the code change and not to data drift — yfinance re-adjusts its price history between pulls, which has produced false positives in this project before. **All checks passed.**

**Default-path non-regression — the decisive check.** All **21 per-ticker figures byte-identical** to the pre-task baseline, spanning the three profiles the brief named and four more:

| ticker | profile | fundamentals | valuation | growth |
|---|---|---|---|---|
| AAPL | `standard` | 50,191 B ✓ | 23,294 B ✓ | 18,966 B ✓ |
| JPM | `financial` | 52,374 B ✓ | 15,679 B ✓ | 18,876 B ✓ |
| AMT | `reit` | 25,630 B ✓ | 16,138 B ✓ | 18,821 B ✓ |

(MSFT, BAC, AFL and O likewise.) All **4 comparison figures byte-identical**, including the returned `excluded` list.

*A first run failed exactly here, on the comparisons only.* The diff showed `data equal: True`, `layout equal: True`, identical key sets and identical length (14,548 B) — the difference was purely the **order** in which layout keys were serialised, caused by moving `width`/`height` to the end of the layout dict. Structurally harmless, but a real byte difference in a written `.json`, so the fix was to restore the original keyword position via the splat form above rather than to soften the claim. The per-ticker figures had happened to survive the same reordering, which is precisely why "it passed for those" was not sufficient evidence.

**Panel narrowing and re-tiling.** AAPL's 9 visible fundamentals panels narrowed to 3 render exactly the expected titles in config order; grid 3×3 → 1×3 with `width`/`height` following `_make_grid`; 3 axes for 3 panels, i.e. no trailing empty cells. Narrowing to 1, 4 and 7 gives 1×1, 2×3, 3×3 with matching axis counts. `build_growth` and `build_valuation` narrow correctly too, both in config order.

**`is_hidden` cannot be bypassed.** Three cases, each with the precondition asserted against `config.is_hidden` first: `p_ffo` for AAPL (`standard`, valuation chart), `efficiency_ratio` for AAPL (fundamentals), `fcf_margin` for JPM (`financial`). In each, requesting `[hidden_concept, visible_concept]` renders only the visible one, and the printed note names the reason. An unknown concept (`does_not_exist`) is likewise ignored with `(unbekannt)` and the call is **not** refused — the Step 1.2 behaviour actually observed, not assumed.

**Narrowing to nothing** returns `None` for all three builders, both for an empty list and for a list containing only hidden concepts, and `plot_fundamentals(..., concepts=[])` writes neither file.

**Responsive sizing.** `width=None` produces a layout whose key set contains no `width` (verified against the serialised JSON, not the Python object), with `height` still 990; `width=None, height=None` omits both; explicit `1234`/`567` are honoured; the default call carries exactly today's `width=1500, height=990`. Confirmed for all three per-ticker builders and for the comparison, which keeps its `meta` and `hovermode` when resized.

**`as_of` window,** on JPM/`pe_ratio`:

| call | x-range | points |
|---|---|---|
| default | 2021-09-30 … 2026-03-31 | 19 |
| `as_of=2020-06-30` | 2015-06-30 … 2020-06-30 | 21 |

Both bounds checked against the expected window (`last ≤ 2020-06-30`, `first ≥ 2015-06-30`), and the point count checked against the number of rows the raw frame actually has in that window (21 = 21) rather than merely against "fewer than before". `as_of=None` reproduces the default figure byte-for-byte. `build_valuation` and `build_ticker_comparison` return the identical window for the same ticker/metric/date. `as_of` leaves a non-valuation comparison (`revenue_yoy_growth`) byte-identical, confirming it is inert where no window was ever applied. Both wrappers pass it through to the written file.

**Purity constraint held:** no Streamlit import, no module-level mutable state, and no file-path knowledge outside the `plot_*` wrappers.

No scratch scripts were left behind; the isolated baseline/verification workspace was deleted after the run.
