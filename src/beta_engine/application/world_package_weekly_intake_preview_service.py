"""Read-only weekly intake preview for World Package countries."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.application.world_package_countries_service import WorldPackageCountriesService
from beta_engine.domain.calendar import season_week_to_calendar_position
from beta_engine.domain.countries import Country
from beta_engine.domain.calendar.season_weeks import PLAYER_15TH_BIRTHDAY_AGE
from beta_engine.domain.players.intake_volume_policy import (
    IntakeVolumePolicy,
    IntakeVolumePolicyConfig,
    SeasonIntakeVolumePlan,
)
from beta_engine.domain.players.weekly_intake import WeeklyIntakePlan, WeeklyIntakePlanner


@dataclass(frozen=True)
class WorldPackageWeeklyIntakeSeasonScheduleWeek:
    season_week: int
    target_intake_count: int
    week_weight: float
    calendar_year: int
    year_week: int
    birth_year: int
    birth_year_week: int


@dataclass(frozen=True)
class WorldPackageWeeklyIntakeSeasonSchedulePreviewResult:
    world_id: str
    world_name: str
    plan: SeasonIntakeVolumePlan
    weeks: list[WorldPackageWeeklyIntakeSeasonScheduleWeek]


@dataclass(frozen=True)
class WorldPackageWeeklyIntakePreviewResult:
    world_id: str
    world_name: str
    plan: WeeklyIntakePlan


@dataclass(slots=True)
class WorldPackageWeeklyIntakePreviewService:
    """Plan weekly intake against package-scoped countries without mutating state."""

    countries_service: WorldPackageCountriesService
    planner: WeeklyIntakePlanner = WeeklyIntakePlanner()
    volume_policy: IntakeVolumePolicy = IntakeVolumePolicy()

    def preview(
        self,
        *,
        world_id: str,
        season: str,
        season_week: int,
        target_intake_count: int,
        country_code: str | None = None,
        region: str | None = None,
    ) -> WorldPackageWeeklyIntakePreviewResult | None:
        countries_result = self.countries_service.get_countries(world_id)
        if countries_result is None:
            return None

        countries = self._filter_countries(countries_result.countries, country_code=country_code, region=region)
        plan = self.planner.plan_weekly_intake(
            countries=countries,
            season=season,
            season_week=season_week,
            target_intake_count=target_intake_count,
        )
        return WorldPackageWeeklyIntakePreviewResult(
            world_id=countries_result.world_id,
            world_name=countries_result.world_name,
            plan=plan,
        )

    def preview_season_schedule(
        self,
        *,
        world_id: str,
        season: str,
        base_annual_intake_target: int = 200,
        season_growth_rate: float = 0.015,
    ) -> WorldPackageWeeklyIntakeSeasonSchedulePreviewResult | None:
        countries_result = self.countries_service.get_countries(world_id)
        if countries_result is None:
            return None

        plan = self.volume_policy.plan_season(
            world_id=countries_result.world_id,
            season=season,
            config=IntakeVolumePolicyConfig(
                base_annual_intake_target=base_annual_intake_target,
                season_growth_rate=season_growth_rate,
            ),
        )
        weeks = []
        for week in plan.weeks:
            position = season_week_to_calendar_position(plan.season, week.season_week)
            weeks.append(
                WorldPackageWeeklyIntakeSeasonScheduleWeek(
                    season_week=week.season_week,
                    target_intake_count=week.target_intake_count,
                    week_weight=week.week_weight,
                    calendar_year=position.calendar_year,
                    year_week=position.year_week,
                    birth_year=position.calendar_year - PLAYER_15TH_BIRTHDAY_AGE,
                    birth_year_week=position.year_week,
                )
            )
        return WorldPackageWeeklyIntakeSeasonSchedulePreviewResult(
            world_id=countries_result.world_id,
            world_name=countries_result.world_name,
            plan=plan,
            weeks=weeks,
        )

    def _filter_countries(self, countries: list[Country], *, country_code: str | None, region: str | None) -> list[Country]:
        filtered = countries
        if country_code is not None:
            normalized_country_code = country_code.strip().upper()
            filtered = [country for country in filtered if country.code == normalized_country_code]
        if region is not None:
            normalized_region = region.strip().upper()
            filtered = [
                country
                for country in filtered
                if country.region.upper() == normalized_region or (country.travel_region or "").upper() == normalized_region
            ]
        return list(filtered)
