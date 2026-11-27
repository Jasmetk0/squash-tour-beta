# MatchEngine for wide draws: one hash per event, byte-identical (27 November 2026)

Task #1911. Branch `claude/task-1911-implementation-ab-l2pmfe` from `buuk 29784d5`
(the issue proposed `claude/perf-match-kernel-wide-draw`; the session may push only
to its assigned branch). Draft only; Radim merges.

Scope: `src/beta_engine/domain/matches/{content_hash,match_engine,rallies,stamina,timeline}.py`,
direct tests, the match benchmark (`scripts/benchmark_match_engine.py`,
`scripts/profile_match_engine_phases.py`) and a new pinned driver
(`scripts/ab_match_kernel.py`). Untouched: `core/rng.py`, `slot_batch.py`,
`match_workers.py`, `calendar_match_state.py`, `calendar_global_slots.py`, the shared
A/B scripts, Save/Restore/replay, Saved format, Tour services, Full Simulation, ATP,
frontend, Master, workflows, timeouts. No sporting rule, probability, RNG draw, seed
branch, schema, hash definition, history volume or output byte changes. Open PRs #1905,
#1907, #1909 and #1910 have no file in common with this branch.

## Commits (measurement separable from each optimization)

| Commit | Content |
| --- | --- |
| `3593718` bench | 32/64/128 Lab knockouts, `http64`, production corpus, live restart in a new process, `--chains`/`--emit`, `MATCH_BENCH_SOURCE_ROOT`, `ab_match_kernel.py` |
| `2b220af` perf 1 | engine-fresh events enter their logs without a second identical hash |
| `1aa1043` perf 2 | event hashes encode without circular-reference bookkeeping |
| `2302b72` perf 3 | stamina/control validators use prebuilt member tables |
| `b804edb` test | buuk-pinned production corpus, stored-record rejection |

## 1. Contract and measurement

`scripts/benchmark_match_engine.py` scenarios (fresh process each):

| Scenario | Real path | Matches |
| --- | --- | ---: |
| `ko32` / `ko64` / `ko128` | `TournamentTestLabService` knockout, real draw and bracket kernels, `MatchEngine.simulate(context)` | 31 / 63 / 127 |
| `http64` (`http16`) | real uvicorn server + disposable SQLite, `POST /admin/labs/tournament/run`, complete response body fingerprinted | 63 (15) |
| `corpus` | production input path: `MatchInputSnapshot.create` + every effective snapshot (timing, stamina, calibration, gameplans, rules, Health) | 12 |
| `restart` | `Simulate Next Rally` for N rallies, working input/state serialized to JSON, a NEW process reloads them (full validation) and finishes; must equal the uninterrupted step path and the bulk result byte for byte | 4 |
| `single`, `set`, `lab`, `cases` | unchanged historical scenarios | 1 / 24 / 24 / 10 |

Corpus: human Admin inputs (form, sharpness, fatigue, health and travel modifiers,
upset variance 0/0.05/0.3), Health snapshots (active Injury with permanent
consequence, recovering Illness), gameplans and rally rules in every match, forced
tie-breaks (upset variance 0, 6 and 9 deuce rallies), PAR-15, long retriever rallies
(up to 16 control segments), BO1/BO3/BO5, explicit and probabilistic retirement.

Named difference: the Lab knockout calls `simulate(context)` with default effective
snapshots, not a Run calendar slot with frozen `MatchInputSnapshot`s; the production
input path is covered by `corpus`/`restart`, and a real native Tour week (HTTP, SQLite,
Saved v2, explicit Save, stored-history replay) by the black-box
`scripts/profile_native_week_ab.py` A/B below. The native wide slot (64/128 matches in
one global slot) was not driven: building that Run requires the slot/worker services
this task must not touch; workers stay off everywhere.

The server path and the real engine are proven per run: every report carries the
imported `beta_engine/__init__.py`, the engine call and rally counts (the wrapper sits
on `MatchEngine.simulate`, also inside the uvicorn thread), and the driver refuses a
report whose imported file lies outside the pinned worktree.

`scripts/ab_match_kernel.py --a <sha> --b <sha>`: two detached worktrees, one harness,
`PYTHONHASHSEED=0`, same Python/venv. Pass 1 is the equality run (`--chains`,
not timed). Pass 2 is A B B A per round in fresh processes; child CPU and peak RSS
come from `os.wait4`. A/A uses the same commit in two worktrees.

## 2. Where the time went (`buuk`, profiled separately from the timed runs)

Machine: 4 vCPU Firecracker VM (shared host), Linux 6.18, CPython 3.12.3 from the
locked CI requirements (`.github/requirements/fast-ci-linux.lock.txt`, pydantic
2.14.2), `PYTHONHASHSEED=0`.

Uninstrumented `ko128` on `buuk`: 127 real matches, 6,779 rallies, 19.6 s wall,
19.5 s CPU, MatchEngine 14.5 s (74 %; 114 ms per match, 2.1 ms per rally), Lab
tournament infrastructure 5.2 s (including ~1.8 s of first imports), peak RSS
131 MB. A `py-spy` sampling profile (250 Hz, separate run) puts 77.5 % of all samples
inside `MatchEngine.simulate`; the rest is the Lab service (its per-match result
dump + fingerprint is 12.5 %) and imports.

Inside the engine (`py-spy`, exclusive time, `ko128`): JSON encoding of hash
payloads 18.3 %, pydantic construction/dump/copy 17.3 %, `random.Random` seeding and
draws 12.1 %, `core/rng.py` derivation 8.2 %, remaining Python in `match_engine.py`
15.5 %, `stamina.py` 10.7 %, `rallies.py` 7.2 %, enum attribute access 4.0 %. By phase:
hidden-control rally 31.5 % (≈45 RNG branches per rally), rally event creation 15.7 %,
stamina log build 13.4 %, **rally log assembly 9.4 %** (almost entirely the second
validation + hash of every event), live stamina advance 6.8 %, gameplans 4.9 %,
timeline 3.9 %.

Phase profile (`scripts/profile_match_engine_phases.py set`, CPU-time sampler,
24 production-path matches, 1,343 rallies; harness excluded):

| Phase | `buuk` CPU | candidate CPU | sampled heap rise `buuk` → candidate |
| --- | ---: | ---: | ---: |
| RNG derive + seed | 0.93 s | 0.82 s | 15.9 → 16.7 MiB |
| rally event hash | **0.78 s** | **0.43 s** | **31.0 → 18.4 MiB** |
| stamina transition hash | **0.33 s** | **0.12 s** | 3.1 → 3.3 MiB |
| rally loop + control | 0.33 s | 0.32 s | 20.6 → 20.7 MiB |
| stamina state math | 0.32 s | 0.33 s | 10.4 → 8.4 MiB |
| rally nested models | 0.20 s | 0.15 s | 7.7 → 6.1 MiB |
| gameplans | 0.14 s | 0.12 s | 6.2 → 6.7 MiB |
| attributes + probabilities | 0.14 s | 0.12 s | 4.5 → 4.8 MiB |
| timeline event hash | 0.09 s | 0.08 s | 2.8 → 2.2 MiB |
| **engine total** | **3.64 s** | **2.83 s** | **112.3 → 96.2 MiB** |

GC: 425 vs 432 collections, 0.36 s on both sides. One profile run per side on a
noisy host: individual small phases move by ±0.05 s; the hash phases moved far
beyond that. Microbenchmarks of one 9.7 KB rally event (`buuk`): `model_dump(json)`
54 µs, sorted `json.dumps` 136 µs (94 µs without the circular check), its log-entry
re-validation incl. hash 182 µs; stamina transition re-validation 48 µs; one RNG
branch 2.2 µs, `random.Random(seed)` 6.5 µs (6.4 µs even when the Python wrappers
are bypassed).

## 3. Changes

Paths explored (the issue asks for at least two):

1. **Immutable match inputs vs per-rally state (path 1) — examined, not applied.**
   The heavy projections (base strength, style/archetype matchup, stamina and timing
   profiles, gameplan snapshot, Health projection) are already built once per match.
   What remains per segment is small pure arithmetic (`_probability_logit` of the
   rally's base probability, `_control_pressure_factor`, `_executed_effort_intensity`),
   together below 3 % of engine CPU in the profile: a match-local memo would not
   clear the noise floor, so it was not added.
2. **No hollow re-assembly of identical bytes (path 2) — applied (perf 1).** Pydantic
   re-runs a model's `after` validator for every model instance placed in a parent.
   Each engine event was therefore validated and hashed at creation, and validated and
   hashed again when `MatchRallyLog`/`MatchTimelineLog`/`MatchStaminaLog` were built:
   the second hash re-serialized the identical value (≈190 µs per 9.7 KB rally event).
   Now, inside one `MatchEngine.simulate`/`simulate_next_rally` call
   (`engine_event_scope`), that second run still executes every structural check but
   skips the hash comparison only for the exact instance the engine factory just hashed,
   only once (consumed), and only when none of its fields was reassigned (identity of
   every field value against the recorded tuple). Stored data, `model_validate`,
   `model_validate_json`, copies, public `create` factories and events created outside
   an engine call keep the full check. Nested mutation cannot be detected cheaply at
   run time; a static test (AST) pins that no module in `domain/matches` stores to a
   non-`self` attribute, `__dict__` item or `setattr`. The objection recorded in
   `docs/MATCHENGINE_PERFORMANCE.md` ("the only guard against mutating a created event
   before it is logged; needs Work's/owner's decision") is answered by that static
   guard plus the field-identity check; Work/the owner decide whether that suffices.
3. **Internal representation without changing bytes (path 3) — applied in two small
   steps.** perf 2: the three event hashes use one encoder with exactly the
   `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False)` options but
   `check_circular=False` (138 → 94 µs per rally payload). Input is always a fresh,
   acyclic JSON-mode dump; tests compare the bytes with `json.dumps` on awkward values
   and recompute every stored event hash independently. perf 3: stamina state math and
   validators iterate a module tuple of `StaminaDimension` (same members and order)
   instead of the Enum class, and per-call dict literals became constants; lookups keep
   first-match semantics and raise `StopIteration`/`KeyError` exactly as before (checked
   against `buuk`). No arithmetic, operation order, rounding, RNG draw or seed changed.

Rejected or out of scope: MT19937 seeding (inherent ~6.4 µs per child generator in C;
bypassing the Python `Random.__init__`/`seed` wrappers saves <0.1 µs), merged or skipped
RNG branches (change the draw sequence), building nested trace models from dicts to
avoid pydantic's nested `after` re-runs (≈2–3 %, larger diff in the rally loop), and
anything in `core/rng.py` (handed to Work below).

## 4. Results

Pins: A = `buuk 29784d51d01d9d747705be8abae30f0c82706c1e` (src tree `494a35ec`,
matches tree `2d8baa57`), B = `5a3308b4111eb4f6d3aca2e0a27c6df7d34b10be` (src tree
`91236374`, matches tree `606e7034`; `core/rng.py` blob `259b6359` on both sides),
harness SHA-256 `00a71bdd…`. Same VM, same venv, separate processes. Raw manifests,
equality reports and summaries: `docs/evidence/match_kernel_ab_2026_11_27/`.

**Noise.** The first A/A (3 rounds, fixed A B B A order) showed a position effect:
identical trees differed by +8.6…+10.6 % in every ko64 round. The driver now
alternates A B B A / B A A B; the decisive A/A and A/B below use 6 rounds (12 samples
per side and scenario). "Paired" is the median over rounds of
(B₁+B₂)/(A₁+A₂) − 1, with the per-round minimum/maximum in brackets.

| Scenario (matches / rallies) | Metric | A/A paired | A/B medians A → B | A/B paired |
| --- | --- | ---: | ---: | ---: |
| `ko64` Lab knockout (63 / 3,382) | wall | −0.1 % [−12.3, +6.3] | 12.13 → 10.52 s | **−13.8 %** [−15.7, −8.1] |
| | engine | +1.1 % [−12.9, +7.9] | 9.13 → 7.59 s | **−15.4 %** [−17.9, −8.0] |
| | process CPU | +1.2 % | 12.67 → 11.16 s | −12.9 % |
| `ko128` Lab knockout (127 / 6,779) | wall | 0.0 % [−3.8, +5.5] | 22.00 → 19.41 s | **−13.0 %** [−17.5, −8.7] |
| | engine | 0.0 % [−4.9, +6.0] | 17.49 → 14.92 s | **−14.5 %** [−21.3, −11.3] |
| | process CPU | −0.3 % | 22.52 → 20.00 s | −12.3 % |
| `corpus` production inputs (12 / 697) | wall | +0.2 % [−1.9, +16.5] | 1.81 → 1.56 s | **−11.0 %** [−19.8, −3.9] |
| | engine | +0.2 % [−2.8, +17.6] | 1.62 → 1.37 s | **−13.3 %** [−21.0, −5.2] |

Every one of the 6 A/B rounds is faster on B for ko64, ko128 and corpus (wall and
engine); for ko128 the A/A and A/B round ranges do not overlap. Per match / per rally
(engine medians): ko128 137.7 → 117.5 ms per match, 2.58 → 2.20 ms per rally; ko64
144.9 → 120.4 ms, 2.70 → 2.24 ms. Peak RSS is unchanged: 126.5–127.0 MB (ko64/ko128),
73.4 MB (corpus) on both sides; RSS of these processes is dominated by imports and the
Lab service, and each match's results are released after fingerprinting. The sampled
heap-rise proxy of the engine itself falls 112 → 96 MiB for 24 matches (−14 %), the
rally-hash part 31 → 18 MiB.

Earlier 3-round run (fixed order, therefore indicative only; includes `ko32`,
`http64`, `restart`): A/B paired wall ko32 −12.2 %, ko64 −16.3 %, ko128 −14.3 %,
corpus −19.2 %, http64 −11.0 % (engine −11.2 %), restart engine −10.2 % (its wall is
dominated by four child-process starts). Its A/A paired medians were −0.4 % (ko32),
+8.6 % (ko64, the position effect), +1.5 % (ko128), −8.0 % (corpus), −0.9 % (http64).
The http64 and restart rows are therefore not claimed beyond "faster engine, equal
bytes"; the real HTTP pass gains less in total because app start, HTTP and the Lab
response (≈7 s) are unchanged.

What the share means: MatchEngine was 74–80 % of a Lab knockout's wall time on
`buuk`; it gains ~15 %, so the whole draw gains ~13 %. A season is not claimed: the
earlier W6 native season measurements are dominated by Saved validation and
persistence, which this branch does not touch.

## 5. Determinism and stored history

- **Reference in a separate process on pinned `buuk`.** Every A/B equality pass runs
  the reference worktree (`buuk 29784d5`) and the candidate in separate processes with
  the same harness; for every real `MatchResult` it compares the complete
  `model_dump_json` bytes, sorted JSON, the result without logs, each rally, timeline
  and stamina chain, the event/transition hash chains, gameplan contexts, rules
  resolutions, control traces, rally numbers/sets/times/shots/segments/winners,
  timeline kinds and times, and stamina states before/delta/after (19 digests per
  result), plus the complete scenario output (bracket progression, HTTP body).
  Any difference is blocking (exit 1). No ID normalization was needed: the HTTP body
  contains no externally generated ID.
- **Bulk vs step vs restart.** `restart` serializes the live working input and state
  after 1, 15, 23 and 40 rallies, reloads them in a new process through full
  validation, finishes the match and requires the step outcomes and final bytes to
  equal both the uninterrupted step path and the bulk simulation. `cases` keeps the
  step-wise deuce and probabilistic-retirement corpus.
- **Golden fingerprints** (generated on `buuk` in a separate process) stay pinned in
  `tests/domain/test_match_engine_performance_equivalence.py`; this branch adds the
  production corpus `c66519d3…`.
- **Stored records.** The historical `legacy_engine_v8.json` (rally v5, timeline v1,
  stamina v3) and a current v6 result reload through full validation inside and
  outside an engine scope; changed rally seeds, broken previous hashes, timeline
  times, stamina states, gameplan evidence and truncated rally/stamina chains are
  rejected.
- **Changed boundary behaviour has regression tests:** one rehash skipped per fresh
  event and consumed; reassigned field rejected; copy/reload/outside-scope fully
  checked; scope cleared after a failed call; step path count; missing-dimension
  `StopIteration`, unknown-dimension `KeyError`, str-valued dimension; tampered
  stamina after-state; wrong control transition kind; two-level effort jump.
- Authoritative replay (stored-history re-simulation that compares stored bytes) sees
  byte-identical engine output, so it is unaffected.
- **Real server path, black box.** `scripts/profile_native_week_ab.py` (unchanged,
  shared driver) `prepare` + `ab --scenario w6 --a 29784d5 --b 5a3308b` with
  `BETA_ENGINE_NEW_RUN_SAVED_STORAGE=saved_v2`: a real uvicorn/SQLite native Tour week
  with 16 measured HTTP requests (18 in the deliberate-retry path), three matches,
  result confirmation, three explicit Saves and S1W4 → S1W5. Verdict `equal` for the
  normal and the retry path (full inspection, logical history, request digests,
  SQLite integrity); the input backup's SHA-256 was unchanged afterwards. One trial:
  34.6 vs 33.3 s wall, not a performance claim (three matches per week).

## 6. Reproduce

```bash
python3.12 -m venv .venv && .venv/bin/pip install --only-binary=:all: --require-hashes \
  -r .github/requirements/fast-ci-linux.lock.txt
a=29784d51d01d9d747705be8abae30f0c82706c1e
b=5a3308b4111eb4f6d3aca2e0a27c6df7d34b10be
.venv/bin/python scripts/ab_match_kernel.py --a $a --b $a --out work/aa --rounds 6 \
  --python .venv/bin/python --skip-equality ko64 ko128 corpus
.venv/bin/python scripts/ab_match_kernel.py --a $a --b $b --out work/ab --rounds 6 \
  --python .venv/bin/python ko64 ko128 corpus          # equality pass first, exit 1 on any difference
.venv/bin/python scripts/ab_match_kernel.py --a $a --b $b --out work/ab-wide --rounds 3 \
  --python .venv/bin/python ko32 ko64 ko128 corpus http64 restart   # the earlier 3-round run
MATCH_BENCH_SOURCE_ROOT=<tree> .venv/bin/python scripts/profile_match_engine_phases.py set --json
```

Corpus size: ko32/ko64/ko128 31/63/127 matches and 1,610/3,382/6,779 rallies; http64
63/3,318; corpus 12/697; restart 4/283 (+ the step path of each); cases 10.

## 7. Not resolved / next

- **Largest remaining cost: RNG (~25–29 % of engine CPU).** About 45 child RNGs per
  rally; each costs a BLAKE2b derivation (1.6 µs) and an MT19937 seeding of a 128-bit
  seed (6.4 µs in C). It is inherent in the seed hierarchy; any change belongs to
  `core/rng.py` and would change or re-architect the draw sequence, so it is handed to
  Work with these numbers, not touched here.
- Remaining engine cost after this branch: one hash per event (rally ≈ 150 µs:
  JSON-mode dump + sorted encoding; fixed by the hash definition), pydantic's nested
  `after` re-runs at event creation (≈2–3 %), stamina state model construction.
- Step mode (`Simulate Next Rally`) still re-validates and re-hashes every earlier
  event of the match in each new `MatchRallyWorkingState` (quadratic in rallies); only
  the new event's rehash is skipped. A fix touches the persisted working-state
  contract and is left for a separate decision.
- Outside the engine: the Lab service's per-match result dump + fingerprint (≈12 % of
  a knockout), app start, HTTP and response encoding. Not this task's area.
- Not measured: a native Run calendar slot with 64/128 matches (see §1); Windows;
  hosted CI runners. A short real native week (HTTP/SQLite/Saved v2) was run as a
  black-box integration check (§5), not as a performance claim.
- Decision for Work/owner: whether the scoped single validation (§3, path 2) is an
  acceptable replacement for the second hash as a mutation guard.
