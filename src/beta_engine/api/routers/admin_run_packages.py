"""Narrow Run/Branch Package inspection, preview, and confirm API."""

from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from beta_engine.api.deps import (
    get_calendar_package_run_adapter,
    get_run_package_service,
    get_world_package_run_adapter,
)
from beta_engine.application.calendar_package_run_adapter import CalendarPackageRunAdapter
from beta_engine.application.run_package_service import (
    RunPackageConflictError,
    RunPackageNotFoundError,
    RunPackageService,
)
from beta_engine.application.world_package_run_adapter import WorldPackageRunAdapter
from beta_engine.domain.run_packages import CanonicalPackageDocument

router = APIRouter(
    prefix="/admin/runs/{run_id}/branches/{branch_id}/packages",
    tags=["admin-run-packages"],
)


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document: CanonicalPackageDocument


class ConfirmRequest(PreviewRequest):
    command_id: str
    expected_head_revision_id: str
    expected_draft_version: int
    expected_state_fingerprint: str | None
    expected_preview_fingerprint: str
    conflict_resolutions: dict[str, Literal["keep_run", "use_source"]] = {}
    selected_entities: tuple[str, ...] | None = None


class SourceWorldConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command_id: str
    expected_head_revision_id: str
    expected_draft_version: int
    expected_state_fingerprint: str | None
    expected_preview_fingerprint: str
    conflict_resolutions: dict[str, Literal["keep_run", "use_source"]] = {}
    selected_entities: tuple[str, ...] | None = None


@router.get("")
def get_state(
    run_id: str,
    branch_id: str,
    service: RunPackageService = Depends(get_run_package_service),
):
    try:
        state = service.get(run_id=run_id, branch_id=branch_id)
        return {
            "state": state.model_dump(mode="json") if state else None,
            "fingerprint": state.fingerprint if state else None,
        }
    except RunPackageNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/preview")
def preview(
    run_id: str,
    branch_id: str,
    request: PreviewRequest,
    service: RunPackageService = Depends(get_run_package_service),
):
    try:
        result = service.preview(
            run_id=run_id, branch_id=branch_id, document=request.document
        )
        return {
            **result.model_dump(mode="json"),
            "preview_fingerprint": result.preview_fingerprint,
        }
    except (RunPackageConflictError, RunPackageNotFoundError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/confirm")
def confirm(
    run_id: str,
    branch_id: str,
    request: ConfirmRequest,
    service: RunPackageService = Depends(get_run_package_service),
):
    try:
        result = service.confirm(
            run_id=run_id,
            branch_id=branch_id,
            document=request.document,
            command_id=request.command_id,
            expected_head_revision_id=request.expected_head_revision_id,
            expected_draft_version=request.expected_draft_version,
            expected_state_fingerprint=request.expected_state_fingerprint,
            expected_preview_fingerprint=request.expected_preview_fingerprint,
            conflict_resolutions=request.conflict_resolutions,
            selected_entities=request.selected_entities,
        )
        return {
            "state": result.state.model_dump(mode="json") if result.state else None,
            "state_fingerprint": result.state.fingerprint if result.state else None,
            "draft_version": result.draft_version,
            "already_applied": result.already_applied,
            "command_id": result.command_id,
        }
    except RunPackageNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (RunPackageConflictError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/source-world/{world_id}/preview")
def preview_source_world(
    run_id: str,
    branch_id: str,
    world_id: str,
    service: RunPackageService = Depends(get_run_package_service),
    adapter: WorldPackageRunAdapter = Depends(get_world_package_run_adapter),
):
    try:
        document = adapter.build_document(world_id)
        result = service.preview(
            run_id=run_id, branch_id=branch_id, document=document
        )
        return {
            **result.model_dump(mode="json"),
            "preview_fingerprint": result.preview_fingerprint,
        }
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (RunPackageConflictError, RunPackageNotFoundError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/source-world/{world_id}/confirm")
def confirm_source_world(
    run_id: str,
    branch_id: str,
    world_id: str,
    request: SourceWorldConfirmRequest,
    service: RunPackageService = Depends(get_run_package_service),
    adapter: WorldPackageRunAdapter = Depends(get_world_package_run_adapter),
):
    try:
        document = adapter.build_document(world_id)
        result = service.confirm(
            run_id=run_id,
            branch_id=branch_id,
            document=document,
            command_id=request.command_id,
            expected_head_revision_id=request.expected_head_revision_id,
            expected_draft_version=request.expected_draft_version,
            expected_state_fingerprint=request.expected_state_fingerprint,
            expected_preview_fingerprint=request.expected_preview_fingerprint,
            conflict_resolutions=request.conflict_resolutions,
            selected_entities=request.selected_entities,
        )
        return {
            "state": result.state.model_dump(mode="json") if result.state else None,
            "state_fingerprint": result.state.fingerprint if result.state else None,
            "draft_version": result.draft_version,
            "already_applied": result.already_applied,
            "command_id": result.command_id,
        }
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RunPackageNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (RunPackageConflictError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/world/{package_id}/countries")
def get_run_world_countries(
    run_id: str,
    branch_id: str,
    package_id: str,
    service: RunPackageService = Depends(get_run_package_service),
    adapter: WorldPackageRunAdapter = Depends(get_world_package_run_adapter),
):
    try:
        state = service.get(run_id=run_id, branch_id=branch_id)
        if state is None:
            raise RunPackageNotFoundError("Run Package state was not found")
        projection = adapter.project_countries(state, package_id=package_id)
        return {
            **projection.model_dump(mode="json"),
            "fingerprint": projection.fingerprint,
        }
    except RunPackageNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/world/{package_id}/generation")
def get_run_world_generation(
    run_id: str,
    branch_id: str,
    package_id: str,
    service: RunPackageService = Depends(get_run_package_service),
    adapter: WorldPackageRunAdapter = Depends(get_world_package_run_adapter),
):
    try:
        state = service.get(run_id=run_id, branch_id=branch_id)
        if state is None:
            raise RunPackageNotFoundError("Run Package state was not found")
        projection = adapter.project_generation(state, package_id=package_id)
        return {
            **projection.model_dump(mode="json"),
            "fingerprint": projection.fingerprint,
            "content_fingerprint": projection.content_fingerprint,
        }
    except RunPackageNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/source-calendar/{season}/preview")
def preview_source_calendar(
    run_id: str,
    branch_id: str,
    season: str,
    service: RunPackageService = Depends(get_run_package_service),
    adapter: CalendarPackageRunAdapter = Depends(get_calendar_package_run_adapter),
):
    try:
        document = adapter.build_document(season)
        result = service.preview(
            run_id=run_id, branch_id=branch_id, document=document
        )
        return {
            **result.model_dump(mode="json"),
            "preview_fingerprint": result.preview_fingerprint,
        }
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (RunPackageConflictError, RunPackageNotFoundError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/source-calendar/{season}/confirm")
def confirm_source_calendar(
    run_id: str,
    branch_id: str,
    season: str,
    request: SourceWorldConfirmRequest,
    service: RunPackageService = Depends(get_run_package_service),
    adapter: CalendarPackageRunAdapter = Depends(get_calendar_package_run_adapter),
):
    try:
        document = adapter.build_document(season)
        result = service.confirm(
            run_id=run_id,
            branch_id=branch_id,
            document=document,
            command_id=request.command_id,
            expected_head_revision_id=request.expected_head_revision_id,
            expected_draft_version=request.expected_draft_version,
            expected_state_fingerprint=request.expected_state_fingerprint,
            expected_preview_fingerprint=request.expected_preview_fingerprint,
            conflict_resolutions=request.conflict_resolutions,
            selected_entities=request.selected_entities,
        )
        return {
            "state": result.state.model_dump(mode="json") if result.state else None,
            "state_fingerprint": result.state.fingerprint if result.state else None,
            "draft_version": result.draft_version,
            "already_applied": result.already_applied,
            "command_id": result.command_id,
        }
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RunPackageNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (RunPackageConflictError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/calendar/{package_id}")
def get_run_calendar(
    run_id: str,
    branch_id: str,
    package_id: str,
    service: RunPackageService = Depends(get_run_package_service),
    adapter: CalendarPackageRunAdapter = Depends(get_calendar_package_run_adapter),
):
    try:
        state = service.get(run_id=run_id, branch_id=branch_id)
        if state is None:
            raise RunPackageNotFoundError("Run Package state was not found")
        projection = adapter.project_calendar(state, package_id=package_id)
        return {
            **projection.model_dump(mode="json"),
            "fingerprint": projection.fingerprint,
            "content_fingerprint": projection.content_fingerprint,
        }
    except RunPackageNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
