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
