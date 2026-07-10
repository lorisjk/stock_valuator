from fetchers.edgar import extract_annual_values, fetch_or_cache, build_ticker_to_cik, get_cik, get_company_info
from parsers.parse_edgar import build_dataframe, extract_merged_annual_values
from config import EDGAR_USER_AGENT, TICKERS, CONCEPT_CANDIDATES, DATA_DIR
from metrics import calculate_yoy_growth, calculate_ratio, calculate_difference, calculate_ratio_from_dfs, calculate_sum_from_dfs
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
    roe = calculate_ratio(final_df, "NetIncomeLoss", "StockholdersEquity", "roe")
    fcf = calculate_difference(final_df, "OperatingCashFlow", "Capex", "fcf", "-")
    ebitda = calculate_difference(final_df, "OperatingIncomeLoss", "DepreciationAndAmortization", "ebitda", "+")
    net_debt = calculate_difference(final_df, "LongTermDebt", "CashAndEquivalents", "net_debt", "-")
    debt_to_equity = calculate_ratio(final_df, "LongTermDebt", "StockholdersEquity", "debt_to_equity")
    payout_ratio = calculate_ratio(final_df, "DividendsPerShare", "EPS", "payout_ratio")
    fcf_margin = calculate_ratio_from_dfs(fcf, final_df[final_df["concept"] == "Revenue"][["ticker", "end", "value"]], "fcf", "value", "fcf_margin" )
    net_debt_to_ebitda = calculate_ratio_from_dfs(net_debt, ebitda, "net_debt", "ebitda", "net_debt_to_ebitda")
    rule_of_40 = calculate_sum_from_dfs(revenue_growth, fcf_margin, "yoy_growth", "fcf_margin", "rule_of_40")
    print(rule_of_40)


if __name__ == "__main__":
    main()