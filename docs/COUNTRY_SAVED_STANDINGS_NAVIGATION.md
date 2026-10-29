# National standings — exact Saved Revision paging and navigation

## Scope and authority

Admin → Run → World → Country → Records displays a descriptive national
**statistical standings** table over the **entire exact immutable reachable
Saved Revision**. The backend, not the UI, orders by titles, total finals,
played match wins, fewest played losses, then stable player ID; walkovers are
separate. This is neither an Official Ranking nor a claim of ranking points.
Master §21.3.1 / §27.24 / §31.39 targets more comprehensive records and Saved
Views later; this small slice does not implement those broader decisions.

## Implemented

- The source bound to each page is the exact selected Run, Branch, reachable
  Saved Revision and country. Schema, read-only source, original revision
  Branch, calendar status, summary counts, offset and 25-row limit are verified
  before rendering. A source mismatch, duplicate/missing identity, wrong
  nationality, contradictory final appearances, impossible totals, incomplete
  in-range page, invalid continuation or wrong per-page ordering fails closed
  with a visible localized error.
- Every returned player's position must match the 1-based absolute index
  across that Saved Revision; all displayed totals must be nonnegative integers
  with evidence. No wins, finishes or points are invented by the client.
- First / previous / next / last and bounded numeric one-based page jump provide
  navigation over the server-computed **complete** count. Page offset is
  synchronously reset on changes to Run / Branch / Saved Revision / country.
  Locale changes retain the selected page and do not trigger another API read.
- A true zero-player source displays **Page 0 / 0**, not 1 / 1. An invalid
  out-of-range cursor is visibly flagged with first/last valid-page recovery
  instead of a false empty standings message. Historical player names and
  IDs never link to a present-day profile.
- No write, simulation, extra API endpoint, server sporting command,
  aggregation, shared API/client/type, workflow, time limit, or styling change.

## Evidence

`countrySavedStandingsNavigation.test.ts` tests scope, invalid response
fields, full-window and order invariants, zero/last-page edge cases and jump
limits. `RunWorldCountryPlayerStandings.test.tsx` checks interactions with
**mocked API** including source switches, locale, numeric jump and historical
nonlinks. Existing `RunWorldCountrySavedPaging.test.tsx` now uses full,
schema-valid mock pages instead of a one-row body inconsistent with its
reported 50-player count.

Mocked frontend tests and build cannot establish full real-Run persistence.
The existing real Country HTTP/SQLite/Chromium acceptance plus the separate
release matrix remain distinct and must be checked before full release claims.

### Independent review correction — 29 October

The new ordering guard originally used browser `localeCompare` for tied player
IDs, while the backend uses Python's Unicode code-point ordering. Valid server
pages with mixed case or punctuation could therefore be incorrectly withheld.
The guard now compares code points, including supplementary Unicode characters,
without changing sporting order or sorting the returned rows. A regression failed
before the correction and passes afterward; it also rejects a reversed server
order. The three focused frontend files pass 15 tests locally. Final-head hosted
checks remain required.

## Ownership

Files: `RunWorldCountryPlayerStandings.tsx`, its new colocated tests,
`countrySavedStandingsNavigation.ts` and its new tests, the existing
source-switch paging regression fixture and this document. No overlap with
open PR #1652 (Saved player career), #1653 (Country match record evidence) or
#1654 (Country match listing), and no backend domain/API edits.
