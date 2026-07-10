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
    return history[["ticker", "Date", "Close"]].rename(columns={"Date": "date", "Close": "close"})   