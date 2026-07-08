from fetchers.edgar import fetch_or_cache, build_ticker_to_cik, get_cik
from config import EDGAR_USER_AGENT, TICKERS


def main():
    mapping = fetch_or_cache(
        url="https://www.sec.gov/files/company_tickers.json",
        cache_path="cache/ticker_mapping.json",
        headers={"User-Agent": EDGAR_USER_AGENT}
    )
    cik_mapping = build_ticker_to_cik(mapping)

    for ticker in TICKERS:
        cik = get_cik(ticker, cik_mapping)
        print(f"{ticker}: {cik}")

if __name__ == "__main__":
    main()