# MatchEngine performance (15 November 2026)

Branch `claude/matchengine-perf` from `buuk 320e476`. Independent of Draft #1803 (no
shared files). No sporting rule, probability, RNG draw, seed, schema, hash
definition or result changes.

## Benchmark

`scripts/benchmark_match_engine.py` runs each scenario in a fresh process and prints
wall/CPU seconds, peak RSS, engine-only seconds (time inside `MatchEngine.simulate`)
and a SHA-256 over every complete `MatchResult` dump:

| Scenario | What runs |
| --- | --- |
| `single` | one real match through the production input path (`MatchInputSnapshot` + every effective snapshot, as Run/slot services call it) |
| `set` | 24 matches: strength gaps 0–22, five styles, five archetypes, BO5 and BO3, distinct seeds; production path |
| `lab` | the same 24 through plain `MatchEngine.simulate(context)` (Tournament Lab path) |
| `ko128` | a complete 128-player Tournament Lab knockout, 127 real matches; engine time vs tournament infrastructure separately |

```bash
python scripts/benchmark_match_engine.py all --repeats 3
```

## Where the time went (sampling profile, `buuk`)

JSON encoding for event content hashes ~23 %, `model_dump` ~10 %, `random.Random`
seeding ~10 %, the recursive `_json_value` copy ~5 %, pydantic construction ~5 %.
Every rally, stamina-transition and timeline event was hashed twice on creation:
once from an unvalidated `model_construct` draft in `create`, once from the
validated model in its validator.

## Changes

1. **One hash per created event** (`domain/matches/content_hash.py`, `rallies.py`,
   `stamina.py`, `timeline.py`). `create` validates once; every validator check runs
   except the final hash comparison, which is deferred for exactly that instance
   (consumed once, exact type only). The hash is then computed from the VALIDATED
   model and stored with `model_copy`. Whenever the original sequence succeeded both
   hashes were equal, so the event is byte-identical. Loading stored events,
   `model_validate` and direct construction keep the complete validator.
2. **Lazy `random.Random`** in `DeterministicRng` (`core/rng.py`): created on first
   draw from the same seed, so identical state and sequence; ~21 % of child RNGs only
   derive further seeds and never draw.
3. **JSON fast paths**: `_json_value` handles exact JSON-native types first (same
   output, fresh containers); the rally hash payload of a fresh `mode="json"` dump is
   not deep-copied a second time.

Rejected after measurement: further stamina micro-optimizations (1–3 %, touch numeric
code); skipping pydantic's re-run of `after` validators when events are placed into
logs (the models are not frozen, so that second check is the only guard against a
later mutation); RNG seeding itself (inherent to the seed hierarchy).

## Results

Equality: every scenario's result fingerprint is byte-identical to `buuk`
(`single 7ef71261…`, `set 2cad1b21…`, `lab 7a84fa14…`, `ko128 795da202…`).

Balanced A B B A, 3 repeats each, same host (noisy 4-vCPU; medians of 6 samples):

| Scenario | `buuk` | candidate | change |
| --- | ---: | ---: | ---: |
| 128-player knockout, total | 34.7 s | 26.5 s | −24 % |
| 128-player knockout, engine only | 28.7–33.5 s | 21.3–22.9 s | −25…−30 % |
| 128-player knockout, infrastructure | 3.3–4.5 s | 3.3–3.7 s | ≈ |
| 24 matches, production path | 5.65 s | 4.91 s | −13 % |
| 24 matches, Lab path | 5.7 s | 4.6 s | −19 % |
| one match | 0.22 s | 0.18 s | ≈ −18 % |

Peak RSS of the benchmark processes unchanged (≈ 50 MB single, ≈ 127 MB others).
The final commit (fresh-dump payload) measured a further few percent (set 4.1–4.5 s,
knockout 24.2–27.3 s) in a non-interleaved run.

Whole W6 native Run, two seasons through real HTTP/SQLite (the #1803 season driver,
used as a temporary uncommitted copy), A B B A:

| | runs | mean |
| --- | --- | ---: |
| `buuk` | 693.4, 655.5, 661.3, 662.2 s | 668 s |
| candidate | 677.2, 662.1, 665.5 s | 668 s |

At season level there is no measurable difference: a W6 season spends most of its
time in Saved-revision validation and persistence (the subject of #1803), and plays
only 12 matches. Peak RSS: `buuk` 1,074 / 1,095 / 1,121 / 1,093 MB, candidate 1,109 /
1,113 / 1,098 MB (no consistent difference).

**Cross-read on real season data.** A cold read replays every stored match with the
MatchEngine and compares the stored bytes. The final DB built by `buuk` (A3) read
cold by the candidate, and the DB built by the candidate (B3) read cold by `buuk`,
both pass; each DB gives identical `inspect`, archive and both season-summary
responses from either reader (cold read ≈ 38 s for both readers).

**Sporting results.** All 12 matches of the candidate season B3 are identical to the
`buuk` season A4 (seeds, pre-match player attributes, winners, rally counts, rally
time). Separate observation, pre-existing and unrelated to this change: two seasons
on the SAME `buuk` code (A3, A4) differ in 3 of 12 matches by ±1 in one player's
pre-match attribute. The server generates random Saved revision IDs and the stored
components reference them, so this scenario is not run-to-run repeatable on `buuk`
itself; a reproducible season benchmark therefore compares sporting tuples per
build pair and relies on the cross-read for exact equality. This is reported for a
separate decision, not changed here.

## Tests

- `tests/domain/test_match_engine_performance_equivalence.py`: golden fingerprints
  computed on `buuk` (one production-path match; six varied matches on both paths);
  every created event's hash equals the original full algorithm; stored events,
  transitions and timeline events reload through the complete validator; tampered
  stored values (a hash-only field, the hash itself, an elapsed time) are rejected;
  the deferred check is consumed once and only for the created type; the lazy
  generator draws the identical sequence.
- Domain + application suites (2,090 tests) and API + infrastructure match /
  knockout / tournament / slot / season suites (417 tests): 2,488 passed; the same 19
  tests fail identically on clean `buuk` (pre-existing: e.g. a `match_input_snapshot`
  v10/v11 expectation, season match service, rally rules configuration).

## Limits and risks

- The removed draft-vs-validated hash comparison in `create` could only fire if the
  engine passed values that validation coerces into a different JSON encoding (an
  engine bug). With the change such an event would be stored with the hash of its
  validated value instead of failing. Every load path still validates fully.
- Measurements are from one noisy shared host; hosted runners may differ.
- No production season-level speedup is claimed; the gain is in matches and
  tournaments. Larger gains need structural changes (cheaper event hashing formats,
  not materializing full rally/timeline/stamina logs), which change persisted formats
  and are out of scope here.
