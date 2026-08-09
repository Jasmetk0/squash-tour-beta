"""Application service for Admin initial player-pool preview persistence."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from beta_engine.application.countries_service import CountriesConfigService
from beta_engine.domain.players.initial_pool import (
    CustomInitialPoolPlayerCreate,
    InitialPlayerPoolGenerator,
    InitialPoolAuditEvent,
    InitialPoolAuditList,
    InitialPoolGeneratedPlayer,
    InitialPoolPlayerUpdate,
    InitialPoolRegistry,
    InitialPoolResult,
)
from beta_engine.infrastructure.world_config import load_player_identity_config


@dataclass(slots=True)
class InitialPlayerPoolService:
    countries_service: CountriesConfigService
    config_path: Path = Path("config/simulation/initial_player_pool.json")
    identity_config_path: Path = Path("config/player_generation/player_identity.json")

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

    def get_audit_events(self, *, season: str | None = None, player_id: str | None = None) -> InitialPoolAuditList:
        events = self._load().audit_events
        if season is not None:
            events = [event for event in events if event.season == season]
        if player_id is not None:
            events = [event for event in events if event.player_id == player_id]
        return InitialPoolAuditList(audit_events=events)

    def generate_pool(self, *, season: str, seed: int, target_pool_size: int, dry_run: bool) -> InitialPoolResult:
        registry = self._load()
        locked = [player for player in registry.players if player.created_for_season == season and player.locked]
        before = self._season_fingerprint(registry.players, season=season)
        result = self._generator().generate(
            countries=self.countries_service.list_countries(),
            season=season,
            seed=seed,
            target_pool_size=target_pool_size,
            existing_locked_players=locked,
            dry_run=dry_run,
        )
        if not dry_run:
            self._replace_season(
                season=season,
                players=result.players,
                audit_event=self._audit_event(
                    registry=registry,
                    action="generate_pool",
                    season=season,
                    player_id=None,
                    actor="admin",
                    reason=None,
                    changed_fields=["players"],
                    before_fingerprint=before,
                    after_fingerprint=self._season_fingerprint(result.players, season=season),
                ),
            )
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
        registry = self._load()
        current = [player for player in registry.players if player.created_for_season == season]
        if not current:
            return self.generate_pool(season=season, seed=seed, target_pool_size=target_pool_size or 128, dry_run=dry_run)
        before = self._season_fingerprint(registry.players, season=season)
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
            changed_fields = ["unlocked_players"]
            if country_code:
                changed_fields.append("country_code")
            if region:
                changed_fields.append("region")
            self._replace_season(
                season=season,
                players=result.players,
                audit_event=self._audit_event(
                    registry=registry,
                    action="regenerate_unlocked",
                    season=season,
                    player_id=None,
                    actor="admin",
                    reason=None,
                    changed_fields=changed_fields,
                    before_fingerprint=before,
                    after_fingerprint=self._season_fingerprint(result.players, season=season),
                ),
            )
        return result

    def create_custom_player(self, payload: CustomInitialPoolPlayerCreate) -> InitialPoolGeneratedPlayer:
        registry = self._load()
        self._validate_country(payload.country_code)
        player_id = payload.player_id or self._custom_player_id(payload=payload, registry=registry)
        if any(player.player_id == player_id for player in registry.players):
            raise ValueError(f"player_id '{player_id}' already exists")
        season_start_year = int(payload.created_for_season.split("/")[0])
        age = season_start_year - payload.birth_year
        base = {
            "player_id": player_id,
            "name": payload.name,
            "country_code": payload.country_code,
            "nationality": payload.nationality or payload.country_code,
            "birth_year": payload.birth_year,
            "birth_year_week": payload.birth_year_week,
            "age_at_generation": age,
            "current_age_years": age,
            "current_ability": payload.current_ability,
            "potential_ability": payload.potential_ability,
            "potential_tier": payload.potential_tier,
            "career_stage": payload.career_stage,
            "play_style": payload.play_style,
            "archetype": payload.archetype,
            "attributes": payload.attributes,
            "hidden_career_traits": payload.hidden_career_traits,
            "locked": True,
            "generation_source": "manual",
            "manual_override": True,
            "generation_seed": 0,
            "generation_fingerprint": "pending",
            "created_for_season": payload.created_for_season,
        }
        fingerprint = self._manual_player_fingerprint(base)
        created = InitialPoolGeneratedPlayer.model_validate({**base, "generation_fingerprint": fingerprint})
        event = self._audit_event(
            registry=registry,
            action="create_custom_player",
            season=created.created_for_season,
            player_id=created.player_id,
            actor=payload.actor,
            reason=payload.reason,
            changed_fields=["player"],
            before_fingerprint=None,
            after_fingerprint=created.generation_fingerprint,
        )
        self._save(InitialPoolRegistry(players=[*registry.players, created], audit_events=[*registry.audit_events, event]))
        return created

    def update_player(self, *, player_id: str, payload: InitialPoolPlayerUpdate) -> InitialPoolGeneratedPlayer:
        registry = self._load()
        updated_players: list[InitialPoolGeneratedPlayer] = []
        updated: InitialPoolGeneratedPlayer | None = None
        before_fingerprint: str | None = None
        changed_fields: list[str] = []
        patch = payload.model_dump(exclude_unset=True, exclude={"reason", "actor"})
        if not patch:
            raise ValueError("update requires at least one editable field")
        for player in registry.players:
            if player.player_id != player_id:
                updated_players.append(player)
                continue
            before_fingerprint = player.generation_fingerprint
            candidate_data = player.model_dump(mode="python")
            for field, value in patch.items():
                if candidate_data.get(field) != value:
                    changed_fields.append(field)
                    candidate_data[field] = value
            if not player.locked:
                changed_fields.append("locked")
                candidate_data["locked"] = True
            if not player.manual_override:
                changed_fields.append("manual_override")
                candidate_data["manual_override"] = True
            candidate_data["generation_fingerprint"] = self._manual_player_fingerprint(candidate_data)
            if candidate_data["generation_fingerprint"] != before_fingerprint:
                changed_fields.append("generation_fingerprint")
            updated = InitialPoolGeneratedPlayer.model_validate(candidate_data)
            updated_players.append(updated)
        if updated is None:
            raise KeyError(f"player '{player_id}' not found")
        event = self._audit_event(
            registry=registry,
            action="update_player",
            season=updated.created_for_season,
            player_id=updated.player_id,
            actor=payload.actor,
            reason=payload.reason,
            changed_fields=sorted(set(changed_fields)),
            before_fingerprint=before_fingerprint,
            after_fingerprint=updated.generation_fingerprint,
        )
        self._save(InitialPoolRegistry(players=updated_players, audit_events=[*registry.audit_events, event]))
        return updated

    def set_lock(self, *, player_id: str, locked: bool) -> InitialPoolGeneratedPlayer:
        registry = self._load()
        players = []
        updated: InitialPoolGeneratedPlayer | None = None
        before_fingerprint: str | None = None
        for player in registry.players:
            if player.player_id == player_id:
                before_fingerprint = player.generation_fingerprint
                updated = player.model_copy(update={"locked": locked})
                players.append(updated)
            else:
                players.append(player)
        if updated is None:
            raise KeyError(f"player '{player_id}' not found")
        event = self._audit_event(
            registry=registry,
            action="lock_player" if locked else "unlock_player",
            season=updated.created_for_season,
            player_id=updated.player_id,
            actor="admin",
            reason=None,
            changed_fields=["locked"],
            before_fingerprint=before_fingerprint,
            after_fingerprint=updated.generation_fingerprint,
        )
        self._save(InitialPoolRegistry(players=players, audit_events=[*registry.audit_events, event]))
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

    def _replace_season(self, *, season: str, players: list[InitialPoolGeneratedPlayer], audit_event: InitialPoolAuditEvent | None = None) -> None:
        registry = self._load()
        retained = [player for player in registry.players if player.created_for_season != season]
        audit_events = [*registry.audit_events]
        if audit_event is not None:
            audit_events.append(audit_event)
        self._save(InitialPoolRegistry(players=[*retained, *players], audit_events=audit_events))

    def _validate_country(self, country_code: str) -> None:
        if self.countries_service.get_country(country_code) is None:
            raise ValueError(f"country_code '{country_code}' is not configured")

    def _custom_player_id(self, *, payload: CustomInitialPoolPlayerCreate, registry: InitialPoolRegistry) -> str:
        season_start_year = int(payload.created_for_season.split("/")[0])
        slug = re.sub(r"[^A-Z0-9]+", "-", payload.name.upper()).strip("-")[:24] or "PLAYER"
        prefix = f"CUST-{season_start_year}-{payload.country_code}-{slug}"
        existing = {player.player_id for player in registry.players}
        if prefix not in existing:
            return prefix
        sequence = 2
        while f"{prefix}-{sequence:04d}" in existing:
            sequence += 1
        return f"{prefix}-{sequence:04d}"

    def _manual_player_fingerprint(self, data: dict[str, Any]) -> str:
        material = dict(data)
        material.pop("generation_fingerprint", None)
        return hashlib.blake2b(json.dumps(material, default=str, sort_keys=True).encode(), digest_size=16).hexdigest()

    def _season_fingerprint(self, players: list[InitialPoolGeneratedPlayer], *, season: str) -> str:
        season_players = [player for player in players if player.created_for_season == season]
        material = "|".join(player.model_dump_json() for player in sorted(season_players, key=lambda item: item.player_id))
        return hashlib.blake2b(f"{season}|{material}".encode(), digest_size=16).hexdigest()

    def _audit_event(
        self,
        *,
        registry: InitialPoolRegistry,
        action: str,
        season: str,
        player_id: str | None,
        actor: str,
        reason: str | None,
        changed_fields: list[str],
        before_fingerprint: str | None,
        after_fingerprint: str | None,
    ) -> InitialPoolAuditEvent:
        sequence = len(registry.audit_events) + 1
        material = "|".join(
            [
                str(sequence),
                action,
                season,
                player_id or "",
                actor,
                reason or "",
                ",".join(sorted(changed_fields)),
                before_fingerprint or "",
                after_fingerprint or "",
            ]
        )
        suffix = hashlib.blake2b(material.encode(), digest_size=5).hexdigest()
        return InitialPoolAuditEvent(
            audit_id=f"AUD-{season.split('/')[0]}-{sequence:06d}-{suffix}",
            timestamp_utc=None,
            actor=actor,
            action=action,  # type: ignore[arg-type]
            player_id=player_id,
            season=season,
            reason=reason,
            changed_fields=sorted(set(changed_fields)),
            before_fingerprint=before_fingerprint,
            after_fingerprint=after_fingerprint,
        )
