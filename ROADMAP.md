# Squash Engine roadmap

This is a milestone summary, not a second product constitution. **Master Vision v42** plus newer explicit decisions recorded in `PROJECT_CONSTITUTION_TECHNICAL_PLAN.md` take precedence; `docs/ENGINE_UX_SPEC.md` provides subordinate migration guidance. Planned behavior must not be described as implemented unless verified in the repository.

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

## 6. Match Engine v1

- Build matches **rally-by-rally**, not shot-by-shot.
- Implement the hidden multi-phase control/pressure process without prematurely freezing still-open probability mathematics.
- Keep three distinct **physical stamina match dimensions/bars** with capacity/current-state/recovery behavior.
- Follow the newer V1 direction that these three physical bars derive from the lighter underlying attribute/state model rather than becoming three independent standalone trainable attributes; exact derivation remains open.
- Add one or more mental match-state dimensions only as a provisional direction until count/names/mechanics are explicitly decided.
- Let player AI estimate opponent fatigue and vary effort; it must not read hidden Admin truth directly.
- Keep serve influence squash-appropriate and relatively weak.
- Use simplified `No Let / Yes Let / Stroke` interference in v1.
- Persist compact authoritative rally and timing data.
- Referee errors, detailed review, deliberate delay and detailed court-condition simulation remain later scope.

## 7. Player state and ranking policy

- Keep the first-version attribute model intentionally lighter and extensible rather than prematurely freezing a final large attribute catalogue.
- Implement one current **Form** per player, updated after played matches and regressing toward an individual long-term norm rather than resetting.
- Keep Form separate from long-term attributes and physical stamina state/capacity.
- Preserve v42 handling of W/O, DQ, RET and abnormal/no-contest cases.
- Official Run season `2000/01` starts with Best 15; later seasons initially inherit the previous season's effective Best N while remaining independently configurable.
- Preserve historical ranking-policy snapshots.

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
- Expand historically correct rankings, statistics, H2H and records from authoritative branch/week data.
- Rivalries exist as a product concept; detailed detection, group behavior, scoring and Viewer placement remain partially provisional.
- Tournament Prestige/Tournament Appeal must remain at their actual provisional strengths.

## Guardrails

- Viewer stays read-only; authoritative mutation, reconstruction commit and simulation stay in Admin/application commands.
- No branch is Main/Official; Viewer Branch is display selection only.
- Package snapshots are not live links to global source Packages.
- Do not claim target behavior as already implemented.
- Do not silently finalize open/provisional areas such as final navigation, Viewer reveal modes, Country Ranking, full seed contract, final Forecast architecture, complete Entry Freeze rules, Match Reconstruction probability details, exact stamina derivation or mental-bar mechanics.
