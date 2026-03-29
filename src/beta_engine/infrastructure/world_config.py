"""Loaders for world data configs used by generation pipelines."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from beta_engine.domain.countries.models import CountriesConfig


class PlayerIdentityConfig(BaseModel):
    given_names: list[str] = Field(min_length=1)
    family_names: list[str] = Field(min_length=1)
    play_styles: list[str] = Field(min_length=1)
    archetypes: list[str] = Field(min_length=1)
    growth_curves: list[str] = Field(min_length=1)


def _load_json(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_countries_config(path: str | Path = "config/world/countries.json") -> CountriesConfig:
    return CountriesConfig.model_validate(_load_json(path))


def load_player_identity_config(
    path: str | Path = "config/world/player_identity.json",
) -> PlayerIdentityConfig:
    return PlayerIdentityConfig.model_validate(_load_json(path))
