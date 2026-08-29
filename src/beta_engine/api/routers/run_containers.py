"""Canonical product-level Run container endpoints.

Legacy ``/runs`` remains the season-attempt API in R1.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import (
    get_run_branch_creation_service,
    get_run_container_creation_service,
    get_run_saved_revision_history_service,
    get_run_working_draft_service,
    get_simulation_api_service,
)
from beta_engine.api.schemas import (
    CreateRunBranchRequest,
    CreateRunContainerRequest,
    RunBranchResponse,
    RunContainerListResponse,
    RunContainerResponse,
    SavedRevisionHistoryDetailResponse,
    SavedRevisionHistoryEntryResponse,
    SavedRevisionHistoryListResponse,
    SavedRevisionResponse,
    SaveWorkingDraftRequest,
    SaveWorkingDraftResponse,
    StageViewerBranchRequest,
    ViewerBranchWorkingDraftResponse,
)
from beta_engine.application.api_services import SimulationApiService
from beta_engine.application.run_branch_creation_service import (
    RunBranchCreationService,
)
from beta_engine.application.run_container_creation_service import (
    RunContainerCreationService,
)
from beta_engine.application.run_saved_revision_history_service import (
    RunSavedRevisionHistoryService,
)
from beta_engine.application.run_working_draft_service import (
    RunWorkingDraftService,
)
from beta_engine.domain.run_branches import BranchDisplayNameValidationError
from beta_engine.domain.run_containers import RunDisplayNameValidationError
from beta_engine.infrastructure.db import (
    BranchCreationIdentityConflictError,
    BranchDisplayNameConflictError,
    BranchSavedRevisionHistoryRecord,
    BranchSavedRevisionRecord,
    RunBranchRecord,
    RunContainerRecord,
    RunDisplayNameConflictError,
    RunIdentityConflictError,
    SavedRevisionBranchForkConflictError,
    SavedRevisionBranchForkNotFoundError,
    SavedRevisionHistoryConflictError,
    SavedRevisionHistoryNotFoundError,
    ViewerBranchSaveResult,
    ViewerBranchWorkingDraftRecord,
    WorkingDraftConflictError,
    WorkingDraftIdentityConflictError,
    WorkingDraftNotFoundError,
    WorkingDraftVersionConflictError,
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


def _working_draft_response(
    record: ViewerBranchWorkingDraftRecord,
) -> ViewerBranchWorkingDraftResponse:
    return ViewerBranchWorkingDraftResponse(
        run_id=record.run_id,
        branch_id=record.branch_id,
        draft_id=record.draft_id,
        base_saved_revision_id=record.base_saved_revision_id,
        saved_viewer_branch_id=record.saved_viewer_branch_id,
        proposed_viewer_branch_id=record.proposed_viewer_branch_id,
        current_viewer_branch_id=record.current_viewer_branch_id,
        status=record.status,
        change_count=record.change_count,
        draft_version=record.draft_version,
        can_save=record.can_save,
    )


def _save_response(record: ViewerBranchSaveResult) -> SaveWorkingDraftResponse:
    revision = record.saved_revision
    return SaveWorkingDraftResponse(
        run_id=record.run_id,
        branch_id=record.branch_id,
        previous_viewer_branch_id=record.previous_viewer_branch_id,
        viewer_branch_id=record.viewer_branch_id,
        saved_revision=SavedRevisionResponse(
            revision_id=revision.revision_id,
            sequence=revision.sequence,
            parent_revision_id=revision.parent_revision_id,
            kind=revision.kind,
            payload_schema_version=revision.payload_schema_version,
            content_hash_algorithm=revision.content_hash_algorithm,
            content_hash=revision.content_hash,
            change_summary=revision.change_summary,
        ),
        working_draft=_working_draft_response(record.working_draft),
        audit_event_id=record.audit_event.audit_event_id,
    )


def _revision_history_entry_response(
    record: BranchSavedRevisionRecord,
    *,
    requested_branch_id: str,
    saved_head_revision_id: str,
) -> SavedRevisionHistoryEntryResponse:
    return SavedRevisionHistoryEntryResponse(
        revision_id=record.revision_id,
        revision_branch_id=record.branch_id,
        sequence=record.sequence,
        parent_revision_id=record.parent_revision_id,
        kind=record.kind,
        payload_schema_version=record.payload_schema_version,
        content_hash_algorithm=record.content_hash_algorithm,
        content_hash=record.content_hash,
        change_summary=record.change_summary,
        created_at=record.created_at,
        is_shared_revision=record.branch_id != requested_branch_id,
        is_branch_head=record.revision_id == saved_head_revision_id,
    )


def _revision_history_response(
    record: BranchSavedRevisionHistoryRecord,
) -> SavedRevisionHistoryListResponse:
    return SavedRevisionHistoryListResponse(
        run_id=record.run_id,
        branch_id=record.branch_id,
        saved_head_revision_id=record.saved_head_revision_id,
        saved_revisions=[
            _revision_history_entry_response(
                revision,
                requested_branch_id=record.branch_id,
                saved_head_revision_id=record.saved_head_revision_id,
            )
            for revision in record.saved_revisions
        ],
    )


def _raise_saved_revision_history_http_error(exc: Exception) -> None:
    if isinstance(exc, SavedRevisionHistoryNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "saved_revision_history_not_found", "message": str(exc)},
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": "saved_revision_history_conflict", "message": str(exc)},
    ) from exc


def _raise_working_draft_http_error(exc: Exception) -> None:
    if isinstance(exc, WorkingDraftNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "working_draft_not_found", "message": str(exc)},
        ) from exc
    if isinstance(exc, WorkingDraftVersionConflictError):
        code = "working_draft_version_conflict"
    elif isinstance(exc, WorkingDraftIdentityConflictError):
        code = "working_draft_identity_conflict"
    else:
        code = "working_draft_conflict"
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": code, "message": str(exc)},
    ) from exc


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


@router.get(
    "/{run_id}/branches/{branch_id}/working-draft",
    response_model=ViewerBranchWorkingDraftResponse,
)
def get_working_draft(
    run_id: str,
    branch_id: str,
    service: RunWorkingDraftService = Depends(get_run_working_draft_service),
) -> ViewerBranchWorkingDraftResponse:
    try:
        return _working_draft_response(
            service.get_viewer_branch_draft(
                run_id=run_id, branch_id=branch_id
            )
        )
    except (WorkingDraftNotFoundError, WorkingDraftConflictError) as exc:
        _raise_working_draft_http_error(exc)
        raise AssertionError("unreachable")


@router.put(
    "/{run_id}/branches/{branch_id}/working-draft/viewer-branch",
    response_model=ViewerBranchWorkingDraftResponse,
)
def stage_viewer_branch(
    run_id: str,
    branch_id: str,
    payload: StageViewerBranchRequest,
    service: RunWorkingDraftService = Depends(get_run_working_draft_service),
) -> ViewerBranchWorkingDraftResponse:
    try:
        return _working_draft_response(
            service.stage_viewer_branch(
                run_id=run_id,
                branch_id=branch_id,
                viewer_branch_id=payload.viewer_branch_id,
                expected_draft_version=payload.expected_draft_version,
            )
        )
    except (WorkingDraftNotFoundError, WorkingDraftConflictError) as exc:
        _raise_working_draft_http_error(exc)
        raise AssertionError("unreachable")


@router.post(
    "/{run_id}/branches/{branch_id}/working-draft/save",
    response_model=SaveWorkingDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def save_working_draft(
    run_id: str,
    branch_id: str,
    payload: SaveWorkingDraftRequest,
    service: RunWorkingDraftService = Depends(get_run_working_draft_service),
) -> SaveWorkingDraftResponse:
    try:
        return _save_response(
            service.save(
                run_id=run_id,
                branch_id=branch_id,
                expected_draft_version=payload.expected_draft_version,
            )
        )
    except (WorkingDraftNotFoundError, WorkingDraftConflictError) as exc:
        _raise_working_draft_http_error(exc)
        raise AssertionError("unreachable")


@router.get(
    "/{run_id}/branches/{branch_id}/saved-revisions",
    response_model=SavedRevisionHistoryListResponse,
)
def list_saved_revision_history(
    run_id: str,
    branch_id: str,
    service: RunSavedRevisionHistoryService = Depends(
        get_run_saved_revision_history_service
    ),
) -> SavedRevisionHistoryListResponse:
    try:
        return _revision_history_response(
            service.list_history(run_id=run_id, branch_id=branch_id)
        )
    except (
        SavedRevisionHistoryNotFoundError,
        SavedRevisionHistoryConflictError,
    ) as exc:
        _raise_saved_revision_history_http_error(exc)
        raise AssertionError("unreachable")


@router.get(
    "/{run_id}/branches/{branch_id}/saved-revisions/{revision_id}",
    response_model=SavedRevisionHistoryDetailResponse,
)
def get_saved_revision_history_detail(
    run_id: str,
    branch_id: str,
    revision_id: str,
    service: RunSavedRevisionHistoryService = Depends(
        get_run_saved_revision_history_service
    ),
) -> SavedRevisionHistoryDetailResponse:
    try:
        detail = service.get_revision(
            run_id=run_id,
            branch_id=branch_id,
            revision_id=revision_id,
        )
    except (
        SavedRevisionHistoryNotFoundError,
        SavedRevisionHistoryConflictError,
    ) as exc:
        _raise_saved_revision_history_http_error(exc)
        raise AssertionError("unreachable")

    entry = _revision_history_entry_response(
        detail.saved_revision,
        requested_branch_id=branch_id,
        saved_head_revision_id=detail.saved_head_revision_id,
    )
    return SavedRevisionHistoryDetailResponse(
        **entry.model_dump(),
        run_id=run_id,
        branch_id=branch_id,
        payload=detail.saved_revision.payload,
    )


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
