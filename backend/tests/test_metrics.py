"""Accuracy metrics. Expected numbers are computed by hand in the comments."""

import math
from datetime import date

import pandas as pd
import pytest
from app.services.metrics import (
    error_histogram,
    error_quantiles,
    metrics_by_horizon_bucket,
    metrics_by_hour_of_day,
    metrics_by_wind_level_bucket,
    overall_metrics,
    worst_days,
)


def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    columns = [
        "start_time_utc",
        "actual_mw",
        "forecast_mw",
        "horizon_hours",
        "missing_actual",
        "has_forecast",
    ]
    frame = pd.DataFrame(rows, columns=columns)
    frame["start_time_utc"] = pd.to_datetime(frame["start_time_utc"], utc=True)
    return frame


def _row(
    start: str,
    actual: float | None,
    forecast: float | None,
    horizon: float | None,
    *,
    missing_actual: bool = False,
    has_forecast: bool = True,
) -> dict[str, object]:
    return {
        "start_time_utc": start,
        "actual_mw": actual,
        "forecast_mw": forecast,
        "horizon_hours": horizon,
        "missing_actual": missing_actual,
        "has_forecast": has_forecast,
    }


def test_overall_metrics_hand_computed() -> None:
    """errors +10, -20, +30. One missing row is counted and ignored."""
    # bias = (10 - 20 + 30) / 3 = 20/3 ≈ 6.667
    # mae = (10 + 20 + 30) / 3 = 20
    # rmse = sqrt((100 + 400 + 900) / 3) = sqrt(1400/3) ≈ 21.602
    # mean actual = (100 + 50 + 30) / 3 = 60
    # normalized_mae = 20 / 60 = 1/3
    frame = _frame(
        [
            _row("2026-01-15T00:00:00Z", 100, 110, 15),
            _row("2026-01-15T00:30:00Z", 50, 30, 15.5),
            _row("2026-01-15T01:00:00Z", 30, 60, 16),
            _row("2026-01-15T01:30:00Z", None, 999, None, missing_actual=True, has_forecast=False),
        ]
    )

    result = overall_metrics(frame)

    assert result["n"] == 3
    assert result["n_excluded"] == 1
    assert result["bias"] == pytest.approx(20 / 3)
    assert result["mae"] == 20
    assert result["rmse"] == pytest.approx(math.sqrt(1400 / 3))
    assert result["normalized_mae"] == pytest.approx(1 / 3)


def test_overall_metrics_empty_and_all_missing() -> None:
    """No usable pairs: every score is None, and exclusions are counted."""
    empty = _frame([])
    missing = _frame(
        [
            _row("2026-01-15T00:00:00Z", None, None, 1, missing_actual=True, has_forecast=False),
            _row("2026-01-15T00:30:00Z", 10, None, 1, has_forecast=False),
        ]
    )

    empty_result = overall_metrics(empty)
    missing_result = overall_metrics(missing)

    assert empty_result == {
        "n": 0,
        "n_excluded": 0,
        "bias": None,
        "mae": None,
        "rmse": None,
        "normalized_mae": None,
    }
    assert missing_result["n"] == 0
    assert missing_result["n_excluded"] == 2
    assert missing_result["mae"] is None
    assert missing_result["normalized_mae"] is None


def test_overall_metrics_zero_mean_actual() -> None:
    """errors +10 and -20 on actuals of 0. nMAE is None; the other scores stay."""
    # bias = (10 - 20) / 2 = -5
    # mae = (10 + 20) / 2 = 15
    # rmse = sqrt((100 + 400) / 2) = sqrt(250)
    frame = _frame(
        [
            _row("2026-01-15T00:00:00Z", 0, 10, 12),
            _row("2026-01-15T00:30:00Z", 0, -20, 12.5),
        ]
    )

    result = overall_metrics(frame)

    assert result["n"] == 2
    assert result["bias"] == -5
    assert result["mae"] == 15
    assert result["rmse"] == pytest.approx(math.sqrt(250))
    assert result["normalized_mae"] is None


def test_error_quantiles_hand_computed() -> None:
    """Linear quantile at index (n - 1) * q. An excluded +1000 does not move them."""
    # sorted errors: -20, 10, 30
    # q=0.05 -> -20 + 0.10 * 30 = -17
    # q=0.10 -> -20 + 0.20 * 30 = -14
    # q=0.50 -> 10
    # q=0.90 -> 10 + 0.80 * 20 = 26
    # q=0.95 -> 10 + 0.90 * 20 = 28
    frame = _frame(
        [
            _row("2026-01-15T00:00:00Z", 100, 110, 10),
            _row("2026-01-15T00:30:00Z", 50, 30, 10),
            _row("2026-01-15T01:00:00Z", 30, 60, 10),
            _row("2026-01-15T01:30:00Z", 1, 1001, 10, missing_actual=True),
        ]
    )

    result = error_quantiles(frame)

    assert result[0.05] == -17
    assert result[0.10] == -14
    assert result[0.50] == 10
    assert result[0.90] == 26
    assert result[0.95] == 28
    assert error_quantiles(frame.iloc[0:0]) == {
        0.05: None,
        0.10: None,
        0.50: None,
        0.90: None,
        0.95: None,
    }


def test_metrics_by_horizon_bucket() -> None:
    """11.9h stays below 12. Exactly 48h starts the top bucket."""
    # <0: error +10. bias 10, mae 10, rmse 10, mean actual 100, nMAE 0.1
    # [0,6): errors -20 and +30. bias 5, mae 25, rmse sqrt(650), mean actual 45
    # [6,12): one usable error 0 and one missing forecast. nMAE 0
    # >=48: error +4. mae 4, mean actual 4, nMAE 1
    frame = _frame(
        [
            _row("2026-01-15T00:00:00Z", 100, 110, -1),
            _row("2026-01-15T00:30:00Z", 50, 30, 0),
            _row("2026-01-15T01:00:00Z", 40, 70, 5),
            _row("2026-01-15T01:30:00Z", 10, 10, 11.9),
            _row("2026-01-15T02:00:00Z", 10, None, 8, has_forecast=False),
            _row("2026-01-15T02:30:00Z", 20, 25, 12),
            _row("2026-01-15T03:00:00Z", 8, 8, 36),
            _row("2026-01-15T03:30:00Z", 4, 8, 48),
        ]
    )

    rows = metrics_by_horizon_bucket(frame)
    by_label = {row["label"]: row for row in rows}

    assert [row["label"] for row in rows] == [
        "<0",
        "[0,6)",
        "[6,12)",
        "[12,24)",
        "[24,36)",
        "[36,48)",
        ">=48",
    ]
    assert by_label["<0"]["n"] == 1
    assert by_label["<0"]["mae"] == 10
    assert by_label["<0"]["normalized_mae"] == pytest.approx(0.1)
    assert by_label["[0,6)"]["n"] == 2
    assert by_label["[0,6)"]["bias"] == 5
    assert by_label["[0,6)"]["mae"] == 25
    assert by_label["[0,6)"]["rmse"] == pytest.approx(math.sqrt(650))
    assert by_label["[0,6)"]["normalized_mae"] == pytest.approx(25 / 45)
    assert by_label["[6,12)"]["n"] == 1
    assert by_label["[6,12)"]["n_excluded"] == 1
    assert by_label["[6,12)"]["mae"] == 0
    assert by_label["[12,24)"]["mae"] == 5
    assert by_label["[24,36)"]["n"] == 0
    assert by_label["[24,36)"]["mae"] is None
    assert by_label["[36,48)"]["n"] == 1
    assert by_label[">=48"]["mae"] == 4
    assert by_label[">=48"]["normalized_mae"] == 1


def test_metrics_by_hour_of_day_uses_london() -> None:
    """January 00:30Z is hour 0. July 00:30Z is hour 1."""
    # hour 0 errors +10 and -20: bias -5, mae 15, rmse sqrt(250), mean actual 90
    # hour 1 error +30: mae 30, mean actual 40, nMAE 0.75
    # hour 12 has only a missing actual
    frame = _frame(
        [
            _row("2026-01-15T00:00:00Z", 100, 110, 15),
            _row("2026-01-15T00:30:00Z", 80, 60, 15.5),
            _row("2026-07-15T00:30:00Z", 40, 70, 10),
            _row("2026-01-15T12:00:00Z", None, 5, 3, missing_actual=True, has_forecast=False),
        ]
    )

    rows = metrics_by_hour_of_day(frame)

    assert [row["hour"] for row in rows] == list(range(24))
    hour0 = rows[0]
    hour1 = rows[1]
    assert hour0["n"] == 2
    assert hour0["bias"] == -5
    assert hour0["mae"] == 15
    assert hour0["rmse"] == pytest.approx(math.sqrt(250))
    assert hour0["normalized_mae"] == pytest.approx(15 / 90)
    assert hour1["n"] == 1
    assert hour1["mae"] == 30
    assert hour1["normalized_mae"] == pytest.approx(0.75)
    assert rows[12]["n"] == 0
    assert rows[12]["n_excluded"] == 1
    assert rows[12]["mae"] is None
    assert rows[2]["n"] == 0


def test_metrics_by_wind_level_bucket() -> None:
    """Fixed actual-MW edges. 10 starts the next bucket; 20 starts the top one."""
    # [0,10): errors +10 and +10. bias 10, mae 10, mean actual 4.5, nMAE 10/4.5
    # [10,20): error 0, plus one missing forecast
    # >=20: error +10, mean actual 20, nMAE 0.5
    frame = _frame(
        [
            _row("2026-01-15T00:00:00Z", -5, -5, 10),
            _row("2026-01-15T00:30:00Z", 0, 10, 10),
            _row("2026-01-15T01:00:00Z", 9, 19, 10),
            _row("2026-01-15T01:30:00Z", 10, 10, 10),
            _row("2026-01-15T02:00:00Z", 15, None, 10, has_forecast=False),
            _row("2026-01-15T02:30:00Z", 20, 30, 10),
        ]
    )

    rows = metrics_by_wind_level_bucket(frame, edges=(0, 10, 20))
    by_label = {row["label"]: row for row in rows}

    assert [row["label"] for row in rows] == ["<0", "[0,10)", "[10,20)", ">=20"]
    assert by_label["<0"]["n"] == 1
    assert by_label["<0"]["mae"] == 0
    assert by_label["[0,10)"]["n"] == 2
    assert by_label["[0,10)"]["bias"] == 10
    assert by_label["[0,10)"]["mae"] == 10
    assert by_label["[0,10)"]["normalized_mae"] == pytest.approx(10 / 4.5)
    assert by_label["[10,20)"]["n"] == 1
    assert by_label["[10,20)"]["n_excluded"] == 1
    assert by_label["[10,20)"]["mae"] == 0
    assert by_label[">=20"]["mae"] == 10
    assert by_label[">=20"]["normalized_mae"] == pytest.approx(0.5)


def test_worst_days_orders_by_mae() -> None:
    """Day MAE uses only usable half-hours. The higher MAE is first."""
    # 2026-01-01 errors +10, -20: mae 15, bias -5, mean actual 90
    # 2026-01-02 error +30: mae 30, bias 30, mean actual 40
    # the missing row on 2026-01-01 does not create a third day
    frame = _frame(
        [
            _row("2026-01-01T00:00:00Z", 100, 110, 15),
            _row("2026-01-01T00:30:00Z", 80, 60, 15.5),
            _row("2026-01-01T01:00:00Z", None, 1, 16, missing_actual=True, has_forecast=False),
            _row("2026-01-02T00:00:00Z", 40, 70, 15),
        ]
    )

    days = worst_days(frame, n=5)

    assert [row["date"] for row in days] == [date(2026, 1, 2), date(2026, 1, 1)]
    assert days[0]["mae"] == 30
    assert days[0]["bias"] == 30
    assert days[0]["mean_actual"] == 40
    assert days[1]["mae"] == 15
    assert days[1]["bias"] == -5
    assert days[1]["mean_actual"] == 90
    assert worst_days(frame, n=1)[0]["date"] == date(2026, 1, 2)
    assert worst_days(frame.iloc[0:0]) == []


def test_error_histogram_half_open_bins_and_closed_last_edge() -> None:
    """Width 500. 10 is in [0, 500). 500 and 900 share the closed last bin."""
    # floor(10 / 500) * 500 = 0, ceil(900 / 500) * 500 = 1000
    # [0, 500) -> 10
    # [500, 1000] -> 500 and 900
    frame = _frame(
        [
            _row("2026-01-15T00:00:00Z", 0, 10, 1),
            _row("2026-01-15T00:30:00Z", 0, 500, 1),
            _row("2026-01-15T01:00:00Z", 0, 900, 1),
            _row("2026-01-15T01:30:00Z", None, 5000, 1, missing_actual=True, has_forecast=False),
        ]
    )

    bins = error_histogram(frame, width=500)

    assert bins == [
        {"edge_low_mw": 0.0, "edge_high_mw": 500.0, "count": 1},
        {"edge_low_mw": 500.0, "edge_high_mw": 1000.0, "count": 2},
    ]
    assert error_histogram(frame.iloc[0:0]) == []
