"""Read-only inspection endpoints for mutable branch-head metadata."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from beta_engine.api.deps import get_simulation_api_service
from beta_engine.api.schemas import BranchStateListResponse, BranchStateResponse
from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import RunBranchStateRecord

router = APIRouter(prefix="/branch-states", tags=["branch-states"])


def _response(record: RunBranchStateRecord) -> BranchStateResponse:
    return BranchStateResponse.model_validate({**record.__dict__, "metadata_json": record.metadata})


@router.get("", response_model=BranchStateListResponse)
def list_branch_states(run_id: str | None = Query(None), service: SimulationApiService = Depends(get_simulation_api_service)) -> BranchStateListResponse:
    return BranchStateListResponse(branch_states=[_response(item) for item in service.repository.list_branch_states(run_id=run_id)])


@router.get("/{branch_id}", response_model=BranchStateResponse)
def get_branch_state(branch_id: str, service: SimulationApiService = Depends(get_simulation_api_service)) -> BranchStateResponse:
    record = service.repository.get_branch_state(branch_id=branch_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"branch state {branch_id} was not found")
    return _response(record)
