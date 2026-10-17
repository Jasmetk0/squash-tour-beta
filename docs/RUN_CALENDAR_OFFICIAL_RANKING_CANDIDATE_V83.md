# V83 — Versioned calendar-aware Official Ranking candidate

**Scope:** deterministic, immutable Official Ranking candidate calculation on an **explicitly saved Run calendar**. An entirely new `calendar_official_ranking_candidate.v1` schema prevents any reinterpretation of historical FAX `official_ranking_calculation.v1` snapshots, signed hashes or Week 61 publication lineage.

## Usable domain/application integration

- `CalendarRankingWeek` represents season index and Week in Run-scoped time; `RunCalendar.ordinal()` supplies the actual W. Versioned RunCalendar v1 is mandatory for all new candidates. `RankingWeek` and its historical W61 ordinal remain intact.
- `CalendarRankingResult` keeps final resolved Q and main totals, Edition identity, provenance and exact completed/first publication week. By default a result remains eligible for **W** weeks; explicit positive per-result validity is already supported. Publication must strictly follow completion, and the input set cannot include future publications or out-of-horizon weeks. Closing-only final-season results remain **unsupported** in this candidate, not silently classified.
- `CalendarOfficialRankingSnapshot` includes source clock, typed week, historically effective Best N policy, predecessor fingerprint, input fingerprint, canonical rankings and disciplinary zero IDs. Best N picks highest points with historical completed-week/Edition tie-break; season boundary and 80th week are safe. Disciplines reduce available slots, expire at exact elapsed weeks and retain their *literal weekly* durations.
- Tour entrants appear only after their entry week. Retired players are excluded. Existing previous rank and persisted tie-break tokens disambiguate equal profiles, without hidden randomness.
- `load_calendar_official_ranking_candidate()` requires external expected hash, Run ID, Branch ID, week and Run calendar, and refuses mismatched or tampered candidates.
- `preview_calendar_official_ranking_from_saved_run()` requires exact expected Saved HEAD and a caller-owned coherent SQLite read snapshot. It verifies the actual Saved Run clock before evaluating previously resolved input facts. It **does not** resolve the provenance of sport results by itself.

## Strict migration boundary

The actual Official Ranking **writer/Week Transition** still uses legacy `RankingWeek`, old `RankingRevisionState`, signed publications and frozen Full Simulation tasks. The new candidate is a read-only calculation primitive; it cannot be saved/published as official, does not create edits, import unsaved outcomes, change audit history, permit restart of sporting workers or remove W52/W80 simulation fences.

Actual publication needs additional cohesive migration of the authoritative result/zero/correction manifests, transition state and week/season writers, replay semantics, long-term development and Frozen Task goals. A candidate preview **does not imply live sporting support**. Historic snapshots retain unchanged bytes/hashes.

## Verification

PR-critical tests cover W52/W61/W80 exact result expiry and publication, Season Week W → next Week 1 lineage, Week 80, effective/expiring disciplinary zero, Best N, prior tie-breaking, tour entry, retirement, legacy W61 row equivalence, row/clock/hash/identity tampering, duplicate/foreign/future data and read-only real SQLite Saved-head authority, including cold failure on corrupt Saved fingerprints. Fast CI final HEAD is required; broad release and full-season populated acceptance remain separate.


## Calendar source history integration candidate (after #1511)

A separately typed, **read-only** calendar source resolver now models
`CalendarRankingResultVersion` and `CalendarRankingZeroVersion`, preserving
corrected award and sanction lineages with exact effective weeks. Results
cannot be backdated before their original first publication, completed dates,
first-publication dates and result validity stay immutable across corrections.
Discipline corrections may adjust the duration/decision but cannot restart the
original effective week or alter the player/scope identity. Versions must be
canonical, hash-linked, within the saved Run's W/horizon and non-overlapping.
Resolving an earlier week ignores later corrections without rewriting history.

The source manifest fingerprint includes only versions already effective as of
the requested week and the immutable Run week basis; **horizon extension alone
cannot change a historical source manifest hash**. New calendar candidates can
chain from immutable snapshots created before a strict Run horizon extension
when W, season offset and start year are identical. Decreasing horizon or
rebasing invalidates that link; old serialized snapshots are not rewritten.

The signed Saved-head application bridge validates the current Run clock and
calculates the corrected read-only candidate plus a source manifest. **Important
trust boundary:** callers must still load source versions from independently
authenticated storage. The bridge validates structure/lineage, but it does not
claim the caller's supplied version objects are real match receipts. No
storage writer, ranking publication, historical legacy conversion, UI sporting
switch, rank correction mutation, Week Transition or Full Simulation is enabled.

Focused tests cover W52/W61/W80 correction timing, zero changes/expiry,
as-of manifest stability across horizon extension, immutable predecessor
compatibility and wrong-scope/hash/order/clock rejection, plus real signed-head
SQLite non-mutation. Follow-up must bind this model to an authoritative versioned
source store before enabling a publishing writer.


## SQLite unpublished source staging (next bounded vertical slice)

`StagedCalendarRankingSourceStore` adds two **separate namespaced SQLite
tables**, not the historical FAX `OfficialRankingResultVersionModel` or
`OfficialRankingZeroVersionModel`. Callers explicitly start a physical SQLite
read snapshot; writes require caller-owned `BEGIN IMMEDIATE`, then exactly
validate the signed Run/Branch Saved HEAD, RunCalendar, input lineages and stored
row identity/hash before appending. Unique composite keys enforce idempotent
exact retries and reject same-effective-week conflicting edits. The caller owns
commit/rollback; injected later failure leaves no partial staging record.
Reads verify **all** corrections and zero decisions, including future-dated
versions, and resolve an exact as-of source manifest before a read-only ranking
preview. Data persists across process restart. Different W/offset/start-year
Run clocks, stale heads, read-only scopes, forks without an ancestry materializer
and already published legacy sporting branches fail closed.

**Crucial limitation:** these are *unpublished internal staging* rows. They
are deliberately **not** included in immutable Saved Revision components,
restore, historical Saved diff, Branch forks, Viewer, World Events or
authoritative ranking source provenance. The caller is still responsible for
authenticating match/Edition/disciplinary receipts, and the recorded row hash
is a corruption check, not an external authority signature. Do not add a
public user-edit endpoint, interpret these rows as sporting state, or unlock
Full Simulation. Future authoritative integration must migrate the trust
boundary and Save/fork/restore/publication atomically. Staged candidates
are only operator/developer inspection, not a production sporting write.

**Saved HEAD pinning:** each staged source row records the exact immutable Saved Revision ID active at creation. Subsequent read and write refuse any row originating at a different Saved HEAD. A later legitimate user Save (including a production horizon extension creating a new Saved Revision) therefore fails closed until a reviewed rebase/materialization is implemented. Pure domain horizon continuity does not override this staging ownership barrier. This is deliberately not an automatic Save or fork migration.


## Immutable SQLite staging checkpoint bundle (post #1513)

An internal versioned `calendar_ranking_source_staging_bundle.v1` combines
the exact Run and Branch IDs, pinned Saved HEAD ID + validated immutable
Saved content hash, full explicit RunCalendar and complete canonical
hash-linked result/disciplinary-zero version histories. The canonical
bundle SHA-256 covers all these fields. `load_calendar_ranking_source_bundle`
requires an **externally supplied trusted expected SHA-256** as well as exact
Run/Branch, Saved origin and Run calendar; the payload alone cannot authorize
its own import. It fails closed on changed clock, horizon, origin, incorrect
scope, invalid history, altered or omitted sources.

The SQLite staging store offers `export_bundle` under physical `BEGIN`
and `import_bundle` under the caller's `BEGIN IMMEDIATE`. Import validates
the *entire* bundle before writing, installs only into an empty isolated
staging store, permits byte-equivalent idempotent retries, and rejects
partial or conflicting target histories rather than merging. It verifies the
installed fingerprint inside the same caller transaction; errors roll back
all rows. Restoring an unmodified bundle into an identically scoped clean
SQLite database survives process restart. W52/W61/W80, zero corrections,
historical as-of resolution, tampered rows/payloads and partial transaction
failure are covered by real SQLite PR-critical tests.

**NOT a product Save, Branch fork, restore operation or promotion to official
sporting facts.** The bundle must not be embedded into new Saved Revisions or
served through public UI without full component ownership/fork/restore,
provenance and replay contracts. A new Saved HEAD, even after compatible Run
extension, requires an explicit reviewed rebase path; copying a checkpoint
from another Branch/Run is rejected. It is a bounded persistence/recovery
building block, not a real tournament source importer or Full Simulation
unlock.
