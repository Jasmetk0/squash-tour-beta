"""Deterministic initial player-pool preview and regeneration foundation."""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from beta_engine.core import DeterministicRng, SeedScope
from beta_engine.domain.countries import Country
from beta_engine.domain.players.models import HiddenCareerTraits
from beta_engine.infrastructure.world_config import PlayerIdentityConfig

CareerStage = Literal["junior", "developing", "breakthrough", "prime", "veteran", "late_career"]
PotentialTier = Literal["S", "A", "B", "C", "D"]
GenerationSource = Literal["initial_pool", "annual_intake", "manual", "imported"]
InitialPoolAuditAction = Literal["create_custom_player", "update_player", "lock_player", "unlock_player", "regenerate_unlocked", "generate_pool"]

DEFAULT_ARCHETYPES = (
    "all_court",
    "power_attacker",
    "counterpuncher",
    "retriever",
    "shotmaker",
    "attritional_runner",
    "tactical_controller",
)
DEFAULT_PLAY_STYLES = (
    "balanced",
    "front_court_attacker",
    "counter_attacker",
    "defensive_retriever",
    "creative_shotmaker",
    "attritional_runner",
    "tempo_controller",
)
DEFAULT_GROWTH_CURVES = ("early", "steady", "late", "volatile")
DEFAULT_GIVEN_NAMES = ("Adam", "Karim", "Miguel", "Sam", "Jonas", "Leo", "Omar", "Ravi", "Tariq", "Youssef")
DEFAULT_FAMILY_NAMES = ("Ahmed", "Khan", "Rossi", "Smith", "Patel", "Garcia", "Hassan", "Muller", "Ali", "Brown")

STAGE_AGE_RANGES: dict[CareerStage, tuple[int, int]] = {
    "junior": (15, 18),
    "developing": (18, 22),
    "breakthrough": (20, 24),
    "prime": (24, 30),
    "veteran": (30, 34),
    "late_career": (35, 45),
}
STAGE_WEIGHTS: tuple[tuple[CareerStage, float], ...] = (
    ("junior", 0.14),
    ("developing", 0.20),
    ("breakthrough", 0.18),
    ("prime", 0.26),
    ("veteran", 0.14),
    ("late_career", 0.08),
)


class GeneratedPlayerAttributes(BaseModel):
    technique: int = Field(ge=1, le=99)
    movement: int = Field(ge=1, le=99)
    physical: int = Field(ge=1, le=99)
    mental: int = Field(ge=1, le=99)
    consistency: int = Field(ge=1, le=99)
    clutch: int = Field(ge=1, le=99)
    recovery: int = Field(ge=1, le=99)


class InitialPoolAuditEvent(BaseModel):
    """Compact audit record for intentional Admin initial-pool mutations."""

    model_config = ConfigDict(extra="forbid")

    audit_id: str
    timestamp_utc: str | None = None
    actor: str = "admin"
    action: InitialPoolAuditAction
    player_id: str | None = None
    season: str
    reason: str | None = None
    changed_fields: list[str] = Field(default_factory=list)
    before_fingerprint: str | None = None
    after_fingerprint: str | None = None


class InitialPoolAuditList(BaseModel):
    audit_events: list[InitialPoolAuditEvent] = Field(default_factory=list)


class CustomInitialPoolPlayerCreate(BaseModel):
    """Validated command payload for manual initial-pool player creation."""

    model_config = ConfigDict(extra="forbid")

    player_id: str | None = None
    name: str = Field(min_length=1, max_length=120)
    country_code: str = Field(min_length=3, max_length=3)
    nationality: str | None = Field(default=None, min_length=3, max_length=3)
    birth_year: int = Field(ge=1900, le=2100)
    birth_year_week: int = Field(ge=1, le=52)
    current_ability: int = Field(ge=1, le=99)
    potential_ability: int = Field(ge=1, le=99)
    potential_tier: PotentialTier
    career_stage: CareerStage
    play_style: str = Field(min_length=1, max_length=80)
    archetype: str = Field(min_length=1, max_length=80)
    attributes: GeneratedPlayerAttributes
    hidden_career_traits: HiddenCareerTraits
    created_for_season: str = "2000/2001"
    reason: str | None = Field(default=None, max_length=500)
    actor: str = Field(default="admin", min_length=1, max_length=80)

    @field_validator("country_code", "nationality")
    @classmethod
    def normalize_country_code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @field_validator("player_id", "name", "play_style", "archetype", "reason", "actor")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None

    @model_validator(mode="after")
    def validate_custom_player(self) -> "CustomInitialPoolPlayerCreate":
        if self.current_ability > self.potential_ability + 4:
            raise ValueError("current_ability may not exceed potential_ability by more than 4")
        if self.hidden_career_traits.potential_ceiling < self.potential_ability:
            raise ValueError("potential_ceiling must be at least potential_ability")
        if self.nationality is None:
            self.nationality = self.country_code
        return self


class InitialPoolPlayerUpdate(BaseModel):
    """Safe partial update payload for Admin initial-pool edits."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    nationality: str | None = Field(default=None, min_length=3, max_length=3)
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    birth_year_week: int | None = Field(default=None, ge=1, le=52)
    current_ability: int | None = Field(default=None, ge=1, le=99)
    potential_ability: int | None = Field(default=None, ge=1, le=99)
    potential_tier: PotentialTier | None = None
    career_stage: CareerStage | None = None
    play_style: str | None = Field(default=None, min_length=1, max_length=80)
    archetype: str | None = Field(default=None, min_length=1, max_length=80)
    attributes: GeneratedPlayerAttributes | None = None
    hidden_career_traits: HiddenCareerTraits | None = None
    reason: str | None = Field(default=None, max_length=500)
    actor: str = Field(default="admin", min_length=1, max_length=80)

    @field_validator("nationality")
    @classmethod
    def normalize_country_code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @field_validator("name", "play_style", "archetype", "reason", "actor")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class InitialPoolGeneratedPlayer(BaseModel):
    """Canonical DTO for inspectable pre-season initial-pool generation."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    name: str
    country_code: str = Field(min_length=3, max_length=3)
    nationality: str | None = None
    birth_year: int = Field(ge=1900, le=2100)
    birth_year_week: int = Field(ge=1, le=52)
    age_at_generation: int = Field(ge=15, le=45)
    current_age_years: int = Field(ge=15, le=45)
    current_ability: int = Field(ge=1, le=99)
    potential_ability: int = Field(ge=1, le=99)
    potential_tier: PotentialTier
    career_stage: CareerStage
    play_style: str
    archetype: str
    attributes: GeneratedPlayerAttributes
    hidden_career_traits: HiddenCareerTraits
    locked: bool
    generation_source: GenerationSource
    manual_override: bool
    generation_seed: int
    generation_fingerprint: str
    created_for_season: str = "2000/2001"

    @model_validator(mode="after")
    def validate_pool_player(self) -> "InitialPoolGeneratedPlayer":
        if self.current_ability > self.potential_ability + 4:
            raise ValueError("current_ability may not exceed potential_ability by more than 4")
        if self.hidden_career_traits.potential_ceiling < self.potential_ability:
            raise ValueError("potential_ceiling must be at least potential_ability")
        if self.nationality is None:
            self.nationality = self.country_code
        return self

    @field_validator("country_code", "nationality")
    @classmethod
    def normalize_country_code(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None


class InitialPoolMetadata(BaseModel):
    season: str
    seed: int
    target_pool_size: int
    country_code: str | None = None
    region: str | None = None
    dry_run: bool = True
    generated_count: int
    preserved_locked_count: int = 0
    changed_count: int = 0
    generation_fingerprint: str


class InitialPoolSummary(BaseModel):
    total_players: int
    locked_players: int
    unlocked_players: int
    countries_represented: int
    average_current_ability: float
    average_potential_ability: float
    by_country: dict[str, int]
    by_career_stage: dict[str, int]
    by_potential_tier: dict[str, int]


class InitialPoolResult(BaseModel):
    players: list[InitialPoolGeneratedPlayer]
    summary: InitialPoolSummary
    metadata: InitialPoolMetadata


class InitialPoolRegistry(BaseModel):
    players: list[InitialPoolGeneratedPlayer] = Field(default_factory=list)
    audit_events: list[InitialPoolAuditEvent] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def load_legacy_registry(cls, value: object) -> object:
        if isinstance(value, list):
            return {"players": value, "audit_events": []}
        if isinstance(value, dict) and "audit_events" not in value:
            return {**value, "audit_events": []}
        return value


@dataclass(slots=True)
class InitialPlayerPoolGenerator:
    identity_config: PlayerIdentityConfig | None = None

    def generate(
        self,
        *,
        countries: list[Country],
        season: str = "2000/2001",
        seed: int,
        target_pool_size: int = 128,
        country_code: str | None = None,
        region: str | None = None,
        existing_locked_players: list[InitialPoolGeneratedPlayer] | None = None,
        dry_run: bool = True,
    ) -> InitialPoolResult:
        selected = self._filter_countries(countries, country_code=country_code, region=region)
        if not selected:
            raise ValueError("initial pool generation requires at least one matching country")
        locked = sorted(existing_locked_players or [], key=lambda player: player.player_id)
        unlocked_slots = max(0, target_pool_size - len(locked))
        allocations = self._allocate_counts(selected, unlocked_slots, seed=seed, season=season)
        generated: list[InitialPoolGeneratedPlayer] = []
        locked_sequences = {country.code: self._locked_sequences_for_country(locked, country.code) for country in selected}
        for country in selected:
            sequence = 1
            generated_for_country = 0
            while generated_for_country < allocations[country.code]:
                if sequence not in locked_sequences[country.code]:
                    generated.append(self._generate_player(country=country, season=season, seed=seed, sequence=sequence))
                    generated_for_country += 1
                sequence += 1
        players = sorted([*locked, *generated], key=lambda player: (player.country_code, player.player_id))
        fingerprint = self._fingerprint(players, season=season, seed=seed)
        return InitialPoolResult(
            players=players,
            summary=self._summarize(players),
            metadata=InitialPoolMetadata(
                season=season,
                seed=seed,
                target_pool_size=target_pool_size,
                country_code=country_code.upper() if country_code else None,
                region=region,
                dry_run=dry_run,
                generated_count=len(generated),
                preserved_locked_count=len(locked),
                changed_count=len(generated),
                generation_fingerprint=fingerprint,
            ),
        )

    def regenerate_unlocked(
        self,
        *,
        countries: list[Country],
        current_players: list[InitialPoolGeneratedPlayer],
        season: str,
        seed: int,
        target_pool_size: int | None = None,
        country_code: str | None = None,
        region: str | None = None,
        dry_run: bool = True,
    ) -> InitialPoolResult:
        country_codes = {country.code for country in self._filter_countries(countries, country_code=country_code, region=region)}
        scoped_locked = [player for player in current_players if player.country_code in country_codes and player.locked]
        outside_scope = [player for player in current_players if player.country_code not in country_codes]
        current_scope_count = sum(1 for player in current_players if player.country_code in country_codes)
        scope_target = max(current_scope_count, len(scoped_locked)) if target_pool_size is None else target_pool_size
        scoped = self.generate(
            countries=countries,
            season=season,
            seed=seed,
            target_pool_size=scope_target,
            country_code=country_code,
            region=region,
            existing_locked_players=scoped_locked,
            dry_run=dry_run,
        )
        players = sorted([*outside_scope, *scoped.players], key=lambda player: (player.country_code, player.player_id))
        fingerprint = self._fingerprint(players, season=season, seed=seed)
        return InitialPoolResult(
            players=players,
            summary=self._summarize(players),
            metadata=scoped.metadata.model_copy(
                update={
                    "target_pool_size": len(players),
                    "generated_count": len(scoped.players) - len(scoped_locked),
                    "preserved_locked_count": len(scoped_locked),
                    "changed_count": len(scoped.players) - len(scoped_locked),
                    "generation_fingerprint": fingerprint,
                }
            ),
        )

    def _locked_sequences_for_country(self, players: list[InitialPoolGeneratedPlayer], country_code: str) -> set[int]:
        sequences: set[int] = set()
        for player in players:
            if player.country_code != country_code:
                continue
            try:
                sequences.add(int(player.player_id.rsplit("-", 1)[1]))
            except (IndexError, ValueError):
                continue
        return sequences

    def _filter_countries(self, countries: list[Country], *, country_code: str | None, region: str | None) -> list[Country]:
        items = countries
        if country_code:
            normalized = country_code.upper()
            items = [country for country in items if country.code == normalized]
        if region:
            items = [country for country in items if country.region == region or country.effective_travel_region == region]
        return sorted(items, key=lambda country: country.code)

    def _allocate_counts(self, countries: list[Country], target: int, *, seed: int, season: str) -> dict[str, int]:
        if target <= 0:
            return {country.code: 0 for country in countries}
        weights = {country.code: self._quantity_weight(country) for country in countries}
        total = sum(weights.values())
        counts = {country.code: int((weights[country.code] / total) * target) for country in countries}
        for country in countries:
            if counts[country.code] == 0 and target >= len(countries):
                counts[country.code] = 1
        remainder = target - sum(counts.values())
        ranked = sorted(countries, key=lambda c: (-((weights[c.code] / total) * target - int((weights[c.code] / total) * target)), c.code))
        index = 0
        while remainder > 0:
            counts[ranked[index % len(ranked)].code] += 1
            remainder -= 1
            index += 1
        while remainder < 0:
            removable = sorted(countries, key=lambda c: (-counts[c.code], c.code))
            for country in removable:
                if counts[country.code] > 0:
                    counts[country.code] -= 1
                    remainder += 1
                    break
        return counts

    def _generate_player(self, *, country: Country, season: str, seed: int, sequence: int) -> InitialPoolGeneratedPlayer:
        rng = DeterministicRng(seed).branch(SeedScope.SEASON, "initial_pool", season, country.code, sequence)
        quality = self._country_quality(country)
        stage = self._choose_stage(rng)
        age_min, age_max = STAGE_AGE_RANGES[stage]
        age = rng.randint(age_min, age_max)
        season_start_year = int(season.split("/")[0])
        birth_week = rng.randint(1, 52)
        birth_year = season_start_year - age
        potential_tier, potential = self._potential(rng, quality)
        growth_curve = rng.choice(self._identity().growth_curves)
        current = self._current_ability(rng, age=age, potential=potential, growth_curve=growth_curve)
        archetype = self._choose_from_style_dna(country, rng, self._identity().archetypes)
        play_style = self._identity().play_styles[self._identity().archetypes.index(archetype) % len(self._identity().play_styles)] if archetype in self._identity().archetypes else rng.choice(self._identity().play_styles)
        attributes = self._attributes(rng, current=current, archetype=archetype)
        hidden = HiddenCareerTraits(
            potential_ceiling=potential,
            growth_curve=growth_curve,
            professionalism=self._clamp01(0.25 + country.system_quality_norm * 0.45 + rng.uniform(-0.08, 0.25)),
            ambition=self._clamp01(0.25 + country.squash_popularity_norm * 0.35 + rng.uniform(-0.05, 0.35)),
            travel_tolerance=self._clamp01(0.35 + country.wealth_support_norm * 0.25 + rng.uniform(-0.12, 0.32)),
            schedule_aggression=self._clamp01(0.20 + rng.uniform(0.0, 0.65)),
            injury_proneness=self._clamp01(0.45 - country.system_quality_norm * 0.16 + rng.uniform(-0.18, 0.28)),
            resilience=self._clamp01(0.25 + country.squash_tradition_norm * 0.30 + rng.uniform(-0.05, 0.38)),
        )
        player_id = f"P-{season_start_year}-{country.code}-{sequence:04d}"
        fingerprint = hashlib.blake2b(f"{season}|{seed}|{country.code}|{sequence}".encode(), digest_size=8).hexdigest()
        return InitialPoolGeneratedPlayer(
            player_id=player_id,
            name=self._name(rng, country, sequence),
            country_code=country.code,
            nationality=country.code,
            birth_year=birth_year,
            birth_year_week=birth_week,
            age_at_generation=age,
            current_age_years=age,
            current_ability=current,
            potential_ability=potential,
            potential_tier=potential_tier,
            career_stage=stage,
            play_style=play_style,
            archetype=archetype,
            attributes=attributes,
            hidden_career_traits=hidden,
            locked=False,
            generation_source="initial_pool",
            manual_override=False,
            generation_seed=rng.seed.value,
            generation_fingerprint=fingerprint,
            created_for_season=season,
        )

    def _identity(self) -> PlayerIdentityConfig:
        return self.identity_config or PlayerIdentityConfig(
            given_names=list(DEFAULT_GIVEN_NAMES),
            family_names=list(DEFAULT_FAMILY_NAMES),
            play_styles=list(DEFAULT_PLAY_STYLES),
            archetypes=list(DEFAULT_ARCHETYPES),
            growth_curves=list(DEFAULT_GROWTH_CURVES),
        )

    def _quantity_weight(self, country: Country) -> float:
        population_component = min(3.0, (country.population / 5_000_000) ** 0.35)
        courts = 0.25 if country.court_count is None else min(1.4, (country.court_count / 300) ** 0.35)
        culture = 0.55 + country.squash_popularity_norm + country.squash_tradition_norm * 0.85
        system = 0.45 + country.system_quality_norm * 0.85 + ((country.competition_density or 3.0) - 1) / 4 * 0.45
        return max(0.1, population_component * 0.65 + culture * 0.9 + system * 0.8 + courts * 0.35)

    def _country_quality(self, country: Country) -> float:
        competition = ((country.competition_density or 3.0) - 1) / 4
        federation = ((country.federation_quality or float(country.system_quality)) - 1) / 4
        courts = 0.35 if country.court_count is None else min(1.0, (country.court_count / 900) ** 0.4)
        return self._clamp01(
            country.squash_popularity_norm * 0.17
            + country.squash_tradition_norm * 0.22
            + country.system_quality_norm * 0.24
            + competition * 0.12
            + federation * 0.12
            + country.wealth_support_norm * 0.08
            + courts * 0.05
        )

    def _choose_stage(self, rng: DeterministicRng) -> CareerStage:
        roll = rng.random()
        cumulative = 0.0
        for stage, weight in STAGE_WEIGHTS:
            cumulative += weight
            if roll <= cumulative:
                return stage
        return "prime"

    def _potential(self, rng: DeterministicRng, quality: float) -> tuple[PotentialTier, int]:
        score = self._clamp01(quality * 0.72 + rng.random() * 0.42)
        if score >= 0.88:
            return "S", rng.randint(91, 99)
        if score >= 0.72:
            return "A", rng.randint(82, 92)
        if score >= 0.52:
            return "B", rng.randint(72, 84)
        if score >= 0.30:
            return "C", rng.randint(60, 74)
        return "D", rng.randint(50, 62)

    def _current_ability(self, rng: DeterministicRng, *, age: int, potential: int, growth_curve: str) -> int:
        if age < 18:
            factor = 0.48 + (age - 15) * 0.055
        elif age < 23:
            factor = 0.62 + (age - 18) * 0.045
        elif age < 30:
            factor = 0.82 + (age - 23) * 0.025
        elif age < 35:
            factor = 0.93 - (age - 30) * 0.018
        else:
            factor = 0.84 - (age - 35) * 0.025
        if growth_curve == "early":
            factor += 0.05 if age <= 24 else -0.01
        elif growth_curve == "late":
            factor += -0.05 if age <= 22 else 0.03
        elif growth_curve == "volatile":
            factor += rng.uniform(-0.05, 0.05)
        return max(1, min(99, potential + 4, int(round(potential * factor + rng.uniform(-4, 4)))))

    def _attributes(self, rng: DeterministicRng, *, current: int, archetype: str) -> GeneratedPlayerAttributes:
        leans = {
            "power_attacker": {"physical": 6, "clutch": 3, "recovery": -3},
            "counterpuncher": {"movement": 4, "mental": 4, "technique": -1},
            "retriever": {"movement": 6, "recovery": 5, "technique": -3},
            "shotmaker": {"technique": 7, "clutch": 3, "physical": -3},
            "attritional_runner": {"physical": 5, "recovery": 6, "clutch": -2},
            "tactical_controller": {"mental": 7, "consistency": 4, "physical": -2},
        }.get(archetype, {})
        values = {}
        for attr in ("technique", "movement", "physical", "mental", "consistency", "clutch", "recovery"):
            values[attr] = max(1, min(99, int(round(current + leans.get(attr, 0) + rng.uniform(-6, 6)))))
        return GeneratedPlayerAttributes(**values)

    def _choose_from_style_dna(self, country: Country, rng: DeterministicRng, options: list[str]) -> str:
        positive = [(key, weight) for key, weight in country.style_dna.items() if key in options and weight > 0]
        if not positive:
            return rng.choice(options)
        total = sum(weight for _, weight in positive)
        roll = rng.random() * total
        cumulative = 0.0
        for key, weight in sorted(positive):
            cumulative += weight
            if roll <= cumulative:
                return key
        return positive[-1][0]

    def _name(self, rng: DeterministicRng, country: Country, sequence: int) -> str:
        identity = self._identity()
        return f"{rng.choice(identity.given_names)} {rng.choice(identity.family_names)} {country.code[:2]}{sequence:02d}"

    def _summarize(self, players: list[InitialPoolGeneratedPlayer]) -> InitialPoolSummary:
        count = len(players)
        return InitialPoolSummary(
            total_players=count,
            locked_players=sum(1 for player in players if player.locked),
            unlocked_players=sum(1 for player in players if not player.locked),
            countries_represented=len({player.country_code for player in players}),
            average_current_ability=round(sum(player.current_ability for player in players) / count, 2) if count else 0.0,
            average_potential_ability=round(sum(player.potential_ability for player in players) / count, 2) if count else 0.0,
            by_country=dict(sorted(Counter(player.country_code for player in players).items())),
            by_career_stage=dict(sorted(Counter(player.career_stage for player in players).items())),
            by_potential_tier=dict(sorted(Counter(player.potential_tier for player in players).items())),
        )

    def _fingerprint(self, players: list[InitialPoolGeneratedPlayer], *, season: str, seed: int) -> str:
        material = "|".join([season, str(seed), *(player.model_dump_json() for player in players)])
        return hashlib.blake2b(material.encode(), digest_size=16).hexdigest()

    @staticmethod
    def _clamp01(value: float) -> float:
        return round(max(0.0, min(1.0, value)), 4)
