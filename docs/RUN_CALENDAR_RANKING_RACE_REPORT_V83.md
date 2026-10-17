# Run-calendared ranking/race point reports — V83 dependency

## Existing compatibility and new capability

The legacy `RankingRaceEngine` remains a **deterministic read-only points report**, not the authoritative Official Ranking publication writer. Its historical no-calendar interface still uses W61, 61-week default validity, existing Best-12 point selection and byte-compatible `RankingRaceReport` JSON structure. Passing a historic `RunCalendar.legacy_fax()` object as a new explicit clock is forbidden; absence of clock is what means legacy interpretation.

New callers pass the verified **RunCalendar v1** from `resolve_saved_run_calendar` and receive `RunCalendarRankingRaceReport` with `run_calendar_ranking_race_report.v1` source-clock provenance. The default rolling validity is exactly **W weeks**, independently of season offset and display labels. Explicit positive `window_weeks` overrides are allowed and never silently clamped; Race remains **target-season only**, not rolling. `best_of_results` retains the existing default 12 for *this report*; that default must not be substituted for the separate, versioned Official Ranking Best N policy.

Inputs and requested ranking/Race positions are validated against the **exact Run start year, W and season horizon**. W80 Week 80 works with no modulo or 61-week truncation; W52 Week 53 fails. Old years before 1900 may be used only with an explicitly supplied versioned calendar. A report of elapsed time cannot include future tournament sources, including events with no point awards or unranked results. Report model reload validates source clock and rejects out-of-horizon and future point awards. Ranking points come solely from deterministic recorded placement/round and configured authored table, with no hidden outcomes.

## What it does **not** enable

This is deliberately a narrowly scoped **calculator migration with real Signed Saved-clock integration evidence**, not a new Run simulation mode. `RankingWeek`, Official Ranking snapshots/publications, disciplinary-zero durations, player annual sporting development, week/season transition, Full Simulation targets, and immutable historical replay still contain FAX/W61-specific semantics. **All sporting writer guards remain closed** for non-reference clocks. Do not remove them or claim W52/W80 sporting readiness from this report.

No new endpoint, Save, DB mutation, generation, task or historic Saved Revision modification is performed. Wiring this calculator into future Run sport requires the authentic stored result history, corresponding explicit clock and safe migration of the independent authoritative consumers. Do not feed current legacy simulated sport directly into an arbitrary calendar or reinterpret old FAX hashes.

## Regression evidence expected

New PR-critical pure tests exercise W52/W61/W80 result ages, exact W-1/W cutoff, W80 Week 80 and offset 37, optional nonclamped windows, Race independence, future source/input injection, invalid horizon, year zero, default legacy output equality, serialized provenance tampering and horizon extension stability. SQLite tests load an actual **hash-verified Saved Revision** and prove no current-state mutation or change to Full Simulation preflight. Final-head Fast CI and relevant browser acceptance are still required before merging. Full reference-season and release gates are separate.
