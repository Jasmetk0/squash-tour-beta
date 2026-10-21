# Native Saved fork: historical source authority

This implements the **source side**, not independent target continuation. Native
creation still returns its existing blockers. The original MatchEngine inputs,
results, rally anchors, lifecycle admissions, Health and prospect epochs retain
their original Branch identities. A new source reference never authorizes writes
to that original Branch.

## Implemented boundary

The existing server Branch review returns `native_source_binding` for a native
played source, or `null` for a source without native played evidence. It contains
the actual Saved revision/owner/content hash, canonical hashes of every complete
Saved component, and distinct original execution-source revisions with their
owners and authenticated content hashes. Its own fingerprint is part of the
existing source/head/Viewer/inventory-bound confirmation fingerprint.

The adapter consumes the repository's fully validated lineage and restricts
execution sources to revisions **before the selected source**, rather than the
original Branch's later live head. It checks the opening match against its actual
pre-play Saved population and frozen Health. Tour origins retain their existing
draw, policy, checkpoint, prospect-epoch and receipt verification, with the same
historical boundary propagated into nested native roots. Original command and
Edition sources must also be real earlier revisions of the original owner.

`resolve_native_fork_source_binding` independently reauthenticates a reference
against actual reachable Saved records in the caller's transaction. A model,
self-consistent reference hash or recomputed component hash is insufficient.
It returns the original record; it does not remap state or install a target.
The adapter retains only reference metadata for ordinary historical command
sources, avoiding an extra full population/rally-payload copy per command.

Review and resolution do not read the live Run prospect catalog, mutate any
SQLite state, run simulation, Save drafts or change Viewer selection. Existing
repository exact-byte validation caches retain their original integrity checks.

## Required next boundary

The target needs its own explicit fork baseline and continuation authority for
sporting, lifecycle, Health, Entry and Tour. It must reference this authenticated
original root while giving every **new** command a target-owned predecessor.
Do not enable native creation by adding its component names to the old remapping
whitelist, rewriting historical owner fields/log hashes, or treating a valid
source binding as proof that mutable target state has been installed correctly.

Completion still requires real independent play/Save/restart/restore of both
Branches, rollback/concurrency/tamper cases and the actual Admin browser flow.
The source-authority checks and native refusal acceptance do not prove that.
