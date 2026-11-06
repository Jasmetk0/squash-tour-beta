# Admin — side-by-side Saved Branch readiness inspection (1 November 2026)

## Why

Run Home exposes one verified, Saved HEAD-scoped foundation inspection, but
an owner comparing alternative timelines could not inspect the same six
categories next to each other without changing the selected Admin Branch.
This bounded feature adds an **on-demand** two-Branch comparison at the Run
overview below the existing Readiness panel. It does not change which Branch
is selected, or which Branch the public Viewer displays.

## Evidence contract

- Reads the existing `/admin/runs/{run_id}/branches/{branch_id}/home-readiness`
  endpoint for each of exactly two named Branches in the same Run. Both
  existing server and frontend validators still apply.
- Fetches the Branch list **before and after** the independent reads; rejects
  foreign/duplicate records, missing Saved HEADs, changed HEADs, wrong Run
  scope, stale result HEADs, invalid content hashes, and incomplete foundation
  responses. Requests are triggered only by the user.
- Displays Saved counts and statuses for World, Calendar, initial population,
  Health, published ranking and the selected Working Draft. Differences,
  phase, clock, recorded transitions, ranking publications and active tasks
  are labelled as distinct inspections, not as a readiness clearance.
- Explicitly shows when the two **Run calendar configurations differ**.
  Different configurations are legal; there is no universal 61-week rule.
- Offers one explicit, local JSON export containing only the verified
  identity, source checksum, counts, status and difference metadata. Never
  includes full player rosters, raw Saved payloads or source Package bodies.
- The comparator does not perform a cross-Branch transaction: an unchanged
  Saved HEAD cannot prove that concurrent Working Draft edits did not occur.
  In particular, **no sporting operation is authorized** by this feature.
  An execution still requires its own current operation preflight and manual
  Save boundaries. Missing or conflicting evidence is shown as unavailable.

## Changed scope and isolation

Only one new pure read model, one on-demand Admin component, Run Home
placement, related frontend tests and this document. No backend writes,
no new HTTP endpoint, no Master edits, no simulation/Entry/World data
changes. Unrelated Viewer/research PRs and the Windows backup PR remain
untouched. This slice does not subsume cross-Run Saved payload comparison
PR #1704 or certify full pre-alpha acceptance.

## Test coverage

Unit contracts include correct two-HEAD double-check, count/status deltas,
different clocks, inherited identical-head identity, missing/foreign/
duplicated source rejection, and stale responses. Component tests cover
CS/EN, user-triggered reads, error states and removal of a previously
shown comparison after HEAD drift. GitHub Fast CI executes the changed
frontend tests and TypeScript build; its result belongs to the final
PR head only. Real SQLite multi-Branch persistence, full browser acceptance
and the complete internal-release gate are separate.
