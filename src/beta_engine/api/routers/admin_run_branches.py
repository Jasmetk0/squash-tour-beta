"""Admin commands for materializing product Run Branch timelines."""

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import get_simulation_api_service
from beta_engine.api.schemas import (
    AdminForkRunBranchRequest, AdminForkRunBranchResponse,
    AdminSetOfficialRunBranchRequest, AdminSetOfficialRunBranchResponse,
)
from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import (
    BranchForkIdempotencyConflictError,
    BranchForkSourceStateMismatchError,
    BranchForkTargetExistsError,
    BranchForkValidationError,
    ForkRunBranchCommand,
    SetOfficialRunBranchCommand,
    OfficialBranchSelectionValidationError,
    OfficialBranchSelectionConflictError,
    OfficialBranchSelectionIdempotencyConflictError,
    OfficialBranchSelectionStateMismatchError,
)

router = APIRouter(prefix="/admin/runs", tags=["admin-runs"])


@router.post("/{product_run_id}/branches/fork", response_model=AdminForkRunBranchResponse)
def fork_run_branch(
    product_run_id: str,
    payload: AdminForkRunBranchRequest,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> AdminForkRunBranchResponse:
    """Create, or idempotently return, an established atomic Branch fork."""
    command = ForkRunBranchCommand(product_run_id=product_run_id, **payload.model_dump())
    try:
        result = service.fork_run_branch_atomically(command)
    except BranchForkTargetExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except BranchForkIdempotencyConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except BranchForkSourceStateMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except BranchForkValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return AdminForkRunBranchResponse.model_validate(result.__dict__)


@router.post("/{product_run_id}/branches/{target_branch_id}/make-official", response_model=AdminSetOfficialRunBranchResponse)
def make_official_run_branch(product_run_id: str, target_branch_id: str, payload: AdminSetOfficialRunBranchRequest, service: SimulationApiService = Depends(get_simulation_api_service)) -> AdminSetOfficialRunBranchResponse:
    """Atomically publish an existing Branch as the Product Run's official Branch."""
    command = SetOfficialRunBranchCommand(product_run_id=product_run_id, target_branch_id=target_branch_id, **payload.model_dump())
    try:
        result = service.set_official_run_branch_atomically(command)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except OfficialBranchSelectionIdempotencyConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except OfficialBranchSelectionStateMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except OfficialBranchSelectionConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except OfficialBranchSelectionValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return AdminSetOfficialRunBranchResponse.model_validate(result.__dict__)
