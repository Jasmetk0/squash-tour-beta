from __future__ import annotations

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
from beta_engine.domain.tournaments import SeasonBuilderPreflightRequest, SeasonBuilderPreflightResponse, SeasonCalendarBuildRequest, SeasonCalendarBuildResult

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
    warnings: list[str] = []
    errors: list[str] = []
    source_resolved = False
    target_calendar_exists: bool | None = None
    target_event_count: int | None = None
    normalized_target: str = payload.target_season_label

    try:
        normalized_target = to_long_season_label(normalize_season_label(payload.target_season_label))
    except ValueError as exc:
        errors.append(f"Invalid target season label '{payload.target_season_label}': {exc}")

    if not errors:
        calendar_result = calendar_service.get_calendar(season=normalized_target)
        target_calendar_exists = calendar_result.calendar is not None
        target_event_count = len(calendar_result.calendar.events) if calendar_result.calendar else 0
        if target_calendar_exists and not payload.overwrite_policy:
            errors.append("Explicit overwrite/merge policy is required before any future build when a target calendar already exists.")

    source_summary: dict[str, object] = {"source_type": payload.source_type}
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
                source_summary.update({"template_name": selected.name, "slot_count": selected.slot_count, "week_count": selected.week_count})

    authoritative_diff_summary = {
        "status": "read_only_preflight",
        "target_calendar_exists": target_calendar_exists,
        "target_event_count": target_event_count,
        "placeholder": "Authoritative event-level diff is planned in a future phase.",
    }

    audit_preview = {
        "action": "season_builder_preflight",
        "requested_by": payload.requested_by,
        "target_season_label": normalized_target,
        "source_type": payload.source_type,
        "source_template_id": payload.source_template_id,
        "overwrite_policy": payload.overwrite_policy,
        "read_only": True,
        "mutation_permitted": False,
    }

    return SeasonBuilderPreflightResponse(
        can_build=False,
        target_season_label=normalized_target,
        source_type=payload.source_type,
        source_template_id=payload.source_template_id,
        target_calendar_exists=target_calendar_exists,
        target_event_count=target_event_count,
        source_resolved=source_resolved,
        source_summary=source_summary,
        authoritative_diff_summary=authoritative_diff_summary,
        validation_warnings=warnings,
        validation_errors=errors,
        audit_preview=audit_preview,
    )
