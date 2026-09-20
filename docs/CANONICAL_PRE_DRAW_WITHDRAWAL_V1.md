# Canonical Pre-Draw Withdrawal V1

This document records the implemented narrow authority boundary for pre-draw
withdrawals. The canonical product authority remains
`SQUASH_ENGINE_MASTER_VISION.md`, especially the tournament entry/replacement
rules in chapters 15.1 and 15.9.

## Implemented boundary

`CanonicalPreDrawWithdrawalService` owns one SQLite transaction for a pre-draw
withdrawal command scoped to an existing Run / Branch / Tournament Edition field.

The command does **not** choose an arbitrary replacement. It appends a new immutable
`TournamentEntryField` version through `TournamentEntryFieldStore` and therefore
reuses:

- the exact Tournament Ranking Snapshot already adopted for the Edition;
- the exact Tournament Entry/Application payload frozen with the initial field;
- the previous field version as predecessor authority.

A Main-field withdrawal therefore uses the existing canonical field resolver:
the best still-eligible ranking-ordered candidate is promoted into Main and the
Qualification field is backfilled from below its cut. A Qualification withdrawal
backfills Qualification without changing Main when no Main vacancy exists.

## Determinism and replay

The persistence store remains append-only.

- Every new command carries the field fingerprint it was prepared against; if another
  repair has advanced the field first, the stale command fails closed instead of
  silently rebasing itself.
- Command IDs are idempotent.
- Reusing a command ID with different withdrawal input fails closed.
- An exact historical retry keeps using its original predecessor fingerprint and
  remains replayable even after later field versions or Draw Input commitment.
- Frozen application evidence is not re-read from mutable legacy Entry state.
- Every stored field version is replayed against its frozen applications and
  Tournament Ranking Snapshot authority.
- The result exposes predecessor and new field fingerprints plus the actual
  promotion/backfill delta for audit and later Admin presentation.

## Canonical Admin HTTP boundary

The Run/Branch authority is exposed through a separate canonical Admin route family:

- `GET /admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/entry-field`
  returns the current field sequence/fingerprint, Main/Qualification/below-cut
  partitions, withdrawals and whether Draw Input has already locked further repair.
- `POST .../entry-field/pre-draw-withdrawal` accepts the exact
  `CanonicalPreDrawWithdrawalCommand`, including the expected field fingerprint.

The path scope and command scope must match. Validation errors return 422; missing
field reads return 404; stale field identity, scope mismatch and draw-locked mutation
return 409. Exact historical retries retain their existing idempotent behavior.

This is intentionally separate from the legacy `/runs/{run_id}/events/.../pre-draw-withdrawal`
surface, whose identity belongs to the older simulation-run namespace and whose
direct-replacement semantics are not canonical Run/Branch authority.

The canonical command is now exposed in Planned Event under **Canonical Main Draw
preflight**. Admin selects an active Main or Qualification player from the current
Run/Branch field; the client binds the command to the exact current field fingerprint
and the server remains the only rebalance authority.

The legacy simulation-run pre-draw authoring surface is retired. Its GET/POST
`.../pre-draw-withdrawal` endpoints return `410 Gone`, and the old Commissioner
mutation form is no longer rendered. Existing
`.../pre-draw-withdrawal-actions` history remains read-only for old saves and audit.

## Hard boundary

This command is **pre-draw only**. Once `TournamentDrawInputAuthority` is committed,
new repair commands remain blocked by the existing draw lock. Exact historical
command retries remain replayable.

This slice deliberately does not implement:

- Qualification redraw/cascade/freeze phases after a draw exists;
- Lucky Loser ordering or LL slot creation;
- Reserve Wild Card / WC repair;
- per-player first-real-match replacement cutoff;
- Final Commitment / Week Tournament Lock policy;
- migration/retirement of the legacy simulation-run pre-draw endpoint and its UI.

Those remain separate Gate 3 work. The legacy direct-alternate shortcut must stay
non-authoritative and must not be treated as a substitute for this Run-owned field
repair.