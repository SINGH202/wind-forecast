"""Firm wind from decision-forecast errors on earlier delivery days. No I/O.

Error = forecast_mw - actual_mw. A positive error means the forecast was too high.
Example: a 1000 MW forecast and a 700 MW actual is an error of +300 MW. If +300 is
the P90 of earlier days, firm wind is 1000 - 300 = 700 MW. That is the generation
the buyer can count on. The upper edge uses the P10 of error, which is a smaller
number, so the band sits above the forecast when past forecasts ran low.
"""

from datetime import date
from typing import NamedTuple

import pandas as pd

from app.services.selection import decision_forecast, join_with_actuals

HOURLY_SLOT_H = 1.0
HALF_HOUR_H = 0.5


class PriorErrors(NamedTuple):
    """Paired decision-forecast errors and how many earlier days contributed."""

    values: list[float]
    prior_days_used: int


def prior_decision_errors(
    forecasts: pd.DataFrame,
    actuals: pd.DataFrame,
    before_day: date,
    cutoff_hhmm: str,
    tz: str,
) -> PriorErrors:
    """Decision-forecast errors for delivery days strictly before ``before_day``.

    A day counts only when at least one half-hour has both a decision forecast and
    an actual. Days on or after ``before_day`` are left out.
    """
    if forecasts.empty:
        return PriorErrors([], 0)
    local_days = forecasts["start_time_utc"].dt.tz_convert(tz).dt.date
    candidate_days = sorted({day for day in local_days if day < before_day})
    errors: list[float] = []
    days_used = 0
    for day in candidate_days:
        paired = _paired_errors(forecasts, actuals, day, cutoff_hhmm, tz)
        if paired.empty:
            continue
        days_used += 1
        errors.extend(float(value) for value in paired.tolist())
    return PriorErrors(errors, days_used)


def historical_error_quantiles(
    forecasts: pd.DataFrame,
    actuals: pd.DataFrame,
    before_day: date,
    cutoff_hhmm: str,
    tz: str,
    qs: tuple[float, ...] = (0.10, 0.90),
    min_days: int = 3,
) -> dict[float, float] | None:
    """Pooled decision-forecast error quantiles for delivery days strictly before ``before_day``.

    Each prior day uses the same cutoff clock as the decision view. A forecast
    published after that day's cutoff is not an error in this pool. Days on or
    after ``before_day`` are ignored, so a bad outcome on the selected day cannot
    move the band.

    Quantiles are linear: sort the paired errors and read index ``(n - 1) * q``.
    A day counts toward ``min_days`` only when it has at least one paired error.
    The return value is None when fewer than ``min_days`` such days exist.
    """
    history = prior_decision_errors(forecasts, actuals, before_day, cutoff_hhmm, tz)
    if history.prior_days_used < min_days or not history.values:
        return None
    values = pd.Series(history.values, dtype="float64").quantile(list(qs), interpolation="linear")
    return {q: float(values.iloc[i]) for i, q in enumerate(qs)}


def apply_band(
    decision_df: pd.DataFrame,
    error_q10: float | None,
    error_q90: float | None,
) -> pd.DataFrame:
    """Add the firm-wind band to a decision-forecast frame.

    ``lower_mw = max(0, forecast_mw - error_q90)``

    ``upper_mw = forecast_mw - error_q10``

    ``firm_mw = lower_mw``

    Example: forecast 100 MW, P10 of error -20 MW, P90 of error +150 MW.
    ``lower_mw = max(0, 100 - 150) = 0`` and ``upper_mw = 100 - (-20) = 120``.
    The unclipped firm value would be -50 MW, and it is clipped to 0.
    A missing forecast stays null. If either quantile is None, all three
    columns are null.
    """
    out = decision_df.copy()
    if error_q10 is None or error_q90 is None:
        out["lower_mw"] = pd.NA
        out["upper_mw"] = pd.NA
        out["firm_mw"] = pd.NA
        return out
    out["lower_mw"] = (out["forecast_mw"] - error_q90).clip(lower=0)
    out["upper_mw"] = out["forecast_mw"] - error_q10
    out["firm_mw"] = out["lower_mw"]
    return out


def day_kpis(decision_df: pd.DataFrame) -> dict[str, float | dict[str, float | None] | None]:
    """Day energy and the age of the forecasts that made the cutoff.

    ``expected_mwh`` sums ``forecast_mw * slot_hours`` where a forecast is present.
    ``firm_mwh`` sums ``firm_mw * slot_hours`` where firm MW is present.
    ``slot_hours`` is the gap between forecast start times: 1.0 h for an hourly
    WINDFOR slot, 0.5 h when forecasts land on both :00 and :30. An empty slot
    is left out of the sum; it is not treated as 0 MW. The sum is None when no
    slot contributes.

    ``forecast_age_hours`` is ``cutoff_utc - publish_time_utc`` in hours, for rows
    with a forecast. The frame carries ``cutoff_utc`` on each row. ``min`` is the
    freshest forecast that made the cutoff, ``max`` is the oldest, and ``median``
    is the middle age. With no selected forecast every age is None, not zero.
    """
    hours = _slot_hours(decision_df)
    return {
        "expected_mwh": _mwh(decision_df, "forecast_mw", hours),
        "firm_mwh": _mwh(decision_df, "firm_mw", hours),
        "forecast_age_hours": _forecast_ages(decision_df),
    }


def _paired_errors(
    forecasts: pd.DataFrame,
    actuals: pd.DataFrame,
    delivery_day: date,
    cutoff_hhmm: str,
    tz: str,
) -> pd.Series:
    selected = decision_forecast(forecasts, delivery_day, cutoff_hhmm, tz)
    joined = join_with_actuals(selected, actuals)
    usable = joined.loc[
        joined["has_forecast"]
        & ~joined["missing_actual"]
        & joined["forecast_mw"].notna()
        & joined["actual_mw"].notna()
    ]
    return usable["forecast_mw"] - usable["actual_mw"]


def _slot_hours(frame: pd.DataFrame) -> float:
    """Hours represented by one present forecast.

    The shortest gap between forecast start times is the slot length, so a
    missing hour does not stretch the previous slot. Hourly WINDFOR starts are
    1.0 h apart. Forecasts on both :00 and :30 are 0.5 h apart. One forecast on
    the hour, or a frame without start times, is 1.0 h.
    """
    if "start_time_utc" not in frame.columns or "forecast_mw" not in frame.columns:
        return HOURLY_SLOT_H
    present = (
        frame.loc[frame["forecast_mw"].notna(), "start_time_utc"].dropna().sort_values()
    )
    if len(present) >= 2:
        gaps = present.diff().dt.total_seconds().dropna() / 3600
        positive = gaps[gaps > 0]
        if not positive.empty:
            return float(positive.min())
    if len(present) == 1 and pd.Timestamp(present.iloc[0]).minute == 30:
        return HALF_HOUR_H
    return HOURLY_SLOT_H


def _mwh(frame: pd.DataFrame, column: str, slot_hours: float) -> float | None:
    if column not in frame.columns:
        return None
    present = frame[column].dropna()
    if present.empty:
        return None
    return float((present * slot_hours).sum())


def _forecast_ages(decision_df: pd.DataFrame) -> dict[str, float | None]:
    empty = {"min": None, "median": None, "max": None}
    if "publish_time_utc" not in decision_df or "cutoff_utc" not in decision_df:
        return empty
    rows = decision_df
    if "has_forecast" in rows:
        rows = rows.loc[rows["has_forecast"].fillna(False).astype(bool)]
    rows = rows.loc[rows["publish_time_utc"].notna() & rows["cutoff_utc"].notna()]
    if rows.empty:
        return empty
    age_hours = (rows["cutoff_utc"] - rows["publish_time_utc"]).dt.total_seconds() / 3600
    return {
        "min": float(age_hours.min()),
        "median": float(age_hours.median()),
        "max": float(age_hours.max()),
    }
