# Saved v2 storage — one production path (Draft, 17 November 2026)

Status: **implemented behind an explicit, default-off opt-in for NEW Runs**; not
merged, not approved. Draft PR #1827. Implements the unified direction of the #1823 ADR candidate
(one Run-scoped content-addressed Merkle representation) on `buuk` `f82bd81`
(after #1826). It is the only v2 writer/reader; the #1805/#1811/#1821 prototypes
and their tables are not used by production.

## What changes and what does not

| Area | v1 Runs (all existing history) | Saved v2 Runs |
| --- | --- | --- |
| Opt-in | none — unchanged default | `BETA_ENGINE_NEW_RUN_SAVED_STORAGE=saved_v2` (or `DatabaseSettings.new_run_saved_storage`) when the Run is CREATED; recorded once in insert-only `run_saved_storage_formats` |
| `branch_saved_revisions` row | unchanged bytes and code path | identical identity fields, `content_hash`, `change_summary_json`; `payload_json` stores a ~150-byte envelope `{"saved_v2":{"chars","format","root","run_id"}}` |
| Logical payload text | stored inline | materialized from `saved_revision_nodes`; byte-identical to the text the writer supplied |
| Content hash / revision IDs / seeds / fingerprints | unchanged | **unchanged definition** — computed over the same logical text |
| Readers and validation gates | unchanged | unchanged: every SELECT of `payload_json` (ORM or Core column) returns the logical text |

No migration, re-signing, re-hashing or reinterpretation of old rows. A database
may hold v1 and v2 Runs side by side; an existing Run never changes format.

## Physical format `saved_v2.rope.1`

* `saved_revision_nodes(run_id, digest, body)`, primary key `(run_id, digest)`;
  insert-only (ORM guard + SQLite `RAISE(ABORT)` triggers). No cross-Run sharing:
  a node is visible only to its own Run.
* `body = header "\n" data`; header is canonical JSON `{"c":[child digests],
  "k":"v"|"s","n":[piece lengths]}`; materialized text = `p0 + M(c1) + p1 + ...`.
  `digest = SHA-256(body)`. References are out of band, so no JSON literal (for
  example a value that looks like a reference, `null`, Unicode, ` `) can
  alias a reference.
* Splitting follows JSON structure of the exact text: every container ≥ 4,096
  characters is its own value node; a container whose own literal text exceeds
  32 KiB or that has more than 64 child nodes is cut into content-defined chunks
  (CRC-32 of each member, ≈ 8 members per chunk, forced cut at 64 KiB), and wide
  chunk lists are grouped into a content-defined tree. Text that is not compact
  JSON is stored exactly as 64 KiB segments.
* Consequence: an append, a historical correction, a deletion or a Restore changes
  only nearby chunks plus the path to the root (copy-on-write); nothing assumes
  append-only data and no legitimate edit is rejected.

## Authority chain and reads (fail closed)

The column type compiles each SELECT of `payload_json` to
`CASE WHEN <envelope prefix> OR saved_v2_run(run_id) THEN saved_v2_payload(run_id,
payload_json) ELSE payload_json END`. v1 rows never call Python. The SQLite
function runs on the SAME connection, hence inside the caller's own transaction
snapshot, and for every call:

1. requires the Run to be recorded v2 (a v2 envelope in a v1 Run, or an inline row
   in a v2 Run, is rejected);
2. validates the envelope (canonical, format, `run_id` equal to the row);
3. fetches every reachable node of **that Run only**, re-hashes the actual bytes,
   validates headers, detects cycles, depth (256) and expansion (2^31 chars) and
   requires the total size to equal the envelope;
4. returns the exact text, which then passes through every existing v1 gate
   (content hash, lineage, owners, sources, replay, closure).

Reuse is limited to ONE explicit SQLite transaction on one connection: verified
nodes and assembled row texts are kept in a per-connection snapshot cache whose
epoch is bumped at every transaction/savepoint boundary and every DDL or other
non-DML statement; outside an explicit transaction nothing is cached. Own DML
keeps the nodes (they are insert-only: ORM guard plus `RAISE(ABORT)` triggers that
only DDL can drop). The verified text is handed to the ORM result processor by a
single-use in-process token instead of being copied through SQLite again. There
is no persisted or cross-request "verified" flag, so corruption after a
successful warm read fails the next read (next transaction). A
self-consistent re-hashed forgery (new nodes + envelope + recomputed content hash)
is in the same threat class as a re-hashed v1 row and is rejected by the same
semantic gates (tested). Integrity failures surface as `SavedV2IntegrityError`
(a `ValueError`) through the engine's `handle_error` hook.

## Writes (atomic, incremental)

In the same flush as the Saved row (`before_insert`): encode the exact logical text,
`INSERT OR IGNORE` only nodes this Save produced, store the envelope. In
`after_insert`: re-read the ACTUAL stored row through the same verified read and
require exactly the original text; otherwise the flush fails and the whole Save
transaction (nodes, row, head, draft, Viewer selection, audit) rolls back. A
pre-existing node with the same digest but different bytes therefore aborts the
Save rather than being trusted.

A bounded process-local index `(Run, exact value text) → node digest` (SHA-256 of
the candidate region compared before use) lets the writer skip rescanning
unchanged subtrees; a changed version of a known large value is scanned member by
member instead of being decoded whole. The index is a pure cache: hints for
another Run are never used, and a hint naming a node invisible in the current
transaction (for example after a rollback) triggers a full re-encode.

## Evidence

### Measured A-B-B-A (real HTTP/SQLite, 18 November 2026)

`scripts/measure_saved_v2_growth.py`, raw data in
`docs/evidence/saved-v2-abba-1000-w12-20261118.json`. Production source tree
`1a53174f` (head `5bdbaaf`), one 4-vCPU host, cases run sequentially
a1 v1 → b1 v2 → b2 v2 → a2 v1. Workload per case: NEW Run, 1,000 players, W12
clock, population, health, real MatchEngine opening match, two overlapping
4-player Editions with real matches, confirmed results, every Week Transition to
season end plus Season Transition, explicit Save after every operation: 170 HTTP
requests, 21 Saves, 26 Saved Revisions. Entity IDs deterministic.

| | v1 a1 | v2 b1 | v2 b2 | v1 a2 |
| --- | ---: | ---: | ---: | ---: |
| Saved IDs + content hashes, final inspection | — | identical | identical | identical |
| Sum of request wall time (s) | 1,294.9 | 1,274.7 | 1,284.7 | 1,178.2 |
| of which Saves (s) | 307.7 | 301.2 | 304.4 | 281.9 |
| of which GETs (s) | 436.0 | 441.8 | 447.1 | 396.7 |
| Last Save (week 12) wall (s) | 40.26 | 41.24 | 41.58 | 37.49 |
| Restart cold GET / warm GET (s) | 85.2 / 15.5 | 80.9 / 16.6 | 77.5 / 15.8 | 82.3 / 14.1 |
| Peak RSS (MiB) | 4,463 | 4,442 | 4,457 | 4,445 |
| SQLite main file / WAL (MiB) | 953 / 101 | 236 / 93 | 236 / 93 | 953 / 101 |
| Saved payload bytes stored (MiB) | 850 inline | 54 nodes | 54 nodes | 850 inline |
| File growth over the last Save (MiB) | +109 | +19 | +19 | +109 |

Reading (no extrapolation): Saved storage is 15.7× smaller and the database file
4.0× smaller; the per-week file growth of the Saved history drops from ~100 MiB to
~19 MiB (most of the remainder is the live working checkpoint rewritten each
week, not Saved data). Wall time is NOT improved: v2 is +3.5% versus the v1 mean
(+2.7% for Saves), which is inside the 9% spread between the two v1 runs; cold
restart reads are 5% faster, warm reads 10% slower (per-transaction re-hash of
all nodes). Peak RSS is unchanged. Save time still grows from 12 s to 40 s over
nine weeks in both formats: that growth is CPU in JSON/Pydantic/deep copies and
replay (the v1 profile of a 1,000-player Save shows ~2.5 s `json.dumps`, ~2 s
deep copies, ~0.55 s SQL), which this storage PR does not change. The #1820
W8 120 s Save timeout is therefore **not** shown to be fixed by this PR.

An intermediate variant that also memoized assembled subtree texts per snapshot
was measured worse (peak RSS 5.3 GiB, GET +10%) and removed (`5bdbaaf`).

### Tests (executed on the final production tree)

* `tests/infrastructure/test_saved_v2_store.py` (28) — exact round trip (Unicode,
  `null`/absent, empty containers, NaN/Infinity, non-compact JSON, reference-like
  literals), determinism with/without hints, append/edit/truncate copy-on-write,
  foreign hints, tampered/re-hashed/missing/foreign-Run nodes, forged sizes,
  malformed headers, cycles and exponential expansion, envelope binding, snapshot
  reuse bounded by the transaction (another connection's committed tamper is
  isolated inside the snapshot and rejected in the next one).
* `tests/api/test_saved_v2_http.py` (13) — real HTTP/SQLite: the same native
  scenario (population, health, MatchEngine opening match and Tour matches, two
  overlapping Editions, Saves, nested fork, Restore) on v1 and v2 with deterministic
  IDs: identical IDs/hashes/payload text and public DTOs/histories; restart;
  409 on corruption after a warm read (changed, missing, foreign-Run node, missing
  format, forged size); downgraded inline row; v2 envelope in a v1 Run; re-hashed
  forgery; mixed database (old v1 Run stays v1 while a new Run is v2);
  concurrent/stale Save; failed post-write verification rolls back nodes and row.
* v1 regression on this branch: `test_native_long_run_cold_lineage.py`,
  `test_native_long_run_text_proofs.py`, `test_native_saved_new_json_hash.py`
  with `GLOBAL_SLOT_CALENDAR=6`: 23/23 passed (measured on `3b2d76c`; later
  commits touch only the v2 path and the measurement script).
* The same three suites with v2 forced for every new Run: 12/23 pass; all 11
  others fail at their own tamper step, which rewrites `payload_json` through the
  ORM and is refused by v2 (see limits).
* Full `pr_critical` (3,882 tests) was not completed locally on this host; CI's
  Backend PR critical job is the gate.

## Known limits (honest)

* Storage only. Saved-read CPU is unchanged: readers still decode and validate each
  full logical payload, so cold reads remain dominated by JSON/Pydantic/replay
  (the profile of the 1,000-player W80 Save attributes ~2.5 s to `json.dumps`,
  ~2 s to deep copies and only ~0.55 s to SQL). Node-keyed semantic memoization is
  the next dependency and is NOT implemented here.
* Every new transaction re-fetches and re-hashes all nodes it reads (by design: no
  cross-request trust); this is the measured +10% on warm reads.
* Existing v1 tamper fixtures that rewrite `payload_json` through the ORM cannot run
  against v2 Runs: v2 refuses the write (`Saved v2 revision payloads are
  immutable`). Equivalent physical attacks are covered by the v2 tests above.
* No garbage collection (nodes of every reachable revision and fork are kept).
* Node parameters (4 KiB / 32 KiB / CRC chunking) are fixed for this format version;
  the physical page-size matrix of the ADR was not re-run.
