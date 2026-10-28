# Pre-alpha Run creation and Saved-preparation guidance

## Scope and authority

Master v85 §31.38 and `AGENTS.md` govern this small Run-setup slice.
Creating a Run requires only its unique display name. Optional calendar/range
review remains explicit and independent of Package selection. This slice does
not add a generator, a second readiness authority or a hidden Save.

## Changes

1. The create form synchronously fences overlapping submit events as well as
   disabling its submit control during the request. Only one authoritative
   `createEmptyRunContainer` command is sent for the same in-flight submission.
2. The returned Run ID, name, ownership and (when requested) calendar are checked
   before any navigation or local navigation hints are written.
3. A best-effort inventory cache invalidation is not allowed to turn a
   server-confirmed Run creation into a false failure and a duplicate retry.
4. If routing itself fails after server-confirmed creation, the form says the
   Run **already exists** and directs the operator to find it in Runs rather
   than attempting a second create.
5. Browser-local recent/last-Run persistence remains optional. The server
   creates the authoritative Run; unavailable storage does not prevent opening it.
6. The Run Home Saved-readiness card prioritizes review/Save of an unsaved
   Working Draft over further apparent missing-Saved setup actions. This is a
   navigation recommendation, **not** a Save, an authorization or a claim that
   all world content must exist before unrelated operations.
7. An all-optional/all-saved inspection no longer claims that every foundation
   has been saved or that all sporting operations are ready. Each operation
   retains its own preflight and unsupported features stay unsupported.

## Validation boundary

Focused React component regressions exercise rapid double-submit, rejected
inventory refresh, navigation failure after success, unavailable localStorage,
dirty-draft priority and all-optional Saved-inspection wording. They mock the
API boundary and are **not** production HTTP/SQLite or real-browser acceptance.

The relevant frontend test/build and final-head hosted checks must complete
successfully before the owner considers merging. Draft skips do not count as
passes. The full Master §31 pre-alpha release gates (including real FAX
50-season and 1,000-player acceptance) are unchanged.

## Parallel-work exclusion

As inspected on 28 October 2026, open PRs #1647, #1648, #1649 reserve native
groups/global slots, Saved Tour/player explorer and Admin Diagnostics
respectively. This slice modifies none of their tracked paths. All changes
are on one independent branch; only the project owner merges.
