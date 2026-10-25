"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router
from app.config import Settings
from app.dataset import load_dataset, resolve_data_dir


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app. The parquet snapshot is read here, not on each request."""
    current = settings if settings is not None else Settings()
    app = FastAPI(title="Wind forecast API")
    app.state.settings = current
    app.state.dataset = load_dataset(resolve_data_dir(current.data_dir))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=current.allowed_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
