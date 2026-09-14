# Authoritative Player Sporting Week State V1

This is an implemented technical contract, not a decision of the still-open
development calibration. It extends the single authoritative Week Transition
transaction owner; it does not create a second simulation or transaction path.

## Product-canonical boundary

`attribute_catalog.py` is the one catalogue for the pre-alpha's six groups and
57 independently stored attributes. A `PlayerSportingRecord` accepts all and
only those names, with integer values `0..200`. Its calculated current OVR is a
separate view over the attributes. `potential_ovr` is one immutable hidden
soft-potential value: development never clamps current attributes or OVR to it.
The only absolute clamp is the decided attribute space `0..200`.

`player_sporting_week_state.v1` is an immutable Run/Branch/week snapshot. It
contains canonical sporting records, fixed development timing (`Early Bloomer`,
`Standard`, `Late Bloomer`), current Form and its individual long-term norm,
Match Sharpness `0..100`, long-term Fatigue `0..100`, the effective historical
development policy, completed-context fingerprint, predecessor fingerprint,
owned InitialWorld fingerprint, stage provenance and stable snapshot
fingerprint. Identity, birth, Tour entry and retirement remain exclusively in
`PlayerLifecycleWeekState`. Health is explicitly `unsupported`; this slice does
not invent an injury or healing model.

## Explicit legacy compatibility adapter

The production InitialWorld still owns a legacy seven-value `1..99` player
source. `legacy-7x99-to-canonical-57x200.v1` is an explicit provisional bootstrap
policy, not the new player canon. It deterministically projects the owned source
groups to `0..200`, adds small player/attribute-scoped deterministic jitter from
the already-owned source-generation fingerprint, maps legacy growth-curve labels
to fixed development timing, and records the complete policy and potential
provenance. It reads no ranking, country allocation, target-week content, or live
global file. Changing policy identity or parameters changes state fingerprints.

## Provisional weekly policy

`weekly-player-development.provisional.v1` stores every numeric value used by
the first kernel: timing shifts `-3/0/+3`, growth/physical/other decline ages,
weekly change and Form influence basis points, Form regression divisor,
inactive Sharpness decay, and Fatigue recovery. These are implementation and
calibration values only. They are embedded in each historical snapshot, so a
later tuning version cannot reinterpret old history.

The pure development kernel canonicalizes player order and scopes its hash-based
random stream by Run, Branch, predecessor fingerprint, completed week, effective
policy, completed-context fingerprint, player, and attribute. It receives no
target-week event/config payload. It may grow, hold, or decline attributes;
physical/movement decline can begin earlier, while other groups can hold longer.
Development timing shifts age, never potential. Potential is unchanged.

The following separate between-week kernel then regresses Form gradually toward
the player's norm, decays Sharpness only when the owned completed-week context
reports no competitive match, and recovers rather than resets Fatigue. Match
gain is deliberately not fabricated. Development therefore observes the final
pre-regression Form of the completed week, while the target snapshot stores the
post-between-week values.

## Persistence, transition, and recovery

`player_sporting_week_states` owns append-only week snapshots independently of
lifecycle, ranking, and InitialWorld. The sole `BEGIN IMMEDIATE` Week Transition
path now stages sporting development, stages between-week state, advances
lifecycle, stages/publishes ranking, advances world state, writes its World Event
and receipt, validates, and commits once. Preview calls that exact writer and
rolls back. Result, receipt, and World Event carry the sporting fingerprint;
exact retry validates and returns the stored target rather than developing twice.
The unresolved RunProspect guard remains unchanged.

Saved Revisions use a separate `player_sporting_state` component containing the
validated complete chain. Restore verifies the live saved head before replacing
it atomically with the target history. A component-less legacy Week-1 target may
be reconstructed only from its restored owned InitialWorld; the newly created
restore revision captures the reconstructed component and the legacy revision is
not rewritten. A later target with an advanced world clock cannot be reconstructed
unambiguously and fails before mutation.

## Explicitly still open/out of scope

The projection and development numbers, final OVR weights, Form-from-match,
Sharpness gains, detailed training, medical simulation, 57-attribute Match
Engine consumption, prospect/Tour-entry bridge, player AI, Season Transition,
and final development probability architecture remain unimplemented or open.
