import sys

from fetchers.edgar import fetch_or_cache, build_ticker_to_cik, get_cik, get_company_info
from config import EDGAR_USER_AGENT
from quality import search_tags


def main():
    if len(sys.argv) < 3:
        print("Usage: python explore_tags.py <TICKER> <keyword> [keyword ...]")
        print("Example: python explore_tags.py AMZN depreciation amortization")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    keywords = sys.argv[2:]

    mapping = fetch_or_cache(
        url="https://www.sec.gov/files/company_tickers.json",
        cache_path="cache/ticker_mapping.json",
        headers={"User-Agent": EDGAR_USER_AGENT},
    )
    cik_mapping = build_ticker_to_cik(mapping)
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