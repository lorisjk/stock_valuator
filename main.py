from fetchers.edgar import fetch_or_cache
from config import EDGAR_USER_AGENT

def main():
    mapping = fetch_or_cache(
        url="https://www.sec.gov/files/company_tickers.json",
        cache_path="cache/ticker_mapping.json",
        headers={"User-Agent": EDGAR_USER_AGENT}
    )
    print(mapping)

if __name__ == "__main__":
    main()