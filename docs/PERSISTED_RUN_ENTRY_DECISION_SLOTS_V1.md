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
slot or chronology-aware canonical WC decision already owns the same global position.

`AuthoritativeSlotMatchExecutor.create_slot(...)` performs the symmetric checks and
rejects a match slot when a persisted entry-decision or canonical WC-decision slot owns
that position.

`TournamentWildCardAuthority` v2 freezes its own FAX week/global ordinal. WC resolution
is complete when that immutable authority is persisted, so later Entry/match slots may
count the WC ordinal as completed. A WC decision cannot overtake an unresolved earlier
Entry slot, incomplete match slot, missing ordinal or an ordinal reserved by the adopted
match schedule.

Thus technical execution order cannot create two different “slot 4” authorities.

## Reserved vs completed Entry slot

Persisting `RunEntryDecisionSlotAuthority` freezes the slot's complete simultaneous
candidate decisions and reserves its global ordinal. It does **not** by itself make
the slot chronologically complete.

The Entry slot becomes complete only when the corresponding
`ResolvedApplicationValidationSlot` exists for the same Run/Branch/week/ordinal.
That resolution covers every preserved application decision exactly once and can then
atomically create valid submissions plus first Tour-entry triggers.

A later Entry slot or a later match slot therefore fails closed while any earlier
Entry ordinal is still only reserved and has no complete validation result.

## Saved Revision history

Saved Revisions capture entry-decision slots before application-validation results:

1. lifecycle;
2. Run entry-decision slots;
3. resolved application-validation slots;
4. valid submissions;
5. definitive WC/RWC assignments;
6. first Tour-entry triggers;
7. later sporting / match-slot state.

Before restore, both current and target Saved Revisions are checked across all three
currently separate global-slot owners: Entry decisions, chronology-aware WC decisions
and match slots. A historical snapshot that claims the same Run/Branch/week/ordinal for
more than one kind fails closed. Historical WC v1 authorities carry no global slot and
therefore remain outside this chronology without being rewritten.

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
separate Entry, WC-decision and match persistence paths from diverging chronologically.
