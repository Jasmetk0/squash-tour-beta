"""Admin HTTP boundary for canonical World Tour Finals Race authority."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.application.finals_race_authority import (
    WorldTourFinalsRaceAuthorityService,
    WorldTourFinalsRaceConfigurationCommand,
)
from beta_engine.domain.finals import (
    WorldTourFinalsRaceConfiguration,
    WorldTourFinalsRaceSnapshot,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.finals_race_authority import (
    WorldTourFinalsRaceAuthorityConflict,
)


router = APIRouter(
    prefix="/admin/runs/{run_id}/branches/{branch_id}/finals-race",
    tags=["admin-finals-race"],
)


class WorldTourFinalsRaceConfigurationRequest(BaseModel):
    finals_event_id: str = Field(min_length=1)
    best_n: int = Field(ge=1)
    eligible_categories: tuple[str, ...]
    cutoff_week: RankingWeek
    command_id: str = Field(min_length=1, max_length=128)


class WorldTourFinalsRaceAuthorityResponse(BaseModel):
    run_id: str
    branch_id: str
    target_season_index: int
    configuration: WorldTourFinalsRaceConfiguration | None
    snapshot: WorldTourFinalsRaceSnapshot | None


def _service(runtime: ApiRuntime) -> WorldTourFinalsRaceAuthorityService:
    return WorldTourFinalsRaceAuthorityService(runtime.repository._session_factory)


@router.get(
    "/{target_season_index}",
    response_model=WorldTourFinalsRaceAuthorityResponse,
)
def inspect_world_tour_finals_race_authority(
    run_id: str,
    branch_id: str,
    target_season_index: int,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> WorldTourFinalsRaceAuthorityResponse:
    try:
        configuration, snapshot = _service(runtime).inspect(
            run_id=run_id,
            branch_id=branch_id,
            target_season_index=target_season_index,
        )
        return WorldTourFinalsRaceAuthorityResponse(
            run_id=run_id,
            branch_id=branch_id,
            target_season_index=target_season_index,
            configuration=configuration,
            snapshot=snapshot,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "finals_race_inspection_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post(
    "/{target_season_index}/configuration",
    status_code=201,
    response_model=WorldTourFinalsRaceConfiguration,
)
def configure_world_tour_finals_race(
    run_id: str,
    branch_id: str,
    target_season_index: int,
    payload: WorldTourFinalsRaceConfigurationRequest,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> WorldTourFinalsRaceConfiguration:
    try:
        command = WorldTourFinalsRaceConfigurationCommand(
            run_id=run_id,
            branch_id=branch_id,
            target_season_index=target_season_index,
            finals_event_id=payload.finals_event_id,
            best_n=payload.best_n,
            eligible_categories=payload.eligible_categories,
            cutoff_week=payload.cutoff_week,
            command_id=payload.command_id,
        )
        return _service(runtime).create_configuration(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except WorldTourFinalsRaceAuthorityConflict as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "finals_race_configuration_conflict",
                "message": str(exc),
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "finals_race_configuration_invalid",
                "message": str(exc),
            },
        ) from exc


@router.post(
    "/{target_season_index}/snapshot",
    status_code=201,
    response_model=WorldTourFinalsRaceSnapshot,
)
def build_world_tour_finals_race_snapshot(
    run_id: str,
    branch_id: str,
    target_season_index: int,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> WorldTourFinalsRaceSnapshot:
    try:
        return _service(runtime).build_snapshot(
            run_id=run_id,
            branch_id=branch_id,
            target_season_index=target_season_index,
        )
    except WorldTourFinalsRaceAuthorityConflict as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "finals_race_snapshot_conflict",
                "message": str(exc),
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "finals_race_snapshot_invalid",
                "message": str(exc),
            },
        ) from exc
