# One native Edition — real HTTP/SQLite operator chain (2026-11-01)

## Why this targeted test exists

The complete native Tour tests already cover multi-Edition outcomes,
W52/W61/W80 and many cross-season boundaries. Some are long-running and
require their own release/Ready acceptance gates. This additional single
**4-real-player** test makes the exact operator-controlled Entry → approved
field → signed draw → production MatchEngine → reviewed results → Official
ranking/points → manual Save → physical database restart dependency observable
on every changed PR head without substituting mocks or SQL fixture repair.

It uses the existing production
`tests.api.test_calendar_tour_flow` commands and the real
`tests.api.test_saved_revision_history_api.ApiServer` stack, not a
second sporting or persistence implementation.

## What the new gate actually tests

- Creates a writable Run with the real native population/Health/sporting
  prerequisites and a four-entrant Tour Edition scheduled two weeks later.
- Moves through two explicit Run week transitions and normal Saved boundaries.
- Submits actual player IDs, confirms the entry field and draws explicitly.
  The draft is *not* a Saved draw. The real production Preview denies play
  until the separate immutable manual Save.
- Viewer remains unchanged while the Admin prepares an unsaved
  field/draw and again while real played matches and reviewed results
  await manual Save.
- Signed draw allows actual four-player MatchEngine play:
  exactly two semifinals and one final; a reviewed result is signed
  separately; the next Official Week publishes exactly 30/30/60/100 points.
- Physically closes and reopens the SQLite backend and verifies Saved HEAD,
  actual match/result evidence, ranking points, Viewer visibility and
  exact original replay for play/transition (no duplicated awards/matches).
- Rejects a foreign Branch-scoped request.

The dedicated CI workflow runs the scenario **even while the PR is Draft**,
using an isolated SQLite fixture and explicit production acceptance event.
The existing Fast CI remains unchanged; long native acceptance and full
release gates are not downgraded or skipped.

## What it DOES NOT prove

- It is a single, four-player native Edition, not the FAX reference of at
  least 1,000 players / 80 actual World Tour Editions.
- It does not implement the still-open complete automatic application
  eligibility/deadline policy, lower Tours, World Tour Finals or every
  entered Edition.
- It does not complete one entire reference season or 50 seasons.
- It is real HTTP/SQLite, **not a new Chromium UI** acceptance.
- The full current pre-alpha release gate in `docs/PRE_ALPHA_TEST_POLICY.md`
  and separate existing multi-Edition native acceptance must still pass.
- This scope changes only its own test, workflow and evidence document;
  no sporting rules, code contract, old fixtures, package data or Master.
  Avoid overlap with Jules' independent FAX calendar, population, Earth and
  Labs tasks and open PRs #1700–#1712.

Owner-only merge; the PR stays Draft until the final-head real gate passes.
