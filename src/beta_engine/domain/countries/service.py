"""Pure country-domain helpers for deterministic participation and development weighting."""

from __future__ import annotations

import math

from beta_engine.domain.countries.models import Country


class CountryTalentModel:
    """Derive V1 country-level squash-pipeline factors.

    The six authored country ratings describe different stages of the sporting
    environment.  These helpers intentionally use simple baseline mathematics;
    exact calibration remains a separate tuning decision.
    """

    def population_factor(self, country: Country) -> float:
        """Legacy-safe nonlinear population context used by old generators."""

        return min(1.0, max(0.0, (math.log10(country.population) - 5.0) / 4.0))

    def participation_factor(self, country: Country) -> float:
        """Per-capita squash-pool factor from popularity and practical access.

        Ratings use value/5 rather than the normalized 1->0 helper so even a
        country rated 1 retains a small non-zero squash population.
        """

        popularity = country.squash_popularity / 5.0
        access = country.squash_access / 5.0
        return popularity * access

    def effective_squash_pool_weight(self, country: Country, population: int | float | None = None) -> float:
        """Relative player-pool weight used for country intake allocation."""

        base_population = float(country.population if population is None else population)
        return max(0.0, base_population) * self.participation_factor(country)

    def development_environment(self, country: Country) -> float:
        """Simple V1 development/conversion environment, independent of innate talent.

        Development quality is the largest authored driver; competition and
        elite support are substantial distinct stages, while tradition is a
        smaller continuity modifier. Exact weights remain calibration baseline.
        """

        return (
            country.development_quality_norm * 0.40
            + country.competition_quality_norm * 0.25
            + country.elite_support_norm * 0.25
            + country.squash_tradition_norm * 0.10
        )

    def ecosystem_strength(self, country: Country) -> float:
        """Compatibility summary for diagnostics; not an authored country attribute."""

        return (self.participation_factor(country) + self.development_environment(country)) / 2.0

    def talent_index(self, country: Country) -> float:
        """Compatibility score for legacy generator call sites.

        This is deliberately *not* an innate-talent probability.  Country V1 has
        no authored Talent Quality rating; innate potential is sampled separately.
        """

        return self.development_environment(country)
