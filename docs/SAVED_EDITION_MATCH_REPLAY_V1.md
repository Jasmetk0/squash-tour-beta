# Saved Revision Edition Match Detail & Rally Replay — 13 October 2026

This coherent Master v80 read-only UI/API slice follows merged PR #1420.
It does not change current Player Match Detail, simulation, RNG, Schedule or
Official Viewer behavior.

## Exact historical scope

`GET /admin/runs/{run_id}/branches/{branch_id}/tour/editions/{event_id}/matches/{match_id}?revision_id={revision_id}&season_index={0..49}&offset={n}&limit={1..25}`

- `RunSavedRevisionHistoryService.get_revision` verifies selected Branch lineage
  and the actual reachable immutable Saved Revision, including shared pre-fork
  ancestors. All Calendar, Ranking and Simulation Slot components are loaded
  from the SAME Saved Revision using its original owning Branch, not today's
  Saved HEAD or current Official Viewer.
- The match must exist **exactly once** in the canonical *published*
  Tournament Result matching Run/original Branch/Event/season/week. Unknown
  matches and pre-publication revisions remain HTTP 404. A 409 is returned for
  corrupt/ambiguous authorities, forged source identity or replay mismatch.
- Canonical result, winner, loser, draw type, round, bracket position and
  scoreline are always visible for an eligible match. BYE/non-played entries
  without a real opponent are not represented as invented played matches.
- Archived rally replay is separately optional. Its saved competitive group
  must prove exact Run/original Branch/week/event/match, winner/loser and
  player A/B identities. An unrelated Event with the same match ID is NOT a
  replay authority. W/O or missing rally log yields `replay_status=unavailable`.
  The API exposes up to 25 true archived frames per request and total count;
  it does NOT reveal RNG seeds, immutable input fingerprints or engine internals.

## UI

Edition Results and Schedule link actual published, two-sided matches to
`/admin/runs/:runId/tour/calendar/:eventId/matches/:matchId`, preserving all
query filters, selected Branch, explicit Saved Revision, season and parent tab.
The new historical page never navigates into current Saved Player HEAD.
Rally Previous/Next controls page on exact revision-scoped API and reset when
any match, branch or revision changes. CS/EN labels and honest absence text.
Read-only historical checkpoint→Saved Revision mapping remains fail-closed;
no active Admin Branch switching or implicit Save.

## Gate

Focused Python application/real FastAPI+SQLite API tests, frontend response
scope & pager tests, Vite build, and actual 64-player Chromium Saved Replay
acceptance using true archived rally frames for the exact Edition. Acceptance
must show rally 26 (crossing pagination), back-navigation with the original
filters, and repeat identical proof after backend SQLite restart.

Still missing: historical replay for matches without archived rally logs,
rally commentary data, and explicit in-Schedule group-format match anchors
without published canonical IDs; none is fabricated.
