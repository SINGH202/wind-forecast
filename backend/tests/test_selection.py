"""Decision-cutoff and horizon selection. Hand-built frames only."""

from datetime import date

import pandas as pd
from app.services.selection import (
    build_cutoff_utc,
    decision_forecast,
    forecast_for_horizon,
    horizon_forecast,
    join_with_actuals,
    latest_forecast_at,
)

LONDON = "Europe/London"


def _utc(value: str) -> pd.Timestamp:
    return pd.Timestamp(value, tz="UTC")


def _forecasts(rows: list[tuple[str, str, float, float]]) -> pd.DataFrame:
    """Rows are start, publish, forecast MW, horizon hours."""
    return pd.DataFrame(
        {
            "start_time_utc": [_utc(row[0]) for row in rows],
            "publish_time_utc": [_utc(row[1]) for row in rows],
            "forecast_mw": [row[2] for row in rows],
            "horizon_hours": [row[3] for row in rows],
        }
    )


def test_exact_cutoff_is_kept_and_one_minute_later_is_not() -> None:
    """publishTime == cutoff is eligible; one minute later is leakage."""
    cutoff = _utc("2026-01-14T09:00:00Z")
    start = "2026-01-15T00:00:00Z"
    forecasts = _forecasts(
        [
            (start, "2026-01-14T08:00:00Z", 50.0, 16.0),
            (start, "2026-01-14T09:00:00Z", 80.0, 15.0),
            (start, "2026-01-14T09:01:00Z", 999.0, 14.983333),
        ]
    )

    selected = latest_forecast_at(forecasts, cutoff)

    assert len(selected) == 1
    assert selected.loc[0, "forecast_mw"] == 80.0
    assert selected.loc[0, "publish_time_utc"] == cutoff


def test_latest_valid_publish_wins_for_one_target() -> None:
    """Several rows for one start time: the greatest publishTime still <= cutoff."""
    cutoff = _utc("2026-01-14T09:00:00Z")
    start = "2026-01-15T12:00:00Z"
    other = "2026-01-15T12:30:00Z"
    forecasts = _forecasts(
        [
            (start, "2026-01-14T07:00:00Z", 10.0, 29.0),
            (start, "2026-01-14T08:30:00Z", 20.0, 27.5),
            (other, "2026-01-14T09:00:00Z", 30.0, 27.5),
            (start, "2026-01-14T09:30:00Z", 40.0, 26.5),
        ]
    )

    selected = latest_forecast_at(forecasts, cutoff).set_index("start_time_utc")

    assert selected.loc[_utc(start), "forecast_mw"] == 20.0
    assert selected.loc[_utc(other), "forecast_mw"] == 30.0
    assert _utc("2026-01-14T09:30:00Z") not in set(selected["publish_time_utc"])


def test_horizon_12_excludes_11_9() -> None:
    """H=12 keeps the latest publish with horizon >= 12 and drops 11.9h."""
    start = "2026-01-02T00:00:00Z"
    forecasts = _forecasts(
        [
            (start, "2026-01-01T04:00:00Z", 10.0, 20.0),
            (start, "2026-01-01T12:00:00Z", 12.0, 12.0),
            (start, "2026-01-01T12:06:00Z", 99.0, 11.9),
        ]
    )

    selected = forecast_for_horizon(forecasts, 12)

    assert len(selected) == 1
    assert selected.loc[0, "forecast_mw"] == 12.0
    assert selected.loc[0, "horizon_hours"] == 12.0


def test_build_cutoff_utc_winter_and_summer() -> None:
    """09:00 Europe/London is 09:00 UTC in January and 08:00 UTC in July."""
    winter = build_cutoff_utc(date(2026, 1, 15), "09:00", LONDON)
    summer = build_cutoff_utc(date(2026, 7, 15), "09:00", LONDON)

    assert pd.Timestamp(winter) == _utc("2026-01-14T09:00:00Z")
    assert pd.Timestamp(summer) == _utc("2026-07-14T08:00:00Z")


def test_decision_forecast_is_48_london_half_hours_and_flags_gaps() -> None:
    """January delivery day D is 48 London half-hours; a late publish is not a forecast."""
    start_ok = "2026-01-15T00:00:00Z"
    start_late = "2026-01-15T00:30:00Z"
    forecasts = _forecasts(
        [
            (start_ok, "2026-01-14T08:00:00Z", 40.0, 16.0),
            (start_ok, "2026-01-14T09:00:00Z", 70.0, 15.0),
            (start_late, "2026-01-14T09:01:00Z", 999.0, 15.483333),
        ]
    )

    selected = decision_forecast(forecasts, date(2026, 1, 15), "09:00", LONDON)

    assert len(selected) == 48
    assert selected["start_time_utc"].is_unique
    assert "has_forecast" in selected.columns
    starts = list(selected["start_time_utc"])
    assert starts[0] == _utc("2026-01-15T00:00:00Z")
    assert starts[-1] == _utc("2026-01-15T23:30:00Z")
    assert starts[1] - starts[0] == pd.Timedelta(minutes=30)
    by_start = selected.set_index("start_time_utc")
    assert bool(by_start.loc[_utc(start_ok), "has_forecast"]) is True
    assert by_start.loc[_utc(start_ok), "forecast_mw"] == 70.0
    assert bool(by_start.loc[_utc(start_late), "has_forecast"]) is False
    assert pd.isna(by_start.loc[_utc(start_late), "forecast_mw"])
    assert int(by_start["has_forecast"].sum()) == 1


def test_join_with_actuals_keeps_every_selected_row() -> None:
    """Missing actuals are flagged. No selected half-hour is dropped."""
    selected = pd.DataFrame(
        {
            "start_time_utc": [_utc("2026-01-15T00:00:00Z"), _utc("2026-01-15T00:30:00Z")],
            "forecast_mw": [70.0, pd.NA],
            "has_forecast": [True, False],
        }
    )
    actuals = pd.DataFrame(
        {
            "start_time_utc": [_utc("2026-01-15T00:00:00Z")],
            "actual_mw": [65.0],
        }
    )

    joined = join_with_actuals(selected, actuals)

    assert len(joined) == 2
    assert list(joined["start_time_utc"]) == list(selected["start_time_utc"])
    by_start = joined.set_index("start_time_utc")
    assert bool(by_start.loc[_utc("2026-01-15T00:00:00Z"), "missing_actual"]) is False
    assert by_start.loc[_utc("2026-01-15T00:00:00Z"), "actual_mw"] == 65.0
    assert bool(by_start.loc[_utc("2026-01-15T00:30:00Z"), "missing_actual"]) is True
    assert pd.isna(by_start.loc[_utc("2026-01-15T00:30:00Z"), "actual_mw"])


def test_horizon_tie_uses_latest_publish_not_largest_horizon() -> None:
    """Two eligible horizons: the later publishTime wins, not the longer horizon."""
    start = "2026-01-02T00:00:00Z"
    forecasts = _forecasts(
        [
            (start, "2026-01-01T00:00:00Z", 5.0, 24.0),
            (start, "2026-01-01T12:00:00Z", 9.0, 12.0),
        ]
    )

    selected = forecast_for_horizon(forecasts, 12)

    assert selected.loc[0, "forecast_mw"] == 9.0


def test_horizon_forecast_keeps_48_rows_and_drops_a_short_horizon() -> None:
    """H=12 keeps horizon 12 and leaves the 11.9h publish off the grid."""
    start = "2026-01-15T00:00:00Z"
    forecasts = _forecasts(
        [
            (start, "2026-01-14T12:00:00Z", 12.0, 12.0),
            (start, "2026-01-14T12:06:00Z", 99.0, 11.9),
        ]
    )

    selected = horizon_forecast(forecasts, date(2026, 1, 15), 12, LONDON)

    assert len(selected) == 48
    midnight = selected.set_index("start_time_utc").loc[_utc(start)]
    assert midnight["forecast_mw"] == 12.0
    assert bool(midnight["has_forecast"]) is True
    assert int(selected["has_forecast"].sum()) == 1
