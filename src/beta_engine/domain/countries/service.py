"""Pure country-domain services for deterministic talent weighting."""

from __future__ import annotations

import math

from beta_engine.domain.countries.models import Country


class CountryTalentModel:
    """Computes deterministic country-level talent factors for player generation."""

    def population_factor(self, country: Country) -> float:
        # Log scale keeps population relevant without dominating outcomes.
        return min(1.0, max(0.0, (math.log10(country.population) - 5.0) / 4.0))

    def ecosystem_strength(self, country: Country) -> float:
        return (
            country.squash_popularity * 0.20
            + country.infrastructure_level * 0.20
            + country.development_pipeline_quality * 0.22
            + country.elite_system_strength * 0.22
            + country.historical_tradition * 0.16
        )

    def talent_index(self, country: Country) -> float:
        ecosystem = self.ecosystem_strength(country)
        population = self.population_factor(country)
        return ecosystem * 0.74 + population * 0.26
