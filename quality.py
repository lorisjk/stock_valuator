import pandas as pd


def check_data_quality(df: pd.DataFrame, expected_concepts_by_ticker: dict, threshold: float = 0.5) -> pd.DataFrame:
    rows = []
    for ticker in df["ticker"].unique():
        expected = set(expected_concepts_by_ticker.get(ticker, []))
        ticker_df = df[(df["ticker"] == ticker) & (df["concept"].isin(expected))]
        counts = ticker_df.groupby("concept").size().reset_index(name="count")

        present = set(counts["concept"])
        missing = expected - present
        if missing:
            counts = pd.concat(
                [counts, pd.DataFrame([{"concept": c, "count": 0} for c in missing])],
                ignore_index=True,
            )
        counts["ticker"] = ticker
        rows.append(counts)

    all_counts = pd.concat(rows, ignore_index=True)
    all_counts["max_for_ticker"] = all_counts.groupby("ticker")["count"].transform("max")
    all_counts["ratio"] = all_counts["count"] / all_counts["max_for_ticker"]

    problems = all_counts[all_counts["ratio"] < threshold].copy()
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
        print(f"Data fine - no concept below {threshold:.0%} coverage.")
        return

    print(f"\n{'='*72}")
    print(f"DATA QUALITY: concepts below {threshold:.0%} coverage")
    print(f"{'='*72}")

    for _, row in problems.iterrows():
        marker = "MISSING " if row["count"] == 0 else "thin "
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