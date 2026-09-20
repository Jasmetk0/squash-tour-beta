# Squash Engine roadmap

This is a milestone summary, not a second product constitution. [`SQUASH_ENGINE_MASTER_VISION.md`](SQUASH_ENGINE_MASTER_VISION.md) plus newer explicit decisions take precedence over `PROJECT_CONSTITUTION_TECHNICAL_PLAN.md`; `docs/ENGINE_UX_SPEC.md` provides subordinate migration guidance. Planned behavior must not be described as implemented unless verified in the repository.

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
General draws, Qualification, WC/LL, Entries, AI-authored/general scheduling, and health remain Gate 3 work.
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
tournament authority v5 includes the exact Draw Authority fingerprint. Multi-Q
sections, dynamic qualifier-vs-BYE auto-advance, WC/LL and post-draw repair still
fail closed rather than borrowing legacy DrawPackage policy.

Qualification promotion plus unambiguous one-player BYEs now execute through the
authoritative tournament/ranking bridge. Wild-card provenance from #738 remains a
useful primitive. The #739/#740 pre-/post-draw replacement shortcut producers are
now fail-closed after the post-merge canon audit; already persisted packages remain
historically readable. Canonical pre-draw field rebalance now has a Run/Branch application command over
the frozen Tournament Ranking Snapshot and Entry/Application payload, plus a
separate canonical Run/Branch Admin HTTP boundary for field inspection and guarded
withdrawal mutation. The older simulation-run Admin endpoint remains legacy rather
than being silently reinterpreted. Later replacement work must
still proceed through Qualification/Main Draw repair phases, RWC/WC handling, Lucky
Loser priority and the per-player first-real-match replacement cutoff.

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
- **Implemented foundation:** Run simulation freezes persisted Entry/Draw/Match evidence as a versioned topology DAG and validates explicit global-slot coverage for complete binary Main Draws; production eight-player Main Draws repeat across three authoritative weeks while retaining the historical four-player reader. Indexed qualifier mappings and unambiguous one-player Qualification BYEs execute and ingest into ranking authority. Entry decisions for overlapping events are generated transactionally from one shared snapshot, but unresolved competing acceptances remain provisional and must fail closed before play until Final Commitment / Week Tournament Lock authority exists. WC and alternate-replacement provenance primitives exist. Canonical pre-draw field rebalance is implemented as an append-only Run/Branch command and now has a branch-scoped Admin HTTP boundary; legacy UI/endpoint retirement, RWC/WC repair, post-draw repair phases, LL ordering and the replacement cutoff remain Gate 3 work.

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
legacy branch wrapper. Higher-level Next Round / Next Week / Next Tournament / Full
Season controls remain clearly marked compatibility actions until equivalent
canonical orchestration is implemented.

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

Unbridged target-week prospects still block Week Transition rather than being
silently omitted, but the blocker is now inspectable through a canonical read-only
Run/Branch boundary. The engine derives the target calendar/season week from the
current Official Ranking head, selects the exact Run-scoped blocking prospect rows,
surfaces cohort/profile versions and explicit placeholder status for attributes,
development, potential and traits, and fingerprints that blocking set. The Admin
Simulation page renders the inspection only when `prospect_bridge_missing` is
present. This is intentionally **not** the prospect/Tour-entry bridge: the current
technical contracts still leave Tour-entry activation and canonical sporting-profile
creation open, so no mutation is exposed until those rules are decided/implemented.

Week 61 now also has a canonical **read-only Season Transition preflight**. It
freezes the current authoritative Position, Saved Revision head and branch-state
blockers, distinguishes those from still-missing engine writers, and projects only
the Master-defined next boundary: next Season Week 1, or final Run closure after
season 2049/50. The Admin Simulation page now renders that preflight at Week 61,
shows state blockers and implementation gaps separately, and hides the ordinary Week
Transition review/confirm controls at that boundary. The preflight never calls the
legacy rollover path and always reports execution unavailable in this slice; no
Season Transition mutation is claimed.

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
future caller-owned Season transaction. Run prospects due in target Week 1 remain
explicitly fail-closed rather than being omitted. The incoming Week-1 Official
Ranking can now be resolved read-only and staged through the canonical
RankingWeekCommand from the incoming policy, exact staged lifecycle roster,
disciplinary history and Week-61 owned tournament sources. Staging does not publish
the Ranking or move the world clock. Remaining ordinary season-0–48 work is the
prospect/Tour-entry + sporting-profile bridge plus the public-state/atomic rollover
writer that persists and publishes all selected staging outputs together.

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
Auto-BYE-only Qualification terminals and group-Qualification LL ordering remain
later Gate 3 work. Legacy simulation-run UI/endpoint retirement remains separate
Gate 3 work.