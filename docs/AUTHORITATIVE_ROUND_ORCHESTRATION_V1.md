# Authoritative Next Round v1

## Purpose

The canonical simulation path now has a round-level orchestration boundary above
`Next Slot` and `Next Match Day`.

`Next Round` means: **finish the nearest unfinished round identity owned by the
current canonical V2 schedule slot**. The identity is the immutable tuple:

- `event_id`
- `draw_phase` (`qualification` or `main`)
- `round_number`

It does not mean "all matches with the same round number across the week" and does
not copy legacy event iteration order.

## Chronology horizon

A round can span multiple Match Days, and other tournaments can be interleaved in
the same global Simulation Slot chronology.

The preview therefore freezes two related sets:

1. **Round target slots** — remaining slots belonging to the current round identity.
2. **Chronology horizon** — every global match slot from the current position through
   the last remaining target slot.

Any interleaved match slot from another event/phase/round is exposed as a **transit
slot**. It is executed only because global chronology cannot be skipped. Slots after
the last target slot are not part of the command.

If the horizon would cross an Entry or Wild Card process slot, the command fails
closed. The first version does not silently resolve process decisions on behalf of
the Admin.

## Preview and commit

`GET .../authoritative-simulation/next-round/preview` is read-only and returns the
round identity, target slots/groups, chronology horizon, transit slots/groups, Week
Schedule fingerprint, Position fingerprint and Saved Revision head.

`POST .../authoritative-simulation/simulate-next-round` creates a durable parent
receipt and executes the frozen horizon through deterministic child `Next Slot`
commands. Each child payload is persisted before execution.

This gives the same resumability contract as Next Match Day:

- committed child slots are not rerolled;
- response loss is safe to retry with the same parent command ID;
- an interrupted round resumes from the exact frozen child command;
- schedule, Saved Revision, week or chronology drift fails closed;
- the parent completes only after every frozen horizon child is complete.

## Admin UI

The canonical Simulation Admin panel exposes a two-step review:

1. **Review authoritative Next Round**
2. **Simulate reviewed authoritative Next Round**

The review explicitly shows the selected event/phase/round, target matches,
chronology horizon and transit matches. A normal response/network failure preserves
the same command ID for retry. A canonical conflict discards stale review and
refreshes Position/Schedule.

## Scope limits

Canonical `Next Tournament` is now implemented separately in
`docs/AUTHORITATIVE_TOURNAMENT_ORCHESTRATION_V1.md`. It expands the same frozen
chronology-horizon contract from one round identity to the full current event and
requires canonical tournament-source closure. `Next Week`, `Next Season` and
`Full Simulation` remain wider follow-up ranges that must compose canonical
boundaries rather than reusing the legacy branch wrapper.
