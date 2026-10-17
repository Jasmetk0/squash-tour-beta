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
