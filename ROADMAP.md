# Squash Engine roadmap

This is a milestone summary, not a second product constitution. [`SQUASH_ENGINE_MASTER_VISION.md`](SQUASH_ENGINE_MASTER_VISION.md) plus newer explicit decisions take precedence over `PROJECT_CONSTITUTION_TECHNICAL_PLAN.md`; `docs/ENGINE_UX_SPEC.md` provides subordinate migration guidance. Planned behavior must not be described as implemented unless verified in the repository.

## Implemented narrow tournament integration

The current narrow driver retains automatic compatibility adoption for one persisted
supported four-player Main Draw. For multiple supported events it requires an
immutable, fingerprinted Run/Branch/RankingWeek schedule explicitly adopted through
the Admin preview/confirm boundary; that payload alone maps exact match groups onto
ordered global Simulation Slots. Each event closes independently and exactly once
through the existing completion, award and `OwnedTournamentRankingSource` contracts.
Legacy `start_day`, list/event ordering and draw-round arithmetic are not substitutes. Explicit authoritative Admin routes expose
position, split Next Match and Next Slot without redirecting legacy simulation.
Independent same-slot groups now commit atomically and resume after failure, while
transition readiness reuses the authoritative match/effect sporting preflight.
General draws, Qualification, WC/LL, Entries, AI-authored/general scheduling, and health remain Gate 3 work.
The repeated-flow acceptance now proves three completed authoritative RankingWeeks
(Week 1 → Week 2 → Week 3 → Week 4), and a separate production-backed acceptance
repeats generalized eight-player/seven-match Main Draws across the same three-week
chain with explicit schedules, ranking transitions and historical replay.

The merged #743–#749 chain now owns Tournament Ranking Snapshot → canonical
Entry Field → immutable Draw Input → replayable Run-owned Qualification/Main Draw
Authority. The current bounded follow-up makes that Draw Authority the preferred
source of authoritative match topology: direct participants, feeder winners,
terminal identity, explicit BYE auto-advance and the single-Q promotion edge are
projected from the canonical bracket. Legacy MatchPackage remains only a temporary
execution/result payload and must bind one-to-one to canonical nodes. New frozen
tournament authority v5 includes the exact Draw Authority fingerprint. Multi-Q
sections, dynamic qualifier-vs-BYE auto-advance, WC/LL and post-draw repair still
fail closed rather than borrowing legacy DrawPackage policy.

Qualification promotion plus unambiguous one-player BYEs now execute through the
authoritative tournament/ranking bridge. Wild-card provenance from #738 remains a
useful primitive. The #739/#740 pre-/post-draw replacement shortcut producers are
now fail-closed after the post-merge canon audit; already persisted packages remain
historically readable. Canonical replacement work must proceed through Tournament
Ranking Snapshot field rebalance, Qualification/Main Draw repair phases, Lucky Loser
priority and the per-player first-real-match replacement cutoff.

## Active pre-alpha dependency path (audit after #728 plus current driver slice)

This sequence is a technical plan, not a new product-rule registry. Re-evaluate
it after each merge using `CURRENT_STATE.md`. Existing detailed targets below
remain valid; their numbering is not a mandate to implement them in that order.

| Gate | Coherent outcome | Evidence required to advance |
|---|---|---|
| 0 — synchronize | One canonical Master, clear authority, verified state and next Codex task | Documentation preservation/link checks; no invented product decisions |
| 1 — source bridge (implemented slice) | Supported real main-draw results/awards become owned Run/Branch sources, feed Official candidate and survive Save/Restore | Real producer + API/SQLite covers preview, rollback, retry, reopen and recovery; broader source types remain guarded |
| 2 — one true week boundary (implemented expanded slice) | One SQLite owner resolves an explicit owned completed-tournament manifest, develops canonical sporting state, performs provisional between-week updates, derives lifecycle roster, then atomically publishes/advances/audits | Missing/empty sporting evidence fails closed; match-derived state beyond counts and health remain boundaries; matching Run prospects fail closed |
| 3 — repeated sporting flow | Entries/draw/match/close/ranking consumers use the same scoped timeline across weeks | Multiple weeks without manual DB repair; slot simultaneity, expiry, corrections, historical reads and recovery |
| 4 — season boundary | Outgoing Season Closing + summary/marker; incoming policy + Week 1; final season terminates without season 51 | Whole season and rollover; outgoing/incoming policy separation, final Run edge, save/reload/replay |
| 5 — pre-alpha acceptance | Both Master 31.3 flows, including required minimum Reconstruction/player/AI scope | Official season -> next season and empty Run -> two manual players -> standalone match, repeatedly without history damage |

Full-Run/multi-season stress checks follow progressively; do not confuse a long
successful batch with empirically calibrated realism. Protected Ranking and other
required downstream rules enter where their consumers require them, not as an
unbounded ranking detour. Genuinely open product questions remain explicit gates.
Consider an integration checkpoint after 5–10 significant PRs or a major subsystem.

## 1. Canonical foundation and migration safety

- Keep independent Runs, equal branches and exactly one Viewer Branch per Run.
- Preserve 50 seasons (`2000/01–2049/50`) and exactly 61 Season Weeks per season.
- Preserve deterministic replay, historical snapshots, provenance, auditability and operation-scoped validation.
- Keep `World Event Log`, `Audit Log`, `Task Center` and `Notification Center` as separate concepts.
- Migrate legacy Main/Official branch terminology only with compatibility and persistence planning.
- Preserve still-valid earlier canon when synchronizing newer Master revisions; absence from a short summary is not evidence of supersession.

## 2. Application shell and Admin/Viewer scopes

- Complete neutral Squash Engine Home with global Runs and Packages.
- Keep Global Admin separate from Run Admin.
- Standardize Run/Branch/Time/Viewer-Admin controls and context-preserving switching.
- Continue Run Home as an overview with the fixed overall-Run and current-season progress indicators.
- Move execution-heavy actions into dedicated Simulation workflows.
- Do not silently finalize the still-provisional complete sidebar/navigation tree.

## 3. Packages, world and future planning

- Keep source World/Category Packages separate from independent Run snapshots.
- Continue country/population/talent/lifecycle work without hard-coded world content.
- Support efficient future-season planning through inherited plans rather than eagerly materializing every future Edition.
- Add Travel Regions/Timezone Areas only to the currently decided coarse level; precise travel/acclimatization mathematics remains later/open.

## 4. Chronological simulation foundation

- Implement explicit **Week Transition** between weeks.
- Include `Weekly Player Development Update` using only information known through the completed week.
- Model each week as a variable chronological sequence of **Simulation Slots**.
- Events in the same slot use one common pre-slot snapshot and must not become order-dependent.
- Support `Simulate Next Slot` and split `Simulate Next Match` semantics.
- Implement **Season Transition** as the Week 61 → Week 1 special boundary with atomic seasonal-policy activation, scoped resets and a lightweight Season Closure Marker.

## 5. Tournament lifecycle, public knowledge and entries

- Consolidate Tournament Series/Editions, calendars, qualification, draws and lifecycle validation.
- Derive Tournament Edition lifecycle/component state and public `Public Stage` from authoritative state.
- Persist historical `announcement_week`; Viewer and player AI may know an Edition only after the corresponding public World Event.
- Keep entry decisions within a slot on a shared snapshot and commit them transactionally.
- Preserve entry/application objects as historical state.
- Keep unresolved Entry Freeze/cut-off details open.
- **Implemented foundation:** Run simulation freezes persisted Entry/Draw/Match evidence as a versioned topology DAG and validates explicit global-slot coverage for complete binary Main Draws; production eight-player Main Draws repeat across three authoritative weeks while retaining the historical four-player reader. Indexed qualifier mappings and unambiguous one-player Qualification BYEs execute and ingest into ranking authority. Entry decisions for overlapping events are generated transactionally from one shared snapshot, but unresolved competing acceptances remain provisional and must fail closed before play until Final Commitment / Week Tournament Lock authority exists. WC and alternate-replacement provenance primitives exist, while canonical RWC, pre-draw field rebalance, draw repair phases, LL ordering and replacement cutoff remain Gate 3 work.

## 6. Match Engine v1

- Build matches **rally-by-rally**, not shot-by-shot.
- Implement the hidden multi-phase control/pressure process without prematurely freezing still-open probability mathematics.
- Keep three distinct **physical stamina match dimensions/bars** with capacity/current-state/recovery behavior.
- Follow the newer V1 direction that these three physical bars derive from the lighter underlying attribute/state model rather than becoming three independent standalone trainable attributes; exact derivation remains open.
- Add one or more mental match-state dimensions only as a provisional direction until count/names/mechanics are explicitly decided.
- Let player AI estimate opponent fatigue and vary effort; it must not read hidden Admin truth directly.
- Keep the implemented four-axis Active Gameplan V1 historically snapshotted and replayable; later replace its explicit legacy style/adaptability proxies with authored career profiles, Match Preparation and richer scouting inputs.
- Keep serve influence squash-appropriate and relatively weak.
- Keep the implemented simplified `No Let / Yes Let / Stroke`, ball-hit-player and short external-interruption resolver historically versioned; tune its provisional situation generator without reinterpreting stored matches. See `docs/RALLY_RULES_RESOLVER_V1.md`.
- Persist compact authoritative rally and timing data.
- Referee errors, detailed review, deliberate delay and detailed court-condition simulation remain later scope.

## 7. Player state and ranking policy

- Keep the decided pre-alpha 57-attribute `0..200` catalogue centralized and individually stored; its taxonomy remains revisable after pre-alpha.
- Implement one current **Form** per player, updated after played matches and regressing toward an individual long-term norm rather than resetting.
- Keep Form separate from long-term attributes and physical stamina state/capacity.
- Preserve v42 handling of W/O, DQ, RET and abnormal/no-contest cases.
- Official Run season `2000/01` starts with Best 15; later seasons initially inherit the previous season's effective Best N while remaining independently configurable.
- Preserve historical ranking-policy snapshots.
- **Implemented initial slice:** explicitly adopt the complete production initial pool and an explicit first-season policy into an independent Run/Branch snapshot; derive the initial ranking candidate server-side and preserve both through Save/reopen/restore. See `docs/INITIAL_WORLD_RANKING_INTEGRATION_V1.md`.
- The supported ordinary transition bootstraps Week 1 lifecycle and canonical sporting state from owned initial-world players, runs provisional historical development and between-week state, advances birthdays/retirement, and derives ranking identity server-side. Match-derived state/health remain open and prospect intake still fails closed. See `docs/AUTHORITATIVE_PLAYER_LIFECYCLE_WEEK_STATE_V1.md` and `docs/AUTHORITATIVE_PLAYER_SPORTING_WEEK_STATE_V1.md`.

## 8. Match Reconstruction v1

- Add Admin **Match Reconstruction** where manually supplied facts are hard constraints.
- Let Admin choose candidate count and inspect compact summaries plus complete read-only candidate detail.
- Candidate generation must not mutate authoritative history.
- Only an explicitly selected candidate may become history, with validation and provenance/audit.
- Keep candidate-generation probability architecture, session retention and exact compact-card design at their unresolved status.

## 9. Events, notifications and historical MSA content

- Implement branch-scoped **World Event Log** as the source for historical world facts and public knowledge.
- Keep Audit Log for data changes/provenance, Task Center for operations and Notification Center for Admin attention.
- Support system notifications and watchlists with consistent info/warning/critical semantics.
- Public MSA homepage messages/news must derive from then-public World Events and obey historical time filtering.
- Standalone News page, News Importance Score and detailed event taxonomy remain unresolved/provisional as specified.

## 10. Forecast and Future Locks — provisional track

- Forecast remains non-authoritative and must not mutate a Run merely by running.
- Preserve the strong direction toward reproducible Forecast Sessions, conditional analysis, sample reconstruction and explicit branch materialization.
- Preserve Future Locks as a strong direction with feasibility separate from natural probability and Admin-only provenance.
- Do not promote still-open sampling algorithms, UI, retention, conflict handling or lifecycle rules to canon.

## 11. Branches, history, records and Viewer

- Build branch map/timeline, versions, checkpoints and recoverable saves with shared pre-divergence history stored once.
- Preserve the Working Draft boundary for Viewer Branch changes: Viewer switches only through an atomic Save that also creates the Saved Revision and audit event.
- Expose the complete validated Saved Revision lineage and scoped revision detail as a read-only foundation for historical branching; recognize that guarded restore and paired recovery activity already exist; pagination, general comparison and complete sporting restore remain follow-ups (see CURRENT_STATE.md).
- Expand historically correct rankings, statistics, H2H and records from authoritative branch/week data.
- Rivalries exist as a product concept; detailed detection, group behavior, scoring and Viewer placement remain partially provisional.
- Tournament Prestige/Tournament Appeal must remain at their actual provisional strengths.

## Guardrails

- Viewer stays read-only; authoritative mutation, reconstruction commit and simulation stay in Admin/application commands.
- No branch is Main/Official; Viewer Branch is display selection only.
- Package snapshots are not live links to global source Packages.
- Do not claim target behavior as already implemented.
- Do not silently finalize open/provisional areas such as final navigation, Viewer reveal modes, Country Ranking, full seed contract, final Forecast architecture, complete Entry Freeze rules, Match Reconstruction probability details, exact stamina derivation or mental-bar mechanics.


### Run-owned MatchPackage projection follow-up

After #750, canonical Draw Authority owns match topology. The current follow-up also
removes the file-backed MatchPackage prerequisite for canonical events: the driver
builds a deterministic in-memory compatibility package from canonical Draw + Calendar
evidence and freezes that payload with tournament authority. Existing result/points
builders remain temporary adapters; canonical payloads explicitly bypass legacy
DrawPackage lookup.


### Run-owned Tournament Result authority follow-up

After #751, canonical tournaments no longer require file-backed MatchPackage
generation. The current follow-up removes the next legacy producer from the
canonical close path: champion/finalist, Qualification provenance, reached stages
and match-result references are built into immutable `TournamentResultAuthority`
directly from canonical Draw + authoritative match receipts. New owned ranking
sources persist that truth as v2. Legacy-shaped result DTOs remain only as temporary
inputs to the existing points/ranking adapter.
