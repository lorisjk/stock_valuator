TICKERS = ["TRV"]

EDGAR_USER_AGENT = "Loris loris2006@gmx.de"

PERIOD = "quarterly"

SNAPSHOT_AS_OF_DATES = []  

CONCEPT_CANDIDATES = {
    "Revenue": {
        "tags": [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
            "SalesRevenueGoodsNet",
            "RevenueFromContractWithCustomerIncludingAssessedTax",
        ],
        "point_in_time": False,
        "mode": "fallback",
    },
    "NetIncomeLoss": {
        "tags": [
            "NetIncomeLoss",
            "NetIncomeLossAvailableToCommonStockholdersBasic"
        ],
        "point_in_time": False,
        "mode": "fallback",
    },

    "SharesOutstanding": {
        "tags": [
            "WeightedAverageNumberOfDilutedSharesOutstanding",
            "WeightedAverageNumberOfSharesOutstandingBasic",
            "CommonStockSharesOutstanding",
        ],
        "point_in_time": True,
        "mode": "fallback",
    },
    "StockholdersEquity": {
        "tags": [
            "StockholdersEquity",
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        ],
        "point_in_time": True,
        "mode": "fallback",
    },
    "OperatingIncomeLoss": {
        "tags": ["OperatingIncomeLoss"],
        "point_in_time": False,
        "mode": "fallback",
    },
    "OperatingCashFlow": {
        "tags": [
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
            "NetCashProvidedByUsedInOperatingActivities",
        ],
        "point_in_time": False,
        "mode": "fallback",
    },
    "Capex": {
        "tags": [
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "PaymentsToAcquireProductiveAssets",
        ],
        "point_in_time": False,
        "mode": "fallback",
    },
   "DepreciationAndAmortization": {
    "sources": [
        {"type": "tag", "tag": "DepreciationDepletionAndAmortization"},
        {"type": "tag", "tag": "DepreciationAndAmortization"},
        {"type": "tag", "tag": "DepreciationAmortizationAndAccretionNet"},
        {"type": "sum", "tags": ["Depreciation", "AmortizationOfIntangibleAssets"]},
        {"type": "tag", "tag": "AdjustmentForAmortization"},
        {"type": "tag", "tag": "FiniteLivedIntangibleAssetsAmortizationExpense"},
    ],
    "point_in_time": False,
    "mode": "priority_merge",
    },
    "LongTermDebt": {
        "sources": [
            {"type": "tag", "tag": "LongTermDebt"},
            {"type": "tag", "tag": "DebtLongtermAndShorttermCombinedAmount"},
            {"type": "tag", "tag": "LongTermNotesAndLoans"},
            {"type": "tag", "tag": "ConvertibleLongTermNotesPayable"},
            {"type": "tag", "tag": "ConvertibleDebtNoncurrent"},
            {"type": "tag", "tag": "ConvertibleDebtCurrent"},
            {"type": "tag", "tag": "ConvertibleNotesPayableCurrent"},
            {"type": "sum", "tags": ["LongTermDebtNoncurrent", "LongTermDebtCurrent", "NotesPayableCurrent"]},
            {"type": "tag", "tag": "LongTermDebtAndCapitalLeaseObligations"},
            {"type": "tag", "tag": "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities"},
            {"type": "tag", "tag": "UnsecuredLongTermDebt"},
        ],
        "point_in_time": True,
        "mode": "priority_merge",
    },

    "CashAndEquivalents": {
        "tags": [
            "CashAndCashEquivalentsAtCarryingValue",
            "CashAndCashEquivalentsAtCarryingValueIncludingDiscontinuedOperations",
        ],
        "point_in_time": True,
        "mode": "fallback",
    },
    "DividendsPerShare": {
        "tags": [
            "CommonStockDividendsPerShareDeclared",
            "CommonStockDividendsPerShareCashPaid",
        ],
        "point_in_time": False,
        "mode": "fallback",
    },
    "Goodwill": {
            "tags": ["Goodwill"],
            "point_in_time": True,
            "mode": "fallback",
        },

}

TTM_CONCEPTS = [
    "Revenue",
    "NetIncomeLoss",
    "OperatingIncomeLoss",
    "OperatingCashFlow",
    "Capex",
    "DepreciationAndAmortization",
    "DividendsPerShare",
    "NetInterestIncome",
    "NoninterestExpense",
    "ProvisionForCreditLosses",
    "NoninterestIncome",
    "EarnedPremiums",
    "IncurredLosses",
    "BenefitsLossesAndExpenses",
    "NetInvestmentIncome",
    "RealizedInvestmentGains",
]

SEARCH_HINTS = {
    "Revenue": ["revenue", "salesrevenue"],
    "NetIncomeLoss": ["netincome"],
    "OperatingIncomeLoss": ["operatingincome"],
    "OperatingCashFlow": ["operatingactivities"],
    "Capex": ["propertyplant", "productiveassets"],
    "DepreciationAndAmortization": ["depreciation", "amortization"],
    "LongTermDebt": ["longtermdebt", "borrowings", "notespayable"],
    "CashAndEquivalents": ["cashandcash"],
    "StockholdersEquity": ["stockholdersequity"],
    "SharesOutstanding": ["sharesoutstanding"],
    "DividendsPerShare": ["dividendspershare"],
    # bank concepts:
    "Assets": ["assets"],
    "NetInterestIncome": ["interestincome", "interestexpensenet"],
    "NoninterestExpense": ["noninterestexpense"],
    "NoninterestIncome": ["noninterestincome"],
    "Goodwill": ["goodwill", "intangible"],
    "ProvisionForCreditLosses": ["provisionforloan", "provisionforcredit"],
    # insurance_pc concepts:
    "EarnedPremiums": ["premiumsearned"],
    "IncurredLosses": ["benefitsandclaims", "policyholderbenefits"],
    "BenefitsLossesAndExpenses": ["benefitslossesandexpenses"],
    "NetInvestmentIncome": ["netinvestmentincome"],
    "Investments": ["investments"],
    "ClaimsReserve": ["liabilityforclaims", "claimsadjustmentexpense"],
}

DEFAULT_PROFILE = "standard"

TICKER_PROFILES = {
    "BAC": "financial",
    "C": "financial",    
    "JPM": "financial",  
    "WFC": "financial",  
    "USB": "financial", 
    "PNC": "financial",  
    "TFC": "financial",  
    "COF": "financial", 
    "FITB": "financial",
    "HBAN": "financial",
    "KEY": "financial",
    "MTB": "financial",
    "RF": "financial",
    "CFG": "financial", 
    "BNY": "financial", 
    "STT": "financial",
    "NTRS": "financial", 
    "SYF": "financial",
    "AXP": "financial",
    "GS": "financial",

    "TRV": "insurance_pc",
    "CB": "insurance_pc",
    "PGR": "insurance_pc",
    "ALL": "insurance_pc",
    "AIG": "insurance_pc",
    "WRB": "insurance_pc",
    "CINF": "insurance_pc",
    "ACGL": "insurance_pc",
    "HIG": "insurance_pc",
    "L": "insurance_pc",
    "EG": "insurance_pc",

    "MET": "insurance_life",
    "PRU": "insurance_life",
    "AFL": "insurance_life",
    "PFG": "insurance_life",
    "GL": "insurance_life",
    "AIZ": "insurance_life",
    "ERIE": "insurance_life",


}

PROFILE_HIDDEN = {
    "standard": {
        "net_interest_margin",
        "efficiency_ratio",
        "p_tbv",
        "roa",
        "equity_to_assets",
        "provision_ratio",
        "p_ppnr", 
        "combined_ratio",
        "loss_ratio",
        "expense_ratio",
        "net_investment_yield",
        "reserve_growth",
        "p_core_earnings",
    },
    "financial": {
        "pfcf_ttm", "ev_ebitda", "ev_sales",
        "pfcf_ratio", "net_debt_to_ebitda", "fcf_margin",
        "debt_to_equity", "operating_margin", "rule_of_40",
        "pb_ratio",
        "combined_ratio",
        "loss_ratio",
        "expense_ratio",
        "net_investment_yield",
        "reserve_growth",
        "p_core_earnings",
    },
    "insurance_pc":{
        "pfcf_ttm", 
        "ev_ebitda", 
        "ev_sales",
        "pfcf_ratio", 
        "net_debt_to_ebitda", 
        "fcf_margin",
        "debt_to_equity", 
        "operating_margin", 
        "rule_of_40",
        "pb_ratio",

        "net_interest_margin",
        "efficiency_ratio",
        "roa",
        "equity_to_assets",
        "provision_ratio",
        "p_ppnr"
    },
    "insurance_life":{
        "pfcf_ttm", 
        "ev_ebitda", 
        "ev_sales",
        "pfcf_ratio", 
        "net_debt_to_ebitda", 
        "fcf_margin",
        "debt_to_equity", 
        "operating_margin", 
        "rule_of_40",
        "pb_ratio",

        "net_interest_margin",
        "efficiency_ratio",
        "roa",
        "equity_to_assets",
        "provision_ratio",
        "p_ppnr"
    }
}

PROFILE_CONCEPT_OVERRIDES = {
    "financial": {
        "Revenue": {
            "sources": [
                {"type": "tag", "tag": "RevenuesNetOfInterestExpense"},
                {"type": "tag", "tag": "Revenues"},
                {"type": "sum", "tags": ["InterestIncomeExpenseNet", "NoninterestIncome"]},
            ],
            "point_in_time": False,
            "mode": "priority_merge",
        },
        "CashAndEquivalents": {
            "tags": [
                "CashAndCashEquivalentsAtCarryingValue",
                "CashAndDueFromBanks",
            ],
            "point_in_time": True,
            "mode": "fallback",
        },
        "Assets": {
            "tags": ["Assets"],
            "point_in_time": True,
            "mode": "fallback",
        },
        "NetInterestIncome": {
            "tags": ["InterestIncomeExpenseNet"],
            "point_in_time": False,
            "mode": "fallback",
        },
        "NoninterestExpense": {
            "tags": ["NoninterestExpense"],
            "point_in_time": False,
            "mode": "fallback",
        },
        
        "DepreciationAndAmortization": {
            "sources": [
                {"type": "tag", "tag": "DepreciationDepletionAndAmortization"},
                {"type": "tag", "tag": "DepreciationAndAmortization"},
                {"type": "tag", "tag": "DepreciationAmortizationAndAccretionNet"},
                {"type": "sum", "tags": ["Depreciation", "AmortizationOfIntangibleAssets", "AmortizationOfMortgageServicingRightsMSRs"]},
                {"type": "tag", "tag": "DepreciationNonproduction"},
                {"type": "tag", "tag": "DepreciationPremisesAndEquipment"},
                {"type": "tag", "tag": "CapitalizedComputerSoftwareAmortization"},
            ],
            "point_in_time": False,
            "mode": "priority_merge",
        },
        "ProvisionForCreditLosses": {
            "tags": [
                "ProvisionForLoanLeaseAndOtherLosses",
                "ProvisionForLoanAndLeaseLosses",
                "ProvisionForLoanLossesExpensed",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
        "NoninterestIncome": {
            "tags": ["NoninterestIncome"],
            "point_in_time": False,
            "mode": "fallback",
        },
    },

    "insurance_pc": {
        "EarnedPremiums": {
            "tags": ["PremiumsEarnedNet"],
            "point_in_time": False,
            "mode": "fallback",
        },
        "IncurredLosses": {
            "tags": ["PolicyholderBenefitsAndClaimsIncurredNet"],
            "point_in_time": False,
            "mode": "fallback",
        },
        "BenefitsLossesAndExpenses": {
            "tags": ["BenefitsLossesAndExpenses"],
            "point_in_time": False,
            "mode": "fallback",
        },
        "NetInvestmentIncome": {
            "tags": ["NetInvestmentIncome"],
            "point_in_time": False,
            "mode": "fallback",
        },
        "Investments": {
            "tags": ["Investments"], 
            "point_in_time": True, 
            "mode": "fallback"
        },
        "ClaimsReserve": {
        "tags": ["LiabilityForClaimsAndClaimsAdjustmentExpense"], 
        "point_in_time": True, 
        "mode": "fallback"
        },
        "RealizedInvestmentGains": {
        "tags": ["RealizedInvestmentGainsLosses"],
        "point_in_time": False,
        "mode": "fallback",
        },


    },

    "insurance_life": {

    },
}

PROFILE_EXCLUDED_CONCEPTS = {
    "standard": {
        "IncurredLosses",
        "ClaimsReserve",
        "NetInvestmentIncome",
        "EarnedPremiums",
        "BenefitsLossesAndExpenses",
        "Investments",
        "RealizedInvestmentGains",
    },
    "financial": {
        "Capex",
        "OperatingIncomeLoss",
        "LongTermDebt",
        "CashAndEquivalents",
        "RealizedInvestmentGains",
    },

    "insurance_pc": {
    "Capex",
    "CashAndEquivalents",
    "OperatingIncomeLoss",
    "CashAndEquivalents",
    },
}




def get_expected_concepts(ticker: str) -> list[str]:
    profile = TICKER_PROFILES.get(ticker, DEFAULT_PROFILE)
    candidates = set(get_concept_candidates(ticker).keys())
    excluded = PROFILE_EXCLUDED_CONCEPTS.get(profile, set())
    return list(candidates - excluded)


def is_hidden(ticker: str, metric_name: str) -> bool:
    profile = TICKER_PROFILES.get(ticker, DEFAULT_PROFILE)
    return metric_name in PROFILE_HIDDEN.get(profile, set())

def filter_hidden_rows(df, ticker_col="ticker", concept_col="concept"):
    if df.empty:
        return df
    mask = df.apply(
        lambda row: not is_hidden(row[ticker_col], row[concept_col]),
        axis=1,
    )
    return df[mask].reset_index(drop=True)

def get_concept_candidates(ticker: str) -> dict:
    profile = TICKER_PROFILES.get(ticker, DEFAULT_PROFILE)
    overrides = PROFILE_CONCEPT_OVERRIDES.get(profile, {})
    resolved = dict(CONCEPT_CANDIDATES)      
    resolved.update(overrides)               
    return resolved

CACHE_DIR = "cache"
DATA_DIR = "data"
FIGURE_DIR = "figures"