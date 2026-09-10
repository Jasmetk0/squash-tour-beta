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
