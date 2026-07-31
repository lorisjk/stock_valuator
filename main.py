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
    SEARCH_HINTS,
    SNAPSHOT_AS_OF_DATES,
    TICKER_PROFILES,
    PROFILE_HIDDEN,
    DEFAULT_PROFILE,
    get_expected_concepts,
    is_hidden,
    filter_hidden_rows,
    get_concept_candidates,
    get_active_tickers,
    CACHE_DIR,
)
from metrics import (
    add_ttm_concepts,
    add_as_concept,
    calculate_growth,
    calculate_ratio,
    calculate_difference,
    calculate_ratio_from_dfs,
    calculate_sum_from_dfs,
    calculate_difference_from_dfs,
    calculate_rolling_average,
    get_latest_value,
    get_latest_row,
    to_long_format,
    normalize_split_adjusted,
    apply_denominator_scale_guard,
    apply_self_relative_scale_guard,
    MIN_DENOMINATOR_SCALE_RATIO,
    MIN_OPERATING_LEVERAGE_REVENUE_GROWTH,
    MAX_OPERATING_LEVERAGE_ABS,
    MIN_NET_DEBT_TO_EBITDA_ABS,
    MAX_NET_DEBT_TO_EBITDA_ABS,
    MIN_DEBT_TO_EQUITY_SCALE_RATIO,
    REVENUE_SELF_SCALE_WINDOW,
    MIN_REVENUE_SELF_SCALE_RATIO,
    MIN_PEG_REVENUE_GROWTH,
    MAX_PEG_RATIO_ABS,
)
from figures import plot_fundamentals, plot_valuation, plot_growth
from quality import print_data_quality

import os
import time
import pandas as pd

from datetime import date, datetime


def load_facts() -> pd.DataFrame:
    mapping = fetch_or_cache(
        url="https://www.sec.gov/files/company_tickers.json",
        cache_path="cache/ticker_mapping.json",
        headers={"User-Agent": EDGAR_USER_AGENT},
    )
    cik_mapping = build_ticker_to_cik(mapping)

    all_dfs = []
    for ticker in TICKERS:
        concept_candidates = get_concept_candidates(ticker)
        cik = get_cik(ticker, cik_mapping)
        company_info = get_company_info(ticker, cik, EDGAR_USER_AGENT)
        all_dfs.append(build_dataframe(ticker, company_info, concept_candidates, period=PERIOD))
        
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

    tangible_equity = calculate_difference(facts, "StockholdersEquity", "Goodwill", "value", "-")
    tangible_equity["concept"] = "TangibleEquity"
    facts = pd.concat([facts, tangible_equity[["ticker", "end", "concept", "value"]]], ignore_index=True)

    nii = facts[facts["concept"] == "NetInterestIncome_TTM"][["ticker", "end", "value"]].rename(columns={"value": "nii"})
    nonii = facts[facts["concept"] == "NoninterestIncome_TTM"][["ticker", "end", "value"]].rename(columns={"value": "nonii"})
    nonexp = facts[facts["concept"] == "NoninterestExpense_TTM"][["ticker", "end", "value"]].rename(columns={"value": "nonexp"})

    ppnr = nii.merge(nonii, on=["ticker", "end"]).merge(nonexp, on=["ticker", "end"])
    ppnr["value"] = ppnr["nii"] + ppnr["nonii"] - ppnr["nonexp"]
    ppnr["concept"] = "PPNR"
    facts = pd.concat([facts, ppnr[["ticker", "end", "concept", "value"]]], ignore_index=True)

    ni = facts[facts["concept"] == "NetIncomeLoss_TTM"][["ticker", "end", "value"]].rename(columns={"value": "ni"})
    realized = facts[facts["concept"] == "RealizedInvestmentGains_TTM"][["ticker", "end", "value"]].rename(columns={"value": "realized"})

    core_earnings = ni.merge(realized, on=["ticker", "end"])
    core_earnings["value"] = core_earnings["ni"] - core_earnings["realized"]
    core_earnings["concept"] = "CoreOperatingEarnings"
    facts = pd.concat([facts, core_earnings[["ticker", "end", "concept", "value"]]], ignore_index=True)

    ni_ffo = facts[facts["concept"] == "NetIncomeLoss_TTM"][["ticker", "end", "value"]].rename(columns={"value": "ni"})
    dep_ffo = facts[facts["concept"] == "DepreciationAndAmortization_TTM"][["ticker", "end", "value"]].rename(columns={"value": "dep"})
    re_gains = facts[facts["concept"] == "GainLossOnSaleOfProperties_TTM"][["ticker", "end", "value"]].rename(columns={"value": "gains"})

    ffo = ni_ffo.merge(dep_ffo, on=["ticker", "end"]).merge(re_gains, on=["ticker", "end"], how="left")
    ffo["gains"] = ffo["gains"].fillna(0)
    ffo["value"] = ffo["ni"] + ffo["dep"] - ffo["gains"]
    ffo["concept"] = "FFO_TTM"
    facts = pd.concat([facts, ffo[["ticker", "end", "concept", "value"]]], ignore_index=True)

    return facts


def add_quarterly_derived_concepts(facts: pd.DataFrame) -> pd.DataFrame:
    """Single-quarter counterparts of the derived concepts in add_derived_concepts()
    that currently exist only in TTM form -- so a single quarter's inflection (e.g. a
    company's most recent quarterly FCF turning negative) is visible immediately
    instead of only once it has moved the trailing-twelve-month sum. Mirrors
    add_derived_concepts() exactly, just built from the plain (already-quarterly)
    concepts instead of their "_TTM" versions. Purely additive: every concept added
    here is new (a "_QUARTERLY" name), nothing here touches or replaces a TTM concept.
    """
    eps_q = calculate_ratio(facts, "NetIncomeLoss", "SharesOutstanding", "value")
    eps_q["concept"] = "EPS_QUARTERLY_CALC"
    facts = pd.concat([facts, eps_q[["ticker", "end", "concept", "value"]]], ignore_index=True)

    nii = facts[facts["concept"] == "NetInterestIncome"][["ticker", "end", "value"]].rename(columns={"value": "nii"})
    nonii = facts[facts["concept"] == "NoninterestIncome"][["ticker", "end", "value"]].rename(columns={"value": "nonii"})
    nonexp = facts[facts["concept"] == "NoninterestExpense"][["ticker", "end", "value"]].rename(columns={"value": "nonexp"})

    ppnr_q = nii.merge(nonii, on=["ticker", "end"]).merge(nonexp, on=["ticker", "end"])
    ppnr_q["value"] = ppnr_q["nii"] + ppnr_q["nonii"] - ppnr_q["nonexp"]
    ppnr_q["concept"] = "PPNR_QUARTERLY"
    facts = pd.concat([facts, ppnr_q[["ticker", "end", "concept", "value"]]], ignore_index=True)

    ni = facts[facts["concept"] == "NetIncomeLoss"][["ticker", "end", "value"]].rename(columns={"value": "ni"})
    realized = facts[facts["concept"] == "RealizedInvestmentGains"][["ticker", "end", "value"]].rename(columns={"value": "realized"})

    core_q = ni.merge(realized, on=["ticker", "end"])
    core_q["value"] = core_q["ni"] - core_q["realized"]
    core_q["concept"] = "CoreOperatingEarnings_QUARTERLY"
    facts = pd.concat([facts, core_q[["ticker", "end", "concept", "value"]]], ignore_index=True)

    ni_ffo = facts[facts["concept"] == "NetIncomeLoss"][["ticker", "end", "value"]].rename(columns={"value": "ni"})
    dep_ffo = facts[facts["concept"] == "DepreciationAndAmortization"][["ticker", "end", "value"]].rename(columns={"value": "dep"})
    re_gains = facts[facts["concept"] == "GainLossOnSaleOfProperties"][["ticker", "end", "value"]].rename(columns={"value": "gains"})

    ffo_q = ni_ffo.merge(dep_ffo, on=["ticker", "end"]).merge(re_gains, on=["ticker", "end"], how="left")
    ffo_q["gains"] = ffo_q["gains"].fillna(0)
    ffo_q["value"] = ffo_q["ni"] + ffo_q["dep"] - ffo_q["gains"]
    ffo_q["concept"] = "FFO_QUARTERLY"
    facts = pd.concat([facts, ffo_q[["ticker", "end", "concept", "value"]]], ignore_index=True)

    return facts


def calculate_all_metrics(facts: pd.DataFrame) -> dict:
    m = {}

    m["revenue_growth"] = calculate_growth(facts, "Revenue_TTM", 4, "yoy_growth")
    m["income_growth"] = calculate_growth(facts, "NetIncomeLoss_TTM", 4, "yoy_growth")

    m["operating_margin"] = calculate_ratio(
        facts, "OperatingIncomeLoss_TTM", "Revenue_TTM", "operating_margin"
    )
    m["roe"] = calculate_ratio(
        facts, "NetIncomeLoss_TTM", "StockholdersEquity", "roe",
        require_positive_denominator=True,
        min_denominator_scale_ref="Revenue_TTM",
        min_denominator_scale_ratio=MIN_DENOMINATOR_SCALE_RATIO,
    )
    m["payout_ratio"] = calculate_ratio(
        facts, "DividendsPerShare_TTM", "EPS_TTM_CALC", "payout_ratio",
        require_positive_denominator=True,
    )

    m["debt_to_equity"] = calculate_ratio(
        facts, "LongTermDebt", "StockholdersEquity", "debt_to_equity",
        require_positive_denominator=True,
        min_denominator_scale_ref="LongTermDebt",
        min_denominator_scale_ratio=MIN_DEBT_TO_EQUITY_SCALE_RATIO,
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

    revenue_ttm_rows = facts[facts["concept"] == "Revenue_TTM"][["ticker", "end", "value"]].rename(
        columns={"value": "Revenue_TTM"}
    )

    m["operating_margin"] = m["operating_margin"].merge(revenue_ttm_rows, on=["ticker", "end"], how="left")
    m["operating_margin"]["operating_margin"] = apply_self_relative_scale_guard(
        m["operating_margin"], "operating_margin", "Revenue_TTM",
        window=REVENUE_SELF_SCALE_WINDOW, min_self_scale_ratio=MIN_REVENUE_SELF_SCALE_RATIO,
    )
    m["operating_margin"] = m["operating_margin"][["ticker", "end", "operating_margin"]]

    m["fcf_margin"] = calculate_ratio_from_dfs(
        m["fcf"], revenue_ttm_rows, "fcf", "Revenue_TTM", "fcf_margin"
    )
    m["fcf_margin"] = m["fcf_margin"].merge(revenue_ttm_rows, on=["ticker", "end"], how="left")
    m["fcf_margin"]["fcf_margin"] = apply_self_relative_scale_guard(
        m["fcf_margin"], "fcf_margin", "Revenue_TTM",
        window=REVENUE_SELF_SCALE_WINDOW, min_self_scale_ratio=MIN_REVENUE_SELF_SCALE_RATIO,
    )
    m["fcf_margin"] = m["fcf_margin"][["ticker", "end", "fcf_margin"]]

    m["net_debt_to_ebitda"] = calculate_ratio_from_dfs(
        m["net_debt"], m["ebitda"], "net_debt", "ebitda", "net_debt_to_ebitda",
        min_denominator_abs=MIN_NET_DEBT_TO_EBITDA_ABS,
        max_abs_result=MAX_NET_DEBT_TO_EBITDA_ABS,
    )
    m["rule_of_40"] = calculate_sum_from_dfs(
        m["revenue_growth"], m["fcf_margin"], "yoy_growth", "fcf_margin", "rule_of_40"
    )

    m["net_interest_margin"] = calculate_ratio(
        facts, "NetInterestIncome_TTM", "Assets", "net_interest_margin"
    )
    m["efficiency_ratio"] = calculate_ratio(
        facts, "NoninterestExpense_TTM", "Revenue_TTM", "efficiency_ratio"
    )
    m["roa"] = calculate_ratio(
        facts, "NetIncomeLoss_TTM", "Assets", "roa"
    )
    m["equity_to_assets"] = calculate_ratio(
        facts, "StockholdersEquity", "Assets", "equity_to_assets"
    )
    m["provision_ratio"] = calculate_ratio(
        facts, "ProvisionForCreditLosses_TTM", "Revenue_TTM", "provision_ratio"
    )
    m["combined_ratio"] = calculate_ratio(
        facts, "BenefitsLossesAndExpenses_TTM", "EarnedPremiums_TTM", "combined_ratio"
    )
    m["loss_ratio"] = calculate_ratio(
        facts, "IncurredLosses_TTM", "EarnedPremiums_TTM", "loss_ratio"
    )
    m["expense_ratio"] = calculate_difference_from_dfs(
        m["combined_ratio"], m["loss_ratio"], "combined_ratio", "loss_ratio", "expense_ratio"
    )
    m["net_investment_yield"] = calculate_ratio(
        facts, "NetInvestmentIncome_TTM", "Investments", "net_investment_yield"
    )
    m["reserve_growth"] = calculate_growth(
        facts, "ClaimsReserve", 4, "reserve_growth"
    )
  
    m["inventory_turnover"] = calculate_ratio(
        facts, "CostOfRevenue_TTM", "Inventory", "inventory_turnover"
    )

    m["dio"] = calculate_ratio(facts, "Inventory", "CostOfRevenue_TTM", "dio")
    m["dio"]["dio"] = m["dio"]["dio"] * 365

    m["dso"] = calculate_ratio(facts, "AccountsReceivable", "Revenue_TTM", "dso")
    m["dso"]["dso"] = m["dso"]["dso"] * 365

    m["dpo"] = calculate_ratio(facts, "AccountsPayable", "CostOfRevenue_TTM", "dpo")
    m["dpo"]["dpo"] = m["dpo"]["dpo"] * 365

    dio_plus_dso = calculate_sum_from_dfs(m["dio"], m["dso"], "dio", "dso", "dio_plus_dso")
    m["cash_conversion_cycle"] = calculate_difference_from_dfs(
        dio_plus_dso, m["dpo"], "dio_plus_dso", "dpo", "cash_conversion_cycle"
    )
    m["rd_intensity"] = calculate_ratio(
    facts, "ResearchAndDevelopment_TTM", "Revenue_TTM", "rd_intensity"
    )
    m["operating_income_growth"] = calculate_growth(
        facts, "OperatingIncomeLoss_TTM", 4, "operating_income_yoy_growth"
    )
    m["operating_leverage"] = calculate_ratio_from_dfs(
        m["operating_income_growth"], m["revenue_growth"],
        "operating_income_yoy_growth", "yoy_growth", "operating_leverage",
        min_denominator_abs=MIN_OPERATING_LEVERAGE_REVENUE_GROWTH,
        max_abs_result=MAX_OPERATING_LEVERAGE_ABS,
    )
    m["capex_intensity"] = calculate_ratio(
    facts, "Capex_TTM", "Revenue_TTM", "capex_intensity"
    )
    m["ffo_margin"] = calculate_ratio(
        facts, "FFO_TTM", "Revenue_TTM", "ffo_margin"
    )
    return m


def calculate_quarterly_metrics(facts: pd.DataFrame) -> dict:
    m = {}

    m["fcf_quarterly"] = calculate_difference(
        facts, "OperatingCashFlow", "Capex", "fcf_quarterly", "-"
    )
    m["ebitda_quarterly"] = calculate_difference(
        facts, "OperatingIncomeLoss", "DepreciationAndAmortization", "ebitda_quarterly", "+"
    )

    revenue_q_rows = facts[facts["concept"] == "Revenue"][["ticker", "end", "value"]].rename(
        columns={"value": "Revenue"}
    )

    m["operating_margin_quarterly"] = calculate_ratio(
        facts, "OperatingIncomeLoss", "Revenue", "operating_margin_quarterly"
    )
    m["payout_ratio_quarterly"] = calculate_ratio(
        facts, "DividendsPerShare", "EPS_QUARTERLY_CALC", "payout_ratio_quarterly",
        require_positive_denominator=True,
    )
    m["fcf_margin_quarterly"] = calculate_ratio_from_dfs(
        m["fcf_quarterly"], revenue_q_rows, "fcf_quarterly", "Revenue", "fcf_margin_quarterly"
    )
    m["efficiency_ratio_quarterly"] = calculate_ratio(
        facts, "NoninterestExpense", "Revenue", "efficiency_ratio_quarterly"
    )
    m["provision_ratio_quarterly"] = calculate_ratio(
        facts, "ProvisionForCreditLosses", "Revenue", "provision_ratio_quarterly"
    )
    m["combined_ratio_quarterly"] = calculate_ratio(
        facts, "BenefitsLossesAndExpenses", "EarnedPremiums", "combined_ratio_quarterly"
    )
    m["loss_ratio_quarterly"] = calculate_ratio(
        facts, "IncurredLosses", "EarnedPremiums", "loss_ratio_quarterly"
    )
    m["expense_ratio_quarterly"] = calculate_difference_from_dfs(
        m["combined_ratio_quarterly"], m["loss_ratio_quarterly"],
        "combined_ratio_quarterly", "loss_ratio_quarterly", "expense_ratio_quarterly"
    )
    m["rd_intensity_quarterly"] = calculate_ratio(
        facts, "ResearchAndDevelopment", "Revenue", "rd_intensity_quarterly"
    )
    m["capex_intensity_quarterly"] = calculate_ratio(
        facts, "Capex", "Revenue", "capex_intensity_quarterly"
    )
    m["ffo_margin_quarterly"] = calculate_ratio(
        facts, "FFO_QUARTERLY", "Revenue", "ffo_margin_quarterly"
    )

    return m


_TTM_LIKE_SUFFIX = "_TTM"
_TTM_LIKE_NAMES = {"PPNR", "CoreOperatingEarnings"}   # TTM-derived despite the name

_GROWTH_EXCLUDED_CONCEPTS = {"GainLossOnSaleOfProperties", "RealizedInvestmentGains"}


GROWTH_MIN_BASE_RATIO_OVERRIDES = {
    "Capex": 0.05,
    "Goodwill": 0.05,
    "CashAndEquivalents": 0.05,
    "Inventory": 0.05,
    "LongTermDebt": 0.05,
    "ProvisionForCreditLosses": 0.05,
    "TangibleEquity": 0.05,
}

GROWTH_COLUMN = "yoy_growth"


def growth_concepts(facts: pd.DataFrame) -> list[str]:
    return sorted(
        c for c in facts["concept"].unique()
        if _TTM_LIKE_SUFFIX not in c
        and c not in _TTM_LIKE_NAMES
        and c not in _GROWTH_EXCLUDED_CONCEPTS
    )


def add_growth_column(facts: pd.DataFrame) -> pd.DataFrame:
    """Attach a year-over-year growth column to the facts frame.

    Purely additive by construction: the row set and the `value` column are returned
    untouched, and rows with no prior-year match within calculate_growth()'s date
    tolerance (or masked by min_base_ratio) simply get NaN in the new column rather than
    being dropped. Applied at the very end of the pipeline, immediately before writing
    the CSV, so no intermediate consumer of `facts` ever sees the extra column.
    """
    parts = []
    for concept in growth_concepts(facts):
        g = calculate_growth(
            facts, concept, 4, GROWTH_COLUMN,
            min_base_ratio=GROWTH_MIN_BASE_RATIO_OVERRIDES.get(concept, 0.33),
        )
        if g.empty:
            continue
        g = g[["ticker", "end", GROWTH_COLUMN]].copy()
        g["concept"] = concept
        parts.append(g)

    if not parts:
        facts[GROWTH_COLUMN] = pd.NA
        return facts

    growth = pd.concat(parts, ignore_index=True).drop_duplicates(subset=["ticker", "concept", "end"])
    return facts.merge(growth, on=["ticker", "concept", "end"], how="left")


def build_metrics_long(metrics: dict, quarterly_metrics: dict = None) -> pd.DataFrame:
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
        (metrics["net_interest_margin"], "net_interest_margin", "net_interest_margin"),
        (metrics["efficiency_ratio"], "efficiency_ratio", "efficiency_ratio"),
        (metrics["roa"], "roa", "roa"),
        (metrics["equity_to_assets"], "equity_to_assets", "equity_to_assets"),
        (metrics["provision_ratio"], "provision_ratio", "provision_ratio"),
        (metrics["combined_ratio"], "combined_ratio", "combined_ratio"),
        (metrics["loss_ratio"], "loss_ratio", "loss_ratio"),
        (metrics["expense_ratio"], "expense_ratio", "expense_ratio"),
        (metrics["net_investment_yield"], "net_investment_yield", "net_investment_yield"),
        (metrics["reserve_growth"], "reserve_growth", "reserve_growth"),
        (metrics["inventory_turnover"], "inventory_turnover", "inventory_turnover"),
        (metrics["dio"], "dio", "dio"),
        (metrics["dso"], "dso", "dso"),
        (metrics["dpo"], "dpo", "dpo"),
        (metrics["cash_conversion_cycle"], "cash_conversion_cycle", "cash_conversion_cycle"),
        (metrics["rd_intensity"], "rd_intensity", "rd_intensity"),
        (metrics["capex_intensity"], "capex_intensity", "capex_intensity"),
        (metrics["operating_leverage"], "operating_leverage", "operating_leverage"),
        (metrics["operating_income_growth"], "operating_income_yoy_growth", "operating_income_yoy_growth"),
        (metrics["ffo_margin"], "ffo_margin", "ffo_margin"),
    ]

    if quarterly_metrics:
        spec += [
            (quarterly_metrics["operating_margin_quarterly"], "operating_margin_quarterly", "operating_margin_quarterly"),
            (quarterly_metrics["payout_ratio_quarterly"], "payout_ratio_quarterly", "payout_ratio_quarterly"),
            (quarterly_metrics["fcf_margin_quarterly"], "fcf_margin_quarterly", "fcf_margin_quarterly"),
            (quarterly_metrics["efficiency_ratio_quarterly"], "efficiency_ratio_quarterly", "efficiency_ratio_quarterly"),
            (quarterly_metrics["provision_ratio_quarterly"], "provision_ratio_quarterly", "provision_ratio_quarterly"),
            (quarterly_metrics["combined_ratio_quarterly"], "combined_ratio_quarterly", "combined_ratio_quarterly"),
            (quarterly_metrics["loss_ratio_quarterly"], "loss_ratio_quarterly", "loss_ratio_quarterly"),
            (quarterly_metrics["expense_ratio_quarterly"], "expense_ratio_quarterly", "expense_ratio_quarterly"),
            (quarterly_metrics["rd_intensity_quarterly"], "rd_intensity_quarterly", "rd_intensity_quarterly"),
            (quarterly_metrics["capex_intensity_quarterly"], "capex_intensity_quarterly", "capex_intensity_quarterly"),
            (quarterly_metrics["ffo_margin_quarterly"], "ffo_margin_quarterly", "ffo_margin_quarterly"),
        ]

    rows = [to_long_format(df, value_col, name) for df, value_col, name in spec]
    return pd.concat(rows, ignore_index=True)


MIN_VALUATION_DENOMINATOR_SCALE_RATIO = 0.001


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


def build_valuation_history(facts: pd.DataFrame, price_history: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
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
        "TangibleEquity",
        "PPNR", 
        "CoreOperatingEarnings",
        "FFO_TTM"
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
    wide["revenue_yoy_growth"] = wide.groupby("ticker")["Revenue_TTM"].pct_change(periods=4)

    shares_outstanding_count = wide.groupby("ticker")["SharesOutstanding"].transform("count")
    shares_fallback = wide["ticker"].map(prices.set_index("ticker")["shares_outstanding"])
    shares_for_market_cap = wide["SharesOutstanding"].where(shares_outstanding_count > 0, shares_fallback)

    wide["market_cap"] = wide["close"] * shares_for_market_cap
    wide["net_debt"] = wide["LongTermDebt"] - wide["CashAndEquivalents"]
    wide["ev"] = wide["market_cap"] + wide["net_debt"]
    

    wide["pe_ratio"] = wide["close"] / wide["EPS_TTM_CALC"].where(wide["EPS_TTM_CALC"] > 0)
    wide["pb_ratio"] = wide["market_cap"] / wide["StockholdersEquity"].where(wide["StockholdersEquity"] > 0)
    wide["pfcf_ratio"] = wide["market_cap"] / wide["FCF_TTM"].where(wide["FCF_TTM"] > 0)
    wide["ev_ebitda"] = wide["ev"] / wide["EBITDA_TTM"].where(wide["EBITDA_TTM"] > 0)
    wide["ev_sales"] = wide["ev"] / wide["Revenue_TTM"].where(wide["Revenue_TTM"] > 0)
    wide["dividend_yield"] = (wide["DividendsPerShare_TTM"].where(wide["DividendsPerShare_TTM"] >= 0) / wide["close"])

    wide["p_tbv"] = wide["market_cap"] / wide["TangibleEquity"].where(wide["TangibleEquity"] > 0)
    wide["p_ppnr"] = wide["market_cap"] / wide["PPNR"].where(wide["PPNR"] > 0)
    wide["p_core_earnings"] = wide["market_cap"] / wide["CoreOperatingEarnings"].where(wide["CoreOperatingEarnings"] > 0)
    wide["p_ffo"] = wide["market_cap"] / wide["FFO_TTM"].where(wide["FFO_TTM"] > 0)

    implied_earnings_ttm = wide["EPS_TTM_CALC"] * shares_for_market_cap
    for col, denominator in [
        ("pe_ratio", implied_earnings_ttm),
        ("pb_ratio", wide["StockholdersEquity"]),
        ("pfcf_ratio", wide["FCF_TTM"]),
        ("ev_ebitda", wide["EBITDA_TTM"]),
        ("p_tbv", wide["TangibleEquity"]),
        ("p_ppnr", wide["PPNR"]),
        ("p_core_earnings", wide["CoreOperatingEarnings"]),
        ("p_ffo", wide["FFO_TTM"]),
    ]:
        wide[col] = apply_denominator_scale_guard(
            wide[col], denominator, wide["Revenue_TTM"], MIN_VALUATION_DENOMINATOR_SCALE_RATIO
        )

    wide["peg_ratio"] = wide["pe_ratio"] / (wide["revenue_yoy_growth"] * 100)
    wide["peg_ratio"] = wide["peg_ratio"].where(wide["revenue_yoy_growth"] > MIN_PEG_REVENUE_GROWTH)
    wide["peg_ratio"] = wide["peg_ratio"].where(wide["peg_ratio"].abs() <= MAX_PEG_RATIO_ABS)

    value_cols = ["pe_ratio", "pb_ratio", "pfcf_ratio", "ev_ebitda", "ev_sales", "dividend_yield", "p_tbv", "p_ppnr", "p_core_earnings", "peg_ratio", "p_ffo"]

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
    as_of: "str | pd.Timestamp | None" = None,
) -> pd.DataFrame:
    
    as_of_date = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp(date.today())

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

    nim = get_latest_row(metrics["net_interest_margin"])
    efficiency = get_latest_row(metrics["efficiency_ratio"])
    tangible_equity = get_latest_value(facts, "TangibleEquity").rename(columns={"value": "tangible_equity"})
    roa = get_latest_row(metrics["roa"])
    equity_to_assets = get_latest_row(metrics["equity_to_assets"])
    provision_ratio = get_latest_row(metrics["provision_ratio"])
    ppnr_latest = get_latest_value(facts, "PPNR").rename(columns={"value": "ppnr_ttm"})
    combined_ratio = get_latest_row(metrics["combined_ratio"])
    loss_ratio = get_latest_row(metrics["loss_ratio"])
    expense_ratio = get_latest_row(metrics["expense_ratio"])
    net_investment_yield = get_latest_row(metrics["net_investment_yield"])
    reserve_growth = get_latest_row(metrics["reserve_growth"])
    core_earnings_latest = get_latest_value(facts, "CoreOperatingEarnings").rename(columns={"value": "core_earnings_ttm"})
    inventory_turnover = get_latest_row(metrics["inventory_turnover"])
    dio = get_latest_row(metrics["dio"])
    dso = get_latest_row(metrics["dso"])
    dpo = get_latest_row(metrics["dpo"])
    ccc = get_latest_row(metrics["cash_conversion_cycle"])
    rd_intensity = get_latest_row(metrics["rd_intensity"])
    capex_intensity = get_latest_row(metrics["capex_intensity"])
    operating_leverage = get_latest_row(metrics["operating_leverage"])


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
        (nim, ["ticker", "net_interest_margin"]),
        (efficiency, ["ticker", "efficiency_ratio"]),
        (tangible_equity, ["ticker", "tangible_equity"]),
        (roa, ["ticker", "roa"]),
        (equity_to_assets, ["ticker", "equity_to_assets"]),
        (provision_ratio, ["ticker", "provision_ratio"]),
        (ppnr_latest, ["ticker", "ppnr_ttm"]),
        (combined_ratio, ["ticker", "combined_ratio"]),
        (loss_ratio, ["ticker", "loss_ratio"]),
        (expense_ratio, ["ticker", "expense_ratio"]),
        (net_investment_yield, ["ticker", "net_investment_yield"]),
        (reserve_growth, ["ticker", "reserve_growth"]),
        (core_earnings_latest, ["ticker", "core_earnings_ttm"]),
        (inventory_turnover, ["ticker", "inventory_turnover"]),
        (dio, ["ticker", "dio"]),
        (dso, ["ticker", "dso"]),
        (dpo, ["ticker", "dpo"]),
        (ccc, ["ticker", "cash_conversion_cycle"]),
        (rd_intensity, ["ticker", "rd_intensity"]),
        (capex_intensity, ["ticker", "capex_intensity"]),
        (operating_leverage, ["ticker", "operating_leverage"])
    ]:
        snap = pd.merge(snap, df[cols], on="ticker", how="left")

    snap["net_debt"] = snap["debt"] - snap["cash"]
    snap["ev"] = snap["market_cap"] + snap["net_debt"]

    snap["pe_ttm"] = snap["price"] / snap["eps_ttm"]
    snap["pb_ratio"] = apply_denominator_scale_guard(
        snap["market_cap"] / snap["equity"], snap["equity"], snap["revenue_ttm"], MIN_DENOMINATOR_SCALE_RATIO
    )
    snap["pfcf_ttm"] = snap["market_cap"] / snap["fcf_ttm"]
    snap["ev_ebitda"] = snap["ev"] / snap["ebitda_ttm"]
    snap["ev_sales"] = snap["ev"] / snap["revenue_ttm"]
    snap["peg_ratio"] = snap["pe_ttm"].where(snap["pe_ttm"] > 0) / (snap["yoy_growth"] * 100)
    snap["peg_ratio"] = snap["peg_ratio"].where(snap["yoy_growth"] > MIN_PEG_REVENUE_GROWTH)
    snap["peg_ratio"] = snap["peg_ratio"].where(snap["peg_ratio"].abs() <= MAX_PEG_RATIO_ABS)
    snap["dividend_yield"] = snap["dividends_ttm"] / snap["price"]
    snap["p_tbv"] = apply_denominator_scale_guard(
        snap["market_cap"] / snap["tangible_equity"], snap["tangible_equity"], snap["revenue_ttm"], MIN_DENOMINATOR_SCALE_RATIO
    )
    snap["p_ppnr"] = snap["market_cap"] / snap["ppnr_ttm"]
    snap["p_core_earnings"] = snap["market_cap"] / snap["core_earnings_ttm"]
    snap = snap.rename(columns={"pe_ttm": "pe_ratio", "pfcf_ttm": "pfcf_ratio"})

    value_cols = [c for c in snap.columns if c != "ticker"]
    long = snap.melt(id_vars=["ticker"], value_vars=value_cols, var_name="concept", value_name="value")
    long = long.dropna(subset=["value"])
    long["end"] = as_of_date
    return long[["ticker", "end", "concept", "value"]]


def price_summary(long_snapshot: pd.DataFrame) -> pd.DataFrame:
    sub = long_snapshot[long_snapshot["concept"].isin(["price", "shares_outstanding", "market_cap"])]
    return sub.pivot_table(index="ticker", columns="concept", values="value").reset_index()


def get_price_as_of(price_history: pd.DataFrame, cutoff_date: pd.Timestamp) -> pd.DataFrame:
    hist = price_history[price_history["date"] <= cutoff_date]
    latest = hist.loc[hist.groupby("ticker")["date"].idxmax()]
    return latest[["ticker", "close"]].rename(columns={"close": "price"})


def build_snapshot_as_of(
    cutoff_date: str,
    facts: pd.DataFrame,
    metrics: dict,
    price_history: pd.DataFrame,
    rolling_pe: pd.DataFrame,
) -> pd.DataFrame:
    cutoff_date = pd.Timestamp(cutoff_date)

    facts_cut = facts[facts["end"] <= cutoff_date]
    metrics_cut = {k: df[df["end"] <= cutoff_date] for k, df in metrics.items()}
    rolling_pe_cut = rolling_pe[rolling_pe["end"] <= cutoff_date]

    prices_cut = get_price_as_of(price_history, cutoff_date)
    shares = get_latest_value(facts_cut, "SharesOutstanding").rename(
        columns={"value": "shares_outstanding"}
    )
    prices_cut = pd.merge(prices_cut, shares[["ticker", "shares_outstanding"]], on="ticker", how="left")
    prices_cut["market_cap"] = prices_cut["price"] * prices_cut["shares_outstanding"]

    return build_snapshot(facts_cut, metrics_cut, prices_cut, rolling_pe_cut, as_of=cutoff_date)


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(FIGURE_DIR, exist_ok=True)

    facts = load_facts()
    facts = normalize_split_adjusted(facts, ["SharesOutstanding"])
   
    expected_by_ticker = {ticker: get_expected_concepts(ticker) for ticker in TICKERS}
    print_data_quality(facts, expected_by_ticker, SEARCH_HINTS)
    
    

    facts = add_derived_concepts(facts)
    facts = add_quarterly_derived_concepts(facts)
    metrics = calculate_all_metrics(facts)
    quarterly_metrics = calculate_quarterly_metrics(facts)

    facts = add_as_concept(facts, metrics["fcf"], "fcf", "FCF_TTM")
    facts = add_as_concept(facts, metrics["ebitda"], "ebitda", "EBITDA_TTM")
    facts = add_as_concept(facts, quarterly_metrics["fcf_quarterly"], "fcf_quarterly", "FCF_QUARTERLY")
    facts = add_as_concept(facts, quarterly_metrics["ebitda_quarterly"], "ebitda_quarterly", "EBITDA_QUARTERLY")

    duplicates = facts[facts.duplicated(subset=["ticker", "concept", "end"], keep=False)]
    if not duplicates.empty:
        print("WARNUNG: Duplikate gefunden!")
        print(duplicates)

    metrics_long = build_metrics_long(metrics, quarterly_metrics)

    price_history = load_price_history()
    prices = load_current_prices()

    valuation_history = build_valuation_history(facts, price_history, prices)
    _, rolling_pe = calculate_historical_pe(facts, price_history)
    snapshot = build_snapshot(facts, metrics, prices, rolling_pe)

   

    for cutoff in SNAPSHOT_AS_OF_DATES:
        hist_snapshot = build_snapshot_as_of(cutoff, facts, metrics, price_history, rolling_pe)

        print(f"\n--- Snapshot as of {cutoff} ---")
        print(price_summary(hist_snapshot))
        print(f"\n-------------------------------")

    metrics_long = filter_hidden_rows(metrics_long)
    valuation_history = filter_hidden_rows(valuation_history)
    facts = filter_hidden_rows(facts)
    snapshot = filter_hidden_rows(snapshot)

    facts = add_growth_column(facts)

    facts.to_csv(os.path.join(DATA_DIR, f"{PERIOD}_facts.csv"), index=False)
    metrics_long.to_csv(os.path.join(DATA_DIR, "metrics_long.csv"), index=False)
    valuation_history.to_csv(os.path.join(DATA_DIR, "valuation_history.csv"), index=False)
    snapshot.to_csv(os.path.join(DATA_DIR, "current_snapshot.csv"), index=False)

    print(price_summary(snapshot))

    for ticker in TICKERS:
        plot_fundamentals(ticker, metrics_long, os.path.join(FIGURE_DIR, f"{ticker}_fundamentals.png"))
        plot_valuation(ticker, valuation_history, os.path.join(FIGURE_DIR, f"{ticker}_valuation.png"))
        plot_growth(ticker, facts, os.path.join(FIGURE_DIR, f"{ticker}_growth.png"))


def delete_cached_facts(tickers: list[str]) -> list[str]:
    deleted = []
    for ticker in tickers:
        path = os.path.join(CACHE_DIR, f"{ticker}_company_info.json")
        if os.path.exists(path):
            os.remove(path)
            deleted.append(path)
    return deleted


def _timing_summary(times: dict, slowest_n: int = 10) -> dict:
    if not times:
        return {"total": 0.0, "average": 0.0, "n": 0, "slowest": []}
    total = sum(times.values())
    n = len(times)
    slowest = sorted(times.items(), key=lambda kv: kv[1], reverse=True)[:slowest_n]
    return {"total": total, "average": total / n, "n": n, "slowest": slowest}


def write_full_refresh_report(
    report_path: str,
    run_start: datetime,
    run_end: datetime,
    active_tickers: list[str],
    deleted_cache_files: list[str],
    edgar_times: dict,
    yfinance_times: dict,
    calc_time: float,
    plot_times: dict,
    quality_flags: list[dict],
) -> None:
    edgar = _timing_summary(edgar_times)
    yfin = _timing_summary(yfinance_times)
    plot = _timing_summary(plot_times)
    total_wall = (run_end - run_start).total_seconds()

    lines = []
    lines.append("# Full Refresh Report\n")
    lines.append("## Run metadata\n")
    lines.append(f"- Start: {run_start.isoformat(timespec='seconds')}")
    lines.append(f"- End: {run_end.isoformat(timespec='seconds')}")
    lines.append(f"- Total wall-clock time: {total_wall:.1f}s ({total_wall/60:.1f} min)")
    lines.append(f"- Active tickers processed: {len(active_tickers)}")
    lines.append(f"- Cached facts files deleted: {len(deleted_cache_files)}\n")
    if deleted_cache_files:
        lines.append("<details><summary>Deleted cache files</summary>\n")
        for p in deleted_cache_files:
            lines.append(f"- `{p}`")
        lines.append("\n</details>\n")

    lines.append("## Timing\n")
    lines.append("### Phase 1 -- EDGAR fetch")
    lines.append(f"- Total: {edgar['total']:.1f}s across {edgar['n']} tickers")
    lines.append(f"- Average per ticker: {edgar['average']:.2f}s")
    lines.append("- Slowest 10 tickers:")
    for t, s in edgar["slowest"]:
        lines.append(f"  - {t}: {s:.2f}s")
    lines.append("")

    lines.append("### Phase 2 -- yfinance fetch")
    lines.append(f"- Total: {yfin['total']:.1f}s across {yfin['n']} tickers")
    lines.append(f"- Average per ticker: {yfin['average']:.2f}s")
    lines.append("- Slowest 10 tickers:")
    for t, s in yfin["slowest"]:
        lines.append(f"  - {t}: {s:.2f}s")
    lines.append("")

    lines.append("### Phase 3 -- Calculate + plot")
    lines.append(
        f"- Calculate (calculate_all_metrics/build_metrics_long/build_valuation_history"
        f"/build_snapshot, whole batch, one run -- not decomposed per ticker, since "
        f"doing so would mean calling these functions once per ticker instead of once "
        f"for the batch, a change to how the calculation runs rather than pure "
        f"instrumentation): {calc_time:.1f}s"
    )
    lines.append(f"- Plot (per ticker, both figures): total {plot['total']:.1f}s "
                  f"across {plot['n']} tickers, average {plot['average']:.2f}s/ticker")
    lines.append("- Slowest 10 tickers (plotting):")
    for t, s in plot["slowest"]:
        lines.append(f"  - {t}: {s:.2f}s")
    lines.append("")

    lines.append("## Data quality flags\n")
    if not quality_flags:
        lines.append("No concept fell below the coverage threshold for any active ticker.\n")
    else:
        by_profile = {}
        for f in quality_flags:
            profile = TICKER_PROFILES.get(f["ticker"], DEFAULT_PROFILE)
            by_profile.setdefault(profile, []).append(f)
        lines.append(f"{len(quality_flags)} flags across {len(by_profile)} profiles.\n")
        for profile in sorted(by_profile):
            lines.append(f"### {profile}\n")
            flags_sorted = sorted(by_profile[profile], key=lambda f: (f["ticker"], f["ratio"]))
            for f in flags_sorted:
                marker = "MISSING" if f["count"] == 0 else "thin"
                lines.append(
                    f"- **{marker}** {f['ticker']} `{f['concept']}`: "
                    f"{f['count']} of {f['max_for_ticker']} ({f['ratio']:.0%})"
                    + (f" -- `python explore_tags.py {f['ticker']} {f['hint']}`" if f["hint"] else "")
                )
            lines.append("")

    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def run_full_refresh():
    run_start = datetime.now()

    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(FIGURE_DIR, exist_ok=True)

    active_tickers = get_active_tickers()
    print(f"Full refresh: {len(active_tickers)} active tickers.")

    deleted = delete_cached_facts(active_tickers)
    print(f"Deleted {len(deleted)} cached company-facts files.")

    # --- Phase 1: EDGAR fetch, timed per ticker ---
    mapping = fetch_or_cache(
        url="https://www.sec.gov/files/company_tickers.json",
        cache_path="cache/ticker_mapping.json",
        headers={"User-Agent": EDGAR_USER_AGENT},
    )
    cik_mapping = build_ticker_to_cik(mapping)

    edgar_times = {}
    facts_frames = []
    for ticker in active_tickers:
        t0 = time.perf_counter()
        concept_candidates = get_concept_candidates(ticker)
        cik = get_cik(ticker, cik_mapping)
        company_info = get_company_info(ticker, cik, EDGAR_USER_AGENT)
        facts_frames.append(build_dataframe(ticker, company_info, concept_candidates, period=PERIOD))
        edgar_times[ticker] = time.perf_counter() - t0
    print(f"EDGAR fetch done: {sum(edgar_times.values()):.1f}s total.")

    facts = pd.concat(facts_frames, ignore_index=True)
    facts["end"] = pd.to_datetime(facts["end"]).astype("datetime64[ns]")
    facts = normalize_split_adjusted(facts, ["SharesOutstanding"])

    quality_flags = []
    expected_by_ticker = {ticker: get_expected_concepts(ticker) for ticker in active_tickers}
    print_data_quality(facts, expected_by_ticker, SEARCH_HINTS, collect_flags=quality_flags)

    # --- Phase 2: yfinance fetch, timed per ticker ---
    yfinance_times = {}
    price_frames = []
    current_price_rows = []
    for ticker in active_tickers:
        t0 = time.perf_counter()
        history = get_price_history(ticker)
        price_frames.append(history)
        data = get_current_price_and_shares(ticker)
        data["ticker"] = ticker
        current_price_rows.append(data)
        yfinance_times[ticker] = time.perf_counter() - t0
    print(f"yfinance fetch done: {sum(yfinance_times.values()):.1f}s total.")

    price_history = pd.concat(price_frames, ignore_index=True)
    price_history["date"] = price_history["date"].dt.tz_localize(None).astype("datetime64[ns]")
    prices = pd.DataFrame(current_price_rows)
    prices["market_cap"] = prices["price"] * prices["shares_outstanding"]

    # --- Phase 3: calculate (batch) + plot (per ticker) ---
    t0 = time.perf_counter()
    facts = add_derived_concepts(facts)
    facts = add_quarterly_derived_concepts(facts)
    metrics = calculate_all_metrics(facts)
    quarterly_metrics = calculate_quarterly_metrics(facts)
    facts = add_as_concept(facts, metrics["fcf"], "fcf", "FCF_TTM")
    facts = add_as_concept(facts, metrics["ebitda"], "ebitda", "EBITDA_TTM")
    facts = add_as_concept(facts, quarterly_metrics["fcf_quarterly"], "fcf_quarterly", "FCF_QUARTERLY")
    facts = add_as_concept(facts, quarterly_metrics["ebitda_quarterly"], "ebitda_quarterly", "EBITDA_QUARTERLY")

    duplicates = facts[facts.duplicated(subset=["ticker", "concept", "end"], keep=False)]
    if not duplicates.empty:
        print(f"WARNUNG: {len(duplicates)} Duplikate gefunden!")

    metrics_long = build_metrics_long(metrics, quarterly_metrics)
    valuation_history = build_valuation_history(facts, price_history, prices)
    _, rolling_pe = calculate_historical_pe(facts, price_history)
    snapshot = build_snapshot(facts, metrics, prices, rolling_pe)
    calc_time = time.perf_counter() - t0

    metrics_long = filter_hidden_rows(metrics_long)
    valuation_history = filter_hidden_rows(valuation_history)
    facts_out = filter_hidden_rows(facts)
    snapshot = filter_hidden_rows(snapshot)

    facts_out = add_growth_column(facts_out)

    facts_out.to_csv(os.path.join(DATA_DIR, f"{PERIOD}_facts.csv"), index=False)
    metrics_long.to_csv(os.path.join(DATA_DIR, "metrics_long.csv"), index=False)
    valuation_history.to_csv(os.path.join(DATA_DIR, "valuation_history.csv"), index=False)
    snapshot.to_csv(os.path.join(DATA_DIR, "current_snapshot.csv"), index=False)

    plot_times = {}
    for ticker in active_tickers:
        t0 = time.perf_counter()
        plot_fundamentals(ticker, metrics_long, os.path.join(FIGURE_DIR, f"{ticker}_fundamentals.png"))
        plot_valuation(ticker, valuation_history, os.path.join(FIGURE_DIR, f"{ticker}_valuation.png"))
        plot_growth(ticker, facts_out, os.path.join(FIGURE_DIR, f"{ticker}_growth.png"))
        plot_times[ticker] = time.perf_counter() - t0
    print(f"Calculate + plot done: {calc_time + sum(plot_times.values()):.1f}s total.")

    run_end = datetime.now()

    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "full_refresh_report.md")
    write_full_refresh_report(
        report_path, run_start, run_end, active_tickers, deleted,
        edgar_times, yfinance_times, calc_time, plot_times, quality_flags,
    )
    print(f"Full refresh complete. Report: {report_path}")


if __name__ == "__main__":
    main()