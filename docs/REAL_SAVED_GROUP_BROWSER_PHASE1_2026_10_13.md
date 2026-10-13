# Real Saved Group Pre-result Browser Acceptance — 13 October 2026

This acceptance addresses the first half of the previously identified
non-knockout historical Edition browser gap. It deliberately does **not**
pretend to complete or simulate every round-robin match.

## What is real

- Same disposable production FastAPI + SQLite + Vite + Chromium setup used by
  the proven Run tournament browser acceptance; a new isolated Run and initial
  64-player generated InitialWorld with authoritative ranking and real AI Entry
  decisions are made through the existing browser workflow.
- The normal **browser** previews, approves and freezes the canonical 4-player
  Entry Field. Genuine **HTTP production commands** then adopt a versioned
  group-rules policy, configure one 4-player BO3 `groups` format, generate the
  canonical Format-bound Topology, and freeze all six round-robin matches over
  three conflict-free Match Days.
- All these are persisted in the Run's ordinary SQLite authority tables,
  then saved through the standard Working Draft Save endpoint to an immutable
  Saved Revision. The older revision must not change even though commands were
  already committed in live Run state.
- The existing production historical `/tour/editions/{event}` endpoint must
  read exactly the new Saved Revision with the real original branch,
  schedule fingerprint, players, BO3/Match Days and no fake standings or
  published match results.
- In Chromium, the actual Edition Schedule tab must display all six real
  pairings (BO3), while Results must refuse to show an unearned final table.
  Another clean browser context reopens the same Run after a real backend
  process restart against the same SQLite database. JSON response equality
  and screenshots/traces are preserved.
- Foreign/unreachable revisions and cross-season event lookups are rejected.

## Honest boundary

This is **real pre-result Group Format/Topology/Schedule Save → historical
Edition → SQLite restart E2E**, not a finished tournament or hybrid group
closure. The Stage 2 acceptance remains:
simulate every group match through AuthoritativeRunSimulationDriver,
write canonical group result receipts, materialize Group Standings and any
explicit Admin tie authority, Save that result in a later revision, verify
historical immutable separation and final group standings in Chromium,
and repeat after SQLite restart. A hybrid knockout needs additional
post-group entrants, bracket, match execution and closure beyond that.

The dedicated workflow runs on changes to this script or these particular
Saved Group projections, not on arbitrary frontend/style PRs. It does not
trigger the entire legacy tournament browser for a group-only PR.
