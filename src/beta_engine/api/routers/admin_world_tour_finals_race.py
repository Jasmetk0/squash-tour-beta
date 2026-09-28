"""Admin API for canonical World Tour Finals Race snapshots."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.application.world_tour_finals_race_service import (
    WorldTourFinalsRaceService,
)
from beta_engine.domain.finals.race import WorldTourFinalsRaceSnapshot
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.world_tour_finals_race import (
    WorldTourFinalsRaceConflict,
)


router = APIRouter(
    prefix=(
        "/admin/runs/{run_id}/branches/{branch_id}"
        "/world-tour-finals-race/{season_index}"
    ),
    tags=["admin-world-tour-finals-race"],
)


class CreateWorldTourFinalsRaceRequest(BaseModel):
    command_id: str = Field(min_length=1, max_length=128)
    cutoff_week: RankingWeek
    best_result_count: int = Field(ge=1)
    eligible_event_ids: tuple[str, ...] = Field(min_length=1)


@router.get("", response_model=WorldTourFinalsRaceSnapshot)
def get_world_tour_finals_race(
    run_id: str,
    branch_id: str,
    season_index: int,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> WorldTourFinalsRaceSnapshot:
    try:
        snapshot = WorldTourFinalsRaceService(
            runtime.repository._session_factory
        ).get(
            run_id=run_id,
            branch_id=branch_id,
            season_index=season_index,
        )
        if snapshot is None:
            raise KeyError("World Tour Finals Race snapshot does not exist")
        return snapshot
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "world_tour_finals_race_unavailable",
                "message": str(exc),
            },
        ) from exc


@router.post("", status_code=201, response_model=WorldTourFinalsRaceSnapshot)
def create_world_tour_finals_race(
    run_id: str,
    branch_id: str,
    season_index: int,
    payload: CreateWorldTourFinalsRaceRequest,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> WorldTourFinalsRaceSnapshot:
    try:
        return WorldTourFinalsRaceService(
            runtime.repository._session_factory
        ).create(
            run_id=run_id,
            branch_id=branch_id,
            season_index=season_index,
            cutoff_week=payload.cutoff_week,
            best_result_count=payload.best_result_count,
            eligible_event_ids=payload.eligible_event_ids,
            command_id=payload.command_id,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except WorldTourFinalsRaceConflict as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "world_tour_finals_race_conflict",
                "message": str(exc),
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "world_tour_finals_race_unavailable",
                "message": str(exc),
            },
        ) from exc
