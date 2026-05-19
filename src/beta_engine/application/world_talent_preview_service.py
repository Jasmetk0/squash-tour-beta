"""Read-only world talent preview diagnostics built on top of annual planner."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.application.countries_service import CountriesConfigService, CountriesDatasetMetadata
from beta_engine.domain.players import AnnualTalentClassPlanner, TalentQualityBand


def _empty_band_counts() -> dict[str, int]:
    return {band.value: 0 for band in TalentQualityBand}


def _empty_band_weights() -> dict[str, float]:
    return {band.value: 0.0 for band in TalentQualityBand}


@dataclass(frozen=True)
class CountryTalentYearPreview:
    country_code: str
    country_name: str
    planned_count: int
    quality_weights: dict[str, float]
    actual_band_counts: dict[str, int]
    elite_talents: int
    tour_talents: int
    pro_depth: int
    bias_profile: dict[str, float]
    dampener: dict[str, object]


@dataclass(frozen=True)
class TalentClassYearPreview:
    year: int
    seed: int
    dataset_status: str | None
    country_count: int
    source_path: str
    total_talents: int
    countries: list[CountryTalentYearPreview]


@dataclass(frozen=True)
class CountryTalentSpanSummary:
    country_code: str
    country_name: str
    total_planned_talents: int
    average_talents_per_year: float
    total_elite_count: int
    total_special_count: int
    total_generational_count: int
    total_elite_talents: int
    total_tour_talents: int
    total_pro_depth: int
    average_elite_talents_per_year: float
    average_tour_talents_per_year: float
    average_pro_depth_per_year: float
    average_top_band_rate: float


@dataclass(frozen=True)
class TalentClassSummaryPreview:
    year_start: int
    years: int
    seed: int
    dataset_status: str | None
    country_count: int
    source_path: str
    total_talents_across_span: int
    average_total_talents_per_year: float
    global_band_totals: dict[str, int]
    global_elite_talents: int
    global_tour_talents: int
    global_pro_depth: int
    countries: list[CountryTalentSpanSummary]


@dataclass(slots=True)
class WorldTalentPreviewService:
    countries_service: CountriesConfigService
    planner: AnnualTalentClassPlanner = AnnualTalentClassPlanner()

    def preview_year(self, *, year: int, seed: int) -> TalentClassYearPreview:
        config = self.countries_service.get_config()
        metadata = self.countries_service.get_metadata()
        plan = self.planner.plan(year=year, seed=seed, countries=config.countries)
        country_names = {country.code: country.name for country in config.countries}

        country_previews: list[CountryTalentYearPreview] = []
        for allocation in plan.allocations:
            band_counts = _empty_band_counts()
            for talent in allocation.talents:
                band_counts[talent.quality_band.value] += 1

            quality_weights = _empty_band_weights()
            quality_weights.update({band.value: weight for band, weight in allocation.quality_weights.items()})
            country_previews.append(
                # Temporary aggregate bridge mapping until the final potential-tier model lands:
                # Elite ~= L through S-, Tour ~= A+ through B+, Pro Depth ~= B through C-ish.
                CountryTalentYearPreview(
                    country_code=allocation.country_code,
                    country_name=country_names.get(allocation.country_code, allocation.country_code),
                    planned_count=allocation.planned_count,
                    quality_weights=quality_weights,
                    actual_band_counts=band_counts,
                    elite_talents=(
                        band_counts[TalentQualityBand.ELITE.value]
                        + band_counts[TalentQualityBand.SPECIAL.value]
                        + band_counts[TalentQualityBand.GENERATIONAL.value]
                    ),
                    tour_talents=band_counts[TalentQualityBand.STRONG.value],
                    pro_depth=band_counts[TalentQualityBand.SOLID.value],
                    bias_profile=allocation.bias_profile.model_dump(),
                    dampener=allocation.dampener.model_dump(mode="json"),
                )
            )

        return TalentClassYearPreview(
            year=year,
            seed=seed,
            dataset_status=metadata.dataset_status,
            country_count=metadata.country_count,
            source_path=metadata.source_path,
            total_talents=plan.total_talents,
            countries=country_previews,
        )

    def summary(self, *, year_start: int, years: int, seed: int) -> TalentClassSummaryPreview:
        config = self.countries_service.get_config()
        metadata = self.countries_service.get_metadata()
        country_names = {country.code: country.name for country in config.countries}

        total_talents = 0
        per_country_planned = {country.code: 0 for country in config.countries}
        per_country_bands = {country.code: _empty_band_counts() for country in config.countries}
        global_band_totals = _empty_band_counts()

        for offset in range(years):
            plan = self.planner.plan(year=year_start + offset, seed=seed, countries=config.countries)
            total_talents += plan.total_talents
            for allocation in plan.allocations:
                per_country_planned[allocation.country_code] += allocation.planned_count
                for talent in allocation.talents:
                    band_key = talent.quality_band.value
                    per_country_bands[allocation.country_code][band_key] += 1
                    global_band_totals[band_key] += 1

        countries_summary: list[CountryTalentSpanSummary] = []
        for country in sorted(config.countries, key=lambda item: item.code):
            planned_total = per_country_planned[country.code]
            bands = per_country_bands[country.code]
            top_band_total = (
                bands[TalentQualityBand.ELITE.value]
                + bands[TalentQualityBand.SPECIAL.value]
                + bands[TalentQualityBand.GENERATIONAL.value]
            )
            countries_summary.append(
                CountryTalentSpanSummary(
                    country_code=country.code,
                    country_name=country_names[country.code],
                    total_planned_talents=planned_total,
                    average_talents_per_year=round(planned_total / years, 4),
                    total_elite_count=bands[TalentQualityBand.ELITE.value],
                    total_special_count=bands[TalentQualityBand.SPECIAL.value],
                    total_generational_count=bands[TalentQualityBand.GENERATIONAL.value],
                    total_elite_talents=top_band_total,
                    total_tour_talents=bands[TalentQualityBand.STRONG.value],
                    total_pro_depth=bands[TalentQualityBand.SOLID.value],
                    average_elite_talents_per_year=round(top_band_total / years, 4),
                    average_tour_talents_per_year=round(bands[TalentQualityBand.STRONG.value] / years, 4),
                    average_pro_depth_per_year=round(bands[TalentQualityBand.SOLID.value] / years, 4),
                    average_top_band_rate=round(top_band_total / planned_total, 6) if planned_total > 0 else 0.0,
                )
            )

        return TalentClassSummaryPreview(
            year_start=year_start,
            years=years,
            seed=seed,
            dataset_status=metadata.dataset_status,
            country_count=metadata.country_count,
            source_path=metadata.source_path,
            total_talents_across_span=total_talents,
            average_total_talents_per_year=round(total_talents / years, 4),
            global_band_totals=global_band_totals,
            global_elite_talents=(
                global_band_totals[TalentQualityBand.ELITE.value]
                + global_band_totals[TalentQualityBand.SPECIAL.value]
                + global_band_totals[TalentQualityBand.GENERATIONAL.value]
            ),
            global_tour_talents=global_band_totals[TalentQualityBand.STRONG.value],
            global_pro_depth=global_band_totals[TalentQualityBand.SOLID.value],
            countries=countries_summary,
        )
