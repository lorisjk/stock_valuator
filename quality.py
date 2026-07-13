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


def print_data_quality(df: pd.DataFrame, expected_concepts: list[str], threshold: float = 0.5) -> None:
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

    print(f"{'='*72}\n")