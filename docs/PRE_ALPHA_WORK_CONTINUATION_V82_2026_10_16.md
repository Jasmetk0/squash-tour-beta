# Continuation — reviewed calendar creation

User: continue implementation directly in this task, use current 6.1 Sol High,
avoid duplicated Codex work. User alone merges. Integration branch is `buuk`.

## Reviewed baseline

`buuk` 85966e03cf382d34e3375100809d6e1d924fc4df, merged #1495.
PRs #1490–1495 are merged and their available final-head checks were green:
consent generation fix, pure RunCalendar, explicit first-save clock, verified
Saved clock authority, read-only target math, Week/Season execution gates.
No open PR overlapped at the last inventory. Do not reimplement those slices.

## This branch

`feat/v82-calendar-settings-20261015`: optional new-Run calendar API and pure
creation preview; usable CS/EN FAX/Earth/custom form; reviewed exact request and
returned clock; bounded Run-local Home progress. Existing name-only defaults
remain. W52/O1/O35 creation, Save, fork and restart are real HTTP/SQLite tests.
Legacy sporting writes are fenced for unsupported explicit clocks, preserving
exact completed replay and historical fork materialization. Real standalone
acceptance found and fixed a missing initial Health bootstrap.

See `docs/RUN_CALENDAR_CREATION_V82.md` for contracts and limits. W52 creation is
planning/storage support only. Do not delete the execution guards as a shortcut.
No old payloads, sources, seeds, task goals or rankings were migrated in place.

Local focused evidence: 51 backend creation/calendar/authority/bootstrap/fork
checks; 15 focused creation/sporting/standalone/slot checks; 25 new/touched UI
checks; earlier 169 focused/stable UI checks; production TypeScript/Vite build.
The existing Shell Browser workflow now owns real custom creation evidence.
These are not release gates, populated full seasons or W52 sporting acceptance.
Check every required workflow on the latest PR head before offering merge.

## Next work

1. Fresh-fetch `buuk` and open PRs; determine whether this branch was merged.
   Finish/repair its final-head CI before starting overlapping changes.
2. Propagate explicit calendar units through player age/yearly development and
   ranking validity, preserving absent legacy semantics and exact old replay.
   Inspect actual callers; do not just add unused helpers or globally scale all
   fatigue/PR/entry/penalty coefficients. Avoid inventing open growth mechanics.
3. Remaining sporting clock migration must cover actual RankingWeek ordinals,
   Week/Season boundaries, source calendar dates and frozen Full Simulation
   targets together before enabling a formerly blocked clock.
4. Explicit prestart edits, all-Branch horizon extension, import compatibility
   and stronger populated next-season/full-season acceptance still remain.
5. Update current-state evidence at meaningful checkpoints. Never merge for user.

## Local environment at this checkpoint

Isolated worktree: `/workspace/scratch/725c98cf5edf/calendar-work`.
Do not overwrite the dirty original `squash-tour-beta` checkout.
Python: `/tmp/squash-calendar-env/bin/python` with editable project/dev deps.
Node bin: `/opt/codex/runtimes/codex-primary-runtime/dependencies/node/bin`.
`web/node_modules` is a local dependency symlink; never commit it.
Local Playwright browser download failed; no claim of local Chromium execution.
CI uses its installed Chrome. Public git fetch works, git push lacks credentials;
publishing uses the connected GitHub blob/tree/commit/branch/PR API.
