# Exact Saved Revision Run World reads — pre-alpha, 12 October 2026

## Contracts and scope

Run World has three independent dimensions: the **World data year** for population/rating projections, the **simulation clock/checkpoint**, and the **Saved Revision identity** of an immutable Run-owned World copy. A present-time selection of an explicitly reachable Saved Revision reads `GET /run-containers/{run}/branches/{branch}/saved-revisions/{revision}`. The existing service verifies the revision is reachable in that Branch, including shared ancestry; no current World Package request is used as a fallback. Direct old revision URLs are allowed, but the revision endpoint still checks reachability and denies foreign IDs.

A Saved Revision payload contains `content.run_package_state` with a preserved `fingerprint` and `state`. The projection validates response Run/Branch/revision ID; payload Run; snapshot owner Branch; shape and declared fingerprint. Shared ancestors retain the **original** `revision_branch_id` instead of mutating source state, payload bytes or hashes to impersonate the selected child Branch. A new read does not edit current HEAD, Run, Package Library, or source snapshots. Missing/malformed stored World is explicitly unavailable.

Historical **country roster** remains unavailable because the present canonical Saved HEAD players endpoint cannot truthfully represent an older revision; no current player substitution is permitted. Other unfinished records/tournaments remain explicit placeholders. Unlinked simulation checkpoints stay blocked: legacy checkpoint payloads do not supply a verified Saved Revision mapping, so the interface never guesses an appropriate World snapshot. A future separate authoritative mapping from simulation checkpoint to Saved Revision must be explicitly versioned and validated before this limitation is lifted.

The selector shows the latest 200 reachable revision records. An exact older revision ID may be supplied by URL for a reachability-checked read. Current live Run state is an explicit separate choice and can contain unsaved changes; it is not identical to Saved HEAD by assumption. Cache keys include Run, Branch, revision and read mode; changing to a checkpoint hides any cached current or historical World.

## Verification

Deterministic parser tests cover distinct saved Worlds, shared ancestry, foreign/forged identity, missing historical component and immutability. UI tests cover revision switching, separate data-year scope, missing data, inaccessible scope, roster fail-closed and checkpoint-cache isolation. Mock tests are labeled mock tests; browser workflow and historic roster projection are independent acceptance gates. This is not a 50-season or sport-realism validation.
