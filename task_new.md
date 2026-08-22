# Task: Per-Ticker JSON Export

**Read first:** `streamlit_inventory.md` §1.1–1.3 (the data contract and the size measurements that
make this task necessary), `registry_export_report.md` (the export conventions just established —
atomicity, schema versioning, validator shape, and the deduplication technique), and
`app_export_layer_report.md` (`export_for_app` and its "meta.json written last" invariant).

## Context

The registry export closed the config gap. This closes the data gap: the six parquet frames total
**309 MB as JSON**, which is not shippable to a browser, but a single ticker's complete payload is
**~650 kB raw / ~120 kB gzipped** — a per-ticker fetch.

This task produces that per-ticker export. Nothing else.

**Explicitly NOT in this task:** no frontend code, no changes to `app.py`, `figures.py` or
`config.py`, no pipeline logic changes, no changes to what the parquet export contains, no fixes to
anything the inventory listed as a bug or a deliberate decision, no registry changes.

---

## Step 1 — Decide the shape, on measurements

`streamlit_inventory.md` §1.3 recommends `{ticker}/facts.json`, `{ticker}/metrics.json`,
`{ticker}/valuation.json`, `{ticker}/growth.json`, `{ticker}/snapshot.json`. Treat that as a
proposal to verify, not a specification to implement.

Decide and state, each on a measured number:

1. **One file per ticker, or one per ticker per frame?** A single file is one fetch; five files
   let a view load only what it needs. Measure both for a real ticker — the inventory's per-frame
   numbers show `facts_full` alone is 406 kB of AAPL's 650 kB, and only two of six tabs need it.
2. **How many files this creates.** 609 tickers × 5 frames is 3,045 files per run. Check what that
   does to the export step's runtime, to the deploy branch's commit, and to git — the nightly
   already commits ~18.8 MB of parquet, and this adds a second population of files that changes
   every night. **Report the added size and the added file count**, because the deploy branch's
   growth is a known standing cost (~560 MB/month, flattened by a monthly orphan reset).
3. **Whether the parquet export stays.** Streamlit reads parquet and will keep running for months
   while the frontend is built. **It stays** — but say explicitly that both are written, and what
   guarantees they describe the same run.
4. **Numeric precision.** JSON serialises floats as text. The data tab's display-versus-export
   distinction (§3.4 of the inventory) means full precision must survive. State how you serialise
   and confirm a round-trip preserves the value, not just its rendering.
5. **Dates.** Parquet carries `datetime64`; JSON does not. Pick a representation (ISO strings are
   the obvious choice) and state it, because every chart's x-axis depends on it and a mis-parsed
   date is the kind of error that renders without complaining.
6. **Nulls.** A null in a metric series is information — it is the difference between a coverage
   gap and a zero. Confirm nulls survive as `null` and are not dropped, coerced, or filled.

## Step 2 — The comparison problem

The Comparison view needs **one concept across N tickers**, which the per-ticker shape cannot serve
without N fetches. The inventory measured a concept-major axis at ~2.5 MB of JSON per concept
across 609 tickers.

Decide and state:

- **Whether to build the concept-major axis now**, or let the frontend do N per-ticker fetches for
  the 2–5 tickers a comparison actually involves. The comparison view caps at a handful of tickers,
  so N is small — measure what N fetches actually costs against a 2.5 MB concept file before
  assuming the second axis is needed.
- If you build it, **which concepts get it.** All 52, or only the valuation multiples the
  comparison view actually offers.

A justified "not needed, and here is the number" is a successful outcome.

## Step 3 — Implement

In `main.py`, alongside `export_for_app` and `export_registry`, following the conventions the
registry export just established:

- **Atomic writes** — write-then-`os.replace`, per file.
- **Written before `meta.json`**, so `meta.json`'s presence still means the whole export is on
  disk. That invariant now covers frames, registry and per-ticker JSON alike.
- **A schema version**, and an entry in `meta.json`'s inventory in the same shape the registry
  block uses (named counts, not a "rows" count, for things that have no rows).
- **Derived from the same in-memory frames** the parquet export writes, in the same call, so the
  two can never describe different runs.
- Extend `validate_export.py` with checks in the same shape as the existing ones. Note what the
  registry export established: **row-count floors are the wrong check for files that do not grow
  with new quarters.** Decide which checks are meaningful here — per-ticker files *do* grow with
  quarters, so floors may apply, but a per-file floor across 3,045 files is not a table anyone
  reads. State what you check and why.

## Step 4 — Verify

1. **Round-trip fidelity, the decisive check.** For a sample spanning profiles and edge cases —
   at minimum one `standard`, one `financial`, one `reit`, one of the four tickers with missing
   per-share data (V, STZ, ERIE, BKR), and one of the short-history candidates (CRWV or FIG) —
   load the JSON back and confirm it reconstructs the parquet slice **exactly**: same rows, same
   columns, same values to full precision, same nulls, same dtypes after parsing. Not "looks
   right" — element-wise equality.
2. **Every universe ticker has a file** for every frame it has data in, and no file exists for a
   ticker that is not in the universe.
3. **Dates round-trip**: parse the exported representation back and confirm it equals the original
   `datetime64` values, including the earliest and latest in the set.
4. **Nulls round-trip** as nulls, verified on a ticker known to have coverage gaps.
5. **Nothing else changed.** `config.py`, `figures.py`, `app.py` untouched (confirm by diff). The
   six parquet frames come back content-identical. Note the caveat the registry report recorded:
   byte-identity across environments is affected by the pyarrow version, so state content equality
   and byte equality separately.
6. **Report the totals**: bytes on disk, bytes gzipped, file count, and the added export runtime.

## Step 5 — Record

Update `bugfixes_opdate_history.md`: the shape decision with its measurement, the schema version,
the comparison-axis verdict, and the added cost to the nightly and the deploy branch.

## Output

One file, `per_ticker_export_report.md`:

1. The Step 1 shape decisions, each with the measurement behind it.
2. The Step 2 comparison verdict.
3. What was implemented and where.
4. The Step 4 verification, especially the round-trip equality result and the edge-case tickers.
5. **The totals**: size, file count, runtime, and what it adds to the nightly commit.
6. Anything deliberately omitted, with reasoning.

No scratch scripts left behind.