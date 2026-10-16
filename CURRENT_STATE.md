# Current calendar implementation — Master v82

Verified base `buuk`: `643ee60868ee57cecfdc560e9079ac68f2bdda00`, merged #1498
(16 October 2026). Fresh review confirms #1496, #1497 and #1498 are merged;
no other PR was open at task start. Their final checks were green before handoff.
Master v82 remains the canon; this task changes implementation, not product scope.

**Implemented on buuk:** consent cancellation fix; versioned Run clock and exact
conversion/target planning; optional CS/EN custom calendar creation with immutable
first Save and correct Home timeline; hash-verified selected-Saved clock authority;
explicit age/birth unit helpers; guards on still-legacy generation and sporting
writers. Archive/proposal reads preserve original data. Custom clocks are not yet
sporting-ready. #1496 also fixed real standalone Health bootstrap and an acceptance
Save/navigation race without weakening Saved-HEAD checks.

**Current candidate:** calendar-aware initial-player preview through the real Run
API and the existing Players → Generate page. New v2 identities bind the actual
clock, correct birthdays/ages/population cohorts and source-year diagnostics;
v1 fingerprints and adoption/replay paths remain unchanged. A custom-clock
preview is read-only and cannot add players or run sport. Actual Earth-package
1,000-player HTTP/SQLite tests and the extended existing Shell browser scenario
own the relevant acceptance. See [contract and verification](docs/CALENDAR_PLAYER_PREVIEW_V82.md).
This candidate is not included in the base above until the user merges it.

**Next:** version actual InitialWorld/bootstrap/lifecycle and the Run-local time
position contract before accepting v2 players into authoritative state. Then
migrate annual sporting development, ranking validity and transitions/frozen
Full Simulation goals. Existing guards stay until each writer is proven. Custom
prestart edits, all-Branch horizon extension and import compatibility remain.

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
