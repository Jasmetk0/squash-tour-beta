# Rally Rules Resolver V1

## Implemented scope

This pre-alpha slice implements Master Vision v61 sections 16.4 and 17.8.3:
ground-truth terminal facts, a deterministic rules resolver, ordered score
mutations, and neutral replay. It does not implement a complete referee.

The historical ruleset is `world_squash_singles_2025_v1_2_2`, with resolver
`pre_alpha_rules_v1`. Reference: [World Squash Officiating, Rules of Squash](https://worldsquashofficiating.com/rules-of-squash/),
2025 singles rules, particularly sections 5, 8, 9 and the external-interruption
rules. Store future rule changes as a new version; never reinterpret old facts
using a newer resolver.

## Sporting contract

| Final call | Score | Next serve |
| --- | --- | --- |
| `POINT_AWARDED` | One point for the ordinary return/serve result | Point winner |
| `NO_LET` | One point for the opponent of the requesting striker | Point winner |
| `YES_LET` | No winner and no score mutation | Same server, same box |
| `STROKE` | One point for the player selected by the relevant rule | Point winner |

Stroke is not unconditionally awarded to the striker: a turning player who
hits the opponent with an otherwise good outbound ball loses the point, unless
the opponent deliberately intercepted it. Direct/via-other-wall returns and
first/further attempts are resolved separately. Incoming-ball situations use
the receiving player as striker.

Interference facts distinguish view, access, reasonable swing, front-wall
freedom, good/winning return, clearing and striker effort, self-created path,
wrong-footed recovery, minimal interference, played-through interference,
excessive swing, turning and further attempts. The resolver applies the general
eligibility checks and the supported specific rule branches. Stored contradictory
facts and verdicts fail validation, even if an enclosing event is rehashed.

Every situation has one primary terminal trigger. Analytical attribution stays
separate: ordinary winners/errors, official awards, or neutral replay. The
ordered `score_mutations` container is retained for later conduct additions;
this slice emits exactly one mutation for a point and none for a let. It does
not yet emit additional conduct strokes after a rally.

## Situation generation and provisional calibration

The existing opening/control/terminal trace generates physical duration, shot
estimates and workload. At its abstract terminal boundary, a separate seeded
`rule-situation-v1` stream may generate an interference, ball-hit or external
incident instead of an ordinary finish. Facts are generated before adjudication;
no RNG is called by the resolver, and initial/final calls are identical.

This is deliberately not collision geometry. Estimated shots are not a precise
list of racket contacts, and a stopped terminal attempt does not imply that a
real shot was struck. Detailed actor trajectories, incident-dependent terminal
duration calibration and official discussion time remain follow-ups.

`EffectiveRallyRulesSnapshot` freezes the replaceable generation profile:

- base interference probability `0.04`, adjusted by control pressure and the
  movement proxy;
- ball-hit probability `0.004`;
- external-interruption probability `0.001`;
- a generation guard after eight consecutive lets.

These are **provisional starting coefficients, not measured professional
incident rates**. Rule-fact sampling coefficients also belong to the named
`pre_alpha_rule_situations_v1` generation. Serve faults and the currently
modelled serve/first-return opening terminals retain ordinary resolution;
incident generation in those short openings is not implemented yet.

The guard suppresses incident generation for the next abstract finish. It
never changes a verdict for an already-created situation and is not a squash
rule limiting the number of lets.

## Time, physical work and tactical evidence

A let does not refund physical work. Every played rally consumes its logged
individual workload, whether it scores or is replayed. Both players recover
through exactly the same subsequent authoritative elapsed interval.

An external incident stores a reason and duration and produces an
`OBJECTIVE_DELAY` timeline event. It replaces the ordinary between-rally event;
elapsed time is the maximum of the interruption duration and ordinary restart
readiness, not their sum. Stamina uses `OBJECTIVE_DELAY_RECOVERY` once. The
provisional generator samples short delays of 30–90 seconds. There is no new
hard suspension threshold: `Suspended`, rescheduling and long-delay workflow
remain open/unimplemented.

Gameplan reassessment counts a let as an observed neutral rally, not a win or
loss. The logged point differential and neutral count are validated against
the prior authoritative rallies. Both players still make decisions from the
same pre-rally state and their existing imperfect perceptions.

## Historical schemas and replay

| Component | New generation |
| --- | --- |
| Match engine | `match_engine_v9` |
| Match input | `match_input_snapshot.v9`, with protected `effective_rally_rules` |
| Rally event/log | `rally_event.v6` / `match_rally_log.v6` |
| Match timeline | `match_timeline_log.v2` |
| Rules and objective delay | `effective_rally_rules.v1` / `objective_delay_event.v1` |

`winner_player_id` is nullable only for current neutral replay events. Each v6
event stores current and next service box, rule facts, initial/final calls and
decision code. The log reports both `scoring_rallies` and `replay_rallies`.
Readers must not equate total rally count with total points.

Old input versions v1–v8, rally events v1–v5 and timeline v1 remain readable.
New fields are excluded from legacy hash payloads, and unprotected non-default
rules data cannot be smuggled into older schemas. No historical row is migrated
or regenerated. The checked-in `tests/fixtures/matches/legacy_engine_v8.json`
was generated by unmodified commit `41151cfe80d2465961f8337158f9a88d06134526`
using a one-point test format; tests load its original hashes without rehashing
or running the current engine.

Stored replay remains read-only and does not rerun RNG. New simulations may
produce different outcomes from v8; this does not change existing history.
General rollback/rerun UI and a dedicated rules editor are not added here.

## Verification and follow-ups

Tests cover the supported rules table, turning and further attempts, fact
contradictions, deterministic simulation, score/server/box continuity, workload
on lets, non-duplicated interruption recovery, historical hashes and rehashed
tampering. The season service persists the new snapshot and returns the same
stored truth on replay. TypeScript API definitions expose the new contract;
this PR adds no new viewer screen.

Still unimplemented: referee errors/review, fuller conduct escalation, health
stops, procedural stops, long suspension/rescheduling, exact shot geometry,
and empirical calibration of incident rates and durations. The Master file is
intentionally unchanged.
