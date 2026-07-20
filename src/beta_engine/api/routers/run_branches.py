"""Read-only metadata endpoints for timelines inside product-level Runs."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from beta_engine.api.deps import get_simulation_api_service
from beta_engine.api.schemas import RunBranchListResponse, RunBranchResponse
from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import RunBranchRecord

router = APIRouter(prefix="/run-branches", tags=["run-branches"])


def _response(record: RunBranchRecord) -> RunBranchResponse:
    payload = record.__dict__.copy()
    payload["metadata_json"] = payload.pop("metadata")
    return RunBranchResponse.model_validate(payload)


@router.get("", response_model=RunBranchListResponse)
def list_run_branches(
    run_id: str | None = Query(None), service: SimulationApiService = Depends(get_simulation_api_service)
) -> RunBranchListResponse:
    if run_id is not None and service.repository.get_run_container(run_id=run_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"run container {run_id} was not found")
    return RunBranchListResponse(run_branches=[_response(record) for record in service.repository.list_run_branches(run_id=run_id)])


@router.get("/{branch_id}", response_model=RunBranchResponse)
def get_run_branch(branch_id: str, service: SimulationApiService = Depends(get_simulation_api_service)) -> RunBranchResponse:
    record = service.repository.get_run_branch(branch_id=branch_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"run branch {branch_id} was not found")
    return _response(record)
