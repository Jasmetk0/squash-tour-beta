# Current implementation and next action

Audited 12 September 2026 against `buuk` **08a29074250675a61434ba58fb42a185474648d5**
(PR #720 merged). This file is an evidence/index snapshot, not product authority.
Always verify the current remote head before acting. Product rules and decision
statuses live in [Master Vision](SQUASH_ENGINE_MASTER_VISION.md); the development
protocol is chapter 36. The proposed documentation synchronization is not yet
merged at the time of this snapshot.

## What exists, and where integration stops

| Area | Evidence in audited code | Remaining boundary |
|---|---|---|
| Run foundation | `application/run_container_creation_service.py`, `run_working_draft_service.py`, `run_saved_revision_*`, DB revision models | New Run roots/revisions coexist with legacy simulation identities; full sporting state is not covered by every save/restore path |
| Branch isolation/recovery | `infrastructure/db/repositories.py` validates ancestry, receipts and checkpoints; rejects ranking-bearing forks | Ranking identity remapping and complete sporting-world recovery remain |
| Packages/players | World package, initial pool, season bootstrap and Run prospect services | File-backed `SeasonActivePlayer` is not proof of authoritative Branch/week roster/lifecycle resolution |
| Tournament flow | `season_event_simulation_service.py`, result/award services; `docs/TOURNAMENT_INTEGRATION_STABILIZATION.md` | Four-player main-draw path exists; Q/WC/LL and complete scoped lifecycle are not certified by that test |
| Match engine | `domain/matches/match_engine.py`, immutable input/format contracts and recorded replay; Master 35.9–35.20 | Stored match/replay does not prove whole-world mid-match restore, global slot scheduling or finished realism |
| Official ranking | `domain/rankings/official.py`, `application/ranking_week_command.py`, DB ranking stores/runner | Candidate computation/history exists; full authoritative source/roster/policy resolution and world publication do not |
| Ranking Admin | `admin_ranking_candidates.py`, `RankingPreparationPanel.tsx`, `RankingResultCorrections.tsx` | Preview/confirm, manual input review, zeros and stored-result corrections; new tournament ingestion is explicitly rejected at the API boundary |
| Ranking Save | `saved_revision_rankings.py`, `ranking_revision_state.py`, `ranking_state_restore.py` | Verified component recovery, not full sporting-world recovery |
| Week execution | `season_week_simulation_execution_service.py` declares `NO_ROLLBACK_WARNING` | Legacy event loop is not the atomic Master Week Transition; snapshot service copies active-player totals |
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
- No full-suite, browser E2E, whole-season or full-Run execution in this task.
  Earlier baseline failures are not silently cleared. Docs CI validates docs only.

## Best next implementation slice

**Scoped completed tournament → Official ranking candidate → Save/reload/restore.**
This removes the concrete source-ownership blocker before attempting the atomic
Week Transition. Do not spend the next PR on deeper ranking UI, Protected Ranking
or realism calibration. Next, integrate authoritative world/player/policy state and
Week Transition in Master order; see [ROADMAP.md](ROADMAP.md).

## Ready-to-paste Codex prompt

```text
Work in Jasmetk0/squash-tour-beta. Implement one coherent vertical slice:
real persisted supported main-draw tournament results and awards -> independently
owned Run/Branch-scoped source snapshot -> next Official ranking candidate ->
explicit Save -> reload and supported restore, preserving audit and history.

Why now: after #720 the ranking API can correct stored results but rejects new
tournament bindings because legacy files do not prove product Run/Branch ownership.
That boundary blocks useful ranking/world integration. Fix the boundary before
attempting a full Week Transition; do not merely add another candidate-only form.

Before editing, fetch current buuk, inspect AGENTS.md, SQUASH_ENGINE_MASTER_VISION.md
(especially 6.5, 18, 31 and 36), CURRENT_STATE.md, ROADMAP.md and the actual source.
Do not assume the old baseline 08a29074250675a61434ba58fb42a185474648d5 is current.
Preserve newer work. Verify the documentation synchronization has been merged;
if not, read it from its PR without overwriting unrelated changes.

Inspect existing production paths before deciding the smallest implementation:
- application/ranking_tournament_ingestion.py and its tests: supports ordinary
  completed main draws; rejects qualification/BYE/W/O/RET and unauthored awards.
- season_event_simulation_service.py, season_event_results_service.py,
  season_point_awards_service.py and tournament integration tests.
- infrastructure/db/repositories.py: prepare_official_ranking rejects tournaments;
  new RunContainer/RunBranch/revision models coexist with legacy simulation mappings.
- ranking_week_command.py runner/stage/preview, result history and input manifests.
- saved_revision_rankings.py, ranking_revision_state.py, ranking_state_restore.py
  and independent Save/restore API tests.
- API preparation router and web preparation/confirmation transport if touched.
All paths are under src/beta_engine unless stated. Verify current paths yourself.

In scope:
1. Establish a persisted, verifiable source ownership boundary for one supported
   completed tournament. Reuse authoritative existing mappings where they actually
   prove ownership. Otherwise use an explicit audited adoption/import of an
   independent frozen snapshot into the selected Run/Branch, with honest provenance.
   A request's run_id/branch_id, identical event name, path or hash alone is not
   proof that global source data belongs to that branch. Never silently relabel it.
2. Validate the full source snapshot, completion boundary, identities, result/award
   fingerprints and authored points before mutation. Read later computations from
   this frozen owned snapshot, not a live global file. Decide storage technically
   using existing versioned component patterns; avoid a second generic state engine.
3. Connect the source to the existing audited ranking preparation command with
   production preview, confirmation and exact retry. Reuse the current calculator,
   ingestion validation, version history and manifests. Freeze the provenance used
   by the calculation. Reject changed/stale preview inputs before any partial write.
4. Include every newly authoritative persisted record in compatible Save/reload/
   restore semantics, or atomically preserve its full evidence in an existing
   captured component. No hidden table outside recovery. Keep old revisions readable.
5. Provide a usable explicit Admin command/API flow. Reuse existing UI controls
   where sensible; add only the minimum selection/review surface needed for this
   slice, without visual redesign. No raw database edits required for normal flow.

Non-goals: full Week/Season Transition, advancing world time, public publication,
Protected Ranking, automatic sanctions, broad Q/WC/LL/abnormal result support,
ranking-bearing branch remapping, realism tuning, visual polish or unrelated cleanup.
This does not remove any of those requirements from pre-alpha. Preserve current
unsupported-scope guards. Do not invent a sporting rule to make the demo pass.

Invariants: deterministic domain calculations and injected RNG; immutable original
result timing/expiry; isolated Run/Branch and historical snapshots; no future inputs;
operation-scoped validation; preview has no writes; source adoption + ranking writes
form the declared atomic command; error rolls back all of it; idempotent exact retry;
Viewer reads saved state and never becomes authority; Save stays explicit; old
payload hashes/receipts remain valid or receive an explicit backward-safe migration.
If an explicit import ownership choice truly changes undecided product behavior,
finish the technical investigation and ask the owner that precise question rather
than assume an answer or ask generic technical questions.

Acceptance criteria and integration evidence:
- A fresh Run and a real isolated four-player main-draw production pipeline can
  yield authored results/awards, explicitly adopt them in the intended Branch,
  preview the next candidate, confirm, Save, reopen and inspect the same points,
  source hashes, timing and audit without manually inserting result rows.
- Production service/API + real file-backed SQLite, not mocked award producers.
- Preview database/source state is unchanged. Inject a failure after source staging
  and after ranking staging: no partial state/receipts or changed draft remain.
- Lost-response retry uses the same command; repeats do not duplicate anything;
  changed payload/lineage conflicts. Editing source after preview rejects commit
  or leaves the explicitly frozen snapshot unchanged under the documented contract.
- Two Runs/Branches with colliding event names cannot leak sources. Cross-scope,
  wrong hash, future week and unsupported source cases reject without mutation.
- Save/reload and restore before/after adoption preserve the complete new evidence;
  older revisions still load. Existing unsupported fork guard stays safe.
- Earlier ranking/source history is unchanged; original validity is never restarted.
- Run relevant regression tests, static checks/build and UI tests if touched. Say
  which boundaries are mocked; never call those full integration. Add critical
  tests to the appropriate CI gate. No unnecessary full-suite repetitions.

After implementation do a distinct review for scope, rollback, retries, migration,
Save/Restore, source completeness and preview/commit drift. Fix material findings.
Update CURRENT_STATE.md and affected scoped contract docs truthfully. Do not inflate
Master with per-file PR logs or mark this as full Week Transition/pre-alpha.
Open one reviewable PR against buuk, report changed files and why, actual test
results, remaining boundaries and recommended next step. Do not merge it yourself.
```
