TICKERS = ["SOFI"]

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
            {
                "type": "sum",
                "tags": ["LongTermDebtNoncurrent", "LongTermDebtCurrent", "NotesPayableCurrent"],
                "require": "LongTermDebtNoncurrent",
            },
            {"type": "tag", "tag": "LongTermDebtAndCapitalLeaseObligations"},
            {"type": "tag", "tag": "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities"},
            {"type": "tag", "tag": "UnsecuredLongTermDebt"},
            # --- current-portion-only tags: last resort, after every complete-debt source ---
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
        "capex_intensity","operating_leverage","operating_income_yoy_growth",
        "ffo_margin", "p_ffo",
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
        "capex_intensity","operating_leverage","operating_income_yoy_growth", "ffo_margin", "p_ffo",
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
        "rule_of_40", "pfcf_ratio", "ffo_margin", "p_ffo",
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
    # --- retroactive batch scan of the 58 reconciliation tickers, Group 1 (`standard`) ---
    "SOFI": {
        # SoFi (a fintech lender, not a traditional bank) tags its loan-loss provision
        # as FinancingReceivableExcludingAccruedInterestCreditLossExpenseReversal, not
        # any of the base financial-profile's provision tags. Without it, coverage was
        # 2 of 28 quarters (7.1%), both from ProvisionForLoanLossesExpensed. Verified:
        # the one date where both tags report (2022-03-31) matches EXACTLY
        # ($12,961,000), confirming this is the same underlying figure under SoFi's
        # own tag name, not a different concept. Adding it (kept after the existing
        # tags, so nothing already resolving changes) raises coverage to 19/28 (68%).
        # Scoped to SOFI only -- this tag name is specific to SoFi's XBRL filings and
        # is not expected to generalize to MS, GS, or any other `financial` ticker.
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
        # Pre-ASC-606 FIS tagged revenue as SalesRevenueServicesNet, which is not in
        # the base Revenue list, so everything before 2017-03-31 was missing (49%).
        # Appending it is purely additive (fallback = first tag per end-date wins) and
        # changes no existing value. Verified by reconstructing annual revenue from the
        # spliced quarterly series: FY2009 $3.735B, FY2019 $10.333B, FY2020 $12.553B,
        # all matching reported figures, with a continuous seam at 2016-12-31 -> 2017-03-31.
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
        # T. Rowe tags its real depreciation as DepreciationNonproduction, which is not
        # in the base D&A list. Without it the list fell through to
        # AmortizationOfIntangibleAssets -- a trivial line for this company -- and
        # resolved D&A to $100k-$200k per quarter for 2008-2013 when actual
        # depreciation was $15.3M-$25.1M. That is a wrong value, not a gap: off by
        # ~150-250x. Confirmed correct because where DepreciationDepletionAndAmortization
        # does resolve (2021-03-31 onward) it equals DepreciationNonproduction exactly.
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
        # Erie switched from PaymentsForProceedsFromProductiveAssets to
        # PaymentsToAcquireProductiveAssets in 2018. The two agree to the dollar in all
        # three overlapping quarters, so appending the older tag extends Capex back to
        # 2008 without altering anything. Its three net-proceeds (negative) quarters are
        # handled by the existing _NON_NEGATIVE_FLOW_CONCEPTS mask, which covers Capex.
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
}


def get_active_tickers() -> list[str]:
    """Every ticker the full-refresh pipeline should process. A commented-out
    TICKER_PROFILES line (e.g. `#"CVNA": "retail", doesnt work`) is this project's
    established "known broken, don't run this one" marker -- but that convention
    lives entirely in the source TEXT. Python's own parser strips comments before
    the dict literal is ever built, so the loaded TICKER_PROFILES dict already
    contains only the active entries; no extra parsing of config.py's source is
    needed at runtime. Verified independently (not assumed): a regex scan of this
    file's raw text for every `"TICKER": "profile"` occurrence, split by whether it
    is preceded by a `#` on its own line, finds the exact same active set as
    TICKER_PROFILES.keys() -- confirming CVNA/APA/NVR/PHM (the current commented-out
    entries) are correctly excluded and nothing else is silently missing.
    """
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
    "FCF_TTM": ["pfcf_ratio", "fcf_margin"],
    "EBITDA_TTM": ["ev_ebitda", "net_debt_to_ebitda"],
    "eps_ttm": ["pe_ratio"],
    "pe_ttm": ["pe_ratio"],
    "avg_pe_5y": ["pe_ratio"],
    "tangible_equity": ["p_tbv"],
    "ppnr_ttm": ["p_ppnr"],
    "core_earnings_ttm": ["p_core_earnings"],
    "fcf_ttm": ["pfcf_ratio", "fcf_margin"],
    "pfcf_ttm": ["pfcf_ratio"],
    "ebitda_ttm": ["ev_ebitda", "net_debt_to_ebitda"],
    "net_debt": ["net_debt_to_ebitda"],
    "ev": ["ev_ebitda", "ev_sales"],
}


def is_hidden(ticker: str, metric_name: str) -> bool:
    profile = TICKER_PROFILES.get(ticker, DEFAULT_PROFILE)
    hidden_set = PROFILE_HIDDEN.get(profile, set())
    if metric_name in hidden_set:
        return True
    consumers = _DERIVED_CONCEPT_CONSUMERS.get(metric_name)
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

CACHE_DIR = "cache"
DATA_DIR = "data"
FIGURE_DIR = "figures"

