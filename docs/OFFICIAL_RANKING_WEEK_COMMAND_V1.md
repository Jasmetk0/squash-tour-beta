# Atomic ranking preparation command V1

`RankingWeekCommandRunner.execute` combines persisted tournament ingestion,
historical source resolution, candidate calculation and an idempotency receipt
in one owned SQLite transaction. `BEGIN IMMEDIATE` acquires the write lock before
reading the candidate head or receipt. Any ingestion, calculation, receipt-write
or commit failure rolls back the database transaction. Lock/busy failures are
surfaced for whole-command retry; no partial commit is returned as success.

The immutable command requires an ID, historically resolved transition context
and the explicit tuple of tournament bindings from #695. Scope, consecutive-week
boundary, each initial publication boundary and duplicate event/Edition identities
are validated. Input ordering of players/tournaments is canonicalized for request
fingerprinting. An empty batch supports a week without newly ingested tournaments;
it is not proof that the caller found every eligible tournament.

A receipt links the scoped command ID, request hash, target week and candidate
hash. The same command returns the validated historical candidate without reading
current legacy JSON files. A changed request under that ID is rejected. A new ID
cannot adopt an already staged target week, including one staged through an older
path. A missing/altered referenced snapshot fails closed, including deletion of
the candidate tail when replaying its receipt. This receipt is not a full saved
revision anchor and does not detect coordinated deletion of receipts/history.

Replay is a historical read (and may return in a now-read-only scope); new work
retains source/candidate store write guards. SQLite locking serializes database
writers, not concurrent external JSON edits. Expected source hashes and trusted
Run/Branch/Edition/publication bindings remain required. The caller owns source
file stability and the completeness/authority of roster, tokens, policy and batch.

This is an internal ranking preparation command, not a full Week Transition. It
does not move the simulation clock, publish Viewer data or implement other weekly
processes. The future full transition must include this work inside its own unit
of work; it must not call this independently committing runner midway through a
larger transition. No public endpoint is added. Initial bootstrap stays separate.

Tests exercise real SQLite commits and rollbacks using persisted packages from
real extraction/award services over a synthetic bracket. They cover replay after
legacy JSON changes, canonical roster order, ID conflicts, invalid batch scope,
missing candidate tail, second-tournament failure, calculation failure after
source insertion and receipt failure after candidate insertion. Existing ranking
and ingestion tests remain in the focused verification set; no full season/API
acceptance is claimed. Qualification/exceptions, production scheduling/bindings,
roster/policy/token resolution, discipline and full revision/fork integration remain.

## Composition in a larger transaction

`stage_ranking_week_command(session, awards, command)` now exposes the same
validated preparation and receipt/replay path without committing the caller's
transaction. The standalone runner delegates to it. A future Week Transition can
call this component between its other stages and commit everything once:

```python
with factory.begin() as session:
    session.execute(text("BEGIN IMMEDIATE"))
    # Resolve and validate transition inputs under the same transaction.
    candidate = stage_ranking_week_command(session, awards, command)
    # Complete the other transition stages; any failure aborts the outer transaction.
```

The component requires an already active physical SQLite transaction, not just
SQLAlchemy autobegin. This prevents SQLite legacy transaction control from
committing a standalone savepoint when it is released. The caller must acquire
the write lock before reading transition inputs; the guard checks physical
transaction presence, not the lock mode. Busy/lock failures still require retrying
the complete outer command.

A nested savepoint rolls back this component's source, candidate and receipt
writes if preparation fails, even if the caller catches the exception. SQLAlchemy
flushes previously pending ORM work before creating that savepoint; that work
belongs to the caller. Successful preparation remains invisible to other sessions
until the outer commit, and a later stage's failure rolls it all back.

Real SQLite tests cover delayed visibility, replay within one transaction, later
outer failure, caught calculation failure preserving unrelated outer work, and
rejection of absent/ORM-only transactions. This is a composable ranking stage,
not yet a production Week Transition orchestrator or public ranking publication.

## Corrections at the target boundary

`RankingWeekCommand.corrections` is an optional tuple of `RankingResultVersion`
records for previously ingested Edition/player results. Each correction must be
scoped to the command, effective exactly at its target week, and reference a prior
version of a result first published in an earlier week. Duplicate Edition/player
corrections and simultaneous initial ingestion/correction of one Edition are
rejected. The source store verifies the predecessor fingerprint and preserves
original completion, first-publication and validity timing.

Corrections are appended after initial tournament ingestion and before historical
source resolution, within the same savepoint/outer transaction as candidate and
receipt. A failed correction rolls back the entire batch; an accepted correction
changes the new candidate without rewriting earlier source versions or candidates.
There is no extension of result lifetime. This also supports correction-only weeks.

Correction ordering is canonicalized by Edition/player in the command fingerprint.
Empty corrections are omitted from its hash payload to preserve replay of receipts
created before this field existed. Nonempty corrections participate in the request
hash, so changed corrections cannot reuse the same command ID.

Inputs remain explicitly resolved, trusted application inputs: this is not an
Admin editing endpoint or an automatic importer of changed legacy award files.
Correction authorization/provenance resolution and full Week Transition publication
remain the caller's responsibility. Tests use real persisted synthetic tournament
packages and SQLite, including multi-result rollback, old-history preservation,
canonical replay, legacy hash compatibility, invalid scope/boundary and attempts
to change original validity.

## Initial candidate command

`RankingBootstrapCommand` provides an explicit first-week entry point through
`RankingWeekCommandRunner.execute` and the caller-owned staging function. It
requires a resolved policy, roster/tokens and the supported `discipline="none"`
scope. Its target is restricted to 2000/01 Week 1. The operation uses no tournament
results: no completed tournament can first become eligible before this boundary.
Existing kernel lifecycle rules still apply: players entering in Week 1 remain NR
in that snapshot and first appear in Week 2, including zero-point players.

The initial candidate and its command receipt are written atomically. Exact replay
returns validated saved history even after later weeks; changed requests or another
command trying to claim the existing initial candidate are rejected. Fork ancestry,
read-only scope and invalid roster guards remain enforced by the existing layers.
The versioned bootstrap request has a distinct hash shape from weekly requests.

An award service is optional for bootstrap and weeks with no tournament ingestion;
commands with tournament bindings require it. This permits initialization and
empty-week progression without unrelated legacy tournament files. Empty roster is
supported, but creation of an empty Run does not automatically initialize rankings.

This command does not publish to Viewer, create a Saved Revision or move time.
Its explicit initial-week scope does not replace a future import/mid-run bootstrap
or fork adapter. SQLite tests cover initial-to-next-week progression, canonical
replay, conflicts, outer rollback, invalid scope/roster/week, read-only/fork guards,
and empty initialization. The core command/transaction tests are included in smoke CI.

## Complete input manifests

New command receipts store version 1 input manifests alongside their candidate
hash: the complete resolved roster (including NR/retired players and tie-break
tokens) and all resolved result inputs, including results outside Best N. Policy,
week, scope and predecessor are already protected by the candidate snapshot.
The manifest is stored in the same savepoint/transaction, including bootstrap.

Command replay and Admin history verification reconstruct the candidate using
these frozen inputs and its stored predecessor/policy, and compare the complete
candidate fingerprint. This is verification only: no history is replaced and no
current legacy award files are read. A missing payload, unknown manifest version,
changed input or nonmatching reconstruction fails closed. Source inspection also
compares its full effective result set against the stored manifest, detecting
missing or changed uncounted results as well as counted ones.

Two nullable receipt columns are added through the existing idempotent SQLite
compatibility migration. Legacy receipts with both columns null retain their old
read/replay behavior; their missing inputs are not reconstructed from current data.
A manifest proves the exact supplied calculation inputs, not the caller's authority
or completeness against the whole world. Coordinated corruption of the manifest
version marker and payload to impersonate a legacy receipt is not detected without
an external immutable revision anchor. Full Saved Revision/publication integration
is still outstanding. Future calculator changes must retain verification support
for the persisted version-1 calculation contract.
