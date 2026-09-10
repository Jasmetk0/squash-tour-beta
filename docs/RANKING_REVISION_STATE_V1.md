# Ranking preparation state for future Saved Revisions

`RankingRevisionState` is a versioned, self-contained representation of the ranking
preparation component: the complete candidate chain from Run Week 1, a verified
input manifest and command receipts for each candidate, and immutable result source
versions including correction lineage. Its SHA-256 fingerprint covers the complete
canonical JSON payload. It is not a complete world snapshot or a publication marker.

`capture_ranking_revision_state` reads this representation from one caller-owned
physical SQLite transaction. It does not commit, write, select Viewer or advance
time. It can be called after ranking preparation inside the larger transaction;
the caller must persist its content and trusted hash only when that transaction
successfully commits. Capturing it does not itself install it into Saved Revisions.

`load_ranking_revision_state` verifies an externally supplied trusted hash and
Run/Branch identity. It also verifies candidate week/parent continuity, every
calculation from its frozen inputs and predecessor, command identity uniqueness,
source identity/correction chains, and agreement between each candidate's complete
result input set and the source versions effective at that week. Verification needs
neither database access nor current award files. Hashing alone is not provenance:
the expected hash must later be anchored by the Saved Revision system.

Empty ranking state can be captured. Histories with missing command manifests,
legacy receipts or unsupported fork ancestry are rejected rather than presented as
complete. Existing Admin legacy inspection is unchanged. Read-only scopes can be
captured. Source versions scheduled after the latest candidate remain part of this
internal Admin preparation state; it must never be used directly as a Viewer payload.

Tests exercise real SQLite capture, serialization/independent loading, correction
boundaries, repeatability, outer rollback, read-only/fork/transaction guards, legacy
rejection, damaged input/source/week/receipt/scope and external hash verification.
This is the ranking component's serialization contract; Saved Revision save/restore
installation, branch remapping, full Week Transition and public publication remain
separate integration work. No sporting rules or realism parameters change.

## Installation into empty ranking storage

`install_ranking_revision_state` now installs a trusted same-Run/Branch payload into
an existing, empty ranking subsystem. It verifies the payload and external hash,
then installs source versions, candidates and reconstructed command receipts with
complete input manifests in one savepoint. A final recapture must match the trusted
fingerprint. Original command replay therefore remains available after installation.

The caller starts `BEGIN IMMEDIATE` before restore reads and owns the outer commit.
A later component failure rolls back the ranking installation. A caught installation
failure rolls back all its writes, while unrelated caller work remains. As with
other SQLAlchemy savepoint components, pending caller ORM work is flushed at
savepoint entry; callers should flush their own work before inspecting targets.

An exactly matching installed state is a no-write retry, including read-only scopes.
A different nonempty, partial, corrupt or legacy state is rejected. A new installation
requires a writable supported scope. No rows are deleted or overwritten, and there
is no branch identity remapping. Empty bundles remain valid no-op installations.

This is a ranking component installer for a larger recovery transaction, not a full
Run restore command. Run/Branch metadata must already exist; the caller must obtain
the trusted payload/hash from an authoritative Saved Revision and coordinate all
other world components. There is no public restore endpoint, Viewer selection,
clock advancement or replacement of an existing timeline in this change.

Additional real SQLite tests cover install/recapture equality, exact retry and
original command replay, outer rollback, caught receipt-write failure, existing
history conflicts, wrong hash/scope, read-only writes and transaction guards.
