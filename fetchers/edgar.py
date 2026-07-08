import os
import json
import requests

def fetch_or_cache(url: str, cache_path: str, headers: dict) -> dict:
    if os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            return json.load(f)
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # wirft Fehler bei 4xx/5xx statt stillschweigend weiterzumachen
    data = response.json()
    
    with open(cache_path, "w") as f:
        json.dump(data, f)
    
    return data


def build_ticker_to_cik(mapping: dict) -> dict:
    cik_mapping = {}
    for entry in mapping.values():
        cik_mapping[entry["ticker"]] = str(entry["cik_str"]).zfill(10)
    return cik_mapping


def get_cik(ticker: str, cik_mapping: dict) -> str:
    if ticker not in cik_mapping:
        raise ValueError(f"Ticker {ticker} not found in mapping.")
    return cik_mapping[ticker]
 