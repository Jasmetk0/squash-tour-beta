# Run storage measurement — independent diagnostic

The collector reads an existing SQLite file through a mode=ro URI and
query_only connection. It never invokes the engine, Save, simulation, migrations,
VACUUM, WAL checkpointing, or journal-mode changes. Normal SQLite WAL reader
coordination may update SHM; this is NOT a promise of unchanged physical files
while another process runs.

## Usage

    python scripts/profile_run_storage.py --database data/run.sqlite
    python scripts/profile_run_storage.py --database data/run.sqlite --run-id RUN_ID --label season-01 --output new-report.json

The output path must be new and cannot be the database, WAL or SHM. Existing files,
symlinks and hard links are refused. Missing input never creates a database.
Failures print an error to stderr, return nonzero and do not emit a success report.
UTF-8 SQLite text encoding is required; UTF-16 is explicitly rejected instead of
misreporting native stored text bytes as UTF-8.

## Schema and scopes

The JSON schema identifier is run_storage_profile.v1. The report records UTC
observation bounds, elapsed collector time and Python/SQLite versions.
Related logical queries share one read transaction, which closes before filesystem
size collection. DB/WAL/SHM sizes therefore have a separate observation interval
and need not match the logical snapshot if another writer commits meanwhile.
A missing sidecar is null/absent; an unreadable file is unavailable with a reason.

Page count × page size is allocated page bytes. Freelist bytes and non-freelist
page bytes are separate. These and physical file sizes always describe the WHOLE
DATABASE, even when row/payload observations use --run-id. They are not the size
attributable to one Run. dbstat/per-table/index physical attribution is deliberately
not collected in v1 and is explicitly reported as such.

Only the bounded known Run/Saved/task/Package table inventory is queried.
Missing historical tables are listed as unavailable rather than zero. A table
without run_id has explicitly whole_database row counts, even with a filter.
Known core tables with missing required columns, corrupt databases and databases
with no supported tables fail. Unknown tables/views are not executed; a view or
virtual table impersonating a known persisted table is refused.

Saved aggregates use SQL COUNT/SUM/MAX/AVG and length(cast(text AS BLOB)) on UTF-8
databases. They do not materialize or decode every payload in Python. SQL scans
can nevertheless read many bytes and hold a read snapshot for their duration;
measure collection overhead before choosing frequent sampling.

branch_saved_revisions groups each PERSISTED owner row once. Shared ancestry is
not multiplied by descendant Branch count. branch_heads separately reports the
actual run_branches.saved_head_revision_id pointer and original revision owner.
It never substitutes Working Draft.base_revision_id. Fresh forks can legitimately
reference a source-owned revision and have no owned revision of their own.
A missing or foreign-Run HEAD reference fails. These observations do not prove
lineage reachability, hashes, original source validity or sporting replay.

## Actually executed synthetic example

A disposable database created by the current production ORM schema, with two
Runs and a source-owned inherited fork, produced this selected-Run excerpt:

    saved_revision_totals:
      count: 2
      payload_bytes_sum: 30
      change_summary_bytes_sum: 4
      payload_bytes_max: 17
      payload_bytes_mean: 15.0
    branch_heads:
      root: { revision_id: a2, original_owner_branch_id: root, payload_bytes: 17 }
      fork: { revision_id: a1, original_owner_branch_id: root, payload_bytes: 13 }
    page_metrics:
      scope: whole_database
      page_size: 4096
      page_count: 329
      allocated_bytes: 1347584

The two synthetic payloads are {"name":"é"} and {"name":"Ř😀"} (13 and 17 UTF-8
bytes). The full ORM database includes many empty tables and indexes. These
observations are NOT a 1,000-player or 50-season benchmark.

## Independent review and verification

The initial candidate's five tests passed over an invented draft schema.
Against the real ORM schema, its CLI failed with:
"no such column: d.based_on_revision_id". The actual draft field is
base_revision_id, and even that is not the authoritative Branch HEAD.
The reviewed collector uses the real Branch pointer and separate owner metrics.

The revised 15 focused cases exercise production ORM tables, non-ASCII bytes,
two Runs, inherited HEAD without an owned revision, stale draft base, committed
WAL with an uncommitted competing writer, URI characters, malformed/empty/corrupt
inputs, unsupported encoding, optional historical tables, foreign HEADs and
exclusive output creation. Fixture payload hashes are synthetic metadata:
this test validates storage accounting, not an integrity/replay validator.

    python -m pytest tests/infrastructure/test_run_storage_profile.py -q
    python -m ruff check scripts/profile_run_storage.py tests/infrastructure/test_run_storage_profile.py
    git diff --check

No production persistence, sporting rules, existing profiles, CI selectors,
timeouts or dependencies change.

## Future checkpoint use

Call the collector explicitly before/after selected Saves and at season boundaries
of the already-required reference run, using distinct output names and labels.
Keep reports associated with the actual engine commit, hardware and scenario in
the surrounding acceptance evidence; a collector label is not proof of DB origin.
Compare cumulative persisted payload bytes, latest HEAD sizes, row counts and
whole DB/WAL observations over time. Do not force a checkpoint to improve a metric.
This PR does not wire into or launch a full season/50-season campaign.

Payload-byte totals are not archive size, index size, filesystem peak usage,
temporary validation space, RSS, recovery certification, a storage quota or proof
of quadratic growth. No release threshold or history pruning is introduced.
