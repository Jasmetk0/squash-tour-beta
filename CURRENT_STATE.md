# Current implementation and next action

Audited 15 September 2026 from merged PR #728 at `fbcb54d3ccea8f1c0c2b61c56a94a85767f36b84`, plus the narrow authoritative repeated-simulation driver in this branch.

This branch adds the first Run/Branch/Week/global-slot-owned competitive match execution path: frozen same-slot inputs, complete Match Engine replay evidence, exactly-once Form/Sharpness/Fatigue effects, intra-week checkpoints, later-slot causal consumption, Saved Revision capture/restore, and terminal-state handoff to Weekly Development. See `docs/AUTHORITATIVE_SIMULATION_SLOT_MATCH_EFFECTS_V1.md`.

PR #728 review hardening preserves owned InitialWorld style/profile truth, carries Form/Sharpness/Fatigue as distinct match inputs, makes any planned slot authoritative even before its first group commit, enforces feeder topology/global ordinals, and semantically revalidates replay and Saved Revision slot chains.

The follow-up compatibility correction assigns Sharpness-aware matches to `match_input_snapshot.v10` / `match_engine_v10`; v1-v9 hash payloads continue to omit the later Sharpness field and retain their historical identities.

The single supported persisted four-player Main Draw retains its explicit compatibility projection into the Run/Branch/week slot ledger and back through tournament completion, authored awards, ranking validation and `OwnedTournamentRankingSource`; every completion ref retains the exact Slot result fingerprint. Multiple same-week events fail closed before mutation because current persisted data has no authoritative mapping onto the global Simulation Slot chronology. Legacy calendar `start_day`, calendar/list order, event identity and draw-round arithmetic are not treated as that missing authority. Gate 3 is not complete: Entries, general draws, Qualification, WC/LL, cross-event scheduling, AI, health and broader event types remain gaps.

This file is an evidence/index snapshot, not product authority.
Always verify the current remote head before acting. Product rules and decision
statuses live in [Master Vision](SQUASH_ENGINE_MASTER_VISION.md); the development
protocol is chapter 36. PR #728 is the latest verified merge.

## What exists, and where integration stops

| Area | Evidence in audited code | Remaining boundary |
|---|---|---|
| Run foundation | `application/run_container_creation_service.py`, `run_working_draft_service.py`, `run_saved_revision_*`, DB revision models | New Run roots/revisions coexist with legacy simulation identities; full sporting state is not covered by every save/restore path |
| Branch isolation/recovery | `infrastructure/db/repositories.py` validates ancestry, receipts and checkpoints; rejects ranking-bearing forks | Ranking identity remapping and complete sporting-world recovery remain |
| Packages/players | World package, owned InitialWorld, lifecycle, `player_sporting_week_states`, and slot checkpoints | Canonical 57×0–200 sporting history and match-derived Form/Sharpness/Fatigue exist for the narrow slot slice; health and prospects remain open |
| Tournament flow | `season_event_simulation_service.py`, result/award services, `owned_tournament_sources.py`; real producer/API/SQLite test | Supported four-player main draw can be explicitly adopted as immutable Run/Branch evidence; producer files remain legacy/global and Q/WC/LL/abnormal sources remain rejected |
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
tournament-to-ranking bridge are implemented, not future gaps. Multiple same-week
events, Qualification, non-four-player draws and ambiguous scheduling continue to
fail closed.

The narrow repeated-flow acceptance now drives two distinct persisted four-player
events through production authoritative HTTP commands and real Week Transition
preview/confirm boundaries from Week 1 to Week 3. It saves the simulation component,
preserves frozen tournament authority and verifies historical Week 1 replay, two
owned sources, immutable published rankings and the three-week sporting chain.
The real SQLite application regression proves that two persisted same-week events
are rejected before any adopted authority, command, slot, group or owned tournament
source is written. No multi-event execution or general scheduler is claimed.
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
