# Reviewed point preparation from real calendar knockout — v84 continuation

## Operational boundary

A native W52 or W80 Run/Branch with a **Signed Saved**
`calendar_opening_knockout.v1` result can prepare and explicitly Save
an operator-configured point distribution. The four players, placements and
winning finalist come exclusively from the previously played MatchEngine
semifinals/final; none can be supplied or changed by the points command.
The entered table has three integer values `champion >= finalist >= semifinal`,
distinguishes champion from semifinal, and has a required authored label,
fixed `source_kind=admin_explicit_reviewed` and Run-year-long `validity_weeks=W`.
The proposed first publication is **Season 1 Week 2**, never Week 1.

**This is not an Official ranking publication or Category/Edition policy.**
The policy is explicit operator-configured source data, not a claim that the
existing original Category/Edition policy was authored or inherited. Until
Category/Edition binding and a safe calendar-native Week Transition are
complete, these immutable prepared points cannot affect current World
Tour/Official Ranking, Viewer or tournament records. The explicit
`publication_status=prepared_not_official` survives Save/restart/restore.

## One fully usable workflow

1. Real W52/W80 Saved population -> play real four-player tournament using
   `calendar-opening-knockout/simulate` -> existing explicit immutable Save.
2. Admin configures the stage table and label, calls
   `POST .../calendar-opening-knockout/awards/review`. The server rereads
   the Saved branch HEAD and exact verified live MatchEngine knockout within
   one SQLite read transaction. The preview signs the Saved HEAD content hash,
   original bracket fingerprint, policy and four derived placements.
3. Admin explicitly confirms review and calls
   `POST .../calendar-opening-knockout/awards/apply` with exact preview
   fingerprint and idempotent command ID. Within `BEGIN IMMEDIATE`, the
   live saved-bracket row is replaced by a strictly validated
   `calendar_scored_opening_knockout.v1` row embedding the original v1
   bracket, frozen operator policy, four stage awards and W2 timing.
   Response-loss retry with the same command is exact; changed command fails.
4. The existing `calendar-opening-knockout/save/preview` and
   `.../save` perform the **second explicit immutable Saved Revision**.
   Before Save the UI marks points as unsaved; afterward the Signed Saved
   payload contains the complete prepared policy and match evidence.
5. Cold restart loads original bracket/replay and prepared policy unchanged.
   Same-Branch restore to the older Signed knockout or pre-match population
   removes points appropriately; old signed content/hash stays untouched.
   Cross-Branch forking a scored sporting revision remains safely blocked.

The same `calendar_standalone_match` Saved content key/SQLite row family
is used for the new versioned schema. An explicit schema discriminator
preserves old Signed v1 exhibition and knockout content byte-for-byte.
The underlying historical MatchEngine inputs and rally/timeline/stamina
logs are nested, not recomputed from present-day defaults.

## Required checks

- `tests/api/test_calendar_knockout_awards_flow.py`: W52/W80 real API/
  SQLite from initial population to Saved match -> reviewed points -> new
  immutable Saved head; idempotent retry, stale/wrong policy, tamper,
  cold restart, restore to earlier Signed bracket.
- Run directly affected existing standalone match, knockout, calendar
  extension, restore and ranking source-history tests as appropriate.
- The existing real Chromium Shell now covers both existing exhibition
  and new knockout with prepared points, second manual Save, CS/EN and reload.
- Scope remains bounded to one first-week native knockout per Branch;
  no native Official publication, Week Transition, general tournament
  bracket, ranking correction/zero, world events, full season or Full
  Simulation release acceptance is claimed.

Next: bind original configured Category/Edition point policy and effective
versions to tournament authority, migrate persisted calendar-native
ranking publication plus dependency-reviewed Week/Season Transition.
