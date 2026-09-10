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
