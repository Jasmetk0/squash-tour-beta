# Native prospect 15th-birthday v3/v4 lifecycle full-history replay

## Purpose

The production Saved native Tour validator still reconstructs only a legacy
initial-population v2 bootstrap and canonical v3 weekly life states. PR #1554
added pure v4 birth evidence but **did not authorize persisting it**; PR #1555
independently stages Health/sporting population equivalence. Before real birth
activation, a Signed history reader must be able to reconstruct the entire
life timeline rather than trust just a submitted terminal v4 fingerprint.

This slice implements the pure **`verify_calendar_native_birth_history`**
and versioned `calendar_native_birth_replay_proof.v1`:

- Replay from immutable original v2 Week 1, requiring exactly one consecutive
  state for every Run ordinal through the declared current week.
- For every W/O-aware calendar week, recompute the full canonical 15-year-old
  birth event from the caller's **already-authenticated** Saved Run prospect
  source and authoritative World Package. A v3 step may never silently omit
  a due 15th birthday.
- If a successor is v4, require exact equality to the entire reconstructed
  birth event; use the genuine existing lifecycle kernel to derive each
  player's age, retirement status and prior-week Entry.
- Preserve genuine v3 serialization/hashes unchanged; allow a v3 step
  without due birthdays following an earlier v4. A v4 empty-birth event is
  also valid and verifiable. Replay supports horizon extension only when it
  keeps original W, O and start year and never contracts the season horizon.
- Validate the real calendar-owned Tour application evidence: proper
  Run/Branch, unique application IDs, no future-owned-week entries,
  no application before a player's birth or after retirement, distinct
  first-entry tie-break tokens. New birth players are **not** entered/ranked
  at their birthday; an actual valid application during that week first
  affects the following lifecycle week.
- Return one fingerprinted proof binding every lifecycle state hash, every
  v4 birth event hash (explicitly `null` on genuine v3 steps), all actual
  application hashes, the source fingerprint and admitted identities.

All operations are read-only and do not alter the Run, Tour, Admin Working
Draft, SQLite, Save or Viewer.

## Authority boundary

The function **cannot authenticate Signed SQLite or Saved source data by itself**.
Its caller must first verify the exact Saved HEAD and immutable historical
prospect-source version, including Run/Branch/World consistency and the
relevant Tour Entry authority. The current Saved/restore validator does not
yet consume this proof or load v4; the production writer and
`intake_source_requires_native_calendar_materialization` guard are
deliberately unchanged. A future production PR must bind this replay to
the Saved source chain, real sporting/Health checkpoint, ranking, Entry,
transactional writer, restart, fork and corruption rejection before enabling
native activation.

## Coverage

Real W52/O1, W52/O35, W61/O37, W80/O15, W80/O80 boundary transitions,
whole-history birth detection, preservation through empty v4 events, first
application chronological sealing, no-before-birth and no-future Entry,
foreign provenance, rehashed birth forgery, missing v4 birth, distinct
NR tie-break, horizon extension and complete JSON proof replay are tested
as focused `pr_critical` domain cases.
