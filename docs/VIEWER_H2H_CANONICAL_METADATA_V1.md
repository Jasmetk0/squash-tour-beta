# Viewer H2H Canonical Metadata Boundary v1

## Purpose

H2H subroutes remain deferred until an authoritative match-history read model exists.

Their sporting source metadata now comes from canonical Saved-Revision/publication authorities. Player samples are the only remaining legacy source because a canonical Product Run player projection does not yet exist.

## Canonical sporting metadata

H2H subroutes consume the shared canonical deferred-source hook:

- \`viewer_run_calendar.v1\`;
- canonical Tournament History;
- canonical Official Ranking History;
- canonical World Tour Finals Race History.

These sources are Product Run-scoped.

## Explicit legacy exception

\`listRunPlayers\` still reads the legacy SimulationRun player registry.

This exception is isolated to player sample/browsing metadata. It must not be used to infer tournament, ranking, Race, Finals, schedule or history state.

If a Product Run is selected without a mapped legacy SimulationRun player source, H2H still renders canonical sporting metadata and reports the player source as unavailable.

## Deferred boundary

No rivalry, most-played, Finals-rivalry or H2H analytics are synthesized here. Those outputs remain deferred until authoritative match history is available.
