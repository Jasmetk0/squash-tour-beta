"""Differential corpus of the RNG API (and one non-match RNG consumer) for one tree.

Run once per pinned source tree, each in its own process, and compare the
emitted digests (``--compare A.json B.json``). Every value is recorded exactly:
floats as ``float.hex``, generator states as the SHA-256 of their complete
``getstate()`` repr, seeds as decimal integers.

Sections:

* ``api``: ``derive``/``branch`` chains (one to five levels), empty suffix,
  repeated creation of the same branch followed by further draws, interleaved
  ``random``/``uniform``/``randint``/``choice``/``shuffle``, zero, negative,
  64/128/129-bit and very large root seeds, ``Seed`` and ``int`` roots,
  non-``int`` ``Seed`` values (float, str, bool), Unicode/empty/pipe/None/
  float/bool/tuple/enum/Seed identity parts, every ``SeedScope`` and alternating
  scopes on one parent, plus ``derive_child_seed``/``derive_seed_hierarchy``;
  and the materialized generator state after each sequence.
* ``random_corpus``: 4,000 pseudo-random identity chains and draw programs from
  a fixed program seed (the program generator is plain ``random.Random`` in the
  driver, never the tree under test).
* ``population`` (needs pydantic): ``InitialPlayerPoolGenerator.generate`` for
  three countries and several seeds/options; complete ``model_dump_json`` bytes.

    python scripts/rng_differential_corpus.py --source <tree> --emit a.json
    python scripts/rng_differential_corpus.py --compare a.json b.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random as stdlib_random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _value(value):
    if isinstance(value, float):
        return ["f", value.hex()]
    if isinstance(value, bool) or value is None:
        return ["b", repr(value)]
    if isinstance(value, int):
        return ["i", str(value)]
    if isinstance(value, (list, tuple)):
        return ["l", [_value(item) for item in value]]
    return ["r", repr(value)]


def _state(rng) -> str:
    return hashlib.sha256(repr(rng._draw().getstate() if hasattr(rng, "_draw")
                               else rng._random.getstate()).encode()).hexdigest()


def _program(rng, steps, records, stdlib_random_state):
    for step in steps:
        kind = step[0]
        if kind == "random":
            records.append(_value(rng.random()))
        elif kind == "uniform":
            records.append(_value(rng.uniform(step[1], step[2])))
        elif kind == "randint":
            records.append(_value(rng.randint(step[1], step[2])))
        elif kind == "choice":
            records.append(_value(rng.choice(step[1])))
        elif kind == "shuffle":
            items = list(step[1])
            rng.shuffle(items)
            records.append(_value(items))
    if stdlib_random_state:
        records.append(["state", _state(rng)])


def api_section(rng_module, types_module) -> list:
    DeterministicRng = rng_module.DeterministicRng
    Seed, SeedScope = types_module.Seed, types_module.SeedScope
    records: list = []
    roots = [0, 1, -1, 7, 2**31 - 1, 2**32 - 1, 2**32, 2**63, -(2**63), 2**64 + 5,
             2**127, 2**128 - 1, 2**128, -(2**128 - 1), 2**129 + 3, 10**60, -(10**80),
             2**4000 + 17, 555, 2027, 4242, 123456789]
    parts_list = [
        (), ("",), ("opening",), ("segment", 1), ("segment", 24), ("x", 1),
        ("rally-detail", 0), ("rally-detail", -5), ("Čeština", "Žluťoučký kůň"),
        ("😀", "🎾", "\u0000", "a|b", "|", "||"), (None,), (True, False), (1.5, -0.0),
        (float("inf"),), (2**200,), (-(2**200),), ((1, 2),), (SeedScope.WEEK,),
        (Seed(5),), ("P0001", "P0002", 3), ("2030-W12-M3",),
    ]
    program = [("random",), ("uniform", -0.68, 0.68), ("randint", 1, 6),
               ("choice", ["LEFT", "RIGHT"]), ("shuffle", list(range(9))),
               ("random",), ("uniform", 5.5, 9.5), ("randint", -10**30, 10**30)]
    for root in roots:
        for root_kind in ("int", "seed"):
            rng = DeterministicRng(root if root_kind == "int" else Seed(root))
            records.append(["root", str(root), root_kind, str(rng.seed.value)])
            for scope in SeedScope:
                for parts in parts_list:
                    seed = rng.derive(scope, *parts)
                    child = rng.branch(scope, *parts)
                    records.append(["derive", scope.value, repr(parts), str(seed.value),
                                    str(child.seed.value),
                                    str(rng_module.derive_child_seed(root, scope, *parts).value)])
            # One-shot draws, then the same branch again with further draws.
            for parts in parts_list[:8]:
                first = rng.branch(SeedScope.MATCH, *parts)
                _program(first, program[:1], records, False)
                again = rng.branch(SeedScope.MATCH, *parts)
                _program(again, program, records, True)
                _program(first, program[1:], records, True)
            # Draw from the root itself, interleaved with branching.
            _program(rng, program[:3], records, False)
            child = rng.branch(SeedScope.MATCH, "after-draw")
            _program(child, program, records, True)
            _program(rng, program[3:], records, True)
    # Multi-level chains and alternating scopes on one parent.
    for root in (2027, 2**127 + 99, -(2**90)):
        rng = DeterministicRng(root)
        level = rng
        for depth, (scope, parts) in enumerate([
            (SeedScope.SEASON, (2031,)), (SeedScope.WEEK, (12,)),
            (SeedScope.MATCH, ("2031-W12-M1",)), (SeedScope.MATCH, ("set", 2)),
            (SeedScope.MATCH, ("rally-detail", 7)), (SeedScope.MATCH, ()),
        ]):
            level = level.branch(scope, *parts)
            records.append(["chain", depth, str(level.seed.value)])
            _program(level, program, records, True)
        for scope in [SeedScope.MATCH, SeedScope.WEEK, SeedScope.MATCH, SeedScope.GLOBAL,
                      SeedScope.MATCH, SeedScope.SEASON, SeedScope.SEASON]:
            records.append(["alternate", scope.value, str(rng.derive(scope, "k", 1).value)])
    # A scope that is not a SeedScope member but has a ``value``.
    class OtherScope:
        def __init__(self, value):
            self.value = value

    other = OtherScope("match")
    rng = DeterministicRng(31337)
    records.append(["other-scope", str(rng.derive(other, "a").value)])
    other.value = "week"
    records.append(["other-scope-mutated", str(rng.derive(other, "a").value)])
    records.append(["other-scope-member", str(rng.derive(SeedScope.MATCH, "a").value)])
    # Non-int Seed values keep random.Random's own seeding semantics.
    for odd in (3.5, -0.0, "seed-text", "Čeština", True, False, b"bytes"):
        rng = DeterministicRng(Seed(odd))
        try:
            values = [_value(rng.random()), _value(rng.uniform(0, 1)),
                      str(rng.derive(SeedScope.MATCH, "odd", 1).value)]
        except Exception as error:  # pragma: no cover - recorded, not hidden
            values = ["error", type(error).__name__, str(error)]
        records.append(["odd-seed", repr(odd), values])
    # Invalid roots raise the same exception type.
    for bad in ("abc", None, 1.5, "12"):
        try:
            records.append(["bad-root", repr(bad), str(DeterministicRng(bad).seed.value)])
        except Exception as error:
            records.append(["bad-root", repr(bad), "error", type(error).__name__])
    hierarchy_path = types_module.SeedPath(season=2028, week=7, match="QF-2")
    for root in (12345, 2**127 + 1, -1):
        hierarchy = rng_module.derive_seed_hierarchy(root, hierarchy_path)
        records.append(["hierarchy", [[k.value, str(v.value)] for k, v in hierarchy.items()]])
    return records


def random_corpus_section(rng_module, types_module, count: int) -> list:
    DeterministicRng = rng_module.DeterministicRng
    Seed, SeedScope = types_module.Seed, types_module.SeedScope
    program_rng = stdlib_random.Random(1917)
    alphabet = "abcXYZ019-_|čšžřÄ€😀 "
    scopes = list(SeedScope)
    records: list = []
    for _ in range(count):
        root = program_rng.choice([
            program_rng.randrange(-(2**130), 2**130), program_rng.randrange(0, 2**32),
            program_rng.randrange(0, 2**128),
        ])
        rng = DeterministicRng(Seed(root) if program_rng.random() < 0.5 else root)
        for _ in range(program_rng.randrange(1, 6)):
            parts = []
            for _ in range(program_rng.randrange(0, 4)):
                if program_rng.random() < 0.5:
                    parts.append(program_rng.randrange(-(2**70), 2**70))
                else:
                    parts.append("".join(program_rng.choice(alphabet)
                                         for _ in range(program_rng.randrange(0, 9))))
            rng = rng.branch(program_rng.choice(scopes), *parts)
            records.append(["seed", str(rng.seed.value)])
            steps = []
            for _ in range(program_rng.randrange(0, 5)):
                kind = program_rng.choice(["random", "uniform", "randint", "choice", "shuffle"])
                if kind == "uniform":
                    steps.append((kind, program_rng.uniform(-5, 5), program_rng.uniform(-5, 5)))
                elif kind == "randint":
                    low = program_rng.randrange(-1000, 1000)
                    steps.append((kind, low, low + program_rng.randrange(0, 10**6)))
                elif kind in ("choice", "shuffle"):
                    steps.append((kind, list(range(program_rng.randrange(1, 12)))))
                else:
                    steps.append((kind,))
            _program(rng, steps, records, program_rng.random() < 0.1)
    return records


def population_section() -> list:
    try:
        from beta_engine.domain.countries import Country
        from beta_engine.domain.players.initial_pool import InitialPlayerPoolGenerator
    except ModuleNotFoundError as error:
        return [["unavailable", str(error)]]

    def country(code, population, system, popularity, tradition, region="EUROPE", name=None):
        return Country(code=code, name=name or code, region=region, population=population,
                       wealth_support=system, squash_popularity=popularity,
                       squash_tradition=tradition, system_quality=system,
                       competition_density=float(system), federation_quality=float(system),
                       court_count=500 if system >= 4 else 80)

    countries = [
        country("AAA", 12_000_000, 3, 3, 3, name="Česko"),
        country("BBB", 80_000_000, 5, 4, 5),
        country("CCC", 3_000_000, 2, 2, 1, region="ASIA"),
    ]
    generator = InitialPlayerPoolGenerator()
    records = []
    for seed, size, options in [
        (17, 3, {}), (802, 128, {}), (2**127 + 5, 64, {}), (1234, 40, {"min_age": 18, "max_age": 24}),
        (99, 32, {"country_quotas": {"AAA": 10, "CCC": 5}}),
        (5, 16, {"naming_policy": "country_serial.v1"}),
    ]:
        result = generator.generate(countries=countries, seed=seed, target_pool_size=size, **options)
        payload = result.model_dump_json().encode()
        records.append(["population", str(seed), size, hashlib.sha256(payload).hexdigest(), len(payload)])
    return records


def emit(source: Path, corpus_size: int) -> dict:
    sys.path.insert(0, str(source / "src"))
    import beta_engine.core.rng as rng_module
    import beta_engine.core.types as types_module

    if not Path(rng_module.__file__).resolve().is_relative_to(source.resolve()):
        raise SystemExit(f"imported {rng_module.__file__} outside {source}")
    sections = {
        "api": api_section(rng_module, types_module),
        "random_corpus": random_corpus_section(rng_module, types_module, corpus_size),
        "population": population_section(),
    }
    digests = {}
    for name, records in sections.items():
        body = json.dumps(records, ensure_ascii=False, separators=(",", ":")).encode()
        digests[name] = {"sha256": hashlib.sha256(body).hexdigest(), "records": len(records)}
    return {
        "source": str(source),
        "rng_file": rng_module.__file__,
        "rng_sha256": hashlib.sha256(Path(rng_module.__file__).read_bytes()).hexdigest(),
        "python": platform.python_version(),
        "machine": platform.machine(),
        "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
        "digests": digests,
    }


def compare(paths: list[Path]) -> int:
    reports = [json.loads(path.read_text()) for path in paths]
    reference = reports[0]["digests"]
    equal = True
    for path, report in zip(paths, reports):
        for name, digest in report["digests"].items():
            same = digest == reference.get(name)
            equal &= same
            print(f"{'equal' if same else 'DIFFERENT':9s} {name:14s} {digest['records']:7d} "
                  f"{digest['sha256'][:16]}  py{report['python']} "
                  f"hashseed={report['pythonhashseed']} {path}")
    print("verdict:", "equal" if equal else "DIFFERENT")
    return 0 if equal else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=ROOT)
    parser.add_argument("--emit", type=Path)
    parser.add_argument("--corpus-size", type=int, default=4000)
    parser.add_argument("--compare", nargs="+", type=Path)
    args = parser.parse_args(argv)
    if args.compare:
        return compare(args.compare)
    report = emit(args.source.resolve(), args.corpus_size)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.emit:
        args.emit.write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
