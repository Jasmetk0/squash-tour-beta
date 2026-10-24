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

## Verification ledger

Pending implementation and focused tests, real HTTP/SQLite and Chromium,
order/retry/restart/restore/fork/corruption/conflict/boundary scenarios, comparative
performance, distinct adversarial review, and relevant executed exact-head CI.
Draft skips are not passes. No MERGE recommendation or pre-alpha completion claim.
