from fetchers.edgar import (
    fetch_or_cache,
    build_ticker_to_cik,
    get_cik,
    get_company_info,
    get_submissions,
    get_latest_filed_period,
)
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
    HARMONIC_MEAN_CONCEPTS,
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
    calculate_rolling_harmonic_stats,
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
from figures import (plot_fundamentals, plot_valuation, plot_growth)
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


MIN_BUYBACK_EQUITY_QOQ_DECLINE = 0.15
BUYBACK_QOQ_GAP_DAYS = (60, 120)


def calculate_buyback_distortion_flag(facts: pd.DataFrame) -> pd.DataFrame:

    se = facts[facts["concept"] == "StockholdersEquity"][["ticker", "end", "value"]].rename(columns={"value": "equity"})
    ni = facts[facts["concept"] == "NetIncomeLoss_TTM"][["ticker", "end", "value"]].rename(columns={"value": "ni_ttm"})

    se = se.sort_values(["ticker", "end"])
    se["prev_equity"] = se.groupby("ticker")["equity"].shift(1)
    se["prev_end"] = se.groupby("ticker")["end"].shift(1)
    gap_days = (se["end"] - se["prev_end"]).dt.days
    # computed as columns on `se` itself (not free-standing Series) so they survive the merge
    # below row-for-row instead of being re-aligned against merged's fresh RangeIndex.
    se["_applicable"] = gap_days.between(*BUYBACK_QOQ_GAP_DAYS) & (se["equity"] > 0) & (se["prev_equity"] > 0)
    se["_qoq_decline"] = 1 - se["equity"] / se["prev_equity"]

    merged = se.merge(ni, on=["ticker", "end"], how="left")
    profitable = merged["ni_ttm"] > 0

    raw_flag = (merged["_qoq_decline"] > MIN_BUYBACK_EQUITY_QOQ_DECLINE) & profitable
    merged["buyback_distortion_flag"] = raw_flag.astype(float).where(merged["_applicable"])

    return merged[["ticker", "end", "buyback_distortion_flag"]].dropna(subset=["buyback_distortion_flag"])


def _qoq_change(facts: pd.DataFrame, concept: str, value_name: str) -> pd.DataFrame:
    """Consecutive-quarter change in `concept`, with the same gap-days sanity restriction
    calculate_buyback_distortion_flag() uses -- shared so the two guards can't disagree about
    what "quarter over quarter" means. Change columns live on the frame (not free-standing
    Series) so they survive a later merge row-for-row; see the buyback flag for why."""
    sub = facts[facts["concept"] == concept][["ticker", "end", "value"]].rename(columns={"value": value_name})
    sub = sub.sort_values(["ticker", "end"])
    sub[f"prev_{value_name}"] = sub.groupby("ticker")[value_name].shift(1)
    prev_end = sub.groupby("ticker")["end"].shift(1)
    sub["_gap_ok"] = (sub["end"] - prev_end).dt.days.between(*BUYBACK_QOQ_GAP_DAYS)
    return sub


MIN_GOODWILL_QOQ_GROWTH = 0.20


def calculate_inorganic_flag(facts: pd.DataFrame) -> pd.DataFrame:
    """Flags periods where Goodwill jumped >MIN_GOODWILL_QOQ_GROWTH quarter-over-quarter --
    i.e. an acquisition closed, so growth rates spanning that period are inorganic (M&A-driven)
    rather than organic. Mirrors calculate_buyback_distortion_flag()'s mechanism exactly.

    Requires a positive prior Goodwill base: a company going 0 -> anything is an infinite
    percentage change, and "first ever acquisition" is already visible as the goodwill line
    appearing at all. Threshold calibrated in the report -- 20% sits far out in the tail of the
    real QoQ goodwill-change distribution, which is overwhelmingly ~0 (goodwill is static
    between deals, moving only on impairment or FX).
    """
    gw = _qoq_change(facts, "Goodwill", "goodwill")
    gw["_applicable"] = gw["_gap_ok"] & (gw["prev_goodwill"] > 0)
    growth = gw["goodwill"] / gw["prev_goodwill"] - 1
    gw["inorganic_contaminated"] = (growth > MIN_GOODWILL_QOQ_GROWTH).astype(float).where(gw["_applicable"])
    return gw[["ticker", "end", "inorganic_contaminated"]].dropna(subset=["inorganic_contaminated"])


MIN_SHARE_COUNT_QOQ_CHANGE = 0.15
MIN_CORROBORATING_EQUITY_FLOW_RATIO = 0.5


def calculate_share_count_jump_flag(facts: pd.DataFrame) -> pd.DataFrame:
    """Flags periods where SharesOutstanding moved >MIN_SHARE_COUNT_QOQ_CHANGE QoQ with no
    buyback or issuance of comparable size to explain it -- i.e. the share count itself is
    suspect (tag switch, split not caught by normalize_split_adjusted, class-mix change),
    not a real corporate action. Informational, like buyback_distortion_flag: it does not mask.

    "Comparable size" is deliberately loose (>=50% of the implied value of the share change at
    that quarter's own implied price): buyback/issuance cash flows and share-count deltas never
    reconcile exactly (options exercise, RSU vesting, ASR timing), so demanding tight agreement
    would flag everything.

    Note on coverage, measured before building this: PaymentsForRepurchaseOfCommonStock exists
    for 96.2% of active tickers but ProceedsFromIssuanceOfCommonStock only 54.6%. A missing
    issuance tag is therefore treated as "no corroboration available" rather than "no issuance
    happened" -- which makes the flag conservative in the *reporting* direction (it can flag a
    real issuance whose tag is absent) rather than silently missing suspect share counts.
    """
    shares = _qoq_change(facts, "SharesOutstanding", "shares")
    shares["_applicable"] = shares["_gap_ok"] & (shares["prev_shares"] > 0)
    shares["_abs_change"] = (shares["shares"] / shares["prev_shares"] - 1).abs()
    shares["_share_delta"] = (shares["shares"] - shares["prev_shares"]).abs()

    flows = facts[facts["concept"].isin(["StockRepurchased", "StockIssued"])]
    flows = flows.pivot_table(index=["ticker", "end"], columns="concept", values="value").reset_index()
    for col in ("StockRepurchased", "StockIssued"):
        if col not in flows.columns:
            flows[col] = float("nan")

    merged = shares.merge(flows, on=["ticker", "end"], how="left")

    # implied price for this ticker/quarter, from EDGAR fundamentals only (no yfinance
    # dependency -- this runs inside calculate_all_metrics(), before prices are joined):
    # equity per share is a crude but scale-correct proxy for converting a cash flow into
    # a share count, which is all the "comparable magnitude" test needs.
    equity = facts[facts["concept"] == "StockholdersEquity"][["ticker", "end", "value"]].rename(columns={"value": "equity"})
    merged = merged.merge(equity, on=["ticker", "end"], how="left")
    implied_price = (merged["equity"] / merged["shares"]).abs()

    flow_cash = merged[["StockRepurchased", "StockIssued"]].abs().max(axis=1)
    implied_flow_shares = flow_cash / implied_price.where(implied_price > 0)
    corroborated = implied_flow_shares >= MIN_CORROBORATING_EQUITY_FLOW_RATIO * merged["_share_delta"]

    raw = (merged["_abs_change"] > MIN_SHARE_COUNT_QOQ_CHANGE) & ~corroborated.fillna(False)
    merged["share_count_jump_flag"] = raw.astype(float).where(merged["_applicable"])
    return merged[["ticker", "end", "share_count_jump_flag"]].dropna(subset=["share_count_jump_flag"])


def calculate_fcf_exceeds_ebitda_flag(fcf_df: pd.DataFrame, ebitda_df: pd.DataFrame) -> pd.DataFrame:
    """Flags periods where trailing FCF > trailing EBITDA. Deliberately named for the
    *observation*, not a presumed cause: investigation (see the report) found the driver
    differs by ticker -- stock-based compensation for some, working-capital/deferred-revenue
    builds for others -- so a flag asserting "SBC-driven" would be wrong for a meaningful share
    of cases. Both sides must be positive: when EBITDA is negative the comparison is trivially
    true and says nothing about cash-conversion quality.

    Takes the already-computed fcf/ebitda frames rather than reading FCF_TTM/EBITDA_TTM out of
    `facts`, because those concepts are only injected into facts (via add_as_concept) *after*
    calculate_all_metrics() returns -- reading them here would silently produce nothing.
    """
    merged = fcf_df.merge(ebitda_df, on=["ticker", "end"])
    applicable = (merged["fcf"] > 0) & (merged["ebitda"] > 0)
    merged["fcf_exceeds_ebitda"] = (merged["fcf"] > merged["ebitda"]).astype(float).where(applicable)
    return merged[["ticker", "end", "fcf_exceeds_ebitda"]].dropna(subset=["fcf_exceeds_ebitda"])


MAX_NOL_EFFECTIVE_TAX_RATE = 0.10


def calculate_tax_metrics(facts: pd.DataFrame) -> tuple:
    """effective_tax_rate = IncomeTaxExpense_TTM / PretaxIncome_TTM, plus a low-rate flag.

    Only meaningful for profitable periods, so a positive pretax denominator is required
    (`require_positive_denominator`): a loss-making quarter produces a tax *benefit* over
    negative pretax income, whose ratio is arithmetically positive but means the opposite of
    a low tax burden. The same MIN_DENOMINATOR_SCALE_RATIO guard used for roe protects against
    a near-break-even pretax base exploding the rate.
    """
    rate = calculate_ratio(
        facts, "IncomeTaxExpense_TTM", "PretaxIncome_TTM", "effective_tax_rate",
        require_positive_denominator=True,
        min_denominator_scale_ref="Revenue_TTM",
        min_denominator_scale_ratio=MIN_DENOMINATOR_SCALE_RATIO,
    )
    flag = rate.dropna(subset=["effective_tax_rate"]).copy()
    flag["low_tax_rate_flag"] = (flag["effective_tax_rate"] < MAX_NOL_EFFECTIVE_TAX_RATE).astype(float)
    return rate, flag[["ticker", "end", "low_tax_rate_flag"]]


def calculate_all_metrics(facts: pd.DataFrame) -> dict:
    m = {}

    m["buyback_distortion_flag"] = calculate_buyback_distortion_flag(facts)
    m["inorganic_contaminated"] = calculate_inorganic_flag(facts)
    m["share_count_jump_flag"] = calculate_share_count_jump_flag(facts)
    m["effective_tax_rate"], m["low_tax_rate_flag"] = calculate_tax_metrics(facts)

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
    m["fcf_exceeds_ebitda"] = calculate_fcf_exceeds_ebitda_flag(m["fcf"], m["ebitda"])

    # owner_fcf: FCF with stock-based compensation treated as the real economic cost it is,
    # rather than an add-back. Inner-joins on SBC availability by construction, so a ticker
    # missing the tag gets no owner_fcf rather than a silently SBC-free (= overstated) one.
    # Built from m["fcf"] rather than a facts lookup for the same reason as
    # calculate_fcf_exceeds_ebitda_flag(): FCF_TTM isn't in facts yet at this point.
    sbc_ttm_rows = facts[facts["concept"] == "ShareBasedCompensation_TTM"][["ticker", "end", "value"]].rename(
        columns={"value": "sbc_ttm"}
    )
    m["owner_fcf"] = calculate_difference_from_dfs(
        m["fcf"], sbc_ttm_rows, "fcf", "sbc_ttm", "owner_fcf"
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
        (metrics["buyback_distortion_flag"], "buyback_distortion_flag", "buyback_distortion_flag"),
        (metrics["inorganic_contaminated"], "inorganic_contaminated", "inorganic_contaminated"),
        (metrics["share_count_jump_flag"], "share_count_jump_flag", "share_count_jump_flag"),
        (metrics["fcf_exceeds_ebitda"], "fcf_exceeds_ebitda", "fcf_exceeds_ebitda"),
        (metrics["effective_tax_rate"], "effective_tax_rate", "effective_tax_rate"),
        (metrics["low_tax_rate_flag"], "low_tax_rate_flag", "low_tax_rate_flag"),
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


AVG_5Y_WINDOW = 20
MIN_AVG_5Y_DIVERGENCE = 0.20   # calibrated below, in build_snapshot()'s divergence flag
MIN_AVG_5Y_OBSERVATIONS = 12   # 3 of the 5 nominal years; see build_snapshot()'s history_too_short

# Naming for each in-scope multiple's rolling 5y reference field, generalizing the original
# PE-only "avg_pe_5y" (built by the now-removed calculate_historical_pe()) to every multiple in
# HARMONIC_MEAN_CONCEPTS. pe_ratio keeps its original name for backward compatibility with
# existing consumers of the snapshot CSV.
AVG_5Y_FIELD_NAMES = {
    "pe_ratio": "avg_pe_5y",
    "pfcf_ratio": "avg_pfcf_5y",
    "ev_ebitda": "avg_ev_ebitda_5y",
    "p_tbv": "avg_p_tbv_5y",
    "p_ppnr": "avg_p_ppnr_5y",
    "p_core_earnings": "avg_p_core_earnings_5y",
    "p_ffo": "avg_p_ffo_5y",
}


def calculate_rolling_multiple_averages(valuation_history: pd.DataFrame) -> pd.DataFrame:
    """Rolling 20-observation harmonic mean + median for every multiple in
    HARMONIC_MEAN_CONCEPTS, replacing the old PE-only arithmetic calculate_historical_pe().
    Sourced from build_valuation_history()'s already denominator-guarded series (not
    recomputed from raw facts), so this can't drift from the guards already applied there.
    Returns one row per (ticker, end) any in-scope concept has a value at (outer-merged, so a
    date where one multiple was itself masked doesn't drop the others) -- build_snapshot()
    collapses each concept's own columns to its own latest independently, the same
    "each field is as fresh as its own last available point" pattern as every other
    get_latest_value()/get_latest_row() call there.
    """
    wide = None
    for concept in sorted(HARMONIC_MEAN_CONCEPTS):
        field = AVG_5Y_FIELD_NAMES[concept]
        series = valuation_history[valuation_history["concept"] == concept][["ticker", "end", "value"]]
        if series.empty:
            continue
        stats = calculate_rolling_harmonic_stats(series, "value", AVG_5Y_WINDOW, field)
        wide = stats if wide is None else wide.merge(stats, on=["ticker", "end"], how="outer")
    return wide if wide is not None else pd.DataFrame(columns=["ticker", "end"])


MIN_PEER_GROUP_SIZE = 5
PEER_BAND_WINDOW_YEARS = 5


def calculate_peer_band_flags(valuation_history: pd.DataFrame) -> pd.DataFrame:
    """historical_band_elevated: a ticker sitting near its OWN 5-year low for a multiple, while
    that low is still above the median of what its peers trade at today.

    Design choices, both real and worth stating:

    1. "Peer" = profile-mate (TICKER_PROFILES). That assignment already encodes this project's
       structural view of which companies are economically comparable -- it is what drives which
       metrics are even shown per sector -- so reusing it keeps one definition of comparability
       instead of inventing a second one. Profiles smaller than MIN_PEER_GROUP_SIZE are skipped
       entirely: a "median" over 1-2 peers (alt_asset_manager, homebuilder, airline) is not a
       sector level, it's noise, and flagging against it would be worse than not flagging.

    2. The peer median is taken over each peer's OWN most recent value, not a strict same-date
       cross-section. Fiscal calendars differ across a profile, so a same-date cross-section
       would silently drop most peers on most dates; "what do comparable companies trade at
       right now" is also the question an investor actually asks. The cost is that peers are
       aligned to within a quarter of each other rather than exactly -- acceptable for a
       median, and stated rather than hidden.

    Only the multiples already in HARMONIC_MEAN_CONCEPTS are covered: those are the price/flow
    multiples where "cheap vs expensive" is directionally meaningful in the first place.
    """
    profiles = valuation_history["ticker"].map(lambda t: TICKER_PROFILES.get(t, DEFAULT_PROFILE))
    vh = valuation_history.assign(profile=profiles)
    cutoff = pd.Timestamp.today() - pd.DateOffset(years=PEER_BAND_WINDOW_YEARS)
    window = vh[(vh["end"] >= cutoff) & (vh["value"] > 0)]

    out = []
    for concept in sorted(HARMONIC_MEAN_CONCEPTS):
        sub = window[window["concept"] == concept]
        if sub.empty:
            continue
        own_low = sub.groupby(["ticker", "profile"])["value"].min().rename("own_5y_low").reset_index()
        latest = sub.loc[sub.groupby("ticker")["end"].idxmax(), ["ticker", "value"]].rename(
            columns={"value": "latest"}
        )
        own_low = own_low.merge(latest, on="ticker", how="left")

        sizes = own_low.groupby("profile")["ticker"].transform("size")
        peer_median = own_low.groupby("profile")["latest"].transform("median")
        eligible = sizes >= MIN_PEER_GROUP_SIZE

        flag = (own_low["own_5y_low"] > peer_median).astype(float).where(eligible)
        res = own_low[["ticker"]].copy()
        res["concept"] = f"{concept}_band_elevated"
        res["value"] = flag
        out.append(res.dropna(subset=["value"]))

    if not out:
        return pd.DataFrame(columns=["ticker", "concept", "value"])
    return pd.concat(out, ignore_index=True)


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
        "FFO_TTM",
        "ShareBasedCompensation_TTM",
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
    wide["ev_fcf"] = wide["ev"] / wide["FCF_TTM"].where(wide["FCF_TTM"] > 0)
    # owner FCF = FCF net of stock-based compensation; NaN wherever SBC isn't tagged, so a
    # ticker without the tag gets no pfcf_ex_sbc rather than one silently equal to pfcf_ratio.
    wide["owner_fcf"] = wide["FCF_TTM"] - wide["ShareBasedCompensation_TTM"]
    wide["pfcf_ex_sbc"] = wide["market_cap"] / wide["owner_fcf"].where(wide["owner_fcf"] > 0)
    wide["ev_ebitda"] = wide["ev"] / wide["EBITDA_TTM"].where(wide["EBITDA_TTM"] > 0)
    wide["ev_sales"] = wide["ev"] / wide["Revenue_TTM"].where(wide["Revenue_TTM"] > 0)
    wide["dividend_yield"] = (wide["DividendsPerShare_TTM"].where(wide["DividendsPerShare_TTM"] >= 0) / wide["close"])

    # tangible_book: this project already computes StockholdersEquity - Goodwill as
    # "TangibleEquity" for p_tbv -- no separate intangibles-net-of-goodwill concept exists
    # anywhere in CONCEPT_CANDIDATES project-wide (checked directly), so tangible_book IS
    # TangibleEquity, not a second parallel field. A negative tangible book makes P/B on a
    # tangible basis undefined, so pb_ratio (the ordinary, goodwill-inclusive P/B) is hidden
    # for that ticker/period -- data-triggered visibility, independent of the scale guard above.
    wide["pb_ratio"] = wide["pb_ratio"].where(~(wide["TangibleEquity"] < 0))

    wide["p_tbv"] = wide["market_cap"] / wide["TangibleEquity"].where(wide["TangibleEquity"] > 0)
    wide["p_ppnr"] = wide["market_cap"] / wide["PPNR"].where(wide["PPNR"] > 0)
    wide["p_core_earnings"] = wide["market_cap"] / wide["CoreOperatingEarnings"].where(wide["CoreOperatingEarnings"] > 0)
    wide["p_ffo"] = wide["market_cap"] / wide["FFO_TTM"].where(wide["FFO_TTM"] > 0)

    implied_earnings_ttm = wide["EPS_TTM_CALC"] * shares_for_market_cap
    for col, denominator in [
        ("pe_ratio", implied_earnings_ttm),
        ("pb_ratio", wide["StockholdersEquity"]),
        ("pfcf_ratio", wide["FCF_TTM"]),
        ("ev_fcf", wide["FCF_TTM"]),
        ("pfcf_ex_sbc", wide["owner_fcf"]),
        ("ev_ebitda", wide["EBITDA_TTM"]),
        ("p_tbv", wide["TangibleEquity"]),
        ("p_ppnr", wide["PPNR"]),
        ("p_core_earnings", wide["CoreOperatingEarnings"]),
        ("p_ffo", wide["FFO_TTM"]),
    ]:
        wide[col] = apply_denominator_scale_guard(
            wide[col], denominator, wide["Revenue_TTM"], MIN_VALUATION_DENOMINATOR_SCALE_RATIO
        )

    wide["pe_to_revenue_growth"] = wide["pe_ratio"] / (wide["revenue_yoy_growth"] * 100)
    wide["pe_to_revenue_growth"] = wide["pe_to_revenue_growth"].where(wide["revenue_yoy_growth"] > MIN_PEG_REVENUE_GROWTH)
    wide["pe_to_revenue_growth"] = wide["pe_to_revenue_growth"].where(wide["pe_to_revenue_growth"].abs() <= MAX_PEG_RATIO_ABS)

    # single implementation shared with build_metrics_long()'s roe-adjacent flag -- see
    # calculate_buyback_distortion_flag() for the calibration reasoning.
    wide = wide.merge(calculate_buyback_distortion_flag(facts), on=["ticker", "end"], how="left")

    value_cols = ["pe_ratio", "pb_ratio", "pfcf_ratio", "ev_fcf", "pfcf_ex_sbc", "ev_ebitda", "ev_sales", "dividend_yield", "p_tbv", "p_ppnr", "p_core_earnings", "pe_to_revenue_growth", "p_ffo", "buyback_distortion_flag"]

    long = wide.melt(
        id_vars=["ticker", "end"],
        value_vars=value_cols,
        var_name="concept",
        value_name="value",
    )

    return long.dropna(subset=["value"])

MIN_SHARE_COUNT_DISAGREEMENT = 0.10
MIN_YF_SHARE_OVERSTATEMENT = 1.50
MAX_EDGAR_SHARE_LAG_DAYS = 200   # ~two quarters: one missed filing is tolerable, five years isn't


def _resolve_share_sources(facts: pd.DataFrame, prices: pd.DataFrame) -> tuple:
    """The edgar/yfinance share counts, the prefer_edgar decision, and the % delta between
    them -- the single implementation both resolve_snapshot_share_count() and build_snapshot()'s
    shares_source_is_edgar/shares_delta_pct columns are built from, so the two can't drift."""
    yf_shares = prices["shares_outstanding"]

    edgar_latest = get_latest_value(facts, "SharesOutstanding")[["ticker", "value", "end"]]
    edgar_shares = prices["ticker"].map(edgar_latest.set_index("ticker")["value"])

    # EDGAR-larger: the original dual-class/stale-yfinance case.
    edgar_larger = (edgar_shares / yf_shares > 1 + MIN_SHARE_COUNT_DISAGREEMENT)

    # yfinance-larger by a gross factor: the opposite failure (KLAC/CRWD/DVN, where yfinance
    # overstates by ~9.9x/3.9x/1.9x). Deliberately NOT the 1.10 rule inverted -- the real
    # negative-delta distribution doesn't separate at 1.10. Measured across all 495 tickers
    # with both sources, the yfinance/edgar ratios above 1.0 run
    # 9.91, 3.95, 1.87 | 1.23, 1.12, 1.09, 1.06, 1.06, 1.05 ... continuously down to 1.0;
    # the only wide gap sits between 1.87 and 1.12 once BKR (1.23) is excluded as stale below.
    # MIN_YF_SHARE_OVERSTATEMENT sits in that gap: the three above it are off by near-integer
    # factors (a units/split error on yfinance's side), while everything below is ordinary
    # definitional drift that switching source would not improve.
    yf_grossly_larger = (yf_shares / edgar_shares > MIN_YF_SHARE_OVERSTATEMENT)

    # ...but only when EDGAR's own share count is current. BKR's newest SharesOutstanding fact
    # is 2021-06-30 while its newest fact of any kind is 2026-06-30 -- there, yfinance is right
    # and EDGAR is five years stale, so preferring EDGAR would make market_cap worse, not
    # better. Staleness is measured against the ticker's own newest fact rather than today's
    # date, so a ticker whose whole payload lags (the SEC-aggregation case handled elsewhere)
    # isn't punished twice.
    newest_any = facts.groupby("ticker")["end"].max()
    shares_end = prices["ticker"].map(edgar_latest.set_index("ticker")["end"])
    shares_lag_days = (prices["ticker"].map(newest_any) - shares_end).dt.days
    edgar_shares_current = shares_lag_days <= MAX_EDGAR_SHARE_LAG_DAYS

    usable = edgar_shares.notna() & yf_shares.notna() & (yf_shares > 0) & (edgar_shares > 0)
    prefer_edgar = usable & (edgar_larger | (yf_grossly_larger & edgar_shares_current))

    delta_pct = (edgar_shares - yf_shares) / yf_shares * 100
    return edgar_shares, yf_shares, prefer_edgar, delta_pct


def resolve_snapshot_share_count(facts: pd.DataFrame, prices: pd.DataFrame) -> pd.Series:
    """Share count for build_snapshot()'s market_cap, indexed like `prices`."""
    edgar_shares, yf_shares, prefer_edgar, _ = _resolve_share_sources(facts, prices)
    return edgar_shares.where(prefer_edgar, yf_shares)


def build_snapshot(
    facts: pd.DataFrame,
    metrics: dict,
    prices: pd.DataFrame,
    rolling_multiples: pd.DataFrame,
    as_of: "str | pd.Timestamp | None" = None,
    peer_band_flags: "pd.DataFrame | None" = None,
) -> pd.DataFrame:

    as_of_date = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp(date.today())

    snap = prices.copy()
    # Resolved ONCE, off the untouched `prices`, and reused for both the share count and the
    # two audit columns. Calling _resolve_share_sources() again against `snap` after
    # overwriting snap["shares_outstanding"] would compare EDGAR to the already-resolved
    # count instead of to yfinance's original -- reporting a 0% delta and source="yfinance"
    # for exactly the tickers that did switch.
    edgar_shares, yf_shares, prefer_edgar, shares_delta_pct = _resolve_share_sources(facts, prices)
    snap["shares_outstanding"] = edgar_shares.where(prefer_edgar, yf_shares)
    snap["market_cap"] = snap["price"] * snap["shares_outstanding"]
    snap["shares_source_is_edgar"] = prefer_edgar.astype(float)
    snap["shares_delta_pct"] = shares_delta_pct

    eps = get_latest_value(facts, "EPS_TTM_CALC").rename(columns={"value": "eps_ttm"})
    revenue = get_latest_value(facts, "Revenue_TTM").rename(columns={"value": "revenue_ttm"})
    dividends = get_latest_value(facts, "DividendsPerShare_TTM").rename(columns={"value": "dividends_ttm"})

    fcf = get_latest_row(metrics["fcf"]).rename(columns={"fcf": "fcf_ttm"})
    ebitda = get_latest_row(metrics["ebitda"]).rename(columns={"ebitda": "ebitda_ttm"})

    equity = get_latest_value(facts, "StockholdersEquity").rename(columns={"value": "equity"})
    debt = get_latest_value(facts, "LongTermDebt").rename(columns={"value": "debt"})
    cash = get_latest_value(facts, "CashAndEquivalents").rename(columns={"value": "cash"})

    growth = get_latest_row(metrics["revenue_growth"])

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

    # Rolling 5y harmonic-mean reference + median, collapsed to each multiple's OWN latest
    # available point independently (not a single shared "latest end" across all multiples --
    # see calculate_rolling_multiple_averages()), plus a divergence flag calibrated from real
    # data: 0.20 sits at ~p90 of the observed |harmonic-median|/median distribution across the
    # in-scope multiples (~9% of ticker-concept pairs flagged), a deliberately selective,
    # tail-focused signal rather than routine noise.
    for concept in HARMONIC_MEAN_CONCEPTS:
        field = AVG_5Y_FIELD_NAMES[concept]
        median_field = f"{field}_median"
        count_field = f"{field}_n"
        cols = ["ticker", "end", field, median_field, count_field]
        sub = rolling_multiples[cols].dropna(subset=[field]) if field in rolling_multiples.columns else pd.DataFrame(columns=cols)
        if sub.empty:
            continue
        latest = get_latest_row(sub)
        diverges = (latest[field] - latest[median_field]).abs() / latest[median_field]
        latest[f"{field}_diverges"] = (diverges > MIN_AVG_5Y_DIVERGENCE).astype(float)
        # A "5-year average" built from a handful of quarters is formally valid and
        # substantively meaningless -- calculate_rolling_harmonic_stats() uses min_periods=1,
        # so a just-IPO'd ticker gets a number from as little as one observation. This marks
        # those, without masking (a short-history average is still the best available anchor,
        # it just shouldn't be read as a 5-year norm).
        latest[f"{field}_history_too_short"] = (latest[count_field] < MIN_AVG_5Y_OBSERVATIONS).astype(float)
        snap = pd.merge(
            snap,
            latest[["ticker", field, median_field, f"{field}_diverges",
                    f"{field}_history_too_short"]],
            on="ticker", how="left",
        )

    snap["net_debt"] = snap["debt"] - snap["cash"]
    snap["ev"] = snap["market_cap"] + snap["net_debt"]

    snap["pe_ttm"] = snap["price"] / snap["eps_ttm"]
    snap["pb_ratio"] = apply_denominator_scale_guard(
        snap["market_cap"] / snap["equity"], snap["equity"], snap["revenue_ttm"], MIN_DENOMINATOR_SCALE_RATIO
    )
    # tangible_book == tangible_equity (see build_valuation_history()); a negative tangible
    # book makes P/B on a tangible basis undefined, so hide the ordinary P/B for that ticker.
    snap["pb_ratio"] = snap["pb_ratio"].where(~(snap["tangible_equity"] < 0))
    snap["pfcf_ttm"] = snap["market_cap"] / snap["fcf_ttm"]
    snap["ev_ebitda"] = snap["ev"] / snap["ebitda_ttm"]
    snap["ev_sales"] = snap["ev"] / snap["revenue_ttm"]
    # see build_valuation_history() for why this is revenue growth and renamed, not recomputed
    snap["pe_to_revenue_growth"] = snap["pe_ttm"].where(snap["pe_ttm"] > 0) / (snap["yoy_growth"] * 100)
    snap["pe_to_revenue_growth"] = snap["pe_to_revenue_growth"].where(snap["yoy_growth"] > MIN_PEG_REVENUE_GROWTH)
    snap["pe_to_revenue_growth"] = snap["pe_to_revenue_growth"].where(snap["pe_to_revenue_growth"].abs() <= MAX_PEG_RATIO_ABS)
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

    if peer_band_flags is not None and not peer_band_flags.empty:
        bands = peer_band_flags.copy()
        bands["end"] = as_of_date
        long = pd.concat([long, bands[["ticker", "end", "concept", "value"]]], ignore_index=True)

    return long[["ticker", "end", "concept", "value"]]


STALENESS_DAYS_FALLBACK = 135


def add_staleness_fields(
    snapshot: pd.DataFrame,
    facts: pd.DataFrame,
    latest_filed_periods: dict | None = None,
    as_of: "str | pd.Timestamp | None" = None,
) -> pd.DataFrame:

    as_of_date = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp(date.today())

    newest = facts.groupby("ticker")["end"].max().rename("newest_end").reset_index()
    newest["days_since_last_filing"] = (as_of_date - newest["newest_end"]).dt.days

    if latest_filed_periods:
        published = newest["ticker"].map(
            {t: pd.Timestamp(p) for t, p in latest_filed_periods.items() if p}
        )
        stale = published.notna() & (published > newest["newest_end"])
        # a ticker with no submissions entry still gets the date-based answer
        stale = stale.where(published.notna(),
                            newest["days_since_last_filing"] > STALENESS_DAYS_FALLBACK)
    else:
        stale = newest["days_since_last_filing"] > STALENESS_DAYS_FALLBACK

    newest["fundamentals_stale"] = stale.astype(float)

    extra = newest.melt(
        id_vars=["ticker"],
        value_vars=["days_since_last_filing", "fundamentals_stale"],
        var_name="concept",
        value_name="value",
    )
    extra["end"] = as_of_date
    return pd.concat([snapshot, extra[["ticker", "end", "concept", "value"]]], ignore_index=True)


def load_latest_filed_periods(tickers: list[str]) -> dict:
    mapping = fetch_or_cache(
        url="https://www.sec.gov/files/company_tickers.json",
        cache_path="cache/ticker_mapping.json",
        headers={"User-Agent": EDGAR_USER_AGENT},
    )
    cik_mapping = build_ticker_to_cik(mapping)

    periods = {}
    for ticker in tickers:
        try:
            submissions = get_submissions(ticker, get_cik(ticker, cik_mapping), EDGAR_USER_AGENT)
            periods[ticker] = get_latest_filed_period(submissions)
        except Exception:
            periods[ticker] = None
    return periods


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
    rolling_multiples: pd.DataFrame,
) -> pd.DataFrame:
    cutoff_date = pd.Timestamp(cutoff_date)

    facts_cut = facts[facts["end"] <= cutoff_date]
    metrics_cut = {k: df[df["end"] <= cutoff_date] for k, df in metrics.items()}
    rolling_multiples_cut = rolling_multiples[rolling_multiples["end"] <= cutoff_date]

    prices_cut = get_price_as_of(price_history, cutoff_date)
    shares = get_latest_value(facts_cut, "SharesOutstanding").rename(
        columns={"value": "shares_outstanding"}
    )
    prices_cut = pd.merge(prices_cut, shares[["ticker", "shares_outstanding"]], on="ticker", how="left")
    prices_cut["market_cap"] = prices_cut["price"] * prices_cut["shares_outstanding"]

    return build_snapshot(facts_cut, metrics_cut, prices_cut, rolling_multiples_cut, as_of=cutoff_date)


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
    rolling_multiples = calculate_rolling_multiple_averages(valuation_history)
    peer_bands = calculate_peer_band_flags(valuation_history)
    snapshot = build_snapshot(facts, metrics, prices, rolling_multiples, peer_band_flags=peer_bands)
    snapshot = add_staleness_fields(snapshot, facts, load_latest_filed_periods(TICKERS))




    for cutoff in SNAPSHOT_AS_OF_DATES:
        hist_snapshot = build_snapshot_as_of(cutoff, facts, metrics, price_history, rolling_multiples)
        hist_snapshot = filter_hidden_rows(hist_snapshot)

        print(f"\n--- Snapshot as of {cutoff} ---")
        print(price_summary(hist_snapshot))
        print(f"\n-------------------------------")

        hist_snapshot.to_csv(os.path.join(DATA_DIR, f"snapshot_as_of_{cutoff}.csv"), index=False)



    metrics_long = filter_hidden_rows(metrics_long)
    valuation_history = filter_hidden_rows(valuation_history)
    facts = filter_hidden_rows(facts)
    snapshot = filter_hidden_rows(snapshot)

    facts = add_growth_column(facts)

    snapshot.sort_values(by=["ticker", "concept"], inplace=True)
    valuation_history.sort_values(by=["ticker", "concept"], inplace=True)
    metrics_long.sort_values(by=["ticker", "concept"], inplace=True)
    facts.sort_values(by=["ticker", "concept"], inplace=True)

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
        for name in (f"{ticker}_company_info.json", f"{ticker}_submissions.json",
                     f"{ticker}_cache_meta.json"):
            path = os.path.join(CACHE_DIR, name)
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
    rolling_multiples = calculate_rolling_multiple_averages(valuation_history)
    peer_bands = calculate_peer_band_flags(valuation_history)
    snapshot = build_snapshot(facts, metrics, prices, rolling_multiples, peer_band_flags=peer_bands)
    snapshot = add_staleness_fields(snapshot, facts, load_latest_filed_periods(active_tickers))
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