# Native groups over the global Simulation Slot ledger

Implementation candidate on `buuk` baseline
`af0e906ce374c3406fb43c29fe65b007546b9303` (27 October 2026).
The owner merged #1643, #1645 and #1644. #1646 is separate; its ranking forms
and read-only candidate components are outside this patch.

## Audited gap and authority

The native CalendarTourEdition path supported Ranked four/eight-player knockout
only. Existing SimulationRun group execution already owned the general format,
seed placement, equal-group topology, circle schedule, standings, explicit tie
cases, crossings and multi-round hybrid bracket. The native adapter reuses those
same domain authorities instead of creating a Finals-only competition engine.
The shared pure phase-point composer serves both legacy and native hybrids.

Master §§15.14–15.15, 16.1–16.3 and 26.1 remain the product authority. Eight
players in two groups are a test configuration, not a universal Finals default.
No complete Finals qualification, pre-alpha or 50-season release is certified.

## Version and storage boundary

* `calendar_tournament_edition.v3` requires `native_group_configuration.v1`.
  Its exact group capacity uses the existing fixed participant Entry geometry.
* Configuration stores the full immutable group rules source, effective season,
  phase BO3/BO5, explicit seeds/crossings and explicit ranking rewards. Unknown
  formats and incomplete/duplicate crossings fail validation.
* `native_group_draw.v1` freezes the existing format, topology and schedule.
  Approval/draw still consume actual validated applications and frozen ranking.
* `calendar_global_slot.v2` holds new frozen group match contracts with their
  Effective Match Format Snapshots and audited tie decision records. Its actual
  played matches use `calendar_continuation_match.v3`; old v1/v2 remain BO5.
* Group standings v3 opt into the Master-decided RET exception using an explicit
  retirement receipt: maximum group points, zero loser points and no ratio data
  from the incomplete match. Its played result/rallies remain in the ledger.
  The older standings/receipt path continues to reject RET.
* The existing v13 checkpoint/v5 Tour containers retain explicit historical
  roots and their normal independent command replay and physical source gates.
  No old Edition, seed, receipt, source hash or Saved history is rewritten.

A completed `calendar_group_tournament_result.v1` is a derived view of the actual
slot ledger. It carries standings, winner-fed bracket and one prepared award per
player. Group table points are separate from Official rewards. Group-win and
knockout components compose into one Edition result for Best N. Multiple pure
groups have group winners and no single Edition champion.

## Simultaneity, decisions and recovery

The nearest slot freezes every due Edition from one pre-slot player/Health
snapshot. Partial Next Match, manual Save and restart retain that snapshot and
all remaining match inputs. MatchEngine generates actual played results.

The shared standings authority applies wins, table points, two-player H2H and
exact all-group game/ball ratios. A persistent tie is visible in inspection and
blocks dependent advancement. `resolve-group-tie` validates the exact current
case and explicit full order, stores operator/reason/command evidence, and is
independently replayed. It cannot use a player-ID, Race or random fallback.

Forks retain source-owned authorities and accepted source matches. New target
matches/decisions use the target branch and the existing source/owner/lineage
proofs. Manual Save retains the original before/staged/installed/commit gates.
Native Full Simulation calls the same slot commands, preserves its parent and
frozen target, stops for Entry/tie/result review and manual Save, and resumes only
through the existing explicit Continue workflow.

## Evidence so far (not final-head acceptance)

* Real HTTP/SQLite: two groups of four, 12 group matches, semifinals/final,
  partial Save, physical restart, exact retry, result confirmation and next-week
  Official points: passed (231.15 seconds).
* Real HTTP/SQLite: stale/foreign source rejection, late-write rollback, exact
  retry, rehashed coupled scheduled-seed forgery rejection and recovery: passed
  (140.83 seconds).
* 39 focused version/group/slot contracts passed; 42 shared hybrid/pure-group
  policy and native contracts passed. These are domain/application evidence,
  not a substitute for real HTTP/browser acceptance.
* Four-group, pure-group, nested fork/restore/worker and Chromium scenarios are
  under verification. A previous fork run found an event-filtering bug; the fix
  is being rechecked. Early browser attempts failed because the harness selected
  a port outside the existing backend CORS origins; the standard port is used.

## Outstanding acceptance and boundaries

Do not present this Draft as merge-ready. Final-head W52/W61/W80 native group
acceptance, actual Chromium creation/playoff/results/Save/restart, simultaneity
across group and original knockout Editions, native forks/worker/recovery and all
existing relevant acceptance workflows must actually pass. Existing reference
1,000-player fixtures, assertions and deadlines remain unchanged.

The legacy W/O authority and the new RET receipt preserve decided table semantics.
A native withdrawal/W/O authoring path still needs explicit end-to-end evidence;
no fabricated score/rally is substituted for it. DQ/ABN/Default group effects are
not invented and block the affected standings operation. A genuine exact tie
under native production seeding still needs HTTP/worker/browser evidence; older
real MatchEngine cyclic-tie authority tests do not certify that native scenario.

Only the owner merges. Never enable auto-merge.

## Recovery checkpoint — 27 October 2026

The local workspace was pruned before the previous continuation was pushed.
This continuation reconstructs and tests the hybrid tie scheduling barrier and
strict JSON order decoding. An unresolved hybrid tie reserves its first playoff
slot, preventing execution of a later slot with future sporting input. Earlier
independent slots remain available; pure groups reserve no nonexistent playoff.
Admin displays the blocker and disables slot execution until explicit resolution.

Fresh focused backend validation: 30 tests passed, including seven new boundary
contracts. These use synthetic/mocked dependencies and are not native seeded tie
HTTP acceptance. Prior local fork/worker logs and unpushed delayed-fork metadata
and mixed-format recovery tests were lost; they are not claimed as final-head
passes. Reconstruct the delayed-fork metadata update and genuine mixed-format
restart/order acceptance next. All outstanding acceptance above still applies.

The delayed-fork metadata update is now reconstructed. Resolving a tie for an
owned earlier slot updates that slot in place and preserves player state,
accepted matches, subsequent slots and the source branch. The adapter rejects
changes to any other slot field, removed matches, duplicate appended decisions
and invalid indices. Thirty-one focused backend contracts pass. The genuine
nested-fork HTTP/SQLite scenario passed (321.62 seconds including setup).

## Additional genuine acceptance — 27 October 2026

The mixed group/knockout scenario passes (211.14 seconds): twelve real players,
six simultaneous actual MatchEngine matches, full-slot execution versus reverse
individual execution, manual partial Save and complete application/SQLite reopen.
The two resulting complete sporting checkpoints compare equal, including all
accepted matches, rally evidence, frozen inputs and physical player state.
This is one W52 mixed-slot acceptance, not the full W52/W61/W80 matrix.

The nested-fork case independently passes with actual two-level branching,
fifteen-match completion, result confirmation, Official points, unchanged source
and partial-source restoration. Thirty-nine mocked frontend tests pass, including
CS/EN disabled simulation controls while a group tie awaits explicit review.
Native production-seeded exact ties, withdrawal/W/O and the remaining full
calendar/browser/worker acceptance are still outstanding. Draft remains Draft.
