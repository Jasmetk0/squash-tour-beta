"""Deterministic RNG service and explicit seed hierarchy helpers.

This module intentionally centralizes pseudo-random behavior so future simulation
logic can depend on injected RNG instances rather than ambient randomness.
"""

from __future__ import annotations

import _random
import hashlib
import random
from collections.abc import MutableSequence, Sequence
from typing import TypeVar

from beta_engine.core.types import Seed, SeedPath, SeedScope

T = TypeVar("T")

_Random = random.Random
_blake2b = hashlib.blake2b
_int_from_bytes = int.from_bytes
_new_object = object.__new__
# ``random.Random(x)`` for an exact ``int`` runs only ``_random.Random.seed(x)``
# (MT19937 ``init_by_array`` over the 32-bit words of ``abs(x)``) and sets
# ``gauss_next = None``. Doing exactly that without the Python ``__init__`` and
# ``seed`` frames yields the identical generator state; anything else, or a
# ``random.Random`` whose base is not the C generator, uses the constructor.
_seed_generator = (
    _random.Random.seed if _Random.__bases__ == (_random.Random,) else None
)
_new_generator = _Random.__new__


def _generator_for(value: object) -> random.Random:
    if type(value) is int and _seed_generator is not None:
        generator = _new_generator(_Random)
        _seed_generator(generator, value)
        generator.gauss_next = None
        return generator
    return _Random(value)


class DeterministicRng:
    """Seeded RNG wrapper with deterministic child-seed derivation."""

    __slots__ = ("_value", "_seed", "_generator", "_seed_text", "_scope", "_prefix")

    def __init__(self, seed: Seed | int):
        if not isinstance(seed, Seed):
            seed = Seed(int(seed))
        self._seed: Seed | None = seed
        self._value = seed.value
        # Created on first draw from the same seed: identical state and
        # sequence. Many child RNGs only derive further seeds and never draw.
        self._generator: random.Random | None = None
        # Decimal text of the seed and the ``v1|<scope>|<text>`` prefix of the
        # last scope, reused by every child derivation.
        self._seed_text: str | None = None
        self._scope: SeedScope | None = None
        self._prefix: str | None = None

    @classmethod
    def _child(cls, value: int) -> "DeterministicRng":
        # A branch child: same state as ``DeterministicRng(Seed(value))``; its
        # ``Seed`` object is created only if ``seed`` is read.
        rng = _new_object(DeterministicRng)
        rng._seed = None
        rng._value = value
        rng._generator = None
        rng._seed_text = None
        rng._scope = None
        rng._prefix = None
        return rng

    def _draw(self) -> random.Random:
        generator = self._generator
        if generator is None:
            generator = self._generator = _generator_for(self._value)
        return generator

    @property
    def seed(self) -> Seed:
        """Return this RNG's typed seed."""

        seed = self._seed
        if seed is None:
            seed = self._seed = Seed(self._value)
        return seed

    def random(self) -> float:
        """Return a deterministic float in [0.0, 1.0)."""

        generator = self._generator
        if generator is None:
            generator = self._generator = _generator_for(self._value)
        return generator.random()

    def randint(self, a: int, b: int) -> int:
        """Return deterministic integer N such that a <= N <= b."""

        return self._draw().randint(a, b)

    def uniform(self, a: float, b: float) -> float:
        """Return deterministic float N such that a <= N <= b."""

        generator = self._generator
        if generator is None:
            generator = self._generator = _generator_for(self._value)
        return generator.uniform(a, b)

    def choice(self, sequence: Sequence[T]) -> T:
        """Return a deterministic element from a non-empty sequence."""

        return self._draw().choice(sequence)

    def shuffle(self, sequence: MutableSequence[T]) -> None:
        """In-place deterministic shuffle for mutable sequences."""

        self._draw().shuffle(sequence)

    def _child_value(self, scope: SeedScope, parts: tuple[object, ...]) -> int:
        # Same material and digest as ``derive_child_seed`` (the reference):
        # ``"|".join(("v1", scope.value, str(seed), *map(str, parts)))``. The
        # first three fields are joined once per scope member and reused.
        if scope is self._scope:
            prefix = self._prefix
        else:
            text = self._seed_text
            if text is None:
                text = self._seed_text = str(self._value)
            prefix = "|".join(("v1", scope.value, text))
            if type(scope) is SeedScope:
                self._scope = scope
                self._prefix = prefix
        material = "|".join((prefix, *map(str, parts)))
        digest = _blake2b(material.encode("utf-8"), digest_size=16).digest()
        return _int_from_bytes(digest, "big")

    def derive(self, scope: SeedScope, *parts: object) -> Seed:
        """Derive a deterministic child seed for the given scope and identity parts."""

        return Seed(self._child_value(scope, parts))

    def branch(self, scope: SeedScope, *parts: object) -> "DeterministicRng":
        """Create a child RNG deterministically derived from this RNG's seed."""

        return DeterministicRng._child(self._child_value(scope, parts))


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
