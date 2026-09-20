# Current implementation and next action

Re-audited 18 September 2026 from merged PR #757 at
`0b3441909f89983e97e12d342c0835db63fb7654`, plus the current bounded
canonical Tournament Entry Field Admin HTTP slice. The audit compares merged code against the
canonical Master Vision instead of treating PR descriptions or Fast CI as product
authority.

This branch adds the first Run/Branch/Week/global-slot-owned competitive match execution path: frozen same-slot inputs, complete Match Engine replay evidence, exactly-once Form/Sharpness/Fatigue effects, intra-week checkpoints, later-slot causal consumption, Saved Revision capture/restore, and terminal-state handoff to Weekly Development. See `docs/AUTHORITATIVE_SIMULATION_SLOT_MATCH_EFFECTS_V1.md`.

PR #728 review hardening preserves owned InitialWorld style/profile truth, carries Form/Sharpness/Fatigue as distinct match inputs, makes any planned slot authoritative even before its first group commit, enforces feeder topology/global ordinals, and semantically revalidates replay and Saved Revision slot chains.

The follow-up compatibility correction assigns Sharpness-aware matches to `match_input_snapshot.v10` / `match_engine_v10`; v1-v9 hash payloads continue to omit the later Sharpness field and retain their historical identities.

The tournament bridge freezes a v4 Run/Branch/week authority bundle and consumes a canonical executable DAG built from persisted match IDs, direct slots and `winner_to_match_id` evidence. Production-backed eight-player/seven-match Main Draws repeat across three completed authoritative weeks with authoritative schedules, Week Transition and replay. A PR-critical acceptance proves a Run-owned sixteen-player/fifteen-match complete-binary Main Draw from published Official Ranking → Tournament Ranking Snapshot → Entry Field → Draw Input → Draw Authority → four topological Simulation Slots → canonical tournament close, producing `OwnedTournamentRankingSource v5` with 16 player results and all 15 canonical match results. A follow-up acceptance now covers a non-power-of-two entrant field: 13 entrants retain a fixed 16-position canonical bracket, three explicit BYEs and only 12 simulated competitive matches across derived 5→4→2→1 Simulation Slots, while the completed canonical result still retains all 15 bracket-node results including the BYEs. Canonical point awards preserve actual finishing stage separately from the Master §15.4 first-real-match ranking unlock via an optional `point_stage`; W/O advancement remains the §16.3 exception. Players who participate in both Qualification and Main now receive the Master §18.1 additive Q + Main ranking value in Point Award v3, with the two draw unlocks evaluated independently. Canonical Main capacity is derived automatically from the requested entrant count at Tournament Edition creation by rounding to the next power-of-two capacity and recording the remainder as explicit BYEs; seed count remains Master-derived rather than manually authored. The current supported classic-bracket ceiling is 128 positions: 65–128 entrants remain supported (and advisory-warned as an exceptional large Main field), while 129+ entrants fail closed instead of silently deriving a 256-position bracket. A non-authoritative pre-alpha diagnostic layer emits stable Admin warnings for every odd Main entrant count, for opening rounds where more than half of matches contain a BYE, and for Main fields above 64 entrants. These diagnostics are exposed through canonical capacity/draw helpers and the existing DrawPackage validation-warning surface, but are excluded from persisted sporting authority and Draw fingerprints; seed-band/section asymmetry remains a later refinement. The driver can now derive a deterministic, read-only topological schedule proposal directly from the canonical executable DAG: every group is placed in the earliest global Simulation Slot strictly after all feeder groups, independent groups at the same depth share one slot, and proposal identity is registry-order independent. The proposal is not persisted until an explicit guarded adoption command is used. A dedicated atomic proposal-adoption path now rebuilds the proposal under `BEGIN IMMEDIATE`, binds it to the expected Ranking Week plus proposal/position fingerprints, and only then persists the immutable Week Simulation Schedule. The client no longer needs to round-trip the full schedule payload to adopt the engine-generated proposal; exact retries remain idempotent. Qualification promotion and unambiguous one-player BYE evidence execute through the same closure/ranking path. PRs #738–#740 also added persisted Wild Card and withdrawal/replacement provenance primitives. A post-merge Master Vision audit found that those primitives are not the completed repair workflow: overlapping entries may remain provisional until commitment authority; pre-draw withdrawals must rebalance Main/Qualification field cuts from the Tournament Ranking Snapshot; and post-draw repair must honor redraw/cascade/freeze phases, Lucky Loser priority and the first-real-match replacement cutoff. This correction branch removes the #737 automatic preferred-tournament choice and fails closed before play when overlapping commitments remain unresolved. Historical v1-v3 four-player readers remain compatible. Legacy `start_day`, list order and round-name text are never chronology authority.

The eight-player acceptance directly exercises the Saved Revision simulation-state
component capture and process reopen, while Week Transition plus post-transition
Replay remains production-covered by the existing multi-event HTTP acceptance.

This file is an evidence/index snapshot, not product authority.
Always verify the current remote head before acting. Product rules and decision
statuses live in [Master Vision](SQUASH_ENGINE_MASTER_VISION.md); the development
protocol is chapter 36. PR #757 is the latest merged implementation in this audit base.

## What exists, and where integration stops

| Area | Evidence in audited code | Remaining boundary |
|---|---|---|
| Run foundation | `application/run_container_creation_service.py`, `run_working_draft_service.py`, `run_saved_revision_*`, DB revision models | New Run roots/revisions coexist with legacy simulation identities; full sporting state is not covered by every save/restore path |
| Branch isolation/recovery | `infrastructure/db/repositories.py` validates ancestry, receipts and checkpoints; rejects ranking-bearing forks | Ranking identity remapping and complete sporting-world recovery remain |
| Packages/players | World package, owned InitialWorld, lifecycle, `player_sporting_week_states`, and slot checkpoints | Canonical 57×0–200 sporting history and match-derived Form/Sharpness/Fatigue exist for the narrow slot slice; health and prospects remain open |
| Tournament flow | Tournament Ranking Snapshot → Entry Field → Draw Input → Run-owned Draw → canonical Match topology/package → Tournament Result Authority; current branch adds Run-owned Point Award Authority and direct ranking-history materialization | Canonical events no longer use legacy DrawPackage, file-backed MatchPackage, SeasonEventResultsService extraction or SeasonPointAwardsService award generation as sporting/ranking producers. OwnedTournamentRankingSource v3 persists canonical result + point authorities and next-week ranking ingestion can run without a legacy award service. Legacy-shaped result/award DTOs remain compatibility children only. Multi-Q, dynamic Q-vs-BYE, WC/LL and post-draw repair remain fail-closed boundaries. |
| Match engine | `domain/matches/match_engine.py`, immutable inputs/replay, `simulation_slots.py`, and Run/Branch slot persistence | Narrow four-player scheduling and later-slot sporting causality exist; general global scheduling, native 57-attribute Rally Setup, and finished realism remain open |
| Official ranking | `domain/rankings/official.py`, `application/ranking_week_command.py`, `infrastructure/db/authoritative_week_transition.py` | The supported Week 1→2 boundary now publishes an immutable Official Ranking and advances the scoped world clock atomically; Viewer/history consumers and broader lifecycle resolution remain |
| Ranking Admin | `admin_ranking_candidates.py`, `RankingPreparationPanel.tsx`, `RankingResultCorrections.tsx` | Preview/confirm, manual input review, zeros, corrections and explicit supported tournament binding; minimum API flow exists but no broader tournament picker redesign |
| Ranking Save | `saved_revision_rankings.py`, `ranking_revision_state.py`, `ranking_state_restore.py` | Owned source packages, candidates, inputs and audit survive explicit Save/reload/restore; still not full sporting-world recovery |
| Week execution | `infrastructure/db/authoritative_week_transition.py` owns one `BEGIN IMMEDIATE`; owned complete tournament result manifests can resolve completed-match counts | Sporting development then between-week recovery, prospect-aware lifecycle, ranking/publication/event/receipt share the transaction; a missing/empty authoritative sporting context fails closed for the simulation-ready roster, while broader match-state updates and full prospect sporting-profile materialization remain outside it |
| Season rollover | `rollover_service.py`, `run_bootstrap_service.py` use persisted MVP rollover/legacy simulation runs | Not the Master Season Closing + new-policy Week 1 + final Run completion contract |
| Viewer/downstream | Legacy ranking/Race/Finals paths plus a canonical Viewer Next Gen read model exist | Next Gen now derives visibility from the selected Viewer Branch lifecycle and never from future pregeneration rows; broader Official ranking, entries/seeding and Finals still need historically faithful public integration |
| Other pre-alpha scope | Master 31 remains authoritative | Minimum Reconstruction, player development/AI and lifecycle must not be dropped merely because ranking work dominated recent PRs |

Paths above are relative to `src/beta_engine/` unless a `web` component or document
is named. Ranking detail: [completion checklist](docs/RANKING_COMPLETION_STATUS.md).

## Audit findings and corrections

- Post-#740 audit correction: Fast CI is only the smoke suite. The separate Full Test
  Suite is the complete repository safety net. The latest known frontend full-suite
  failure is the pre-existing Viewer route-context test boundary; backend full pytest
  passed after #736, while later full-suite runs were cancelled by subsequent merges
  or were still running during this audit.
- #737's Qualification/BYE/ranking-ingestion work remains useful. Its overlapping
  Entry resolver was product-wrong because it automatically chose one tournament
  using Entry score/Main-vs-Qualification preference. Canon permits provisional
  overlapping applications and requires later commitment/lock authority.
- #738 is treated as a Wild Card provenance primitive, not the completed WC/RWC
  workflow. #739/#740 are provenance experiments, not canonical repair authority.
  New pre-draw direct-alternate and post-draw MatchPackage replacement commands now
  fail closed; already persisted Draw/Match packages remain readable/replayable.
  Canonical pre-draw field rebalance now has a Run/Branch transaction-owned
  application command that reuses the frozen Tournament Ranking Snapshot and
  frozen Tournament Entry/Application payload. The current follow-up exposes that
  authority through a separate Run/Branch-scoped Admin HTTP boundary with field
  fingerprint inspection and optimistic mutation guards. The canonical initial Draw
  pipeline is now exposed through a separate Run/Branch Admin authority boundary:
  terminal Entry Field -> CAS-guarded Draw Input commit -> immutable initial Draw
  generation -> read-only Draw Authority payload. Main classic capacity now fails
  closed outside 2/4/8/16/32/64/128; real canonical generation is directly covered
  at every supported capacity, including 128. Planned Event Detail consumes the
  canonical field/draw surfaces, renders the existing geometry warnings, allows the
  technical deterministic draw seed to be frozen, generates the initial authority
  without client-supplied seed counts, and renders Main/Q slot tables. Planned Event
  now also consumes the immutable Draw process-window authority, requires explicit
  Main/Q window counts rather than inventing defaults, renders the effective Draw
  after append-only revisions and exposes compact revision audit history while
  preserving the initial Draw as historical truth.
  The Simulation page now exposes the existing Run/Branch-owned authoritative sporting
  driver as a separate canonical panel. It inspects immutable Week Schedule
  requirements before Position, can build/review/adopt the dependency-safe
  topological proposal, executes Next Match only against an explicitly reviewed
  eligible group, executes Next Slot without a hidden group override, and Saves only
  against the exact simulation draft fingerprint/version. Every execution command is
  CAS-guarded by the current authoritative position fingerprint plus the Branch Saved
  Revision head. When Position reaches the existing `week_ready_for_transition`
  boundary, Admin can now request a **server-derived** Week Transition preview: the
  backend freezes the current Saved Revision head, persisted Ranking Transition
  Authority and all Owned Tournament bindings into the exact canonical command.
  The UI confirms only that reviewed request. Server-side confirm guards the request
  plus the reviewed Official Ranking, lifecycle and sporting fingerprints inside the
  same `BEGIN IMMEDIATE`; any preview drift rolls the transition back before commit.
  The flow then reuses the ranking Save CAS to persist the transitioned ranking/world
  draft as a new recoverable Saved Revision. The client never authors
  tournament bindings or an authority fingerprint. The immediately preceding
  Ranking Transition Authority prerequisite is now also server-derived for ordinary
  within-season Week Transition: Admin supplies only audit provenance, while the
  backend freezes the current Saved Revision head, target-week lifecycle roster and
  predecessor Official Ranking policy, previews the exact authority fingerprint,
  confirms it under CAS, and Saves it through the same ranking revision boundary.
  Missing authority can therefore be resolved from canonical Run truth; stale
  authority and Week 61 rollover remain fail-closed. Target-week Run prospects are
  now activated exactly when their birth week opens: the transition validates the
  pregenerated Run row, adds the same stable identity to branch-owned lifecycle with
  `tour_entry_week=None`, and leaves it out of Official Ranking and sporting state.
  The existing Prospect Bridge endpoint is now only a read-only profile-readiness
  diagnostic; it fingerprints the exact target rows and placeholder
  sporting/development/potential/trait fields but reports no transition blocker.
  No Tour-entry event or fabricated 57-attribute profile is invented.
  Week 61 exposes a **read-only canonical Season Transition preflight**.
  It freezes current Position/Saved Revision evidence, separates current branch
  blockers from known missing Season Transition writers and projects the next Season
  Week 1 target (or final Run closure after 2049/50). Final 2049/50 can execute when
  its real blockers are empty; ordinary season rollover remains blocked by its
  remaining writers. Ordinary rollover now also resolves a deterministic
  `season_transition_configuration.v1`: the current Week-61 Official/sporting
  fingerprints and Saved Revision head are bound to incoming Ranking + Development
  policies and an explicit season-scoped reset catalog. Default preview inherits the
  outgoing supported policies; the Admin API can preview explicit incoming
  overrides without mutation. The reset registry is currently intentionally empty
  because there is still no authoritative branch-scoped resettable season-stat
  producer. A dedicated ordinary cross-season sporting kernel now resolves and can
  stage the next Season Week-1 sporting snapshot without advancing lifecycle or the
  public world: development plus recovery still use the outgoing Week-61 effective
  Development Policy, and only the resulting Week-1 state installs the selected
  incoming policy. The Season preflight fingerprints this exact default sporting
  candidate. The common weekly sporting path also fixes terminal-match lineage:
  target snapshots now retain the persisted weekly predecessor fingerprint, while
  terminal match state remains independently bound by CompletedWeekSportingContext.
  Ordinary cross-season lifecycle staging now advances the persisted Week-61 roster
  into next-season Week 1, including canonical calendar-week birthdays and age-based
  retirement, while preserving predecessor lineage and leaving the public world clock
  untouched. Lifecycle now explicitly supports pre-Tour identities: a player with no
  formal `tour_entry_week` remains in historical lifecycle state but is excluded from
  the Official Ranking roster until a later authoritative entry event. Target-week Run
  prospects are activated exactly when their birth week opens as pre-Tour Draft
  lifecycle identities; their placeholder profile does not enter the simulation-ready
  sporting roster and does not block Week/Season Transition. Birth-week visibility is
  not Tour entry. The Season preflight fingerprints the exact lifecycle candidate,
  including any target Week-1 Draft prospects, while sporting/ranking fingerprints
  remain scoped to their respective simulation-ready/Tour populations.
  The next-season Official Ranking is now resolvable and stageable from the same
  frozen Season configuration. The read-only candidate uses the incoming Ranking
  Policy, the exact staged Week-1 lifecycle roster, persisted disciplinary-zero
  history and all canonical Week-61 owned tournament sources whose first publication
  boundary is Week 1. The write path reuses the existing RankingWeekCommand so result
  history, input manifests and command receipts stay on the canonical ranking path.
  The staging primitive itself still does not publish or advance the world clock.
  A new ordinary atomic Season Transition writer now owns that final boundary: inside
  one caller-owned SQLite transaction it stages the Closing Ranking and Season
  Summary/Closure Marker, cross-season sporting state, lifecycle and Week-1 Official
  Ranking, then publishes Week 1, advances the authoritative world head, emits the
  season-transition World Event and captures the resulting state into a new Saved
  Revision plus audit event. Exact retries resolve from that Saved Revision/audit
  identity, and injected failures after staging or publication roll the entire
  transaction back. The writer refuses any non-empty season reset catalog until a
  real reset adapter exists. Target-week prospects no longer block ordinary rollover:
  they enter W1 lifecycle as pre-Tour Draft identities while sporting and ranking
  remain scoped to their respective simulation-ready/Tour populations.
  Ordinary Season Transition Saved Revisions use `ranking_revision_state.v7` when
  their authoritative transition state contains a `season_transition_completed`
  World Event; Week Transition receipt/event pairing stays strict and historical
  v4-v6 bundles retain their prior meaning. At Week 61 the Admin Simulation page
  renders the preflight, exposes an explicit Review → Advance flow for executable
  ordinary rollover, separates branch blockers from engine gaps and hides ordinary
  Week Transition controls. It does not reuse the legacy MVP rollover service.
  The first Season Transition write primitive is now implemented separately:
  `season_closing_ranking.v1` calculates an immutable archived ranking immediately
  after Week 61 under the outgoing Week 61 policy, and an append-only store binds it
  to the exact current Official Ranking Week 61 head. Week 61 results can therefore
  affect the closing order without any Official publication/world-clock mutation.
  Ordinary season boundaries now resolve/stage that archive directly from the
  published Week 61 head, Week 61 lifecycle roster, frozen Run-owned tournament
  sources and historical result/discipline stores inside the caller transaction.
  Canonical simulation now closes completed Week-61 tournaments for seasons 0–48
  before stopping at the season boundary: their immutable ranking sources persist
  with next Season Week 1 as first publication, the final simulation command succeeds
  idempotently, and the returned position remains Week 61 with
  `season_transition_required` rather than advancing the world clock.
  The 2049/50 edge now uses a canonical Closing-only owned tournament source v6:
  it carries a boundary ordinal after final Week 61 rather than inventing 2050/51
  Week 1, never enters Official ranking history, and feeds the final Season Closing
  Ranking directly. Closing Ranking archives participate in Saved Revision capture/restore
  through `ranking_revision_state.v6`; restore requires the exact recovered Week-61
  publication and outgoing policy before archive installation. A new immutable
  step-3 closure package now freezes a `season_summary.v1` against that Closing
  Ranking and builds a lightweight Closure Marker candidate bound to the summary,
  Closing Ranking and outgoing Official Ranking Policy fingerprint. The current
  season-scoped statistics registry is explicitly empty rather than fabricating
  zero-valued Race/counter data from legacy stores. Final Marker identity is not
  persisted early: it binds to a Saved Revision only after that revision has been
  staged inside the future atomic Season Transition transaction. A final-Run
  lifecycle kernel now also exists: canonical `working` and legacy `active`
  product-container states may transition to `completed` only when the Branch head
  is a Saved Revision carrying matching Season Closure evidence for 2049/50 Week 61.
  Exact retries are idempotent; `archived`, non-final weeks, missing closure evidence
  and non-head revisions fail closed. Final closure evidence is a Saved Revision
  component; restore may read it, while direct forking from that final closure
  revision remains blocked until branch/revision identity remapping is implemented.
  Final 2049/50 closure now has a real atomic command: a fresh final preflight can
  commit Closing Ranking → Season Summary/Closure Marker → complete Saved Revision →
  clean Working Draft base/head update → Run `completed` under one SQLite
  `BEGIN IMMEDIATE`. The revision payload already records `completed`, the Marker
  self-references that exact revision, an append-only audit event stores the request
  fingerprint, exact retries return the committed result, and injected failure after
  revision staging rolls every closure write back. No 2050/51 Week 1 or Official
  Ranking is created. Ordinary seasons 0–48 now have the atomic backend + Admin
  rollover path; the remaining content blocker is prospect activation into canonical
  player state when a target week actually contains new prospects.
  The legacy branch-simulation controls remain explicitly labeled compatibility
  actions for higher-level Next Round/Week/Tournament/Season commands; those are not
  claimed to be canonical equivalents yet.
  The legacy simulation-run endpoint/UI remain non-canonical. Post-draw repair phases, RWC/WC repair, LL
  priority and the first-real-match replacement cutoff are still required before
  those later producer paths may be re-enabled.
- #689 (including #690) and #691–720 are in the fetched ancestry; the v64 Master
  statement that #689 was open is historical. #720 feature CI #861 succeeded.
- Active authority pointers to v50/v54/v61 were stale documentation, not competing
  product decisions. The synchronization uses one stable root Master path.
  Historical version references in scoped contracts remain valid provenance.
- Preserve all AGENTS engineering safeguards; add navigation/workflow rather than
  destructively compressing product protections. Constitution remains subordinate.
- Staging documentation's original `none`-only discipline restriction was stale;
  stored/resolved zero support is documented, with no sanction bypass.
- The key architectural gap is ownership/transaction continuity between legacy
  file-based tournament simulation and Run/Branch-scoped ranking/revisions. Adding
  request scope labels to a global file would not solve it.
- Shared chat retrieval failed. This audit uses the supplied v64 file, visible
  conversation/new protocol, GitHub metadata, fetched code and targeted tests;
  it does not claim to have reread unavailable chat messages.
- No newly discovered sporting-policy conflict was decided during synchronization.
  PAQ-082, open sanction tariffs, Protected Ranking details and other open rules
  retain their existing status. The technical plan below is not a product default.

## Validation evidence

- #720 Fast CI #861: success on `c216fe64fd9983cd2346cba6ad9b4b0f1c0692ec`.
- Previous #720 handoff: 60 targeted backend, 36 frontend tests and production build
  passed. These are historical results, not new executions in this docs task.
- Current synchronization run: **41 passed in 126.38s**, using `PYTHONPATH=src`
  and `pytest -o addopts='' -q` on the following selected files:
  `test_run_container_foundation.py`, `test_saved_revision_ranking_restore.py`,
  `test_season_week_simulation_execution_service.py`, `test_rollover_orchestration.py`,
  `test_match_input_snapshot.py`, `test_ranking_preparation_preview_api.py`.
  Some legacy orchestration tests use substitutes; real HTTP/SQLite ranking
  preview/restore tests do not prove a complete week or season.
- Current source-bridge implementation run: **109 passed in 103.96s** across the
  tournament producer/ingestion, ranking API, revision capture/restore, Saved
  Revision API and simulation-service suites. The acceptance test uses the real
  four-player producer, HTTP routes and file-backed SQLite, then explicitly saves,
  reopens, restores before adoption and restores the adopted revision again.
- Pre-merge compatibility follow-up verifies historical `ranking_revision_state.v1`
  hashes against equivalent live V2 captures without rewriting either wire format;
  V1↔V2 restore, exact retry and real changed-state rejection are covered. The
  resulting Fast CI backend smoke selection passed **96 tests** locally.
- Current initial-world integration run: **98 smoke tests passed in 111.53s**. A focused real HTTP/file-backed SQLite suite passed **53 tests in 22.11s**, including production generation, independent adoption, derived preview/confirm, Save/reopen and bidirectional restore.
- Current Week Transition slice: **13 real HTTP/file-backed SQLite acceptance cases**
  cover preview rollback, six forced failure boundaries, confirm, exact retry,
  changed-request conflict, publication/clock/event cardinality, Save/reopen and
  bidirectional restore. The broader targeted ranking/revision set passed **67**
  tests. Review hardening passed **139** targeted lifecycle, sporting-context,
  ranking,
  revision, Match Engine and HTTP/SQLite tests; Fast CI backend smoke passed
  **99** tests.
  Review hardening additionally rejects Week 61 rollover, requires both reviewed
  request and ranking fingerprints at confirm, validates canonical World Events,
  and preserves historical exact retry after a later coherent world head.
- No full-suite, browser E2E, whole-season or full-Run execution in this task.
  Earlier baseline failures are not silently cleared. Docs CI validates docs only.

## Best next implementation slice

**Broaden the proven repeated sporting flow without weakening its authority.** The
narrow single-event four-player path still derives a stable Run/Branch position,
commits independent same-slot groups over one frozen snapshot, resumes partial
commands, runs the sporting-context preflight consumed by Week Transition,
materializes the dependent Final and closes exactly once into
`OwnedTournamentRankingSource`. Match-derived Form/Sharpness/Fatigue and the
tournament-to-ranking bridge are implemented, not future gaps. Multiple same-week events without an adopted schedule still fail closed before mutation, but a dependency-safe schedule can now be proposed automatically from canonical topology instead of authored manually. Ambiguous player commitments still fail closed and are never resolved by schedule ordering. Match Day timing, courts, travel/rest optimization and Final Commitment remain outside this technical proposal.

The narrow repeated-flow acceptance drives two persisted four-player weeks through
production authoritative HTTP commands and real Week Transition preview/confirm
boundaries from Week 1 to Week 3, with Save/reopen and historical Week 1 replay.
The real SQLite application regression proves that two persisted same-week events are rejected before mutation without a schedule, validates incomplete/duplicate/dependency-invalid proposals, adopts explicit chronology idempotently, shares one frozen start across each same-slot group, closes the first event while the second remains pending, and ultimately persists exactly two owned sources. This is not a general tournament scheduler.
The acceptance's compact four-player player-world setup still uses the existing
owned-state fixture writers because no production bootstrap currently emits this
synthetic narrow package; every simulation, Save, ranking-authority and Week
Transition operation after that setup uses its production HTTP/application boundary.

## Current limitations

- The explicit later-week authority adoption command remains the supported bridge after the
  new initial player/policy projection; complete later-week player lifecycle state is not yet owned. Scope, base revision and
  structural invariants are checked, but roster completeness, lifecycle truth and
  historical policy effectiveness are not yet resolved from stored world state; they
  remain audited declarations and are not inferred from legacy season files.
- Ranking-bearing branch fork remapping, Protected Ranking, abnormal tournament
  inputs and Viewer consumption of the new publication remain unsupported.
- Production branch-from-Saved-Revision still rejects ranking-bearing forks, so this
  slice does not claim a real divergent sporting-branch acceptance; no model-copy
  substitute is treated as branch evidence.
- The legacy season execution service still has no rollback and is not the Week
  Transition transaction owner.


## Current follow-up after #750

The current branch removes the legacy `season_matches.json` prerequisite for
canonical Draw events. A deterministic in-memory `SeasonEventMatchPackage`
compatibility payload is projected directly from Run-owned Draw Authority plus the
season Calendar Event, then frozen by the existing adopted tournament authority.
For this canonical payload the authoritative result builder deliberately performs no
legacy DrawPackage lookup. Legacy MatchPackage/DrawPackage files remain readers only
for historical events that do not have canonical Draw authority.


## Current follow-up after #751

Canonical Draw events now close through immutable `TournamentResultAuthority`
derived directly from completed authoritative match receipts plus Run-owned Draw
authority. New `OwnedTournamentRankingSource v2` persists that result truth.
The legacy `SeasonEventResultPackage` survives only as an in-memory compatibility
DTO for the still-legacy point/ranking adapter; canonical close no longer calls
`SeasonEventResultsService.extract_event_result()`.


## Current follow-up after #752

Canonical tournament close now derives immutable `TournamentPointAwardAuthority`
from `TournamentResultAuthority` plus the already-frozen authored point
distribution. The authority stores the full distribution snapshot and semantically
replays every award. New Point Award v3 also implements the Master §18.1 additive
Qualification + Main contract: a player who appears in both draws freezes an
independent Qualification component (successful qualifier or actual LL finishing
stage) plus the Main component, while BYE/W/O unlock rules are evaluated separately
inside each draw. Historical Point Award v1/v2 payloads keep their original
single-component fingerprint contracts. `OwnedTournamentRankingSource v3` binds
canonical result and point authorities while retaining self-consistent legacy-shaped
DTOs only for compatibility. Ranking-week ingestion materializes
`RankingResultVersion` directly from those canonical authorities and does not
require `SeasonPointAwardsService`.


## Current follow-up after #753

New canonical tournament closes persist `OwnedTournamentRankingSource v4` with
only `TournamentResultAuthority`, `TournamentPointAwardAuthority`, binding and
provenance. Legacy `SeasonEventResultPackage` / `EventPointAwardPackage` copies
are neither produced nor persisted for v4. Historical v1-v3 payloads remain
readable with their original fingerprint contracts. Ranking-week ingestion and
completed-week sporting context consume canonical authorities directly.


## Current follow-up after #754

New canonical week adoption now freezes `adopted_tournament_authority.v6` as
Calendar Event snapshot + Run-owned Draw fingerprint + frozen point authority.
It does not persist a `SeasonEventMatchPackage`. After adoption, the executable
package is deterministically replayed from that frozen evidence and no live Calendar
registry or legacy match registry is consulted for canonical events. Historical
adopted-authority v1-v5 payloads remain readable with their original fingerprint
contracts.

## Current follow-up after #756

Canonical pre-draw withdrawals now have a Run/Branch-owned application command over
the append-only Tournament Entry Field history. The command never selects an
arbitrary direct alternate and never re-reads mutable legacy Entry state: it reuses
the application payload frozen by the field plus the Edition's Tournament Ranking
Snapshot, so a Main withdrawal promotes from the ranking-ordered Qualification pool
and backfills Qualification from below the cut. Qualification-only withdrawals
backfill Qualification without changing Main. Command retry is idempotent and the
result exposes predecessor/new field fingerprints plus promotion/backfill deltas.

The existing Tournament Draw Input commitment remains the hard lock for new pre-draw
repairs. The canonical Run/Branch Admin HTTP inspection and mutation routes do not
reuse or reinterpret the older simulation-run endpoint.

The current Tournament Draw follow-up removes the single-qualifier topology limit.
For multiple qualifier spots, canonical Draw Authority v2 now materializes equal,
independent bracket Qualification sections `Q1..Qn`; each section has one terminal
winner permanently bound to the same-named Main Draw placeholder. The first global
Qualification seed layer is fixed one-per-section, later section allocation remains
deterministic from frozen Draw Input, all Q sections project into authoritative match
topology, and Tournament Result authority records every Qualification winner. A
production-backed acceptance now proves four independent two-player sections
`Q1..Q4` through authoritative Simulation Slots into one eight-player Main Draw,
canonical close and `TournamentPointAwardAuthority v3`: all 11 competitive matches
are Run-owned, all four Q winners become Main participants with additive
Qualification + Main ranking values, and the four Q losers retain their actual
Qualification-final value. Historical single-Q Draw Authority v1 remains the
compatibility representation.

New Draw Input commitments now use the Master-aligned v2 contract: classic seed
counts are derived from bracket capacity and actual player count, while explicitly
supplied counts are treated only as validation assertions. New Draw authorities use
`idealized_seed_tiers.v2`: every physical position carries its idealized slot number,
seed 1 / seed 2 are fixed to idealized 1 / 2, later seed tiers shuffle only within
their allowed idealized tier, and initial Main Draw BYEs occupy the highest idealized
slot numbers. Historical Draw Input/Draw v1 payloads replay with their stored
algorithm and fingerprint shape.

Qualification capacity may now exceed the actual Q field. The missing positions are
materialized as canonical Qualification BYEs. For multiple parallel Q sections the
BYEs follow Master §15.6 layer allocation: each full BYE layer gives one highest
remaining idealized BYE slot to every Q section, while an incomplete final layer is
distributed deterministically across Q sections from the frozen draw seed. Single-Q
BYEs use the same idealized-slot rule. Every Q section must still contain at least
one real player so that it can produce one actual qualifier.

Canonical WC/RWC resolution now exists before Draw Input commitment. The authority
freezes original WC nominations, ordered RWC candidates and unavailable identities
against the terminal Entry Field. Direct acceptance automatically releases an
original WC, the first eligible available RWC receives the slot, and a WC player
taken from Qualification is atomically removed from Q with ranking-ordered backfill
from below the Qualification cut. New WC events commit Draw Input v3, retain the WC
authority fingerprint, seed Direct + WC players from the same frozen Tournament
Ranking Snapshot and preserve explicit `wild_card` provenance in Main Draw slots.
The authority is included in Saved Revision state and locks after Draw Input commit.

Qualification/Main Draw process windows now have canonical Run/Branch authority.
Each persisted process authority is bound to one exact Draw Authority fingerprint.
Qualification and Main keep independent configured window counts; the penultimate
window is always the Redraw Cutoff / seed-cascade phase and the final window is
always Draw Freeze, while all earlier configured windows are complete-redraw phase.
No default number of early windows is invented because Master §15.10 keeps that
configuration open. The process authority participates in Saved Revision capture /
restore and historical states without it retain their previous fingerprint shape.

Canonical pre-cutoff full redraw is now append-only withdrawal repair history.
The initial Draw remains immutable. Each revision freezes the repaired Entry Field,
its derived Draw Input and the successor Draw, all still using the original frozen
Tournament Ranking Snapshot but a new repair draw seed. A Main withdrawal therefore
atomically promotes the highest eligible Qualification player into Main and backfills
Qualification from below the cut before both affected components are redrawn. A
Qualification-only withdrawal repairs/redraws Qualification while preserving Main.
Each affected component must independently still be in its own full-redraw phase.
Permanent Q1..Qn linkage identities are preserved, multiple withdrawals chain from
the previous revision's full successor field, and the active Draw projection resolves
to the latest append-only revision. Draw revisions are Saved Revision state and
corrupt predecessor chains fail closed before live mutation. WC/RWC events remain
deliberately blocked from this generic slice until their dedicated post-draw repair
authority exists.

The Redraw Cutoff → Draw Freeze middle phase now has append-only physical repair.
A seeded withdrawal executes tier-aware seed cascade without a new draw seed: moved
seeded players retain their original seed numbers, only the necessary later seed
layers move, the highest-ranked surviving eligible unseeded player closes the final
seed vacancy, and the ordinary incoming replacement fills that player's vacated
physical slot. If no ordinary replacement remains, that final physical vacancy
becomes a BYE instead of failing the cascade. Seed 2 therefore does not get renamed
after seed 1 withdraws. An ordinary unseeded withdrawal in the same phase bypasses
cascade and directly fills its exact physical slot; if no replacement exists, that
same slot becomes a BYE. Main and Qualification gate independently: one atomic v3
revision can therefore fully redraw one affected component while cascading the other,
with the repair seed applying only to the component that is actually redrawn.
Multi-Q section/Q identities remain stable, simultaneous withdrawals are
canonicalized, and the complete v3 repair revision deterministically replays from
frozen authority.
Historical v2 full-redraw fingerprints remain backward-compatible.

Draw Freeze now has append-only v4 physical-slot repair. Once a component is
frozen, no seed cascade, sector movement or other-slot mutation is allowed: the
ranking-resolved incoming player enters the exact vacated physical slot without
inheriting seed number, seed protection or entry status. If no replacement remains,
that exact slot becomes a late BYE. Main and Qualification still gate independently,
so one atomic v4 revision may combine a frozen-slot repair with a seed cascade or
full redraw in the other component. Multi-Q section/Q identities stay fixed, pure
frozen repair keeps the existing draw seed, replay is deterministic from frozen
authority, and Saved Revision restore covers the v4 successor.

The Master player-specific replacement cutoff is now an explicit authority.
New successful Draw repairs use revision v5 and freeze one cutoff snapshot for every
withdrawn player. The snapshot is derived from validated Run/Branch competitive
match receipts: no real-match receipt means the slot is still replaceable; if the
latest real match was won, replacement is rejected with an explicit
`walkover_required` state; if it was lost, the tournament path is already
eliminated and cannot be repaired. Canonical BYEs do not create competitive group
receipts, so one or more BYEs do not prematurely close replacement. Because the
current Match Engine command is atomic, the first committed competitive group is the
current durable evidence for first-real-match start. Historical Draw revisions v2-v4
continue replaying from their stored payload and are not reinterpreted using newer
match history.

Post-cutoff W/O is now explicit Run/Branch authority. Once a player's replacement
cutoff is `walkover_required`, the next already-planned match that consumes that
player's latest real-match win can be completed by
`tournament_walkover_authority.v1`. The opponent must already resolve from the
authoritative topology. The Draw is not revised, the Match Engine is not called,
and the W/O event group carries zero Form/Sharpness/Fatigue effects. It still
completes the planned group and feeds its winner forward. Saved Revision
capture/restore validates the same immutable W/O receipt, and the Run driver plus
Admin endpoint expose the operation as an idempotent command.

Canonical Tournament Result records `walkovers_received` and
`retired_or_walkover_loss` separately: W/O advances reached-stage progression but
does not increment played wins or losses. Sporting week transition likewise counts
only competitive match effects, so W/O contributes zero competitive matches.
Canonical point/ranking handling now follows Master §16.3: stage progression from
W/O is eligible for the same authored ranking-point value as that finishing stage,
while the point builder independently verifies that BYE/W/O evidence did not leak
into played win/loss counters. A terminal post-cutoff W/O now runs the normal
canonical tournament close in the same command. New canonical closes persist
`OwnedTournamentRankingSource v5`, adding immutable
`TournamentPrizeMoneyAwardAuthority v1` beside the existing Result and Point Award
authorities. Prize awards use only the player's canonical finishing stage plus the
Edition's frozen original-currency stage table: W/O therefore unlocks the payout of
the actually reached stage without becoming a played win, successful Q/LL entrants
receive only their final Main payout, and missing payout stages remain Unknown rather
than zero. Partial tables persist a known awarded subtotal but keep total prize pool
status Incomplete/Unknown; events with no payout table are explicitly
`not_configured`. Historical v1-v4 owned tournament sources remain readable and
retain their old fingerprint contracts.

Branch-scoped player prize-money history is now projected directly from immutable
owned tournament sources rather than persisted a second time. The read model exposes
chronological per-event payout status, season summaries and career known totals
**grouped by original currency**. Known EUR/USD/etc. values are never added together
without FX conversion; Unknown and not-configured payouts remain distinct, and
pre-v5 tournament history is surfaced as `historical_unavailable` rather than
retroactively becoming zero. The Admin read endpoint is scoped to one Run/Branch.
Master §19.1 reporting-currency season/career totals remain a separate gap until a
historical week-indexed FX authority and rounding policy exist.

Frozen external RWC repair is now canonical for the bounded case where an
unseeded active WC holder withdraws after Main Draw Freeze and the next available
Reserve Wild Card is not already active in Qualification. The new
`tournament_post_draw_wild_card_repair.v1` authority freezes the original WC
authority, predecessor Draw/Input, exact physical WC slot, stored RWC ordinal,
replacement-cutoff evidence and explicit unavailable reserves. Draw revision v6
replaces that exact physical slot with the RWC, keeps `entry_status=wild_card`,
does not inherit seed status, leaves Qualification untouched, and chains Draw Input
v4 post-draw WC repair fingerprints. Repeated RWC use and Saved Revision
backward/forward replay are deterministic.

Frozen cross-draw RWC promotion is now canonical when the next RWC is an unseeded
Qualification player and both affected draws are after Draw Freeze. The v2 RWC
repair authority freezes the exact Q section/slot plus the ranking-ordered below-cut
backfill. Draw revision v7 atomically moves that RWC into the exact `[WC]` Main
slot and inserts the backfill into the exact vacated Q slot without seed
inheritance; Draw Input v4 updates both active WC and Qualification identities.
Saved Revision backward/forward replay validates the same cross-draw evidence.

Frozen seeded WC/RWC repair is now supported. Post-draw WC repair authority v3
freezes vacated Main and/or Qualification seed numbers, while Draw Input v5 keeps
the original canonical seed count as history and stores active seed identities plus
explicit frozen seed vacancies. The replacement RWC or Q backfill keeps the exact
physical slot but receives no seed number, and active `seed_positions` shrink to
the seeds that still exist. Saved Revision replay rebuilds the same vacancy evidence.

Unseeded Q-RWC promotion now honors Qualification's independent repair phase even
when Main is already frozen. Before the Q Redraw Cutoff, Draw revision v8 performs
a full Q redraw with an explicit repair seed. In the middle Q phase, because the
promoted RWC is unseeded, the exact vacated Q slot is filled directly and seed
structure remains unchanged. After Q Freeze, revision v7 keeps the existing exact
frozen-slot behavior. Saved Revision replay validates the same phase and redraw seed.

Seeded Q-RWC promotion now follows the Q phase too. Before Q Redraw Cutoff,
successor Draw Input is re-seeded from the new ranking-ordered Q field and revision
v8 fully redraws Qualification with the persisted repair seed. In the middle Q phase,
the generic seed-cascade engine consumes the seeded departure: surviving seeds retain
their own seed numbers, unseeded players can move into the vacated physical tier
without inheriting a seed, and Draw Input v5 records any resulting seed vacancy.
After Q Freeze, the existing v7 frozen-vacancy repair remains authoritative.

RWC exhaustion is phase-dependent under Master §15.1/§15.8: before Qualification
starts the ordinary Q-list source applies; after Qualification starts the ordinary
source is Lucky Loser priority. The first LL authority is now canonical for the
post-Q-start vacancy boundary. A frozen Direct Main withdrawal with replacement-open
cutoff becomes the next chronological `LLx` placeholder in its exact physical slot.
`tournament_lucky_loser_vacancy.v1` freezes one first-real-Q-match proof plus the
withdrawn-player cutoff and physical/seed provenance. Draw Input v6 stores
`LL1..LLn` chronology, Draw revision v9 stores the frozen slot mutation, and
unresolved LL placeholders remain blocked from executable topology.

Bracket-Q candidate ranking is now canonical. Historical
`tournament_lucky_loser_order.v1` remains the played-terminal contract; new
`tournament_lucky_loser_order.v2` additionally freezes structurally resolved
auto-BYE Qualification terminals. The resolver reads the current canonical Q Draw,
validated authoritative Q match receipts and the frozen Tournament Ranking Snapshot.
A one-player Q section counts as complete only when its terminal winner can be
derived unambiguously through BYE sources with no real match required. Such a section
adds no LL candidate, because nobody lost; mixed Q tournaments can therefore combine
played terminal receipts with auto-BYE terminal evidence. The resolver still waits
for every non-BYE terminal to have a real result, then orders eliminated players by
highest reached Q round and uses Tournament Ranking rank only inside the same
elimination round. The authority freezes one terminal fingerprint per Q section plus
every candidate's elimination result, so later fills do not recalculate historical
LL priority from mutable state.

Bracket-Q LL placeholder filling is now canonical. `tournament_lucky_loser_fill.v1`
freezes the original LL order authority, the next chronological `LLx` slot, selected
candidate, prior assignments, explicit unavailable identities and every higher-
priority candidate skipped for those reasons. Draw Input v7 allows the selected LL
player to remain part of historical Qualification while becoming active Main, and
Draw revision v10 replaces the unresolved placeholder in the exact physical slot
with a player carrying `entry_status=lucky_loser` plus the retained `LLx` identity.
No Lucky Loser ever inherits a seed. Successive fills reuse the first frozen LL order
rather than recalculating priority from the changed Draw.

Replacement-source selection is now canonical in
`tournament_replacement_source.v1`. The resolver evaluates the current effective
Draw/Input and player cutoff, derives real Q/Main start evidence from authoritative
receipts, applies RWC priority for WC slots, switches from pre-Q Q-list promotion to
post-Q LL workflow, then falls through to ranking-ordered external reserves and, if
Main has not started, a late BYE. A closed player replacement cutoff always resolves
to W/O before any candidate source is considered. External reserves explicitly skip
players now active in Main or Qualification, even when they came from an older
below-cut list. The resolver reads the latest revision successor field/input rather
than stale persisted base state.

The unified execution layer is canonical for **frozen Main Draw** vacancies.
`AuthoritativeFrozenMainReplacement` resolves
`tournament_replacement_source.v1` and dispatches deterministic child commands into
the canonical RWC, pre-Q Q-promotion, LL vacancy/fill, reserve/BYE and W/O paths.
Draw Input v8 plus Draw revision v11 cover ordinary Direct-Main external reserve and
late BYE. Exhausted WC slots can now enter the same ordinary reserve/BYE fallback:
Draw Input v9 freezes the original ordinals of former WC slots that were released, Draw revision v12
preserves the exact physical slot, and the incoming ordinary reserve does **not**
inherit WC status. The original Wild Card authority remains immutable provenance;
active WC identities plus released-WC lineage continue to account for the reserved
WC capacity. Revision history rebuilds these transitions from frozen source authority
rather than recalculating today's candidate state.

This unified slice deliberately stops at Main Draw Freeze. After RWC exhaustion, a
WC slot can now fall through canonically to **pre-Q Qualification promotion, Lucky
Loser, external reserve or BYE**. For the LL path, Draw revision v13 binds the
chronological `LLx` vacancy to the frozen replacement-source authority while Draw
Input v9 releases the original WC ordinal and appends that source fingerprint; a
later LL fill therefore uses the same ordinary LL machinery without ever restoring
WC status. Pre-Q promotion is now source-bound too: Draw revision v14 consumes the
frozen `qualification_promotion` source, preserves the exact frozen Main slot,
releases WC status when applicable, honors explicit unavailable-player skips, and
repairs Qualification according to its own redraw / seed-cascade / freeze phase.
Draw Input v8 is used for ordinary Direct-Main promotion and v9 when a WC ordinal is
released; both retain the replacement-source fingerprint for deterministic replay. The
intermediate state where Main has already started, player cutoff remains open and all
sources are exhausted remains fail-closed because Master §15.8 does not explicitly
define it. Auto-BYE-only Q terminals and group-Qualification LL ordering remain
later edges. See
`docs/MASTER_CLASSIC_BRACKET_GEOMETRY_V2.md` and
`docs/CANONICAL_PRE_DRAW_WITHDRAWAL_V1.md`.

## Current follow-up after #849

The first canonical **prospect sporting-profile kernel** now exists as a pure,
versioned domain boundary. From the already-owned hidden prospect profile,
development and potential seeds it deterministically derives all 57 canonical
`0..200` attributes, a hidden potential identity/value and development timing under
`prospect-sporting-profile.provisional.v1`. The result carries the exact policy
fingerprint and only seed digests; raw hidden seeds are not copied into the profile
payload.

This does **not** yet make a birth-week prospect part of
`player_sporting_week_state`. Lifecycle visibility therefore remains independent
from sporting participation: a pre-Tour Draft does not start ordinary weekly
development, junior match simulation, Official Ranking or Tour competition merely
because the hidden profile kernel can now be derived. Persistence into newly
pregenerated prospect metadata and the later guarded adoption/Tour-entry boundary
remain separate follow-ups. See `docs/PROSPECT_SPORTING_PROFILE_V1.md`.
