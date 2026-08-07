# Squash Engine

Squash Engine is a deterministic, data-driven manager and simulator of the fictional men’s professional **FAX squash world**. It is intended to generate and evolve countries, players, tournaments, rankings, careers, and decades of history across independent saved Runs and alternative branch timelines.

## Product model

- **Viewer** is a historically faithful, read-only environment for fictional public websites; the primary current site is **MSA Squash**.
- **Admin** creates, edits, validates, simulates, and audits data. **Global Admin** manages Runs and source Packages; **Run Admin** operates one Run and one active Admin branch.
- A **Run** is an independent saved world spanning exactly 50 seasons, `2000/01–2049/50`. Every season contains exactly 61 Season Weeks.
- Branches are equal alternative timelines within a Run. There is no privileged Main or Official branch. Each Run has exactly one **Viewer Branch**, which only selects the timeline displayed by Viewer.
- Every Run receives independent, versioned snapshots of one World Package and one Category Package at creation. Source Package identity/version is retained as provenance, not as a live link.

The repository is a beta in migration: the target model above is canonical, but not every capability or legacy technical name has been migrated yet.

## Engine foundations

- Python deterministic modular monolith with a FastAPI application boundary.
- React + TypeScript + Vite client; simulation authority remains in the engine/API, never in Viewer or hidden client logic.
- SQLite/SQLAlchemy persistence with historical snapshots, provenance, and auditable Admin changes.
- Config/data-driven world and competition content with validation.
- Injected, hierarchical randomness and replayable commands; AI may explain or suggest but never decides authoritative sporting outcomes.
- Professional set-by-set matches (default Official Run format: BO5, games to 11, win by 2) and explicit abnormal outcomes.
- Historically versioned ranking policies and snapshots. Ranking formulae are configuration/history, not a globally hard-coded “best N” rule.

## Documentation authority

Use this order when documentation conflicts:

1. explicit newer product decisions,
2. the current Master Vision and its synchronized repository constitution,
3. [`PROJECT_CONSTITUTION_TECHNICAL_PLAN.md`](PROJECT_CONSTITUTION_TECHNICAL_PLAN.md),
4. subordinate migration guidance such as [`docs/ENGINE_UX_SPEC.md`](docs/ENGINE_UX_SPEC.md),
5. older documents, handoffs, and existing beta behavior as historical or implementation evidence only.

`PROJECT_CONSTITUTION_TECHNICAL_PLAN.md` is the active repository constitution synchronized from Master Vision v31. `Beta_Engine.docx` and documents that describe earlier phase-specific designs are non-authoritative background unless the current constitution explicitly reconfirms them. See [`ROADMAP.md`](ROADMAP.md) for the current milestone sequence.

## Development

Backend tests use Pytest; frontend tests use Vitest. Fast CI runs a broad smoke subset and the separate full-suite workflow is the complete validation safety net. Shared FAX contract/component fixtures are deliberately not called real integration tests; see [`docs/testing/fax-reference-strategy.md`](docs/testing/fax-reference-strategy.md).
