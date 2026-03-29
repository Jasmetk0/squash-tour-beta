# Beta_Engine

Beta_Engine is a deterministic, data-driven simulator of a **fictional men’s professional squash ecosystem**. It models World Tour + Elite Tour seasons with qualification/main draws, set-by-set matches, rankings, race standings, career progression, and historical archives.

## What this project is
- A modular simulation engine for multi-season professional tour careers.
- A configurable sandbox for tuning calendar structure, tournament templates, points, and balance.
- A commissioner-operable world with auditable manual interventions.

## What the MVP includes
- Country-driven talent generation pipeline.
- Editable World Tour + Elite Tour calendar.
- Entry generation, qualification draw + main draw flow.
- Set-by-set match simulation (11, win by 2) with core form/fatigue/upset factors.
- Official ranking: rolling 61 weeks, best 12 results.
- Seasonal Race standings.
- Simulation commands up to full-season runs.
- Weekly snapshots + basic historical archives.
- Minimal web UI for simulation control and key read views.

## Chosen tech stack
- **Backend:** Python 3.12, FastAPI, Pydantic
- **Domain architecture:** deterministic modular monolith
- **Persistence:** SQLite (WAL), SQLAlchemy
- **Config:** YAML + JSON Schema validation
- **Frontend:** React + TypeScript + Vite (+ TanStack Query, Tailwind planned)
- **Quality/tooling:** Pytest, Ruff, Black, mypy, pre-commit

## Important constraints
- Determinism is mandatory: same state + config + seed + command => same result.
- World content is config/data-driven; avoid hardcoded tour content.
- AI is assistant-only (explanations/analysis), not outcome authority.
