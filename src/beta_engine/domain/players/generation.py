"""Deterministic player generator influenced by country-level strength."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.core import DeterministicRng, SeedScope
from beta_engine.domain.countries import Country, CountryTalentModel
from beta_engine.domain.players.models import HiddenCareerTraits, Player
from beta_engine.domain.players.talent_models import CountryGenerationBiasProfile, TalentQualityBand
from beta_engine.infrastructure.world_config import PlayerIdentityConfig


@dataclass(slots=True)
class PlayerGenerator:
    rng: DeterministicRng
    identity_config: PlayerIdentityConfig
    country_talent_model: CountryTalentModel

    def generate(self, *, country: Country, sequence: int) -> Player:
        """Legacy-compatible generation path used by non-planner tests/helpers."""

        player_rng = self.rng.branch(SeedScope.SEASON, "player", country.code, sequence)
        talent_index = self.country_talent_model.talent_index(country)
        return self._generate_from_rng(
            country=country,
            sequence=sequence,
            player_rng=player_rng,
            talent_index=talent_index,
            quality_band=TalentQualityBand.SOLID,
            bias_profile=None,
        )

    def generate_from_talent_seed(
        self,
        *,
        country: Country,
        sequence: int,
        talent_seed_value: int,
        quality_band: TalentQualityBand,
        bias_profile: CountryGenerationBiasProfile | None,
    ) -> Player:
        """Planner-driven runtime path: deterministic talent seed + quality band -> player."""

        player_rng = DeterministicRng(talent_seed_value).branch(SeedScope.SEASON, "planned_player", country.code, sequence)
        talent_index = self.country_talent_model.talent_index(country)
        return self._generate_from_rng(
            country=country,
            sequence=sequence,
            player_rng=player_rng,
            talent_index=talent_index,
            quality_band=quality_band,
            bias_profile=bias_profile,
        )

    def _generate_from_rng(
        self,
        *,
        country: Country,
        sequence: int,
        player_rng: DeterministicRng,
        talent_index: float,
        quality_band: TalentQualityBand,
        bias_profile: CountryGenerationBiasProfile | None,
    ) -> Player:
        band_baseline_bonus, band_ceiling_bonus, age_shift = self._quality_band_parameters(quality_band)
        technical_lean = 0.0 if bias_profile is None else bias_profile.technical_vs_physical_lean
        mental_lean = 0.0 if bias_profile is None else bias_profile.mental_sharpness_tendency
        professional_lean = 0.0 if bias_profile is None else bias_profile.professionalism_tendency

        age = self._clamp_int(
            17,
            36,
            int(round(player_rng.uniform(17, 33) + (1.0 - talent_index) * 1.6 - age_shift)),
        )
        name = self._build_name(player_rng, country, sequence)

        archetype = player_rng.choice(self.identity_config.archetypes)
        play_style = player_rng.choice(self.identity_config.play_styles)

        technique = self._skill_value(
            player_rng,
            talent_index,
            country.development_pipeline_quality,
            band_baseline_bonus + technical_lean * 6.0,
        )
        movement = self._skill_value(player_rng, talent_index, country.infrastructure_level, band_baseline_bonus)
        physical = self._skill_value(
            player_rng,
            talent_index,
            self.country_talent_model.population_factor(country),
            band_baseline_bonus - technical_lean * 4.0,
        )
        mental = self._skill_value(
            player_rng,
            talent_index,
            country.historical_tradition,
            band_baseline_bonus + mental_lean * 6.0,
        )

        consistency = self._skill_value(player_rng, (technique + movement) / 200.0, country.elite_system_strength)
        clutch = self._skill_value(player_rng, mental / 99.0, country.historical_tradition)
        recovery = self._skill_value(player_rng, physical / 99.0, country.infrastructure_level)

        potential_floor = self._potential_floor_by_band(quality_band)
        hidden = HiddenCareerTraits(
            potential_ceiling=max(
                potential_floor,
                self._clamp_int(
                    55,
                    99,
                    int(round(66 + talent_index * 30 + band_ceiling_bonus + player_rng.uniform(-8, 8))),
                ),
            ),
            growth_curve=player_rng.choice(self.identity_config.growth_curves),
            professionalism=self._clamp_float(
                country.development_pipeline_quality * 0.62 + professional_lean * 0.33 + player_rng.uniform(0.10, 0.42)
            ),
            ambition=self._clamp_float(country.squash_popularity_norm * 0.50 + player_rng.uniform(0.12, 0.55)),
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

    def _skill_value(
        self,
        rng: DeterministicRng,
        talent_index: float,
        contextual_factor: float,
        additive_bonus: float = 0.0,
    ) -> int:
        baseline = 34 + talent_index * 36 + contextual_factor * 18 + additive_bonus
        noise = rng.uniform(-8.0, 8.0)
        return self._clamp_int(20, 99, int(round(baseline + noise)))

    def _travel_tolerance(self, country: Country, rng: DeterministicRng) -> float:
        if country.travel_affinity:
            affinity = sum(country.travel_affinity.values()) / len(country.travel_affinity)
        else:
            affinity = 0.5
        return self._clamp_float(affinity * 0.68 + rng.uniform(0.08, 0.42))

    @staticmethod
    def _quality_band_parameters(quality_band: TalentQualityBand) -> tuple[float, float, float]:
        if quality_band == TalentQualityBand.GENERATIONAL:
            return (22.0, 22.0, 1.1)
        if quality_band == TalentQualityBand.SPECIAL:
            return (14.0, 14.0, 0.8)
        if quality_band == TalentQualityBand.ELITE:
            return (9.0, 10.0, 0.5)
        if quality_band == TalentQualityBand.STRONG:
            return (4.0, 4.0, 0.2)
        return (0.0, 0.0, 0.0)

    @staticmethod
    def _potential_floor_by_band(quality_band: TalentQualityBand) -> int:
        if quality_band == TalentQualityBand.GENERATIONAL:
            return 94
        if quality_band == TalentQualityBand.SPECIAL:
            return 87
        if quality_band == TalentQualityBand.ELITE:
            return 80
        if quality_band == TalentQualityBand.STRONG:
            return 70
        return 55
