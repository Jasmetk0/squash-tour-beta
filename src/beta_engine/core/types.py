"""Shared lightweight value objects for deterministic core infrastructure."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SeedScope(str, Enum):
    """Supported deterministic seed hierarchy scopes."""

    GLOBAL = "global"
    SEASON = "season"
    WEEK = "week"
    MATCH = "match"


@dataclass(frozen=True, slots=True)
class Seed:
    """Typed seed value used by the deterministic RNG service."""

    value: int


@dataclass(frozen=True, slots=True)
class SeedPath:
    """Structured identity for seed lineage derivation."""

    season: int
    week: int | None = None
    match: str | int | None = None
