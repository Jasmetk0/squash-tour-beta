"""Narrow Run/Branch Package inspection, preview, and confirm API."""

from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from beta_engine.api.deps import get_run_package_service
from beta_engine.application.run_package_service import (
    RunPackageConflictError,
    RunPackageNotFoundError,
    RunPackageService,
)
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
            run_id=run_id, branch_id=branch_id, **request.model_dump()
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
