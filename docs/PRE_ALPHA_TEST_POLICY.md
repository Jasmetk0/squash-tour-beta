# Pre-alpha test and internal release policy

This file records the current engineering test policy for Squash Engine pre-alpha work.
It is an implementation/development policy, not sporting product canon.

## Historical Run-to-Lab copies — 22 October 2026

Changes to the historical Lab adapter, Player Session boundary or historical
source controls require the additional `Historical native Run copies / three
Labs / real HTTP Chromium restart` Ready/manual job. It runs actual reachable
source/dependency rejection and all three Lab APIs, then real Admin source
selection, a born native W52 player, delayed import delivery, independent Session
Save, SQLite reopen and exact replay. One immutable production fixture is reused
through isolated SQLite backups; proof validations and negative checks remain.
This complements the existing Lab workflow gate and relevant native/Saved gates.
As elsewhere, final evidence must match the final head; Draft skips are not passes.

## Isolated Lab workflow acceptance — 22 October 2026

The scoped `Test Lab Session and Run Proposal Browser` Ready/manual workflow
runs genuine Match, Tournament and Player Lab calculations, persistent sessions,
a concurrent second session writer, delayed delivery of a real Save response,
non-Lab SQLite isolation, a separately reviewed Lab-to-Run proposal, normal Save
and physical database reopen. It fabricates no API result. Focused frontend tests
cover delayed replies, lost sessions, reload consent, exact uncertain-command
retry and blocked duplicate in-flight calculations. Existing Lab API/application
regressions retain real transaction rollback and immutable Saved assertions.
This gate does not replace relevant Run/native fork/browser acceptance, and its
Draft skip never counts as an executed pass.

## Native fork iteration and unrelated catalog work — 21 October 2026

The real public native fork scenario runs in its own parallel Ready/manual job,
including birth, actual MatchEngine, independent Saved histories, points,
restore/restart, nested forks, Viewer and strict extension. Fast CI also includes
the small v2 format guards. Neither replaces existing original-source and native
Tour acceptance; skipped Draft gates remain non-passes.

Run overview defers the large global World source catalog until the Admin uses
that selector. The dedicated Package setup still loads it normally. Browser
scenarios that actually copy a World source focus that selector before selection;
Branch-only navigation no longer triggers unrelated Earth catalog computation.
The registry also reuses its one freshly validated country config when computing
that same response's semantic fingerprint. There is no cross-request country
cache or change to fingerprint values. Browser shutdown explicitly drains its
real API thread and reports a bounded teardown failure instead of leaving native
work running during interpreter destruction.

## Native Full Simulation task acceptance — 23 October 2026

Native v2 task changes require `Pre-alpha Native Full Simulation`: real HTTP/SQLite
control, final-closure, recovery, independent fork/horizon/restore scenarios; the
short/W52/W61/W80 complete week-to-season matrix with actual MatchEngine/points;
and the genuine Chromium Admin flow. Unit DTO/ranking/client contracts are separate
evidence. Every new native runtime/helper is watched by that workflow. Its Draft
skips do not count as passes. Shared legacy control/persistence changes also retain
their existing FAX task/browser and native Tour/Save acceptance gates.

## Draft feedback and review acceptance — 21 October 2026

During implementation, keep the PR in Draft. Fast CI and CodeQL still run on
each applicable push. The dedicated pre-alpha API/browser and Earth acceptance
jobs defer expensive execution while the PR is Draft; their skipped checks are
**not integration evidence and do not permit merge**. Local focused tests remain
required for changed behavior.

Marking the PR Ready for review triggers `ready_for_review` on every relevant
acceptance workflow. The existing path filters, scenarios, negative checks,
timeouts and artifacts remain unchanged. Subsequent commits to a ready PR run
those gates again. Manual `workflow_dispatch` always executes acceptance, even
on a Draft branch. Before merge, inspect the latest SHA and require all relevant
acceptance jobs to have actually executed successfully; Draft skips never satisfy
that gate. Full release/checkpoint regression remains mandatory separately.

Batch changes and local fixes before publishing a stable review candidate. Do
not toggle Draft merely to hide a failure, bypass branch protection, or cancel
a required final acceptance. Configuration-only or documentation-only follow-up
commits still follow the latest-head rule; prepare their evidence before pushing.

Explicit test-file commands in PR automation must bypass the changed-module
collection filter for that process, using the existing acceptance event convention.
Otherwise an unchanged requested file can be deselected and pytest exits with 5.

### Separate shell contracts from population scale

The Shell browser uses 64 real players for navigation, Health, original matches,
points, horizon extension and Save/replay contracts. Its existing assertions and
real production stack remain; only the fixture cardinality is parameterized. The
separate large-cohort browser still verifies 1,000 actual players, Adopt/Save,
ranking and restart, and the native W80 browser still uses 1,000 players. Neither
large-population gate is removed or made optional for its relevant ready PRs.

For an internal release/checkpoint, also run the complete Shell scenario with
`--population-size 1000`. This is available directly alongside the 64-player
iteration mode; it is not a claimed 1,000-player pass when only 64 executed.

## Native Tour long-running acceptance gate

The production HTTP/SQLite configured-Tour scenario runs in the dedicated
`Pre-alpha Native Tour API Acceptance` workflow, in parallel with Fast CI,
when the native Tour, Saved restore, persistence, relevant player/ranking domain,
API or test code changes. It includes two real tournaments, Manual Save,
extension, atomic rollback, replay, restart, historical restore and corruption
rejection. The test remains part of the Full Test Suite.

This acceptance is **not optional** for relevant PRs: neither green Fast CI nor
the native Chromium browser matrix substitutes for a failed/pending native Tour
API acceptance. Never remove its negative checks or declare a PR merge-ready
until all three relevant gates are green on the *same latest commit*.
Unlike the HTTP acceptance workflow, Fast CI's `pr_critical` selector must
exclude this full 20+ minute production lifecycle scenario, so fast feedback
does not wait for a second serial execution of the same expensive flow.

## Native post-admission competition acceptance

Changes to native post-admission competition also require all three real
HTTP/SQLite cases in `test_calendar_native_post_intake_tour.py` (Earth, FAX,
extended) and `native_post_intake_tour_browser_acceptance.py` with real Chromium.
The dedicated jobs pass their own process-level acceptance event so the ordinary
changed-module PR filter cannot deselect an unchanged mandatory case. They do
not replace the original full native Tour/season API, birth cases or browser
matrix. Fast CI stays focused; no 50-season release suite is added to ordinary PRs.

## Pull-request development

### Confirmed native birth acceptance

Changes to the coupled native birth/Tour writer also require the dedicated
`Native birth Week/Season` HTTP/SQLite matrix in the native Tour API workflow.
Earth, FAX, extended W80, short-year Season boundary and real pre-birth Edition
Entry/award scenarios run independently in parallel. This is mandatory alongside
the original native Tour/season/browser gates, not their replacement. The birth
module is `smoke`, excluded from Fast CI's tiny `pr_critical` selection, but remains
in both its dedicated production gate and the Full Test Suite. Do not weaken
rollback, Signed replay, Viewer isolation, restart, restore or corruption checks.
Native runtime capability changes additionally run their real HTTP readiness
scenario and the separate `Native birth readiness / real Chromium` gate. This
must execute against the actual backend; mocked UI tests/build do not replace it.

### Isolated native Tour API-client edits

Six legacy hybrid/Full Simulation browser workflows also watch the shared
`web/src/api/client.ts`. A native Tour wrapper edit formerly triggered all six,
even when no legacy hybrid execution path changed. Their bounded selector now
uses the TypeScript parser and the actual PR base/tested Git tree to recognize
only isolated `inspect/preview/execute/saveCalendarTour*` function declarations.
Every shared client declaration must be unchanged. Production consumers in both
trees must preserve the native page's exclusive use; namespace/dynamic consumers,
extra subsystem changes, missing Git evidence or unfamiliar syntax run the full
browser. Manual dispatch and selector/workflow/dependency edits also run it.

These are **scoped-out unrelated scenarios**, not evidence that their browser
tests executed. Every decision records its reason and compared commits in the
workflow summary. The original commands, assertions, timeouts and artifact uploads
remain in place when selected. The native Tour API, season API and W52/W61/W80
browser workflows are outside this exception and remain mandatory as before.
See [implementation and measured scope](CI_NATIVE_TOUR_BROWSER_SCOPE.md).

During ordinary pre-alpha construction:

- run only the tests that are relevant to the code changed by the pull request;
- keep Fast CI short enough to remain useful as merge feedback;
- long, unrelated or already-proven regression tests may stay hidden from automatic PR CI;
- a PR must not be presented as merge-ready while any test that is required for that PR is red;
- adding a new focused test for the changed behavior is preferred over re-running the entire historical suite.

The repository currently enforces the backend part of this rule by selecting backend test
modules changed by the PR. The complete `Full Test Suite` workflow is manual-only.

"Hidden" does not mean deleted. Deferred tests remain in the repository as regression
coverage and can still be run explicitly when a change touches their behavior.

## Internal release / checkpoint

Whenever we deliberately declare an internal build to be an official project version
(for example a pre-alpha checkpoint/release), the narrow PR policy is suspended for the
release gate.

Before that version is accepted:

1. run the complete backend regression suite;
2. run the complete frontend test/build gate that applies to the version;
3. run the mandatory end-to-end acceptance flows from Master §31.3;
4. include any explicit smoke/performance/recovery checks assigned to that release;
5. do not call the version released while required checks are red.

This is intentionally different from everyday PR development: broad regression cost is
paid around explicit release/checkpoint boundaries rather than on every small merge.

## Current pre-alpha release gate

The first pre-alpha release gate must at minimum include:

- an editable copy of the versioned FAX reference template completing a full season through Season Transition into next Season Week 1; do not mutate protected built-in/Official sources;
- empty Run -> two manual players -> one standalone match;
- save/reopen/replay integrity required by those flows;
- the complete regression suite, not only PR-selected tests;
- the preserved 50-season FAX reference acceptance and the Run-calendar/extension compatibility acceptance assigned by Master §§31.28 and 31.37. The reference 50 × 61 configuration is not a universal Run limit.

Future release-specific checks may be added without changing this basic policy.


## Hard rule for sharing PRs with the user

A pull request must **not** be sent to the user as ready to review/merge, and its link
must not be surfaced as the next merge action, until every required check for that PR
has completed successfully.

Concretely:

- queued or in-progress required checks are not green;
- any failed, cancelled or timed-out required check blocks sharing the PR for merge;
- after a fix, verify the checks on the **latest PR head commit**, not an older run;
- only when all required checks on that latest head are green may the PR be presented
  to the user as ready to merge.

The assistant may continue repairing the PR privately while checks are red. The user
should only receive the PR as a mergeable handoff after this green-only gate is met.
