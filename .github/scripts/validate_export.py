"""Gate between a finished pipeline run and publishing its export.

The pipeline exits non-zero when something raises. This script exists for the
other failure: a run that *completes* and produces data that is quietly wrong.

The reason that case is real, and not hypothetical, is the yfinance layer. Both
of its entry points return a well-formed nothing when Yahoo refuses a symbol --
`get_price_history` a zero-row frame with the right columns, and
`get_current_price_and_shares` a dict of Nones -- so a total price outage raises
no exception anywhere. EDGAR would still supply every fundamental, so
`meta.json`'s `tickers_with_data` would still read 501 of 501. Counting tickers
therefore cannot detect it; counting *price-derived values* can, which is what
PRICE_* below do.

The per-ticker JSON under `tickers/` fails in a third way: 1,218 files of which
any one could be missing, truncated or misaligned while the population total
looks healthy. All of them are opened and checked against the parquet slice they
were cut from -- 1.9 s for 1,218 files, against a ~40 min run. A sampled version
of this check was written first and rejected: it passed eight deliberate
corruptions because none of them landed on a sampled ticker.

The registry files (`registry.json`, `concept_candidates.json`) fail differently
again: they describe `config.py`, not the filings, so their sizes do not drift
and a floor tells you nothing. What matters is that they still answer the
question the app asks of them -- every universe ticker resolvable to a profile
whose visibility row covers every metric, and every metric carrying the fields a
frontend formats on. Those are checked structurally below.

Thresholds are floors derived from a measured full run (see BASELINE), not
guesses. Row counts only grow as new quarters are filed, so a floor at 90% of a
measured run is slack for drift and still tight enough to catch a systemic
extraction failure. Ticker counts are a fraction of the requested universe, so
index changes and a few delistings pass while an outage does not.

Exit 0 = safe to publish. Exit 1 = leave the previous export in place.

    python .github/scripts/validate_export.py [--dir data/app]
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta

import pandas as pd


# Measured on the 2026-08-12 full run: 501 requested, 501 with data, 39.5 min
# wall clock, write_charts=False. Kept here as the provenance of every number
# below -- a threshold whose origin is not written down cannot be re-judged.
BASELINE = {
    "tickers_requested": 501,
    "tickers_with_data": 501,
    "metrics_long.parquet": 506_774,
    "valuation_history.parquet": 305_253,
    "facts_growth.parquet": 211_956,
    "facts_full.parquet": 1_016_350,
    "current_snapshot.parquet": 21_241,
    "universe.parquet": 501,
    "valuation_history_nonnull": 210_348,
    "snapshot_price_nonnull": 501,
    "snapshot_market_cap_nonnull": 501,
}

ROW_FLOOR = 0.90          # of the measured baseline
TICKER_FLOOR = 0.95       # of the universe requested by this run
PRICE_FLOOR = 0.95        # of the tickers this run produced data for
MAX_EXPORT_AGE_HOURS = 6  # the run that wrote it must be the one that just ran
EXPECTED_SCHEMA = 4
EXPECTED_REGISTRY_SCHEMA = 1
EXPECTED_TICKER_SCHEMA = 1

FRAMES = ["metrics_long.parquet", "valuation_history.parquet", "facts_growth.parquet",
          "facts_full.parquet", "current_snapshot.parquet", "universe.parquet"]

# The registry files describe config.py rather than the filings, so a row floor
# is the wrong instrument: these counts do not grow with time and a drop is not
# drift, it is a bug. They are checked for exact structural soundness instead --
# every universe ticker resolvable to a profile, every profile's visibility row
# complete, every ticker pointing at a candidate variant that exists.
REGISTRY_FILES = ["registry.json", "concept_candidates.json"]

# The per-ticker JSON. Unlike the registry, these DO grow with new quarters, so a
# floor is the right instrument -- but one floor on the population, not 1,218 of
# them, because a per-file table is not something anyone reads. The floor that
# matters per file is a different question: a file can be present and still be
# empty or truncated, which the population total would not notice, so the
# smallest file is checked against a hard minimum rather than a fraction.
TICKER_SUBDIR = "tickers"
TICKER_FRAMES = ["metrics_long", "valuation_history", "facts_growth",
                 "current_snapshot", "facts_full"]
TICKER_BYTES_BASELINE = 140_501_901   # measured 2026-08-22, 609 tickers
MIN_TICKER_FILE_BYTES = 4_096         # half the smallest measured file (8,249 B)


class Checks:
    def __init__(self):
        self.rows = []

    def add(self, name, ok, got, want):
        self.rows.append((name, bool(ok), got, want))

    def report(self):
        width = max(len(r[0]) for r in self.rows)
        print(f"\n{'check'.ljust(width)}  {'':4}  {'measured':>14}  requirement")
        print("-" * (width + 46))
        for name, ok, got, want in self.rows:
            print(f"{name.ljust(width)}  {'PASS' if ok else 'FAIL':4}  {got:>14}  {want}")
        failed = [r[0] for r in self.rows if not r[1]]
        print()
        if failed:
            print(f"REJECTED: {len(failed)} of {len(self.rows)} checks failed "
                  f"({', '.join(failed)}).")
            print("The previous export stays published. Nothing was committed.")
            return 1
        print(f"ACCEPTED: all {len(self.rows)} checks passed. Safe to publish.")
        return 0


def main(out_dir: str, max_age_hours: float = MAX_EXPORT_AGE_HOURS) -> int:
    c = Checks()

    meta_path = os.path.join(out_dir, "meta.json")
    if not os.path.exists(meta_path):
        # meta.json is written last, after every frame is in place, so its absence
        # means the run did not reach the end of export_for_app.
        print(f"FATAL: {meta_path} does not exist -- the run never completed its export.")
        return 1
    with open(meta_path, encoding="utf-8") as fh:
        meta = json.load(fh)

    c.add("meta.schema", meta.get("schema") == EXPECTED_SCHEMA,
          str(meta.get("schema")), f"== {EXPECTED_SCHEMA}")

    # An export older than the run that just finished means the pipeline wrote
    # nothing and we are about to republish yesterday's file as today's.
    try:
        age = datetime.now() - datetime.fromisoformat(meta["exported_at"])
        c.add("export age", age < timedelta(hours=max_age_hours),
              f"{age.total_seconds() / 3600:.1f} h", f"< {max_age_hours} h")
    except (KeyError, ValueError) as exc:
        c.add("export age", False, f"unparseable ({exc})", "ISO timestamp")

    frames = {}
    for name in FRAMES:
        path = os.path.join(out_dir, name)
        try:
            frames[name] = pd.read_parquet(path)
            readable = True
            got = f"{len(frames[name]):,} rows"
        except Exception as exc:                       # noqa: BLE001 -- any read failure disqualifies
            readable = False
            got = f"{type(exc).__name__}"
        c.add(f"{name} readable", readable, got, "parses as parquet")

    if len(frames) != len(FRAMES):
        return c.report()

    for name in FRAMES:
        floor = int(BASELINE[name] * ROW_FLOOR)
        c.add(f"{name} rows", len(frames[name]) >= floor,
              f"{len(frames[name]):,}", f">= {floor:,} ({ROW_FLOOR:.0%} of {BASELINE[name]:,})")

    requested = meta.get("tickers_requested", 0)
    produced = meta.get("tickers_with_data", 0)
    floor = int(requested * TICKER_FLOOR)
    c.add("tickers_with_data", produced >= floor and requested > 0,
          f"{produced} of {requested}", f">= {floor} ({TICKER_FLOOR:.0%} of requested)")

    # --- the yfinance detectors -------------------------------------------------
    # These are the only checks that would notice a total price outage. Everything
    # above stays green when Yahoo returns nothing, because it is all EDGAR-derived.
    snapshot = frames["current_snapshot.parquet"]
    for concept in ("price", "market_cap", "shares_outstanding"):
        sub = snapshot[snapshot["concept"] == concept]
        nonnull = int(sub["value"].notna().sum())
        floor = int(produced * PRICE_FLOOR)
        c.add(f"snapshot `{concept}` non-null", nonnull >= floor,
              f"{nonnull}", f">= {floor} ({PRICE_FLOOR:.0%} of {produced} produced)")

    # --- the registry files -----------------------------------------------------
    # The app cannot render a picker, an axis label or a reference line without
    # these, so an export missing them is not publishable even though every
    # parquet frame above is intact.
    registry = {}
    for name in REGISTRY_FILES:
        path = os.path.join(out_dir, name)
        try:
            with open(path, encoding="utf-8") as fh:
                registry[name] = json.load(fh)
            got, ok = "parsed", True
        except Exception as exc:                       # noqa: BLE001 -- any read failure disqualifies
            got, ok = type(exc).__name__, False
        c.add(f"{name} readable", ok, got, "parses as JSON")

    if len(registry) == len(REGISTRY_FILES):
        reg = registry["registry.json"]
        cand = registry["concept_candidates.json"]
        c.add("registry.schema", reg.get("schema") == EXPECTED_REGISTRY_SCHEMA,
              str(reg.get("schema")), f"== {EXPECTED_REGISTRY_SCHEMA}")

        metrics = reg.get("metrics", [])
        c.add("registry metrics", len(metrics) > 0, f"{len(metrics)}", "> 0")

        # Every field the frontend formats on. A metric missing value_column is
        # the percent-formatting trap: the growth entry `Revenue` would then be
        # indistinguishable from the facts column of the same name.
        required = {"id", "chart", "label", "percent", "ref_line",
                    "id_namespace", "value_column"}
        incomplete = [m.get("id", "?") for m in metrics if not required <= set(m)]
        c.add("registry metric fields", not incomplete,
              f"{len(incomplete)} incomplete", f"all of {sorted(required)}")

        charts = reg.get("charts", {})
        orphan_chart = [m["id"] for m in metrics if m.get("chart") not in charts]
        c.add("every metric's chart is declared", not orphan_chart,
              f"{len(orphan_chart)} orphans", "chart in registry.charts")

        # The substitution the export exists to make: profile_visibility plus
        # ticker->profile has to answer get_plottable_metrics for every ticker.
        # It cannot if a ticker resolves to a profile with no visibility row, or
        # a row that does not cover every metric.
        vis = reg.get("profile_visibility", {})
        ids = {m["id"] for m in metrics}
        ticker_profile = reg.get("ticker_profile", {})
        unresolvable = [t for t, p in ticker_profile.items() if p not in vis]
        c.add("every ticker resolves to a profile", not unresolvable,
              f"{len(unresolvable)} unresolvable", "profile in profile_visibility")
        short = [p for p, row in vis.items() if set(row) != ids]
        c.add("every profile covers every metric", not short,
              f"{len(short)} incomplete of {len(vis)}", f"{len(ids)} metrics each")

        universe_tickers = set(frames["universe.parquet"]["ticker"])
        c.add("registry covers the universe",
              universe_tickers <= set(ticker_profile),
              f"{len(universe_tickers - set(ticker_profile))} missing", "0 missing")

        variants = cand.get("variants", [])
        index = cand.get("ticker_variant", {})
        dangling = [t for t, i in index.items()
                    if not isinstance(i, int) or not 0 <= i < len(variants)]
        c.add("candidate variants resolve", not dangling,
              f"{len(dangling)} dangling of {len(index)}", f"index into {len(variants)} variants")
        c.add("candidates cover the universe",
              universe_tickers <= set(index),
              f"{len(universe_tickers - set(index))} missing", "0 missing")

    # --- the per-ticker JSON ----------------------------------------------------
    ticker_dir = os.path.join(out_dir, TICKER_SUBDIR)
    universe_tickers = sorted(frames["universe.parquet"]["ticker"])
    if not os.path.isdir(ticker_dir):
        c.add(f"{TICKER_SUBDIR}/ present", False, "missing", "directory exists")
    else:
        on_disk = set(os.listdir(ticker_dir))
        expected = {f"{t}{suffix}" for t in universe_tickers
                    for suffix in (".json", ".facts.json")}
        c.add("per-ticker files", on_disk == expected,
              f"{len(on_disk):,} files", f"exactly {len(expected):,} (2 x universe)")
        missing = sorted(expected - on_disk)[:3]
        c.add("no ticker missing a file", not (expected - on_disk),
              f"{len(expected - on_disk)} missing {missing}", "0 missing")
        c.add("no file for a ticker outside the universe", not (on_disk - expected),
              f"{len(on_disk - expected)} strays", "0 strays")

        sizes = {f: os.path.getsize(os.path.join(ticker_dir, f)) for f in on_disk & expected}
        total = sum(sizes.values())
        floor = int(TICKER_BYTES_BASELINE * ROW_FLOOR)
        c.add("per-ticker bytes", total >= floor, f"{total:,}",
              f">= {floor:,} ({ROW_FLOOR:.0%} of {TICKER_BYTES_BASELINE:,})")
        # A present-but-empty file is the failure a population total hides: 1,218
        # files each 200 bytes would still be 1,218 files.
        runts = sorted(f for f, n in sizes.items() if n < MIN_TICKER_FILE_BYTES)
        c.add("no truncated per-ticker file", not runts,
              f"{len(runts)} under {MIN_TICKER_FILE_BYTES:,} B {runts[:3]}",
              f"all >= {MIN_TICKER_FILE_BYTES:,} B")

        # Every file, not a sample. Sampling was tried and rejected: it passed
        # eight deliberate corruptions because none of them happened to land on a
        # sampled ticker. Parsing all 1,218 files costs 1.9 s against a ~40 min
        # pipeline run, which is not a trade worth making.
        expected_rows = {name: frames[f"{name}.parquet"]["ticker"].value_counts().to_dict()
                         for name in TICKER_FRAMES}
        expected_cols = {name: [c for c in frames[f"{name}.parquet"].columns if c != "ticker"]
                         for name in TICKER_FRAMES}
        problems, rows_seen = [], 0
        for ticker in universe_tickers:
            try:
                payload = {}
                for suffix in (".json", ".facts.json"):
                    with open(os.path.join(ticker_dir, ticker + suffix), encoding="utf-8") as fh:
                        doc = json.load(fh)
                    if doc.get("schema") != EXPECTED_TICKER_SCHEMA:
                        problems.append(f"{ticker}{suffix}: schema {doc.get('schema')}")
                    if doc.get("ticker") != ticker:
                        problems.append(f"{ticker}{suffix}: ticker {doc.get('ticker')!r}")
                    payload.update(doc.get("frames", {}))
                for name in TICKER_FRAMES:
                    block = payload.get(name)
                    if not block or not block.get("columns"):
                        problems.append(f"{ticker}: no {name}")
                        continue
                    # Column-major: every column must be the same length, and that
                    # length must be the parquet slice's row count. A misaligned
                    # export shows up here and nowhere else.
                    want = expected_rows[name].get(ticker, 0)
                    lengths = {len(col) for col in block["data"]}
                    if lengths != {want}:
                        problems.append(f"{ticker}/{name}: rows {sorted(lengths)} vs {want}")
                    else:
                        rows_seen += want
                    if block["columns"] != expected_cols[name]:
                        problems.append(f"{ticker}/{name}: columns {block['columns']}")
            except Exception as exc:                   # noqa: BLE001 -- any failure disqualifies
                problems.append(f"{ticker}: {type(exc).__name__}")
        c.add(f"every per-ticker file ({len(universe_tickers) * 2:,})", not problems,
              f"{len(problems)} problems {problems[:2]}",
              "parses, right schema and ticker, all 5 frames, rows and columns match parquet")

        # The rows the per-ticker export does not carry must all belong to tickers
        # the universe does not list -- otherwise a ticker is silently short.
        universe_set = set(universe_tickers)
        orphan = sum(int((~frames[f"{name}.parquet"]["ticker"].isin(universe_set)).sum())
                     for name in TICKER_FRAMES)
        parquet_rows = sum(len(frames[f"{name}.parquet"]) for name in TICKER_FRAMES)
        c.add("per-ticker rows account for the parquet",
              not problems and rows_seen + orphan == parquet_rows,
              f"{rows_seen:,} + {orphan} outside the universe", f"== {parquet_rows:,}")

    val = frames["valuation_history.parquet"]
    nonnull = int(val["value"].notna().sum())
    floor = int(BASELINE["valuation_history_nonnull"] * ROW_FLOOR)
    c.add("valuation_history non-null", nonnull >= floor,
          f"{nonnull:,}", f">= {floor:,} ({ROW_FLOOR:.0%} of {BASELINE['valuation_history_nonnull']:,})")

    # Every valuation multiple divides by a price or a market cap. A ticker with
    # no valuation rows at all is a ticker whose price series never arrived.
    universe = frames["universe.parquet"]
    empty = int((universe["n_valuation"] == 0).sum())
    c.add("tickers with no valuation", empty <= int(produced * (1 - PRICE_FLOOR)),
          f"{empty}", f"<= {int(produced * (1 - PRICE_FLOOR))}")

    return c.report()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default=os.path.join("data", "app"),
                    help="the export directory to validate (default: data/app)")
    ap.add_argument("--max-age-hours", type=float, default=MAX_EXPORT_AGE_HOURS,
                    help="raise only to re-check an archived export by hand; the "
                         "workflow always uses the default, because in CI the run "
                         "that wrote the export is the one that just finished")
    args = ap.parse_args()
    sys.exit(main(args.dir, args.max_age_hours))
