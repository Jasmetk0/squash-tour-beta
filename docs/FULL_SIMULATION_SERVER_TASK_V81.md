# Server-owned Full Simulation tasks — v81

Baseline: `buuk` `0f4d89dd8635f41f0d9b0cee2c831211a34a7fae`, merged #1469.
This candidate implements issue #1470 above the existing authoritative driver.
It changes execution lifetime, not sporting rules, RNG, or Saved Revision authority.

## User workflow

1. Review the original Full Simulation command in Run Admin, including operator,
   reason, Position, Saved Revision and final target. Confirm that review and
   choose **Start as server task**. HTTP 202 acknowledges the durable task ID,
   unchanged parent Command ID and accepted revision before sporting work finishes.
2. Close the tab or browse elsewhere. While this server lives, its dispatcher
   continues canonical work. Open Global Task Center, inspect the stored task and
   follow its exact Run/Branch/task link. Polling only reads evidence.
3. Existing audited safe pause, Stop and weekly/relative retarget controls still
   control the same parent. A live worker acknowledges pause after its current
   safe transaction. An idle task can acknowledge a pause without executing sport.
   Explicit task continuation requires a new operator/reason/request ID.
4. At Entry, week preparation, Save, Season Transition or final closure review,
   the worker records the exact canonical checkpoint and waits. Resolve the real
   prerequisite using the existing Run Admin authority, then explicitly resume
   the same task. No Save or approval is performed by the worker.
5. After process death, inspect the same task. Another server instance's
   unexpired lease is shown as **ownership unverified**, never as proof of
   continuing execution. Expired/lost ownership becomes **recoverable**. Recovery
   is an explicit audited POST; it cannot steal an unexpired lease.

Both Admin and Global Task Center provide CS/EN presentation. A lost start or
continuation response is retried with exactly the original ID, audit input and
expected revision. Inspection and replay of an old acknowledgement never enqueue
work. Cancel a failed continuation retry and refresh before authorizing changed
input. Terminal summaries reuse #1469's immutable captured evidence.

## Persistence and transitions

`full_simulation_tasks` is additive SQLite schema, bootstrapped with the existing
repository schema mechanism. Each task has a stable ID, exact Run/Branch/parent
scope, unique scoped start request, immutable reviewed command, fingerprinted
payload, monotonic event revision and hash-linked transition history. Each
accepted request stores its exact input and frozen acknowledgement. Payload,
identity, command, request and transition corruption fails closed. This detects
inconsistent stored evidence, not a malicious administrator rewriting an entire
SQLite database and every checksum.

Durable transitions:

- explicit Start → `queued` → `active`;
- `active` → `paused`, `awaiting_operator`, `stopped`, `target_reached`, `complete`
  or `failed`;
- explicit Resume: `paused` / `awaiting_operator` → `queued`;
- explicit Recover: expired `queued` / `active` / `failed` → `queued`;
- an idle `awaiting_operator` task can acknowledge a safe pause;
- terminal parent receipts remain terminal. A different operation needs a new
  separately reviewed parent.

Observed `pause_requested`, `recoverable` and `ownership_unverified` are derived
from the parent control, current global lease and observer instance; GET does
not persist transitions. A parent's Stop/target/completion is authoritative even
if it commits before the disposable worker records its last observation.

Heartbeat classification is independent of desired task state. **recent** means
an actual worker heartbeat was observed recently, not that useful progress or
healthy execution is guaranteed. **stale** is explicitly unverified; **inactive**
means no valid matching ownership. Current week comes from committed Branch
world/sporting state; checkpoint/progress comes from the canonical driver. There
are no fabricated percentages, events or ETAs.

## Claim, execution and shutdown

Start freezes the existing reviewed parent, creates the task and reserves the
existing global invocation lease in **one BEGIN IMMEDIATE transaction**. Failure
rolls all three back. A process-local dispatcher is merely an executor of that
persisted claim; it is not the source of task identity or command intent. There
is no request-bound background execution or second simulator.

Only one Full Simulation owner can hold the database's global lease. The old
synchronous endpoint retains its ordinary contract; it cannot race a reserved
server task, and a task-owned parent must be continued through task controls.
The existing renewable token fence is rechecked after SQLite writer acquisition,
at ORM flush and at commit. Task payload/claim integrity is checked there too.
Expired/reclaimed owners cannot commit more sport or overwrite a newer task
claim. Release is token-conditional.

The dispatcher yields before a new transaction after at most 64 writer-boundary
attempts per chunk, then re-enters the same driver with the same command and
frozen child IDs. A synchronous child is not forcibly interrupted mid-commit.
The first real prerequisite exits execution; it is never retried in a busy loop.
A shutdown signal prevents the next sporting transaction and records a failure
where the claim is still valid. Abrupt death leaves a durable claim and expiring
lease. New application startup does **not** scan or execute old queued/active
records. Recovery creates a new token in the writer transaction and retains all
canonical child IDs and results.

Task records are control-plane evidence, not Saved Revisions or Recovery Draft
substitutes. A restored world with a missing/mismatched parent must fail closed;
the task layer does not recreate removed historical command evidence.

## Versioned HTTP actions

All scoped paths below start with
`/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation`.

```http
POST /full-simulation/tasks
{"request_id":"operator-start-1","command":{...original reviewed Full Simulation command...}}
```

Returns HTTP 202 `full_simulation_task_ack.v1`, including task/parent/scope,
request ID and accepted revision. Exact replay returns the same acknowledgement
also after progress or completion. Reusing an ID with changed input is HTTP 409.

```http
GET /full-simulation/tasks
GET /full-simulation/tasks/{task_id}
GET /run-containers/full-simulation/tasks
```

The last path is global (without the scoped prefix). All return
`full_simulation_tasks.v1` with validated `full_simulation_task_view.v1` rows,
including terminal history. Cross-scope task detail fails closed.

```http
POST /full-simulation/tasks/{task_id}/continue
{"request_id":"recovery-1","action":"recover","expected_revision":4,
 "operator_label":"Admin","audit_reason":"Inspected interrupted task after restart"}
```

`action` is `recover` or `resume`; changed/stale revision, illegal state,
unexpired ownership, terminal parent and read-only/archived scope are rejected.
The original command is never replaced. Existing `/full-simulation/control`,
`/full-simulation/target` and stored terminal summary endpoints remain canonical.

## Verification and boundaries

Focused HTTP tests use production FastAPI over TCP, file-backed SQLite and real
MatchEngine children. They cover quick durable acknowledgement, lost-response
replay, concurrent starts, competing scope exclusion, pause/resume/Stop,
corruption during execution, explicit takeover and stale-owner fencing, manual
checkpoint and unchanged Saved history. React/client tests mock HTTP and prove
CS/EN contracts, exact retries, malformed responses and truthful offline errors.

The dedicated `Full Simulation Server Tasks Browser` workflow runs
`scripts/full_simulation_server_tasks_browser.py`: actual native Run/Players/
Ranking/Entry/Draw/Schedule setup, discarded real POST response, original-page
closure followed by an additional genuine sporting receipt, Task Center return,
safe pause, explicit resume, **SIGKILL** of the active server process, new
process/database handles, no startup execution, rejection before lease expiry,
explicit Czech recovery, real operator checkpoint and safe terminal Stop. It
compares canonical sporting receipts, shared slot snapshots and Saved history
with an uninterrupted server using an identical pre-task SQLite backup and
original command. A test-only writer gate and controlled lease expiry bound the
proof; they do not create outcomes, alter RNG or Save. JSON, screenshots, trace
and process logs are preserved. Existing controls and Saved Group browser gates
remain independent regressions.

This is a bounded lifecycle/recovery slice, not full-season/50-season acceptance
or a pre-alpha release. Instant mid-match pause, event/intra-week targets, richer
metrics, watched events and notifications remain their own Master-aligned work.
Every required final-head CI check must be green before Ready for review.

## Local verified evidence (15 October 2026)

- 49 focused backend tests passed across server tasks, original real HTTP controls,
  frozen summaries, invocation lease and global Task Center; 23 task/final-season
  tests passed in the final boundary pass (17 additional final-season cases,
  66 distinct cases across the selections). The enhanced idle-pause/stale-revision
  case was then verified separately.
- 83 focused React/client tests passed; the final stricter task validator and
  CS/EN task components were repeated successfully (14 tests). These mock HTTP.
- Native Chromium reported `SERVER TASK BROWSER / ACTUAL PROCESS DEATH / RECOVERY /
  EQUIVALENCE PASSED`. The actual closed-page receipt count grew 1 → 2; a safe
  pause/resume committed the third match. SIGKILL/restart/explicit recovery then
  progressed to Week 61 and `season_transition_save_required`. An uninterrupted
  copy reached the same checkpoint with byte-equivalent canonical sporting/slot
  evidence and unchanged Saved history. Safe Stop produced the stored summary.
- TypeScript/Vite production build, backend compile, Ruff on the new Python
  modules and `git diff --check` passed. Existing modified large modules have
  pre-existing lint debt; no claim of repository-wide lint/full-suite acceptance.

Local evidence is in the disposable `work/server-task-browser-4/artifacts/`;
the dedicated workflow recreates and uploads evidence for the reviewed commit.
Final-head required CI outcomes are recorded in the PR before Ready for review.
