# Viewer: signed native Tour records from Saved seasons (1 November 2026)

## Purpose

This vertical slice connects the existing public native Tour records endpoint to the existing Viewer **Records** landing. The pre-existing backend already signs completed native seasons, derives six cumulative records (player/country × titles/finals/awarded points), records every co-holder, preserves closure-stamped holder changes and limits leaderboards.

Previously, these records were available from Admin and the public GET endpoint, but the Viewer Records page remained a metadata-only placeholder. The change makes those existing authoritative Saved results browsable without adding sporting rules, publication events, data migrations or new API endpoints.

## Scope

- Isolated, read-only Viewer GET wrapper at web/src/api/viewerSignedTourRecords.ts; no modification of the shared API client or POST.
- Conservative runtime envelope, identity, timeframe, counts, ranking and holder-history checks before displaying data.
- CS/EN public UI; all six record types; explicit filters for signed from/to seasons and optional ISO-3 country. The baseline read supplies available signed seasons, applying a filter is a separate GET.
- The new section is embedded only for the Records landing; the Stats landing is unchanged.
- Focused Vitest tests and a shared fixture cover both source rejection and read-only UI.

The legacy official_branch_id field from the canonical Viewer context identifies the selected Viewer Branch, never a privileged Official/Main branch. The endpoint derives the exact Saved revision from that branch, not the Admin Working Draft. Frontend code does not compute points, winners, titles or holder history.

Filters work against the backend's signed-record computation rather than a local subset. Selected reads are made only after explicit submission. A verified signed zero is distinct from an unsupported, unsigned, inconsistent or missing source.

A changed Run, mismatched Viewer Branch, malformed source envelope or contradictory historical evidence causes the result to be withheld. The Saved Revision ID is displayed; focus/remount causes refetch. These client checks are not a replacement for backend replay and integrity gates.

## Not implemented

- Full Master §31.39 Records catalog or Saved Views, rolling windows, Weeks at No. 1, all-time H2H or notifications.
- Working Draft reads, new simulation or sporting decisions, source rewriting, release certification.
- Future-only or unpublished public events.

The existing Title Leaders placeholder for the general records system remains deferred; signed native Tour titles are a narrower currently supported evidence class.

## Verification and owner handoff

Focused checkout commands:

    npm --prefix web ci
    npm --prefix web run test -- src/pages/viewer/stats/viewerSignedTourRecords.test.ts src/pages/viewer/stats/ViewerSignedTourRecords.test.tsx src/pages/viewer/stats/ViewerRecordsPage.test.tsx
    npm --prefix web run build

Mocked frontend tests do not prove real HTTP/SQLite/Chromium. Actual Viewer browser acceptance, a Saved Viewer Branch switch, restart and all applicable pre-alpha gates must run against the final PR head before merge consideration. Draft CI skips are not passes. Only the owner merges; the PR remains Draft.

Parallel PR #1704 owns App.tsx, api/client.ts and the Saved comparison backend and route; this PR touches none of those. Research PRs #1700, #1702, #1703, #1705 remain independent. No Master decision is changed.

Coordinator source-fence repair (2026-11-02): filtered record responses must match
both the Saved HEAD and Tour fingerprint of their independently loaded season
inventory. A different Save cannot reuse older cached filter results under the
same Branch. Retry refreshes both source inventory and the selected read; mocked
regressions exercise both mismatched identities separately.
