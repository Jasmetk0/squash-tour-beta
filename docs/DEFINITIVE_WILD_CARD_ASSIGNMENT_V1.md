# Definitive Wild Card assignment authority v1

Master Vision §9.2 distinguishes a preliminary WC offer or Reserve Wild Card ordering
from the exact moment that creates MSA Tour status.

A prospect becomes a Tour Player through the WC path only when a **valid WC is
definitively assigned into the field**. No separate accept action exists. An unfilled
slot, preliminary offer, or mere presence in the RWC ordering is not enough.

`DefinitiveWildCardAssignmentAuthority` therefore timestamps an already-canonical
`TournamentWildCardAuthority` slot with:

- exact FAX week;
- global Simulation Slot ordinal;
- active player and Tournament Edition identity;
- WC slot index;
- original-WC vs RWC source and reserve ordinal where applicable;
- source WC command ID, authority fingerprint, Entry Field fingerprint and field
  sequence.

The authority can only be created from an active resolved WC/RWC slot. An unfilled or
missing slot fails closed.

Both canonical first-entry sources now project into the same
`PlayerTourEntryTrigger` contract:

1. valid tournament application submission;
2. definitive valid WC/RWC assignment.

This remains a pure domain boundary. Persistence and atomic command integration remain
separate so the submission/WC evidence and the player's first Tour-entry trigger can
later commit in one transaction without inventing timing from downstream field state.
