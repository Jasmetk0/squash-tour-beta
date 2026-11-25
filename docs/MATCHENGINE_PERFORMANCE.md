# MatchEngine performance (25 November 2026)

Branch `claude/awesome-maxwell-m305sa` from `buuk 8af660d`. Scope:
`domain/matches`, the directly used `core/rng.py`, focused tests and benchmark
tools. No sporting rule, probability, RNG draw order, seed, schema, hash
definition, result, score, time or log changes. Saved v1/v2, SQLite, stored-history
replay, Task Center, Full Simulation, ATP, frontend and CI are untouched.

Draft #1804 (15 November, `claude/matchengine-perf`, never reviewed or merged)
is the starting evidence. Its three changes are carried here unchanged and
re-verified on current `buuk` (the match domain did not change since its base):
if this PR is accepted, #1804 is superseded and can be closed by the owner.

## Tools

| Tool | What it measures |
| --- | --- |
| `scripts/benchmark_match_engine.py` | wall/CPU, engine-only time (inside `MatchEngine.simulate`), peak RSS and a SHA-256 over complete serialized outputs, per scenario |
| `scripts/profile_match_engine_phases.py` | exclusive CPU per phase (CPU-time sampling, `ITIMER_PROF`, each sample charged to the innermost engine frame), gross allocation volume per phase (second identical pass under `tracemalloc`) and GC runs |
| `scripts/ab_match_engine.py` | interleaved A B B A rounds of two source trees, a fresh `PYTHONHASHSEED=0` process per sample, medians, aborts on any fingerprint difference |

Scenarios: `single` (one real match through the production input path), `set`
(24 varied matches, production path), `lab` (same 24, Tournament Lab path),
`cases` (edge corpus below), `ko128` (complete 128-player Tournament Lab knockout,
127 real matches) and `http16` (a short real pass: real uvicorn HTTP server and a
disposable SQLite database, `POST /admin/labs/tournament/run`, 16-player knockout,
15 real matches; fingerprint = complete HTTP response).

The `cases` corpus: forced deuce in BO5 (12–10 set), PAR-15 BO3, BO1, explicit
retirement at set 1 (no rally) and set 3, probabilistic retirement, an injured/ill
participant (active Injury record, permanent consequence, negative health/fatigue/
form modifiers through the effective Health snapshot), a Lab-path retirement, and
two step-wise `Simulate Next Rally` matches (7 deuce rallies; probabilistic
retirement) whose every persisted working state and step outcome is hashed and
whose final result must equal the full simulation. The corpus contains all four
timeline event kinds, including an objective delay.

## Where the time went (`buuk`, 24 matches, 4.48 s CPU)

| Phase (exclusive CPU) | share | per item on `buuk` |
| --- | ---: | --- |
| rally event content hash | 27.7 % | 3 hashes per event: draft in `create`, validator, again when the log validates its events |
| RNG seed derivation + `random.Random` seeding | 20.9 % | 89,616 generators seeded, ~21 % never draw |
| stamina transition hash | 8.4 % | 3 per transition |
| stamina state math | 6.9 % | `advance_states` twice per transition (live loop + timeline rebuild) |
| rally loop + control | 6.6 % | |
| timeline event hash | 3.7 % | 4 per between-rally interval: the live loop built a complete hashed event only for its elapsed time, the timeline built it again |
| benchmark harness | 10 % | result dump for the fingerprint, not engine |

A hash itself is ~150 µs for an 11 KB rally event (dump 43, `json.dumps` with
sorted keys 94, SHA-256 10) plus 100 µs of the defensive `_json_value` copy; the
byte format is fixed, so the levers are how often things are computed.

## Changes

1. **Restart sampled once** (`match_engine.py`). `_sample_between_rally_interval`
   performs exactly the former RNG draws and arithmetic without creating an event.
   The live loop (full and step-wise) keeps only elapsed time and kind for stamina;
   `_build_timeline` reuses the live sample only when the previous rally's hash and
   the freshly derived interval seed are equal, otherwise it recomputes. Saves 7
   seed derivations, 6 generator seedings, one event validation and two hashes per
   interval.
2. **Exact-input stamina memo** (`stamina.py`, `StaminaAdvanceMemo`). The timeline
   rebuild takes the live `advance_states` result only for the very same state
   objects, the same snapshot object and type-exact scalars (`float.hex`, so
   `0.0`/`-0.0` and `1`/`1.0` never merge). Any difference misses and is recomputed,
   so `live stamina state diverged` still detects a disagreement between timeline
   and live loop. Halves `advance_states` calls (all rebuild steps hit).
3. From #1804: **one hash per created event** (`content_hash.py`); **lazy
   `random.Random`**; **JSON fast paths** (`_json_value`, fresh-dump payload).
4. **Seed text cached** in `DeterministicRng.derive` (same material
   `v1|scope|parent|parts` and BLAKE2b digest as the reference
   `derive_child_seed`): 2.7 → 1.7 µs per derivation.

Rejected or not applied:

- Skipping the hash re-check when events enter `MatchRallyLog`/`MatchTimelineLog`/
  `MatchStaminaLog`: measured **a further ~9 % CPU** (24 matches 2.97 → 2.71 s,
  identical fingerprint), but it is the only guard against mutating a created
  event before it is logged (models are not frozen). Needs Work's/owner's decision.
- Avoiding pydantic's re-run of nested `after` validators, faster MT seeding,
  merged RNG branches and numeric stamina rewrites: change validation semantics or
  the draw sequence, or touch calibrated arithmetic.

## Equality evidence

Fingerprints identical between `buuk 8af660d` and the candidate in every A/B
sample: `single 7ef71261…`, `set 2cad1b21…`, `lab 7a84fa14…`, `cases 70b082cb…`,
`http16 7b62db7b…`, `ko128 795da202…` (`single`, `set`, `lab`, `ko128` also equal
#1804's `buuk 320e476` values). `tests/domain/test_match_engine_performance_equivalence.py`
pins the golden values and additionally checks: every event hash equals the
original full algorithm; stored events reload through the complete validator;
tampered stored values are rejected; the edge corpus really contains deuce, every
retirement kind, the step path and all timeline kinds; each restart is sampled once;
stale samples (wrong rally hash or seed) are recomputed identically; the memo
build equals the plain build, foreign snapshots/equal-valued copies/perturbed
inputs miss; cached derivation equals `derive_child_seed` for 1,200 random inputs;
lazy generators draw identical sequences.

## Results (same host, interleaved A B B A, 3 rounds, 6 samples per side, medians)

| Scenario | `buuk` | candidate | change |
| --- | ---: | ---: | ---: |
| one match, wall | 0.189 s | 0.131 s | −31 % |
| 24 matches production path, engine | 4.05 s | 2.64 s | **−35 %** |
| 24 matches Lab path, engine | 4.09 s | 2.63 s | −36 % |
| edge corpus, engine | 1.21 s | 0.78 s | −35 % |
| 128-player knockout, total | 25.7 s | 18.2 s | **−29 %** |
| 128-player knockout, engine | 22.6 s | 15.0 s | −34 % |
| 128-player knockout, tournament infrastructure | 3.10 s | 3.22 s | ≈ (not changed) |
| real HTTP/SQLite 16-player pass, total | 8.38 s | 7.48 s | **−11 %** |
| same, engine | 3.46 s | 2.38 s | −31 % |
| same, app start + HTTP + SQLite + Lab service | 4.90 s | 4.98 s | ≈ (not changed) |

Sample ranges do not overlap in any engine row (e.g. ko128 engine A 22.1–24.0 s,
B 14.4–16.6 s). Peak RSS unchanged (50.6 / 89.7 / 135 / 239 MB). Gross allocation
volume of the 24 matches without the fingerprint dump: 144 → 104 MB (−28 %);
rally-hash allocations 58 → 25 MB.

Increment over #1804 alone (A = #1804 tree, B = candidate, 2 rounds): 24 matches
engine −8 %, ko128 engine −10 %.

Phase shares after the change (24 matches, 3.07 s CPU): RNG derive+seed 21 % (now
almost entirely the inherent MT19937 seeding of 62,788 generators that do draw,
~6.3 µs each in C), rally hash 13 % (2 per event: create + log entry), stamina math
10 %, rally loop 9 %, nested-model validation 8 %, stamina hash 6 %.

## Where the benefit does not show

- Tournament/Lab infrastructure around the matches (ko128 ~3.2 s, app start/HTTP/
  SQLite in `http16` ~5 s) is unchanged; the short real pass therefore gains only
  11 % in total although its engine part gains 31 %.
- Season-level runs: #1804 measured a W6 native two-season run (668 s both sides);
  it plays 12 matches and is dominated by Saved validation and persistence. Not
  re-run here (owner asked for no further giant run); no season speedup is claimed.
- Stored-history replay re-validates persisted results through the application
  layer; its share outside `MatchEngine` was not measured or changed.
- Only one noisy shared 4-vCPU host; hosted runners may differ.

## Tests (actual runs)

- Focused match suites (33 files: engine, logs, rules, gameplans, Health input,
  Match/Tournament Lab service+API, live match state, reconstruction, slot matches,
  knockout, standalone/calendar match flows, season match service): candidate 386
  passed, 14 failed; clean `buuk` 373 passed, the **same 14** failed (pre-existing:
  `match_input_snapshot` v10/v11 and Health tuple expectations, rally rules config
  hash, authoritative slot matches requiring Health authority, season match service).
- The complete domain+application suites were started on both trees in parallel and
  were killed by the container memory limit at 62–64 %; they are not claimed.
- No browser test; no full CI run claimed.
