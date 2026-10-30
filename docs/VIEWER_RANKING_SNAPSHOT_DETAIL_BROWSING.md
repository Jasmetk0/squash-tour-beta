# Viewer ranking snapshot detail browsing (legacy V1)

## Why and scope

This small read-only frontend slice is the destination of the Official Ranking
publication history links. The existing GET endpoint is
`/viewer/runs/{product_run_id}/rankings/history/{week_ordinal}` and returns
`viewer_official_ranking.v1`. This slice changes only the run-scoped detail
page, colocated tests, one local pure helper and this scoped note.

The existing canonical legacy `RankingWeek` projection uses 61 weeks and 50
seasons from 2000/01. The ordinal bounds in the local validation are **specific
to this existing V1 endpoint**, not a universal calendar rule for W52/W61/W80
or future calendar-native publication schemas. Nothing here migrates those
schemas, creates sports rules, or recalculates a historical snapshot.

## Trust and source isolation

- The route must have a canonical nonnegative legacy ordinal and a complete,
  matching Product Run / Viewer Branch route context, without loading or
  stale state. An invalid route issues no request.
- The React Query key includes Run ID, Viewer Branch ID and ordinal, while a
  keyed child remounts the local player-search and pagination state when any
  source identity changes. An older GET response is never displayed in the
  new scope, including an old response delivered after switching the source.
- The response is checked for exact `viewer_official_ranking.v1` schema,
  Product Run, Viewer Branch, ordinal, corresponding season/week, fingerprint
  format, historical policy fields, declared row count, unique nonempty player
  IDs, contiguous supplied ranks and finite nonnegative integer points.
  Invalid evidence is not repaired, guessed, or partially rendered.
- A valid `row_count = 0` produces an explicit empty publication. An empty
  local search and a failed GET/invalid response have distinct states. The
  explicit retry repeats the existing **GET only**.

## Presentation

- The page translates headings, labels, accessible names, loading/error/empty
  states, and navigation in CS/EN using the existing LanguageContext.
  Historical `policy_id`, `player_id`, fingerprints, points and links remain
  unmodified. Language switching preserves query identity and local page/search.
- The table shows only the actual fields available from this endpoint: rank,
  player ID and points. IDs link to the standard Viewer player-profile route,
  **not** to a claim of historically reconstructed profile attributes.
  No inferred names, countries, movement, counted-tournament data or points
  breakdowns are shown.
- Local case-insensitive search considers player IDs from the **complete
  returned snapshot**. The unchanged rank/points order is preserved, then
  results are split into pages of 50 with first/previous/next/last, a
  bounded numeric jump and an exact 1-based displayed range.
- Native form controls support keyboard access and explicit labels. Clearing
  search, changing source or changing the search term resets pagination;
  changing language does not.

## Verification boundary

Colocated React/Vitest tests **mock the GET client** and pure-helper tests
verify validation and browsing. These are not real Chromium, HTTP, backend,
or SQLite integration checks. The project pre-alpha policy still requires
relevant final-head CI, TypeScript/production build, and any applicable
Ready/manual acceptance. Draft skips are not successful acceptance.
