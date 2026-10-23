# Native Full Simulation server tasks

Baseline: `buuk` `79affb0e5e8b76d58535d01d50acd5a8ec7577fa`, owner-merged
#1635. One implementation branch and PR #1637; only the owner merges.

## Versioned execution boundary

`authoritative_full_simulation_command.v2` freezes the actual original Saved
calendar, source revision, root seed and target. The complete original preview
binds that source's content hash to the immutable command's preview fingerprint.
A weekly target means opening the selected week; omitting it requests the
original Run's final closure. A later horizon Save, fork, restore or Branch
movement cannot replace those bytes or extend/restart a terminal task.
V1 commands, RankingWeek, legacy final closure and precise v1 selectors retain
their original meaning. Native weekly/end targets have no legacy 61/50 bound.

The original durable task envelope remains v1, with the versioned command inside
it. Start/retry, audited continuation, singleton invocation lease, heartbeat,
claim validation, pre/post writer-lock fencing and final commit fencing use the
same production control plane. A server restart never scans/enqueues old work.
Recovery/continuation is an explicit POST against the same task and original
command. A child is durably reviewed before the real sporting call. Exact retry
uses the same request/seed; actual receipts authenticate the child audit chain.
Native v2 parent metadata is excluded from legacy sporting snapshot capture and
restore. Terminal controls survive an actual original/native-fork restore and
Run horizon Save unchanged; pending native tasks explicitly block sporting
restore until the operator stops them. V1 snapshot semantics stay unchanged.

The native adapter calls CalendarTourService and its existing public native fork
dispatcher. They own Entry, MatchEngine, slot inputs, results/points, development,
Health, lifecycle, ranking and transition persistence. No FAX calendar conversion,
new calibration, accepted result JSON insertion or detached runner is involved.
Disjoint approved fields retain the existing simultaneous input rules.

## Manual boundaries

- Start requires a clean, fully Saved initialized native Tour/sporting population.
  Admin reviews the native clock/source/target, then separately confirms Start.
- Missing applications, approved field/draw and result confirmation wait for the
  actual operator. The worker does not create or approve them.
- Every dirty sporting child waits for a separate manual Save and explicit
  continuation of the same task. Save itself never enqueues work.
- At Week W, a Season Transition waits for separate review/approval of its exact
  pending child. Its outgoing Closing Ranking/summary and original Saved source
  are retained in the child audit before the production transition executes.
  Approval itself does not continue or Save the task.
- Final closure has three separate actions: read review, explicit approval, and
  manual final Save. The immutable Saved revision contains a Branch-scoped native
  closure marker, outgoing Closing Ranking and season summary. Source facts are
  independently recomputed from actual immutable ancestry on Saved validation.
  Run status becomes Completed atomically with this Save. No development,
  lifecycle intake, new week/season or Official publication beyond the horizon
  is fabricated. Explicit task continuation reconciles the Saved closure as
  `complete`; opening a selected weekly target is instead `target_reached`.

Pause, stop, awaiting operator, recoverable, target reached and actual completion
remain separate states. A safe stop preserves committed sport. Native terminal
summaries retain their endpoint/source; current Branch position never substitutes
for a historical endpoint. The Admin provides CS/EN native controls and handoff
to the exact native Tour/Branch, plus the original-clock task labels.

## Read and integrity boundary

Task inventory uses one actual SQLite read snapshot. The original immutable Saved
clock and original reviewed content hash are authenticated. Native progress is a
hash/scope-checked projection of the actual sporting/Tour or native Working Draft
aggregate and its receipts. It does not run MatchEngine, repair data, renew a
lease, approve a child or grant writer readiness. Full production source replay
and physical dependency checks still run at sporting/Save authorities. Original
v1 slot/group counters retain their original meaning; native match counters are
separate and identify their source fingerprint.
Sporting, Tour and native-fork component hashes retain their existing canonical
UTF-8 serialization; parent/task/terminal-summary fingerprints retain their own
historical serialization. Czech audit labels and Unicode command IDs exercise
both contracts through actual execution and SQLite reopen, without rewriting data.

An independent native Branch aggregate is explicitly rejected by legacy sporting
and Full Simulation writers, even if W/offset/start/horizon numerically equal
reference FAX. Existing v1 historical execution remains available unchanged.

## Current supported scope and limits

Supported initialized native Tour authorities use their own positive W, offset,
start year and saved horizon, including independent native fork aggregates.
The existing production Tour formats, point policies and Health constraints
still apply; this does not add new tournament formats or realism models.

A native Edition in the original final Run week still needs a dedicated
closing-only result source adapter. Such a task stops explicitly; it never skips
the Edition or creates an out-of-horizon publication. The complete short Run
acceptance therefore uses a valid final week without an unresolved Edition.
Native precise slot/round/Edition retargeting and initial-world preparation are
not advertised by this v2 interface; the existing legacy controls keep their
own supported scope. Unsupported Health healing/permanent effects and source
activation combinations remain blocked by their existing authorities.

## Verification ledger

WAIT — the single PR is still undergoing acceptance. Candidate local
results already executed (earlier source-tree states; not final-head claims):

| Evidence | Executed result |
| --- | --- |
| Actual native task Week/Save/target/SQLite restart and exact start retry | 1 passed, 50.09 s initially; expanded core repeated later |
| Actual short native Run-end approval/manual Save, late rollback, restart | 1 passed, 93.27 s initially |
| Real rollback, loss after child commit, exact recovery, concurrent/stale worker | 1 passed, 82.57 s initially |
| Actual short sporting season, worker matches/points and real rollover | 1 passed, 403.56 s |
| Separate seasonal review, safe pause, no silent approval and SQLite restart | 1 passed, 127.54 s |
| Expanded native target/closure/recovery core | 3 passed, 238.40 s |
| Preserved actual legacy task/control/lease/summary regressions | 14 passed, 123.40 s |
| Repeated legacy regressions after native metadata separation | 14 passed, 112.91 s |
| Actual native fork, horizon Save, both restores, independent continuation, source rehash rejection and restart | 1 passed, 116.12 s |
| Consolidated native HTTP/SQLite target, final closure, recovery, seasonal approval and fork/horizon/restore | 5 passed, about 428.4 s |
| Final candidate legacy task/lease/summary regressions | 14 passed, 69.97 s |
| Actual legacy precise-boundary Chromium, process death, CS/EN and frozen summaries | passed locally; two earlier hosted duplicate-GET attempts failed with ECONNRESET and are not counted as passes |
| Legacy boundary Chromium using the actual Admin review response, with all sporting assertions preserved | passed locally, 134.90 s; latest-head hosted rerun required |
| Rehashed unsupported Tour version, read non-mutation, target Save and restart regression | 1 passed, 46.94 s |
| Czech audit / Unicode task ID, actual original and native-fork execution, summary, Save/restore/horizon/restart | 2 passed, 117.38 s; pre-fix mismatch reproduced through real HTTP and retained as failed evidence |
| Closing Ranking unit contracts plus original task-calendar regressions | 18 passed, 2.33 s |
| Focused existing/new frontend contracts | 121 passed, 7.81 s (five files; API mocks/component contracts, not sporting integration) |
| Native seed/action/audit integrity, Closing Ranking and original calendar contracts | 35 passed, 7.23 s |
| Actual Chromium reviewed Start, three matches/points, manual approvals/Saves, final closure and physical SQLite reopen | passed; local evidence in `work/native-browser-6/evidence.json` |
| Production frontend build | passed |

The finalized W52/W61/W80 matrix walks every actual week using small isolated
production fixtures; a genuine late-season four-player tournament proves matches,
points, rollover, original source preservation and cold SQLite restart. A separate
matrix artifact preserves each actual SQLite fixture, including failed runs. The
short original-Branch case and actual native fork/extension/independent-continuation
case cover the two writer authorities. The real Chromium script performs reviewed
Start, three MatchEngine matches, result approval, manual Saves, final closure and
cold restart without mocking API responses.

Those longer cases and the relevant latest-head hosted gates must actually pass
before recommending merge. The dedicated workflow watches every new runtime,
shared authority and Admin/helper path. Draft skips never count as a pass. Failed
or interrupted development attempts remain visible in local logs; they are not
reported as successful evidence. Full release/50-season acceptance is a separate
repository release gate, not silently substituted for this task's acceptance.

## Distinct adversarial review

The post-implementation pass traced the actual writer fences, uncertain child
commit/recovery, ordinary and native restore paths, horizon extension, terminal
summaries and final closure ancestry. It found and corrected two additional
boundaries: a target cannot settle before its separate manual Save, and every
persisted/pending child must preserve the original parent's derived seed, audit
identity and allowed sporting action. An idle stop must also settle the task
ledger, not merely its parent. Unicode review also found and corrected a mixed
JSON hash contract in progress and terminal-summary reads; actual Czech-audit
original/fork regressions first reproduced the error and then passed. Focused
regressions exercise those cases; final
hosted evidence remains required above. Parallel World Package files and the
Master remain untouched.

The legacy boundary browser captures and checks the actual target-review response
triggered by its UI button, rather than issuing a duplicate synchronous GET through
the separate API context after process death/restart. It retains every sporting,
target, CS/EN, Saved and recovery assertion, and records unexpected backend exits.
No HTTP failure/status or sporting assertion is retried or suppressed by this change.
