from fetchers.edgar import (
    extract_annual_values,
    extract_quarterly_values,
    extract_summed_annual_values,
    extract_summed_values,
)
from config import TTM_SOURCE_ANNUAL

from datetime import date
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


_EPS_TAGS = ("EarningsPerShareDiluted", "EarningsPerShareBasic")
_SCALE_EVIDENCE_TOLERANCE = 0.35  # log10; a scale error is a whole power of ten


def _facts_by_filing(us_gaap_data: dict, tags) -> dict:
    """{(accn, start, end): [values]} -- keyed on the reporting period as well as the
    filing, so a quarterly net income is never divided by a year-to-date share count."""
    out = {}
    for tag in tags:
        concept = us_gaap_data.get(tag)
        if not concept:
            continue
        for items in concept.get("units", {}).values():
            for item in items:
                if item.get("val") is not None:
                    out.setdefault((item["accn"], item.get("start"), item["end"]), []).append(float(item["val"]))
    return out


def _scale_evidence(shares: dict, eps: dict, income: dict, end: str, value: float, factor: float) -> str:
    """'supported' / 'refuted' / 'unknown' for one proposed power-of-ten correction.

    Supported when the same period is reported elsewhere at value x factor, when the
    period's net income is restated by that same factor (the whole filing was tagged
    in thousands), or when the filing's own EPS arithmetic implies exactly it.
    Refuted when that arithmetic says the value as filed is already right.
    """
    target = math.log10(factor)

    for (_accn, _start, other_end), other in shares.items():
        if other_end == end and any(v > 0 and abs((v / value) / factor - 1) < 0.02 for v in other):
            return "supported"

    errors = []
    for (accn, start, other_end), reported in shares.items():
        if other_end != end or not any(v and abs(v / value - 1) < 1e-9 for v in reported):
            continue                                    # not a filing that reported this number
        for own in income.get((accn, start, end), []):
            for elsewhere in _income_for_period(income, start, end):
                if own and abs((elsewhere / own) / factor - 1) < 0.02:
                    return "supported"
        for per_share in eps.get((accn, start, end), []):
            for total in income.get((accn, start, end), []):
                if abs(per_share) > 1e-6:
                    errors.append(math.log10(abs((total / value) / per_share)))

    if not errors:
        return "unknown"
    implied = sorted(errors)[len(errors) // 2]
    if abs(implied - target) < _SCALE_EVIDENCE_TOLERANCE:
        return "supported"
    if abs(implied) < _SCALE_EVIDENCE_TOLERANCE:
        return "refuted"
    return "unknown"


def _income_for_period(income: dict, start, end) -> list:
    return [v for (_a, s, e), vals in income.items() if s == start and e == end for v in vals]


def _corroborated_scale_correction(us_gaap_data: dict, share_tags, income_tags,
                                   as_filed: list[dict], values: list[dict]) -> list[dict]:
    """Run the outlier sweep, then drop the corrections the filings refute.

    The sweep proposes a power-of-ten correction whenever a value sits far below its
    neighbours -- a good detector, but neighbour distance alone cannot tell a mis-typed
    scale from a real one. Chesapeake's post-reverse-split share counts are genuinely
    ~9.8m against a ~1.4bn history, and the sweep multiplied ten of them by 100.
    """
    swept = _normalize_scale_outliers(values)
    proposals = [i for i, (before, after) in enumerate(zip(values, swept))
                 if before["value"] and after["value"] != before["value"]]
    if not proposals:
        return swept

    shares = _facts_by_filing(us_gaap_data, share_tags)
    eps = _facts_by_filing(us_gaap_data, _EPS_TAGS)
    income = _facts_by_filing(us_gaap_data, income_tags)
    filed_value = {v["end"]: v["value"] for v in as_filed}

    out = list(swept)
    for i in proposals:
        end = values[i]["end"]
        factor = swept[i]["value"] / values[i]["value"]
        if _scale_evidence(shares, eps, income, end, filed_value.get(end), factor) == "refuted":
            out[i] = values[i]
    return out


_SIBLING_MIN_LOG = 0.7      # ~5x; the share tags differ by a few percent, never by this
_SIBLING_POWER_TOL = 0.05   # how far the ratio may sit off a whole power of ten
_OUT_OF_LINE_LOG = 2.0      # a value this far from its own series' median is not drift


def _series_median_log(values: list[dict], skip_end: str = None) -> float | None:
    logs = [math.log10(abs(v["value"])) for v in values
            if v["value"] and v["end"] != skip_end]
    if len(logs) < 5:
        return None
    return sorted(logs)[len(logs) // 2]


def _directional_scale_repair(us_gaap_data: dict, share_tags, income_tags,
                              as_filed: list[dict], values: list[dict]) -> list[dict]:
    """Repair values the upward sweep cannot reach, using evidence that names the culprit.

    `net income / shares = EPS` fires equally hard whether the share count or the net
    income is mis-scaled, so on its own it cannot decide anything. Two instruments do:

      * a sibling share tag in the *same accession* reporting the same period a power
        of ten away -- one filing, two share counts, only one of which matches the
        company's own history. Taking the sibling is extraction, not correction.
      * failing that, the value being orders of magnitude off its own series while the
        period's net income sits squarely on its. Nothing then supplies a replacement,
        so the row is dropped rather than passed through: Sherwin-Williams reporting
        130,924,690,000 shares is not a better input than a gap.
    """
    if not values:
        return values
    median_log = _series_median_log(values)
    if median_log is None:
        return values

    shares = _facts_by_filing(us_gaap_data, share_tags)
    eps = _facts_by_filing(us_gaap_data, _EPS_TAGS)
    income = _facts_by_filing(us_gaap_data, income_tags)
    income_log = None
    income_all = [abs(v) for vals in income.values() for v in vals if v]
    if len(income_all) >= 5:
        income_log = sorted(math.log10(v) for v in income_all)[len(income_all) // 2]
    filed_value = {v["end"]: v["value"] for v in as_filed}

    out = []
    for value in values:
        v, end = value["value"], value["end"]
        filed = filed_value.get(end)
        if not v or not filed or v <= 0:
            out.append(value)
            continue
        own_median = _series_median_log(values, skip_end=end)
        if own_median is None or abs(math.log10(v) - own_median) < _OUT_OF_LINE_LOG:
            out.append(value)
            continue

        basis = v / filed          # whatever the split basis already applied
        power = _sibling_scale_power(shares, end, filed, own_median, basis)
        if power is not None:
            # rescale in place rather than adopting the sibling's number: the sibling
            # establishes the magnitude, but it is a different measure of the share
            # count (period-end rather than weighted-average diluted) and swapping it
            # in would put a 5-7% measurement step into the middle of the series.
            out.append({**value, "value": v / (10 ** power)})
            continue
        if _income_is_sound(eps, income, income_log, shares, end, filed):
            continue               # provably wrong, nothing to replace it with -> drop
        out.append(value)
    return out


def _sibling_scale_power(shares: dict, end: str, filed: float, median_log: float, basis: float):
    """How many powers of ten a same-accession sibling says this value is out by.

    The sibling is a different measure of the same quantity -- period-end common
    shares against a weighted average -- so it agrees on the magnitude and not on the
    number. Only the exponent is taken from it.
    """
    accessions = {accn for (accn, _start, fact_end), reported in shares.items()
                  if fact_end == end and any(s and abs(s / filed - 1) < 1e-9 for s in reported)}
    if not accessions:
        return None
    for (accn, _start, other_end), others in shares.items():
        if accn not in accessions or other_end != end:
            continue
        for candidate in others:
            if candidate <= 0:
                continue
            gap = math.log10(filed / candidate)
            if gap < _SIBLING_MIN_LOG or abs(gap - round(gap)) > _SIBLING_POWER_TOL:
                continue
            if abs(math.log10(candidate * basis) - median_log) < 1.0:
                return int(round(gap))
    return None


def _income_is_sound(eps: dict, income: dict, income_log: float | None,
                     shares: dict, end: str, filed: float) -> bool:
    """The filing's EPS arithmetic fails and its net income is not what is off."""
    if income_log is None:
        return False
    errors, totals = [], []
    for (accn, start, fact_end), reported in shares.items():
        if fact_end != end or not any(s and abs(s / filed - 1) < 1e-9 for s in reported):
            continue
        for per_share in eps.get((accn, start, end), []):
            for total in income.get((accn, start, end), []):
                if abs(per_share) > 1e-6 and total:
                    errors.append(math.log10(abs((total / filed) / per_share)))
                    totals.append(abs(total))
    if not errors or not totals:
        return False
    implied = sorted(errors)[len(errors) // 2]
    if abs(implied) < _OUT_OF_LINE_LOG:
        return False
    typical = sorted(totals)[len(totals) // 2]
    return abs(math.log10(typical) - income_log) < 1.0


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


def _values_for_tag(us_gaap_data: dict, tag: str, period: str, is_point_in_time: bool) -> list[dict]:
    concept_data = us_gaap_data.get(tag)
    if concept_data is None:
        return []
    extractor = extract_annual_values if period == "annual" else extract_quarterly_values
    return extractor(concept_data, is_point_in_time=is_point_in_time)


def extract_priority_merge(
    us_gaap_data: dict,
    sources: list[dict],
    period: str,
    is_point_in_time: bool,
    non_negative: bool = False,
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
            required = source.get("require")
            if required:
                required_ends = {
                    v["end"]
                    for v in _values_for_tag(us_gaap_data, required, period, is_point_in_time)
                }
                values = [v for v in values if v["end"] in required_ends]
        else:
            raise ValueError(f"unknown source type: {source['type']}")
        if non_negative:
            values = [v for v in values if v["value"] is None or v["value"] >= 0]

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
            non_negative=cfg.get("non_negative", False),
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
    ("ARES", "PartnersCapital"): [
        {"end": "2013-12-31", "filed": "2014-06-10", "val": 1000},
        {"end": "2014-03-31", "filed": "2014-06-10", "val": 1000},
    ],
    ("ARES", "LimitedPartnersCapitalAccount"): [
        {"end": "2018-12-31", "filed": "2019-02-26", "val": 0},
    ],
    ("ARES", "CommonStockSharesOutstanding"): [
        {"end": "2017-12-31", "filed": "2019-02-26", "val": 0},
    ],
    ("ARES", "StockholdersEquity"): [
        {"end": "2017-12-31", "filed": "2020-02-28", "val": 1460292000},
        {"end": "2017-12-31", "filed": "2019-02-26", "val": 573618000},
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
    ("OXY", "RevenueFromContractWithCustomerExcludingAssessedTax"): [
        {"end": "2023-12-31", "filed": "2026-02-18", "val": 23230000000},
        {"end": "2024-12-31", "filed": "2026-02-18", "val": 22710000000},
    ],
    ("GLW", "PaymentsToAcquireProductiveAssets"): [
        {"end": "2011-03-31", "filed": "2011-04-29", "val": 100000000000},
    ],
    ("BKR", "CommonStockSharesOutstanding"): [
        {"end": "2016-12-31", "filed": "2017-07-28", "val": 100},
        {"end": "2017-06-30", "filed": "2017-07-28", "val": 100},
    ],

    ("WDAY", "CommonStockSharesOutstanding"): [
        {"end": "2012-10-31", "filed": "2012-12-07", "val": 0},
    ],

    ("FIX", "Revenues"): [
        {"end": "2025-12-31", "filed": "2026-04-23", "val": 1831286000},
    ],
    ("FIX", "OperatingIncomeLoss"): [
        {"end": "2025-12-31", "filed": "2026-04-23", "val": 209098000},
    ],
    ("MOS", "CommonStockDividendsPerShareCashPaid"): [
        {"end": "2025-09-30", "filed": "2025-11-05", "val": 220000},
        {"end": "2025-09-30", "filed": "2025-11-05", "val": 440000},
        {"end": "2026-03-31", "filed": "2026-05-11", "val": 220000},
    ],
    ("DD", "RevenueFromContractWithCustomerExcludingAssessedTax"): [
        {"end": "2020-12-31", "filed": "2023-02-15", "val": 11128000000},
    ],
    ("IP", "RevenueFromContractWithCustomerExcludingAssessedTax"): [
        {"end": "2019-12-31", "filed": "2022-02-18", "val": 18317000000},
        {"end": "2020-12-31", "filed": "2022-02-18", "val": 17565000000},
        {"end": "2020-12-31", "filed": "2023-02-17", "val": 17565000000},
        {"end": "2023-12-31", "filed": "2026-02-27", "val": 16033000000},
    ],
    ("EQR", "Revenues"): [
        {"end": "2009-12-31", "filed": "2010-09-14", "val": 1921047000},
        {"end": "2009-12-31", "filed": "2012-02-24", "val": 1640224000},
        {"end": "2009-12-31", "filed": "2012-06-13", "val": 1620815000},
        {"end": "2010-12-31", "filed": "2012-06-13", "val": 1754244000},
        {"end": "2010-12-31", "filed": "2013-02-21", "val": 1674709000},
        {"end": "2010-12-31", "filed": "2013-06-17", "val": 1456257000},
    ],
    ("KIM", "Revenues"): [
        {"end": "2012-12-31", "filed": "2014-02-26", "val": 874403000},
        {"end": "2012-12-31", "filed": "2015-02-27", "val": 793373000},
    ],
    ("UDR", "Revenues"): [
        {"end": "2010-12-31", "filed": "2011-08-05", "val": 617789000},
        {"end": "2010-12-31", "filed": "2012-02-27", "val": 586586000},
        {"end": "2010-12-31", "filed": "2012-05-03", "val": 525052000},
        {"end": "2010-12-31", "filed": "2013-02-27", "val": 525052000},
    ],
    ("WELL", "Revenues"): [
        {"end": "2010-12-31", "filed": "2011-05-10", "val": 672638000},
        {"end": "2010-12-31", "filed": "2011-08-09", "val": 663763000},
        {"end": "2010-12-31", "filed": "2012-02-17", "val": 657297000},
        {"end": "2010-12-31", "filed": "2012-05-10", "val": 635378000},
        {"end": "2010-12-31", "filed": "2012-08-06", "val": 618821000},
        {"end": "2010-12-31", "filed": "2012-11-07", "val": 609417000},
        {"end": "2010-12-31", "filed": "2013-02-26", "val": 578571000},
        {"end": "2010-12-31", "filed": "2013-05-07", "val": 578040000},
        {"end": "2010-12-31", "filed": "2013-08-06", "val": 575700000},
        {"end": "2010-12-31", "filed": "2013-11-05", "val": 569371000},
    ],
    ("AMT", "Revenues"): [
        {"end": "2022-12-31", "filed": "2025-02-25", "val": 9645400000},
    ],
    ("WAT", "WeightedAverageNumberOfDilutedSharesOutstanding"): [
        {"end": "2025-03-29", "filed": "2026-05-12", "val": 59711000000},
        {"end": "2026-04-04", "filed": "2026-05-12", "val": 82139000000},
    ],
    ("WAT", "WeightedAverageNumberOfSharesOutstandingBasic"): [
        {"end": "2025-03-29", "filed": "2026-05-12", "val": 59439000000},
        {"end": "2026-04-04", "filed": "2026-05-12", "val": 82139000000},
    ],
    ("NTRS", "WeightedAverageNumberOfDilutedSharesOutstanding"): [
        {"end": "2008-12-31", "filed": "2011-02-25", "val": 224053430000000},
        {"end": "2009-12-31", "filed": "2011-02-25", "val": 236416029000000},
        {"end": "2010-12-31", "filed": "2011-02-25", "val": 242502531000000},
    ],
    ("NTRS", "WeightedAverageNumberOfSharesOutstandingBasic"): [
        {"end": "2008-12-31", "filed": "2011-02-25", "val": 221446382000000},
        {"end": "2009-12-31", "filed": "2011-02-25", "val": 235511879000000},
        {"end": "2010-12-31", "filed": "2011-02-25", "val": 242028776000000},
    ],
    ("ANET", "NetIncomeLoss"): [
        {"end": "2021-12-31", "filed": "2026-04-16", "val": 841},
        {"end": "2022-12-31", "filed": "2026-04-16", "val": 1352},
        {"end": "2023-12-31", "filed": "2026-04-16", "val": 2087},
        {"end": "2024-12-31", "filed": "2026-04-16", "val": 2852},
        {"end": "2025-12-31", "filed": "2026-04-16", "val": 3511},
    ],
    ("SCHW", "NetIncomeLoss"): [
        {"end": "2021-12-31", "filed": "2026-04-06", "val": 5855000},
        {"end": "2022-12-31", "filed": "2026-04-06", "val": 7183000},
        {"end": "2023-12-31", "filed": "2026-04-06", "val": 5067000},
        {"end": "2024-12-31", "filed": "2026-04-06", "val": 5942000},
        {"end": "2025-12-31", "filed": "2026-04-06", "val": 8852000},
    ],
    ("ED", "NetIncomeLoss"): [
        {"end": "2021-12-31", "filed": "2026-04-08", "val": 1346000},
        {"end": "2022-12-31", "filed": "2026-04-08", "val": 1660000},
        {"end": "2023-12-31", "filed": "2026-04-08", "val": 2519000},
        {"end": "2024-12-31", "filed": "2026-04-08", "val": 1820000},
        {"end": "2025-12-31", "filed": "2026-04-08", "val": 2023000},
    ],

    ("ICE", "StockholdersEquity"): [
        {"end": "2013-06-30", "filed": "2013-08-07", "val": 10},
        {"end": "2013-09-30", "filed": "2013-11-05", "val": 10},
    ],
    ("SW", "StockholdersEquity"): [
        {"end": "2022-12-31", "filed": "2024-06-07", "val": 107},
        {"end": "2022-12-31", "filed": "2024-08-09", "val": 107},
        {"end": "2023-03-31", "filed": "2024-06-07", "val": 109},
        {"end": "2023-03-31", "filed": "2024-08-09", "val": 109},
        {"end": "2023-06-30", "filed": "2024-08-09", "val": 109},
        {"end": "2023-12-31", "filed": "2024-06-07", "val": 111},
        {"end": "2023-12-31", "filed": "2024-08-09", "val": 111},
        {"end": "2024-03-31", "filed": "2024-06-07", "val": 108},
        {"end": "2024-03-31", "filed": "2024-08-09", "val": 108},
        {"end": "2024-06-30", "filed": "2024-08-09", "val": 14462},
    ],
    ("AMCR", "StockholdersEquity"): [
        {"end": "2018-12-31", "filed": "2019-05-09", "val": 130},
        {"end": "2019-03-31", "filed": "2019-05-09", "val": 96},
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

_NON_NEGATIVE_BALANCE_CONCEPTS = {
    "LongTermDebt",
}


def _mask_negative_balance_values(key: str, values: list[dict]) -> list[dict]:
    if key not in _NON_NEGATIVE_BALANCE_CONCEPTS:
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
    ("OXY", "Revenue"): {"2025-12-31"},
    ("F", "LongTermDebt"): {"2018-12-31", "2019-12-31", "2020-12-31"},
    ("SOFI", "Assets"): {"2020-09-30", "2021-03-31"},
}


def _mask_known_scope_mismatch_outliers(ticker: str, key: str, values: list[dict], period: str) -> list[dict]:
    if period != "quarterly":
        return values
    bad_ends = _KNOWN_SCOPE_MISMATCH_OUTLIERS.get((ticker, key))
    if not bad_ends:
        return values
    return [v for v in values if v["end"] not in bad_ends]


_SPLIT_MATCH_TOLERANCE = 0.02  # log-space; a restated period differs by the ratio exactly
# A split moves the share count by at least a quarter. Below this the feed is
# reporting a stock dividend of a percent or two, where a 2% match tolerance is wider
# than the effect itself and any small restatement would "confirm" it. Ignoring those
# leaves the share count off by that percent -- an order of magnitude below the 15%
# the jump flag is looking for.
_MIN_SPLIT_LOG_MAGNITUDE = 0.182  # ln(1.2)


def _restatements(us_gaap_data: dict, candidate_tags: list[str]) -> list[tuple]:
    """(earlier_filed, later_filed, ratio) for every period a filer reported twice."""
    out = []
    for tag in candidate_tags:
        concept = us_gaap_data.get(tag)
        if not concept:
            continue
        for items in concept.get("units", {}).values():
            by_end = {}
            for item in items:
                if item.get("val"):
                    by_end.setdefault(item["end"], []).append((item["filed"], float(item["val"])))
            for facts in by_end.values():
                if len(facts) < 2:
                    continue
                facts.sort()
                for (f1, v1), (f2, v2) in zip(facts, facts[1:]):
                    if v1 > 0 and v2 > 0 and f1 != f2:
                        out.append((f1, f2, v2 / v1))
    return out


def corroborated_split_events(us_gaap_data: dict, candidate_tags: list[str],
                              splits: list[dict]) -> list[dict]:
    """Keep only the split events the filer's own numbers confirm.

    A share count is stated on the share basis in force when it was *filed*, so a
    filer that splits restates the same period at the new basis in its next filing.
    The same period reported at two filing dates that straddle a real split differs
    by exactly the split ratio -- the underlying count is identical, so the tolerance
    can be tight. A spin-off or stock-dividend ratio, which yfinance reports in the
    same column, changes the price and not the share count, so it never corroborates.
    That distinction cannot be made from the ratio's shape: Agilent's Keysight
    spin-off is 1.398 and a 7:5 split would be 1.4.
    """
    if not splits:
        return []
    changes = _restatements(us_gaap_data, candidate_tags)
    confirmed = []
    for event in splits:
        day, ratio = event["date"], float(event["ratio"])
        if ratio <= 0 or abs(math.log(ratio)) < _MIN_SPLIT_LOG_MAGNITUDE:
            continue
        for earlier, later, observed in changes:
            if not (earlier < day <= later):
                continue
            if abs(math.log(observed / ratio)) < _SPLIT_MATCH_TOLERANCE:
                confirmed.append({"date": day, "ratio": ratio})
                break
    return confirmed


def _apply_split_basis(values: list[dict], confirmed: list[dict]) -> list[dict]:
    """Restate every value onto the current share basis, using only corroborated
    splits. A value filed after the last split is already current and is left alone;
    with no corroborating evidence the factor is 1 and the value passes through."""
    if not confirmed:
        return values

    out = []
    for v in values:
        filed = v.get("filed")
        factor = 1.0
        if filed:
            for event in confirmed:
                if event["date"] > filed:
                    factor *= event["ratio"]
        out.append(v if factor == 1.0 else {**v, "value": v["value"] * factor})
    return out


_DUPLICATE_END_MAX_GAP = 7


def merge_duplicate_period_ends(values: list[dict]) -> list[dict]:
    """One reporting period tagged under two calendars is one period.

    A 52/53-week filer's quarter ends on a weekday near the month end, and many
    such filers tag the same quarter twice -- once on the fiscal end, once on the
    calendar end. `extract_period_values` keys on `(end, days)` and
    `decumulate_period_values` keys on `end`, so both survive and the series
    carries the quarter twice:

        WAT Revenue  2024-03-31 -> 2024-06-29  and  2024-04-01 -> 2024-06-30
                     both 90 days, both 708,529,000

    Seven days is the mechanism's own bound: a fiscal period end is the chosen
    weekday nearest the month end, so it can sit at most six days from it. The
    next phenomenon up the scale is a month apart (the 28-31 day cluster), which
    is a different period and is left alone.

    The later end survives. The two candidates are equally good as a step
    boundary -- measured, 419 of 452 windows are quarter-length either way -- so
    the deciding argument is the anchor invariant: keeping the later end can only
    leave a series' newest period where it is or move it forward, never back.
    """
    if len(values) < 2:
        return values

    ordered = sorted(values, key=lambda v: v["end"])
    kept = [ordered[0]]
    for v in ordered[1:]:
        gap = (date.fromisoformat(v["end"]) - date.fromisoformat(kept[-1]["end"])).days
        if gap <= _DUPLICATE_END_MAX_GAP:
            kept[-1] = v
        else:
            kept.append(v)
    return kept


def annual_ttm_values(us_gaap_data: dict, cfg: dict, quarterly_values: list[dict]) -> list[dict]:
    """The 12-month facts of a filer that discloses this item only once a year.

    A 12-month fact at a fiscal year end *is* the trailing-twelve-month value at
    that date -- not an approximation of it -- so it is taken as filed.

    The boundary against `decumulate_period_values`: this runs only where the
    quarterly extraction produced nothing at all. Such a filer has no sub-annual
    year-to-date point to difference, which is both why the quarterly pipeline
    gets zero and why the rolling window has no rows to roll over. The two paths
    are therefore disjoint by construction rather than by a runtime check --
    neither can write a value at a date the other reaches.
    """
    if quarterly_values:
        return []
    return merge_duplicate_period_ends(extract_with_mode(us_gaap_data, cfg, "annual"))


def build_dataframe(
    ticker: str,
    company_info: dict,
    concept_candidates: dict,
    period: str = "annual",
    splits: list[dict] | None = None,
    annual_ttm_concepts: list[str] | None = None,
) -> pd.DataFrame:

    us_gaap_data = company_info["facts"]["us-gaap"]
    us_gaap_data = _drop_known_bad_facts(ticker, us_gaap_data)
    rows = []
    annual_ttm = set(annual_ttm_concepts or ())

    for key, cfg in concept_candidates.items():
        values = extract_with_mode(us_gaap_data, cfg, period)
        # after the tag merge and after decumulation, because both can regenerate
        # a twin the other dropped: the fiscal end arrives from the year-to-date
        # ladder and the calendar end from a discrete quarterly fact
        values = merge_duplicate_period_ends(values)

        if key in annual_ttm:
            # before the `not values` skip below: an empty quarterly extraction
            # is exactly the case this path exists for. The masks further down
            # are not applied -- they guard decumulation artefacts, and an
            # as-filed annual fact was never decumulated.
            for v in annual_ttm_values(us_gaap_data, cfg, values):
                rows.append(
                    {
                        "ticker": ticker,
                        "concept": f"{key}_TTM",
                        "end": v["end"],
                        "value": v["value"],
                        "ttm_source": TTM_SOURCE_ANNUAL,
                    }
                )

        if not values:
            continue

        if key in _SCALE_CORRECTED_CONCEPTS:
            # split basis first, unit scale second: which basis a number is on is a
            # property of the filing, whereas a scale error is a property of how it
            # was typed. Reversed, the scale sweep absorbs the split with the wrong
            # factor -- Chipotle's pre-split count is 50x low and the sweep, which
            # only knows powers of ten, "fixes" it by 100x.
            as_filed = values
            values = _apply_split_basis(
                values,
                corroborated_split_events(us_gaap_data, cfg.get("tags", []), splits or []),
            )
            income_tags = concept_candidates.get("NetIncomeLoss", {}).get("tags", [])
            values = _corroborated_scale_correction(
                us_gaap_data, cfg.get("tags", []), income_tags, as_filed, values,
            )
            # the sweep only ever raises a value; this reaches the ones that are too
            # large, which it cannot see at all
            values = _directional_scale_repair(
                us_gaap_data, cfg.get("tags", []), income_tags, as_filed, values,
            )

        values = _mask_negative_flow_values(key, values, period)
        values = _mask_negative_balance_values(key, values)
        values = _mask_known_positive_outliers(ticker, key, values, period)
        values = _mask_known_scope_mismatch_outliers(ticker, key, values, period)

        for v in values:
            rows.append(
                {
                    "ticker": ticker,
                    "concept": key,
                    "end": v["end"],
                    "value": v["value"],
                    "ttm_source": None,
                }
            )

    df = pd.DataFrame(rows)
    return df.sort_values(["ticker", "concept", "end"]).reset_index(drop=True)