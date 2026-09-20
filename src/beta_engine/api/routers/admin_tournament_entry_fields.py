"""Canonical Admin HTTP boundary for Run/Branch Tournament Entry Fields."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.application.authoritative_pre_draw_withdrawal import (
    CanonicalPreDrawWithdrawalCommand,
    CanonicalPreDrawWithdrawalResult,
    CanonicalPreDrawWithdrawalService,
    CanonicalTournamentEntryFieldState,
)
from beta_engine.domain.tournaments.entry_field import (
    TournamentEntryField,
    TournamentEntryFieldCapacity,
)
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
)


router = APIRouter(
    prefix="/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/entry-field",
    tags=["admin-tournament-entry-fields"],
)


def _service(runtime: ApiRuntime) -> CanonicalPreDrawWithdrawalService:
    return CanonicalPreDrawWithdrawalService(runtime.repository._session_factory)


@router.post(
    "/from-valid-submissions",
    status_code=201,
    response_model=TournamentEntryField,
)
def create_entry_field_from_valid_submissions(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentEntryField:
    try:
        capacity = TournamentEntryFieldCapacity.model_validate(payload["capacity"])
        command_id = payload["command_id"]
        with runtime.repository._session_factory.begin() as session:
            return TournamentEntryFieldStore(
                session
            ).stage_initial_from_persisted_submissions(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                capacity=capacity,
                command_id=command_id,
            )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "canonical_entry_field_creation_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get("", response_model=CanonicalTournamentEntryFieldState)
def inspect_entry_field(
    run_id: str,
    branch_id: str,
    event_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> CanonicalTournamentEntryFieldState:
    try:
        return _service(runtime).inspect(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "canonical_entry_field_conflict", "message": str(exc)},
        ) from exc


@router.post(
    "/pre-draw-withdrawal",
    response_model=CanonicalPreDrawWithdrawalResult,
)
def apply_pre_draw_withdrawal(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> CanonicalPreDrawWithdrawalResult:
    try:
        command = CanonicalPreDrawWithdrawalCommand.model_validate(payload)
        if (command.run_id, command.branch_id, command.event_id) != (
            run_id,
            branch_id,
            event_id,
        ):
            raise ValueError("canonical pre-draw withdrawal request scope mismatch")
        return _service(runtime).execute(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "canonical_pre_draw_withdrawal_conflict",
                "message": str(exc),
            },
        ) from exc
