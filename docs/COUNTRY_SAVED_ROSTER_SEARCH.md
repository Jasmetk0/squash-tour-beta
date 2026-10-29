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
- Saved-roster navigation includes **first / previous / next / last** and an
  explicit **one-based numeric page jump**, not just two sequential buttons.
  The input accepts only canonical integers 1..totalPages; invalid text,
  zero, leading zeros and pages beyond the real count never issue an API GET.
  Every accepted jump uses the same backend filters and exact Saved source.
- The UI also shows the absolute visible row range (e.g. 51–55 of 55),
  without claiming those are globally ranked players. Jump input and page
  reset on a new applied search, prepared toggle or Run/Branch/HEAD/country.
  Switching CS/EN never re-fetches the same Saved source or loses filters.
  An actual empty response shows **Page 0 / 0**; navigation is unavailable.
  A no-longer-valid higher page offers explicit first/last valid-page
  recovery instead of a false empty state.
- No UI read triggers Save, simulation, or a write endpoint.

## Shareable deep link and return from a player profile

The Country players tab preserves filter, exact status, prepared opt-in and
one-based page as named `sp*` URL parameters, alongside the existing World
year and country search. This state is keyed to the **exact Run + selected
Branch + Saved HEAD + country**; an old `spScope` from a different Saved
source is ignored completely (including opt-in to potentially future players).
All URL inputs remain ordinary view requests, never sporting authority.
Malformed/oversized filter parameters and invalid page numbers are rejected.
React Router may update only the query string while keeping the Country component
mounted: changes to roster-owned URL keys therefore remount that scoped view
and restore the newly selected query/filters/page immediately. Browser Back and
in-app same-route bookmark navigation cannot leave earlier local filters/page
in charge of a different URL. Changes to unrelated World parameters or CS/EN
do not remount the roster.
The original API proof and full-source filter/page validations still apply.

A player profile link carries a bounded `fromCountry` return URL to the
currently filtered and paged country view. The present-time profile offers
**Back to filtered country roster** only after a verified saved player
identity is present, and only for an exact, local current-Run Country URL
whose Country matches that player's verified nationality **and** whose
embedded source scope matches the profile's current selected Branch and
Saved HEAD exactly. External URLs, other Run IDs/countries, old Branches or
Saved HEADs, missing/duplicated source scope, non-Country paths and historical
revision links are ignored. Profile tabs preserve the return parameter.
General Back to Players
remains available and no new write or saved view is created.

A permalink is not yet a named persisted `Saved View` from Master §27.24:
it is a shareable current-Run view selection, and a branch/HEAD change
intentionally resets it.

## Verification and limits

`web/src/pages/RunWorldCountryRosterSearch.test.tsx` covers mock HTTP over
55 saved players, the second 25-row page, server-wide name/ID search, exact
status with search, controlled submission, clear, prepared opt-in and future
identity, loss of Saved HEAD, source changes, CS/EN and mismatched filter
identity. Two further tests cover exact page 3 of 3 for 55 authentic-shaped
Saved players, malformed and out-of-range page input without network GETs,
first/last jumps and synchronous cursor resets across filters, prospect opt-in
and immutable sources. Another pair covers restoring a shared URL and rejecting
scope from an older immutable HEAD. Four pure URL tests protect state round-trips,
context preservation, rejected old-source filters/future opt-ins and safe
profile returns. `SavedPlayerCountryRosterReturn.test.tsx` additionally
mounts the actual Country and Saved Profile React routes together, verifying
a real filtered-page → player-profile → filtered-page round trip and
rejecting obsolete Branch, HEAD or foreign-country return targets.
The Country roster React tests also navigate to an entirely different Saved
roster bookmark **on the same mounted route**, then Browser Back, asserting
the exact new search, page and server offset instead of stale component state.
Original `RunWorldCountrySavedPaging.test.tsx` remains unchanged,
so its unrelated source-switch/standings tests also run.

These are mocked frontend tests; they do not replace real production
HTTP/SQLite/Chromium acceptance, the shell gate, the original 1,000-player
fixture or release acceptance. The existing native Saved Players read contract
remains authoritative, and no unverified full pre-alpha completion is claimed.

## Isolation

Only `RunWorldCountrySavedPlayers.tsx`, `SavedPlayerIdentityPage.tsx`,
the search React test, a dedicated pure permalink helper + four tests, four full React
route-transition cases and this document. Independent of the open Saved Career, Country Match Records, Country
Match List and Country Standings PRs #1652–#1655, with **no shared file edits**.
