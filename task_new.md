# Task: Export the Config Registry as JSON

**Read first:** `streamlit_inventory.md` §1.5 (the table of what the app reads from `config.py` at
runtime — that table is this task's specification), §3.1 and §3.2 (the two rules the export must
not break), `metrics_registry_report.md` (the registry's shape and the derived compatibility
layer), and `app_export_layer_report.md` (the existing `export_for_app` and its atomicity
convention).

## Context

The Streamlit app imports `config.py` and calls into it at runtime. A browser cannot. The inventory
identified this as **the single biggest gap in the current export**: a few hundred kB of
information that nothing produces today and that almost every part of a replacement frontend needs.

This task produces it. Nothing else.

**Explicitly NOT in this task:** no per-ticker frame export (that is the next task), no frontend
code, no changes to `app.py`, no changes to `figures.py`, no changes to what `METRICS` contains, no
pipeline logic changes, no fixes to anything the inventory listed as a bug or a deliberate
decision.

---

## Step 1 — Confirm the specification against the code

`streamlit_inventory.md` §1.5 lists what is needed. **Verify each entry against `config.py` as it
stands** rather than trusting the table — the registry has changed several times and the inventory
is a snapshot.

Report anything the table names that no longer exists, and anything the app reads that the table
missed. Grep `app.py` for every `config.` reference and reconcile the two lists.

## Step 2 — Design the export

State the shape and the reasoning. Points to decide:

1. **One file or several.** The metric registry, the per-profile visibility matrix and the
   per-ticker concept candidates are different sizes and change at different rates. Splitting them
   lets a frontend fetch only what a view needs; one file is simpler. Measure the sizes before
   deciding.
2. **Per-ticker visibility is the size question.** `get_plottable_metrics(chart, ticker)` is a
   function of both. Exporting it for 609 tickers × 3 charts is one option; exporting
   `profile_visibility()` plus each ticker's profile, and letting the frontend do the lookup, is
   another and is far smaller — **but only if the two are genuinely equivalent.** §3.1 says
   `is_hidden` is applied twice and involves derived-concept-consumer logic and per-ticker
   overrides, so profile alone may not determine visibility. **Check whether any ticker's
   visibility differs from its profile's**, and let the measurement decide the shape. If they
   differ for even a handful, say which and how you handle it.
3. **The id-namespace split must survive.** §3.2: fundamentals and valuation ids are metric names,
   growth ids are XBRL concept names, and three ids exist in both namespaces. The export must carry
   `id_namespace` and `value_column` explicitly, so a frontend cannot reproduce the percent-
   formatting trap that hit the raw facts table.
4. **Which `Metric` fields go out.** The inventory names id, label, chart, `percent`, `ref_line`,
   `value_column`, `description`, `formula`, `documented`, `harmonic`. Confirm against the
   dataclass and include everything a frontend could need — this file is small and a missing field
   means a re-export later.
5. **A schema version field**, as `meta.json` already carries. The frontend will be developed
   against this contract and needs to detect a mismatch rather than fail obscurely.

## Step 3 — Implement

Add the export to `main.py` alongside `export_for_app`, written by the same run so the registry can
never disagree with the frames it describes.

Requirements:

- **The same atomicity convention** as the existing export: write-then-`os.replace`, and whatever
  file plays the role `meta.json` plays there written last.
- **`config.py` is the source, not a second copy.** Derive everything from `METRICS`,
  `is_hidden`, `get_plottable_metrics` and friends by calling them. Do not restate any value as a
  literal — the registry task made `METRICS` the single source of truth and this export must not
  become a second one.
- Extend the existing validation script to cover the new file, in the same shape as the current
  checks.
- Extend `meta.json`'s row counts if that is where the export's own inventory lives.

## Step 4 — Verify

1. **Round-trip equivalence, the decisive check.** Load the exported JSON back and confirm that for
   **every** (chart, ticker) pair in the universe, the metric list it yields is identical — same
   ids, same order — to what `config.get_plottable_metrics(chart, ticker)` returns. Not a sample:
   all 609 tickers × 3 charts. Any disagreement means the export is not usable as a substitute for
   calling into config.
2. **`profile_visibility()` round-trips** identically, all profiles × all metrics.
3. **`get_concept_candidates(ticker)`** round-trips for every ticker.
4. **The three dual-namespace ids** (`Revenue`, `NetIncomeLoss`, `SharesOutstanding`) appear with
   the correct `id_namespace` and `value_column` for each chart they belong to, and a consumer
   reading the export cannot confuse the growth entry with a facts concept.
5. **Field completeness**: every `Metric` field that exists in the dataclass is either exported or
   listed in the report as deliberately omitted with a reason.
6. **Nothing else changed.** `config.py`, `figures.py`, `app.py` untouched (confirm by diff); a full
   run still produces byte-identical frames, with the price-capture constraint from
   `product_cleanup_report.md` in mind — one price capture for any before/after comparison.
7. **Report the file size(s)**, and what they imply for a frontend that fetches them on load.

## Step 5 — Record

Update `bugfixes_opdate_history.md` per convention: what is exported, the shape decision from
Step 2.2 with its measurement, and the schema version.

## Output

One file, `registry_export_report.md`:

1. The Step 1 reconciliation: what the inventory named, what actually exists, what it missed.
2. The export shape with reasoning, including the per-ticker-versus-per-profile measurement.
3. What was implemented and where.
4. The Step 4 verification, especially the all-tickers round-trip result.
5. The file sizes.
6. Anything deliberately omitted, with reasoning.

No scratch scripts left behind.