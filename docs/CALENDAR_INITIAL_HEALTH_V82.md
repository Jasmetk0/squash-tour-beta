# Calendar-owned initial Health — Master v82

Baseline merged in #1501; reviewed event-edit candidate on `buuk`
`2b472b287452b9faa00552ef0b74889e83cfc785`; no new product mechanics or Master
revision. This closes the initial-health persistence boundary, not sporting time.

## Operator flow and authority

After a custom-clock population has been explicitly saved, Players → Generate
shows Initial health in CS/EN. Review is read-only. Separate consent confirms a
fresh baseline into a dirty Working Draft; it does not Save. Another consent and
manual Health Save creates an immutable revision using the existing Health Save
CAS. The UI verifies scope, clock, roster, Saved head, draft version, review and
Save receipt. A lost confirmation response is recovered by reading current state.
Review/consent is discarded when its source changes; automatic mutation retries
are disabled.

The baseline is explicitly `fresh_without_history.v1`, with no Injury, Illness or
permanent-consequence records. It is not a realistic random distribution and does
not heal existing players: it may only initialize absent health for an unstarted,
writable custom Run with a clean Draft and already saved V2 population. Future
initial-condition sampling remains separate from this explicit test baseline.

## Backend contract

`calendar_initial_health_state.v1` owns a `RunWeekPosition` and requires ordinal
zero, canonical roster, empty event history and a source population fingerprint.
It records command/request fingerprints and Admin label/reason. GET inspection
and POST review/confirmation live at
`/admin/runs/{run}/branches/{branch}/player-health/calendar-initial` (review suffix
`/preview`). Confirmation holds `BEGIN IMMEDIATE` and revalidates Saved population,
lifecycle, clock, head, draft and expected health hash before atomic state/draft
writes. Exact installed command retries return the installed view without adding
another draft change. Failure rolls back both health and draft.

Existing explicit `/player-health/save` captures the component. Snapshot loading
validates hashes, owner, population roster and actual calendar. Fork remaps branch
ownership while preserving historical source provenance; restore and restart
preserve exact states. Restoring a population-only revision does not backfill
health. Legacy Health V1 schemas/hashes and old Week semantics are unchanged.

The baseline schema cannot contain event history. Legacy RankingWeek reads and
writers reject calendar health even when both ordinals are zero. The event-edit
contract below adds explicit dated facts through a separate state version; it
does not change or reinterpret this baseline schema.

## Verification

- Seven real HTTP/SQLite scenarios cover W52, W80 and W1/year zero; review
  non-mutation; confirmation vs Save; exact retries before/after Save; materialized
  fork, backward/forward restore and process restart; stale review/draft; concurrent
  identical commands; injected post-write rollback; legacy read refusal.
- Focused legacy Health edit/persistence/API, restore and lifecycle-fork regressions.
- Five new frontend component tests cover two consents, response loss, asynchronous
  stale review, wrong-population proof and mismatched Save receipt. Existing
  population controls remain covered; these component tests mock the API boundary.
- Existing Shell acceptance is extended (no new workflow) to review/confirm/save
  actual 1,000-player W52 health, verify unchanged head before Save, inspect Saved
  component, reload exact state and capture a screenshot. Final-head CI/browser
  results belong in the PR evidence; local build alone is not browser evidence.

## Reviewed event editing on the real player profile

The present-time saved-player profile (`/admin/runs/{run}/people/{player}`) now
includes **Health / Zdraví**. It reuses `PlayerHealthAdminPanel`, the existing
`/players/{player}/health` inspect/preview/confirm endpoints and `/player-health/save`.
The UI displays the actual season label, W, offset, year/week and horizon; it never
maps calendar-owned facts modulo 61. V1 display retains explicit historical FAX
semantics. No Viewer or historical-profile fallback is introduced.

`admin_health_edit_request.v2` requires the Saved head, Working Draft version and
current Health fingerprint. Its records use full `RunWeekPosition` dates. Request
V1 (including its former omitted-version default) remains legacy-only. Schema
versions cannot be interchanged even at the same ordinal. Inspect and preview run
in a read transaction. Preview is deterministic and writes nothing.

The first effective explicitly confirmed profile edit converts the live opening
baseline to `player_health_calendar_state.v2`. Empty no-op edits are rejected. This
state stores calendar profiles, original baseline hash/command/audit evidence,
InitialWorld provenance and cumulative branch-scoped Admin edit evidence. The
baseline's immutable Saved Revision is unchanged; there is no read-time upgrade.
Severity, Injury/Illness, lifecycle, recurrence and permanent consequences keep
their separate meanings. New `Recovered` records require zero acute severity;
legacy V1 is loaded exactly, without retroactive repair. `started_before_run`
remains explicit and has no fabricated pre-Run date. Estimated recovery windows
retain their exact integer number of weeks (including the existing 0–520 bounds),
not W/61 scaling or a promised future recovery date.

Validation binds owner, verified Saved clock/population/lifecycle and canonical
roster. Dates must be in horizon, use the same stored calendar and not exceed the
current authoritative health boundary. Recovery cannot precede onset, and a
recurrence cannot precede its known source/on-record recovery. Unknown/cyclic
references, foreign scope and mixed time/schema authority fail closed. Equal
ordinals in different calendars are not interchangeable. Calendar horizon
extension remains a separate, unfinished migration; old health time bases are
never recomputed from newer defaults.

Confirmation re-evaluates the preview under `BEGIN IMMEDIATE`, including Saved
head, draft base/version, live health/component and population/lifecycle. State,
existing Admin audit receipt and one dirty Draft change commit atomically; no
Saved Revision is created. A changed request/proof under an existing command ID
is rejected. An exact installed retry returns the original result without writing,
including after Save/restart. Receipt metadata/result/proof consistency is checked;
a receipt whose state was removed by restore or later correction is historical
and cannot reinstall that state. Branch forks preserve source edit evidence while
new edits receive the fork's own command scope.

The editor shows the complete selected player's before/after facts and requires
fresh confirmation after preview, then separate Save consent. Source, proof,
scope or input changes revoke consent, including change-back and late responses.
Mutation retry is disabled. After a lost confirmation/Save response the UI reads
current authority; a retained exact confirmation retry requires new explicit
approval. Save receipts must identify the actual scope, component and clean draft.

Saved capture/load, materialized fork and restore dispatch by exact state version.
Old V1 and initial baseline JSON/hashes stay exact. New snapshot records, recurrence
and consequence links, origin and cumulative edit provenance survive restart/fork/
restore. Legacy writers cannot overwrite a calendar-owned state. Pure
`carry_calendar_health_forward` preserves known facts over consecutive matching
Run weeks and records predecessor identity. It has no endpoint, healing model or
sporting transition authority. Annual development, ranking validity and Full
Simulation are unchanged and unsupported custom sporting writers remain guarded.

## Event-edit verification and adversarial pass

- Real HTTP/SQLite tests: W52/O35, W80/O80 (300-season horizon), W1/year zero;
  read-only preview, confirmation without Save, retry before/after Save/restart,
  changed-command conflicts, materialized fork editing, exact backward/forward
  restore, two competing reviews, Saved-head change, identical concurrency and
  injected failure after health/draft/receipt flush with full database rollback.
- Integrity tests recompute damaged component hashes and still reject calendar,
  roster, source-provenance, schema and audit-owner corruption. Legacy direct
  writers/readers and corrupted receipts fail closed without further writes.
- Pure domain tests cross actual year and season boundaries (including W80 dates
  after Week 61) without manufacturing authoritative sporting progression. They
  cover future/foreign/reversed dates, recurrence order, horizon and unchanged
  recovery estimates/facts.
- Frontend component tests use API mocks: separate consents, W80/year-zero date
  inputs, source drift/change-back, response loss without write retry, CS copy and
  the preserved baseline/population controls. These are not integration evidence.
- The existing real Shell Chromium acceptance is extended with actual 1,000-player
  W52 player-profile Health editing, reviewed onset clock, confirmation without
  Save, explicit Health Save and exact reload. No separate workflow was added.
  Local and final-head CI results are recorded in the PR; this document alone
  does not assert a green final head.
- A distinct adversarial review examined time aliases, cross-branch commands,
  stale preview/Saved/draft/health proofs, replay after restore, snapshot integrity
  and partial-write rollback. It added receipt-integrity checks, opening-chain/
  provenance guards and the corresponding negative tests. No new product mechanics
  or unsupported time-progression shortcut was introduced.

Next: annual development and remaining calendar sporting callers. Health realism
and exact probability/healing calibration remain separate later testing work.
