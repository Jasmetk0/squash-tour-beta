# Definitive Wild Card assignment persistence v1

Master Vision §9.2 makes a **definitive valid WC/RWC assignment into the field** the
second formal Tour-entry path. Preliminary offers and mere RWC ordering do not qualify.

This slice persists the time-aware
`DefinitiveWildCardAssignmentAuthority` as append-only Branch-owned evidence and
coordinates it with the same first `PlayerTourEntryTrigger` store used by valid
tournament applications.

## Rules

- every definitive WC/RWC assignment remains immutable historical evidence;
- exact assignment-identity retry is idempotent;
- the first qualifying WC assignment creates Tour-entry truth only when the player has
  no earlier first-entry trigger;
- later WC assignments remain historical but never rewrite career entry;
- if a valid application already created earlier Tour entry, a later WC is persisted
  while the application remains the first-entry source;
- an out-of-order WC that predates persisted first-entry truth fails closed;
- distinct first-entry authorities in the exact same global slot require explicit
  slot-level arbitration rather than technical processing order.

Saved Revisions capture both valid application submissions and definitive WC
assignments before the shared Tour-entry trigger component is restored.
