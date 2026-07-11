from fetchers.edgar import extract_annual_values, fetch_or_cache, build_ticker_to_cik, get_cik, get_company_info
from fetchers.yfinance_fetcher import get_current_price_and_shares, get_price_history
from parsers.parse_edgar import build_dataframe
from config import EDGAR_USER_AGENT, TICKERS, CONCEPT_CANDIDATES, DATA_DIR, PERIOD
from metrics import (
    calculate_growth,
    calculate_ratio,
    calculate_difference,
    calculate_ratio_from_dfs,
    calculate_sum_from_dfs,
    get_latest_value,
    calculate_historical_pe,
    calculate_rolling_average,
    calculate_ttm,
    get_latest_row,
)
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
        df = build_dataframe(ticker, company_info, CONCEPT_CANDIDATES, period=PERIOD)
        all_dfs.append(df)

    final_df = pd.concat(all_dfs, ignore_index=True)

    duplicates = final_df[final_df.duplicated(subset=["ticker", "concept", "end"], keep=False)]
    if not duplicates.empty:
        print("Warnung: Duplikate gefunden!")
        print(duplicates)

    os.makedirs(DATA_DIR, exist_ok=True)
    output_path = os.path.join(DATA_DIR, f"{PERIOD}_facts.csv")
    final_df.to_csv(output_path, index=False)

    # periods=4, weil bei Quartalsdaten "ein Jahr zurueck" vier Zeilen zurueck
    # bedeutet (saisonbereinigter Vergleich), nicht periods=1 (das waere QoQ).
    revenue_growth = calculate_growth(final_df, "Revenue", 4, "yoy_growth")
    income_growth = calculate_growth(final_df, "NetIncomeLoss", 4, "yoy_growth")

    # Verhaeltniskennzahlen: unveraendert, weil sie Werte INNERHALB derselben
    # Periode vergleichen (kein Zeit-Shift noetig) - funktionieren identisch
    # auf Quartals- wie auf Jahresdaten.
    operating_margin = calculate_ratio(final_df, "OperatingIncomeLoss", "Revenue", "operating_margin")
    roe = calculate_ratio(final_df, "NetIncomeLoss", "StockholdersEquity", "roe")
    debt_to_equity = calculate_ratio(final_df, "LongTermDebt", "StockholdersEquity", "debt_to_equity")
    payout_ratio = calculate_ratio(final_df, "DividendsPerShare", "EPS", "payout_ratio")

    fcf = calculate_difference(final_df, "OperatingCashFlow", "Capex", "fcf", "-")
    ebitda = calculate_difference(final_df, "OperatingIncomeLoss", "DepreciationAndAmortization", "ebitda", "+")
    net_debt = calculate_difference(final_df, "LongTermDebt", "CashAndEquivalents", "net_debt", "-")

    fcf_margin = calculate_ratio_from_dfs(
        fcf, final_df[final_df["concept"] == "Revenue"][["ticker", "end", "value"]],
        "fcf", "value", "fcf_margin"
    )
    net_debt_to_ebitda = calculate_ratio_from_dfs(net_debt, ebitda, "net_debt", "ebitda", "net_debt_to_ebitda")
    rule_of_40 = calculate_sum_from_dfs(revenue_growth, fcf_margin, "yoy_growth", "fcf_margin", "rule_of_40")

    # Aktienanzahl-Historie, wie gehabt aus NetIncomeLoss/EPS abgeleitet -
    # funktioniert unveraendert auf Quartalsbasis.
    shares_outstanding_historical = calculate_ratio(final_df, "NetIncomeLoss", "EPS", "shares_outstanding")
    shares_outstanding_long = shares_outstanding_historical[["ticker", "end", "shares_outstanding"]].rename(
        columns={"shares_outstanding": "value"}
    )
    shares_outstanding_long["concept"] = "SharesOutstanding"
    final_df = pd.concat([final_df, shares_outstanding_long], ignore_index=True)

    # Historische Kurse holen und an final_df mergen (merge_asof) - unveraendert,
    # nur dass final_df jetzt sehr viel mehr (quartalsweise) Zeitpunkte hat.
    price_histories = []
    for ticker in TICKERS:
        price_histories.append(get_price_history(ticker))
    price_history_df = pd.concat(price_histories, ignore_index=True)
    price_history_df["date"] = price_history_df["date"].dt.tz_localize(None).astype("datetime64[ns]")

    final_df["end"] = pd.to_datetime(final_df["end"]).astype("datetime64[ns]")

    final_df_with_price = pd.merge_asof(
        final_df.sort_values("end"),
        price_history_df.sort_values("date"),
        left_on="end",
        right_on="date",
        by="ticker",
        direction="backward",
    )

    # Historisches P/E: WICHTIG - hier darf NICHT das rohe Quartals-EPS als
    # Nenner dienen (das ist nur ~1/4 des Jahresgewinns, wuerde das P/E um
    # den Faktor ~4 verzerren). Stattdessen TTM-EPS je Quartal berechnen und
    # DAS mit dem historischen Kurs kombinieren.
    eps_ttm_series = calculate_ttm(final_df, "EPS", "eps_ttm")
    eps_ttm_series["end"] = pd.to_datetime(eps_ttm_series["end"]).astype("datetime64[ns]")

    eps_ttm_with_price = pd.merge_asof(
        eps_ttm_series.sort_values("end"),
        price_history_df.sort_values("date"),
        left_on="end",
        right_on="date",
        by="ticker",
        direction="backward",
    )
    eps_ttm_with_price["pe_ratio"] = eps_ttm_with_price["close"] / eps_ttm_with_price["eps_ttm"]

    # Gleitender Durchschnitt ueber die letzten 20 Quartale (= 5 Jahre)
    rolling_pe = calculate_rolling_average(eps_ttm_with_price, "pe_ratio", 20, "avg_pe_5y")

    # --- Aktueller TTM-Snapshot ---

    eps_ttm = calculate_ttm(final_df, "EPS", "eps_ttm")
    latest_eps_ttm = get_latest_row(eps_ttm)

    fcf_ttm = calculate_ttm(fcf.rename(columns={"fcf": "value"}).assign(concept="fcf"), "fcf", "fcf_ttm")
    latest_fcf_ttm = get_latest_row(fcf_ttm)

    latest_equity = get_latest_value(final_df, "StockholdersEquity").rename(columns={"value": "equity"})
    latest_debt = get_latest_value(final_df, "LongTermDebt").rename(columns={"value": "debt"})
    latest_cash = get_latest_value(final_df, "CashAndEquivalents").rename(columns={"value": "cash"})

    price_rows = []
    for ticker in TICKERS:
        price_data = get_current_price_and_shares(ticker)
        price_data["ticker"] = ticker
        price_rows.append(price_data)
    price_df = pd.DataFrame(price_rows)
    price_df["market_cap"] = price_df["price"] * price_df["shares_outstanding"]

    snapshot = price_df.copy()
    snapshot = pd.merge(snapshot, latest_eps_ttm[["ticker", "eps_ttm"]], on="ticker")
    snapshot["pe_ttm"] = snapshot["price"] / snapshot["eps_ttm"]

    snapshot = pd.merge(snapshot, latest_equity[["ticker", "equity"]], on="ticker")
    snapshot["pb_ratio"] = snapshot["market_cap"] / snapshot["equity"]

    snapshot = pd.merge(snapshot, latest_fcf_ttm[["ticker", "fcf_ttm"]], on="ticker")
    snapshot["pfcf_ttm"] = snapshot["market_cap"] / snapshot["fcf_ttm"]

    snapshot = pd.merge(snapshot, latest_debt[["ticker", "debt"]], on="ticker")
    snapshot = pd.merge(snapshot, latest_cash[["ticker", "cash"]], on="ticker")
    snapshot["net_debt"] = snapshot["debt"] - snapshot["cash"]
    snapshot["ev"] = snapshot["market_cap"] + snapshot["net_debt"]

    # Aktuellster 5-Jahres-Oe-P/E pro Ticker, aus der rollierenden Reihe
    current_avg_pe_5y = get_latest_row(rolling_pe)
    snapshot = pd.merge(snapshot, current_avg_pe_5y[["ticker", "avg_pe_5y"]], on="ticker")

    print(snapshot)

    snapshot_path = os.path.join(DATA_DIR, "current_snapshot.csv")
    snapshot.to_csv(snapshot_path, index=False)


if __name__ == "__main__":
    main()