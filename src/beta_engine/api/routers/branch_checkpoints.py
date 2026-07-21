"""Capture-only immutable branch checkpoint inspection endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from beta_engine.api.deps import get_simulation_api_service
from beta_engine.api.schemas import (
    BranchCheckpointListResponse,
    BranchCheckpointResponse,
    CaptureCurrentBranchCheckpointRequest,
    CaptureCompletedEventBranchCheckpointRequest,
    CaptureCompletedWeekBranchCheckpointRequest,
    CaptureInitialBranchCheckpointRequest,
    CaptureAdminActionBranchCheckpointRequest,
)
from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import BranchCheckpointRecord

router = APIRouter(prefix="/branch-checkpoints", tags=["branch-checkpoints"])


def _response(record: BranchCheckpointRecord) -> BranchCheckpointResponse:
    return BranchCheckpointResponse.model_validate(record.__dict__)


@router.get("", response_model=BranchCheckpointListResponse)
def list_branch_checkpoints(
    branch_id: str | None = Query(None),
    run_id: str | None = Query(None),
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> BranchCheckpointListResponse:
    return BranchCheckpointListResponse(
        branch_checkpoints=[
            _response(item)
            for item in service.repository.list_branch_checkpoints(branch_id=branch_id, run_id=run_id)
        ]
    )


@router.get("/{checkpoint_id}", response_model=BranchCheckpointResponse)
def get_branch_checkpoint(
    checkpoint_id: str,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> BranchCheckpointResponse:
    record = service.repository.get_branch_checkpoint(checkpoint_id=checkpoint_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"branch checkpoint {checkpoint_id} was not found",
        )
    return _response(record)


@router.post("/capture-initial", response_model=BranchCheckpointResponse)
def capture_initial(
    payload: CaptureInitialBranchCheckpointRequest,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> BranchCheckpointResponse:
    try:
        record = service.repository.capture_initial_checkpoint_for_legacy_simulation_run(
            simulation_run_id=payload.simulation_run_id,
            command_id=payload.command_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _response(record)


@router.post("/capture-current", response_model=BranchCheckpointResponse)
def capture_current(
    payload: CaptureCurrentBranchCheckpointRequest,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> BranchCheckpointResponse:
    try:
        record = service.repository.capture_current_checkpoint_for_legacy_simulation_run(
            simulation_run_id=payload.simulation_run_id,
            command_id=payload.command_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _response(record)


@router.post("/capture-completed-event", response_model=BranchCheckpointResponse)
def capture_completed_event(
    payload: CaptureCompletedEventBranchCheckpointRequest,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> BranchCheckpointResponse:
    try:
        record = service.repository.capture_completed_event_checkpoint_for_legacy_simulation_run(
            simulation_run_id=payload.simulation_run_id,
            event_id=payload.event_id,
            event_sequence=payload.event_sequence,
            command_id=payload.command_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _response(record)


@router.post("/capture-completed-week", response_model=BranchCheckpointResponse)
def capture_completed_week(
    payload: CaptureCompletedWeekBranchCheckpointRequest,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> BranchCheckpointResponse:
    try:
        record = service.repository.capture_completed_week_checkpoint_for_legacy_simulation_run(
            simulation_run_id=payload.simulation_run_id, week=payload.week, command_id=payload.command_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _response(record)


@router.post("/capture-admin-action", response_model=BranchCheckpointResponse)
def capture_admin_action(
    payload: CaptureAdminActionBranchCheckpointRequest,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> BranchCheckpointResponse:
    try:
        record = service.repository.capture_admin_action_checkpoint_for_legacy_simulation_run(
            simulation_run_id=payload.simulation_run_id, action_id=payload.action_id,
            action_sequence=payload.action_sequence, command_id=payload.command_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _response(record)
