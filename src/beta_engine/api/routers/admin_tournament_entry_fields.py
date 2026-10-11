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


@router.post("/from-valid-submissions/preview")
def preview_reviewed_entry_field_from_valid_submissions(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> dict:
    """Read-only, complete player cut with exact source fingerprint for Admin review."""
    try:
        capacity = TournamentEntryFieldCapacity.model_validate(payload["capacity"])
        with runtime.repository._session_factory() as session:
            field = TournamentEntryFieldStore(
                session
            ).preview_initial_from_persisted_submissions(
                run_id=run_id, branch_id=branch_id, event_id=event_id,
                capacity=capacity,
            )
        return {
            "preview_only": True,
            "run_id": run_id,
            "branch_id": branch_id,
            "event_id": event_id,
            "field_fingerprint": field.fingerprint,
            "field": field.model_dump(mode="json"),
        }
    except (KeyError, TypeError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "reviewed_entry_field_preview_conflict", "message": str(exc)},
        ) from exc


@router.post(
    "/from-valid-submissions/reviewed",
    status_code=201,
    response_model=TournamentEntryField,
)
def commit_reviewed_entry_field_from_valid_submissions(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentEntryField:
    """Replay Preview and atomically refuse a changed Ranking/Submission field cut."""
    try:
        capacity = TournamentEntryFieldCapacity.model_validate(payload["capacity"])
        expected = payload["expected_field_fingerprint"]
        if not isinstance(expected, str) or len(expected) != 64 or any(
            char not in "0123456789abcdef" for char in expected
        ):
            raise ValueError("expected_field_fingerprint must be SHA-256")
        command_id = payload["command_id"]
        with runtime.repository._session_factory.begin() as session:
            return TournamentEntryFieldStore(
                session
            ).stage_reviewed_initial_from_persisted_submissions(
                run_id=run_id, branch_id=branch_id, event_id=event_id,
                capacity=capacity, command_id=command_id,
                expected_field_fingerprint=expected,
            )
    except (KeyError, TypeError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "reviewed_entry_field_commit_conflict", "message": str(exc)},
        ) from exc


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


@router.post(
    "/from-finals-participant-selection",
    status_code=201,
    response_model=TournamentEntryField,
)
def create_entry_field_from_finals_participant_selection(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentEntryField:
    try:
        target_season_index = int(payload["target_season_index"])
        command_id = payload["command_id"]
        with runtime.repository._session_factory.begin() as session:
            return TournamentEntryFieldStore(
                session
            ).stage_initial_from_finals_participant_selection(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                target_season_index=target_season_index,
                command_id=command_id,
            )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "canonical_finals_entry_field_creation_conflict",
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
