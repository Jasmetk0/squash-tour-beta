"""API route registration."""

from fastapi import APIRouter

from beta_engine.api.routers.admin_draws import router as admin_draws_router
from beta_engine.api.routers.admin_entries import router as admin_entries_router
from beta_engine.api.routers.admin_matches import router as admin_matches_router
from beta_engine.api.routers.admin_results import router as admin_results_router
from beta_engine.api.routers.admin_players import router as admin_players_router
from beta_engine.api.routers.admin_points import router as admin_points_router
from beta_engine.api.routers.admin_seasons import router as admin_seasons_router
from beta_engine.api.routers.config import router as config_router
from beta_engine.api.routers.countries import router as countries_router
from beta_engine.api.routers.health import router as health_router
from beta_engine.api.routers.history import router as history_router
from beta_engine.api.routers.point_breakdowns import router as point_breakdowns_router
from beta_engine.api.routers.runs import router as runs_router
from beta_engine.api.routers.rankings import router as rankings_router
from beta_engine.api.routers.ranking_snapshots import router as ranking_snapshots_router
from beta_engine.api.routers.sim import router as sim_router
from beta_engine.api.routers.tournament_templates import router as tournament_templates_router
from beta_engine.api.routers.world_talent_preview import router as world_talent_preview_router
from beta_engine.api.routers.world_manual_player_overrides import router as world_manual_player_overrides_router
from beta_engine.api.routers.world_package import router as world_package_router

router = APIRouter()
router.include_router(health_router)
router.include_router(config_router)
router.include_router(admin_players_router)
router.include_router(admin_points_router)
router.include_router(admin_entries_router)
router.include_router(admin_draws_router)
router.include_router(admin_matches_router)
router.include_router(admin_results_router)
router.include_router(admin_seasons_router)
router.include_router(countries_router)
router.include_router(tournament_templates_router)
router.include_router(runs_router)
router.include_router(rankings_router)
router.include_router(ranking_snapshots_router)
router.include_router(point_breakdowns_router)
router.include_router(sim_router)
router.include_router(history_router)
router.include_router(world_talent_preview_router)
router.include_router(world_manual_player_overrides_router)
router.include_router(world_package_router)
