"""Choose one forecast row per half-hour. No I/O."""

from datetime import date, timedelta

import pandas as pd


def latest_forecast_at(forecasts: pd.DataFrame, cutoff_utc: pd.Timestamp) -> pd.DataFrame:
    """Per start time, the row with the greatest publish time at or before the cutoff.

    A publish time one minute after the cutoff is excluded. A start time with no
    eligible row is omitted; the 48-row decision grid puts that gap back.
    """
    eligible = forecasts.loc[forecasts["publish_time_utc"] <= cutoff_utc]
    if eligible.empty:
        return forecasts.iloc[0:0].copy()
    ordered = eligible.sort_values(
        ["start_time_utc", "publish_time_utc"],
        kind="mergesort",
    )
    return ordered.groupby("start_time_utc", as_index=False).tail(1).reset_index(drop=True)


def forecast_for_horizon(forecasts: pd.DataFrame, min_horizon_hours: float) -> pd.DataFrame:
    """Per start time, the latest publish whose horizon is at least ``min_horizon_hours``.

    Horizon is ``start_time - publish_time`` in hours. A horizon of 11.9 does not
    satisfy a minimum of 12. This is not the decision cutoff.
    """
    eligible = forecasts.loc[forecasts["horizon_hours"] >= min_horizon_hours]
    if eligible.empty:
        return forecasts.iloc[0:0].copy()
    ordered = eligible.sort_values(
        ["start_time_utc", "publish_time_utc"],
        kind="mergesort",
    )
    return ordered.groupby("start_time_utc", as_index=False).tail(1).reset_index(drop=True)


def build_cutoff_utc(delivery_day: date, cutoff_hhmm: str, tz: str) -> pd.Timestamp:
    """Cutoff clock time on day D-1 in ``tz``, as a UTC timestamp.

    09:00 Europe/London is 09:00 UTC in January and 08:00 UTC in July.
    The previous calendar day is used, so a DST boundary does not shift the clock time.
    """
    hour_text, minute_text = cutoff_hhmm.split(":")
    previous = delivery_day - timedelta(days=1)
    local = pd.Timestamp(
        year=previous.year,
        month=previous.month,
        day=previous.day,
        hour=int(hour_text),
        minute=int(minute_text),
        tz=tz,
    )
    return local.tz_convert("UTC")


def decision_forecast(
    forecasts: pd.DataFrame,
    delivery_day: date,
    cutoff_hhmm: str,
    tz: str,
) -> pd.DataFrame:
    """48 half-hours of the London delivery day, with the decision forecast filled in.

    The grid is local midnight through 23:30 in ``tz``. January has no DST, so those
    instants match 00:00Z through 23:30Z. ``has_forecast`` is false when nothing was
    published at or before the cutoff. The row is kept.
    """
    chosen = latest_forecast_at(forecasts, build_cutoff_utc(delivery_day, cutoff_hhmm, tz))
    return _fill_half_hour_grid(forecasts, delivery_day, tz, chosen)


def horizon_forecast(
    forecasts: pd.DataFrame,
    delivery_day: date,
    min_horizon_hours: float,
    tz: str,
) -> pd.DataFrame:
    """48 London half-hours with the latest forecast at least ``min_horizon_hours`` ahead.

    This is the horizon view. It does not apply the decision cutoff.
    """
    chosen = forecast_for_horizon(forecasts, min_horizon_hours)
    return _fill_half_hour_grid(forecasts, delivery_day, tz, chosen)


def join_with_actuals(selected: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    """Left join actual MW onto the selected rows. No selected row is dropped.

    ``missing_actual`` is true when that start time has no actual.
    """
    merged = selected.merge(actuals, on="start_time_utc", how="left")
    merged["missing_actual"] = merged["actual_mw"].isna()
    return merged


def _fill_half_hour_grid(
    forecasts: pd.DataFrame,
    delivery_day: date,
    tz: str,
    chosen: pd.DataFrame,
) -> pd.DataFrame:
    """One row per London half-hour. ``forecasts`` supplies columns when nothing was chosen."""
    local_midnight = pd.Timestamp(
        year=delivery_day.year,
        month=delivery_day.month,
        day=delivery_day.day,
        tz=tz,
    )
    starts = pd.date_range(local_midnight, periods=48, freq="30min")
    grid = pd.DataFrame({"start_time_utc": starts.tz_convert("UTC")})
    columns = chosen if not chosen.empty else forecasts.iloc[0:0]
    merged = grid.merge(columns, on="start_time_utc", how="left")
    merged["has_forecast"] = merged["forecast_mw"].notna()
    return merged
