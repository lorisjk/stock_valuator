# Task: Data Inspection Layer — Export Completion + App Data Tab

**Depends on the app export layer task being complete and shipped.** Read
`app_export_layer_report.md`, `metrics_registry_report.md` and the current `main.py`, `app.py`,
`config.py` before changing anything.

## Context

The Streamlit prototype renders charts well. What it cannot do is show the **data behind them**,
which for this project is not a secondary feature: showing coverage honestly — what was
extracted, what is structurally not applicable, what failed — is the stated differentiator over
commercial providers that buy standardized data and show no provenance.

The goal is that a user looking at a ticker can walk the full chain from raw filing facts to the
final snapshot, inspect any level as a readable table, download it, and paste it into an LLM.

Two gaps block this today:

1. **`build_snapshot()`'s output is not exported.** It runs in the pipeline and is written as
   `current_snapshot.csv`, but `export_for_app()` does not include it, so the app cannot show it.
2. **`facts_growth.parquet` is narrowed to the three growth-chart concepts** (a correct decision
   for charting, 18,120 → 1,705 rows). The data layer needs the full facts frame, which contains
   both raw XBRL concepts (`Revenue`, `StockholdersEquity`, `Goodwill`, `LongTermDebt`, …) and
   the pipeline's derived ones (`Revenue_TTM`, `FCF_QUARTERLY`, `EPS_TTM_CALC`, …) — that pairing
   is precisely what makes the TTM derivation auditable.

**Explicitly NOT in this task:** no changes to `figures.py`, no changes to the chart tabs beyond
what is needed to add a new tab, no Phase 4, no `PROFILE_HIDDEN` refactor, no new metrics, no
`SharesOutstanding` fix, no deployment or auth work.

---

## Step 1 — Complete the export

Extend `export_for_app()` in `main.py`. Keep the existing five outputs unchanged, and add:

| file | contents |
|---|---|
| `current_snapshot.parquet` | the snapshot frame `build_snapshot()` produces |
| `facts_full.parquet` | the full facts frame — all concepts, not narrowed to growth panels |

Requirements and things to decide:

1. **Inspect the snapshot frame's actual shape first** and report it: columns, dtypes, one row
   per ticker or something else, and whether it is wide or long. Do not assume — the app's
   rendering depends on it.
2. **`facts_growth.parquet` stays** as it is. It is what the growth charts consume and it is
   10.6× smaller; do not merge the two. State in the report that this is deliberate duplication
   with a clear division of labour (charts vs. inspection).
3. **Confirm what `filter_hidden_rows` did before the export.** The exported frames are
   post-filter, which should mean a ticker's hidden metrics are already absent. Verify that
   empirically for a `financial` and a `reit` ticker rather than assuming it — the data tab must
   not become a way to see metrics that `is_hidden` deliberately suppresses.
4. **File size.** Report the resulting size of `facts_full.parquet` for the run you test with,
   and extrapolate to the full ~500-ticker universe. If it lands somewhere that would be a
   problem to ship, say so with numbers rather than trimming silently.
5. Extend `meta.json`'s row counts to cover the new files, and keep the write-then-`os.replace`
   atomicity and the "meta.json written last" rule.

## Step 2 — Long-to-wide pivot helper in `app.py`

Every exported frame is long (`ticker`, `end`, `concept`, `value`), which is unreadable as a
table and unusable for an LLM. Build one shared helper that pivots a long frame for a single
ticker into **rows = period end, columns = concept**.

Design points:

1. **Sort newest first.** A user opening the table wants the recent quarters, not 2009.
2. **Missing values stay visibly missing.** Do not fill, do not drop columns that are entirely
   empty for the ticker. A concept that is present in the frame but null for this ticker is
   information — it is the difference between "not applicable to this business model" and
   "extraction failed", and hiding it would defeat the purpose of this tab. (Concretely: `rotce`
   is ~52% null for AAPL in the sample data.)
3. **Display formatting vs. export precision must be separated.** On screen, raw fact values run
   to `339000000.0` and ratios to many decimals; both are hard to read. Decide a display
   treatment (e.g. thousands separators or scaled units for absolute values, fixed decimals for
   ratios) — but **the download and the LLM copy block must carry full unrounded precision**.
   State how you keep the two apart, and how you tell an absolute value from a ratio (the
   `METRICS` registry's `percent` flag covers the metric frames; facts are a separate case —
   say what you do there).
4. Handle a ticker with no rows in a frame without raising.

## Step 3 — The data tab

Add a new top-level tab alongside the existing chart tabs. It shows, for the currently selected
ticker, four sections corresponding to the pipeline chain:

| section | source | what it demonstrates |
|---|---|---|
| Raw & derived facts | `facts_full` | what came out of EDGAR, and what the pipeline derived from it |
| Calculated metrics | `metrics_long` | what the pipeline computes from those facts |
| Valuation history | `valuation_history` | multiples over time |
| Current snapshot | `current_snapshot` | the latest state, one row per ticker |

Requirements:

1. **Separate quality flags from metrics in the `metrics_long` section.** The frame mixes actual
   metrics with binary flags — in the sample data, `buyback_distortion_flag`,
   `fcf_exceeds_ebitda`, `inorganic_contaminated`, `low_tax_rate_flag` and `share_count_jump_flag`
   sit alongside `roe` and `operating_margin`. Rendering 0/1 flags as columns between ratios is
   noise, and worse, it buries information that matters: the flags are the pipeline telling the
   user where it is unsure. Give them their own presentation. Decide how to identify them —
   prefer something more robust than a `_flag` suffix match if the project offers one (check
   `config.py` and `quality.py` first and say what you found); if a name-based rule is the only
   option available, say so plainly and keep the rule in one place.
2. **Distinguish raw from derived in the facts section.** The `_TTM` / `_QUARTERLY` / `_CALC`
   suffixes carry that distinction. Make it visible (grouping, ordering, or a filter — your
   call), because seeing `Revenue` next to `Revenue_TTM` is how a user audits the TTM logic.
3. **A row/period limit with an explicit opt-out.** Default to a recent window (e.g. the last
   ~12–20 periods) with a control to show everything. State the default you chose.
4. **Per-section download button** producing the filtered, single-ticker table as CSV with a
   meaningful filename (e.g. `AAPL_metrics.csv`). Full precision, not display-rounded.
5. **An LLM-friendly copy block per section** — `st.code` with the table as CSV or Markdown text,
   which gives a built-in copy button. Default it to a smaller window than the table view (state
   the number) and note in the UI roughly how large it is, since a full 73×19 table plus facts is
   near the practical limit for pasting into a chat.
6. **The snapshot section** renders the single row for the selected ticker readably — a
   transposed one-column view is likely better than a very wide single-row table, but decide
   based on its actual shape from Step 1.1 and justify.

Keep it consistent with the existing prototype: no custom CSS, no multi-page structure,
`@st.cache_data` on data loading only and never on rendered output.

## Step 4 — Verify

- **Export round-trip:** the two new Parquet files load back with dtypes preserved (`end` as
  `datetime64[ns]`), and their contents equal the in-memory frames they came from.
- **The pivot is correct, checked against the source frame**: for at least one ticker and one
  frame, verify a handful of individual cells against the long-format rows they came from, and
  confirm the pivot's shape matches the ticker's distinct period/concept counts. Use at least one
  `financial` or `reit` ticker, not only a `standard` one.
- **Nulls survive the pivot** — a concept that is null for the ticker is still a column, still
  null, not dropped and not filled.
- **Downloads carry full precision:** compare a downloaded value against the source frame's
  value, not against what the screen shows.
- **Hidden metrics do not appear** in the data tab for a ticker whose profile hides them —
  assert the precondition against `config.is_hidden` first, then check the rendered table.
- **`app.py` still imports cleanly, imports no pipeline module**, and the whole page body runs to
  completion in Streamlit's bare mode with the new tab included, as the previous task verified
  it. State honestly what was not verifiable without a browser.
- **Nothing regressed:** the chart tabs still render identically, `run_full_refresh()` runs end to
  end, and `figures.py` / `config.py` are unmodified (confirm by hash, not memory).

## Output

One file, `data_tab_report.md`: the snapshot frame's actual shape from Step 1.1, the export
additions with file sizes and the full-universe extrapolation, the pivot and formatting design
decisions, how flags and raw-vs-derived are distinguished (and what you found in `config.py` /
`quality.py` for the flag identification), the limits and defaults chosen, and the Step 4
verification results.

No scratch scripts left behind.