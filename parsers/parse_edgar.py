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
            values = extract_annual_values(
                concept_data,
                is_point_in_time=is_point_in_time,
            )

        elif period == "quarterly":
            values = extract_quarterly_values(
                concept_data,
                is_point_in_time=is_point_in_time,
            )

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
        {
            "end": end,
            "value": data["value"],
            "filed": data["filed"],
        }
        for end, data in merged.items()
    ]


def build_dataframe(
    ticker: str,
    company_info: dict,
    concept_candidates: dict,
    period: str = "annual",
) -> pd.DataFrame:

    rows = []

    for key, cfg in concept_candidates.items():

        mode = cfg.get("mode", "fallback")

        if mode == "sum":

            if period == "annual":
                values = extract_summed_annual_values(
                    company_info["facts"]["us-gaap"],
                    cfg["tags"],
                    is_point_in_time=cfg["point_in_time"],
                )

            elif period == "quarterly":
                values = extract_summed_values(
                    company_info["facts"]["us-gaap"],
                    cfg["tags"],
                    is_point_in_time=cfg["point_in_time"],
                )

            else:
                raise ValueError("period must be 'annual' or 'quarterly'")

        else:

            values = extract_merged_values(
                company_info["facts"]["us-gaap"],
                cfg["tags"],
                period=period,
                is_point_in_time=cfg["point_in_time"],
            )

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
