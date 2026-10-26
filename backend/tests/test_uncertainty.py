"""Firm wind. Expected numbers are computed by hand in the comments."""

from datetime import date

import pandas as pd
from app.services.uncertainty import (
    apply_band,
    day_kpis,
    historical_error_quantiles,
    prior_decision_errors,
)

LONDON = "Europe/London"


def _utc(value: str) -> pd.Timestamp:
    return pd.Timestamp(value, tz="UTC")


def _history() -> tuple[pd.DataFrame, pd.DataFrame]:
    """One half-hour per day. Later days exist so a leak would change the quantile.

    2026-01-01: 110 - 100 = +10. A 09:01 publish of 9999 MW is after the cutoff.
    2026-01-02: 120 - 100 = +20
    2026-01-03: 130 - 100 = +30
    2026-01-04: 10000 - 0 = +10000, the selected day, excluded
    2026-01-05: 20000 - 0 = +20000, after the selected day, excluded
    """
    forecasts = pd.DataFrame(
        {
            "start_time_utc": [
                _utc("2026-01-01T00:00:00Z"),
                _utc("2026-01-01T00:00:00Z"),
                _utc("2026-01-02T00:00:00Z"),
                _utc("2026-01-03T00:00:00Z"),
                _utc("2026-01-04T00:00:00Z"),
                _utc("2026-01-05T00:00:00Z"),
            ],
            "publish_time_utc": [
                _utc("2025-12-31T08:00:00Z"),
                _utc("2025-12-31T09:01:00Z"),
                _utc("2026-01-01T08:00:00Z"),
                _utc("2026-01-02T08:00:00Z"),
                _utc("2026-01-03T08:00:00Z"),
                _utc("2026-01-04T08:00:00Z"),
            ],
            "forecast_mw": [110.0, 9999.0, 120.0, 130.0, 10000.0, 20000.0],
            "horizon_hours": [16.0, 14.983333, 16.0, 16.0, 16.0, 16.0],
        }
    )
    actuals = pd.DataFrame(
        {
            "start_time_utc": [
                _utc("2026-01-01T00:00:00Z"),
                _utc("2026-01-02T00:00:00Z"),
                _utc("2026-01-03T00:00:00Z"),
                _utc("2026-01-04T00:00:00Z"),
                _utc("2026-01-05T00:00:00Z"),
            ],
            "actual_mw": [100.0, 100.0, 100.0, 0.0, 0.0],
        }
    )
    return forecasts, actuals


def test_historical_quantiles_ignore_the_selected_day_and_later_days() -> None:
    """Pooled errors are +10, +20, +30. Later errors of +10000 and +20000 stay out."""
    # sorted 10, 20, 30. n = 3
    # P10 index (3 - 1) * 0.10 = 0.2 -> 10 + 0.2 * 10 = 12
    # P90 index (3 - 1) * 0.90 = 1.8 -> 20 + 0.8 * 10 = 28
    forecasts, actuals = _history()

    result = historical_error_quantiles(forecasts, actuals, date(2026, 1, 4), "09:00", LONDON)
    history = prior_decision_errors(forecasts, actuals, date(2026, 1, 4), "09:00", LONDON)

    assert history.prior_days_used == 3
    assert history.values == [10.0, 20.0, 30.0]
    assert result is not None
    assert result[0.10] == 12
    assert result[0.90] == 28


def test_historical_quantiles_return_none_below_min_days() -> None:
    """Two prior days are not enough for the default of three. Two is enough at min_days=2."""
    # errors +10, +20
    # P10 index 0.1 -> 11
    # P90 index 0.9 -> 19
    forecasts, actuals = _history()

    assert (
        historical_error_quantiles(forecasts, actuals, date(2026, 1, 3), "09:00", LONDON) is None
    )
    two_days = historical_error_quantiles(
        forecasts,
        actuals,
        date(2026, 1, 3),
        "09:00",
        LONDON,
        min_days=2,
    )
    assert two_days is not None
    assert two_days[0.10] == 11
    assert two_days[0.90] == 19


def test_apply_band_clips_firm_wind_at_zero() -> None:
    """P90 error above the forecast clips firm wind to 0. A gap stays null."""
    # forecast 100, P10 -20, P90 +150
    # lower = max(0, 100 - 150) = 0
    # upper = 100 - (-20) = 120
    # forecast 200 -> lower = max(0, 200 - 150) = 50, upper = 220
    decision = pd.DataFrame(
        {
            "start_time_utc": [_utc("2026-01-15T00:00:00Z"), _utc("2026-01-15T00:30:00Z")],
            "forecast_mw": [100.0, 200.0],
            "has_forecast": [True, True],
        }
    )

    band = apply_band(decision, error_q10=-20, error_q90=150)

    assert band.loc[0, "lower_mw"] == 0
    assert band.loc[0, "upper_mw"] == 120
    assert band.loc[0, "firm_mw"] == 0
    assert band.loc[1, "lower_mw"] == 50
    assert band.loc[1, "upper_mw"] == 220
    assert band.loc[1, "firm_mw"] == 50

    gap = apply_band(
        pd.DataFrame({"forecast_mw": [pd.NA], "has_forecast": [False]}),
        error_q10=-20,
        error_q90=150,
    )
    assert pd.isna(gap.loc[0, "firm_mw"])
    assert pd.isna(apply_band(decision, None, None).loc[0, "lower_mw"])


def test_day_kpis_use_hourly_slot_mwh_and_forecast_age() -> None:
    """An hourly forecast is MW times 1.0 h. Age is cutoff minus publish time."""
    # starts 00:00, 00:30 (empty), 01:00, 02:00. The shortest forecast gap is 1 h.
    # expected = 10 * 1 + 30 * 1 + 8 * 1 = 48. The empty slot adds nothing.
    # firm = 0 * 1 + 10 * 1 + 4 * 1 = 14
    # ages from 09:00Z: 08:00 -> 1 h, 07:00 -> 2 h, 05:00 -> 4 h
    # min 1, median 2, max 4. The empty slot has no publish time.
    cutoff = _utc("2026-01-14T09:00:00Z")
    decision = pd.DataFrame(
        {
            "start_time_utc": [
                _utc("2026-01-15T00:00:00Z"),
                _utc("2026-01-15T00:30:00Z"),
                _utc("2026-01-15T01:00:00Z"),
                _utc("2026-01-15T02:00:00Z"),
            ],
            "forecast_mw": [10.0, pd.NA, 30.0, 8.0],
            "firm_mw": [0.0, pd.NA, 10.0, 4.0],
            "has_forecast": [True, False, True, True],
            "publish_time_utc": [
                _utc("2026-01-14T08:00:00Z"),
                pd.NaT,
                _utc("2026-01-14T07:00:00Z"),
                _utc("2026-01-14T05:00:00Z"),
            ],
            "cutoff_utc": [cutoff, cutoff, cutoff, cutoff],
        }
    )

    kpis = day_kpis(decision)

    assert kpis["expected_mwh"] == 48
    assert kpis["firm_mwh"] == 14
    half_hour = pd.DataFrame(
        {
            "start_time_utc": [
                _utc("2026-01-15T00:00:00Z"),
                _utc("2026-01-15T00:30:00Z"),
            ],
            "forecast_mw": [10.0, 20.0],
            "firm_mw": [4.0, 6.0],
        }
    )
    half = day_kpis(half_hour)
    assert half["expected_mwh"] == 15
    assert half["firm_mwh"] == 5
    assert kpis["forecast_age_hours"] == {"min": 1.0, "median": 2.0, "max": 4.0}
    assert day_kpis(decision.iloc[0:0])["forecast_age_hours"]["min"] is None
    assert day_kpis(pd.DataFrame({"forecast_mw": [pd.NA], "firm_mw": [pd.NA]}))[
        "expected_mwh"
    ] is None
