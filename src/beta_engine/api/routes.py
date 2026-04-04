"""API route registration."""

from fastapi import APIRouter

from beta_engine.api.routers.config import router as config_router
from beta_engine.api.routers.countries import router as countries_router
from beta_engine.api.routers.health import router as health_router
from beta_engine.api.routers.history import router as history_router
from beta_engine.api.routers.runs import router as runs_router
from beta_engine.api.routers.sim import router as sim_router
from beta_engine.api.routers.world_talent_preview import router as world_talent_preview_router
from beta_engine.api.routers.world_manual_player_overrides import router as world_manual_player_overrides_router

router = APIRouter()
router.include_router(health_router)
router.include_router(config_router)
router.include_router(countries_router)
router.include_router(runs_router)
router.include_router(sim_router)
router.include_router(history_router)
router.include_router(world_talent_preview_router)
router.include_router(world_manual_player_overrides_router)
