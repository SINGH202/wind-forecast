"""Horizon-view route."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_dataset, get_settings
from app.api.schemas import SeriesResponse
from app.api.validation import require_horizon, require_range
from app.config import Settings
from app.dataset import Dataset
from app.services.portal import build_series

router = APIRouter()


@router.get("/series", response_model=SeriesResponse)
def get_series(
    dataset: Annotated[Dataset, Depends(get_dataset)],
    settings: Annotated[Settings, Depends(get_settings)],
    start_day: Annotated[date, Query()],
    end_day: Annotated[date, Query()],
    horizon_hours: Annotated[int, Query()] = 0,
) -> SeriesResponse:
    """Return actuals and the latest forecast at or beyond the horizon."""
    require_range(start_day, end_day, dataset)
    require_horizon(horizon_hours)
    payload = build_series(dataset, start_day, end_day, horizon_hours, settings.timezone)
    return SeriesResponse.model_validate(payload)
