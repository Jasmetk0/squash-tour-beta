# Copied-FAX current Entry decision bootstrap

## Purpose

Advance the copied-FAX release fixture through the real shared-snapshot Entry AI boundary without inventing the still-open automatic application eligibility/deadline policy.

## Reviewed flow

The helper uses `AuthoritativeRunSimulationDriver.position()` as the source of truth for the exact current Entry slot. Preview then:

- requires `current_slot_kind=entry`,
- uses the Position's exact slot ordinal,
- derives current-week World Tour event IDs from the Run-owned Calendar Package,
- calls the production `preview_entry_decision_slot()` with one shared snapshot and deterministic seed,
- freezes Saved Revision, Position, batch, application-decision and slot fingerprints.

Apply re-runs Preview, rejects stale evidence and commits through the production `commit_entry_decision_slot()` path.

## Explicit boundary

This slice does not decide application validity. The current Master/technical plan still leaves the automatic eligibility/deadline validator unresolved.

Therefore a successful Apply returns:

- `validation_required=true`,
- `validation_policy_status=automatic_policy_unresolved`.

The next acceptance blocker is intentionally the existing explicit Application Validation authority, not a fabricated Entry Field.

## Why this matters

The copied-FAX long-run path now reaches the exact point where sporting-policy work is genuinely missing. Infrastructure already exists for shared-snapshot Entry decisions, immutable slot ownership, explicit validation outcomes, valid application submissions and Entry Field construction.