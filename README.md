# Squash Engine

Squash Engine is a deterministic, data-driven manager and simulator of the fictional men's professional **FAX squash world**. It is intended to generate and evolve countries, players, tournaments, rankings, careers, matches, public history, and alternative timelines across independent saved Runs.

The repository is a beta in migration. The product model below is canonical target behavior, but individual capabilities may still be partial, transitional, or not implemented yet.

## Product model

- **Viewer** is a historically faithful, read-only environment for fictional public websites; the primary current site is **MSA Squash**.
- **Admin** creates, edits, validates, simulates, reconstructs, and audits data. **Global Admin** manages Runs and source Packages; **Run Admin** operates one Run and one active Admin branch in a selected time context.
- A **Run** is an independent saved world spanning exactly 50 seasons, `2000/01–2049/50`. Every season contains exactly 61 Season Weeks.
- Branches are equal alternative timelines within a Run. There is no privileged Main or Official branch. Each Run has exactly one **Viewer Branch**, which only selects the timeline displayed by Viewer.
- A Viewer Branch selection is first staged in Admin's Working Draft. Viewer remains on the saved selection until Save atomically creates a Saved Revision and audit event, activates the selection, and returns the editing Branch to a clean Working Draft.
- A Run may start completely empty. In the first pre-alpha, its unique displayed name is the only user-supplied creation field; `run_id`, the fixed time frame, one neutral initial Viewer Branch, its first Saved Revision, and a clean Working Draft are created atomically.
- Saved Revision history exposes a Branch's complete validated lineage, including shared pre-fork revisions, so a historical revision can be inspected and used by the existing branch-creation workflow without reading internal persistence identifiers.
- Packages are optional one-time content sources. Applied content becomes an independent, versioned Run snapshot; source identity/version remains provenance, not a live link.

## Simulation model

The target simulation is chronological and historically safe rather than a collection of unrelated buttons.

- Week changes are handled by an explicit **Week Transition**; the season boundary uses a special **Season Transition**.
- A week contains a variable chronological sequence of **Simulation Slots**. Events in one slot are simultaneous and read from the same pre-slot snapshot.
- The first-version match engine is **rally-by-rally**, not shot-by-shot. A rally has hidden control/pressure phases, individual physical load, explicit sporting/officiating outcomes, and compact authoritative logging.
- Player state includes long-term attributes plus changing form, fatigue, health, physical stamina state, mental match state direction and decision state. The current post-v42 V1 direction keeps the attribute model deliberately lighter: three physical stamina bars/dimensions should derive from underlying attributes/state rather than become three independent standalone trainable attributes; exact derivation and mental-bar mechanics remain open.
- **Match Reconstruction** is a first-version Admin workflow: known facts become constraints, multiple candidate histories may be generated and inspected, and only an explicitly selected candidate becomes authoritative history.
- Long-running work belongs in the Task Center/job model with visible state and safe recovery boundaries.

## Historical truth, events and attention

Squash Engine keeps several concepts deliberately separate:

- **World Event Log** — authoritative facts/events of a branch timeline,
- **Audit Log** — changes to data and their provenance,
- **Task Center** — running/completed operations,
- **Notification Center** — things that need Admin attention.

Viewer never exposes internal technical alerts or future-only information. Public MSA news/messages are derived from then-public World Events rather than becoming a second source of truth.

## Engine foundations

- Python deterministic modular monolith with a FastAPI application boundary.
- React + TypeScript + Vite client; simulation authority remains in the engine/API, never in Viewer or hidden client logic.
- SQLite/SQLAlchemy persistence with historical snapshots, provenance, and auditable Admin changes.
- Config/data-driven world and competition content with validation.
- Injected, hierarchical randomness and replayable commands; AI may explain or suggest but never decides authoritative sporting outcomes.
- Official Run individual-match default: BO5, games to 11, win by 2, unless narrower stored configuration overrides it.
- Historically versioned ranking policies and snapshots. Ranking formulae are configuration/history, not globally hard-coded constants.
- Operation-scoped validation: unrelated incomplete data should not block an otherwise valid operation.

## Documentation authority

Use this order when documentation conflicts:

1. explicit newer product decisions,
2. **Squash Engine Master Vision v54** and later audited revisions,
3. [`PROJECT_CONSTITUTION_TECHNICAL_PLAN.md`](PROJECT_CONSTITUTION_TECHNICAL_PLAN.md), including newer post-v42 decisions recorded there,
4. subordinate migration guidance such as [`docs/ENGINE_UX_SPEC.md`](docs/ENGINE_UX_SPEC.md),
5. older documents, handoffs, and existing beta behavior as historical or implementation evidence only.

`PROJECT_CONSTITUTION_TECHNICAL_PLAN.md` is the active shorter repository constitution governed by Master Vision v54. It may lag Master detail but intentionally preserves still-valid earlier canon. `Beta_Engine.docx` and documents that describe earlier phase-specific designs are non-authoritative background unless the current constitution explicitly reconfirms them. See [`ROADMAP.md`](ROADMAP.md) for the current milestone sequence.

Decision status matters: **decided**, **provisional**, **target**, **open**, **deferred**, and **later** must not be silently collapsed into one level of certainty.

## Development

Backend tests use Pytest; frontend tests use Vitest. Fast CI runs a broad smoke subset and the separate full-suite workflow is the complete validation safety net. Shared FAX contract/component fixtures are deliberately not called real integration tests; see [`docs/testing/fax-reference-strategy.md`](docs/testing/fax-reference-strategy.md).
