import sys

from fetchers.edgar import get_cik, get_company_info
from config import EDGAR_USER_AGENT
from main import resolve_cik_mapping
from quality import search_tags


def main():
    if len(sys.argv) < 3:
        print("Usage: python explore_tags.py <TICKER> <keyword> [keyword ...]")
        print("Example: python explore_tags.py AMZN depreciation amortization")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    keywords = sys.argv[2:]

    # Via main rather than assembling the mapping here: a diagnostic that resolves
    # tickers differently from the pipeline cannot reproduce the pipeline's bugs, which
    # is exactly what a 37-day-old cache did on 2026-08-14 -- the CI crash on AEP was
    # not reproducible locally because the two sides resolved from different files.
    cik_mapping = resolve_cik_mapping(report_overrides=False)
    cik = get_cik(ticker, cik_mapping)
    company_info = get_company_info(ticker, cik, EDGAR_USER_AGENT)

    hits = search_tags(company_info, keywords)

    print()
    print("=" * 72)
    print(f"{ticker}  |  Suche nach: {', '.join(keywords)}")
    print("=" * 72)

    if not hits:
        print("  Keine Treffer.")
    else:
        for tag in hits:
            print(f"  {tag}")
        print()
        print(f"  {len(hits)} Treffer")

    print("=" * 72)
    print()


if __name__ == "__main__":
    main()