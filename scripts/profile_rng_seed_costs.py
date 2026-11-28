"""Where one child RNG of the seed hierarchy spends its CPU and allocations.

Pure-function decomposition of ``DeterministicRng.branch(...)`` plus its draw,
for the source tree named by ``--source`` (default: this checkout), so two
pinned trees can be compared in separate processes. It is a cause finder, not
the acceptance metric: the acceptance metric is the time of whole matches and
real 64/128 knockouts (``scripts/ab_match_kernel.py`` of #1916).

Components (one identity shape ``("segment", 7)`` and a one-part shape
``("closure",)``, a 128-bit parent seed as in every MatchEngine branch):

* identity serialization (``"|".join`` of version, scope, seed text, parts),
  UTF-8 encoding, BLAKE2b-128, ``int.from_bytes``, ``Seed`` and child objects;
* MT19937 seeding through ``random.Random(seed)`` and through the C seed alone;
* the first draw (``random``/``uniform``/``choice``/``randint``);
* the complete public operations (``derive``, ``branch``, ``branch().random()``).

``--count HARNESS SCENARIO`` instead wraps the RNG of ``--source`` and runs one
scenario of a MatchEngine benchmark harness in-process (for example #1916's
``scripts/benchmark_match_engine.py`` at ``1935e535``), counting derivations,
generator materializations and draws per method and per rally. Counting slows
the run; its times are meaningless.

    python scripts/profile_rng_seed_costs.py --source <tree> --json
    python scripts/profile_rng_seed_costs.py --source <tree> --count <harness.py> ko64
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import platform
import runpy
import sys
import timeit
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT_SEED = 2**127 + 0x1234567890ABCDEF


def _import(source: Path):
    sys.path.insert(0, str(source / "src"))
    import beta_engine.core.rng as rng_module

    if not Path(rng_module.__file__).resolve().is_relative_to(source.resolve()):
        raise SystemExit(f"imported {rng_module.__file__} outside {source}")
    return rng_module


def _time(stmt: str, namespace: dict, number: int, repeat: int) -> float:
    best = min(timeit.repeat(stmt, globals=namespace, number=number, repeat=repeat))
    return best / number * 1e6


def _transient_bytes(stmt: str, namespace: dict) -> int:
    code = compile(stmt, "<op>", "exec")
    exec(code, namespace)  # warm caches outside the trace
    tracemalloc.start()
    tracemalloc.reset_peak()
    base, _ = tracemalloc.get_traced_memory()
    exec(code, namespace)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak - base


def decompose(source: Path, number: int, repeat: int) -> dict:
    rng_module = _import(source)
    import hashlib
    import random
    import _random

    from beta_engine.core.types import Seed, SeedScope

    DeterministicRng = rng_module.DeterministicRng
    parent = DeterministicRng(PARENT_SEED)
    parent.derive(SeedScope.MATCH, "warm")
    text = str(PARENT_SEED)
    scope = SeedScope.MATCH
    parts = ("segment", 7)
    material = "|".join(("v1", scope.value, text, *map(str, parts)))
    material_bytes = material.encode("utf-8")
    digest = hashlib.blake2b(material_bytes, digest_size=16).digest()
    value = int.from_bytes(digest, byteorder="big", signed=False)
    seeded = random.Random(1)
    namespace = {
        "hashlib": hashlib, "random": random, "_random": _random, "Seed": Seed,
        "DeterministicRng": DeterministicRng, "parent": parent, "text": text,
        "scope": scope, "parts": parts, "material": material,
        "material_bytes": material_bytes, "digest": digest, "value": value,
        "seed_object": Seed(value), "seeded": seeded,
    }
    components = {
        "identity_join": '"|".join(("v1", scope.value, text, *map(str, parts)))',
        "scope_value": "scope.value",
        "utf8_encode": 'material.encode("utf-8")',
        "blake2b_128": "hashlib.blake2b(material_bytes, digest_size=16).digest()",
        "int_from_bytes": 'int.from_bytes(digest, byteorder="big", signed=False)',
        "seed_object": "Seed(value)",
        "rng_object_from_seed": "DeterministicRng(seed_object)",
        "mt_random_constructor": "random.Random(value)",
        "mt_c_seed_only": "_random.Random.seed(seeded, value)",
        "draw_random": "seeded.random()",
        "draw_uniform": "seeded.uniform(1.0, 2.0)",
        "draw_choice": 'seeded.choice(("LEFT", "RIGHT"))',
        "draw_randint": "seeded.randint(1, 6)",
        "api_derive_2_parts": 'parent.derive(scope, "segment", 7)',
        "api_branch_2_parts": 'parent.branch(scope, "segment", 7)',
        "api_branch_1_part": 'parent.branch(scope, "closure")',
        "api_branch_random": 'parent.branch(scope, "closure").random()',
        "api_branch_uniform": 'parent.branch(scope, "duration").uniform(1.0, 2.0)',
        "api_branch_choice": 'parent.branch(scope, "box").choice(["LEFT", "RIGHT"])',
        "api_branch_branch_random": (
            'parent.branch(scope, "segment", 7).branch(scope, "closure").random()'
        ),
    }
    report = {}
    for name, stmt in components.items():
        report[name] = {
            "us": round(_time(stmt, namespace, number, repeat), 4),
            "transient_bytes": _transient_bytes(stmt, namespace),
            "stmt": stmt,
        }
    generator = random.Random(value)
    return {
        "source": str(source),
        "rng_file": rng_module.__file__,
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "machine": platform.machine(),
        "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
        "number": number,
        "repeat": repeat,
        "generator_retained_bytes": sys.getsizeof(generator),
        "components": report,
    }


def count(source: Path, harness: Path, scenario: str) -> dict:
    rng_module = _import(source)
    os.environ["MATCH_BENCH_SOURCE_ROOT"] = str(source)
    cls = rng_module.DeterministicRng
    counts: collections.Counter = collections.Counter()
    materialized: collections.Counter = collections.Counter()

    original_derive_paths = {name: getattr(cls, name) for name in ("derive", "branch")}

    depth = [0]

    def counted(name, original):
        # ``branch`` may call ``derive`` internally (it does on buuk): count
        # only the outermost call so both trees count the same operations.
        def wrapper(self, scope, *parts):
            if not depth[0]:
                counts[f"{name}_calls"] += 1
                counts[f"parts_{len(parts)}"] += 1
            depth[0] += 1
            try:
                return original(self, scope, *parts)
            finally:
                depth[0] -= 1

        return wrapper

    for name, original in original_derive_paths.items():
        setattr(cls, name, counted(name, original))

    for name in ("random", "randint", "uniform", "choice", "shuffle"):
        original = getattr(cls, name)

        def draw(self, *args, _original=original, _name=name):
            if self._generator is None:
                counts["materializations"] += 1
                materialized[self.seed.value] += 1
            counts[f"draw_{_name}"] += 1
            return _original(self, *args)

        setattr(cls, name, draw)

    captured = {}
    argv = sys.argv
    sys.argv = [str(harness), scenario, "--repeats", "1", "--in-process"]
    stdout = sys.stdout
    try:
        import io

        buffer = io.StringIO()
        sys.stdout = buffer
        runpy.run_path(str(harness), run_name="__main__")
    except SystemExit:
        pass
    finally:
        sys.stdout = stdout
        sys.argv = argv
    for line in buffer.getvalue().splitlines():
        if line.startswith("{"):
            captured = json.loads(line)
    rallies = captured.get("engine_rallies_last") or 0
    total = dict(counts)
    total["materialized_distinct_seeds"] = len(materialized)
    total["materialized_same_seed_again"] = sum(c - 1 for c in materialized.values() if c > 1)
    per_rally = {k: round(v / rallies, 2) for k, v in total.items()} if rallies else {}
    return {
        "source": str(source),
        "harness": str(harness),
        "scenario": scenario,
        "matches": captured.get("engine_calls_last"),
        "rallies": rallies,
        "fingerprint": captured.get("fingerprint"),
        "counts": total,
        "per_rally": per_rally,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=ROOT)
    parser.add_argument("--number", type=int, default=200_000)
    parser.add_argument("--repeat", type=int, default=7)
    parser.add_argument("--count", nargs=2, metavar=("HARNESS", "SCENARIO"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.count:
        report = count(args.source.resolve(), Path(args.count[0]).resolve(), args.count[1])
    else:
        report = decompose(args.source.resolve(), args.number, args.repeat)
    if args.json:
        print(json.dumps(report, sort_keys=True))
    elif args.count:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"{report['source']}  Python {report['python']}")
        for name, row in report["components"].items():
            print(f"{row['us']:9.3f} us {row['transient_bytes']:7d} B  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
