from __future__ import annotations

from fastapi import APIRouter, Depends

from beta_engine.api.deps import get_season_week_simulation_preflight_service
from beta_engine.application.season_week_simulation_preflight_service import (
    SimulateSeasonWeekPreflightApiRequest,
    SimulateSeasonWeekPreflightRequest,
    SimulateSeasonWeekPreflightResult,
    SeasonWeekSimulationPreflightService,
)

router = APIRouter(prefix="/admin/weeks", tags=["admin-weeks"])


@router.post("/preflight", response_model=SimulateSeasonWeekPreflightResult)
def preflight_season_week(
    payload: SimulateSeasonWeekPreflightApiRequest,
    service: SeasonWeekSimulationPreflightService = Depends(get_season_week_simulation_preflight_service),
) -> SimulateSeasonWeekPreflightResult:
    request = SimulateSeasonWeekPreflightRequest(**payload.model_dump(exclude={"season", "season_week"}))
    return service.preflight_week(season=payload.season, season_week=payload.season_week, request=request)
