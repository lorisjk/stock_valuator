import os
import json
import requests
from datetime import date, datetime


def fetch_or_cache(url: str, cache_path: str, headers: dict, max_age_days: int | None = None) -> dict:

    if os.path.exists(cache_path):
        fresh_enough = True
        if max_age_days is not None:
            age = date.today() - date.fromtimestamp(os.path.getmtime(cache_path))
            fresh_enough = age.days < max_age_days
        if fresh_enough:
            with open(cache_path, "r") as f:
                return json.load(f)

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
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



SUBMISSIONS_MAX_AGE_DAYS = 1


def _cache_meta_path(ticker: str) -> str:
    return f"cache/{ticker}_cache_meta.json"


def _read_cache_meta(ticker: str) -> dict:
    path = _cache_meta_path(ticker)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _write_cache_meta(ticker: str, meta: dict) -> None:
    path = _cache_meta_path(ticker)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(meta, f)


def newest_reported_period(company_info: dict) -> str | None:

    newest = ""
    for concept in company_info.get("facts", {}).get("us-gaap", {}).values():
        for items in concept.get("units", {}).values():
            for item in items:
                if item.get("form") in ("10-Q", "10-K"):
                    end = item.get("end") or ""
                    if end > newest:
                        newest = end
    return newest or None


def get_submissions(ticker: str, cik: str, user_agent: str) -> dict:
    return fetch_or_cache(
        url=f"https://data.sec.gov/submissions/CIK{cik}.json",
        cache_path=f"cache/{ticker}_submissions.json",
        headers={"User-Agent": user_agent},
        max_age_days=SUBMISSIONS_MAX_AGE_DAYS,
    )


def _fetch_company_info(ticker: str, cik: str, user_agent: str) -> dict:
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    cache_path = f"cache/{ticker}_company_info.json"

    response = requests.get(url, headers={"User-Agent": user_agent})
    response.raise_for_status()
    data = response.json()

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(data, f)
    return data


def get_company_info(ticker: str, cik: str, user_agent: str, check_staleness: bool = True) -> dict:

    cache_path = f"cache/{ticker}_company_info.json"
    today = date.today().isoformat()

    if not os.path.exists(cache_path):
        data = _fetch_company_info(ticker, cik, user_agent)
        _write_cache_meta(ticker, {"newest_period": newest_reported_period(data),
                                   "last_refetch_attempt": today})
        return data

    if not check_staleness:
        with open(cache_path, "r") as f:
            return json.load(f)

    meta = _read_cache_meta(ticker)
    cached_period = meta.get("newest_period")

    if cached_period is None:
        # first run against a cache written before the sidecar existed -- derive and store it
        with open(cache_path, "r") as f:
            data = json.load(f)
        cached_period = newest_reported_period(data)
        meta["newest_period"] = cached_period
        _write_cache_meta(ticker, meta)
    else:
        data = None

    try:
        published_period = get_latest_filed_period(get_submissions(ticker, cik, user_agent))
    except Exception:
        # the probe is an optimisation, never a hard dependency: if it fails, serve the cache
        published_period = None

    behind = bool(published_period and cached_period and published_period > cached_period)
    already_tried_today = meta.get("last_refetch_attempt") == today

    if behind and not already_tried_today:
        meta["last_refetch_attempt"] = today
        _write_cache_meta(ticker, meta)
        data = _fetch_company_info(ticker, cik, user_agent)
        meta["newest_period"] = newest_reported_period(data)
        _write_cache_meta(ticker, meta)
        return data

    if data is None:
        with open(cache_path, "r") as f:
            data = json.load(f)
    return data


def get_latest_filed_period(submissions: dict) -> str | None:

    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    report_dates = recent.get("reportDate", [])

    periods = [
        rd for form, rd in zip(forms, report_dates)
        if form in ("10-Q", "10-K") and rd
    ]
    return max(periods) if periods else None


# A quarter is not 13 weeks for every filer. Measured over the 622,845 differences
# decumulate_period_values forms across all 501 tickers (decumulation_window_report.md):
#
#   80..100   604,683   the calendar quarter (89-92) and the 12-week quarter (83-84)
#   101..105        0   empty
#   106..120    1,625   the 16-week (111/112) and 17-week (118/119) fiscal quarter
#   121..160      112   merger, spin-off, IPO and fiscal-year-change stubs
#   161..200    9,307   two quarters, one of the filer's points missing
#
# 120 days is 17 weeks plus a day: the longest quarter any fiscal calendar has.
_QUARTER_MIN_DAYS = 80
_QUARTER_MAX_DAYS = 100
_LONG_QUARTER_MAX_DAYS = 120
# The 106..120 band still mixes the two: eight 52/53-week filers (AZO, COST, DPZ,
# PEP, KR, YUM, HST, MAR) and eight one-off stubs. They are told apart by
# repetition rather than by length -- the eight filers produce 15-29 such periods
# per concept, every stub exactly one. Three keeps Marriott's and Host's
# short-lived 52/53-week era and admits no stub.
_MIN_LONG_QUARTER_PERIODS = 3


def _is_quarter_length(days: int, long_quarters_ok: bool = False) -> bool:
    if _QUARTER_MIN_DAYS <= days <= _QUARTER_MAX_DAYS:
        return True
    return long_quarters_ok and _QUARTER_MAX_DAYS < days <= _LONG_QUARTER_MAX_DAYS


def extract_period_values(concept_data: dict, is_point_in_time: bool = False, period: str = "annual") -> list[dict]:
    values = {}

    units = concept_data.get("units", {})
    if not units:
        return []

    preferred = ["USD", "USD/shares", "shares"]
    unit_key = next((u for u in preferred if u in units), None)
    if unit_key is None:
        unit_key = list(units.keys())[0]
    
    items = units[unit_key]

    for item in items:
        fp = item.get("fp")
        days_diff = None

        if "start" in item:
            start = date.fromisoformat(item["start"])
            end = date.fromisoformat(item["end"])
            days_diff = (end - start).days

        if is_point_in_time:
            if period == "annual":
                is_valid = fp == "FY"
            elif period == "quarterly":
                if days_diff is None:
                    is_valid = True
                else:
                    # a weighted-average share count carries the duration of the
                    # period it averages, so a 16-week quarter's count is 111 days
                    is_valid = _is_quarter_length(days_diff, long_quarters_ok=True) or (
                        350 <= days_diff <= 380
                    )
            else:
                raise ValueError(f"Unbekannter period-Wert: {period}")
        else:
            if days_diff is None:
                continue

            if period == "annual":
                is_valid = 350 <= days_diff <= 380
            elif period == "quarterly":
                is_valid = 80 <= days_diff <= 380
            else:
                raise ValueError(f"Unbekannter period-Wert: {period}")

        if not is_valid:
            continue

        end_date = item["end"]
        key = end_date if is_point_in_time else (end_date, days_diff)

        new_entry = {
            "end": end_date,
            "value": item["val"],
            "filed": item["filed"],
            "fp": fp,
            "fy": item.get("fy"),
            "start": item.get("start"),
            "days": days_diff,
        }

        existing = values.get(key)

        if existing is None:
            values[key] = new_entry
            continue

        if is_point_in_time:
            existing_days = existing.get("days")
            new_days = days_diff

            if existing_days is None or new_days is None:
                if item["filed"] > existing["filed"]:
                    values[key] = new_entry
            elif new_days < existing_days:
                values[key] = new_entry
            elif new_days == existing_days and item["filed"] > existing["filed"]:
                values[key] = new_entry
        else:
            if item["filed"] > existing["filed"]:
                values[key] = new_entry

    return list(values.values())


def decumulate_period_values(period_values: list[dict]) -> list[dict]:
    entries = [v for v in period_values if v.get("start")]
    quarter_starts = set()
    for v in entries:
        days = (date.fromisoformat(v["end"]) - date.fromisoformat(v["start"])).days
        if _is_quarter_length(days, long_quarters_ok=True):
            quarter_starts.add(v["start"])

    cleaned = []
    for v in entries:
        days = (date.fromisoformat(v["end"]) - date.fromisoformat(v["start"])).days
        if 350 <= days <= 380 and v["start"] not in quarter_starts:
            continue
        cleaned.append(v)

    entries = cleaned
    if not entries:
        return []

    annuals = []
    by_start = {}
    for v in entries:
        by_start.setdefault(v["start"], []).append(v)

    # First pass: every difference this function can form, with the length it
    # covers. Acceptance needs the whole set, because whether a 16-week
    # difference is a fiscal quarter or a one-off stub is decided by how often
    # this filer produces one -- see _MIN_LONG_QUARTER_PERIODS.
    candidates = []
    for start_str, group in by_start.items():
        start = date.fromisoformat(start_str)
        group_sorted = sorted(group, key=lambda x: x["end"])

        prev_value = 0.0
        prev_days = 0
        for v in group_sorted:
            days = (date.fromisoformat(v["end"]) - start).days
            is_annual_point = 350 <= days <= 380

            if is_annual_point:
                annuals.append({"end": v["end"], "value": v["value"], "filed": v["filed"]})

            # an annual point with nothing before it is a whole year, not a quarter
            if prev_days > 0 or not is_annual_point:
                candidates.append({
                    "start": start_str,
                    "end": v["end"],
                    "value": v["value"] - prev_value,
                    "filed": v["filed"],
                    "length": days - prev_days,
                })

            prev_value = v["value"]
            prev_days = days

    long_periods = {
        (c["start"], c["end"]) for c in candidates
        if _QUARTER_MAX_DAYS < c["length"] <= _LONG_QUARTER_MAX_DAYS
    }
    long_quarters_ok = len(long_periods) >= _MIN_LONG_QUARTER_PERIODS

    quarters = {}
    for c in candidates:
        if _is_quarter_length(c["length"], long_quarters_ok):
            quarters[c["end"]] = {"end": c["end"], "value": c["value"], "filed": c["filed"]}

    quarters_sorted = sorted(quarters.values(), key=lambda x: x["end"])

    for ann in annuals:
        if ann["end"] in quarters:
            continue

        ann_end = date.fromisoformat(ann["end"])
        preceding = [
            q for q in quarters_sorted
            if date.fromisoformat(q["end"]) < ann_end
            and (ann_end - date.fromisoformat(q["end"])).days <= 300
        ][-3:]

        if len(preceding) == 3:
            q4 = ann["value"] - sum(q["value"] for q in preceding)
            quarters[ann["end"]] = {"end": ann["end"], "value": q4, "filed": ann["filed"]}

    return sorted(quarters.values(), key=lambda x: x["end"])


def extract_quarterly_values(concept_data: dict, is_point_in_time: bool = False) -> list[dict]:
    raw = extract_period_values(concept_data, is_point_in_time=is_point_in_time, period="quarterly")
   
    if is_point_in_time:
        return [{"end": v["end"], "value": v["value"], "filed": v["filed"]} for v in raw]
    else:
        
        return decumulate_period_values(raw)


def extract_annual_values(concept_data: dict, is_point_in_time: bool = False) -> list[dict]:
    raw = extract_period_values(concept_data, is_point_in_time=is_point_in_time, period="annual")
    return [{"end": v["end"], "value": v["value"], "filed": v["filed"]} for v in raw]


def extract_summed_values(us_gaap_data: dict, tags_to_sum: list[str], is_point_in_time: bool = False, period: str = "annual") -> list[dict]:
    per_tag_values = []
    for tag in tags_to_sum:
        concept_data = us_gaap_data.get(tag)
        if concept_data is None:
            continue
        if period == "annual":
            per_tag_values.append(extract_annual_values(concept_data, is_point_in_time=is_point_in_time))
        elif period == "quarterly":
            per_tag_values.append(extract_quarterly_values(concept_data, is_point_in_time=is_point_in_time))
        else:
            raise ValueError(f"Unbekannter period-Wert: {period}")

    summed = {}
    for values in per_tag_values:
        for v in values:
            end_date = v["end"]
            summed[end_date] = summed.get(end_date, 0) + v["value"]

    return [{"end": end, "value": value} for end, value in summed.items()]


def extract_summed_annual_values(us_gaap_data: dict, tags_to_sum: list[str], is_point_in_time: bool = False) -> list[dict]:
    return extract_summed_values(us_gaap_data, tags_to_sum, is_point_in_time=is_point_in_time, period="annual")