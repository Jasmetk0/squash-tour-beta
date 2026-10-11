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
from beta_engine.domain.run_packages import CanonicalPackageDocument, canonical_hash, entity_content_fingerprint

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



class WorldSelectionRequest(BaseModel):
    """Exact World entity selection. Empty selection is a legitimate read-only preview."""

    model_config = ConfigDict(extra="forbid")
    selected_entities: tuple[str, ...] = ()
    conflict_resolutions: dict[str, Literal["keep_run", "use_source"]] = {}


class WorldSelectionConfirmRequest(WorldSelectionRequest):
    command_id: str
    expected_head_revision_id: str
    expected_draft_version: int
    expected_state_fingerprint: str | None
    expected_preview_fingerprint: str
    expected_selection_fingerprint: str


def _review_world_selection(preview, state, request: WorldSelectionRequest) -> dict:
    """Build truthful selection-bound before/after evidence on the server.

    The existing package service remains authoritative for atomic confirm, local
    identity allocation, receipts, draft staging and saved-head concurrency.
    """
    doc = preview.document
    available = {
        f"{doc.package_id}/{entity.source_entity_id}": entity
        for entity in doc.entities
    }
    selected = tuple(sorted(request.selected_entities))
    if len(set(selected)) != len(selected) or set(selected) - set(available):
        raise ValueError("Selection contains duplicate or unknown World entities")
    local = {
        f"{e.source_package_id}/{e.source_entity_id}": e
        for e in (state.entities if state else ())
    }
    divergence = {
        c.removesuffix(":local_divergence")
        for c in preview.conflicts
        if c.endswith(":local_divergence")
    }
    if set(request.conflict_resolutions) - (set(selected) & divergence):
        raise ValueError("Conflict resolutions must target selected, locally diverged entities")

    selected_set = set(selected)
    excluded = sorted(set(available) - selected_set)
    rows = []
    blockers = []
    for label in selected:
        entity = available[label]
        old = local.get(label)
        before = old.payload if old is not None else None
        after = entity.payload
        strategy = request.conflict_resolutions.get(label)
        status = ("keep_run" if strategy == "keep_run" else
                  "add" if old is None else
                  "unchanged" if old.content_fingerprint ==
                  entity_content_fingerprint(
                      entity_kind=entity.entity_kind,
                      entity_schema_version=entity.entity_schema_version,
                      scope=entity.scope,
                      payload=entity.payload,
                      references=entity.references,
                  ) else "update")
        effective_after = before if strategy == "keep_run" else after
        values = [
            {"field": field, "before": before.get(field) if before else None,
             "after": effective_after.get(field) if effective_after else None}
            for field in sorted(set(before or {}) | set(effective_after or {}))
            if (before or {}).get(field) != (effective_after or {}).get(field)
        ]
        if not entity.valid:
            blockers.append(f"{label}: invalid source entity")
        if label in divergence and strategy is None:
            blockers.append(f"{label}: local divergence requires an explicit choice")
        rows.append({
            "label": label,
            "entity_kind": entity.entity_kind,
            "scope": entity.scope,
            "status": status,
            "before": before,
            "after": effective_after,
            "fields": values,
            "local_divergence": label in divergence,
        })

        # References to excluded incoming entities are NOT implicitly imported.
        for ref in entity.references:
            target_label = f"{ref.source_package_id}/{ref.source_entity_id}"
            target = (
                local.get(target_label)
                if target_label not in selected_set
                else available.get(target_label)
            )
            if target is None:
                blockers.append(f"{label}: missing dependency {target_label}")
            elif target.entity_kind != ref.expected_entity_kind or (
                target.entity_schema_version < ref.minimum_schema_version
            ):
                blockers.append(f"{label}: incompatible dependency {target_label}")

    for conflict in preview.conflicts:
        if conflict.endswith(":local_divergence"):
            continue
        if "->" in conflict:
            referenced = conflict.split("->", 1)[0]
            if referenced in selected_set:
                blockers.append(conflict)
        elif selected:
            blockers.append(conflict)
    # An existing entity in the Run may also depend on a newly selected entity;
    # the core service checks this against the full package document at confirm.
    for issue in preview.unresolved:
        if issue.split("->", 1)[0] in selected_set:
            blockers.append(issue)
    blockers = sorted(set(blockers))
    selections = [{"label": label, "entity_kind": e.entity_kind,
                   "scope": e.scope, "valid": e.valid,
                   "status": ("add" if label in preview.additions else
                              "update" if label in preview.updates else
                              "unchanged" if label in preview.unchanged else "invalid"),
                   "local_divergence": label in divergence}
                  for label, e in sorted(available.items())]
    fingerprint = canonical_hash({
        "preview_fingerprint": preview.preview_fingerprint,
        "selected_entities": selected,
        "conflict_resolutions": request.conflict_resolutions,
        "rows": rows,
        "blockers": blockers,
    })
    return {
        "run_id": preview.run_id,
        "branch_id": preview.branch_id,
        "saved_head_revision_id": preview.saved_head_revision_id,
        "draft_version": preview.draft_version,
        "current_state_fingerprint": preview.current_state_fingerprint,
        "preview_fingerprint": preview.preview_fingerprint,
        "selection_fingerprint": fingerprint,
        "source": {"package_id": doc.package_id, "source_version": doc.source_version,
                   "source_fingerprint": doc.source_fingerprint},
        "available": selections,
        "selected_entities": list(selected),
        "excluded_entities": excluded,
        "changes": rows,
        "blockers": blockers,
        "can_confirm": bool(selected) and not blockers,
    }


@router.post("/source-world/{world_id}/selection-preview")
def preview_source_world_selection(
    run_id: str,
    branch_id: str,
    world_id: str,
    request: WorldSelectionRequest,
    service: RunPackageService = Depends(get_run_package_service),
    adapter: WorldPackageRunAdapter = Depends(get_world_package_run_adapter),
):
    try:
        document = adapter.build_document(world_id)
        preview = service.preview(run_id=run_id, branch_id=branch_id, document=document)
        state = service.get(run_id=run_id, branch_id=branch_id)
        return _review_world_selection(preview, state, request)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (RunPackageConflictError, RunPackageNotFoundError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/source-world/{world_id}/selection-confirm")
def confirm_source_world_selection(
    run_id: str,
    branch_id: str,
    world_id: str,
    request: WorldSelectionConfirmRequest,
    service: RunPackageService = Depends(get_run_package_service),
    adapter: WorldPackageRunAdapter = Depends(get_world_package_run_adapter),
):
    try:
        document = adapter.build_document(world_id)
        preview = service.preview(run_id=run_id, branch_id=branch_id, document=document)
        state = service.get(run_id=run_id, branch_id=branch_id)
        reviewed = _review_world_selection(preview, state, request)
        if not reviewed["can_confirm"] or reviewed["blockers"]:
            raise RunPackageConflictError("Selected World scope is invalid or blocked")
        if (
            reviewed["selection_fingerprint"] != request.expected_selection_fingerprint
            or reviewed["preview_fingerprint"] != request.expected_preview_fingerprint
            or reviewed["saved_head_revision_id"] != request.expected_head_revision_id
            or reviewed["draft_version"] != request.expected_draft_version
            or reviewed["current_state_fingerprint"] != request.expected_state_fingerprint
        ):
            raise RunPackageConflictError("World selection preview is stale")
        result = service.confirm(
            run_id=run_id, branch_id=branch_id, document=document,
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


@router.post("/source-calendar/{season_key}/preview")
def preview_source_calendar(
    run_id: str,
    branch_id: str,
    season_key: str,
    service: RunPackageService = Depends(get_run_package_service),
    adapter: CalendarPackageRunAdapter = Depends(get_calendar_package_run_adapter),
):
    try:
        season = season_key.replace("-", "/", 1)
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


@router.post("/source-calendar/{season_key}/confirm")
def confirm_source_calendar(
    run_id: str,
    branch_id: str,
    season_key: str,
    request: SourceWorldConfirmRequest,
    service: RunPackageService = Depends(get_run_package_service),
    adapter: CalendarPackageRunAdapter = Depends(get_calendar_package_run_adapter),
):
    try:
        season = season_key.replace("-", "/", 1)
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
