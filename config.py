TICKERS = ["AMD", "MU"]

EDGAR_USER_AGENT = "Loris loris2006@gmx.de"

PERIOD = "quarterly"

SNAPSHOT_AS_OF_DATES = []  # in YYYY-MM-DD format, e.g. ["2023-12-31", "2024-03-31"]

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
            {
                "type": "sum",
                "tags": ["LongTermDebtNoncurrent", "LongTermDebtCurrent", "NotesPayableCurrent"],
                "require": "LongTermDebtNoncurrent",
            },
            {"type": "tag", "tag": "LongTermDebtAndCapitalLeaseObligations"},
            {"type": "tag", "tag": "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities"},
            {"type": "tag", "tag": "UnsecuredLongTermDebt"},
            {"type": "tag", "tag": "ConvertibleDebtCurrent"},
            {"type": "tag", "tag": "ConvertibleNotesPayableCurrent"},
        ],
        "point_in_time": True,
        "mode": "priority_merge",
        "non_negative": True,
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
    "RealEstateDepreciation", 
    "GainLossOnSaleOfProperties",
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
    "SCHW": "financial", "RJF": "financial",
    "IBKR": "financial", "HOOD": "financial",
    "MS": "financial", "SOFI": "financial",


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
    "CAH": "retail", "COR": "retail", "MCK": "retail", "HSIC": "retail",
    #"CVNA": "retail", doesnt work

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
    "CL": "consumer_staples",  

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
    "WAT": "pharma_medtech",
    "WST": "pharma_medtech",
    "ZBH": "pharma_medtech",
    "ZTS": "pharma_medtech",
    "INCY": "pharma_medtech",

    "DGX": "health_services",
    "LH": "health_services",
    "HCA": "health_services",
    "DVA": "health_services",
    "UHS": "health_services",
    "CVS": "health_services",
    "CI": "health_services", "ELV": "health_services",
    "HUM": "health_services", "CNC": "health_services", "UNH": "health_services",

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
    "APTV": "industrials", "VRT": "industrials",
    "SNA": "industrials",
    "TSLA": "industrials",

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
    "DRI": "leisure", "YUM": "leisure",  

    "SO": "utilities",
    "AES": "utilities", "LNT": "utilities", "AEE": "utilities", "AEP": "utilities",
    "AWK": "utilities", "ATO": "utilities", "CNP": "utilities", "CMS": "utilities",
    "ED": "utilities", "CEG": "utilities", "D": "utilities", "DTE": "utilities",
    "DUK": "utilities", "EIX": "utilities", "ETR": "utilities", "EVRG": "utilities",
    "ES": "utilities", "EXC": "utilities", "FE": "utilities", "NEE": "utilities",
    "NI": "utilities", "NRG": "utilities", "PCG": "utilities", "PEG": "utilities",
    "PNW": "utilities", "PPL": "utilities", "SRE": "utilities", "VST": "utilities",
    "WEC": "utilities", "XEL": "utilities",

    "T": "telecom_cable",
    "VZ": "telecom_cable", "TMUS": "telecom_cable",
    "CMCSA": "telecom_cable", "CHTR": "telecom_cable", "SATS": "telecom_cable",

    "UNP": "railroads",
    "CSX": "railroads",
    "NSC": "railroads",

    "XOM": "energy_integrated",
    "CVX": "energy_integrated",
    "EOG": "energy", "COP": "energy_integrated", "OXY": "energy_integrated", "DVN": "energy_integrated",
    "FANG": "energy", ""
    #"APA": "energy", HAS NO REVENUE
    "EQT": "energy", "EXE": "energy",
    "WMB": "energy", "OKE": "energy", "KMI": "energy", "TRGP": "energy",
    "MPC": "energy", "PSX": "energy_integrated", "VLO": "energy",
    "SLB": "energy_integrated", "HAL": "energy", "BKR": "energy_integrated",
    "TPL": "energy",

    "LIN": "materials",
    "APD": "materials", "SHW": "materials_integrated", "ECL": "materials", "FCX": "materials",
    "NEM": "materials_integrated", "DOW": "materials_integrated", "DD": "materials_integrated", "LYB": "materials",
    "PPG": "materials", "ALB": "materials", "CE": "materials", "IFF": "materials",
    "MLM": "materials", "VMC": "materials", "NUE": "materials_integrated", "STLD": "materials",
    "PKG": "materials", "IP": "materials_integrated", "AVY": "materials_integrated", "BALL": "materials_integrated",
    "AMCR": "materials", "CF": "materials", "MOS": "materials",
    "CRH": "materials", "SW": "materials", "CTVA": "materials",

    "O": "reit",
    "PLD": "reit", "PSA": "reit", "EXR": "reit", "DLR": "reit", "EQIX": "reit",
    "AMT": "reit", "CCI": "reit", "SBAC": "reit", "SPG": "reit", "REG": "reit",
    "FRT": "reit", "KIM": "reit", "AVB": "reit", "EQR": "reit", "MAA": "reit",
    "ESS": "reit", "INVH": "reit", "UDR": "reit", "CPT": "reit", "WELL": "reit",
    "VTR": "reit", "DOC": "reit", "BXP": "reit", "HST": "reit", "WY": "reit",
    "IRM": "reit",
    "ARE": "reit", "VICI": "reit",  

    "EBAY": "marketplace",
    "BKNG": "marketplace", "EXPE": "marketplace",
    "DASH": "marketplace", "ABNB": "marketplace", "UBER": "marketplace",

    "F": "captive_finance",
    "GM": "captive_finance", "CAT": "captive_finance",
    "PCAR": "captive_finance", "TXT": "captive_finance",

    "LUV": "airline",
    "DAL": "airline", "UAL": "airline",

 
    "AAPL": "standard", "ACN": "standard", "ADBE": "standard", "ADI": "standard",
    "ADSK": "standard", "AKAM": "standard", "AMAT": "standard", "AMD": "standard",
    "AMZN": "standard", "ANET": "standard", "APH": "standard", "AVGO": "standard",
    "CDNS": "standard", "CDW": "standard", "CIEN": "standard", "COHR": "standard",
    "CRM": "standard", "CRWD": "standard", "CSCO": "standard", "CTSH": "standard",
    "DDOG": "standard", "DELL": "standard", "FFIV": "standard", "FICO": "standard",
    "FLEX": "standard", "FSLR": "standard", "FTNT": "standard", "GDDY": "standard",
    "GEN": "standard", "GLW": "standard", "GOOG": "standard", "GOOGL": "standard",
    "HPE": "standard", "HPQ": "standard", "IBM": "standard", "INTC": "standard",
    "INTU": "standard", "IT": "standard", "JBL": "standard", "KEYS": "standard",
    "KLAC": "standard", "LITE": "standard", "LRCX": "standard", "MA": "standard",
    "MCHP": "standard", "META": "standard", "MPWR": "standard", "MRVL": "standard",
    "MSFT": "standard", "MSI": "standard", "MU": "standard", "NTAP": "standard",
    "NVDA": "standard", "NXPI": "standard", "ON": "standard", "ORCL": "standard",
    "PANW": "standard", "PLTR": "standard", "PTC": "standard", "Q": "standard",
    "QCOM": "standard", "RDDT": "standard", "ROP": "standard", "SMCI": "standard",
    "SNDK": "standard", "SNPS": "standard", "STX": "standard", "SWKS": "standard",
    "TDY": "standard", "TEL": "standard", "TER": "standard", "TRMB": "standard",
    "TXN": "standard", "TYL": "standard", "V": "standard", "VRSN": "standard",
    "WDAY": "standard", "WDC": "standard", "ZBRA": "standard",
    "FISV": "standard", "FIS": "standard", "GPN": "standard", "PYPL": "standard",
    "XYZ": "standard", "CPAY": "standard", "JKHY": "standard",
    "CME": "standard", "CBOE": "standard", "ICE": "standard", "NDAQ": "standard",
    "COIN": "standard",
    "SPGI": "standard", "MCO": "standard", "MSCI": "standard", "FDS": "standard",
    "AON": "standard", "MRSH": "standard", "WTW": "standard", "AJG": "standard",
    "BRO": "standard",
    "ERIE": "standard",
    "BLK": "standard", "TROW": "standard", "BEN": "standard", "IVZ": "standard",
    "AMP": "standard",
    "CBRE": "standard", "CSGP": "standard",
    "APP": "standard", "NOW": "standard",

    "BX": "alt_asset_manager",
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
        "capex_intensity","operating_leverage","operating_income_yoy_growth",
        "ffo_margin", "p_ffo"
    },
    "financial": {
        "pfcf_ttm", "ev_ebitda", "ev_sales",
        "pfcf_ratio", "ev_fcf", "net_debt_to_ebitda", "fcf_margin",
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
        "capex_intensity","operating_leverage","operating_income_yoy_growth",
        "ffo_margin", "p_ffo",
    },
    "insurance_pc":{
        "pfcf_ttm",
        "ev_ebitda",
        "ev_sales",
        "pfcf_ratio",
        "ev_fcf",
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
        "capex_intensity","operating_leverage","operating_income_yoy_growth", "ffo_margin", "p_ffo",
    },
    "insurance_life":{
        "pfcf_ttm",
        "ev_ebitda",
        "ev_sales",
        "pfcf_ratio",
        "ev_fcf",
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
        "capex_intensity","operating_leverage","operating_income_yoy_growth", "ffo_margin", "p_ffo",
    },
    "retail": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings", "rule_of_40","operating_margin",  
        "net_debt_to_ebitda", "payout_ratio", "capex_intensity","operating_leverage","operating_income_yoy_growth",
        "ffo_margin", "p_ffo",
    },
     "consumer_staples": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings", "rd_intensity",
        "rule_of_40", "capex_intensity","operating_leverage","operating_income_yoy_growth", "ffo_margin", "p_ffo",
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
        "ev_ebitda", "capex_intensity","operating_leverage","operating_income_yoy_growth", "ffo_margin", "p_ffo",

    },

    "health_services": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "rule_of_40","rd_intensity",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "rd_intensity", "capex_intensity","operating_leverage","operating_income_yoy_growth", "ffo_margin", "p_ffo",
    },
     "industrials": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "rule_of_40",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "rd_intensity", "ffo_margin", "p_ffo",
    },
    "media": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "rd_intensity",
        "capex_intensity", "operating_leverage", "operating_income_yoy_growth",
        "rule_of_40", "ffo_margin", "p_ffo",
    },

    "homebuilder": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "rd_intensity",
        "capex_intensity", "operating_leverage", "operating_income_yoy_growth", "rule_of_40",
        "operating_margin", "net_debt_to_ebitda", "ev_ebitda", "ffo_margin", "p_ffo",
    },
        "leisure": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "rd_intensity",
        "capex_intensity", "operating_leverage", "operating_income_yoy_growth",
        "rule_of_40", "ffo_margin", "p_ffo",
    },
        "utilities": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "rd_intensity",
        "operating_leverage", "operating_income_yoy_growth",
        "rule_of_40", "pfcf_ratio", "ev_fcf", "ffo_margin", "p_ffo",
    },
        "telecom_cable": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "rd_intensity",
        "operating_leverage", "operating_income_yoy_growth",
        "rule_of_40", "ffo_margin", "p_ffo",
    },
        "railroads": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "rd_intensity",
        "operating_leverage", "operating_income_yoy_growth", "rule_of_40", "ffo_margin", "p_ffo",
    },
        "energy": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "rd_intensity",
        "operating_leverage", "operating_income_yoy_growth",
        "rule_of_40", "ffo_margin", "p_ffo",
    },
        "energy_integrated": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "rd_intensity",
        "operating_leverage", "operating_income_yoy_growth",
        "operating_margin", "net_debt_to_ebitda", "ev_ebitda",
        "rule_of_40", "ffo_margin", "p_ffo",
    },
        "materials": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "rd_intensity",
        "operating_leverage", "operating_income_yoy_growth", "rule_of_40", "ffo_margin", "p_ffo",
    },
        "materials_integrated": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "rd_intensity",
        "operating_leverage", "operating_income_yoy_growth", "rule_of_40",
        "operating_margin", "net_debt_to_ebitda", "ev_ebitda", "ffo_margin", "p_ffo",
    },
        "reit": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "rd_intensity", "operating_leverage", "operating_income_yoy_growth",
        "rule_of_40",
        "capex_intensity",    
        "pe_ratio",          
        "payout_ratio",        
        "income_yoy_growth",   
        "operating_margin", "net_debt_to_ebitda", "ev_ebitda",
        "pfcf_ratio",   
        "fcf_margin",
    },
        "marketplace": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "rd_intensity",
        "operating_leverage", "operating_income_yoy_growth",
        "ffo_margin", "p_ffo", "dividend_yield",
        "payout_ratio",
    },
        "captive_finance": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "rd_intensity", "operating_leverage", "operating_income_yoy_growth",
        "ffo_margin", "p_ffo",
        "rule_of_40",
    },
     "airline": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "rd_intensity", "operating_leverage", "operating_income_yoy_growth",
        "ffo_margin", "p_ffo",
        "rule_of_40",
    },
        "alt_asset_manager": {
        "net_interest_margin", "efficiency_ratio", "p_tbv", "roa",
        "equity_to_assets", "provision_ratio", "p_ppnr", "combined_ratio",
        "loss_ratio", "expense_ratio", "net_investment_yield",
        "reserve_growth", "p_core_earnings",
        "inventory_turnover", "dio", "dso", "dpo", "cash_conversion_cycle",
        "rd_intensity", "operating_leverage", "operating_income_yoy_growth",
        "ffo_margin", "p_ffo",
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

    "utilities": {
        "CashAndEquivalents": {
            "tags": [
                "CashAndCashEquivalentsAtCarryingValue",
                "CashAndCashEquivalentsAtCarryingValueIncludingDiscontinuedOperations",
                "Cash",
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
                "RegulatedAndUnregulatedOperatingRevenue",
                "UtilityRevenue",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
        "Capex": {
            "tags": [
                "PaymentsToAcquireProductiveAssets",
                "PaymentsToAcquirePropertyPlantAndEquipment",
                "PaymentsToAcquireOtherProductiveAssets",
                "PaymentsToAcquireOtherPropertyPlantAndEquipment",
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
                {"type": "tag", "tag": "UtilitiesOperatingExpenseDepreciationAndAmortization"},
            ],
            "point_in_time": False,
            "mode": "priority_merge",
        },
    },

    "energy": {
        "Capex": {
            "tags": [
                "PaymentsToAcquirePropertyPlantAndEquipment",
                "PaymentsToAcquireProductiveAssets",
                "PaymentsToAcquireOilAndGasPropertyAndEquipment",
                "PaymentsToExploreAndDevelopOilAndGasProperties",
                "PaymentsToAcquireOilAndGasProperty",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
        "CashAndEquivalents": {
            "tags": [
                "CashAndCashEquivalentsAtCarryingValue",
                "CashAndCashEquivalentsAtCarryingValueIncludingDiscontinuedOperations",
                "Cash",
                "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
            ],
            "point_in_time": True,
            "mode": "fallback",
        },
    },
    "energy_integrated": {
        "Capex": {
            "tags": [
                "PaymentsToAcquirePropertyPlantAndEquipment",
                "PaymentsToAcquireProductiveAssets",
                "PaymentsToAcquireOilAndGasPropertyAndEquipment",
                "PaymentsToExploreAndDevelopOilAndGasProperties",
                "PaymentsToAcquireOilAndGasProperty",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
        "CashAndEquivalents": {
            "tags": [
                "CashAndCashEquivalentsAtCarryingValue",
                "CashAndCashEquivalentsAtCarryingValueIncludingDiscontinuedOperations",
                "Cash",
                "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
            ],
            "point_in_time": True,
            "mode": "fallback",
        },
    },
    "reit": {
        "Revenue": {
            "tags": [
                "Revenues",
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "SalesRevenueNet",
                "SalesRevenueGoodsNet",
                "RevenueFromContractWithCustomerIncludingAssessedTax",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
        "GainLossOnSaleOfProperties": {
            "tags": [
                "GainLossOnSaleOfProperties",
                "GainsLossesOnSalesOfInvestmentRealEstate",
                "GainLossOnSaleOfPropertiesNetOfTax",
                "GainLossOnDispositionOfRealEstate",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
        "LongTermDebt": {
            "tags": [
                "NotesPayable",
                "LongTermDebt",
                "LongTermDebtNoncurrent",
            ],
            "point_in_time": True,
            "mode": "fallback",
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
    "railroads": {
        "Goodwill"
    }, 
    "energy": {
        "Goodwill"
    },
    "energy_integrated": {
        "Goodwill", "OperatingIncomeLoss"
    },
    "materials_integrated": {
        "OperatingIncomeLoss"
    },
    "reit": {
    "OperatingIncomeLoss", 
    "Capex"
    },
}


TICKER_CONCEPT_OVERRIDES = {
    "SOFI": {
        "ProvisionForCreditLosses": {
            "tags": [
                "ProvisionForLoanLeaseAndOtherLosses",
                "ProvisionForLoanAndLeaseLosses",
                "ProvisionForLoanLossesExpensed",
                "FinancingReceivableExcludingAccruedInterestCreditLossExpenseReversal",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
    },
    "FIS": {
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
    "TROW": {
        "DepreciationAndAmortization": {
            "sources": [
                {"type": "tag", "tag": "DepreciationDepletionAndAmortization"},
                {"type": "tag", "tag": "DepreciationNonproduction"},
                {"type": "tag", "tag": "DepreciationAndAmortization"},
                {"type": "tag", "tag": "DepreciationAmortizationAndAccretionNet"},
                {"type": "sum", "tags": ["Depreciation", "AmortizationOfIntangibleAssets"]},
            ],
            "point_in_time": False,
            "mode": "priority_merge",
        },
    },
    "ERIE": {
        "Capex": {
            "tags": [
                "PaymentsToAcquirePropertyPlantAndEquipment",
                "PaymentsToAcquireProductiveAssets",
                "PaymentsForProceedsFromProductiveAssets",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
    },
    "NVR": {
        "Inventory": {
            "tags": ["InventoryRealEstateLandAndLandDevelopmentCosts"],
            "point_in_time": True,
            "mode": "fallback",
        },
    },
    "DLR": {
        "LongTermDebt": {
            "tags": ["NotesPayable", "SeniorNotes", "LongTermDebt", "LongTermDebtNoncurrent"],
            "point_in_time": True,
            "mode": "fallback",
        },
    },
    "HST": {
        "LongTermDebt": {
            "tags": ["NotesPayable", "DebtAndCapitalLeaseObligations", "LongTermDebtNoncurrent"],
            "point_in_time": True,
            "mode": "fallback",
        },
    },
    "BXP": {
        "LongTermDebt": {
            "tags": ["SecuredDebt", "SeniorNotes"],
            "point_in_time": True,
            "mode": "sum",
        },
    },
    "AMT": {
        "LongTermDebt": {
            "tags": ["NotesPayable", "LongTermDebtAndCapitalLeaseObligations", "LongTermDebtNoncurrent"],
            "point_in_time": True,
            "mode": "fallback",
        },
    },
    "CCI": {
        "LongTermDebt": {
            "tags": ["NotesPayable", "LongTermDebtAndCapitalLeaseObligations", "LongTermDebtNoncurrent"],
            "point_in_time": True,
            "mode": "fallback",
        },
    },
    "EXR": {
        "LongTermDebt": {
            "tags": ["SeniorNotes", "NotesPayable", "LongTermDebtNoncurrent"],
            "point_in_time": True,
            "mode": "fallback",
        },
    },
    "CPT": {
        "Revenue": {
            "tags": ["OperatingLeaseLeaseIncome", "RealEstateRevenueNet", "Revenues",
                     "RevenueFromContractWithCustomerExcludingAssessedTax"],
            "point_in_time": False,
            "mode": "fallback",
        },
    },
    "FRT": {
        "LongTermDebt": {
            "tags": ["DebtAndCapitalLeaseObligations", "LongTermDebt", "LongTermDebtNoncurrent"],
            "point_in_time": True,
            "mode": "fallback",
        },
        "GainLossOnSaleOfProperties": {
            "tags": [
                "GainLossOnSaleOfProperties",
                "GainsLossesOnSalesOfInvestmentRealEstate",
                "GainLossOnSaleOfPropertiesNetOfTax",
                "GainLossOnDispositionOfRealEstate",
                "GainLossOnSaleOfPropertiesNetOfApplicableIncomeTaxes",
            ],
            "point_in_time": False,
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
    "EBAY": {
        "LongTermDebt": {
            "tags": [
                "LongTermDebtAndCapitalLeaseObligations",
                "LongTermDebtNoncurrent",
            ],
            "point_in_time": True,
            "mode": "fallback"
        }
    },
    "BKNG": {
        "LongTermDebt": {
            "sources": [
                {"type": "tag", "tag": "LongTermDebt"},
                {"type": "sum", "tags": ["LongTermDebtNoncurrent", "LongTermDebtCurrent"]},
            ],
            "point_in_time": True,
            "mode": "priority_merge",
        }
    },
    "CAT": {
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
    "F": {
        "LongTermDebt": {
            "tags": ["DebtAndCapitalLeaseObligations"],
            "point_in_time": True,
            "mode": "fallback",
        },
    },
    "ABNB": {
        "DepreciationAndAmortization": {
            "sources": [
                {"type": "tag", "tag": "DepreciationDepletionAndAmortization"},
                {"type": "tag", "tag": "DepreciationAndAmortization"},
                {"type": "tag", "tag": "DepreciationAmortizationAndAccretionNet"},
                {"type": "sum", "tags": ["Depreciation", "AmortizationOfIntangibleAssets"]},
                {"type": "tag", "tag": "AdjustmentForAmortization"},
                {"type": "tag", "tag": "FiniteLivedIntangibleAssetsAmortizationExpense"},
                {"type": "tag", "tag": "OtherDepreciationAndAmortization"},
            ],
            "point_in_time": False,
            "mode": "priority_merge",
        }
    },
    # --- full flag sweep task ---
    "PRU": {
        "RealizedInvestmentGains": {
            "sources": [
                {"type": "sum", "tags": ["GainLossOnSaleOfInvestments", "GainLossOnSaleOfOtherInvestments"]},
                {"type": "tag", "tag": "GainLossOnInvestments"},
                {"type": "tag", "tag": "RealizedInvestmentGainsLosses"},
            ],
            "point_in_time": False,
            "mode": "priority_merge",
        },
    },
    "AIG": {
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
                {"type": "tag", "tag": "OtherLongTermDebt"},
            ],
            "point_in_time": True,
            "mode": "priority_merge",
        },
    },
    "IDXX": {
        "LongTermDebt": {
            "sources": [
                {"type": "tag", "tag": "LongTermDebt"},
                {"type": "tag", "tag": "DebtLongtermAndShorttermCombinedAmount"},
                {"type": "tag", "tag": "LongTermNotesAndLoans"},
                {"type": "tag", "tag": "ConvertibleLongTermNotesPayable"},
                {"type": "tag", "tag": "ConvertibleDebtNoncurrent"},
                {
                    "type": "sum",
                    "tags": ["LongTermDebtNoncurrent", "LongTermDebtCurrent", "NotesPayableCurrent"],
                    "require": "LongTermDebtNoncurrent",
                },
                {"type": "tag", "tag": "LongTermDebtAndCapitalLeaseObligations"},
                {"type": "tag", "tag": "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities"},
                {"type": "tag", "tag": "UnsecuredLongTermDebt"},
                {"type": "tag", "tag": "ConvertibleDebtCurrent"},
                {"type": "tag", "tag": "ConvertibleNotesPayableCurrent"},
                {"type": "tag", "tag": "SecuredLongTermDebt"},
            ],
            "point_in_time": True,
            "mode": "priority_merge",
            "non_negative": True,
        },
    },
    "ARE": {
        "GainLossOnSaleOfProperties": {
            "tags": [
                "GainLossOnSaleOfProperties",
                "GainsLossesOnSalesOfInvestmentRealEstate",
                "GainLossOnSaleOfPropertiesNetOfTax",
                "GainLossOnDispositionOfRealEstate",
                "GainLossOnDispositionOfRealEstateDiscontinuedOperations",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
    },
    "TGT": {
        "AccountsReceivable": {
            "tags": [
                "AccountsReceivableNetCurrent",
                "ReceivablesNetCurrent",
                "AccountsReceivableTradeNetCurrent",
                "AccountsNotesAndLoansReceivableNetCurrent",
                "AccountsAndOtherReceivablesNetCurrent",
            ],
            "point_in_time": True,
            "mode": "fallback",
        },
    },
    "GDDY": {
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
    "GLW": {
        "Capex": {
            "tags": [
                "PaymentsToAcquirePropertyPlantAndEquipment",
                "PaymentsToAcquireProductiveAssets",
                "PaymentsForProceedsFromProductiveAssets",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
    },
    "MA": {
        "NetIncomeLoss": {
            "tags": [
                "NetIncomeLoss",
                "NetIncomeLossAvailableToCommonStockholdersBasic",
                "ProfitLoss",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
    },
    "KEYS": {
        "NetIncomeLoss": {
            "tags": [
                "NetIncomeLoss",
                "NetIncomeLossAvailableToCommonStockholdersBasic",
                "ProfitLoss",
            ],
            "point_in_time": False,
            "mode": "fallback",
        },
    },
}


def get_active_tickers() -> list[str]:
    return sorted(TICKER_PROFILES.keys())


def get_expected_concepts(ticker: str) -> list[str]:
    profile = TICKER_PROFILES.get(ticker, DEFAULT_PROFILE)
    candidates = set(get_concept_candidates(ticker).keys())
    excluded = PROFILE_EXCLUDED_CONCEPTS.get(profile, set())
    return list(candidates - excluded)


_DERIVED_CONCEPT_CONSUMERS = {
    "EPS_TTM_CALC": ["pe_ratio", "payout_ratio"],
    "TangibleEquity": ["p_tbv"],
    "PPNR": ["p_ppnr"],
    "CoreOperatingEarnings": ["p_core_earnings"],
    "FFO_TTM": ["p_ffo", "ffo_margin"],
    "FCF_TTM": ["pfcf_ratio", "fcf_margin", "ev_fcf"],
    "EBITDA_TTM": ["ev_ebitda", "net_debt_to_ebitda"],
    "eps_ttm": ["pe_ratio"],
    "pe_ttm": ["pe_ratio"],
    # avg_X_5y / _median / _diverges names must stay in sync with main.py's AVG_5Y_FIELD_NAMES --
    # otherwise a hidden multiple's rolling reference fields leak visible for that profile.
    "avg_pe_5y": ["pe_ratio"],
    "avg_pe_5y_median": ["pe_ratio"],
    "avg_pe_5y_diverges": ["pe_ratio"],
    "avg_pfcf_5y": ["pfcf_ratio"],
    "avg_pfcf_5y_median": ["pfcf_ratio"],
    "avg_pfcf_5y_diverges": ["pfcf_ratio"],
    "avg_ev_ebitda_5y": ["ev_ebitda"],
    "avg_ev_ebitda_5y_median": ["ev_ebitda"],
    "avg_ev_ebitda_5y_diverges": ["ev_ebitda"],
    "avg_p_tbv_5y": ["p_tbv"],
    "avg_p_tbv_5y_median": ["p_tbv"],
    "avg_p_tbv_5y_diverges": ["p_tbv"],
    "avg_p_ppnr_5y": ["p_ppnr"],
    "avg_p_ppnr_5y_median": ["p_ppnr"],
    "avg_p_ppnr_5y_diverges": ["p_ppnr"],
    "avg_p_core_earnings_5y": ["p_core_earnings"],
    "avg_p_core_earnings_5y_median": ["p_core_earnings"],
    "avg_p_core_earnings_5y_diverges": ["p_core_earnings"],
    "avg_p_ffo_5y": ["p_ffo"],
    "avg_p_ffo_5y_median": ["p_ffo"],
    "avg_p_ffo_5y_diverges": ["p_ffo"],
    "tangible_equity": ["p_tbv"],
    "ppnr_ttm": ["p_ppnr"],
    "core_earnings_ttm": ["p_core_earnings"],
    "fcf_ttm": ["pfcf_ratio", "fcf_margin"],
    "pfcf_ttm": ["pfcf_ratio"],
    "ebitda_ttm": ["ev_ebitda", "net_debt_to_ebitda"],
    "net_debt": ["net_debt_to_ebitda"],
    "ev": ["ev_ebitda", "ev_sales"],
    # quarterly (non-TTM) counterparts of the derived concepts above -- hidden under
    # exactly the same condition as their TTM sibling, so a profile that hides e.g.
    # PPNR-derived output also hides the new PPNR_QUARTERLY reporting-view concept.
    "EPS_QUARTERLY_CALC": ["pe_ratio", "payout_ratio"],
    "PPNR_QUARTERLY": ["p_ppnr"],
    "CoreOperatingEarnings_QUARTERLY": ["p_core_earnings"],
    "FFO_QUARTERLY": ["p_ffo", "ffo_margin"],
    "FCF_QUARTERLY": ["pfcf_ratio", "fcf_margin"],
    "EBITDA_QUARTERLY": ["ev_ebitda", "net_debt_to_ebitda"],
}


def is_hidden(ticker: str, metric_name: str) -> bool:
    profile = TICKER_PROFILES.get(ticker, DEFAULT_PROFILE)
    hidden_set = PROFILE_HIDDEN.get(profile, set())

    base_name = metric_name[:-len("_quarterly")] if metric_name.endswith("_quarterly") else metric_name
    if metric_name in hidden_set or base_name in hidden_set:
        return True
    consumers = _DERIVED_CONCEPT_CONSUMERS.get(metric_name) or _DERIVED_CONCEPT_CONSUMERS.get(base_name)
    if consumers:
        return all(c in hidden_set for c in consumers)
    return False

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

GROWTH_BASE_PANELS = ["shares_outstanding_growth", "equity_growth", "debt_growth"]

GROWTH_PROFILE_EXTRA = {
    # capital/asset-light sectors where growth investors watch cash generation directly
    "standard": ["fcf_growth", "ebitda_growth"],
    "media": ["fcf_growth", "ebitda_growth"],
    "leisure": ["fcf_growth", "ebitda_growth"],
    "marketplace": ["fcf_growth", "ebitda_growth"],
    # capex-heavy / physical-asset sectors: capex growth is the central capacity signal
    "industrials": ["fcf_growth", "capex_growth"],
    "telecom_cable": ["fcf_growth", "capex_growth"],
    "railroads": ["fcf_growth", "capex_growth"],
    "airline": ["fcf_growth", "capex_growth"],
    "energy": ["capex_growth", "ebitda_growth"],
    "energy_integrated": ["capex_growth", "ebitda_growth"],
    "utilities": ["capex_growth", "assets_growth"],
    "materials": ["capex_growth", "inventory_growth"],
    "materials_integrated": ["capex_growth", "inventory_growth"],
    # inventory-driven sectors
    "retail": ["inventory_growth", "cash_growth"],
    "consumer_staples": ["inventory_growth", "fcf_growth"],
    "homebuilder": ["inventory_growth", "fcf_growth"],
    # R&D-driven sectors
    "pharma_medtech": ["rd_growth", "fcf_growth"],
    "health_services": ["rd_growth", "fcf_growth"],
    # bank / balance-sheet-driven sectors
    "financial": ["nii_growth", "provision_growth"],
    "captive_finance": ["fcf_growth", "assets_growth"],
    "alt_asset_manager": ["fcf_growth", "assets_growth"],
    # insurance: premium and investment-income growth are the core underwriting signals
    # (reserve_growth already exists and is already plotted on the fundamentals chart)
    "insurance_pc": ["earned_premiums_growth", "net_investment_income_growth"],
    "insurance_life": ["earned_premiums_growth", "net_investment_income_growth"],
    # REIT: FFO growth is the headline metric this sector is valued on
    "reit": ["ffo_growth", "cash_growth"],
}


def get_growth_panels(ticker: str) -> list[str]:
    profile = TICKER_PROFILES.get(ticker, DEFAULT_PROFILE)
    return GROWTH_BASE_PANELS + GROWTH_PROFILE_EXTRA.get(profile, [])


CACHE_DIR = "cache"
DATA_DIR = "data"
FIGURE_DIR = "figures"



# FOR FIGURES:PY

QUARTERLY_COUNTERPART = {
    "operating_margin": "operating_margin_quarterly",
    "payout_ratio": "payout_ratio_quarterly",
    "fcf_margin": "fcf_margin_quarterly",
    "efficiency_ratio": "efficiency_ratio_quarterly",
    "provision_ratio": "provision_ratio_quarterly",
    "combined_ratio": "combined_ratio_quarterly",
    "loss_ratio": "loss_ratio_quarterly",
    "expense_ratio": "expense_ratio_quarterly",
    "rd_intensity": "rd_intensity_quarterly",
    "capex_intensity": "capex_intensity_quarterly",
    "ffo_margin": "ffo_margin_quarterly",
}

FUNDAMENTALS_TO_PLOT = [
    ("revenue_yoy_growth", "Revenue growth", 0, True, False),
    ("income_yoy_growth", "Income growth", 0, True, False),
    ("operating_margin", "Operating Margin", None, True, False),
    ("roe", "Return on Equity", None, True, False),
    ("debt_to_equity", "Debt-to-Equity Ratio", None, False, False),
    ("payout_ratio", "Payout Ratio", None, True, False),
    ("fcf_margin", "Free Cash Flow Margin", None, True, False),
    ("net_debt_to_ebitda", "Net Debt / EBITDA", 0, False, False),
    ("rule_of_40", "Rule of 40", 0.4, True, False),
    ("net_interest_margin", "Net Interest Margin", None, True, False),
    ("efficiency_ratio", "Efficiency Ratio", None, True, False),
    ("roa", "Return on Assets", None, True, False),
    ("equity_to_assets", "Equity / Assets", None, True, False),
    ("provision_ratio", "Provision/Revenue", 0, True, False),
    ("combined_ratio", "Combined Ratio", 1.0, True, False),
    ("loss_ratio", "Loss Ratio", None, True, False),
    ("expense_ratio", "Expense Ratio", None, True, False),
    ("net_investment_yield", "Net Investment Yield", None, True, False),
    ("reserve_growth", "Reserve Growth", 0, True, False),
    ("inventory_turnover", "Inventory Turnover (x/Year)", None, False, False),
    ("dio", "Days Inventory Outstanding", None, False, False),
    ("dso", "Days Sales Outstanding", None, False, False),
    ("dpo", "Days Payable Outstanding", None, False, False),
    ("cash_conversion_cycle", "Cash Conversion Cycle (Days)", 0, False, False),
    ("rd_intensity", "R&D Intensity (% Revenue)", None, True, False),
    ("capex_intensity", "CapEx Intensity (% Revenue)", None, True, False),
    ("operating_leverage", "Operating Leverage", 1.0, False, False),
    ("operating_income_yoy_growth", "Operating Income YOY Growth", 0, True, False),
    ("ffo_margin", "FFO Margin (% Revenue)", None, True, False),
]

GROWTH_PANELS = [
    ("Revenue", "Revenue growth (Quartal, YoY)"),
    ("NetIncomeLoss", "Net Income Growth (Quartal, YoY)"),
    ("SharesOutstanding", "Shares Outstanding (Stock Dilution/Repurchase)"),
]

VALUATIONS_TO_PLOT = [
    ("pe_ratio", "P/E (TTM)", None, False),
    ("pb_ratio", "P/B", None, False),
    ("pfcf_ratio", "P/FCF (TTM)", None, False),
    ("ev_fcf", "EV/FCF (TTM)", None, False),
    ("ev_ebitda", "EV/EBITDA", None, False),
    ("ev_sales", "EV/Sales", None, False),
    ("dividend_yield", "dividend yield", None, True),
    ("p_tbv", "P/TBV", None, False),
    ("p_ppnr", "P/PPNR", None, False),
    ("p_core_earnings", "P/Core Earnings", None, False),
    ("p_ffo", "P/FFO (TTM)", None, False),
    ("peg_ratio", "PEG Ratio Revenue", None, False),
]

# Multiples where the denominator can plausibly approach zero (thin earnings/FCF/EBITDA),
# so the arithmetic mean of the ratio gets distorted by near-infinite spikes -- the harmonic
# mean (mean of the reciprocal "yield", inverted back) is used instead for the chart reference
# line and the rolling 5y snapshot average. Scope calibrated from real cached valuation_history
# data (median divergence 4-12% across these seven, materially larger than ev_sales' ~3% or
# dividend_yield's noise-dominated near-zero comparisons); ev_sales (revenue is never
# realistically near zero) and pe_to_revenue_growth (a ratio-of-ratios with its own dedicated
# guards, not a simple price/flow multiple) were checked and excluded.
HARMONIC_MEAN_CONCEPTS = {
    "pe_ratio", "pfcf_ratio", "ev_ebitda", "p_tbv", "p_ppnr", "p_core_earnings", "p_ffo",
}