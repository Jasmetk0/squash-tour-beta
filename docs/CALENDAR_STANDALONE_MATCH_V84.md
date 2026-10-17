# Calendar-native opening-week MatchEngine and Saved replay (v84)

## Implemented backend boundary

A writable custom Run with a Saved versioned RunCalendar and a Saved
`initial_world_state.v2` now supports one *actual* two-player BO5 MatchEngine
exhibition at Season 1 Week 1. The two participants must be distinct current
Saved population players; no fabricated outcomes or direct Saved re-signing
is permitted. The operation requires a clean Working Draft, exact current
Saved head and source InitialWorld fingerprint. It uses an injected explicit
seed, produces full authoritative rally/timeline/stamina logs, and freezes
the exact participant input/profile/seed, input anchor, source Saved HEAD,
Run W/offset/start/horizon and operator audit metadata.

This is an isolated standalone exhibition, **not** a tournament, official
ranking, point award, full sporting state evolution or a week transition.
Initial population still has only seven compatible player attributes and
no calendar-native active 57-attribute sporting week. The compatibility
projection is explicit, values are clamped to MatchEngine bounds and the
unchanged original player source stays in the Saved InitialWorld. Missing
Health evidence is not inferred as a valid injury state: the operation
refuses already installed sporting/Health/legacy Slot authorities rather
than bypassing them. Until those writers migrate, no supported routine
may convert calendar positions to legacy 61-week ordinals.

## Transaction / history / replay contract

- `POST /admin/runs/{run}/branches/{branch}/authoritative-simulation/calendar-standalone-match/simulate`
  writes a completed, validated match plus exact command identity atomically
  under `BEGIN IMMEDIATE`. A retry of the same command is byte-identical;
  any second match or changed command fails closed.
- `GET .../calendar-standalone-match` exposes current Saved Run/calendar,
  selected players, stored result and whether the immutable Saved head includes
  that result; unsaved playing remains visibly unsaved.
- `GET .../calendar-standalone-match/{match_id}/replay` reruns the real
  deterministic MatchEngine from the immutable frozen input and seed,
  rejecting a result/log mismatch.
- `GET .../calendar-standalone-match/save/preview` produces the current
  match component fingerprint, Saved head and Working Draft version.
- `POST .../calendar-standalone-match/save` uses the existing immutable
  Save machinery with an exact fingerprint and draft-version check, new Saved
  Revision and audit event. The original Signed HEAD is never changed.
- Cold reopen/restart loads the matching SQLite row and signed Saved
  component. Restore preflight registers these owned rows; supported same-
  branch historical restore reinstalls the target match or removes it.
  A fork of a match-containing Saved Revision is **explicitly blocked**
  until native matching roster/input remap and fork-proof exist; a fork from
  an earlier saved revision without a match remains available. That is
  preferable to fabricating valid results for a different branch.
- Old FAX Saved payload schema, hashes, legacy Simulation Slot keys,
  authoritative guard and 61-week ranking implementation are unchanged.

## Acceptance and limits

`tests/api/test_calendar_standalone_match_flow.py` exercises real HTTP,
SQLite, 52-week and 80-week Run clocks, population adoption + manual Save,
actual MatchEngine simulation, exact replay, command idempotency/conflict,
manual match Save, immutable source HEAD and cold restart. This is a
production backend vertical slice, not a browser UI or a full native
sporting tournament. No CS/EN browser path or Week/Season Transition is
claimed. Those must follow once persistent health/sporting week effects,
slot simultaneity, tournament-owned results, point policy and transition
writers share one validated RunCalendar authority.
