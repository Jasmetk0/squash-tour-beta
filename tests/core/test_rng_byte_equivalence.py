"""#1917: the faster DeterministicRng is byte-for-byte the reference RNG.

``_ReferenceRng`` is the unchanged ``buuk 29784d5`` implementation. Every
derived seed, generator state and draw of the production class must equal it,
for every supported identity part, root seed shape and draw method.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
import sys
from pathlib import Path

import pytest

from beta_engine.core import rng as rng_module
from beta_engine.core.rng import DeterministicRng, derive_child_seed
from beta_engine.core.types import Seed, SeedScope

ROOT = Path(__file__).resolve().parents[2]


class _ReferenceRng:
    """``buuk 29784d5`` ``DeterministicRng``, verbatim apart from the name."""

    def __init__(self, seed):
        self._seed = seed if isinstance(seed, Seed) else Seed(int(seed))
        self._generator = None
        self._seed_text = None

    @property
    def _random(self) -> random.Random:
        generator = self._generator
        if generator is None:
            generator = self._generator = random.Random(self._seed.value)
        return generator

    @property
    def seed(self) -> Seed:
        return self._seed

    def random(self):
        return self._random.random()

    def randint(self, a, b):
        return self._random.randint(a, b)

    def uniform(self, a, b):
        return self._random.uniform(a, b)

    def choice(self, sequence):
        return self._random.choice(sequence)

    def shuffle(self, sequence):
        self._random.shuffle(sequence)

    def derive(self, scope, *parts):
        text = self._seed_text
        if text is None:
            text = self._seed_text = str(self._seed.value)
        material = "|".join(("v1", scope.value, text, *map(str, parts)))
        digest = hashlib.blake2b(material.encode("utf-8"), digest_size=16).digest()
        return Seed(int.from_bytes(digest, byteorder="big", signed=False))

    def branch(self, scope, *parts):
        return _ReferenceRng(self.derive(scope, *parts))


ROOTS = [0, 1, -1, 2**32 - 1, 2**32, -(2**63), 2**64 + 5, 2**127, 2**128 - 1,
         2**128, -(2**128 - 1), 2**129 + 3, 10**60, 2**4000 + 17, 4242]
PARTS = [(), ("",), ("opening",), ("segment", 24), ("rally-detail", -5),
         ("Čeština", "Žluťoučký kůň"), ("😀", "\u0000", "a|b", "||"), (None, True, 1.5),
         (-0.0, float("inf")), (2**200, -(2**200)), ((1, "x"),), (SeedScope.WEEK,),
         (Seed(5),), ("P0001", "P0002", 3)]


def _draws(rng, values):
    values.append(rng.random().hex())
    values.append(rng.uniform(-0.68, 0.68).hex())
    values.append(rng.randint(-(10**30), 10**30))
    values.append(rng.choice(["LEFT", "RIGHT", "CENTRE"]))
    items = list(range(11))
    rng.shuffle(items)
    values.append(items)
    values.append(rng.uniform(5.5, 9.5).hex())


def _run(factory) -> list:
    values: list = []
    for root in ROOTS:
        for root_value in (root, Seed(root)):
            rng = factory(root_value)
            values.append(rng.seed.value)
            for scope in SeedScope:
                for parts in PARTS:
                    values.append(rng.derive(scope, *parts).value)
                    values.append(rng.branch(scope, *parts).seed.value)
            for parts in PARTS[:6]:
                first = rng.branch(SeedScope.MATCH, *parts)
                values.append(first.random().hex())
                again = rng.branch(SeedScope.MATCH, *parts)
                _draws(again, values)
                _draws(first, values)
            _draws(rng, values)
            level = rng
            for scope, parts in [(SeedScope.SEASON, (2031,)), (SeedScope.WEEK, (12,)),
                                 (SeedScope.MATCH, ("set", 2)), (SeedScope.MATCH, ())]:
                level = level.branch(scope, *parts)
                values.append(level.seed.value)
                _draws(level, values)
    return values


@pytest.mark.pr_critical
def test_every_seed_and_draw_equals_the_reference_rng() -> None:
    assert _run(DeterministicRng) == _run(_ReferenceRng)


def test_materialized_generator_state_equals_random_random_constructor() -> None:
    for value in [*ROOTS, *(DeterministicRng(4242).derive(SeedScope.MATCH, i).value
                            for i in range(200))]:
        produced = DeterministicRng(value)._draw()
        assert type(produced) is random.Random
        assert produced.getstate() == random.Random(value).getstate()
        assert vars(produced) == vars(random.Random(value))
    child = DeterministicRng(2**127).branch(SeedScope.MATCH, "x", 1)
    assert child._draw().getstate() == random.Random(child.seed.value).getstate()


def test_non_int_seed_values_keep_the_constructor_semantics() -> None:
    for odd in (3.5, -0.0, "seed-text", "Čeština", True, False, b"bytes"):
        produced, reference = DeterministicRng(Seed(odd)), _ReferenceRng(Seed(odd))
        assert [produced.random(), produced.uniform(0, 1)] == [
            reference.random(), reference.uniform(0, 1)]
        assert produced.derive(SeedScope.MATCH, "odd").value == reference.derive(
            SeedScope.MATCH, "odd").value

    class IntSubclass(int):
        pass

    assert (DeterministicRng(Seed(IntSubclass(77)))._draw().getstate()
            == random.Random(IntSubclass(77)).getstate())
    for bad in ("abc", None, [1]):
        with pytest.raises(Exception) as produced:
            DeterministicRng(bad)
        with pytest.raises(Exception) as reference:
            _ReferenceRng(bad)
        assert type(produced.value) is type(reference.value)


def test_seed_object_identity_and_lazy_child_seed() -> None:
    seed = Seed(2**127 + 9)
    rng = DeterministicRng(seed)
    assert rng.seed is seed
    assert DeterministicRng(12).seed == Seed(12)
    child = rng.branch(SeedScope.MATCH, "x", 1)
    assert child.seed is child.seed
    assert child.seed == rng.derive(SeedScope.MATCH, "x", 1)
    assert child.seed == derive_child_seed(seed, SeedScope.MATCH, "x", 1)
    assert type(child) is DeterministicRng


def test_scope_prefix_reuse_never_leaks_between_scopes_or_foreign_scopes() -> None:
    rng, reference = DeterministicRng(31337), _ReferenceRng(31337)
    for scope in [SeedScope.MATCH, SeedScope.WEEK, SeedScope.MATCH, SeedScope.GLOBAL,
                  SeedScope.MATCH, SeedScope.SEASON, SeedScope.SEASON, SeedScope.MATCH]:
        assert rng.derive(scope, "k", 1) == reference.derive(scope, "k", 1)
        assert rng.derive(scope) == reference.derive(scope)

    class OtherScope:
        def __init__(self, value):
            self.value = value

    other = OtherScope("match")
    first = rng.derive(other, "a")
    other.value = "week"
    second = rng.derive(other, "a")  # directly after: no member resets the prefix
    assert first == DeterministicRng(31337).derive(SeedScope.MATCH, "a")
    assert second == reference.derive(other, "a") == DeterministicRng(31337).derive(
        SeedScope.WEEK, "a")
    with pytest.raises(AttributeError):
        rng.derive("match", "a")
    with pytest.raises(AttributeError):
        reference.derive("match", "a")


def test_children_with_the_same_identity_have_independent_streams() -> None:
    rng = DeterministicRng(2**127 + 5)
    first = rng.branch(SeedScope.MATCH, "segment", 3)
    head = [first.random() for _ in range(3)]
    second = rng.branch(SeedScope.MATCH, "segment", 3)
    assert [second.random() for _ in range(3)] == head
    assert first._draw() is not second._draw()
    rng.random()
    assert rng.branch(SeedScope.MATCH, "segment", 3).random() == head[0]


def test_reference_stdlib_layout_assumed_by_the_fast_seed_path() -> None:
    # The fast path is used only when random.Random sits directly on the C
    # generator; otherwise every generator comes from the constructor.
    assert rng_module._seed_generator is not None
    assert random.Random.__bases__[0].seed is rng_module._seed_generator


def test_rng_output_does_not_depend_on_pythonhashseed() -> None:
    program = (
        "import hashlib, json\n"
        "from beta_engine.core.rng import DeterministicRng\n"
        "from beta_engine.core.types import SeedScope\n"
        "r = DeterministicRng(2**127 + 3)\n"
        "out = []\n"
        "for i in range(300):\n"
        "    c = r.branch(SeedScope.MATCH, 'rally-detail', i).branch(SeedScope.MATCH, 'č', str(i))\n"
        "    out += [c.seed.value, c.random().hex(), c.randint(1, 6), c.choice('ab')]\n"
        "print(hashlib.sha256(json.dumps(out).encode()).hexdigest())\n"
    )
    digests = set()
    for hash_seed in ("0", "1", "4294967295"):
        env = {**os.environ, "PYTHONHASHSEED": hash_seed,
               "PYTHONPATH": str(ROOT / "src")}
        digests.add(subprocess.run([sys.executable, "-c", program], env=env, check=True,
                                   capture_output=True, text=True).stdout.strip())
    reference = _ReferenceRng(2**127 + 3)
    out = []
    for i in range(300):
        c = reference.branch(SeedScope.MATCH, "rally-detail", i).branch(
            SeedScope.MATCH, "č", str(i))
        out += [c.seed.value, c.random().hex(), c.randint(1, 6), c.choice("ab")]
    assert digests == {hashlib.sha256(json.dumps(out).encode()).hexdigest()}
