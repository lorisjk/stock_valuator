from dataclasses import dataclass

TICKERS = ["AAPL", "MSFT"]

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
    "ShareBasedCompensation": {
        "tags": [
            "ShareBasedCompensation",
            "AllocatedShareBasedCompensationExpense",
            "AdjustmentsToAdditionalPaidInCapitalSharebasedCompensationRequisiteServicePeriodRecognitionValue",
        ],
        "point_in_time": False,
        "mode": "fallback",
    },

    "IncomeTaxExpense": {
        "tags": ["IncomeTaxExpenseBenefit"],
        "point_in_time": False,
        "mode": "fallback",
    },
    "PretaxIncome": {
        "tags": [
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic",
        ],
        "point_in_time": False,
        "mode": "fallback",
    },

    "StockRepurchased": {
        "tags": [
            "PaymentsForRepurchaseOfCommonStock",
            "PaymentsForRepurchaseOfEquity",
            "StockRepurchasedDuringPeriodValue",
            "StockRepurchasedAndRetiredDuringPeriodValue",
            "TreasuryStockValueAcquiredCostMethod",
            "PartnersCapitalAccountTreasuryUnitsPurchases",
        ],
        "point_in_time": False,
        "mode": "fallback",
    },
    "StockIssued": {

        "tags": [
            "ProceedsFromIssuanceOfCommonStock",
            "StockIssuedDuringPeriodValueNewIssues",
            "ProceedsFromIssuanceOrSaleOfEquity",
            "ProceedsFromIssuanceOfSharesUnderIncentiveAndShareBasedCompensationPlansIncludingStockOptions",
            "ProceedsFromStockPlans",
            "ProceedsFromStockOptionsExercised",
            "ProceedsFromIssuanceOfSharesUnderIncentiveAndShareBasedCompensationPlans",
            "ProceedsFromSaleOfTreasuryStock",
            "StockIssuedDuringPeriodValueStockOptionsExercised",
            "StockIssuedDuringPeriodValueEmployeeStockPurchasePlan",
        ],
        "point_in_time": False,
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
    "ShareBasedCompensation",
    "IncomeTaxExpense",
    "PretaxIncome",
    "StockRepurchased",
    "StockIssued",
]

# How a <concept>_TTM value was derived. A series that mixes the two is not
# uniform and should not look uniform, so the label travels with the value in
# the facts frame's `ttm_source` column.
TTM_SOURCE_ROLLING = "quarterly_rolling"   # four consecutive quarters summed
TTM_SOURCE_ANNUAL = "annual_fact"          # one 12-month fact, taken as filed

# How FFO_TTM's real-estate-gains term was obtained. Same instrument as ttm_source
# and for the same reason: the term is absent for roughly 77% of REIT FFO periods
# and is filled with zero, which asserts "no disposals" from "not extracted". The
# two cannot be told apart from the pipeline's own output, so the assumption is
# recorded rather than hidden. See alignment_and_defaults_report.md.
FFO_GAINS_REPORTED = "reported"            # a filed GainLossOnSaleOfProperties_TTM
FFO_GAINS_IMPUTED_ZERO = "imputed_zero"    # no fact found; zero assumed

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
    "StockRepurchased": ["repurchase", "treasurystock", "buyback"],
    "StockIssued": ["issuanceofcommon", "stockissuedduringperiodvalue", "saleofequity"],
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
    "FANG": "energy", 
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
    "KKR": "alt_asset_manager",
    "ARES": "alt_asset_manager",
    "APO": "alt_asset_manager",
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
        "pfcf_ratio", "ev_fcf", "pfcf_ex_sbc", "net_debt_to_ebitda", "fcf_margin",
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
        # Banks do not file an operating-income line, so the growth panel would be
        # permanently empty rather than merely sparse (0 of 2 financial tickers
        # tested have any value). PPNR is the aggregate that replaces it here.
        # Only `financial` is listed: captive_finance and alt_asset_manager were
        # not tested, so they keep the panel rather than being hidden on a guess.
        "OperatingIncomeLoss_TTM",
    },
    "insurance_pc":{
        "pfcf_ttm",
        "ev_ebitda",
        "ev_sales",
        "pfcf_ratio",
        "ev_fcf",
        "pfcf_ex_sbc",
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
        "pfcf_ex_sbc",
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
        "rule_of_40", "pfcf_ratio", "ev_fcf", "pfcf_ex_sbc", "ffo_margin", "p_ffo",
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
        "pfcf_ex_sbc",
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
        "operating_margin", "net_debt_to_ebitda", "ev_ebitda",
        "fcf_margin", "pfcf_ratio", "ev_fcf", "pfcf_ex_sbc", "rule_of_40", "capex_intensity",
    },
}


PROFILE_CONCEPT_OVERRIDES = {
    "alt_asset_manager": {
        "StockholdersEquity": {
            "tags": [
                "StockholdersEquity",
                "LimitedPartnersCapitalAccount",
                "PartnersCapital",
            ],
            "point_in_time": True,
            "mode": "fallback",
        },
    },
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
        # NAREIT FFO removes gains on sales of *depreciable real property*, so every tag
        # here has to measure that and nothing wider. Ordered by scope, and `fallback`
        # takes the first tag that reports a given period end -- it never sums -- which
        # is what keeps a filer's pre-tax and net-of-tax figures for one gain from being
        # added together, and keeps the last entry from overriding a property-scoped one.
        #
        # Rejected on the evidence, not for tidiness: GainLossOnDispositionOfAssets and
        # GainLossOnDispositionOfAssets1 would have contributed more TTM values than every
        # accepted tag combined (+145 of +350) and measure something else -- AVB tags a
        # 2011 property gain of 294.8m and 13.7m of "assets", PLD 656.9m against 195.1m.
        # See ffo_gains_report.md.
        "GainLossOnSaleOfProperties": {
            "tags": [
                "GainLossOnSaleOfProperties",
                "GainsLossesOnSalesOfInvestmentRealEstate",
                "GainLossOnSaleOfPropertiesNetOfTax",
                "GainLossOnDispositionOfRealEstate",
                # net-of-tax before pre-tax: FFO starts from net income, so the figure that
                # flowed through it is the consistent one (and it is 8 REITs against 3)
                "GainLossOnSaleOfPropertiesNetOfApplicableIncomeTaxes",
                "GainLossOnSaleOfPropertiesBeforeApplicableIncomeTaxes",
                "GainLossOnDispositionOfRealEstateDiscontinuedOperations",
                "GainsLossesOnSalesOfOtherRealEstate",
                "GainLossOnDispositionOfProperty",
                "GainLossOnSaleOfProperty",
                "GainLossOnSaleOfTimberProperty",
                # last: for a data-centre, tower or storage REIT the operating real estate
                # is tagged as PP&E, and where a property-scoped tag also reports the period
                # the two agree to rounding (DLR, 9 of 9). Placed last so it only ever fills
                # a period nothing above it reported.
                "GainLossOnSaleOfPropertyPlantEquipment",
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
    "alt_asset_manager": {
        # Confirmed absent, not merely unmapped: BX reports no discrete operating-income
        # subtotal under any tag. Excluding it stops the coverage warning from reporting a
        # gap that no tag can close.
        "OperatingIncomeLoss",
    },
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
        # GainLossOnSaleOfProperties stood here: a one-off adding a single tag that the
        # reit profile's list now carries for every REIT. A ticker override replaces the
        # profile entry outright, so leaving it would have pinned this filer to the old,
        # narrower list.
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
        # GainLossOnSaleOfProperties stood here: a one-off adding a single tag that the
        # reit profile's list now carries for every REIT. A ticker override replaces the
        # profile entry outright, so leaving it would have pinned this filer to the old,
        # narrower list.
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
    "FCF_TTM": ["pfcf_ratio", "fcf_margin", "ev_fcf", "pfcf_ex_sbc"],
    "ShareBasedCompensation": ["pfcf_ex_sbc"],
    "ShareBasedCompensation_TTM": ["pfcf_ex_sbc"],
    "owner_fcf": ["pfcf_ex_sbc"],
    "IncomeTaxExpense": ["effective_tax_rate"],
    "IncomeTaxExpense_TTM": ["effective_tax_rate"],
    "PretaxIncome": ["effective_tax_rate"],
    "PretaxIncome_TTM": ["effective_tax_rate"],
    "low_tax_rate_flag": ["effective_tax_rate"],
    "StockRepurchased": ["share_count_jump_flag"],
    "StockRepurchased_TTM": ["share_count_jump_flag"],
    "StockIssued": ["share_count_jump_flag"],
    "StockIssued_TTM": ["share_count_jump_flag"],
    "EBITDA_TTM": ["ev_ebitda", "net_debt_to_ebitda"],
    "eps_ttm": ["pe_ratio"],
    "pe_ttm": ["pe_ratio"],
    "avg_pe_5y": ["pe_ratio"],
    "avg_pe_5y_median": ["pe_ratio"],
    "avg_pe_5y_diverges": ["pe_ratio"],
    "avg_pe_5y_n": ["pe_ratio"],
    "avg_pe_5y_history_too_short": ["pe_ratio"],
    # A P/E with a denominator attached is still a P/E. Every other thing built on GAAP
    # earnings already resolves through this map -- eps_ttm, pe_ttm, EPS_TTM_CALC and the
    # five avg_pe_5y fields above -- and pe_to_revenue_growth was the one that did not, so
    # the reit profile published a PEG whose numerator it had decided is not meaningful.
    "pe_to_revenue_growth": ["pe_ratio"],
    "avg_pfcf_5y": ["pfcf_ratio"],
    "avg_pfcf_5y_median": ["pfcf_ratio"],
    "avg_pfcf_5y_diverges": ["pfcf_ratio"],
    "avg_pfcf_5y_n": ["pfcf_ratio"],
    "avg_pfcf_5y_history_too_short": ["pfcf_ratio"],
    "avg_ev_ebitda_5y": ["ev_ebitda"],
    "avg_ev_ebitda_5y_median": ["ev_ebitda"],
    "avg_ev_ebitda_5y_diverges": ["ev_ebitda"],
    "avg_ev_ebitda_5y_n": ["ev_ebitda"],
    "avg_ev_ebitda_5y_history_too_short": ["ev_ebitda"],
    "avg_p_tbv_5y": ["p_tbv"],
    "avg_p_tbv_5y_median": ["p_tbv"],
    "avg_p_tbv_5y_diverges": ["p_tbv"],
    "avg_p_tbv_5y_n": ["p_tbv"],
    "avg_p_tbv_5y_history_too_short": ["p_tbv"],
    "avg_p_ppnr_5y": ["p_ppnr"],
    "avg_p_ppnr_5y_median": ["p_ppnr"],
    "avg_p_ppnr_5y_diverges": ["p_ppnr"],
    "avg_p_ppnr_5y_n": ["p_ppnr"],
    "avg_p_ppnr_5y_history_too_short": ["p_ppnr"],
    "avg_p_core_earnings_5y": ["p_core_earnings"],
    "avg_p_core_earnings_5y_median": ["p_core_earnings"],
    "avg_p_core_earnings_5y_diverges": ["p_core_earnings"],
    "avg_p_core_earnings_5y_n": ["p_core_earnings"],
    "avg_p_core_earnings_5y_history_too_short": ["p_core_earnings"],
    "avg_p_ffo_5y": ["p_ffo"],
    "avg_p_ffo_5y_median": ["p_ffo"],
    "avg_p_ffo_5y_diverges": ["p_ffo"],
    "avg_p_ffo_5y_n": ["p_ffo"],
    "avg_p_ffo_5y_history_too_short": ["p_ffo"],
    "tangible_equity": ["p_tbv"],
    "ppnr_ttm": ["p_ppnr"],
    "core_earnings_ttm": ["p_core_earnings"],
    "fcf_ttm": ["pfcf_ratio", "fcf_margin"],
    "pfcf_ttm": ["pfcf_ratio"],
    "ebitda_ttm": ["ev_ebitda", "net_debt_to_ebitda"],
    "net_debt": ["net_debt_to_ebitda"],
    "ev": ["ev_ebitda", "ev_sales"],
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

# GROWTH_BASE_PANELS / GROWTH_PROFILE_EXTRA / get_growth_panels() stood here: an
# earlier sketch of per-profile growth panels, with zero consumers. It named 15
# concepts (fcf_growth, nii_growth, ffo_growth, equity_growth, ...) of which not
# one existed in any dataframe or in this registry -- an invented naming scheme
# that was never wired to data. The growth entries in METRICS supersede it, keyed
# by real concept names and made per-profile by is_hidden rather than by a second
# visibility mechanism, so it is deleted rather than left as a third parallel one.

CACHE_DIR = "cache"
DATA_DIR = "data"
FIGURE_DIR = "figures"



# FOR FIGURES:PY
#
# METRICS is the single source of truth for everything that gets plotted. The
# five structures figures.py has always imported (FUNDAMENTALS_TO_PLOT,
# VALUATIONS_TO_PLOT, GROWTH_PANELS, QUARTERLY_COUNTERPART,
# HARMONIC_MEAN_CONCEPTS) are derived from it further down, so existing
# consumers keep working unchanged. Add a metric here and nowhere else.

CHART_FUNDAMENTALS = "fundamentals"
CHART_VALUATION = "valuation"
CHART_GROWTH = "growth"
CHART_RAW_FACTS = "raw_facts"

# What an id in a given chart actually names, and which dataframe column holds
# its values. Declared once rather than repeated on 45 entries, but reachable
# per metric via Metric.id_namespace / Metric.value_column.
CHART_SPECS = {
    CHART_FUNDAMENTALS: {"id_namespace": "metric", "value_column": "value"},
    CHART_VALUATION: {"id_namespace": "metric", "value_column": "value"},
    CHART_GROWTH: {"id_namespace": "xbrl_concept", "value_column": "yoy_growth"},
    CHART_RAW_FACTS: {"id_namespace": "xbrl_concept", "value_column": "value"},
}

# `label` is the string rendered onto the chart today and must stay byte-identical.
# It is registered as the primary language; some entries mix German words
# ("Quartal"), which is preserved verbatim -- relabelling is a separate job.
LANGUAGE_PRIMARY = "en"


@dataclass(frozen=True)
class Metric:
    """One plottable metric.

    Frozen dataclass rather than a dict: a missing required field or a typo'd
    field name raises TypeError at import, instead of a dict's .get() quietly
    returning None and producing a blank axis at render time.
    """
    id: str
    chart: str
    label: str
    ref_line: float | int | None = None
    percent: bool = False
    quarterly: bool = False   # a <id>_quarterly series exists
    harmonic: bool = False    # mean line uses the harmonic mean
    label_de: str | None = None
    # Encyclopedia text. Optional with a None default, so every structure derived
    # from this class keeps its shape -- but optional means a new metric can
    # silently arrive undocumented, which is what undocumented_metrics() below is
    # for. `formula` names the actual concepts and period basis the pipeline uses,
    # never the textbook definition: several of these deliberately differ.
    description: str | None = None
    formula: str | None = None

    @property
    def documented(self) -> bool:
        return bool(self.description and self.formula)

    @property
    def id_namespace(self) -> str:
        return CHART_SPECS[self.chart]["id_namespace"]

    @property
    def value_column(self) -> str:
        return CHART_SPECS[self.chart]["value_column"]

    def label_for(self, language: str = LANGUAGE_PRIMARY) -> str:
        """Label in `language`, falling back to the primary label.

        Never returns an empty string: an unpopulated translation falls back
        rather than blanking an axis title.
        """
        if language != LANGUAGE_PRIMARY:
            translated = getattr(self, f"label_{language}", None)
            if translated:
                return translated
        return self.label


METRICS = [
    # --- fundamentals: order is panel order ---
    Metric("revenue_yoy_growth", CHART_FUNDAMENTALS, "Revenue growth", 0, percent=True,
           description="How much larger trailing-twelve-month sales are than a year ago. "
                       "The top line, and the number hardest to influence through accounting choices.",
           formula="calculate_growth on `Revenue_TTM`, 4-quarter lag. `Revenue` is mapped "
                   "per profile -- for `financial` it is RevenuesNetOfInterestExpense, not gross revenue."),
    Metric("income_yoy_growth", CHART_FUNDAMENTALS, "Income growth", 0, percent=True,
           description="The same year-over-year comparison applied to profit after everything.",
           formula="calculate_growth on `NetIncomeLoss_TTM`, 4-quarter lag."),
    Metric("operating_margin", CHART_FUNDAMENTALS, "Operating Margin", None, percent=True, quarterly=True,
           description="Cents of operating profit per dollar of sales, before interest and tax.",
           formula="`OperatingIncomeLoss_TTM` / `Revenue_TTM`. A self-relative scale guard blanks "
                   "periods where Revenue_TTM falls below 10% of its own max over the surrounding "
                   "±8 quarters, which suppresses ratios built on a partially-filed quarter."),
    Metric("roe", CHART_FUNDAMENTALS, "Return on Equity", None, percent=True,
           description="Profit earned per dollar of shareholders' equity.",
           formula="`NetIncomeLoss_TTM` / `StockholdersEquity`. Equity is the point-in-time "
                   "balance, NOT a period average. Requires positive equity, and equity of at "
                   "least 1% of Revenue_TTM."),
    Metric("debt_to_equity", CHART_FUNDAMENTALS, "Debt-to-Equity Ratio", None,
           description="Long-term borrowings measured against the equity cushion beneath them.",
           formula="`LongTermDebt` / `StockholdersEquity`, both point-in-time. Long-term debt "
                   "only -- short-term borrowings are not included. Requires positive equity of "
                   "at least 5% of LongTermDebt."),
    Metric("payout_ratio", CHART_FUNDAMENTALS, "Payout Ratio", None, percent=True, quarterly=True,
           description="The share of earnings paid out as dividends.",
           formula="`DividendsPerShare_TTM` / `EPS_TTM_CALC`, requires a positive denominator. "
                   "EPS_TTM_CALC is the pipeline's own figure (see P/E), not reported EPS."),
    Metric("fcf_margin", CHART_FUNDAMENTALS, "Free Cash Flow Margin", None, percent=True, quarterly=True,
           description="Cents of free cash flow per dollar of sales -- how much of the revenue "
                       "actually becomes spendable cash.",
           formula="(`OperatingCashFlow_TTM` − `Capex_TTM`) / `Revenue_TTM`, with the same "
                   "±8-quarter self-relative revenue guard as the operating margin."),
    Metric("net_debt_to_ebitda", CHART_FUNDAMENTALS, "Net Debt / EBITDA", 0,
           description="Years of current earnings it would take to repay borrowings net of cash.",
           formula="(`LongTermDebt` − `CashAndEquivalents`) / (`OperatingIncomeLoss_TTM` + "
                   "`DepreciationAndAmortization_TTM`). Blanked when |EBITDA| < $10m or the "
                   "result exceeds ±60."),
    Metric("rule_of_40", CHART_FUNDAMENTALS, "Rule of 40", 0.4, percent=True,
           description="Growth plus cash-flow margin, the software-industry trade-off between "
                       "growing and being profitable. Above 40% is the convention.",
           formula="`revenue_yoy_growth` + `fcf_margin`, both as fractions -- so the 0.4 "
                   "reference line is the conventional 40%. Inherits the TTM basis of both."),
    Metric("net_interest_margin", CHART_FUNDAMENTALS, "Net Interest Margin", None, percent=True,
           description="A bank's spread: interest earned minus interest paid, per dollar of assets.",
           formula="`NetInterestIncome_TTM` / `Assets`. Denominator is TOTAL assets at period "
                   "end, not average earning assets, so the level runs below the conventional NIM."),
    Metric("efficiency_ratio", CHART_FUNDAMENTALS, "Efficiency Ratio", None, percent=True, quarterly=True,
           description="What a bank spends to earn a dollar of revenue. Lower is better; this "
                       "is the one ratio where a falling line is the good news.",
           formula="`NoninterestExpense_TTM` / `Revenue_TTM`. For the `financial` profile "
                   "Revenue maps to RevenuesNetOfInterestExpense, which makes this close to the "
                   "conventional bank efficiency ratio."),
    Metric("roa", CHART_FUNDAMENTALS, "Return on Assets", None, percent=True,
           description="Profit per dollar of assets, the return measure that ignores leverage.",
           formula="`NetIncomeLoss_TTM` / `Assets`, assets point-in-time rather than averaged."),
    Metric("equity_to_assets", CHART_FUNDAMENTALS, "Equity / Assets", None, percent=True,
           description="The simple capital ratio: what fraction of the balance sheet is "
                       "shareholders' money rather than borrowed.",
           formula="`StockholdersEquity` / `Assets`, both point-in-time. Book equity, not a "
                   "regulatory capital measure such as CET1."),
    Metric("provision_ratio", CHART_FUNDAMENTALS, "Provision/Revenue", 0, percent=True, quarterly=True,
           description="How much of revenue is being set aside against expected credit losses.",
           formula="`ProvisionForCreditLosses_TTM` / `Revenue_TTM`. Denominator is revenue, not "
                   "average loans, so this is not the conventional provisioning rate."),
    Metric("combined_ratio", CHART_FUNDAMENTALS, "Combined Ratio", 1.0, percent=True, quarterly=True,
           description="An insurer's claims and expenses per dollar of premium. Above 100% means "
                       "underwriting loses money, and the investment income has to make up for it.",
           formula="`BenefitsLossesAndExpenses_TTM` / `EarnedPremiums_TTM` -- a single reported "
                   "aggregate over premiums, not losses and expenses summed separately."),
    Metric("loss_ratio", CHART_FUNDAMENTALS, "Loss Ratio", None, percent=True, quarterly=True,
           description="The claims half of the combined ratio: payouts per dollar of premium.",
           formula="`IncurredLosses_TTM` / `EarnedPremiums_TTM`."),
    Metric("expense_ratio", CHART_FUNDAMENTALS, "Expense Ratio", None, percent=True, quarterly=True,
           description="The cost half of the combined ratio: what it costs to write the business.",
           formula="`combined_ratio` − `loss_ratio`, so TTM like both of them. Obtained by "
                   "subtraction, not from a reported expense figure, so it absorbs any "
                   "difference in how the two source tags are drawn."),
    Metric("net_investment_yield", CHART_FUNDAMENTALS, "Net Investment Yield", None, percent=True,
           description="What an insurer earns on the float it holds between premium and claim.",
           formula="`NetInvestmentIncome_TTM` / `Investments`, investments point-in-time."),
    Metric("reserve_growth", CHART_FUNDAMENTALS, "Reserve Growth", 0, percent=True,
           description="Year-over-year change in the reserve set aside for future claims.",
           formula="calculate_growth on `ClaimsReserve`, 4-quarter lag, point-in-time balance."),
    Metric("inventory_turnover", CHART_FUNDAMENTALS, "Inventory Turnover (x/Year)", None,
           description="How many times a year the shelves are emptied and refilled.",
           formula="`CostOfRevenue_TTM` / `Inventory`. Period-end inventory, not the average "
                   "balance the textbook ratio uses."),
    Metric("dio", CHART_FUNDAMENTALS, "Days Inventory Outstanding", None,
           description="Days of stock on hand at the current rate of sale.",
           formula="`Inventory` / `CostOfRevenue_TTM` × 365, period-end inventory."),
    Metric("dso", CHART_FUNDAMENTALS, "Days Sales Outstanding", None,
           description="Days between making a sale and being paid for it.",
           formula="`AccountsReceivable` / `Revenue_TTM` × 365, period-end receivables."),
    Metric("dpo", CHART_FUNDAMENTALS, "Days Payable Outstanding", None,
           description="Days the company takes to pay its own suppliers.",
           formula="`AccountsPayable` / `CostOfRevenue_TTM` × 365, period-end payables."),
    Metric("cash_conversion_cycle", CHART_FUNDAMENTALS, "Cash Conversion Cycle (Days)", 0,
           description="Days of cash tied up in working capital. Negative means suppliers "
                       "finance the business -- customers pay before the bills come due.",
           formula="`dio` + `dso` − `dpo`; inherits the period-end balances of all three."),
    Metric("rd_intensity", CHART_FUNDAMENTALS, "R&D Intensity (% Revenue)", None, percent=True, quarterly=True,
           description="The share of revenue reinvested into research and development.",
           formula="`ResearchAndDevelopment_TTM` / `Revenue_TTM`."),
    Metric("capex_intensity", CHART_FUNDAMENTALS, "CapEx Intensity (% Revenue)", None, percent=True, quarterly=True,
           description="The share of revenue spent on property, plant and equipment.",
           formula="`Capex_TTM` / `Revenue_TTM`."),
    Metric("operating_leverage", CHART_FUNDAMENTALS, "Operating Leverage", 1.0,
           description="How much faster operating profit moves than sales. Above 1 means growth "
                       "is amplified on the way down as well as up.",
           formula="`operating_income_yoy_growth` / `revenue_yoy_growth`, both TTM growth rates. "
                   "Blanked when revenue growth is under ±2% (a near-zero denominator) or "
                   "the result exceeds ±15."),
    Metric("operating_income_yoy_growth", CHART_FUNDAMENTALS, "Operating Income YOY Growth", 0, percent=True,
           description="Year-over-year change in operating profit.",
           formula="calculate_growth on `OperatingIncomeLoss_TTM`, 4-quarter lag."),
    Metric("ffo_margin", CHART_FUNDAMENTALS, "FFO Margin (% Revenue)", None, percent=True, quarterly=True,
           description="Funds from operations per dollar of revenue -- the REIT profitability "
                       "measure, since depreciation makes reported net income misleading for property.",
           formula="`FFO_TTM` / `Revenue_TTM`, where FFO_TTM = `NetIncomeLoss_TTM` + "
                   "`DepreciationAndAmortization_TTM` − `GainLossOnSaleOfProperties_TTM`. Total "
                   "D&A is added back, not only real-estate depreciation as NAREIT specifies."),

    # --- valuation: order is panel order ---
    Metric("pe_ratio", CHART_VALUATION, "P/E (TTM)", None, harmonic=True,
           description="Price per dollar of annual earnings -- the years of current profit you "
                       "are paying for one share.",
           formula="close / `EPS_TTM_CALC`, where EPS_TTM_CALC = `NetIncomeLoss_TTM` / "
                   "`SharesOutstanding`. Computed, not the reported diluted EPS, and the share "
                   "count is normally the diluted weighted average. Only positive EPS is plotted."),
    Metric("pb_ratio", CHART_VALUATION, "P/B", None,
           description="Market value per dollar of book equity.",
           formula="market cap / `StockholdersEquity`, equity point-in-time at the period end, "
                   "positive only. Additionally blanked when TangibleEquity is negative, since "
                   "book value carried by goodwill is not a meaningful denominator."),
    Metric("pfcf_ratio", CHART_VALUATION, "P/FCF (TTM)", None, harmonic=True,
           description="Price per dollar of free cash flow -- the earnings equivalent that is "
                       "harder to manipulate.",
           formula="market cap / `FCF_TTM`, where FCF_TTM = `OperatingCashFlow_TTM` − `Capex_TTM`. "
                   "Positive FCF only."),
    Metric("ev_fcf", CHART_VALUATION, "EV/FCF (TTM)", None,
           description="The same, but priced as if you bought the whole company including its debt.",
           formula="EV / `FCF_TTM`, EV = market cap + `LongTermDebt` − `CashAndEquivalents`. "
                   "Short-term debt, minority interest and preferred are not in this EV."),
    Metric("pfcf_ex_sbc", CHART_VALUATION, "P/FCF ex-SBC (TTM)", None,
           description="P/FCF after treating stock-based compensation as the real cost it is. "
                       "The gap against plain P/FCF is how much of the cash flow is paid for in shares.",
           formula="market cap / (`FCF_TTM` − `ShareBasedCompensation_TTM`)."),
    Metric("ev_ebitda", CHART_VALUATION, "EV/EBITDA", None, harmonic=True,
           description="Enterprise value per dollar of pre-depreciation operating profit; the "
                       "standard cross-company multiple because it is indifferent to capital structure.",
           formula="EV / `EBITDA_TTM`, EBITDA_TTM = `OperatingIncomeLoss_TTM` + "
                   "`DepreciationAndAmortization_TTM` (built up from operating income, not from net income)."),
    Metric("ev_sales", CHART_VALUATION, "EV/Sales", None,
           description="Enterprise value per dollar of revenue -- the fallback multiple when a "
                       "company has no profit to divide by.",
           formula="EV / `Revenue_TTM`."),
    Metric("dividend_yield", CHART_VALUATION, "dividend yield", None, percent=True,
           description="Cash dividends over the last year as a percentage of the share price.",
           formula="`DividendsPerShare_TTM` / close. Dividends declared per share; buybacks are "
                   "not included."),
    Metric("p_tbv", CHART_VALUATION, "P/TBV", None, harmonic=True,
           description="Price per dollar of book value with goodwill stripped out -- the standard "
                       "bank and insurer multiple, because acquired goodwill absorbs losses first.",
           formula="market cap / (`StockholdersEquity` − `Goodwill`), both point-in-time at the "
                   "period end. Only goodwill is removed; other intangibles stay in, so this "
                   "sits above a strict tangible book value."),
    Metric("p_ppnr", CHART_VALUATION, "P/PPNR", None, harmonic=True,
           description="Price against a bank's earnings power before credit losses -- what it "
                       "earns in a normal year, independent of where it is in the credit cycle.",
           formula="market cap / `PPNR`, PPNR = `NetInterestIncome_TTM` + `NoninterestIncome_TTM` "
                   "− `NoninterestExpense_TTM`."),
    Metric("p_core_earnings", CHART_VALUATION, "P/Core Earnings", None, harmonic=True,
           description="Price against insurance earnings with investment gains removed, since "
                       "realised gains are a timing choice rather than underwriting performance.",
           formula="market cap / `CoreOperatingEarnings`, = `NetIncomeLoss_TTM` − "
                   "`RealizedInvestmentGains_TTM`. A subtraction of realised gains only."),
    Metric("p_ffo", CHART_VALUATION, "P/FFO (TTM)", None, harmonic=True,
           description="The REIT equivalent of P/E, using funds from operations because property "
                       "depreciation is an accounting charge rather than an economic one.",
           formula="market cap / `FFO_TTM` (see FFO Margin for the FFO build-up). "),
    Metric("pe_to_revenue_growth", CHART_VALUATION, "PE to Revenue Growth", None,
           description="A PEG-style ratio: the P/E divided by the growth rate that justifies it. "
                       "Below 1 is the conventional 'growth is cheap' threshold.",
           formula="`pe_ratio` / (revenue growth in percentage points). Uses REVENUE growth, not "
                   "earnings growth as a textbook PEG does. That growth rate is also its own "
                   "figure -- Revenue_TTM.pct_change(4) computed inside build_valuation_history, "
                   "not the guarded calculate_growth used elsewhere. Requires growth above 2%; "
                   "results beyond ±30 are dropped."),

    # --- growth: ids are XBRL concept names, values read from `yoy_growth`.
    #     ref_line/percent match what build_growth draws (a 0 line, percent axis).
    #
    #     Per-profile visibility runs through is_hidden like everywhere else -- there
    #     is no growth-specific visibility mechanism. The three sector aggregates
    #     below are *derived* concepts, so _DERIVED_CONCEPT_CONSUMERS already resolves
    #     them to exactly the right profiles at zero cost in PROFILE_HIDDEN entries:
    #     PPNR -> financial only, FFO_TTM -> reit only, CoreOperatingEarnings ->
    #     the two insurance profiles. Registering the raw sector tags instead
    #     (NetInterestIncome_TTM, EarnedPremiums_TTM, ...) would have cost 22-23
    #     hide entries each, since PROFILE_HIDDEN is a negative list.
    Metric("Revenue", CHART_GROWTH, "Revenue growth (Quartal, YoY)", 0, percent=True,
           description="Sales in this quarter against the same quarter a year earlier.",
           formula="Single quarter as filed, against the quarter ~365 days earlier."),
    Metric("NetIncomeLoss", CHART_GROWTH, "Net Income Growth (Quartal, YoY)", 0, percent=True,
           description="Quarterly profit against the same quarter a year earlier. Gappy by "
                       "design: a loss quarter on either side produces no value at all.",
           formula="Single quarter as filed."),
    Metric("SharesOutstanding", CHART_GROWTH, "Shares Outstanding (Stock Dilution/Repurchase)", 0, percent=True,
           description="Change in the share count -- negative means buybacks, positive means "
                       "dilution. Every per-share figure moves with this line.",
           formula="Point-in-time share count, normally the diluted weighted average, restated "
                   "onto the current split basis by parse_edgar._apply_split_basis -- which "
                   "applies only splits the corporate-action feed reports and the filer's own "
                   "restatements confirm, so an uncorroborated period is left as filed."),
    Metric("EPS_TTM_CALC", CHART_GROWTH, "EPS Growth (TTM, YoY)", 0, percent=True,
           description="Growth in earnings per share on a trailing-twelve-month basis -- profit "
                       "growth and share-count change combined into the number that reaches the shareholder.",
           formula="`NetIncomeLoss_TTM` / `SharesOutstanding`, the pipeline's own EPS."),
    Metric("FCF_TTM", CHART_GROWTH, "Free Cash Flow Growth (TTM, YoY)", 0, percent=True,
           description="Growth in trailing free cash flow.",
           formula="`OperatingCashFlow_TTM` − `Capex_TTM`."),
    Metric("OperatingIncomeLoss_TTM", CHART_GROWTH, "Operating Income Growth (TTM, YoY)", 0, percent=True,
           description="Growth in trailing operating profit, before interest and tax.",
           formula="`OperatingIncomeLoss_TTM`. Hidden for `financial`: banks do not file an "
                   "operating-income line, so the panel would always be empty."),
    Metric("StockholdersEquity", CHART_GROWTH, "Equity Growth (Quartal, YoY)", 0, percent=True,
           description="Growth in book equity -- retained profit less dividends and buybacks. "
                       "The compounding measure for a bank or insurer.",
           formula="Point-in-time `StockholdersEquity`."),
    Metric("PPNR", CHART_GROWTH, "PPNR Growth (TTM, YoY)", 0, percent=True,
           description="Growth in a bank's pre-provision earnings power.",
           formula="`NetInterestIncome_TTM` + `NoninterestIncome_TTM` − `NoninterestExpense_TTM`."),
    Metric("CoreOperatingEarnings", CHART_GROWTH, "Core Operating Earnings Growth (TTM, YoY)", 0, percent=True,
           description="Growth in insurance earnings excluding realised investment gains.",
           formula="`NetIncomeLoss_TTM` − `RealizedInvestmentGains_TTM`."),
    Metric("FFO_TTM", CHART_GROWTH, "FFO Growth (TTM, YoY)", 0, percent=True,
           description="Growth in a REIT's funds from operations.",
           formula="`NetIncomeLoss_TTM` + `DepreciationAndAmortization_TTM` − "
                   "`GainLossOnSaleOfProperties_TTM`."),

   

    ]




# Documented once and referenced by every growth panel, rather than repeated on ten
# entries. Read off calculate_growth() and main.add_growth_column().
GROWTH_MECHANISM_NOTE = """
Every growth panel is produced by the same function, and its guards are the reason
you see gaps rather than nonsense.

- **4-quarter lag.** Each period is compared against the observation closest to
  365 days earlier (tolerance ±45 days), so a quarterly series is compared like
  for like -- Q3 against Q3 -- and seasonality is not what you are looking at.
- **Both values must be positive.** If either the current or the prior figure is
  zero or negative, no growth value is produced. A percentage change across zero
  has no meaning, so the pipeline declines to invent one. This is why loss-making
  quarters leave holes in the net-income and cash-flow panels.
- **A minimum-base guard.** The prior value must be at least 33% of the current
  one, which caps a reported growth rate at about +200% and suppresses the
  explosions that come from a near-zero base. Seven balance-sheet concepts --
  Capex, Goodwill, CashAndEquivalents, Inventory, LongTermDebt,
  ProvisionForCreditLosses and TangibleEquity -- loosen this to 5%, because
  those legitimately grow from a small base.
- **TTM versus quarterly.** Panels labelled *TTM* run on a rolling four-quarter
  sum; those labelled *Quartal* run on the single quarter as filed. Measured
  across this ticker set, a quarterly growth series is roughly 1.1--2.2x more
  volatile than the TTM series of the same concept.
- **Annual-cadence series.** Some filers disclose an item only once a year --
  share-based compensation and pre-tax income are the common cases. There is then
  nothing quarterly to sum, so the pipeline reads the 12-month fact as filed
  instead, and the series carries one point per year. Its growth panel therefore
  shows one value per year too. **That is complete coverage of what the filer
  published, not missing data**, and it is the distinction the marked columns in
  the data tab exist to make: a column marked *annual cadence* is sparse by the
  filer's choice, an unmarked sparse column is a gap. Which path produced each
  value is recorded per row in the facts frame's `ttm_source` column
  (`quarterly_rolling` / `annual_fact`); the two are disjoint by construction, so
  no series mixes them.
- Two concepts are excluded from growth entirely -- GainLossOnSaleOfProperties
  and RealizedInvestmentGains -- because their level swings sign freely.
"""

VALUATION_MECHANISM_NOTE = """
All valuation multiples share one price convention and one averaging convention.

- **Which price.** Each period end is matched to the most recent daily close at
  or before it (a backward as-of join on the yfinance history), so the multiple
  is what the market was charging on the day the period closed -- not today's
  price applied to an old balance sheet.
- **Market cap and enterprise value.** Market cap is that close times the share
  count from EDGAR, falling back to yfinance where EDGAR reports none.
  EV = market cap + LongTermDebt − CashAndEquivalents. Short-term debt, minority
  interest and preferred stock are *not* in this enterprise value.
- **The mean line.** Multiples that compound multiplicatively use a **harmonic**
  mean, which is the correct average for a ratio and is not dragged upward by a
  few expensive quarters; the rest use an arithmetic mean. The harmonic set is
  read from the registry, not hardcoded. Only positive observations enter either.
- **The green marker** is the current value: today's price against the latest
  available fundamentals. It is a separate trace, deliberately excluded from the
  mean line so the historical benchmark is not contaminated by the value being
  judged against it, and it is hidden when an as-of date earlier than the
  snapshot is selected.
- **A scale guard** blanks any multiple whose denominator falls below 0.1% of
  Revenue_TTM, which removes the ratios that explode on a near-zero denominator.
"""


def _index_metrics(metrics: list[Metric]) -> dict[str, Metric]:
    """Fail loudly at import on a duplicate id or an unknown chart."""
    index = {}
    for metric in metrics:
        if metric.chart not in CHART_SPECS:
            raise ValueError(
                f"METRICS: '{metric.id}' has unknown chart {metric.chart!r}; "
                f"expected one of {sorted(CHART_SPECS)}"
            )
        if metric.id in index:
            raise ValueError(
                f"METRICS: duplicate id {metric.id!r} "
                f"(charts {index[metric.id].chart!r} and {metric.chart!r})"
            )
        index[metric.id] = metric
    return index


METRICS_BY_ID = _index_metrics(METRICS)


def _metrics_for(chart: str) -> list[Metric]:
    return [m for m in METRICS if m.chart == chart]


def undocumented_metrics() -> list[str]:
    """Registry ids missing a description or a formula.

    The documentation fields are optional so that adding a metric cannot break
    any derived structure -- but optional means a new metric can arrive
    undocumented and render blank. This is what makes that detectable instead:
    the app lists these honestly rather than showing an empty section, and the
    verification asserts against it.
    """
    return [m.id for m in METRICS if not m.documented]


def profile_visibility(chart: str | None = None) -> dict[str, dict[str, bool]]:
    """{profile: {metric_id: visible}} for every profile, straight from is_hidden.

    Generated, never hand-maintained: a written-down table would drift from the
    code within one change, and the point of this mapping is that it is
    authoritative.

    is_hidden takes a ticker, but it uses that ticker only to look up its
    profile -- PROFILE_HIDDEN and _DERIVED_CONCEPT_CONSUMERS are both keyed by
    profile, and there is no per-ticker override in that path. So a synthetic
    ticker name that is absent from TICKER_PROFILES cannot be used (it would
    resolve to DEFAULT_PROFILE); a representative real ticker per profile is
    used instead, and every ticker of a profile provably gives the same answer.
    """
    metrics = [m for m in METRICS if chart is None or m.chart == chart]
    representative = {}
    for ticker, profile in TICKER_PROFILES.items():
        representative.setdefault(profile, ticker)
    representative.setdefault(DEFAULT_PROFILE, next(iter(TICKER_PROFILES)))
    return {
        profile: {m.id: not is_hidden(ticker, m.id) for m in metrics}
        for profile, ticker in sorted(representative.items())
    }


def get_plottable_metrics(
    chart: str,
    ticker: str | None = None,
    language: str = LANGUAGE_PRIMARY,
) -> list[tuple[str, str]]:
    """(id, label) pairs for a chart type, in panel order -- for a UI picker.

    With a ticker, the list is already narrowed by `is_hidden`; without one it is
    the full catalogue. Narrowing only, never bypassing: this is the same rule
    the figure builders follow, so a picker cannot offer a metric the chart would
    then refuse to draw.
    """
    if chart not in CHART_SPECS:
        raise ValueError(f"unknown chart {chart!r}; expected one of {sorted(CHART_SPECS)}")
    return [
        (m.id, m.label_for(language))
        for m in _metrics_for(chart)
        if ticker is None or not is_hidden(ticker, m.id)
    ]


# --- derived compatibility layer -------------------------------------------
# Everything below is generated from METRICS and must stay equal to the literals
# these names held before the registry existed. The legacy symlog flag is not
# part of the registry (no metric ever set it and nothing renders it); the
# 5-tuple below supplies its constant False positionally.

FUNDAMENTALS_TO_PLOT = [
    (m.id, m.label, m.ref_line, m.percent, False) for m in _metrics_for(CHART_FUNDAMENTALS)
]

VALUATIONS_TO_PLOT = [
    (m.id, m.label, m.ref_line, m.percent) for m in _metrics_for(CHART_VALUATION)
]

GROWTH_PANELS = [(m.id, m.label) for m in _metrics_for(CHART_GROWTH)]



QUARTERLY_COUNTERPART = {m.id: f"{m.id}_quarterly" for m in METRICS if m.quarterly}

HARMONIC_MEAN_CONCEPTS = {m.id for m in METRICS if m.harmonic}