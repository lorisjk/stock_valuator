import pandas as pd
import numpy as np
COMMON_SPLIT_FACTORS = [1, 2, 3, 4, 5, 6, 7, 8, 10, 15, 20, 25, 30, 40, 50]


def calculate_growth(df: pd.DataFrame, concept: str, periods: int, result_name: str) -> pd.DataFrame:
    filtered_df = df[df["concept"] == concept].copy()
    filtered_df = filtered_df.sort_values(["ticker", "end"])

    filtered_df["prev_value"] = filtered_df.groupby("ticker")["value"].shift(periods)
    filtered_df["prev_value"] = filtered_df["prev_value"].where(filtered_df["prev_value"] > 0)
    filtered_df[result_name] = filtered_df["value"] / filtered_df["prev_value"] - 1

    return filtered_df[["ticker", "end", "value", result_name]]


def calculate_ratio(
    df: pd.DataFrame,
    numerator_concept: str,
    denominator_concept: str,
    result_name: str,
    require_positive_denominator: bool = False,
) -> pd.DataFrame:

    numerator = df[df["concept"] == numerator_concept].copy()
    denominator = df[df["concept"] == denominator_concept].copy()

    merged = pd.merge(
        numerator,
        denominator,
        on=["ticker", "end"],
        suffixes=(f"_{numerator_concept}", f"_{denominator_concept}"),
    )

    numerator_col = f"value_{numerator_concept}"
    denominator_col = f"value_{denominator_concept}"

    if require_positive_denominator:
        merged[denominator_col] = merged[denominator_col].where(merged[denominator_col] > 0)

    merged[result_name] = merged[numerator_col] / merged[denominator_col]

    return merged[["ticker", "end", result_name]]


def calculate_difference(
    df: pd.DataFrame,
    variable_1_concept: str,
    variable_2_concept: str,
    result_name: str,
    sign: str,
) -> pd.DataFrame:

    var_1 = df[df["concept"] == variable_1_concept].copy()
    var_2 = df[df["concept"] == variable_2_concept].copy()

    merged = pd.merge(
        var_1,
        var_2,
        on=["ticker", "end"],
        suffixes=(f"_{variable_1_concept}", f"_{variable_2_concept}"),
    )

    var_1_col = f"value_{variable_1_concept}"
    var_2_col = f"value_{variable_2_concept}"

    if sign == "+":
        merged[result_name] = merged[var_1_col] + merged[var_2_col]
    else:
        merged[result_name] = merged[var_1_col] - merged[var_2_col]

    return merged[["ticker", "end", result_name]]


def calculate_ratio_from_dfs(
    numerator_df: pd.DataFrame,
    denominator_df: pd.DataFrame,
    numerator_column: str,
    denominator_column: str,
    result_name: str,
) -> pd.DataFrame:

    merged = pd.merge(numerator_df, denominator_df, on=["ticker", "end"])
    merged[result_name] = merged[numerator_column] / merged[denominator_column]

    return merged[["ticker", "end", result_name]]


def calculate_sum_from_dfs(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    column1: str,
    column2: str,
    result_name: str,
) -> pd.DataFrame:

    merged = pd.merge(df1, df2, on=["ticker", "end"])
    merged[result_name] = merged[column1] + merged[column2]

    return merged[["ticker", "end", result_name]]


def calculate_ttm(df: pd.DataFrame, concept: str, result_name: str) -> pd.DataFrame:
    filtered_df = df[df["concept"] == concept].copy()
    filtered_df = filtered_df.sort_values(["ticker", "end"])

    filtered_df[result_name] = (
        filtered_df.groupby("ticker")["value"]
        .rolling(window=4)
        .sum()
        .reset_index(level=0, drop=True)
    )

    return filtered_df[["ticker", "end", result_name]]


def calculate_rolling_average(df: pd.DataFrame, value_col: str, window: int, result_name: str) -> pd.DataFrame:
    df = df.sort_values(["ticker", "end"]).copy()

    df[result_name] = (
        df.groupby("ticker")[value_col]
        .rolling(window=window, min_periods=1)
        .mean()
        .reset_index(level=0, drop=True)
    )

    return df[["ticker", "end", result_name]]


def get_latest_value(df: pd.DataFrame, concept: str) -> pd.DataFrame:
    filtered_df = df[df["concept"] == concept]
    latest = filtered_df.loc[filtered_df.groupby("ticker")["end"].idxmax()]
    return latest[["ticker", "end", "value"]]


def get_latest_row(df: pd.DataFrame, date_col: str = "end") -> pd.DataFrame:
    return df.loc[df.groupby("ticker")[date_col].idxmax()]


def to_long_format(df: pd.DataFrame, value_col: str, concept_name: str) -> pd.DataFrame:
    long = df[["ticker", "end", value_col]].copy().rename(columns={value_col: "value"})
    long["concept"] = concept_name
    return long[["ticker", "end", "value", "concept"]]


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
    new_concept = to_long_format(df, value_col, concept_name)
    return pd.concat([facts, new_concept], ignore_index=True)

  
def _normalize_series(values: pd.Series, dates: pd.Series) -> pd.Series:
    if len(values) < 2:
        return values
 
    anchor = values.iloc[-1]
    if anchor <= 0 or pd.isna(anchor):
        return values
 
    normalized = []
    for v in values:
        if pd.isna(v) or v <= 0:
            normalized.append(v)
            continue
 
        best = v
        best_err = abs(np.log(v / anchor))
 
        for f in COMMON_SPLIT_FACTORS:
            for candidate in (v * f, v / f):
                err = abs(np.log(candidate / anchor))
                if err < best_err:
                    best = candidate
                    best_err = err
 
        normalized.append(best)
 
    return pd.Series(normalized, index=values.index)
 
 
def normalize_split_adjusted(df: pd.DataFrame, concepts: list[str]) -> pd.DataFrame:
    mask = df["concept"].isin(concepts)
    target = df[mask].copy()
    rest = df[~mask]

    if target.empty:
        return df

    target = target.sort_values(["ticker", "concept", "end"])

    normalized_parts = []
    for _, group in target.groupby(["ticker", "concept"]):
        group = group.copy()
        group["value"] = _normalize_series(group["value"], group["end"])
        normalized_parts.append(group)

    target = pd.concat(normalized_parts, ignore_index=True)

    return pd.concat([rest, target], ignore_index=True)
 