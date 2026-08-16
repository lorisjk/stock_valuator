import pandas as pd
import numpy as np

from config import TTM_SOURCE_ROLLING

MIN_DENOMINATOR_SCALE_RATIO = 0.01
MIN_OPERATING_LEVERAGE_REVENUE_GROWTH = 0.02
MAX_OPERATING_LEVERAGE_ABS = 15
MIN_NET_DEBT_TO_EBITDA_ABS = 10_000_000
MAX_NET_DEBT_TO_EBITDA_ABS = 60
MIN_DEBT_TO_EQUITY_SCALE_RATIO = 0.05
# Two years of calendar either side, not eight rows either side: over the 37,891 full
# 17-row windows the row rule formed, the modal span was 1,461 days -- sixteen
# quarter-steps, what this constant now says outright -- but the tail reached 4,475,
# twelve years. See MDs/metrics.md.
REVENUE_SELF_SCALE_HALF_WINDOW_DAYS = 730
MIN_REVENUE_SELF_SCALE_RATIO = 0.10
MIN_PEG_REVENUE_GROWTH = 0.02
MAX_PEG_RATIO_ABS = 30

# calculate_ttm sums four *rows*, which are only four quarters if the series has
# no holes. Every bound below is the midpoint of an empty run measured over the
# 333,737 windows the implementation forms across all 501 tickers and 24 TTM
# concepts -- not a round number chosen in advance. See MDs/metrics.md.
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
    """Blank a ratio whose denominator is too small to be a denominator.

    **A missing reference cannot fire this guard**, and that is a property of the
    comparison rather than a choice: `denominator < ratio * NaN` is False, so the value
    passes unguarded. Callers therefore hand in a reference already carried across the
    periods where the filer did not report it (`fill_scale_reference`); what still arrives
    missing is missing for a whole ticker, and there is nothing to compare against.
    """
    too_small = denominator.abs() < min_denominator_scale_ratio * scale_reference.abs()
    return ratio.where(~too_small)


def fill_scale_reference(
    frame: pd.DataFrame,
    reference_col: str,
    ticker_col: str = "ticker",
    date_col: str = "end",
) -> pd.Series:
    """A ticker's scale reference carried into the periods where it is missing.

    A scale guard asks an order-of-magnitude question, so a neighbouring period's revenue
    answers it as well as the absent one would. Forward first, then backward for a leading
    hole.

    This is what lets the guard evaluate instead of silently passing, and the alternative
    was measured: the unguarded population is *tamer* than the guarded one (median pe_ratio
    17.2 against 18.7, max 1,783 against 25,466), so treating "cannot evaluate" as "fails"
    would have deleted the better-behaved half.
    """
    work = frame[[ticker_col, date_col, reference_col]].sort_values([ticker_col, date_col])
    filled = work.groupby(ticker_col)[reference_col].ffill().bfill()
    return filled.reindex(frame.index)


def apply_self_relative_scale_guard(
    df: pd.DataFrame,
    value_col: str,
    reference_col: str,
    half_window_days: int,
    min_self_scale_ratio: float,
) -> pd.Series:
    """Blank a value whose own reference collapsed against the scale of its neighbours.

    The window is a **calendar span**, `[end - half_window_days, end + half_window_days]`,
    not a row count. There is no empty run in the span distribution to derive a threshold
    from -- a span is a sum of quarter-steps, so its support is a lattice with ~91-day
    spacing and every gap is that spacing -- which is why the window is defined directly
    rather than a wrong one being masked.

    **Centred, so it looks forward as well as back, and that is a decision rather than an
    oversight.** The quantity is "the scale of this business around this period", which is
    symmetric: a backward-only reference would judge a company's first years against
    nothing and its post-divestiture years against a business that no longer exists. The
    cost is that the guard is **not causal** -- a row's visibility can change when a later
    period is filed, and an as-of view assembled by cutting rows was still guarded using
    data from after the cut. Do not "fix" the forward-looking window without reading
    MDs/metrics.md first.

    A thin window needs no special case: `min_periods=1` puts the row in its own window, so
    a row with no neighbours is compared against itself and passes -- the same "cannot
    evaluate, therefore do not blank" property the denominator guard has.

    Rows to days moved no value, and the headroom is measurable: the two rules disagree
    about the reference on 25% of rows (up to 5.9x), but the guard fires at a factor of
    ten and only fourteen rows sit within [0.10, 0.15) of it.
    """
    work = df[["ticker", "end", reference_col]].copy().sort_values(["ticker", "end"])
    work["_abs_ref"] = work[reference_col].abs()
    # 2*half+1 days centred is exactly [end - half, end + half] with both ends closed.
    # groupby(...).rolling(on=...) returns a (ticker, end) MultiIndex that cannot be aligned
    # back by index; work is sorted by ticker then end and groupby walks the tickers in that
    # order, so the rows come back in the order they went in and position is the alignment.
    work["_window_max"] = (
        work.groupby("ticker")
        .rolling(window=f"{2 * half_window_days + 1}D", on="end", center=True, min_periods=1)["_abs_ref"]
        .max()
        .to_numpy()
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
            merged[result_name], merged[denominator_col],
            fill_scale_reference(merged, "_scale_ref"), min_denominator_scale_ratio
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
    observation whose end falls in `(end - window, end]`. A row count is not the same
    measurement -- twenty consecutive quarters span 1,735 days, not 1,826 -- and measured
    over the 23,734 windows the valuation history forms, 21% of the row-counted five-year
    means were an average over some other period. See MDs/metrics.md.

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


# How stale a carried-forward value may be. A TTM figure covers twelve months, so a value
# whose period ended more than four quarters before the concept's newest row describes a
# year that no longer overlaps the one the newest period would cover -- that is where the
# bound comes from, not from fitting. The measured distribution corroborates it without
# being what chose it: over the 83 (ticker, concept) pairs whose newest row is null with a
# real value behind it, the observed distances form a quarterly lattice that stops at 365
# and does not resume until 546, so every bound in [365, 545] selects the identical 37
# pairs. See MDs/metrics.md.
MAX_LATEST_VALUE_AGE_DAYS = 365


def get_latest_value(
    df: pd.DataFrame, concept: str, max_value_age_days: "int | None" = MAX_LATEST_VALUE_AGE_DAYS
) -> pd.DataFrame:
    """The newest row of `concept` that actually carries a value, per ticker.

    Skipping nulls **without a bound** is the version of this fix that is worse than the
    bug: the observed distances run to 5,021 days, and a dividend from 2012 beside today's
    price is not a stale number, it is a wrong one. `max_value_age_days` bounds it; `None`
    disables it for a caller that wants a value at any age -- the scale guard's
    order-of-magnitude reference is the one such caller.

    `end` is the period the returned **value** is from, not the period the newest row is
    from, and `value_age_days` is the distance between the two. That is what lets a caller
    publish how the number was obtained, the way `ttm_source` and `ffo_gains_source` do.
    """
    filtered_df = df[df["concept"] == concept]
    newest_end = filtered_df.groupby("ticker")["end"].max()

    with_value = filtered_df[filtered_df["value"].notna()]
    latest = with_value.loc[with_value.groupby("ticker")["end"].idxmax()].copy()
    latest["value_age_days"] = (latest["ticker"].map(newest_end) - latest["end"]).dt.days

    if max_value_age_days is not None:
        latest = latest[latest["value_age_days"] <= max_value_age_days]
    return latest[["ticker", "end", "value", "value_age_days"]]


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
