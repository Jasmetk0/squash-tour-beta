# Beta_Engine Roadmap

This roadmap is a milestone summary. Detailed current-vs-target architecture and workflow planning lives in `docs/ENGINE_UX_SPEC.md`.

## Phase 0 — Documentation alignment (current task)
- Align README/ROADMAP/spec docs with the planned FAX/MSA long-term UX and architecture direction.
- Explicitly separate: current implementation, planned target, and future phases.
- No backend/frontend/API/database behavior changes in this phase.

## Phase 1 — Navigation / UX shell cleanup
- Consolidate top-level Admin IA toward: World, Players, Tour & Seasons, Runs, Simulate, Diagnostics.
- Keep existing routes operational; add transitional labels/badges for placeholder/advanced areas.

## Phase 2 — World cleanup
- World hub focuses on Countries + Talent Preview.
- Fold Country Momentum into country detail development curves (future direction).
- Plan country detail route and move duplicate/copy actions into detail-level controls.

## Phase 3 — Talent Preview redesign
- Expected Mode first-class framing (forecast, not concrete generation).
- Main aggregates: Elite Talents, Tour Talents, Pro Depth; advanced tier breakdown optional.

## Phase 4 — Player module restructure
- Decompose Players into Player Database, Talent Intake, Custom Players, Locks & Overrides, Player Audit, Player Detail.
- Add explicit seasonal Talent Intake workflow/statuses without overclaiming detailed progression systems.

## Phase 5 — Tour & Seasons architecture
- Consolidate categories/tournaments/templates/seasons into one workflow.
- Strengthen Season Registry, calendar editor, compare/apply flows, and validation UX.

## Phase 6 — Tournament lifecycle + simulation controls
- Standardize tournament lifecycle statuses and allowed actions by state.
- Build top-level simulation launcher (match/round/tournament/week/season/full timeline) and downstream invalidation UX.

## Phase 7 — Narrative locks
- Introduce lock model (soft/hard/winner/round/path/match constraints) with conflict checking and auditability.

## Phase 8 — Diagnostics control center
- Build cross-module diagnostics: world balance, calendar validation, run health, invalidated data, narrative locks, warnings/audit.

## Phase 9 — Future realism updates
- Player identity and realism expansions (name pools/distributions, flags, physical profile, attributes, progression depth).

## Guardrails
- Preserve determinism, replayability, and auditability.
- Keep world/tour content data-driven.
- Maintain Admin vs Viewer conceptual separation.
- Do not claim planned features as implemented before delivery.
