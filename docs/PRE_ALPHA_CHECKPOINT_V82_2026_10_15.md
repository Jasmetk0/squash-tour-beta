# Master v82 checkpoint — calendar decisions and focused PR review

Date: 15 October 2026. Baseline `buuk` **b63f40387bed75812ae9f9585734a6226b93fda9**, merge #1488. This is a documentation/product checkpoint and read-only code/CI audit, not a release or application implementation.

## Review scope

Fresh inventory covered the latest 100 updated PRs (all open entries were absent at audit start), with focused diff/code review of every PR added since the prior #1484 checkpoint: #1486, #1487, #1488. A compare from #1484 merge `8a4fe84483945526e89ee2e15416a561f5cafcd9` returned 29 commits and contained all three final feature HEADs. #1485 is closed unmerged. #1470 and #1472 are issues, not missing PRs.

Earlier already-audited #1454–1484 are summarized in Master §35.39 and existing v81/CI history. This pass does not claim to reread every old PR or rerun all old tests. Source review and actual final-head CI are distinct from mock component evidence and release acceptance.

## New PRs and CI

| PR | Final feature HEAD | Status | Available final-head CI |
| --- | --- | --- | --- |
| [#1486](https://github.com/Jasmetk0/squash-tour-beta/pull/1486) | `9a170b8a9e5edc755affafb9217ee85c1e9f18a6` | merged | [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38787954317) — success |
| [#1487](https://github.com/Jasmetk0/squash-tour-beta/pull/1487) | `090d75029a23995fdbb26f953e306e0b613898f3` | merged | [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38789878055) — success; [Pre-alpha Shell Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38789878236) — success; [Pre-alpha Full Simulation Boundary Targets Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38789878089) — success; [Pre-alpha Full Simulation Server Tasks Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38789878279) — success |
| [#1488](https://github.com/Jasmetk0/squash-tour-beta/pull/1488) | `23da7006a8dc425344c46dae0ac9729e2f8a5fe1` | merged | [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38792755361) — success; [Pre-alpha Full Simulation Boundary Targets Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38792755331) — success; [Pre-alpha Full Simulation Server Tasks Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38792755346) — success |

All eight available workflows were successful on the exact final feature HEADs. Fast CI jobs not selected for the changed scope were skipped, not executed as a full backend suite. Actual #1488 frontend log: 155 stable baseline tests + 41 changed/colocated tests and build passed. Server-task workflow: 14 backend tests and real browser/page-close/SIGKILL/recovery equivalence passed. Boundary workflow: 27 backend tests plus its browser scenario passed. Relevant run/job IDs: 38792755361/116621317181; 38792755346/116621829660; 38792755331/116621803747.

## Correct behavior and limits

- #1486 correctly remounts consent when Run/Branch/Task/revision, receipt/schedule proof or suffix slots change. Exact mutation arguments remain frozen for retry after response loss. The previous changed-evidence consent bug is fixed.
- #1487 fixes the previously inspected light-on-light Task Center styling, renders stored `progress.detail`/`blockers`, distinguishes current versus last checkpoint, explains supported extension approval and links server tasks to original receipts. Identity matching includes Run, Branch and parent command, not a display name.
- #1488 uses navigation-only links for the blocked task's exact Run/Branch Calendar and preselects a supported Season Builder registry entry. The tests mock HTTP for these new links. Neither navigation nor green existing recovery acceptance proves a new-season calendar has been authored/copied/Saved or its tournaments played.
- Actual #1484 CI evidence inspected at the preceding audit showed Season index 0 Week 61 → explicit Save → real canonical transition → Season index 1 Week 1 on the same second task, with replay/history preserved. Only three actual matches preceded mostly empty weeks. Keep that distinction from full populated season/50-season acceptance.

## Remaining findings

**A82-01 — confirmed component consent gap:** `FullSimulationWeekScheduleReview.tsx` uses an evidence-keyed form, but Cancel resets only the frozen request/mutation. If evidence stays identical, the form stays mounted with the previous checked consent and operator/reason. The next click creates a new `control_command_id` without a fresh consent action. An isolated test using the exact current production component, real React Query and mocked API reproduced this: failed request → Cancel → checkbox still checked/button enabled → second, distinct command ID. One test passed because it asserts the observed bug. This is not a backend integration test, a bypass of proof validation or evidence of duplicate sport writes. Add cancellation-generation/remount or equivalent explicit consent invalidation while preserving exact-request retry.

**A82-02 — localization:** new RunPackageSetupPanel requested-season/source-authoring guidance remains literal English. Complete touched CS/EN during the next UI/navigation slice; raw technical stored blocker IDs remain evidence, not fabricated translations.

**A82-03 — calendar integration target:** `domain/run_containers.py` still fixes 2000–2049/50/61; `domain/calendar/season_weeks.py` rejects non-61 years and has default offset 37. `taskCalendarHandoff` computes `2000 + season_index`; UI season validators restrict 2000–2049 and crossing-year labels. These matched the prior canon; they now require an explicit v82 migration, not a blind replacement or a claim that #1488 broke a previously supported Earth calendar. Inventory all callers, targets, Saved Revision payloads, age/annual rates and ranking duration paths.

**A82-04 — unfinished sports acceptance:** exact cause of the real post-boundary `week_preparation_required` must still be captured before claiming a fix. Author/copy/Save genuine calendars and resolve actual prerequisites through existing authorities; then prove multiple Tournament Editions and genuine MatchEngine games to an explicit next-week target on the same nonterminal task. Do not use a terminal first task, dummy results or an empty-calendar fallback.

Earlier observed transient SQLite heartbeat `database is locked` during green #1484 evidence is not established data loss. Investigate with bounded lease/concurrency tests if the calendar work touches that path; do not hide the error or inflate global timeouts blindly.

## Documentation integrity and implementation limits

Master v82 updates current product chapters/registries, preserves all 36 chapters and all 157 historical PAQ IDs, keeps dated audit evidence, and distinguishes new decisions from implemented behavior. AGENTS, constitution, frontend contract, README, active CURRENT_STATE/ROADMAP headers and release-test wording are synchronized. No application code or built-in data is changed by this checkpoint.

Focused PR tests follow `docs/PRE_ALPHA_TEST_POLICY.md`; a future release still requires complete regression, populated FAX season/50-season reference and explicit calendar compatibility acceptance. Exact growth curves, realism calibration and detailed training/deload scheduling remain open/deferred. This audit does not close all pre-alpha work.
