import os
import json
import requests
from datetime import date


def fetch_or_cache(url: str, cache_path: str, headers: dict) -> dict:
    if os.path.exists(cache_path):
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


def get_company_info(ticker: str, cik: str, user_agent: str) -> dict:
    return fetch_or_cache(
        url=f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
        cache_path=f"cache/{ticker}_company_info.json",
        headers={"User-Agent": user_agent}
    )


def extract_period_values(concept_data: dict, is_point_in_time: bool = False, period: str = "annual") -> list[dict]:
    """
    Kernfunktion: extrahiert Rohwerte aus einem XBRL-Konzept, gefiltert nach Periodentyp.

    WICHTIGE ERKENNTNIS aus der Entwicklung: das "fp"-Feld (Q1/Q2/Q3/FY) ist
    NICHT zuverlaessig - manche Firmen/Tags (z.B. NVDA RevenueFromContract...)
    taggen praktisch ALLES als "FY", auch eindeutig quartalsgrosse Werte.
    Deshalb wird die Zeitraumlaenge (days_diff), nicht "fp", als Klassifizierungs-
    merkmal genutzt. "fp"/"fy"/"start" werden trotzdem mitgegeben (fuer die
    Q4-Ableitung und Debugging), aber die Kernentscheidung haengt nicht mehr an "fp".
    """
    values = {}

    units = concept_data.get("units", {})
    if not units:
        return []

    first_unit_key = list(units.keys())[0]
    items = units[first_unit_key]

    for item in items:
        fp = item.get("fp")

        if is_point_in_time:
            if period == "annual":
                is_valid = fp == "FY"
            elif period == "quarterly":
                is_valid = True
            else:
                raise ValueError(f"Unbekannter period-Wert: {period}")
        else:
            if "start" not in item:
                continue
            start = date.fromisoformat(item["start"])
            end = date.fromisoformat(item["end"])
            days_diff = (end - start).days

            if period == "annual":
                is_valid = 350 <= days_diff <= 380
            elif period == "quarterly":
                is_valid = 80 <= days_diff <= 380
            else:
                raise ValueError(f"Unbekannter period-Wert: {period}")

        if not is_valid:
            continue

        end_date = item["end"]
        existing = values.get(end_date)
        if existing is None or item["filed"] > existing["filed"]:
            values[end_date] = {
                "end": end_date,
                "value": item["val"],
                "filed": item["filed"],
                "fp": fp,
                "fy": item.get("fy"),
                "start": item.get("start"),
            }

    return list(values.values())


def decumulate_period_values(period_values: list[dict]) -> list[dict]:
    entries = [v for v in period_values if v.get("start")]
    if not entries:
        return []

    quarters = {}   # end-Datum -> echter Quartalswert
    annuals = []    # volle Jahreswerte (nur fuer Q4-Ableitung im Einzelquartals-Fall)

    # Nach start-Datum gruppieren. Bei KUMULATIVEN Daten (Cashflow-Positionen)
    # haben alle Perioden eines Geschaeftsjahres denselben start (Jahresbeginn)
    # und laufen nur unterschiedlich lang. Bei EINZELQUARTALEN (Revenue, GuV)
    # hat jedes Quartal seinen eigenen start.
    by_start = {}
    for v in entries:
        by_start.setdefault(v["start"], []).append(v)

    for start_str, group in by_start.items():
        start = date.fromisoformat(start_str)
        group_sorted = sorted(group, key=lambda x: x["end"])

        prev_value = 0.0
        prev_days = 0
        for v in group_sorted:
            days = (date.fromisoformat(v["end"]) - start).days

            if 350 <= days <= 380:
                # Volle Jahresperiode: als Jahreswert merken. Falls sie in einer
                # kumulativen Gruppe steht, ist sie zugleich die letzte YTD-Stufe
                # -> Q4 ergibt sich als Differenz zur vorigen Stufe.
                annuals.append({"end": v["end"], "value": v["value"], "filed": v["filed"]})
                if prev_days > 0 and 80 <= (days - prev_days) <= 100:
                    quarters[v["end"]] = {
                        "end": v["end"],
                        "value": v["value"] - prev_value,
                        "filed": v["filed"],
                    }
                prev_value = v["value"]
                prev_days = days
                continue

            # Differenz zur vorherigen Stufe derselben start-Gruppe.
            # Bei Einzelquartalen ist prev_value=0 (eigene Gruppe) -> Wert bleibt
            # unveraendert. Bei kumulativen Daten wird korrekt de-kumuliert.
            quarter_value = v["value"] - prev_value
            quarter_len = days - prev_days

            if 80 <= quarter_len <= 100:
                quarters[v["end"]] = {
                    "end": v["end"],
                    "value": quarter_value,
                    "filed": v["filed"],
                }

            prev_value = v["value"]
            prev_days = days

    # Q4-Ableitung fuer den EINZELQUARTALS-Fall (dort ist der FY-Wert keine
    # kumulative Endstufe, sondern ein separater Eintrag): Q4 = FY - (Q1+Q2+Q3).
    quarters_sorted = sorted(quarters.values(), key=lambda x: x["end"])

    for ann in annuals:
        if ann["end"] in quarters:
            continue  # schon abgedeckt

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
    """
    Oeffentliche Funktion fuer Quartalsdaten: kombiniert Extraktion + Q4-Ableitung.
    Bei Stichtagswerten ist keine Ableitung noetig (jeder Stichtag ist fuer
    sich schon ein gueltiger Wert).
    """
    raw = extract_period_values(concept_data, is_point_in_time=is_point_in_time, period="quarterly")

    if is_point_in_time:
        return [{"end": v["end"], "value": v["value"], "filed": v["filed"]} for v in raw]
    else:
        return decumulate_period_values(raw)


def extract_annual_values(concept_data: dict, is_point_in_time: bool = False) -> list[dict]:
    """
    Bestehende Funktion, unveraendertes Verhalten fuer bestehenden Code.
    Intern nur noch ein duenner Wrapper um extract_period_values(period="annual").
    """
    raw = extract_period_values(concept_data, is_point_in_time=is_point_in_time, period="annual")
    return [{"end": v["end"], "value": v["value"], "filed": v["filed"]} for v in raw]


def extract_summed_values(us_gaap_data: dict, tags_to_sum: list[str], is_point_in_time: bool = False, period: str = "annual") -> list[dict]:
    """
    Verallgemeinerte Version von extract_summed_annual_values: summiert mehrere
    Tags pro Periode, egal ob annual oder quarterly.
    """
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
    """Bestehende Funktion, unveraendertes Verhalten - Wrapper um extract_summed_values(period="annual")."""
    return extract_summed_values(us_gaap_data, tags_to_sum, is_point_in_time=is_point_in_time, period="annual")