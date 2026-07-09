# config.py

TICKERS = ["AAPL", "MSFT", "NVDA"]

# SEC verlangt einen echten Kontakt im User-Agent, sonst 403
EDGAR_USER_AGENT = "Loris loris2006@gmx.de"

CONCEPT_CANDIDATES = {
    "Revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"],
    "NetIncomeLoss": ["NetIncomeLoss"],
    "EPS": ["EarningsPerShareDiluted"],
}

CACHE_DIR = "cache"
DATA_DIR = "data"