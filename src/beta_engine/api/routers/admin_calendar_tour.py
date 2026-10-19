"""Production Admin boundary for configured Run-calendar Tour execution."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from beta_engine.api.deps import ApiRuntime, get_run_working_draft_service, get_runtime
from beta_engine.application.calendar_tour_service import (
    CalendarTourCommand,
    CalendarTourCommit,
    CalendarTourService,
)
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.application.calendar_native_prospect_intake import inspect_native_prospect_intake

router = APIRouter(
    prefix="/admin/runs/{run_id}/branches/{branch_id}/calendar-tour",
    tags=["admin-calendar-tour"],
)


def conflict(exc):
    return HTTPException(
        status_code=409, detail={"code": "calendar_tour_conflict", "message": str(exc)}
    )


@router.get("")
def inspect(
    run_id: str, branch_id: str, runtime: Annotated[ApiRuntime, Depends(get_runtime)]
):
    try:
        return CalendarTourService(runtime.repository).inspect(
            run_id=run_id, branch_id=branch_id
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise conflict(exc) from exc


@router.get("/prospect-intake/preflight")
def native_prospect_intake_preflight(
    run_id: str, branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        return inspect_native_prospect_intake(
            runtime.repository, run_id=run_id, branch_id=branch_id,
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise conflict(exc) from exc


@router.get("/records")
def signed_career_records(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    as_of_season_index: int | None = Query(default=None, ge=0),
    from_season_index: int = Query(default=0, ge=0),
    country_code: str | None = Query(default=None),
    leaderboard_limit: int = Query(default=20, ge=1, le=100),
):
    try:
        return CalendarTourService(runtime.repository).records(
            run_id=run_id, branch_id=branch_id,
            as_of_season_index=as_of_season_index,
            from_season_index=from_season_index,
            country_code=country_code, leaderboard_limit=leaderboard_limit,
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise conflict(exc) from exc


@router.get("/seasons/{season_index}")
def season_summary(
    run_id: str,
    branch_id: str,
    season_index: int,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    compare_to: int | None = Query(default=None, ge=0),
):
    try:
        return CalendarTourService(runtime.repository).season_summary(
            run_id=run_id, branch_id=branch_id,
            season_index=season_index, compare_to=compare_to,
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise conflict(exc) from exc


@router.post("/preview")
def preview(
    run_id: str,
    branch_id: str,
    payload: CalendarTourCommand,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        return CalendarTourService(runtime.repository).preview(
            run_id=run_id, branch_id=branch_id, command=payload
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise conflict(exc) from exc


@router.post("/execute", status_code=201)
def execute(
    run_id: str,
    branch_id: str,
    payload: CalendarTourCommit,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        return CalendarTourService(runtime.repository).execute(
            run_id=run_id, branch_id=branch_id, request=payload
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise conflict(exc) from exc


class TourSaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_draft_version: int = Field(ge=1)
    expected_calendar_tour_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


@router.get("/players/{player_id}")
def player(
    run_id: str,
    branch_id: str,
    player_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        return CalendarTourService(runtime.repository).player(
            run_id=run_id, branch_id=branch_id, player_id=player_id
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise conflict(exc) from exc


@router.post("/save", status_code=201)
def save(
    run_id: str,
    branch_id: str,
    payload: TourSaveRequest,
    service: Annotated[RunWorkingDraftService, Depends(get_run_working_draft_service)],
):
    try:
        result = service.save_calendar_tour(
            run_id=run_id, branch_id=branch_id, **payload.model_dump()
        )
        # Save still captures and authenticates the complete immutable payload.
        # This command receipt needs its identity/hash, not another transfer of
        # every population snapshot and rally log. History/detail owns that read.
        revision = result.saved_revision
        return {
            "schema_version": "calendar_tour_save_receipt.v1",
            "run_id": result.run_id,
            "branch_id": result.branch_id,
            "viewer_branch_id": result.viewer_branch_id,
            "previous_viewer_branch_id": result.previous_viewer_branch_id,
            "saved_revision": {
                key: getattr(revision, key)
                for key in (
                    "revision_id",
                    "run_id",
                    "branch_id",
                    "sequence",
                    "parent_revision_id",
                    "kind",
                    "payload_schema_version",
                    "content_hash_algorithm",
                    "content_hash",
                    "created_at",
                    "change_summary",
                )
            },
            "working_draft": result.working_draft,
            "audit_event": result.audit_event,
        }
    except (KeyError, ValueError, TypeError) as exc:
        raise conflict(exc) from exc
