# Viewer Canonical People UI Migration v1

## Purpose

Viewer people list/search/sample surfaces now consume the Product Run-scoped canonical people APIs:

- \`viewer_players.v1\`;
- \`viewer_countries.v1\`.

These surfaces no longer depend on legacy SimulationRun \`listRunPlayers\` or \`listRunNations\`.

## Migrated surfaces

- top-level Players hub;
- top-level Countries hub;
- Viewer Search player/country results;
- H2H deferred player sample;
- run-scoped Players list;
- run-scoped Countries list.

Viewer Search also uses canonical Saved Calendar + Tournament History for tournament results instead of legacy \`getRun/listEvents\`.

## Deliberately not migrated in this slice

Detailed player career/history/performance/tournament-result endpoints and detailed country profile endpoints still use their existing legacy detail APIs because \`viewer_players.v1\` / \`viewer_countries.v1\` intentionally publish current Saved-Revision summaries, not historical career breakdowns.

Those detail routes remain an explicit compatibility island for a later dedicated canonical history/profile read model.

## Identity

All migrated links use Product Run IDs and canonical player/country identities.
