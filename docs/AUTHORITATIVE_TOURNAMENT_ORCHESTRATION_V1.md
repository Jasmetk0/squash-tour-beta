# Authoritative Next Tournament v1

## Purpose

The canonical simulation path now exposes a tournament-level orchestration boundary.

`Next Tournament` means: **finish the tournament identified by the current canonical
V2 schedule slot's `event_id`**. The server freezes every remaining slot belonging
to that event and the exact global Simulation Slot chronology required to reach the
last one.

This does not use legacy event iteration order and does not mean "simulate every
tournament in the week".

## Chronology horizon

Multiple tournaments can be interleaved in one week. The preview therefore freezes:

1. **Tournament target slots** — remaining competitive slots whose `event_id` is the
   selected tournament.
2. **Chronology horizon** — every global competitive slot from the current position
   through the tournament's final remaining target slot.
3. **Transit slots** — interleaved matches owned by other tournament events that must
   execute because global chronology cannot be skipped.

Nothing after the selected tournament's last remaining slot belongs to the command.

If the horizon would cross an Entry or Wild Card process slot, the operation fails
closed. The first version never resolves an explicit Admin decision as a hidden side
effect of tournament simulation.

## Preview and commit

`GET .../authoritative-simulation/next-tournament/preview` returns a read-only frozen
scope containing the event ID, target slots/groups, chronology horizon, transit
slots/groups, Week Schedule fingerprint, Position fingerprint and Saved Revision
head.

`POST .../authoritative-simulation/simulate-next-tournament` creates one durable
parent operation receipt. Every frozen horizon slot executes through the existing
authoritative `Next Slot` command with a deterministic child command ID.

The parent only completes after:

- every frozen child receipt is complete;
- Position has advanced beyond the frozen horizon; and
- exactly one Run/Branch-owned tournament ranking source exists for the selected
  `event_id`.

The result exposes that `OwnedTournamentRankingSource` fingerprint as proof that the
selected tournament closed through the normal canonical result/points pipeline.

## Retry contract

Each child payload is persisted before execution. Therefore response loss or process
interruption can retry the same parent command without rerolling committed matches.

Schedule changes, Saved Revision changes, week changes or chronology drift fail
closed instead of being silently absorbed.

## Admin UI

The canonical Simulation Admin panel provides:

1. **Review authoritative Next Tournament**
2. **Simulate reviewed authoritative Next Tournament**

The review shows the selected event, target matches, complete chronology horizon and
all transit matches. A normal network/response failure preserves the same parent
command ID. A canonical conflict discards stale review and refreshes Position and
Schedule.

## Scope limits

Canonical `Next Week` is now implemented separately in
`docs/AUTHORITATIVE_WEEK_ORCHESTRATION_V1.md`. It inherits the contained sporting
prerequisites, freezes every remaining current-week competitive slot and composes the
existing atomic Week Transition without hiding process blockers. `Next Season` and
`Full Simulation` remain wider follow-up ranges.
