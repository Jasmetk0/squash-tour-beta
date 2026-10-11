"""Canonical Admin read model for Run-owned tournament preparation."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.application.canonical_tournament_preparation import (
    CanonicalTournamentPreparationService,
    CanonicalTournamentPreparationState,
)


router = APIRouter(
    prefix="/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/preparation",
    tags=["admin-tournament-preparation"],
)


@router.get("", response_model=CanonicalTournamentPreparationState)
def inspect_tournament_preparation(
    run_id: str,
    branch_id: str,
    event_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> CanonicalTournamentPreparationState:
    try:
        return CanonicalTournamentPreparationService(
            runtime.repository._session_factory
        ).inspect(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "canonical_tournament_preparation_conflict",
                "message": str(exc),
            },
        ) from exc
