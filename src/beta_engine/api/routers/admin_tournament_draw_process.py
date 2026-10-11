"""Canonical Admin HTTP boundary for Draw process-window configuration."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.application.authoritative_tournament_draw_process import (
    CanonicalDrawProcessConfigureCommand,
    CanonicalTournamentDrawProcessService,
    CanonicalTournamentDrawProcessState,
)


router = APIRouter(
    prefix="/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/draw/process",
    tags=["admin-tournament-draw-process-authority"],
)


def _service(runtime: ApiRuntime) -> CanonicalTournamentDrawProcessService:
    return CanonicalTournamentDrawProcessService(runtime.repository._session_factory)


@router.get("", response_model=CanonicalTournamentDrawProcessState)
def inspect_draw_process(
    run_id: str,
    branch_id: str,
    event_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> CanonicalTournamentDrawProcessState:
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
            detail={"code": "canonical_draw_process_conflict", "message": str(exc)},
        ) from exc


@router.post("/configure", response_model=CanonicalTournamentDrawProcessState)
def configure_draw_process(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> CanonicalTournamentDrawProcessState:
    try:
        command = CanonicalDrawProcessConfigureCommand.model_validate(payload)
        if (command.run_id, command.branch_id, command.event_id) != (
            run_id,
            branch_id,
            event_id,
        ):
            raise ValueError("canonical Draw process request scope mismatch")
        return _service(runtime).configure(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "canonical_draw_process_conflict", "message": str(exc)},
        ) from exc
