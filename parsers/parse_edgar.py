from fetchers.edgar import (
    extract_annual_values,
    extract_quarterly_values,
    extract_summed_annual_values,
    extract_summed_values,
)

import pandas as pd


def extract_merged_values(
    us_gaap_data: dict,
    candidate_tags: list[str],
    period: str = "annual",
    is_point_in_time: bool = False,
) -> list[dict]:

    merged = {}

    for tag in candidate_tags:
        concept_data = us_gaap_data.get(tag)
        if concept_data is None:
            continue

        if period == "annual":
            values = extract_annual_values(concept_data, is_point_in_time=is_point_in_time)
        elif period == "quarterly":
            values = extract_quarterly_values(concept_data, is_point_in_time=is_point_in_time)
        else:
            raise ValueError("period must be 'annual' or 'quarterly'")

        for v in values:
            if v["end"] in merged:
                continue

            merged[v["end"]] = {
                "value": v["value"],
                "filed": v["filed"],
            }

    return [
        {"end": end, "value": data["value"], "filed": data["filed"]}
        for end, data in merged.items()
    ]


def extract_with_mode(us_gaap_data: dict, cfg: dict, period: str) -> list[dict]:
    mode = cfg.get("mode", "fallback")
    is_point_in_time = cfg["point_in_time"]
    
    if mode == "fallback_then_sum":
        aggregate_values = extract_merged_values(
            us_gaap_data,
            cfg["tags"],
            period=period,
            is_point_in_time=is_point_in_time,
        )
        component_values = extract_summed_values(
            us_gaap_data,
            cfg["sum_tags"],
            is_point_in_time=is_point_in_time,
            period=period,
        )

        merged = {v["end"]: v for v in component_values}
        merged.update({v["end"]: v for v in aggregate_values})

        return sorted(merged.values(), key=lambda v: v["end"])
    
    if mode == "sum":
        return extract_summed_values(
            us_gaap_data,
            cfg["tags"],
            is_point_in_time=is_point_in_time,
            period=period,
        )

    values = extract_merged_values(
        us_gaap_data,
        cfg["tags"],
        period=period,
        is_point_in_time=is_point_in_time,
    )

    if mode == "fallback_sum" and not values:
        values = extract_summed_values(
            us_gaap_data,
            cfg["fallback_sum_tags"],
            is_point_in_time=is_point_in_time,
            period=period,
        )

    return values


def build_dataframe(
    ticker: str,
    company_info: dict,
    concept_candidates: dict,
    period: str = "annual",
) -> pd.DataFrame:

    us_gaap_data = company_info["facts"]["us-gaap"]
    rows = []

    for key, cfg in concept_candidates.items():
        values = extract_with_mode(us_gaap_data, cfg, period)

        if not values:
            continue

        for v in values:
            rows.append(
                {
                    "ticker": ticker,
                    "concept": key,
                    "end": v["end"],
                    "value": v["value"],
                }
            )

    df = pd.DataFrame(rows)
    return df.sort_values(["ticker", "concept", "end"]).reset_index(drop=True)