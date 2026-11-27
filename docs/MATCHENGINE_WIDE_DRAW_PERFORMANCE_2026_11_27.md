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

## 2. Where the time went (`buuk`, sampled, separate from timed runs)

TBD

## 3. Changes

TBD

## 4. Results

TBD

## 5. Determinism and stored history

TBD

## 6. Not resolved / next

TBD
