# Viewer Season Calendar — complete read-only Saved season browser

## Purpose

The existing top-level \`/viewer/tour/calendar\` showed only Saved Calendar
counts and a hardcoded week-24 jump demo. The new page displays **actual
saved events**, sourced exclusively from the existing canonical Saved-Revision
Calendar GET. No invented week or event is substituted.

## Verified source and trust boundary

1. Resolve the active Product Run's saved Viewer Branch with the existing
   \`useViewerOfficialRunContext\` GET. Its legacy field \`official_branch_id\`
   denotes the actual saved Viewer Branch, not a privileged simulation branch.
2. Issue \`getViewerRunCalendar(productRunId)\` only after confirming the
   context's exact Product Run identity and a nonempty Viewer Branch.
3. Accept \`viewer_run_calendar.v1\` only with matching Product Run/Viewer Branch,
   exact \`season_count\`/\`event_count\`, unique season and event identities,
   coherent per-season event counts, safe numeric fields and supported
   event statuses. Reject foreign, stale, malformed or incomplete payloads.
4. Key the GET cache and rendered child by **both** Product Run and Viewer
   Branch. Pending context refresh conceals the previous source; a delayed
   response from an old Run or Branch cannot be rendered under a new one.
   An explicit retry reruns GET only.

The current \`viewer_run_calendar.v1\` source projects the original **W61**
calendar package read model. Its explicit weeks 1–61 constraint is tied to
that versioned DTO; **it is not a product-wide limitation** on future
calendar-native W52/W61/W80 Run setups. Do not attempt to reinterpret other
calendars as this legacy schema.

## Read-only interactions

- CS/EN for headings, event status, filters, labels, and error messages.
  Event IDs, categories, countries, host locations, dates and calendar week
  metadata remain unmodified source data.
- All saved seasons and events are available with newest season first in the
  browsing order; no hardcoded demo or top-eight cap.
- Filters for season, **actual saved week within the selected season**,
  saved event status, and case-insensitive name/ID/country/city search.
- The displayed week is a saved data field; we deliberately do not link
  \`/viewer/runs/:id/weeks/:week\` for past seasons because that route alone
  cannot identify which season a historical week belongs to.
  Actual event detail links use \`viewerPlannedEventPath(runId,eventId)\`.
- Pagination in groups of 25, first/previous/next/last, bounded numeric
  page jump, keyboard-labeled controls and separate empty/no-match states.
- Filters/page reset when source changes and the selected week resets when
  season changes; language toggles preserve the same data and choices.
- No Admin, mutate, Save, repair, simulation or fabricated publication status.

## Verification boundary

New unit tests validate DTO identity and counts, duplicates, legacy week
bounds, source changes, filtering and page safety. React component tests use
**mocked GET API**, including delayed old-Run replies, changed Branch, CS/EN,
error/read retry, encoded event links, actual saved weeks, pagination and
empty states. They do **not** establish Chromium/real HTTP/SQLite integration.

Require final-head frontend baseline/changed tests, TypeScript/Vite build,
CodeQL and SonarCloud. Additional release scenario gates remain separate;
unrelated skipped CI jobs are not passes. Owner controls merges.
