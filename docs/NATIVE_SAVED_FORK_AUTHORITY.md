# Native Saved fork: historical source authority

This implements source authority, target-baseline preparation and **internal atomic
baseline persistence**, not independent target continuation. Native
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

## Target current baseline preparation

`NativeForkBaselinePreparationService` prepares a typed `native_fork_baseline.v1`
for a distinct, as-yet unreserved target identifier inside one SQLite read
snapshot. It copies complete current lifecycle identities/policy, all 57
attributes/potential/Form/sharpness/fatigue, actual Health facts and slot cursor.
The original population, lifecycle, Health, checkpoint, Tour and current Official
ranking remain explicit source references. Historical matches, Entry tokens,
birth events and ranking hashes are not re-signed for the target.

All three current populations must be complete, identical and canonical. Source
dates and compatible older horizon values are preserved. In particular, a valid
pre-birth Saved Tour may still carry an earlier Health source: its exact week and
facts remain recorded, without inventing a weekly Health transition or healing.
The effective current clock comes from the selected Saved snapshot, never later
Run metadata or future prospect catalog contents.

`verify` receives the expected Run/source/target command identities separately,
reauthenticates actual reachable source records and reconstructs every projected
fact. A self-consistently rehashed change to current attributes, injury facts,
lifecycle policy or ranking reference is rejected. Preparation rejects an already
used target identifier; verification of an installed historical root additionally
requires its declared fork origin to match. Neither operation reserves IDs,
creates Branch/draft/runtime rows, grants creation permission, saves or simulates.

This is an internal preparation service. It is not wired into the public create
writer. Persistence is a separate internal kernel described below; preparation's
JSON round trip alone is not evidence of a persisted new Branch.
The actual-source HTTP/SQLite scenario reuses real pre/post-birth and post-match
Saved states and source epochs, rather than creating a second large fixture.
Pure tests separately cover W7/W52/W61/W80, retained injury facts, compatible
horizon extension and malformed populations/time scopes.

## Atomic baseline persistence (internal staging only)

`NativeForkBaselineInstallationService` opens `BEGIN IMMEDIATE` and invokes the
session-owned installation kernel. It reauthenticates the actual original source
and every projected fact, checks the expected source head/Viewer and reserves
the target identifiers/name. It atomically inserts five rows: Branch metadata,
Branch state metadata, a clean Working Draft, a target-owned Saved root and its
audit/installation receipt. There are no nested commits or source-row updates.
Failure at the final audit insertion rolls back all five rows. Exact concurrent
retries return the authenticated original result; conflicting receipt arguments
or an already changed target are rejected without overwriting anything.

The Saved schema is `native_fork_saved_root.v1`. Its only content component is
the typed baseline plus its fingerprint. Its parent is the actual selected
original revision, with the next contiguous sequence. Original native components
are read through authenticated ancestry; they are not copied under a new owner.
The root retains the selected Saved calendar, including an older compatible
horizon. This staging snapshot does not rebase or execute a current-calendar task.

Ordinary Saved detail, list, history, hash and revision-state reads reauthenticate
the root and its actual source dependencies. A target-byte cache cannot certify
unchanged external source rows, so these roots are not retained as independent
cached proofs. Source resolution happens outside revision stripe locks, with a
context-local cycle guard. The affected detail/list/history/revision-state/draft reads use explicit SQLite
snapshots.
The pure component parser alone does not grant database/source authority.

The target is deliberately `preparing_native_fork` and read-only, with no live
sporting/lifecycle/Health/Tour runtime rows. Existing active-Branch, read-only and
unsupported-content guards prevent execution, Manual Save, restore and Viewer
selection. Public native creation stays blocked; no endpoint exposes this staging
installer. A stored root is **not** evidence of independent simulation readiness.

The real installation scenario uses a production HTTP/MatchEngine source, then
tests late failure rollback, two concurrent first attempts, exact/conflicting
retries, original-history preservation, ordinary HTTP history and server restart.
It also forces all revision work locks onto one stripe and rejects changed source
bytes, fully rehashed baseline facts, schema/component downgrades and cross-Branch
source cycles. The separate
acceptance job runs in parallel with the longer birth/epoch scenario; neither is
added to Draft Fast CI.

## Required next boundary

The pending target baseline must be activated atomically with its continuation authority
for sporting, lifecycle, Health, Entry and Tour. New execution adapters must
reference this authenticated original root while giving every **new** command a
target-owned predecessor. Do not insert the baseline into old same-owner history
formats without their dedicated versioned fork handling.
Do not enable native creation by adding its component names to the old remapping
whitelist, rewriting historical owner fields/log hashes, or treating a valid
source binding as proof that mutable target state has been installed correctly.

Completion still requires real independent play/Save/restart/restore of both
Branches, rollback/concurrency/tamper cases and the actual Admin browser flow.
The source-authority checks and native refusal acceptance do not prove that.
