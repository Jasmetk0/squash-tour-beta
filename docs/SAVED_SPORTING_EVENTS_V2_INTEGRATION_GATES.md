# Saved sporting events: gates for any real v2 integration

**Status:** design checklist only, 16 November 2026. This document does NOT authorize a production schema change. The experimental store in PR #1821 is disconnected from real Run Save/Reader; its SQLite numbers are a structural possibility, not a product performance claim.

## Observed baseline

- Source: original 256-player W12 native Tour, 8 completed real four-player Editions, 24 MatchEngine matches, physical SQLite from run `43919075227`, SHA-256 `17d8bae0e69e08457cb3ba2d76da813b6a2a684da76eb96ab39fb0ae51ab78e7`.
- 46 independent original Saved Revision hashes were recomputed.
- Across 39 physical v13 `calendar_player_sporting_checkpoint.state.events` arrays: 566,039,006 total JSON bytes; exactly 15 immutable event objects totaling 39,026,296 bytes plus 28,973 bytes of owner-scoped prototype manifests, or 93.10% fewer **event-list text bytes only**. Exactly 39/39 original arrays were rebuilt; 38/38 adjacent lists happen to have an unchanged previous prefix on this Run.
- Different evidence: Claude's #1805 Merkle whole-payload prototype tested native-fork histories, and ChatGPT's #1811 covers other native-fork append-only streams. They must not be treated as competing active production schemas. Keep a *single* reviewed format owner.

## Authority invariant

A revision must be authenticated against actual physical Run/Branch owner, parent, sequence, status, content hash and *all source dependencies*, not an `event_sha256` or `manifest_sha256` printed by an untrusted record itself.

- A private hash against itself is a corruption detector **only while its expected digest is authenticated elsewhere**. If an adversary rewrites an event and the manifest's self-hash consistently, those bytes must not become an authoritative Saved source. The current prototype requires externally verified target full Saved hash **and** target canonical events-array hash; predecessor append requires the corresponding two independently verified original digests.
- **Remaining gap before production:** Every ancestor manifest must also be committed by an independently verified original physical Saved row or by a parent-root commitment in a versioned Signed Saved envelope. Checking only the current and immediate predecessor is NOT sufficient in a mixed or tampered historical chain.
- Exact order, number and canonical bytes of event arrays must be committed. A forged array that merely contains plausible match outcomes is unacceptable. Physical reads must rehash reachable actual node bytes after any warm read; no declared digest, cache hit or unrelated process can authorize a value.
- Owners: specify Run-scoped vs Branch-scoped nodes, fork inheritance and the reachable source-graph proof explicitly. A child Branch must not be able to import an event from a foreign Run or an unreachable history even if its SHA-256 value coincides.

## Incremental migration gates

1. **Freeze design with Work / Claude:** choose a single versioned v2 envelope and node type (consistent with #1805); decide whether `events` use generic Merkle list nodes or a linked append journal. Reject any PR that silently overwrites existing v1 bytes.
2. **Version flag:** only explicitly enabled newly created Runs write v2; v1 Runs keep existing read/write rules until a reviewed migration. No auto-re-signing old Save hashes.
3. **Strict writer:** derive accepted event append from authorized MatchEngine and WeekTransition commands, not a client-provided `new_items` assertion. If a legitimate restart/restore/edit rewrites the prefix, fail closed and use an explicitly reviewed full-snapshot or copy-on-write fallback; never discard results.
4. **SQLite authority:** insert new nodes, versioned root, Saver audit event and branch-head pointer in the same transaction. Inject failure after each write phase and verify complete rollback, no dangling roots. Concurrency: one Winner for simultaneous Save; conflicting Expected Saved HEAD must raise 409. No read of uncommitted foreign nodes.
5. **Reader:** verify actual roots, reachable node bytes, owner and ancestry in one consistent SQLite read snapshot; prove hashes of reconstructed sporting state before semantic replay. Maintain protections against missing, changed, duplicate, non-canonical, cyclic, foreign Run/Branch and not-yet-committed node graphs. Reject physical mutation after successful warm read.
6. **Interoperability:** mixed v1/v2 chain, merge-like restore, Branch fork, season extension, export/archive, cross-Run Saved comparisons, explicit Save, cold restart, historical read and user-owned existing Saved data must round-trip identically.
7. **Proof of no sporting regression:** the same seed, Calendar, admissions, draws, 24 real global-slot matches, ranking points, confirmations and week/season transitions must yield identical externally visible sporting DTOs, event SHA-256, determinism and user access control between v1 and v2 (except genuinely versioned internal Saved identifiers).
8. **Quantify before claiming speed:** A-B-B-A fresh-process runs on identical real SQLite W12 and W52 at multiple history depths, measuring cold/warm history reads, Save, preview, execute, RSS, SQLite file and true node/revision payload bytes. Isolated 93.1% event-text savings is NOT full database size; a prototype `append` speedup is NOT a production week speedup. Explicitly report runner CPU, total wall, repeated samples, instrumented vs uninstrumented and test coverage.
9. **Long-haul gate:** complete 52-week, multiple-season real native history with restarts and tamper mutations, followed by a larger 1,000+ player scenario. The requested 16–128/Q World Championship schedule in #1820 is still capability-gated and is **not** a completed full-scale test.

## Ownership and merge

- Work coordinates and validates architectural compatibility; Claude's #1803/#1805 and our #1811/#1819/#1821 changes should not be blindly combined.
- All diagnostic/prototype PRs remain Draft unless explicitly selected, tested and approved.
- Radim alone decides and performs merges into `buuk`.
