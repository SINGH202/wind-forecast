"""Query checks. No dataframes."""

from datetime import date

from fastapi import HTTPException

from app.constants import CUTOFF_OPTIONS, MAX_HORIZON_HOURS, MIN_HORIZON_HOURS
from app.dataset import Dataset


def require_cutoff(cutoff: str) -> str:
    """Accept only the five London clock times."""
    if cutoff not in CUTOFF_OPTIONS:
        raise HTTPException(status_code=400, detail="cutoff is invalid")
    return cutoff


def require_delivery_day(day: date, dataset: Dataset) -> date:
    """January 2026, and inside the loaded coverage span."""
    if not _in_january(day) or not dataset.covers(day):
        raise HTTPException(status_code=400, detail="delivery_day is invalid")
    return day


def require_range(start: date, end: date, dataset: Dataset) -> None:
    """Both ends are inside coverage, and start is not after end."""
    if not _in_january(start) or not dataset.covers(start):
        raise HTTPException(status_code=400, detail="start_day is invalid")
    if not _in_january(end) or not dataset.covers(end):
        raise HTTPException(status_code=400, detail="end_day is invalid")
    if start > end:
        raise HTTPException(status_code=400, detail="start_day is invalid")
    return None


def require_horizon(horizon_hours: int) -> int:
    """Horizon hours are an integer from 0 through 48."""
    if horizon_hours < MIN_HORIZON_HOURS or horizon_hours > MAX_HORIZON_HOURS:
        raise HTTPException(status_code=400, detail="horizon_hours is invalid")
    return horizon_hours


def _in_january(day: date) -> bool:
    return day.year == 2026 and day.month == 1
