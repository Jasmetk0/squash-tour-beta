# Frozen Full Simulation terminal summary — 14 October 2026

Baseline `buuk`: `e271ef07` (merge #1468). #1465–1468 are merged; safe Stop,
absolute weekly targets and relative week/season targets already exist. This
candidate adds summary evidence, not duplicate controls or new sporting rules.

## Implemented boundary

New safe Stop and reached-week terminal receipts capture a fingerprinted summary
inside the same SQLite writer transaction as their terminal state. It contains
the immutable original command identity, actual start/end weeks, original and
effective targets/revision, reason, persisted child-command count and Saved
Revision at operation end. Subsequent terminal retries use this frozen Position
instead of the current Branch Position; the endpoint cannot drift after later
work or an explicit Save.

Completed tournaments and champion/finalist IDs come exclusively from validated
canonical/legacy Owned Tournament Ranking Sources whose original adopting
command is reachable through this Full Simulation's persisted child-command
graph. Other Branch tournaments and earlier owners are not reassigned. An
unexecuted child placeholder is not a completed result. Three terminal match
receipts alone do not establish a closed tournament source.

`GET /admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation/full-simulation/parents/{command_id}/summary`
reads stored evidence, validates the parent identity/fingerprint, summary hash,
scope and chronology, and performs no writes. A missing historical summary is
explicitly unavailable; it never substitutes today's Position or sporting data.
Tampered or mismatched data returns HTTP 409. New CS/EN presentation is available
through the original parent's History detail in the exact Run/Branch. Technical
IDs/fingerprints remain unchanged.

## Verification

- 60 focused backend tests pass across summary, Full Simulation HTTP controls,
  lease/commit fencing, final-season boundaries and global Task Center modules.
- New HTTP/SQLite tests execute actual MatchEngine children, validate an owned
  tournament winner, cover both Stop and reached target, confirm a later explicit
  Save and verify unchanged summary/terminal replay with current-Position access
  deliberately forbidden. Wrong Run/Branch, corrupt hash and legacy non-mutation
  are tested. Other existing fixture tests may patch Position; those are not the
  source of this HTTP execution claim.
- 64 focused React/client tests pass (52 existing panel tests and 12 new summary
  presentation/contract tests). These mock the HTTP boundary and prove CS/EN
  presentation, scope/shape validation and unavailable legacy evidence.
- Native Chromium creates a Run, 64 athletes, Entry/Draw/Schedule through real
  Admin forms, pauses/resumes/retargets, executes three real matches and allows
  the canonical tournament source to close before its second pause. It then
  performs real Stop and inspects the stored winner/end in Czech and English.
  Exact summary replay and all existing Saved Revisions remain unchanged.
- Build, backend compilation and diff checks pass locally. All triggered CI
  workflows on the final PR head remain required for merge handoff.

The acceptance-only gate waits before a SQLite writer and observes real group
and source receipts. It does not inject results, alter RNG or become a production
worker. JSON evidence, screenshots and trace are uploaded by the existing
Full Simulation Controls Browser workflow.

## Limits and next PR

This is the frozen summary of safe Stop and weekly-target completion. Older
terminal receipts and final 50-season Run-closure summaries without this captured
evidence stay unavailable. Ranking movement, watched events and notifications
are explicitly unavailable. No significant-event importance policy, unsupported
event target, background worker, active-tab reconnect or full pre-alpha release
is invented. Save stays manual; summary persistence does not publish a revision.

Next: event/intra-week target boundaries or the independent server task lifecycle
and reconnect path, reusing the already versioned target and frozen terminal
evidence. Extend ranking/watched-event summaries only from their actual historical
authorities; do not derive them from the current Branch.
