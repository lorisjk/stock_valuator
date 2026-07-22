from fetchers.edgar import (
    extract_annual_values,
    extract_quarterly_values,
    extract_summed_annual_values,
    extract_summed_values,
)

import math
import pandas as pd
_SCALE_CORRECTED_CONCEPTS = {"SharesOutstanding"}
_SCALE_UP_FACTORS = [100, 1_000, 10_000, 100_000, 1_000_000, 10_000_000]
_GATE_LOG_GAP = 1.5
_MATCH_TOLERANCE = 0.5


def _closest_scale_factor(own_log: float, anchor_log: float):
    best_factor, best_diff = None, None
    for factor in _SCALE_UP_FACTORS:
        diff = abs((own_log + math.log10(factor)) - anchor_log)
        if diff <= _MATCH_TOLERANCE and (best_diff is None or diff < best_diff):
            best_factor, best_diff = factor, diff
    return best_factor


def _sweep_scale_outliers(values: list[dict], order: list[int]) -> dict:
    fixed = {}
    seed_pool = []
    for i in order[:5]:
        val = values[i]["value"]
        if val:
            seed_pool.append(math.log10(abs(val)))
    anchor_log = sorted(seed_pool)[len(seed_pool) // 2] if seed_pool else None

    for i in order:
        val = values[i]["value"]
        if not val:
            continue
        own_log = math.log10(abs(val))

        if anchor_log is None:
            anchor_log = own_log
            continue

        if abs(own_log - anchor_log) <= _GATE_LOG_GAP:
            anchor_log = own_log
            continue

        if own_log > anchor_log:
            continue

        factor = _closest_scale_factor(own_log, anchor_log)
        if factor is not None:
            fixed[i] = val * factor
            anchor_log = own_log + math.log10(factor)
    return fixed


def _normalize_scale_outliers(values: list[dict]) -> list[dict]:
    if len(values) < 4:
        return values

    ordered = sorted(range(len(values)), key=lambda i: values[i]["end"])
    forward = _sweep_scale_outliers(values, ordered)
    backward = _sweep_scale_outliers(values, list(reversed(ordered)))

    corrected = list(values)
    for i in range(len(values)):
        f_val, b_val = forward.get(i), backward.get(i)
        if f_val is not None and b_val is not None:
            if abs(f_val - b_val) <= 1e-6 * max(abs(f_val), 1):
                corrected[i] = {**values[i], "value": f_val}
        elif f_val is not None:
            corrected[i] = {**values[i], "value": f_val}
        elif b_val is not None:
            corrected[i] = {**values[i], "value": b_val}

    return corrected


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


def extract_priority_merge(
    us_gaap_data: dict,
    sources: list[dict],
    period: str,
    is_point_in_time: bool,
) -> list[dict]:
    merged = {}
    for source in sources:
        if source["type"] == "tag":
            concept_data = us_gaap_data.get(source["tag"])
            if concept_data is None:
                continue
            values = (extract_annual_values if period == "annual" else extract_quarterly_values)(
                concept_data, is_point_in_time=is_point_in_time
            )
        elif source["type"] == "sum":
            values = extract_summed_values(
                us_gaap_data, source["tags"], is_point_in_time=is_point_in_time, period=period
            )
        else:
            raise ValueError(f"unknown source type: {source['type']}")

        for v in values:
            if v["end"] not in merged:
                merged[v["end"]] = v

    return sorted(merged.values(), key=lambda v: v["end"])


def extract_with_mode(us_gaap_data: dict, cfg: dict, period: str) -> list[dict]:
    mode = cfg.get("mode", "fallback")
    is_point_in_time = cfg["point_in_time"]

    if mode == "priority_merge":
        return extract_priority_merge(
            us_gaap_data,
            cfg["sources"],
            period=period,
            is_point_in_time=is_point_in_time,
        )

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

_KNOWN_BAD_FACTS = {
    ("BAC", "Assets"): [
        {"end": "2008-12-31", "filed": "2011-02-25", "val": 0},
    ],
    ("ROK", "CommonStockDividendsPerShareDeclared"): [
        {"end": "2017-12-31", "filed": "2019-01-31", "val": 835000},
        {"end": "2018-03-31", "filed": "2019-04-25", "val": 1670000},
        {"end": "2018-03-31", "filed": "2019-04-25", "val": 835000},
        {"end": "2018-06-30", "filed": "2019-07-25", "val": 3510000},
        {"end": "2018-06-30", "filed": "2019-07-25", "val": 1840000},
        {"end": "2018-12-31", "filed": "2019-01-31", "val": 970000},
        {"end": "2019-03-31", "filed": "2019-04-25", "val": 1940000},
        {"end": "2019-03-31", "filed": "2019-04-25", "val": 970000},
        {"end": "2019-06-30", "filed": "2019-07-25", "val": 3880000},
        {"end": "2019-06-30", "filed": "2019-07-25", "val": 1940000},
    ],
    ("STX", "CommonStockDividendsPerShareDeclared"): [
        {"end": "2022-07-01", "filed": "2024-08-02", "val": 2770000},
        {"end": "2023-06-30", "filed": "2024-08-02", "val": 2800000},
        {"end": "2024-06-28", "filed": "2024-08-02", "val": 2800000},
    ],
    ("EXC", "Revenues"): [
        {"end": "2020-12-31", "filed": "2022-06-30", "val": 16663000000},
        {"end": "2020-12-31", "filed": "2023-02-14", "val": 16663000000},
    ],
    ("FE", "Revenues"): [
        {"end": "2016-12-31", "filed": "2019-02-19", "val": 10700000000},
    ],
    ("PPL", "Revenues"): [
        {"end": "2013-12-31", "filed": "2016-02-19", "val": 7263000000},
    ],
    ("PPL", "RevenueFromContractWithCustomerExcludingAssessedTax"): [
        {"end": "2019-12-31", "filed": "2022-02-18", "val": 5541000000},
    ],
    ("A", "Revenues"): [
        {"end": "2013-10-31", "filed": "2015-12-21", "val": 3894000000},
    ],
    ("A", "SalesRevenueNet"): [
        {"end": "2013-10-31", "filed": "2015-12-21", "val": 3894000000},
    ],
    ("HPQ", "Revenues"): [
        {"end": "2013-10-31", "filed": "2016-04-27", "val": 55273000000},
        {"end": "2014-10-31", "filed": "2016-04-27", "val": 56651000000},
        {"end": "2014-10-31", "filed": "2016-12-15", "val": 56651000000},
    ],
    ("HPE", "Revenues"): [
        {"end": "2015-10-31", "filed": "2017-12-15", "val": 31077000000},
    ],
    ("FTV", "RevenueFromContractWithCustomerExcludingAssessedTax"): [
        {"end": "2023-12-31", "filed": "2026-02-25", "val": 3913900000},
    ],
    ("J", "RevenueFromContractWithCustomerIncludingAssessedTax"): [
        {"end": "2022-09-30", "filed": "2024-11-25", "val": 9783074000},
    ],
    ("WDC", "RevenueFromContractWithCustomerExcludingAssessedTax"): [
        {"end": "2023-06-30", "filed": "2025-08-14", "val": 6255000000},
    ],
    ("DLTR", "RevenueFromContractWithCustomerExcludingAssessedTax"): [
        {"end": "2023-01-28", "filed": "2025-03-26", "val": 15405700000},
    ],
    ("DLTR", "CostOfGoodsAndServicesSold"): [
        {"end": "2023-01-28", "filed": "2025-03-26", "val": 9630200000},
        {"end": "2024-02-03", "filed": "2025-03-26", "val": 10761400000},
        {"end": "2024-02-03", "filed": "2026-03-16", "val": 10761400000},
    ],
    ("DLTR", "PaymentsToAcquireProductiveAssets"): [
        {"end": "2023-01-28", "filed": "2025-03-26", "val": 639000000},
        {"end": "2024-02-03", "filed": "2025-03-26", "val": 1193800000},
        {"end": "2024-02-03", "filed": "2026-03-16", "val": 1193800000},
    ],
    ("SATS", "RevenueFromContractWithCustomerExcludingAssessedTax"): [
        {"end": "2021-12-31", "filed": "2024-02-29", "val": 19818678000},
    ],
    ("SATS", "PaymentsToAcquirePropertyPlantAndEquipment"): [
        {"end": "2021-12-31", "filed": "2024-02-29", "val": 1619312000},
        {"end": "2022-12-31", "filed": "2024-02-29", "val": 3050472000},
        {"end": "2022-12-31", "filed": "2025-02-27", "val": 3050472000},
    ],
    ("SATS", "NetCashProvidedByUsedInOperatingActivities"): [
        {"end": "2021-12-31", "filed": "2024-02-29", "val": 4655373000},
        {"end": "2022-12-31", "filed": "2024-02-29", "val": 3621190000},
        {"end": "2022-12-31", "filed": "2025-02-27", "val": 3621190000},
    ],
}


def _drop_known_bad_facts(ticker: str, us_gaap_data: dict) -> dict:
    bad_by_tag = {}
    for (bad_ticker, tag), facts in _KNOWN_BAD_FACTS.items():
        if bad_ticker == ticker:
            bad_by_tag.setdefault(tag, []).extend(facts)

    if not bad_by_tag:
        return us_gaap_data

    result = dict(us_gaap_data)
    for tag, bad_facts in bad_by_tag.items():
        if tag not in result:
            continue

        concept_data = result[tag]
        new_units = {}
        for unit_key, items in concept_data.get("units", {}).items():
            new_units[unit_key] = [
                item for item in items
                if not any(
                    item.get("end") == bf["end"]
                    and item.get("filed") == bf["filed"]
                    and item.get("val") == bf["val"]
                    for bf in bad_facts
                )
            ]
        result[tag] = {**concept_data, "units": new_units}

    return result


_NON_NEGATIVE_FLOW_CONCEPTS = {
    "Revenue",
    "Capex",
    "CostOfRevenue",
    "DepreciationAndAmortization",
    "DividendsPerShare",
    "ResearchAndDevelopment",
    "EarnedPremiums",
}


def _mask_negative_flow_values(key: str, values: list[dict], period: str) -> list[dict]:
    if period != "quarterly" or key not in _NON_NEGATIVE_FLOW_CONCEPTS:
        return values
    return [v for v in values if v["value"] is None or v["value"] >= 0]

_KNOWN_POSITIVE_OUTLIERS = {
    ("ED", "Capex"): {"2016-12-31", "2017-12-31", "2018-12-31", "2019-12-31"},
}


def _mask_known_positive_outliers(ticker: str, key: str, values: list[dict], period: str) -> list[dict]:
    if period != "quarterly":
        return values
    bad_ends = _KNOWN_POSITIVE_OUTLIERS.get((ticker, key))
    if not bad_ends:
        return values
    return [v for v in values if v["end"] not in bad_ends]

_KNOWN_SCOPE_MISMATCH_OUTLIERS = {
    ("ADM", "OperatingCashFlow"): {"2016-12-31"},
    ("FLEX", "OperatingCashFlow"): {"2017-03-31"},
    ("JBL", "OperatingCashFlow"): {"2017-08-31"},
    ("TMUS", "OperatingCashFlow"): {"2011-12-31"},
}


def _mask_known_scope_mismatch_outliers(ticker: str, key: str, values: list[dict], period: str) -> list[dict]:
    if period != "quarterly":
        return values
    bad_ends = _KNOWN_SCOPE_MISMATCH_OUTLIERS.get((ticker, key))
    if not bad_ends:
        return values
    return [v for v in values if v["end"] not in bad_ends]


def build_dataframe(
    ticker: str,
    company_info: dict,
    concept_candidates: dict,
    period: str = "annual",
) -> pd.DataFrame:

    us_gaap_data = company_info["facts"]["us-gaap"]
    us_gaap_data = _drop_known_bad_facts(ticker, us_gaap_data)
    rows = []

    for key, cfg in concept_candidates.items():
        values = extract_with_mode(us_gaap_data, cfg, period)

        if not values:
            continue

        if key in _SCALE_CORRECTED_CONCEPTS:
            values = _normalize_scale_outliers(values)

        values = _mask_negative_flow_values(key, values, period)
        values = _mask_known_positive_outliers(ticker, key, values, period)
        values = _mask_known_scope_mismatch_outliers(ticker, key, values, period)

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