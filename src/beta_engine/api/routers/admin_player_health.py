"""Run/Branch Admin Player Health inspection, reviewed edits, and Save boundary."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from beta_engine.api.deps import (
    ApiRuntime,
    get_run_working_draft_service,
    get_runtime,
)
from beta_engine.application.admin_health_edit import (
    AdminHealthEditRequest,
    AdminHealthEditService,
)
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.infrastructure.db.player_health_state import (
    PLAYER_HEALTH_COMPONENT_KEY,
    health_component,
)

router = APIRouter(
    prefix="/admin/runs/{run_id}/branches/{branch_id}",
    tags=["admin-player-health"],
)


def _service(runtime: ApiRuntime) -> AdminHealthEditService:
    return AdminHealthEditService(runtime.repository)


@router.get("/players/{player_id}/health")
def inspect_player_health(
    run_id: str,
    branch_id: str,
    player_id: str,
    runtime: ApiRuntime = Depends(get_runtime),
):
    try:
        return _service(runtime).inspect(
            run_id=run_id,
            branch_id=branch_id,
            player_id=player_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "player_health_unavailable", "message": str(exc)},
        ) from exc


@router.post("/players/{player_id}/health/preview")
def preview_player_health_edit(
    run_id: str,
    branch_id: str,
    player_id: str,
    payload: AdminHealthEditRequest,
    runtime: ApiRuntime = Depends(get_runtime),
):
    if payload.player_id != player_id:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "player_health_scope_mismatch",
                "message": "Player Health request player differs from URL scope",
            },
        )
    try:
        preview = _service(runtime).preview(
            run_id=run_id,
            branch_id=branch_id,
            request=payload,
        )
        return {
            **preview.model_dump(mode="json"),
            "preview_fingerprint": preview.preview_fingerprint,
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "player_health_preview_conflict", "message": str(exc)},
        ) from exc


@router.post("/players/{player_id}/health")
def commit_player_health_edit(
    run_id: str,
    branch_id: str,
    player_id: str,
    payload: AdminHealthEditRequest,
    expected_preview: str = Header(
        alias="X-Player-Health-Preview-Fingerprint",
        pattern=r"^[0-9a-f]{64}$",
    ),
    runtime: ApiRuntime = Depends(get_runtime),
):
    if payload.player_id != player_id:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "player_health_scope_mismatch",
                "message": "Player Health request player differs from URL scope",
            },
        )
    try:
        return _service(runtime).commit(
            run_id=run_id,
            branch_id=branch_id,
            request=payload,
            expected_preview_fingerprint=expected_preview,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "player_health_commit_conflict", "message": str(exc)},
        ) from exc


@router.get("/player-health/save/preview")
def preview_player_health_save(
    run_id: str,
    branch_id: str,
    runtime: ApiRuntime = Depends(get_runtime),
):
    try:
        draft = runtime.repository.get_viewer_branch_working_draft(
            run_id=run_id,
            branch_id=branch_id,
        )
        revision_state = runtime.repository.get_branch_revision_state(
            branch_id=branch_id
        )
        if revision_state.run_id != run_id:
            raise ValueError("Player Health Save Run/Branch scope differs")
        with runtime.repository._session_factory() as session:
            component = health_component(
                session,
                run_id=run_id,
                branch_id=branch_id,
            )
        if component is None:
            raise ValueError("Canonical Player Health state is missing")
        saved = runtime.repository.get_branch_saved_revision(
            revision_id=draft.base_saved_revision_id
        )
        saved_component = (
            saved.payload.get("content", {}).get(PLAYER_HEALTH_COMPONENT_KEY)
            if saved is not None
            else None
        )
        changes = revision_state.working_draft.changes
        return {
            "run_id": run_id,
            "branch_id": branch_id,
            "draft_version": draft.draft_version,
            "draft_status": draft.status,
            "health_component_fingerprint": component["fingerprint"],
            "changed_since_saved_head": component != saved_component,
            "can_save": (
                draft.status == "dirty"
                and component != saved_component
                and bool(changes)
                and all(
                    isinstance(change, dict)
                    and change.get("kind") == "player_health_state"
                    for change in changes
                )
            ),
        }
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "player_health_save_unavailable", "message": str(exc)},
        ) from exc


class PlayerHealthSaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_draft_version: int = Field(ge=0)
    expected_player_health_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


@router.post("/player-health/save", status_code=201)
def save_player_health(
    run_id: str,
    branch_id: str,
    payload: PlayerHealthSaveRequest,
    service: RunWorkingDraftService = Depends(get_run_working_draft_service),
):
    try:
        return service.save_player_health(
            run_id=run_id,
            branch_id=branch_id,
            **payload.model_dump(),
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "player_health_save_conflict", "message": str(exc)},
        ) from exc
