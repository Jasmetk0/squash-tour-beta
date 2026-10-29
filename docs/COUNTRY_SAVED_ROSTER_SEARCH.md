# Country Saved roster search and exact-status filtering

## Real feature, existing backend authority

Admin → Run → World → Country → Saved country players now supports a
**full-source server-side search** on saved player **name or player ID**, plus
the backend's exact status string filter. Both may be combined and include all
matching records before pagination. A visible **Apply filters** action submits
a search (typing does not trigger network requests); **Clear filters** returns
to the full country roster. Status comparison is exact, case-insensitive in
the existing backend, not a locally guessed category or an enum invented by
the frontend. Input maxima mirror backend limits (search 120, status 80).

The explicit **include prepared prospects** opt-in remains independent. Future
prospects are still hidden by default; enabling them does not pretend they
are present-day players. The selected World data year is not the Saved player's
sport-time clock, and old initial ability/age are not fabricated as OVR/current
age. Ranking / NR remains the existing Saved public-ranking indication.

All reads use the existing immutable selected Run/Branch/Saved HEAD inventory
endpoint with `search`, `country_code`, `status_filter`,
`include_prepared`, `offset` and `limit=25`. The client already validates
identity/source/filters and each player response; this country view additionally
checks its own expected filter values. No API/schema/backend/Save/Viewer/source
rewrite is introduced.

## Stateful navigation rules

- A user may edit the search/status drafts without changing the displayed
  results or making a network request. Submitting applies **both** at once,
  resets the page **before** the first new read and retains a visible filter
  summary.
- Changing prepared-prospect inclusion resets the page while preserving the
  current applied search and status. Clearing filters does not silently enable
  prepared prospects.
- Run, Branch, Saved HEAD or country changes remount the scoped viewer: no
  draft, applied filter, prepared opt-in or page may cross from another source.
  The first query for the new source is unfiltered `offset=0`.
- Switching CS/EN never re-fetches the same Saved source or loses filters.
  An actual empty response shows **Page 0 / 0**. A no-longer-valid higher
  page offers an explicit first-page recovery instead of a false empty state.
- No UI read triggers Save, simulation, or a write endpoint.

## Verification and limits

`web/src/pages/RunWorldCountryRosterSearch.test.tsx` covers mock HTTP over
55 saved players, the second 25-row page, server-wide name/ID search, exact
status with search, controlled submission, clear, prepared opt-in and future
identity, loss of Saved HEAD, source changes, CS/EN and mismatched filter
identity. Original `RunWorldCountrySavedPaging.test.tsx` remains unchanged,
so its unrelated source-switch/standings tests also run.

These are mocked frontend tests; they do not replace real production
HTTP/SQLite/Chromium acceptance, the shell gate, the original 1,000-player
fixture or release acceptance. The existing native Saved Players read contract
remains authoritative, and no unverified full pre-alpha completion is claimed.

## Isolation

Only `RunWorldCountrySavedPlayers.tsx`, the new search React test, and this
document. Independent of the open Saved Career, Country Match Records, Country
Match List and Country Standings PRs #1652–#1655, with **no shared file edits**.
