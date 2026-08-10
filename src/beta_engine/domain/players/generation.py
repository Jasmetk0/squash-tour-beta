"""Deterministic player generator influenced by country development environment."""

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
        development_environment = self.country_talent_model.development_environment(country)
        return self._generate_from_rng(
            country=country,
            sequence=sequence,
            player_rng=player_rng,
            development_environment=development_environment,
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
        development_environment = self.country_talent_model.development_environment(country)
        return self._generate_from_rng(
            country=country,
            sequence=sequence,
            player_rng=player_rng,
            development_environment=development_environment,
            quality_band=quality_band,
            bias_profile=bias_profile,
        )

    def _generate_from_rng(
        self,
        *,
        country: Country,
        sequence: int,
        player_rng: DeterministicRng,
        development_environment: float,
        quality_band: TalentQualityBand,
        bias_profile: CountryGenerationBiasProfile | None,
    ) -> Player:
        band_baseline_bonus, _band_ceiling_bonus, age_shift = self._quality_band_parameters(quality_band)
        technical_lean = 0.0 if bias_profile is None else bias_profile.technical_vs_physical_lean
        mental_lean = 0.0 if bias_profile is None else bias_profile.mental_sharpness_tendency
        professional_lean = 0.0 if bias_profile is None else bias_profile.professionalism_tendency

        age = self._clamp_int(
            17,
            36,
            int(round(player_rng.uniform(17, 33) + (1.0 - development_environment) * 1.6 - age_shift)),
        )
        name = self._build_name(player_rng, country, sequence)

        archetype = player_rng.choice(self.identity_config.archetypes)
        play_style = player_rng.choice(self.identity_config.play_styles)

        # Country V1 affects realised development environment, not innate talent.
        technique = self._skill_value(
            player_rng,
            development_environment,
            country.development_quality_norm,
            band_baseline_bonus + technical_lean * 6.0,
        )
        movement = self._skill_value(
            player_rng,
            development_environment,
            country.squash_access_norm,
            band_baseline_bonus,
        )
        physical = self._skill_value(
            player_rng,
            development_environment,
            country.development_quality_norm,
            band_baseline_bonus - technical_lean * 4.0,
        )
        mental = self._skill_value(
            player_rng,
            development_environment,
            country.competition_quality_norm,
            band_baseline_bonus + mental_lean * 6.0,
        )

        consistency = self._skill_value(player_rng, (technique + movement) / 200.0, country.competition_quality_norm)
        clutch = self._skill_value(player_rng, mental / 99.0, country.competition_quality_norm)
        recovery = self._skill_value(player_rng, physical / 99.0, country.development_quality_norm)

        potential_floor = self._potential_floor_by_band(quality_band)
        potential_center = self._potential_center_by_band(quality_band)
        potential_spread = self._potential_spread_by_band(quality_band)
        hidden = HiddenCareerTraits(
            potential_ceiling=max(
                potential_floor,
                self._clamp_int(
                    55,
                    99,
                    # Innate ceiling depends on rarity band + deterministic RNG,
                    # never on the country development ratings. Even the rarest
                    # band keeps a small distribution instead of becoming 99/99.
                    int(round(potential_center + player_rng.uniform(-potential_spread, potential_spread))),
                ),
            ),
            growth_curve=player_rng.choice(self.identity_config.growth_curves),
            professionalism=self._clamp_float(0.48 + professional_lean * 0.20 + player_rng.uniform(-0.22, 0.24)),
            ambition=self._clamp_float(player_rng.uniform(0.22, 0.88)),
            travel_tolerance=self._travel_tolerance(player_rng),
            schedule_aggression=self._clamp_float(player_rng.uniform(0.18, 0.82)),
            injury_proneness=self._clamp_float(player_rng.uniform(0.08, 0.72)),
            resilience=self._clamp_float(player_rng.uniform(0.22, 0.90)),
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
        development_environment: float,
        contextual_factor: float,
        additive_bonus: float = 0.0,
    ) -> int:
        baseline = 34 + development_environment * 36 + contextual_factor * 18 + additive_bonus
        noise = rng.uniform(-8.0, 8.0)
        return self._clamp_int(20, 99, int(round(baseline + noise)))

    def _travel_tolerance(self, rng: DeterministicRng) -> float:
        return self._clamp_float(rng.uniform(0.18, 0.86))

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
        return {
            TalentQualityBand.SOLID: 55,
            TalentQualityBand.STRONG: 70,
            TalentQualityBand.ELITE: 80,
            TalentQualityBand.SPECIAL: 87,
            TalentQualityBand.GENERATIONAL: 94,
        }[quality_band]

    @staticmethod
    def _potential_center_by_band(quality_band: TalentQualityBand) -> float:
        return {
            TalentQualityBand.SOLID: 67.0,
            TalentQualityBand.STRONG: 76.0,
            TalentQualityBand.ELITE: 85.0,
            TalentQualityBand.SPECIAL: 92.0,
            TalentQualityBand.GENERATIONAL: 97.0,
        }[quality_band]

    @staticmethod
    def _potential_spread_by_band(quality_band: TalentQualityBand) -> float:
        return {
            TalentQualityBand.SOLID: 8.0,
            TalentQualityBand.STRONG: 7.0,
            TalentQualityBand.ELITE: 6.0,
            TalentQualityBand.SPECIAL: 5.0,
            TalentQualityBand.GENERATIONAL: 3.0,
        }[quality_band]
