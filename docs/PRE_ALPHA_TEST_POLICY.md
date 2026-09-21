# Pre-alpha test and internal release policy

This file records the current engineering test policy for Squash Engine pre-alpha work.
It is an implementation/development policy, not sporting product canon.

## Pull-request development

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

- Official Run full-season continuity through Season Transition into next Season Week 1;
- empty Run -> two manual players -> one standalone match;
- save/reopen/replay integrity required by those flows;
- the complete regression suite, not only PR-selected tests.

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
