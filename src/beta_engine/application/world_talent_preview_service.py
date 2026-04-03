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
    bias_profile: dict[str, float]


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
                CountryTalentYearPreview(
                    country_code=allocation.country_code,
                    country_name=country_names.get(allocation.country_code, allocation.country_code),
                    planned_count=allocation.planned_count,
                    quality_weights=quality_weights,
                    actual_band_counts=band_counts,
                    bias_profile=allocation.bias_profile.model_dump(),
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
            countries=countries_summary,
        )
