"""Deterministic player generator influenced by country-level strength."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.core import DeterministicRng, SeedScope
from beta_engine.domain.countries import Country, CountryTalentModel
from beta_engine.domain.players.models import HiddenCareerTraits, Player
from beta_engine.infrastructure.world_config import PlayerIdentityConfig


@dataclass(slots=True)
class PlayerGenerator:
    rng: DeterministicRng
    identity_config: PlayerIdentityConfig
    country_talent_model: CountryTalentModel

    def generate(self, *, country: Country, sequence: int) -> Player:
        player_rng = self.rng.branch(SeedScope.SEASON, "player", country.code, sequence)
        talent_index = self.country_talent_model.talent_index(country)

        age = self._clamp_int(17, 36, int(round(player_rng.uniform(17, 33) + (1.0 - talent_index) * 1.6)))
        name = self._build_name(player_rng, country, sequence)

        archetype = player_rng.choice(self.identity_config.archetypes)
        play_style = player_rng.choice(self.identity_config.play_styles)

        technique = self._skill_value(player_rng, talent_index, country.development_pipeline_quality)
        movement = self._skill_value(player_rng, talent_index, country.infrastructure_level)
        physical = self._skill_value(player_rng, talent_index, self.country_talent_model.population_factor(country))
        mental = self._skill_value(player_rng, talent_index, country.historical_tradition)

        consistency = self._skill_value(player_rng, (technique + movement) / 200.0, country.elite_system_strength)
        clutch = self._skill_value(player_rng, mental / 99.0, country.historical_tradition)
        recovery = self._skill_value(player_rng, physical / 99.0, country.infrastructure_level)

        hidden = HiddenCareerTraits(
            potential_ceiling=self._clamp_int(55, 99, int(round(66 + talent_index * 30 + player_rng.uniform(-8, 8)))),
            growth_curve=player_rng.choice(self.identity_config.growth_curves),
            professionalism=self._clamp_float(country.development_pipeline_quality * 0.62 + player_rng.uniform(0.10, 0.42)),
            ambition=self._clamp_float(country.squash_popularity * 0.50 + player_rng.uniform(0.12, 0.55)),
            travel_tolerance=self._travel_tolerance(country, player_rng),
            schedule_aggression=self._clamp_float(player_rng.uniform(0.18, 0.82)),
            injury_proneness=self._clamp_float(1.0 - (country.infrastructure_level * 0.55 + player_rng.uniform(0.12, 0.42))),
            resilience=self._clamp_float(country.historical_tradition * 0.42 + player_rng.uniform(0.24, 0.68)),
        )

        return Player(
            player_id=f"{country.code}-{sequence:05d}",
            name=name,
            age=age,
            nationality=country.code,
            technique=technique,
            movement=movement,
            physical=physical,
            mental=mental,
            consistency=consistency,
            clutch=clutch,
            recovery=recovery,
            play_style=play_style,
            archetype=archetype,
            hidden_career_traits=hidden,
        )

    def _build_name(self, rng: DeterministicRng, country: Country, sequence: int) -> str:
        given = rng.choice(self.identity_config.given_names)
        family = rng.choice(self.identity_config.family_names)
        return f"{given} {family}-{country.code}{sequence:03d}"

    @staticmethod
    def _clamp_int(minimum: int, maximum: int, value: int) -> int:
        return max(minimum, min(maximum, value))

    @staticmethod
    def _clamp_float(value: float) -> float:
        return max(0.0, min(1.0, round(value, 4)))

    def _skill_value(self, rng: DeterministicRng, talent_index: float, contextual_factor: float) -> int:
        baseline = 34 + talent_index * 36 + contextual_factor * 18
        noise = rng.uniform(-8.0, 8.0)
        return self._clamp_int(20, 99, int(round(baseline + noise)))

    def _travel_tolerance(self, country: Country, rng: DeterministicRng) -> float:
        if country.travel_affinity:
            affinity = sum(country.travel_affinity.values()) / len(country.travel_affinity)
        else:
            affinity = 0.5
        return self._clamp_float(affinity * 0.68 + rng.uniform(0.08, 0.42))
