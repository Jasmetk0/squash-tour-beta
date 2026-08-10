from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from beta_engine.api.deps import get_season_registry_service, get_world_package_clone_service, get_world_package_countries_service, get_world_package_effective_population_service, get_world_package_registry_service, get_world_package_weekly_intake_preview_service, get_world_package_validation_service
from beta_engine.api.schemas import (
    WorldPackageCloneErrorResponse,
    WorldPackageCloneRequest,
    WorldPackageCloneResponse,
    CountryResponse,
    WorldPackageCountriesResponse,
    WorldPackageCountryDetailResponse,
    WorldPackageCountryUpdateRequest,
    WorldPackageCountryUpdateResponse,
    WorldPackageGeographyResponse,
    WorldPackageCountryEffectivePopulationResponse,
    WeeklyIntakePreviewResponse,
    WeeklyIntakeSeasonSchedulePreviewResponse,
    WeeklyIntakeSeasonScheduleWeekResponse,
    WorldPackageDetailResponse,
    WorldPackageListResponse,
    WorldPackageSummaryResponse,
    WorldPackageValidationResponse,
)
from beta_engine.application.world_package_clone_service import WorldPackageCloneResult, WorldPackageCloneService
from beta_engine.application.world_package_countries_service import WorldPackageCountriesResult, WorldPackageCountriesService, WorldPackageCountryUpdate, WorldPackageMutationError
from beta_engine.application.world_package_effective_population_service import WorldPackageCountryEffectivePopulationResult, WorldPackageEffectivePopulationService
from beta_engine.application.world_package_registry_service import OFFICIAL_FAX_WORLD_ID, WorldPackageRegistryRecord, WorldPackageRegistryService
from beta_engine.application.world_package_validation_service import WorldPackageValidationResult, WorldPackageValidationService
from beta_engine.application.season_registry_service import SeasonRegistryService
from beta_engine.application.world_package_weekly_intake_preview_service import WorldPackageWeeklyIntakePreviewResult, WorldPackageWeeklyIntakeSeasonSchedulePreviewResult, WorldPackageWeeklyIntakeSeasonScheduleWeek, WorldPackageWeeklyIntakePreviewService

router = APIRouter(prefix="/world/packages", tags=["world"])


def _to_summary(record: WorldPackageRegistryRecord) -> WorldPackageSummaryResponse:
    return WorldPackageSummaryResponse.model_validate(record, from_attributes=True)


def _to_detail(record: WorldPackageRegistryRecord) -> WorldPackageDetailResponse:
    return WorldPackageDetailResponse.model_validate(record, from_attributes=True)


def _to_validation(result: WorldPackageValidationResult) -> WorldPackageValidationResponse:
    return WorldPackageValidationResponse.model_validate(result, from_attributes=True)


def _to_countries(result: WorldPackageCountriesResult) -> WorldPackageCountriesResponse:
    return WorldPackageCountriesResponse(
        world_id=result.world_id,
        world_name=result.world_name,
        type=result.type,
        source=result.source,
        read_only=result.read_only,
        country_count=result.country_count,
        source_path=result.source_path,
        countries=[CountryResponse.model_validate(country.model_dump(mode="json")) for country in result.countries],
    )


@router.get("/{world_id}/geography", response_model=WorldPackageGeographyResponse)
def get_world_package_geography(
    world_id: str,
    service: WorldPackageCountriesService = Depends(get_world_package_countries_service),
) -> WorldPackageGeographyResponse:
    result = service.get_geography(world_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"world package '{world_id}' not found")
    return WorldPackageGeographyResponse.model_validate(result, from_attributes=True)


def _to_effective_population(result: WorldPackageCountryEffectivePopulationResult) -> WorldPackageCountryEffectivePopulationResponse:
    return WorldPackageCountryEffectivePopulationResponse.model_validate(result, from_attributes=True)


def _to_weekly_intake_preview(result: WorldPackageWeeklyIntakePreviewResult) -> WeeklyIntakePreviewResponse:
    plan_payload = result.plan.model_dump(mode="json")
    return WeeklyIntakePreviewResponse(world_id=result.world_id, world_name=result.world_name, **plan_payload)


def _to_weekly_intake_schedule_week(
    week: WorldPackageWeeklyIntakeSeasonScheduleWeek,
) -> WeeklyIntakeSeasonScheduleWeekResponse:
    return WeeklyIntakeSeasonScheduleWeekResponse(
        season_week=week.season_week,
        target_intake_count=week.target_intake_count,
        week_weight=week.week_weight,
        calendar_year=week.calendar_year,
        year_week=week.year_week,
        birth_year=week.birth_year,
        birth_year_week=week.birth_year_week,
    )


def _to_weekly_intake_season_schedule_preview(
    result: WorldPackageWeeklyIntakeSeasonSchedulePreviewResult,
) -> WeeklyIntakeSeasonSchedulePreviewResponse:
    plan_payload = result.plan.model_dump(mode="json", exclude={"world_id", "weeks"})
    return WeeklyIntakeSeasonSchedulePreviewResponse(
        world_id=result.world_id,
        world_name=result.world_name,
        **plan_payload,
        weeks=[_to_weekly_intake_schedule_week(week) for week in result.weeks],
    )


def _to_clone_response(result: WorldPackageCloneResult) -> WorldPackageCloneResponse:
    return WorldPackageCloneResponse(
        ok=result.ok,
        dry_run=result.dry_run,
        source_world_id=result.source_world_id,
        new_world_id=result.new_world_id,
        target_path=result.target_path,
        created_files=result.created_files,
        package=_to_detail(result.package) if result.package is not None else None,
        validation=_to_validation(result.validation) if result.validation is not None else None,
        errors=[WorldPackageCloneErrorResponse(field=item.field, message=item.message) for item in result.errors],
    )


@router.get("", response_model=WorldPackageListResponse)
def list_world_packages(
    service: WorldPackageRegistryService = Depends(get_world_package_registry_service),
) -> WorldPackageListResponse:
    return WorldPackageListResponse(packages=[_to_summary(record) for record in service.list_packages()])


@router.post("/{world_id}/clone", response_model=WorldPackageCloneResponse)
def clone_world_package(
    world_id: str,
    payload: WorldPackageCloneRequest,
    service: WorldPackageCloneService = Depends(get_world_package_clone_service),
) -> WorldPackageCloneResponse:
    if world_id != OFFICIAL_FAX_WORLD_ID:
        raise HTTPException(status_code=404, detail=f"world package '{world_id}' clone is not supported")
    result = service.clone_official_world(
        new_world_id=payload.new_world_id,
        name=payload.name,
        description=payload.description,
        dry_run=payload.dry_run,
    )
    return _to_clone_response(result)


@router.get("/{world_id}/countries", response_model=WorldPackageCountriesResponse)
def get_world_package_countries(
    world_id: str,
    service: WorldPackageCountriesService = Depends(get_world_package_countries_service),
) -> WorldPackageCountriesResponse:
    result = service.get_countries(world_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"world package '{world_id}' not found")
    return _to_countries(result)


@router.get(
    "/{world_id}/countries/{country_code}/effective-population",
    response_model=WorldPackageCountryEffectivePopulationResponse,
)
def get_world_package_country_effective_population(
    world_id: str,
    country_code: str,
    year: int = Query(ge=1955, le=2050),
    service: WorldPackageEffectivePopulationService = Depends(get_world_package_effective_population_service),
) -> WorldPackageCountryEffectivePopulationResponse:
    result = service.get_effective_population(world_id=world_id, country_code=country_code, requested_year=year)
    if result is None:
        countries_result = service.countries_service.get_countries(world_id)
        if countries_result is None:
            raise HTTPException(status_code=404, detail=f"world package '{world_id}' not found")
        raise HTTPException(status_code=404, detail=f"country '{country_code.upper()}' not found in world package '{world_id}'")
    return _to_effective_population(result)


@router.get("/{world_id}/countries/{country_code}", response_model=WorldPackageCountryDetailResponse)
def get_world_package_country(
    world_id: str,
    country_code: str,
    service: WorldPackageCountriesService = Depends(get_world_package_countries_service),
) -> WorldPackageCountryDetailResponse:
    result = service.get_country(world_id, country_code)
    if result is None:
        if service.registry_service.get_package(world_id) is None:
            raise HTTPException(status_code=404, detail=f"world package '{world_id}' not found")
        raise HTTPException(status_code=404, detail=f"country '{country_code.upper()}' not found in world package '{world_id}'")
    return WorldPackageCountryDetailResponse(
        package=_to_summary(result.package),
        country=CountryResponse.model_validate(result.country.model_dump(mode="json")),
        region=result.region.model_dump() if result.region else None,
        continent=result.continent.model_dump() if result.continent else None,
        travel_region=result.travel_region.model_dump() if result.travel_region else None,
        source_path=result.source_path,
    )


@router.put("/{world_id}/countries/{country_code}", response_model=WorldPackageCountryUpdateResponse)
def update_world_package_country(
    world_id: str,
    country_code: str,
    payload: WorldPackageCountryUpdateRequest,
    service: WorldPackageCountriesService = Depends(get_world_package_countries_service),
) -> WorldPackageCountryUpdateResponse:
    try:
        result = service.update_country(world_id, country_code, WorldPackageCountryUpdate.model_validate(payload.model_dump()))
    except WorldPackageMutationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    detail = result.detail
    detail_response = WorldPackageCountryDetailResponse(
        package=_to_summary(detail.package),
        country=CountryResponse.model_validate(detail.country.model_dump(mode="json")),
        region=detail.region.model_dump() if detail.region else None,
        continent=detail.continent.model_dump() if detail.continent else None,
        travel_region=detail.travel_region.model_dump() if detail.travel_region else None,
        source_path=detail.source_path,
    )
    return WorldPackageCountryUpdateResponse(
        country_detail=detail_response,
        package=detail_response.package,
        validation=_to_validation(result.validation),
    )


@router.get("/{world_id}/weekly-intake/preview", response_model=WeeklyIntakePreviewResponse)
def preview_world_package_weekly_intake(
    world_id: str,
    season: str,
    season_week: int = Query(..., ge=1, le=61),
    target_intake_count: int = Query(..., ge=0),
    country_code: str | None = None,
    region: str | None = None,
    service: WorldPackageWeeklyIntakePreviewService = Depends(get_world_package_weekly_intake_preview_service),
) -> WeeklyIntakePreviewResponse:
    result = service.preview(
        world_id=world_id,
        season=season,
        season_week=season_week,
        target_intake_count=target_intake_count,
        country_code=country_code,
        region=region,
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"world package '{world_id}' not found")
    if not result.plan.allocations and target_intake_count > 0:
        raise HTTPException(status_code=404, detail="no matching countries found for weekly intake preview")
    return _to_weekly_intake_preview(result)


@router.get(
    "/{world_id}/weekly-intake/season-schedule/preview",
    response_model=WeeklyIntakeSeasonSchedulePreviewResponse,
)
def preview_world_package_weekly_intake_season_schedule(
    world_id: str,
    season: str,
    base_annual_intake_target: int = Query(200, ge=0),
    season_growth_rate: float = Query(0.015, ge=0.0, le=0.10),
    service: WorldPackageWeeklyIntakePreviewService = Depends(get_world_package_weekly_intake_preview_service),
    season_registry: SeasonRegistryService = Depends(get_season_registry_service),
) -> WeeklyIntakeSeasonSchedulePreviewResponse:
    try:
        registry_entry = season_registry.get_season(label=season)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if registry_entry is None:
        raise HTTPException(status_code=422, detail=f"season '{season}' is outside the supported season registry")

    result = service.preview_season_schedule(
        world_id=world_id,
        season=season,
        base_annual_intake_target=base_annual_intake_target,
        season_growth_rate=season_growth_rate,
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"world package '{world_id}' not found")
    return _to_weekly_intake_season_schedule_preview(result)


@router.get("/{world_id}/validation", response_model=WorldPackageValidationResponse)
def validate_world_package(
    world_id: str,
    service: WorldPackageValidationService = Depends(get_world_package_validation_service),
) -> WorldPackageValidationResponse:
    result = service.validate_package(world_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"world package '{world_id}' not found")
    return _to_validation(result)


@router.get("/{world_id}", response_model=WorldPackageDetailResponse)
def get_world_package(
    world_id: str,
    service: WorldPackageRegistryService = Depends(get_world_package_registry_service),
) -> WorldPackageDetailResponse:
    record = service.get_package(world_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"world package '{world_id}' not found")
    return _to_detail(record)
