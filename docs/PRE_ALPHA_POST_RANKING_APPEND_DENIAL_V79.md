# F79-09 — published ranking closes opening-population Add Selected

This acceptance extends F79-07's **real Chromium / production backend /
isolated SQLite / restart** run. The test builds a genuine 34-player
InitialWorld, explicitly saves the new revision, restarts the backend, then
uses the Admin to calculate, save, publish and save a real Week-1 Official
Ranking.

A separately generated source of 200 players is inspected; the Admin selects
one new, non-colliding ID and obtains a read-only server-provided combined
preview. The user deliberately approves the selected Add **after ranking
publication**.

The server must reject its final POST with `409` and
`selected_initial_world_append_conflict`, explaining that ranking/sporting
activity closes this opening-week operation. The test hashes a full canonical
SQLite dump before source preview and after rejection: no revision, ranking,
health, sporting, lifecycle, generation or other SQL row may change. Existing
34-player data and Week-1 projections are compared separately. Screenshots,
trace and the structured evidence artifact are retained.

This is **not** a design for adding late players into a running season.
Late/weekly intake, formal Tour-entry date, ranking eligibility and
historical event policy remain a separate product feature.

The browser extends the existing source script and triggers the same
path-scoped GitHub Action. A small separate PR-critical SQLite test checks
repeated ranked-state rejection against the *entire* raw persisted database,
including immutable Saved Revision rows. Only the necessary tests run in
ordinary PR CI; no new recurring expensive broad suite.
