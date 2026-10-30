# Copied-FAX reference preparation — 30 October 2026

## Reproduced blocker

On `buuk` `edd237b7a2d5e1d69cf96aafce13799bf428253b`, actual HTTP
Preview → Materialize created and Saved 1,000 generated players, 80 World Tour
Editions, the initial ranking and authoritative Week 1. The input profile reported
ready. After adopting both current-week Tournament Ranking Snapshots, real Entry
preview failed because every newly generated ranked Edition had an empty points
table. This is a preparation defect, not evidence that the native or legacy
simulation engines cannot handle the copied fixture.

## Corrected boundary

The acceptance Calendar source now snapshots the same Season Category Points
initialization candidate used by an ordinary calendar preview. It does not write
the global Category registry, invent missing stages or consult it during replay.
Existing authored zero awards remain zero; missing qualification awards remain
missing. The Edition payload and source/preview fingerprints bind the entire table.

Reference Preview lists `incomplete_points_event_ids` and cannot be ready while a
World Tour Edition fails its existing points-completeness contract. Materialize
rejects that input before creating any Run. The existing input profile also reports
`FAX_ACCEPTANCE_RANKING_POINTS_INCOMPLETE` for an already-copied incomplete Calendar.
The historical schema names and source version remain; changed contents produce
changed fingerprints and require a fresh review. Stored earlier Runs are not rewritten.

Materialize captures World and Calendar documents once, validates their combined
preview fingerprint and installs those exact captured documents. It no longer
re-reads a possibly changed live source after creating the Run. Changes before
capture invalidate the reviewed preview; changes after capture cannot substitute
unreviewed Package bytes.

## Actual integration evidence

`tests/api/test_pre_alpha_fax_reference_preparation_api.py` uses the real HTTP API,
generator, World/Calendar adapters, ranking publication, shared-snapshot Entry AI,
Full Simulation driver and SQLite. It:

1. Copies the versioned built-in FAX World to an isolated read-only source.
2. Authors complete Category tables using the normal HTTP configuration API. Zero
   qualification awards here are explicitly disposable test inputs, **not FAX canon**.
3. Rejects a stale award/source preview before any Run exists.
4. Materializes and Saves exactly 1,000 generated players and 80 Editions.
5. Changes the live global points table and proves the Run-owned Saved profile stays
   unchanged; the already-copied source does not follow that live change.
6. Adopts the current-week ranking snapshots, including a real identical retry.
7. Freezes actual Entry decisions for the two Week-1 Editions from a shared snapshot.
8. Runs the real long-acceptance probe, which stops at
   `application_validation_policy_unresolved` without fabricating validation.
9. Opens a fresh API server/SQLite connection and verifies the same input profile,
   Entry authority/policy gate, immutable Saved Revision/hash and 1,000 identities.
10. Verifies the copied and original FAX source hashes remain unchanged.

The separate contract tests cover World/Calendar source changes both before
review confirmation and during Run creation, missing-point versus zero semantics,
read-only previews and historical snapshot independence.

`Pre-alpha FAX Reference Preparation` runs these exact bounded contracts and real
HTTP/SQLite scenario on a Ready candidate or manual dispatch. Draft skips do not
count as evidence. It leaves existing native/browser/release gates unchanged.

## Remaining boundary

The repository's baseline Category tables do not define all qualification awards.
This change deliberately reports that missing input rather than deciding it. A
complete disposable test configuration can reach the real automatic application
eligibility/deadline policy boundary; that policy remains OPEN. No Entry Fields,
Draws, results, native population owner or application validation are fabricated.

This proves reference **preparation**, not a played 80-Edition season, a native
reference migration, Save/replay of tournament results, historical intake realism,
lower-Tour aggregation, the mandatory 50-season acceptance or release readiness.
The next dependent sporting slice needs the owner's actual policy decision.
No unrelated Viewer work or pending PR #1662/#1670 files are changed.
