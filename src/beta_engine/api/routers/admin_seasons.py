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
from beta_engine.application.season_calendar_service import SeasonCalendarAlreadyExistsError, SeasonCalendarService
from beta_engine.application.season_readiness_service import SeasonReadinessRequest, SeasonReadinessResult, SeasonReadinessService
from beta_engine.application.season_range_preflight_service import SeasonRangePreflightRequest, SeasonRangePreflightResult, SeasonRangePreflightService
from beta_engine.application.season_range_execution_service import RunSeasonRangeRequest, RunSeasonRangeResult, SeasonRangeExecutionService
from beta_engine.application.season_registry_service import SeasonRegistryResponse, SeasonRegistryService
from beta_engine.application.season_template_service import (
    SeasonTemplateSlotConflictCodeRegistryResponse,
    SeasonTemplateSlotConflictReportResponse,
    SeasonTemplatesResponse,
    SeasonTemplateService,
    SeasonTemplateSlotValidationIssueCodeRegistryResponse,
    SeasonTemplateSlotValidationResponse,
    SeasonTemplateValidationIssue,
)
from beta_engine.domain.calendar.season_labels import normalize_season_label, to_long_season_label
from beta_engine.api.season_label_params import normalize_season_for_legacy_services
from beta_engine.domain.tournaments import (
    SeasonBuilderApplyCommandContractRequest,
    SeasonBuilderApplyCommandContractResponse,
    SeasonBuilderApplyCreateOnlyCommandRequest,
    SeasonBuilderApplyCreateOnlyCommandResponse,
    SeasonBuilderApplyCreateOnlyReadinessResponse,
    SeasonBuilderDryRunBuildRequest,
    SeasonBuilderDryRunBuildResponse,
    SeasonBuilderPreflightRequest,
    SeasonBuilderPreflightResponse,
    SeasonTemplateSlotValidationPreview,
    SeasonCalendarBuildRequest,
    SeasonCalendarBuildResult,
    SeasonCalendar,
    SeasonCalendarEvent,
    SeasonCalendarValidationResponse,
    SeasonCalendarValidationIssueCodeRegistryResponse,
)

router = APIRouter(prefix="/admin/seasons", tags=["admin-seasons"])


def _build_deterministic_digest(payload: dict[str, object]) -> str:
    canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


def _format_template_issue(issue: SeasonTemplateValidationIssue) -> str:
    slot = f" [slot={issue.slot_id}]" if issue.slot_id else ""
    return f"[{issue.code}]{slot} {issue.message}"


@router.get("/registry", response_model=SeasonRegistryResponse)
def get_season_registry(service: SeasonRegistryService = Depends(get_season_registry_service)) -> SeasonRegistryResponse:
    return service.build_registry()


@router.get("/templates", response_model=SeasonTemplatesResponse)
def get_season_templates(service: SeasonTemplateService = Depends(get_season_template_service)) -> SeasonTemplatesResponse:
    return service.list_templates()

@router.get(
    "/templates/slot-validation/issue-codes",
    response_model=SeasonTemplateSlotValidationIssueCodeRegistryResponse,
)
def get_template_slot_validation_issue_codes(
    service: SeasonTemplateService = Depends(get_season_template_service),
) -> SeasonTemplateSlotValidationIssueCodeRegistryResponse:
    return service.list_slot_validation_issue_codes()


@router.get("/templates/{template_id}/slot-validation", response_model=SeasonTemplateSlotValidationResponse)
def get_template_slot_validation(
    template_id: str,
    service: SeasonTemplateService = Depends(get_season_template_service),
) -> SeasonTemplateSlotValidationResponse:
    return service.validate_template_by_id(template_id=template_id)


@router.get(
    "/templates/slot-conflicts/codes",
    response_model=SeasonTemplateSlotConflictCodeRegistryResponse,
)
def get_template_slot_conflict_codes(
    service: SeasonTemplateService = Depends(get_season_template_service),
) -> SeasonTemplateSlotConflictCodeRegistryResponse:
    return service.list_slot_conflict_codes()


@router.get("/templates/{template_id}/slot-conflicts", response_model=SeasonTemplateSlotConflictReportResponse)
def get_template_slot_conflicts(
    template_id: str,
    service: SeasonTemplateService = Depends(get_season_template_service),
) -> SeasonTemplateSlotConflictReportResponse:
    return service.analyze_template_slot_conflicts(template_id=template_id)


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


@router.get(
    "/calendar/validation/issue-codes",
    response_model=SeasonCalendarValidationIssueCodeRegistryResponse,
)
def get_season_calendar_validation_issue_codes(
    service: SeasonCalendarService = Depends(get_season_calendar_service),
) -> SeasonCalendarValidationIssueCodeRegistryResponse:
    return service.list_validation_issue_codes()


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


@router.get("/{season:path}/calendar/validation", response_model=SeasonCalendarValidationResponse)
def get_season_calendar_validation(
    season: str,
    service: SeasonCalendarService = Depends(get_season_calendar_service),
) -> SeasonCalendarValidationResponse:
    normalized = normalize_season_for_legacy_services(season)
    return service.validate_persisted_calendar(season=normalized)


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
    template_slot_validation_preview: SeasonTemplateSlotValidationPreview | None = None

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
                template_issues = template_service.validate_template_slots(selected)
                template_slot_validation_preview = template_service.build_slot_validation_preview(
                    issues=template_issues,
                    template_id=selected.template_id,
                    template_exists=True,
                )
                warnings.extend([_format_template_issue(i) for i in template_issues if i.severity == "warning"])
                errors.extend([_format_template_issue(i) for i in template_issues if i.severity == "error"])
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
    preflight_fingerprint = f"pf_{_build_deterministic_digest(fingerprint_payload)[:16]}"
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
        template_slot_validation_preview=template_slot_validation_preview,
        validation_warnings=warnings,
        validation_errors=errors,
        audit_preview=audit_preview,
    )


@router.post("/builder/dry-run-build", response_model=SeasonBuilderDryRunBuildResponse)
def post_season_builder_dry_run_build_contract(
    payload: SeasonBuilderDryRunBuildRequest,
    template_service: SeasonTemplateService = Depends(get_season_template_service),
    calendar_service: SeasonCalendarService = Depends(get_season_calendar_service),
) -> SeasonBuilderDryRunBuildResponse:
    def _dedupe_keep_order(values: list[str]) -> list[str]:
        seen: set[str] = set()
        deduped: list[str] = []
        for value in values:
            normalized = value.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return deduped
    errors: list[str] = []
    warnings: list[str] = []
    template_slot_validation_preview: SeasonTemplateSlotValidationPreview | None = None

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
    candidate_event_contract_preview = {
        "status": "contract_preview_only",
        "will_generate_candidates": False,
        "candidate_count": 0,
        "event_shape": {
            "candidate_id": "string",
            "source_slot_id": "string",
            "season_week_start": "int",
            "season_week_end": "int",
            "event_name": "string",
            "tour_level": "string",
            "category": "string",
            "host_country": "string",
            "region": "string",
            "main_draw_size": "int",
            "qualification_draw_size": "int",
            "point_distribution_ref": "string",
            "prize_money": "int",
            "prestige": "int",
            "duration_in_season_weeks": "int",
            "source_template_id": "string | null",
            "source_type": "string",
            "candidate_status": "planned | conflict | invalid",
            "comparison_classification": "addition | replacement | conflict | invalid",
            "comparison_reason": "string",
            "matched_existing_event_id": "string | null",
            "matched_existing_event_name": "string | null",
            "matched_existing_event_week": "int | null",
            "validation_errors": "string[]",
            "validation_warnings": "string[]",
        },
        "structural_summary_shape": {
            "candidate_count": "int",
            "target_event_count": "int | null",
            "additions_count": "int",
            "replacement_count": "int",
            "conflict_count": "int",
            "invalid_count": "int",
        },
        "conflict_summary_shape": {
            "week_conflicts": "array",
            "slot_conflicts": "array",
            "policy_conflicts": "array",
            "validation_conflicts": "array",
        },
        "blocked_reason": "Candidate event generation is not implemented in this phase.",
    }

    conflict_contract_preview = {
        "status": "contract_preview_only",
        "will_compute_conflicts": False,
        "conflict_count": 0,
        "week_conflict_shape": {
            "conflict_id": "string",
            "conflict_type": "week_overlap",
            "season_week": "int",
            "candidate_id": "string",
            "existing_event_id": "string | null",
            "message": "string",
            "severity": "info | warning | blocking",
        },
        "slot_conflict_shape": {
            "conflict_id": "string",
            "conflict_type": "slot_collision",
            "source_slot_id": "string",
            "candidate_id": "string",
            "existing_event_id": "string | null",
            "message": "string",
            "severity": "info | warning | blocking",
        },
        "policy_conflict_shape": {
            "conflict_id": "string",
            "conflict_type": "policy_violation",
            "policy": "merge_preview | overwrite_preview | create_only_preview | repair_preview",
            "candidate_id": "string | null",
            "message": "string",
            "severity": "info | warning | blocking",
        },
        "validation_conflict_shape": {
            "conflict_id": "string",
            "conflict_type": "validation_error",
            "field": "string",
            "candidate_id": "string | null",
            "message": "string",
            "severity": "warning | blocking",
        },
        "blocked_reason": "Conflict computation is not implemented in this phase.",
    }
    dry_run_result_contract_preview = {
        "status": "contract_preview_only",
        "will_return_real_result": False,
        "candidate_events": [],
        "structural_summary": {
            "candidate_count": 0,
            "target_event_count": None,
            "additions_count": 0,
            "replacement_count": 0,
            "conflict_count": 0,
            "invalid_count": 0,
        },
        "conflict_summary": {
            "week_conflicts": [],
            "slot_conflicts": [],
            "policy_conflicts": [],
            "validation_conflicts": [],
        },
        "result_metadata": {
            "preflight_fingerprint": payload.preflight_fingerprint,
            "reviewed_diff_id": payload.reviewed_diff_id,
            "execution_enabled": False,
            "read_only": True,
            "mutation_permitted": False,
        },
        "blocked_reason": "Dry-run result generation is not implemented in this phase.",
    }
    candidate_events: list[dict[str, object | None]] = []
    normalized_target = payload.target_season_label
    target_calendar_exists = False
    target_events: list[object] = []
    target_event_count = 0
    try:
        normalized_target = to_long_season_label(normalize_season_label(payload.target_season_label))
        calendar_result = calendar_service.get_calendar(season=normalized_target)
        if calendar_result.calendar is not None:
            target_calendar_exists = True
            target_events = list(calendar_result.calendar.events)
            target_event_count = len(target_events)
    except ValueError as exc:
        errors.append(f"Invalid target season label '{payload.target_season_label}': {exc}")

    dry_run_status = "read_only_generated"
    if payload.source_type != "season_template":
        warnings.append("Read-only candidate generation currently supports season_template sources only.")
        dry_run_status = "unsupported_source_type"
    elif not payload.source_template_id:
        errors.append("source_template_id could not be resolved for read-only dry-run candidate generation.")
        dry_run_status = "blocked_unresolved_source"
    else:
        templates_response = template_service.list_templates()
        selected = next((template for template in templates_response.templates if template.template_id == payload.source_template_id), None)
        if selected is None:
            errors.append("source_template_id could not be resolved for read-only dry-run candidate generation.")
            dry_run_status = "blocked_unresolved_source"
        else:
            template_issues = template_service.validate_template_slots(selected)
            template_slot_validation_preview = template_service.build_slot_validation_preview(
                issues=template_issues,
                template_id=selected.template_id,
                template_exists=True,
            )
            warnings.extend([_format_template_issue(i) for i in template_issues if i.severity == "warning"])
            errors.extend([_format_template_issue(i) for i in template_issues if i.severity == "error"])
            templates_config = template_service.template_service.get_config()
            templates_by_id = {template.template_id: template for template in templates_config.templates}
            for index, slot in enumerate(selected.slots, start=1):
                source_slot_id = slot.slot_id or f"slot_{index}"
                week_start = slot.season_week_start
                week_end = slot.season_week_end
                duration = (week_end - week_start + 1) if isinstance(week_start, int) and isinstance(week_end, int) else None
                source_template = templates_by_id.get(slot.source_template_id or "")
                candidate_events.append(
                    {
                        "candidate_id": f"cand_{payload.source_template_id}_{source_slot_id}",
                        "source_slot_id": source_slot_id,
                        "season_week_start": week_start,
                        "season_week_end": week_end,
                        "event_name": slot.tournament_name,
                        "tour_level": source_template.tour_level if source_template else None,
                        "category": slot.category,
                        "host_country": slot.host_country,
                        "region": slot.region,
                        "main_draw_size": source_template.main_draw_size if source_template else None,
                        "qualification_draw_size": source_template.qualification_draw_size if source_template else None,
                        "point_distribution_ref": source_template.point_distribution_ref if source_template else None,
                        "prize_money": source_template.prize_money if source_template else None,
                        "prestige": source_template.prestige if source_template else None,
                        "duration_in_season_weeks": duration,
                        "source_template_id": payload.source_template_id,
                        "source_template_ref": slot.source_template_id,
                        "source_type": payload.source_type,
                        "candidate_status": "planned",
                        "comparison_classification": "addition",
                        "comparison_reason": "Candidate does not match an existing target event and would be an addition in a future dry-run plan.",
                        "matched_existing_event_id": None,
                        "matched_existing_event_name": None,
                        "matched_existing_event_week": None,
                        "validation_errors": [],
                        "validation_warnings": [],
                    }
                )

    week_conflicts: list[dict[str, object | None]] = []
    slot_conflicts: list[dict[str, object | None]] = []
    policy_conflicts: list[dict[str, object | None]] = []
    validation_conflicts: list[dict[str, object | None]] = []
    candidate_ids_with_conflicts: set[str] = set()
    replacement_count = 0
    additions_count = 0
    for candidate in candidate_events:
        candidate_id = str(candidate["candidate_id"])
        candidate_week = candidate.get("season_week_start")
        candidate_name = (candidate.get("event_name") or "").strip().lower()
        candidate_slot = candidate.get("source_slot_id")
        matched_existing = None
        match_reason = None
        week_overlap_existing = None
        slot_overlap_existing = None
        for existing_event in target_events:
            existing_name = (existing_event.event_name or "").strip().lower()
            existing_slot = None
            event_metadata = getattr(existing_event, "metadata", None)
            if isinstance(event_metadata, dict):
                existing_slot = event_metadata.get("source_slot_id")
            same_week = existing_event.season_week == candidate_week
            if same_week and existing_name == candidate_name:
                matched_existing = existing_event
                match_reason = "same_week_event_name"
                break
            if candidate_slot and existing_slot and candidate_slot == existing_slot:
                matched_existing = existing_event
                match_reason = "source_slot_metadata"
                break
            if same_week and week_overlap_existing is None:
                week_overlap_existing = existing_event
            if candidate_slot and existing_slot and candidate_slot == existing_slot and slot_overlap_existing is None:
                slot_overlap_existing = existing_event
        if matched_existing is not None:
            replacement_count += 1
            candidate["matched_existing_event_id"] = matched_existing.event_id
            candidate["matched_existing_event_name"] = matched_existing.event_name
            candidate["matched_existing_event_week"] = matched_existing.season_week
            candidate["_match_reason"] = match_reason
        else:
            additions_count += 1
            candidate["matched_existing_event_id"] = None
            candidate["matched_existing_event_name"] = None
            candidate["matched_existing_event_week"] = None
            candidate["_match_reason"] = None
        if week_overlap_existing is not None and (week_overlap_existing.event_name or "").strip().lower() != candidate_name:
            candidate_ids_with_conflicts.add(candidate_id)
            week_conflicts.append(
                {
                    "conflict_id": f"week_overlap_{candidate_id}_{week_overlap_existing.event_id}",
                    "conflict_type": "week_overlap",
                    "season_week": candidate_week,
                    "candidate_id": candidate_id,
                    "existing_event_id": week_overlap_existing.event_id,
                    "message": f"Candidate week {candidate_week} overlaps existing event '{week_overlap_existing.event_name}'.",
                    "severity": "warning",
                }
            )
        if slot_overlap_existing is not None and (slot_overlap_existing.event_name or "").strip().lower() != candidate_name:
            candidate_ids_with_conflicts.add(candidate_id)
            slot_conflicts.append(
                {
                    "conflict_id": f"slot_collision_{candidate_id}_{slot_overlap_existing.event_id}",
                    "conflict_type": "slot_collision",
                    "source_slot_id": candidate_slot,
                    "candidate_id": candidate_id,
                    "existing_event_id": slot_overlap_existing.event_id,
                    "message": f"Candidate source slot '{candidate_slot}' differs from existing event '{slot_overlap_existing.event_name}'.",
                    "severity": "warning",
                }
            )
        validation_errors = candidate.get("validation_errors") or []
        if isinstance(validation_errors, list) and validation_errors:
            for index, validation_error in enumerate(validation_errors, start=1):
                validation_conflicts.append(
                    {
                        "conflict_id": f"validation_{candidate_id}_{index}",
                        "conflict_type": "validation_error",
                        "field": "candidate",
                        "candidate_id": candidate_id,
                        "message": str(validation_error),
                        "severity": "blocking",
                    }
                )

    if target_calendar_exists and payload.overwrite_policy is None:
        policy_conflicts.append(
            {
                "conflict_id": "policy_violation_missing_overwrite_policy",
                "conflict_type": "policy_violation",
                "policy": None,
                "candidate_id": None,
                "message": "Existing target calendar requires explicit merge/overwrite policy before future mutation.",
                "severity": "blocking",
            }
        )

    for candidate in candidate_events:
        candidate_id = str(candidate["candidate_id"])
        validation_errors = candidate.get("validation_errors") or []
        if isinstance(validation_errors, list) and validation_errors:
            candidate["candidate_status"] = "invalid"
            candidate["comparison_classification"] = "invalid"
            candidate["comparison_reason"] = "Candidate has validation errors."
        elif candidate_id in candidate_ids_with_conflicts:
            candidate["candidate_status"] = "conflict"
            candidate["comparison_classification"] = "conflict"
            candidate["comparison_reason"] = "Candidate has read-only comparison conflicts."
        elif candidate.get("matched_existing_event_id") is not None:
            candidate["comparison_classification"] = "replacement"
            if candidate.get("_match_reason") == "source_slot_metadata":
                candidate["comparison_reason"] = "Candidate matches existing event by source slot metadata."
            else:
                candidate["comparison_reason"] = "Candidate matches existing event by same week and event name."
        else:
            candidate["candidate_status"] = "planned"
            candidate["comparison_classification"] = "addition"
            candidate["comparison_reason"] = "Candidate does not match an existing target event and would be an addition in a future dry-run plan."
        candidate.pop("_match_reason", None)

    dry_run_result_preview = {
        "status": dry_run_status,
        "execution_enabled": False,
        "mutation_permitted": False,
        "candidate_events": candidate_events,
        "structural_summary": {
            "candidate_count": len(candidate_events),
            "target_event_count": target_event_count,
            "additions_count": additions_count,
            "replacement_count": replacement_count,
            "conflict_count": len(week_conflicts) + len(slot_conflicts) + len(policy_conflicts) + len(validation_conflicts),
            "invalid_count": len([candidate for candidate in candidate_events if candidate["validation_errors"]]),
        },
        "conflict_summary": {
            "week_conflicts": week_conflicts,
            "slot_conflicts": slot_conflicts,
            "policy_conflicts": policy_conflicts,
            "validation_conflicts": validation_conflicts,
        },
        "result_metadata": {
            "preflight_fingerprint": payload.preflight_fingerprint,
            "reviewed_diff_id": payload.reviewed_diff_id,
            "source_type": payload.source_type,
            "source_template_id": payload.source_template_id,
            "overwrite_policy": payload.overwrite_policy,
            "target_calendar_exists": target_calendar_exists,
            "target_event_count": target_event_count,
            "comparison_performed": dry_run_status == "read_only_generated",
            "read_only": True,
            "mutation_permitted": False,
        },
    }
    blocking_count = 0
    warning_count = 0
    info_count = 0
    blocking_reasons: list[str] = []
    warning_reasons: list[str] = []
    info_messages: list[str] = []
    for conflict_group in (week_conflicts, slot_conflicts, policy_conflicts, validation_conflicts):
        for conflict in conflict_group:
            severity = str(conflict.get("severity") or "").strip().lower()
            message = str(conflict.get("message") or "").strip()
            if severity == "blocking":
                blocking_count += 1
                if message:
                    blocking_reasons.append(message)
            elif severity == "warning":
                warning_count += 1
                if message:
                    warning_reasons.append(message)
            elif severity == "info":
                info_count += 1
                if message:
                    info_messages.append(message)

    blocking_reasons.extend(errors)
    warning_reasons.extend(warnings)
    blocking_reasons = _dedupe_keep_order(blocking_reasons)
    warning_reasons = _dedupe_keep_order(warning_reasons)
    info_messages = _dedupe_keep_order(info_messages)

    candidate_status_counts = {"planned": 0, "replacement": 0, "conflict": 0, "invalid": 0}
    for candidate in candidate_events:
        status_value = str(candidate.get("candidate_status") or "").strip().lower()
        classification = str(candidate.get("comparison_classification") or "").strip().lower()
        effective_status = "replacement" if classification == "replacement" else status_value
        if effective_status in candidate_status_counts:
            candidate_status_counts[effective_status] += 1

    conflict_type_counts = {
        "week_conflicts": len(week_conflicts),
        "slot_conflicts": len(slot_conflicts),
        "policy_conflicts": len(policy_conflicts),
        "validation_conflicts": len(validation_conflicts),
    }
    if blocking_count > 0 or len(errors) > 0:
        validation_status = "blocking"
    elif warning_count > 0 or len(warnings) > 0:
        validation_status = "warnings"
    else:
        validation_status = "clean"

    validation_summary = {
        "status": validation_status,
        "blocking_count": blocking_count,
        "warning_count": warning_count,
        "info_count": info_count,
        "blocking_reasons": blocking_reasons,
        "warning_reasons": warning_reasons,
        "info_messages": info_messages,
        "candidate_status_counts": candidate_status_counts,
        "conflict_type_counts": conflict_type_counts,
    }
    plan_readiness = {
        "read_only_plan_available": dry_run_status == "read_only_generated",
        "has_blocking_issues": validation_status == "blocking",
        "has_warnings": validation_status == "warnings" or warning_count > 0,
        "mutation_still_disabled": True,
        "next_required_step": "Review dry-run summary; execution remains disabled.",
    }
    dry_run_result_preview["validation_summary"] = validation_summary
    dry_run_result_preview["plan_readiness"] = plan_readiness
    dry_run_identity_payload = {
        "target_season_label": normalized_target,
        "source_type": payload.source_type,
        "source_template_id": payload.source_template_id,
        "overwrite_policy": payload.overwrite_policy,
        "preflight_fingerprint": payload.preflight_fingerprint,
        "reviewed_diff_id": payload.reviewed_diff_id,
        "candidate_events": candidate_events,
        "structural_summary": dry_run_result_preview["structural_summary"],
        "conflict_summary": dry_run_result_preview["conflict_summary"],
        "validation_summary": dry_run_result_preview["validation_summary"],
        "plan_readiness": dry_run_result_preview["plan_readiness"],
        "result_metadata": dry_run_result_preview["result_metadata"],
    }
    dry_run_result_fingerprint = f"drf_{_build_deterministic_digest({'kind': 'dry_run_result_fingerprint', 'payload': dry_run_identity_payload})[:16]}"
    dry_run_result_id = f"drr_{_build_deterministic_digest({'kind': 'dry_run_result_id', 'payload': dry_run_identity_payload})[:16]}"
    dry_run_result_preview["dry_run_result_fingerprint"] = dry_run_result_fingerprint
    dry_run_result_preview["dry_run_result_id"] = dry_run_result_id
    dry_run_result_preview_result_metadata = dry_run_result_preview.get("result_metadata")
    if isinstance(dry_run_result_preview_result_metadata, dict):
        dry_run_result_preview_result_metadata["dry_run_result_fingerprint"] = dry_run_result_fingerprint
        dry_run_result_preview_result_metadata["dry_run_result_id"] = dry_run_result_id

    validation_summary_status = str(validation_summary.get("status") or "unknown").strip()
    has_preflight_fingerprint = bool(payload.preflight_fingerprint and payload.preflight_fingerprint.strip())
    has_reviewed_diff_id = bool(payload.reviewed_diff_id and payload.reviewed_diff_id.strip())
    has_dry_run_result_fingerprint = isinstance(dry_run_result_fingerprint, str) and dry_run_result_fingerprint.startswith("drf_")
    has_dry_run_result_id = isinstance(dry_run_result_id, str) and dry_run_result_id.startswith("drr_")
    plan_available = bool(plan_readiness.get("read_only_plan_available"))

    identity_items: list[dict[str, str]] = [
        {
            "area": "preflight_fingerprint",
            "status": "OK" if has_preflight_fingerprint else "Missing",
            "message": "Preflight fingerprint is present." if has_preflight_fingerprint else "Preflight fingerprint is missing.",
        },
        {
            "area": "reviewed_diff_id",
            "status": "OK" if has_reviewed_diff_id else "Missing",
            "message": "Reviewed diff id is present." if has_reviewed_diff_id else "Reviewed diff id is missing.",
        },
        {
            "area": "dry_run_result_fingerprint",
            "status": "OK" if has_dry_run_result_fingerprint else "Missing",
            "message": "Dry-run result fingerprint is present." if has_dry_run_result_fingerprint else "Dry-run result fingerprint is missing or invalid.",
        },
        {
            "area": "dry_run_result_id",
            "status": "OK" if has_dry_run_result_id else "Missing",
            "message": "Dry-run result id is present." if has_dry_run_result_id else "Dry-run result id is missing or invalid.",
        },
        {
            "area": "validation_summary",
            "status": "Blocked" if validation_summary_status == "blocking" else ("Info" if validation_summary_status == "warnings" else "OK"),
            "message": f"Validation summary status is '{validation_summary_status}'.",
        },
        {
            "area": "plan_readiness",
            "status": "OK" if plan_available else "Blocked",
            "message": "Read-only plan is available." if plan_available else "Read-only plan is not available.",
        },
        {
            "area": "mutation_state",
            "status": "Blocked",
            "message": "Mutation remains disabled; this checklist is reference-only.",
        },
    ]

    missing_identity = not all(
        [has_preflight_fingerprint, has_reviewed_diff_id, has_dry_run_result_fingerprint, has_dry_run_result_id]
    )
    blocked_reference = validation_summary_status == "blocking" or not plan_available
    identity_status = "missing_identity" if missing_identity else ("blocked_reference" if blocked_reference else "ready_reference")
    dry_run_result_preview["identity_readiness"] = {
        "status": identity_status,
        "items": identity_items,
        "future_command_reference": {
            "preflight_fingerprint": payload.preflight_fingerprint,
            "reviewed_diff_id": payload.reviewed_diff_id,
            "dry_run_result_fingerprint": dry_run_result_fingerprint,
            "dry_run_result_id": dry_run_result_id,
            "can_reference_future_command": identity_status == "ready_reference",
            "mutation_still_disabled": True,
        },
    }

    return SeasonBuilderDryRunBuildResponse(
        enabled=False,
        can_execute=False,
        can_mutate=False,
        target_season_label=normalized_target,
        source_type=payload.source_type,
        source_template_id=payload.source_template_id,
        overwrite_policy=payload.overwrite_policy,
        preflight_fingerprint=payload.preflight_fingerprint,
        reviewed_diff_id=payload.reviewed_diff_id,
        template_slot_validation_preview=template_slot_validation_preview,
        validation_errors=errors,
        validation_warnings=warnings,
        audit_preview={
            "action": "season_builder_dry_run_build",
            "read_only": True,
            "mutation_permitted": False,
            "execution_enabled": False,
            "target_season_label": normalized_target,
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
            "candidate_event_contract_preview_available": True,
            "conflict_contract_preview_available": True,
            "dry_run_result_contract_preview_available": True,
            "dry_run_result_preview_available": True,
            "dry_run_result_identity_available": True,
        },
        generation_design_preview=generation_design_preview,
        candidate_event_contract_preview=candidate_event_contract_preview,
        conflict_contract_preview=conflict_contract_preview,
        dry_run_result_contract_preview=dry_run_result_contract_preview,
        dry_run_result_preview=dry_run_result_preview,
    )




@router.post("/builder/apply-create-only-command", response_model=SeasonBuilderApplyCreateOnlyCommandResponse)
def post_season_builder_apply_create_only_command(
    payload: SeasonBuilderApplyCreateOnlyCommandRequest,
    template_service: SeasonTemplateService = Depends(get_season_template_service),
    calendar_service: SeasonCalendarService = Depends(get_season_calendar_service),
) -> SeasonBuilderApplyCreateOnlyCommandResponse:
    errors: list[str] = []
    warnings: list[str] = []
    apply_gate_summary: dict[str, bool] = {
        "source_type_valid": False,
        "target_absent_before_apply": False,
        "identity_fields_present": False,
        "audit_metadata_present": False,
        "explicit_confirmation_valid": False,
        "mutation_scope_valid": False,
        "dry_run_identity_matched": False,
        "dry_run_validation_clean": False,
        "candidate_events_non_empty": False,
        "service_insert_succeeded": False,
    }
    normalized_target = payload.target_season_label
    try:
        normalized_target = to_long_season_label(normalize_season_label(payload.target_season_label))
    except ValueError as exc:
        errors.append(f"Invalid target season label '{payload.target_season_label}': {exc}")

    if payload.source_type != "season_template":
        errors.append("source_type must be 'season_template'.")
    else:
        apply_gate_summary["source_type_valid"] = True
    if not payload.source_template_id:
        errors.append("source_template_id is required when source_type is 'season_template'.")

    if payload.mutation_scope != "create_only":
        errors.append("mutation_scope must be exactly 'create_only' for this command.")
    else:
        apply_gate_summary["mutation_scope_valid"] = True
    if payload.overwrite_policy not in (None, "create_only"):
        errors.append("overwrite_policy must be null or 'create_only' for create-only apply.")
    if payload.explicit_confirmation != "I understand this will create a new season calendar.":
        errors.append("explicit_confirmation must exactly match the required confirmation text.")
    else:
        apply_gate_summary["explicit_confirmation_valid"] = True

    if not payload.preflight_fingerprint.strip():
        errors.append("preflight_fingerprint is required.")
    if not payload.reviewed_diff_id.strip():
        errors.append("reviewed_diff_id is required.")
    if not payload.dry_run_result_fingerprint.strip():
        errors.append("dry_run_result_fingerprint is required.")
    if not payload.dry_run_result_id.strip():
        errors.append("dry_run_result_id is required.")
    if not payload.requested_by.strip():
        errors.append("requested_by is required.")
    if not payload.audit_reason.strip():
        errors.append("audit_reason is required.")
    if payload.requested_by.strip() and payload.audit_reason.strip():
        apply_gate_summary["audit_metadata_present"] = True
    if (
        payload.preflight_fingerprint.strip()
        and payload.reviewed_diff_id.strip()
        and payload.dry_run_result_fingerprint.strip()
        and payload.dry_run_result_id.strip()
    ):
        apply_gate_summary["identity_fields_present"] = True

    calendar_result = calendar_service.get_calendar(season=normalized_target) if not errors else None
    if calendar_result and calendar_result.calendar is not None:
        errors.append("Target season calendar already exists; create-only apply cannot modify existing calendars.")
    elif calendar_result and calendar_result.calendar is None:
        apply_gate_summary["target_absent_before_apply"] = True

    dry_run_identity: dict[str, object] = {}
    candidate_events: list[dict[str, object]] = []
    if not errors:
        dry_run_response = post_season_builder_dry_run_build_contract(
            SeasonBuilderDryRunBuildRequest(
                target_season_label=normalized_target,
                source_type=payload.source_type,
                source_template_id=payload.source_template_id,
                overwrite_policy=payload.overwrite_policy,
                preflight_fingerprint=payload.preflight_fingerprint,
                reviewed_diff_id=payload.reviewed_diff_id,
                requested_by=payload.requested_by,
                audit_reason=payload.audit_reason,
                explicit_confirmation=payload.explicit_confirmation,
                mutation_scope=payload.mutation_scope,
            ),
            template_service=template_service,
            calendar_service=calendar_service,
        )
        dry_run_preview = dry_run_response.dry_run_result_preview
        recomputed_fingerprint = str(dry_run_preview.get("dry_run_result_fingerprint") or "")
        recomputed_id = str(dry_run_preview.get("dry_run_result_id") or "")
        dry_run_identity = {
            "preflight_fingerprint": payload.preflight_fingerprint,
            "reviewed_diff_id": payload.reviewed_diff_id,
            "requested_dry_run_result_fingerprint": payload.dry_run_result_fingerprint,
            "requested_dry_run_result_id": payload.dry_run_result_id,
            "recomputed_dry_run_result_fingerprint": recomputed_fingerprint,
            "recomputed_dry_run_result_id": recomputed_id,
            "identity_matches": recomputed_fingerprint == payload.dry_run_result_fingerprint and recomputed_id == payload.dry_run_result_id,
        }
        if recomputed_fingerprint != payload.dry_run_result_fingerprint or recomputed_id != payload.dry_run_result_id:
            errors.append("Dry-run identity mismatch: recomputed result fingerprint/id does not match request.")
        else:
            apply_gate_summary["dry_run_identity_matched"] = True
        validation_status = str((dry_run_preview.get("validation_summary") or {}).get("status") or "")
        if validation_status != "clean":
            errors.append("Recomputed dry-run validation summary must be 'clean'.")
        else:
            apply_gate_summary["dry_run_validation_clean"] = True
        candidate_events = list(dry_run_preview.get("candidate_events") or [])
        if not candidate_events:
            errors.append("Recomputed dry-run candidate_events must be non-empty.")
        else:
            apply_gate_summary["candidate_events_non_empty"] = True

    audit_preview = {
        "action": "season_builder_apply_create_only",
        "requested_by": payload.requested_by,
        "audit_reason": payload.audit_reason,
        "mutation_scope": payload.mutation_scope,
        "read_only": False,
        "explicit_confirmation_present": bool(payload.explicit_confirmation.strip()),
        "dry_run_result_fingerprint": payload.dry_run_result_fingerprint,
        "dry_run_result_id": payload.dry_run_result_id,
        "applied_event_count": 0,
        "audit_persisted": False,
        "audit_persistence_status": "not_implemented",
    }
    if errors:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT if any("already exists" in e for e in errors) else status.HTTP_400_BAD_REQUEST, detail=SeasonBuilderApplyCreateOnlyCommandResponse(
            enabled=True, can_execute=False, can_mutate=False, applied=False, target_season_label=normalized_target,
            validation_errors=errors, validation_warnings=warnings, dry_run_identity=dry_run_identity, audit_preview=audit_preview,
            apply_gate_summary=apply_gate_summary,
            message="Create-only apply rejected; no mutation performed.",
        ).model_dump())

    persisted_events = []
    for idx, candidate in enumerate(candidate_events, start=1):
        week = int(candidate.get("season_week_start") or 1)
        persisted_events.append(SeasonCalendarEvent(
            event_id=f"EVT-{normalized_target.replace('/', '-')}-W{week:02d}-{idx:03d}",
            season=normalized_target,
            season_week=week,
            calendar_year=None,
            year_week=week,
            template_id=str(candidate.get("source_template_ref") or candidate.get("source_template_id") or payload.source_template_id),
            event_name=str(candidate.get("event_name") or ""),
            category=str(candidate.get("category") or ""),
            tour_level=candidate.get("tour_level"),
            host_country=str(candidate.get("host_country") or "UNK")[:3].upper(),
            region=str(candidate.get("region") or "UNKNOWN"),
            duration_in_season_weeks=int(candidate.get("duration_in_season_weeks") or 1),
            end_season_week=int(candidate.get("season_week_end") or week),
            main_draw_size=max(1, int(candidate.get("main_draw_size") or 1)),
            qualification_draw_size=int(candidate.get("qualification_draw_size") or 0),
            point_distribution_ref=candidate.get("point_distribution_ref"),
            prize_money=int(candidate.get("prize_money") or 0),
            prestige=float(candidate.get("prestige") or 0.0),
            event_level_overrides={"source_slot_id": str(candidate.get("source_slot_id") or "")},
        ))

    created = SeasonCalendar(season=normalized_target, events=persisted_events)
    try:
        calendar_service.create_calendar_if_absent(season=normalized_target, calendar=created)
        apply_gate_summary["service_insert_succeeded"] = True
    except SeasonCalendarAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=SeasonBuilderApplyCreateOnlyCommandResponse(
            enabled=True, can_execute=False, can_mutate=False, applied=False, target_season_label=normalized_target,
            validation_errors=["Target season calendar already exists; create-only apply cannot modify existing calendars."],
            validation_warnings=warnings, dry_run_identity=dry_run_identity, audit_preview=audit_preview,
            apply_gate_summary=apply_gate_summary,
            message="Create-only apply rejected; no mutation performed.",
        ).model_dump())

    audit_preview["applied_event_count"] = len(persisted_events)
    created_event_preview = [
        {
            "event_id": event.event_id,
            "event_name": event.event_name,
            "season_week": event.season_week,
            "end_season_week": event.end_season_week,
            "category": event.category,
            "tour_level": event.tour_level,
            "host_country": event.host_country,
            "main_draw_size": event.main_draw_size,
        }
        for event in persisted_events[:3]
    ]
    weeks = [event.season_week for event in persisted_events]
    categories = sorted({str(event.category) for event in persisted_events if str(event.category)})
    tour_levels = sorted({str(event.tour_level) for event in persisted_events if event.tour_level is not None})
    event_ids_fingerprint = _build_deterministic_digest(
        {"season": normalized_target, "event_ids": [event.event_id for event in persisted_events]}
    )
    created_calendar_identity = {
        "target_season_label": normalized_target,
        "source_type": payload.source_type,
        "source_template_id": payload.source_template_id,
        "dry_run_result_fingerprint": payload.dry_run_result_fingerprint,
        "dry_run_result_id": payload.dry_run_result_id,
        "applied_event_count": len(persisted_events),
        "created_calendar_event_ids_fingerprint": f"evt_{event_ids_fingerprint[:16]}",
    }
    persisted_validation = calendar_service.validate_persisted_calendar(season=normalized_target)
    validation_summary = persisted_validation.validation_summary
    issue_codes_first_10 = [issue.code for issue in persisted_validation.issues[:10]]
    created_calendar_validation_preview = {
        "validation_status": validation_summary.status,
        "error_count": validation_summary.error_count,
        "warning_count": validation_summary.warning_count,
        "info_count": validation_summary.info_count,
        "event_count": validation_summary.event_count,
        "calendar_exists": persisted_validation.calendar_exists,
        "read_only": persisted_validation.read_only,
        "first_season_week": validation_summary.first_season_week,
        "last_season_week": validation_summary.last_season_week,
        "categories": validation_summary.categories,
        "tour_levels": validation_summary.tour_levels,
        "host_countries": validation_summary.host_countries,
        "issue_codes_first_10": issue_codes_first_10,
        "message": persisted_validation.message,
    }

    return SeasonBuilderApplyCreateOnlyCommandResponse(
        enabled=True, can_execute=True, can_mutate=True, applied=True, target_season_label=normalized_target,
        created_calendar_summary={
            "calendar_exists": True,
            "season": normalized_target,
            "event_count": len(persisted_events),
            "first_season_week": min(weeks) if weeks else None,
            "last_season_week": max(weeks) if weeks else None,
            "categories": {"count": len(categories), "values": categories},
            "tour_levels": {"count": len(tour_levels), "values": tour_levels},
        },
        created_event_preview=created_event_preview,
        created_calendar_identity=created_calendar_identity,
        created_calendar_validation_preview=created_calendar_validation_preview,
        apply_gate_summary=apply_gate_summary,
        applied_event_count=len(persisted_events), dry_run_identity=dry_run_identity, audit_preview=audit_preview,
        message="Create-only apply executed successfully.",
    )


@router.post("/builder/apply-create-only-readiness", response_model=SeasonBuilderApplyCreateOnlyReadinessResponse)
def post_season_builder_apply_create_only_readiness(
    payload: SeasonBuilderApplyCreateOnlyCommandRequest,
    template_service: SeasonTemplateService = Depends(get_season_template_service),
    calendar_service: SeasonCalendarService = Depends(get_season_calendar_service),
) -> SeasonBuilderApplyCreateOnlyReadinessResponse:
    errors: list[str] = []
    warnings: list[str] = []
    apply_gate_summary: dict[str, bool] = {
        "source_type_valid": False,
        "target_absent_before_apply": False,
        "identity_fields_present": False,
        "audit_metadata_present": False,
        "explicit_confirmation_valid": False,
        "mutation_scope_valid": False,
        "dry_run_identity_matched": False,
        "dry_run_validation_clean": False,
        "candidate_events_non_empty": False,
        "service_insert_applicable": False,
    }
    normalized_target = payload.target_season_label
    try:
        normalized_target = to_long_season_label(normalize_season_label(payload.target_season_label))
    except ValueError as exc:
        errors.append(f"Invalid target season label '{payload.target_season_label}': {exc}")

    if payload.source_type != "season_template":
        errors.append("source_type must be 'season_template'.")
    else:
        apply_gate_summary["source_type_valid"] = True
    if not payload.source_template_id:
        errors.append("source_template_id is required when source_type is 'season_template'.")

    if payload.mutation_scope != "create_only":
        errors.append("mutation_scope must be exactly 'create_only' for this command.")
    else:
        apply_gate_summary["mutation_scope_valid"] = True
    if payload.overwrite_policy not in (None, "create_only"):
        errors.append("overwrite_policy must be null or 'create_only' for create-only apply.")
    if payload.explicit_confirmation != "I understand this will create a new season calendar.":
        errors.append("explicit_confirmation must exactly match the required confirmation text.")
    else:
        apply_gate_summary["explicit_confirmation_valid"] = True

    if not payload.preflight_fingerprint.strip():
        errors.append("preflight_fingerprint is required.")
    if not payload.reviewed_diff_id.strip():
        errors.append("reviewed_diff_id is required.")
    if not payload.dry_run_result_fingerprint.strip():
        errors.append("dry_run_result_fingerprint is required.")
    if not payload.dry_run_result_id.strip():
        errors.append("dry_run_result_id is required.")
    if not payload.requested_by.strip():
        errors.append("requested_by is required.")
    if not payload.audit_reason.strip():
        errors.append("audit_reason is required.")
    if payload.requested_by.strip() and payload.audit_reason.strip():
        apply_gate_summary["audit_metadata_present"] = True
    if (
        payload.preflight_fingerprint.strip()
        and payload.reviewed_diff_id.strip()
        and payload.dry_run_result_fingerprint.strip()
        and payload.dry_run_result_id.strip()
    ):
        apply_gate_summary["identity_fields_present"] = True

    calendar_result = calendar_service.get_calendar(season=normalized_target) if not errors else None
    if calendar_result and calendar_result.calendar is not None:
        errors.append("Target season calendar already exists; create-only apply cannot modify existing calendars.")
    elif calendar_result and calendar_result.calendar is None:
        apply_gate_summary["target_absent_before_apply"] = True

    dry_run_identity: dict[str, object] = {}
    candidate_events: list[dict[str, object]] = []
    if not errors:
        dry_run_response = post_season_builder_dry_run_build_contract(
            SeasonBuilderDryRunBuildRequest(
                target_season_label=normalized_target,
                source_type=payload.source_type,
                source_template_id=payload.source_template_id,
                overwrite_policy=payload.overwrite_policy,
                preflight_fingerprint=payload.preflight_fingerprint,
                reviewed_diff_id=payload.reviewed_diff_id,
                requested_by=payload.requested_by,
                audit_reason=payload.audit_reason,
                explicit_confirmation=payload.explicit_confirmation,
                mutation_scope=payload.mutation_scope,
            ),
            template_service=template_service,
            calendar_service=calendar_service,
        )
        dry_run_preview = dry_run_response.dry_run_result_preview
        recomputed_fingerprint = str(dry_run_preview.get("dry_run_result_fingerprint") or "")
        recomputed_id = str(dry_run_preview.get("dry_run_result_id") or "")
        dry_run_identity = {
            "preflight_fingerprint": payload.preflight_fingerprint,
            "reviewed_diff_id": payload.reviewed_diff_id,
            "requested_dry_run_result_fingerprint": payload.dry_run_result_fingerprint,
            "requested_dry_run_result_id": payload.dry_run_result_id,
            "recomputed_dry_run_result_fingerprint": recomputed_fingerprint,
            "recomputed_dry_run_result_id": recomputed_id,
            "identity_matches": recomputed_fingerprint == payload.dry_run_result_fingerprint and recomputed_id == payload.dry_run_result_id,
        }
        if recomputed_fingerprint != payload.dry_run_result_fingerprint or recomputed_id != payload.dry_run_result_id:
            errors.append("Dry-run identity mismatch: recomputed result fingerprint/id does not match request.")
        else:
            apply_gate_summary["dry_run_identity_matched"] = True
        validation_status = str((dry_run_preview.get("validation_summary") or {}).get("status") or "")
        if validation_status != "clean":
            errors.append("Recomputed dry-run validation summary must be 'clean'.")
        else:
            apply_gate_summary["dry_run_validation_clean"] = True
        candidate_events = list(dry_run_preview.get("candidate_events") or [])
        if not candidate_events:
            errors.append("Recomputed dry-run candidate_events must be non-empty.")
        else:
            apply_gate_summary["candidate_events_non_empty"] = True

    candidate_weeks = [int(c.get("season_week_start") or 1) for c in candidate_events]
    categories = sorted({str(c.get("category")) for c in candidate_events if c.get("category")})
    tour_levels = sorted({str(c.get("tour_level")) for c in candidate_events if c.get("tour_level") is not None})
    candidate_summary = {
        "candidate_count": len(candidate_events),
        "first_season_week": min(candidate_weeks) if candidate_weeks else None,
        "last_season_week": max(candidate_weeks) if candidate_weeks else None,
        "categories": {"count": len(categories), "values": categories},
        "tour_levels": {"count": len(tour_levels), "values": tour_levels},
        "first_candidate_preview": candidate_events[:3],
    }
    can_execute_apply = not errors
    would_create_calendar = can_execute_apply and apply_gate_summary["target_absent_before_apply"]
    audit_preview = {
        "action": "season_builder_apply_create_only_readiness",
        "requested_by": payload.requested_by,
        "audit_reason": payload.audit_reason,
        "mutation_scope": payload.mutation_scope,
        "read_only": True,
        "can_mutate": False,
        "explicit_confirmation_present": bool(payload.explicit_confirmation.strip()),
        "dry_run_result_fingerprint": payload.dry_run_result_fingerprint,
        "dry_run_result_id": payload.dry_run_result_id,
        "audit_persisted": False,
        "audit_persistence_status": "not_implemented",
    }
    return SeasonBuilderApplyCreateOnlyReadinessResponse(
        can_execute_apply=can_execute_apply,
        can_mutate=False,
        would_create_calendar=would_create_calendar,
        service_insert_applicable=False,
        target_season_label=normalized_target,
        validation_errors=errors,
        validation_warnings=warnings,
        apply_gate_summary=apply_gate_summary,
        dry_run_identity=dry_run_identity,
        candidate_summary=candidate_summary,
        audit_preview=audit_preview,
        message="Create-only apply readiness evaluated; no mutation performed.",
    )
@router.post("/builder/apply-command-contract", response_model=SeasonBuilderApplyCommandContractResponse)
def post_season_builder_apply_command_contract(
    payload: SeasonBuilderApplyCommandContractRequest,
) -> SeasonBuilderApplyCommandContractResponse:
    errors: list[str] = []
    warnings: list[str] = []

    if not payload.preflight_fingerprint.strip():
        errors.append("preflight_fingerprint is required before any future apply command.")
    if not payload.reviewed_diff_id.strip():
        errors.append("reviewed_diff_id is required before any future apply command.")
    if not payload.dry_run_result_fingerprint.strip():
        errors.append("dry_run_result_fingerprint is required before any future apply command.")
    if not payload.dry_run_result_id.strip():
        errors.append("dry_run_result_id is required before any future apply command.")

    has_audit_reason = bool(payload.audit_reason and payload.audit_reason.strip())
    has_explicit_confirmation = bool(payload.explicit_confirmation and payload.explicit_confirmation.strip())
    has_mutation_scope = bool(payload.mutation_scope and payload.mutation_scope.strip())
    if not has_audit_reason:
        warnings.append("audit_reason will be required before apply execution is enabled in a future phase.")
    if not has_explicit_confirmation:
        warnings.append("explicit_confirmation will be required before apply execution is enabled in a future phase.")
    if not has_mutation_scope:
        warnings.append("mutation_scope will be required before apply execution is enabled in a future phase.")

    normalized_target = payload.target_season_label
    try:
        normalized_target = to_long_season_label(normalize_season_label(payload.target_season_label))
    except ValueError:
        normalized_target = payload.target_season_label

    required_identity = {
        "preflight_fingerprint": payload.preflight_fingerprint,
        "reviewed_diff_id": payload.reviewed_diff_id,
        "dry_run_result_fingerprint": payload.dry_run_result_fingerprint,
        "dry_run_result_id": payload.dry_run_result_id,
        "all_identity_fields_present": len(errors) == 0,
    }
    required_audit_metadata = {
        "requested_by": payload.requested_by,
        "audit_reason_present": has_audit_reason,
        "explicit_confirmation_present": has_explicit_confirmation,
        "mutation_scope": payload.mutation_scope,
        "all_audit_metadata_present": has_audit_reason and has_explicit_confirmation and has_mutation_scope,
    }
    audit_preview = {
        "action": "season_builder_apply_command",
        "read_only": True,
        "mutation_permitted": False,
        "execution_enabled": False,
        "target_season_label": normalized_target,
        "source_type": payload.source_type,
        "source_template_id": payload.source_template_id,
        "overwrite_policy": payload.overwrite_policy,
        "preflight_fingerprint": payload.preflight_fingerprint,
        "reviewed_diff_id": payload.reviewed_diff_id,
        "dry_run_result_fingerprint": payload.dry_run_result_fingerprint,
        "dry_run_result_id": payload.dry_run_result_id,
        "requested_by": payload.requested_by,
        "audit_reason": payload.audit_reason,
        "explicit_confirmation_present": has_explicit_confirmation,
        "mutation_scope": payload.mutation_scope,
        "audit_trail_contract_preview_available": True,
        "safety_gate_contract_preview_available": True,
    }
    audit_trail_contract_preview = {
        "status": "contract_preview_only",
        "will_persist_audit": False,
        "audit_event_type": "season_builder_apply_command",
        "required_identity_fields": [
            "preflight_fingerprint",
            "reviewed_diff_id",
            "dry_run_result_fingerprint",
            "dry_run_result_id",
        ],
        "required_actor_fields": [
            "requested_by",
            "audit_reason",
            "explicit_confirmation",
            "mutation_scope",
        ],
        "audit_record_shape": {
            "audit_id": "string",
            "timestamp_utc": "datetime",
            "action": "season_builder_apply_command",
            "target_season_label": "string",
            "source_type": "string",
            "source_template_id": "string | null",
            "overwrite_policy": "string | null",
            "preflight_fingerprint": "string",
            "reviewed_diff_id": "string",
            "dry_run_result_fingerprint": "string",
            "dry_run_result_id": "string",
            "requested_by": "string | null",
            "audit_reason": "string | null",
            "explicit_confirmation_present": "bool",
            "mutation_scope": "string | null",
            "execution_enabled": "bool",
            "mutation_permitted": "bool",
            "result": "disabled | executed | rejected",
        },
        "blocked_reason": "Audit trail persistence is not implemented in this phase.",
    }
    safety_gate_contract_preview = {
        "status": "contract_preview_only",
        "will_execute_apply": False,
        "will_mutate_calendar": False,
        "gate_result": "blocked_disabled_phase",
        "required_gates": [
            {
                "gate": "identity",
                "required": True,
                "currently_satisfied": required_identity["all_identity_fields_present"],
                "message": "Preflight, reviewed diff, and dry-run result identities must be present.",
            },
            {
                "gate": "audit_metadata",
                "required": True,
                "currently_satisfied": required_audit_metadata["all_audit_metadata_present"],
                "message": "Audit reason, explicit confirmation, and mutation scope must be present.",
            },
            {
                "gate": "execution_enabled",
                "required": True,
                "currently_satisfied": False,
                "message": "Execution is disabled in this phase.",
            },
            {
                "gate": "mutation_permission",
                "required": True,
                "currently_satisfied": False,
                "message": "Mutation permission is disabled in this phase.",
            },
            {
                "gate": "audit_trail",
                "required": True,
                "currently_satisfied": False,
                "message": "Audit trail persistence is not implemented in this phase.",
            },
        ],
        "future_allowed_mutation_scopes": [
            "create_only_preview",
            "merge_preview",
            "overwrite_preview",
            "repair_preview",
        ],
        "blocked_reason": "Final apply safety gate is contract-only and disabled in this phase.",
    }
    return SeasonBuilderApplyCommandContractResponse(
        enabled=False,
        can_execute=False,
        can_mutate=False,
        target_season_label=normalized_target,
        source_type=payload.source_type,
        source_template_id=payload.source_template_id,
        overwrite_policy=payload.overwrite_policy,
        validation_errors=errors,
        validation_warnings=warnings,
        audit_preview=audit_preview,
        audit_trail_contract_preview=audit_trail_contract_preview,
        safety_gate_contract_preview=safety_gate_contract_preview,
        required_identity=required_identity,
        required_audit_metadata=required_audit_metadata,
    )
