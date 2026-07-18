"""Read-only run-scoped 15-year-old cohort season intake preview."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.application.season_registry_service import SeasonRegistryEntry, SeasonRegistryService
from beta_engine.application.world_package_countries_service import WorldPackageCountriesService
from beta_engine.domain.calendar.season_weeks import PLAYER_15TH_BIRTHDAY_AGE
from beta_engine.domain.countries import Country
from beta_engine.domain.players.intake_volume_policy import IntakeVolumePolicy, IntakeVolumePolicyConfig
from beta_engine.domain.players.weekly_intake import WeeklyIntakeCountryAllocation, WeeklyIntakePlanner
from beta_engine.infrastructure.db import SimulationPersistenceRepository


@dataclass(frozen=True)
class RunWeeklyIntakeCohortCountryAllocation:
    country_code: str
    country_name: str | None
    allocated_count: int
    allocation_weight: float
    allocation_share: float
    effective_population: int | float
    population_source_type: str
    population_source_year: int | None
    is_population_estimated: bool


@dataclass(frozen=True)
class RunWeeklyIntakeCohortSeasonWeek:
    season_week: int
    target_intake_count: int
    total_allocated: int
    week_weight: float
    calendar_year: int
    year_week: int
    birth_year: int
    birth_year_week: int
    allocations: list[RunWeeklyIntakeCohortCountryAllocation]


@dataclass(frozen=True)
class RunWeeklyIntakeCohortCountryTotal:
    country_code: str
    country_name: str | None
    allocated_count: int


@dataclass(frozen=True)
class RunWeeklyIntakeCohortSeasonPreviewResult:
    run_id: str
    world_id: str
    world_name: str
    season: str
    season_start_year: int
    season_index: int
    base_annual_intake_target: int
    season_growth_rate: float
    season_variation_multiplier: float
    annual_target: int
    total_weekly_target: int
    weeks: list[RunWeeklyIntakeCohortSeasonWeek]
    country_totals: list[RunWeeklyIntakeCohortCountryTotal]


@dataclass(slots=True)
class RunWeeklyIntakeCohortPreviewService:
    """Build a deterministic preview from persisted run metadata without mutating state."""

    repository: SimulationPersistenceRepository
    countries_service: WorldPackageCountriesService
    season_registry: SeasonRegistryService
    planner: WeeklyIntakePlanner = WeeklyIntakePlanner()
    volume_policy: IntakeVolumePolicy = IntakeVolumePolicy()

    def preview_season(
        self,
        *,
        run_id: str,
        base_annual_intake_target: int = 200,
        season_growth_rate: float = 0.015,
        country_code: str | None = None,
        region: str | None = None,
    ) -> RunWeeklyIntakeCohortSeasonPreviewResult:
        run_info = self.repository.get_simulation_run(run_id=run_id)
        if run_info is None:
            raise KeyError(f"run_id {run_id} was not found")

        registry_entry = self._get_supported_season(run_info.season)
        countries_result = self.countries_service.get_countries(run_info.world_id)
        if countries_result is None:
            raise LookupError(f"locked world package '{run_info.world_id}' was not found for run_id {run_id}")

        filtered_countries = self._filter_countries(countries_result.countries, country_code=country_code, region=region)
        plan = self.volume_policy.plan_season(
            world_id=run_info.world_id,
            season=registry_entry.label,
            config=IntakeVolumePolicyConfig(
                base_annual_intake_target=base_annual_intake_target,
                season_growth_rate=season_growth_rate,
            ),
        )
        if not filtered_countries and plan.annual_target > 0:
            raise LookupError("no matching countries found for run weekly intake cohort season preview")

        country_names = {country.code: country.name for country in filtered_countries}
        country_totals: dict[str, int] = {}
        weeks: list[RunWeeklyIntakeCohortSeasonWeek] = []
        for volume_week in plan.weeks:
            weekly_plan = self.planner.plan_weekly_intake(
                countries=filtered_countries,
                season=plan.season,
                season_week=volume_week.season_week,
                target_intake_count=volume_week.target_intake_count,
            )
            allocations = [self._to_allocation(allocation, country_names) for allocation in weekly_plan.allocations]
            for allocation in allocations:
                country_totals[allocation.country_code] = country_totals.get(allocation.country_code, 0) + allocation.allocated_count
            weeks.append(
                RunWeeklyIntakeCohortSeasonWeek(
                    season_week=weekly_plan.season_week,
                    target_intake_count=weekly_plan.target_intake_count,
                    total_allocated=weekly_plan.total_allocated,
                    week_weight=volume_week.week_weight,
                    calendar_year=weekly_plan.calendar_year,
                    year_week=weekly_plan.year_week,
                    birth_year=weekly_plan.calendar_year - PLAYER_15TH_BIRTHDAY_AGE,
                    birth_year_week=weekly_plan.birth_year_week,
                    allocations=allocations,
                )
            )

        return RunWeeklyIntakeCohortSeasonPreviewResult(
            run_id=run_info.run_id,
            world_id=run_info.world_id,
            world_name=countries_result.world_name,
            season=plan.season,
            season_start_year=plan.season_start_year,
            season_index=plan.season_index,
            base_annual_intake_target=plan.base_annual_intake_target,
            season_growth_rate=plan.season_growth_rate,
            season_variation_multiplier=plan.season_variation_multiplier,
            annual_target=plan.annual_target,
            total_weekly_target=plan.total_weekly_target,
            weeks=weeks,
            country_totals=[
                RunWeeklyIntakeCohortCountryTotal(
                    country_code=code,
                    country_name=country_names.get(code),
                    allocated_count=allocated_count,
                )
                for code, allocated_count in sorted(country_totals.items())
                if allocated_count > 0
            ],
        )

    def _get_supported_season(self, start_year: int) -> SeasonRegistryEntry:
        entry = self.season_registry.get_season(start_year=start_year)
        if entry is None:
            raise ValueError(f"season start year '{start_year}' is outside the supported season registry")
        return entry

    def _to_allocation(
        self,
        allocation: WeeklyIntakeCountryAllocation,
        country_names: dict[str, str],
    ) -> RunWeeklyIntakeCohortCountryAllocation:
        return RunWeeklyIntakeCohortCountryAllocation(
            country_code=allocation.country_code,
            country_name=country_names.get(allocation.country_code),
            allocated_count=allocation.allocated_count,
            allocation_weight=allocation.allocation_weight,
            allocation_share=allocation.allocation_share,
            effective_population=allocation.effective_population,
            population_source_type=allocation.population_source_type,
            population_source_year=allocation.population_source_year,
            is_population_estimated=allocation.is_population_estimated,
        )

    def _filter_countries(self, countries: list[Country], *, country_code: str | None, region: str | None) -> list[Country]:
        filtered = countries
        if country_code is not None:
            normalized_country_code = country_code.strip().upper()
            filtered = [country for country in filtered if country.code == normalized_country_code]
        if region is not None:
            normalized_region = region.strip().upper()
            filtered = [country for country in filtered if country.region.upper() == normalized_region or (country.travel_region or "").upper() == normalized_region]
        return list(filtered)
