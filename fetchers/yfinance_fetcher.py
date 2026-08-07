import pandas as pd
import yfinance as yf


def get_current_price_and_shares(ticker: str) -> dict:
    info = yf.Ticker(ticker).info
    return {
        "price": info.get("currentPrice"),
        "shares_outstanding": info.get("sharesOutstanding"),
    }

def get_price_history(ticker: str, start: str = "2005-01-01") -> pd.DataFrame:
    history = yf.Ticker(ticker).history(start=start)
    history = history.reset_index()  # Datum steht bei .history() im Index, nicht als Spalte
    history["ticker"] = ticker
    # "Stock Splits" ships in the same response as the prices, so the corporate-action
    # feed that corroborates share-count normalisation costs no extra request. It is
    # zero on every non-event day. Note the Close column is already split-adjusted --
    # yfinance back-adjusts regardless of auto_adjust -- so a split is visible only
    # here, never as a step in the price.
    if "Stock Splits" not in history.columns:
        history["Stock Splits"] = 0.0
    return history[["ticker", "Date", "Close", "Stock Splits"]].rename(
        columns={"Date": "date", "Close": "close", "Stock Splits": "stock_split"}
    )


def split_events(price_history: pd.DataFrame) -> pd.DataFrame:
    """The non-zero split ratios out of a price history, as (ticker, date, ratio)."""
    if "stock_split" not in price_history.columns:
        return pd.DataFrame(columns=["ticker", "date", "ratio"])
    events = price_history.loc[price_history["stock_split"] != 0, ["ticker", "date", "stock_split"]]
    return events.rename(columns={"stock_split": "ratio"}).reset_index(drop=True)