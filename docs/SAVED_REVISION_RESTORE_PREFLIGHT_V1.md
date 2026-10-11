# Saved Revision restore preflight v1

Saved Revision restore is destructive to the current live timeline state, even though it
preserves later history by creating a new restore revision and safety checkpoint.
The UI therefore needs an authoritative read-only review step before explicit confirm.

## Contract

`GET /run-containers/{run_id}/branches/{branch_id}/saved-revisions/{revision_id}/restore-preflight`
performs no mutation. It validates the current Run/Branch revision boundary, resolves
the target revision from validated lineage, and returns:

- the exact current Saved Revision head;
- the current Working Draft version;
- the current Viewer Branch identity;
- the target revision's Viewer Branch identity;
- `can_restore`;
- stable blocker codes plus human-readable messages.

Known blockers include read-only/inactive scope, dirty Working Draft, current-head
selection, uncaptured live Saved Revision component state, transient authoring state,
unsupported legacy-backed Run/Branch state, unsupported component/schema content and an
unavailable target Viewer Branch.

## Confirm boundary

Preflight never authorizes mutation by itself. The POST restore request submits the
server-returned head/draft/viewer snapshot and explicit confirmation. Confirm then
repeats all authoritative checks under `BEGIN IMMEDIATE`, performs component-specific
validation/restore, creates the pre-restore safety checkpoint, appends the new restore
revision and audit event, and commits atomically.

This means a preflight can become stale safely: confirm rejects the stale expected
snapshot rather than applying it.

## UI ownership

Saved Revision History consumes the server preflight rather than duplicating restore
rules in React. The Restore action is disabled while preflight is loading, invalid, or
blocked; all blocker messages come from the backend. Opening the confirmation dialog
binds the expected head, draft version and Viewer Branch directly from the reviewed
preflight response.

This is a technical save/load/recovery contract. It does not introduce product or
sporting rules.
