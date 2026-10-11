# Viewer Canonical People Details v1

## Purpose

Run-scoped Player Profile and Country Profile surfaces now render current state only from Product Run-scoped canonical Saved-Revision people projections.

## Player Profile

The current profile is resolved from `viewer_players.v1` by canonical player ID and exposes only the current Saved-Revision fields already published by that authority.

Season-by-season career history, season performance and per-player tournament-result history are explicitly deferred because no dedicated canonical Saved-Revision history authority exists yet.

Legacy SimulationRun player-detail/career APIs are not used by this Viewer page.

## Country Profile

The current country profile is resolved from `viewer_countries.v1`. The current country roster is resolved from `viewer_players.v1`.

Historical source mix, talent-band evolution and other historical country aggregates remain explicitly deferred.

Legacy SimulationRun nation-detail API is not used by this Viewer page.

## Boundary

The migration does not infer missing history from current summaries, mutable live state or legacy compatibility tables.
