# Historical Country Saved match list — source and paging continuity

This read-only Admin → Run → World → Country → Records lifetime table
shows canonical **Saved Revision** matches. It is a separate component from the
period record-leader evidence under PR #1653 and the Saved Player Career under
PR #1652. It changes neither backend sport results nor the full-source totals.

## Source and page behavior

- Local season, completion, country-outcome filters and page offset reset
  **synchronously** before the first request for any new Run, Branch, Country,
  Saved Revision or historical mode. A locale change alone retains the page and
  filters without issuing another query.
- Every rendered response is bound to the exact requested Run / selected Branch /
  reachable immutable Saved Revision / country / season / result kind / outcome /
  zero-based offset and 25-row page limit. Source, schema, original revision
  Branch and publication status must be present. Contradictory totals, missing
  expected rows, extra rows, duplicate Match IDs, impossible has-more or rows
  violating the selected filters fail closed instead of showing old matches.
- The API computes all totals before paging. This UI never reinterprets its
  player outcomes as match counts, nor treats a W/O as played. The empty filtered
  list shows **Page 0 / 0**. An out-of-range URL-free local cursor displays a
  recovery action to the first or last valid page; it is not called a career
  with no matches.
- Historical participant profiles remain non-links. Historical rows instead
  use the existing **immutable saved Tournament Match detail** with explicitly
  scoped Run/Branch/Revision/season and an exact Country record return link.
  Missing sport-time or revision blocks that link. Non-historical links retain
  their established player route.

## Verification and limits

Pure contract tests in `countrySavedMatchListGuard.test.ts` cover source
tampering, true vs missing zero rows, duplicate or out-of-filter results and
page arithmetic. Mocked React integration tests in
`RunWorldCountryMatchRecords.test.tsx` check paging, switching branch/revision,
locale without refetch, historical links and empty filters. These do **not**
constitute real production HTTP/SQLite acceptance. Existing real Country
Records HTTP/SQLite browser tests and the full release suite remain required
at their respective integration checkpoints.

Five scoped files only: this document, the existing lifetime match-list
component, its new test, and a new dedicated guard plus test. No edit to
#1652/#1653 owned files, shared API client/types, sporting Save, simulation,
common styles, fixtures or acceptance timing.
