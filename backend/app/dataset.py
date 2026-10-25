"""Load the parquet snapshot once. No Elexon calls."""

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from app.services.normalize import ACTUAL_COLUMNS, FORECAST_COLUMNS


@dataclass
class Dataset:
    """Frames kept on the app for the life of the process."""

    actuals: pd.DataFrame
    forecasts: pd.DataFrame
    manifest: dict[str, object] | None
    delivery_days: list[date]
    min_start_time: pd.Timestamp | None
    max_start_time: pd.Timestamp | None

    def covers(self, day: date) -> bool:
        """True when ``day`` sits inside the January 2026 span that was loaded."""
        if not self.delivery_days:
            return False
        return self.delivery_days[0] <= day <= self.delivery_days[-1]


def resolve_data_dir(data_dir: Path) -> Path:
    """Resolve a relative data directory from the backend directory."""
    if data_dir.is_absolute():
        return data_dir
    backend_dir = Path(__file__).resolve().parents[1]
    return (backend_dir / data_dir).resolve()


def load_dataset(data_dir: Path) -> Dataset:
    """Read actuals, forecasts, and the optional manifest. Missing files are empty."""
    actuals = _read_frame(data_dir / "actuals.parquet", ACTUAL_COLUMNS)
    forecasts = _read_frame(data_dir / "forecasts.parquet", FORECAST_COLUMNS)
    days = sorted(_january_days(actuals) | _january_days(forecasts))
    return Dataset(
        actuals=actuals,
        forecasts=forecasts,
        manifest=_read_manifest(data_dir / "_manifest.json"),
        delivery_days=days,
        min_start_time=_limit(actuals, forecasts, days, minimum=True),
        max_start_time=_limit(actuals, forecasts, days, minimum=False),
    )


def _read_frame(path: Path, columns: list[str]) -> pd.DataFrame:
    frame = pd.read_parquet(path) if path.is_file() else pd.DataFrame(columns=columns)
    for column in columns:
        if column not in frame:
            frame[column] = pd.Series(dtype="object")
    for column in ("start_time_utc", "publish_time_utc"):
        if column in frame:
            frame[column] = pd.to_datetime(frame[column], utc=True)
    return frame


def _read_manifest(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _january_days(frame: pd.DataFrame) -> set[date]:
    if frame.empty or "start_time_utc" not in frame:
        return set()
    starts = frame["start_time_utc"].dt.tz_convert("UTC")
    chosen = starts.loc[(starts.dt.year == 2026) & (starts.dt.month == 1)]
    return set(chosen.dt.date)


def _limit(
    actuals: pd.DataFrame,
    forecasts: pd.DataFrame,
    days: list[date],
    *,
    minimum: bool,
) -> pd.Timestamp | None:
    if not days:
        return None
    stamps: list[pd.Timestamp] = []
    for frame in (actuals, forecasts):
        if frame.empty:
            continue
        starts = frame["start_time_utc"].dt.tz_convert("UTC")
        dates = starts.dt.date
        covered = starts.loc[dates.isin(days)]
        if not covered.empty:
            stamps.append(covered.min() if minimum else covered.max())
    if not stamps:
        return None
    return min(stamps) if minimum else max(stamps)
