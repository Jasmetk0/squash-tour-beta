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


## Signed Saved canonical tournament → W61 calendar ranking inspection

`saved_canonical_tournament_ranking_sources` is a **read-only** compatibility
bridge from actual persisted Run/Branch-owned canonical tournament authorities
in the immutable `ranking_preparation` Saved Revision component to
`CalendarRankingResultVersion` candidate records. It verifies the current
Saved HEAD and full Saved content hash, the signed ranking component hash,
exact Run/Branch and Edition identity, and identical live owned source hash.
It reuses `prepare_canonical_tournament_ranking_sources` rather than
recomputing or guessing tournament awards. All player result/award provenance
is validated, and if Saved ranking result versions exist for that Edition,
their initial versions must agree with the canonical projected awards.
The preview service can calculate a deterministic read-only candidate
from these sourced rows, including per-player points and effective dates.
It mutates no SQLite records, Signed Save, staging bundle, Viewer or World Event.

**Calendar compatibility gate:** this bridge is deliberately limited to
the explicit canonical FAX Run clock W61, offset37, starting 2000, horizon 50.
`TournamentRankingBinding` and existing canonical Result/Point Award authority
still carry the **legacy `RankingWeek`** contract. Converting them into
W52/W80 would falsely reinterpret signed historical dates. W52/W80, changed
start year/horizon, Closing-only Week61 records, legacy compatibility-only
Owned sources, fork inheritance without a dedicated materializer, unsaved
Owned rows and a Saved/live mismatch fail closed.

**Authority boundary:** Saved canonical tournament evidence is sufficient to
prove its original event award amounts and proposed first publication timing
for a *candidate inspection*, NOT to publish an Official Ranking or apply
new corrections, zero decisions, Week/Season Transition or Full Simulation.
A future calendar-native tournament authority and Save/restore/fork
integration must be implemented before turning this read-only adapter into
a non-FAX sporting writer.


## W-native complete knockout → whole-edition staging (post #1515)

`CalendarKnockoutRankingEvidence` is a new, separately versioned **calendar-native
preparation evidence** object: exact Run/Branch, Edition, explicit RunCalendar
(W52/W61/W80 supported), completion/publication weeks, ordered power-of-two
bracket entrants (up to 128), and the entire ordered winner/loser match tree.
Every match must refer to precisely the two eligible players at its own
round/position; the following round may only contain the winners from its
two preceding matches. BYE/W/O/RET, missing matches, duplicate entrants,
misordered rounds, impossible winners, incomplete/unranked distributions,
fallback points and future/out-of-horizon publication fail closed.
Authored finishing-stage point distribution covers precisely the actual
placements. Deterministically projected `CalendarRankingResultVersion` rows
have one source fingerprint across the full evidence, start at the first
publication week and cannot fabricate corrected history or disciplinary zeros.

`stage_calendar_knockout_ranking_results` validates the entire draw and an
**independent caller-provided expected evidence fingerprint** against the
Run's signed current Saved clock, then stages the entire Edition as one
transaction-owned batch. Exact retries are read-only; an already partially
populated, corrected or differently sourced Edition is rejected rather than
silently merged. The caller must use `BEGIN IMMEDIATE` and own commit/rollback.
A forced mid-Edition error leaves no rows, while completed staging survives
restart and can drive the existing signed-clock read-only Official Ranking
candidate in Week W → next Season Week 1. Full real SQLite coverage exercises
W52, W61 and W80 and adversarial brackets.

**Important:** this is **not** a simulation engine, nor proof that the
supplied matches happened in the live Run. The external expected fingerprint
and complete bracket checks are integrity/consistency conditions; they do
not authenticate the result against an actual Run-owned Match Authority.
The data is strictly unpublished staging, outside immutable Saved Revision
capture/restore/fork, Viewer, World Event and the authoritative Week/Season
Transition writer. No production W52/W80 sporting execution is unlocked.
The next dependency is an actual calendar-native Run-owned match/result
authority that can authenticate the completed evidence before staging.


## Versioned MatchEngine witness source → W-aware ranking staging (post #1516)

`CalendarEngineMatchWitness` introduces an independently fingerprinted
**complete MatchEngine-result-shaped receipt** containing the frozen match
input fingerprint, full serialized `MatchResult` with real rally events and
the input/result receipt fingerprint computed using the production canonical
algorithm. Validation rejects aborted/RET matches, missing rally logs,
invalid set winners, unordered/post-terminal games, contradictory score
totals, incorrect BO odd-game threshold, reused receipt identity, and
tampering with the input/result fingerprint. Nested `MatchResult` validation
also checks rally-log scores, result sets, timeline and stamina semantics.

`CalendarEngineKnockoutEvidence` binds the entire existing W-aware valid
full knockout bracket to exactly one engine witness per match in canonical
round/position order. Winners, losers and winner-set scorelines must match
the engine results exactly. Its independent SHA-256 covers every frozen
rally event and match receipt as well as player placement/point rules.
The new `prepare_calendar_engine_knockout_versions` projects the same
correct initial Edition results as the v1 bracket route, but sets each
source's fingerprint to the **complete MatchEngine witness root**, not
merely a manually supplied list of winners. The associated staging command
uses the existing whole-Edition, exactly idempotent SQLite transaction
guard and signed Saved W52/W61/W80 clock; it does not rewrite any legacy
FAX source hashes. Real seeded MatchEngine results exercise W52/W61/W80,
SQLite restart and the last-week/next-season boundary.

**Trust boundary remains explicit:** a model-valid MatchResult plus its
frozen-input receipt is **not itself authenticated as a result actually
committed by the Run's saved sporting writer**. The caller supplies an
independently trusted expected witness root; its origin must eventually be
cross-checked against immutable Saved Simulation Slot/group authorities
before any sporting publication. This code remains internal unpublished
staging. No public API, no official ranking, no W52/W80 Full Simulation
unlock, no invented Qualification/W/O/RET treatment.


## Signed Saved Simulation Slot → verified W61 MatchEngine ranking candidate

`saved_slot_verified_knockout_evidence` now reads actual **Run-owned,
completed Simulation Slot match receipts** from the **immutable, hash-verified
Saved Revision**, not caller-provided simulated outcomes. For one explicit
fully completed main-only knockout Edition it:

- verifies the exact Saved HEAD and the complete signed Saved Run clock,
  and intentionally accepts only FAX W61/offset37/start2000/50 seasons;
- validates the full Saved Simulation Slot component using the production
  restore-grade loader (its own component fingerprint and slot/effect/replay
  semantics);
- requires every Edition match to belong to a complete Slot in the actual
  completion week, with no extra, missing, W/O or duplicate event groups;
- rebuilds every group receipt using the production `load_authoritative_group`
  validator, matches all original command/input/result/payload columns
  **exactly** against the corresponding live SQLite group, and rejects
  live-only matches that were never captured into Saved;
- builds the versioned MatchEngine witness **from saved authoritative input
  and result fingerprints**, not independently supplied winner labels,
  then validates all winners, set totals, logs and bracket progression;
- exposes a purely read-only `preview_saved_slot_verified_knockout_ranking`
  using existing Saved-calendar source-history/ranking readers.

Real SQLite acceptance constructs a three-match tournament using the actual
AuthoritativeSlotMatchExecutor, captures its real `simulation_slots` Saved
component, verifies Signed Save/Live group integrity, reopens SQLite and
reproduces a ranked candidate without writing. Negative tests cover missing
Saved component, altered Saved component/revision hash, changed live receipt,
cross-week match, fake winner, stale head, unsupported clocks and fork ancestry.

**Scope:** this authenticates **match outcomes**, NOT the caller's authored
point-distribution policy or canonical Edition schedule/entry authority.
The preview is not Official, and it does not write or authenticate W52/W80:
their actual Match/Slot writer remains 61-based, and casting that persisted
legacy week ordinal into W52/W80 would manufacture provenance. Full
Save/restore/fork/publication still requires a reviewed native writer.
