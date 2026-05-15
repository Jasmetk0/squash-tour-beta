"""Application service for bootstrapping first-season active players from the curated initial pool."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from beta_engine.application.initial_player_pool_service import InitialPlayerPoolService
from beta_engine.domain.players.initial_pool import GeneratedPlayerAttributes, InitialPoolGeneratedPlayer, PotentialTier
from beta_engine.domain.players.models import HiddenCareerTraits

SourceGeneration = Literal["initial_pool", "manual", "imported"]


class SeasonActivePlayer(BaseModel):
    """Canonical active-player record created by the initial-pool bootstrap boundary."""

    model_config = ConfigDict(extra="forbid")

    player_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=120)
    country_code: str = Field(min_length=3, max_length=3)
    nationality: str = Field(min_length=3, max_length=3)
    birth_year: int = Field(ge=1900, le=2100)
    birth_year_week: int = Field(ge=1, le=52)
    age_years_at_season_start: int = Field(ge=0, le=120)
    age_weeks_at_season_start: int = Field(ge=0)
    current_ability: int = Field(ge=1, le=99)
    potential_ability: int = Field(ge=1, le=99)
    potential_tier: PotentialTier
    career_stage: str = Field(min_length=1, max_length=80)
    play_style: str = Field(min_length=1, max_length=80)
    archetype: str = Field(min_length=1, max_length=80)
    attributes: GeneratedPlayerAttributes
    hidden_career_traits: HiddenCareerTraits
    health_status: str = "fresh"
    active_status: str = "active"
    ranking_points: int = Field(default=0, ge=0)
    race_points: int = Field(default=0, ge=0)
    protected_ranking_points: int = Field(default=0, ge=0)
    season: str = Field(min_length=4)
    source_pool_player_id: str = Field(min_length=1)
    source_generation_fingerprint: str = Field(min_length=1)
    source_generation: SourceGeneration
    manual_override: bool
    locked_from_initial_pool: bool
    bootstrap_fingerprint: str = Field(min_length=1)
    bootstrap_seed: int
    bootstrap_id: str = Field(min_length=1)

    @field_validator("country_code", "nationality")
    @classmethod
    def normalize_country_code(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_active_player(self) -> "SeasonActivePlayer":
        if self.current_ability > self.potential_ability + 4:
            raise ValueError("current_ability may not exceed potential_ability by more than 4")
        if self.hidden_career_traits.potential_ceiling < self.potential_ability:
            raise ValueError("potential_ceiling must be at least potential_ability")
        return self


class SeasonBootstrapSummary(BaseModel):
    total_active_players: int = 0
    countries_represented: int = 0
    manual_players: int = 0
    generated_players: int = 0
    locked_from_initial_pool: int = 0
    average_current_ability: float = 0.0
    average_potential_ability: float = 0.0
    by_potential_tier: dict[str, int] = Field(default_factory=dict)


class SeasonBootstrapMetadata(BaseModel):
    season: str
    source_season: str
    bootstrap_seed: int
    dry_run: bool
    overwrite_existing: bool
    source_initial_pool_fingerprint: str
    bootstrap_id: str
    bootstrap_fingerprint: str
    player_count: int
    persistence_path: str | None = None
    ranking_seeding_implemented: bool = False


class SeasonActivePlayersResponse(BaseModel):
    players: list[SeasonActivePlayer]
    summary: SeasonBootstrapSummary
    metadata: SeasonBootstrapMetadata | None = None
    warnings: list[str] = Field(default_factory=list)


class SeasonBootstrapResult(BaseModel):
    players: list[SeasonActivePlayer]
    summary: SeasonBootstrapSummary
    metadata: SeasonBootstrapMetadata
    warnings: list[str] = Field(default_factory=list)


class SeasonActivePlayersRegistry(BaseModel):
    """File-backed active-player registry keyed by season.

    The before validator accepts legacy/minimal shapes so early hand-authored files can be
    inspected without forcing a final database design before historical persistence exists.
    """

    players_by_season: dict[str, list[SeasonActivePlayer]] = Field(default_factory=dict)
    bootstrap_metadata_by_season: dict[str, SeasonBootstrapMetadata] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def load_legacy_registry(cls, value: object) -> object:
        if isinstance(value, list):
            return {"players_by_season": {"2000/2001": value}, "bootstrap_metadata_by_season": {}}
        if isinstance(value, dict) and "players" in value and "season" in value:
            season = str(value.get("season"))
            return {"players_by_season": {season: value.get("players", [])}, "bootstrap_metadata_by_season": {}}
        if isinstance(value, dict) and "players_by_season" not in value:
            return {"players_by_season": value, "bootstrap_metadata_by_season": {}}
        return value


@dataclass(slots=True)
class InitialPoolSeasonBootstrapService:
    initial_pool_service: InitialPlayerPoolService
    active_players_path: Path = Path("config/world/season_active_players.json")

    def __post_init__(self) -> None:
        if not isinstance(self.active_players_path, Path):
            self.active_players_path = Path(self.active_players_path)

    def get_active_players(self, *, season: str) -> SeasonActivePlayersResponse:
        registry = self._load_registry()
        players = list(registry.players_by_season.get(season, []))
        return SeasonActivePlayersResponse(
            players=players,
            summary=self._summary(players),
            metadata=registry.bootstrap_metadata_by_season.get(season),
            warnings=[],
        )

    def bootstrap_from_initial_pool(
        self,
        *,
        season: str = "2000/2001",
        source_season: str | None = None,
        seed: int = 12345,
        dry_run: bool = True,
        overwrite_existing: bool = False,
    ) -> SeasonBootstrapResult:
        source = source_season or season
        source_result = self.initial_pool_service.get_pool(season=source)
        source_players = list(source_result.players)
        if not source_players:
            raise ValueError("Cannot bootstrap season because initial pool is empty. Persist an initial pool first.")
        self._validate_source_players(source_players)

        registry = self._load_registry()
        if not dry_run and registry.players_by_season.get(season) and not overwrite_existing:
            raise ValueError(f"Active players already exist for season '{season}'. Set overwrite_existing=true to replace only that season.")

        source_fingerprint = self._source_pool_fingerprint(source_players, source_season=source)
        bootstrap_id = self._bootstrap_id(season=season, source_season=source, seed=seed, source_fingerprint=source_fingerprint)
        players = [
            self._convert_player(player, season=season, seed=seed, bootstrap_id=bootstrap_id, source_fingerprint=source_fingerprint)
            for player in sorted(source_players, key=lambda item: item.player_id)
        ]
        warnings = self._warnings(players)
        summary = self._summary(players)
        operation_fingerprint = self._operation_fingerprint(players=players, season=season, source_season=source, seed=seed, source_fingerprint=source_fingerprint)
        metadata = SeasonBootstrapMetadata(
            season=season,
            source_season=source,
            bootstrap_seed=seed,
            dry_run=dry_run,
            overwrite_existing=overwrite_existing,
            source_initial_pool_fingerprint=source_fingerprint,
            bootstrap_id=bootstrap_id,
            bootstrap_fingerprint=operation_fingerprint,
            player_count=len(players),
            persistence_path=None if dry_run else str(self.active_players_path),
            ranking_seeding_implemented=False,
        )
        result = SeasonBootstrapResult(players=players, summary=summary, metadata=metadata, warnings=warnings)
        if not dry_run:
            next_players = dict(registry.players_by_season)
            next_metadata = dict(registry.bootstrap_metadata_by_season)
            next_players[season] = players
            next_metadata[season] = metadata
            self._save_registry(SeasonActivePlayersRegistry(players_by_season=next_players, bootstrap_metadata_by_season=next_metadata))
        return result

    def _convert_player(
        self,
        player: InitialPoolGeneratedPlayer,
        *,
        season: str,
        seed: int,
        bootstrap_id: str,
        source_fingerprint: str,
    ) -> SeasonActivePlayer:
        season_start_year = self._season_start_year(season)
        age_years = season_start_year - player.birth_year
        age_weeks = max(0, age_years * 52 + (1 - player.birth_year_week))
        source_generation: SourceGeneration = "manual" if player.manual_override or player.generation_source == "manual" else "initial_pool"
        fingerprint = self._player_bootstrap_fingerprint(
            season=season,
            seed=seed,
            source_fingerprint=source_fingerprint,
            player_id=player.player_id,
            player_fingerprint=player.generation_fingerprint,
        )
        return SeasonActivePlayer(
            player_id=player.player_id,
            name=player.name,
            country_code=player.country_code,
            nationality=player.nationality or player.country_code,
            birth_year=player.birth_year,
            birth_year_week=player.birth_year_week,
            age_years_at_season_start=age_years,
            age_weeks_at_season_start=age_weeks,
            current_ability=player.current_ability,
            potential_ability=player.potential_ability,
            potential_tier=player.potential_tier,
            career_stage=player.career_stage,
            play_style=player.play_style,
            archetype=player.archetype,
            attributes=player.attributes,
            hidden_career_traits=player.hidden_career_traits,
            health_status="fresh",
            active_status="active",
            ranking_points=0,
            race_points=0,
            protected_ranking_points=0,
            season=season,
            source_pool_player_id=player.player_id,
            source_generation_fingerprint=player.generation_fingerprint,
            source_generation=source_generation,
            manual_override=player.manual_override,
            locked_from_initial_pool=player.locked,
            bootstrap_fingerprint=fingerprint,
            bootstrap_seed=seed,
            bootstrap_id=bootstrap_id,
        )

    def _load_registry(self) -> SeasonActivePlayersRegistry:
        if not self.active_players_path.exists():
            return SeasonActivePlayersRegistry()
        return SeasonActivePlayersRegistry.model_validate(json.loads(self.active_players_path.read_text(encoding="utf-8")))

    def _save_registry(self, registry: SeasonActivePlayersRegistry) -> None:
        self.active_players_path.parent.mkdir(parents=True, exist_ok=True)
        self.active_players_path.write_text(json.dumps(registry.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _season_start_year(season: str) -> int:
        try:
            return int(season.split("/", 1)[0])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid season '{season}'. Expected a label like 2000/2001.") from exc

    @staticmethod
    def _hash(material: str, *, digest_size: int = 16) -> str:
        return hashlib.blake2b(material.encode(), digest_size=digest_size).hexdigest()

    def _source_pool_fingerprint(self, players: list[InitialPoolGeneratedPlayer], *, source_season: str) -> str:
        material = "|".join(player.model_dump_json() for player in sorted(players, key=lambda item: item.player_id))
        return self._hash(f"initial-pool|{source_season}|{material}")

    def _bootstrap_id(self, *, season: str, source_season: str, seed: int, source_fingerprint: str) -> str:
        suffix = self._hash(f"bootstrap-id|{season}|{source_season}|{seed}|{source_fingerprint}", digest_size=8)
        return f"BOOT-{season.split('/')[0]}-{suffix}"

    def _player_bootstrap_fingerprint(self, *, season: str, seed: int, source_fingerprint: str, player_id: str, player_fingerprint: str) -> str:
        return self._hash(f"player-bootstrap|{season}|{seed}|{source_fingerprint}|{player_id}|{player_fingerprint}")

    def _operation_fingerprint(self, *, players: list[SeasonActivePlayer], season: str, source_season: str, seed: int, source_fingerprint: str) -> str:
        material = "|".join(player.bootstrap_fingerprint for player in sorted(players, key=lambda item: item.player_id))
        return self._hash(f"operation|{season}|{source_season}|{seed}|{source_fingerprint}|{material}")

    def _validate_source_players(self, players: list[InitialPoolGeneratedPlayer]) -> None:
        ids = [player.player_id for player in players]
        duplicates = sorted(player_id for player_id, count in Counter(ids).items() if count > 1)
        if duplicates:
            raise ValueError(f"Duplicate source initial-pool player IDs are not allowed: {', '.join(duplicates)}")

    def _warnings(self, players: list[SeasonActivePlayer]) -> list[str]:
        warnings: list[str] = []
        if len(players) < 32:
            warnings.append("Source initial pool is very small for a professional tour bootstrap.")
        if not any(player.potential_tier in {"S", "A"} for player in players):
            warnings.append("Source initial pool has no S/A-tier players.")
        if not {player.country_code for player in players}:
            warnings.append("Source initial pool has no countries represented.")
        if not any(player.manual_override for player in players):
            warnings.append("Source initial pool has no manual players; this is informational only.")
        return warnings

    def _summary(self, players: list[SeasonActivePlayer]) -> SeasonBootstrapSummary:
        if not players:
            return SeasonBootstrapSummary()
        by_tier = Counter(player.potential_tier for player in players)
        return SeasonBootstrapSummary(
            total_active_players=len(players),
            countries_represented=len({player.country_code for player in players}),
            manual_players=sum(1 for player in players if player.manual_override),
            generated_players=sum(1 for player in players if player.source_generation == "initial_pool"),
            locked_from_initial_pool=sum(1 for player in players if player.locked_from_initial_pool),
            average_current_ability=round(sum(player.current_ability for player in players) / len(players), 2),
            average_potential_ability=round(sum(player.potential_ability for player in players) / len(players), 2),
            by_potential_tier=dict(sorted(by_tier.items())),
        )
