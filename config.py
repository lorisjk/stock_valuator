TICKERS = ["MSFT"]

EDGAR_USER_AGENT = "Loris loris2006@gmx.de"

PERIOD = "quarterly"

CONCEPT_CANDIDATES = {
    "Revenue": {
        "tags": [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
        ],
        "point_in_time": False,
        "mode": "fallback",
    },
    "NetIncomeLoss": {
        "tags": ["NetIncomeLoss"],
        "point_in_time": False,
        "mode": "fallback",
    },

    "SharesOutstanding": {
        "tags": [
            "WeightedAverageNumberOfDilutedSharesOutstanding",
            "WeightedAverageNumberOfSharesOutstandingBasic",
        ],
        "point_in_time": True,
        "mode": "fallback",
    },
    "StockholdersEquity": {
        "tags": ["StockholdersEquity"],
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
    "tags": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
    ],
    "fallback_sum_tags": ["Depreciation", "AmortizationOfIntangibleAssets"],
    "point_in_time": False,
    "mode": "fallback_sum",
    },
    "LongTermDebt": {
    "tags": [
        "LongTermDebtNoncurrent",
        "ConvertibleDebtNoncurrent",
        "ConvertibleLongTermNotesPayable",
        "LongTermDebtCurrent",
        "ConvertibleDebtCurrent",
        "ConvertibleNotesPayableCurrent",
        "NotesPayableCurrent"
    ],
    "point_in_time": True,
    "mode": "sum",
    },
    "CashAndEquivalents": {
        "tags": ["CashAndCashEquivalentsAtCarryingValue"],
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
}

TTM_CONCEPTS = [
    "Revenue",
    "NetIncomeLoss",
    "OperatingIncomeLoss",
    "OperatingCashFlow",
    "Capex",
    "DepreciationAndAmortization",
    "DividendsPerShare",
]

SEARCH_HINTS = {
    "Revenue": ["revenue", "sales"],
    "NetIncomeLoss": ["netincome"],
    "OperatingIncomeLoss": ["operatingincome"],
    "OperatingCashFlow": ["operatingactivities"],
    "Capex": ["acquire", "propertyplant"],
    "DepreciationAndAmortization": ["depreciation", "amortization"],
    "LongTermDebt": ["debt", "notes", "borrowings"],
    "CashAndEquivalents": ["cashandcash"],
    "StockholdersEquity": ["stockholdersequity"],
    "SharesOutstanding": ["sharesoutstanding"],
    "DividendsPerShare": ["dividendspershare"],
}

CACHE_DIR = "cache"
DATA_DIR = "data"
FIGURE_DIR = "figures"