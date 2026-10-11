# Viewer Finals Race v1

## Purpose

The public Race to Finals surface reads the selected Viewer Branch's immutable Saved
Revision instead of the legacy SimulationRun Race snapshot registry.

The canonical source is the Saved Revision simulation-slot component, which already
captures the season-scoped World Tour Finals Race, participant selection and effective
participant-state lineage.

## Public authority

`viewer_finals_race_history.v1` publishes one immutable Race publication per saved
target season. Each publication exposes:

- target season and frozen cutoff Season Week;
- configured Best-N count;
- ordered Race rank, player ID and Race points;
- number and sporting identity of counted tournament results;
- whether the Finals participant selection has been published;
- when selection exists, the effective current Finals membership, seed and
  direct-entry-vs-Race qualification source.

If an accepted replacement exists, the latest saved effective participant state is used
for public Finals membership. The immutable initial selection remains historical evidence
but is not presented as the current field.

Before participant selection is published, `finals_selected` is null rather than false.
This keeps “selection pending” distinct from “not selected”.

## Saved Revision boundary

Live Admin Race, selection or replacement changes are not public merely because they exist
in the Working Draft. Viewer reads only the saved simulation-slot component of the selected
Viewer Branch. The normal authoritative Simulation Save publishes those changes.

Corrupt scope, duplicate seasonal identity, stale Race/selection/effective-state bindings
or tampered saved fingerprints fail closed.

## Deliberately hidden

The Viewer projection does not expose:

- Race, selection or effective-state fingerprints;
- deterministic tie-break tokens;
- Admin command IDs or predecessor lineage;
- source Point Award fingerprints;
- eligibility/configuration fingerprints or policy internals;
- withdrawal reasons or reserve decision audit.

## Compatibility boundary

The top-level `/viewer/rankings/race` and run-scoped
`/viewer/runs/:runId/race` routes use this canonical authority.

Legacy snapshot-sequence detail routes (`race/:snapshotSequence`) and other older Viewer
home/history/deferred consumers may still read the legacy Race snapshot registry until their
separate compatibility migration. Those reads are not canonical Race authority.
