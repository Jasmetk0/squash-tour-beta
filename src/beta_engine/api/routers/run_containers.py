"""Read-only product-level Run container endpoints.

Legacy ``/runs`` remains the season-attempt API in R1.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import get_simulation_api_service
from beta_engine.api.schemas import RunContainerListResponse, RunContainerResponse
from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import RunContainerRecord

router = APIRouter(prefix="/run-containers", tags=["run-containers"])


def _response(record: RunContainerRecord) -> RunContainerResponse:
    payload = record.__dict__.copy()
    payload["metadata_json"] = payload.pop("metadata")
    return RunContainerResponse.model_validate(payload)


@router.get("", response_model=RunContainerListResponse)
def list_run_containers(service: SimulationApiService = Depends(get_simulation_api_service)) -> RunContainerListResponse:
    return RunContainerListResponse(run_containers=[_response(record) for record in service.repository.list_run_containers()])


@router.get("/{run_id:path}", response_model=RunContainerResponse)
def get_run_container(run_id: str, service: SimulationApiService = Depends(get_simulation_api_service)) -> RunContainerResponse:
    record = service.repository.get_run_container(run_id=run_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"run container {run_id} was not found")
    return _response(record)
