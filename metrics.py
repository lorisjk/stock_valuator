import pandas as pd

def calculate_yoy_growth(df: pd.DataFrame, concept: str) -> pd.DataFrame:
    # 1. Nur Zeilen für das gewünschte concept behalten
    filtered_df = df[df["concept"] == concept].copy()
    
    # 2. Nach ticker UND end sortieren (wichtig für .shift()!)
    filtered_df = filtered_df.sort_values(["ticker", "end"])
    
    # 3. Pro ticker den Vorjahreswert per .shift() holen
    filtered_df["prev_value"] = filtered_df.groupby("ticker")["value"].shift(1)
    
    # 4. Wachstumsrate berechnen
    filtered_df["yoy_growth"] = filtered_df["value"] / filtered_df["prev_value"] - 1
    
    return filtered_df[["ticker", "end", "value", "yoy_growth"]]

def calculate_ratio(df: pd.DataFrame, numerator_concept: str, denominator_concept: str, result_name: str) -> pd.DataFrame:
    filtered_numerator_df = df[df["concept"] == numerator_concept].copy()
    filtered_denominator_df = df[df["concept"] == denominator_concept].copy()
    
    df_merged = pd.merge(
        filtered_numerator_df, filtered_denominator_df,
        on=["ticker", "end"],
        suffixes=(f"_{numerator_concept}", f"_{denominator_concept}")
    )
    
    numerator_col = f"value_{numerator_concept}"
    denominator_col = f"value_{denominator_concept}"
    df_merged[result_name] = df_merged[numerator_col] / df_merged[denominator_col]
    
    return df_merged[["ticker", "end", result_name]]