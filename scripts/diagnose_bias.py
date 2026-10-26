"""Shift the January decision forecast and recompute MAE and bias.

Uses pandas and the parquet snapshot only. It does not import the application
and it does not change any service.

    backend/.venv/bin/python scripts/diagnose_bias.py
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
JANUARY_START = date(2026, 1, 1)
JANUARY_END = date(2026, 1, 31)
SAMPLE_DAYS = (date(2026, 1, 5), date(2026, 1, 15), date(2026, 1, 28))
SHIFTS_MINUTES = (-60, -30, 0, 30, 60)
PAIRS_PER_DAY = 6


def main() -> None:
    """Print the shift table and six hourly pairs for three delivery days."""
    actuals, forecasts = _load_snapshot(DATA_DIR)
    decision = _january_decision(forecasts, actuals)
    print("shift_min  n    mae_mw    bias_mw")
    for minutes in SHIFTS_MINUTES:
        scored = _score(decision, actuals, minutes)
        print(
            f"{minutes:9d}  {int(scored['n']):3d}  {scored['mae']:8.2f}  {scored['bias']:8.2f}"
        )
    print()
    for delivery_day in SAMPLE_DAYS:
        print(f"{delivery_day.isoformat()}  utc_start  forecast_mw  actual_mw")
        pairs = _hourly_pairs(decision, delivery_day).head(PAIRS_PER_DAY)
        for row in pairs.itertuples(index=False):
            print(
                f"  {_iso_z(row.start_time_utc)}  {row.forecast_mw:11.0f}  {row.actual_mw:9.0f}"
            )
        print()


def _load_snapshot(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    actual_path = data_dir / "actuals.parquet"
    forecast_path = data_dir / "forecasts.parquet"
    if not actual_path.is_file() or not forecast_path.is_file():
        message = f"missing parquet snapshot in {data_dir}"
        raise SystemExit(message)
    actuals = pd.read_parquet(actual_path)
    forecasts = pd.read_parquet(forecast_path)
    for frame, columns in (
        (actuals, ("start_time_utc",)),
        (forecasts, ("start_time_utc", "publish_time_utc")),
    ):
        for column in columns:
            frame[column] = pd.to_datetime(frame[column], utc=True)
    return actuals, forecasts


def _january_decision(forecasts: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    """Decision forecast for every January delivery day, paired at shift 0."""
    day = JANUARY_START
    pieces: list[pd.DataFrame] = []
    while day <= JANUARY_END:
        pieces.append(_decision_forecast(forecasts, day))
        day += timedelta(days=1)
    selected = pd.concat(pieces, ignore_index=True)
    paired = selected.merge(
        actuals[["start_time_utc", "actual_mw"]],
        on="start_time_utc",
        how="left",
    )
    return paired.dropna(subset=["forecast_mw", "actual_mw"]).reset_index(drop=True)


def _score(decision: pd.DataFrame, actuals: pd.DataFrame, minutes: int) -> dict[str, float]:
    """MAE and bias after moving each forecast start by ``minutes``.

    Error stays forecast minus actual. A pair is kept only when an actual
    exists at the shifted time.
    """
    shifted = decision[["start_time_utc", "forecast_mw"]].copy()
    shifted["start_time_utc"] = shifted["start_time_utc"] + pd.Timedelta(minutes=minutes)
    paired = shifted.merge(
        actuals[["start_time_utc", "actual_mw"]],
        on="start_time_utc",
        how="inner",
    )
    error = paired["forecast_mw"] - paired["actual_mw"]
    return {
        "n": float(len(paired)),
        "mae": float(error.abs().mean()),
        "bias": float(error.mean()),
    }


def _hourly_pairs(decision: pd.DataFrame, delivery_day: date) -> pd.DataFrame:
    """Shift-0 pairs on one delivery day, in UTC start order."""
    local = decision["start_time_utc"].dt.tz_convert("Europe/London")
    day_rows = decision.loc[local.dt.date == delivery_day]
    return day_rows.sort_values("start_time_utc")


def _decision_forecast(forecasts: pd.DataFrame, delivery_day: date) -> pd.DataFrame:
    """One row per London half-hour. The chosen publish is the latest at or before 09:00."""
    cutoff = _cutoff_utc(delivery_day)
    grid = pd.DataFrame({"start_time_utc": _london_half_hours(delivery_day)})
    eligible = forecasts.loc[forecasts["publish_time_utc"] <= cutoff]
    if eligible.empty:
        chosen = forecasts.iloc[0:0]
    else:
        latest_index = eligible.groupby("start_time_utc")["publish_time_utc"].idxmax()
        chosen = eligible.loc[latest_index]
    return grid.merge(chosen, on="start_time_utc", how="left")


def _cutoff_utc(delivery_day: date) -> pd.Timestamp:
    """09:00 Europe/London on the day before delivery, as UTC."""
    previous = delivery_day - timedelta(days=1)
    local = pd.Timestamp(
        year=previous.year,
        month=previous.month,
        day=previous.day,
        hour=9,
        minute=0,
        tz="Europe/London",
    )
    return local.tz_convert("UTC")


def _london_half_hours(delivery_day: date) -> pd.DatetimeIndex:
    """Midnight through 23:30 Europe/London, expressed in UTC."""
    midnight = pd.Timestamp(
        year=delivery_day.year,
        month=delivery_day.month,
        day=delivery_day.day,
        tz="Europe/London",
    )
    return pd.date_range(midnight, periods=48, freq="30min").tz_convert("UTC")


def _iso_z(value: pd.Timestamp) -> str:
    return value.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    main()
