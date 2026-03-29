"""Deterministic RNG service and explicit seed hierarchy helpers.

This module intentionally centralizes pseudo-random behavior so future simulation
logic can depend on injected RNG instances rather than ambient randomness.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import MutableSequence, Sequence
from typing import TypeVar

from beta_engine.core.types import Seed, SeedPath, SeedScope

T = TypeVar("T")


class DeterministicRng:
    """Seeded RNG wrapper with deterministic child-seed derivation."""

    def __init__(self, seed: Seed | int):
        self._seed = seed if isinstance(seed, Seed) else Seed(int(seed))
        self._random = random.Random(self._seed.value)

    @property
    def seed(self) -> Seed:
        """Return this RNG's typed seed."""

        return self._seed

    def random(self) -> float:
        """Return a deterministic float in [0.0, 1.0)."""

        return self._random.random()

    def randint(self, a: int, b: int) -> int:
        """Return deterministic integer N such that a <= N <= b."""

        return self._random.randint(a, b)

    def uniform(self, a: float, b: float) -> float:
        """Return deterministic float N such that a <= N <= b."""

        return self._random.uniform(a, b)

    def choice(self, sequence: Sequence[T]) -> T:
        """Return a deterministic element from a non-empty sequence."""

        return self._random.choice(sequence)

    def shuffle(self, sequence: MutableSequence[T]) -> None:
        """In-place deterministic shuffle for mutable sequences."""

        self._random.shuffle(sequence)

    def derive(self, scope: SeedScope, *parts: object) -> Seed:
        """Derive a deterministic child seed for the given scope and identity parts."""

        return derive_child_seed(self._seed, scope, *parts)

    def branch(self, scope: SeedScope, *parts: object) -> "DeterministicRng":
        """Create a child RNG deterministically derived from this RNG's seed."""

        return DeterministicRng(self.derive(scope, *parts))


def derive_child_seed(parent_seed: Seed | int, scope: SeedScope, *parts: object) -> Seed:
    """Derive a stable seed from parent seed, scope, and identity parts.

    Notes:
    - Uses a content hash rather than Python's hash() to avoid hash randomization.
    - The algorithm is intentionally versioned in the material prefix for stability.
    """

    normalized_parent = parent_seed if isinstance(parent_seed, Seed) else Seed(int(parent_seed))
    material = "|".join(["v1", scope.value, str(normalized_parent.value), *(str(p) for p in parts)])
    digest = hashlib.blake2b(material.encode("utf-8"), digest_size=16).digest()
    return Seed(int.from_bytes(digest, byteorder="big", signed=False))


def derive_season_seed(global_seed: Seed | int, season: int) -> Seed:
    """Derive season-level seed from global seed."""

    return derive_child_seed(global_seed, SeedScope.SEASON, season)


def derive_week_seed(season_seed: Seed | int, week: int) -> Seed:
    """Derive week-level seed from season seed."""

    return derive_child_seed(season_seed, SeedScope.WEEK, week)


def derive_match_seed(week_seed: Seed | int, match: str | int) -> Seed:
    """Derive match-level seed from week seed."""

    return derive_child_seed(week_seed, SeedScope.MATCH, match)


def derive_seed_hierarchy(global_seed: Seed | int, seed_path: SeedPath) -> dict[SeedScope, Seed]:
    """Build the standard global -> season -> week -> match hierarchy.

    Returned mapping includes keys up to the deepest level present in ``seed_path``.
    """

    seeds: dict[SeedScope, Seed] = {
        SeedScope.GLOBAL: global_seed if isinstance(global_seed, Seed) else Seed(int(global_seed))
    }
    season_seed = derive_season_seed(seeds[SeedScope.GLOBAL], seed_path.season)
    seeds[SeedScope.SEASON] = season_seed

    if seed_path.week is not None:
        week_seed = derive_week_seed(season_seed, seed_path.week)
        seeds[SeedScope.WEEK] = week_seed

        if seed_path.match is not None:
            seeds[SeedScope.MATCH] = derive_match_seed(week_seed, seed_path.match)

    return seeds
