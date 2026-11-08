# Viewer Signed Season comparison – 1 November 2026

## Motivation

The existing Viewer Season Hub displays canonical Saved calendar and tournament
metadata, but has not yet exposed the independently implemented public native
Tour Signed Season Summary API. This vertical slice connects existing public
GET data to a **read-only** CS/EN season report and comparative national table.

## Authority

- The public endpoint /viewer/runs/{run_id}/calendar-tour/records is used
  only to enumerate already *completed and signed* native seasons.
- The public endpoint /viewer/runs/{run_id}/calendar-tour/seasons/{season_index}
  returns the exact selected season, optionally with a second signed season
  and country deltas. Both read the current Saved Viewer Branch.
- Existing legacy Product Run calendar counts never infer a native signed
  Season Transition. The frontend never manufactures future seasons, results,
  rankings, records, champion identities, country changes or writes.
- The legacy context property official_branch_id represents the selected
  Viewer Branch. It is not a privileged Main/Official timeline.
- No access to Working Draft or Admin state, no simulated or unsigned seasons.

## New frontend scope

- web/src/api/viewerSignedSeason.ts: independent GET wrapper.
- web/src/pages/viewer/tour/viewerSignedSeasonReadModel.ts: strict Run/Branch,
  Saved HEAD, signed period, per-season evidence, leaderboard and national delta
  guards. On invalid source no authoritative data are displayed.
- web/src/pages/viewer/tour/ViewerSignedSeasonComparison.tsx:
  explicit season/comparison selection, CS/EN tables for signed Editions,
  players, countries, final-week published ranking and server country deltas.
  Uses scoped React Query keys and revalidates Saved HEAD.
- ViewerSeasonHubPage.tsx: one isolated component added below the existing
  legacy Saved summary. Its previous content and links remain intact.
- Five scoped source/consent/error cases in mock HTTP React tests plus
  pure read-model regression tests and adapted original hub tests.

The selected period's awarded tournament points and current published ranking
points are intentionally separate. The complete table source comes from
already-authenticated backend summaries, not UI calculations.

## Deliberate limits

This does not introduce new API routes or database structures, alter Season
Transition semantics, implement the entire Master season notification system,
change historical source persistence or certify 50-season release endurance.
No country mechanics are invented.

Only signed native seasons are supported; older legacy Runs without that
authority show an explicit unavailable state in this optional section.
There is no fabricated default season.

## Verification and merge constraints

From repo checkout:

    npm --prefix web ci
    npm --prefix web run test -- src/pages/viewer/tour/viewerSignedSeasonReadModel.test.ts src/pages/viewer/tour/ViewerSignedSeasonComparison.test.tsx src/pages/viewer/tour/ViewerSeasonHubPage.test.tsx
    npm --prefix web run build

Vitest component tests use mocked GET responses. These are NOT real
HTTP/SQLite/Chromium acceptance. The actual native signed API acceptance,
Saved Branch switch, browser and restart, relevant pre-alpha gates and final
PR head must be verified independently. Draft skips are not passes.
Only the product owner merges.

Parallel isolation: This PR does NOT modify PR #1704 Cross-Run Saved
Comparison, PR #1706 Viewer Signed Records, or research PR #1700, #1702,
#1703, #1705. No modifications to App.tsx, shared API client,
domain/sporting rules, Master or backend persistence.
