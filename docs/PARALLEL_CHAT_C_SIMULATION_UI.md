# Parallel Chat C — Simulation operator UI

Date: 2026-10-22. Base `buuk` at `0bd062166150283e22163f52a97aa96649bcbf04`. This branch is limited to the existing simulation UI and its tests. The product owner alone merges.

## Inspected route and contracts

- `RunSimulationPage` resolves an explicit Run/Branch and shows `AuthoritativeSimulationPanel` before legacy compatibility actions. The authoritative panel already has the reviewed Full Simulation command, explicit operator controls, pause/resume/stop and a per-Branch server-task list. Do not duplicate these.
- The server-task contract is `web/src/api/fullSimulationTasks.ts`: `startServerTask(run, branch, requestId, command)`, `continueServerTask(task, {request_id, action, expected_revision, operator_label, audit_reason})`. Requests are audited, revision-bound and idempotent by request ID. Success ACK includes exact Run, Branch, task and parent identity. Polling (`useServerTasks`) is read-only.
- The status evidence separates actual task state, requested state, last heartbeat, lease expiry, current operator checkpoint, historic checkpoint and stored driver evidence. Worker health is not established by a receipt or unexpired lease.
- Existing checkpoint flows: `week_schedule_review_required` opens a read-only extension inspection/explicit approval; ordinary preparation routes to Run Management; Save, season/final review and task recovery remain deliberate separate operator actions. No polling or render starts work.

## Implemented in this branch

1. **Frozen start requests.** `StartServerTask` captures Run ID, Branch ID, request ID, command ID, operator, audit reason, expected start, revision and fingerprints at the actual click. React Query receives that immutable snapshot as mutation variables; a rerender/offline pause cannot redirect it. Retry reuses the full original snapshot. A new context cannot issue a misleading retry, and a late successful response cannot call the newly selected context's acceptance callback. Parent also keys the component by Run/Branch/command.
2. **Frozen continuation/recovery.** `TaskCard` freezes the exact task identity and submitted `ContinueTask` together. Retry and post-success invalidation use that snapshot instead of props changed during polling. The existing same-request uncertain-response retry contract is preserved. No automatic recovery.
3. **Operator evidence.** The existing task state/checkpoint distinction is preserved; requested task state and lease expiry are visibly separate from worker heartbeat, with explicit wording that lease is not process-health proof.
4. **Exact linked task.** The existing `?branch=...&task=...` Run Simulation link now focuses the task row (first in the scoped list and marked as selected). A missing task in that Run/Branch produces a visible warning; no substitute task is selected or acted on. No new route.
5. **Reviewed parent controls.** Pause, resume, permanent Stop and target-change submissions in `AuthoritativeSimulationPanel` now pass exact Run/Branch plus frozen command/payload as mutation variables. Any offline-queued request remains bound to the submitted parent and audit values. Successful late replies invalidate their original Run/Branch only, not a later selection. A lost reply is retried with its original payload (not the currently edited form); the fields lock until explicit cancel or success. Run/Branch switching clears only local editor state, not the already submitted remote command.
6. **Calendar handoff correction.** Task evidence contains a season index but no authoritative calendar year/start offset. The earlier hard-coded `2000 + season_index` produced a possibly incorrect `calendarSeason`; the link now goes to the actual Run Management page with the exact Branch selected, leaving calendar-season choice explicit.

CS/EN task messages live in the locally scoped task component, with additional local bilingual frozen-request feedback in the authoritative panel. Earlier universal text claiming season index 0 means 2000/01 and every season is W61 is removed; the form's inherited legacy numeric limits remain unchanged pending a versioned Run calendar contract. API/client/types, shared translations, backend, styles and unrelated chats remain unchanged.

## Validation / boundaries

Added focused mocked UI regressions covering offline-queued start and pause across context switch, exact pending continuation across polling revision, frozen control/retarget fields on lost replies, dropped-response retry, linked task focus and missing-task warning, plus the previously covered bilingual checkpoint/driver/heartbeat guidance. These tests only exercise React/query behavior with mocked HTTP and **do not prove a real worker or restart**.

No local checkout/node dependency installation was available in this chat runtime, so do **not** mark these tests or the TypeScript build as locally executed. Verify Fast CI, TypeScript/Vite build and focused Vitest on the exact PR head, and run applicable real HTTP/Chromium/SQLite release acceptance before declaring merge readiness. Draft skipped checks are not passes.

## Explicit contract gap for backend/API owner (not changed)

`web/src/api/fullSimulationTasks.ts` still validates task weeks and elapsed time with an implicit W61 calendar (`week <= 61`, `season_index*61`), while Master v82 supports Run-specific W and start year/offset. The task view lacks the current Run calendar basis needed to derive the real calendar season label and validate elapsed weeks across all Runs. Coordinate a separate versioned API/task-evidence extension with the backend owner, rather than introducing a client-side guessed year or changing the shared client during this parallel branch.

## Next bounded work

Remaining non-server command paths include the legacy Full Simulation parent invocation and pause acknowledgement; audit their offline-queued and late-result scoping separately. Do not broaden this parallel PR into sporting decisions, backend/worker, routes or shared API contracts. Run exact-head focused Vitest, TypeScript/build, relevant real HTTP/Chromium/SQLite acceptance and independent review before requesting merge. Then validate on the exact latest commit and request independent review. Owner merges only.
