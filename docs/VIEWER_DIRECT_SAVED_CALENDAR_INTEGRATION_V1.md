# Viewer Direct Saved Calendar Integration v1

## Purpose

Season Calendar, Planned Event and Week Detail now consume the canonical `viewer_run_calendar.v1` projection captured by the selected Viewer Branch Saved Revision.

These routes no longer reconstruct schedule truth from legacy SimulationRun `getRun` or `listEvents` readers.

## Sources

The routes combine:

- `viewer_run_calendar.v1` for saved schedule/event geometry;
- `viewer_tournament_history.v1` for published Tournament Result status and champion/finalist joins by stable event ID;
- `viewer_official_ranking_history.v1` for canonical ranking publications linked by `week_ordinal`;
- legacy Race snapshots only for the remaining explicit `snapshotSequence` compatibility surface.

## Saved-Revision boundary

Working Draft Calendar edits are invisible until Save publishes a new Viewer Branch Saved Revision.

The Viewer does not reload source Calendar packages or infer schedule state from mutable Admin runtime state.

## Identity rules

- Calendar events use stable `event_id`.
- Official Ranking publications use `week_ordinal`.
- Legacy Race publications retain `snapshotSequence`.
- No implicit mapping is made between Ranking, Race and Finals Race identities.

## Non-goals

This slice does not change sporting rules, tournament simulation, ranking calculations, Finals qualification, Race calculation or Admin authoring behavior.
