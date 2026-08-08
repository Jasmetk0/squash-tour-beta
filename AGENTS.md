# AGENTS.md — Squash Engine operating instructions

## Product and documentation authority

Build a deterministic, data-driven manager and simulator of the fictional men’s professional FAX squash world.

When sources conflict, use this precedence:

1. explicit newer user/product decisions,
2. the current Master Vision and later synchronized revisions,
3. `PROJECT_CONSTITUTION_TECHNICAL_PLAN.md` (the active repository constitution),
4. subordinate guidance such as `docs/ENGINE_UX_SPEC.md`,
5. older documents, handoffs, and current beta behavior as history/implementation evidence only.

`Beta_Engine.docx` is non-authoritative background. `README.md` is an overview and `ROADMAP.md` is a milestone summary; neither may override the constitution. Mark assumptions and distinguish implemented behavior from target behavior.

## Current canonical product rules

- A Run is an independent saved world with exactly 50 seasons, `2000/01–2049/50`; every season has exactly 61 Season Weeks.
- Branches are equal alternative timelines inside a Run. Never introduce a privileged Main/Official branch concept.
- Every Run has exactly one **Viewer Branch**. It only selects the timeline shown by Viewer; legacy `official_branch` technical names are migration debt, not product terminology.
- Every Run selects exactly one World Package and one Category Package. At creation their selected versions become independent, versioned Run snapshots; provenance remains, but there is no live source link.
- Viewer is historically faithful and read-only. Admin is authoritative and has distinct Global Admin (no Run context) and Run Admin (Run + active Admin branch + time context) scopes.
- Ranking policies and snapshots are historically versioned/configurable. Do not revive obsolete universal claims such as rolling 61 weeks / best 12 results.

## Architecture and determinism (non-negotiable)

- Use a deterministic Python modular monolith, not microservices.
- Keep players, tournaments, matches, rankings/statistics, health, history, packages, and Admin operations separated by clear domain/application boundaries.
- Keep domain logic pure/testable and isolate I/O in infrastructure. The UI calls application/API commands and contains no hidden simulation authority.
- Reproducibility target: `(world_state snapshot + historically effective configuration/package snapshots + RNG seed hierarchy + command) => identical result`.
- Use injected RNG only; no ambient randomness. Preserve explicit seed hierarchy and idempotent commands where feasible.
- History, snapshots, provenance, and audit are product data, not optional logs. Never recompute old history from current defaults.
- AI may explain, summarize, analyze, and suggest; it never decides authoritative outcomes or replaces rules.

## Competition and data rules

- Keep editable world/competition content in validated config/data, not hard-coded logic.
- Support qualification/main draws, seeds, byes, wild cards, Lucky Losers, withdrawals, walkovers, and retirements when the relevant slice is touched.
- Official Run match default is BO5, games to 11, win by 2, unless narrower stored configuration overrides it.
- Do not silently decide areas the constitution labels open, provisional, deferred, or later.

## Testing expectations

- Every logic change includes deterministic tests for touched logic: replay behavior, application/API contract, and snapshot integrity as applicable.
- Add regression tests for edge tournament states when those states are touched.
- Contract/component tests may mock an API boundary and must be described as such. Call a test “integration” only when it exercises the real production service/API/persistence stack.
- Shared built-in FAX sources are read-only test inputs. Mutation tests must use isolated disposable copies; fixture identity/version must not be stored in `config_version`.
- Reject realism changes that reduce determinism, replayability, or observability.

## Admin safety and build discipline

- Manual overrides are explicit validated commands with audit logging; never silently mutate authoritative state.
- Preserve ranking/history continuity and provide a rollback/rerun path or document the current limitation.
- Deliver vertical slices, stabilize foundations before realism expansion, and avoid UI-driven shortcuts or speculative mechanics.
- Each PR/task reports changed files and rationale, tests/checks, assumptions/constraints, follow-ups/open decisions, and preservation of canonical non-negotiables.
