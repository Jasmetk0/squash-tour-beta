# Match Day Schedule V1

Status: pre-alpha hard-constraint foundation.

Product authority remains `SQUASH_ENGINE_MASTER_VISION.md`. This document describes
the implemented compatibility boundary; it does not add new sporting policy.

## Why Week Simulation Schedule v2 exists

Historical `week_simulation_schedule.v1` is a global dependency schedule. Independent
matches may share one global Simulation Slot and therefore one pre-slot sporting
snapshot. That is useful for truly simultaneous independent work, but it is not the
Master Match Day contract for matches played sequentially during one tournament day.

New automatically derived tournament schedules therefore use
`week_simulation_schedule.v2`.

V1 remains readable and keeps its historical fingerprint payload exactly. Existing
Saved Revisions, manual compatibility schedules and fork replay do not get silently
reinterpreted as V2.

## Two chronology axes

V2 keeps the global Simulation Slot ordinal and adds:

- `match_day_ordinal`
- `match_order`
- `event_id`
- `draw_phase` (`qualification` or `main`)
- `round_number`

Every V2 competitive match owns exactly one global match slot. Multiple matches may
share one Match Day, but never one global match slot.

This means same-day matches execute in stored `match_order`. After one match commits,
its normal sporting effects/checkpoint become the opening sporting truth for the next
global match slot. Later matches therefore see current Form/Sharpness/Fatigue and other
canonical sporting state rather than the beginning-of-day snapshot.

## Implemented hard constraints

The automatic proposal currently enforces:

1. every competitive group is scheduled exactly once;
2. every feeder is on an earlier Match Day than its dependent match;
3. Qualification competitive rounds complete before the event's Main Draw begins;
4. a directly known player cannot occupy two matches on one Match Day;
5. within-day order is deterministic from event, phase, round, bracket position and
   match identity;
6. each V2 global match slot contains exactly one competitive group;
7. Entry and Wild Card decision global ordinals remain reserved and are skipped;
8. proposal/adoption remains immutable, fingerprinted, CAS-guarded and exact-retryable.

For the currently supported single-week canonical tournament flow, Qualification round
numbers map to the first Match Days and Main round numbers follow after the last
competitive Qualification round.

## Persistence, history and branches

Week Simulation Schedule remains part of the authoritative Simulation Slot Saved
Revision component. V2 metadata therefore participates in the schedule fingerprint,
Working Draft save identity, restore and materialized Branch fork identity.

Fork remap changes Branch-bound schedule identity while preserving Match Day / match
order metadata. Historical V1 schedule fingerprints are calculated from their original
V1 payload shape and do not include V2 null/default fields.

## Deliberate follow-ups

This slice is not the complete generic Round/Match Schedule system. It does not claim:

- multi-week Round Schedule ranges;
- explicit configurable rest-day ranges beyond the current next-round/day hard
  boundary;
- court assignment or court-capacity scheduling;
- travel/acclimatization optimization;
- carryover optimization between consecutive events;
- fairness scoring or schedule-quality optimization;
- automatic reshuffling after later tournament configuration changes;
- a finalized Final Commitment deadline/preference policy.

Those rules should be added only when their Master contract is sufficiently decided.
