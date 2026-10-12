# Country Records — canonical Saved player standings

Date: 2026-10-12. One vertical read-only slice (API, UI, deterministic and real-browser tests).

## Purpose
For each Run → World → Country → Records tab, show a pageable **statistical list of national athletes** with an exact Run/Branch/Saved Revision source, not an Official Ranking or invented "power score". This includes anyone with a canonical published first/second place or played/walkover match, and excludes BYEs and unsupported future/unsaved tournament activity.

## Evidence and deterministic order
- `country_titles` = canonical champion placements published for a country's Saved participants.
- `runner_up_finishes` = published finalist placements, distinct from titles.
- `final_appearances` = titles + runner-up placements.
- `played_wins/losses` and `walkover_wins/losses` = canonical match outcomes with saved participant identities, not match node counts or calendar-only status.
- Same-country head-to-head match counts one national played win **and** one national played loss, with one each for the respective players. No BYE rows.
- Order = most titles, then most final appearances, then most played wins, then fewest played losses, then ascending stable Saved player ID. This is a sortable factual presentation priority, **not an asserted official ranking policy**.
- A single full Saved Revision source projection is shared with existing published Country Records and Match Records. The match collector returns all validated matches internally; the already published 25-row match API remains paginated, so standings never use a truncated page.
- Server counts are reconciled against the underlying complete Country Titles and Match results. Any identity discrepancy or contradiction returns 409; no guessed participants or silently omitted matches.

## API
`GET /admin/runs/{run_id}/branches/{branch_id}/country-player-standings/{country_code}?revision_id={reachable_revision_id}&offset=0&limit=25`

Bounded limit 1–50. Scope matches the **selected** Branch but Saved components are loaded from the actual original owner of a reachable historical/shared-ancestor revision. Responses contain source, provenance, total player count, aggregate published counters and 25-row default pages with stable absolute positions.

The UI is Czech/English, read-only, shows full-candidate page count and never links historical Saved Revision standings to present player profiles. Missing/inaccessible Saved evidence fails visibly, not as a fabricated zero.

## Verification
Deterministic backend tests validate derby accounting, more than 25 matches and 25 ranked players, cross-source contradictions, name conflicts, pagination/sort. FastAPI SQLite tests validate scope, missing/rejected revisions, invalid requests and backend restart. Frontend tests validate exact-source query, current/historical links, missing HEAD and 26-player pagination. The existing real Chromium+production API+SQLite tournament/save/restart workflow checks genuine published player standings derived independently from three real tournament matches, including a historical revision without results, both before and after restart.

No full 50-season scale/performance guarantee is inferred from those tests.
