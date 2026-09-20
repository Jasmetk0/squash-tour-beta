"""Explicit preview/confirm API for the canonical atomic Week Transition."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from beta_engine.api.deps import ApiRuntime, get_runtime, get_season_point_awards_service
from beta_engine.application.authoritative_week_transition import AuthoritativeWeekTransitionCommand
from beta_engine.application.season_point_awards_service import SeasonPointAwardsService
from beta_engine.infrastructure.db.authoritative_week_transition import (
    AuthoritativeWeekTransitionRunner,
    derive_persisted_week_transition_command,
)

router = APIRouter(prefix="/admin/runs/{run_id}/branches/{branch_id}/week-transitions", tags=["admin-week-transitions"])


def _run(
    runtime,
    awards,
    run_id,
    branch_id,
    payload,
    *,
    preview,
    expected_ranking=None,
    expected_lifecycle=None,
    expected_sporting=None,
    expected_request=None,
):
    try:
        command = AuthoritativeWeekTransitionCommand.model_validate_json(json.dumps(payload))
        if (command.run_id, command.branch_id) != (run_id, branch_id):
            raise ValueError("Week Transition request scope mismatch")
        if not preview and command.fingerprint != expected_request:
            raise ValueError("Week Transition command changed since preview")
        runner = AuthoritativeWeekTransitionRunner(runtime.repository._session_factory, awards)
        result = runner.preview(command) if preview else runner.execute(
            command,
            expected_ranking_fingerprint=expected_ranking,
            expected_lifecycle_fingerprint=expected_lifecycle,
            expected_sporting_fingerprint=expected_sporting,
        )
        return {"request_fingerprint": command.fingerprint, "result": result}
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_week_transition", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "week_transition_conflict", "message": str(exc)}) from exc


class DerivedWeekTransitionPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    command_id: str = Field(min_length=1, max_length=128)


@router.post("/derived/preview")
def preview_derived_week_transition(
    run_id: str,
    branch_id: str,
    payload: DerivedWeekTransitionPreviewRequest,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    awards: Annotated[SeasonPointAwardsService, Depends(get_season_point_awards_service)],
):
    try:
        with runtime.repository._session_factory() as session:
            command = derive_persisted_week_transition_command(
                session,
                run_id=run_id,
                branch_id=branch_id,
                command_id=payload.command_id,
            )
        runner = AuthoritativeWeekTransitionRunner(
            runtime.repository._session_factory,
            awards,
        )
        result = runner.preview(command)
        return {
            "request_fingerprint": command.fingerprint,
            "command": command.model_dump(mode="json"),
            "result": result,
        }
    except (ValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "derived_week_transition_unavailable",
                "message": str(exc),
            },
        ) from exc


@router.post("/preview")
def preview_week_transition(run_id: str, branch_id: str, payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    awards: Annotated[SeasonPointAwardsService, Depends(get_season_point_awards_service)]):
    return _run(runtime, awards, run_id, branch_id, payload, preview=True)


@router.post("", status_code=201)
def confirm_week_transition(run_id: str, branch_id: str, payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    awards: Annotated[SeasonPointAwardsService, Depends(get_season_point_awards_service)],
    expected_ranking: Annotated[str, Header(alias="X-Week-Transition-Ranking-Fingerprint", pattern=r"^[0-9a-f]{64}$")],
    expected_lifecycle: Annotated[str, Header(alias="X-Week-Transition-Lifecycle-Fingerprint", pattern=r"^[0-9a-f]{64}$")],
    expected_sporting: Annotated[str, Header(alias="X-Week-Transition-Sporting-Fingerprint", pattern=r"^[0-9a-f]{64}$")],
    expected_request: Annotated[str, Header(alias="X-Week-Transition-Request-Fingerprint", pattern=r"^[0-9a-f]{64}$")]):
    return _run(
        runtime,
        awards,
        run_id,
        branch_id,
        payload,
        preview=False,
        expected_ranking=expected_ranking,
        expected_lifecycle=expected_lifecycle,
        expected_sporting=expected_sporting,
        expected_request=expected_request,
    )
