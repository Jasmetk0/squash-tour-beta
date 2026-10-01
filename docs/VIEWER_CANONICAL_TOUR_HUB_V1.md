# Viewer Canonical Tour Hub v1

## Purpose

Top-level Viewer Tour pages now use Product Run-scoped canonical Saved-Revision/publication authorities.

Migrated surfaces:

- Season Hub;
- All Tournaments;
- Current Week.

## Canonical sources

- Saved Calendar via `viewer_run_calendar.v1`;
- Tournament History via `viewer_tournament_history.v1`;
- Finals Race History for Season Hub Finals publication metadata.

These pages no longer read legacy SimulationRun run state, event lists, run status summaries or legacy Finals summaries.

## Boundary

Season Hub progress is expressed only from canonical publication counts and Saved Calendar state. No legacy mutable progress state is reintroduced.

Current Week filters the Saved Calendar by the Viewer-selected season/week.

No tournament result detail, ranking or Finals result authority is inferred beyond the existing canonical read models.
