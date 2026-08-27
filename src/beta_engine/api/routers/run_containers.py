"""Canonical product-level Run container endpoints.

Legacy ``/runs`` remains the season-attempt API in R1.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import (
    get_run_branch_creation_service,
    get_run_container_creation_service,
    get_simulation_api_service,
)
from beta_engine.api.schemas import (
    CreateRunBranchRequest,
    CreateRunContainerRequest,
    RunBranchResponse,
    RunContainerListResponse,
    RunContainerResponse,
)
from beta_engine.application.api_services import SimulationApiService
from beta_engine.application.run_branch_creation_service import (
    RunBranchCreationService,
)
from beta_engine.application.run_container_creation_service import (
    RunContainerCreationService,
)
from beta_engine.domain.run_containers import RunDisplayNameValidationError
from beta_engine.domain.run_branches import BranchDisplayNameValidationError
from beta_engine.infrastructure.db import (
    BranchCreationIdentityConflictError,
    BranchDisplayNameConflictError,
    RunBranchRecord,
    RunContainerRecord,
    RunDisplayNameConflictError,
    RunIdentityConflictError,
    SavedRevisionBranchForkConflictError,
    SavedRevisionBranchForkNotFoundError,
)

router = APIRouter(prefix="/run-containers", tags=["run-containers"])


def _response(record: RunContainerRecord) -> RunContainerResponse:
    payload = record.__dict__.copy()
    payload["metadata_json"] = payload.pop("metadata")
    payload["viewer_branch_id"] = record.viewer_branch_id
    return RunContainerResponse.model_validate(payload)


def _branch_response(record: RunBranchRecord) -> RunBranchResponse:
    payload = record.__dict__.copy()
    payload["metadata_json"] = payload.pop("metadata")
    payload["is_viewer_branch"] = record.is_viewer_branch
    return RunBranchResponse.model_validate(payload)


@router.post(
    "", response_model=RunContainerResponse, status_code=status.HTTP_201_CREATED
)
def create_run_container(
    payload: CreateRunContainerRequest,
    service: RunContainerCreationService = Depends(get_run_container_creation_service),
) -> RunContainerResponse:
    try:
        return _response(service.create_empty_run(display_name=payload.display_name))
    except RunDisplayNameConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "run_display_name_conflict", "message": str(exc)},
        ) from exc
    except RunIdentityConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "run_identity_conflict", "message": str(exc)},
        ) from exc
    except RunDisplayNameValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get("", response_model=RunContainerListResponse)
def list_run_containers(
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> RunContainerListResponse:
    return RunContainerListResponse(
        run_containers=[
            _response(record) for record in service.repository.list_run_containers()
        ]
    )


@router.post(
    "/{run_id}/branches",
    response_model=RunBranchResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_run_branch(
    run_id: str,
    payload: CreateRunBranchRequest,
    service: RunBranchCreationService = Depends(get_run_branch_creation_service),
) -> RunBranchResponse:
    try:
        branch = service.create_from_saved_revision(
            run_id=run_id,
            source_branch_id=payload.source_branch_id,
            source_saved_revision_id=payload.source_saved_revision_id,
            display_name=payload.display_name,
        )
    except SavedRevisionBranchForkNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "saved_revision_branch_source_not_found", "message": str(exc)},
        ) from exc
    except BranchDisplayNameConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "branch_display_name_conflict", "message": str(exc)},
        ) from exc
    except BranchCreationIdentityConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "branch_identity_conflict", "message": str(exc)},
        ) from exc
    except SavedRevisionBranchForkConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "saved_revision_branch_conflict", "message": str(exc)},
        ) from exc
    except BranchDisplayNameValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return _branch_response(branch)


@router.get("/{run_id:path}", response_model=RunContainerResponse)
def get_run_container(
    run_id: str,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> RunContainerResponse:
    record = service.repository.get_run_container(run_id=run_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"run container {run_id} was not found",
        )
    return _response(record)
