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
3. If the server confirms a Run identity but returns a mismatched reviewed
   calendar, the form blocks a duplicate create and offers a link to inspect
   the existing Run. Uncertain transport errors explicitly advise checking
   the Run inventory before retrying. If the POST response is lost, the
   creation form now blocks another POST and offers an explicit fresh
   `listRunContainers` read for the exact requested name, without using local
   storage or cached listings as authority. A single exact match yields an
   inspection link (not an assertion of who created it). No match unlocks only
   an explicit manual retry, never an automatic retry; an unreadable, malformed
   or ambiguous inventory fails closed. The name remains fixed until that
   reconciliation has succeeded, so editing cannot accidentally bypass it.
   Invalid server-returned Run IDs and malformed unrelated inventory rows are
   rejected too: no guessed link, local identity update or false negative.
4. A best-effort inventory cache invalidation is not allowed to turn a
   server-confirmed Run creation into a false failure and a duplicate retry.
5. If routing itself fails after server-confirmed creation, the form says the
   Run **already exists**, disables repeated creation and links directly to the
   created Run rather than allowing another create.
6. Browser-local recent/last-Run persistence remains optional. The server
   creates the authoritative Run; unavailable storage does not prevent opening it.
7. The Run Home Saved-readiness card prioritizes review/Save of an unsaved
   Working Draft over further apparent missing-Saved setup actions. This is a
   navigation recommendation, **not** a Save, an authorization or a claim that
   all world content must exist before unrelated operations.
8. The preparation phase links to the existing global Test Lab, which does not
   require a Run. This does not create a parallel sporting world or authorize a
   Run operation.
9. An all-optional/all-saved inspection no longer claims that every foundation
   has been saved or that all sporting operations are ready. Each operation
   retains its own preflight and unsupported features stay unsupported.

## Validation boundary

Focused React component regressions exercise rapid double-submit, rejected
inventory refresh, navigation failure/repeated submission after success, unavailable localStorage,
dirty-draft priority, all-optional Saved-inspection wording, and
URL encoding of returned Run identifiers and preparation-only Lab navigation. An uncertain create can be retried **only after** a successful, matching-name
inventory reconciliation with no matching Run. A server-confirmed create cannot
be retried on the same form. The negative inventory result is point-in-time
evidence, not a guarantee about a concurrently completing request. They mock the
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
