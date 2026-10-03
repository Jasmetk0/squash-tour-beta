# Global Player Test Lab V1 — shared development foundation

## Scope

Player Lab V1 adds the third global Test Lab module required by Master v72 without
creating a second player-development engine.

The Lab is available without an active Product Run and executes portable player
scenarios against the same pure weekly sporting kernels used by authoritative Run
transitions:

- `weekly_player_development_update`;
- `between_week_state_update`.

V1 varies explicit completed competitive-match counts through the canonical sporting kernel and may also carry an explicit canonical `PlayerHealthProfile` timeline through the shared Match Health limitation projection. It does not invent a Lab-only Health model, Training Load, Experience, Match Preparation, Financial Level or career AI contract.

## Isolation and determinism

A `player_test_lab_scenario.v1` contains:

- one canonical `PlayerSportingRecord`;
- birth year/week and a starting `RankingWeek`;
- one historically explicit `PlayerDevelopmentPolicy`;
- one or more named variants;
- an explicit weekly competitive-match-count sequence per variant;
- an optional explicit Health timeline containing the start profile plus one profile per simulated week;
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
- canonical Match Health projection, affected domains, highest current Severity and projection fingerprint;
- count of attributes changed from the initial state;
- aggregate attribute delta;
- canonical sporting-state fingerprint.

The aggregate report exposes final OVR/Sharpness ranges and the count of distinct final
states.

## API and Admin

- `GET /admin/labs/player/scenarios`
- `POST /admin/labs/player/run`
- Admin page: `/admin/labs/player`

The first built-in scenario compares eight weeks with one competitive match each week against eight inactive weeks from the same initial state. A second built-in compares an explicit `Active → Recovering → Recovered` ankle-Injury timeline with a healthy control.

## Explicit V1 boundaries

The compatibility response truthfully reports:

- `health_supported=true` for canonical explicit Health timelines and Match limitation projection;
- `training_load_supported=false`;
- `career_ai_supported=false`.

`PlayerSportingRecord.health_state` remains an unrelated legacy placeholder; Player Lab Health comes from canonical `PlayerHealthProfile` timelines. The Lab does **not** generate Health Checks, healing, stacking or numeric Match penalties. Persistent Player Lab Test Sessions, Run/Saved Revision player copy, optional standalone matches and career AI remain later slices.

## Next

Use the shared Health projection to test approved limitation/stacking and recovery calibration before those effects enter Product Runs. Persistent Player Lab sessions can then preserve replayable development/Health comparisons safely.
