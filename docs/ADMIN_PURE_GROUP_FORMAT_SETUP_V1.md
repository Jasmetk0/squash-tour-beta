# Admin pure-group tournament preparation — 13 October 2026

This is a production UI unblocker identified during attempted real hybrid/group
browser acceptance. Earlier #1422/#1423 have immutable Saved Edition group
Schedule and completed Standings projections, but the Run's tournament
preparation UI lacked working Format/Topology setup controls.

## User workflow

On the exact writable selected Run + Branch and Present mode, with a frozen
canonical Entry Field, the `configure_tournament_format` handoff now renders
an actual group setup panel. It reads **effective season-specific group rules**
from the production Admin API and requires an explicit approval to adopt BO3
or BO5 group policy only when no effective policy exists.

The Admin chooses group count and players per group; capacity **must exactly
partition the real direct main entrants**. The first UI slice supports **pure
round robin with no seeded group placements**, no Q/WC/BYE reservations, and
no invented post-group crossing. It explicitly does not silently invent the
crossing scheme for `groups_knockout`. A separate hybrid editor can enable
those rules after they are decided.

After an explicit confirmation the UI calls the existing production
`format/configure` endpoint, verifies the returned frozen Format and
invalidates canonical preparation. The next `generate_tournament_topology`
handoff shows the explicit confirmation for production Topology generation.
Its success invalidates preparation and unlocks the **existing**
`prepare_group_match_schedule` action, then the authoritative week scheduling
and actual match simulation driver already in the engine.

No API changes, fixture-generated sporting facts, RNG changes, implicit Save,
fake historical revisions, or current-Branch bypass were added.

## Acceptance

Frontend component and pure validation tests cover effective rules vs missing
policy, intentional confirmation for each irreversible authority, group
partition integrity, qualification/BYE refusal and mutation payload/run scope.
Existing Fast CI frontend and backend lanes must stay green. This PR does
**not** claim a finished group/hybrid real-browser simulation: next task is
a distinct genuine Chromium + FastAPI/SQLite Run group workflow from
rules/format/topology/schedule through played canonical matches, frozen
standings, Save and restart. Group standings browser assertions must only
follow actual played/authoritative receipts.
