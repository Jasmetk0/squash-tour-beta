"""Explicit preview/confirm API for the canonical atomic Week Transition."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import ValidationError

from beta_engine.api.deps import ApiRuntime, get_runtime, get_season_point_awards_service
from beta_engine.application.authoritative_week_transition import AuthoritativeWeekTransitionCommand
from beta_engine.application.season_point_awards_service import SeasonPointAwardsService
from beta_engine.infrastructure.db.authoritative_week_transition import AuthoritativeWeekTransitionRunner

router = APIRouter(prefix="/admin/runs/{run_id}/branches/{branch_id}/week-transitions", tags=["admin-week-transitions"])


def _run(runtime, awards, run_id, branch_id, payload, *, preview, expected=None):
    try:
        command = AuthoritativeWeekTransitionCommand.model_validate_json(json.dumps(payload))
        if (command.run_id, command.branch_id) != (run_id, branch_id):
            raise ValueError("Week Transition request scope mismatch")
        runner = AuthoritativeWeekTransitionRunner(runtime.repository._session_factory, awards)
        result = runner.preview(command) if preview else runner.execute(
            command, expected_ranking_fingerprint=expected)
        return {"request_fingerprint": command.fingerprint, "result": result}
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_week_transition", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "week_transition_conflict", "message": str(exc)}) from exc


@router.post("/preview")
def preview_week_transition(run_id: str, branch_id: str, payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    awards: Annotated[SeasonPointAwardsService, Depends(get_season_point_awards_service)]):
    return _run(runtime, awards, run_id, branch_id, payload, preview=True)


@router.post("", status_code=201)
def confirm_week_transition(run_id: str, branch_id: str, payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    awards: Annotated[SeasonPointAwardsService, Depends(get_season_point_awards_service)],
    expected: Annotated[str | None, Header(alias="X-Week-Transition-Ranking-Fingerprint", pattern=r"^[0-9a-f]{64}$")] = None):
    return _run(runtime, awards, run_id, branch_id, payload, preview=False, expected=expected)
