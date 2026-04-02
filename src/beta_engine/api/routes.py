"""API route registration."""

from fastapi import APIRouter

from beta_engine.api.routers.config import router as config_router
from beta_engine.api.routers.health import router as health_router
from beta_engine.api.routers.history import router as history_router
from beta_engine.api.routers.runs import router as runs_router
from beta_engine.api.routers.sim import router as sim_router

router = APIRouter()
router.include_router(health_router)
router.include_router(config_router)
router.include_router(runs_router)
router.include_router(sim_router)
router.include_router(history_router)
