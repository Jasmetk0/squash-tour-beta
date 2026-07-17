"""Read-only weekly intake preview for World Package countries."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.application.world_package_countries_service import WorldPackageCountriesService
from beta_engine.domain.countries import Country
from beta_engine.domain.players.weekly_intake import WeeklyIntakePlan, WeeklyIntakePlanner


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
