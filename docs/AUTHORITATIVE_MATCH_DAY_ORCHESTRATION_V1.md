# Authoritative Next Match Day v1

## Purpose

The canonical simulation path now has a first higher-level orchestration boundary above
`Next Match` and `Next Slot`: **Next Match Day**. It is deliberately derived from
the adopted `week_simulation_schedule.v2` Match Day metadata rather than from legacy
round names, event iteration order, or client-side loops.

This is a pre-alpha building block for later canonical `Next Round`, `Next Week`,
`Next Tournament`, and `Full Season` orchestration.

## Preview contract

`GET .../authoritative-simulation/next-match-day/preview` is read-only. It requires:

- a current competitive match slot;
- an adopted Week Simulation Schedule v2;
- a canonical Match Day on that slot;
- consecutive remaining global Simulation Slots for that Match Day;
- no Entry/WC process slot interleaved inside the frozen Match Day range;
- a current Saved Revision head.

The preview freezes the current Match Day ordinal, exact remaining slot ordinals,
group IDs, schedule fingerprint, position fingerprint and Saved Revision head.

## Commit contract

`POST .../authoritative-simulation/simulate-next-match-day` creates one durable parent
operation receipt. Each frozen slot is then executed through the existing
`simulate_next_slot` authority using a deterministic child command ID.

The parent persists the exact child command payload **before** that child starts.
Therefore:

1. already committed child slots are never rerolled on retry;
2. a lost response after a committed child is safe to retry;
3. an interrupted Match Day resumes from the exact frozen child command;
4. schedule changes, Saved Revision head changes, week changes, or chronology drift
   fail closed instead of being silently absorbed;
5. the parent becomes complete only after every frozen child receipt is complete and
   the canonical Position has advanced beyond that Match Day.

The Match Day operation is intentionally resumable rather than pretending the whole
day is one database transaction. Individual Simulation Slots retain their existing
atomic/exactly-once behavior and historical receipts.

## Admin UI

The canonical Simulation Admin panel exposes this boundary as a reviewed two-step
operation. **Review authoritative Next Match Day** loads the server-derived preview
and shows the frozen Match Day, global slots, competitive groups, Saved Revision and
schedule fingerprint. **Simulate reviewed authoritative Match Day** then sends only
the reviewed CAS inputs plus one stable command ID.

A normal network/response failure keeps that command ID and review so the Admin can
retry the exact resumable parent operation. A canonical 409 conflict discards the
stale review and refreshes current Position/Schedule instead of encouraging a retry
against changed history.

## Scope limits

Canonical `Next Round` is now implemented separately in
`docs/AUTHORITATIVE_ROUND_ORCHESTRATION_V1.md`. It derives the current
event/phase/round identity from V2 schedule metadata and freezes every required global
match slot through the last remaining target of that round, including explicitly
reported interleaved transit matches.

It also does not auto-cross Entry/WC process slots, Week Transition, Season Transition,
or a Saved Revision boundary. Those remain explicit canonical boundaries.
