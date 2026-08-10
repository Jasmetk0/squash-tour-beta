"""Deterministic annual talent-class planner (foundation slice)."""

from __future__ import annotations

import math

from beta_engine.core import DeterministicRng, SeedScope
from beta_engine.domain.countries import Country, CountryTalentModel
from beta_engine.domain.players.talent_dampener import (
    NeutralRecentGreatnessDampener,
    RecentGreatnessDampener,
)
from beta_engine.domain.players.talent_models import (
    AnnualTalentClassPlan,
    CountryDampenerSnapshot,
    CountryGenerationBiasProfile,
    CountryTalentAllocation,
    DampenerContributionSnapshot,
    TalentQualityBand,
    TalentSeed,
)


class AnnualTalentClassPlanner:
    """Build deterministic year-specific country allocations and innate rarity bands.

    Country V1 separates two ideas that the legacy planner mixed together:
    participation/pipeline determines how many prospects a country samples, while
    innate quality-band rarity is global.  Country development strength can later
    affect how much of that potential is realised, but does not make a person more
    likely to be born with generational potential.
    """

    # Calibration baseline only; these are not product-canon probabilities.
    BASE_QUALITY_WEIGHTS = {
        TalentQualityBand.GENERATIONAL: 0.001,
        TalentQualityBand.SPECIAL: 0.016,
        TalentQualityBand.ELITE: 0.080,
        TalentQualityBand.STRONG: 0.270,
        TalentQualityBand.SOLID: 0.633,
    }

    def __init__(self, dampener: RecentGreatnessDampener | None = None) -> None:
        self._dampener = dampener or NeutralRecentGreatnessDampener()
        self._country_model = CountryTalentModel()

    def plan(self, *, year: int, seed: int, countries: list[Country]) -> AnnualTalentClassPlan:
        if not countries:
            return AnnualTalentClassPlan(year=year, seed=seed, total_talents=0, allocations=[])

        root_rng = DeterministicRng(seed).branch(SeedScope.SEASON, "annual_talent_class", year)
        total_talents = self._total_talent_count(root_rng=root_rng, country_count=len(countries))
        allocations_by_code = self._allocate_counts(countries=countries, total_talents=total_talents)

        allocations: list[CountryTalentAllocation] = []
        for country in sorted(countries, key=lambda item: item.code):
            country_count = allocations_by_code[country.code]
            country_rng = root_rng.branch(SeedScope.SEASON, "country", country.code)
            quality_weights, dampener_snapshot = self._quality_weights(country=country, year=year)
            talents = self._build_talent_seeds(
                country=country,
                year=year,
                country_rng=country_rng,
                count=country_count,
                quality_weights=quality_weights,
            )
            allocations.append(
                CountryTalentAllocation(
                    country_code=country.code,
                    planned_count=country_count,
                    quality_weights=quality_weights,
                    bias_profile=self._bias_profile(country),
                    dampener=dampener_snapshot,
                    talents=talents,
                )
            )

        return AnnualTalentClassPlan(
            year=year,
            seed=seed,
            total_talents=total_talents,
            allocations=allocations,
        )

    def _total_talent_count(self, *, root_rng: DeterministicRng, country_count: int) -> int:
        baseline = max(30, country_count * 20)
        cycle = root_rng.uniform(-0.18, 0.2)
        return max(country_count, int(round(baseline * (1.0 + cycle))))

    def _allocate_counts(self, *, countries: list[Country], total_talents: int) -> dict[str, int]:
        weights: dict[str, float] = {}
        for country in countries:
            # Effective squash pool is population × popularity × access.  A log
            # transform keeps huge countries relevant without allowing raw
            # population to swamp the rest of the world.  Exact calibration is
            # intentionally left tunable after simulation data exists.
            pool = self._country_model.effective_squash_pool_weight(country)
            weights[country.code] = max(1.0, math.log10(max(10.0, pool)))

        weight_sum = sum(weights.values())
        if weight_sum <= 0:
            even = total_talents // len(countries)
            return {country.code: even for country in countries}

        raw = {code: (total_talents * weight / weight_sum) for code, weight in weights.items()}
        allocation = {code: int(value) for code, value in raw.items()}
        remaining = total_talents - sum(allocation.values())

        remainders = sorted(raw.items(), key=lambda item: (item[1] - int(item[1]), item[0]), reverse=True)
        for idx in range(remaining):
            code = remainders[idx % len(remainders)][0]
            allocation[code] += 1

        return allocation

    def _quality_weights(self, *, country: Country, year: int) -> tuple[dict[TalentQualityBand, float], CountryDampenerSnapshot]:
        # Innate rarity is global in Country V1.  The existing recent-greatness
        # dampener is retained as an explicit historical balancing mechanism,
        # but authored country strength no longer changes top-band birth odds.
        probabilities = {
            band: (
                self._apply_dampener(country.code, year, band, value)
                if band in {TalentQualityBand.GENERATIONAL, TalentQualityBand.SPECIAL, TalentQualityBand.ELITE}
                else value
            )
            for band, value in self.BASE_QUALITY_WEIGHTS.items()
        }
        total = sum(probabilities.values())
        normalized = {band: value / total for band, value in probabilities.items()}
        diagnostics = self._dampener.diagnostics(country_code=country.code, year=year)
        snapshot = CountryDampenerSnapshot(
            recent_greatness_score=diagnostics.recent_greatness_score,
            signal_count=diagnostics.signal_count,
            multipliers=diagnostics.multipliers,
            active=diagnostics.active,
            contributions=[
                DampenerContributionSnapshot(
                    source=item.source,
                    season=item.season,
                    quality_band=item.quality_band,
                    reference_id=item.reference_id,
                    raw_weight=item.raw_weight,
                    decay_factor=item.decay_factor,
                    effective_weight=item.effective_weight,
                )
                for item in diagnostics.contributions
            ],
        )
        return normalized, snapshot

    def _build_talent_seeds(
        self,
        *,
        country: Country,
        year: int,
        country_rng: DeterministicRng,
        count: int,
        quality_weights: dict[TalentQualityBand, float],
    ) -> list[TalentSeed]:
        thresholds = self._cumulative_thresholds(quality_weights)
        talents: list[TalentSeed] = []

        for sequence in range(1, count + 1):
            band_roll = country_rng.random()
            band = self._pick_band(band_roll, thresholds)
            talent_seed = country_rng.derive(SeedScope.SEASON, "talent_seed", year, country.code, sequence)
            talents.append(
                TalentSeed(
                    sequence=sequence,
                    seed_value=talent_seed.value,
                    quality_band=band,
                )
            )

        return talents

    @staticmethod
    def _bias_profile(country: Country) -> CountryGenerationBiasProfile:
        # National style/personality DNA is deliberately deferred beyond V1.
        # Retain the persisted shape but make it neutral.
        _ = country
        return CountryGenerationBiasProfile(
            professionalism_tendency=0.0,
            technical_vs_physical_lean=0.0,
            mental_sharpness_tendency=0.0,
        )

    def _apply_dampener(self, country_code: str, year: int, band: TalentQualityBand, value: float) -> float:
        multiplier = self._dampener.quality_multiplier(country_code=country_code, year=year, band=band)
        return max(0.0, value * max(0.0, multiplier))

    @staticmethod
    def _cumulative_thresholds(
        weights: dict[TalentQualityBand, float],
    ) -> list[tuple[float, TalentQualityBand]]:
        order = [
            TalentQualityBand.GENERATIONAL,
            TalentQualityBand.SPECIAL,
            TalentQualityBand.ELITE,
            TalentQualityBand.STRONG,
            TalentQualityBand.SOLID,
        ]
        cumulative = 0.0
        result: list[tuple[float, TalentQualityBand]] = []
        for band in order:
            cumulative += weights.get(band, 0.0)
            result.append((cumulative, band))
        result[-1] = (1.0, result[-1][1])
        return result

    @staticmethod
    def _pick_band(roll: float, thresholds: list[tuple[float, TalentQualityBand]]) -> TalentQualityBand:
        for threshold, band in thresholds:
            if roll <= threshold:
                return band
        return TalentQualityBand.SOLID
