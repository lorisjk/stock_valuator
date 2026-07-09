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



def extract_annual_values(concept_data: dict, is_point_in_time: bool = False) -> list[dict]:
    annual_values = {}

    units = concept_data.get("units", {})
    if not units:
        return []

    first_unit_key = list(units.keys())[0]
    items = units[first_unit_key]

    for item in items:
        # fp == "FY" ist in beiden Fällen die Grundvoraussetzung
        if item.get("fp") != "FY":
            continue

        if is_point_in_time:
            # Stichtagswert (z.B. Eigenkapital): kein "start", kein Zeitraum-Check nötig
            is_valid_entry = True
        else:
            # Zeitraumwert (z.B. Revenue): braucht "start", und der Zeitraum
            # muss ungefähr ein Jahr lang sein
            if "start" not in item:
                continue
            start = date.fromisoformat(item["start"])
            end = date.fromisoformat(item["end"])
            days_diff = (end - start).days
            is_valid_entry = 350 <= days_diff <= 380

        if not is_valid_entry:
            continue

        end_date = item["end"]
        if end_date not in annual_values or item["filed"] > annual_values[end_date]["filed"]:
            annual_values[end_date] = {"value": item["val"], "filed": item["filed"]}

    return [
        {"end": end, "value": data["value"], "filed": data["filed"]}
        for end, data in annual_values.items()
    ]

def extract_summed_annual_values(us_gaap_data: dict, tags_to_sum: list[str], is_point_in_time: bool = False) -> list[dict]:
    # Pro Tag erstmal einzeln extrahieren (ohne Priorisierung, wir wollen ja alle addieren)
    per_tag_values = []
    for tag in tags_to_sum:
        concept_data = us_gaap_data.get(tag)
        if concept_data is None:
            continue
        per_tag_values.append(extract_annual_values(concept_data, is_point_in_time=is_point_in_time))
    
    # Jetzt pro end-Datum die Werte aus allen Tags aufsummieren
    summed = {}  # end-Datum -> summierter Wert
    for values in per_tag_values:
        for v in values:
            end_date = v["end"]
            summed[end_date] = summed.get(end_date, 0) + v["value"]
    
    return [{"end": end, "value": value} for end, value in summed.items()] 