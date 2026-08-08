import pandas as pd
import numpy as np

from config import TTM_SOURCE_ROLLING

MIN_DENOMINATOR_SCALE_RATIO = 0.01
MIN_OPERATING_LEVERAGE_REVENUE_GROWTH = 0.02
MAX_OPERATING_LEVERAGE_ABS = 15
MIN_NET_DEBT_TO_EBITDA_ABS = 10_000_000
MAX_NET_DEBT_TO_EBITDA_ABS = 60
MIN_DEBT_TO_EQUITY_SCALE_RATIO = 0.05
REVENUE_SELF_SCALE_WINDOW = 8
MIN_REVENUE_SELF_SCALE_RATIO = 0.10
MIN_PEG_REVENUE_GROWTH = 0.02
MAX_PEG_RATIO_ABS = 30

# calculate_ttm sums four *rows*, which are only four quarters if the series has
# no holes. Every bound below is the midpoint of an empty run measured over the
# 333,737 windows the implementation forms across all 501 tickers and 24 TTM
# concepts -- not a round number chosen in advance. See ttm_window_report.md.
#
#   window span = end[i] - end[i-3]
#     245 |  gap 246..250  | 251 ... 304 |  gap 305..362  | 363
#     ^ four rows that do not tile a year   ^ legitimate,   ^ a quarter is missing
#                                            incl. 52/53-week and fiscal-year changes
_TTM_WINDOW_MIN_DAYS = 248
_TTM_WINDOW_MAX_DAYS = 333
#
#   step between adjacent rows inside the window
#     72 |  gap 73..80  | 81 ... 121 |  gap 122..152  | 153
#                         ^ 12-week to 17-week fiscal quarters
_TTM_STEP_MIN_DAYS = 76
_TTM_STEP_MAX_DAYS = 137


def apply_denominator_scale_guard(
    ratio: pd.Series,
    denominator: pd.Series,
    scale_reference: pd.Series,
    min_denominator_scale_ratio: float,
) -> pd.Series:
    too_small = denominator.abs() < min_denominator_scale_ratio * scale_reference.abs()
    too_small = too_small & scale_reference.notna()
    return ratio.where(~too_small)


def apply_self_relative_scale_guard(
    df: pd.DataFrame,
    value_col: str,
    reference_col: str,
    window: int,
    min_self_scale_ratio: float,
) -> pd.Series:
    work = df[["ticker", "end", reference_col]].copy().sort_values(["ticker", "end"])
    work["_abs_ref"] = work[reference_col].abs()
    work["_window_max"] = (
        work.groupby("ticker")["_abs_ref"]
        .rolling(window=2 * window + 1, center=True, min_periods=1)
        .max()
        .reset_index(level=0, drop=True)
    )
    too_small = work["_abs_ref"] < min_self_scale_ratio * work["_window_max"]
    too_small = too_small.reindex(df.index)
    return df[value_col].where(~too_small)


GROWTH_PERIOD_TOLERANCE_DAYS_PER_4Q = 45


def calculate_growth(df: pd.DataFrame, concept: str, periods: int, result_name: str, min_base_ratio: float = 0.33) -> pd.DataFrame:
    filtered_df = df[df["concept"] == concept].copy()
    filtered_df = filtered_df.sort_values(["ticker", "end"]).reset_index(drop=True)
    filtered_df["end"] = filtered_df["end"].astype("datetime64[ns]")

    target_offset = pd.to_timedelta(periods * 365.25 / 4, unit="D")
    tolerance = pd.to_timedelta(periods * GROWTH_PERIOD_TOLERANCE_DAYS_PER_4Q / 4, unit="D")
    filtered_df["target_date"] = filtered_df["end"] - target_offset

    lookup = filtered_df[["ticker", "end", "value"]].rename(
        columns={"end": "lookup_end", "value": "prev_value"}
    )

    matched = pd.merge_asof(
        filtered_df.sort_values("target_date"),
        lookup.sort_values("lookup_end"),
        left_on="target_date",
        right_on="lookup_end",
        by="ticker",
        direction="nearest",
        tolerance=tolerance,
    )
    filtered_df = matched.sort_values(["ticker", "end"]).reset_index(drop=True)

    valid_base = (
        (filtered_df["prev_value"] > 0)
        & (filtered_df["value"] > 0)
        & (filtered_df["prev_value"] >= min_base_ratio * filtered_df["value"])
    )
    filtered_df["prev_value"] = filtered_df["prev_value"].where(valid_base)

    filtered_df[result_name] = filtered_df["value"] / filtered_df["prev_value"] - 1

    return filtered_df[["ticker", "end", "value", result_name]]


def calculate_ratio(
    df: pd.DataFrame,
    numerator_concept: str,
    denominator_concept: str,
    result_name: str,
    require_positive_denominator: bool = False,
    min_denominator_scale_ref: str = None,
    min_denominator_scale_ratio: float = None,
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

    if min_denominator_scale_ref is not None and min_denominator_scale_ratio is not None:
        scale = df[df["concept"] == min_denominator_scale_ref][["ticker", "end", "value"]].rename(
            columns={"value": "_scale_ref"}
        )
        merged = pd.merge(merged, scale, on=["ticker", "end"], how="left")
        merged[result_name] = apply_denominator_scale_guard(
            merged[result_name], merged[denominator_col], merged["_scale_ref"], min_denominator_scale_ratio
        )

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
    min_denominator_abs: float = None,
    max_abs_result: float = None,
) -> pd.DataFrame:

    merged = pd.merge(numerator_df, denominator_df, on=["ticker", "end"])
    merged[result_name] = merged[numerator_column] / merged[denominator_column]

    if min_denominator_abs is not None:
        too_small = merged[denominator_column].abs() < min_denominator_abs
        merged[result_name] = merged[result_name].where(~too_small)

    if max_abs_result is not None:
        too_large = merged[result_name].abs() > max_abs_result
        merged[result_name] = merged[result_name].where(~too_large)

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

def calculate_difference_from_dfs(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    column1: str,
    column2: str,
    result_name: str,
) -> pd.DataFrame:
    merged = pd.merge(df1, df2, on=["ticker", "end"])
    merged[result_name] = merged[column1] - merged[column2]
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

    # The sum above is over four rows. Four rows are twelve months only when the
    # series has no hole in it -- on a thin concept they can span years, and the
    # result is then labelled "trailing twelve months" while being nothing of the
    # kind. A window that does not cover a year yields no value rather than a
    # wrong one.
    ends = filtered_df.groupby("ticker")["end"]
    step = (filtered_df["end"] - ends.shift(1)).dt.days
    span = (filtered_df["end"] - ends.shift(3)).dt.days

    step_ok = step.between(_TTM_STEP_MIN_DAYS, _TTM_STEP_MAX_DAYS)
    by_ticker = step_ok.groupby(filtered_df["ticker"])
    # all three steps inside the window, not just the newest one: a window can
    # span the right number of days while double-counting one quarter and
    # skipping another.
    covers_year = (
        step_ok
        & by_ticker.shift(1, fill_value=False).astype(bool)
        & by_ticker.shift(2, fill_value=False).astype(bool)
        & span.between(_TTM_WINDOW_MIN_DAYS, _TTM_WINDOW_MAX_DAYS)
    )
    filtered_df.loc[~covers_year, result_name] = np.nan

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


def harmonic_mean(values: pd.Series) -> float:

    positive = values[values > 0].dropna()
    if positive.empty:
        return float("nan")
    return len(positive) / (1 / positive).sum()


def calculate_rolling_harmonic_stats(
    df: pd.DataFrame, value_col: str, window: str, result_prefix: str
) -> pd.DataFrame:
    """Harmonic mean, median and observation count over a *calendar* window.

    `window` is a pandas offset string, not a row count: the window holds every
    observation whose end falls in `(end - window, end]`. A row count is not the
    same measurement. Twenty consecutive quarters span nineteen quarter-steps --
    1,735 days between the outer end dates, not 1,826 -- and only a series with no
    hole and no extra row lands there. Measured over the 23,734 windows the
    valuation history forms, 12.3% reached back more than five years (up to 11.2)
    and 8.8% covered less than 4.65, so 21% of the five-year means were an average
    over some other period. See rolling_window_report.md.

    The count is not fixed at twenty, deliberately: five years of history with a
    gap in it is still five years, and `_n` reports how many observations were
    actually available. A row that carries no usable value now displaces nothing,
    because it occupies no time.
    """
    df = df.sort_values(["ticker", "end"]).copy()
    positive = df[value_col].where(df[value_col] > 0)

    work = df[["ticker", "end"]].copy()
    work["_value"] = positive.to_numpy()
    work["_inverse"] = 1 / positive.to_numpy()

    # groupby(...).rolling(on=...) returns a (ticker, end) MultiIndex, which cannot be
    # aligned back onto df by index. The frame is sorted by ticker then end and groupby
    # walks the tickers in that same order, so the rows come back in the order they went
    # in -- positional assignment is the alignment.
    rolling = work.groupby("ticker").rolling(window=window, on="end", min_periods=1)

    df[result_prefix] = 1 / rolling["_inverse"].mean().to_numpy()
    df[f"{result_prefix}_median"] = rolling["_value"].median().to_numpy()
    df[f"{result_prefix}_n"] = rolling["_value"].count().to_numpy()

    return df[["ticker", "end", result_prefix, f"{result_prefix}_median", f"{result_prefix}_n"]]


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
        # only a row that carries a number claims a derivation
        ttm["ttm_source"] = np.where(ttm["value"].notna(), TTM_SOURCE_ROLLING, None)
        ttm_frames.append(ttm[["ticker", "end", "concept", "value", "ttm_source"]])

    if not ttm_frames:
        return df

    return pd.concat([df] + ttm_frames, ignore_index=True)


def add_as_concept(facts: pd.DataFrame, df: pd.DataFrame, value_col: str, concept_name: str) -> pd.DataFrame:
    new_concept = to_long_format(df, value_col, concept_name)
    return pd.concat([facts, new_concept], ignore_index=True)

  
# _normalize_series / normalize_split_adjusted stood here. They rescaled every
# historical SharesOutstanding value by whichever factor from COMMON_SPLIT_FACTORS
# brought it closest to the newest value -- share-count history pulled toward the
# anchor, with no notion of when a split happened or whether one had. Of the 929
# rescaling events it performed across 335 tickers, 7 were corroborated by an actual
# corporate action. Split normalisation now lives in parse_edgar._apply_split_basis,
# where the filing date of each fact and the corporate-action feed are both available
# and no guessing is required.


 