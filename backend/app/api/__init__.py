"""HTTP routes. No forecast logic."""

from fastapi import APIRouter

from app.api.decision import router as decision_router
from app.api.health import router as health_router
from app.api.meta import router as meta_router
from app.api.metrics import router as metrics_router
from app.api.series import router as series_router

router = APIRouter()
router.include_router(health_router)
router.include_router(meta_router)
router.include_router(decision_router)
router.include_router(series_router)
router.include_router(metrics_router)
