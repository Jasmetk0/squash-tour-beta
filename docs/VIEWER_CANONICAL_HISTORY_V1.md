# Viewer Canonical History v1

## Purpose

The run-scoped Viewer History page is a public sporting publication timeline. It must not use the legacy SimulationRun activity feed as its authority.

## Canonical sources

The page reads only public Saved-Revision projections for the selected Viewer Branch:

- `viewer_tournament_history.v1` for completed published Tournament Results;
- `viewer_official_ranking_history.v1` for published Official Ranking history;
- `viewer_finals_race_history.v1` for published World Tour Finals Race history.

These sources already enforce the normal Viewer Branch + Saved Revision publication boundary.

## Presentation

History is intentionally shown as separate canonical sporting timelines instead of pretending unrelated publication identities share one universal sequence:

- completed tournaments are filtered to `result_published=true`;
- Official Ranking publications retain their canonical `week_ordinal`;
- Finals Race publications retain their canonical `target_season_index` and cutoff week.

The page does not invent a cross-domain ordinal or map legacy snapshot sequence values onto canonical publication identities.

## Hidden evidence

Viewer History does not expose:

- Saved Revision IDs or component fingerprints;
- Official Ranking snapshot fingerprints;
- command/audit provenance;
- legacy SimulationRun activity payloads;
- unpublished Working Draft state.

## Failure behavior

Each canonical source reports its own read failure. There is no fallback to `getRunActivity()` or other legacy activity data.

## Non-goals

This slice does not replace the legacy Race snapshot-sequence detail route because that route's `snapshotSequence` identity is not equivalent to canonical Finals Race `target_season_index`. Resolving or retiring that compatibility URL requires an explicit identity decision rather than silent reinterpretation.
