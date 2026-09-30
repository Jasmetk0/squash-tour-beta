# Viewer World Tour Finals Participants v1

## Purpose

Viewer World Tour Finals summary and qualification pages publish the confirmed Finals
participant field from the selected Viewer Branch's immutable Saved Revision.

They do not read the legacy SimulationRun Finals qualification/summary registry.

## Authority

The public field is derived from the canonical Saved Finals Race publication:

1. the frozen World Tour Finals Race snapshot defines Race rank and Race points;
2. the persisted participant-selection snapshot establishes that selection was published
   and identifies the Finals event;
3. when replacement history exists, the latest valid
   `WorldTourFinalsEffectiveParticipantState` replaces the initial selected field for
   public confirmed participation.

This means a withdrawn selected player disappears from the current public confirmed field
and an accepted frozen-Race replacement appears with their own Race rank, Race points and
new Finals seed. The immutable initial selection is never rewritten.

## Public projection

The Viewer participant table exposes only sporting facts:

- Finals seed;
- player identity;
- frozen Race rank;
- frozen Race points;
- qualification source: direct entry or Race.

The Finals summary also exposes public publication context such as target season index,
Finals event identity, Race cutoff week, Best-N and confirmed participant count.

## Hidden evidence

Viewer does not expose:

- selection/effective-state/Race fingerprints;
- predecessor lineage;
- withdrawn-player audit history;
- replacement command IDs;
- decline/accept audit evidence;
- direct-entry source-event internals;
- Admin provenance.

Those remain authoritative Admin/recovery evidence.

## Publication boundary

Live Finals Race, participant selection or replacement state is not public merely because
it exists in working persistence. Viewer reads only the Saved Revision Simulation
component already used by `viewer_finals_race_history.v1`.

## Result boundary

This slice migrates the Finals hub and qualification/participant field only.

The dedicated Finals result subpage remains a separate compatibility surface until it is
bound to canonical Tournament Result history. No result is inferred from qualification,
Race order or legacy summary metadata.
