# Calendar-owned initial Health — Master v82

Implementation candidate on merged #1500; no new product mechanics or Master
revision. This closes the initial-health persistence boundary, not sporting time.

## Operator flow and authority

After a custom-clock population has been explicitly saved, Players → Generate
shows Initial health in CS/EN. Review is read-only. Separate consent confirms a
fresh baseline into a dirty Working Draft; it does not Save. Another consent and
manual Health Save creates an immutable revision using the existing Health Save
CAS. The UI verifies scope, clock, roster, Saved head, draft version, review and
Save receipt. A lost confirmation response is recovered by reading current state.
Review/consent is discarded when its source changes; automatic mutation retries
are disabled.

The baseline is explicitly `fresh_without_history.v1`, with no Injury, Illness or
permanent-consequence records. It is not a realistic random distribution and does
not heal existing players: it may only initialize absent health for an unstarted,
writable custom Run with a clean Draft and already saved V2 population. Future
initial-condition sampling remains separate from this explicit test baseline.

## Backend contract

`calendar_initial_health_state.v1` owns a `RunWeekPosition` and requires ordinal
zero, canonical roster, empty event history and a source population fingerprint.
It records command/request fingerprints and Admin label/reason. GET inspection
and POST review/confirmation live at
`/admin/runs/{run}/branches/{branch}/player-health/calendar-initial` (review suffix
`/preview`). Confirmation holds `BEGIN IMMEDIATE` and revalidates Saved population,
lifecycle, clock, head, draft and expected health hash before atomic state/draft
writes. Exact installed command retries return the installed view without adding
another draft change. Failure rolls back both health and draft.

Existing explicit `/player-health/save` captures the component. Snapshot loading
validates hashes, owner, population roster and actual calendar. Fork remaps branch
ownership while preserving historical source provenance; restore and restart
preserve exact states. Restoring a population-only revision does not backfill
health. Legacy Health V1 schemas/hashes and old Week semantics are unchanged.

The new schema cannot contain mixed/advanced health history. Legacy RankingWeek
reads and writers reject it, even when both ordinals are zero. Injury edits,
recovery and later weeks require a subsequent versioned calendar-event migration;
this slice does not unlock sporting execution or invent annual growth scaling.

## Verification

- Seven real HTTP/SQLite scenarios cover W52, W80 and W1/year zero; review
  non-mutation; confirmation vs Save; exact retries before/after Save; materialized
  fork, backward/forward restore and process restart; stale review/draft; concurrent
  identical commands; injected post-write rollback; legacy read refusal.
- Focused legacy Health edit/persistence/API, restore and lifecycle-fork regressions.
- Five new frontend component tests cover two consents, response loss, asynchronous
  stale review, wrong-population proof and mismatched Save receipt. Existing
  population controls remain covered; these component tests mock the API boundary.
- Existing Shell acceptance is extended (no new workflow) to review/confirm/save
  actual 1,000-player W52 health, verify unchanged head before Save, inspect Saved
  component, reload exact state and capture a screenshot. Final-head CI/browser
  results belong in the PR evidence; local build alone is not browser evidence.

Next: actual Run-owned health-event dates and annual development, then the other
calendar sporting callers. Calibration stays an explicit later testing activity.
