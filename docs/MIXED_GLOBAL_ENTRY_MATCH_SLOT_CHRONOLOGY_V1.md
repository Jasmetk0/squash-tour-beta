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

Examples:

- entry slot 1 → first match layer gets global slot 2;
- match layer 1 → entry slot 2 → next match layer gets global slot 3.

A manually authored match schedule with slots 1 and 3 is rejected unless slot 2 is an
actual persisted entry-decision slot.

## Sporting checkpoint chain

Entry decisions do not alter match sporting state in this slice.

When materializing a match slot, the executor therefore chains from the latest earlier
**match** checkpoint, not blindly from global ordinal minus one.

If there is no earlier match slot, it starts from the opening sporting week state even
when one or more earlier global positions are entry slots.

Every skipped ordinal between two match slots must be owned by a persisted entry slot.

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
