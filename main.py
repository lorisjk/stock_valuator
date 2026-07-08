from fetchers.edgar import fetch_or_cache, build_ticker_to_cik, get_cik, get_company_info
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
        company_info = get_company_info(ticker, cik, EDGAR_USER_AGENT)
        import json
        print(json.dumps(company_info["facts"]["us-gaap"]["NetIncomeLoss"], indent=2)[:2000])
if __name__ == "__main__":
    main()