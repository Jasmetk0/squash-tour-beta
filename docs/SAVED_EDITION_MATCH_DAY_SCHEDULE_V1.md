# Saved Edition Match Day Schedule v1 — 13 October 2026

A bounded, historical **read-only** schedule from the exact selected Saved
Revision, not live Admin, Viewer HEAD, a Calendar label, or an inferred time.

## Authority

`WeekSimulationSchedule` v2 is the only source of Match Day number, within-day
order, global slot number, event id, phase and round. It is validated against
the saved row fingerprint, Run, original owning Branch and exact sport season
and week. The validator rejects duplicates, invalid canonical metadata,
foreign Slot plans and mismatched schedule provenance. A persisted Slot plan
can add an exact Match ID if its group/event and fingerprint match; otherwise
the Match ID stays absent rather than being invented. Scorelines are shown
**only** where the canonical published Tournament Result independently
contains the same actual Match ID.

This revision adds nullable `match_schedule` to the existing
`run_saved_tour_edition.v1` payload, without changing Calendar contracts,
sporting state or legacy result models. Historical v1 global schedules had
no Event/Match Day metadata: they remain `null`, not attributed to a
specific Edition. Missing v2 schedules or uninitialized Slot plans similarly
do not create fake results. The UI shows Match Day as an **ordinal**,
not an actual date/time; no hour, court or day-of-week is inferred.

## UI

Edition's existing **Schedule & matches** tab displays actual Saved global
slot, Match Day and order, phase/round, optional saved Match ID and, when
independently published, the result. Main (including group) is first,
Qualification follows with in-page anchors. Results tab remains separate.
When only published results exist, they are explicitly labeled as match
result evidence, **not** a schedule. All filters/Back, Run/Branch/season/
revision context and unsupported checkpoint guards are preserved.

## Acceptance

- New focused application tests for two simultaneous Editions, exact Match Day
  chronology, linked and uninitialized Slot plans, v1 missing attribution,
  foreign/forged schedules/plans and duplicates.
- Frontend component tests for non-inferred days/results; TypeScript
  response guards reject wrong original source Branch, event, season, week,
  duplicate ordinal/group and corrupt fingerprint.
- Existing production FastAPI + real Chromium Saved Replay journey checks
  the canonical saved event's schedule, group Match ID linkage, UI evidence,
  and bit-for-bit equality after SQLite restart.

Not addressed: exact wall-clock match start, court assignment, entire
hybrid-specific timeline from group schedule authorities, or unpersisted
future match plans. These require explicit authority and later separate
implementation slices.
