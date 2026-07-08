import os
import json
import requests
from datetime import date


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
 
def get_company_info(ticker: str, cik : str, user_agent: str) -> dict:
    return fetch_or_cache(
        url=f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
        cache_path=f"cache/{ticker}_company_info.json",
        headers={"User-Agent": user_agent}
    )

def extract_annual_values(concept_data: dict) -> list[dict]:
    annual_values = {}

    for item in concept_data.get("units", {}).get("USD", []):
        # Kein "start" vorhanden? -> Stichtagswert (z.B. Bilanzposition), kein Zeitraum, überspringen
        if "start" not in item:
            continue

        start = date.fromisoformat(item["start"])
        end = date.fromisoformat(item["end"])
        days_diff = (end - start).days

        if item.get("fp") == "FY" and 350 <= days_diff <= 380:
            end_date = item["end"]
            if end_date not in annual_values or item["filed"] > annual_values[end_date]["filed"]:
                annual_values[end_date] = {"value": item["val"], "filed": item["filed"]}

    return [
        {"end": end, "value": data["value"], "filed": data["filed"]}
        for end, data in annual_values.items()
    ]