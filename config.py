TICKERS = ["MCD"]

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
    "CostOfRevenue",
    "ResearchAndDevelopment",
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
    # insurance concepts:
    "EarnedPremiums": ["premiumsearned"],
    "IncurredLosses": ["benefitsandclaims", "policyholderbenefits"],
    "BenefitsLossesAndExpenses": ["benefitslossesandexpenses"],
    "NetInvestmentIncome": ["netinvestmentincome"],
    "Investments": ["investments"],
    "ClaimsReserve": ["liabilityforclaims", "claimsadjustmentexpense", "futurepolicybenefits"],
    "RealizedInvestmentGains": ["realizedgain", "realizedinvestment"],
    #retail concepts : 
    "Inventory": ["inventorynet", "merchandiseinventory", "inventoryfinishedgoods"],
    "CostOfRevenue": ["costofgoods", "costofrevenue", "costofsales"],
    "AccountsReceivable": ["accountsreceivable", "receivablesnet"],
    "AccountsPayable": ["accountspayable"],
    "ResearchAndDevelopment": ["researchanddevelopment", "rndexpense"],
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
    "AIZ": "insurance_pc",

    "MET": "insurance_life",
    "PRU": "insurance_life",
    "AFL": "insurance_life",
    "PFG": "insurance_life",
    "GL": "insurance_life",

    "ORLY": "retail",
    "AZO": "retail",
    "BBY": "retail",
    "GPC": "retail",
    "HD": "retail",
    "LOW": "retail",
    "LULU": "retail",
    "NKE": "retail",
    "POOL": "retail",
    "RL": "retail",
    "ROST": "retail",
    "TJX": "retail",
    "TSCO": "retail",
    "ULTA": "retail",
    "WSM": "retail",
    "DECK": "retail",
    "TPR": "retail",
    "HAS": "retail",
    "GRMN": "retail",
    "WMT": "retail",
    "COST": "retail",
    "TGT": "retail",
    "DG": "retail",
    "DLTR": "retail",

    "MO": "consumer_staples",
    "ADM": "consumer_staples",
    "BF-B": "consumer_staples",
    "BG": "consumer_staples",
    "CPB": "consumer_staples",
    "CASY": "consumer_staples",
    "CHD": "consumer_staples",
    "CLX": "consumer_staples",
    "KO": "consumer_staples",
    "CAG": "consumer_staples",
    "STZ": "consumer_staples",
    "EL": "consumer_staples",
    "GIS": "consumer_staples",
    "HSY": "consumer_staples",
    "HRL": "consumer_staples",
    "KVUE": "consumer_staples",
    "KDP": "consumer_staples",
    "KMB": "consumer_staples",
    "KHC": "consumer_staples",
    "KR": "consumer_staples",
    "MKC": "consumer_staples",
    "TAP": "consumer_staples",
    "MDLZ": "consumer_staples",
    "MNST": "consumer_staples",
    "PEP": "consumer_staples",
    "PM": "consumer_staples",
    "PG": "consumer_staples",
    "SJM": "consumer_staples",
    "SYY": "consumer_staples",
    "TSN": "consumer_staples",

    "JNJ": "pharma_medtech",
    "ABT": "pharma_medtech",
    "ABBV": "pharma_medtech",
    "A": "pharma_medtech",
    "ALGN": "pharma_medtech",
    "AMGN": "pharma_medtech",
    "BAX": "pharma_medtech",
    "BDX": "pharma_medtech",
    "TECH": "pharma_medtech",
    "BIIB": "pharma_medtech",
    "BSX": "pharma_medtech",
    "BMY": "pharma_medtech",
    "CRL": "pharma_medtech",
    "COO": "pharma_medtech",
    "DHR": "pharma_medtech",
    "DXCM": "pharma_medtech",
    "EW": "pharma_medtech",
    "GEHC": "pharma_medtech",
    "GILD": "pharma_medtech",
    "IDXX": "pharma_medtech",
    "PODD": "pharma_medtech",
    "IQV": "pharma_medtech",
    "ISRG": "pharma_medtech",
    "LLY": "pharma_medtech",
    "MDT": "pharma_medtech",
    "MRK": "pharma_medtech",
    "MTD": "pharma_medtech",
    "PFE": "pharma_medtech",
    "REGN": "pharma_medtech",
    "RMD": "pharma_medtech",
    "RVTY": "pharma_medtech",
    "SOLV": "pharma_medtech",
    "STE": "pharma_medtech",
    "SYK": "pharma_medtech",
    "TMO": "pharma_medtech",
    "VEEV": "pharma_medtech",
    "VTRS": "pharma_medtech",
    "VRTX": "pharma_medtech",
   # "WAT": "pharma_medtech", TICKER BORKEN FOR SHARES OTSTANDING AS OF 21.07
    "WST": "pharma_medtech",
    "ZBH": "pharma_medtech",
    "ZTS": "pharma_medtech",

    "DGX": "health_services",
    "LH": "health_services",
    "HCA": "health_services",
    "DVA": "health_services",
    "UHS": "health_services",
    "CVS": "health_services",

    "HON": "industrials",
    "MMM": "industrials",
    "AOS": "industrials",
    "ALLE": "industrials",
    "AME": "industrials",
    "ADP": "industrials",
    "AXON": "industrials",
    "BA": "industrials",
    "BR": "industrials",
    "BLDR": "industrials",
    "CHRW": "industrials",
    "CARR": "industrials",
    "CTAS": "industrials",
    "CPRT": "industrials",
    "CMI": "industrials",
    "DE": "industrials",
    "DOV": "industrials",
    "EME": "industrials",
    "EMR": "industrials",
    "EFX": "industrials",
    "ETN": "industrials",
    "EXPD": "industrials",
    "FAST": "industrials",
    "FDX": "industrials",
    "FTV": "industrials",
    "FIX": "industrials",
    "GE": "industrials",
    "GEV": "industrials",
    "GNRC": "industrials",
    "GD": "industrials",
    "HWM": "industrials",
    "HUBB": "industrials",
    "HII": "industrials",
    "IEX": "industrials",
    "ITW": "industrials",
    "IR": "industrials",
    "J": "industrials",
    "JBHT": "industrials",
    "JCI": "industrials",
    "LHX": "industrials",
    "LDOS": "industrials",
    "LII": "industrials",
    "LMT": "industrials",
    "MAS": "industrials",
    "NDSN": "industrials",
    "NOC": "industrials",
    "ODFL": "industrials",
    "OTIS": "industrials",
    "PH": "industrials",
    "PAYX": "industrials",
    "PNR": "industrials",
    "PWR": "industrials",
    "RSG": "industrials",
    "ROK": "industrials",
    "ROL": "industrials",
    "RTX": "industrials",
    "SWK": "industrials",
    "TT": "industrials",
    "TDG": "industrials",
    "UPS": "industrials",
    "URI": "industrials",
    "VLTO": "industrials",
    "VRSK": "industrials",
    "WAB": "industrials",
    "WM": "industrials",
    "GWW": "industrials",
    "XYL": "industrials",

    "DIS": "media",
    "NFLX": "media",
    "WBD": "media",
    "EA": "media",
    "TTWO": "media",
    "LYV": "media",
    "OMC": "media",
    "TTD": "media",
    "PSKY": "media",
    "TKO": "media",
    "FOXA": "media",
    "FOX": "media",
    "NWSA": "media",
    "NWS": "media",

    "DHI": "homebuilder",
    "LEN": "homebuilder",
   # "PHM": "homebuilder", WORKS NOT WELL
   # "NVR": "homebuilder", SAME AS ABOVE

    "MCD": "leisure",
    "SBUX": "leisure", "DPZ": "leisure", "CMG": "leisure",
    "MAR": "leisure", "HLT": "leisure",
    "CCL": "leisure", "RCL": "leisure", "NCLH": "leisure",
    "LVS": "leisure", "MGM": "leisure", "WYNN": "leisure",
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
        "rd_intensity",
        "p_core_earnings",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "capex_intensity","operating_leverage","operating_income_yoy_growth"
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
        "rd_intensity",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "capex_intensity","operating_leverage","operating_income_yoy_growth"
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
        "p_ppnr",
        "rd_intensity",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "capex_intensity","operating_leverage","operating_income_yoy_growth"
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
        "p_ppnr",
        "rd_intensity",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "capex_intensity","operating_leverage","operating_income_yoy_growth"
    },
    "retail": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings", "rule_of_40","operating_margin",  
        "net_debt_to_ebitda", "payout_ratio", "capex_intensity","operating_leverage","operating_income_yoy_growth"
    },
     "consumer_staples": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings", "rd_intensity",
        "rule_of_40", "capex_intensity","operating_leverage","operating_income_yoy_growth"
     },

    "pharma_medtech": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "rule_of_40",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "operating_margin",
        "net_debt_to_ebitda", "rd_intensity",
        "ev_ebitda", "capex_intensity","operating_leverage","operating_income_yoy_growth"

    },

    "health_services": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "rule_of_40","rd_intensity",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "rd_intensity", "capex_intensity","operating_leverage","operating_income_yoy_growth"
    },
     "industrials": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "rule_of_40",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "rd_intensity",
    },
    "media": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "rd_intensity",
        "capex_intensity", "operating_leverage", "operating_income_yoy_growth",
        "rule_of_40",
    },

    "homebuilder": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "rd_intensity",
        "capex_intensity", "operating_leverage", "operating_income_yoy_growth", "rule_of_40",
        "operating_margin", "net_debt_to_ebitda", "ev_ebitda",
    },
        "leisure": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "rd_intensity",
        "capex_intensity", "operating_leverage", "operating_income_yoy_growth",
        "rule_of_40",
    },

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
            "tags": ["PremiumsEarnedNet", "PremiumsEarnedNetPropertyAndCasualty"],
            "point_in_time": False,
            "mode": "fallback",
        },
        "IncurredLosses": {
            "tags": ["PolicyholderBenefitsAndClaimsIncurredNet", "IncurredClaimsPropertyCasualtyAndLiability"],
            "point_in_time": False,
            "mode": "fallback",
        },
        "BenefitsLossesAndExpenses": {
            "tags": ["BenefitsLossesAndExpenses"],
            "point_in_time": False,
            "mode": "fallback",
        },
        "NetInvestmentIncome": {
            "tags": ["NetInvestmentIncome", "InvestmentIncomeNet"],
            "point_in_time": False,
            "mode": "fallback",
        },
        "Investments": {
            "tags": ["Investments", "InvestmentsFairValueDisclosure", "SummaryOfInvestmentsOtherThanInvestmentsInRelatedPartiesCarryingAmount"],
            "point_in_time": True,
            "mode": "fallback"
        },
        "ClaimsReserve": {
        "tags": ["LiabilityForClaimsAndClaimsAdjustmentExpense", "LiabilityForClaimsAndClaimsAdjustmentExpensePropertyCasualtyLiability"],
        "point_in_time": True,
        "mode": "fallback"
        },
        "RealizedInvestmentGains": {
        "tags": ["RealizedInvestmentGainsLosses"],
        "point_in_time": False,
        "mode": "fallback",
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
                {"type": "tag", "tag": "SeniorLongTermNotes"},
                {"type": "sum", "tags": ["SeniorNotes", "NotesPayable", "SubordinatedDebt"]},
            ],
            "point_in_time": True,
            "mode": "priority_merge",
        },

    },

    "insurance_life": {
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
            "mode": "fallback",
        },
        "ClaimsReserve": {
            "tags": ["LiabilityForFuturePolicyBenefits"],
            "point_in_time": True,
            "mode": "fallback",
        },
        "RealizedInvestmentGains": {
            "sources": [
                {"type": "sum", "tags": ["GainLossOnSaleOfInvestments", "GainLossOnSaleOfOtherInvestments"]},
                {"type": "tag", "tag": "GainLossOnInvestments"},
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
                {"type": "tag", "tag": "NotesPayable"},
            ],
            "point_in_time": True,
            "mode": "priority_merge",
        },
    },

    "retail": {
        "Inventory": {
            "tags": [
                "InventoryNet",
                "InventoryFinishedGoodsNetOfReserves",
                "InventoryFinishedGoods",
                "RetailRelatedInventoryMerchandise"
            ],
            "point_in_time": True,
            "mode": "fallback",
        },
        "CostOfRevenue": {
            "tags": [
                "CostOfGoodsAndServicesSold",
                "CostOfRevenue",
                "CostOfGoodsSold",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
        "AccountsReceivable": {
            "tags": [
                "AccountsReceivableNetCurrent",
                "ReceivablesNetCurrent",
                "AccountsReceivableTradeNetCurrent",
                "AccountsNotesAndLoansReceivableNetCurrent",
            ],
            "point_in_time": True,
            "mode": "fallback",
        },
        "AccountsPayable": {
            "tags": [
                "AccountsPayableCurrent",
                "AccountsPayableTradeCurrent",
            ],
            "point_in_time": True,
            "mode": "fallback",
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
                {"type": "tag", "tag": "NotesPayable"},
                {"type": "tag", "tag": "OtherBorrowings"},
            ],
            "point_in_time": True,
            "mode": "priority_merge",
        },
    },

    "consumer_staples": {
        "CashAndEquivalents": {
            "tags": [
                "CashAndCashEquivalentsAtCarryingValue",
                "CashAndCashEquivalentsAtCarryingValueIncludingDiscontinuedOperations",
                "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
            ],
            "point_in_time": True,
            "mode": "fallback",
        },
    },
    "pharma_medtech": {
        "ResearchAndDevelopment": {
            "tags": [
                "ResearchAndDevelopmentExpense",
                "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
        "Capex": {
            "tags": [
                "PaymentsToAcquirePropertyPlantAndEquipment",
                "PaymentsToAcquireProductiveAssets",
                "PaymentsToAcquireOtherPropertyPlantAndEquipment",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
    },
    "health_services": {
        "ResearchAndDevelopment": {
            "tags": [
                "ResearchAndDevelopmentExpense",
                "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
        "Capex": {
            "tags": [
                "PaymentsToAcquirePropertyPlantAndEquipment",
                "PaymentsToAcquireProductiveAssets",
                "PaymentsToAcquireOtherPropertyPlantAndEquipment",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
    },
    "industrials": {
        "NetIncomeLoss": {
            "tags": [
                "NetIncomeLoss",
                "NetIncomeLossAvailableToCommonStockholdersBasic",
                "ProfitLoss",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
        "Capex": {
            "tags": [
                "PaymentsToAcquirePropertyPlantAndEquipment",
                "PaymentsToAcquireProductiveAssets",
                "PaymentsToAcquireOtherPropertyPlantAndEquipment",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
        "CashAndEquivalents": {
            "tags": [
                "CashAndCashEquivalentsAtCarryingValue",
                "CashAndCashEquivalentsAtCarryingValueIncludingDiscontinuedOperations",
                "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
            ],
            "point_in_time": True,
            "mode": "fallback",
        },
        "Revenue": {
            "tags": [
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "Revenues",
                "SalesRevenueNet",
                "SalesRevenueGoodsNet",
                "RevenueFromContractWithCustomerIncludingAssessedTax",
                "SalesRevenueServicesNet",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
    },
    "media": {
        "Capex": {
            "tags": [
                "PaymentsToAcquirePropertyPlantAndEquipment",
                "PaymentsToAcquireProductiveAssets",
                "PaymentsToAcquireOtherPropertyPlantAndEquipment",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
        "CashAndEquivalents": {
            "tags": [
                "CashAndCashEquivalentsAtCarryingValue",
                "CashAndCashEquivalentsAtCarryingValueIncludingDiscontinuedOperations",
                "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
            ],
            "point_in_time": True,
            "mode": "fallback",
        },
    },
     "homebuilder": {
        "Inventory": {
            "tags": [
                "InventoryRealEstate",
                "InventoryOperativeBuilders",
            ],
            "point_in_time": True,
            "mode": "fallback",
        },
        "CostOfRevenue": {
            "tags": [
                "CostOfRevenue",
                "CostOfRealEstateRevenue",
                "CostOfGoodsAndServicesSold",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
        "AccountsReceivable": {
            "tags": [
                "AccountsAndNotesReceivableNet",
            ],
            "point_in_time": True,
            "mode": "fallback",
        },
        "AccountsPayable": {
            "tags": [
                "AccountsPayableCurrentAndNoncurrent",
            ],
            "point_in_time": True,
            "mode": "fallback",
        },
        "LongTermDebt": {
            "sources": [
                {"type": "tag", "tag": "LongTermDebt"},
                {"type": "tag", "tag": "NotesPayable"},
                {"type": "tag", "tag": "SeniorNotes"},
            ],
            "point_in_time": True,
            "mode": "priority_merge",
        },
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
     "insurance_life": {
    "Capex",
    "CashAndEquivalents",
    "OperatingIncomeLoss",
    "CashAndEquivalents",
    "DepreciationAndAmortization",
    },
    "retail": {
        "Goodwill"
    }, 
    "pharma_medtech": {
        "OperatingIncomeLoss",
        "DepreciationAndAmortization",
    },
    "health_services": {
        "ResearchAndDevelopment",
    },
    "homebuilder": {
        "OperatingIncomeLoss",
    },

}


TICKER_CONCEPT_OVERRIDES = {
    "NVR": {
        "Inventory": {
            "tags": ["InventoryRealEstateLandAndLandDevelopmentCosts"],
            "point_in_time": True,
            "mode": "fallback",
        },
    },
    "CMG": {
        "Revenue": {
            "tags": [
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "Revenues",
                "SalesRevenueNet",
                "SalesRevenueGoodsNet",
                "RevenueFromContractWithCustomerIncludingAssessedTax",
                "FoodAndBeverageRevenue",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
    },
    "CCL": {
        "Revenue": {
            "tags": [
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "Revenues",
                "SalesRevenueNet",
                "SalesRevenueGoodsNet",
                "RevenueFromContractWithCustomerIncludingAssessedTax",
                "SalesRevenueServicesGross",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
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
    resolved.update(TICKER_CONCEPT_OVERRIDES.get(ticker, {}))
    return resolved

CACHE_DIR = "cache"
DATA_DIR = "data"
FIGURE_DIR = "figures"