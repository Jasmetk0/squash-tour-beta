# Viewer Tournament Result v1

## Purpose

Viewer Tournament Detail reads completed tournament sporting outcomes from the selected
Viewer Branch's immutable Saved Revision. The public projection does not consult the
legacy SimulationRun event-result registry and does not read the live Working Draft.

## Authority

The source is the Saved Revision `RankingRevisionState.tournament_sources` collection.
The requested event must resolve to exactly one `OwnedTournamentRankingSource` with a
canonical `TournamentResultAuthority`.

The source must match the selected Product Run, Viewer Branch and event identity.
Missing canonical result evidence returns not-found; ambiguous or incoherent canonical
evidence fails closed.

A live canonical tournament close is intentionally invisible until the Ranking component
is explicitly Saved. This preserves the same Viewer publication boundary used by
canonical Official Ranking.

## Public sporting projection

`viewer_tournament_result.v1` exposes:

- Product Run, Viewer Branch and event identity;
- completed season index and Season Week;
- champion and finalist player IDs;
- Qualification winner IDs;
- per-player sporting outcome: draw type, seed, qualifier/Main-entry status, reached
  stage, elimination/match references, wins/losses, BYEs/W/Os and group/hybrid placement
  fields when those are part of canonical result history;
- completed match identity, phase, round/position, winner/loser and scoreline.

## Deliberately hidden

Viewer does not expose:

- authority/source fingerprints;
- command IDs or Admin provenance;
- draw/match-package fingerprints;
- per-match result fingerprints;
- canonical point-award or prize-money authority internals;
- ranking point-distribution configuration;
- live Working Draft state.

## Compatibility boundary

Tournament Detail now uses this canonical projection for its primary result section.
Legacy event/result payloads may still exist as collapsed technical compatibility data
and the tournament-list summary may still use the legacy event record until a separate
list/history detachment slice is completed. Their presence does not make them authority
for the canonical detail result.
