"""Admin commands for materializing product Run Branch timelines."""

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import get_simulation_api_service
from beta_engine.api.schemas import AdminForkRunBranchRequest, AdminForkRunBranchResponse
from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import (
    BranchForkIdempotencyConflictError,
    BranchForkSourceStateMismatchError,
    BranchForkTargetExistsError,
    BranchForkValidationError,
    ForkRunBranchCommand,
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
