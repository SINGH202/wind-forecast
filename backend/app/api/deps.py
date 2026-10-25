"""Request dependencies. The snapshot is the object stored at startup."""

from fastapi import Request

from app.config import Settings
from app.dataset import Dataset


def get_settings(request: Request) -> Settings:
    """Settings captured when the app was created."""
    return request.app.state.settings


def get_dataset(request: Request) -> Dataset:
    """The parquet snapshot loaded once in ``create_app``."""
    return request.app.state.dataset
