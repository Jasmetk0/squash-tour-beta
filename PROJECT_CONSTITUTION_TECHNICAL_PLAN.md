# Beta_Engine — Practical Technical Plan (from `Beta_Engine.docx`)

## 1) Architecture Summary

### 1.1 Core principles translated to engineering constraints
- **Determinism first:** every simulation run must be reproducible from `(world_state_snapshot + config version + RNG seed + command)`.
- **Modularity:** split bounded contexts: `players`, `tournaments`, `match_engine`, `ranking`, `race`, `injuries`, `history`, `commissioner`.
- **Data-first world:** tournaments/calendar/countries/points/rules live in editable config tables/files, not hardcoded logic.
- **Historical memory:** snapshots and append-only history are first-class outputs, not logging afterthoughts.
- **Commissioner overrideability:** manual edits and admin interventions are explicit audited operations.
- **AI as assistant only:** AI can explain/recommend, never authoritatively decide match outcomes.

### 1.2 Recommended high-level architecture
- **Domain core (pure Python):** deterministic simulation services and rules engine.
- **Application layer:** orchestrates simulation modes (`next_match`, `next_round`, `next_tournament`, `next_week`, `full_season`).
- **Persistence layer (SQLite):** current world state + event/history tables + snapshots.
- **Config layer (YAML/JSON):** country model, calendar templates, draw templates, point schemas, tuning constants.
- **API layer (FastAPI):** exposes read models and command endpoints.
- **Web UI (React + TypeScript):** commissioner/admin + dashboards over API.
- **CLI:** thin adapter over the same application services.

---

## 2) Best Architecture by Area

### 2.1 Backend simulation engine
**Pattern:** domain-driven modular monolith (not microservices).

**Key engine components:**
- `SimulationKernel`: owns RNG seeding, tick progression, transaction boundaries.
- `CalendarPlanner`: resolves weekly playable events and player entry eligibility.
- `EntryEngine`: generates entry lists from ranking/rules/status.
- `DrawEngine`: creates qualification + main draws from draw templates.
- `MatchEngine`: set-by-set simulation (11, win-by-2), supporting retirements/walkovers.
- `TournamentEngine`: advances bracket round-by-round.
- `RankingEngine`: rolling 61 weeks / best 12.
- `RaceEngine`: seasonal standings for World Tour Finals qualification.
- `CareerEngine`: development, progression, scheduling personality shifts.
- `HealthEngine`: fresh/managed/worn/compromised states + injury impacts.
- `HistoryEngine`: snapshots and archives.

**Determinism approach:**
- Seed hierarchy: `global_seed -> season_seed -> week_seed -> match_seed`.
- All random calls via injected RNG service (no direct `random` usage).
- Idempotent command handlers where possible.

### 2.2 Persistence / database
**Primary DB:** SQLite (WAL mode).

**Data model style:**
- Normalized OLTP core tables for current state (`players`, `events`, `entries`, `matches`, `rankings`).
- Append-only event/history tables (`match_results`, `ranking_snapshots`, `season_archives`, `player_history`, `nation_history`).
- Audit table for commissioner actions (`admin_actions`).

**Snapshot strategy:**
- Weekly snapshot materialization: ranking, race, player status summary, nation aggregates.
- Season-end archives for quick historical queries.

**Migrations:** Alembic (or lightweight SQL migration runner if preferred simplicity).

### 2.3 Config / data layer
**Format:** YAML for readability + JSON Schema validation.

**Config domains:**
- `countries.yaml` (population, squash popularity, infrastructure, pipeline, elite system, legacy strength, travel affinity)
- `calendar/*.yaml` (season templates and weekly slots)
- `tournament_templates/*.yaml` (draw sizes, seeds, LL rules, byes, points)
- `points/*.yaml` (category-based point distributions)
- `balance/*.yaml` (injury probabilities, fatigue/travel coefficients, upset variance)

**Config lifecycle:**
- Version each config bundle (`config_version`).
- Save config fingerprint with simulation snapshots.

### 2.4 API
**Style:** command-query separation (single service).

**Endpoint groups:**
- `POST /sim/*`: run simulation commands.
- `GET /world/*`: calendar, players, events, matches, rankings, race.
- `GET /history/*`: snapshots, archives, records.
- `POST /commissioner/*`: controlled overrides with audit logging.
- `POST /config/validate`: schema and business-rule checks.

**Operational notes:**
- Long-running simulation steps can be queued as background tasks.
- Return simulation job IDs for progressive UI updates.

### 2.5 Web UI
**Stack:** React + TypeScript + Vite + TanStack Query + Tailwind.

**UI areas:**
- **Simulation Control:** sim buttons by granularity, seed controls, run logs.
- **Tour Center:** weekly calendar, active tournaments, draw views.
- **Player Hub:** profile, attributes, health, form, career timeline.
- **Rankings & Race:** current + historical charts.
- **Nation Dashboard:** top-N strength metrics and trend lines.
- **Commissioner Console:** edit players/events/draws, force outcomes, rerun segments.

---

## 3) Milestone Plan

### MVP
- Country database + player generation pipeline.
- World Tour + Elite Tour editable calendar.
- Entry list generation, qualification + main draw creation.
- Set-by-set match simulation with basic fatigue/form/upset factors.
- Official ranking (61 weeks / best 12) + Race.
- Full season simulation commands.
- Weekly snapshots and basic archive tables.
- Minimal web UI for simulation controls + key views.

### V1.1
- Deeper injury system with recurrence/comeback quality.
- Stronger travel burden integration into scheduling and performance.
- Richer archetypes and play-style matchup effects.
- Full World Tour Finals format (8 players, groups + playoffs).
- Expanded nation dashboards and legacy records.
- More powerful commissioner operations and rollback/rerun support.

### V2
- Embedded AI assistant for explanations/recaps/admin guidance.
- Natural-language commissioner commands mapped to deterministic backend actions.
- Advanced analytics and balancing assistant.
- Narrative outputs (season previews, recaps, storylines) sourced from deterministic data.

---

## 4) MVP: Exact Modules, Files, Responsibilities

```text
beta_engine/
  pyproject.toml
  README.md
  .env.example
  migrations/
    versions/
  config/
    countries.yaml
    calendar/world_tour_2027.yaml
    calendar/elite_tour_2027.yaml
    tournament_templates/world_*.yaml
    tournament_templates/elite_*.yaml
    points/world_points.yaml
    points/elite_points.yaml
    balance/defaults.yaml
    schemas/*.json

  src/
    beta_engine/
      __init__.py
      main.py                         # FastAPI app bootstrap
      cli.py                          # CLI entrypoint for sim commands

      core/
        rng.py                        # deterministic RNG wrappers + seed derivation
        clock.py                      # week/season progression utilities
        types.py                      # shared enums/value objects
        errors.py

      domain/
        players/
          models.py                   # player aggregate + attrs
          generation.py               # player generation from country model
          progression.py              # base career progression logic
        countries/
          models.py
          service.py                  # country impact on talent generation
        tournaments/
          models.py
          templates.py                # template loaders/validators
          entry_engine.py             # entry list rules
          draw_engine.py              # qualification/main draw generation
          tournament_engine.py        # round advancement orchestration
        matches/
          models.py
          match_engine.py             # set-by-set simulation
        rankings/
          ranking_engine.py           # 61-week / best-12 logic
          race_engine.py              # season race logic
        health/
          health_engine.py            # freshness and basic injury states
        history/
          snapshot_engine.py          # weekly snapshots + season archive writes

      application/
        commands.py                   # command DTOs (sim next week, full season...)
        handlers.py                   # transactional command handlers
        services.py                   # orchestration façade for CLI/API

      infrastructure/
        db/
          sqlite.py                   # DB connection/session setup
          models.py                   # SQLAlchemy models
          repositories.py             # persistence adapters
          migrations.py               # migration runner hooks
        config/
          loader.py                   # YAML loading + schema validation
          validators.py               # business-rule validators
        logging/
          audit.py                    # commissioner/action audit logging

      api/
        routers/
          sim.py                      # simulation command endpoints
          world.py                    # players/calendar/events/rankings
          history.py                  # snapshots/archive endpoints
          commissioner.py             # manual overrides (MVP-limited)
        schemas/
          requests.py
          responses.py
        deps.py

      ui/                             # if monorepo, otherwise separate /web
        (placeholder for web app)

  web/
    package.json
    src/
      main.tsx
      app/routes.tsx
      features/sim-control/*
      features/calendar/*
      features/tournaments/*
      features/rankings/*
      features/players/*
      features/history/*
      features/commissioner/*
      shared/api/client.ts
      shared/components/*
```

### MVP responsibility map
- **`domain/*`**: pure business logic, deterministic and testable.
- **`application/*`**: use-case orchestration + command handling.
- **`infrastructure/*`**: I/O and persistence.
- **`api/*`**: transport adapters.
- **`web/*`**: operator-facing UI.
- **`config/*`**: editable world definition.

---

## 5) Beginner-Friendly Stack & Codex-Centric Workflow

### 5.1 Recommended stack
- **Backend:** Python 3.12, FastAPI, Pydantic, SQLAlchemy, SQLite.
- **Config:** YAML + JSON Schema.
- **Frontend:** React + TypeScript + Vite.
- **Testing:** Pytest (backend), Vitest/Playwright later (frontend).
- **Tooling:** Ruff + Black + mypy (light strictness initially), pre-commit.

### 5.2 Workflow for a beginner managing via Codex
1. Keep a **single source-of-truth docs folder** (`/docs/constitution`, `/docs/decisions`, `/docs/roadmap`).
2. Use **small issue prompts**: one module, one acceptance checklist.
3. Require Codex to always output:
   - changed files,
   - tests run,
   - assumptions,
   - follow-up tasks.
4. Enforce a **definition of done** per task:
   - deterministic behavior validated,
   - API contract documented,
   - snapshot integrity preserved,
   - no hardcoded world content.
5. Build by vertical slices:
   - first end-to-end `sim next week`, then deepen realism.
6. Freeze configs with version tags before long simulations.

### 5.3 Suggested delivery order (first 6 slices)
1. Core project skeleton + deterministic RNG + DB setup.
2. Country config + player generation.
3. Calendar + tournament templates + entry generation.
4. Draw generation + match engine.
5. Ranking/Race + weekly snapshots.
6. FastAPI + minimal UI controls.

---

## 6) Main Risks
- **Complexity creep:** too many realism mechanics before stable core.
- **Determinism regressions:** accidental non-seeded randomness.
- **Config inconsistency:** invalid templates causing broken seasons.
- **History bloat/performance:** large archives without query strategy.
- **Commissioner side-effects:** manual edits can corrupt ranking continuity unless audited and validated.
- **UI-driven architecture drift:** forcing backend compromises to satisfy early UI shortcuts.

## 7) Open Questions to Decide Later
- Exact point tables by category and how often categories can change.
- Precise draw template catalog for both tours.
- Injury probability model calibration targets.
- Travel burden formula and region clustering definitions.
- Retirement/aging and new talent influx rates.
- Tie-break and edge-case ranking rules (e.g., equal points ordering).
- World Tour Finals qualification tie-breakers and reserve logic.
- Snapshot retention policy and archival compaction strategy.
- Commissioner rollback semantics (event-sourced undo vs snapshot rewind).
- Whether UI lives in monorepo or separate repo from day one.
