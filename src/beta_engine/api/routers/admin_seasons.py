from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import get_initial_pool_season_bootstrap_service, get_season_calendar_service, get_season_readiness_service
from beta_engine.api.schemas import SeasonBootstrapRequest
from beta_engine.application.season_player_bootstrap_service import (
    InitialPoolSeasonBootstrapService,
    SeasonActivePlayersResponse,
    SeasonBootstrapResult,
)
from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.season_readiness_service import SeasonReadinessRequest, SeasonReadinessResult, SeasonReadinessService
from beta_engine.domain.tournaments import SeasonCalendarBuildRequest, SeasonCalendarBuildResult

router = APIRouter(prefix="/admin/seasons", tags=["admin-seasons"])


@router.post("/readiness", response_model=SeasonReadinessResult)
def inspect_season_readiness(
    payload: SeasonReadinessRequest,
    service: SeasonReadinessService = Depends(get_season_readiness_service),
) -> SeasonReadinessResult:
    return service.inspect_season(payload)


@router.get("/{season:path}/players", response_model=SeasonActivePlayersResponse)
def get_season_active_players(
    season: str,
    service: InitialPoolSeasonBootstrapService = Depends(get_initial_pool_season_bootstrap_service),
) -> SeasonActivePlayersResponse:
    return service.get_active_players(season=season)


@router.post("/{season:path}/bootstrap-from-initial-pool", response_model=SeasonBootstrapResult)
def bootstrap_season_from_initial_pool(
    season: str,
    payload: SeasonBootstrapRequest,
    service: InitialPoolSeasonBootstrapService = Depends(get_initial_pool_season_bootstrap_service),
) -> SeasonBootstrapResult:
    try:
        return service.bootstrap_from_initial_pool(
            season=season,
            source_season=payload.source_season,
            seed=payload.seed,
            dry_run=payload.dry_run,
            overwrite_existing=payload.overwrite_existing,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{season:path}/calendar", response_model=SeasonCalendarBuildResult)
def get_season_calendar(
    season: str,
    service: SeasonCalendarService = Depends(get_season_calendar_service),
) -> SeasonCalendarBuildResult:
    return service.get_calendar(season=season)


@router.post("/{season:path}/calendar/build", response_model=SeasonCalendarBuildResult)
def build_season_calendar(
    season: str,
    payload: SeasonCalendarBuildRequest,
    service: SeasonCalendarService = Depends(get_season_calendar_service),
) -> SeasonCalendarBuildResult:
    try:
        return service.build_calendar(season=season, request=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
