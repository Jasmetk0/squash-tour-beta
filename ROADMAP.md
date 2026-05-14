# Beta_Engine Roadmap

## Phase 0 — Documentation & Startup Stability
- Align AGENTS.md, README.md, ROADMAP.md, and PROJECT_CONSTITUTION_TECHNICAL_PLAN.md.
- Keep simple local runners: run_backend.bat and run_frontend.bat.
- Ensure backend/frontend can start locally without manual command guessing.

## Phase 1 — App Mode Split
- Add clear Admin / Engine Mode and Viewer / MSA Website Mode separation.
- Add mode switch in UI.
- Admin Mode contains editor/simulation tools.
- Viewer Mode contains public-style browsing pages.

## Phase 2 — World Editor
- Improve country editor.
- Support country parameters for talent generation.
- Add court count and style DNA fields if not already present.
- Add design support for future country momentum / era modifiers.

## Phase 3 — Tournament Templates
- Improve tournament category/template editor.
- Support draw size, qualification size, seeds, wildcards, qualifier spots, lucky losers, points, prestige, duration.

## Phase 4 — Seasons & Calendar
- Implement or align season model around 61 Season Weeks.
- Add Year Week / calendar positioning.
- Support season templates and season-specific overrides.
- Detect overlaps and impossible calendars.

## Phase 5 — Player Generation Control
- Add initial player pool generation for the first season.
- Add preview/edit/lock/regenerate workflows.
- Support regeneration by country, region, and full unlocked pool.
- Add birth_year and birth_year_week design support.

## Phase 6 — End-of-Season Lifecycle
- Add annual 15-year-old talent intake.
- Add retirement decisions for players of any age.
- Improve aging, progression, regression, injuries, and recovery.
- Prepare next season baseline.

## Phase 7 — History Regeneration
- Detect edits to past seasons/world data.
- Mark future history as stale/invalid.
- Allow regeneration from a selected season/week forward.
- Preserve earlier valid history.

## Phase 8 — Bulk History Simulation
- Support simulation from season X to season Y.
- Support full FAX history simulation from 2000/2001 to 2039/2040.
- Add long-run realism diagnostics.

## Phase 9 — Viewer / MSA Website Depth
- Improve rankings, tournaments, players, countries, history, and records pages.
- Make Viewer Mode feel like a real professional squash association website.

## Guardrails
- Do not weaken determinism.
- Do not hardcode editable world content.
- Do not let UI dictate core simulation architecture.
- Do not use AI to decide sporting outcomes.
- Do not mix Admin Mode and Viewer Mode unnecessarily.
