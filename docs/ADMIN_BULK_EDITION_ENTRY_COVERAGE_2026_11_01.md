# Admin — bounded Edition Entry coverage audit (1 November 2026)

## Problem and purpose

The Run-owned per-Edition Entry timing editor can inspect one Edition at a time,
but a reference FAX Calendar can have **80 actual World Tour Editions**.
Identifying missing future Entry plans and exact Official Ranking sources across
80 Editions one by one is cumbersome and makes missing prerequisites hard to
diagnose. This integration-facing UI adds a separate **explicit read-only batch
inspection** under Run Management.

It is NOT an eligibility service, batch acceptance, simulated Tour completion,
Saved proof, new official ranking, automation, or alternate authority.

## Boundary and source checks

1. The user explicitly clicks to load the current Run-owned Calendar Package
   IDs; the panel makes no network requests on mount.
2. The user selects exactly one Package, then explicitly starts the audit.
   Package state and Run Branch Saved HEAD are checked before the scan.
3. The production Run Calendar projection must match that Package state
   fingerprint, Run/Branch/Package, season, uniqueness, week range and
   validation_errors; no assumed FAX W61 clock. This currently supports up to
   **200 Editions per selected Calendar Package**. Larger packages fail closed
   rather than silently present partial coverage.
4. At most **four** GET requests are in flight; each uses the existing
   `GET .../packages/calendar/{packageId}/editions/{eventId}/entry-timing`.
   The existing API client performs its nested DTO validation. Responses are
   classified by returned preflight/ranking state, not a client-created
   ranking, deadline or qualification rule.
5. The Branch HEAD, Package state and Calendar projection are re-fetched after
   the full scan. Changes are fatal to this report and require a new audit.
   Individual per-Edition 409/error/malformed responses become **unverified**
   with explicit per-row errors and incomplete coverage counts, never ready.
6. The UI shows status counts, search/filter, exact technical IDs and blockers,
   and a deep-link to the existing per-Edition Entry editor with the exact
   Branch and Calendar query parameters. Czech and English are supported.

A valid plan missing its future ranking publication may have a
`missing_ranking` status; a publication ready for explicit binding is
`configuration_ready`; `bound` means that current Working Draft reports a
ranking binding. None imply Saved publication, automatic eligibility, field,
draw, tournament participation, or simulation authorization.

## Explicit limits

- This report reflects a **current Working Draft**, and performs independent
  read transactions rather than a single atomic 80-Edition snapshot. It
  detects most ordinary mutations by checking Package fingerprint and HEAD
  before/after, but does not claim cross-operation transaction isolation.
- This slice does not change per-Edition timing, ranking binding, Save,
  eligibility, draw, points, Master, backend API, or simulation rules.
- Existing browser and backend HTTP/SQLite acceptance for single Edition
  ownership remain separate. React mock/pure unit tests do not certify a
  complete 80-Edition production flow, real tournament outcomes, or the
  reference FAX 50-season release.
- If the Run lacks explicit valid v1 calendar metadata, the panel does not
  appear and no fallback default clock is fabricated.
- Neither Jules' parallel work nor any research PR should edit these files.

## Test scope

`web/src/pages/runEditionCoverageAudit.test.ts` checks an actual count of
80 modeled Editions, bounded concurrency, correct missing/bound states,
stale foreign HEAD, Package/Calendar drift, partial errors and invalid
Calendar source. `web/src/components/RunEditionCoveragePanel.test.tsx`
exercises explicit request initiation, status/errors, links and CS/EN. The
Run Management contract suite remains in changed-file CI, alongside TS/Vite.
Separate actual SQLite/browser integration and complete pre-alpha release
gates remain required.
