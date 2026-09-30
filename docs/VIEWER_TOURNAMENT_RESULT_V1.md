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

## Public sporting projections

`viewer_tournament_result.v1` exposes one completed event in detail:



- Product Run, Viewer Branch and event identity;
- completed season index and Season Week;
- champion and finalist player IDs;
- Qualification winner IDs;
- per-player sporting outcome: draw type, seed, qualifier/Main-entry status, reached
  stage, elimination/match references, wins/losses, BYEs/W/Os and group/hybrid placement
  fields when those are part of canonical result history;
- completed match identity, phase, round/position, winner/loser and scoreline.

`viewer_completed_tournaments.v1` exposes the Saved-Revision history collection:

- one deterministic summary per event with canonical result authority;
- completed season index and Season Week;
- champion/finalist and Qualification winner IDs;
- player and completed-match counts;
- deterministic ordering by completed season, completed week and event ID.

The collection skips ranking tournament sources that do not yet own canonical Result
authority and fails closed if duplicate event identities make public history ambiguous.

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

Tournament Detail uses the canonical single-event projection for its primary result
section. The tournament list uses the canonical completed-history collection for
completion state, champion/finalist and result counts.

Legacy event/result payloads may still exist as collapsed technical compatibility data.
The list still uses legacy/ordered-calendar records only for schedule metadata such as
sequence, template, category and tour because Viewer Saved Revision does not yet expose a
public Calendar Package component. A canonical completed result is still listed even if
the legacy event record is absent. Legacy result payloads are never authority for public
sporting outcomes.
