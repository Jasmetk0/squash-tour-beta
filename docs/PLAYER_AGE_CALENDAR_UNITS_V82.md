# Player age calendar units — v82 migration foundation

The existing pure birth/age entrypoints in `domain/calendar/season_weeks.py`
accept an explicit keyword `weeks_per_calendar_year`:

- completed age at a calendar position;
- birth-year derivation for an intended age and known birth week;
- completed weeks since birth;
- calendar and season position of the fifteenth birthday (the latter also
  accepts the explicit season offset).

Omitting the keyword preserves the historical FAX scale of 61 exactly. There
are no new fields in old lifecycle, player or Saved payloads, no old birthdays
are sampled again, and no persisted hash is rewritten. Invalid scales or a
birthday outside the supplied W are rejected. A FAX birthday in Week 61 must
not silently become Earth Week 9 or 52.

`synthesize_birth_year_week` accepts the same explicit scale for **new** identity
sampling. Its original seed material and default modulo remain unchanged. It
is not an importer or conversion command for an existing birth identity.

Tests cover exact 18-year elapsed weeks, birthday boundaries, inverse age/birth
calculation, fifteen-year activation through crossing-year offsets, scales
1/7/52/61/80, deterministic identity sampling, invalid inputs and legacy values.
Both existing callers and the new explicit-scale paths are exercised. This is
pure domain support, not a claim that an authoritative W52 lifecycle is installed.

## Required caller migration before enabling new sporting clocks

- `PlayerLifecycleWeekState` still validates legacy RankingWeek and the
  2000/61 calendar. Its schema/fingerprint transition must be explicit.
- Initial-pool allocation/birth sampling and `SeasonActivePlayer` bootstrap
  still own legacy bounds and season labels. Feed the verified Run clock into
  the full generation/bootstrap chain, not just the age helper at the end.
- Lifecycle bootstrap/prospects, retirement and Tour entry must share the
  same saved time basis and reject incompatible stored identities.
- The provisional sporting policy still expresses its change chance weekly.
  Version annual normalization and old replay separately before passing a new
  W through production. Do not multiply age by W/61 or rescale every fatigue,
  recovery, sharpness, PR, entry-window or penalty coefficient.
- RankingWeek ordinals, result validity, transition boundaries and Full
  Simulation frozen goals must migrate coherently. The existing execution
  guards remain necessary. Exact growth calibration remains a testing task.

This branch is based on merged #1495 and does not depend on the calendar
creation PR. It intentionally avoids conflicting CURRENT_STATE/ROADMAP edits;
that creation branch owns the current active summary checkpoint.
