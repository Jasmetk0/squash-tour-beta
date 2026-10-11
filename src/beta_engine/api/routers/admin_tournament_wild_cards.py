"""Canonical Admin HTTP boundary for explicit WC/RWC review and commit."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.application.authoritative_wild_card_assignment import (
    AuthoritativeWildCardAssignmentCommitResult,
    AuthoritativeWildCardAssignmentPreview,
    AuthoritativeWildCardAssignmentService,
    AuthoritativeWildCardAssignmentState,
    AuthoritativeWildCardCommitCommand,
    AuthoritativeWildCardReviewRequest,
)
from beta_engine.infrastructure.db.tournament_wild_card_authority import (
    TournamentWildCardAuthorityConflict,
)


router = APIRouter(
    prefix="/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/wild-cards",
    tags=["admin-tournament-wild-cards"],
)


def _service(runtime: ApiRuntime) -> AuthoritativeWildCardAssignmentService:
    return AuthoritativeWildCardAssignmentService(
        runtime.repository._session_factory
    )


@router.get("", response_model=AuthoritativeWildCardAssignmentState)
def inspect_wild_card_state(
    run_id: str,
    branch_id: str,
    event_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> AuthoritativeWildCardAssignmentState:
    try:
        return _service(runtime).inspect(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "canonical_wc_state_conflict", "message": str(exc)},
        ) from exc


@router.post("/preview", response_model=AuthoritativeWildCardAssignmentPreview)
def preview_wild_card_assignment(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> AuthoritativeWildCardAssignmentPreview:
    try:
        request = AuthoritativeWildCardReviewRequest.model_validate_json(
            json.dumps(payload)
        )
        return _service(runtime).preview(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            request=request,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, ValueError, TournamentWildCardAuthorityConflict) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "canonical_wc_preview_conflict", "message": str(exc)},
        ) from exc


@router.post(
    "/commit",
    status_code=201,
    response_model=AuthoritativeWildCardAssignmentCommitResult,
)
def commit_wild_card_assignment(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> AuthoritativeWildCardAssignmentCommitResult:
    try:
        command = AuthoritativeWildCardCommitCommand.model_validate_json(
            json.dumps(payload)
        )
        return _service(runtime).commit(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            command=command,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, ValueError, TournamentWildCardAuthorityConflict) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "canonical_wc_commit_conflict", "message": str(exc)},
        ) from exc
