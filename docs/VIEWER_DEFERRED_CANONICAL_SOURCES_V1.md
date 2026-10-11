# Viewer Deferred Canonical Sources v1

## Purpose

Deferred Viewer pages must not infer sporting outputs that do not yet have dedicated canonical read models. They may, however, show safe source availability from canonical Saved-Revision/publication authorities.

## Canonical sources

The shared deferred source hook reads only:

- \`viewer_run_calendar.v1\` for Saved Calendar season/event availability;
- \`viewer_tournament_history.v1\` for completed published Tournament Results;
- \`viewer_official_ranking_history.v1\` for Official Ranking publication history;
- \`viewer_finals_race_history.v1\` for World Tour Finals Race publication history.

## Removed legacy readers

The shared deferred path no longer reads:

- SimulationRun \`getRun\`;
- Run status summaries;
- persisted legacy event lists;
- Ranking snapshot lists;
- Race snapshot lists;
- legacy Finals summary.

## Deferred boundary

No statistics, predictions, records, ranking analyses or Tour outputs are synthesized from these source counts. The pages only expose safe publication/source availability and navigation to existing canonical Viewer surfaces.

## Identity

All links are Product Run-scoped. Ranking detail links use canonical \`week_ordinal\`. Finals Race links target the canonical Race surface rather than legacy Race snapshot detail identities.
