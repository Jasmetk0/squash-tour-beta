# Native Tour Signed Records v1 — bounded career leaderboard / holder-history candidate

## Authority and scope

**Base:** owner-merged PR #1547 (`buuk` at
`93a3f946e86af8265b8e7539d6c6ffcd174f3282`).
The new report is **read-only**, derived from exactly one fully validated
Saved Revision native Tour + Saved InitialWorld. It has no RNG, no new
sporting write authority, no manual/automatic Save, no new records table,
no new canonical record flags, and cannot unlock unsupported Full Simulation.
It reuses the per-completed-season authoritative
`native_tour_season_summary`, which itself requires genuine played
MatchEngine receipts and confirmed Tour Editions (the Signed sporting
lineage is authenticated before reading).

Endpoints:

- `GET /admin/runs/{run_id}/branches/{branch_id}/calendar-tour/records`
- `GET /viewer/runs/{run_id}/calendar-tour/records`

Both accept:
- `as_of_season_index` — the last **Saved completed** season to count;
  if omitted use the latest Signed closed season.
- `from_season_index` — inclusive first **Saved completed** season
  (default S1 index 0).
- `country_code` — optional exact uppercase three-character national
  identity, filtering **both** Players and Countries, *including* record
  holder history, from the beginning of the requested period.
- `leaderboard_limit` — default 20, 1–100 per metric; **all** tied
  record holders are always returned even when a display leaderboard
  is shorter.

Unknown/future/in-progress/foreign season, invalid filter or Run/Branch,
missing Saved, and corrupted sporting receipts are rejected; no
Working-Draft-born record is made public. The Viewer uses the one current
Viewer Branch Saved Revision, not the selected Admin Branch nor an
uncommitted draft; the Admin uses the selected Branch's authenticated Saved
HEAD. The exact Saved Revision ID is returned for UI provenance checks.

## Extensible native record catalog

Record IDs are deliberately versioned and scoped:

| Owner | Record metric |
| --- | --- |
| Player | `native_tour.player.titles.v1` |
| Player | `native_tour.player.finals.v1` |
| Player | `native_tour.player.awarded_points.v1` |
| Country | `native_tour.country.titles.v1` |
| Country | `native_tour.country.finals.v1` |
| Country | `native_tour.country.awarded_points.v1` |

These are genuine per-Edition Champion, losing Finalist and **original
Edition awarded points**, accumulated across the selected inclusive
period. They are NOT wins in individual matches, ranking Best N points,
Race points, national team results or the season-end canonical prize
book. Titles and finalist finishes can include unranked Editions if
their authentic placements are confirmed, while their awarded points
remain 0 according to their frozen table. The all-world
`completed_edition_count` counts eligible global completed Editions,
even with a country filter: the filter scopes record competitors, not
the identity of played tournaments.

The career leaderboards use competition ranking (e.g. 1, 1, 3) and
deterministic identity tiebreak ordering. Record holders with equal
maximum strictly positive value are **all** co-holders; 0 or an empty
season produces no invented holder. Holder history records each
changed record maximum or co-holder set only **at the signed Season
closure**, not a fictional match date, with `established`,
`improved` or `tied` and the immutable Season Transition command ID.
Within the fixed selected period, `from` resets cumulative totals
and the record history: it does not pretend previous-year totals or
record lineage remain inside a later fixed window.

CS/EN Admin can select inclusive period and optional ISO-3 country,
then explicitly request all 6 metrics, their ordered leaderboards,
all co-holders and chronology. Reports never initiate a command Save.

## Testing / release boundaries

- Focused pr-critical domain tests cover two signed Seasons, co-holder
  tie semantics, historical as-of isolation, post-S1 subset and country
  recalculation, leaderboard truncation without co-holder loss,
  empty Editions, type/range/identity errors and forged played results.
- Existing HTTP/SQLite cross-season flow is extended to assert records
  before real S2 rollover (still unsigned), after authentic Season
  Transition, Admin/Viewer equivalence, date and country filters,
  first-year retrospective, real restart and Saved replay.
- Existing Native Tour signed full HTTP/SQLite replay, 52/61/80-week
  browser and Fast CI must succeed on the final commit; none are
  bypassed merely to make this candidate green.

**Not implemented:** the general Master §31.39 Records service,
cross-product records, configurable persisted Saved Views, rolling
windows, head-to-head career statistics, real historical age-cohort/
intake, Health/healing, external correction/discipline, ranking-era
award catalog, season alert system or 50×61 official pre-alpha
reference endurance. This is a meaningful bounded read model only.
