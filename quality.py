import pandas as pd


def check_data_quality(df: pd.DataFrame, threshold: float = 0.5) -> pd.DataFrame:
    """
    Findet Konzepte, die fuer einen Ticker auffaellig duenn befuellt sind.

    Idee: Pro Ticker gibt es Konzepte, die vollstaendig vorliegen (z.B. Revenue,
    ~70 Quartale). Wenn ein anderes Konzept desselben Tickers deutlich weniger
    Zeilen hat, fehlt dort wahrscheinlich ein XBRL-Tag in CONCEPT_CANDIDATES.

    Rueckgabe: DataFrame mit allen Konzepten unterhalb des Schwellwerts,
    sortiert nach Schwere (schlimmste zuerst).
    """
    counts = df.groupby(["ticker", "concept"]).size().reset_index(name="count")

    # Pro Ticker: wie viele Zeilen hat das am besten befuellte Konzept?
    counts["max_for_ticker"] = counts.groupby("ticker")["count"].transform("max")

    # Verhaeltnis: 1.0 = so vollstaendig wie das beste Konzept, 0.1 = nur 10%
    counts["ratio"] = counts["count"] / counts["max_for_ticker"]

    problems = counts[counts["ratio"] < threshold].copy()
    problems = problems.sort_values(["ticker", "ratio"])

    return problems[["ticker", "concept", "count", "max_for_ticker", "ratio"]]


def print_data_quality(df: pd.DataFrame, threshold: float = 0.5) -> None:
    """Menschenlesbare Ausgabe von check_data_quality."""
    problems = check_data_quality(df, threshold)

    if problems.empty:
        print(f"Datenqualitaet OK - kein Konzept unter {threshold:.0%} Abdeckung.")
        return

    print(f"\n{'='*70}")
    print(f"WARNUNG: Konzepte mit weniger als {threshold:.0%} Abdeckung")
    print(f"{'='*70}")
    for _, row in problems.iterrows():
        print(
            f"  {row['ticker']:6s} {row['concept']:30s} "
            f"{row['count']:3d} von {row['max_for_ticker']:3d} Zeilen "
            f"({row['ratio']:.0%})"
        )
    print(f"{'='*70}\n")


