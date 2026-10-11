# Mixed global entry + match slot chronology v1

The Master defines one global chronological sequence of Simulation Slots per FAX week.
The engine currently persists two specialized slot authorities:

- Run entry-decision slots;
- match Simulation Slots.

The match schedule is still match-specific, but its ordinals are global. Therefore
match ordinals may no longer be assumed to be a dense 1..N sequence when an entry slot
occupies a position between them.

## Match schedule semantics

`WeekSimulationSchedule` remains a schedule of match groups only.

Its slot ordinals must be:

- positive;
- unique;
- strictly increasing.

They may contain gaps **only** where a persisted Run entry-decision slot owns that
global ordinal.

The topological proposal assigns each dependency layer to the earliest available global
ordinal while skipping persisted entry ordinals. It does not move or invent entry
slots.

Implemented pre-alpha example:

- entry slot 1 → optional entry slot 2 → first match layer gets the next free global slot.

A new Entry slot may only commit after every earlier global ordinal is already complete.
For an Entry ordinal, **complete** means both the persisted decision authority and its
complete `ResolvedApplicationValidationSlot`; a decision-only slot is reserved but
still blocks later global execution.

The current bridge therefore supports a contiguous Entry-decision prefix before match
schedule adoption. Planning a future Entry slot between already-planned match layers
requires the later generic multi-kind slot planner/reservation authority and is not
claimed here.

A manually authored match schedule with slots 1 and 3 is rejected unless slot 2 is an
actual persisted entry-decision slot.

## Sporting checkpoint chain

Entry decisions do not alter match sporting state in this slice.

When materializing a match slot, the executor therefore chains from the latest earlier
**match** checkpoint, not blindly from global ordinal minus one.

If there is no earlier match slot, it starts from the opening sporting week state even
when one or more earlier global positions are completed Entry slots.

Every skipped ordinal before a match slot must be owned by a completed persisted Entry
slot. Entry persistence itself requires every earlier global ordinal to be complete,
so chronology cannot be backfilled out of order.

## Reservation safety

Chronology is protected before and after match-slot materialization:

- an existing entry slot blocks a match schedule or match slot at the same ordinal;
- an adopted match schedule blocks a later entry slot from taking one of its ordinals;
- a materialized match slot also blocks a later entry slot;
- Saved Revision validation rejects entry/match collisions and unexplained global
  gaps.

## Deliberate boundary

This is not the final generic multi-kind Simulation Slot schema. It is the minimum
interoperability layer needed to make today's separate entry and match authorities obey
one real global ordinal sequence without inventing the unresolved full slot taxonomy.
In particular, future mid-match Entry reservations remain outside this slice.
