import pandas as pd


def check_data_quality(df: pd.DataFrame, expected_concepts: list[str], threshold: float = 0.5) -> pd.DataFrame:
    counts = df.groupby(["ticker", "concept"]).size().reset_index(name="count")

    missing_rows = []
    for ticker in df["ticker"].unique():
        present = set(counts[counts["ticker"] == ticker]["concept"])
        for concept in set(expected_concepts) - present:
            missing_rows.append({"ticker": ticker, "concept": concept, "count": 0})

    if missing_rows:
        counts = pd.concat([counts, pd.DataFrame(missing_rows)], ignore_index=True)

    counts["max_for_ticker"] = counts.groupby("ticker")["count"].transform("max")
    counts["ratio"] = counts["count"] / counts["max_for_ticker"]

    problems = counts[counts["ratio"] < threshold].copy()
    return problems.sort_values(["ticker", "ratio"])[
        ["ticker", "concept", "count", "max_for_ticker", "ratio"]
    ]


def print_data_quality(
    df: pd.DataFrame,
    expected_concepts: list[str],
    search_hints: dict = None,
    threshold: float = 0.5,
) -> None:
    problems = check_data_quality(df, expected_concepts, threshold)

    if problems.empty:
        print(f"Datenqualitaet OK - kein Konzept unter {threshold:.0%} Abdeckung.")
        return

    print(f"\n{'='*72}")
    print(f"DATENQUALITAET: Konzepte unter {threshold:.0%} Abdeckung")
    print(f"{'='*72}")

    for _, row in problems.iterrows():
        marker = "FEHLT " if row["count"] == 0 else "duenn "
        print(
            f"  {marker} {row['ticker']:6s} {row['concept']:32s} "
            f"{row['count']:3d} von {row['max_for_ticker']:3d} ({row['ratio']:.0%})"
        )
        hint = search_hints.get(row["concept"]) if search_hints else None
        if hint:
            print(f"         → python explore_tags.py {row['ticker']} {' '.join(hint)}")
    print(f"{'='*72}\n")

def search_tags(company_info: dict, keywords: list[str]) -> list[str]:
    lower_cased_keywords = [word.lower() for word in keywords]
    tags = []

    for key in company_info["facts"]["us-gaap"].keys():
        key_lower = key.lower()
        if any(word in key_lower for word in lower_cased_keywords):
            tags.append(key)

    tags.sort()
    return tags