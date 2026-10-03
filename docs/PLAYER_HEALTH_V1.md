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
- Admin mutation endpoints for explicit health editing;
- Player Lab health/recovery scenarios.

Those must build on this same authority rather than introduce parallel state.

## Next

The next useful vertical slice is explicit audited Admin Health editing, including
pre-start inputs and current-state corrections. After that, the shared health
projection can feed Match Engine and Player Lab, followed by calibrated stochastic
Health Check/recovery mechanics.
