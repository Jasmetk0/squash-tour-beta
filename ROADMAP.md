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
- Foundation added: Season Week + Year Week calendar model with deterministic 61-week mapping.
- Official FAX mapping: one calendar year has 61 Year Weeks, each season has 61 Season Weeks, and Season Week 1 starts at Year Week 37 by default. Season Week and Year Week are separate concepts: Season Week is simulation order; Year Week is calendar position within the 61-week calendar year.
- Foundation added: first-season calendar builder can preview and persist planned events from editable tournament templates.
- Foundation added: Admin Seasons can preview and persist deterministic entry lists for persisted season calendar events from persisted active season players, including main draw acceptances, qualification acceptances, alternates, validation issues, and provenance fingerprints.
- Foundation added: Admin Seasons can preview and persist deterministic qualification/main draw packages from persisted event entry lists, including seeds, BYEs, qualifier placeholders, validation issues, and provenance fingerprints.
- Foundation added: Admin Seasons can preview/persist deterministic match packages from persisted draw packages and simulate selected or next pending matches with file-backed result storage and provenance fingerprints.
- Foundation added: conservative persisted tournament progression commands can process BYEs, refresh/advance completed propagation, promote completed qualification winners into main-draw qualifier placeholders, and simulate explicit rounds/draws from the match package.
- Foundation added: event result extraction can preview/persist completed, incomplete, or blocked tournament outcome summaries from persisted match packages, including champion/finalist/top finishers/qualification winners/player round reached and provenance fingerprints.
- Foundation added: event-level ranking/race point awards can now be previewed, persisted, and explicitly applied to active season players from persisted event result packages, with duplicate-application prevention and provenance fingerprints.
- Foundation added: current Ranking/Race read tables can now be derived deterministically from active season player ranking_points/race_points in Admin Seasons and Viewer MSA Rankings.
- Foundation added: event-by-event player point breakdowns can now be read from persisted point award packages in Admin Seasons and Viewer MSA Rankings, including applied totals, event sources, fingerprints, and consistency checks against active season players.
- Foundation added: weekly ranking/race snapshot foundation can preview and persist season-week ranking publications from current active season player totals, then expose read-only Admin/Viewer snapshot retrieval with simple previous-week movement.
- Foundation added: Admin Seasons can inspect a derived, read-only Event Lifecycle status for each persisted calendar event from existing artifact registries, including next recommended action, blockers, point application, and week snapshot publication.
- Foundation added: Admin Seasons can now preview or run an explicit one-event orchestration command from lifecycle state, coordinating existing backend services for entries, draws, matches/progression, results, point awards, optional point application, and optional week snapshot publication.
- Remaining limitations: simulate-week command is not implemented, simulate-season command is not implemented, rolling 61-week ranking is not implemented, best-N ranking selection is not implemented, progression/regression is not implemented, annual intake/retirement is not implemented, orchestration still uses file-backed artifacts, automatic season-week simulation/publication is not implemented, cross-season movement is not implemented, ranking history analytics such as weeks at #1 and career high are not implemented, full Viewer player profiles are not implemented, Viewer player profile links may still be placeholders, prize money is not awarded, reapply/revert workflow is not implemented, withdrawals/lucky losers are not connected, advanced schedule-of-play is not implemented, Viewer tournament pages are not complete, and final database-backed tournament history persistence is not implemented.

## Phase 5 — Player Generation Control
- Add initial player pool generation for the first season.
- Add preview/edit/lock/regenerate workflows.
- Support regeneration by country, region, and full unlocked pool.
- Add birth_year and birth_year_week design support.
- Foundation added: Admin Players can preview/persist a deterministic 2000/2001 initial pool, inspect generated attributes/traits, and lock/regenerate unlocked players.
- Foundation added: custom player creation, safe selected-player editing, and compact audit metadata for create/update/lock/unlock/generate/regenerate initial-pool operations.
- Foundation added: curated initial pools can be previewed and persisted into first-season active-player records for 2000/2001 bootstrap, preserving IDs, manual provenance, lock provenance, source fingerprints, and zero starting ranking/race points.
- Remaining limitations: initial ranking seeding, tournament entry/draw flow connection to active players, progression/regression, retirement, Viewer player profile depth, and final database-backed historical career persistence are not implemented yet.

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
