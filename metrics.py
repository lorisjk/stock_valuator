import pandas as pd

def calculate_growth(df: pd.DataFrame, concept: str, periods: int, result_name: str) -> pd.DataFrame:
    """
    Verallgemeinerte Wachstumsrate: periods=1 vergleicht mit der unmittelbar
    vorherigen Periode (bei Jahresdaten = YoY, bei Quartalsdaten = QoQ,
    saisonal verzerrt). periods=4 vergleicht bei Quartalsdaten mit demselben
    Quartal vor einem Jahr (echtes, saisonbereinigtes YoY-Wachstum).
    """
    filtered_df = df[df["concept"] == concept].copy()
    filtered_df = filtered_df.sort_values(["ticker", "end"])
    filtered_df["prev_value"] = filtered_df.groupby("ticker")["value"].shift(periods)

    # Wachstumsraten sind mathematisch nur sinnvoll, wenn der Vorjahreswert positiv
    # ist. Bei negativem oder null Basiswert (z.B. NVDA-Verlustjahr 2011) explodiert
    # die Formel und liefert Werte wie -6300% - das ist kein Signal, sondern Artefakt.
    filtered_df["prev_value"] = filtered_df["prev_value"].where(filtered_df["prev_value"] > 0)

    filtered_df[result_name] = filtered_df["value"] / filtered_df["prev_value"] - 1
    filtered_df[result_name] = filtered_df["value"] / filtered_df["prev_value"] - 1
    return filtered_df[["ticker", "end", "value", result_name]]

def calculate_ratio(df: pd.DataFrame, numerator_concept: str, denominator_concept: str, result_name: str, require_positive_denominator=False) -> pd.DataFrame:
    filtered_numerator_df = df[df["concept"] == numerator_concept].copy()
    filtered_denominator_df = df[df["concept"] == denominator_concept].copy()
    
    df_merged = pd.merge(
        filtered_numerator_df, filtered_denominator_df,
        on=["ticker", "end"],
        suffixes=(f"_{numerator_concept}", f"_{denominator_concept}")
    )
   
    numerator_col = f"value_{numerator_concept}"
    denominator_col = f"value_{denominator_concept}"

    if require_positive_denominator:
        df_merged[denominator_col] = df_merged[denominator_col].where(df_merged[denominator_col] > 0)
    df_merged[result_name] = df_merged[numerator_col] / df_merged[denominator_col]
    
    return df_merged[["ticker", "end", result_name]]

def calculate_difference(df : pd.DataFrame, variable_1_concept : str, variable_2_concept : str , result_name : str, sign : str) -> pd.DataFrame:
    filtered_variable_1_df = df[df["concept"] == variable_1_concept].copy()
    filtered_variable_2_df = df[df["concept"] == variable_2_concept].copy()
    
    df_merged = pd.merge(
        filtered_variable_1_df, filtered_variable_2_df,
        on=["ticker", "end"],
        suffixes=(f"_{variable_1_concept}", f"_{variable_2_concept}")
    )
    
    var1_col = f"value_{variable_1_concept}"
    var2_col = f"value_{variable_2_concept}"
    if sign == "+": 
        df_merged[result_name] = df_merged[var1_col] + df_merged[var2_col]
    
    else: 
        df_merged[result_name] = df_merged[var1_col] - df_merged[var2_col]
    
    return df_merged[["ticker", "end", result_name]]

def calculate_ratio_from_dfs(
    numerator_df: pd.DataFrame,
    denominator_df: pd.DataFrame,
    numerator_column: str,
    denominator_column: str,
    result_name: str,
) -> pd.DataFrame:
    
    df_merged = pd.merge(
        numerator_df,
        denominator_df,
        on=["ticker", "end"],
    )
    
    df_merged[result_name] = (
        df_merged[numerator_column] /
        df_merged[denominator_column]
    )
    
    return df_merged[["ticker", "end", result_name]]

def calculate_sum_from_dfs(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    column1: str,
    column2: str,
    result_name: str,
) -> pd.DataFrame:

    df_merged = pd.merge(
        df1,
        df2,
        on=["ticker", "end"],
    )

    df_merged[result_name] = (
        df_merged[column1] +
        df_merged[column2]
    )

    return df_merged[["ticker", "end", result_name]]

def get_latest_value(df: pd.DataFrame, concept: str) -> pd.DataFrame:
    filtered_df = df[df["concept"] == concept]
    latest = filtered_df.loc[filtered_df.groupby("ticker")["end"].idxmax()]
    return latest[["ticker", "end", "value"]]

def calculate_historical_pe(df_with_price: pd.DataFrame) -> pd.DataFrame:
    eps_df = df_with_price[df_with_price["concept"] == "EPS"].copy()
    eps_df["pe_ratio"] = eps_df["close"] / eps_df["value"]
    return eps_df[["ticker", "end", "pe_ratio"]]

def calculate_rolling_average(df: pd.DataFrame, value_col: str, window: int, result_name: str) -> pd.DataFrame:
    df = df.sort_values(["ticker", "end"]).copy()
    df[result_name] = df.groupby("ticker")[value_col].rolling(window=window).mean().reset_index(level=0, drop=True)
    return df[["ticker", "end", result_name]]

def calculate_ttm(df: pd.DataFrame, concept: str, result_name: str) -> pd.DataFrame:
    """
    TTM (Trailing Twelve Months) = rollierende Summe der letzten 4 Quartale.
    Nur sinnvoll fuer Zeitraumwerte (Revenue, NetIncomeLoss, EPS, ...),
    NICHT fuer Bilanzpositionen (die brauchen keine Summierung, siehe get_latest_row).
    """
    filtered_df = df[df["concept"] == concept].copy()
    filtered_df = filtered_df.sort_values(["ticker", "end"])
    filtered_df[result_name] = (
        filtered_df.groupby("ticker")["value"]
        .rolling(window=4)
        .sum()
        .reset_index(level=0, drop=True)
    )
    return filtered_df[["ticker", "end", result_name]]


def get_latest_row(df: pd.DataFrame, date_col: str = "end") -> pd.DataFrame:
    """
    Generische Version von get_latest_value: nimmt die neueste Zeile pro
    ticker, unabhaengig davon, wie die Wert-Spalte heisst. Braucht KEINE
    "concept"-Spalte, im Unterschied zu get_latest_value - nuetzlich fuer
    bereits abgeleitete DataFrames (z.B. das Ergebnis von calculate_ttm).
    """
    return df.loc[df.groupby("ticker")[date_col].idxmax()]
"""
revenue_growth_long = revenue_growth[["ticker", "end", "yoy_growth"]].rename(columns={"yoy_growth" : "value"})
    revenue_growth_long["concept"] = "revenue_yoy_growth"   
    metric_rows.append(revenue_growth_long)
"""
def to_long_format(df : pd.DataFrame, value_col: str, concept_name: str) -> pd.DataFrame: 
    
    filtered_df_long = df[["ticker", "end", value_col]].copy().rename(columns={value_col : "value"})
    filtered_df_long ["concept"] = concept_name
    return filtered_df_long[["ticker", "end", "value","concept"]]

def add_ttm_concepts(df: pd.DataFrame, concepts: list[str]) -> pd.DataFrame:
    ttm_frames = []

    for concept in concepts:
        ttm = calculate_ttm(df, concept, "value")
        ttm["concept"] = f"{concept}_TTM"
        ttm_frames.append(ttm[["ticker", "end", "concept", "value"]])

    if not ttm_frames:
        return df

    return pd.concat([df] + ttm_frames, ignore_index=True)

def add_as_concept(facts: pd.DataFrame, df: pd.DataFrame, value_col: str, concept_name: str) -> pd.DataFrame:
    filtered_df_concept = df[["ticker", "end", value_col]].copy().rename(columns={value_col : "value"})
    filtered_df_concept ["concept"] = concept_name

    return pd.concat([facts, filtered_df_concept], axis=0, ignore_index=True)