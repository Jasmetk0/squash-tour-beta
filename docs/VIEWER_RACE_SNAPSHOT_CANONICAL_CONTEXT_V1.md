# Viewer Race Snapshot Canonical Source Context v1

## Purpose

The routed legacy Race snapshot detail remains compatibility-only because its `snapshot_sequence` identity is distinct from canonical seasonal Finals Race identity.

This slice removes legacy SimulationRun event/run context from that detail page without reinterpreting the snapshot itself.

## Legacy compatibility retained

The page still reads:

- `getRaceSnapshot(legacySimulationRunId, snapshotSequence)`;
- `listRaceSnapshots(legacySimulationRunId)` for previous/next snapshot navigation.

The legacy SimulationRun ID is therefore retained only for snapshot lookup/navigation.

## Canonical source context

Source-event context now comes from Product Run-scoped Saved-Revision authorities:

- `viewer_run_calendar.v1` for source event week/category/tour/template/season;
- `viewer_tournament_history.v1` for canonical tournament-history presence and published-result availability.

Legacy `getRun` and `listEvents` are not used.

## Boundary

`snapshot_sequence` must not be mapped to Finals Race `target_season_index`.

The legacy snapshot payload remains conservative audit/debug compatibility data. Canonical source context does not make the snapshot itself a canonical Finals Race publication.
