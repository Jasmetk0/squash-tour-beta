# Slot matches on several CPU cores (26 November 2026)

Branch `claude/epic-shannon-zx6y13` from `buuk 29784d5`. Scope: computing new
matches of an already frozen Simulation Slot, and the measurements for it. No
sporting rule, seed, RNG draw, schema, hash definition, Saved format, Save,
Restore, replay authority, Task Center driver, timeout, ATP, CI or Master change.

## Result in one paragraph

Matches of one slot are pure functions of their frozen input, so they can be
calculated in other processes. With 3 spawn workers on a 4-core machine the
`execute` of a 32-match slot takes 11.2 s instead of 16.8 s (−33 %), 16 matches
6.8 s instead of 9.0 s (−24 %) and 8 matches 4.5 s instead of 5.4 s. The
whole measured operation (three slots, inspections, one explicit Save and a cold
restart) is 4–13 % faster, depending on the slot size. All outputs are
identical. The process group needs 170–300 MiB more memory. The gain is limited
by the parent, which must fully decode each returned result: in isolation,
64 matches reach about 1.9×, not 4×. The candidate is **opt-in**
(`BETA_ENGINE_MATCH_WORKERS`); off, the code path is the original sequential one.
A second, sequential saving hashes each played result once per match instead
of once per player.

## Where a slot spends its time (`buuk`, measured before the change)

A real HTTP/SQLite `next-slot` runs MatchEngine for every match **twice**: in
`apply_global_slot` and again in the independent post-write verification
(`verify_appended_slot` → `verify_competition_payload` → `accept_slot`). A cold
restart replays the matches a third time (`saved_checkpoint` →
`verify_competition_payload`). Explicit Save never runs MatchEngine. All three
paths go through `accept_slot` → `calculate_match`, so one change covers them.

Inputs common to all matches of a slot are decided in the parent before any
match runs: `freeze_slot` builds every `FrozenSlotMatch` from the same
`checkpoint.players` snapshot (projections, seed, Health snapshot, Saved head,
sequence). Each match then needs only its `MatchContext`, seed, log anchor
(`continuation_anchor`, the independent replay proof bound into the rally log)
and Health snapshot. State effects need the two players' records and stay in
the parent.

Handler-thread exclusive CPU, 8 parallel 8-player Editions, three slots
(32 + 16 + 8 matches, 56 matches, 168 MatchEngine calls), one Save, cold restart.
Separate instrumented runs (`--phases`), not the A/B timing runs:

| Phase | sequential | 3 workers |
| --- | ---: | ---: |
| MatchEngine in the parent | 19.41 s | 0 |
| bind + full `MatchResult` decode of worker results | – | 6.45 s |
| wait for workers (blocked, no CPU) | – | 0.00 s |
| encode requests | – | 0.003 s |
| state effects (`continuation_effects`) | 2.66 s (5.33 s before the hash change) | 2.74 s |
| freeze + prepare inputs | 0.63 s | 0.64 s |
| match inputs + anchor | 0.05 s | 0.05 s |
| checkpoint write | 4.19 s | 4.25 s |
| post-write verification, other work | 17.65 s | 17.97 s |
| execute, other work | 9.11 s | 9.09 s |
| explicit Save | 11.49 s | 11.12 s |
| inspections (incl. restart verification), other | 60.77 s | 61.60 s |

Decoding a result costs about a third of simulating it (isolated: 1.34 s vs
3.57 s for 24 matches; 755 KB JSON per match). That decode is the parent's own
validation and is kept, so the parent remains the bottleneck.

## Change

1. **`domain/matches/slot_batch.py`.** `simulate_batch` runs
   `(context, seed, anchor, health)` items and returns results in request order.
   The default is the original in-process call. An optional executor receives
   only `FrozenMatchRequest` (match id, seed, anchor, context JSON, Health JSON).
   The parent places every response by its own request index and accepts it only
   if index, match id and anchor are its own and the complete `MatchResult`
   validator accepts the bytes; it then checks match id, players, format and the
   rally-log anchor. A missing, duplicate, foreign or invalid result, an
   exception, a crash or a timeout discards the pool and recomputes the whole
   batch sequentially in the parent, which is the original behaviour. A genuine
   MatchEngine error is therefore raised exactly as before.
2. **`calendar_global_slots.py`.** `calculate_match` became
   `calculate_matches`: parent inputs/anchor → one batch → parent state effects
   and `CalendarContinuationMatch` in request order. Participation, collisions,
   walkovers, numeric Health checks and the snapshot stay in `accept_slot` and
   `prepare_global_slot`. The private replay memo keeps its per-match key, its
   decode of stored bytes and its LRU byte accounting; only missing results are
   batched.
3. **`infrastructure/match_workers.py`.** One `ProcessPoolExecutor` per server
   process, `spawn` start on every platform, started lazily (about 0.4 s for 3
   workers) and shared by every Run/Branch request, closed in the FastAPI
   lifespan. Workers get no session, connection, repository, Signed cache or
   Save authority. `BETA_ENGINE_MATCH_WORKERS`: unset/`0`/`off` = sequential,
   `auto` = `min(4, CPUs − 1)` (3 on the 4-core reference), or an explicit
   1–32. A batch of one match never uses workers.
4. **`calendar_match_state.advance_played_slot`.** The input and result
   fingerprints are computed once per match, and the unchanged source states once
   per call. Before, every one of the two effects hashed the full result dump
   again. The values are identical. This saves 2.7 s of 5.3 s handler CPU for
   168 effect calculations, which is too small to show above A/B noise for the
   whole operation.

Pause/Stop and Task Center semantics are unchanged: a slot step is still atomic
and the parent installs nothing until every result is accepted.

## Measurement procedure

Linux container, Intel Xeon @ 2.10 GHz, 4 cores (1 thread per core), 15 GiB
RAM, Python 3.12.3 in a venv from `.github/requirements/fast-ci-linux.lock.txt`,
`PYTHONHASHSEED=0`, default Saved storage (v1). Not the Windows reference PC: a
Linux `spawn` run shows the start method, not Windows behaviour.

A = `29784d51d01d9d747705be8abae30f0c82706c1e` (`buuk`). B =
`4f5d1bdc72dadcb762cd904d256f37aaefd2d8ee` (local; not pushed). Its `src` tree
`843f8349de1bf5a4d06739d7ad26ab42b6133fe6` and `tests` tree equal pushed commit
`17404cb`, which only drops a stray downloaded file from it. The later head
changes in `src` only the FastAPI lifespan order in `main.py` (an invalid
setting now fails inside `try`), outside the measured slot path.
Each A/B case uses detached worktrees, the driver from this checkout, a fresh
process per sample, A B B A per worker variant, a byte-identical copy of one
pinned fixture, and requires identical outputs across every sample.

```bash
python scripts/profile_slot_match_workers.py prepare --editions 8 --database work/e8x8.db   # also 1, 2, 4
python scripts/profile_slot_match_workers.py ab --a "$A" --b "$B" --input work/e8x8.db \
  --sha256 "$(sha256sum work/e8x8.db | cut -d' ' -f1)" --steps 3 --b-workers 0,2,3,4 --out work/ab-e8x8
python scripts/profile_slot_match_workers.py ab ... --b-workers 3 --prestart --out work/ab-e8x8-prestart
python scripts/profile_slot_match_workers.py run --root . --input work/e8x8.db --sha256 ... \
  --workers 3 --steps 3 --phases --out work/phases-w3.json
python scripts/profile_slot_match_workers.py isolated --corpus ko128 --matches 64 --workers 3
```

| fixture | Editions × entrants | slots of steps 1/2/3 | played matches / rallies | SHA-256 |
| --- | --- | --- | --- | --- |
| e1x8 | 1 × 8 | 4 / 2 / 1 | 7 / 335 | `360dd8b8f7f542acc7913ea606538f309f617a61f56ad3e375b84ef501fd64da` |
| e2x8 | 2 × 8 | 8 / 4 / 2 | 14 / 645 | `fdefddd70abd9f630f2e3969e69a884745e420f4c831cd509b5772a7c4090da5` |
| e4x8 | 4 × 8 | 16 / 8 / 4 | 28 / 1,337 | `4552548629df0325a6565e51588e74cf467ea05d5813a25daaca259f1d275106` |
| e8x8 | 8 × 8 | 32 / 16 / 8 | 56 / 2,688 | `79bb72040289ee91fb4ecab17958d30b65c8d2873bb482a6dfb4573105301923` |

Each fixture is a real HTTP/SQLite Run (W52, 2 seasons, population =
Editions × 8) with that many `calendar_tournament_edition.v2` Editions in week 4,
reviewed draws and explicit Saves, stored as one SQLite file without WAL.
Per step the driver records wall time, parent process CPU, CPU of every
descendant process, the peak RSS of the whole process group (parent and
descendants; sampled every 20 ms and at each step boundary; a just-forked
child before `exec` is not counted) and SQLite+WAL bytes. Equality evidence:
digests of all execute results, of every played match (`model_dump`), of the
saved inspection and of the restarted inspection (each without the random Saved
revision id), the checkpoint fingerprint, and restart = saved.

## Results (medians; wall s / parent CPU s / descendant CPU s / group peak RSS MiB)

### 32 + 16 + 8 matches (e8x8), A n = 8, each B variant n = 2

| step | A | B, sequential | B, 2 workers | B, 3 workers | B, 4 workers |
| --- | --- | --- | --- | --- | --- |
| slot 1 execute (32) | 16.83 / 16.73 / 0 / 724 | 16.18 / 16.09 / 0 / 736 | 13.57 / 11.38 / 9.11 / 908 | **11.23** / 10.11 / 8.68 / 964 | 11.79 / 10.78 / 9.57 / 988 |
| slot 2 execute (16) | 14.25 / 14.14 / 0 / 1072 | 13.96 / 13.84 / 0 / 1046 | 13.06 / 12.10 / 3.69 / 1188 | **11.25** / 10.79 / 3.28 / 1251 | 12.05 / 11.61 / 3.64 / 1300 |
| slot 3 execute (8) | 17.03 / 16.88 / 0 / 1172 | 18.61 / 18.41 / 0 / 1177 | 16.24 / 15.31 / 2.61 / 1329 | **14.86** / 14.37 / 2.52 / 1371 | 16.58 / 16.05 / 2.87 / 1451 |
| explicit Save | 23.94 / 23.91 / 0 / 1266 | 24.29 / 24.27 / 0 / 1268 | 23.98 / 23.99 / 0 / 1411 | 23.07 / 23.05 / 0 / 1453 | 24.77 / 24.70 / 0 / 1531 |
| restart, first inspect | 28.18 / 28.24 / 0 / 1925 | 27.77 / 27.81 / 0 / 1927 | 26.12 / 24.08 / 8.25 / 2194 | **24.06** / 23.01 / 8.12 / 2225 | 26.22 / 25.19 / 9.23 / 2303 |
| **whole operation, wall** | **131.45** | 133.39 | 124.96 | **114.74 (−12.7 %)** | 123.95 |
| whole operation, parent CPU | 131.35 | 133.06 | 118.99 | 111.72 | 120.98 |
| descendant CPU (whole run) | 0 | 0 | 23.67 | 22.60 | 25.32 |
| group peak RSS | 1,925 | 1,927 | 2,195 | 2,225 | 2,303 |
| SQLite + WAL, max | 208,613,712 B | same | same | same | same |

The whole operation also contains the inspections and previews, which do not
calculate matches. Save does not get slower, so the benefit has not moved into
Save; the cold restart verification profits too. Four workers on four cores
compete with the parent's decoding and lose to three. A host drift is visible
in A (126.6–146.1 s): one round per variant, so differences below about 3 %
(e.g. B sequential vs A) are noise.

### Warm pool: the same with the pool started before the first slot (n = 2 each)

The pool start took 0.39–0.42 s. First 32-match slot: A 16.49 s, B with a
pre-started pool 11.18 s (cold pool: 11.23 s above). Whole operation 132.16 →
116.41 s. Starting the pool is not a relevant part of the first slot.

### Slot size (execute wall, A → B 3 workers)

| matches in the slot | e1x8 | e2x8 | e4x8 | e8x8 |
| ---: | --- | --- | --- | --- |
| 1 | 3.29 → 3.20 (sequential path) | | | |
| 2 | 3.10 → 2.77 | 5.49 → 5.11 | | |
| 4 | 3.91 → 3.35 (cold pool) | 4.68 → 4.30 | 8.84 → 7.89 | |
| 8 | | 5.37 → 4.54 (cold pool) | 8.35 → 6.90 | 17.03 → 14.86 |
| 16 | | | 9.03 → 6.84 (cold pool) | 14.25 → 11.25 |
| 32 | | | | 16.83 → 11.23 (cold pool) |
| whole operation | 31.15 → 29.89 (−4.0 %) | 45.92 → 43.34 (−5.6 %) | 72.82 → 64.57 (−11.3 %) | 131.45 → 114.74 (−12.7 %) |
| group peak RSS | 574 → 755 MiB | 796 → 993 MiB | 1,300 → 1,497 MiB | 1,925 → 2,225 MiB |

The maximum SQLite+WAL size is identical for A and B in every case (45,295,744 /
67,213,736 / 114,360,248 / 208,613,712 bytes). e4x8 with 2 workers: whole
operation 70.53 s, 1,471 MiB. Samples: A n = 2
(e1x8, e2x8) or 4 (e4x8), each B variant n = 2. Slots of the same size get slower with a longer
history (e8x8 slot 3 has 8 matches but is the slowest step) because the
non-match work grows; this is the existing history cost, not this change.

### Isolated batch (Lab supplement; no HTTP, SQLite or Run state)

`ko128`: the 64 independent first-round matches of the `ko128` Tournament Lab
scenario players; `cases`: the abnormal corpus (deuce, PAR-15 BO3, BO1, explicit
and probabilistic retirement, injury Health). Warm batch wall in seconds
(first batch with a cold pool in brackets); all digests equal per size:

| matches | ko128 seq | 2 w | 3 w | 4 w | cases seq | 3 w |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 0.58 | 0.43 (0.72) | 0.45 (0.69) | 0.43 (0.65) | 0.35 | 0.46 (0.70) |
| 8 | 0.76 | 0.46 (1.04) | 0.39 (1.02) | 0.40 (1.01) | 0.83 | 0.74 (1.09) |
| 16 | 1.60 | 1.24 (1.46) | 0.96 (1.25) | 0.87 (1.18) | 1.91 | 1.16 (1.41) |
| 32 | 3.46 | 2.09 (2.42) | 1.65 (2.00) | 1.76 (2.18) | 3.62 | 1.79 (2.25) |
| 64 | 8.70 | 5.72 (6.28) | 4.48 (5.37) | 4.44 (5.07) | 7.61 | 4.34 (4.20) |

Group peak RSS for 64 ko128 matches: 552 MiB sequential, 872 MiB with 3 workers.
A single spawn worker is about 37 MiB after start and about 50 MiB after
matches. This upper bound is Lab/isolated only.

## Equality and isolation evidence

- Every A/B sample of a case produced the same execute results, played matches,
  checkpoint fingerprint and saved/restarted inspections (`equal_outputs: true`
  in all five A/B cases, 36 samples).
- `tests/domain/test_slot_match_batch.py` (component): random completion order,
  the abnormal corpus, missing/duplicate/foreign/swapped/tampered results, a
  wrong anchor, executor exceptions, a real spawn pool whose workers use another
  `PYTHONHASHSEED`, a worker killed by `os._exit` (pool discarded, sequential
  recomputation, a fresh pool next time), closed-pool rejection and the bounded
  process-wide installation.
- `tests/domain/test_calendar_match_state_hash_once.py`: effects equal the
  previous per-effect hashing byte for byte.
- `tests/api/test_slot_match_workers.py` (production HTTP/SQLite): sequential
  `next-match`, Save, a cold restart of the partially played slot, the
  remaining batch and finals with workers, Save and restart equal the sequential
  Run (random Saved ids normalized); two different Runs execute concurrently on
  one shared two-worker pool and equal their sequential results.
- Existing global-slot, group, walkover and appended-slot verification HTTP
  suites were also run with `BETA_ENGINE_MATCH_WORKERS=2` (see the PR).

## Limitations

- Windows was not run. The reference PC (4 cores, 8 GB) should repeat the
  `ab` command with `--b-workers 3`; the extra 170–300 MiB were measured on Linux.
- One round per variant; A/B noise is about ±3 % on this host.
- Saved v1 only. No long-history snapshot with large slots was available, so
  there is no early/late history comparison; within e8x8 the history grows
  over three slots.
- In worker mode a test that patches `MatchEngine` in the parent cannot see
  worker calculations; the sequential runs remain the authority for such guards.
- Task Center full simulation uses the same service path but was not measured
  with workers.
