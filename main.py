from fetchers.edgar import fetch_or_cache, build_ticker_to_cik, get_cik, get_company_info
from fetchers.yfinance_fetcher import get_current_price_and_shares, get_price_history
from parsers.parse_edgar import build_dataframe
from config import (
    EDGAR_USER_AGENT,
    TICKERS,
    CONCEPT_CANDIDATES,
    TTM_CONCEPTS,
    PERIOD,
    DATA_DIR,
    FIGURE_DIR,
    SEARCH_HINTS
)
from metrics import (
    add_ttm_concepts,
    add_as_concept,
    calculate_growth,
    calculate_ratio,
    calculate_difference,
    calculate_ratio_from_dfs,
    calculate_sum_from_dfs,
    calculate_rolling_average,
    get_latest_value,
    get_latest_row,
    to_long_format,
    normalize_split_adjusted
)
from figures import plot_fundamentals, plot_valuation
from quality import print_data_quality

import os
import pandas as pd

from datetime import date


def load_facts() -> pd.DataFrame:
    mapping = fetch_or_cache(
        url="https://www.sec.gov/files/company_tickers.json",
        cache_path="cache/ticker_mapping.json",
        headers={"User-Agent": EDGAR_USER_AGENT},
    )
    cik_mapping = build_ticker_to_cik(mapping)

    all_dfs = []
    for ticker in TICKERS:
        cik = get_cik(ticker, cik_mapping)
        company_info = get_company_info(ticker, cik, EDGAR_USER_AGENT)
        all_dfs.append(build_dataframe(ticker, company_info, CONCEPT_CANDIDATES, period=PERIOD))
        
    df = pd.concat(all_dfs, ignore_index=True)
    df["end"] = pd.to_datetime(df["end"]).astype("datetime64[ns]")
    return df


def load_price_history() -> pd.DataFrame:
    histories = [get_price_history(ticker) for ticker in TICKERS]
    df = pd.concat(histories, ignore_index=True)
    df["date"] = df["date"].dt.tz_localize(None).astype("datetime64[ns]")
    return df


def load_current_prices() -> pd.DataFrame:
    rows = []
    for ticker in TICKERS:
        data = get_current_price_and_shares(ticker)
        data["ticker"] = ticker
        rows.append(data)

    df = pd.DataFrame(rows)
    df["market_cap"] = df["price"] * df["shares_outstanding"]
    return df


def add_derived_concepts(facts: pd.DataFrame) -> pd.DataFrame:
    facts = add_ttm_concepts(facts, TTM_CONCEPTS)

    eps_ttm = calculate_ratio(facts, "NetIncomeLoss_TTM", "SharesOutstanding", "value")
    eps_ttm["concept"] = "EPS_TTM_CALC"
    facts = pd.concat([facts, eps_ttm[["ticker", "end", "concept", "value"]]], ignore_index=True)

    return facts


def calculate_all_metrics(facts: pd.DataFrame) -> dict:
    m = {}

    m["revenue_growth"] = calculate_growth(facts, "Revenue_TTM", 4, "yoy_growth")
    m["income_growth"] = calculate_growth(facts, "NetIncomeLoss_TTM", 4, "yoy_growth")

    m["operating_margin"] = calculate_ratio(
        facts, "OperatingIncomeLoss_TTM", "Revenue_TTM", "operating_margin"
    )
    m["roe"] = calculate_ratio(facts, "NetIncomeLoss_TTM", "StockholdersEquity", "roe")
    m["payout_ratio"] = calculate_ratio(
        facts, "DividendsPerShare_TTM", "EPS_TTM_CALC", "payout_ratio",
        require_positive_denominator=True,
    )

    m["debt_to_equity"] = calculate_ratio(
        facts, "LongTermDebt", "StockholdersEquity", "debt_to_equity"
    )
    m["net_debt"] = calculate_difference(
        facts, "LongTermDebt", "CashAndEquivalents", "net_debt", "-"
    )

    m["fcf"] = calculate_difference(
        facts, "OperatingCashFlow_TTM", "Capex_TTM", "fcf", "-"
    )
    m["ebitda"] = calculate_difference(
        facts, "OperatingIncomeLoss_TTM", "DepreciationAndAmortization_TTM", "ebitda", "+"
    )

    revenue_ttm_rows = facts[facts["concept"] == "Revenue_TTM"][["ticker", "end", "value"]]

    m["fcf_margin"] = calculate_ratio_from_dfs(
        m["fcf"], revenue_ttm_rows, "fcf", "value", "fcf_margin"
    )
    m["net_debt_to_ebitda"] = calculate_ratio_from_dfs(
        m["net_debt"], m["ebitda"], "net_debt", "ebitda", "net_debt_to_ebitda"
    )
    m["rule_of_40"] = calculate_sum_from_dfs(
        m["revenue_growth"], m["fcf_margin"], "yoy_growth", "fcf_margin", "rule_of_40"
    )

    return m


def build_metrics_long(metrics: dict) -> pd.DataFrame:
    spec = [
        (metrics["revenue_growth"], "yoy_growth", "revenue_yoy_growth"),
        (metrics["income_growth"], "yoy_growth", "income_yoy_growth"),
        (metrics["operating_margin"], "operating_margin", "operating_margin"),
        (metrics["roe"], "roe", "roe"),
        (metrics["debt_to_equity"], "debt_to_equity", "debt_to_equity"),
        (metrics["payout_ratio"], "payout_ratio", "payout_ratio"),
        (metrics["fcf_margin"], "fcf_margin", "fcf_margin"),
        (metrics["net_debt_to_ebitda"], "net_debt_to_ebitda", "net_debt_to_ebitda"),
        (metrics["rule_of_40"], "rule_of_40", "rule_of_40"),
    ]

    rows = [to_long_format(df, value_col, name) for df, value_col, name in spec]
    return pd.concat(rows, ignore_index=True)


def calculate_historical_pe(facts: pd.DataFrame, price_history: pd.DataFrame) -> tuple:
    eps_ttm = facts[facts["concept"] == "EPS_TTM_CALC"][["ticker", "end", "value"]].copy()
    eps_ttm = eps_ttm.rename(columns={"value": "eps_ttm"})

    with_price = pd.merge_asof(
        eps_ttm.sort_values("end"),
        price_history.sort_values("date"),
        left_on="end",
        right_on="date",
        by="ticker",
        direction="backward",
    )
    with_price["pe_ratio"] = with_price["close"] / with_price["eps_ttm"]

    with_price["pe_ratio"] = with_price["pe_ratio"].where(with_price["pe_ratio"] <= 200)

    rolling = calculate_rolling_average(with_price, "pe_ratio", 20, "avg_pe_5y")
    return with_price, rolling


def build_valuation_history(facts: pd.DataFrame, price_history: pd.DataFrame) -> pd.DataFrame:
    needed = [
        "EPS_TTM_CALC",
        "Revenue_TTM",
        "StockholdersEquity",
        "SharesOutstanding",
        "LongTermDebt",
        "CashAndEquivalents",
        "DividendsPerShare_TTM",
        "FCF_TTM",
        "EBITDA_TTM",
    ]

    wide = (
    facts[facts["concept"].isin(needed)]
    .pivot_table(index=["ticker", "end"], columns="concept", values="value")
    .reset_index()
)

    for concept in needed:
        if concept not in wide.columns:
            wide[concept] = pd.NA

    wide = pd.merge_asof(
        wide.sort_values("end"),
        price_history.sort_values("date"),
        left_on="end",
        right_on="date",
        by="ticker",
        direction="backward",
    )

    wide["market_cap"] = wide["close"] * wide["SharesOutstanding"]
    wide["net_debt"] = wide["LongTermDebt"] - wide["CashAndEquivalents"]
    wide["ev"] = wide["market_cap"] + wide["net_debt"]

    wide["pe_ratio"] = wide["close"] / wide["EPS_TTM_CALC"].where(wide["EPS_TTM_CALC"] > 0)
    wide["pb_ratio"] = wide["market_cap"] / wide["StockholdersEquity"].where(wide["StockholdersEquity"] > 0)
    wide["pfcf_ratio"] = wide["market_cap"] / wide["FCF_TTM"].where(wide["FCF_TTM"] > 0)
    wide["ev_ebitda"] = wide["ev"] / wide["EBITDA_TTM"].where(wide["EBITDA_TTM"] > 0)
    wide["ev_sales"] = wide["ev"] / wide["Revenue_TTM"].where(wide["Revenue_TTM"] > 0)
    wide["dividend_yield"] = (
        wide["DividendsPerShare_TTM"].where(wide["DividendsPerShare_TTM"] >= 0) / wide["close"]
    )

    value_cols = ["pe_ratio", "pb_ratio", "pfcf_ratio", "ev_ebitda", "ev_sales", "dividend_yield"]

    MAX_MULTIPLE = 200

    for col in ["pe_ratio", "pb_ratio", "pfcf_ratio", "ev_ebitda", "ev_sales"]:
        wide[col] = wide[col].where(wide[col] <= MAX_MULTIPLE)

    long = wide.melt(
        id_vars=["ticker", "end"],
        value_vars=value_cols,
        var_name="concept",
        value_name="value",
    )

    return long.dropna(subset=["value"])


def build_snapshot(
    facts: pd.DataFrame,
    metrics: dict,
    prices: pd.DataFrame,
    rolling_pe: pd.DataFrame,
) -> pd.DataFrame:

    snap = prices.copy()

    eps = get_latest_value(facts, "EPS_TTM_CALC").rename(columns={"value": "eps_ttm"})
    revenue = get_latest_value(facts, "Revenue_TTM").rename(columns={"value": "revenue_ttm"})
    dividends = get_latest_value(facts, "DividendsPerShare_TTM").rename(columns={"value": "dividends_ttm"})

    fcf = get_latest_row(metrics["fcf"]).rename(columns={"fcf": "fcf_ttm"})
    ebitda = get_latest_row(metrics["ebitda"]).rename(columns={"ebitda": "ebitda_ttm"})

    equity = get_latest_value(facts, "StockholdersEquity").rename(columns={"value": "equity"})
    debt = get_latest_value(facts, "LongTermDebt").rename(columns={"value": "debt"})
    cash = get_latest_value(facts, "CashAndEquivalents").rename(columns={"value": "cash"})

    growth = get_latest_row(metrics["revenue_growth"])
    avg_pe = get_latest_row(rolling_pe)

    for df, cols in [
        (eps, ["ticker", "eps_ttm"]),
        (equity, ["ticker", "equity"]),
        (fcf, ["ticker", "fcf_ttm"]),
        (ebitda, ["ticker", "ebitda_ttm"]),
        (revenue, ["ticker", "revenue_ttm"]),
        (dividends, ["ticker", "dividends_ttm"]),
        (debt, ["ticker", "debt"]),
        (cash, ["ticker", "cash"]),
        (growth, ["ticker", "yoy_growth"]),
        (avg_pe, ["ticker", "avg_pe_5y"]),
    ]:
        snap = pd.merge(snap, df[cols], on="ticker", how="left")

    snap["net_debt"] = snap["debt"] - snap["cash"]
    snap["ev"] = snap["market_cap"] + snap["net_debt"]

    snap["pe_ttm"] = snap["price"] / snap["eps_ttm"]
    snap["pb_ratio"] = snap["market_cap"] / snap["equity"]
    snap["pfcf_ttm"] = snap["market_cap"] / snap["fcf_ttm"]
    snap["ev_ebitda"] = snap["ev"] / snap["ebitda_ttm"]
    snap["ev_sales"] = snap["ev"] / snap["revenue_ttm"]
    snap["peg_ratio"] = snap["pe_ttm"] / (snap["yoy_growth"] * 100)
    snap["dividend_yield"] = snap["dividends_ttm"] / snap["price"]

    return snap


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(FIGURE_DIR, exist_ok=True)

    facts = load_facts()
    facts = normalize_split_adjusted(facts, ["SharesOutstanding"])
    print_data_quality(facts, list(CONCEPT_CANDIDATES.keys()), SEARCH_HINTS)
    
    

    facts = add_derived_concepts(facts)
    metrics = calculate_all_metrics(facts)

    facts = add_as_concept(facts, metrics["fcf"], "fcf", "FCF_TTM")
    facts = add_as_concept(facts, metrics["ebitda"], "ebitda", "EBITDA_TTM")
    

    duplicates = facts[facts.duplicated(subset=["ticker", "concept", "end"], keep=False)]
    if not duplicates.empty:
        print("WARNUNG: Duplikate gefunden!")
        print(duplicates)

    metrics_long = build_metrics_long(metrics)

    price_history = load_price_history()
    prices = load_current_prices()

    valuation_history = build_valuation_history(facts, price_history)
    _, rolling_pe = calculate_historical_pe(facts, price_history)
    snapshot = build_snapshot(facts, metrics, prices, rolling_pe)


    facts.to_csv(os.path.join(DATA_DIR, f"{PERIOD}_facts.csv"), index=False)
    metrics_long.to_csv(os.path.join(DATA_DIR, "metrics_long.csv"), index=False)
    valuation_history.to_csv(os.path.join(DATA_DIR, "valuation_history.csv"), index=False)
    snapshot.to_csv(os.path.join(DATA_DIR, "current_snapshot.csv"), index=False)

    print(snapshot[["ticker", "price", "pe_ttm", "avg_pe_5y", "pb_ratio", "ev_ebitda", "peg_ratio"]])

    for ticker in TICKERS:
        plot_fundamentals(ticker, metrics_long, os.path.join(FIGURE_DIR, f"{ticker}_fundamentals.png"))
        plot_valuation(ticker, valuation_history, os.path.join(FIGURE_DIR, f"{ticker}_valuation.png"))


if __name__ == "__main__":
    main()