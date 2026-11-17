# Saved v2 storage — one production path (Draft, 17 November 2026)

Status: **implemented behind an explicit, default-off opt-in for NEW Runs**; not
merged, not approved. Implements the unified direction of the #1823 ADR candidate
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

Nothing is cached across calls: there is no persisted or in-process "verified"
flag, so corruption after a successful warm read fails the next read. A
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

See the measurement section added with the final head in the PR description
(`scripts/measure_saved_v2_growth.py`, A-B-B-A on identical deterministic
workloads). Tests:

* `tests/infrastructure/test_saved_v2_store.py` — exact round trip (Unicode,
  `null`/absent, empty containers, NaN/Infinity, non-compact JSON, reference-like
  literals), determinism with/without hints, append/edit/truncate copy-on-write,
  foreign hints, tampered/re-hashed/missing/foreign-Run nodes, forged sizes,
  malformed headers, cycles and exponential expansion, envelope binding.
* `tests/api/test_saved_v2_http.py` — real HTTP/SQLite: the same native scenario
  (population, health, MatchEngine opening match and Tour matches, two overlapping
  Editions, Saves, nested fork, Restore) on v1 and v2 with deterministic IDs:
  identical IDs/hashes/payload text and public DTOs/histories; restart; corruption
  after a warm read (changed, missing, foreign-Run node, missing format, forged
  size); downgraded inline row; v2 envelope in a v1 Run; re-hashed forgery; mixed
  database (old v1 Run stays v1 while a new Run is v2); concurrent/stale Save;
  failed post-write verification rolls back nodes and row.

## Known limits (honest)

* Storage only. Saved-read CPU is unchanged: readers still decode and validate each
  full logical payload, so cold reads remain dominated by JSON/Pydantic/replay
  (the profile of the 1,000-player W80 Save attributes ~2.5 s to `json.dumps`,
  ~2 s to deep copies and only ~0.55 s to SQL). Node-keyed semantic memoization is
  the next dependency and is NOT implemented here.
* Every read re-fetches and re-hashes all nodes of each row it returns (parity with
  v1 reading the full row); no per-snapshot node cache yet.
* Existing v1 tamper fixtures that rewrite `payload_json` through the ORM cannot run
  against v2 Runs: v2 refuses the write (`Saved v2 revision payloads are
  immutable`). Equivalent physical attacks are covered by the v2 tests above.
* No garbage collection (nodes of every reachable revision and fork are kept).
* Node parameters (4 KiB / 32 KiB / CRC chunking) are fixed for this format version;
  the physical page-size matrix of the ADR was not re-run.
