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