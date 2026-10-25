"""Turn raw Elexon dicts into UTC tables. No cutoff or metric logic."""

from typing import Any

import pandas as pd

ACTUAL_COLUMNS = ["start_time_utc", "actual_mw"]
FORECAST_COLUMNS = [
    "start_time_utc",
    "publish_time_utc",
    "forecast_mw",
    "horizon_hours",
]


class NormalizeError(ValueError):
    """A required field is missing or null."""


def normalize_actuals(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """One actual MW per start time. The last row for that start time wins."""
    if not rows:
        return _empty(ACTUAL_COLUMNS)
    frame = pd.DataFrame(rows)
    _require(frame, ["startTime", "generation"], "actuals")
    out = pd.DataFrame(
        {
            "start_time_utc": pd.to_datetime(frame["startTime"], utc=True, errors="coerce"),
            "actual_mw": pd.to_numeric(frame["generation"], errors="coerce"),
        }
    )
    _reject_nulls(out, ["start_time_utc", "actual_mw"], "actuals")
    out = out.drop_duplicates(keep="last")
    # Actuals have no publish time in the output, so the key is the start time alone.
    out = out.drop_duplicates(subset=["start_time_utc"], keep="last")
    return out.sort_values("start_time_utc").reset_index(drop=True)


def normalize_forecasts(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """One forecast MW per start and publish time, with horizon in hours."""
    if not rows:
        return _empty(FORECAST_COLUMNS)
    frame = pd.DataFrame(rows)
    _require(frame, ["startTime", "publishTime", "generation"], "forecasts")
    start = pd.to_datetime(frame["startTime"], utc=True, errors="coerce")
    publish = pd.to_datetime(frame["publishTime"], utc=True, errors="coerce")
    out = pd.DataFrame(
        {
            "start_time_utc": start,
            "publish_time_utc": publish,
            "forecast_mw": pd.to_numeric(frame["generation"], errors="coerce"),
            "horizon_hours": (start - publish).dt.total_seconds() / 3600,
        }
    )
    _reject_nulls(
        out,
        ["start_time_utc", "publish_time_utc", "forecast_mw", "horizon_hours"],
        "forecasts",
    )
    out = out.drop_duplicates(keep="last")
    out = out.drop_duplicates(subset=["start_time_utc", "publish_time_utc"], keep="last")
    return out.sort_values(["start_time_utc", "publish_time_utc"]).reset_index(drop=True)


def _empty(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _require(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        message = f"{label} is missing {', '.join(missing)}"
        raise NormalizeError(message)


def _reject_nulls(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    source = {
        "start_time_utc": "startTime",
        "publish_time_utc": "publishTime",
        "actual_mw": "generation",
        "forecast_mw": "generation",
        "horizon_hours": "horizon_hours",
    }
    for column in columns:
        nulls = int(frame[column].isna().sum())
        if nulls:
            name = source[column]
            message = f"{label}.{name} is null on {nulls} row(s)"
            raise NormalizeError(message)
