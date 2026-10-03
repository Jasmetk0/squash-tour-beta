# Canonical Player Health V1 authority

Status: first authoritative Master v72 Health substrate for pre-alpha.

## Scope

Health V1 is a separate Run/Branch/week authority. It is deliberately not folded
into the canonical 57 sporting attributes and it does not change fixed innate
Potential.

The authority supports:

- independent `Injury` and `Illness` records;
- Severity on the Master 0–100 scale;
- `At Risk → Active → Recovering → Recovered` lifecycle state;
- multiple simultaneous independent records;
- recurrence links to earlier same-kind records;
- uncertain recovery windows as historical inputs;
- explicitly labelled pre-start health history without fabricating matches or a
  simulated pre-Week-1 timeline;
- persistent post-recovery consequences stored separately from the recovered acute
  record.

A permanent consequence therefore never rewrites or hides the original recovered
record. The two pieces of truth remain independently auditable.

## Historical state

`player_health_week_state.v1` owns the complete health profile for every lifecycle
identity at one weekly boundary.

Each state binds:

- Run and Branch identity;
- exact `RankingWeek`;
- canonical ordered player profiles;
- InitialWorld provenance;
- predecessor Health fingerprint;
- stage provenance;
- deterministic state fingerprint.

Week Transition currently performs an explicit deterministic carry-forward only.
Existing records and permanent consequences survive unchanged; newly materialized
lifecycle identities receive an empty health profile.

This is intentional. PAQ-155 still leaves stochastic Health Check probabilities,
activation/detection curves, recovery mathematics, stacking strength and related
numeric calibration open. V1 must not fabricate those rules.

## Run ownership and recovery

Health V1 is captured as Saved Revision component `player_health_state`.

It participates in:

- InitialWorld bootstrap;
- normal Working Draft Save;
- restore coverage and fail-closed live-vs-saved-head validation;
- materialized Branch fork remapping with rebuilt Branch/predecessor fingerprints;
- ordinary Week Transition;
- ordinary Season Transition;
- final Run closure.

A legacy missing Health authority may be reconstructed automatically only at the
opening Week-1 boundary where no health history could have been simulated yet.
Missing Health at an advanced historical boundary fails closed.

## Reviewed transition boundary

Week Transition preview/confirm now freezes a fourth sporting-state fingerprint:

`X-Week-Transition-Health-Fingerprint`

The committed Week Transition receipt and World Event bind the resulting Health
fingerprint alongside Official Ranking, lifecycle and sporting state. A change to
Health after preview therefore invalidates confirmation rather than silently
changing the result.

Ordinary Season Transition likewise carries Health into next-season Week 1 and
includes its fingerprint in the Season Transition result, World Event, change
summary and Saved Revision.

## Reviewed Admin editing

The reviewed Admin mutation boundary operates only on the exact current Health head.

- `pre_start_input` is permitted only at opening Week 1 and every supplied record must
  explicitly declare `started_before_run=true`; the engine does not invent a pre-Run week.
- Later `current_state_correction` edits may replace the selected player's complete current
  Health profile but cannot rewrite predecessor Health history or InitialWorld provenance.
- Onset/recovery facts cannot point into the future relative to the current authoritative Week.
- Preview is read-only. Commit requires the exact
  `X-Player-Health-Preview-Fingerprint`, revalidates Working Draft/version/current Week under
  one write transaction and records operator/reason plus before/after fingerprints.
- Exact retries are idempotent only while that committed Health result remains current. A
  receipt made historical by a later correction or restore cannot silently re-apply itself.
- The committed edit is staged as ordinary `player_health_state` Working Draft component
  evidence and can be Saved as a recoverable Saved Revision through the normal Run boundary.

The Run Players Admin UI now consumes this exact backend workflow on the Active Admin Branch.
It exposes current Health inspection, complete-profile editing, reviewed server preview, exact
commit retry semantics and explicit Health Saved Revision creation. Historical checkpoint mode
continues to use the shared present-only boundary; no alternate UI-owned Health authority exists.

## Explicit non-goals of this slice

Health V1 does not yet implement:

- stochastic contextual Health Checks;
- exact Injury/Illness susceptibility rates;
- At Risk activation/detection probabilities;
- diminishing-impact stacking mathematics;
- healing/recovery progress curves;
- treatment or surgery detail;
- health-driven W/O / medical timeout / retirement decisions;
- return-risk career AI;
- health-to-Match-Engine limitation projection;
- Player Lab health/recovery scenarios.

Those must build on this same authority rather than introduce parallel state.

## Next

The next useful vertical slice is a shared Health limitation projection into Match Engine and
Player Lab, followed by Health/recovery Lab scenarios. Calibrated stochastic Health Check/recovery
mechanics remain later work.
