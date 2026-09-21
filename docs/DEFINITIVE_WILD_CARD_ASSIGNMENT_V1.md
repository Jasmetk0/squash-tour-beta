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

Canonical WC resolution now has a chronology-aware v2 form. New canonical writers may
freeze the exact FAX week and global Simulation Slot ordinal directly on
`TournamentWildCardAuthority`; historical v1 authorities remain fingerprint-compatible.
A definitive WC/RWC assignment created from v2 must reuse that exact position and cannot
supply a different week or slot ordinal.

The persisted v2 WC authority is itself a completed non-match decision slot: Entry and
match slot writers reject the same position, later global slots may count the WC ordinal
as completed, and Saved Revision collision checks include v2 WC positions.

This remains a pure domain boundary. The next application/API slice must derive the
current week/slot from authoritative Run position, resolve WC/RWC authority and record
all resulting definitive assignments plus first Tour-entry triggers atomically; clients
must not invent chronology.
