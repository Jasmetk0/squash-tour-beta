# Player Tour-entry trigger v1

This contract represents the **first formal MSA Tour-entry trigger** already decided
by Master Vision §9.2. It is intentionally smaller than the future application/Wild
Card workflows.

## Canonical triggers

A pre-Tour prospect becomes a `Tour Player` when either:

1. the player makes the first **valid MSA Tour tournament application**; acceptance
   into Main Draw or Qualification is not required, and a later capacity rejection
   does not undo Tour status; or
2. the player receives a **definitive valid Wild Card assignment** into the field.

A preliminary WC offer, reserve-list presence, junior competition, field-cut
acceptance, draw generation, or match participation is not a substitute trigger.

## Contract

`PlayerTourEntryTrigger` binds:

- Run and Branch;
- stable player and Tournament Edition/event identity;
- exact trigger kind;
- exact FAX week;
- global Simulation Slot ordinal inside that week;
- immutable upstream evidence ID and SHA-256 fingerprint;
- explicit provenance.

The trigger fingerprint is deterministic over the complete payload.

## Deliberate non-goals

This slice does **not** yet:

- decide whether an application is valid;
- create application-submission persistence;
- make the existing `TournamentEntryApplication` field-cut payload the submission
  authority;
- treat the legacy Admin wildcard action as branch-owned lifecycle authority;
- mutate `PlayerLifecycleWeekState`;
- retroactively edit the current published Official Ranking;
- implement NR display/projection;
- implement prospect AI or choice of first tournament.

The current canonical Tournament Entry Field application object is downstream
field-cut evidence and does not carry an authoritative submission week. Therefore it
must not silently create Tour status.

## Next integration boundary

The next persistence slice should create append-only, Branch-owned trigger evidence
with Saved Revision/recovery support. Only then should a lifecycle projection consume
the first trigger for a player and expose `tour_entry_week=trigger.trigger_week`.
Current Official Ranking remains unchanged; the player joins the following Official
snapshot as the existing lifecycle/ranking contract requires.
