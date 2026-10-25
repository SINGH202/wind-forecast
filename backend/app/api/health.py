"""Liveness route."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Liveness payload."""

    status: Literal["ok"]


@router.get("/health")
def get_health() -> HealthResponse:
    """Report that the process is up."""
    return HealthResponse(status="ok")
