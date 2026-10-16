# Current calendar implementation — Master v82

Verified base `buuk`: `85966e03cf382d34e3375100809d6e1d924fc4df`, merged #1495
(15 October 2026). Review of #1490–1495 found all six merged and all available
final-head workflows successful. #1489 Master v82 is merged. The former #1488
baseline remains historical evidence, not the current implementation head.

**Implemented on buuk:** A82-01 fresh-consent cancellation fix; pure versioned
Run calendar W/offset/start/horizon; explicit default calendar in new Run and
first Saved Revision; hash-verified selected-Branch calendar reads; read-only
calendar target preview for W52/W61; fail-closed guards on still-legacy
Week/Season/Full Simulation execution. Other clocks are not sporting-ready.

**Open, verified PRs (not merged):** #1496 calendar creation/UI/Home and guarded
sporting writes, final `6c8b2ed48e01ff927dca8995c84ac3308c90841d`, all 12 workflows
green; #1497 explicit age/birth year units, final
`76c3177b05997fce3332298bd0f7f63c706b04fa`, Fast CI green. Their combined local
tree passed 135 focused backend tests. The 1,000-player browser Save race was
traced to navigating before the Save response, fixed by awaiting the actual
committed receipt, and then passed without weakening Saved-HEAD assertions.

**Current PR candidate (stacked on #1496):** generation preflight at the shared
Run-owned preview service, so direct preview/Keep/edit/proposal routes cannot
sample players under an unsupported saved clock. Archive reads remain exact,
non-regenerating reads. See [generation gate](docs/PLAYER_GENERATION_CALENDAR_GATE_V82.md).

**Next:** propagate the verified clock through actual generation/lifecycle,
ranking/annual-development state and authoritative transition/target callers.
The age helpers alone do not finish that migration. Keep unsupported clocks
honestly planning-only until actual execution proves each boundary, then add
explicit prestart edits, horizon extension and import compatibility workflows.

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
