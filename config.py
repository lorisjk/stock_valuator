# config.py

TICKERS = ["AAPL", "MSFT", "NVDA"]

# SEC verlangt einen echten Kontakt im User-Agent, sonst 403
EDGAR_USER_AGENT = "Loris loris2006@gmx.de"

PERIOD="quarterly"

CONCEPT_CANDIDATES = {
    "Revenue": {
        "tags": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"],
        "point_in_time": False,
        "mode": "fallback",
    },
    "NetIncomeLoss": {
        "tags": ["NetIncomeLoss"],
        "point_in_time": False,
        "mode": "fallback",
    },
    "EPS": {
        "tags": ["EarningsPerShareDiluted", "EarningsPerShareBasic"],
        "point_in_time": False,
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
        "tags": ["NetCashProvidedByUsedInOperatingActivitiesContinuingOperations", "NetCashProvidedByUsedInOperatingActivities"],
        "point_in_time": False,
        "mode": "fallback",
    },
    "LongTermDebt": {
    "tags": ["LongTermDebtNoncurrent", "ConvertibleDebtNoncurrent", "LongTermDebtCurrent", "ConvertibleDebtCurrent"],
    "point_in_time": True,
    "mode": "sum",
    },
    "Capex": {
    "tags": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    "point_in_time": False,
    "mode": "fallback",
    },
    "CashAndEquivalents": {
    "tags": ["CashAndCashEquivalentsAtCarryingValue"],
    "point_in_time": True,
    "mode": "fallback",
    },
    "DepreciationAndAmortization": {
        "tags": ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization"],
        "fallback_sum_tags": ["Depreciation", "AmortizationOfIntangibleAssets"],
        "point_in_time": False,
        "mode": "fallback_sum",
    },
        "DividendsPerShare": {
    "tags": [ "CommonStockDividendsPerShareDeclared", "CommonStockDividendsPerShareCashPaid" ],
    "point_in_time": False,
    "mode": "fallback",
    }
}

TTM_CONCEPTS = [
    "Revenue",
    "NetIncomeLoss",
    "OperatingIncomeLoss",
    "EPS",
    "DividendsPerShare",
    "DepreciationAndAmortization",
    "OperatingCashFlow",
    "Capex",
]

CACHE_DIR = "cache"
DATA_DIR = "data"
FIGURE_DIR = "figures"