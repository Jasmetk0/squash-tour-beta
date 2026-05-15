"""Application service for Admin initial player-pool preview persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from beta_engine.application.countries_service import CountriesConfigService
from beta_engine.domain.players.initial_pool import (
    InitialPlayerPoolGenerator,
    InitialPoolGeneratedPlayer,
    InitialPoolRegistry,
    InitialPoolResult,
)
from beta_engine.infrastructure.world_config import load_player_identity_config


@dataclass(slots=True)
class InitialPlayerPoolService:
    countries_service: CountriesConfigService
    config_path: Path = Path("config/world/initial_player_pool.json")
    identity_config_path: Path = Path("config/world/player_identity.json")

    def __post_init__(self) -> None:
        if not isinstance(self.config_path, Path):
            self.config_path = Path(self.config_path)
        if not isinstance(self.identity_config_path, Path):
            self.identity_config_path = Path(self.identity_config_path)

    def get_pool(self, *, season: str = "2000/2001") -> InitialPoolResult:
        players = [player for player in self._load().players if player.created_for_season == season]
        generator = self._generator()
        return generator.generate(
            countries=self.countries_service.list_countries(),
            season=season,
            seed=0,
            target_pool_size=0,
            existing_locked_players=players,
            dry_run=True,
        )

    def generate_pool(self, *, season: str, seed: int, target_pool_size: int, dry_run: bool) -> InitialPoolResult:
        locked = [player for player in self._load().players if player.created_for_season == season and player.locked]
        result = self._generator().generate(
            countries=self.countries_service.list_countries(),
            season=season,
            seed=seed,
            target_pool_size=target_pool_size,
            existing_locked_players=locked,
            dry_run=dry_run,
        )
        if not dry_run:
            self._replace_season(season=season, players=result.players)
        return result

    def regenerate_unlocked(
        self,
        *,
        season: str,
        seed: int,
        target_pool_size: int | None,
        country_code: str | None,
        region: str | None,
        dry_run: bool,
    ) -> InitialPoolResult:
        current = [player for player in self._load().players if player.created_for_season == season]
        if not current:
            return self.generate_pool(season=season, seed=seed, target_pool_size=target_pool_size or 128, dry_run=dry_run)
        result = self._generator().regenerate_unlocked(
            countries=self.countries_service.list_countries(),
            current_players=current,
            season=season,
            seed=seed,
            target_pool_size=target_pool_size,
            country_code=country_code,
            region=region,
            dry_run=dry_run,
        )
        if not dry_run:
            self._replace_season(season=season, players=result.players)
        return result

    def set_lock(self, *, player_id: str, locked: bool) -> InitialPoolGeneratedPlayer:
        registry = self._load()
        players = []
        updated: InitialPoolGeneratedPlayer | None = None
        for player in registry.players:
            if player.player_id == player_id:
                updated = player.model_copy(update={"locked": locked})
                players.append(updated)
            else:
                players.append(player)
        if updated is None:
            raise KeyError(f"player '{player_id}' not found")
        self._save(InitialPoolRegistry(players=players))
        return updated

    def _generator(self) -> InitialPlayerPoolGenerator:
        identity = load_player_identity_config(self.identity_config_path) if self.identity_config_path.exists() else None
        return InitialPlayerPoolGenerator(identity_config=identity)

    def _load(self) -> InitialPoolRegistry:
        if not self.config_path.exists():
            return InitialPoolRegistry()
        return InitialPoolRegistry.model_validate(json.loads(self.config_path.read_text(encoding="utf-8")))

    def _save(self, registry: InitialPoolRegistry) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(registry.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")

    def _replace_season(self, *, season: str, players: list[InitialPoolGeneratedPlayer]) -> None:
        registry = self._load()
        retained = [player for player in registry.players if player.created_for_season != season]
        self._save(InitialPoolRegistry(players=[*retained, *players]))
