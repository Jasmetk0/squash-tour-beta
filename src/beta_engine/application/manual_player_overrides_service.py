"""File-backed CRUD service for world manual player overrides."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from beta_engine.domain.players import ManualPlayerOverride, ManualPlayerOverridesRegistry
from beta_engine.infrastructure.world_config import load_manual_player_overrides_config


@dataclass(slots=True)
class ManualPlayerOverridesService:
    config_path: Path = Path("config/world/manual_player_overrides.json")

    def __post_init__(self) -> None:
        if not isinstance(self.config_path, Path):
            self.config_path = Path(self.config_path)

    def list_overrides(
        self,
        *,
        season: int | None = None,
        country_code: str | None = None,
        enabled: bool | None = None,
    ) -> list[ManualPlayerOverride]:
        items = self._load().overrides
        if season is not None:
            items = [item for item in items if item.season == season]
        if country_code is not None:
            normalized_country = country_code.upper()
            items = [item for item in items if item.country_code == normalized_country]
        if enabled is not None:
            items = [item for item in items if item.enabled is enabled]
        return sorted(items, key=lambda item: (item.season, item.country_code, item.override_id))

    def get_override(self, override_id: str) -> ManualPlayerOverride | None:
        normalized_id = override_id.strip()
        return next((item for item in self._load().overrides if item.override_id == normalized_id), None)

    def create_override(self, payload: ManualPlayerOverride) -> ManualPlayerOverride:
        registry = self._load()
        if any(item.override_id == payload.override_id for item in registry.overrides):
            raise ValueError(f"override with id '{payload.override_id}' already exists")
        self._save(ManualPlayerOverridesRegistry(overrides=[*registry.overrides, payload]))
        return payload

    def update_override(self, override_id: str, payload: ManualPlayerOverride) -> ManualPlayerOverride:
        normalized_id = override_id.strip()
        registry = self._load()

        if payload.override_id != normalized_id and any(item.override_id == payload.override_id for item in registry.overrides):
            raise ValueError(f"override with id '{payload.override_id}' already exists")

        updated_items: list[ManualPlayerOverride] = []
        replaced = False
        for item in registry.overrides:
            if item.override_id == normalized_id:
                updated_items.append(payload)
                replaced = True
            else:
                updated_items.append(item)

        if not replaced:
            raise LookupError(f"override '{normalized_id}' was not found")

        self._save(ManualPlayerOverridesRegistry(overrides=updated_items))
        return payload

    def delete_override(self, override_id: str) -> None:
        normalized_id = override_id.strip()
        registry = self._load()
        remaining = [item for item in registry.overrides if item.override_id != normalized_id]
        if len(remaining) == len(registry.overrides):
            raise LookupError(f"override '{normalized_id}' was not found")
        self._save(ManualPlayerOverridesRegistry(overrides=remaining))

    def _load(self) -> ManualPlayerOverridesRegistry:
        if not self.config_path.exists():
            return ManualPlayerOverridesRegistry(overrides=[])
        return load_manual_player_overrides_config(self.config_path)

    def _save(self, payload: ManualPlayerOverridesRegistry) -> None:
        seen: set[str] = set()
        for item in payload.overrides:
            if item.override_id in seen:
                raise ValueError(f"duplicate override id '{item.override_id}' in dataset")
            seen.add(item.override_id)

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        target = self.config_path
        tmp_path = target.with_suffix(f"{target.suffix}.tmp")
        with tmp_path.open("w", encoding="utf-8") as fh:
            json.dump(payload.model_dump(mode="json"), fh, indent=2)
            fh.write("\n")
        tmp_path.replace(target)
