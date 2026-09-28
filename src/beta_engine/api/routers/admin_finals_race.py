"""Admin HTTP boundary for canonical World Tour Finals Race authority."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.application.finals_race_authority import (
    FinalsRaceAuthorityService,
    FinalsRaceConfigurationCommand,
)
from beta_engine.domain.finals import FinalsRaceConfiguration, FinalsRaceSnapshot
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.finals_race_authority import (
    FinalsRaceAuthorityConflict,
)


router = APIRouter(
    prefix="/admin/runs/{run_id}/branches/{branch_id}/finals-race",
    tags=["admin-finals-race"],
)


class FinalsRaceConfigurationRequest(BaseModel):
    best_n_results: int = Field(ge=1)
    eligible_categories: tuple[str, ...]
    cutoff_ranking_week: RankingWeek
    command_id: str = Field(min_length=1, max_length=128)


class FinalsRaceAuthorityResponse(BaseModel):
    run_id: str
    branch_id: str
    season_index: int
    configuration: FinalsRaceConfiguration | None
    snapshot: FinalsRaceSnapshot | None


def _service(runtime: ApiRuntime) -> FinalsRaceAuthorityService:
    return FinalsRaceAuthorityService(runtime.repository._session_factory)


@router.get("/{season_index}", response_model=FinalsRaceAuthorityResponse)
def inspect_finals_race_authority(
    run_id: str,
    branch_id: str,
    season_index: int,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> FinalsRaceAuthorityResponse:
    try:
        configuration, snapshot = _service(runtime).inspect(
            run_id=run_id,
            branch_id=branch_id,
            season_index=season_index,
        )
        return FinalsRaceAuthorityResponse(
            run_id=run_id,
            branch_id=branch_id,
            season_index=season_index,
            configuration=configuration,
            snapshot=snapshot,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "finals_race_inspection_conflict", "message": str(exc)},
        ) from exc


@router.post(
    "/{season_index}/configuration",
    status_code=201,
    response_model=FinalsRaceConfiguration,
)
def configure_finals_race(
    run_id: str,
    branch_id: str,
    season_index: int,
    payload: FinalsRaceConfigurationRequest,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> FinalsRaceConfiguration:
    try:
        command = FinalsRaceConfigurationCommand(
            run_id=run_id,
            branch_id=branch_id,
            season_index=season_index,
            best_n_results=payload.best_n_results,
            eligible_categories=payload.eligible_categories,
            cutoff_ranking_week=payload.cutoff_ranking_week,
            command_id=payload.command_id,
        )
        return _service(runtime).create_configuration(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FinalsRaceAuthorityConflict as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "finals_race_configuration_conflict", "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "finals_race_configuration_invalid", "message": str(exc)},
        ) from exc


@router.post(
    "/{season_index}/snapshot",
    status_code=201,
    response_model=FinalsRaceSnapshot,
)
def build_finals_race_snapshot(
    run_id: str,
    branch_id: str,
    season_index: int,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> FinalsRaceSnapshot:
    try:
        return _service(runtime).build_snapshot(
            run_id=run_id,
            branch_id=branch_id,
            season_index=season_index,
        )
    except FinalsRaceAuthorityConflict as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "finals_race_snapshot_conflict", "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "finals_race_snapshot_invalid", "message": str(exc)},
        ) from exc
