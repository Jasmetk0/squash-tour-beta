# RNG seed hierarchy and rally RNG cost (#1917, 27 November 2026)

Branch `claude/blissful-shannon-o0j8xo` from `buuk 29784d5`. The session could push only
to this assigned branch. The only production change is `src/beta_engine/core/rng.py`.
The RNG backend (stdlib MT19937), seed protocol (`v1|scope|seed|parts`, BLAKE2b-128),
draw order, sporting rules, Saved formats, logs, hashes and validators are unchanged.
`match_engine.py` is not touched, so this branch does not conflict with #1916, #1907,
#1909 or #1910.

| Commit | Content |
| --- | --- |
| `ccd4d9e` bench | `scripts/profile_rng_seed_costs.py`: per-component decomposition of one child RNG, and `--count`, which counts RNG work per rally inside a real scenario |
| `61f6ee3` perf | `core/rng.py`, faster child RNG; `tests/core/test_rng_byte_equivalence.py` |
| `201be5f` perf | the reused `(scope, prefix)` pair is published in one assignment, so a parent shared by threads never mixes two scopes (found in self-review, +0.04 % instructions) |
| evidence | `scripts/rng_differential_corpus.py`, `scripts/live_match_sqlite_restart_equality.py`, this report, `docs/evidence/rng_seed_hierarchy_2026_11_27/` |

The final `src` is `201be5f`. Every acceptance run in §4, §5 and §7 was repeated on it.
The decomposition, the phase profile and the variant comparison (§2, §3) were measured
on `61f6ee3`. Later commits change only scripts and docs (`git diff 201be5f HEAD -- src`
is empty).

## 1. Result in one paragraph

Results stay byte-identical everywhere I checked. The deterministic CPU work of a whole
64-player knockout falls by **2.86 %**, counted as instructions over the whole process
(71.108 → 69.075 G, 63 matches, 3,382 rallies). The production corpus falls by
**2.79 %**. That is about 600 k instructions per rally. On top of the #1916 pin the
absolute saving is about the same (2.03 vs 2.07 G instructions), i.e. **−3.56 %** (ko64)
and **−3.50 %** (corpus): the two changes add up. Wall time on this shared 4-vCPU VM is noisy at the 3 % level. The final
paired A/B (6 alternating rounds) gives −5.5 % (ko64), −4.2 % (ko128) and +2.5 % (corpus)
wall, and −5.1 %, −4.0 % and −1.1 % engine. The same-day A/A gives −2.1 %, −0.8 % and
−2.1 %, and an earlier run of the first implementation gave −1.6 %, +0.7 % and −1.6 %.
The timings agree with the instruction counts but cannot prove them on their own. Peak
RSS is unchanged (127.8 MB). The saving is real but small. The dominant cost, MT19937
seeding, is unchanged: it cannot be made cheaper with the same outputs without a new
generator.

## 2. Where the RNG time goes (`buuk`, measured separately from the timed runs)

Real ko64 (`profile_rng_seed_costs.py --count`, #1916 harness `1935e535`): per rally
**63.1 child RNGs**, **48.5 materialized MT19937 generators**, 54.4 draws (31.2 `random`,
21.9 `uniform`, 1.3 `choice`). 99.9 % of generators are seeded from distinct seeds (221 of
164,153 repeat). The counts are identical on the candidate.

Decomposition of one child, CPython 3.12.3, best of 7 × 200k (`--source <tree> --json`):

| Component | `buuk` µs | candidate µs |
| --- | ---: | ---: |
| identity join `"\|".join(("v1", scope.value, text, *map(str, parts)))` | 0.38 | (prefix reused) |
| UTF-8 encode | 0.03 | 0.03 |
| BLAKE2b-128 digest | 0.33 | 0.33 |
| `int.from_bytes` | 0.07 | 0.07 |
| `Seed(value)` | 0.13 | lazy |
| `DeterministicRng(seed)` | 0.10 | 0.06 (`_child`) |
| `random.Random(seed)` (MT19937 `init_by_array` of a 128-bit key + Python `__init__`/`seed`) | **5.22** | 4.8 (C seed only) |
| C `_random.Random.seed` alone | **4.82** | 4.77 |
| first draw `random`/`uniform`/`choice` | 0.03/0.07/0.16 | same |
| **`branch(...)` only** | 1.36–1.43 | **0.89–0.97** |
| **`branch(...).random()`** | 7.03 | **6.30** |
| `branch().uniform()` / `branch().choice()` | 7.17 / 7.23 | 6.33 / 6.63 |

So seeding is about 4.8 µs × 48.5 ≈ 233 µs per rally, roughly 12 % of an
approximately 1.9 ms `buuk` rally. That cost sits inside CPython's C code. A generator
holds 2,552 B. The candidate keeps the same number of generators for the same
lifetimes, so the retained memory does not change. The tracemalloc transient bytes in
the evidence JSON are a coarse peak with a ~160 B measurement floor.

Sampled phase profile (`profile_match_engine_phases.py set`, 24 matches, separate run):
the RNG phases fall from 0.634 s to 0.441 s CPU (`derive+seed` + `draws`). The candidate
seeds inside the draw method, so the sampler books seeding under "draws". Heap rise is
18.8 → 16.8 MiB. That is one sample per side, indicative only.

## 3. Variants examined

| # | Variant | Result | Decision |
| --- | --- | --- | --- |
| A | **Candidate** (`61f6ee3`): (1) reuse the `v1\|<scope>\|<seed>` prefix per `SeedScope` member, never for foreign scope objects; (2) the `branch` child is built directly from the derived int, with `Seed` created only when `.seed` is read; (3) an exact-`int` seed builds its generator with `random.Random.__new__` + `_random.Random.seed` + `gauss_next = None`. These are exactly the steps of `random.Random(x)`, so `getstate()` and `vars()` are identical; any other value, or a stdlib whose `random.Random` is not directly on the C generator, uses the constructor; (4) `__slots__`, and draws dispatch directly instead of through a property | ko64 −2.90 % instructions, corpus −2.81 % (final `201be5f`: −2.86 % / −2.79 %); micro −0.5 µs per derive, −0.7 µs per draw-branch | **applied** |
| B | Prepared BLAKE2b state of the prefix, `copy()` + `update(parts)` per child (`c4d5d94`, local) | Byte-identical; on top of A ko64 −0.16 %, corpus −0.19 % instructions (−0.12 µs per derive; costs one hasher per parent) | rejected: too small to measure, and more state |
| C | One-shot helpers (`_branch_random`, `_branch_uniform`) without a child object | −0.11 to −0.15 µs per one-shot. Applies to about 32 k of the 164 k ko64 generators as direct chains; the other ~132 k would need signature changes in about 15 `match_engine.py` functions (the #1916 conflict area). At most ≈0.3 % | rejected, micro-measured only |
| D | Hoist `_probability_logit(base_probability)` (same input within a rally) out of `_next_control_state` / terminal / opening | 0.25 µs × ≈5.9 calls saved per rally ≈ 1.5 µs/rally, 0.07 % | rejected, micro-measured only |
| E | Reuse generator state or cache values for a repeated seed | Only 0.07 repeated seeds per rally; `setstate` costs more than seeding | rejected |
| F | Native seeding (proposal only, no production change) | `native_mt19937_seed_bound.c` in the evidence folder: CPython-equivalent seed + twist takes 4.33 µs. With the constant `init_genrand(19650218)` prefix precomputed and copied, it takes 3.41 µs, with the same state (asserted). The `init_by_array` chain is serial, so a native module would save ≤0.9 µs per generator (≈2.3 % of a rally) and would need a new dependency/build contract and a cross-platform proof | **not proposed** for production. Numbers handed to Work |

The hidden-control path (#1917 point 1, last bullet): every per-rally projection with
identical inputs is already built once per match or once per rally (#1916 §3 path 1).
What remains between segments uses changing inputs (intensities, control state,
cumulative workloads). The only exact repeat found is D, and it is below the noise.

## 4. Equality evidence (reference = pinned `buuk 29784d5`, separate processes)

- **RNG API differential corpus** (`rng_differential_corpus.py`): 11,086 API records
  plus 37,503 random-program records. They cover derive/branch at one to six levels, empty
  suffixes, repeated branches with further draws, `random/uniform/randint/choice/shuffle`
  interleaved, roots 0/±1, 2³²±1, ±2⁶³, 2¹²⁸±1, 2¹²⁹, 10⁶⁰, −10⁸⁰ and 2⁴⁰⁰⁰, `Seed` and `int`
  roots, non-int `Seed` values (float, str, bool, bytes), invalid roots, Unicode, empty,
  pipe, NUL, None, float, inf, bool, tuple, enum and `Seed` parts, all scopes, alternating
  scopes, a foreign scope object with a mutated `value`, the hierarchy helpers and
  generator `getstate()` after each program. **Equal** for `buuk` and the candidate on
  CPython 3.11.18, 3.12.3 and 3.13.18, each with `PYTHONHASHSEED` 0, 1917 and random
  (18 processes). API and random-corpus digests are also identical across the three
  Python versions.
- **Non-match consumer:** `InitialPlayerPoolGenerator.generate` for 6 cohorts of 3 to 128
  players (quotas, age limits, `country_serial.v1`, a 128-bit seed). Complete
  `model_dump_json` bytes are **equal** on 3.12 and 3.13; pydantic is missing on 3.11.
- **Matches and draws** (#1916 driver `scripts/ab_match_kernel.py` run from its own
  checkout `1935e535`, separate worktrees and output): single, set, lab, cases (deuce,
  PAR-15, BO1, retirements, Health, the step-wise Next Rally path), corpus (Admin inputs,
  Health, gameplans, 10-10/PAR-15 tie-breaks, long retriever rallies, BO1/3/5,
  retirements), restart (Next Rally → serialize → **new process** → finish; equals both
  the uninterrupted step path and bulk), ko32, ko64, ko128 and http64 (real uvicorn +
  SQLite, full response body). All **10 scenarios are equal** with 19 digests per
  `MatchResult`: full JSON bytes, sorted JSON, rally/timeline/stamina chains, hash
  chains, gameplan/rules/control contexts, rally numbers and times, stamina states, and
  the bracket path. That is 359 engine results and 19,176 rallies. The timing passes
  re-checked the fingerprints of every sample (A/B, #1916-combined and variant B).
- **Live match on real SQLite with a restart** (`live_match_sqlite_restart_equality.py`):
  four cases (classic, mismatch, long rallies, a negative 80-bit seed). Each committed
  Next Rally runs in its own session, then the process exits after 1 to 41 rallies; a
  **new process** opens the file and continues to the final result. Every response,
  every state fingerprint and the final result are **byte-identical** between trees and
  equal to bulk; `integrity_check` is `ok`.
- **HTTP/SQLite black box** (`profile_native_week_ab.py ab --scenario w6`, unchanged
  shared driver, `BETA_ENGINE_NEW_RUN_SAVED_STORAGE=saved_v2`): a real native Tour week
  over uvicorn. It makes 16 HTTP requests (18 on the deliberate-retry path), plays three
  matches, confirms results, makes **three explicit Saves**, moves S1W4 → S1W5 and runs
  every case in a new process from the Saved fixture. Verdict **equal** for normal and
  retry. The input SHA-256 `2e7c7884…` is unchanged afterwards.
- **Tests** (`tests/core/test_rng_byte_equivalence.py`, 8 tests): compare against the
  verbatim `buuk` class. Mutation run on `201be5f` in a separate worktree with
  `python -B`/`PYTHONDONTWRITEBYTECODE=1`: 8 of 9 mutants are caught (a cached foreign
  scope, `==` instead of `is`, a stale child prefix, missing `gauss_next`, `repr`
  instead of `str`, field order, little-endian digest, uncached `Seed` identity). The
  survivor is an equivalent mutant: `isinstance` instead of `type is int` takes the same
  C path. The fast path is restricted to exact `int` on purpose.

No new cache proof over Saved history; nothing stored changes.

## 5. Performance (same VM, pinned commits, fresh processes, `PYTHONHASHSEED=0`)

Host: 4 vCPU Firecracker VM, Intel Xeon @ 2.30 GHz, Linux 6.18. CPython 3.12.3 venv from
`.github/requirements/fast-ci-linux.lock.txt` (pydantic 2.14.2). Driver: #1916
`ab_match_kernel.py` at `1935e535`, harness SHA-256 `00a71bdd…`. Each round runs A B B A
(even rounds) or B A A B (odd rounds); there are 6 rounds, i.e. 12 samples per side.
Every timed sample re-checks the scenario fingerprint.

**Deterministic instruction counts (valgrind 3.22 callgrind, whole process, warm `.pyc`):**

| Scenario | `buuk` | final `201be5f` | Δ | #1916 pin `1935e535` | pin + `61f6ee3`+`201be5f` | Δ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ko64 (63 matches, 3,382 rallies) | 71,107,506,584 | 69,075,018,269 | **−2.86 %** | 58,105,527,147 | 56,037,534,743 | **−3.56 %** |
| corpus (12 matches, 697 rallies) | 14,853,411,473 | 14,438,523,342 | **−2.79 %** | 12,209,312,620 | 11,781,605,966 | **−3.50 %** |

A/A repeatability: two `buuk` runs differ by 16,567 instructions (ko64) and 25,953
(corpus), below 0.0002 %. The first implementation `61f6ee3` measured −2.90 % / −2.81 %,
and variant B on top of it adds −0.16 % / −0.19 %. A cold `.pyc` cache adds compilation
work to the first run of a new worktree, so every tree was compiled first
(`python -m compileall -q src scripts`).

**Wall/CPU time, final head** (median of 12 samples; the paired value is the median
per-round change Σ B / Σ A, with min and max over the 6 rounds):

| | rallies | A/A wall paired | A/B wall | A/B wall paired [min, max] | A/B process CPU paired | A/B engine paired [min, max] | engine µs/rally | peak RSS MB |
| --- | ---: | ---: | --- | --- | ---: | --- | --- | --- |
| ko64 | 3,382 | −2.1 % | 8.51 → 8.30 s | −5.5 % [−8.0, +5.9] | −5.3 % | −5.1 % [−8.3, +4.9] | 1,899 → 1,837 | 127.8 → 127.9 |
| ko128 | 6,779 | −0.8 % | 16.39 → 15.41 s | −4.2 % [−9.7, +0.4] | −3.9 % | −4.0 % [−9.1, −1.0] | 1,916 → 1,807 | 127.7 → 127.3 |
| corpus | 697 | −2.1 % | 1.32 → 1.37 s | +2.5 % [−9.1, +9.8] | +0.8 % | −1.1 % [−10.5, +5.9] | 1,713 → 1,699 | 74.2 → 74.2 |
| pin → pin + candidate, ko64 | 3,382 | | 7.66 → 7.49 s | −3.5 % [−9.7, +8.6] | −3.9 % | −4.2 % [−10.9, +9.8] | 1,660 → 1,602 | 127.8 → 127.9 |
| … ko128 | 6,779 | | 14.00 → 13.81 s | −4.7 % [−11.8, +2.8] | −4.5 % | −6.1 % [−13.1, −0.4] | 1,592 → 1,548 | 127.7 → 127.7 |
| … corpus | 697 | | 1.13 → 1.15 s | +1.4 % [−6.5, +7.8] | +2.2 % | −0.2 % [−6.3, +5.4] | 1,439 → 1,436 | 74.2 → 74.2 |

The same driver and host gave the following for the first implementation `61f6ee3`,
about three hours earlier (`first-implementation-61f6ee3/`): A/A wall paired −3.4 %,
+1.7 % and −0.8 %; A/B wall paired −1.6 %, +0.7 % and −1.6 %; engine paired −2.9 %,
−0.1 % and −2.1 %. Per-round standard deviation is ≈4 %, the same order as the effect.
I therefore treat the timing tables as consistent with a −2 to −4 % gain but not as proof
of it; the instruction counts are the proof. The work does not move into serialization
or held memory: the fingerprints, peak RSS, the number of generators and their lifetimes
are all unchanged.

## 6. Reproduce

```bash
python3.12 -m venv .venv && .venv/bin/pip install --only-binary=:all: --require-hashes \
  -r .github/requirements/fast-ci-linux.lock.txt
a=29784d51d01d9d747705be8abae30f0c82706c1e; b=201be5fc93ac0b6df8e0fc579dd5a58ff7c6684c
git worktree add --detach ../pr1916 1935e53555c1f6d3d11481d3e83cb9687bceb3cd   # #1916 driver
(cd ../pr1916 && ../squash-tour-beta/.venv/bin/python scripts/ab_match_kernel.py --a $a --b $b \
  --out ../w/eq --rounds 0 --python $PWD/../squash-tour-beta/.venv/bin/python \
  single set lab cases corpus restart ko32 ko64 ko128 http64)          # equality only
(cd ../pr1916 && .../python scripts/ab_match_kernel.py --a $a --b $a --out ../w/aa --rounds 6 \
  --python ... --skip-equality ko64 ko128 corpus)
(cd ../pr1916 && .../python scripts/ab_match_kernel.py --a $a --b $b --out ../w/ab --rounds 6 \
  --python ... ko64 ko128 corpus)
# instruction counts, per tree (python -m compileall -q src scripts first):
MATCH_BENCH_SOURCE_ROOT=<tree> PYTHONHASHSEED=0 valgrind --tool=callgrind \
  --callgrind-out-file=<out> .venv/bin/python ../pr1916/scripts/benchmark_match_engine.py ko64 --repeats 1 --in-process
python scripts/rng_differential_corpus.py --source <tree> --emit <file>   # per tree/Python/hash seed
python scripts/rng_differential_corpus.py --compare <files...>
python scripts/live_match_sqlite_restart_equality.py --a <buuk tree> --b <candidate tree> --out <dir>
BETA_ENGINE_NEW_RUN_SAVED_STORAGE=saved_v2 python scripts/profile_native_week_ab.py prepare --database <db>
BETA_ENGINE_NEW_RUN_SAVED_STORAGE=saved_v2 python scripts/profile_native_week_ab.py ab --a $a --b $b \
  --sha256 <sha of db> --input <db> --out <dir> --scenario w6
python scripts/profile_rng_seed_costs.py --source <tree> --json
python scripts/profile_rng_seed_costs.py --source <tree> --count ../pr1916/scripts/benchmark_match_engine.py ko64
```

Input fingerprints: ko64 `3f08eb6f…`, ko128 `795da202…`, corpus `c66519d3…`, http64
`ea1506df…`, restart `5736f4e1…`. Every value is in
`docs/evidence/rng_seed_hierarchy_2026_11_27/`.

## 7. Tests run (final `src` `201be5f`, unless stated)

- `tests/core`: 12 pass, 8 of them new. Mutation result: see §4.
- Process note: my first mutation runs edited the main checkout in place. A mutant of
  the same size, restored within the same second, left a stale `rng.cpython-312.pyc`
  there, and the HEAD check then failed. The committed source was correct
  (`wt/cand` at `201be5f` was identical byte for byte and passed). Every measurement
  and equality run used separate worktrees compiled from their own sources. After
  `__pycache__` was deleted, HEAD passes, and the mutants were rerun without bytecode
  as described in §4.
- `-m pr_critical tests/core tests/domain`: 1,069 pass, 1 fail. `buuk` (`29784d5`) has
  1,068 pass and the same failure
  (`test_calendar_postseason_knockout_version::test_season_reducer_rejects_foreign_sources_before_replay`,
  `SimpleNamespace` without `schema_version`); #1916 reports the same.
- Focused match/population/live-state suites (`tests/core`, 14 `tests/domain/test_match_*`
  and rally files, initial pool, draw, entries, career, finals, progression,
  `tests/infrastructure/test_live_match_state.py`): 227 pass, 4 fail; `buuk` 219 pass,
  the same 4 fail (`test_match_input_snapshot` ×3, `test_rally_rules` hash protection;
  pydantic tuple expectations, also reported by #1916). These pre-existing failures are
  handed to Work, not changed here.
- `ruff 0.6.9 check` passes on every changed Python file.
- The full `pr_critical` marker (4,122 tests) was started on both trees and stopped
  after 30 min at about 80 tests per tree, because the first files are hour-scale FAX
  scenarios. It was **not run**; CI must provide it. No browser test, no Windows run,
  no hosted CI.

## 8. Open / for Work

- The remaining RNG cost is MT19937 seeding (≈12 % of a rally), fixed by the stdlib
  backend. Variant F bounds what a native module could save (≤0.9 µs per generator).
  Fewer generators would change the seed protocol or draw order and are out of scope.
- Wall-time gains below ~5 % cannot be resolved on this VM; deterministic instruction
  counts (callgrind) are the cheaper and more reliable acceptance metric for such
  changes. Linux-only; not measured on Windows.
- Accept or reject the restriction of the fast seed path to `type(value) is int` and
  `random.Random.__bases__ == (_random.Random,)`. It is deliberately conservative, and
  other CPython layouts fall back to the constructor.
