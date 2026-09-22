# Current implementation and next action

Re-audited 18 September 2026 from merged PR #757 at
`0b3441909f89983e97e12d342c0835db63fb7654`, plus the current bounded
canonical Tournament Entry Field Admin HTTP slice. The audit compares merged code against the
canonical Master Vision instead of treating PR descriptions or Fast CI as product
authority.

This branch adds the first Run/Branch/Week/global-slot-owned competitive match execution path: frozen same-slot inputs, complete Match Engine replay evidence, exactly-once Form/Sharpness/Fatigue effects, intra-week checkpoints, later-slot causal consumption, Saved Revision capture/restore, and terminal-state handoff to Weekly Development. See `docs/AUTHORITATIVE_SIMULATION_SLOT_MATCH_EFFECTS_V1.md`.

PR #728 review hardening preserves owned InitialWorld style/profile truth, carries Form/Sharpness/Fatigue as distinct match inputs, makes any planned slot authoritative even before its first group commit, enforces feeder topology/global ordinals, and semantically revalidates replay and Saved Revision slot chains.

The follow-up compatibility correction assigns Sharpness-aware matches to `match_input_snapshot.v10` / `match_engine_v10`; v1-v9 hash payloads continue to omit the later Sharpness field and retain their historical identities.

The tournament bridge freezes a v4 Run/Branch/week authority bundle and consumes a canonical executable DAG built from persisted match IDs, direct slots and `winner_to_match_id` evidence. Production-backed eight-player/seven-match Main Draws repeat across three completed authoritative weeks with authoritative schedules, Week Transition and replay. A canonical sixteen-player/fifteen-match Main Draw runs from published Official Ranking → Tournament Ranking Snapshot → Entry Field → Draw Input → Draw Authority → four Match Days containing 8→4→2→1 competitive matches, with every match occupying its own sequential global Simulation Slot, then closes into `OwnedTournamentRankingSource v5` with 16 player results and all 15 canonical match results. A non-power-of-two 13-entrant field retains a fixed 16-position canonical bracket, three explicit BYEs and 12 simulated competitive matches across four Match Days containing 5→4→2→1 played matches, while the completed canonical result still retains all 15 bracket-node results including the BYEs. Canonical point awards preserve actual finishing stage separately from the Master §15.4 first-real-match ranking unlock via an optional `point_stage`; W/O advancement remains the §16.3 exception. Players who participate in both Qualification and Main now receive the Master §18.1 additive Q + Main ranking value in Point Award v3, with the two draw unlocks evaluated independently. Canonical Main capacity is derived automatically from the requested entrant count at Tournament Edition creation by rounding to the next power-of-two capacity and recording the remainder as explicit BYEs; seed count remains Master-derived rather than manually authored. The current supported classic-bracket ceiling is 128 positions: 65–128 entrants remain supported (and advisory-warned as an exceptional large Main field), while 129+ entrants fail closed instead of silently deriving a 256-position bracket. A non-authoritative pre-alpha diagnostic layer emits stable Admin warnings for every odd Main entrant count, for opening rounds where more than half of matches contain a BYE, and for Main fields above 64 entrants. These diagnostics are exposed through canonical capacity/draw helpers and the existing DrawPackage validation-warning surface, but are excluded from persisted sporting authority and Draw fingerprints; seed-band/section asymmetry remains a later refinement. The driver can now derive a deterministic, read-only Match Day schedule proposal directly from the canonical executable DAG. Under `week_simulation_schedule.v2`, every competitive group receives its own global Simulation Slot while same-day matches share immutable Match Day metadata and execute in deterministic stored order; feeder matches remain on earlier Match Days and proposal identity is registry-order independent. The proposal is not persisted until an explicit guarded adoption command is used. A dedicated atomic proposal-adoption path rebuilds the proposal under `BEGIN IMMEDIATE`, binds it to the expected Ranking Week plus proposal/position fingerprints, and only then persists the immutable Week Simulation Schedule. The client no longer needs to round-trip the full schedule payload to adopt the engine-generated proposal; exact retries remain idempotent. Qualification promotion and unambiguous one-player BYE evidence execute through the same closure/ranking path. PRs #738–#740 also added persisted Wild Card and withdrawal/replacement provenance primitives. A post-merge Master Vision audit found that those primitives are not the completed repair workflow: overlapping entries may remain provisional until commitment authority; pre-draw withdrawals must rebalance Main/Qualification field cuts from the Tournament Ranking Snapshot; and post-draw repair must honor redraw/cascade/freeze phases, Lucky Loser priority and the first-real-match replacement cutoff. This correction branch removes the #737 automatic preferred-tournament choice and fails closed before play when overlapping commitments remain unresolved. Historical v1-v3 four-player readers remain compatible. Legacy `start_day`, list order and round-name text are never chronology authority.

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
| Other pre-alpha scope | Master 31 remains authoritative; minimum canonical Match Reconstruction is implemented in the Run/Branch Admin simulation path | Reconstruction probability/forcing/nearest-match/session-retention remain open; player development/AI and broader lifecycle must not be dropped merely because ranking work dominated recent PRs |

Paths above are relative to `src/beta_engine/` unless a `web` component or document
is named. Ranking detail: [completion checklist](docs/RANKING_COMPLETION_STATUS.md).

## Audit findings and corrections

- Fast CI is intentionally a feedback gate rather than the complete safety net. It
  runs a compact `pr_critical` backend baseline, and a compact frontend baseline plus
  changed/colocated frontend tests and the production build. Backend does not auto-run
  every changed test file because several canonical acceptance files are intentionally
  large; focused must-pass backend tests belong in `pr_critical`, while long tournament
  end-to-end acceptances are marked `smoke`. The separate Full Test Suite retains all
  coverage after merge to `buuk` and nightly.
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
tournament-to-ranking bridge are implemented, not future gaps. Multiple same-week events without an adopted schedule still fail closed before mutation. The explicit Week Tournament Lock now resolves overlapping accepted fields before draw/schedule ownership without inventing automatic preference or a Final Commitment deadline. Automatic schedule proposals on this branch use Week Simulation Schedule v2: every competitive match owns one global Simulation Slot, while Match Day metadata freezes day and within-day order so matches on the same playing day execute sequentially rather than sharing one pre-slot snapshot. The canonical path now also exposes a resumable **Next Match Day** orchestration boundary and matching reviewed Admin UI: preview shows the exact frozen day/slots/groups/revision/schedule fingerprint, commit persists deterministic child Next Slot commands before execution, normal lost-response retry reuses the same parent command ID, and canonical conflicts discard stale review instead of absorbing schedule/Saved Revision/chronology drift. It now also exposes canonical **Next Round**: the server freezes the current V2 event/phase/round identity, every remaining target of that round and the exact global chronology horizon through the last target. Interleaved matches from other tournament identities are exposed as transit work and executed only when chronology requires them; Entry/WC process slots are never skipped. Driver, HTTP and reviewed Admin UI flows preserve exact retry through deterministic child Next Slot receipts. Courts, multi-week Round Schedule spans and the remaining travel/rest/carryover/fairness optimization remain outside this foundation. See `docs/AUTHORITATIVE_MATCH_DAY_ORCHESTRATION_V1.md`.

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
reuse or reinterpret the older simulation-run endpoint. Planned Event now exposes
that canonical command directly from the current Branch Entry Field: Admin can choose
an active Main or Qualification player, commit against the exact field fingerprint,
and inspect the server-derived promotion/backfill delta. The old simulation-run
pre-draw GET/POST authoring endpoint returns `410 Gone` and its Commissioner form is
removed; historical `pre_draw_withdrawal_replacement` sidecar actions remain
read-only for compatibility/audit.

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

The frozen-Main source chain now has a canonical **Run/Branch Admin review boundary**.
Planned Event Admin can preview the server-derived replacement source from the current
effective Draw without mutation, including the selected player, physical slot,
player-specific cutoff state and exact source-authority fingerprint. A Draw-revision
commit must present that reviewed fingerprint and the server re-resolves the source
inside one immediate transaction before dispatch, so stale RWC/Q/LL/reserve state
fails closed. Exact retries reuse immutable child revision history. When preview
resolves to post-cutoff W/O, the Draw workflow does not create a competing mutation;
it explicitly hands execution back to the existing canonical Simulation W/O command.

The old simulation-run late-replacement authoring surface is now retired. Its
eligibility, candidate and mutation HTTP endpoints return `410 Gone` and Planned
Event no longer renders the old Commissioner late-replacement controls. Historical
`late_replacement_lucky_loser` admin actions remain readable as a read-only audit
trail so existing saves/history do not lose provenance. The underlying legacy
sidecar readers remain compatibility code only; new mutations must use the active
Run/Branch canonical Draw workflow.

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


## Current follow-up after #850

New 15-year-old cohort materialization now persists the #849 canonical sporting
profile **before** lifecycle activation. Each new Run prospect stores the complete
`prospect_sporting_profile.v1` payload and fingerprint together with
fingerprint-bound development/potential summaries. The materialization policy also
binds the exact sporting-profile policy identity, so replay cannot silently switch to
a newer calibration.

Prospect Bridge inspection validates the persisted canonical payload and its
cross-section fingerprints. Legacy/hand-authored placeholder rows still report
`canonical_sporting_profile` as unresolved; correctly persisted new rows do not.
This remains diagnostic only and does not block Week Transition.

No existing lifecycle-activated prospect is rewritten: the #848 immutability guard
still rejects changed metadata after historical visibility. This persistence slice
alone still does not place birth-week prospects into `player_sporting_week_state`,
create Tour entry, or expose hidden sporting truth to Viewer. That missing birth-week
sporting adoption is an implementation gap, not a product rule: Master Week
Transition creates new 15-year-old prospects after completed-week development, and
the next slice must add their already-persisted simulation-valid sporting core to the
new target-week sporting snapshot without granting Tour status or ranking membership.


## Current follow-up after #851

Ordinary authoritative Week Transition now implements the Master birth-week sporting
boundary for new 15-year-old Run prospects. Completed-week development and
between-week recovery still operate only on the predecessor sporting roster. After
that calculation, the transition loads exact target-week prospect rows, validates the
same birth identity used by lifecycle plus the #850 persisted canonical
57-attribute/development/potential evidence, and appends new `PlayerSportingRecord`
values to the target snapshot before commit.

The prospect simultaneously enters target lifecycle as a pre-Tour Draft with
`tour_entry_week=None`. It therefore remains absent from the Official Ranking
request and receives no retroactive development for the completed week. Initial
Form/Sharpness/Fatigue use the target sporting state's historically persisted
provisional bootstrap defaults. Legacy/placeholder or internally inconsistent
sporting-profile evidence now blocks only the affected Week Transition with
`prospect_sporting_profile_unready`; the Prospect Bridge inspection reports the
same blocker.

Preview/confirm remains atomic. Changes to birth identity or to a coherent hidden
sporting profile after preview invalidate confirm and leave lifecycle, sporting and
ranking target writes absent. Season Transition Week 61 → next-season Week 1 still
needs the same sporting-adoption parity, and formal Tour entry remains a later
separate authority.


## Current follow-up after #852

Ordinary Season Transition now has the same Master-aligned birth-week sporting parity
as ordinary Week Transition. The Week-61 predecessor roster completes development and
between-week recovery under the outgoing policy, the staged Week-1 state installs the
incoming development policy, and only then exact Week-1 15-year-old Run prospects are
validated from their persisted canonical profile and appended to the target sporting
snapshot.

The sibling lifecycle stage still creates the same identities with
`tour_entry_week=None`, so these new players remain pre-Tour and absent from the new
Official Ranking. Canonical profile/development/potential evidence, policy identity and
stored profile/development/potential seeds must agree; legacy placeholder evidence
makes the Season sporting candidate unavailable and blocks the atomic Season advance.

The full ordinary Season writer persists that sporting state, lifecycle state, Week-1
Official Ranking, publication, World Event and Saved Revision atomically. PR-critical
coverage proves both the direct sporting candidate and the complete Season advance
with a Week-1 prospect. The immediate prospect-profile parity gap is therefore closed
for ordinary Week and Season boundaries. Formal prospect → Tour Player activation now has explicit branch-owned trigger
evidence for both Master-defined paths: valid MSA Tour application submission and
definitive WC/RWC assignment. First-entry triggers are persisted append-only, projected
onto current lifecycle reads immediately, and sealed into later lifecycle boundaries
without retroactively rewriting the current Official Ranking. The application path now
preserves the complete shared-snapshot pre-cut decision batch in a Run entry-decision
Simulation Slot, persists complete validation outcomes, atomically commits already-valid
submissions plus first Tour-entry truth, and can project those persisted submissions
directly into the canonical Tournament Entry Field. The authoritative Run driver also
has a guarded preview/commit boundary that rebuilds the shared-snapshot Entry batch
under the expected Branch head and stores the complete Run slot without mutating the
legacy EntryList registry. Persisting those decisions reserves the global ordinal;
chronological completion requires the matching complete validation slot, so later
Entry/match execution cannot overtake unresolved application validity. Exact
eligibility/deadline validation policy remains upstream and intentionally unresolved.
The Simulation Admin workflow can now inspect the currently blocking persisted Entry
slot and commit a complete **explicit Admin validation review** using only valid/invalid
verdicts plus rejection reasons and audit provenance. The server derives application
IDs, source fingerprints, Main/Q windows and NR tie-break evidence from frozen Run
truth and CAS-guards the current Position, Branch head and Entry slot before mutation.
This is an operational pre-alpha bridge, not an invented automatic eligibility or
deadline policy. Field capacity still cannot create or revoke Tour status.

## Current follow-up after #874

Canonical WC/RWC resolution can now participate in the same **global Simulation Slot
chronology** as Entry decisions and matches without pretending that a WC decision is a
match slot. New `TournamentWildCardAuthority v2` freezes the exact FAX week and
one-based global slot ordinal on the immutable WC resolution itself; historical v1
authorities remain fingerprint-compatible and carry no retroactive chronology.

Live writers are symmetric and fail closed. WC v2 cannot claim an ordinal already
owned by a persisted Entry slot, match slot or adopted match schedule, and it cannot
skip an unresolved earlier Entry decision, incomplete match, existing WC decision or
missing ordinal. Entry and match writers now reject chronology-aware WC slots in the
opposite direction. The topological week scheduler treats completed WC decision
ordinals as reserved non-match slots and shifts match layers around them.

Saved Revision validation includes WC v2 positions when checking global-slot
collisions and contiguity while leaving historical WC v1 replay untouched. The
existing definitive WC/RWC assignment domain authority is also bound so that when it
is created from a chronology-aware WC source, it must reuse the exact source week and
slot ordinal.

This is the chronology foundation only. The next slice is the transaction-owning
Run/Branch Admin command that derives the current week/global ordinal from
authoritative Position, resolves canonical WC/RWC authority, records every resulting
definitive assignment plus first Tour-entry trigger atomically, exposes it in Planned
Event Admin, and only then retires the remaining legacy wildcard authoring surface.

## Current follow-up after #875

The chronology foundation now has a transaction-owning **canonical WC/RWC Admin
workflow**. Because Master §15.1 still leaves exact WC eligibility and construction /
ordering of the RWC list open, the pre-alpha boundary does not invent an automatic
selector. Planned Event Admin records an explicit reviewed WC nomination and ordered
RWC list with operator + audit reason under
`explicit_admin_wild_card_selection.v1`.

`TournamentWildCardAuthority v3` freezes that review together with the terminal
Tournament Entry Field, exact current FAX week and next global Simulation Slot. v1 and
v2 fingerprints remain historically compatible. Preview is read-only; commit
re-derives and CAS-checks Branch head, week, global slot and complete proposal
fingerprint under `BEGIN IMMEDIATE`. The canonical WC builder still owns the
Master-decided Direct Acceptance rule: an original WC holder who is already Direct is
released from WC and the next usable player in the reviewed RWC order is consumed.

One successful commit atomically persists the WC authority and every active
`DefinitiveWildCardAssignmentAuthority`; those assignments use the existing shared
first-entry store so the first valid WC/RWC assignment can create the player's first
`PlayerTourEntryTrigger` in the same transaction. Unfilled WC slots and mere presence
in the RWC order still do not create Tour status.

Planned Event now uses the canonical Run/Branch state → preview → commit flow. The old
simulation-run wildcard state, candidate and mutation endpoints return `410 Gone`.
Historical `assign_wildcards` admin-action history remains readable as a read-only
audit trail for old saves. Automatic WC eligibility and automatic RWC ordering remain
unresolved Master policy and are not inferred by this bridge. The later explicit Week
Tournament Lock Admin boundary now supplies the pre-alpha conflict-resolution authority;
automatic Final Commitment deadline/preference policy remains unresolved.



## Current follow-up after #876

The minimum pre-alpha **Match Reconstruction** contract now has a canonical
Run/Branch implementation. Admin can reconstruct the currently eligible match by
supplying hard known facts: winner identity, exact match score and/or exact game
scores. Candidate count is explicit. Candidates are generated through the same
canonical Match Engine and Simulation Slot executor as normal sporting execution,
rather than a second reconstruction engine.

Preview is non-authoritative: adopted authority, slot staging and every candidate
execution are rolled back. Candidate order is deterministic discovery order and each
candidate exposes both a compact score summary and complete read-only Match Result
detail. A bounded natural search may return fewer candidates than requested with an
explicit warning; it does not force a result.

Only an explicitly selected candidate can become history. Commit re-derives the
reviewed preview under the current week, Position and Saved Revision head, replays the
selected seed exactly, persists reconstruction provenance plus operator/audit reason on
the canonical match-group receipt, then uses the normal match-effects and tournament
close path.

This closes the **minimum Match Reconstruction** pre-alpha acceptance item, not the
full reconstruction design. Probability estimates / p-delta-alpha policy, forcing,
nearest-match search, the complete constraint catalog, reconstruction-session
retention and final dedicated UI remain unresolved and are not inferred.


## Current follow-up after #877

The second mandatory pre-alpha acceptance flow from Master §31.3 now has a minimum
backend implementation on this branch: a canonical **empty Run** can author exactly two
manual players and simulate one standalone competitive match without attaching a World
Package, Calendar, Tournament Edition, Entry Field, Wild Card authority, Draw or Week
Simulation Schedule.

The pre-match workspace is Run/Branch-owned and optimistic-fingerprint guarded. Match
commit owns one BEGIN IMMEDIATE transaction: it freezes the reviewed manual players as
manual_standalone.v1 InitialWorld truth, bootstraps Week-1 lifecycle and 57-attribute
sporting state through the existing canonical adapters, creates one direct-player
Simulation Slot and executes through AuthoritativeSlotMatchExecutor / the normal Match
Engine effects path. Exact command retry returns the stored result; conflicting reuse
fails closed.

The PR-critical acceptance also proves operation-scoped modularity by asserting that
Tournament/Entry/WC/Draw/Week-schedule authority remains absent. After completion the
existing authoritative simulation Save captures InitialWorld, lifecycle, sporting,
slot/group and command-receipt truth into the Saved Revision. The transient pre-match
workspace itself is not claimed as independently saveable in this minimum slice.

This implements the narrow PAQ-003 / PAQ-005 acceptance requirement only. It does not
invent a global Start gate, Calendar/Tournament policy, ranking policy, automatic player
generation or a broader standalone multi-match workflow. See
`docs/STANDALONE_MATCH_ACCEPTANCE_V1.md`.

## Current follow-up after #878: authoritative empty weeks

The whole-season Official Run path now has an explicit production boundary for a
genuinely event-free week. `authoritative-simulation/empty-week/complete` is
CAS-guarded by current Position and Saved Revision, requires a real season Calendar,
rejects any Calendar Event interval or existing tournament/simulation ownership,
and persists a zero-match `CompletedWeekSportingContext` with frozen Calendar
evidence. Position accepts that context in place of a match terminal checkpoint,
so the ordinary development/lifecycle/ranking Week Transition can proceed without
direct DB seeding.

This is continuity plumbing only. It does not reinterpret a missing Calendar as an
empty week, does not decide cancellation handling, and does not add any unresolved
Entry/WC/lock/reconstruction policy. PR-critical acceptance covers tournament
weeks -> explicit empty week -> following RankingWeek plus false-empty rejection.


## Current follow-up after #879: Official Run whole-season acceptance

The primary mandatory pre-alpha flow from Master §31.3 is now exercised end to end
through canonical production boundaries. The acceptance creates an owned Official Run
Initial World through Admin API, derives and Saves the initial Official Ranking,
simulates a real Week-1 tournament through the authoritative Match Engine path, then
advances through every remaining week of Season 0. Event-free weeks use the explicit
Calendar-backed zero-match completion boundary from #879; no direct database repair or
synthetic completed-week rows are used inside the flow.

Ordinary Week Transitions remain in the clean Working Draft until an explicit Save
checkpoint, which is the intended Run model rather than an implicit Save-after-every-
week rule. At Week 31 the test Saves the complete ranking/lifecycle/sporting/simulation
state, records the post-Save Position fingerprint, shuts the API process down, reopens
the same Run database, and requires exact Position identity before continuing. Week 61
is Saved again and must produce a ready canonical Season Transition preflight.

The same flow now successfully round-trips the server-derived
`season_transition_configuration.v1` through the HTTP advance endpoint and commits the
ordinary Season Transition to Season 1 Week 1. While building this acceptance, that
round-trip exposed a strict-mode API bug: JSON arrays emitted for immutable tuple fields
were rejected when the preview configuration was posted back. The ordinary transition
endpoint now parses the request in Pydantic JSON mode, preserving strict internal
models while accepting their normal JSON representation.

The whole-season acceptance is the PR-specific backend test for this slice. On the
current GitHub runner its test body completes in 31.28 seconds; the targeted pytest run
reports 1 passed and 2415 deselected in 42.96 seconds. During pre-alpha construction,
pull requests run only tests changed by that PR, while the complete regression suite is
manual and will be run together at the final pre-alpha acceptance gate.

This proves the minimum whole-season continuity / Save-reopen / rollover path, not the
still-open PAQ-006 reference-scale target or unresolved automatic Entry/WC/lock policy.


## Current development test / release policy after #880

During ordinary pre-alpha construction, pull requests should run only the focused tests
that are relevant to the changed behavior. Long or unrelated regression tests may stay
out of automatic PR CI; they remain preserved in the repository and can be invoked
manually. A PR is not merge-ready if a test required for that PR is red.

The complete regression suite is intentionally concentrated around explicit internal
release/checkpoint boundaries. Whenever an internal version is deliberately declared
for release (including the first pre-alpha), the full backend/frontend regression gate,
Master §31.3 mandatory acceptance flows and any release-specific smoke/performance
checks must all be run before that version is accepted.

Canonical engineering wording: `docs/PRE_ALPHA_TEST_POLICY.md`.


## Current follow-up after #882: PAQ-006 measurement foundation

The repository now has a cross-platform, non-authoritative performance profiler for
the two mandatory Master §31.3 acceptance flows. It records wall-clock duration,
Python-managed current/peak heap via `tracemalloc`, exact pytest node IDs, Python and
platform identity, and pytest exit status as
`pre_alpha_performance_profile.v1`.

This is measurement infrastructure only. It deliberately sets no pass/fail time or
memory threshold and therefore does not mark PAQ-006 resolved. The profiler is kept
out of ordinary PR CI under the focused-test policy and is intended for deliberate
performance investigations and explicit internal release/checkpoint gates. See
`docs/PRE_ALPHA_PERFORMANCE_MEASUREMENT_V1.md`.


### Green-only PR handoff rule

PR links are not handed to the user as merge-ready while required CI is queued,
running, failed, cancelled or timed out. After every fix, CI must be re-checked on the
latest head commit. Only an all-green latest head may be presented as the next PR to
merge. This is a hard development workflow rule, not a suggestion.


## Saved Revision restore: Season Closure identity repair

Saved Revision restore now treats embedded `season_closure` evidence as revision-bound
state. Historical target closure evidence is validated against the historical target
revision before restore, then the newly created restore revision receives the same
Season Summary with a newly bound Closure Marker whose `final_saved_revision_id`
points to the restore revision itself. The historical target revision is not rewritten.

This closes a recovery-integrity hole where copying a Season Transition revision into a
new restore revision could leave the embedded closure marker pointing at the old
revision identity, making the new revision fail its own closure identity validation.
Focused regression coverage exercises the real Branch restore transaction and verifies
the resulting Saved Revision content hash.


## Saved Revision restore: complete simulation-authority fail-closed guard

The restore preflight now treats all canonical simulation-adjacent tournament authority
rows as state that must already be captured by the current Saved Revision before a
historical restore may proceed. In addition to slots, groups, schedules, Entry Field,
Draw Input and Draw authority, the guard explicitly covers Tournament WC authority,
Draw Process authority and append-only Draw revisions.

This prevents a legacy/component-less Saved Revision from restoring while newer live
WC/process/revision rows remain in the database as future state. The restore aborts
before mutation instead. Focused regression coverage proves all three omitted authority
types fail closed and create no restore revision/checkpoint.


## Saved Revision restore: orphan completed-week sporting context guard

Restore preflight now treats `CompletedWeekSportingContext` rows as canonical live
sporting state even when no `PlayerSportingWeekState` row is present. Because the
Saved Revision sporting component owns both the player-state chain and completed-week
contexts, a context-only live row cannot be allowed to survive a restore whose current
Saved Revision has no sporting component.

The restore now fails closed before mutation in that inconsistent/legacy state. Focused
regression coverage verifies that no restore revision or safety checkpoint is created.


## Central Saved Revision restore coverage registry

Recovery preflight now has one canonical technical registry mapping Saved Revision
components to the live Run/Branch tables they own. This replaces the growing chain of
hand-written per-component row-presence checks in the repository restore method.

The audit that introduced the registry closed two additional gaps:

- `SeasonClosingRankingModel` is explicitly part of ranking recovery coverage, so a
  legacy/current head without the ranking component cannot hide live archived closing
  ranking history during restore;
- the intentionally transient `StandaloneMatchWorkspaceModel` is a restore blocker.
  A partially authored Master §31.3 standalone match must be completed or discarded
  before historical restore; it is not silently carried into the restored timeline and
  is not misrepresented as Saved Revision content.

The registry also makes the previously added WC/Draw Process/Draw Revision and
CompletedWeekSportingContext guards structural rather than one-off conditions.
`season_closure` remains an embedded-only supported component handled by its dedicated
revision-identity rebinding path. See
`docs/SAVED_REVISION_RESTORE_COVERAGE_V1.md`.


## Saved Revision restore preflight

Historical restore now exposes a read-only, target-specific preflight contract. The
backend resolves validated revision lineage and returns the exact current Saved Revision
head, Working Draft version, current/target Viewer Branch identities and all known
restore blockers without mutating state.

The Saved Revision History UI now consumes that server preflight instead of duplicating
restore eligibility rules client-side. Confirm binds to the reviewed server snapshot and
still revalidates everything under `BEGIN IMMEDIATE`, so a stale preflight fails closed.

Coverage-registry blockers, transient authoring blockers and unsupported legacy-backed
Run/Branch state are visible before opening the confirmation dialog. See
`docs/SAVED_REVISION_RESTORE_PREFLIGHT_V1.md`.


## Saved Revision history pagination and comparison

The validated Saved Revision history read model now supports stable cursor pagination
from the newest reachable history toward older shared/local ancestry. Pages use an
exclusive `before_sequence` cursor and remain chronological inside each page.

Admin can also compare any two loaded/reachable Saved Revisions read-only. The backend
reports Run/Branch metadata changes plus Saved Revision component status
(`added/removed/changed/unchanged`) and deterministic before/after fingerprints.
Comparison performs no domain interpretation and no mutation.

The Saved Revision History UI loads the newest page first, can fetch older pages, and
renders comparison results for two loaded revisions. See
`docs/SAVED_REVISION_HISTORY_PAGINATION_COMPARISON_V1.md`.


## Run prospect source recovery snapshot

Saved Revision recovery now preserves deterministic evidence for the shared Run-scoped
prospect catalog through `run_prospect_source_snapshot.v1`.

All future Saved Revisions capture the canonical Run prospect source when present, and
Admin has an explicit preview/Save boundary for materialized prospect changes. Because
`run_prospects` is shared across Branches, historical restore never rewrites that live
table. Instead both preflight and confirm require the target/current saved source
fingerprint to match the live Run catalog exactly and fail before mutation on drift.

The central restore-coverage registry now has a separate Run-scoped reference category
alongside Branch-owned components and transient blockers. This closes the prospect-source
fidelity portion of complete sporting-world recovery without claiming that the broader
recovery/ranking-remap follow-up is finished. See
`docs/RUN_PROSPECT_SOURCE_SAVED_REVISION_V1.md`.


## Ranking-bearing Branch fork: bootstrap remap slice

The blanket rejection of all ranking-bearing Branch forks is removed for one verified
production-safe subset: a Saved Revision containing a single source-free Week-1
`initial_ranking.v1` history (plus optional Run-scoped prospect-source evidence).

Fork creation now reconstructs the bootstrap command for the target Branch identity,
recalculates its request and Official Ranking fingerprints, installs the remapped
ranking state atomically, and creates a target-owned `branch_fork_materialized`
Saved Revision as a child of the selected source revision. The new Working Draft is
based on that fork-root revision; source history remains immutable shared ancestry.

A PR-critical acceptance proves the target Branch can then prepare and Save Week 2 while
the source Branch remains unchanged. Multi-week ranking history, InitialWorld-bound
ranking, tournament/zero/transition authorities, Season Closing state and other
Branch-owned components still fail closed pending dedicated remap adapters. See
`docs/BOOTSTRAP_RANKING_BRANCH_FORK_REMAP_V1.md`.


## Ranking-bearing Branch fork: source-free multi-week remap

The ranking fork adapter now extends beyond bootstrap-only Week 1. A complete consecutive
source-free Official Ranking history (Week 1..N) can be materialized for a new Branch by
replaying every stored canonical ranking command with only the Branch identity changed.

Each original command must still exactly match its frozen ranking manifest. Target
snapshot fingerprints, request fingerprints and the full previous-fingerprint lineage
are recalculated for the new Branch. A PR-critical acceptance proves a source Week 1–3
history forks into an independent target Week 1–3 history, then the target alone advances
and Saves Week 4 while source history remains unchanged.

Tournament/result/correction history, zero history, authoritative transition inputs,
InitialWorld binding, publication/Season Closing evidence and other unsupported
Branch-owned components remain fail-closed.


## Ranking-bearing Branch fork: disciplinary-zero remap

Result-free ranking-bearing forks now support versioned `stored_zeros` history.
`RankingZeroVersion` records are rebuilt for the target Branch, including their
successor fingerprint chain, and all stored ranking command receipts are rebound to the
target zero fingerprints before ranking snapshots are recalculated.

The fork adapter verifies the frozen manifest against the source zero history at every
ranking week and rejects manual `resolved_zeros` injection. A PR-critical acceptance
proves the target can append its own later zero correction and Save a new ranking while
the source Branch keeps its original zero history.

Tournament/result/correction history and transition/publication authorities remain
fail-closed pending their own remap adapters.


## Ranking-bearing Branch fork: result/correction history remap

Ranking-bearing forks now support Branch-owned `RankingResultVersion` histories and
their correction chains when no `OwnedTournamentRankingSource` authority bundle is
present. Result-version Branch identities and predecessor fingerprints are rebuilt for
the target, weekly correction commands are rebound to the new fingerprints, and every
frozen ranking manifest is checked against source-history resolution before target
snapshots are recalculated.

A PR-critical acceptance proves the target can fork an existing Week-2 result history,
append an independent Week-3 correction, and Save it while the source Branch retains its
original result version and ranking points.

Canonical tournament source/authority remapping remains a separate fail-closed follow-up.


## Ranking-bearing Branch fork: canonical tournament authority remap

Ranking-bearing forks now support canonical `OwnedTournamentRankingSource` v4/v5
bundles. Tournament Result authority is rebound to the target Branch; Point Award
authority and optional Prize Money authority are rebuilt against the new Result
fingerprint; the target tournament binding is then rebuilt against those target-owned
authority fingerprints. Ranking result versions are re-derived from the remapped
canonical authorities rather than copied from source history.

The trusted empty-fork installer accepts this remapped tournament-source state
atomically with the ranking lineage. Legacy tournament source versions v1-v3, final
Closing-only v6 sources, transition/publication/Season Closing authorities remain fail-closed pending their own
explicit adapters.


## Ranking-bearing Branch fork: tournament correction-chain remap

Canonical tournament-backed ranking history may now include later
`RankingResultVersion` corrections. The source correction chain must be complete and
its stored predecessor fingerprint must exactly match the preceding source version.
During fork materialization each correction is rebound to the already remapped target
predecessor fingerprint, so target history remains independently valid and diverges
cleanly from the source Branch.

A malformed or detached predecessor still fails closed before target state is
materialized. This closes the correction-over-canonical-tournament follow-up left after
the v4/v5 authority remap.


## Ranking-bearing Branch fork: transition authority identity adapter

A dedicated Branch-fork adapter now safely rebuilds immutable
`RankingTransitionAuthority` records for a target Branch. It verifies source scope and
canonical target-week ordering, preserves the frozen sporting roster, policy,
provenance and audit, and rebinds both `branch_id` and `base_revision_id` before
recalculating the authority fingerprint. A source-fingerprint -> target-authority map
is produced for the later weekly-command rebind step.

This is deliberately not yet wired into the full ranking fork materialization path.
The target `base_revision_id` must be the real target-owned materialized fork-root
Saved Revision. The next adapter slice must coordinate fork-root revision identity,
weekly command `authority_fingerprint` rebinding and authoritative publication/world
state atomically; transition-bearing forks therefore remain fail-closed at the public
fork boundary for now.


## Ranking-bearing Branch fork: transition-backed command remap

The ranking fork path now consumes the real target-owned materialized fork-root Saved
Revision identity while rebuilding `RankingTransitionAuthority` history. Transition
authorities are installed into the target ranking state, and audited
`RankingWeekCommand` receipts are rebound from the source authority fingerprint to the
new target authority fingerprint before their request and Official Ranking fingerprints
are recalculated.

The adapter verifies that every referenced authority belongs to the Saved Revision and
matches the frozen completed/target week, roster, policy and audit evidence. It also
requires every saved transition authority to be owned by a stored ranking command;
detached authority history fails closed.

Authoritative publication/world state, Tournament Ranking Snapshot authority and Season
Closing archives are still outside this fork slice and remain fail-closed.


## Ranking-bearing Branch fork: Official publication + world-head remap

The fork remapper now carries the authoritative Official Ranking publication lineage
and current world ranking head across Branch identity when that transition state
contains publication/world evidence only. Every source publication must exactly match
the frozen source ranking entry for its week; the publication is then rebuilt from the
already remapped target ranking snapshot, producing the target snapshot fingerprint and
payload. The authoritative world head is rebound to the target Branch and the target
fingerprint at the same current ordinal.

Trusted empty-fork installation now accepts and restores this publication/world bundle
atomically with ranking history.

Week/Season Transition receipts and World Events remain fail-closed because they carry
player lifecycle/sporting or Season Closing fingerprints that cannot be truthfully
rebuilt by the ranking-only Saved Revision slice yet.


## Branch fork: player lifecycle Saved Revision remap

Ranking-bearing materialized Branch forks can now carry the complete
`player_lifecycle` Saved Revision component. The fork path validates the source
component, rebuilds every immutable lifecycle snapshot for the target Branch, rewires
the predecessor fingerprint chain to target-local fingerprints, writes the rebuilt
component into the target materialized Saved Revision, and installs the same lifecycle
history into target Branch persistence in the fork transaction.

Player roster, lifecycle policy, age/status/Tour-entry evidence and shared InitialWorld
provenance remain unchanged. Only Branch-owned identity and predecessor fingerprints
are rebuilt.

Player sporting history remains guarded for the next slice because its completed-week
contexts also reference branch-owned tournament/match-effect evidence that must be
mapped rather than copied.


## Branch fork: player sporting v1 Saved Revision remap

The same materialized Branch-fork path now also supports `player_sporting_state`
history when its completed-week contexts use the v1 OwnedTournamentRankingSource
evidence model. Source tournament fingerprints are rebound through the already-remapped
ranking tournament sources; each completed-week context is then rebuilt for the target
Branch, and every sporting snapshot is rebuilt against the new target context and
predecessor fingerprints. The target component and persisted sporting/context rows are
installed atomically with the fork.

v2 sporting contexts sourced from the authoritative Simulation Slot match/effect ledger
remain fail-closed. Their terminal sporting and match-effect fingerprints belong to
separate Branch-owned authorities that are not yet fork-remapped.


## Branch fork: sporting v2 evidence remap contract

The player sporting Branch-fork remapper now supports
`completed_week_sporting_context.v2` once the authoritative Simulation Slot layer
provides exact target mappings for all external evidence: source result fingerprints,
the terminal sporting checkpoint fingerprint, and every match-effect fingerprint.

No v2 evidence is copied across Branch identity. Missing any source→target mapping fails
closed before a target sporting context is created. Once all mappings are present, the
target context fingerprint and the complete sporting predecessor/context chain are
rebuilt deterministically.


## Branch fork: Simulation Slot sporting identity adapter

A dedicated Simulation Slot fork adapter now rebuilds the branch-owned sporting identity
inside authoritative match history. `PlayerMatchSportingEffect` can be rebound through
target mappings for its pre-match sporting snapshot, protected match input and
authoritative result fingerprints. `PlayerSportingCheckpoint` can likewise be rebound
through target opening-week sporting identity, slot-start identity, predecessor
checkpoint identity and applied match-effect fingerprints.

The adapter is fail-closed on any missing dependency mapping. This establishes the
deterministic week-ordered seam required to break the apparent sporting-v2/slot-ledger
cycle: target opening sporting snapshot -> target match/effect/checkpoint ledger ->
target completed-week sporting v2 context -> next target sporting snapshot.


## Branch fork: completed Simulation Slot core ledger remap

The completed authoritative Simulation Slot core can now be rebuilt across Branch
identity for the saved `slots + groups` ledger. The adapter walks slots in canonical
week/slot order, recomputes target slot-start identity from the target Branch and target
predecessor checkpoint, rebuilds each slot plan, rebinds competitive protected match
input identity, recalculates result fingerprints, rebuilds every match sporting effect,
and then rebuilds slot-start/terminal sporting checkpoints.

The remapper emits exact source->target maps for match inputs, results, match effects,
terminal checkpoints and slot starts. Those maps are the evidence contract already
consumed by sporting v2.

The core adapter intentionally remains fail-closed if any auxiliary Simulation Slot
authority collection is non-empty (commands, schedules, adopted tournament authority,
entry fields, WC/draw authority trees, etc.). Those broader identity trees require their
own remappers and are not silently copied.


## Materialized Branch fork: coupled sporting v2 + Slot core install

Materialized ranking-bearing Branch forks now orchestrate player sporting history and
the completed Simulation Slot core together in canonical week order. Each target
sporting snapshot becomes the opening authority for that week's target Slot ledger; the
rebuilt Slot results, match effects and terminal checkpoint then rebuild the completed
sporting v2 context that feeds the next sporting snapshot.

The remapped sporting component and Slot core component are both written into the
target-owned materialized Saved Revision and installed into target Branch persistence
inside the same fork transaction. A Slot component without captured sporting history
fails closed rather than being copied with source Branch identity.

Auxiliary Slot authority trees remain separately guarded.


## Branch fork: Week Schedule and legacy adopted tournament authority remap

Materialized Branch forks can now preserve two additional Simulation Slot auxiliary
authorities. WeekSimulationSchedule is rebuilt with the target Branch and receives new
schedule/request fingerprints while preserving canonical slot/group chronology.

Adopted Tournament Authority history is also rebuilt when its frozen evidence is
Branch-independent (legacy/no-Draw evidence). Its authority fingerprint is recomputed
against the target Branch using the canonical authority fingerprint algorithm.

Authorities carrying Draw fingerprints remain fail-closed until the Draw authority
tree has an exact source->target mapping. Simulation command receipts also remain
fail-closed because their result payloads are schema-specific and must not be copied
blindly.


## Branch fork: Tournament Ranking Snapshot authority remap

TournamentRankingSnapshotAuthority is now rebuilt against the target Branch's remapped
Official Ranking snapshot for the same ranking week. The target authority preserves
event identity and adoption command provenance while receiving target Branch ownership,
target ranking snapshot identity and a newly computed authority fingerprint.

Trusted materialized ranking installation now accepts these remapped tournament-ranking
authorities. Season Closing authorities remain fail-closed.

This is the required first dependency for safely rebuilding Entry Field and the
downstream WC/Draw authority chain.


## Branch fork: Entry Field -> Wild Card -> Draw Input chain

Materialized Branch forks can now rebuild the canonical pre-draw tournament authority
chain after Tournament Ranking Snapshot authority has been remapped.

Tournament Entry Field history is replayed version-by-version against the target
Tournament Ranking Snapshot authority. Frozen Entry Applications receive target Branch
ownership, application fingerprints and command request fingerprints are recalculated,
and predecessor field chains are rebuilt.

Canonical Wild Card authority is then replayed against the target terminal Entry Field,
preserving frozen nomination/reserve/unavailability/audit evidence while rebuilding
Branch, field binding, request and authority fingerprints.

Tournament Draw Input authority is finally replayed through the canonical builder using
the target ranking authority, target terminal field and target WC authority. Its ranking,
field, WC, request and authority fingerprints are therefore target-local rather than
copied from the source Branch.

Draw generation/revision/process authority remains the next downstream boundary.


## Branch fork: draw-backed Adopted Tournament Authority v6 remap

Materialized Branch forks now carry canonical draw-backed Adopted Tournament Authority evidence once the source Tournament Draw has an exact target mapping. Each adopted tournament bundle is decoded and validated against its stored source authority fingerprint, every Draw authority fingerprint is rebound through the source-to-target Draw map, the canonical v6 package is re-encoded, and the week authority fingerprint is recalculated under the target Branch identity.

Legacy adopted tournament evidence without Draw binding remains supported unchanged. Draw-bound evidence fails closed if any referenced source Draw lacks a target mapping. Draw Revision history is still intentionally unsupported; revision-specific replacement cutoff, Lucky Loser, Wild Card repair and replacement-source evidence must be replayed before revised Draw fingerprints can participate in adopted authority remapping.


## Branch fork: basic Draw Revision replay

Materialized Branch forks now replay the canonical ordinary withdrawal revision chain for `full_redraw`, `seed_cascade_phase`, and `draw_frozen_phase`. Replay occurs after completed Simulation Slot evidence has been remapped, so embedded player replacement-cutoff authorities are rebuilt under the target Branch and any played-match result fingerprints are rebound through the target result map. Successor Entry Field, Draw Input, Draw, revision request identity and revision fingerprint are rebuilt canonically rather than copied.

Every rebuilt revision successor Draw is added to the source-to-target Draw fingerprint map, allowing draw-backed Adopted Tournament Authority v6 to bind to a revised active Draw. Repair-specific `frozen_wild_card_repair`, Lucky Loser, frozen ordinary fallback and source-bound pre-Q promotion revisions remain fail-closed for their dedicated dependency replay slices.


## Branch fork: specialized Draw Revision replay

Materialized Branch forks now replay the remaining specialized Tournament Draw Revision authority families in the same revision lineage as ordinary phase withdrawals: frozen Reserve Wild Card repair, Lucky Loser vacancy, Lucky Loser fill, frozen ordinary fallback, and source-bound pre-Qualification promotion. Frozen nested evidence is retargeted through the accumulated source-to-target authority graph and then revalidated by its domain model before the canonical revision builder creates the target successor Draw.

The shared mapping graph covers Branch identity, Tournament Ranking authority, Entry Field, base Wild Card authority, Draw Input, initial and revised Draw authorities, Draw Process authority, authoritative match result fingerprints, and Qualification bracket fingerprints used by Lucky Loser auto-BYE evidence. Each specialized successor Draw/Input/Field/revision fingerprint is fed back into the graph so mixed revision histories can continue chronologically and draw-backed Adopted Tournament Authority v6 can bind to the final revised Draw.

Unknown revision kinds remain fail-closed. The next fork-hardening work is focused on broader mixed-history coverage and restore/retry invariants rather than another unsupported Draw Revision family.


## Draw Revision restore / retry hardening

Saved Revision restore now treats Tournament Draw Revision identity as a full persisted command contract rather than payload-only history. Saved/replayed revision rows must bind their payload to the exact Run / Branch / event scope, and Tournament Draw Revision history recomputes the canonical request fingerprint for every currently modeled repair kind before accepting the row.

A PR-critical mixed-history scenario now freezes a full-redraw withdrawal followed by a Draw-Freeze withdrawal, captures that state, advances the live branch with a third revision, rejects a scope-corrupted restore target before mutation, restores the two-revision target, retries the restored second command idempotently without creating a duplicate revision, and proves request-fingerprint corruption fails closed. The restored simulation component fingerprint must equal the captured target fingerprint.


## Materialized fork -> restore exactness

Simulation Slot / tournament-authority installation now finishes with a full post-install recapture and fingerprint comparison. A restore or materialized Branch fork therefore succeeds only when the live installed Simulation Slot component is exactly the canonical target Saved Revision component after all Entry Field, WC/RWC, Draw Input, Draw, Draw Process and Draw Revision histories have replayed.

PR-critical coverage now spans a specialized frozen Reserve Wild Card repair on the source Branch, source-to-target Branch remap, exact target installation, a later second live RWC repair on the target Branch, restore back to the materialized fork root, and retry of the restored original RWC command. The target revision lineage remains target-owned, chronological and fingerprint-stable, while source and target revision fingerprints remain distinct.


## Branch fork: strict Lucky Loser / pre-Q frozen evidence remap

Specialized Draw Revision fork replay now treats Lucky Loser and replacement-source evidence as an explicit branch-owned authority graph rather than relying on permissive recursive string replacement. Draw, Draw Input, Ranking, Wild Card, played-result, Qualification bracket and derived auto-BYE terminal fingerprints must all resolve through a target mapping or the fork fails closed.

Lucky Loser v2 auto-BYE terminals are rebuilt first against the target Qualification bracket. Their derived evidence fingerprints are then recalculated and used to rebuild `qualification_terminal_result_fingerprints`, preventing a target LL order from retaining the source Branch's auto-BYE evidence hash. The LL v2 domain model also validates that each embedded auto-BYE terminal's derived fingerprint exactly matches the stored terminal-evidence fingerprint, so stale or partially retargeted evidence fails closed even outside the fork adapter. LL candidate elimination results, vacancy cutoff/start evidence, fill order evidence and source-bound replacement authorities are rebuilt against the same target graph. The LL v2 domain validator now also requires every auto-BYE terminal fingerprint to equal its embedded auto-BYE evidence fingerprint, so this binding is enforced outside the fork adapter as well.

PR-critical coverage exercises the derived auto-BYE fingerprint correction, explicit failure on missing LL result mappings, direct replacement-source rebinding, and a full source-bound pre-Q promotion Saved Revision -> Branch remap -> target materialization -> exact revision retry flow.


## Real Qualification receipts -> Lucky Loser fork/restore acceptance

Branch-fork recovery now has PR-critical coverage driven by real authoritative Qualification match receipts rather than mocked LL evidence. A canonical four-player Qualification bracket executes both semifinals and its terminal through `AuthoritativeSlotMatchExecutor`, producing protected match inputs, result fingerprints, player sporting effects and slot checkpoints in the normal Simulation Slot ledger.

That real Q history then feeds a chronological Lucky Loser vacancy + fill pair on the source Branch. Materialized fork remap must rebind the Q terminal and candidate-elimination result fingerprints into the target LL order, install the target-owned revision chain exactly, allow a second LL vacancy/fill on the target Branch, restore back to the fork root, and preserve exact retry identity for the original LL fill command. The final target component fingerprint must return to the materialized fork-root fingerprint after restore. The acceptance also exposed and closes a canonicalization gap in the fork adapter: remapped Slot rows and Group rows are now ordered with the same keys as Saved Revision capture before the aggregate component fingerprint is calculated, so non-lexical slot IDs cannot make a valid materialized fork fail exactness.


## Match Day Schedule V1 hard-constraint foundation

New automatically derived Week Simulation Schedules use `week_simulation_schedule.v2`. Historical/manual `v1` schedules remain readable and retain their original fingerprint payload contract.

V2 separates **Match Day chronology** from the global Simulation Slot axis. Every competitive match owns exactly one global match slot. Matches sharing one Match Day carry a deterministic `match_order` and therefore execute sequentially; later matches are created from the sporting checkpoint produced by earlier matches rather than sharing a simultaneous pre-slot snapshot. This makes current Form/Sharpness/Fatigue/stamina consequences visible to later matches on the same day.

The current canonical proposal derives hard constraints from frozen tournament topology:
- Qualification competitive rounds precede Main Draw rounds for the same event.
- Every feeder match is scheduled on an earlier Match Day than its dependent match.
- A directly known player cannot be assigned to two matches on the same Match Day.
- Within-day order is deterministic from event / phase / round / bracket position / match identity.
- Entry and WC decision global ordinals remain reserved and are skipped by match slots.
- Admin preview/adoption remains immutable, CAS-guarded and exact-retryable; Branch fork and Saved Revision handling preserve the V2 metadata.

This is deliberately the **single-week pre-alpha Match Day foundation**, not the finished generic tournament scheduler. Calendar-spanning multi-week Round Schedule ranges, explicit rest-day ranges beyond the current next-round/day rule, court allocation, cross-event travel/acclimatization, carryover optimization and fairness scoring remain follow-up policy/optimization work. See `docs/MATCH_DAY_SCHEDULE_V1.md`.


## Manual Match Day Schedule editor

Simulation Admin can now branch from the canonical `week_simulation_schedule.v2` proposal into an explicit manual Match Day review flow before adoption. Admin edits only Match Day and within-day priority; event/phase/round/group identity remains frozen from the canonical proposal. The client reuses the proposal's already-reserved global ordinal pool, then the server revalidates the edited schedule against the same hard constraints used for automatic proposals.

The manual preview is non-persistent and returns a schedule fingerprint plus a position fingerprint bound to both current canonical simulation state and the exact edited schedule. Commit therefore adopts only the reviewed payload; any later edit or concurrent simulation change makes the review stale. Backend PR-critical coverage proves that one round can be deliberately split across multiple Match Days while feeder dependencies still require a later dependent day.

This is the decided Admin-edit foundation from Master §13.4. Automatic lexicographic fair-rest optimization, carryover from the previous week, schedule-quality scoring and minimal-range reflow after later withdrawals/replacements remain follow-up work.
