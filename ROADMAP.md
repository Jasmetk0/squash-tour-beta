# Squash Engine roadmap

This is a milestone summary, not a second product constitution. Master Vision v31 decisions synchronized into `PROJECT_CONSTITUTION_TECHNICAL_PLAN.md` take precedence; `docs/ENGINE_UX_SPEC.md` provides subordinate migration guidance. Status describes direction and does not imply that target behavior is already implemented.

## Current foundation — canonical model and migration safety

- Keep new work aligned with independent Runs, equal branches, and exactly one Viewer Branch per Run; migrate legacy `official_branch`/SimulationRun terminology only with compatibility and persistence planning.
- Preserve the invariant 50-season horizon (`2000/01–2049/50`) and exactly 61 Season Weeks per season.
- Preserve deterministic replay, historical snapshots, provenance, auditability, and operation-scoped validation.
- Strengthen contract/component test foundations now; add persisted canonical FAX Run materialization and genuine production-stack FAX integration tests as a later explicit slice.

## Near term — application shell and scope cleanup

- Complete the neutral Squash Engine Home with global Runs and Packages entry points.
- Keep Global Admin (no Run/branch/time context) distinct from Run Admin (one Run, active Admin branch, and time context).
- Standardize Run-scoped controls around Run, Branch, Time, and Viewer/Admin while preserving context safely.
- Continue turning Run Home into a working dashboard and move execution-heavy controls into dedicated Simulate workflows.
- Remove user-facing privileged Main/Official branch assumptions in favor of Viewer Branch terminology; treat legacy schema/API names as migration debt.

## Package and world lifecycle

- Provide separate global authoring for source World Packages and Category Packages.
- Materialize the selected World + Category Package versions as independent Run snapshots with provenance at Run creation.
- Ensure later source edits affect future Runs only and never silently rewrite existing Run history.
- Continue country/population, talent intake, player identity, and lifecycle work without hard-coded world content.

## Tour, simulation, and history

- Consolidate categories, Tournament Series/Editions, seasons, calendars, qualification, draws, and lifecycle validation into coherent workflows.
- Support deterministic simulation ranges from the next match through a full simulation, with visible long-job state and safe recovery boundaries.
- Expand historically versioned rankings, statistics, records, and read-only Viewer history without inventing unresolved ranking formulae.
- Build branch map/timeline, versions, checkpoints, and recoverable saves while storing common pre-divergence history once.

## Later realism and product depth

- Deepen player development, form, fatigue, health, style, and decision systems only after deterministic contracts are specified.
- Expand diagnostics, import/export, storage/recovery UX, competition formats, and analysis surfaces according to explicitly approved decisions.
- Do not silently implement open Master Vision areas such as the final navigation tree, Viewer reveal modes, Country Ranking formula, Category Package seasonal format, or the complete engine-wide seed contract.

## Guardrails

- Viewer stays read-only; all authoritative mutation and simulation stays in Admin/application commands.
- Runs are independent saved worlds; branches are timelines inside a Run, not lesser “sandbox Runs.”
- No branch is Main/Official. Viewer Branch is a display-selection role only.
- Package snapshots are not live links to global source Packages.
- Do not claim planned target behavior as implemented.
