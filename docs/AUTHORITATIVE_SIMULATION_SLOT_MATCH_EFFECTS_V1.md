# Authoritative Simulation Slot Match Effects V1

This is the implemented technical contract for the first deliberately narrow four-player tournament slice. It does not complete Entries, general draw ownership, cross-tournament scheduling, AI, health, or Gate 3.

## Ownership, frozen time, and atomicity

`simulation_slots` and `simulation_event_groups` are keyed by Run, Branch, Season Week, global Simulation Slot, and stable group identity. A slot is a world-time unit, never a physical draw position. The minimal scheduler requires the preceding slot to be complete before a dependent slot can be frozen and records explicit dependency identities; it does not claim to schedule every future event type.

Each slot stores one immutable plan, its plan fingerprint, frozen slot-start checkpoint, and terminal checkpoint. Every group always projects from the frozen checkpoint, including retries after another independent group committed. Terminal state is rebuilt in canonical group/player order. Groups attempting to update the same player from the same slot fail closed.

One supported atomic group is one competitive match plus its protected input, rally/timeline/stamina logs, result fingerprint, two player effects, and receipt. Calculation is staged in memory. The group row and terminal checkpoint flush only after all evidence validates. Fault seams exist after result staging, after effect staging, and before commit. Independent committed groups remain valid if another fails.

The command fingerprint covers scope, slot-start state, event/player identity, seed, engine version, projection policy, and effects policy. Exact retry returns stored history without re-simulation or a second effect. Changed input under the same identity conflicts.

## Canonical input and compatibility projection

`AuthoritativeMatchInput` retains both complete ordered canonical 57 attributes, Form, Match Sharpness, long-term Fatigue, source/slot fingerprints, policy identity/fingerprint, seed, format, and existing hash-protected `MatchInputSnapshot` including timing, stamina, gameplan, rally rules and calibration.

`canonical-57-to-legacy-match-engine.provisional.v1` is explicitly a temporary compatibility/calibration adapter. It averages canonical groups, scales `0..200` to seven legacy `1..99` inputs, and separately stores Form, Sharpness and Fatigue values/modifiers. The legacy engine has no native Sharpness channel, so only at this final seam its independent modifier is combined with the engine form channel; Fatigue uses the fatigue channel. Ranking and OVR are never bonuses. Native 57-attribute Rally Setup can later consume retained truth without migrating history.

## Provisional effect calibration

`match-sporting-effects.provisional.v1` contains every numeric calibration: Form response `18.0`, expectation sensitivity `1.0`, minimum evidence weight `0.15`, full evidence at `100` rallies; Sharpness `8.0` per played hour plus individual workload / `30`; Fatigue `5.0` per hour plus workload / `18`; Form clamp `0..200`; Sharpness/Fatigue clamps `0..100`.

Form uses authoritative point/rally performance relative to frozen pre-match expectation and played-data weight, not win/loss. A close underdog loss can improve it and a weak favorite win can reduce it. Sharpness only gains from duration/intensity; overload never subtracts it. Fatigue receives positive load. W/O/pre-start DQ has no effect because calculation requires played rallies. Played RET uses only stored evidence. Suspended/ABN variants fail closed.

## Intra-week history, Replay, Save/Restore, and transition

`PlayerSportingWeekState` stays the immutable opening boundary. `PlayerSportingCheckpoint` chains opening fingerprint, slot start, predecessor, effect fingerprints, and resulting full records; it is not a competing week truth. Replay loads stored input/result logs and never reads current state or reruns RNG.

Saved Revision component `simulation_slot_match_state` hash-protects slot/group history and is restored beside sporting state. Backward restore removes later effects; forward restore reinstalls exact receipts.

`completed_week_sporting_context.v2` binds match counts, result/effect fingerprints and terminal checkpoint. Weekly Development validates and substitutes terminal players, observing post-match Form before between-week regression. Legacy owned tournament sources remain compatibility-only when no authoritative ledger exists; paths are never summed.

## Unsupported boundaries

Stamina logs remain per-match truth. Carried physical bars remain unsupported; only long-term Fatigue bridges matches. Health, match World Events, general tournament award publication, Entries, full draw ownership, Qualification/WC/LL, global multi-event scheduling, AI, training, Season Transition, and Viewer UI remain out of scope.
