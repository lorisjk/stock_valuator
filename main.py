from fetchers.edgar import extract_annual_values, fetch_or_cache, build_ticker_to_cik, get_cik, get_company_info
from parsers.parse_edgar import build_dataframe, extract_merged_annual_values
from config import EDGAR_USER_AGENT, TICKERS, CONCEPT_CANDIDATES, DATA_DIR
from metrics import calculate_yoy_growth, calculate_ratio
import os
import pandas as pd


def main():
    mapping = fetch_or_cache(
        url="https://www.sec.gov/files/company_tickers.json",
        cache_path="cache/ticker_mapping.json",
        headers={"User-Agent": EDGAR_USER_AGENT}
    )
    cik_mapping = build_ticker_to_cik(mapping)

    all_dfs = []
    for ticker in TICKERS:
        cik = get_cik(ticker, cik_mapping)
        company_info = get_company_info(ticker, cik, EDGAR_USER_AGENT)
        
        df = build_dataframe(ticker, company_info, CONCEPT_CANDIDATES)
        all_dfs.append(df)

    final_df = pd.concat(all_dfs, ignore_index=True)
    duplicates = final_df[final_df.duplicated(subset=["ticker", "concept", "end"], keep=False)]
    if not duplicates.empty:
        print("Warnung: Duplikate gefunden!")
        print(duplicates)
    #print(final_df.groupby(["ticker", "concept"]).size())

    os.makedirs(DATA_DIR, exist_ok=True)
    output_path = os.path.join(DATA_DIR, "historical_facts.csv")
    final_df.to_csv(output_path, index=False)

    revenue_growth = calculate_yoy_growth(final_df, "Revenue")
    income_growth = calculate_yoy_growth(final_df, "NetIncomeLoss")
    operating_margin = calculate_ratio(final_df, "OperatingIncomeLoss", "Revenue", "operating_margin")
    print(operating_margin)
    
if __name__ == "__main__":
    main()