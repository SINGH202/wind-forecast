"""Accuracy route."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_dataset, get_settings
from app.api.schemas import MetricsResponse
from app.api.validation import require_cutoff, require_range
from app.config import Settings
from app.dataset import Dataset
from app.services.portal import build_metrics

router = APIRouter()


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(
    dataset: Annotated[Dataset, Depends(get_dataset)],
    settings: Annotated[Settings, Depends(get_settings)],
    start_day: Annotated[date, Query()],
    end_day: Annotated[date, Query()],
    cutoff: Annotated[str | None, Query()] = None,
) -> MetricsResponse:
    """Return accuracy for the 24 hourly slots per day, plus vintages by horizon."""
    require_range(start_day, end_day, dataset)
    chosen = require_cutoff(cutoff or settings.decision_cutoff_time)
    payload = build_metrics(dataset, start_day, end_day, chosen, settings.timezone)
    return MetricsResponse.model_validate(payload)
