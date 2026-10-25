"""Decision-view route."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_dataset, get_settings
from app.api.schemas import DecisionResponse
from app.api.validation import require_cutoff, require_delivery_day
from app.config import Settings
from app.dataset import Dataset
from app.services.portal import build_decision

router = APIRouter()


@router.get("/decision", response_model=DecisionResponse)
def get_decision(
    dataset: Annotated[Dataset, Depends(get_dataset)],
    settings: Annotated[Settings, Depends(get_settings)],
    delivery_day: Annotated[date, Query()],
    cutoff: Annotated[str | None, Query()] = None,
) -> DecisionResponse:
    """Return 48 half-hours for one delivery day at the decision cutoff."""
    chosen = require_cutoff(cutoff or settings.decision_cutoff_time)
    require_delivery_day(delivery_day, dataset)
    payload = build_decision(dataset, delivery_day, chosen, settings.timezone)
    return DecisionResponse.model_validate(payload)
