# Native global Simulation Slots

Implementation candidate; not yet acceptance evidence.

Base: `buuk` `94737b0dab67c38c57682480f66bfae365c3225e`, including
owner-merged #1642. The parallel Draft #1641 owns its listed diagnostic and
historical frontend pages; this change excludes those files and their tests.
Only the owner merges. Auto-merge remains disabled.

## Contract

Newly configured slot Editions use an explicit versioned contract. Existing
Edition, tournament, checkpoint and Tour schemas retain their original meaning,
serialized content, seeds and replay. A common Branch/week authority selects the
nearest unresolved match slot across Editions. One immutable slot-start snapshot
owns all simultaneous match inputs. Accepted match evidence is stored once in the
sporting ledger; tournament awards derive only from a complete actual bracket.

Next Match accepts one independent match in the current slot. Next Slot accepts
only remaining matches in that slot. Stable match identities derive seeds without
iteration position. A partial slot retains its frozen inputs across manual Save,
physical reopen, reviewed restore and independent native fork. Week/Season
Transition and final closure require all due sporting content and explicit result
confirmation. Existing #1642 closing-only results and frozen task targets remain.

Each write keeps the existing reviewed command, idempotency, Saved ancestry,
physical source verification, SQLite writer fence and transaction rollback.
Self-consistent hashes are insufficient source evidence. GET/polling does not
simulate matches. Full Simulation uses the same slot commands and explicit review,
Save and closure boundaries as Admin.

## Version and execution boundary

- `calendar_tournament_edition.v2` adds the immutable authored simulation seed.
  v1 serialization omits it and continues its original sequential executor.
- `calendar_global_slot.v1` stores the shared full sporting snapshot, physical
  predecessor, frozen Health/projections, due identities and canonical accepted
  match evidence. The v13 sporting checkpoint owns these records; the v5 Tour
  retains its authentic immutable pre-upgrade root and reviewed receipts.
- Complete v7 tournament views derive from accepted slot matches. They do not
  apply effects again or grant points to incomplete brackets. Native fork v8
  views additionally retain actual inherited match owners. Runtime v2 is used
  only when the fork has its own global slot ledger; v1 bytes remain unchanged.
- Source matches in an inherited partial slot are referenced by ID through the
  authenticated original Saved source. They are not replayed as new target
  results. New target matches and all subsequent slots use the same slot kernel.
- Next Match's optional `match_id` selects only the nearest unresolved slot.
  Conflicting simultaneous player identities block affected matches and the
  whole-slot action. A valid independent match remains selectable. There is no
  new ban on applications, weekly entry, or disciplinary policy.
- Every complete source proof follows actual SQLite bytes, owners, topology and
  reachability. Bounded caches reuse completed proofs only after that dependency
  graph is freshly authenticated. Exact immutable prefixes and within-walk
  derived proofs avoid repeatedly simulating accepted history. Current live
  bytes are always captured and compared; direct SQL and rollback fences remain.
- Stored completed-Edition receipts are projections of complete actual brackets,
  verified by the command reducer. They feed existing national/season summaries
  and closure boundaries; they are not an independent sporting result store.

## Verification ledger

Pending implementation and focused tests, real HTTP/SQLite and Chromium,
order/retry/restart/restore/fork/corruption/conflict/boundary scenarios, comparative
performance, distinct adversarial review, and relevant executed exact-head CI.
Draft skips are not passes. No MERGE recommendation or pre-alpha completion claim.


Development runs (preceding runtime candidates, not final-head certification):
14 initial Tour contracts; 43 legacy Tour/fork contracts; 59 expanded backend
contracts; five new version/seed/schedule contracts; 36 frontend contracts and
production build. The initial full two-Edition HTTP/SQLite restart/points case
passed. Batch and reversed per-match execution produced exactly equal sporting
checkpoints (214.26 / 302.50 s under concurrent local load); the actual worker
slot/frozen-target scenario passed in 517.31 s. A fork test exposed and corrected
an inherited accepted-match scheduling defect; a concurrent cold-read attempt
hit the unchanged 120 s HTTP limit. These are development failures/corrections,
not hidden passes or reasons to increase timeouts. Full final acceptance remains
pending. New fixtures are genuine isolated production SQLite histories, reused
through SQLite backups; results and required assertions are not mocked or cut.
