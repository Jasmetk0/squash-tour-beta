# Persistent first-cohort generation proposals — SQLite V1 candidate

Date: 11 October 2026; underlying Master v78. This contract applies only to Run-owned 2000/01 player proposals, not authoritative Player Package Save or Saved Revision history.

## Storage and ownership

An explicit Admin Save proposal writes one named immutable snapshot scoped to `(run_id, branch_id, proposal_id)`, independently of the Run Working Draft and Saved Revision. Maximum 12 snapshots per Branch. It contains all canonical preview players, source provenance, preview fingerprint, exact generation request/Keep history, selected Keep IDs, pending individual source-attribute locks, initial and next seeds, World conditions, audit reason, Saved HEAD, draft version and Run Package fingerprint. Data and row metadata are rehashed and checked during read. User can list metadata without retrieving the full 1000-player blob, open a selected proposal, and explicitly delete a selected snapshot.

At proposal Save, production backend checks owner/active writable Branch, saved HEAD and clean unchanged working-draft version, exact saved World copy and no already-adopted InitialWorld, then independently previews the requested generation and verifies the exact expected preview fingerprint. No arbitrary client player objects are stored as authority. Replay determinism derives from the already-approved real Run generator.

At proposal Open, backend validates the same scope/HEAD/World/draft and stored model's provenance, then returns the **persisted exact preview bytes** without invoking the generator. If changed or corrupt, opening fails explicitly. The browser rechecks response shape, whole cohort, all source hard conditions and any applied attribute locks before restoring selection state. It never automatically Adopt/Save or regenerate. New generation requires user action. The existing Adopt command still independently recomputes reviewed source and validates fingerprint with the same HEAD/Draft/World boundary.

## Proven/non-proven

Focused backend SQLite/API tests check restart, idempotent Save, corruption rejection, wrong scope, stale expected fingerprint and deletion. UI tests check reload restores pending Keep while never automatically invoking preview/Adopt/Save. Production Chromium verifies exact saved two-pass Keep + field edit over page reload and then a real ranking/tournament Save/replay flow. These are acceptance tests for the supported slice, not a 50-season release gate.

No promise of preserving a proposal through arbitrary later Saved Revision mutations; stale proposals remain visible for audit in list but are blocked from direct reopen. Proposals are not fork-shared, nor part of Viewer history. Proposed caps and management mechanics are technical V1 defaults, not game mechanics.
