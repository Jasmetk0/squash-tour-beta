"""Admin HTTP boundary for canonical World Tour Finals participant selection."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.application.finals_participant_selection import (
    WorldTourFinalsParticipantSelectionAuthorityService,
    WorldTourFinalsParticipantSelectionConfigurationCommand,
)
from beta_engine.domain.finals import (
    WorldTourFinalsParticipantSelectionConfiguration,
    WorldTourFinalsParticipantSelectionSnapshot,
)
from beta_engine.infrastructure.db.finals_participant_selection import (
    WorldTourFinalsParticipantSelectionConflict,
)


router = APIRouter(
    prefix="/admin/runs/{run_id}/branches/{branch_id}/finals-participants",
    tags=["admin-finals-participants"],
)


class WorldTourFinalsParticipantSelectionConfigurationRequest(BaseModel):
    direct_entry_event_ids: tuple[str, ...] = ()
    command_id: str = Field(min_length=1, max_length=128)


class WorldTourFinalsParticipantSelectionAuthorityResponse(BaseModel):
    run_id: str
    branch_id: str
    target_season_index: int
    configuration: WorldTourFinalsParticipantSelectionConfiguration | None
    snapshot: WorldTourFinalsParticipantSelectionSnapshot | None


def _service(
    runtime: ApiRuntime,
) -> WorldTourFinalsParticipantSelectionAuthorityService:
    return WorldTourFinalsParticipantSelectionAuthorityService(
        runtime.repository._session_factory
    )


@router.get(
    "/{target_season_index}",
    response_model=WorldTourFinalsParticipantSelectionAuthorityResponse,
)
def inspect_world_tour_finals_participant_selection(
    run_id: str,
    branch_id: str,
    target_season_index: int,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> WorldTourFinalsParticipantSelectionAuthorityResponse:
    try:
        configuration, snapshot = _service(runtime).inspect(
            run_id=run_id,
            branch_id=branch_id,
            target_season_index=target_season_index,
        )
        return WorldTourFinalsParticipantSelectionAuthorityResponse(
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
                "code": "finals_participant_selection_inspection_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post(
    "/{target_season_index}/configuration",
    status_code=201,
    response_model=WorldTourFinalsParticipantSelectionConfiguration,
)
def configure_world_tour_finals_participant_selection(
    run_id: str,
    branch_id: str,
    target_season_index: int,
    payload: WorldTourFinalsParticipantSelectionConfigurationRequest,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> WorldTourFinalsParticipantSelectionConfiguration:
    try:
        command = WorldTourFinalsParticipantSelectionConfigurationCommand(
            run_id=run_id,
            branch_id=branch_id,
            target_season_index=target_season_index,
            direct_entry_event_ids=payload.direct_entry_event_ids,
            command_id=payload.command_id,
        )
        return _service(runtime).create_configuration(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except WorldTourFinalsParticipantSelectionConflict as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "finals_participant_selection_configuration_conflict",
                "message": str(exc),
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "finals_participant_selection_configuration_invalid",
                "message": str(exc),
            },
        ) from exc


@router.post(
    "/{target_season_index}/snapshot",
    status_code=201,
    response_model=WorldTourFinalsParticipantSelectionSnapshot,
)
def build_world_tour_finals_participant_selection(
    run_id: str,
    branch_id: str,
    target_season_index: int,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> WorldTourFinalsParticipantSelectionSnapshot:
    try:
        return _service(runtime).build_snapshot(
            run_id=run_id,
            branch_id=branch_id,
            target_season_index=target_season_index,
        )
    except WorldTourFinalsParticipantSelectionConflict as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "finals_participant_selection_snapshot_conflict",
                "message": str(exc),
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "finals_participant_selection_snapshot_invalid",
                "message": str(exc),
            },
        ) from exc
