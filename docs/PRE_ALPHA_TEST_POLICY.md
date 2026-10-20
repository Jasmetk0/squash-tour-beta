# Pre-alpha test and internal release policy

This file records the current engineering test policy for Squash Engine pre-alpha work.
It is an implementation/development policy, not sporting product canon.

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
