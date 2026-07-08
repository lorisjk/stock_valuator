from fetchers.edgar import extract_annual_values, fetch_or_cache, build_ticker_to_cik, get_cik, get_company_info
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
        net_income = company_info["facts"]["us-gaap"]["NetIncomeLoss"]
        result = extract_annual_values(net_income)
        for r in result:
            print(r)
if __name__ == "__main__":
    main()