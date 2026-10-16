# Pre-alpha checkpoint v83 — 16 October 2026

## Product decisions and implementation are separate

Canon: Master v83, especially 9.8 and 31.38. These record the owner's
16 October discussion, not automatic runtime capability. Existing v82 calendar
rules, Lab independence, operation-scoped validation, manual Save, deterministic
history and protected Package rules continue.

New decisions: optional resumable world preparation; actual-content readiness
before/after simulation; collapsible Home guidance; selected Run content exported
through existing Packages; initial population prepared from the same 15-year-old
cohort model as ongoing intake using historical country conditions and simplified
individual development to start. Omit already-retired profiles; retain current
state and reproducibility. Count derives from the world, with explicit manual
constraints available. FAX reference still needs at least 1,000 eligible players.
Full/selected prestart regeneration respects locks and existing dependency review.
Confirmation accepts the exact preview, then manual Save.

Deferred explicitly: whether initial custom generation-rule edits apply to future
intake. No automatic inheritance/segregation default is decided. Automatic forecast
triggering, prediction intervals, caching/performance and detailed calibration
require measurement. A separate generation-recipe Package option was proposed but
not accepted; do not silently implement it as decided canon.

## Fresh audit

Base: `buuk` `b51d88efba3977eaf14d165f9dd83b5927310c6c`, merged #1506.
#1506 merged while the initial inventory was being fetched; the fresh local fetch
and second GitHub inventory agree. No open PR remained at that check.

| PR | Actually implemented | Final feature HEAD | Final workflow evidence |
| --- | --- | --- | --- |
| #1502 | Run-owned health facts, reviewed Admin edits and saved-player CS/EN Health panel; persistence/receipt/fork/restore | `ae6136860a6eb9740db66dad46bdfbecd9d3f7d5` | Shell 38940259783, Fast CI 38940259901, Saved Player Replay 38940259786: success |
| #1503 | Storage/exact-JSON bounds for pure horizon planning | `21bd57274dade17b146f17932c3f1697c61b83a0` | Fast CI 38950712092: success |
| #1504 | Read-only Saved-clock extension preview application/API | `8ddf6d75eac6b2f970aad4f35ebd541d7bb0a01e` | Fast CI 38951764716: success |
| #1505 | CS/EN extension inspection on Run Home | `d6b6263d13126e39b39067998a42809de81c41e6` | All eight triggered workflows success; Fast CI 38952222712, Shell 38952222857 |
| #1506 | Read-only all-Branch Saved-head/hash/calendar readiness | `e1e186fdcce5308869ff8c6a0319eb73c7f86c1c` | Fast CI 38952565833: success |

Read the changed domain, application, persistence, API and frontend paths plus
relevant regression tests. Green CI is evidence only for the scenarios actually
run. No new full-suite/release workflow was requested for this checkpoint.

## Findings fixed in the checkpoint PR

1. Extension inspection could display a late response after editing the requested
   horizon or changing scope. Scope/input generation and request sequencing now
   discard stale results/errors and invalidate displayed plans. Two component
   regressions cover late success and former-Branch failure. This is a read-only
   UI bug, not evidence of an unauthorized extension writer.
2. The all-Branch readiness API read multiple rows without an explicit SQLite
   read snapshot. The route now starts BEGIN before the inventory, keeping one
   coherent read transaction. The application helper still accepts its caller's
   transaction, allowing eventual writer reuse. An actual SQLite SQL trace
   regression verifies BEGIN precedes the cohort reads. This does not grant
   readiness the authority of a future extension commit.
3. Isolated readiness test collection exposed a circular import through eager
   db package exports and the calendar sporting guard. Calendar authority defers
   its model imports until runtime; a fresh-process import regression protects
   independent service loading. No calendar guard was weakened.
4. CURRENT_STATE/ROADMAP still called merged #1502 and later features candidates.
   This checkpoint replaces stale active notes with the audited boundary.

Local audit: 31 focused health/domain/API/calendar/extension tests passed before
final snapshot-route placement; 10 authority/extension/readiness tests pass after final snapshot-route/import fixes.
Frontend response-scope regressions and production build are required. Final-head
workflow evidence belongs in the PR handoff; this document alone asserts no CI
result for its own future commit.

## Remaining implementation boundary

Extension currently plans and inspects. It cannot commit, create all Branch Saved
heads atomically, reconcile live calendar-owned snapshots or safely continue a
Completed Run. Dirty/read-only Branches, conflicting tasks, historical restore and
frozen targets need concrete writer semantics/testing before unlock.

Health edits carry actual dates; automatic recovery and calendar sporting
transitions remain guarded. Annual development, ranking validity, sporting
progression and frozen Full Simulation goals still need migration. The natural
historical-cohort bootstrap, readiness guide and expanded Package export UX remain
targets, not shipped functionality. No claim of 1,000 × 80 populated season, all
50 FAX seasons, full regression, realistic retirement distribution or release.

Recommended next work: finish one complete reviewed all-Branch horizon extension
transaction and usable explicit Save flow. Details in the v83 continuation task.
Do not split it into more isolated inspection-only PRs unless a concrete blocker
requires it. User alone merges.
