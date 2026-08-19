# Explaining empty valuation charts

Measured 2026-08-19 against `data/app/` (export of 2026-08-16, 500 tickers). One file changed:
`app.py`. `figures.py`, `config.py` and the pipeline are untouched, confirmed by diff and by
rebuilding 11 charts against `HEAD:figures.py`.

---

## 0. The premise needed correcting first

The brief says V, STZ, ERIE and BKR "render **no** valuation metrics at all — every multiple is
blank across their whole history". **That is not what the export contains.**

| ticker | non-null valuation values | multiples present | span |
|---|---:|---:|---|
| V | **456** | 7 of 9 | 2008-09 → 2026-03 |
| STZ | **418** | 6 of 9 | 2008-02 → 2026-05 |
| ERIE | **203** | 5 of 9 | 2008-12 → 2026-06 |
| BKR | 47 | 5 of 8 (2 values each) | 2016-12 → 2026-06 |

`pb_ratio`, `pfcf_ratio`, `ev_sales`, `ev_ebitda` and `ev_fcf` all work for these tickers, because
they are built from market capitalisation, which comes from the market-data share count, not from
the EDGAR `SharesOutstanding` series.

**What is actually blank is the per-share family**: `pe_ratio` for all four, `pe_to_revenue_growth`
(which derives from it), and `dividend_yield` for three of them. `EPS_TTM_CALC` is
`NetIncomeLoss_TTM ÷ SharesOutstanding`, so it is the one place the missing EDGAR series bites.

**The user's experience is nonetheless exactly as described, for a reason the brief did not
name: the valuation tab's default selection is `pe_ratio`.** So these tickers open on a blank
panel. And a blank panel today is not the "no data" message — `build_valuation` returns a figure
as long as *any* selected concept has data, so `render()`'s `empty_message` never fires and the
reader gets **an axis grid with no line and no explanation**, directly under a working current
multiple.

That is the bug, and it is narrower and more fixable than "these tickers have no valuation data".

---

## 1. The detection rule

### 1.1 What is tested

**Per (ticker, metric, window): does the slice the panel would draw contain a non-null value?**

Not the absence of `SharesOutstanding`, and not an empty `valuation_history` slice for the ticker
as a whole. The brief warns that the two are not identical, and the data proves it in both
directions:

- V has a `valuation_history` slice that is far from empty (456 values) and still draws a blank
  `pe_ratio` panel.
- **EA has 70 `SharesOutstanding` points, 70 `EPS_TTM_CALC` points, 72 `StockholdersEquity`
  points — and not one non-null value in any real multiple.** Its only valuation rows are 69
  `buyback_distortion_flag` values. Testing for share-count absence would miss it entirely.

Testing what the panel actually draws is exact, needs no maintained list, and cannot claim a
cause it has not established.

### 1.2 The threshold — measured, and the finding is that no threshold works

Step 1.2 asks how many share-count points are needed before a multiple appears. Measured across
the 471 tickers for which `pe_ratio` is plottable:

| | min among tickers that **produce** `pe_ratio` | max among tickers that produce **none** |
|---|---:|---:|
| `EPS_TTM_CALC` points | **3** | **70** |
| `SharesOutstanding` points | **9** | **70** |

**The distributions overlap completely.** Q produces a `pe_ratio` from 3 EPS points; EA produces
none from 70. Any cut-off would be wrong in both directions at once.

So the threshold is not a number — it is the direct test in 1.1. That is a better rule than the
one the brief anticipated, and it is derived rather than chosen.

### 1.3 Which tickers the rule identifies

`pe_ratio` blank: **six tickers, not four** — and they have **four different causes**:

| ticker | shares | EPS | equity | cause |
|---|---:|---:|---:|---|
| **V** | 0 | 0 | 71 | no share-count series at all — established in `dei_shares_fallback_report.md` §2.1 |
| **STZ** | 0 | 0 | 67 | same |
| **ERIE** | 0 | 0 | 67 | same |
| **BKR** | 2 | 2 | 42 | share series present but too thin |
| **PSKY** | 7 | 2 | 13 | shares present, EPS thin — a different link in the chain |
| **EA** | 70 | 70 | 72 | **nothing missing on the fundamentals side at all** |

**EA is the new finding and it is not the same cause.** EA was taken private — `25-NSE` filed
2026-08-04, `15-12G` 2026-08-14, last Yahoo price 2026-08-10, recorded in the changelog on
2026-08-19. This export ran 2026-08-16, after the delisting. EA has complete fundamentals and no
usable price side, so **every** multiple is empty while every input is present. It is the exact
case Step 1.1 warns about, and it is why the notice states the symptom unconditionally and the
cause only when it can prove it.

### 1.4 Partial cases, and the true scope

Step 1.3 asks whether a partial case exists — a short but non-empty valuation history caused by
thin share data. **Yes: BKR and PSKY.** BKR draws 2 points for `pb_ratio`, `pfcf_ratio`, `ev_fcf`,
`pfcf_ex_sbc` and `ev_sales`, and 0 for `pe_ratio`. That is a stub, not an absence.

**No second message was built for it.** A two-point line is drawn, so the panel is not blank and
the notice does not fire; there is nothing for a second variant to say that the chart does not
already show.

The wider scope matters and is worth stating plainly: **170 of 500 tickers have at least one
empty panel** among the metrics their profile plots.

| concept | tickers with it empty |
|---|---:|
| `dividend_yield` | **97** |
| `ev_ebitda` | 35 |
| `ev_fcf` | 32 |
| `pb_ratio` | 30 |
| `ev_sales` | 17 |
| `pe_to_revenue_growth` | 9 |
| `pfcf_ex_sbc` | 9 |
| **`pe_ratio`** | **6** |
| `pfcf_ratio` | 5 |
| `p_tbv` / `p_core_earnings` / `p_ppnr` | 3 / 2 / 2 |

The largest group by far is `dividend_yield` on companies that pay no dividend. **That is a true
statement about the business, not a defect**, and it is what forced the wording in §2. The notice
only ever discusses the metrics the reader actually selected, so a reader looking at `pe_ratio`
on a non-payer never sees it.

---

## 2. The message

```
No data for: P/E ratio — nothing to draw in this window. No share-count history is
available for this ticker in the SEC's structured data, and every per-share multiple
needs one as its denominator. The current multiple above still works because it is
computed from market data, which has no filed-history equivalent. Nothing was hidden
or filtered — the value is absent from the source data, and the empty column is still
listed in the Data tab.
```

The second sentence is **conditional** — it appears only when the ticker has zero
`SharesOutstanding` values, which is true for V, STZ and ERIE and for nobody else. BKR (2 points),
PSKY (7) and EA (70) get the notice without it.

The three required elements:

1. **What is missing** — the named metric, and, where established, that the share-count history is
   the denominator every per-share multiple needs.
2. **Why the snapshot still works** — the current figure comes from market data, which has no
   filed-history equivalent. Without this the reader concludes the tool is broken rather than the
   data absent.
3. **Absent, not filtered** — with a pointer to the Data tab, where the empty column is still
   listed.

### What it deliberately does not claim

**Not "because of dimensional tagging."** That is established for V and STZ in the fallback
report — they are missing EPS as well as shares, which is the signature — but the app cannot
demonstrate it for an arbitrary future ticker from the frames it loads. It is an explanation for
a report, not an assertion for a UI.

**Not "this is a gap in the source data."** The first draft said exactly that, and §1.4 shows why
it is wrong: 97 of the affected tickers are non-dividend payers, for whom the absence is correct
and expected. "Nothing was hidden or filtered — the value is absent from the source data" is true
for all 170 and still makes the project's own distinction between an honest gap and a suppressed
value.

**Not a per-ticker claim.** "This ticker has no valuation data" would be plainly false for V,
which has 456 values across seven multiples. The notice is per panel because the failure is per
panel.

---

## 3. Where it appears

### 3.1 The valuation tab — built

An `st.info` under the chart, listing the empty panels among those selected. It sits under rather
than in place of the chart, because with a mixed selection (V with `pe_ratio` **and** `pb_ratio`)
the figure still has a real panel to draw; replacing it would remove working output.

### 3.2 The data tab — already covered, with one blind spot

**No new treatment.** `pivot_ticker` passes `dropna=False` specifically so that "a concept that
exists for the ticker but is null in every period must stay as an all-null column", and the
section caption already reports *"N null in every period shown — kept on purpose, an empty column
is a finding"*. Verified: V's valuation pivot keeps `pe_ratio` as an all-null column and it is
counted. This is the same family of statement and the existing convention already says it.

**The blind spot, recorded not fixed:** the *input* is invisible. V has **zero rows** for
`SharesOutstanding` in `facts_full`, and a concept with no rows never becomes a column, so the
null-column count cannot see it — the facts table simply has one fewer column than another
ticker's. Making absent-entirely concepts visible there is a change to `pivot_ticker`'s contract
and is out of scope.

### 3.3 The comparison tab — wording unified, `figures.py` untouched

`build_ticker_comparison` returns `('V', 'No Data')`, and the app rendered that string directly.
Two different explanations of the same absence in two tabs is exactly the failure to avoid, and
the brief also forbids touching `figures.py`.

Resolved by keeping the fact in `figures.py` and moving the wording to the app: the `"No Data"`
reason is translated to *"no values in this window"*, with *"— no share-count history is available
for it"* appended under the same condition as the valuation notice. `figures.py` still reports the
raw reason; only presentation changed, which is where presentation belongs.

### 3.4 The snapshot marker — checked, and it is already coherent

The concern was a lone green diamond on an otherwise empty chart. **It does not happen.** For V's
`pe_ratio` the figure has **zero traces** — no line and no marker — because `build_snapshot` does
not compute `pe_ratio` for V either, for the same reason the history is missing. Verified:
`pe_ratio` is absent from V's snapshot concepts.

The marker does render where it should: BKR's `pfcf_ratio` draws its two historical points **and**
a snapshot marker, because BKR has a current `pfcf_ratio`. Nothing to change.

---

## 4. Verification

| check | result |
|---|---|
| rule matches an independent recomputation over all 500 tickers | **identical**, 170 tickers |
| `pe_ratio` blank for exactly BKR, EA, ERIE, PSKY, STZ, V | ok |
| `share_history_absent` true for exactly V, STZ, ERIE | ok |
| BKR (2), PSKY (7), EA (70) get the notice **without** the cause clause | ok |
| three unaffected tickers across profiles (AAPL `standard`, JPM `financial`, MSFT `standard`) — no blank panel, no notice | ok |
| chart output identical to `HEAD:figures.py` | **11 of 11 cases** |
| `figures.py`, `config.py`, `main.py`, `metrics.py`, `quality.py`, parsers, fetchers | **unmodified** (git diff empty) |
| `app.py` imports no pipeline module | ok — `figures` only |
| notice fires per selection, not per ticker | V+`pe_ratio` → fires; V+`pb_ratio` → silent; V+both → names only `pe_ratio` |

The chart-identity check runs in a **separate process that never imports `streamlit`**, per the
constraint in `metrics_registry_report.md` that importing Streamlit swaps Plotly's default
template. It compares the working tree against `HEAD:figures.py` loaded side by side.

> A harness bug worth recording, because it produced a convincing false alarm: extracting
> `HEAD:figures.py` with `subprocess.run(..., text=True)` decodes git's bytes with the cp1252
> locale default, which mangles the `Ø` in the mean-line label. Nine of eleven figures then
> differed on `layout.annotations[1].text` — `'? (harm.) 23.7'` against `'Ø (harm.) 23.7'` — in
> files that were byte-identical. Reading bytes and writing them unchanged fixed it. A
> "difference" in a non-ASCII label is worth checking against the harness before the code.

### What could not be verified without a browser

The notice's **rendering** — that `st.info` places it where intended relative to the chart and the
outlier caption, that the bold markup renders, and that it does not push the chart below the fold
on a narrow window. What was verified is that the code path is reached with the right arguments
for the right tickers, that the strings contain the required elements, and that `app.py` parses
and imports cleanly. Streamlit callbacks and layout were not executed.

---

## 5. Deliberately not done

**No second message for the partial case.** BKR and PSKY draw a stub, which is visible; a message
would restate the chart.

**No change to `figures.py`'s `"No Data"` reason**, per the brief. The app translates it, so the
two tabs agree without the library needing an opinion about phrasing.

**No fix for the data tab's absent-concept blind spot** (§3.2) — a change to `pivot_ticker`'s
contract, out of scope here.

**EA's delisting is not handled.** It is in the universe with complete fundamentals, no tradeable
price, and every multiple empty. The notice will fire for it and say the honest thing, but the
real decision — remove it as SATS was, or keep it — is carried forward from the changelog entry of
2026-08-19 and is not a UI question.

**The 97 `dividend_yield` cases were not suppressed.** They are correct absences and the notice
now reads correctly for them, but a reader selecting `dividend_yield` on a non-payer still gets a
notice telling them there is no data. Whether a metric that is structurally inapplicable to a
business should be offered in the multiselect at all is a `PROFILE_HIDDEN` question, which the
brief excludes.
