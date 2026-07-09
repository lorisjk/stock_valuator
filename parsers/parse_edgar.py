from fetchers.edgar import extract_annual_values
import pandas as pd

def extract_merged_annual_values(us_gaap_data: dict, candidate_tags: list[str]) -> list[dict]:
    merged = {}
    
    for tag in candidate_tags:
        concept_data = us_gaap_data.get(tag)
        if concept_data is None:
            continue
        
        values = extract_annual_values(concept_data)
        for v in values:
            if v["end"] in merged:
                continue
            merged[v["end"]] = {"value": v["value"], "filed": v["filed"]}
    
    # end-Datum wieder mit reinpacken, nicht nur die values() zurückgeben
    return [{"end": end, "value": data["value"], "filed": data["filed"]} for end, data in merged.items()]

def build_dataframe(ticker: str, company_info: dict, concept_candidates: dict) -> pd.DataFrame:
    rows = []
    
    for key, candidates in concept_candidates.items():
        values = extract_merged_annual_values(company_info["facts"]["us-gaap"], candidates)
        
        if not values:
            continue
        
        for v in values:
            rows.append({"ticker": ticker, "concept": key, "end": v["end"], "value": v["value"], "filed": v["filed"]})

    df = pd.DataFrame(rows)
    return df.sort_values(["ticker", "concept", "end"]).reset_index(drop=True)