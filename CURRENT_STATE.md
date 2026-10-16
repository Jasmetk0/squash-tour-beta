# Current calendar implementation — Master v82

Verified base `buuk`: `2b472b287452b9faa00552ef0b74889e83cfc785`, merged #1501
(16 October 2026). Task-start GitHub check found no open PR. The local tree was
verified against that exact base. Master v82 remains the canon.

**Implemented on buuk:** consent cancellation fix, versioned Run clock and target
math, custom calendar creation/Home, Saved clock authority, age/birth helpers,
legacy sporting guards, calendar-owned initial-player previews (#1499), reviewed
population confirmation/Save/fork/restore/restart (#1500), and a separately reviewed
fresh initial Health baseline with its own manual Save (#1501). Population lifecycle
is `population_only`; the baseline has no Injury/Illness history. Neither enables
custom-calendar sporting progression or calibrated initial health.

**Current candidate:** actual Run-owned Injury/Illness facts through the existing
Admin health inspect → preview → explicit confirmation → separate Health Save.
The real saved-player profile now exposes a CS/EN Health tab. Dates carry the exact
Run calendar; recovery estimates remain explicit weeks. First effective confirmed
edit converts a baseline to `player_health_calendar_state.v2`; old baseline/V1
Saved payloads and hashes remain unchanged. Writer-lock proof checks, atomic
health/receipt/dirty Draft, exact retry, materialized fork provenance and backward/
forward restore/restart use the existing persistence mechanisms. Pure fact carry
is tested across year/season boundaries without creating sporting state. See the
[health contract](docs/CALENDAR_INITIAL_HEALTH_V82.md) for evidence and limitations.
This candidate is not part of the base above until the owner merges it.

**Next:** annual sporting development, ranking validity and authoritative
transitions/frozen Full Simulation goals. Existing guards stay until each writer
is proven. Custom prestart edits, all-Branch horizon extension and import
compatibility remain. Health fact editing is not W52 sporting execution or realism
calibration.

Authority and long-term task:
[Master](SQUASH_ENGINE_MASTER_VISION.md) §§3.2/6.1/6.9–6.12/31.37;
[v82 checkpoint](docs/PRE_ALPHA_CHECKPOINT_V82_2026_10_15.md);
[handoff](docs/PRE_ALPHA_NEXT_CHATGPT_TASK_V82_2026_10_15.md).

## Verified boundaries to preserve

- Saved history/Compare/replay remain exact revision-owned reads; no current fallback, pre-fork ownership rewrite or regenerated old matches.
- Full Simulation has durable server tasks, exact controls/targets, immutable terminal summaries and a fenced SQLite lease. Browser close is not process death; process restart requires explicit recovery.
- The first real hybrid parent is terminal at Week 2. The second parent survived restart and crossed the actual Season boundary; only the latter can be continued where nonterminal.
- A82-01 was fixed in merged #1490; no duplicate authoritative work was established. A82-02 is incomplete touched localization. A82-03 is the new calendar integration gap. A82-04 is unfinished populated second-season acceptance. Details/tests are in the v82 checkpoint.
- Exact growth/realism/statistical calibration, the canonical richer attribute migration and the rest of the complete pre-alpha scope are not finished. New calendar targets do not close older deferred/open product questions.

## Current execution order

1. Fresh-fetch buuk/open PRs; verify the v82 documentation merge and avoid overlapping work.
2. Preserve merged #1490 consent/response-loss regressions; proceed to usable calendar creation.
3. Inspect all actual time callers; centralize Run calendar/versioned legacy semantics, then propagate safely through persistence and authoritative transitions/targets.
4. Build usable optional calendar/range Admin preview, age/annual/ranking/import integration and explicit horizon extension with relevant real persistence tests. Preserve valid default FAX operation throughout; unsupported migrated scopes must be honest.
5. Extend the strongest real sports acceptance across genuine next-season tournaments, then work toward populated full-season/50-season release gates and calibrated realism.

Keep ordinary PR checks focused. Use Codex only for a bounded difficult integration after direct ChatGPT has gathered the concrete context; if credits end, continue the same branch/PR directly. Never merge on behalf of the user.

## Earlier implementation history

This active summary is intentionally short to avoid repeatedly loading hundreds of obsolete candidate notes. Complete pre-checkpoint evidence remains in the [pinned previous CURRENT_STATE.md](https://github.com/Jasmetk0/squash-tour-beta/blob/b63f40387bed75812ae9f9585734a6226b93fda9/CURRENT_STATE.md) and Git history. Those dated notes are evidence of their time, not an open PR queue. Master chapter 35 and the v82 checkpoint preserve the current audit boundaries.

## Calendar horizon extension preflight hardening (candidate)

The pure `RunCalendar.extend_to` planning helper now rejects extended horizons outside the same signed 32-bit timeline/count and exact JSON week-ordinal ranges enforced at Run creation. Focused boundary tests cover basis preservation, legacy refusal and overflow. This is **not** a writable extension command: no Run, Branch, Saved Revision, Draft, task or sporting state is changed by this helper. All-Branch atomic extension, historical revision compatibility, review/Save and Completed continuation remain pending.
