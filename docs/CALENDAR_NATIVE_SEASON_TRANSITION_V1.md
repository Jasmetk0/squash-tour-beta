# Native configured Tour Season Transition V1 — candidate (19 October 2026)

## Code scope and dependency

Base: owner-merged performance PR #1543, `buuk` merge `63a489b6857cece922a98e597ee225a8deb07119`. The **new** PR #1545 is a candidate until its final-head targeted, browser and Native Tour HTTP/SQLite checks pass. This file records current implementation, *not* release or Master authority; historically valid decisions and legacy semantics prevail. #1544 is the functional target.

Unlike the existing in-season `transition`, the new operator action `season-transition` is legal only when the currently **Saved** full-population sporting clock is exactly Season s / Week W and the Run calendar contains Season s+1. The target is Season s+1 / Week 1, ordinal exactly +1. It never clamps beyond the horizon or invents another W/offset. A horizon extension remains a separate reviewed operation. Its preview is bound to the exact Run/Branch, Saved HEAD, sporting and Tour fingerprints, command payload and seed; an explicit confirmation is required. Commit is atomic; the resulting Tour/Checkpoint/ranking is still a **Working** authority until a separate manual immutable Save.

## New immutable historical authority

- `calendar_sporting_week_advance.v3`: explicit `configured_tour_season_transition` scope; version enforces only W→next season W1. Earlier v1/v2 events remain strictly within-season; their serialized fields, RNG and fingerprints are unchanged.
- `calendar_sporting_checkpoint.v10`: requires an authentic v3 season event in the ordered native sporting history; all previous versions forbid it. All 57 attributes, player identities, played match results, closures, lineage and nonparticipants remain; terminal W development/recovery takes only facts known by the completed week with exactly 1/W annual attribute exposure. This is **not** full Health progression or an invented seasonal statistics reset.
- `calendar_tour_authority.v2`: requires an actual crossing, records one coupled Official ranking and distinct `season_transition_completed` public event at the new Season Week 1, links effective policies, lifecycle source, prior ranking and sporting event by immutable fingerprints. Historical v1 Tour snapshots remain unchanged. The new season ranking inherits the last applicable Best N unless an explicitly Saved future-effective policy exists.
- The ordinary week ledger remains independently validated and no pre-existing v1/v2 event may cross. Every Saved Revision is checked against physical SQLite scope and actual signed payload; forged content with a rehashed component fingerprint still fails the full replay and Tour/ranking/coupling checks.

## Operational boundaries

The implemented scope is **native configured Tour only**. It retains actual player state, signed sporting matches and current form/load across season boundary, performs the current supported last-W development, transitions retirements/birthdates via lifecycle history, and publishes the actual W-aware Official ranking after the manual Save. Only Tour's temporary global slot cursor resets to 0; no unsupported seasonal reset is invented.

Run Prospects/intake requiring native calendar materialization, unresolved Health healing/permanent effects, due staged disciplinary/correction authorities, unsupported match-containing Branch remap/fork, protected source edits and Full Simulation remain blocked, as before. Do not treat a successful bounded Season Transition as a fully autonomous multi-season World or first pre-alpha release.

## Test policy, acceptance and remaining work

Domain tests cover W52, FAX W61/O37 and W80 crossing, wrong weeks, altered target calendar and exhausted horizon. A dedicated true HTTP+SQLite test runs **W4** to exercise an entire sporting last-week-to-first-next-season flow without repeatedly waiting through 52 or 80 production weeks: two official weekly transitions, real terminal season preview and commit, with and without an explicitly future-effective incoming Best N policy; late-transaction injected rollback, deterministic retry, manual Save, revision hash, forged rehash rejection, real process restart and backward/forward historical restoration. Browser CS/EN consent test checks that Season Transition never performs implicit Save.

The existing mandatory W52/W61/W80 Native Tour browser and full real HTTP/SQLite acceptance must pass on the exact final head. Full W52/W80 end-of-season browser acceptance, 50×61 reference endurance, numeric Health, historical intake and season-closing statistics/notification features are **not yet** completed by this slice. No timeout, test scope, played-result or population reduction is permitted. Final result and known limitations must be updated once all checks finish.
