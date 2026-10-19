# Native Run prospect birth → versioned lifecycle v4 (staging boundary)

## Implemented

A **pure, production-derived** `calendar_prospect_birth_event.v1` now describes
the exact week a 15-year-old prospect can join a configured Run. Every birth is
tied to the **Saved Run prospect source fingerprint**, the fingerprint of its
canonical raw record, the fully validated **57-attribute** sporting profile,
and the deterministic original profile/development/potential seeds. Event
provenance and player identities are independently hashed.

This replays on W52, FAX W61 and W80 with an arbitrary native season-to-year
offset, including last Week → next Season Week 1. Prospects join precisely
on their own 15th birthday; future prospects never appear early. Foreign
World Package, source policies, malformed calendar/birth identity, record
collisions, seed/profile drift and forged event/lifecycle receipts are
rejected.

`advance_calendar_lifecycle_with_prospects` performs a **real pure
lifecycle transition**: consecutive week birthday/retirement and completed
Entry processing for original players plus sorted new, active, entry-free
15-year-olds. The successor is explicitly
`player_lifecycle_calendar_state.v4`, retaining its v3 predecessor
fingerprint and embedded birth evidence. Historical v2/v3 models, hashes,
and old branch snapshots are unchanged. Subsequent v4 steps retain entrants.

The Admin's Saved-authenticated
`GET /admin/runs/{run_id}/branches/{branch_id}/calendar-tour/prospect-intake/preflight`
now additionally reports the exact **proposed** v4 roster fingerprint, birth
event fingerprint and count when a valid native cohort is due. Full hidden
profiles are retained inside the proposed domain receipt, not leaked through
the public response. The read-only route never mutates SQLite or Working.

## Not yet enabled

Production Tour does **not** persist the v4 projection. To activate players,
the new receipt must also be consumed by a versioned sporting checkpoint,
Health, ranking, tournament Entry and immutable Saved/restart/fork/restore
validators in **one validated writer transition**. Legacy
`intake_source_requires_native_calendar_materialization` and initial
Tour initialization guards remain intact; no source is silently converted.

Tests: pure W52/W61/W80 and season boundaries, chained v4 transitions,
no-change legacy fingerprints, original 57 profile regeneration,
corrupted/mixed-source/foreign-country/identity/provenance rejection, plus
real HTTP/SQLite Saved Tour preflight and restart with zero activation.
