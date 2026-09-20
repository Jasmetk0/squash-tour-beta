# Resolved application validation persistence v1

Application validity is upstream evidence for valid submissions and Tour entry. Once a
global entry-decision slot is completely resolved, that decision cannot be reconstructed
later from field cuts or UI state.

This slice therefore persists each
`ResolvedApplicationValidationSlot` as one immutable Run/Branch-owned object keyed by:

- FAX week;
- global decision-slot ordinal.

## Atomic downstream commit

`record_resolved_application_validation_slot(...)` first verifies that the same
Run/Branch/week/slot has not already been resolved differently.

It then projects the valid subset through the existing application pipeline:

resolved validation slot
→ valid application subset
→ simultaneous submission batch
→ persisted valid submissions
→ first Tour-entry triggers.

The validation slot and all downstream valid-submission effects use the same SQLAlchemy
transaction supplied by the caller.

If every application in the slot is invalid, the resolved validation evidence is still
persisted, but no submission or Tour-entry trigger is created.

Exact retry is idempotent. A different resolution for an already-resolved slot fails
closed before rewriting downstream history.

## Saved Revision order

Saved Revisions capture and restore the evidence in causal order:

1. player lifecycle;
2. resolved application validation slots;
3. valid application submissions;
4. definitive WC/RWC assignments;
5. first Tour-entry triggers;
6. sporting/simulation state.

Ordinary Season Transition and final Season closure use the same ordering.

Legacy restore is blocked if live validation-slot state exists but the Saved Revision
does not capture it.

## Deliberate boundary

This persistence layer still does not implement the actual eligibility/deadline policy.
It only preserves the complete, versioned result authority defined by the preceding
validation slice.
