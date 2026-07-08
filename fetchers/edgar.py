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


mapping = fetch_or_cache(
    url="https://www.sec.gov/files/company_tickers.json",
    cache_path="cache/ticker_mapping.json",
    headers={"User-Agent": "Loris loris2006@gmx.de"}
)
print(mapping)