"""Accuracy of a forecast population. No I/O and no cutoff selection.

Call ``overall_metrics``, ``error_quantiles``, ``metrics_by_hour_of_day``,
``metrics_by_wind_level_bucket``, and ``worst_days`` on the decision forecast
at the selected cutoff. Call ``metrics_by_horizon_bucket`` on every vintage.
"""

import math
from collections.abc import Sequence
from datetime import date

import pandas as pd

LONDON = "Europe/London"
HEADLINE_QUANTILES = (0.05, 0.10, 0.50, 0.90, 0.95)
HORIZON_EDGES = (0, 6, 12, 24, 36, 48)
# Fixed MW edges, not sample quantiles, so the buckets do not move between days.
WIND_LEVEL_EDGES = (0, 5000, 10000, 15000)

MetricValue = float | None
Overall = dict[str, int | MetricValue]


def overall_metrics(df: pd.DataFrame) -> Overall:
    """Headline scores for the rows in ``df``.

    ``error = forecast_mw - actual_mw``. A positive error is an over-forecast.

    A row is excluded when ``missing_actual`` is true, ``has_forecast`` is false,
    or either MW value is null. Excluded rows are counted in ``n_excluded`` and
    are not filled.

    ``bias = mean(error)``

    ``mae = mean(abs(error))``

    ``rmse = sqrt(mean(error ** 2))``

    ``normalized_mae = mae / mean(actual_mw)``

    ``bias``, ``mae``, and ``rmse`` are None when ``n`` is 0. ``normalized_mae``
    is also None when the mean actual is 0.
    """
    excluded = _excluded(df)
    usable = df.loc[~excluded]
    n_excluded = int(excluded.sum())
    if usable.empty:
        return _empty_overall(n_excluded)
    error = usable["forecast_mw"] - usable["actual_mw"]
    mae = float(error.abs().mean())
    mean_actual = float(usable["actual_mw"].mean())
    normalized = None if mean_actual == 0 else mae / mean_actual
    return {
        "n": int(len(usable)),
        "n_excluded": n_excluded,
        "bias": float(error.mean()),
        "mae": mae,
        "rmse": math.sqrt(float((error**2).mean())),
        "normalized_mae": normalized,
    }


def error_quantiles(
    df: pd.DataFrame,
    qs: tuple[float, ...] = HEADLINE_QUANTILES,
) -> dict[float, MetricValue]:
    """Quantiles of ``forecast_mw - actual_mw`` on the usable rows.

    Interpolation is linear: sort the ``n`` errors and read index ``(n - 1) * q``.
    The same rows are excluded as in ``overall_metrics``. Each quantile is None
    when no usable row remains.
    """
    usable = df.loc[~_excluded(df)]
    if usable.empty:
        return {q: None for q in qs}
    error = usable["forecast_mw"] - usable["actual_mw"]
    values = error.quantile(list(qs), interpolation="linear")
    return {q: float(values.iloc[i]) for i, q in enumerate(qs)}


def metrics_by_horizon_bucket(
    all_vintages_df: pd.DataFrame,
    edges: tuple[float, ...] = HORIZON_EDGES,
) -> list[dict[str, str | int | MetricValue]]:
    """``overall_metrics`` for every horizon bucket.

    Pass all forecast vintages, not the decision forecast. Intervals on ``edges``
    are half-open. Values below the first edge are ``<edge`` and values at or
    above the last edge are ``>=edge``. The default edges are 0, 6, 12, 24, 36,
    and 48 hours, so a horizon of 11.9 is in ``[6,12)`` and a horizon of 48 is
    in ``>=48``. A null horizon is not placed in a bucket.
    """
    return _metrics_by_bucket(all_vintages_df, all_vintages_df["horizon_hours"], edges)


def metrics_by_hour_of_day(df: pd.DataFrame) -> list[dict[str, int | MetricValue]]:
    """``overall_metrics`` for each Europe/London clock hour of ``start_time_utc``.

    Always 24 rows, hours 0 through 23. An hour with no usable pair keeps
    ``n = 0`` and None scores.
    """
    hours = df["start_time_utc"].dt.tz_convert(LONDON).dt.hour
    rows: list[dict[str, int | MetricValue]] = []
    for hour in range(24):
        metrics = overall_metrics(df.loc[hours == hour])
        rows.append({"hour": hour, **metrics})
    return rows


def metrics_by_wind_level_bucket(
    df: pd.DataFrame,
    edges: tuple[float, ...] = WIND_LEVEL_EDGES,
) -> list[dict[str, str | int | MetricValue]]:
    """``overall_metrics`` by actual MW.

    Default edges are 0, 5000, 10000, and 15000 MW: ``<0``, ``[0,5000)``,
    ``[5000,10000)``, ``[10000,15000)``, ``>=15000``. The edges are fixed, not
    quantiles of the sample. A null actual is not placed in a bucket.
    """
    return _metrics_by_bucket(df, df["actual_mw"], edges)


def worst_days(df: pd.DataFrame, n: int = 5) -> list[dict[str, date | float | int]]:
    """Delivery days with the highest MAE.

    The date is the UTC date of ``start_time_utc``. Within a day, ``mae``,
    ``bias``, and ``mean_actual`` use the same usable rows as ``overall_metrics``.
    Days with no usable pair are omitted. The list is sorted by MAE descending,
    then by date, and contains at most ``n`` days.
    """
    usable = df.loc[~_excluded(df)].copy()
    if usable.empty:
        return []
    error = usable["forecast_mw"] - usable["actual_mw"]
    usable = usable.assign(error=error, day=usable["start_time_utc"].dt.tz_convert("UTC").dt.date)
    records: list[dict[str, date | float | int]] = []
    for day, part in usable.groupby("day", sort=True):
        day_error = part["error"]
        records.append(
            {
                "date": day,
                "n": int(len(part)),
                "mae": float(day_error.abs().mean()),
                "bias": float(day_error.mean()),
                "mean_actual": float(part["actual_mw"].mean()),
            }
        )
    records.sort(key=lambda row: (-float(row["mae"]), row["date"]))
    return records[:n]


def error_histogram(df: pd.DataFrame, width: float = 500.0) -> list[dict[str, float | int]]:
    """Count usable errors in bins of ``width`` MW.

    Bins cover the errors in ``df``. Each bin is half-open on the right and the
    last bin is closed, so an error that lands on the final edge is kept. Empty
    bins are omitted. The default width is 500 MW.
    """
    usable = df.loc[~_excluded(df)]
    if usable.empty:
        return []
    error = usable["forecast_mw"] - usable["actual_mw"]
    low = math.floor(float(error.min()) / width) * width
    high = math.ceil(float(error.max()) / width) * width
    if high == low:
        high = low + width
    n_bins = int(round((high - low) / width))
    edges = [low + index * width for index in range(n_bins + 1)]
    rows: list[dict[str, float | int]] = []
    last = len(edges) - 2
    for index in range(last + 1):
        left = edges[index]
        right = edges[index + 1]
        if index == last:
            chosen = error.loc[(error >= left) & (error <= right)]
        else:
            chosen = error.loc[(error >= left) & (error < right)]
        count = int(len(chosen))
        if count == 0:
            continue
        rows.append({"edge_low_mw": float(left), "edge_high_mw": float(right), "count": count})
    return rows


def _excluded(df: pd.DataFrame) -> pd.Series:
    """True when the row cannot form an error."""
    if df.empty:
        return pd.Series(False, index=df.index)
    missing_actual = df["missing_actual"].fillna(True).astype(bool)
    missing_forecast = ~df["has_forecast"].fillna(False).astype(bool)
    return missing_actual | missing_forecast | df["actual_mw"].isna() | df["forecast_mw"].isna()


def _empty_overall(n_excluded: int) -> Overall:
    return {
        "n": 0,
        "n_excluded": n_excluded,
        "bias": None,
        "mae": None,
        "rmse": None,
        "normalized_mae": None,
    }


def _fmt(edge: float) -> str:
    number = float(edge)
    if number.is_integer():
        return str(int(number))
    return str(number)


def _bucket_labels(edges: Sequence[float]) -> list[str]:
    labels = [f"<{_fmt(edges[0])}"]
    labels.extend(
        f"[{_fmt(lo)},{_fmt(hi)})" for lo, hi in zip(edges, edges[1:], strict=False)
    )
    labels.append(f">={_fmt(edges[-1])}")
    return labels


def _metrics_by_bucket(
    df: pd.DataFrame,
    values: pd.Series,
    edges: Sequence[float],
) -> list[dict[str, str | int | MetricValue]]:
    labels = _bucket_labels(edges)
    assigned = pd.cut(
        values,
        bins=[-math.inf, *edges, math.inf],
        right=False,
        labels=labels,
    )
    rows: list[dict[str, str | int | MetricValue]] = []
    for label in labels:
        metrics = overall_metrics(df.loc[assigned == label])
        rows.append({"label": label, **metrics})
    return rows
