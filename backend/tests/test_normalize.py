"""Normalization of hand-built Elexon rows."""

import pandas as pd
import pytest
from app.services.normalize import NormalizeError, normalize_actuals, normalize_forecasts


def test_actuals_keep_last_start_time_and_drop_exact_duplicates() -> None:
    """The later generation wins when the same start time is repeated."""
    rows = [
        {"startTime": "2026-01-01T00:30:00Z", "generation": 20},
        {"startTime": "2026-01-01T00:00:00Z", "generation": 10},
        {"startTime": "2026-01-01T00:00:00Z", "generation": 10},
        {"startTime": "2026-01-01T00:00:00Z", "generation": 15},
    ]

    frame = normalize_actuals(rows)

    assert list(frame.columns) == ["start_time_utc", "actual_mw"]
    assert frame["actual_mw"].tolist() == [15, 20]
    assert str(frame["start_time_utc"].dt.tz) == "UTC"


def test_actuals_convert_offset_timestamps_to_utc() -> None:
    """An explicit offset is shifted to UTC."""
    rows = [{"startTime": "2026-01-02T01:00:00+01:00", "generation": 8}]

    frame = normalize_actuals(rows)

    assert frame.loc[0, "start_time_utc"] == pd.Timestamp("2026-01-02T00:00:00Z")
    assert frame.loc[0, "actual_mw"] == 8


def test_forecast_horizon_is_start_minus_publish() -> None:
    """09:00 published, next midnight starts, is a 15 hour horizon."""
    rows = [
        {
            "startTime": "2026-01-02T00:00:00Z",
            "publishTime": "2026-01-01T09:00:00Z",
            "generation": 100,
        }
    ]

    frame = normalize_forecasts(rows)

    assert frame.loc[0, "horizon_hours"] == 15.0
    assert frame.loc[0, "forecast_mw"] == 100
    assert list(frame.columns) == [
        "start_time_utc",
        "publish_time_utc",
        "forecast_mw",
        "horizon_hours",
    ]


def test_forecasts_keep_last_pair_and_sort() -> None:
    """Same start and publish keeps the last generation, then rows are sorted."""
    rows = [
        {
            "startTime": "2026-01-02T00:00:00+00:00",
            "publishTime": "2026-01-01T12:00:00Z",
            "generation": 1,
        },
        {
            "startTime": "2026-01-02T00:00:00Z",
            "publishTime": "2026-01-01T09:00:00Z",
            "generation": 4,
        },
        {
            "startTime": "2026-01-02T00:00:00Z",
            "publishTime": "2026-01-01T09:00:00Z",
            "generation": 7,
        },
    ]

    frame = normalize_forecasts(rows)

    assert frame["forecast_mw"].tolist() == [7, 1]
    assert frame["publish_time_utc"].tolist() == [
        pd.Timestamp("2026-01-01T09:00:00Z"),
        pd.Timestamp("2026-01-01T12:00:00Z"),
    ]


def test_null_key_raises() -> None:
    """A null start, publish, or generation is an error, not a dropped row."""
    with pytest.raises(NormalizeError, match="startTime"):
        normalize_actuals([{"startTime": None, "generation": 1}])
    with pytest.raises(NormalizeError, match="generation"):
        normalize_actuals([{"startTime": "2026-01-01T00:00:00Z", "generation": None}])
    with pytest.raises(NormalizeError, match="publishTime"):
        normalize_forecasts(
            [
                {
                    "startTime": "2026-01-02T00:00:00Z",
                    "publishTime": None,
                    "generation": 1,
                }
            ]
        )


def test_empty_input_has_the_output_columns() -> None:
    """No rows is an empty frame, not an error."""
    actuals = normalize_actuals([])
    forecasts = normalize_forecasts([])

    assert list(actuals.columns) == ["start_time_utc", "actual_mw"]
    assert actuals.empty
    assert list(forecasts.columns) == [
        "start_time_utc",
        "publish_time_utc",
        "forecast_mw",
        "horizon_hours",
    ]
    assert forecasts.empty
