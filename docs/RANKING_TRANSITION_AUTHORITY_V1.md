# Ranking Transition Authority V1

## Scope and status

This implemented contract prepares only the ranking candidate component of a future
Week Transition. It neither advances world time nor publishes an Official Ranking.

An explicit audited **manual adoption** stores an immutable Run/Branch-owned snapshot containing:

- the Working Draft's base Saved Revision;
- distinct completed and target weeks, which must be consecutive;
- the complete canonical roster, Tour-entry/retirement eligibility and unique stable
  tie-break tokens;
- the historically effective target-week Ranking Policy; and
- human-readable source provenance and command audit.

This adoption is the narrow authority bridge while complete product-level player and
world-time projections are not yet available. The server verifies Run/Branch ownership,
writability, base Saved Revision identity, consecutive week structure, canonical unique
player/tie-break identities, and that no declared Tour entrant lies after the target.
It does **not** independently prove that the client-declared roster is complete, that
retirement/lifecycle flags match a stored world projection, or that the supplied policy
was historically effective. Those fields remain a manually declared frozen snapshot;
legacy season files are not silently accepted as branch truth. This is not an automatic
world/lifecycle resolver.

## API and transaction behavior

`POST /admin/runs/{run}/branches/{branch}/ranking-candidates/transition-authorities`
performs the explicit adoption. It validates writable scope and binds the snapshot to
the current base Saved Revision. A target boundary is append-only; exact retries are
idempotent and conflicting replacements fail closed. A later Save may carry the exact
authority forward. Resolution accepts that newer base only when the current base Saved
Revision's verified ranking component contains the identical fingerprinted authority—not
merely because the original base is an arbitrary ancestor.

The `/prepare/week/authoritative/preview` and `/prepare/week/authoritative` routes take
only command/source operations plus the target locator. The server resolves roster,
policy, completed week and target week from stored authority. Existing result history,
correction and disciplinary-zero resolution then feed the existing deterministic
calculator. Preview runs the production transaction and always rolls it back.
Confirmation can use both preview fingerprints; it re-resolves authority and source
history under the SQLite write lock, so any input drift is rejected even if ordering
would happen to remain unchanged.

Authority snapshots are part of `ranking_revision_state.v3`; Save, reopen and restore
capture, transactionally remove/reinstall, and validate them. V1 and V2 payloads remain
readable and hash-preserving when the new collection is absent. Viewer routes do not
expose draft authority or candidates.

## Deliberate boundaries

This is not the Week Transition transaction owner. Clock movement, lifecycle mutation,
development/recovery, public World Events, Official Ranking publication, fork remapping,
Protected Ranking and broader abnormal-result support remain out of scope.
