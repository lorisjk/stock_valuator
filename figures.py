import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

from config import (
    get_concept_candidates, is_hidden, FUNDAMENTALS_TO_PLOT, QUARTERLY_COUNTERPART, GROWTH_PANELS,
    VALUATIONS_TO_PLOT, HARMONIC_MEAN_CONCEPTS, TICKER_PROFILES, DEFAULT_PROFILE,
    METRICS_BY_ID, CHART_VALUATION, GROWTH_MODES,
)
from metrics import harmonic_mean

# Pinned rather than left to Plotly's cycle: one figure holds every subplot, so an
# automatic cycle would give each panel a different colour and imply a distinction
# that is not there.
_PRIMARY_COLOR = "#1f77b4"
_SECONDARY_COLOR = "#ff7f0e"
# The snapshot marker: green rather than the series blue, and never red, which is
# already the mean line and the reference line.
_SNAPSHOT_COLOR = "#2ca02c"
_PERCENT_TICKFORMAT = ".1~%"
_KNOWN_OUTPUT_EXTENSIONS = {".png", ".html", ".json"}

# One line per ticker; colors assigned by position in the requested list so a
# ticker keeps its color even when another one drops out of the chart.
# Indexing wraps, so more tickers than colors repeats rather than erroring --
# which is what SUGGESTED_MAX_COMPARISON_TICKERS exists to keep rare.
_COMPARISON_COLORS = [
    "#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e",
    "#8c564b", "#e377c2", "#17becf", "#bcbd22", "#7f7f7f",
]
# Advisory only -- a readability limit belongs in the UI that picks the tickers
# (e.g. st.multiselect(max_selections=...)), not in the rendering layer, where a
# hard refusal would turn a UI mistake into a missing chart.
SUGGESTED_MAX_COMPARISON_TICKERS = 3
# Enforced: one ticker is not a comparison. A category check, not a readability guess.
MIN_COMPARISON_TICKERS = 2


def _output_paths(output_path: str) -> tuple[str, str]:
    stem, ext = os.path.splitext(output_path)
    if ext.lower() not in _KNOWN_OUTPUT_EXTENSIONS:
        stem = output_path
    return stem + ".html", stem + ".json"


def _write_figure(fig: go.Figure, output_path: str, write_html: bool = False) -> None:
    """Write one chart's files. JSON always, HTML on request.

    The two are not the same kind of artifact. The JSON is the interface -- ~20-50KB,
    what `from_json` reads back and what a JS frontend would consume. The HTML is a
    standalone viewer with plotly.js inlined, ~5MB, which is ~7.5GB across a full
    501-ticker run. So JSON is unconditional and HTML is opt-in, rather than the two
    sharing one switch.

    The "both files or neither" guarantee is about a *single chart's pair*, and it is
    kept here: one call derives both names from one stem and decides both, so a chart
    can never get a JSON from this configuration and an HTML from a different one
    within the same run.
    """
    html_path, json_path = _output_paths(output_path)
    if write_html:
        fig.write_html(html_path, include_plotlyjs=True, full_html=True)
    fig.write_json(json_path)


def _make_grid(n: int, max_cols: int = 3):

    if n == 0:
        return 1, 1
    cols = min(max_cols, n)
    rows = -(-n // cols)
    return rows, cols


def _select_concepts(ticker: str, catalogue: list, requested: list[str] | None) -> list:
    """Panels to draw: config order, visibility-filtered, optionally narrowed.

    Every catalogue entry is a tuple whose first element is the concept name
    (FUNDAMENTALS_TO_PLOT, VALUATIONS_TO_PLOT, GROWTH_PANELS all share that shape).

    `is_hidden` is applied to the catalogue first and the caller's list only
    narrows what survives, so an explicit request can never surface a concept the
    ticker's profile hides. Requested entries that are unknown or hidden are
    dropped with a printed note rather than refused: a UI hands one selection to
    several tickers, and a concept that is fine for one is routinely hidden for
    another -- normal operation, not a caller error.

    Order always follows `catalogue`, never the caller's list, so a chart's panel
    order is stable no matter what order the UI happens to send.
    """
    visible = [c for c in catalogue if not is_hidden(ticker, c[0])]
    if requested is None:
        return visible

    wanted = set(requested)
    selected = [c for c in visible if c[0] in wanted]
    dropped = sorted(wanted - {c[0] for c in selected})
    if dropped:
        known = {c[0] for c in catalogue}
        detail = ", ".join(
            f"{name} ({'not shown for this profile' if name in known else 'unknown'})"
            for name in dropped
        )
        print(f"[figures] {ticker}: requested concepts not plottable -- {detail}")
    return selected


class _Keep:
    """Sentinel: 'caller said nothing, use this chart's historical value'.

    None cannot serve as that default because None is itself meaningful here --
    it means 'leave the key out of the layout entirely'.
    """
    def __repr__(self):
        return "<unchanged>"


KEEP = _Keep()


def _size(width, height, default_width, default_height) -> dict:
    """The width/height part of a layout, for splatting into update_layout().

    KEEP -> the chart's historical value, None -> omit the key entirely (what a
    responsive frontend needs; Plotly only honours use_container_width when the
    figure does not pin a width), anything else -> that value.

    Returned as a dict to splat rather than merged into a layout dict, so each
    caller keeps its original keyword order and the serialised JSON stays
    byte-identical to what it produced before these parameters existed.
    """
    resolved_width = default_width if width is KEEP else width
    resolved_height = default_height if height is KEEP else height
    sized = {}
    if resolved_width is not None:
        sized["width"] = resolved_width
    if resolved_height is not None:
        sized["height"] = resolved_height
    return sized


def _window_frame(frame: pd.DataFrame, years: int, as_of: pd.Timestamp | None) -> pd.DataFrame:
    """The trailing `years` window ending at `as_of` (default: today).

    Shared by build_valuation and build_ticker_comparison so the two cannot
    drift. With an explicit `as_of` the window is bounded above as well: the
    caller asked for "the last `years` years as of that date", and leaving the
    upper bound open would instead answer "everything since that date" and show
    data the chosen date could not have known.
    """
    anchor = pd.Timestamp.today() if as_of is None else pd.Timestamp(as_of)
    windowed = frame[frame["end"] >= anchor - pd.DateOffset(years=years)]
    if as_of is not None:
        windowed = windowed[windowed["end"] <= anchor]
    return windowed


# --- optional outlier masking -------------------------------------------------
#
# A rendering concern and nothing else. The values stay in the data, in the exports
# and in the data tab; what this controls is whether one panel draws them.
#
# The rule is ratio-to-median rather than a percentile, because a percentile cut always
# removes something -- including from a series that has nothing wrong with it -- while a
# ratio test fires only when a value genuinely stands apart.
#
# k = 5, calibrated against fifteen real series rather than chosen round. The nine
# well-behaved ones (KO, JNJ, PG, MSFT pe_ratio; PLD, O p_ffo; JPM, BAC p_tbv; BA)
# top out at 1.05x-1.52x their median, and the two "difficult but readable" cases at
# 2.25x (XOM) and 3.30x (CCL). The pathological ones start at 12.0x (CRM), 22.0x (DAL)
# and 70.9x (INTC). k=5 sits in that gap: zero false positives on all nine, and on the
# reference case it flags exactly the four points that flatten the chart, leaving a
# 2.51x margin to the highest kept point. k=4 additionally hides DAL's 47.2 (4.90x),
# which does not need hiding; k=6 keeps CRM's 337.8 (5.14x), which does.
OUTLIER_MEDIAN_RATIO = 5.0

# Below this many usable points the rule does not apply at all. There is no knee in the
# data to find -- median stability improves smoothly with length (a trailing-8 median is
# off the full-series median by more than 25% in 26.7% of series, a trailing-4 in 39.0%)
# -- so this is a judgement, stated as one. Eight is the length at which hiding the
# typical two-to-four outliers still leaves something to read; at four it would not.
# It excludes 9.5% of valuation series, almost all of them recently-listed tickers.
OUTLIER_MIN_POINTS = 8

# High only. Measured before building: across the fifteen calibration series not one
# point sits below 0.2x its median, and the lowest ratio anywhere in the set is 0.29x.
# A two-sided rule would be machinery for a case that does not occur.
#
# Valuation multiples only, also measured. The rule needs a positive median to mean
# anything, and only the valuation frame has one everywhere: 0.0% of its 3,260 series
# have a non-positive median, against 6.2% of fundamentals and 24.7% of growth. Growth
# is the clear case against extending -- it crosses zero constantly, its median
# max-to-median ratio is 10.65, and 85% of its series would fire at k=4. That is not the
# rule finding outliers, it is the rule being meaningless.


def outlier_points(
    values: pd.Series,
    k: float = OUTLIER_MEDIAN_RATIO,
    min_points: int = OUTLIER_MIN_POINTS,
) -> pd.Series:
    """Boolean mask over `values`, True where a value is a high outlier.

    All-False -- never all-True -- when the rule does not apply: too few usable points,
    or a median that is not positive. Returning a mask rather than a filtered series is
    deliberate, so the caller keeps the index and can report *which* points it hid.
    """
    mask = pd.Series(False, index=values.index)
    usable = values[np.isfinite(values)]
    if len(usable) < min_points:
        return mask
    median = usable.median()
    if not (median > 0):
        return mask
    mask.loc[usable.index] = (usable / median) > k
    return mask


def outlier_report(
    frame: pd.DataFrame,
    ticker: str,
    concepts: list[str],
    value_col: str = "value",
    k: float = OUTLIER_MEDIAN_RATIO,
    min_points: int = OUTLIER_MIN_POINTS,
) -> dict:
    """{concept: DataFrame of the rows a masked panel would omit}, concepts with none left out.

    The app calls this to name what it is about to hide; plot_metric applies the same
    `outlier_points` to decide what to draw. Two callers of one rule rather than two
    implementations of it -- a silent filter would be the wrong thing in a tool whose
    argument is auditability, and a filter that disagrees with its own description
    would be worse.
    """
    out = {}
    for concept in concepts:
        sub = frame[(frame["ticker"] == ticker) & (frame["concept"] == concept)]
        if sub.empty:
            continue
        hidden = outlier_points(sub[value_col], k=k, min_points=min_points)
        if hidden.any():
            out[concept] = sub.loc[hidden, ["end", value_col]].sort_values("end")
    return out


def _make_subplot_figure(rows: int, cols: int, titles: list[str]) -> go.Figure:
    n = len(titles)
    specs = [
        [{} if r * cols + c < n else None for c in range(cols)]
        for r in range(rows)
    ]
    return make_subplots(rows=rows, cols=cols, specs=specs, subplot_titles=titles)


def _annotate_no_data(
    fig: go.Figure,
    row: int,
    col: int,
) -> None:

    fig.add_annotation(
        text="No Data",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(
            color="red",
            size=14,
        ),
        xanchor="center",
        yanchor="middle",
        row=row,
        col=col,
    )

    fig.update_xaxes(
        showticklabels=False,
        showgrid=False,
        zeroline=False,
        row=row,
        col=col,
    )

    fig.update_yaxes(
        showticklabels=False,
        showgrid=False,
        zeroline=False,
        row=row,
        col=col,
    )


def _style_axes(fig: go.Figure, row: int, col: int, ylabel: str, percent: bool) -> None:
    fig.update_xaxes(dtick="M24", tickformat="%Y", row=row, col=col)
    fig.update_yaxes(
        title_text=ylabel, title_font_size=11,
        tickformat=_PERCENT_TICKFORMAT if percent else None,
        row=row, col=col,
    )


def _snapshot_point(
    snapshot: pd.DataFrame | None,
    ticker: str,
    concept: str,
    as_of: pd.Timestamp | None,
) -> tuple[pd.Timestamp, float] | None:
    """The current value for one panel as (date, value), or None.

    None when there is no snapshot, when this concept has no snapshot counterpart
    (build_snapshot now computes all 13 valuation panels; a concept the ticker's
    profile hides still has no row, and that panel renders without a marker),
    or when `as_of` predates the snapshot: appending a run-date point to a window
    that ends earlier would put data on the chart that the chosen date could not
    have known, which is the error `as_of` exists to prevent.
    """
    if snapshot is None or snapshot.empty:
        return None
    rows = snapshot[(snapshot["ticker"] == ticker) & (snapshot["concept"] == concept)]
    rows = rows.dropna(subset=["end", "value"])
    if rows.empty:
        return None
    latest = rows.sort_values("end").iloc[-1]
    stamp = pd.Timestamp(latest["end"])
    if as_of is not None and pd.Timestamp(as_of) < stamp:
        return None
    return stamp, float(latest["value"])


def plot_metric(
    fig: go.Figure,
    row: int,
    col: int,
    metrics_long: pd.DataFrame,
    ticker: str,
    concept: str,
    ylabel: str,
    ref_line=None,
    percent: bool = False,
    show_mean: bool = False,
    harmonic: bool = False,
    snapshot_point: "tuple[pd.Timestamp, float] | None" = None,
    snapshot_in_legend: bool = False,
    mask_outliers: bool = False,
) -> None:

    filtered = metrics_long[
        (metrics_long["ticker"] == ticker)
        & (metrics_long["concept"] == concept)
    ].sort_values("end")

    valid_values = filtered.dropna(subset=["end", "value"])

    if valid_values.empty:
        _annotate_no_data(fig, row, col)
        return

    # `drawn` is what the trace shows; `filtered` is what the mean is computed from,
    # and the two are allowed to differ only here. Recomputing the mean on the
    # truncated series would compare today's multiple against a benchmark with the bad
    # years taken out -- a different and flattering quantity. Same principle that keeps
    # the snapshot marker out of the mean, for the same reason.
    #
    # Kept as `filtered` unless masking was asked for, so the default path is not merely
    # equivalent to the old one but literally the same object.
    drawn = filtered
    hidden_count = 0
    if mask_outliers:
        hidden = outlier_points(filtered["value"])
        hidden_count = int(hidden.sum())
        if hidden_count:
            drawn = filtered.loc[~hidden]

    fig.add_trace(
        go.Scatter(
            x=drawn["end"],
            y=drawn["value"],
            mode="lines + markers",
            name=concept,
            line=dict(color=_PRIMARY_COLOR),
            connectgaps=True,
            hovertemplate=("Date: %{x|%d.%m.%Y}<br>Value: %{y}<extra></extra>")
        ),
        row=row,
        col=col,

    )
   
    _style_axes(fig, row, col, ylabel, percent)

    # Self-describing when the figure is exported as a file rather than read in the
    # app, where the note next to the toggle would carry this instead. Bottom-right,
    # because the mean label occupies the top-left of the same panel.
    if hidden_count:
        fig.add_annotation(
            text=f"{hidden_count} outlier{'s' if hidden_count > 1 else ''} hidden "
                 f"(&gt;{OUTLIER_MEDIAN_RATIO:g}x median) &middot; Ø unchanged",
            x=0.98,
            y=0.02,
            xref="x domain",
            yref="y domain",
            xanchor="right",
            yanchor="bottom",
            showarrow=False,
            font=dict(color="#888888", size=9),
            row=row,
            col=col,
        )

    if show_mean:
        # `filtered`, not `drawn`. The invariance this whole feature is built around.
        mean_value = (
            harmonic_mean(filtered["value"])
            if harmonic
            else filtered["value"].mean()
        )

        if np.isfinite(mean_value):
            prefix = "Ø (harm.)" if harmonic else "Ø"

            label = (
                f"{prefix} {mean_value:.2%}"
                if percent
                else f"{prefix} {mean_value:.1f}"
            )

            fig.add_hline(
                y=mean_value,
                line_color="red",
                line_width=1,
                row=row,
                col=col,
            )

            fig.add_annotation(
                text=label,
                x=0.02,
                y=0.98,
                xref="x domain",
                yref="y domain",
                xanchor="left",
                yanchor="top",
                showarrow=False,
                font=dict(color="red", size=10),
                row=row,
                col=col,
            )

    if ref_line is not None:
        fig.add_hline(
            y=ref_line,
            line_color="red",
            line_width=1,
            row=row,
            col=col,
        )

    # Added last, and as its own trace: the mean above is computed from
    # `filtered`, which the snapshot never enters. That is what keeps the
    # historical benchmark uncontaminated by the value being judged against it --
    # a structural guarantee, not an ordering convention.
    if snapshot_point is not None:
        stamp, value = snapshot_point
        fig.add_trace(
            go.Scatter(
                x=[stamp],
                y=[value],
                mode="markers",
                name="Snapshot (current value)",
                legendgroup="snapshot",
                showlegend=snapshot_in_legend,
                marker=dict(color=_SNAPSHOT_COLOR, size=9, symbol="circle",
                            line=dict(color="white", width=1)),
                hovertemplate=(
                    "Snapshot (current value)"
                    f"<br>Date: {stamp:%d.%m.%Y}"
                    "<br>Value: %{y}<extra></extra>"
                ),
            ),
            row=row,
            col=col,
        )


def plot_metric_dual(
    fig: go.Figure,
    row: int,
    col: int,
    metrics_long: pd.DataFrame,
    ticker: str,
    concept: str,
    quarterly_concept: str,
    ylabel: str,
    ref_line=None,
    percent: bool = False,
) -> None:

    ttm = metrics_long[
        (metrics_long["ticker"] == ticker)
        & (metrics_long["concept"] == concept)
    ].sort_values("end")

    quarterly = metrics_long[
        (metrics_long["ticker"] == ticker)
        & (metrics_long["concept"] == quarterly_concept)
    ].sort_values("end")

    # no TTM series means an empty panel, whatever the quarterly series holds: the
    # quarterly line alone would be read as the metric itself
    ttm_valid = ttm.dropna(subset=["end", "value"])
    if ttm_valid.empty:
        _annotate_no_data(fig, row, col)
        return

    fig.add_trace(
        go.Scatter(
            x=ttm["end"],
            y=ttm["value"],
            mode="lines + markers",
            name=f"{concept} · TTM",
            line=dict(
                color=_PRIMARY_COLOR,
                width=1.5,
            ),
            connectgaps=True,
            hovertemplate=("Date: %{x|%d.%m.%Y}""<br>Value: %{y}""<extra></extra>")
        ),
        row=row,
        col=col,

    )

    quarterly_valid = quarterly.dropna(subset=["end", "value"])
    if not quarterly_valid.empty:
        fig.add_trace(
            go.Scatter(
                x=quarterly["end"],
                y=quarterly["value"],
                mode="lines",
                name=f"{concept} · quarterly",
                line=dict(
                    color=_SECONDARY_COLOR,
                    width=0.8,
                ),
                opacity=0.6,
                hovertemplate=("Date: %{x|%d.%m.%Y}""<br>Value: %{y}""<extra></extra>")
            ),
            row=row,
            col=col,

        )

    _style_axes(
        fig,
        row,
        col,
        ylabel,
        percent,
    )

    if ref_line is not None:
        fig.add_hline(
            y=ref_line,
            line_color="red",
            line_width=1,
            row=row,
            col=col,
        )

def build_fundamentals(
    ticker: str,
    metrics_long: pd.DataFrame,
    years: int = 15,
    concepts: list[str] | None = None,
    width: int | None = KEEP,
    height: int | None = KEEP,
) -> go.Figure | None:
    """Build the fundamentals grid. None when there is nothing to draw.

    `concepts` narrows the panel set (None = everything the config shows).
    `width`/`height` keep the historical 500*cols / 330*rows unless given; pass
    width=None for a figure with no width in its layout, which is what a
    responsive frontend needs.
    """
    filtered = _window_frame(metrics_long, years=years, as_of=None)
    concepts_to_plot = _select_concepts(ticker, FUNDAMENTALS_TO_PLOT, concepts)

    if not concepts_to_plot:
        print(f"[build_fundamentals] {ticker}: no visible panels, nothing to build.")
        return None

    rows, cols = _make_grid(len(concepts_to_plot))
    fig = _make_subplot_figure(rows, cols, [c[0] for c in concepts_to_plot])

    for idx, (concept, ylabel, ref_line, percent, _symlog) in enumerate(concepts_to_plot):
        r, c = idx // cols + 1, idx % cols + 1
        quarterly_concept = QUARTERLY_COUNTERPART.get(concept)
        if quarterly_concept and not is_hidden(ticker, quarterly_concept):
            plot_metric_dual(fig, r, c, filtered, ticker, concept, quarterly_concept,
                             ylabel, ref_line, percent)
        else:
            plot_metric(fig, r, c, filtered, ticker, concept, ylabel, ref_line, percent)

    fig.update_layout(
        title_text=f"Fundamentals {ticker}",
        **_size(width, height, 500 * cols, 330 * rows),
        hovermode="x unified",
        legend=dict(font=dict(size=9)),
    )
    return fig


def plot_fundamentals(
    ticker: str,
    metrics_long: pd.DataFrame,
    output_path: str,
    years: int = 15,
    concepts: list[str] | None = None,
    write_html: bool = False,
) -> None:
    """File-writing wrapper around build_fundamentals."""
    fig = build_fundamentals(ticker, metrics_long, years, concepts)
    if fig is None:
        return
    _write_figure(fig, output_path, write_html)


def build_growth(
    ticker: str,
    facts: pd.DataFrame,
    years: int = 15,
    growth_column: str = "yoy_growth",
    concepts: list[str] | None = None,
    width: int | None = KEEP,
    height: int | None = KEEP,
) -> go.Figure | None:
    """Build the growth row. None when there is nothing to draw.

    `growth_column` selects the mode -- `yoy_growth` or `qoq_growth`, the two
    columns main.add_growth_column writes. It was already a parameter before
    there was a second column to pass to it; the default is unchanged, so every
    existing caller and every static figure file is byte-identical.
    """

    if growth_column not in facts.columns:
        print(f"[build_growth] {ticker}: column '{growth_column}' missing, nothing to build.")
        return None
    filtered = _window_frame(facts, years=years, as_of=None)
    panels = _select_concepts(ticker, GROWTH_PANELS, concepts)

    if not panels:
        print(f"[build_growth] {ticker}: no visible panels, nothing to build.")
        return None

    # Wraps at _make_grid's 3 columns like the other charts. This was a single row
    # while there were only ever three panels; the registry now yields up to seven,
    # and one row of seven is a 3500px-wide figure. For <= 3 panels the grid is
    # still 1 x n at the same pixel size, so those figures stay byte-identical.
    rows, cols = _make_grid(len(panels))
    fig = _make_subplot_figure(rows, cols, [c for c, _ in panels])

    for idx, (concept, label) in enumerate(panels):
        r, col = idx // cols + 1, idx % cols + 1
        series = filtered[
            (filtered["ticker"] == ticker) & (filtered["concept"] == concept)
        ].sort_values("end")

        series_values = series.dropna(subset=[growth_column])

        if series_values.empty:
            _annotate_no_data(fig, r, col)
            continue

        fig.add_trace(
            go.Scatter(
                x=series["end"], y=series[growth_column], mode="lines + markers",
                name=concept, line=dict(color=_PRIMARY_COLOR), connectgaps=True, hovertemplate=("Date: %{x|%d.%m.%Y}""<br>Value: %{y}""<extra></extra>")
            ),
            row=r, col=col,
        )
        # Read off the registry rather than pinned here. `percent=True` and
        # `ref_line=0` were literals while the catalogue was ten hand-picked
        # entries that all agreed with it; the catalogue is now 39 and the two
        # declarations would diverge the first time one is registered with
        # different values. The React builder already reads the registry for
        # both (charts/growth.ts), so this is the two sides agreeing rather than
        # happening to match.
        metric = METRICS_BY_ID.get(concept)
        _style_axes(fig, r, col, label, percent=bool(metric and metric.percent))
        if metric is not None and metric.ref_line is not None:
            fig.add_hline(y=metric.ref_line, line_color="red", line_width=1, row=r, col=col)

    # The mode belongs in the title now that it is selectable: the axis labels
    # deliberately no longer name it (config.py's growth block says why), so the
    # title is where a reader finds out which of the two they are looking at. An
    # unknown column falls back to the column name rather than raising -- this is
    # a chart title, not a validation point.
    mode = next((m for m in GROWTH_MODES if m["column"] == growth_column), None)
    mode_label = mode["short"] if mode else growth_column
    fig.update_layout(
        title_text=f"Growth ({mode_label}) {ticker}",
        **_size(width, height, 500 * cols, 360 * rows),
        legend=dict(font=dict(size=9)),
        hovermode="x unified",
    )
    return fig


def plot_growth(
    ticker: str,
    facts: pd.DataFrame,
    output_path: str,
    years: int = 15,
    growth_column: str = "yoy_growth",
    concepts: list[str] | None = None,
    write_html: bool = False,
) -> None:
    """File-writing wrapper around build_growth."""
    fig = build_growth(ticker, facts, years, growth_column, concepts)
    if fig is None:
        return
    _write_figure(fig, output_path, write_html)


def build_valuation(
    ticker: str,
    valuation_history: pd.DataFrame,
    years: int = 5,
    concepts: list[str] | None = None,
    as_of: pd.Timestamp | None = None,
    snapshot: pd.DataFrame | None = None,
    width: int | None = KEEP,
    height: int | None = KEEP,
    mask_outliers: bool = False,
) -> go.Figure | None:
    """Build the valuation grid over the trailing `years` window. None when empty.

    `as_of` anchors that window: None means today (unchanged), a date means the
    window runs backwards from that date and is bounded above by it.

    `snapshot` optionally adds the current multiple as one extra marker per panel
    -- the value the history is there to be judged against. It is a separate
    trace, so it never enters the mean line, and it is suppressed for an `as_of`
    earlier than the snapshot itself (see _snapshot_point). Omitting it is the
    default and reproduces this function's output exactly as before.

    `mask_outliers` hides points more than OUTLIER_MEDIAN_RATIO times their panel's
    median. **Per panel, not per figure**: the flag is passed to every panel, but the
    rule is evaluated against each panel's own series, so a grid where one multiple is
    pathological and eight are not loses points from the one. Mean lines are unaffected
    everywhere -- see plot_metric.

    Not mirrored in build_ticker_comparison, deliberately: see that docstring.
    """
    filtered = _window_frame(valuation_history, years, as_of)

    concepts_to_plot = _select_concepts(ticker, VALUATIONS_TO_PLOT, concepts)

    if not concepts_to_plot:
        print(f"[build_valuation] {ticker}: no visible panels, nothing to build.")
        return None

    rows, cols = _make_grid(len(concepts_to_plot))
    fig = _make_subplot_figure(rows, cols, [c[0] for c in concepts_to_plot])

    snapshot_shown = False
    for idx, (concept, ylabel, ref_line, percent) in enumerate(concepts_to_plot):
        r, c = idx // cols + 1, idx % cols + 1
        point = _snapshot_point(snapshot, ticker, concept, as_of)
        plot_metric(fig, r, c, filtered, ticker, concept, ylabel, ref_line, percent,
                    show_mean=True, harmonic=concept in HARMONIC_MEAN_CONCEPTS,
                    snapshot_point=point, snapshot_in_legend=not snapshot_shown,
                    mask_outliers=mask_outliers)
        # one legend entry for all of them, on whichever panel got the first marker
        snapshot_shown = snapshot_shown or point is not None

    fig.update_layout(
        title_text=f"Valuation Data {ticker}",
        **_size(width, height, 500 * cols, 400 * rows),
        legend=dict(font=dict(size=9)),
        hovermode="x unified",
    )
    return fig


def plot_valuation(
    ticker: str,
    valuation_history: pd.DataFrame,
    output_path: str,
    years: int = 5,
    concepts: list[str] | None = None,
    as_of: pd.Timestamp | None = None,
    snapshot: pd.DataFrame | None = None,
    write_html: bool = False,
) -> None:
    """File-writing wrapper around build_valuation."""
    fig = build_valuation(ticker, valuation_history, years, concepts, as_of, snapshot)
    if fig is None:
        return
    _write_figure(fig, output_path, write_html)


def _concept_plot_spec(concept: str):
    """Chart furniture for a concept, straight out of config's METRICS registry,
    which is also what the single-ticker charts are built from -- so a comparison
    chart cannot drift from them.

    Returns (source, ylabel, ref_line, percent, is_valuation, value_column) or
    None if the concept is not something this project plots.

    This used to scan VALUATIONS_TO_PLOT, then FUNDAMENTALS_TO_PLOT, then
    GROWTH_PANELS. That precedence is moot: every id belongs to exactly one
    chart, and config's registry index refuses a duplicate id at import.
    """
    metric = METRICS_BY_ID.get(concept)
    if metric is None:
        return None
    return (
        metric.chart,
        metric.label,
        metric.ref_line,
        metric.percent,
        # plot_valuation applies the rolling year cutoff; comparisons must too
        metric.chart == CHART_VALUATION,
        metric.value_column,
    )


def concept_source(concept: str) -> str | None:
    """Which dataframe a concept lives in: 'fundamentals' (metrics_long),
    'valuation' (valuation_history), 'growth' (facts), or None if unplottable.

    Lets callers route a concept to the right frame without duplicating the
    config lookup.
    """
    spec = _concept_plot_spec(concept)
    return spec[0] if spec else None


def _comparison_selection(
    tickers: list[str],
    concept: str,
    data: pd.DataFrame,
    years: int,
    as_of: "pd.Timestamp | None",
    value_column: "str | None",
):
    """(spec, column, plotted, excluded) for a comparison request, or None if unbuildable.

    Extracted so `build_ticker_comparison` and `comparison_outlier_report` cannot answer
    "which tickers, which window, which column" differently. The app decides whether to
    offer outlier masking from the report and then asks the builder to apply it; if the
    two derived their series separately, the control could name points the chart does not
    draw, or miss ones it does.
    """
    spec = _concept_plot_spec(concept)
    if spec is None:
        print(f"[ticker_comparison] '{concept}' is not a plotted concept, nothing to build.")
        return None
    _source, _ylabel, _ref_line, _percent, is_valuation, default_column = spec
    column = value_column or default_column

    requested = list(dict.fromkeys(tickers))
    if len(requested) < MIN_COMPARISON_TICKERS:
        print(f"[ticker_comparison] {concept}: {len(requested)} distinct ticker(s) "
              f"requested, need at least {MIN_COMPARISON_TICKERS}, nothing to build.")
        return None

    frame = _window_frame(data, years, as_of) #if is_valuation else data

    plotted, excluded = [], []
    for position, ticker in enumerate(requested):
        if is_hidden(ticker, concept):
            profile = TICKER_PROFILES.get(ticker, DEFAULT_PROFILE)
            excluded.append((ticker, f"for profile '{profile}' not shown"))
            continue
        series = frame[
            (frame["ticker"] == ticker) & (frame["concept"] == concept)
        ].sort_values("end")
        if series.dropna(subset=["end", column]).empty:
            excluded.append((ticker, "No Data"))
            continue
        plotted.append((position, ticker, series))

    return spec, column, plotted, excluded


def comparison_outlier_report(
    tickers: list[str],
    concept: str,
    data: pd.DataFrame,
    years: int = 5,
    as_of: "pd.Timestamp | None" = None,
    value_column: "str | None" = None,
) -> dict:
    """{ticker: DataFrame of the rows a masked comparison would omit}. Empty when none.

    **Each line is judged against its own median, never against a pooled one.** Measured
    on the alternative: for NVDA/KO/JPM on `pe_ratio` -- three series with nothing wrong
    with any of them -- a pooled median flags two NVDA points, purely because NVDA trades
    at a higher multiple than a bank. Punishing a ticker for sitting at a different level
    is the opposite of what a comparison chart is for. The same pooled rule
    simultaneously over-masks CRM (7 points against 4) and under-masks INTC (1 against
    3, while its 812.4 sits there), because one threshold cannot serve series whose
    medians differ by 6x.
    """
    selection = _comparison_selection(tickers, concept, data, years, as_of, value_column)
    if selection is None:
        return {}
    spec, column, plotted, _excluded = selection
    if not spec[4]:                    # is_valuation -- see outlier_points' scope note
        return {}
    out = {}
    for _position, ticker, series in plotted:
        hidden = outlier_points(series[column])
        if hidden.any():
            out[ticker] = series.loc[hidden, ["end", column]].sort_values("end")
    return out


def build_ticker_comparison(
    tickers: list[str],
    concept: str,
    data: pd.DataFrame,
    years: int = 5,
    value_column: str | None = None,
    as_of: pd.Timestamp | None = None,
    width: int | None = KEEP,
    height: int | None = KEEP,
    mask_outliers: bool = False,
) -> tuple[go.Figure | None, list[tuple[str, str]]]:
    """One metric, one line per ticker, for comparison. Returns (fig, excluded).

    No file I/O -- for a web layer that wants the figure object. `plot_ticker_comparison`
    is the thin file-writing wrapper around this.

    A ticker is dropped when `is_hidden` hides the metric for its profile -- the
    profile system already decides per metric where a number is meaningful, so a
    comparison must not go behind its back. Drops are never silent: they are
    returned as `excluded` [(ticker, reason), ...], stamped onto `fig.layout.meta`
    so they survive JSON serialisation, printed, and written onto the chart.

    `fig` is None when there is nothing to draw. `excluded` then tells the two
    cases apart: non-empty means every requested ticker was dropped (a data
    outcome), empty means the request itself was rejected (unknown concept, or
    fewer than MIN_COMPARISON_TICKERS tickers).

    No per-ticker mean lines (n of them would bury the data); the metric-level
    reference line stays because it does not depend on the ticker. Per-ticker
    show/hide is left to Plotly's legend, which does it natively.

    `mask_outliers` hides points more than OUTLIER_MEDIAN_RATIO times **their own
    line's** median, and only for valuation concepts. The mean-line invariance that
    governs build_valuation has no counterpart to protect here, precisely because this
    chart draws no means -- the only computed line is `ref_line`, which is a property of
    the metric and not of any series, so masking cannot move it.

    **No snapshot point either, deliberately** -- build_valuation grows one and
    this does not. Same reasoning as the mean lines: n markers, one per ticker,
    all at the same x just past the last filed period, would cluster into what
    reads as a vertical spike rather than n separate current values. And the
    comparison chart answers "how have these moved relative to each other",
    where the shape of the history is the content; the current level for several
    tickers side by side is what the snapshot table already shows better.
    """
    selection = _comparison_selection(tickers, concept, data, years, as_of, value_column)
    if selection is None:
        return None, []
    spec, column, plotted, excluded = selection
    _source, ylabel, ref_line, percent, is_valuation, _default_column = spec

    excluded_text = [f"{ticker} ({reason})" for ticker, reason in excluded]
    if excluded:
        print(f"[ticker_comparison] {concept}: not shown -- "
              f"{', '.join(excluded_text)}")

    if not plotted:
        print(f"[ticker_comparison] {concept}: no ticker left to plot.")
        return None, excluded

    fig = _make_subplot_figure(1, 1, [concept])

    # Per line, against that line's own median -- never a pooled one; see
    # comparison_outlier_report for the measurement behind that choice. Gated on
    # is_valuation, so picking a fundamentals or growth concept ignores the flag
    # rather than applying a rule whose precondition does not hold there.
    #
    # Worth more here than in the valuation grid, and for a structural reason: these
    # lines share one y-axis, so a single ticker's outlier flattens every other line
    # too. On CRM/KO/MSFT it costs the whole chart a 5.0x y-range expansion.
    hidden_by_ticker = {}
    if mask_outliers and is_valuation:
        for _position, ticker, series in plotted:
            hidden = outlier_points(series[column])
            if hidden.any():
                hidden_by_ticker[ticker] = hidden

    for position, ticker, series in plotted:
            drawn = series
            if ticker in hidden_by_ticker:
                drawn = series.loc[~hidden_by_ticker[ticker]]
            fig.add_trace(
                go.Scatter(
                    x=drawn["end"],
                    y=drawn[column],
                    mode="lines+markers",
                    name=ticker,
                    line=dict(color=_COMPARISON_COLORS[position % len(_COMPARISON_COLORS)]),
                    connectgaps=True,
                    hovertemplate="%{fullData.name}: %{y}<extra></extra>",
                ),
                row=1,
                col=1,
            )

    fig.update_xaxes(hoverformat="%d.%m.%Y", row=1, col=1)
    _style_axes(fig, 1, 1, ylabel, percent)

    if ref_line is not None:
        fig.add_hline(
            y=ref_line,
            line_color="red",
            line_width=1,
            row=1,
            col=1,
        )

    if excluded:
        fig.add_annotation(
            text="Not shown: " + ", ".join(excluded_text),
            x=0.0,
            xref="paper",
            xanchor="left",
            y=-0.16,
            yref="paper",
            yanchor="top",
            showarrow=False,
            font=dict(color="red", size=10),
        )

    # Same reasoning as the per-panel note in plot_metric: a file exported from here
    # has no toggle beside it to explain why a line is shorter than the data.
    if hidden_by_ticker:
        hidden_text = ", ".join(
            f"{t} ({int(h.sum())})" for t, h in hidden_by_ticker.items())
        fig.add_annotation(
            text=f"Outliers hidden (&gt;{OUTLIER_MEDIAN_RATIO:g}x each line's own median): "
                 f"{hidden_text}",
            x=1.0,
            xref="paper",
            xanchor="right",
            y=1.04,
            yref="paper",
            yanchor="bottom",
            showarrow=False,
            font=dict(color="#888888", size=10),
        )

    fig.update_layout(
        title_text=f"{ylabel} — {', '.join(t for _, t, _ in plotted)}",
        **_size(width, height, 900, 520),
        legend=dict(font=dict(size=10)),
        hovermode="x unified",
        margin=dict(b=110 if excluded else 80),
        # travels with the figure through to_json/from_json, so a consumer that
        # only receives the serialised figure still learns what was dropped
        meta={
            "concept": concept,
            "tickers": [ticker for _, ticker, _ in plotted],
            "excluded": [{"ticker": t, "reason": r} for t, r in excluded],
            **({"outliers_hidden": {t: int(h.sum())
                                    for t, h in hidden_by_ticker.items()}}
               if hidden_by_ticker else {}),
        },
    )
    return fig, excluded

NOT_NEEDED_ENDING = ["_TTM"]

def plot_ticker_comparison(
    tickers: list[str],
    concept: str,
    data: pd.DataFrame,
    output_path: str,
    years: int = 5,
    value_column: str | None = None,
    as_of: pd.Timestamp | None = None,
) -> None:
    """File-writing wrapper around build_ticker_comparison.

    Nothing to draw -> neither file is written, preserving the both-files-or-neither
    guarantee the other plot functions give.
    """
    fig, _excluded = build_ticker_comparison(tickers, concept, data, years, value_column, as_of)
    if fig is None:
        return
    _write_figure(fig, output_path)

def available_raw_concepts(
    ticker: str,
    facts: pd.DataFrame,
    include_derived: bool = False,
) -> list[str]:
    """Concepts that actually have data for this ticker.

    facts_full is already post-filter_hidden_rows, so profile visibility
    is respected without consulting is_hidden here.
    """
    rows = facts[(facts["ticker"] == ticker)].dropna(subset=["value"])
    concepts = set(rows["concept"].unique())

    if not include_derived:
        queried = set(get_concept_candidates(ticker))   # aus config
        concepts &= queried

    return sorted(concepts)

def build_raw_facts(
    ticker: str,
    facts: pd.DataFrame,
    years: int = 15,
    concepts: list[str] | None = None,
    include_derived: bool = False,
    width: int | None = KEEP,
    height: int | None = KEEP,
) -> go.Figure | None:

    available = available_raw_concepts(ticker, facts, include_derived)
    filtered = _window_frame(facts, years=years, as_of=None)
    if concepts is not None:
        available = [c for c in available if c in set(concepts)]

    if not available:
        print(f"[build_raw_facts] {ticker}: no visible panels, nothing to build.")
        return None

    rows, cols = _make_grid(len(available))
    fig = _make_subplot_figure(rows, cols, available)

    for idx, concept in enumerate(available):
        r, c = idx // cols + 1, idx % cols + 1
        series = filtered[
            (filtered["ticker"] == ticker) & (filtered["concept"] == concept)
        ].sort_values("end")

        series_values = series.dropna(subset=["end", "value"])
        if series_values.empty:
            _annotate_no_data(fig, r, c)
            continue

        fig.add_trace(
            go.Bar(
                x=series["end"],
                y=series["value"],
                name=concept,
                marker_color=_PRIMARY_COLOR,
                hovertemplate=("Date: %{x|%d.%m.%Y}<br>Value: %{y}<extra></extra>")
            ),
            row=r,
            col=c,
        )

    fig.update_layout(
        title_text=f"Raw Facts {ticker}",
        **_size(width, height, 500 * cols, 330 * rows),
        legend=dict(font=dict(size=9)),
    )
    return fig

def plot_raw_facts(
    ticker: str,
    facts: pd.DataFrame,
    output_path: str,
    years: int = 15,
    concepts: list[str] | None = None,
    write_html: bool = False,
) -> None:
    """File-writing wrapper around build_raw_facts."""
    fig = build_raw_facts(ticker, facts, years, concepts)
    if fig is None:
        return
    _write_figure(fig, output_path, write_html)