# Native Full Simulation history performance

Status: measurement and implementation in progress; **WAIT**, no merge recommendation.
Base: owner-merged `buuk` `e39d962bb6797960c47c1c659d57be1dc67bba6b`.
Only the owner merges. One implementation branch/PR; no auto-merge.

The baseline runs the existing genuine W52 worker/Save/season acceptance from an
immutable checkout. It preserves a SQLite backup immediately before task Start,
then idle early/middle/late week snapshots. Before/after full runs must start from
that same backup and retain every actual week, sporting assertion and manual Save.
A snapshot profile measures that section only, not end-to-end completion.

Capture total wall time, per-step Save/resume time, SQL count and statement/parameter
bytes, native context time, Saved payload bytes and process peak RSS. Separate
repository-cold from warm context reads; obtain CPU profiles separately so profiler
overhead is not counted as speed evidence. SQL text/parameter volume is not the
volume of query results. Record returned physical-history bytes separately.

The earlier W52/W61/W80 times in the task describe those individual integration
scenarios and are not a benchmark of every Run or the complete product.

Implementation, comparable measurements, integrity review and final-head test
ledger will be recorded here as they actually execute. Draft-skipped hosted jobs
are not successful acceptance evidence.

## Production changes under test

- Decode original Saved input projections through a repository-local exact-value
  cache. Each lookup hashes the complete current payload and scope; it retains
  at most two entries and at most 4 MiB of serialized input in total. Parsed model
  memory has additional overhead. Oversized inputs bypass retention. Defensive
  copies prevent callers from mutating retained models. This cache grants no
  owner, lineage, source-head or physical-row authority.
- Reread and hash every physical field using type-tagged, length-delimited UTF-8
  bytes. Reuse only the parsed dependency references for those exact current
  bytes, retaining at most 4,096 compact hints per repository. Actual owners,
  source heads and complete dependency topology are still reauthenticated in each
  new snapshot. Python JSON parsing preserves the verifier's duplicate-key
  semantics; SQLite json_extract would choose a different duplicate value.
  These are ephemeral keys only; persisted content hashes, serialization and
  Saved schemas do not change.
- Replace obsolete physical snapshots instead of retaining every write generation.
  Completed operation proofs follow that same transaction/snapshot. SQLite trace
  invalidation also observes raw driver rollback/savepoints and transaction
  restarts, where `total_changes` alone is insufficient. Reject stale loaded
  source/owner ORM identities before certifying changed physical dependencies.
- Bound parsed-runtime value retention to eight entries and 8 MiB of serialized
  inputs per operation, using compact digest keys rather than large JSON keys.

The source, horizon, seed, sporting kernels, task lease/fencing, manual boundaries,
commands, receipts and persisted history formats are unchanged. A changed physical
source must still pass the original full verification. No global history cache,
Saved migration, sporting recalibration or timeout increase is introduced.

## Reproduction

Run `scripts/profile_native_full_simulation_scenario.py --root work/before --weeks
52` on the baseline. It invokes the unchanged actual acceptance case and preserves
its genuine pre-Start SQLite input and selected idle weeks. For a comparable
candidate execution use `--root work/after --weeks 52 --input work/before`.
The input copy only replaces fixture construction; every actual worker operation,
manual Save, tournament, point assertion, transition and cold restart still runs.
Use a fresh output directory. The original fixture is never modified.

For section-only profiles run
`scripts/profile_native_full_simulation_context.py --database
work/before/week-26.db --branch <input.json branch> --root work/profile --profile`.
Use the same profiling scripts and disposable input on both source trees. Cold
means a new repository validation/projection cache, not an OS cache flush. Warm
reads use new transactions; `same_snapshot_warm` separately measures one unchanged
transaction. CPU profiles are separate from unprofiled timing records. Fetch
metrics count actual returned text/blob UTF-8 bytes, excluding scalar/protocol
bytes; SQL text/parameter volume is reported separately.

Compare `sporting-history.json` across runs: all retained native player, lifecycle,
health, ranking, development, match and transition facts are hashed at every Saved
sequence. Generated Save IDs and their reviewed journal/receipt fingerprints are
excluded from this cross-execution sporting comparison; the original integration
assertions independently retain exact retry, immutable original source, restart
and replay checks. A structural digest is not a substitute for those assertions.
