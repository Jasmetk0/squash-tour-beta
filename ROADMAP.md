# Squash Engine roadmap

## Active pre-alpha sequence — Calendar content ownership

1. **Calendar source → Run snapshot:** this branch packages one authored season calendar
   using stable event IDs and exposes an immutable Run-owned typed Calendar projection.
2. Category/Series labels remain payload data only; no unresolved product identity is
   guessed into a source reference.
3. **Next:** route authoritative Week/Season Calendar reads through an explicitly
   selected Run-owned Calendar Package, preserving legacy callers during migration.
4. Then migrate the remaining concrete Week-1 tournament/match fixture content into a
   stable Run-owned source boundary.
5. Release gate remains Master §31.3 Official Run → complete season → Save/reopen →
   Season Transition → next Season Week 1 without fixture-only or live-global
   ownership.


## Active pre-alpha sequence — remove fixture ownership from Official Run acceptance

1. **World player bootstrap in whole-season acceptance:** this branch applies Official
   FAX World through the Run Package boundary, generates the first-season roster from
   Run-owned World state and adopts it directly into InitialWorld.
2. The acceptance no longer creates bespoke global initial-pool players merely to match
   tournament fixture IDs; the remaining fixture bracket is rebound to the generated
   roster.
3. **Next:** migrate the concrete Season-0 tournament/Calendar fixture ownership behind
   stable source identities and canonical Run Package/application semantics. Do not
   infer unresolved Category/Series/Calendar product relationships just to eliminate a
   test fixture.
4. Preserve the already-canonical ranking, Week/Season Transition, Save/reopen and Full
   Simulation orchestration while replacing only bootstrap/content ownership.
5. Release gate remains Master §31.3 Official Run → complete season → Save/reopen →
   Season Transition → next Season Week 1 with no fixture-only or live-global ownership.


## Active pre-alpha sequence — complete World bootstrap ownership

1. **Run-owned World player bootstrap: implemented on this branch.** Player identity
   generation data lives inside the World source Package, materializes through the
   canonical Run Package backbone, generates deterministic read-only pools from
   Run-owned state, and can be reviewed/confirmed directly into InitialWorld.
2. The adopted InitialWorld freezes World-country, generation-config and exact
   generated-pool provenance and survives normal Save/reopen without routing through
   the global `initial_player_pool.json` path.
3. **Next:** re-audit the concrete Official Run acceptance fixture and choose the
   smallest remaining Package/content dependency needed for the complete-season flow.
   Expected candidates remain Category hierarchy / Series / Calendar / tournament
   content, but selection must follow an observed dependency rather than inertia.
4. Do not canonize legacy Category/Calendar template strings as Package identities.
   Category/Series/Calendar adapters must wait for or establish the Master-required
   stable source IDs and unresolved-reference contract.
5. Keep Official FAX source content as an offered default, never a universal Run
   prerequisite.
6. Main release gate remains Master §31.3 Official Run → complete season →
   Save/reopen → Season Transition → next Season Week 1 without fixture-only or live
   global-config ownership.

## Active pre-alpha sequence — first Package semantic adapter

1. **World source → Run-owned countries:** this branch adapts existing directory-backed
   World Packages into the canonical Run Package backbone and exposes a typed Run-owned
   country projection. InitialWorld may explicitly bind to one named World Package
   snapshot without introducing a live source link or implicit multi-Package priority.
2. After merge, compare the remaining Official Run acceptance fixtures against Run-owned
   Package content. Select the smallest next semantic adapter that replaces a real
   legacy/global dependency (expected candidates: Category hierarchy / tournament
   templates / Calendar content).
3. Keep concrete Official FAX CONTENT separate from generic engine semantics. Built-in
   Official packages are defaults, not mandatory requirements for arbitrary Runs.
4. Continue to preserve the already-green empty-Run standalone-match flow and the
   Package Save/restore/fork invariants while connecting consumers.
5. The main release gate remains Master §31.3 Official Run → complete season →
   Save/reopen → Season Transition → next Season Week 1 without fixture-only ownership.

## Active pre-alpha sequence — Run Package backbone implemented on this branch

The canonical five-type Package document, Run/Branch-owned snapshot, preview/confirm,
Saved Revision capture/restore and materialized fork path are now implemented as a
backend authority backbone. This does not yet supply Official FAX content or connect all
Package payloads to sporting consumers. After this PR, audit the remaining semantic
adapter needs, then choose the smallest path to the concrete Official Run bootstrap.

This is a milestone summary, not a second product constitution. [`SQUASH_ENGINE_MASTER_VISION.md`](SQUASH_ENGINE_MASTER_VISION.md) plus newer explicit decisions take precedence over `PROJECT_CONSTITUTION_TECHNICAL_PLAN.md`; `docs/ENGINE_UX_SPEC.md` provides subordinate migration guidance. Planned behavior must not be described as implemented unless verified in the repository.

## Active pre-alpha sequence — post-#971 coverage audit

Read the active checkpoint at the top of [CURRENT_STATE.md](CURRENT_STATE.md).
PR #971 closed the immediate Full Simulation abandonment / Completed-Run alternative
Branch orchestration boundary. The subsequent Master-to-code audit now identifies the
next dependency from §31.3 rather than continuing recovery work by inertia.

1. **Canonical Package → Run snapshot/application backbone.** Establish the common
   versioned identity/envelope and Run-owned Working-Draft preview/apply boundary for
   the five canonical Package types `World / Category / Series / Calendar / Setup`.
   Reuse existing domain/config payloads. Preserve non-destructive partial scope,
   unresolved-dependency visibility, independent Run snapshots, provenance, exact
   retry/idempotence, explicit changed-version diff/update behavior and
   Save/reopen/restore/fork coverage. Do not choose unresolved sporting PRODUCT or
   CONTENT defaults in this technical slice.
2. Refresh the coverage table after the Package slice and select the smallest
   remaining dependency for the main Official Run §31.3 acceptance. Expected later
   gates include freezing the concrete Official Run content/bootstrap set
   (PAQ-135–142) and filling only the player AI/health/calibration minimum actually
   required by that acceptance dataset.
3. Surface true PRODUCT questions to the owner when they block the chosen flow.
   TECH questions may be resolved autonomously; CALIBRATION requires a versioned,
   measurable default; CONTENT belongs to the selected Official Run data rather than
   an engine-wide hidden constant.
4. Once the known implementation/data gaps are closed, reconcile the complete
   pre-alpha Master scope with the owner and record approved minimal defaults or
   deferments explicitly.
5. Release gate: both Master §31.3 flows, required scope coverage, recovery/
   determinism/public-history checks, complete backend/frontend build suites where
   applicable, and an agreed representative performance baseline. Do not declare
   pre-alpha complete from Fast CI or a fixture-only whole-season path.

The empty-Run → two manual players → standalone-match acceptance is already
implemented. The main Official Run season acceptance remains the gating end-to-end
flow; its orchestration foundation is present, but canonical Package/content bootstrap
must replace fixture/legacy ownership before release-grade acceptance can be claimed.

## Implemented narrow tournament integration

The current narrow driver retains automatic compatibility adoption for one persisted
supported four-player Main Draw. For multiple/general supported topologies it still
requires an immutable, fingerprinted Run/Branch/RankingWeek schedule adopted through
the Admin preview/confirm boundary, but the engine can now generate a deterministic
topological proposal from the canonical match DAG. The proposal places every group
in the earliest dependency-safe global Simulation Slot, parallelizes independent
groups at the same depth, remains read-only until adoption, and fails instead of
choosing chronology when one directly known player appears in parallel independent
groups. An explicit atomic Admin command can now adopt the current proposal without
round-tripping its full payload: it rebuilds under the write lock and verifies the
expected Ranking Week, schedule fingerprint and position fingerprint before commit. Each event closes independently and exactly once
through the existing completion, award and `OwnedTournamentRankingSource` contracts.
Legacy `start_day`, list/event ordering and draw-round arithmetic are not substitutes. Explicit authoritative Admin routes expose
position, split Next Match and Next Slot without redirecting legacy simulation.
Independent same-slot groups now commit atomically and resume after failure, while
transition readiness reuses the authoritative match/effect sporting preflight.
General canonical Main/Qualification draws, explicit Entry/WC authority, bracket-Qualification Lucky Loser execution and dynamic qualifier-vs-BYE closure are now production-backed. Remaining Gate 3 boundaries include group-Qualification LL cross-group ordering, the explicitly undefined exhausted-source edge, automatic Entry/WC eligibility policy, broader AI-authored/general scheduling and health.
The repeated-flow acceptance now proves three completed authoritative RankingWeeks
(Week 1 → Week 2 → Week 3 → Week 4), and a production-backed acceptance repeats
eight-player/seven-match Main Draws across the same three-week chain with ranking
transitions and historical replay. A separate Run-owned canonical acceptance now
executes a sixteen-player/fifteen-match complete-binary Main Draw across four derived
Simulation Slots and closes it into `OwnedTournamentRankingSource v5`, including
correct R16/QF/SF/finalist/champion finishing-stage distribution.

The merged #743–#749 chain now owns Tournament Ranking Snapshot → canonical
Entry Field → immutable Draw Input → replayable Run-owned Qualification/Main Draw
Authority. The current bounded follow-up makes that Draw Authority the preferred
source of authoritative match topology: direct participants, feeder winners,
terminal identity, explicit BYE auto-advance and the single-Q promotion edge are
projected from the canonical bracket. Legacy MatchPackage remains only a temporary
execution/result payload and must bind one-to-one to canonical nodes. New frozen
tournament authority v5 includes the exact Draw Authority fingerprint. Multi-Q sections and dynamic qualifier-vs-BYE auto-advance now execute through
the canonical Run-owned path. Bracket Qualification can also continue from real
authoritative Q receipts through frozen Lucky Loser vacancy/fill into repaired Main
execution and canonical tournament close. Group-Qualification LL cross-group ordering
and the explicitly undefined exhausted-source edge remain fail-closed rather than
borrowing legacy DrawPackage policy.

Qualification promotion plus unambiguous one-player BYEs execute through the
authoritative tournament/ranking bridge. Canonical pre-draw field rebalance, reviewed
WC/RWC assignment, Draw process windows, append-only Draw repair, replacement-source
authority and bracket-Qualification Lucky Loser vacancy/fill now operate on the
Run/Branch-owned authority chain. The legacy #739/#740 shortcut producers remain
fail-closed/read-only compatibility history rather than sporting authority. Recent
acceptance proves dynamic qualifier-vs-BYE closure and real Qualification receipts ->
Lucky Loser -> repaired Main -> canonical tournament close. The remaining replacement
boundaries are the explicitly undecided group-Qualification LL cross-group ordering
and post-Main-start/all-sources-exhausted policy; these stay fail-closed rather than
inventing Master rules.

## Active pre-alpha dependency path (audit after #728 plus current driver slice)

This sequence is a technical plan, not a new product-rule registry. Re-evaluate
it after each merge using `CURRENT_STATE.md`. Existing detailed targets below
remain valid; their numbering is not a mandate to implement them in that order.

| Gate | Coherent outcome | Evidence required to advance |
|---|---|---|
| 0 — synchronize | One canonical Master, clear authority, verified state and next Codex task | Documentation preservation/link checks; no invented product decisions |
| 1 — source bridge (implemented slice) | Supported real main-draw results/awards become owned Run/Branch sources, feed Official candidate and survive Save/Restore | Real producer + API/SQLite covers preview, rollback, retry, reopen and recovery; broader source types remain guarded |
| 2 — one true week boundary (implemented expanded slice) | One SQLite owner resolves an explicit owned completed-tournament manifest, develops canonical sporting state, performs provisional between-week updates, derives lifecycle roster including birth-week pre-Tour Draft prospects, then atomically publishes/advances/audits | Missing/empty sporting evidence fails closed for the simulation-ready sporting roster; match-derived state beyond counts and health remain boundaries; incomplete prospect sporting profiles remain deferred until an operation actually requires them |
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
- **Implemented Match Day foundation:** automatically derived tournament schedules now use `week_simulation_schedule.v2`; each competitive match gets its own global slot plus immutable Match Day / within-day order metadata, so same-day tournament matches execute sequentially and later matches see current sporting state. Historical v1 schedules remain compatible.
- Keep the current V2 scheduler deliberately hard-constraint-only: Qualification-before-Main, feeder on an earlier day, directly-known player max one match/day, deterministic order and Entry/WC global-slot reservations. Multi-week Round Schedule spans, courts and travel/rest/carryover/fairness optimization remain follow-ups. See `docs/MATCH_DAY_SCHEDULE_V1.md`.
- Support `Simulate Next Slot` and split `Simulate Next Match` semantics.
- Implement **Season Transition** as the Week 61 → Week 1 special boundary with atomic seasonal-policy activation, scoped resets and a lightweight Season Closure Marker.

## 5. Tournament lifecycle, public knowledge and entries

- Consolidate Tournament Series/Editions, calendars, qualification, draws and lifecycle validation.
- Derive Tournament Edition lifecycle/component state and public `Public Stage` from authoritative state.
- Persist historical `announcement_week`; Viewer and player AI may know an Edition only after the corresponding public World Event.
- Keep entry decisions within a slot on a shared snapshot and commit them transactionally.
- Preserve entry/application objects as historical state.
- Keep unresolved Entry Freeze/cut-off details open.
- **Implemented foundation:** Run simulation freezes persisted Entry/Draw/Match evidence as a versioned topology DAG and validates explicit global-slot coverage for complete binary Main Draws; production eight-player Main Draws repeat across three authoritative weeks while retaining the historical four-player reader. Indexed qualifier mappings and unambiguous one-player Qualification BYEs execute and ingest into ranking authority. Entry decisions for overlapping events are generated transactionally from one shared snapshot, and a blocking persisted Entry slot can now be resolved through an explicit audited Admin validation workflow whose source/application/tie-break authority is derived server-side from frozen Run truth. This operational pre-alpha bridge does not invent the still-open automatic eligibility/deadline policy. Overlapping accepted fields now fail closed until an explicit audited Week Tournament Lock selects one current accepted event per conflicting player and atomically repairs the unselected fields; the automatic Final Commitment deadline/preference policy remains open. WC and alternate-replacement provenance primitives exist. Canonical pre-draw field rebalance is implemented as an append-only Run/Branch command and now has a branch-scoped Admin HTTP boundary; legacy UI/endpoint retirement, RWC/WC repair, post-draw repair phases, LL ordering and the replacement cutoff remain Gate 3 work.

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
- The supported ordinary transition bootstraps Week 1 lifecycle and canonical sporting state from owned initial-world players, runs provisional historical development and between-week state, advances birthdays/retirement, activates exact target-week Run prospects into lifecycle as pre-Tour Draft identities, and derives ranking identity server-side. Sporting state is allowed to be a simulation-ready subset of lifecycle; Match-derived state/health and full prospect sporting-profile creation remain open. See `docs/AUTHORITATIVE_PLAYER_LIFECYCLE_WEEK_STATE_V1.md` and `docs/AUTHORITATIVE_PLAYER_SPORTING_WEEK_STATE_V1.md`.
- **Implemented Master §31.3 acceptance flow #2 backend slice:** a canonical empty product Run may author exactly two complete manual players and simulate one standalone competitive match without Calendar/Tournament/Entry/Draw prerequisites. Commit freezes manual InitialWorld provenance, Week-1 lifecycle/sporting truth and one canonical Simulation Slot atomically; exact retry is idempotent and the existing authoritative simulation Save captures the completed history. See `docs/STANDALONE_MATCH_ACCEPTANCE_V1.md`.

## 8. Match Reconstruction v1

- **Implemented minimum canonical slice:** Admin **Match Reconstruction** treats manually supplied winner, exact match score and exact game scores as hard constraints on the current eligible Run/Branch match.
- Admin chooses candidate count and can inspect compact summaries plus complete read-only canonical Match Result detail.
- Candidate generation reuses the canonical Match Engine / Simulation Slot executor and rolls all preview staging back, so preview does not mutate authoritative history.
- Only an explicitly selected candidate may become history; commit re-derives the reviewed candidate under current week / Position / Saved Revision guards, requires exact result replay and persists reconstruction provenance plus operator/audit reason.
- Bounded natural search may return fewer candidates with a warning; it does not force an answer.
- Keep candidate probability architecture, p/δ/α policy, forcing, nearest-match search, complete constraint catalog, session retention and final compact-card/dedicated-page design at their unresolved status.
- See `docs/MATCH_RECONSTRUCTION_V1.md`.

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


### Run-owned Point Award + direct ranking follow-up

After #752, canonical tournament results are Run-owned. The current larger follow-up
also removes legacy point-award generation and legacy tournament DTO ingestion from
the canonical ranking path. Authored point distribution is frozen once, embedded in
replayable `TournamentPointAwardAuthority`, and persisted with the result as
`OwnedTournamentRankingSource v3`. Point Award v3 now also carries Master §18.1
additive Qualification + Main values for players who participate in both draws:
successful qualifiers use their Qualification-winner value, Lucky Losers retain the
value of the Qualification stage they actually reached, and each draw applies the
BYE/W/O unlock contract independently before the two values are summed. Historical
v1/v2 Point Award fingerprints remain stable. The following Ranking Week can
materialize Official ranking-result history directly from those canonical authorities
without a `SeasonPointAwardsService` instance. Legacy-shaped result/award DTOs remain
only compatibility projections for historical readers.


### Canonical-only owned tournament source follow-up

After #753, canonical result and point authorities already drive ranking directly.
The current follow-up removes their remaining duplicated legacy persistence:
new `OwnedTournamentRankingSource v4` stores only canonical result/point
authorities and their binding. Historical v1-v3 sources remain immutable readers;
new canonical closes do not build or persist legacy result/award DTO copies.


### Canonical adopted-tournament authority v6 follow-up

After #754, ranking-source persistence is canonical-only. The current follow-up
removes the remaining pre-execution MatchPackage snapshot from new canonical week
adoption. v6 freezes the Calendar Event snapshot, Draw fingerprint and point
authority, then rebuilds the execution package deterministically on replay. This
also removes live Calendar and legacy match-registry reads after adoption while
keeping v1-v5 historical readers intact.

### Canonical pre-draw withdrawal follow-up

After #756 restored the complete frontend test baseline, the next bounded Gate 3
slice exposes the already-defined canonical Tournament Entry Field rebalance through
a transaction-owned application command. It reuses frozen application evidence and
the Edition's Tournament Ranking Snapshot, appends one immutable repair version and
reports the exact Main promotion / Qualification backfill delta. The immediate
follow-up exposes this state and command through a dedicated Run/Branch Admin HTTP
surface with expected-field fingerprint protection. New repairs remain locked after
Tournament Draw Input commitment.

The canonical pre-draw surface now continues through the initial Draw boundary.
Run/Branch Admin can inspect Draw state, commit immutable Draw Input against the
expected terminal Entry Field fingerprint, generate the immutable initial Draw
against the expected Draw Input fingerprint, and read the exact canonical bracket
payload. Seed counts remain server-derived from Master rules; the client supplies
only a technical deterministic replay seed. Planned Event Detail consumes this
authority directly and renders Main/Q slot state without reusing the legacy
SeasonDrawService. Classic Main capacity is fail-closed at 2/4/8/16/32/64/128 and
production Draw geometry now has direct canonical generation coverage at every
supported size. Planned Event Admin now continues through the existing process-window
authority and revision visibility boundary: Main/Q window counts are configured
explicitly, Redraw Cutoff/Draw Freeze ordinals remain server-derived from Master
§15.10, the immutable initial Draw remains inspectable, the displayed active bracket
comes from the effective successor Draw, and compact append-only revision history
shows why it changed. This closes the Draw authority inspection/configuration slice.

The existing Run/Branch authoritative Simulation Slot driver is now surfaced in the
Simulation Admin UI as its own canonical path. The UI respects the backend lifecycle:
inspect Week Schedule requirements first; when chronology is required, build and
atomically adopt the dependency-safe topological proposal; only then inspect Position
and execute explicit Next Match / whole Next Slot commands; finally Save through the
simulation-draft fingerprint/version CAS boundary. This does not reinterpret the
legacy branch wrapper. The first higher-level canonical orchestration boundary is now implemented as
**Next Match Day**: a read-only preview freezes the exact remaining V2 Match Day
slots, while a durable parent command executes them through deterministic,
resumable Next Slot children and fails closed on schedule/head/chronology drift.
The canonical Simulation Admin UI now exposes this as a reviewed two-step action and
preserves the same parent command ID across ordinary response-loss retry.
**Next Round is now canonical**: it derives the current event/phase/round identity
from the adopted V2 schedule, freezes the exact global chronology horizon through the
last remaining target match, reports interleaved transit matches, resumes through
deterministic Next Slot children and fails closed on process-slot or chronology drift.
**Next Tournament is now canonical** as well: it freezes the current event ID,
every remaining target match and the exact global chronology horizon through the
event's final target, reports interleaved other-event matches as transit work, and
only completes after canonical Owned Tournament Ranking Source closure.
**Next Week is now canonical**: one reviewed durable parent freezes every
remaining current-week V2 match slot plus the target Ranking Transition Authority,
executes sport through deterministic Next Slot children, then freezes and executes
the existing atomic Week Transition. Known non-progress prerequisites fail the wider
preview closed; later legitimate checkpoints return resumable blocked progress while
preserving the exact parent command. Week 61 remains a Season Transition boundary.
**Next Season is now canonical** as a progressive reviewed parent. It composes
ordinary weeks through exact Next Week children, closes only Calendar-proven empty
weeks through audited Empty Week children, and stops on explicit process decisions.
At Week 61 it finishes sporting evidence, requires a real explicit Save, exposes the
existing Season Transition preflight/review checkpoint, and completes only after the
canonical Season Transition has actually moved Position to next Season Week 1. The
same parent survives reopen and every checkpoint without rerolling completed weeks.
Final 2049/50 closure stays on its dedicated terminal path.

**Full Simulation is now canonical** across the complete remaining Run. Ordinary
seasons are deterministic Next Season children; the final 2049/50 season uses
canonical Week/empty-week/slot evidence and terminates only through the existing final
Run closure. Every Save and ordinary/final transition confirmation remains an explicit
progress checkpoint, while the same parent command survives reopen and exact retry.
This closes the long-range Simulation orchestration stack for the pre-alpha path. See
`docs/AUTHORITATIVE_MATCH_DAY_ORCHESTRATION_V1.md`,
`docs/AUTHORITATIVE_ROUND_ORCHESTRATION_V1.md`,
`docs/AUTHORITATIVE_TOURNAMENT_ORCHESTRATION_V1.md`,
`docs/AUTHORITATIVE_WEEK_ORCHESTRATION_V1.md` and
`docs/AUTHORITATIVE_SEASON_ORCHESTRATION_V1.md` and
`docs/AUTHORITATIVE_FULL_SIMULATION_V1.md`.

The next canonical boundary is now partially integrated rather than client-authored:
once Position reports `week_ready_for_transition`, a new server-derived Week
Transition preview builds the exact command from the current Saved Revision head,
persisted Ranking Transition Authority and Owned Tournament bindings. Admin reviews
that frozen request, confirms it through the existing request/ranking fingerprint
guards, then saves the transitioned ranking/world draft through the ranking Save CAS.
This removes manual Week Transition command assembly from the UI while preserving
exact retry of the reviewed command.

The ordinary within-season Ranking Transition Authority prerequisite is now derived
canonically as well. When it is the sole Week Transition blocker, Admin supplies only
an audit label/reason; the backend freezes the current Saved Revision head,
target-week roster produced by the canonical lifecycle transition and the predecessor
Official Ranking policy. Preview is read-only, confirm is bound to the reviewed
authority fingerprint, and the authority is then Saved through the ranking revision
CAS before Week Transition becomes ready. The manual authority endpoint remains a
compatibility/advanced boundary, not the default canonical UI path. Week 61 continues
to require Season Transition.

Target-week prospect intake is now canonical rather than a Week Transition
blocker. The engine selects the exact matching Run-scoped pregeneration rows only
when their birth week opens, validates the stored birth identity and materializes
them into branch-owned lifecycle with a deterministic tie-break identity and
`tour_entry_week=None`. They are therefore absent from earlier lifecycle history
and from Official Ranking until a later formal Tour-entry event. The existing
Prospect Bridge inspection is retained only as a read-only profile-readiness
diagnostic: it fingerprints target-week rows and exposes placeholder
attributes/development/potential/traits, but reports no transition blocker. Sporting
state may be a simulation-ready subset of lifecycle, so a pre-Tour Draft prospect
does not enter weekly development or normal junior match simulation merely because
it became visible. Full canonical sporting-profile creation remains required before
an operation that actually needs that sporting state. A branch-aware prospect read
model now uses exact lifecycle history as the visibility authority: Admin may inspect
an exact historical week and Viewer exposes only the current selected Viewer Branch
pre-Tour population. Future pregenerated cohorts and seed/profile internals are not
Viewer data. Once a prospect becomes lifecycle-visible on any branch, the backing
public identity metadata is immutable under normal prospect materialization so later
overwrite cannot rewrite historical Viewer identity.

Week 61 now also has a canonical **read-only Season Transition preflight**. It
freezes the current authoritative Position, Saved Revision head and branch-state
blockers, distinguishes those from still-missing engine writers, and projects only
the Master-defined next boundary: next Season Week 1, or final Run closure after
season 2049/50. The Admin Simulation page renders that preflight at Week 61, shows state blockers
and implementation gaps separately, hides the ordinary Week Transition controls,
and exposes the reviewed ordinary Season Transition execution path when the
preflight is ready. The preflight and commit path never call the legacy rollover
service.

The first Season Transition write primitive now exists below that preflight:
`season_closing_ranking.v1` is a separate immutable archive snapshot calculated
from the Week 61 Official head under the outgoing policy. Its ranking boundary is
immediately after Week 61, so newly completed Week 61 results can affect the closing
order without creating a next-season Official Ranking. An append-only Run/Branch/
season store binds the archive to the exact Week 61 Official fingerprint and exact
retries are idempotent. This kernel deliberately does **not** publish to the world
clock or feed entries/seeding/AI. Ordinary season boundaries now also have a
canonical resolver/stager: it requires the published authoritative Week 61 head,
uses the Week 61 lifecycle roster, converts frozen Run-owned Week-61 tournament
sources directly to ranking results, overlays historically resolved result/discipline
state at next Season Week 1, and appends the archive inside the caller transaction.
Canonical simulation now reaches that input boundary correctly for seasons 0–48:
completed Week-61 tournaments freeze their Owned Tournament Ranking Source first,
with publication boundary set to the following Season Week 1, and only the returned
simulation position then exposes `season_transition_required`; no ordinary Week
Transition or world-clock advance occurs.
It deliberately refuses the final 2049/50 edge because no Season 50 Week 1 exists.
Saved Revision capture/restore now includes Closing Ranking archives through
`ranking_revision_state.v6`, preserving exact Week-61 publication/policy binding
and guarded recovery of historical season archives. The final 2049/50 source edge now also has a dedicated Closing-only adapter:
canonical Week-61 tournament evidence is frozen as owned source v6 with an
eligibility ordinal immediately after the last real week, never a fabricated
2050/51 Week 1. The final Closing Ranking resolver consumes that evidence directly
while ordinary Official history remains unchanged. The next step-3 kernel now also
exists without inventing the still-deferred statistic catalogue or Marker storage
schema: `season_summary.v1` freezes only explicitly registered authoritative
season-scoped components against the Closing Ranking, and
`season_closure_marker_candidate.v1` binds that summary, the Closing Ranking and
the outgoing Official Ranking Policy fingerprint. The current canonical registry is
deliberately empty because no branch-scoped resettable statistic store is yet an
authoritative producer; legacy Race snapshots are not promoted into this path.
The Marker receives its final Saved Revision identity only after that revision is
staged by the future atomic Season Transition writer, preventing stale closure
markers across restore/replay. The final-Run lifecycle kernel is now bounded too:
`working` (plus compatibility `active`) may become `completed` only from a
Branch-head Saved Revision that contains matching final Season Closure evidence for
2049/50 Week 61. The transition is idempotent and all other lifecycle/week/evidence
combinations fail closed. Saved Revision restore accepts this immutable closure
component, while direct fork from the final closure revision remains guarded until
identity remapping exists. The final 2049/50 path is now wired end-to-end as one
atomic command: fresh preflight → Closing Ranking → Summary/Marker → complete Saved
Revision → Working Draft/head advance → Run Completed. The command uses
`BEGIN IMMEDIATE`, embeds the closure evidence in the exact final revision, records
an audit request fingerprint for retry identity, and rolls back every staged closure
write on failure. Final preflight can therefore become executable when its real
state blockers are empty. Ordinary seasons now also have a deterministic
`season_transition_configuration.v1` staging contract. It binds the exact Week-61
Official Ranking, Week-61 sporting state and current Saved Revision head to the
incoming Week-1 Ranking Policy, incoming Player Development Policy and an explicit
`season_scoped_reset_catalog.v1`. The default proposal inherits both supported
outgoing policies, while the preview API may supply explicit incoming overrides.
The reset registry is deliberately empty until a real branch-scoped resettable
season-stat producer exists; empty means reset nothing, not fabricate zero values.
The ordinary preflight fingerprints this default configuration and no longer lists
policy activation or reset-catalog construction as missing kernels. Cross-season
sporting staging is now implemented too: Week-61 development and between-week
recovery are calculated under the outgoing effective Development Policy, while the
resulting next-season Week-1 sporting snapshot installs the selected incoming policy.
The preflight binds that exact default W1 sporting fingerprint. The shared weekly
sporting staging path also preserves the persisted weekly predecessor fingerprint
when terminal in-week match state is used; terminal match evidence remains separately
bound through the completed-week context, keeping Saved Revision lineage valid.
The existing-player lifecycle boundary is now staged canonically as well: a
consecutive Week-61 -> next-season Week-1 transition applies mapped birthdays and
age-based retirement, preserves lifecycle lineage and can be persisted inside the
future caller-owned Season transaction. Run prospects due in target Week 1 are activated into the staged lifecycle as
pre-Tour Draft identities and remain outside the staged sporting/ranking rosters. The incoming Week-1 Official
Ranking can now be resolved read-only and staged through the canonical
RankingWeekCommand from the incoming policy, exact staged lifecycle roster,
disciplinary history and Week-61 owned tournament sources. The ordinary atomic
rollover writer is now implemented behind the Admin API: one transaction stages the
Closing Ranking and closure package, sporting, lifecycle and Week-1 Ranking; publishes
Week 1; advances the world head; emits the season-transition World Event; and captures
the complete boundary into a new Saved Revision plus audit event. It is idempotent by
Saved Revision/audit identity and rollback-tested after partial publication. A
non-empty reset catalog fails closed until an authoritative reset adapter exists.
Ordinary boundaries, including a target Week 1 with birth-week prospects, can now
execute through the reviewed Admin flow. Saved Revision recovery preserves ordinary
Season Transition World Events through `ranking_revision_state.v7` while keeping
Week Transition receipts strict. New prospect materialization now persists the
canonical 57-attribute sporting-profile kernel before lifecycle activation and binds
its exact generation-policy fingerprint. Ordinary Week **and Season** Transition now
adopt exact birth-week prospects into the target sporting snapshot only after
completed-week development/recovery, while keeping `tour_entry_week=None` and
excluding them from Official Ranking. Placeholder/corrupt profile evidence fails
closed at the affected transition boundary. Formal Tour-entry activation now has exact branch-scoped evidence for both
Master-defined triggers: valid MSA Tour application submission and definitive WC/RWC
assignment. The first trigger is append-only, immediately visible through the current
lifecycle read projection, and sealed into later lifecycle/ranking boundaries without
retroactive Official Ranking mutation. The application side now preserves a complete
shared-snapshot pre-cut Entry decision slot, persists explicit validation outcomes and
valid submissions, and can feed the canonical Tournament Entry Field from persisted
submission truth rather than caller-reconstructed applications. The remaining Entry
authority work is the concrete versioned eligibility/deadline validator and the later
generic multi-kind Simulation Slot planner needed for future Entry reservations among
already-planned match slots. The historically scoped Admin/Viewer prospect surface is
implemented from lifecycle truth.

The canonical authority now supports equal `Q1..Qn` bracket sections and the
execution/result pipeline preserves all corresponding promotions. A focused
production-backed acceptance proves four two-player Q sections end-to-end:
Official Ranking → frozen Entry/Draw authorities → topological Simulation Slots →
Q1..Q4 promotion into one eight-player Main → canonical close → additive
Qualification + Main Point Award v3. The 12-player scenario owns exactly 11
competitive matches and closes into one ranking source. The same draw slice also
aligns new Draw Input/Draw generation with Master §15.2–15.4: seed counts are
derived canonically, physical slots carry idealized numbers, later seed tiers shuffle
only inside their allowed idealized tier, and initial Main Draw BYEs consume the
highest idealized slots. Historical v1 replay remains intact.

Qualification BYE distribution across parallel Q sections is now the active draw
slice: missing Q-field positions become canonical BYEs, full BYE layers are assigned
one-per-Q-section by descending idealized slot and incomplete final layers are
deterministically shuffled across Q sections. The execution topology also treats a
single-Q BYE as canonical auto-advance into its linked Q slot.

The next draw slice resolves pre-draw WC/RWC authority canonically: original WC
nominations and ordered RWC candidates are frozen against the Entry Field, direct
acceptance releases WC automatically, RWC has priority for the freed WC slot, and
Qualification is atomically backfilled when its player receives WC. Draw Input v3
then consumes the resolved WC players with frozen provenance.

Qualification and Main Draw process-window authority is the next implemented
foundation: each draw component has an independent configured timeline, with the
penultimate window fixed as Redraw Cutoff / seed-cascade and the final window fixed
as Draw Freeze. The authority is bound to the exact canonical Draw fingerprint and
is Saved Revision state.

Phase-aware repair now starts with append-only full-redraw withdrawal repair before
Redraw Cutoff. The repair re-resolves the affected Entry Field from the same frozen
Tournament Ranking Snapshot, freezes that successor field plus its derived Draw Input,
uses a new repair draw seed and stores a predecessor-linked Draw revision. Main
withdrawal can therefore atomically promote from Qualification and backfill Q from
below the cut; Qualification-only withdrawal leaves Main unchanged. Every affected
draw component must independently still be in its own full-redraw phase, and Q1..Qn
linkage identities remain stable. WC/RWC events stay blocked from this generic slice
until their dedicated post-draw repair path exists.

The middle repair phase from Redraw Cutoff through the window before Draw Freeze
now performs tier-aware seed cascade for seeded withdrawals and exact physical-slot
fill for ordinary unseeded withdrawals. Cascade preserves original seed identities,
moves only the necessary later seed layers and promotes the highest-ranked surviving
eligible unseeded player into the final seed vacancy. The ordinary incoming
replacement fills that player's old slot; when no replacement remains, that final
physical vacancy becomes a BYE. An unseeded withdrawal likewise leaves a BYE in its
own exact slot if no replacement exists. Main and Qualification remain independently
phase-gated, so one atomic v3 repair may fully redraw one affected component while
cascading the other; the dedicated repair seed affects only the redrawn component.
Multi-Q identities are preserved and the append-only revision is deterministic Saved
Revision state. Pure cascade keeps the existing draw seed.

The Draw Freeze repair phase now uses append-only v4 revisions. Every affected
component is gated independently: a frozen component changes only the exact vacated
physical slot, while another affected component in the same atomic revision may
still full-redraw or seed-cascade according to its own process window. Frozen-slot
replacements never inherit the predecessor's seed number, seed protection or entry
status. If the ranking-ordered frozen field has no permitted replacement left, the
same physical slot becomes a late BYE with no reshuffle. Multi-Q section identities,
the existing draw seed and deterministic revision replay remain stable. The middle
seed-cascade path now has the same no-replacement safety boundary: after required
cascade moves complete, any remaining final physical vacancy is frozen as a BYE.

The player-specific replacement cutoff is now enforced by canonical draw repair.
Every new successful repair freezes one `tournament_player_replacement_cutoff.v1`
authority per withdrawn player inside cutoff-aware Draw revision v5. Evidence comes
only from validated Run/Branch authoritative competitive match receipts; canonical
BYE auto-advances create no such receipt and therefore do not close the cutoff. In
the current atomic executor, the first committed real-match group is the durable
boundary that the player's first real match has started. A player with no such match
remains replaceable; a player whose latest real match was a win is routed to the
future W/O path, while an already eliminated player cannot mutate the active Draw.
Historical v2-v4 Draw revisions remain replayable without retroactively consulting
later match history.

Post-cutoff W/O now has its own canonical authority and Run/Branch command path.
A W/O is persisted as a noncompetitive authoritative event-group receipt in the
already planned Simulation Slot: it preserves the Draw unchanged, resolves the
opponent from the existing topology, advances that opponent with scoreline `W/O`,
and produces no Match Engine input, rallies or sporting effects. The embedded
replacement-cutoff evidence proves that the withdrawn player had already crossed
their first-real-match boundary. W/O receipts do not themselves become new
real-match cutoff evidence. Saved Revision capture/restore reuses the common group
ledger, and the Admin boundary exposes an explicit post-cutoff W/O command.

Canonical result authority distinguishes W/O from played wins/losses while still
using it for bracket stage progression. Canonical ranking points now implement the
Master §16.3 exception: a W/O advance can unlock the authored value of the player's
actual finishing stage without creating a played win/loss or H2H result. The point
builder revalidates those counters from frozen match evidence, and a terminal W/O
command now executes the normal canonical tournament close and ranking-source
persistence. Canonical prize-money payout calculation is now run-owned. Tournament close builds
`TournamentPrizeMoneyAwardAuthority v1` from the frozen Tournament Result and
Edition payout configuration, then persists it inside
`OwnedTournamentRankingSource v5`. Every player receives one payout status from
their final tournament finishing stage; known amounts stay in the Edition's original
currency, unknown/missing stages remain Unknown, W/O advancement is payout-eligible
without becoming a played win, and the authority distinguishes known subtotal from a
complete prize pool. Ranking ingestion deliberately continues to consume only
canonical Result + Point Awards. Historical v1-v4 sources remain immutable readers.

Player prize-money history now has a branch-scoped read model over those owned
sources. It provides the exact event ledger, per-season status counts and known
season/career totals by original currency, while preserving Unknown,
not-configured and pre-v5 historical-unavailable states. It deliberately does not
sum different currencies. The next finance dependency for Master §19.1 is a
Run-owned historical FX table keyed by week plus reporting-currency conversion;
source/generation of rates, base currency and rounding remain unresolved product
configuration and must not be invented. Post-draw WC/RWC work has now started with the first bounded canonical slice:
after Main Draw Freeze, withdrawal of an **unseeded active WC holder** can consume
the next available **external** Reserve Wild Card in stored RWC order. The repair is
append-only revision v6, preserves the exact physical Main slot, preserves the
`[WC]` entry status without inheriting a seed, freezes replacement-cutoff evidence,
and carries explicit post-draw WC lineage in Draw Input v4. Sequential RWC use and
Saved Revision replay are deterministic.

The next frozen cross-draw RWC slice is now canonical too. If the highest-priority
available RWC is already an **unseeded Qualification player** and both Main and
Qualification are after Draw Freeze, one atomic revision promotes that player into
the exact vacated `[WC]` Main slot and fills the exact vacated Q slot with the
highest available player below the Qualification cut from the same frozen
Tournament Ranking Snapshot. `tournament_post_draw_wild_card_repair.v2` freezes
the Q section/slot and backfill ordinal; Draw revision v7 records Main + Q as one
transaction and Saved Revision replay rebuilds both sides deterministically.

Frozen seeded WC/RWC repair is now canonical as well. After Draw Freeze, a
replacement never inherits the withdrawn or promoted player's seed number. Seeded WC
withdrawal to an external RWC and promotion of a seeded Q-RWC both preserve the exact
physical slot while recording the former seed number as an explicit frozen vacancy.
`tournament_post_draw_wild_card_repair.v3` freezes that evidence and Draw Input v5
separates the historical configured seed count from currently active seeded players.
The draw's `seed_positions` therefore contains only still-active seeds.

Phase-aware Qualification repair is now canonical for **unseeded Q-RWC promotion**
while Main is already frozen. If Q is still before its Redraw Cutoff, the entire
Qualification draw is regenerated with an explicit repair draw seed. Between the Q
Redraw Cutoff and Q Draw Freeze, removing an unseeded RWC performs a direct fill of
that exact Q physical slot; no seed cascade is triggered. After Q Freeze, the
existing exact-slot frozen backfill remains authoritative. Draw revision v8 records
the mixed Main-frozen/Q-pre-freeze transaction and replay uses the same process
window and redraw seed.

Seeded Q-RWC promotion now follows the same independent Qualification phases.
Before Q Redraw Cutoff, full redraw rebuilds the Q seed field from the successor
ranking-ordered participants, so the next eligible Q player becomes the active seed.
Between Q Redraw Cutoff and Q Draw Freeze, the existing seed-cascade geometry moves
surviving players through the vacated seed tier without transferring the departed
seed number; the final active seed set may therefore shrink and Draw Input v5 records
the explicit vacancy. After Q Freeze, the already-canonical frozen vacancy behavior
still applies.

The WC/RWC phase mechanics are now complete through seeded/unseeded Q promotion.
Master §15.1 makes the remaining RWC-exhaustion fallback phase-dependent: before
Qualification starts it falls back to the ordinary Q-list promotion source, while
after Qualification starts it falls into Lucky Loser priority. The latter is no
longer left as an unnamed gap.

The first canonical Lucky Loser slice now owns **vacancy identity and chronology**.
After at least one real Qualification match exists, a replacement-open Direct Main
withdrawal in a frozen Main Draw can convert its exact physical slot into anonymous
`LL1`; later vacancies become `LL2`, `LL3`, etc. strictly by vacancy creation
order, not physical draw position. The authority freezes the first real Q-match
evidence that proves Qualification has started, the withdrawn player's replacement
cutoff, the exact Main slot and any vacated seed number. Draw Input v6 stores the
chronological LL placeholder lineage and Draw revision v9 stores the exact frozen
slot mutation. Unresolved LL placeholders deliberately block executable topology.

Bracket-Qualification **Lucky Loser candidate order** is canonical across both played
and auto-BYE terminals. Historical `tournament_lucky_loser_order.v1` remains valid
for all-played Qualification. New v2 freezes one-player auto-BYE terminal evidence
against the exact Q bracket while real terminals still require authoritative result
receipts. Auto-BYE winners add no LL candidate because no player was eliminated in
that section. Candidates from played Q matches still sort exactly by Master §15.8:
highest reached Q round first, then the frozen Tournament Ranking Snapshot. Mixed
multi-Q completion therefore waits only for unresolved real terminals rather than
failing on an already-complete one-player BYE section.

Lucky Loser placeholders can now be **filled canonically** from the frozen bracket-Q
candidate order. The fill authority always resolves the earliest still-unfilled
`LLx` slot, skips candidates already assigned to an earlier LL or explicitly frozen
as unavailable, and selects the first remaining candidate without reordering the
Master priority. Each fill freezes the order authority, selected candidate, skipped
identities, prior LL assignments and exact physical slot. The resulting Main slot is
a normal player entrant with `entry_status=lucky_loser` plus its retained `LLx`
identity; it never inherits seed status. Draw Input v7 tracks the chronological LL
players while preserving their original Qualification membership, and Draw revision
v10 records the exact fill. All later LL fills reuse the same frozen order authority
instead of recalculating priority after the Draw changes.

A shared **Main Draw replacement-source authority** now owns the source-priority
chain instead of leaving RWC, LL and reserve rules as disconnected mechanisms.
`tournament_replacement_source.v1` freezes the current Draw/Input, exact physical
slot, player-specific replacement cutoff, Q/Main start evidence, unavailable set,
prior LL assignments, external-reserve ordering and any WC/LL authority used by the
decision. Its priority is Master-driven: closed player cutoff → `W/O`; WC slot →
available `RWC`; before Qualification starts → highest eligible Q-list player; after
Qualification starts but before Q completes → pending `LLx`; after Q completes →
frozen LL order; after LL exhaustion → external reserves in frozen ranking order;
if nobody remains and Main has not started → late `BYE`. Active Main and active
Qualification players are excluded from external-reserve reuse.

The resolver derives Q/Main start evidence from authoritative match receipts and
reads the effective Draw Input / Entry Field from the latest revision chain, so it
cannot accidentally fall back to stale pre-revision state. One deliberately
fail-closed edge remains: if Main has already started elsewhere, this player's own
replacement cutoff is still open, and every candidate source is exhausted, Master
§15.8 does not yet state an explicit action for that intermediate state. The engine
therefore refuses to invent one.

A **frozen-Main replacement orchestrator** consumes the source authority and
dispatches one command into the canonical mutation path. It routes direct Main
vacancies to pre-Q Qualification promotion, pending/immediate Lucky Loser creation
and fill, source-aware post-Q external reserve, late BYE, and W/O; WC slots still
consume the dedicated RWC path first. Direct-Main reserve/BYE uses Draw Input v8 /
Draw revision v11. When every RWC is exhausted, WC slots may now fall through to an
ordinary external reserve or BYE: Draw Input v9 freezes exact released-WC ordinals and
Draw revision v12 changes the exact frozen physical slot without transferring WC
status. Deterministic child command IDs keep all of these mutation routes
replayable/idempotent across retries.

This orchestrator is now exposed through the canonical Planned Event Admin workflow:
preview derives the current source authority read-only, commit is bound to its exact
fingerprint and re-resolves under one immediate transaction, and successful Draw
repairs refresh the effective Draw/revision history. A `walkover` preview deliberately
hands off to the existing canonical Simulation W/O command instead of introducing a
second Draw-side W/O authority. The legacy simulation-run late-replacement authoring
surface is now retired: Planned Event no longer exposes its Commissioner controls,
and its eligibility/candidate/mutation endpoints return `410 Gone`. Historical
sidecar action history stays readable for audit/replay compatibility; no new legacy
late-replacement action can be authored through HTTP.

The orchestrator intentionally requires Main to be in Draw Freeze; pre-freeze
full-redraw/cascade routing remains in the existing specialized phase commands.
The post-Q WC→Lucky-Loser gap is closed with source-bound WC release: revision v13
creates the exact chronological LL placeholder while Draw Input v9 records the
released WC ordinal and replacement-source fingerprint. The pre-Q gap is now closed
as well: revision v14 routes both Direct-Main and exhausted-WC vacancies through the
frozen `qualification_promotion` source, skips explicitly unavailable candidates,
releases WC status where needed, and uses Qualification's own redraw /
seed-cascade / freeze phase for the Q-side repair. The older generic field resolver
remains available for non-orchestrated legacy repair paths but is no longer the
orchestrator's source of truth for pre-Q replacement. The undefined
post-Main-start/all-sources-exhausted policy from Master §15.8 remains unchanged.
Bracket-Qualification auto-BYE terminals are already covered by Lucky Loser order v2;
group-Qualification LL cross-group tie-break ordering remains later Gate 3 work.
Legacy simulation-run late-replacement and pre-draw-withdrawal UI/authoring endpoint
retirement are complete. Their historical sidecar action logs remain read-only;
broader retirement of unrelated legacy simulation paths remains separate migration
work.

Canonical WC/RWC resolution now has the chronology foundation required to become a
first-class Run decision. `TournamentWildCardAuthority v2` freezes exact FAX week
plus global Simulation Slot ordinal while preserving historical v1 fingerprints.
Entry, WC and match writers mutually exclude one another at the same global position;
WC decisions cannot overtake incomplete prior slots; week schedule generation reserves
completed WC ordinals; and Saved Revision collision/contiguity validation includes
chronology-aware WC authorities. Definitive WC/RWC assignment evidence created from
v2 must reuse the exact source position.

The immediate follow-up is the canonical **transaction-owning WC Admin command**:
derive current Position server-side, resolve WC/RWC authority at that exact global
slot, atomically persist all definitive WC/RWC assignments and first Tour-entry
triggers, expose the review/commit flow in Planned Event Admin, then retire the legacy
simulation-run wildcard mutation endpoint while keeping historical action data
read-only. This step must not invent Final Commitment / Week Tournament Lock policy.

The canonical **transaction-owning WC Admin boundary** is now implemented on top of
the global-slot chronology. Since Master still defers automatic WC eligibility and RWC
list construction/order, the current pre-alpha policy is explicitly identified as an
Admin review rather than an engine eligibility algorithm. The review freezes operator,
reason, terminal Entry Field, exact FAX week/global slot, original WC nominations,
ordered RWC identities and unavailable identities in
`TournamentWildCardAuthority v3`; historical v1/v2 fingerprints stay stable.

Preview is non-mutating. Commit CAS-checks the reviewed proposal and Branch/world
position under one immediate transaction, persists canonical WC resolution, derives
all definitive active WC/RWC assignments, and records first Tour-entry triggers through
the shared branch-owned trigger store. Planned Event uses this active Run/Branch flow.
Legacy simulation-run wildcard state/candidate/mutation endpoints are retired with
`410 Gone`, while historical wildcard action logs remain read-only.

This closes the legacy WC-authoring migration without deciding the still-open Master
questions. A later policy slice may replace the explicit Admin review with a canonical
automatic eligibility/order authority only after those rules are specified. Final
Commitment / Week Tournament Lock timing is likewise still not invented here.

### Whole-season continuity: explicit empty weeks

Implemented a narrow Gate 5 unblocker for Official Run whole-season acceptance:
an event-free RankingWeek can now be completed with explicit zero-match sporting
evidence instead of manual DB repair. The command hashes the existing season
Calendar authority, fails closed if any Calendar Event or simulation/tournament
work owns the week, and then reuses the normal Saved Revision + Week Transition
path. See `docs/AUTHORITATIVE_EMPTY_WEEK_COMPLETION_V1.md`.


### Official Run whole-season acceptance

Master §31.3's primary pre-alpha acceptance flow now has a direct canonical backend
acceptance test. It starts from the production Admin Initial World boundary, prepares
the derived Week-1 Official Ranking, executes a real Week-1 tournament through the
authoritative Simulation Slot / Match Engine path, advances every remaining
RankingWeek with explicit Calendar-proven empty-week evidence, Saves and reopens the
Run mid-season, completes Week 61, then executes the real ordinary Season Transition
into next Season Week 1.

The long path deliberately keeps ordinary weekly consequences in the clean Working
Draft and checkpoints only at acceptance Save boundaries. This matches the Master
Working Draft / Saved Revision contract and avoids inventing a requirement to create a
Saved Revision after every week. The mid-season restart compares the exact post-Save
Position identity, including Saved Revision head and Working Draft base/version.

The acceptance exposed and fixed one real HTTP round-trip defect: the Season
Transition configuration preview serializes immutable tuple fields as JSON arrays,
while the advance endpoint had been validating the decoded Python dict in strict
Python mode. The advance endpoint now validates the submitted payload in Pydantic JSON
mode, so the exact configuration returned by preview can be posted back unchanged.

This closes the missing end-to-end continuity proof for the minimum Official Run
season path. It does not resolve PAQ-006 scale/performance targets, require every week
to contain a tournament, or decide any still-open Entry/WC/lock/reconstruction product
policy.


## Pre-alpha validation cadence

Ordinary feature PRs use focused validation: run the tests that exercise the changed
slice and keep unrelated long regressions out of automatic PR feedback. Those tests are
retained rather than deleted. A change is not considered merge-ready when a required
focused check is red.

At an explicit internal release/checkpoint, switch to the release gate: run the complete
regression suite plus the mandatory Master §31.3 acceptance flows and any checkpoint
smoke/performance checks. See `docs/PRE_ALPHA_TEST_POLICY.md`.


### PAQ-006 measurement foundation

Before choosing a reference-scale performance target, capture reproducible evidence.
`scripts/profile_pre_alpha_acceptance.py` runs the two mandatory Master §31.3 flows
and emits a versioned JSON report containing wall time and cross-platform Python heap
peak. It does not invent a threshold and does not close PAQ-006. The profiler belongs
to release/checkpoint validation rather than ordinary PR CI.


### Recovery integrity: revision-bound Season Closure

Saved Revision restore must preserve immutable historical closure evidence without
copying stale revision identity. When a restored target contains `season_closure`,
validate the historical component and rebind only its Closure Marker to the newly
created restore revision ID. Keep the Season Summary unchanged and verify the new
Saved Revision hash. This is a technical recovery invariant, not a new sporting rule.


### Recovery integrity: uncaptured simulation authority guard

Saved Revision restore must fail closed whenever live canonical tournament/simulation
authority exists that is not represented by the current Saved Revision simulation
component. The guard includes WC authority, Draw Process authority and Draw revision
history as well as the older slot/draw tables, preventing future tournament state from
surviving a restore to an older snapshot.


### Recovery integrity: completed-week sporting context coverage

The uncaptured-sporting restore guard covers both player sporting week snapshots and
completed-week sporting contexts. A context-only live row is still sporting history and
must block restore when the current Saved Revision does not capture the sporting
component.


### Central recovery ownership registry

Saved Revision restore coverage is now maintained as one explicit component-to-live-
table registry plus a separate transient-blocker registry. New Run/Branch persistence
must declare recovery ownership instead of relying on ad-hoc restore checks.

Current hardened cases include Season Closing Ranking under ranking recovery,
WC/Draw Process/Draw Revision under simulation recovery, completed-week sporting
contexts under sporting recovery, and the transient standalone authoring workspace as
a restore blocker rather than Saved Revision content. This is a Gate 4/5 save-load
integrity mechanism and does not define new sporting policy.


### Restore review preflight

Saved Revision recovery now has an explicit read-only preflight before confirm. Admin
history UI must use server-derived blocker diagnostics and expected head/draft/Viewer
identities rather than reproduce recovery rules in the client. Confirm remains the sole
mutation boundary and repeats all checks under the writer lock. This strengthens the
Gate 4/5 save-load/recovery path without changing product policy.


### Saved Revision history pagination + comparison

The section 11 history follow-up now includes stable newest-to-older cursor pagination
and a generic read-only comparison for two reachable Saved Revisions. Comparison
surfaces Run/Branch metadata changes and component-level added/removed/changed/unchanged
status with deterministic fingerprints. No sporting semantics are inferred by the diff.

This closes the explicit pagination/general-comparison foundation item; complete
sporting-world restore remains a separate follow-up.


### Sporting-world recovery: Run prospect source fidelity

The shared Run prospect catalog now has versioned Saved Revision reference snapshots and
an explicit Save boundary. Historical Branch restore validates this Run-scoped source
rather than mutating it, so one Branch cannot rewind prospect metadata used by another
Branch. Current and target source drift fails closed before restore mutation.

This advances the section 11 complete sporting-world recovery follow-up. Remaining work
still includes broader world-state/identity recovery and ranking-bearing fork identity
remapping; this slice does not promote unresolved Tour-entry/product policy.


### Ranking identity remapping: bootstrap fork slice

Ranking-bearing Branch creation now supports the first remappable subset instead of
blanket rejection. A source-free Week-1 bootstrap ranking is rebuilt for the target
Branch identity, installed atomically, and anchored by a target-owned materialized
fork-root Saved Revision whose parent is the selected source revision.

The target can then diverge with its own later ranking Saves while the source history
remains unchanged. Full ranking-bearing fork support remains open for multi-week
histories, tournament/zero/transition authorities, InitialWorld-linked state and
Season Closing evidence; each requires an explicit identity-remap adapter rather than
generic payload rewriting.


### Ranking identity remapping: source-free multi-week chain

The ranking-bearing fork adapter now reconstructs a complete consecutive source-free
Week 1..N Official Ranking chain, not only its bootstrap root. Every stored command and
manifest is revalidated, Branch-bound request/snapshot fingerprints are recalculated,
and the target materialized fork root owns the resulting independent ranking lineage.

Remaining adapters are the genuinely source-bearing cases: tournament/correction result
history, disciplinary-zero history, transition/publication authorities, InitialWorld-
linked ranking and Season Closing evidence.


### Ranking identity remapping: disciplinary-zero histories

Result-free ranking-bearing forks now remap complete stored disciplinary-zero version
chains alongside ranking commands and snapshots. Branch-bound zero identities,
successor fingerprints, command fingerprints and resolved manifest inputs are
reconstructed for the target Branch.

The next substantial remaining source-bearing adapter is tournament/correction result
history; transition/publication authorities, InitialWorld-linked state and Season
Closing evidence remain separate follow-ups.


### Ranking identity remapping: result-version correction histories

Ranking-bearing forks now remap immutable Branch-owned `RankingResultVersion` chains,
including later corrections and their predecessor fingerprints. The ranking manifests
and stored correction commands are deterministically rebuilt for the target Branch.

The remaining tournament layer is `OwnedTournamentRankingSource` plus canonical
Tournament Result / Point Award / Prize Money authority fingerprints. That authority
bundle remains fail-closed until its dedicated adapter is implemented.


### Ranking identity remapping: canonical tournament authorities

Branch-fork remapping now includes canonical `OwnedTournamentRankingSource` v4/v5
authority bundles. Result, Point Award and optional Prize Money authorities are
rebound to the target Branch and all dependent fingerprints are recalculated before
ranking result versions are re-derived. Trusted fork installation accepts these
remapped tournament sources into otherwise empty target ranking storage.

Legacy v1-v3 tournament sources, final Closing-only v6 sources, and
transition/publication/Season Closing state remain guarded follow-ups rather than
inferred behavior.


### Ranking identity remapping: tournament correction chains

Later `RankingResultVersion` corrections over canonical tournament-backed results are
now supported by Branch forks. The source predecessor chain is verified exactly, then
each correction is rebuilt against the corresponding target-Branch predecessor
fingerprint. Broken or detached correction history remains fail-closed.


### Ranking identity remapping: transition authority identity foundation

A dedicated adapter now rebuilds `RankingTransitionAuthority` records for target
Branch/Saved-Revision identity while preserving frozen roster, policy, provenance and
audit evidence. Source scope and target-week ordering are validated and source
fingerprints map deterministically to the rebuilt target authorities.

This is the identity foundation only. Full transition-bearing Branch forks remain
guarded until materialized fork-root Saved Revision identity, weekly command authority
references, and authoritative publication/world state are rebound together in one
atomic fork path.


### Ranking identity remapping: transition-backed weekly commands

Transition-bearing ranking preparation history now forks across Branch identity using
the actual target materialized Saved Revision id. `RankingTransitionAuthority` records
are rebound to the target fork root, stored audited weekly ranking commands are rebound
to the resulting target authority fingerprints, and the complete request/snapshot
lineage is recalculated before trusted installation.

This closes the transition-authority + ranking-command identity layer. Remaining
authority work is the published authoritative world: Official Ranking publications,
world head, transition receipts/events, Tournament Ranking Snapshot authorities and
Season Closing archives.


### Ranking identity remapping: Official publications and world head

Official Ranking publication rows and the authoritative world ranking head can now be
forked together with ranking history. Source publication payloads are verified against
the frozen source candidate lineage, then rebuilt from target Branch ranking snapshots;
the world head follows the target publication fingerprint at the same ordinal.

Remaining authoritative transition work is intentionally narrower: Week/Season
Transition receipts and World Events require lifecycle/sporting and Season Closing
identity remapping before they can be preserved without fabricating evidence.


### Branch identity remapping: player lifecycle history

The complete `player_lifecycle` Saved Revision chain now forks with a ranking-bearing
materialized Branch. Snapshots are target-scoped, predecessor fingerprints are rebuilt,
and the target DB state and materialized Saved Revision contain the same remapped
lifecycle history atomically.

Next: remap player sporting state together with its completed-week source evidence,
then use the resulting lifecycle/sporting fingerprint maps to preserve Week Transition
receipts and World Events.


### Branch identity remapping: player sporting v1 history

Player sporting Saved Revision history now forks safely for v1 completed-week contexts.
Owned tournament source fingerprints are mapped to their target Branch equivalents,
completed-week context fingerprints are rebuilt, and the sporting predecessor/context
chain is rebuilt and installed atomically with lifecycle/ranking fork state.

Remaining sporting identity work is specifically v2 Simulation Slot match/effect
evidence. Once those authorities are remapped, Week Transition receipt/event
fingerprints can be rebuilt from target ranking + lifecycle + sporting histories.


### Branch identity remapping: sporting v2 evidence contract

The sporting remapper now has the complete target-side contract required by
Simulation Slot identity remapping: result-source, terminal-checkpoint and match-effect
fingerprint maps. This removes sporting-chain ambiguity from the remaining work.

Next: make the Simulation Slot Saved Revision adapter rebuild its branch-bound plans,
protected match inputs, effects and terminal checkpoints and emit those maps. After that
the same fork path can preserve v2 sporting state and Week Transition receipt/event
evidence.


### Branch identity remapping: Simulation Slot sporting identity seam

Simulation Slot sporting identity now has a dedicated fail-closed adapter for match
effects and sporting checkpoints. The remaining full-ledger adapter should process
history in canonical week/slot order and emit source->target maps for protected match
inputs, result fingerprints, match effects and terminal checkpoints.

This ordered seam resolves the dependency cycle with sporting v2: each target week's
opening sporting fingerprint is known before that week's Slot ledger is rebuilt; the
rebuilt ledger then supplies the evidence needed to derive the following sporting
snapshot.


### Branch identity remapping: completed Simulation Slot core ledger

Completed `slots + groups` Saved Revision history can now be rebuilt deterministically
for a target Branch. Slot starts are recomputed from target Branch/predecessor identity;
competitive protected inputs, result fingerprints, match effects and terminal
checkpoints are then rebuilt in canonical order.

The adapter emits the full fingerprint maps needed by sporting v2. Remaining Simulation
Slot work is now the auxiliary authority tree (simulation commands/schedules, adopted
tournament authority, entry field, WC/draw input/draw/revision/process authorities) and
then wiring this completed core directly into materialized Branch-fork installation.


### Materialized Branch fork: coupled sporting v2 + Slot core

The materialized fork transaction now consumes the completed Slot-core fingerprint maps
directly while rebuilding sporting v2 week by week, then installs both target components
atomically. This removes the previous circular dependency between later-week sporting
snapshots and completed Slot evidence.

Remaining Simulation Slot fork work is the auxiliary authority tree: simulation
commands/schedules, adopted tournament authority, entry-field/WC/draw input/draw
revision/process identities, plus walkover-group remapping.


### Branch identity remapping: schedule + adopted tournament authority

The auxiliary Simulation Slot fork path now includes Week Simulation Schedule identity
and Adopted Tournament Authority identity when the adopted evidence has no Draw
dependency. Both are rebuilt into the target component and installed through the same
materialized fork transaction as sporting + Slot core.

Next: remap the Draw/Entry Field/Wild Card authority chain so canonical adopted
tournament authority v6 can be rebuilt too. Simulation command receipts remain a
separate schema-by-schema follow-up.


### Branch identity remapping: Tournament Ranking Snapshot authority

Tournament Ranking Snapshot authority is now part of the supported ranking-bearing
Branch-fork state. It is rebound to the exact target Official Ranking publication at the
same week rather than copying the source snapshot.

Next dependency chain:
Tournament Ranking Snapshot -> Entry Field -> Wild Card -> Draw Input -> Draw ->
Draw Revision / Draw Process -> canonical Adopted Tournament Authority v6.


### Branch identity remapping: pre-draw authority chain

The supported materialized-fork chain now reaches:
Tournament Ranking Snapshot -> Entry Field -> Wild Card -> Draw Input.

Each layer is replayed from its frozen authoritative inputs and bound to the immediately
preceding target authority. Entry applications are also rebound to the target Branch so
their aggregate fingerprint is not reused from source identity.

Next: rebuild Tournament Draw Authority from target Draw Input, then Draw Process and
Draw Revision history, and finally allow canonical Adopted Tournament Authority v6.


### Draw-backed adopted tournament authority fork remap

The materialized Branch-fork path now consumes the canonical source→target Tournament Draw fingerprint map when rebuilding Adopted Tournament Authority. Canonical v6 adopted bundles are re-encoded with target Draw fingerprints and receive new target Branch authority fingerprints instead of retaining source Draw identity. Legacy no-Draw adopted bundles remain compatible, while any unmapped Draw reference still fails closed.

The next downstream recovery slice is Draw Revision replay, including embedded replacement-cutoff and repair-specific LL/WC/replacement-source authorities before revised Draw fingerprints can be considered fully fork-safe.


### Basic Draw Revision Branch replay

Branch-fork reconstruction now covers ordinary phase withdrawals across full redraw, seed cascade and Draw Freeze. Replacement-cutoff evidence is replayed only after target match-result fingerprints exist, and each revision rebuilds its successor field/input/draw plus request and revision identities under the target Branch. Revised successor Draw fingerprints are fed back into the Draw mapping used by canonical adopted tournament authority.

Remaining revision work is repair-specific: post-draw WC/RWC repair, Lucky Loser vacancy/fill, frozen ordinary fallback and source-bound pre-Q promotion.


### Specialized Draw Revision Branch replay

The Branch-fork revision path now covers the full currently modeled Draw Revision family set in one chronological source→target lineage: ordinary full-redraw/seed-cascade/Draw-Freeze withdrawal plus frozen RWC repair, Lucky Loser vacancy/fill, frozen ordinary fallback and source-bound pre-Q promotion.

Specialized frozen evidence is retargeted through one accumulated fingerprint graph and domain-validated before canonical revision builders recreate target Draw state. Revised Draw/Input/Field/revision identities are then added back into the graph for later revisions and Adopted Tournament Authority v6. Follow-up work should emphasize mixed-chain regression coverage, restore/retry equivalence and any future Master-defined revision kinds rather than splitting the present authority families again.


### Draw Revision restore / retry identity hardening

Saved Revision recovery now verifies Draw Revision payload scope and reconstructs canonical request identity for the complete modeled repair-kind set during history replay. This closes the gap between immutable revision payload identity and command-request identity.

PR-critical coverage exercises a mixed revision chain across capture -> additional live mutation -> restore -> exact command retry, plus fail-closed payload-scope and request-fingerprint corruption. Follow-up hardening can move to longer specialized mixed chains and materialized fork -> restore equivalence rather than basic retry semantics.


### Materialized fork -> restore equivalence

The recovery path now verifies the complete installed Simulation Slot component after restore/materialized-fork installation by recapturing live state and comparing its canonical fingerprint to the requested target component. This upgrades component installation from per-store validation to whole-component exactness.

PR-critical coverage joins the Branch fork and restore work into one specialized-history scenario: frozen RWC repair -> target materialization -> later target RWC repair -> restore -> exact original RWC retry. Next hardening should expand this equivalence test across Lucky Loser and source-bound pre-Q repair families and then move back toward pre-alpha feature delivery.


### Strict Lucky Loser / pre-Q fork evidence

Fork replay no longer permits Lucky Loser or replacement-source nested fingerprints to survive merely because a generic recursive retarget did not recognize them. Branch-owned Draw/Input/Ranking/WC/result/Q-bracket evidence now requires exact source->target mappings.

LL v2 auto-BYE evidence is rebuilt before LL-order terminal fingerprints so the target order owns the target auto-BYE evidence hash rather than a stale source hash. Source-bound pre-Q promotion is covered through Saved Revision capture, target Branch remap/materialization and idempotent retry. Remaining recovery work should emphasize broader real-match LL vacancy/fill acceptance and then return to pre-alpha product delivery.


### Real Qualification-receipt Lucky Loser recovery acceptance

The fork/restore safety net now exercises Lucky Loser with real canonical Qualification receipts from the authoritative Simulation Slot executor: Q semifinals -> Q terminal -> LL vacancy -> LL fill -> Branch remap/materialization -> second target LL vacancy/fill -> restore -> idempotent retry.

This closes the main recovery-evidence gap left after strict LL/pre-Q fingerprint remapping. The same slice also canonicalizes remapped Slot/Group row ordering to match Saved Revision capture before aggregate fingerprinting; fork identity no longer depends on slot-ID lexical order accidentally matching slot chronology. Follow-up work should move back toward remaining pre-alpha product delivery unless a new real-world fork/recovery defect appears.


- **Implemented Admin Match Day editing:** the canonical V2 auto-proposal can now be manually redistributed across Match Days and reordered before adoption through a server-validated Review → Commit workflow. Manual edits cannot change frozen event/phase/round/group identity, cannot consume Entry/WC-reserved global ordinals, and cannot bypass feeder/Q-before-Main/player-per-day hard constraints. This also provides a safe pre-alpha route for manually spanning one round across multiple days without inventing a numeric daily-capacity rule.
- **Fair-rest scheduler depth started:** automatic V2 proposals implement the bounded Master §13.4 feeder-finish ordering rule: a dependent path whose previous match finished later in stored Match Day order is kept later. Equal candidates now use a stable Run/Branch/Week-scoped hash tie-break instead of bracket position/seed-derived structural order, and the resulting order is frozen by schedule adoption. Remaining scheduler depth is minimum-rest maximization, recovery-gap balancing, fuller Q/LL protection, previous-week carryover and later minimal-range preservation/reflow. Numeric daily capacity, precise times, courts and travel/acclimatization mathematics remain open/deferred as specified by Master.


## Canonical Viewer Official Ranking read model

The first historically faithful Viewer ranking bridge now reads the selected Viewer Branch's exact current published Official Ranking from `AuthoritativeWorldState` + `PublishedOfficialRanking`. It validates stored scope/fingerprint identity and deliberately ignores persisted future publications until the public world head reaches them. The top-level MSA Rankings page renders this current canonical table. Next Viewer ranking work is the historical Branch-owned publication timeline/detail path and then downstream Entry/seeding/Finals public integration; legacy snapshot pages remain compatibility history meanwhile.


### Viewer ranking legacy-detachment follow-up

Current and historical MSA Official Ranking reads now share one canonical selected-Viewer-Branch authority: current head, publication timeline and exact historical detail are all bounded by the public `AuthoritativeWorldState`. The legacy SimulationRun ranking snapshot store is no longer the authority behind the top-level or run-scoped Viewer ranking routes. Race and broader downstream public consumers (Entry/seeding/Finals/statistics) remain separate migrations.


### Viewer Entry downstream integration

The first post-ranking downstream Viewer bridge now consumes the selected Viewer Branch's canonical Tournament Entry Field on Tournament Detail. The public projection exposes sporting field composition only and does not leak Admin provenance/fingerprint internals. Tournament event/result history, WC/draw public presentation, Race and Finals remain separate migrations; legacy data is not promoted merely to make those surfaces appear canonical.


### Viewer Draw downstream integration

The Viewer tournament downstream chain now reaches canonical Entry Field → effective Draw on the selected Viewer Branch. The Draw projection is sporting-only and revision-aware; it does not expose authority fingerprints, command provenance or generation internals. Public WC-specific presentation, canonical tournament result/history migration, Race and Finals remain separate future slices rather than being inferred from legacy surfaces.


### Viewer Wild Card downstream integration

The selected Viewer Branch now supplies a definitive public WC/RWC projection alongside canonical Entry Field and effective Draw. Only persisted definitive assignments are public; nomination/review state and first-entry/provenance internals stay Admin-side. Canonical tournament results/history, Race and Finals remain separate downstream migrations.
