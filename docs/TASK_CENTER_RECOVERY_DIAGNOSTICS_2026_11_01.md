# Task Center recovery diagnostics — 1 November 2026

## Motivation

Native Full Simulation can persist a parent operation and separately own a
server-side task. The older global pending-receipt inventory is still shown
on the Task Center page, even when a server task exists for the same command.
A long reference FAX run may need operator intervention at Entry/Result/Season
Transition boundaries after a controlled pause or restart.

This slice adds a compact **read-only triage and local diagnostic export**,
not a new task runner or a new state authority.

## Data provenance and safety

- Reuses the two **existing independently validated** endpoints:
  `getServerTasks()` (durable server task state) and
  `getGlobalFullSimulationOperations()` (legacy pending receipts).
- Exact joins use a tuple of `(run_id, branch_id, parent_command_id)` encoded
  as an array; composite separator-based strings may alias unrelated runs.
  A single match is a documented historical association, not another task;
  two matches are explicitly **ambiguous**. Receipt-only history has no
  fabricated server task.
- Shows saved task state, desired state, checkpoint, last reported position,
  operator-action flag, heartbeat health and task/legacy counts.
- A stale heartbeat is a possible investigation signal, **not proof that a
  worker crashed**. A lease does not establish process liveness or owner
  permission to Resume. Other future/missing heartbeat states are not invented.
- The export contains only bounded identifiers, status/progress metadata,
  task revision, checkpoint, heartbeat, selected receipt associations and
  counts. It **excludes** original commands, original seed/policy snapshots,
  stored task event reasons, raw full progress payloads and user Package data.
  It is produced locally on explicit button click.
- When either query is fetching, failed, or its source contract cannot be
  reconciled, previously cached joined evidence and the download action
  disappear. The detail link always navigates to the exact Run/Branch/task,
  where the real preflight must run again.
- No mutation routes, polling changes, Task Center new endpoints, automatic
  Resume/Stop/Save/retry/worker, new sporting rules or release claims.

## Isolation

Changed only the global Task Center presentation, a new pure projection and
new scoped tests/documentation. It does not overlap open #1710 (Run Home Branch
comparison), #1711 (Edition Entry audit), #1708 (Windows offline backup) or
Jules' independent calendar/cohort/Earth/Labs review tasks. Only the owner
merges.

## Verification boundary

Pure tests exercise exact/foreign/colliding scopes, multi-task ambiguous
parents, state priorities, redaction, zero tasks and corrupt inputs. React
tests cover Czech/English, exact escaped destination URLs, user-controlled
details/JSON export, stale-fetch and corrupt-inventory suppression.
The existing Task Center regression plus Fast CI TypeScript/Vite build
must pass on final PR head. This is **not** a full worker-crash/restart
acceptance or the pre-alpha 50-season release gate.
