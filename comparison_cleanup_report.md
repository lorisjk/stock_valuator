# Comparison-Chart Cleanup + Figure-Returning API — Report

**Date:** 2026-08-05
**Touched:** `figures.py`, `main.py`, `config.py` (removal only). No Streamlit code, no Phase 4, no change to share-tag resolution.

---

## Step 1 — Removal of the batch comparison layer

Grepped the whole repo for `COMPARISON_GROUPS`, `render_comparison_charts`, `plot_ticker_comparison`, `concept_source`, `MAX_COMPARISON_TICKERS` and `compare_` before deleting anything. Outside `venv/` and the markdown reports, the batch layer had exactly six touchpoints — the two call sites were **not** the only references:

| location | what it was |
|---|---|
| `config.py` | the `COMPARISON_GROUPS` list (8 groups) and its comment block |
| `main.py` import block | `COMPARISON_GROUPS` from `config` |
| `main.py` import block | `plot_ticker_comparison, concept_source` from `figures` |
| `main.py` ~1242 | `render_comparison_charts` itself |
| `main.py` ~1372 | call site in `main()` |
| `main.py` ~1591 | call site in `run_full_refresh()` **plus** its `t0`/`comparison_time` timing and the modified total-time print |

All six removed. `run_full_refresh()`'s summary line is back to `calc_time + sum(plot_times.values())` exactly as it read before Phase 3 — `write_full_refresh_report` never received `comparison_time`, so its signature and output are untouched.

**Nothing consumed the `compare_*` output files.** Grepped for `FIGURE_DIR`, `.html`, `listdir`, `glob` and `figures/` across every `.py`: `FIGURE_DIR` appears only where charts are *written*, and no code in the project ever reads a figure file back. Verified programmatically that `config.COMPARISON_GROUPS` and `main.render_comparison_charts` no longer exist and that no removed token survives in either source file.

**Existing `figures/compare_*.html` / `.json` on disk are left in place.** They simply stop being refreshed — the same treatment Phase 1 gave the old matplotlib PNGs. They will silently go stale; delete them whenever you like.

`plot_ticker_comparison`, `build_ticker_comparison`, `concept_source`, `_concept_plot_spec` and the palette all stay in `figures.py` — verified present after the removal.

## Step 2 — The build/write split

### 2.1 Naming and shape

```python
build_ticker_comparison(tickers, concept, data, years=5, value_column=None)
        -> tuple[go.Figure | None, list[tuple[str, str]]]
plot_ticker_comparison(tickers, concept, data, output_path, years=5, value_column=None) -> None
```

Convention: **`build_*` returns a figure and does no I/O; `plot_*` is a wrapper that writes it.** The wrapper is four lines — call the builder, return early if `None`, hand the figure to `_write_figure`. No rendering logic is duplicated, and the verification proves it byte-for-byte (below).

This convention extends unchanged to the per-ticker charts (`build_fundamentals`/`plot_fundamentals`, etc.), which is why it was chosen over alternatives like a `write=False` flag (a boolean that changes the return type is worse than two functions) or returning the figure from `plot_*` (which would leave the "no I/O" promise unexpressed in the signature).

**Is the file-writing wrapper worth keeping? Yes.** `main.py`'s two plot loops still write files, the standalone self-contained HTML is how you look at a chart today without a web app, and Phase 1's dual HTML+JSON convention lives in `_write_figure`. Deleting the wrapper would push `_write_figure` calls into `main.py` and spread output-path knowledge across modules. It costs four lines.

### 2.2 How exclusion information reaches the caller

**Three channels, one computation.** The dropped-ticker list is built once and surfaced as:

1. **Return value** — `excluded: list[tuple[str, str]]`, e.g. `[("AAPL", "für Profil 'standard' ausgeblendet")]`. This is the primary channel for a Python caller (Streamlit renders it as an `st.caption` or `st.warning`).
2. **`fig.layout.meta`** — `{"concept": ..., "tickers": [...plotted...], "excluded": [{"ticker": ..., "reason": ...}]}`. Verified to survive `to_json`/`from_json`, so a consumer that receives only the serialised figure — the JS frontend reading the `.json` — learns the same thing. The return value cannot travel that way.
3. **The red on-chart annotation**, unchanged from Phase 3, for whoever opens the standalone HTML with no code around it.

**The tradeoff of returning a tuple:** every caller must unpack it even when it only wants the figure, and the exclusion list is lost the moment the figure is passed on alone. Channel 2 exists precisely to cover that second weakness. The reason the tuple is nonetheless the primary channel — rather than making `layout.meta` the only mechanism — is the degenerate case: **when nothing survives there is no figure to hang meta on**, and that is exactly the case where the caller most needs to know why. A single return channel would have to be the tuple regardless.

**Reason strings are the human-readable German text, not codes.** One string feeds all three channels plus the console message, so the chart, the caption and the JSON can never drift apart. The cost: a caller wanting to branch on *why* a ticker was dropped would be string-matching. That is the right trade here because the authoritative answer is one call away — `is_hidden(ticker, concept)` — and the caller can ask it directly rather than parse prose.

### 2.3 Degenerate cases

`build_ticker_comparison` returns `(None, excluded)`. Not an empty figure (the caller would have to introspect `len(fig.data)` to tell "nothing to show" from "a chart"), and not an exception (an all-hidden request is a legitimate data outcome, not a programming error — and per Step 3's reasoning, a rendering layer should not turn a UI mistake into a traceback).

The two "nothing to draw" cases stay distinguishable through `excluded`:

| outcome | `fig` | `excluded` | meaning |
|---|---|---|---|
| every requested ticker dropped | `None` | non-empty | a data outcome — show the reasons |
| fewer than 2 distinct tickers, or unknown concept | `None` | `[]` | the request itself was rejected |

`plot_ticker_comparison` translates `fig is None` into writing neither file, so Phase 1's both-files-or-neither guarantee is unchanged.

## Step 3 — The ticker cap

Implemented the recommendation.

- **The hard upper cap is gone from the rendering layer.** `MAX_COMPARISON_TICKERS` no longer exists; four and five tickers now render (verified). It was a batch-config-era guard, and with a frontend picker the readable-width question belongs to whatever builds the picker.
- **`SUGGESTED_MAX_COMPARISON_TICKERS = 3` remains** as an advisory module constant, so the number lives in one place for `st.multiselect(max_selections=...)`. Renamed rather than kept as `MAX_*` deliberately: a name that reads like a limit invites someone to re-add an enforcement check against it.
- **`MIN_COMPARISON_TICKERS = 2` is still enforced.** One ticker is not a comparison — a category check, and the single-ticker charts serve that case better.
- **Palette widened from 3 to 10** (`#1f77b4, #d62728, #2ca02c, #9467bd, #ff7f0e, #8c564b, #e377c2, #17becf, #bcbd22, #7f7f7f`) so palette width cannot quietly become the real cap. The **first three are unchanged**, so every existing 2- and 3-ticker chart keeps its exact colors. Indexing is still `position % len(palette)`: beyond ten tickers colors **cycle** rather than raising `IndexError` — verified — which is what the advisory constant exists to keep rare. Phase 3's property is preserved: the index is the ticker's position in the **requested** list, so a ticker keeps its color when a *different* one is excluded.

## Step 4 — The per-ticker functions: built, not proposed

The brief says split them if the split is mechanical. It is, for all of them — each function builds a figure through a single linear path and hands it to `_write_figure` as its last statement, with early `return`s that become `return None`. No control flow was rearranged, no logic moved. So all three were split:

| function | split | note |
|---|---|---|
| `plot_fundamentals` | ✅ `build_fundamentals(ticker, metrics_long) -> go.Figure \| None` | pure cut |
| `plot_growth` | ✅ `build_growth(ticker, facts, growth_column="yoy_growth")` | pure cut; the wrapper keeps `output_path` in its original third position, so callers are unaffected |
| `plot_valuation` | ✅ `build_valuation(ticker, valuation_history, years=5)` | pure cut; the `years` cutoff stays inside the builder |

**A note on "the four per-ticker functions":** the brief says four, but there are three chart-producing functions. `plot_metric` and `plot_metric_dual` are panel-drawing helpers that mutate a figure passed in to them — they neither create nor write a figure, so there is nothing to split. They were left alone.

**Asymmetry with the comparison builder, deliberately.** `build_fundamentals`/`build_growth`/`build_valuation` return a bare `go.Figure | None`, while `build_ticker_comparison` returns `(fig, excluded)`. Returning `(fig, [])` from the other three purely for symmetry would be cargo-culting a second return value that can never carry information — a per-ticker chart has no cross-ticker exclusion concept.

**One intentional behavioural change:** the "nothing to draw" console messages now print from the builder and are prefixed accordingly (`[build_fundamentals] …: no visible panels, nothing to build.` instead of `[plot_fundamentals] …: skipping chart output.`). Keeping the old text would have had `build_fundamentals` claim to be skipping a file write it knows nothing about. Diagnostic output only; no data or file behaviour changed.

**Constraint honoured:** `figures.py` remains pure rendering — no Streamlit import, no module-level mutable state, and no file-path knowledge beyond the `output_path` a caller passes to a `plot_*` wrapper.

## Step 5 — Verification

Real pipeline (cached EDGAR facts, live yfinance prices) in an isolated working directory with a copied cache; the project's `data/`, `cache/` and `figures/` were untouched. Every assertion reads the written `.json` back. **All checks passed.**

**Removal is clean.** `config.COMPARISON_GROUPS` and `main.render_comparison_charts` are gone; `main` no longer exposes `plot_ticker_comparison` or `concept_source`; none of `COMPARISON_GROUPS`, `render_comparison_charts`, `comparison_time`, `compare_` appears anywhere in `main.py`, and `COMPARISON_GROUPS` appears nowhere in `config.py`. `main.py` imports cleanly and both `main()` and `run_full_refresh()` are callable.

**The per-ticker charts did not regress.** For **AAPL** (`standard`), **JPM** (`financial`) and **AMT** (`reit`), all three chart types: both files written and non-empty, and the rendered panel set equal to what `is_hidden` + the config lists prescribe — the same comparison Phase 1's Step 4 made (fundamentals 9/9/4 panels, valuation 9/5/6, growth 3/3/3). Additionally, for all nine ticker×chart combinations, **`build_*(…).to_json()` is byte-identical to the file `plot_*` wrote** — the strongest available statement that the wrapper adds nothing and the split changed no output.

*(A first run reported these nine as failures. The cause was in the check, not the code: it compared `build_*.to_json()` against `plotly.io.from_json(written).to_json()`, and a JSON round-trip re-serialises to an equal-but-not-identical string. Diagnosed by comparing the raw written string directly — `written == built` was `True` at 50,191 bytes with `data` and `layout` structurally equal — and the assertion was corrected to compare against the file contents.)*

**Degenerate paths unchanged:** missing growth column and all-hidden (all three chart types) still write **neither** file, and the corresponding builders return `None`.

**The comparison function still behaves identically** where it was not intentionally changed: per-ticker `is_hidden` exclusion with the on-chart note (`p_ffo` dropping AAPL, `efficiency_ratio` dropping AAPL); the cross-profile positive case JPM/BAC/AFL on `p_tbv`; valuation-window equality against `plot_valuation` (JPM 2021-09-30…2026-03-31, 19 points; BAC 20 points — element-wise identical x and y); growth-concept routing through `yoy_growth` (72 points); and color stability when a ticker is excluded (AMT stays `#1f77b4`, O shifts `#d62728`→`#2ca02c`).

**The return-a-figure path was exercised directly**, with no `output_path` anywhere: `build_ticker_comparison(["JPM","BAC","AFL"], "p_tbv", …)` returns a `go.Figure` with the three expected traces and `excluded == []`. For the known mismatch case `["AMT","O","AAPL"]` on `p_ffo` it returns `excluded == [("AAPL", "für Profil 'standard' ausgeblendet")]`, the identical information on `fig.layout.meta["excluded"]` (which survives a `to_json`/`from_json` round trip), `meta["tickers"] == ["AMT","O"]` recording what *was* drawn, and the red on-chart annotation still present. Both degenerate returns behave as designed — `(None, 2 reasons)` when everything is excluded, `(None, [])` for a 1-ticker request and for an unknown concept — and the wrapper turns `None` into neither-file.

**Cap:** `MAX_COMPARISON_TICKERS` absent, `SUGGESTED_MAX_COMPARISON_TICKERS == 3`, `MIN_COMPARISON_TICKERS == 2`; four tickers render with four distinct colors and five render too; palette length 10; index wrap-around confirmed to return to the first color rather than erroring.

No scratch scripts were left behind; the isolated verification workspace was deleted after the run.
