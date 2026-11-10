"""Narrow Run/Branch Package inspection, preview, and confirm API."""

from collections.abc import Callable
from typing import Literal
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from beta_engine.api.deps import (
    ApiRuntime,
    get_runtime,
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
from beta_engine.application.atp_reference_package_adapter import ATPReferencePackageAdapter
from beta_engine.application.atp_historical_calendar_adapter import ATPHistoricalCalendarAdapter
from beta_engine.application.atp_earth_run_calendar_preview import preview_atp_earth_weeks_on_run
from beta_engine.application.atp_saved_snapshot_week_preview import (
    audit_saved_atp_tour_bindings,
    build_saved_atp_reference_week_mapping,
)
from beta_engine.application.atp_saved_tour_source import read_saved_atp_source
from beta_engine.application.run_calendar_read_authority import resolve_saved_run_calendar
from beta_engine.application.atp_earth_week_mapping import (
    SOURCE_FILE as ATP_DATE_SOURCE_FILE, build_projection,
)
from beta_engine.domain.run_packages import CanonicalPackageDocument, canonical_hash, entity_content_fingerprint
from beta_engine.application.run_edition_entry_timing import RunEditionEntryTimingService
from beta_engine.domain.tournaments.edition_entry_timing import EditionEntryTiming

router = APIRouter(
    prefix="/admin/runs/{run_id}/branches/{branch_id}/packages",
    tags=["admin-run-packages"],
)
atp_reference_catalog_router = APIRouter(
    prefix="/admin/reference-packages", tags=["admin-reference-packages"]
)


class EntryTimingPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timing: dict


class EntryTimingConfirmRequest(EntryTimingPreviewRequest):
    command_id: str = Field(min_length=1, max_length=128)
    expected_preview_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    operator_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)


@router.get("/calendar/{package_id}/editions/{event_id}/entry-timing")
def inspect_entry_timing(run_id: str, branch_id: str, package_id: str, event_id: str,
                        service: RunPackageService = Depends(get_run_package_service)):
    try:
        return RunEditionEntryTimingService(service).inspect(
            run_id=run_id, branch_id=branch_id, package_id=package_id, event_id=event_id)
    except RunPackageNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/calendar/{package_id}/editions/{event_id}/entry-timing/preview")
def preview_entry_timing(run_id: str, branch_id: str, package_id: str, event_id: str,
                         request: EntryTimingPreviewRequest,
                         service: RunPackageService = Depends(get_run_package_service)):
    try:
        timing = EditionEntryTiming.model_validate_json(json.dumps(request.timing))
        return RunEditionEntryTimingService(service).preview(
            run_id=run_id, branch_id=branch_id, package_id=package_id, event_id=event_id, timing=timing)
    except RunPackageNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/calendar/{package_id}/editions/{event_id}/entry-timing/confirm")
def confirm_entry_timing(run_id: str, branch_id: str, package_id: str, event_id: str,
                         request: EntryTimingConfirmRequest,
                         service: RunPackageService = Depends(get_run_package_service)):
    try:
        timing = EditionEntryTiming.model_validate_json(json.dumps(request.timing))
        return RunEditionEntryTimingService(service).confirm(
            run_id=run_id, branch_id=branch_id, package_id=package_id, event_id=event_id,
            timing=timing, command_id=request.command_id,
            expected_preview_fingerprint=request.expected_preview_fingerprint,
            operator_label=request.operator_label, audit_reason=request.audit_reason)
    except RunPackageNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


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



@atp_reference_catalog_router.get("/atp-tour-1990-2026")
@router.get("/source-atp-reference/catalog")
def get_source_atp_reference_catalog():
    """Small, public source manifest; no Run or sporting-state mutation."""
    try:
        return ATPReferencePackageAdapter().catalog()
    except (OSError, ValueError) as exc:
        raise HTTPException(409, "ATP reference source is invalid or unavailable") from exc


def _preview_atp_source(
    run_id: str,
    branch_id: str,
    service: RunPackageService,
    build_document: Callable[[], CanonicalPackageDocument],
):
    try:
        document = build_document()
        result = service.preview(run_id=run_id, branch_id=branch_id, document=document)
        # Do not transmit the full historical JSON on every read-only
        # preview. The CAS fingerprint still covers the frozen Setup and
        # each source child; the client verifies this against the catalog.
        return {
            **result.model_dump(mode="json", exclude={"document"}),
            "document_identity": {
                "package_type": document.package_type.value,
                "package_id": document.package_id,
                "source_version": document.source_version,
                "source_fingerprint": document.source_fingerprint,
            },
            "preview_fingerprint": result.preview_fingerprint,
        }
    except (OSError, RunPackageConflictError, RunPackageNotFoundError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


def _confirm_atp_source(
    run_id: str,
    branch_id: str,
    request: SourceWorldConfirmRequest,
    service: RunPackageService,
    build_document: Callable[[], CanonicalPackageDocument],
):
    try:
        document = build_document()
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
            selected_entities=None,
        )
        return {
            "state": result.state.model_dump(mode="json") if result.state else None,
            "state_fingerprint": result.state.fingerprint if result.state else None,
            "draft_version": result.draft_version,
            "already_applied": result.already_applied,
            "command_id": result.command_id,
        }
    except (OSError, RunPackageConflictError, RunPackageNotFoundError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/source-atp-reference/preview")
def preview_source_atp_reference(
    run_id: str,
    branch_id: str,
    service: RunPackageService = Depends(get_run_package_service),
):
    """Preview both immutable reference types together; never generate Editions."""
    return _preview_atp_source(
        run_id, branch_id, service, lambda: ATPReferencePackageAdapter().build_document(),
    )


@router.post("/source-atp-reference/confirm")
def confirm_source_atp_reference(
    run_id: str,
    branch_id: str,
    request: SourceWorldConfirmRequest,
    service: RunPackageService = Depends(get_run_package_service),
):
    """Apply the two source references through existing CAS-guarded Run Packages."""
    if request.selected_entities is not None:
        raise HTTPException(409, "ATP reference Setup must be applied atomically")
    return _confirm_atp_source(
        run_id, branch_id, request, service, lambda: ATPReferencePackageAdapter().build_document(),
    )


@atp_reference_catalog_router.get("/atp-tour-1990-2026-calendar")
@router.get("/source-atp-reference-calendar/catalog")
def get_source_atp_reference_calendar_catalog():
    """Reference-only 1990–2026 date provenance and child Package fingerprints."""
    try:
        return ATPHistoricalCalendarAdapter().catalog()
    except (OSError, ValueError) as exc:
        raise HTTPException(409, "ATP Calendar reference source is invalid or unavailable") from exc


@atp_reference_catalog_router.get("/atp-tour-1990-2026-calendar/years/{year}")
def get_source_atp_reference_calendar_year(year: int):
    """Read-only dated events for one season; never invent missing Series dates."""
    if not 1990 <= year <= 2026:
        raise HTTPException(404, "ATP Calendar source year is outside 1990–2026")
    try:
        document = ATPHistoricalCalendarAdapter().build_calendar()
        coverage = [
            e for e in document.entities
            if e.entity_kind == "tennis.calendar.coverage.reference.v1"
            and e.payload["atp_season_year"] == year
        ]
        if len(coverage) != 1:
            raise ValueError("Invalid ATP historical Calendar year coverage")
        occurrences = [
            e.payload for e in document.entities
            if e.entity_kind == "tennis.calendar.occurrence.reference.v1"
            and e.payload["atp_season_year"] == year
        ]
        events = [{
            key: e[key] for key in (
                "series_id", "category_id", "start_date", "end_date",
                "start_year_week", "end_year_week", "iso_weeks_occupied",
                "source_url", "year_source_state",
            )
        } for e in sorted(occurrences, key=lambda x: (
            x["start_date"], x["series_id"]
        ))]
        return {
            "year": year,
            "package_id": document.package_id,
            "source_fingerprint": document.source_fingerprint,
            "read_only": True,
            "run_mutated": False,
            "coverage": coverage[0].payload,
            "events": events,
        }
    except (OSError, ValueError) as exc:
        raise HTTPException(409, "ATP Calendar source year is invalid") from exc


@router.get("/source-atp-reference-calendar/run-week-preview")
def preview_atp_reference_against_saved_run_calendar(
    run_id: str,
    branch_id: str,
    year: list[int] | None = Query(default=None),
    runtime: ApiRuntime = Depends(get_runtime),
):
    """Pure source-only ATP projection against a hash-checked Saved Run clock.

    This endpoint never installs Calendar Editions, rounds, Simulation Slots,
    rankings, or a Package; it never changes Working Draft or Saved history.
    Source ATP dates are *server reference data*, NOT a claim of a previously
    applied/saved ATP Package snapshot for this Run.
    """
    if year is not None and any(not 1990 <= item <= 2026 for item in year):
        raise HTTPException(422, "ATP source year must be in 1990–2026")
    try:
        # No source drift: validate the exact historical Calendar adapter's
        # stored generated document against the four canonical source files.
        ATPHistoricalCalendarAdapter().build_calendar()
        dated = json.loads(ATP_DATE_SOURCE_FILE.read_text(encoding="utf-8"))
        mapping = build_projection(dated)
        with runtime.repository._session_factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            clock = resolve_saved_run_calendar(
                session, run_id=run_id, branch_id=branch_id
            )
            report = preview_atp_earth_weeks_on_run(
                calendar=clock, mapping=mapping, years=year
            )
        return {
            **report,
            "run_id": run_id,
            "branch_id": branch_id,
            "saved_run_calendar_verified": True,
            "uses_current_server_reference_not_run_snapshot": True,
            "run_mutated": False,
            "working_draft_mutated": False,
            "historical_revision_mutated": False,
        }
    except (OSError, TypeError, ValueError) as exc:
        raise HTTPException(
            409,
            detail={
                "code": "atp_run_week_preview_conflict",
                "message": str(exc),
            },
        ) from exc



@router.get("/saved-source-atp-reference-calendar/run-week-preview")
def preview_saved_atp_reference_against_saved_run_calendar(
    run_id: str,
    branch_id: str,
    year: list[int] | None = Query(default=None),
    validate_tour_bindings: bool = Query(default=False),
    runtime: ApiRuntime = Depends(get_runtime),
):
    """Read exact immutable Saved ATP Package entities on a verified W52 clock.

    This endpoint does NOT fall back to server-installed source files or a
    mutable Working Draft. Optionally verify the full Saved Tour source links
    needed for sporting conversion, alongside the date-only preview.
    """
    if year is not None and any(not 1990 <= item <= 2026 for item in year):
        raise HTTPException(422, "ATP source year must be in 1990–2026")
    try:
        with runtime.repository._session_factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            clock, revision, state = read_saved_atp_source(
                session, run_id=run_id, branch_id=branch_id
            )
            mapping = build_saved_atp_reference_week_mapping(state)
            report = preview_atp_earth_weeks_on_run(
                calendar=clock, mapping=mapping, years=year
            )
            if validate_tour_bindings:
                report["source_tour_bindings"] = audit_saved_atp_tour_bindings(
                    state,
                    selected_occurrences=frozenset(
                        event["source_identity"] for event in report["events"]
                    ),
                )
        return {
            **report,
            "run_id": run_id,
            "branch_id": branch_id,
            "saved_head_revision_id": revision.revision_id,
            "saved_package_origin_branch_id": revision.branch_id,
            "saved_run_calendar_verified": True,
            "saved_package_source_verified": True,
            "uses_saved_run_package_snapshot": True,
            "uses_current_server_reference_not_run_snapshot": False,
            "run_mutated": False,
            "working_draft_mutated": False,
            "historical_revision_mutated": False,
        }
    except (OSError, TypeError, KeyError, AttributeError, ValueError) as exc:
        raise HTTPException(
            409,
            detail={
                "code": "atp_saved_run_week_preview_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/source-atp-reference-calendar/preview")
def preview_source_atp_reference_calendar(
    run_id: str,
    branch_id: str,
    service: RunPackageService = Depends(get_run_package_service),
):
    """Preview immutable 3-child Setup; omit giant frozen payload from response."""
    return _preview_atp_source(
        run_id, branch_id, service, lambda: ATPHistoricalCalendarAdapter().build_document(),
    )


@router.post("/source-atp-reference-calendar/confirm")
def confirm_source_atp_reference_calendar(
    run_id: str,
    branch_id: str,
    request: SourceWorldConfirmRequest,
    service: RunPackageService = Depends(get_run_package_service),
):
    """Atomically apply Category + Series + Calendar; explicit separate Save."""
    if request.selected_entities is not None:
        raise HTTPException(409, "ATP Calendar reference Setup must be applied atomically")
    return _confirm_atp_source(
        run_id, branch_id, request, service, lambda: ATPHistoricalCalendarAdapter().build_document(),
    )


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
