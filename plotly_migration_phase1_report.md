# Plotly Migration — Phase 1 Report (Core Per-Ticker Chart Migration)

**Date:** 2026-08-03
**Scope:** `figures.py` rewritten matplotlib → Plotly; six call sites in `main.py` updated; `requirements.txt` swapped `matplotlib>=3.7` → `plotly>=6.0`. `config.py` untouched. No Phase 2/3/4 capability (toggle buttons, ticker overlays, cross-sectional plots) implemented.

---

## Step 1 — Findings from reading the current implementation

- **Callers:** exactly six call sites, all in `main.py` — three in the ad-hoc `main()` path (old lines 1337–1339) and three in `run_full_refresh()` (old lines 1553–1555). All passed `os.path.join(FIGURE_DIR, f"{ticker}_<kind>.png")`. No other module calls any plot function.
- **matplotlib usage:** confined to `figures.py` (verified by grep over every `.py` in the project). Nothing else imports `matplotlib`, `pyplot`, `mdates`, or `PercentFormatter`, so removing them from `figures.py` removes them from the project.
- **`GROWTH_PANELS` vs `get_growth_panels()` (known fact confirmed):** `plot_growth` is driven by the static `GROWTH_PANELS` list (`Revenue`, `NetIncomeLoss`, `SharesOutstanding` from `facts.yoy_growth`). `get_growth_panels()`, `GROWTH_BASE_PANELS`, and `GROWTH_PROFILE_EXTRA` have **zero consumers anywhere in the project** — they are defined in `config.py` and imported by nothing. They drive nothing today; their names (`fcf_growth`, `nii_growth`, …) are snapshot-metric-style strings, presumably staged for a future cross-sectional feature. All verification in this task compares against `GROWTH_PANELS`, as instructed.
- **`is_hidden` namespaces:** the migration passes through the exact strings the old code passed — metric names (`c[0]` from `FUNDAMENTALS_TO_PLOT`/`VALUATIONS_TO_PLOT`), the `QUARTERLY_COUNTERPART` values (e.g. `operating_margin_quarterly`), and capitalized concept names from `GROWTH_PANELS`. No normalization anywhere; the selection comprehensions are literally the same expressions as before.

## Step 2 — Design decisions

**2.1 Dual-output file naming.** The single `output_path` parameter is kept and treated as a **stem**: the function writes `{stem}.html` and `{stem}.json`. A defensive rule strips a trailing `.png`/`.html`/`.json` extension if one is passed (whitelist, not `splitext` unconditionally — a blanket strip would mangle dotted tickers like `BF.B_growth`). The six call sites in `main.py` now pass extension-less stems (`f"{ticker}_fundamentals"` etc.), so `figures/AAPL_fundamentals.html` + `.json` land exactly where the `.png` used to. Rationale: signature stays stable for callers, "both files or neither" is enforced in one place (`_write_figure`), and an old-style `.png` call still does the right thing.

**2.2 Subplot grid.** `_make_grid` is preserved verbatim (max 3 columns, `rows = ceil(n/cols)`, `(1,1)` for n=0 — though the n=0 branch is now unreachable, see 2.7). Trailing grid cells are **never created**: `make_subplots` receives a `specs` matrix with `None` for cells beyond the panel count. Verified empirically that `subplot_titles` takes exactly one title per actual (non-`None`) panel. This replaces `ax.axis("off")` with genuine absence.

**2.3 `symlog` — dropped.** Confirmed programmatically: every 5th tuple element in `FUNDAMENTALS_TO_PLOT` is `False` (asserted in the verification run), and `plot_valuation` never passed the flag. The parameter is removed from both helpers. Because `config.py` must not change, `plot_fundamentals` still unpacks the 5-tuple and discards the flag (`_symlog`), with a comment stating why. Rationale: keeping a parameter that renders nothing is fake parity; if symlog is ever wanted, Plotly has no native symlog and the honest implementation is a log-modulus transform of the data plus custom ticks — a deliberate future task, not a dead code path shipped now.

**2.4 "keine Daten" placeholder.** A red annotation at the center of the empty subplot, in domain coordinates (`xref="x{k} domain"`, via `add_annotation(..., row=, col=)`), with both axes set `visible=False` — visually equivalent to the old red `ax.text` with blanked ticks. Panel title still appears (it comes from `subplot_titles`, as `ax.set_title` did before).

**2.5 Percent format, reference lines, mean labels.**
- Percent axes: `tickformat=".1~%"` (d3): `0.25` → "25%", `0.034` → "3.4%" — matching `PercentFormatter(xmax=1)` behavior of scaling fractions and trimming noise.
- Reference lines: `add_hline(y=ref, line_color="red", line_width=1, row=, col=)` — one per panel, exactly where `ax.axhline` was.
- Mean line: the value is computed **unchanged** — `metrics.harmonic_mean(filtered["value"])` for `HARMONIC_MEAN_CONCEPTS`, `Series.mean()` otherwise — and the displayed string is the identical f-string (`Ø (harm.) 23.4` / `Ø 2.64%`). Conveyance: the old per-axes legend has no Plotly equivalent (Plotly's legend is global), so the label is an **annotation pinned top-left inside the subplot** (red, size 10), which is where the old one-line legend visually sat. A legend-carrying dummy trace was rejected: 13 valuation panels would dump 13 near-identical "Ø …" entries into one global legend.
- **Plotly 6.9 trap discovered and worked around:** `add_hline(..., annotation_text=..., row=, col=)` is a *silent no-op* — neither shape nor annotation is created. The mean line is therefore drawn as a plain `add_hline` plus a separate `add_annotation` in domain coordinates. (Plain `add_hline` with `row`/`col` works fine.)
- Non-finite guard: if the mean is NaN/inf (possible only when all values are NaN), no line and no label are drawn — the old code would have drawn an invisible line labeled `nan`; the verification asserts this branch renders nothing rather than garbage.

**2.6 TTM+quarterly overlay.** Preserved as two always-visible traces on the same subplot: TTM `width=1.5`, Quartal `width=0.8, opacity=0.6` — the same visual hierarchy as matplotlib. Legend entries are `"{concept} · TTM"` / `"{concept} · Quartal"`; every data trace carries a legend entry, so native legend-click-to-toggle works per trace. Colors are pinned (`#1f77b4`/`#ff7f0e`) because matplotlib restarted its color cycle per axes while one Plotly figure cycles across all subplots — without pinning, panel 3 would be green and dual panels inconsistent. The button-based TTM/Quartal toggle is explicitly Phase 2 and was not built.

**2.7 Degenerate cases (now defined explicitly).**
- **Missing growth column:** warning printed (`[plot_growth] {ticker}: column '...' missing, skipping chart output.`), **neither** file written. Same net behavior as the old silent `return` (no file), now with a log line and the both-or-neither guarantee.
- **Zero visible panels:** skip-with-warning, applied identically in all three plot functions — no files. Chosen over a placeholder figure because an empty chart file carries no information and the web app can rely on absence. The old behavior differed per function (fundamentals/valuation: near-empty PNG with only a suptitle; growth: crash in `plt.subplots(1, 0)`), so this is strictly a cleanup of undefined behavior. **Regression check:** a scan over all 501 active tickers shows minimum panel counts of 4 (fundamentals), 5 (valuation), 3 (growth) — no ticker reaches the zero-panel branch today, so nothing that was shown before disappears.

## Step 3 — What was implemented

- `figures.py` fully rewritten. Same five public names (`plot_metric`, `plot_metric_dual`, `plot_fundamentals`, `plot_growth`, `plot_valuation`); the helpers' first parameter changed from a matplotlib `ax` to `(fig, row, col)` — unavoidable, since no axes object exists — while the three top-level functions kept their `(ticker, dataframe, output_path[, extra])` signatures.
- **No global state:** each function constructs its own `go.Figure` via `make_subplots`, writes both outputs, and drops the reference. No module-level registries, no pyplot, no mutation of any Plotly global (templates are read, never written). Safe for concurrent calls.
- HTML is written with `include_plotlyjs=True, full_html=True` — fully self-contained per the task (≈4.9 MB each because plotly.js is embedded; at 501 tickers × 3 charts that is ~7.4 GB per full refresh — if that cost ever bites, `include_plotlyjs="directory"` writes one shared `plotly.min.js` per output folder, at the price of files no longer being individually self-contained).
- JSON via `fig.write_json`. Note for the web app: Plotly 6 serializes numeric arrays as typed-array dicts (`{"dtype": "f8", "bdata": "<base64>"}`), which `plotly.js` consumes natively and `plotly.io.from_json` round-trips.
- Sizing matches the old figsize at 100 dpi: 500px/column; 330 (fundamentals), 360 (growth), 400 (valuation) px/row. X-axes: `dtick="M24", tickformat="%Y"` = `YearLocator(2)` + `DateFormatter("%Y")`.
- Callers: the six `main.py` call sites now pass extension-less stems. No other changes to `main.py`.
- **Removed:** all matplotlib imports and usage. Safe because grep shows no other file references matplotlib in any form; `requirements.txt` updated accordingly (`matplotlib>=3.7` → `plotly>=6.0`). Plotly 6.9.0 was installed into the project venv. (Pre-existing, unrelated observation: the venv runs pandas 3.0.3 while `requirements.txt` pins `<3.0`; left as is.)

## Step 4 — Programmatic verification (no eyeballing)

Method: the real pipeline (cached EDGAR facts + live yfinance prices) was run in-memory for **AAPL (standard), JPM (financial), O (reit)** — three meaningfully different hidden-metric sets: fundamentals 9/9/4 panels, valuation 9/5/6 panels. The run used an isolated working directory with a copied cache, so `data/`, `figures/`, and `cache/` of the project were not touched (the live `data/*.csv` currently holds a single-ticker META run that must not be overwritten). Every check reads the **written `.json` back** via `plotly.io.from_json` and compares against expectations computed from config + source dataframes using the *old* code's selection expressions. Result: **all checks passed** (exit 0), including:

- **Panel sets:** for all 9 ticker×chart combinations, the ordered subplot-title list equals the matplotlib-era selection (`[c for c in FUNDAMENTALS_TO_PLOT/VALUATIONS_TO_PLOT if not is_hidden(t, c[0])]`, `[c for c,_ in GROWTH_PANELS if not is_hidden(t, c)]`). Growth was verified against **`GROWTH_PANELS`**, not `get_growth_panels()`.
- **Both outputs exist and are valid:** all 18 files non-empty (HTML 4.87–4.91 MB self-contained, JSON parses as JSON *and* reconstructs via `from_json` with matching trace/subplot counts).
- **Trace-level equality:** trace name lists match the data-driven expectation exactly, including dual panels (JPM fundamentals: 9 panels → 12 traces because `payout_ratio`, `efficiency_ratio`, `provision_ratio` render TTM+Quartal pairs; dual styling asserted: width 1.5/0.8, opacity 0.6).
- **Values:** every growth trace's y-array is numerically identical to the source dataframe's `yoy_growth` column (e.g. AAPL Revenue 68 points, O SharesOutstanding 65 points; decoded from the typed-array JSON encoding).
- **Mean lines — every non-empty valuation panel checked, both paths exercised:** harmonic (e.g. JPM `pe_ratio` → line at 9.9114, label `Ø (harm.) 9.9`; O `p_ffo` → 17.2207, `Ø (harm.) 17.2`) and arithmetic including the percent-label branch (JPM `dividend_yield` → 0.0264, `Ø 2.64%`; O `dividend_yield` → 0.0586, `Ø 5.86%`). Line y-position and label string both recomputed independently from the source dataframe.
- **Reference lines & formatting:** `ref_line` shapes present at exactly the configured y (0-lines, and growth zero-lines on every non-empty panel); `tickformat == ".1~%"` on every percent panel and `None` on non-percent panels (e.g. O `debt_to_equity`).
- **"keine Daten":** the set of placeholder annotations equals the set of panels whose source slice is empty (O valuation: 1 of 6 panels).
- **Degenerate cases behave as designed:** dataframe without `yoy_growth` → warning, neither file written; `is_hidden` forced to all-hide → all three functions skip with a warning and write nothing. Zero-panel scan over all 501 active tickers confirms this branch is unreachable in production data.
- **Stem handling:** `.png`-style legacy path, extension-less stem, and dotted-ticker stem (`BF.B_growth`) all map to the correct `.html`/`.json` pair.
- `import main, figures, config, metrics, parsers.parse_edgar` succeeds from the project directory.

**Non-regression statement:** what gets plotted and why is decided by the same config objects through the same expressions; the verification demonstrates set-equality of rendered panels against the old selection for three profiles and zero-panel-safety for all 501 tickers. `config.py` was not modified. The only intentional behavioral deltas are the output format itself (`.html`+`.json` instead of `.png` — old PNGs in `figures/` are left in place and simply stop being refreshed) and the now-defined degenerate-case handling, which no production ticker triggers.

## Removed, and why it was safe

`import matplotlib.pyplot`, `matplotlib.dates`, `matplotlib.ticker.PercentFormatter`, all `plt.*` calls, and the `symlog` rendering path. Grep across every `.py` in the project shows `figures.py` was the sole matplotlib consumer, and the verification above re-exercises every feature the removed code provided (grids, titles, ylabels, percent axes, ref lines, mean lines with labels, dual overlays, placeholders, 2-year date ticks). `requirements.txt` no longer lists matplotlib.

No scratch scripts were left behind; the isolated verification workspace was deleted after the run.
