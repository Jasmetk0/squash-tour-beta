# AGENTS.md — Beta_Engine Operating Instructions

## Project purpose
Build a deterministic, data-driven **men’s professional squash career simulator** for World Tour + Elite Tour with realistic tournament flow, rankings, race, careers, and historical memory.

## Source-of-truth rules
1. **`PROJECT_CONSTITUTION_TECHNICAL_PLAN.md` is the current active implementation/product blueprint** for coding and product work.
2. **`Beta_Engine.docx` is an older constitutional reference/background document.** Use it for context, not as the deciding implementation source.
3. If `Beta_Engine.docx` conflicts with `PROJECT_CONSTITUTION_TECHNICAL_PLAN.md`, the markdown technical plan wins for current implementation work.
4. `README.md` remains a short project overview; `ROADMAP.md` remains a milestone summary.
5. Preserve all non-negotiables unless a clearly versioned plan/constitution revision is approved.
6. Document assumptions in each task output.

## Architecture principles (non-negotiable)
- Deterministic modular monolith (Python domain core, not microservices).
- Separate bounded contexts: players, tournaments, matches, rankings/race, health/injuries, history, commissioner.
- Keep domain logic pure and testable; isolate I/O in infrastructure layer.
- UI is a client of the engine; UI convenience must not drive core architecture.
- Admin/Engine Mode and Viewer/MSA Website Mode must remain conceptually separated.
- History/snapshots are product features, not optional logs.

## Determinism rules (non-negotiable)
- Reproducibility target: `(world_state_snapshot + config_version + RNG seed + command)` => identical results.
- Use injected RNG service only; no direct ambient randomness.
- Maintain explicit seed hierarchy (`global -> season -> week -> match`).
- Commands should be idempotent when feasible.
- Any feature that breaks replayability is blocked.

## Ranking and competition rules (non-negotiable)
- Official ranking model: **rolling 61 weeks, best 12 results**.
- Race is separate seasonal standings for World Tour Finals qualification.
- Tournament model must support qualification + main draw, seeds, byes, wild cards, lucky losers, withdrawals, walkovers, retirements.
- Match format is set-by-set professional squash (games to 11, win by 2).

## Config / data-driven rules (non-negotiable)
- Editable world content must be in config/data, not hardcoded logic.
- Required config domains: countries, calendar templates, tournament templates, points, balance constants.
- Validate config with schemas + business-rule checks before simulation.
- Persist `config_version`/fingerprint with snapshots for reproducibility.

## UI rules
- Required simulation command levels: sim next match, round, tournament, week, full season.
- Provide commissioner/admin controls and read dashboards (tour, players, rankings, race, history).
- UI should call application/API commands; no hidden client-side simulation logic.

## AI limitations (non-negotiable)
- AI may explain, summarize, analyze, and suggest.
- AI must not decide authoritative sporting outcomes or replace ranking/draw rules.
- Core outcomes remain rule-based, deterministic, testable.

## Testing expectations
- Every logic change must include deterministic tests for touched logic.
- Minimum checks per slice: replay test (same seed => same output), contract test (API/command behavior), snapshot integrity check.
- Add regression tests for edge tournament states (withdrawal, LL, retirement) when touched.
- Reject changes that increase realism but reduce determinism/observability.

## Review expectations
Each PR/task should include:
- changed files and rationale,
- tests/checks run,
- assumptions and constraints,
- follow-up tasks,
- confirmation of non-negotiables preserved.

## Commissioner/admin safety rules
- All manual overrides must be explicit commands with audit logging.
- No silent state mutation.
- Validate commissioner actions before commit; reject illegal states.
- Provide rollback/rerun path (or documented limitation) for admin interventions.
- Protect ranking/history continuity after overrides.

## Build discipline
- Deliver by vertical slices; stabilize core before realism expansion.
- Avoid complexity creep and UI-driven shortcuts.
- Do not implement speculative mechanics before MVP-critical paths are solid.
