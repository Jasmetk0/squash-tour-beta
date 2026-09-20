# Persisted Run entry-decision slots v1

Entry decisions belong to the same product-level global Simulation Slot chronology as
matches, but the current persisted `SimulationSlotModel` payload is still
match-specific. Its `SimulationSlotPlan` requires match groups and match events, so an
entry-decision slot cannot honestly be encoded there without a larger generic-slot
refactor.

This slice therefore persists `RunEntryDecisionSlotAuthority` separately while
preserving one crucial invariant:

> one Run / Branch / FAX week / global slot ordinal can belong to only one slot kind.

## Live collision guard

`RunEntryDecisionSlotStore.append(...)` rejects an entry slot when a persisted match
slot already owns the same global position.

`AuthoritativeSlotMatchExecutor.create_slot(...)` now performs the symmetric check and
rejects a match slot when a persisted entry-decision slot already owns that position.

Thus technical execution order cannot create two different “slot 4” authorities.

## Saved Revision history

Saved Revisions capture entry-decision slots before application-validation results:

1. lifecycle;
2. Run entry-decision slots;
3. resolved application-validation slots;
4. valid submissions;
5. definitive WC/RWC assignments;
6. first Tour-entry triggers;
7. later sporting / match-slot state.

Before restore, both current and target Saved Revisions are checked for collisions
between the entry-slot component and the match-slot component. A historical snapshot
that claims the same global position for both kinds fails closed.

## Persistence identity

One immutable entry-decision slot is keyed by:

- Run;
- Branch;
- FAX week ordinal;
- global decision-slot ordinal.

Exact retry is idempotent. A different authority for the same global position conflicts.

## Deferred generic-slot refactor

This is deliberately an interoperability bridge, not the final generic Simulation Slot
schema. A later refactor may unify entry, match, announcement, commitment and other slot
event kinds under one generalized slot plan. Until that exists, this slice prevents the
separate entry and match persistence paths from diverging chronologically.
