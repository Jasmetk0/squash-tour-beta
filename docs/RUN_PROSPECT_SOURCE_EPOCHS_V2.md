# Historic Run prospect source epochs v2 — implementation candidate (20 October 2026)

**Status:** code candidate for a single PR to `buuk`, not owner-merged and not
pre-alpha release certification. Master product decisions remain unchanged.

## Historical identity / origin

The shared SQLite `run_prospects` table contains the current Run catalog, but
a Branch's exact immutable Saved Revision `content.run_prospect_source` owns the
**effective source authority**. Existing
`run_prospect_source_snapshot.v1` bytes, canonical JSON and fingerprints do
not change. A first explicitly reviewed Save still emits v1.

When the Run catalog gains genuinely new future prospect identities, a Branch
may explicitly Save `run_prospect_source_epochs.v2`, a strict immutable
chronological chain of v1 snapshots. Each epoch has an integer
`effective_from_ordinal` and complete hash-verified nested snapshot.
The v2 chain has an independent canonical SHA-256 over
`schema_version`, `run_id` and the exact ordered `epochs`. The only
accepted v2 fields are those four. Each embedded v1 snapshot must be canonical
and contain exactly the original four v1 fields.

All newer sources must **append** records; changing, deleting, renaming or
reassigning an old source row is rejected even if the caller forges fresh
correct-looking hashes. Every newly added 15th birthday must be on or after
the new epoch's effective week, inside the exact Saved Run W/O calendar, and
strictly later than the latest *authenticated* completed Run week of **every**
Branch. Even a sibling Branch that has already advanced to that week blocks
retroactive admission. InitialWorld and downstream player identity collision
checks remain active.

A Branch's epoch begins at the first week *after that Branch's* completed
lifecycle week, not at the calendar's present global time. Source epochs
contain no priority/main/official Branch and copy **zero** Run databases.
Two equal Branches may continue using different signed historical sources:
other-Branch catalog additions do not implicitly upgrade their Saved HEAD.

## Actual native transition and replay

The Admin panel's source-Save review remains available after a reload or an
interrupted materialization response. Recovery reads the persisted shared
catalog, requires a fresh preview and explicit Save consent, and never
materializes duplicate records or saves automatically.

On preparation and historical verification for week `t`, select
`saved_source.for_week(t)` (most recent epoch starting at or before `t`).
This gives the **original v1 snapshot fingerprint** to deterministic
`CalendarProspectBirthEvent`, player generation, lifecycle, native sporting
development, native Tour receipt recreation, competition/MatchEngine replay
and next-week readiness. Do not compute old events from the latest chain
snapshot. A supported v1-only Saved Revision resolves to its unchanged v1
source for every week.

The weekly reducer receives the complete epoch chain: only the current birth
event selects one effective snapshot. Ranking's complete lifecycle replay keeps
the chain so every earlier birthday uses its original fingerprint. A lifecycle
replay proof binds the v1 snapshot effective at its own last week, with earlier
snapshots bound by the replayed birth-event hashes; appending a future epoch
cannot change a previously confirmed ranking-adoption proof. Execution,
v3 Tour replay and v4 competition replay share this same boundary.

The independent Saved-origin guard accepts a later source only when its parsed
epoch chain preserves every preceding source and activation ordinal as an exact
prefix. It rejects a replacement v1, altered prior epoch, downgrade or truncated
chain; actual Saved Run/Branch ownership and reachable lineage remain required.

The native Week/Season Transition is still the **only** operation that
actually activates a 15-year-old and may create official ranked/entered
players. Generator preview reads a hash-verified Saved World Package and
calendar, prepares 57-attribute records, and performs **zero writes**.
Explicit materialization inserts reviewed future records in a single
`BEGIN IMMEDIATE` transaction; it requires Saved HEAD, fingerprint, audit
reason and confirmed exact request. New records remain only prospects until
the independent source Save and later native transition.

Only `prospect-source/save` may introduce a new epoch. It uses the existing
clean Working Draft, verified Run/Branch/HEAD, reviewed source fingerprint,
expected draft version, independent Saved Revision/audit event and atomic
transaction. The new optional `expected_saved_head_revision_id` provides
an additional strict contemporary HEAD gate while preserving earlier payload
shapes. Ordinary native Tour/Health/match Save, historical fork/restore and
Viewer selection Save preserve the **already Signed** source component;
they never auto-promote a mutable shared catalog.

Historical restore still authenticates both current and target Saved
source **against their immutable prefixes** in the shared Run rows.
It neither rewrites the shared catalog nor copies an older source into it;
the restored Branch reselects the historical source component from its
target Saved Revision. The original Saved snapshots, played attributes,
match results, ranking and replay fingerprints remain immutable.

## Fail-closed / adversarial review

- Duplicate or rewritten old IDs, malformed or rehashed v1/v2 evidence,
  non-canonical epoch ordering, past-year admission and absent/foreign Run
  or Branch scope must fail.
- A second Branch's already played week is a distinct time owner, verified
  by decoding/validating stored lifecycle evidence before authorizing
  another epoch. A raw SQL `MAX` is insufficient.
- Review is strictly read-only; confirmation uses a locked recheck. New
  additions cannot silently bypass explicit Saved publication.
- Prospective source Save binds its exact live fingerprint and optional
  latest Saved HEAD; stale confirmation fails instead of silently
  selecting a newer source.
- Original v1 parser and signature shape remain untouched; the v2 parser
  never accepts unknown fields or synthesizes authority from missing data.
- No new product-level policies, competition mechanics, or unsupported
  source rewrites are introduced.

## Targeted verification / required PR gates

`tests/infrastructure/test_run_prospect_source_epochs.py`: **component**
parser/date/adversarial tests for Earth W52 and FAX W61. They are not
evidence of whole-process acceptance.

`tests/api/test_native_prospect_source_epochs_http.py`: dedicated real
SQLite+HTTP short-calendar **full** source→confirmed birth→Saved→actual
Tournament MatchEngine/points→next annual generation→manual source Save→
subsequent year admission→physical restart→historical restore. Kept out
of Fast CI; executes under a dedicated Native Tour API job.

`scripts/native_prospect_source_epochs_browser_acceptance.py`: real
Chromium Admin generation/review→materialization→manual source Saved
version, with no simulated player admission by the UI.

All original native Earth/FAX/extended, 20+ minute native Tour, admission,
browser and negative integrity gates remain in parallel. New Native
competition persistence and source authoring paths trigger mandatory native
API checks. Never call the PR merge-ready while a relevant latest-head
check is pending, skipped unexpectedly, or failing.

## Remaining limitations

This one implementation block does not certify pre-alpha, 50×61 release
acceptance, numeric Health policy, external world imports, all multi-Branch
policies or new legacy birth/source modification workflows. Only
append-only future prospect records are supported. Changes or deletion
of historic rows remain forbidden.
