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

- Command IDs are idempotent.
- Reusing a command ID with different withdrawal input fails closed.
- Frozen application evidence is not re-read from mutable legacy Entry state.
- Every stored field version is replayed against its frozen applications and
  Tournament Ranking Snapshot authority.
- The result exposes predecessor and new field fingerprints plus the actual
  promotion/backfill delta for audit and later Admin presentation.

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
- migration of the legacy Admin pre-draw endpoint/UI onto this command.

Those remain separate Gate 3 work. The legacy direct-alternate shortcut must stay
non-authoritative and must not be treated as a substitute for this Run-owned field
repair.
