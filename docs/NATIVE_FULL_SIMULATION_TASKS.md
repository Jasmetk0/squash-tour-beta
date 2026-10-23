# Native Full Simulation server tasks (implementation in progress)

Baseline: `buuk` `79affb0e5e8b76d58535d01d50acd5a8ec7577fa`, owner-merged
#1635. One implementation branch/PR; only the owner merges.

The v2 command freezes the authenticated original Saved calendar, source revision,
root seed and explicit target. A weekly target means opening that week; omitting
it requests the original Run's final closure. Extension never updates that intent.
V1 commands, RankingWeek and the legacy execution guards keep their meaning.

The server task worker invokes the existing CalendarTourService (including its
native fork dispatcher). Each sporting child is reviewed and persisted before
execution. Entry/field/draw and result approvals remain manual; every dirty
sporting child waits for a separate manual Save and explicit task continuation.
Task leases, stale-worker fences and the original request/recovery audit remain
the same production control plane. A task inventory uses one SQLite read snapshot.

## Acceptance status

WAIT — implementation and acceptance are in progress. A green Draft skip is not
an executed test. Final closure, native Admin controls, W52/W61/W80 production
scenarios, adversarial recovery/concurrency checks, Chromium and final-head hosted
acceptance must all be completed before recommending merge. This document will
record the executed evidence and remaining supported-scope limits.
