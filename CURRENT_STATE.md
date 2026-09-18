# Current implementation and next action

Re-audited 18 September 2026 from merged PR #757 at
`0b3441909f89983e97e12d342c0835db63fb7654`, plus the current bounded
canonical Tournament Entry Field Admin HTTP slice. The audit compares merged code against the
canonical Master Vision instead of treating PR descriptions or Fast CI as product
authority.

This branch adds the first Run/Branch/Week/global-slot-owned competitive match execution path: frozen same-slot inputs, complete Match Engine replay evidence, exactly-once Form/Sharpness/Fatigue effects, intra-week checkpoints, later-slot causal consumption, Saved Revision capture/restore, and terminal-state handoff to Weekly Development. See `docs/AUTHORITATIVE_SIMULATION_SLOT_MATCH_EFFECTS_V1.md`.

PR #728 review hardening preserves owned InitialWorld style/profile truth, carries Form/Sharpness/Fatigue as distinct match inputs, makes any planned slot authoritative even before its first group commit, enforces feeder topology/global ordinals, and semantically revalidates replay and Saved Revision slot chains.

The follow-up compatibility correction assigns Sharpness-aware matches to `match_input_snapshot.v10` / `match_engine_v10`; v1-v9 hash payloads continue to omit the later Sharpness field and retain their historical identities.

The tournament bridge freezes a v4 Run/Branch/week authority bundle and consumes a canonical executable DAG built from persisted match IDs, direct slots and `winner_to_match_id` evidence. Production-backed eight-player/seven-match Main Draws now repeat across three completed authoritative weeks with explicit schedules, Week Transition and replay. Qualification promotion and unambiguous one-player BYE evidence execute through the same closure/ranking path. PRs #738–#740 also added persisted Wild Card and withdrawal/replacement provenance primitives. A post-merge Master Vision audit found that those primitives are not the completed repair workflow: overlapping entries may remain provisional until commitment authority; pre-draw withdrawals must rebalance Main/Qualification field cuts from the Tournament Ranking Snapshot; and post-draw repair must honor redraw/cascade/freeze phases, Lucky Loser priority and the first-real-match replacement cutoff. This correction branch removes the #737 automatic preferred-tournament choice and fails closed before play when overlapping commitments remain unresolved. Historical v1-v3 four-player readers remain compatible. Legacy `start_day`, list order and round-name text are never chronology authority.

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
| Week execution | `infrastructure/db/authoritative_week_transition.py` owns one `BEGIN IMMEDIATE`; owned complete tournament result manifests can resolve completed-match counts | Sporting development then between-week recovery, lifecycle, ranking/publication/event/receipt share the transaction; a missing/empty authoritative sporting context fails closed, while broader match-state updates, slots and prospects remain outside it |
| Season rollover | `rollover_service.py`, `run_bootstrap_service.py` use persisted MVP rollover/legacy simulation runs | Not the Master Season Closing + new-policy Week 1 + final Run completion contract |
| Viewer/downstream | Legacy ranking/Race/Finals paths and Viewer exist | New Official history is not wired through historically faithful public ranking, entries/seeding and Finals |
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
  fingerprint inspection and optimistic mutation guards. The legacy simulation-run
  endpoint/UI remain non-canonical. Post-draw repair phases, RWC/WC repair, LL
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
tournament-to-ranking bridge are implemented, not future gaps. Multiple same-week events without an adopted explicit schedule, Qualification, non-four-player draws and ambiguous scheduling continue to fail closed.

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
replays every award. `OwnedTournamentRankingSource v3` binds canonical result and
point authorities while retaining self-consistent legacy-shaped DTOs only for
compatibility. Ranking-week ingestion materializes `RankingResultVersion` directly
from v3 authorities and does not require `SeasonPointAwardsService`.


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
repairs. The current follow-up adds canonical Run/Branch Admin HTTP inspection and
mutation routes; they do not reuse or reinterpret the older simulation-run endpoint.
Legacy UI/endpoint retirement, RWC/WC repair, Qualification redraw/cascade/freeze
phases, Lucky Loser ordering and the per-player first-real-match replacement cutoff
remain Gate 3 work. See
`docs/CANONICAL_PRE_DRAW_WITHDRAWAL_V1.md`.