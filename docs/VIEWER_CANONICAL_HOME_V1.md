# Viewer Canonical Home v1

## Purpose

Viewer Home is a read-only public entry surface. Its active-run summaries must come from canonical Viewer projections captured by the selected Viewer Branch Saved Revision, not from legacy SimulationRun runtime/state APIs.

## Canonical readers

Home uses:

- `viewer official context` for Product Run identity and current saved public context;
- `viewer_tournament_history.v1` for published Tournament history;
- `viewer_official_ranking_history.v1` for Official Ranking publications;
- `viewer_finals_race_history.v1` for World Tour Finals Race publications.

Legacy Home readers such as `getRun`, `getRunStatusSummary`, `listEvents`, ranking/race snapshot lists, `getRunActivity`, and `getFinalsSummary` are not used.

## Public summaries

The Home page may show:

- Product Run and Viewer Branch identity;
- current public season/week from Viewer Official Context;
- count and latest published completed Tournament Result;
- latest Official Ranking publication;
- latest World Tour Finals Race publication and selection status;
- canonical History counts.

It does not expose Saved Revision IDs, fingerprints, command/audit provenance, or Working Draft state.

## Calendar boundary

Home does not reconstruct a schedule from legacy SimulationRun state. Until the canonical calendar package stack is integrated into this branch, Home links to the run-scoped calendar surface and leaves schedule interpretation there.

## Snapshot identity boundary

Home no longer links to legacy Ranking/Race `snapshotSequence` detail pages. Canonical Official Ranking uses `week_ordinal`; canonical Finals Race uses `target_season_index`. These identities are not silently translated.

## Failure behavior

If a canonical reader fails, Home shows a safe unavailable state instead of falling back to legacy APIs or inventing partial public truth.

## Non-goals

This slice does not change sporting rules, Race calculation, Finals qualification, tournament results, calendar policy, or the legacy Race detail compatibility route.
