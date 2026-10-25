"""Coverage route."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_dataset, get_settings
from app.api.schemas import MetaResponse
from app.config import Settings
from app.dataset import Dataset
from app.services.portal import build_meta

router = APIRouter()


@router.get("/meta", response_model=MetaResponse)
def get_meta(
    dataset: Annotated[Dataset, Depends(get_dataset)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MetaResponse:
    """Return snapshot coverage, the default cutoff, and the product assumptions."""
    return MetaResponse.model_validate(build_meta(dataset, settings))
