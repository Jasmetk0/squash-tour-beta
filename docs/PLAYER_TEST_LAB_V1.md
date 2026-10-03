# Global Player Test Lab V1 — shared development foundation

## Scope

Player Lab V1 adds the third global Test Lab module required by Master v72 without
creating a second player-development engine.

The Lab is available without an active Product Run and executes portable player
scenarios against the same pure weekly sporting kernels used by authoritative Run
transitions:

- `weekly_player_development_update`;
- `between_week_state_update`.

V1 deliberately varies only explicit completed competitive-match counts because that
is already a real input of the canonical sporting kernel. It does not invent a Lab-only
Training Load, health model, Experience, Match Preparation, Financial Level or career
AI contract.

## Isolation and determinism

A `player_test_lab_scenario.v1` contains:

- one canonical `PlayerSportingRecord`;
- birth year/week and a starting `RankingWeek`;
- one historically explicit `PlayerDevelopmentPolicy`;
- one or more named variants;
- an explicit weekly competitive-match-count sequence per variant;
- portable provenance.

Execution creates only in-memory `PlayerSportingWeekState` and
`CompletedWeekSportingContext` values under the isolated Lab scope
`player-test-lab / isolated`. No Product Run, Branch, Saved Revision, Calendar,
Ranking or tournament authority is created or mutated.

Scenario, request and every resulting sporting state are fingerprinted. Identical
factual inputs replay identically. Variant labels are diagnostic metadata and do not
enter the sporting RNG inputs.

## Diagnostics

Each variant returns the weekly:

- effective week and player age;
- completed competitive-match count;
- OVR and Potential OVR;
- Form, Match Sharpness and long-term fatigue;
- count of attributes changed from the initial state;
- aggregate attribute delta;
- canonical sporting-state fingerprint.

The aggregate report exposes final OVR/Sharpness ranges and the count of distinct final
states.

## API and Admin

- `GET /admin/labs/player/scenarios`
- `POST /admin/labs/player/run`
- Admin page: `/admin/labs/player`

The first built-in scenario compares eight weeks with one competitive match each week
against eight inactive weeks from the same initial state.

## Explicit V1 boundaries

The compatibility response truthfully reports:

- `health_supported=false`;
- `training_load_supported=false`;
- `career_ai_supported=false`.

The current canonical `PlayerSportingRecord.health_state` is still
`unsupported`. V1 therefore does not claim to satisfy Master v72's health/recovery
Player Lab requirements. Persistent Player Lab Test Sessions, Run/Saved Revision
player copy, simulated standalone matches, Health/recovery variants and optional career
AI remain later slices.

## Next

Build canonical Run/Branch-owned Health V1 first, including historically versioned
state and save/restore/fork coverage. Then extend Player Lab over that same health
kernel rather than creating a Lab-only substitute. Persistent Player Lab sessions can
then preserve replayable development/health comparisons safely.
