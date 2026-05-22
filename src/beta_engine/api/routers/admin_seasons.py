from __future__ import annotations

import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import get_initial_pool_season_bootstrap_service, get_season_calendar_service, get_season_range_execution_service, get_season_range_preflight_service, get_season_readiness_service, get_season_registry_service, get_season_template_service
from beta_engine.api.schemas import SeasonBootstrapRequest
from beta_engine.application.season_player_bootstrap_service import (
    InitialPoolSeasonBootstrapService,
    SeasonActivePlayersResponse,
    SeasonBootstrapResult,
)
from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.season_readiness_service import SeasonReadinessRequest, SeasonReadinessResult, SeasonReadinessService
from beta_engine.application.season_range_preflight_service import SeasonRangePreflightRequest, SeasonRangePreflightResult, SeasonRangePreflightService
from beta_engine.application.season_range_execution_service import RunSeasonRangeRequest, RunSeasonRangeResult, SeasonRangeExecutionService
from beta_engine.application.season_registry_service import SeasonRegistryResponse, SeasonRegistryService
from beta_engine.application.season_template_service import SeasonTemplatesResponse, SeasonTemplateService
from beta_engine.domain.calendar.season_labels import normalize_season_label, to_long_season_label
from beta_engine.api.season_label_params import normalize_season_for_legacy_services
from beta_engine.domain.tournaments import SeasonBuilderDryRunBuildRequest, SeasonBuilderDryRunBuildResponse, SeasonBuilderPreflightRequest, SeasonBuilderPreflightResponse, SeasonCalendarBuildRequest, SeasonCalendarBuildResult

router = APIRouter(prefix="/admin/seasons", tags=["admin-seasons"])


@router.get("/registry", response_model=SeasonRegistryResponse)
def get_season_registry(service: SeasonRegistryService = Depends(get_season_registry_service)) -> SeasonRegistryResponse:
    return service.build_registry()


@router.get("/templates", response_model=SeasonTemplatesResponse)
def get_season_templates(service: SeasonTemplateService = Depends(get_season_template_service)) -> SeasonTemplatesResponse:
    return service.list_templates()


@router.post("/readiness", response_model=SeasonReadinessResult)
def inspect_season_readiness(
    payload: SeasonReadinessRequest,
    service: SeasonReadinessService = Depends(get_season_readiness_service),
) -> SeasonReadinessResult:
    return service.inspect_season(payload)


@router.post("/range-run", response_model=RunSeasonRangeResult)
def run_season_range(
    payload: RunSeasonRangeRequest,
    service: SeasonRangeExecutionService = Depends(get_season_range_execution_service),
) -> RunSeasonRangeResult:
    return service.run_range(payload)


@router.post("/range-preflight", response_model=SeasonRangePreflightResult)
def preflight_season_range(
    payload: SeasonRangePreflightRequest,
    service: SeasonRangePreflightService = Depends(get_season_range_preflight_service),
) -> SeasonRangePreflightResult:
    return service.preflight_range(payload)


@router.get("/{season:path}/players", response_model=SeasonActivePlayersResponse)
def get_season_active_players(
    season: str,
    service: InitialPoolSeasonBootstrapService = Depends(get_initial_pool_season_bootstrap_service),
) -> SeasonActivePlayersResponse:
    return service.get_active_players(season=normalize_season_for_legacy_services(season))


@router.post("/{season:path}/bootstrap-from-initial-pool", response_model=SeasonBootstrapResult)
def bootstrap_season_from_initial_pool(
    season: str,
    payload: SeasonBootstrapRequest,
    service: InitialPoolSeasonBootstrapService = Depends(get_initial_pool_season_bootstrap_service),
) -> SeasonBootstrapResult:
    try:
        return service.bootstrap_from_initial_pool(
            season=season,
            source_season=payload.source_season,
            seed=payload.seed,
            dry_run=payload.dry_run,
            overwrite_existing=payload.overwrite_existing,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{season:path}/calendar", response_model=SeasonCalendarBuildResult)
def get_season_calendar(
    season: str,
    service: SeasonCalendarService = Depends(get_season_calendar_service),
) -> SeasonCalendarBuildResult:
    return service.get_calendar(season=normalize_season_for_legacy_services(season))


@router.post("/{season:path}/calendar/build", response_model=SeasonCalendarBuildResult)
def build_season_calendar(
    season: str,
    payload: SeasonCalendarBuildRequest,
    service: SeasonCalendarService = Depends(get_season_calendar_service),
) -> SeasonCalendarBuildResult:
    try:
        return service.build_calendar(season=season, request=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/builder/preflight", response_model=SeasonBuilderPreflightResponse)
def preflight_season_builder(
    payload: SeasonBuilderPreflightRequest,
    calendar_service: SeasonCalendarService = Depends(get_season_calendar_service),
    template_service: SeasonTemplateService = Depends(get_season_template_service),
) -> SeasonBuilderPreflightResponse:
    supported_overwrite_policies = {"merge_preview", "overwrite_preview"}
    warnings: list[str] = []
    errors: list[str] = []
    source_resolved = False
    target_calendar_exists: bool | None = None
    target_event_count: int | None = None
    target_first_week: int | None = None
    target_last_week: int | None = None
    target_week_count: int | None = None
    normalized_target: str = payload.target_season_label

    try:
        normalized_target = to_long_season_label(normalize_season_label(payload.target_season_label))
    except ValueError as exc:
        errors.append(f"Invalid target season label '{payload.target_season_label}': {exc}")

    if not errors:
        calendar_result = calendar_service.get_calendar(season=normalized_target)
        target_calendar_exists = calendar_result.calendar is not None
        target_event_count = len(calendar_result.calendar.events) if calendar_result.calendar else 0
        if calendar_result.calendar and calendar_result.calendar.events:
            target_weeks = [event.season_week for event in calendar_result.calendar.events]
            target_first_week = min(target_weeks)
            target_last_week = max(target_weeks)
            target_week_count = len(set(target_weeks))
        if payload.overwrite_policy is not None and payload.overwrite_policy not in supported_overwrite_policies:
            errors.append(
                f"Unsupported overwrite_policy '{payload.overwrite_policy}'. Supported values are merge_preview and overwrite_preview."
            )

        if target_calendar_exists and not payload.overwrite_policy:
            errors.append("Explicit overwrite/merge policy is required before any future build when a target calendar already exists.")
        elif target_calendar_exists and payload.overwrite_policy == "merge_preview":
            warnings.append(
                "Merge policy preview selected. Future implementation must still perform event-level backend diff before any merge command."
            )
        elif target_calendar_exists and payload.overwrite_policy == "overwrite_preview":
            warnings.append(
                "Overwrite policy preview selected. Future implementation must require explicit audited confirmation before any overwrite command."
            )
        elif not target_calendar_exists and payload.overwrite_policy in supported_overwrite_policies:
            warnings.append(
                "Policy preview selected for an empty target calendar; future build would still require audit."
            )

    source_summary: dict[str, object] = {"source_type": payload.source_type}
    source_slot_count: int | None = None
    source_week_count: int | None = None
    source_first_week: int | None = None
    source_last_week: int | None = None
    source_week_span: set[int] = set()
    if payload.source_type != "season_template":
        warnings.append(f"Source type '{payload.source_type}' is planned and not executable yet in this phase.")
    else:
        if not payload.source_template_id:
            errors.append("source_template_id is required when source_type is 'season_template'.")
        else:
            templates_response = template_service.list_templates()
            selected = next((template for template in templates_response.templates if template.template_id == payload.source_template_id), None)
            if selected is None:
                errors.append(f"season_template source '{payload.source_template_id}' was not found.")
            else:
                source_resolved = True
                source_slot_count = len(selected.slots)
                if selected.slots:
                    source_first_week = min(slot.season_week_start for slot in selected.slots)
                    source_last_week = max(slot.season_week_end for slot in selected.slots)
                    for slot in selected.slots:
                        source_week_span.update(range(slot.season_week_start, slot.season_week_end + 1))
                    source_week_count = len(source_week_span)
                else:
                    source_week_count = 0
                source_summary.update({"template_name": selected.name, "slot_count": selected.slot_count, "week_count": selected.week_count})

    week_count_compatible: bool | None = None
    if source_week_count is not None and target_week_count is not None:
        week_count_compatible = source_week_count == target_week_count

    blocking_reasons = list(errors)
    advisory_notes = list(warnings)
    if payload.source_type != "season_template":
        advisory_notes.append("Concrete slot-level source summary is only available for source_type='season_template' in this phase.")

    requires_overwrite_or_merge_policy = bool(target_calendar_exists and not payload.overwrite_policy)

    authoritative_diff_summary = {
        "status": "read_only_preflight",
        "can_build": False,
        "target_calendar_exists": target_calendar_exists,
        "target_event_count": target_event_count,
        "source_type": payload.source_type,
        "source_resolved": source_resolved,
        "source_slot_count": source_slot_count,
        "source_week_count": source_week_count,
        "target_week_count": target_week_count,
        "week_count_compatible": week_count_compatible,
        "source_range": {"first_week": source_first_week, "last_week": source_last_week},
        "target_range": {"first_week": target_first_week, "last_week": target_last_week},
        "structural_comparison": {
            "planned_source_slots": source_slot_count,
            "existing_target_events": target_event_count,
            "target_is_empty": (target_event_count == 0) if target_event_count is not None else None,
            "requires_overwrite_or_merge_policy": requires_overwrite_or_merge_policy,
        },
        "blocking_reasons": blocking_reasons,
        "advisory_notes": advisory_notes,
        "placeholder": "Event-level additions/replacements/conflicts remain planned for a future phase.",
    }

    fingerprint_payload = {
        "target_season_label": normalized_target,
        "source_type": payload.source_type,
        "source_template_id": payload.source_template_id,
        "overwrite_policy": payload.overwrite_policy,
        "target_calendar_exists": target_calendar_exists,
        "target_event_count": target_event_count,
        "source_resolved": source_resolved,
        "source_summary": source_summary,
        "authoritative_diff_summary": authoritative_diff_summary,
        "validation_warnings": warnings,
        "validation_errors": errors,
    }
    canonical_payload = json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":"))
    preflight_fingerprint = f"pf_{hashlib.sha256(canonical_payload.encode('utf-8')).hexdigest()[:16]}"
    reviewed_seed = f"reviewed_diff:{canonical_payload}"
    reviewed_diff_id = f"rd_{hashlib.sha256(reviewed_seed.encode('utf-8')).hexdigest()[:16]}"
    authoritative_diff_summary["preflight_fingerprint"] = preflight_fingerprint
    authoritative_diff_summary["reviewed_diff_id"] = reviewed_diff_id

    audit_preview = {
        "action": "season_builder_preflight",
        "requested_by": payload.requested_by,
        "target_season_label": normalized_target,
        "source_type": payload.source_type,
        "source_template_id": payload.source_template_id,
        "overwrite_policy": payload.overwrite_policy,
        "read_only": True,
        "mutation_permitted": False,
        "preflight_fingerprint": preflight_fingerprint,
        "reviewed_diff_id": reviewed_diff_id,
    }

    return SeasonBuilderPreflightResponse(
        can_build=False,
        target_season_label=normalized_target,
        source_type=payload.source_type,
        source_template_id=payload.source_template_id,
        preflight_fingerprint=preflight_fingerprint,
        reviewed_diff_id=reviewed_diff_id,
        target_calendar_exists=target_calendar_exists,
        target_event_count=target_event_count,
        source_resolved=source_resolved,
        source_summary=source_summary,
        authoritative_diff_summary=authoritative_diff_summary,
        validation_warnings=warnings,
        validation_errors=errors,
        audit_preview=audit_preview,
    )


@router.post("/builder/dry-run-build", response_model=SeasonBuilderDryRunBuildResponse)
def post_season_builder_dry_run_build_contract(
    payload: SeasonBuilderDryRunBuildRequest,
) -> SeasonBuilderDryRunBuildResponse:
    errors: list[str] = []
    warnings: list[str] = []

    if not payload.preflight_fingerprint.strip():
        errors.append(
            "preflight_fingerprint is required for any future dry-run build command."
        )
    if not payload.reviewed_diff_id.strip():
        errors.append("reviewed_diff_id is required for any future dry-run build command.")
    if payload.audit_reason is None or not payload.audit_reason.strip():
        warnings.append(
            "audit_reason will be required before execution is enabled in a future phase."
        )
    if payload.explicit_confirmation is None or not payload.explicit_confirmation.strip():
        warnings.append(
            "explicit_confirmation will be required before execution is enabled in a future phase."
        )
    if payload.mutation_scope is None or not payload.mutation_scope.strip():
        warnings.append(
            "mutation_scope will be required before execution is enabled in a future phase."
        )
    generation_design_preview = {
        "status": "design_preview_only",
        "execution_enabled": False,
        "will_generate_events": False,
        "will_persist_calendar": False,
        "will_mutate_existing_calendar": False,
        "planned_steps": [
            "Validate reviewed preflight identity.",
            "Resolve target season.",
            "Resolve source template or future source.",
            "Compute source event candidates.",
            "Compare candidates with target calendar.",
            "Return additions/replacements/conflicts without persistence.",
            "Require separate audited command before any mutation.",
        ],
        "required_future_inputs": [
            "preflight_fingerprint",
            "reviewed_diff_id",
            "audit_reason",
            "explicit_confirmation",
            "mutation_scope",
        ],
        "planned_output_sections": [
            "candidate_events",
            "structural_summary",
            "conflict_summary",
            "validation_errors",
            "validation_warnings",
            "audit_preview",
        ],
        "blocked_reason": "Dry-run generation is not implemented in this phase.",
    }

    return SeasonBuilderDryRunBuildResponse(
        enabled=False,
        can_execute=False,
        can_mutate=False,
        target_season_label=payload.target_season_label,
        source_type=payload.source_type,
        source_template_id=payload.source_template_id,
        overwrite_policy=payload.overwrite_policy,
        preflight_fingerprint=payload.preflight_fingerprint,
        reviewed_diff_id=payload.reviewed_diff_id,
        validation_errors=errors,
        validation_warnings=warnings,
        audit_preview={
            "action": "season_builder_dry_run_build",
            "read_only": True,
            "mutation_permitted": False,
            "execution_enabled": False,
            "target_season_label": payload.target_season_label,
            "source_type": payload.source_type,
            "source_template_id": payload.source_template_id,
            "overwrite_policy": payload.overwrite_policy,
            "preflight_fingerprint": payload.preflight_fingerprint,
            "reviewed_diff_id": payload.reviewed_diff_id,
            "requested_by": payload.requested_by,
            "audit_reason": payload.audit_reason,
            "explicit_confirmation_present": bool(
                payload.explicit_confirmation and payload.explicit_confirmation.strip()
            ),
            "mutation_scope": payload.mutation_scope,
            "generation_design_preview_available": True,
        },
        generation_design_preview=generation_design_preview,
    )
