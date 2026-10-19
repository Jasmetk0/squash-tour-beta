# Native 15yo birthday plus genuine Official sporting development (pure v1)

## Why this boundary matters

Signed native admission (#1555) produces an accurate next-week 57-attribute
birth/Health/lifecycle proposal, but cannot apply itself as a weekly sporting
transition: existing athletes must *first* undergo the completed week's
deterministic development, current Form recovery, match-sharpness decay and
weekly fatigue recovery. A 15-year-old arriving at the newly opened week
must receive neither a fictional match nor an extra older-week update.

The official `develop_and_recover` kernel currently consumes World-style
birth identities and rejects anything outside the original InitialWorld.
This immutable adapter supplies the **current verified lifecycle** as the
profile input instead, using the exact same official kernel, W-scaled RNG
and recovery rules. This allows real born-in-Run players to participate in
*subsequent* development without modifying or duplicating the historic
development math. Retirement policy is still taken from the stored lifecycle,
not current global defaults.

## `calendar_native_sporting_birth_advance.v1`

- Takes exact current-week sporting checkpoint and matching authenticated
  lifecycle, the Signed native birth event for precisely the consecutive
  next week, a caller-supplied seed, effective development policy and
  verified per-player played counts from the *completed* week.
- Requires current sporting and lifecycle IDs to agree exactly.
- Develops and recovers only existing players using **the existing official
  kernel**, preserving all match-related Form/sharpness/fatigue effects.
- Appends newborns at the target-week opening using the original **57
  birth-profile attributes, potential and bootstrap defaults**. Newborns
  receive no development, fatigue or play counts in their birth week.
- Exposes developed, recovered and final sorted rosters, their canonical
  fingerprints, source checkpoint/lifecycle hash, source native birth
  event, command seed, policy and exact played counts. No player is
  silently dropped or duplicated.
- The *next* proposed week includes the now-present newborn among the
  current athletes, so he receives ordinary deterministic W-aware growth.

`calendar_native_admission_week_projection.v1` additionally binds the
whole sporting-week proposal to #1555's Signed **Health + lifecycle +
57-attribute admission**. It requires exact common birthday evidence,
checkpoint owner, same old and target roster identities and unchanged
newborn profile, then hashes the union. It cannot publish, save or write.

## Strict limitations

This is a deterministic **read-only staging adapter**, not production
Week Transition or sport persistence v11. The caller must authenticate
previous Signed HEAD, true played-match counts, actual checkpoint, source
and effective seasonal policy. This layer does not override them.
It deliberately does **not** alter historical checkpoint v1–v10,
`CalendarSportingWeekAdvance` v1–v3, Saved history, Health healing,
Entry, ranking, Tour initialization, or the
`intake_source_requires_native_calendar_materialization` blocker.
`signed_writer_supported` is fixed to false.

Production activation requires a new supported checkpoint/event schema
with exact restart/restore/fork replay, transactional lifecycle/Health and
Ranking/Entry publication under the same command. Do not enable native
birth adoption until those cross-domain validators agree.

## Tests

Six W52/W61/W80 plus year/season offset cases compare the old players'
**full developed and recovered records** byte-for-byte with the existing
official kernel; check that newborns appear only in the new week; verify
a second-week development including prior newborns; bind the complete
Signed Health/lifecycle/admission projection; guard against foreign
Run/Branch, mismatched counts, stale/rehashed birth event, forged
checkpoint/roster, and invalid seeds. Every result is JSON replayable.
