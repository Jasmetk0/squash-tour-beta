# Portable Saved Branch archive v1

Implementation candidate against `buuk` `9980628243f6ac637cb6ab803af1e4c632520849`,
under the single Draft PR #1677. Only the owner merges. This document does not
certify pre-alpha, the full release gate, or completion of Master §24.

## Scope and format

This is **custom selected Saved Branch export with dependency history**. It is
neither a full Run archive nor a compact snapshot. It preserves original Run,
Branch, player, match and revision identities. New-ID copies and confirmed
replacement of an existing Run with backup/diff remain required follow-up modes
under Master §§24.2/31.29. This mode refuses every collision; it cannot replace,
merge or rename an existing identity/name.

The provisional `.sqbranch` file is uncompressed UTF-8 JSON. Its closed manifest
is `run_branch_archive.v1`; required engine capability is `run_branch_archive.v1`,
based on engine `0.1.0` at `9980628243f6ac637cb6ab803af1e4c632520849` plus this
implementation. An unmodified engine at that base does not implement the feature.
No generic older-schema migration or newer-format downgrade is claimed.

Fixed ordered parts are `run`, `branches`, `revisions`, `audits`, `checkpoints`
and `allocator`. Each part has its exact UTF-8 byte length, SHA-256 and JSON text.
Branches are sorted by ID, revisions by sequence/ID and audits/checkpoints by ID.
Original `payload_json`, `change_summary_json`, original hash algorithm/hash and
original owner context are retained, without rewriting or re-signing history.
The entire delivered file has a separate SHA-256 used by preview/confirmation.
Transport checksums detect damage; they are not signatures or proof of origin.
Original Saved and independent native source/replay authorities remain mandatory.

Uncompressed JSON avoids extraction paths and decompression amplification while
keeping original bytes inspectable. The provisional HTTP/parser budget is 128 MiB
per operation, with a three-file-size temporary/target space estimate. It is not
a Run/history/storage quota. An oversized request is rejected in full; history is
never truncated or deleted. Streaming larger files is a technical follow-up.

## Supported matrix

| Area | v1 behavior |
| --- | --- |
| Run | Custom, writable Saved Run with no legacy simulation/global metadata owner; valid stored calendar/name/status |
| Selected Branch | Current Saved HEAD, complete reachable parent lineage, active writable Branch; clean exported current state |
| Saved envelopes | `empty_run_saved_revision_v1`, `run_saved_revision_v1`, `native_fork_saved_root.v2` |
| Native fork | Existing active v2 aggregate, original baseline/source owners, full historical source proofs and Run calendar; normal existing continuation/Save |
| Population and Packages | Existing InitialWorld/Run Package adapters, complete Run-owned snapshots and provenance; legitimate unresolved Package references retained and listed |
| Sporting components | Existing lifecycle, Health, sporting, slot/match, calendar standalone/checkpoint/Tour adapters; their existing typed version/replay validators run |
| Entry components already in Saved content | Existing entry-decision, validation-slot, application, Wild Card and Tour-entry adapters; no Entry policy/contract change |
| Recovery | Reachable Saved history, original revision audit events and required pre-restore Saved checkpoints; existing supported checkpoint/restore audit pairing is checked |
| Prospects | Union of original Signed immutable source snapshots/epochs, including Run-owned prospect records, without a source registry |
| Activation | Original Saved aggregate or normal component adapters, new clean draft at version 0, original saved Viewer choice; no simulation/task starts |
| Unknown/new content | Whole operation blocked with a reason; no discarded components or downgrade |

A historical source-owner Branch can end at the required original prefix rather
than its later divergent HEAD. Preview names all included Branches and roles,
all retained original revision IDs/hashes/parents, selected HEAD components,
Package unresolved references, dependency history, audit/checkpoint counts,
original target identity/name, bytes and omitted Branch IDs/areas. Source/Viewer
branches are dependencies, never privileged Main/Official timelines.

Run activation has an explicit original Saved witness. If a third editing Branch
Saved the actual Viewer choice, that witness and its dependency history travel
too. Viewer is never silently redirected to the exported Branch.

This first matrix rejects pending native fork v1, legacy-backed Runs/checkpoints,
unsupported ranking-preparation/season-closure/Lab components, unknown activation
metadata, nonempty shared HEAD activation requiring materialization, and independent
Task Center history (including completed native task controls). Task history needs
its own semantic adapter: it is not silently treated as a regenerable process.
Only supported adapter/schema combinations that pass the complete isolated
installation are exportable/importable.

The exact declared omissions are unselected divergent future, recovery drafts,
working changes, caches, temporary calculations, worker processes/task controls,
global Package files and **non-Saved authoring receipts**. Component-embedded
sporting command receipts/journals and original revision audits are retained.
This custom Saved-history scope does not promise retries of old source authoring
commands held exclusively outside Saved content, nor a complete global Audit Log.
The import command itself always has a durable exact-retry receipt. Full archive,
other custom selections and compact export remain separate pre-alpha requirements.

## Boundaries and existing adapters

The initial audit found substantial existing support: repository Saved
identity/hash/lineage verification, original native physical dependency/source
proofs, materialized fork aggregates and fixed component capture/restore adapters.
The new boundary composes these; it does not introduce a SQL dump/loader or an
import-only simulation state. Shared persistence, sporting logic, dependencies,
CI, frontend #1676, Entry authorities/driver, Master, AGENTS, CURRENT_STATE and
ROADMAP are unchanged. `api/routes.py` only registers the new router.

Export preview and download each use one explicit SQLite `BEGIN` read snapshot.
The command binds HEAD and exact file digest. A Save during that snapshot may
finish independently under WAL: the response still represents the exact old
reviewed state. A subsequent request with the old preview is stale. Drafts and
actual live components of exported current HEADs must be clean/equal to Saved.
An omitted foreign dirty Branch is outside that scope.

Import preview parses the closed format and original hashes, then performs a
complete installation using the normal adapters in a fresh disposable SQLite
file and fresh repository. It verifies owner topology, source proofs, replay,
calendar, activation, original bytes and allocator safety there. It makes no
writes to the target. Confirmation repeats independent complete validation even
if a client computes a review fingerprint without calling preview.

The actual target then acquires `BEGIN IMMEDIATE`, repeats receipt/review/conflict
checks and atomically installs Run, Branch context, original revisions, audits,
checkpoints, Signed prospect sources, live components, allocator, clean drafts
and the import audit/receipt. Late failure rolls back every row. Conflicts include
orphaned Run namespaces, original Branch/revision/audit/checkpoint identities,
clean-draft IDs and the Run name, including archived names.

The receipt records actor, reason, explicit confirmation, exact archive digest,
preview fingerprint, request fingerprint, timestamp and original result. Exact
retry returns that result across process/SQLite restarts and later continuation.
Different bytes/review/audit under the same command ID fail. Concurrent different
commands cannot pass identity/name conflict checks. Writer contention has an
explicit exact-retry error rather than an alternative import path.

## API

All routes are under `/admin/run-archives`; no UI was added.

1. `POST /export/preview`, JSON `{run_id, branch_id}`.
2. `POST /export`, JSON `{run_id, branch_id, expected_head_revision_id,
   expected_archive_digest}`. Binary attachment response uses a fixed filename.
3. `POST /import/preview`, raw file bytes, returns `can_restore`, conflicts and
   `preview_fingerprint` after complete independent validation.
4. `POST /import/confirm`, identical raw bytes, query parameters `command_id`,
   `expected_preview_fingerprint`, `explicit_confirmation=true`, `operator_label`
   and `audit_reason`. Success is HTTP 201 with the durable original receipt.

No archive-controlled filesystem location, Python deserialization, executable
SQL, code execution or global Package reload is accepted. Unresolved Package
references remain distinct from missing required runtime dependencies. Import
never grants sporting readiness; the normal operation-scoped preview/replay
remains authoritative.

## Reproducible evidence and review

The new tests use actual HTTP, SQLite and production writers/MatchEngine. They do
not fabricate sporting results or clone `dev.db`:

- Empty Run, two manually supplied players, actual rally MatchEngine, explicit
  Save, deterministic file download; source DB/handles removed; import preview,
  explicit confirmation, fresh target process restart, identical full stored
  replay, Saved detail/history and normal Viewer snapshot read. Target processes
  run in an empty directory without `config/` and inherit no source Python caches.
- The existing four-player native/fork fixture, real opening knockout and Tour,
  Signed source catalog, original baseline/owner proofs, actual native birth,
  explicit Save; file transferred to another empty process/directory/DB; exact
  original history/payload and supported Tour view, normal continuation and Save,
  second restart and original import retry. Built-in FAX source tree hash and
  source DB contents are checked unchanged before removal.
- A real HTTP Save commits while an export is deliberately held after its first
  snapshot reads; download retains the exact reviewed old file, then a new request
  with that preview is rejected. This is actual overlap, not two serial calls.
- Two HTTP confirmations with different command IDs race: one succeeds, one is
  stale/conflicting. Concurrent exact retries return the identical original result.
- Truncation, unknown version/fields/component, original hash failure despite new
  transport checksums, rehashed native original-source mismatch, foreign/missing
  owner, unreachable revision, cycle, missing runtime dependency, dirty exported
  draft/authoring, omitted dirty Branch, name/ID collisions, third-Branch Viewer
  witness, unresolved Package preservation, final receipt failure/complete rollback,
  and a self-declared review that causes **zero target writes** before rejection.

Pure tests cover the closed manifest and graph without I/O. Existing persistence,
Saved/fork/recovery and native acceptance are separate regression commands.
The exact executed final-head commands/results belong in PR #1677's evidence;
local smoke, Draft skips and unselected workflows are not full regression or a
50-season release pass. No browser changes or browser acceptance are claimed.

Independent adversarial review specifically revisited malformed shapes, foreign
owners, independently bound native original hashes, lost confirmation/retry,
third-Branch Viewer selection and concurrent writers. It led to the pre-write
independent confirmation gate, explicit activation witness, complete conflict
reservation, own-HEAD context checks and fail-closed Task-history boundary.
