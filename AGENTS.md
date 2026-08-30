# AGENTS.md — Squash Engine operating instructions

## Product and documentation authority

Build a deterministic, data-driven manager and simulator of the fictional men's professional FAX squash world.

When sources conflict, use this precedence:

1. explicit newer user/product decisions,
2. the latest audited **Squash Engine Master Vision** — currently v60 plus newer explicit decisions,
3. `PROJECT_CONSTITUTION_TECHNICAL_PLAN.md` (the active repository constitution, including newer decisions recorded there),
4. subordinate guidance such as `docs/ENGINE_UX_SPEC.md` and explicit current-version decision specs such as `docs/COUNTRY_ATTRIBUTES_V1.md`,
5. older documents, handoffs, and current beta behavior as history/implementation evidence only.

`Beta_Engine.docx` is non-authoritative background. `README.md` is an overview and `ROADMAP.md` is a milestone summary; neither may override the constitution. Mark assumptions and distinguish implemented behavior from target behavior.

Never collapse status labels. A `[DECIDED]` rule, `[PROVISIONAL]` direction, `[TARGET]` capability, `[OPEN]` question, `[DEFERRED]` item and `[LATER]` idea are not interchangeable. Never silently delete an older still-valid decided rule merely because a newer summary omits it.

## Current canonical product rules

- A Run is an independent saved world with exactly 50 seasons, `2000/01–2049/50`; every season has exactly 61 Season Weeks.
- Branches are equal alternative timelines inside a Run. Never introduce a privileged Main/Official branch concept.
- Every Run has exactly one **Viewer Branch**. It only selects the timeline shown by Viewer; legacy `official_branch` technical names are migration debt, not product terminology.
- Selecting a different Viewer Branch is an uncommitted Admin change in the active Branch's Working Draft. Viewer stays on the current saved selection until a confirmed Save atomically creates the new immutable Saved Revision and audit event, activates the selected Viewer Branch, and leaves a clean Working Draft based on the new revision.
- A Run may be created completely empty. Its sole required user input in the first pre-alpha is a unique display name; the engine assigns `run_id`, creates its empty `2000/01–2049/50` time frame and keeps it in `Working`. Packages and sporting content are operation-scoped additions, not creation prerequisites.
- Creating that empty Run is itself its first successful save: the initial Viewer Branch points to one immutable, parentless Saved Revision and starts with a clean Working Draft based on it. This revision is recoverable history, not a checkpoint or simulation state.
- Saved Revision history reads return the complete reachable lineage of the selected Branch, including shared pre-fork ancestry, and may expose a revision detail only when that revision is reachable through the supplied Run/Branch context. Reads are oldest-to-newest, fail closed on identity/hash/lineage corruption and never mutate Viewer, draft or revision state.
- The initial Branch is named `Timeline 1`. Each later ordinary Branch proposes the first unused exact `Timeline N` name within the Run; the user may replace that proposal before creation, and every stored Branch name remains unique within its Run.
- When a Package is applied to a Run, its selected content becomes an independent, versioned Run snapshot; provenance remains, but there is no live source link.
- Viewer is historically faithful and read-only. Admin is authoritative and has distinct Global Admin and Run Admin scopes.
- **Country Game Attributes V1:** authored country ratings are exactly `Squash Popularity`, `Squash Access`, `Development Quality`, `Competition Quality`, `Elite Support`, and `Squash Tradition`, each 1–5. Population/area/region/travel region/**timezone area**/court count are factual data, while Effective Squash Pool, Competitive Depth, Talent Discovery Rate, Professional Conversion Rate and current country strength are derived. Country ratings may affect sampling and development/conversion, but must not directly make innate/generational potential more likely by nationality or create national technical, mental, personality or style DNA. `style_dna` is deferred beyond V1. Travel Region and Timezone Area are distinct geography layers; the currently missing Timezone Area registry is implementation debt, not permission to collapse the concepts. See `docs/COUNTRY_ATTRIBUTES_V1.md`.
- Ranking policies and snapshots are historically versioned/configurable. The Official Run begins season `2000/01` with Best 15; each later season initially inherits the previous season's effective Best N but remains independently configurable.
- Week progression uses explicit **Week Transition**; season rollover uses **Season Transition**. A week contains a variable chronological sequence of **Simulation Slots**.
- Events in the same Simulation Slot are simultaneous and must read from the same pre-slot snapshot.
- The first-version Match Engine is rally-by-rally, not shot-by-shot, with explicit authoritative rally/time logging and three physical stamina dimensions/bars.
- **Current V1 direction:** those three physical stamina dimensions should derive from the lighter underlying attribute/state model rather than be hard-coded as three independent standalone trainable attributes; exact mapping remains open.
- **Current provisional direction:** one or more mental match-state bars/dimensions should exist; exact count/names/mechanics remain open.
- Each player has one current Form; it updates from played performance and regresses toward an individual long-term norm rather than resetting.
- `World Event Log`, `Audit Log`, `Task Center`, and `Notification Center` are separate concepts and must not be conflated.
- Public MSA news/messages derive from then-public World Events. Viewer must not expose technical alerts or future-only information.
- First-version **Match Reconstruction** treats manually supplied facts as constraints; candidates remain non-authoritative until the Admin explicitly selects one.

## Architecture and determinism — non-negotiable

- Use a deterministic Python modular monolith, not microservices.
- Keep players, tournaments, matches, rankings/statistics, health, history, packages, Admin operations, notifications and reconstruction separated by clear domain/application boundaries.
- Keep domain logic pure/testable and isolate I/O in infrastructure. The UI calls application/API commands and contains no hidden simulation authority.
- Reproducibility target: `(world_state snapshot + historically effective configuration/package snapshots + RNG seed hierarchy + command) => identical result`.
- Use injected RNG only; no ambient randomness. Preserve explicit seed hierarchy and idempotent commands where feasible.
- Events that are logically simultaneous must not become order-dependent merely because code executes them sequentially.
- History, snapshots, provenance, audit and authoritative logs are product data, not optional debug output. Never recompute old history from current defaults.
- AI may explain, summarize, analyze, and suggest; it never decides authoritative outcomes or replaces rules.

## Time, simulation and sporting rules

- Week Transition is not a normal Simulation Slot. It prepares the next week's valid initial state from information known through the end of the completed week.
- Weekly development must not use information from the newly opened or future week.
- Season Transition is the special Week 61 → Week 1 rollover. It activates new seasonal policy atomically and resets only explicitly season-scoped state.
- Support operation-scoped validation. Missing unrelated future data must not block an otherwise valid local operation.
- `Simulate Next Slot` resolves the nearest unresolved slot. `Simulate Next Match` may resolve one match inside that slot without changing the inputs of other simultaneous matches.
- Keep editable world/competition content in validated config/data, not hard-coded logic.
- Official Run individual-match default is BO5, games to 11, win by 2, unless narrower stored configuration overrides it.
- The first-version rally engine uses squash-appropriate serve influence and simplified interference semantics `No Let / Yes Let / Stroke`; referee-error/review depth is later scope.
- Do not silently decide areas the constitution labels open, provisional, deferred, or later.

## Historical knowledge and tournament publication

- A Tournament Edition may exist internally before it becomes public.
- `announcement_week` is historical data. Viewer and player AI may know an Edition only after the corresponding public World Event becomes effective.
- Avoid future leaks in Viewer, player AI, generated news, ranking views, odds and predictions.
- Tournament lifecycle/public stage should be derived from authoritative state/events rather than duplicated as an unrelated source of truth.

## Match Reconstruction safety

- Reconstruction constraints are facts, not hints to overwrite silently.
- Generated candidates are inspectable alternatives; they do not mutate history by existing.
- Full candidate detail is read-only until one candidate is explicitly chosen.
- Only the explicit commit/selection operation may install a reconstructed history, with validation and audit/provenance.
- Exact probability architecture, candidate-generation mathematics and retention remain open unless a later decision resolves them.

## Testing expectations

- Every logic change includes deterministic tests for touched logic: replay behavior, application/API contract, and snapshot integrity as applicable.
- Add regression tests for slot simultaneity/order independence when Simulation Slots are touched.
- Add transition-boundary tests when Week Transition or Season Transition is touched.
- Add no-future-leak tests when Viewer/public knowledge/announcement timing is touched.
- Add reconstruction non-mutation tests when Match Reconstruction is touched.
- Add regression tests for edge tournament and abnormal match states when those states are touched.
- Contract/component tests may mock an API boundary and must be described as such. Call a test “integration” only when it exercises the real production service/API/persistence stack.
- Shared built-in FAX sources are read-only test inputs. Mutation tests must use isolated disposable copies; fixture identity/version must not be stored in `config_version`.
- Reject realism changes that reduce determinism, replayability or observability.

## Admin safety and build discipline

- Manual overrides are explicit validated commands with audit logging; never silently mutate authoritative state.
- Blue informational state does not block, orange warns without blocking, and red blocks/stops only the affected operation or branch.
- Preserve ranking/history continuity and provide a rollback/rerun path or document the current limitation.
- Deliver vertical slices, stabilize foundations before realism expansion, and avoid UI-driven shortcuts or speculative mechanics.
- Each PR/task reports changed files and rationale, tests/checks, assumptions/constraints, follow-ups/open decisions, and preservation of canonical non-negotiables.
