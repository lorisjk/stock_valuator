"""Fail in 30 seconds instead of 40 minutes when a data source is unreachable.

The full refresh takes ~40 minutes and does its yfinance work first, its EDGAR
work second. Discovering at minute 40 that Yahoo has been returning empty frames
the whole time is the expensive failure this step exists to prevent.

It calls the project's own fetchers rather than a plain HTTP request, so what it
proves is that *this code path* works from *this IP*, which is the thing in doubt:
Yahoo throttles datacenter ranges and GitHub's runners are exactly that.

Both yfinance entry points fail silently -- `get_price_history` returns a zero-row
frame with the right columns and `get_current_price_and_shares` a dict of Nones --
so the checks below assert on content, never on "did it raise".

Retry policy lives here rather than around the pipeline: a transient Yahoo refusal
is worth waiting out for a minute, and re-running the whole 40-minute pipeline is
not. If the probes still fail after the backoff, the block is not transient and the
run should stop before it starts.

    python .github/scripts/preflight.py
"""
import os
import sys
import time

# This script sits two levels under the repo root, so importing the project's own
# fetchers needs the root on the path -- sys.path[0] is the script's directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Enough tickers to tell "Yahoo is refusing this runner" from "one symbol is having
# a bad day", few enough to stay under a minute. Deliberately not the first entries
# of the universe: a spread of listing ages and index membership.
PROBE_TICKERS = ["AAPL", "JPM", "XOM", "PLD", "KO"]

MIN_PRICE_ROWS = 1000       # ~4 years of trading days; a live symbol has ~5,400 since 2005
ATTEMPTS = 4
BACKOFF_SECONDS = [0, 15, 45, 90]


def probe_yfinance() -> list[str]:
    """Names of the probes that came back empty. Empty list = healthy."""
    from fetchers.yfinance_fetcher import get_price_history, get_current_price_and_shares

    failures = []
    for ticker in PROBE_TICKERS:
        history = get_price_history(ticker)
        if len(history) < MIN_PRICE_ROWS:
            failures.append(f"{ticker} price history: {len(history)} rows "
                            f"(expected >= {MIN_PRICE_ROWS})")
        else:
            print(f"  {ticker} price history: {len(history):,} rows "
                  f"through {history['date'].max().date()}")

        current = get_current_price_and_shares(ticker)
        if current.get("price") is None or current.get("shares_outstanding") is None:
            failures.append(f"{ticker} quote: {current}")
        else:
            print(f"  {ticker} quote: price {current['price']}, "
                  f"shares {current['shares_outstanding']:,}")
    return failures


def probe_edgar() -> list[str]:
    """The same for EDGAR. Cheap, and it proves the User-Agent is accepted."""
    from config import EDGAR_USER_AGENT
    from fetchers.edgar import get_cik, get_company_info
    # Through the pipeline's own resolver, so this probes the mapping the run will
    # actually use -- including its freshness policy and its CIK overrides. Probing a
    # differently-assembled mapping would prove nothing about the run that follows.
    from main import resolve_cik_mapping

    failures = []
    try:
        cik_mapping = resolve_cik_mapping()
        print(f"  ticker->CIK mapping: {len(cik_mapping):,} symbols")
        # Reported, never failed on. An unresolvable ticker is a skip by design (see
        # run_full_refresh), so turning it into a preflight failure here would undo
        # that decision. This line exists so the count is visible in the log *before*
        # the 40-minute run, not so it can stop one.
        from config import get_active_tickers
        universe = get_active_tickers()
        unresolved = [t for t in universe if t not in cik_mapping]
        print(f"  universe resolves: {len(universe) - len(unresolved)} of {len(universe)}"
              + (f"  unresolvable: {', '.join(unresolved)}" if unresolved else ""))
    except Exception as exc:                            # noqa: BLE001
        return [f"company_tickers.json: {type(exc).__name__}: {exc}"]

    ticker = PROBE_TICKERS[0]
    try:
        facts = get_company_info(ticker, get_cik(ticker, cik_mapping), EDGAR_USER_AGENT)
        tags = len(facts.get("facts", {}).get("us-gaap", {}))
        if tags == 0:
            failures.append(f"{ticker} companyfacts: 0 us-gaap tags")
        else:
            print(f"  {ticker} companyfacts: {tags:,} us-gaap tags")
    except Exception as exc:                            # noqa: BLE001
        failures.append(f"{ticker} companyfacts: {type(exc).__name__}: {exc}")
    return failures


def main() -> int:
    for attempt, wait in enumerate(BACKOFF_SECONDS[:ATTEMPTS], start=1):
        if wait:
            print(f"\nretrying in {wait}s ...")
            time.sleep(wait)
        print(f"\n--- preflight attempt {attempt} of {ATTEMPTS} ---")

        print("yfinance:")
        yf_failures = probe_yfinance()
        print("EDGAR:")
        edgar_failures = probe_edgar()

        failures = yf_failures + edgar_failures
        if not failures:
            print("\nPreflight OK. Both sources answer this runner. Starting the run.")
            return 0
        print(f"\n{len(failures)} probe(s) failed:")
        for f in failures:
            print(f"  - {f}")

    print("\nPREFLIGHT FAILED after all attempts. Not starting the ~40 minute run.")
    print("A yfinance failure here is most likely Yahoo refusing this runner's IP "
          "range; that is not transient and a full retry would waste 40 minutes.")
    print("Nothing was published. The previous export is untouched.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
