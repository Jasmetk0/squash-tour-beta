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
            country.squash_popularity_norm * 0.23
            + country.system_quality_norm * 0.33
            + country.squash_tradition_norm * 0.29
            + country.wealth_support_norm * 0.15
        )

    def talent_index(self, country: Country) -> float:
        ecosystem = self.ecosystem_strength(country)
        population = self.population_factor(country)
        return ecosystem * 0.74 + population * 0.26
