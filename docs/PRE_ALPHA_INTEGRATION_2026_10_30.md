# Post-merge pre-alpha evidence map — 30 October 2026

## Audited baseline and authority

Merged `buuk`: **`d45b7d3b3aa7e585e3c777cb166c6c5f2bb2f81d`**, tree
`307c44b66b503c1b2c27a7ed83c0eab2f7c995a2`. All twelve PRs #1661–#1672,
including the final documentation head ce6395b8, are merged. No PR was open when
this audit began. Reconstructing those exact heads produced the identical tree;
no merge content was lost. Refresh GitHub before beginning later work.

Master **v86** and newer explicit owner decisions remain product authority. This
map is implementation/evidence indexing in the EXISTING checkpoint document,
not a second Master or PAQ registry. No product status/count/ID is changed. The
section ranges below account for all **157** original PAQ IDs once; later §31.25–40
consolidations override older summaries and are covered separately below.

**Evidence legend:** E = a named scenario actually executed (scope stated);
I = implementation/contract inspected or located, not an execution claim;
U = requirement not established by this audit, not proof that every implementation
is absent. D = explicit Master deferral/exclusion only. An E within a grouped row
never closes every question in that row. RESOLVED describes a product answer;
merged code and passing scoped tests are separate axes. No completion percentage
is calculated from PR/test/PAQ counts.

## Current integration evidence and limits

- The pre-merge disposable combination of these exact candidate contents passed
  113 frontend component/value tests across 16 files, TypeScript/Vite build and
  92 selected backend/domain/cache/profile tests, including actual copied-FAX
  HTTP/SQLite source/Entry/continuation/reopen scenarios. These are historical
  execution results for contents reconstructed above, not a full release suite.
- #1662's final head e1f7c578 passed 56 hosted checks, including 49 actual native
  acceptance jobs. All-week W52/W61/W80, sparse competition, native Save/fork,
  worker and browser scopes remain distinct. They were not rerun for this docs PR.
- #1671's final head b36eed8e passed actual 1,000-player/80-Edition preparation,
  source/hash/concurrent-read guards and restart. #1672 d2fc8c86 passed actual
  pending-command continuation, audit/retarget rejection, Pause/Resume and restart.
- Sonar is advisory per owner: merged #1669 has D Reliability, #1671 C Security/D
  Reliability with unavailable issue details. Findings are unclassified, not
  declared fixed/false-positive. Do not convert green functional checks into a
  security clearance. No branch protection was changed.
- The post-merge spot-check results are recorded below after execution. A docs
  audit is NOT an official internal release: the complete backend/frontend suite,
  assigned browser/recovery flows and full reference season/50 seasons remain
  required at the explicit release gate (`docs/PRE_ALPHA_TEST_POLICY.md`).

## Coverage of the original PAQ gate

Product statuses remain exactly those of the linked Master sections, including
partial, testing, deferred and excluded parts. The rows describe runtime/evidence
boundaries, not replacements for those statuses. Paths are repository-relative.

| PAQ IDs | Authority / requirement | Implementation / evidence entry point | Remaining blocker or uncertainty | Priority / next action |
| --- | --- | --- | --- | --- |
| 001–006 | §31.3; two Admin flows, 1,000/80 reference, 50-season acceptance | E: `tests/application/test_standalone_match_acceptance.py`; real copied-FAX preparation in #1671/#1672 | Full reference season and 50-season completion NOT proven. Four-player legacy season is not reference scale. | Release gate; progressive integration |
| 007–013 | §31.4; stable identities, provenance, effective versions, missing values, migration | I/E: typed Run/Package models, `src/beta_engine/application/run_calendar_read_authority.py`; #1671 authenticates original Saved hash | Scoped integrity is implemented; comprehensive schema/migration/entity matrix not re-certified. | Preserve; release recovery audit |
| 014–021 | §31.5; drafts, Saved histories, forks, Undo/recovery, Compare | I/E: `src/beta_engine/application/run_working_draft_service.py`, `src/beta_engine/application/run_saved_revision_history_service.py`; native final-head gates in #1662 | Saved/fork evidence does not close all retention, candidate-future or cross-Run Compare requirements. | Preserve; audit remaining UX/history |
| 022–029 | §31.6; partial Packages, dependencies, divergent versions, export/Setup | I: `src/beta_engine/application/run_package_service.py`, `tests/api/test_run_package_api.py` | Partial apply/review exists. Complete portable Run/Package archive, migration and own partial export not demonstrated by this audit. Player/Hybrid schema still follows its Master status. | Release blocker until round-trip located/proven |
| 030–037 | §31.7; simultaneous slots, Week/Season transitions, tasks, terminal closure | E: #1662 unchanged native API/browser/worker matrices; `src/beta_engine/application/native_full_simulation.py`; #1672 actual continuation/pause/retarget rejection | Sparse sporting schedules with all-week transitions are not a full 80-Edition World Tour season. | Integration prerequisite |
| 038–044 | §31.8 plus §31.38; pool, intake, identities and historical regeneration | I/E: `src/beta_engine/application/native_calendar_cohort_service.py`; 1,000 actual generated players in #1671 | 15-year native intake exists; full initial historical-cohort survival/development and regeneration/locks contract not established by roster count. | Required initial-population audit |
| 045–053 | §31.9; 57 attributes/0–200, potential, OVR, development/Form/training | I/E: `src/beta_engine/domain/players/sporting.py`, native sporting tests in #1662 | Canonical records/selected transitions exist. Do not certify all formula/default/training/gameplan requirements from attributes being stored. No new calibration requested. | Preserve provisional versioned defaults; verify contract coverage |
| 054–062 | §31.10 plus §31.28; fatigue/stamina/mental/health/travel | I: `src/beta_engine/domain/players/health.py`, `tests/domain/test_match_stamina.py`, `tests/domain/test_calendar_native_health_preparation.py` | Required health consequences and source continuity exceed a fresh-health baseline. Full travel/mental/recovery and return-risk coverage not re-certified. | Required sporting coverage; no realism campaign now |
| 063–073 | §31.11; authoritative rally engine, format, timing, replay | I/E: `src/beta_engine/domain/matches/match_engine.py`; actual native MatchEngine and replay gates; Reconstruction test below | Actual match kernel exists. Entire incident/config inheritance/timing matrix is separate from one completed match. | Preserve; match-level regression at release |
| 074–082 | §31.12; Edition hierarchy/lifecycle, public knowledge and schedules | I/E: `src/beta_engine/domain/tournaments/calendar_tour.py`; native groups/global-slot gates | PAQ-080 historical RESOLVED is superseded for first-release scope by §31.28: extraordinary tournament lifecycle excluded; individual RET/W/O/DQ retained. Full inherited-plan/public-stage coverage unverified. | Core required; excluded extraordinary lifecycle stays excluded |
| 083–094 | §31.13 plus §15.1/31.26/31.29; Entry, Q, WC/LL, draws | I/E: `src/beta_engine/domain/tournaments/application_validation_authority.py`, `src/beta_engine/application/pre_alpha_fax_current_week_ranking_snapshots.py`; #1671 real shared-snapshot Entry | Validity outcome DTO is not an automatic validator. Main 2 + Q 1 weeks and ranking Main Closing Week − 1 already decided. Saved timing/eligibility/source binding missing from the proven reference flow; some cut-offs genuinely remain open. | NEXT: bounded Saved Entry timing/preflight slice |
| 095–102 | §31.14 plus §18.4/31.29; Official/Closing ranking, points, PR, discipline | I/E: `src/beta_engine/application/season_category_points_service.py`; #1671 preserves authored zero vs missing points | Reference baseline lacks complete qualification awards; disposable zero awards are not chosen canon. Full PR-case consumption/qualification composition/discipline coverage not certified. PAQ-101 prize money and separate Live Ranking are not required. | Content/policy dependencies; do not invent awards |
| 103–110 | §31.15 plus §31.27; minimum Reconstruction, isolated candidates, explicit selection | E: `tests/application/test_match_reconstruction_run_save_restart.py` actually selects a genuine match and verifies Saved/reopen/replay | Single knockout match does not prove full constraints catalog, group ties or no-candidate UX. Forcing and advanced naturalness remain deferred/testing per Master, not newly required. | Retain minimum; scoped recovery/constraint review |
| 111–118 | §31.16; AI knowledge, portfolio, health/retirement, Admin override | I/E: shared-snapshot Entry in #1671; `src/beta_engine/application/season_entry_batch_service.py` | AI proposal is not validated participation. Full knowledge/retirement/health/gameplan coverage unverified; simple versioned AI is allowed, exact weights are later calibration. | Supports Entry path; no global perfect-AI prerequisite |
| 119–126 | §31.17 and §31.30–36; usable CS/EN Admin, historical context, errors | I/E: `src/beta_engine/application/run_home_readiness.py`; existing scoped Admin and Lab browser gates | Readiness currently covers World/Calendar/population/health/ranking/draft; not every required setup/export step. PAQ-120/121 Viewer pages/counterparts not first-release gates. New Viewer PRs do not close Admin coverage. | Admin flow before further Viewer |
| 127–134 | §31.18; determinism, seed, rollback, audits, golden fixtures, performance/recovery | E: #1662 source/physical/Save gates and paired measurements; #1671 real rehash/concurrent-read rejection; #1672 exact retry/control/reopen | No owner-hardware SLA selected; 64 MiB is input-byte budget, not heap cap. Two timing samples are not a stable speedup. Full release regression, backup/import recovery still outstanding. | Preserve invariants; release gate |
| 135–142 | §31.19 plus §31.26/28; FAX content, World Tour, Finals, lower Tours | I/E: `src/beta_engine/application/pre_alpha_fax_acceptance_calendar_source.py`; FAX source hash + 1,000/80 preparation in #1671 | 80 fixture Editions are not 80 played Editions. Finals qualification/selection/full competition and lower-Tour aggregate consequences not proven by native groups or Viewer Race. Final content/hierarchy/awards not selected by tests. | Blocking reference-season content/integration |
| 143–150 | §31.20 plus §31.25–28; representation/history/events/H2H/Labs/concurrency/import | I/E: `src/beta_engine/application/historical_lab_source.py`, `tests/api/test_historical_lab_copies.py`; 3 Lab services/workflow exist | Three Lab minimum retained. Full notifications, watchlists, event producer/history and import boundary still require evidence. PAQ-150 Viewer reveal not required; public-knowledge invariants remain. | Required cross-cutting closure; no fourth mandatory Lab |
| 151–157 | §31.23; experience/sharpness/preparation/health/financial/branch naming | I/E: `src/beta_engine/domain/players/sporting.py`; native cohort/health records and existing Run creation | Stored sporting state is not proof of all formula/Financial Level/Match Preparation behavior. PAQ-154 advanced historical search has later/testing limits; branch naming product answer is not a new release pass. | Verify specific contracts; no new calibration constants |

## Later decided requirements that the original question list does not replace

| Master authority | Required behavior and inspected evidence | Remaining boundary / next action |
| --- | --- | --- |
| §31.25–27 | Global three Labs, cross-Run Compare, branch map, logical/selective Save/export, tray continuation, notes, Saved Views, watchlists, compact branch export, storage size, basic Records/holder history and rivalries are required, subject to their stated limits. Run/Branch Saved APIs and scoped Lab workflows exist. | No full portable Run archive/compact branch export/tray/watchlist/Saved Views delivery was established in the inspected application/router/UI paths. This is U, not a claim of repository-wide absence. Locate and exercise the real producer/persistence/consumer or implement the missing requirement before release. Do not silently defer the entire set. |
| §31.28 | Three Labs use shared models; permanent health consequences and return-risk history retained. Extra Talent Lab, team/junior/Olympic events, doping, prize money, detailed medical treatment and extraordinary tournament lifecycle are excluded from first release. | Keep required health/Player Lab proof separate from excluded mechanics; RET/W/O/DQ and ordinary discipline remain required. |
| §31.29 | Final Commitment defaults to end of Q Entry Window; PR consumption/continuing cases/non-stacking cases, RWC ordering, explicit identity restore backup and future-rally effort/gameplan edits already decided. | These are not all new questions for the owner. Verify each path and its original policy snapshot; exact calibration and remaining boundary cut-offs stay open. |
| §31.30–36 | Functional CS/EN Admin, historical objects, Saved notes, safe running console, task ownership, stop rules/notifications and nonblocking summaries. `src/beta_engine/application/full_simulation_summary.py` explicitly lists `ranking_changes`, `watched_events`, `notifications` as unavailable. | Concrete partial producer output, not a complete v81/v85 summary/notification implementation. Preserve the true scope in UI; close required sections later through their real data producers. |
| §31.37 | Fixed positive Run W/offset/year/horizon, one-way extension, original historical clocks and elapsed-year development. Native W52/W61/W80 gates provide scoped evidence. | Reference 50 seasons is a particular FAX acceptance configuration, not a universal limit or an invented full 50-season Cartesian test across all calendars. |
| §31.38 | Historical initial 15-year cohort model with pre-start development/retirement filtering; resumable preparation, operation-scoped readiness and selected content export. `run_home_readiness.py` explicitly exposes six item codes. | A 1,000-player generated roster and six readiness items do not certify the complete historical model or export/setup workflow. Preserve ordinary manual Save and existing owners. |
| §31.39 | Automatic total with exact partial quotas preserves unaffected players; extensible world/country/tournament records, holder history, leaderboards, combined filters and fixed/rolling Saved Views. Country Saved match record projections exist. | Record highlights are not a complete record-event ledger/Saved Views implementation. Full quota/identity-preservation and record-history contract needs separate evidence. |
| §31.40 | Personal milestones/career/retirement summary, followed-player and country notices, grouped alerts retaining individual history, national season comparisons. `calendar_tour_season_summary.py` has signed completed-season/national comparison projection. | Its pure tests use constructed summaries; this audit found 4 failures/2 passes because their Edition mock lacks schema_version. Repair that fixture/negative coverage before treating it as valid evidence. This does not establish a production summary defect or full milestone/notification producers. Existing projection is partial evidence, not a duplicate summary authority. |
| Newer explicit owner scope (FIFA/ATP Earth) | Both Earth Packages remain in pre-alpha scope. `src/beta_engine/application/earth_package_builder.py` and Package directories exist. | No new full country/year/attribute-content audit was performed here. Reconcile the owner's confirmed coverage with manifests/observations and actual copied-Run acceptance; file presence is not completeness. |

## §36.5 progressive integration ladder

| Stage | Actual boundary | Next proof required |
| --- | --- | --- |
| Empty Run → two manual players → Saved match/reopen | Existing actual acceptance; spot check below | Retain as independent release flow, not a substitute for World Tour |
| One actual sporting user flow | Native Tour/global slots API/browser evidence from reviewed feature heads | Reference content/Entry must participate in the same supported owner; no legacy/native state mixing |
| Complete week; Week N → N+1; several weeks | Native all-week matrices and sparse multi-tournament cases | Multiple real reference Editions, shared slot/entry state, manual Save/reopen without fixture repair |
| Whole reference season → Season Transition | Legacy whole-season test explicitly asserts four participants; sparse native season evidence separate | 1,000 initial players, all 80 actual World Tour Editions, Finals and abstract lower-Tour consequences on the same valid reference path |
| Multiple seasons → full 50-season FAX Run | Structured long probe currently stops; no complete required reference run verified | Only after prior stages: deterministic long-run, intake/lifecycle/history growth, recovery and original source protection |

The ladder orders evidence; it does not remove other decided release requirements.
A complete release needs the required side capabilities above as well as the two
main flows. Already excluded functions are not reinstated by this audit.

## Selected next vertical slice (technical recommendation, not new canon)

**Immediate maintenance PR:** restore the obsolete Edition fixture in
`tests/application/test_calendar_tour_season_summary.py` against the supported
typed Edition contract and rerun its positive/comparison/forged-input checks.
The production function now reads `item.schema_version` for v3 group semantics;
the mock Edition omits that required discriminator. Do not add a permissive
production fallback or weaken negative assertions merely to make the mock pass.
This is a bounded confirmed test-evidence defect, not an invented sporting rule.

**Following feature slice:** persisted per-Edition Entry timing/preflight and
ranking-source binding.

Why this first: the real 1,000-player/80-Edition probe has reached shared-snapshot
Entry proposals, but its generic hard-coded unresolved-policy label cannot say
which stored prerequisite is missing. The validity authority explicitly freezes
valid/invalid outcomes and says it does NOT implement eligibility/deadlines.
The current copied-FAX ranking helper picks the latest publication at/before the
current week; that bounded bootstrap is not proof of the canonical per-Edition
snapshot rule. Timing/source authority must exist before unattended validation
can safely resolve applications and feed a field/draw. This is a tighter technical
slice than inventing one global eligibility policy or jumping to a 50-season run.

Confirmed inputs to reuse (Master §15.1/31.26/31.29):

- Main Entry Window defaults to two weeks, followed by one Q week; Edition values
  can be explicitly overridden. Lengths do not specify a universal start lead.
- Default ranking is the existing Official snapshot after Main Closing Week − 1;
  explicit Edition selection may choose another existing snapshot. Do not silently
  substitute current ranking or synthesize pre-start history.
- Shared-snapshot/atomic slot publication, canonical identities and NR tokens,
  one historical application object, existing manual Save and original policy
  provenance remain; voluntary conflicts are not globally banned by week number.
- Exact extra decision-slot count, remaining late movement cut-offs, thresholds,
  future-start/pre-start fixture bootstrap and final FAX content are not silently
  chosen from the illustrative schedule. Missing inputs must be operation-scoped.

Implementation-ready boundary for the following runtime PR:

1. Inspect existing Edition/Calendar ownership and migrations before adding any
   field. Reuse normal Package/Working Draft Preview → explicit confirmation →
   Save and the Run calendar. Keep legacy/native command schemas separate.
2. Represent reviewed Edition window/closing/Final Commitment inputs with a
   historically effective snapshot. Apply decided duration defaults only where
   the required timing inputs are known; validate configured overrides/ranges.
3. Resolve the exact historical ranking source (or explicit reviewed override),
   then provide a read-only operation preflight: ready / missing content /
   unsupported execution / genuinely open policy, with a concrete reason/action.
4. Keep missing points/identity/lifecycle/timing/format checks separate. Do not
   auto-approve all proposals or import legacy Entry truth into native sporting
   state. Unsupported pre-start geometry must explain its gap, not clamp/modulo.
5. Verify actual HTTP/SQLite Preview non-mutation, stale reviews, exact retry,
   Save/reopen, source independence, Main/Q/closed boundaries and historical
   ranking selection, including missing predecessor and explicit override.
6. Stop only at a concrete remaining PRODUCT choice. Bring that one bounded
   choice to the owner with a recommendation; do not re-ask the decided 2+1 rule.

This slice should enable an Admin to inspect/save real Entry timing and receive
an honest validation prerequisite report. It does not itself promise all eligible
outcomes, final fields/draws, awards or a played season. Subsequent slices consume
that authority through existing validation → field → draw → actual MatchEngine →
points/Save/restart, then advance the integration ladder.

Priority comparison: portable archives/recovery, initial historical cohorts,
Records/notifications and other required side capabilities remain release blockers
or U until proven. They are retained in the map rather than discarded because
Entry was selected first. More Viewer polish and a realism/benchmark campaign
have lower immediate dependency value.

## Audit execution record

Baseline for the following fresh spot checks: d45b7d3b3aa7e585e3c777cb166c6c5f2bb2f81d.
Command: `PYTHONPATH=src:tests/application GITHUB_EVENT_NAME=workflow_dispatch python -m pytest`
with `tests/application/test_standalone_match_acceptance.py`,
`tests/application/test_match_reconstruction_run_save_restart.py`,
`tests/domain/test_application_validation_authority.py`, and
`tests/application/test_calendar_tour_season_summary.py --maxfail=1`.
Result: **8 passed, 1 failed in 15.14s**. The two production HTTP/SQLite flows
passed (2.98s empty-Run match; 5.73s Reconstruction Save/reopen); six typed
validation-outcome unit contracts passed, without claiming an automatic policy.
The summary module failed before completing; an isolated full-module run then
reported **4 failed, 2 passed in 0.11s**, all four failures at the missing
`schema_version` on its constructed Edition. Both failing runs are retained as
negative evidence, not renamed integration passes. No tests, timeout or runtime
code were changed in this documentation PR. No full regression or real browser
was run for this audit. These failures must be resolved in the follow-up
maintenance slice before summary evidence/release certification.

---

# Historical pre-merge checkpoint (superseded implementation snapshot)

The text below is preserved dated evidence. Its open/candidate labels describe
the earlier edd237b7 baseline; the current merged state and next task are above.
It must not be used as the current task queue.

# Current verified integration — 30 October 2026

This is the active implementation snapshot. Earlier notes in CURRENT_STATE.md and ROADMAP.md are dated provenance, not an instruction to repeat
completed work. Product authority remains the complete Master and newer explicit
owner decisions; implementation evidence never changes a sporting rule.

## Baseline and review boundary

- Verified merged `buuk`: `edd237b7a2d5e1d69cf96aafce13799bf428253b`.
  Owner merges #1652–#1659 and #1660 are present. This is not a release.
- Backend #1662 remains **open, not merged** at
  `e1f7c578032c5064aa1f2eb6a90a5f1fda9af332`. Its latest hosted inventory
  is 56 successful checks and three unrelated skips, including 49 actual native
  acceptance jobs across seven workflows. No failed/pending functional check.
  These are candidate-head results, not tests of the merged base.
- Viewer #1661 and #1663–#1668 are open with successful applicable final-head
  tests/build/static checks at this audit snapshot. They are read-only legacy
  projection improvements, not new native sporting capabilities.
- Viewer #1669 is reviewed/Ready at `6119781fb16e8d83d753d582d4056ec7ba7b1c05`.
  Fast CI and CodeQL passed; Sonar reports D new-code reliability. The report's
  issue details were unavailable in this review environment. No specific runtime
  defect was independently confirmed; the advisory is unresolved, not dismissed.
  Under the owner's advisory-only Sonar policy it is disclosed rather than counted
  as a pass or used alone to block this PR. No enforced repository rule is bypassed.
- Refresh GitHub before acting: PR state and candidate heads can change after this
  snapshot. Only the owner merges. No auto-merge.

## Independently executed integration evidence

All nine candidate file sets merged without conflict in a disposable local
checkout based on the merged SHA above. No integration commit was published.

- 113 focused frontend tests across 16 files passed; they use mocked GET data.
- TypeScript and the production Vite build passed.
- 56 focused backend cache/dependency/domain/profiling tests passed.
- Three actual HTTP/SQLite Save, limited-budget, rollback/handoff and reopen
  cases passed using production services.
- Seven release-map checks passed: actual empty Run/two manual players/Saved
  standalone match, four deterministic 80-Edition calendar-source tests and two
  actual HTTP rejection checks for missing FAX release inputs.
- The 80-Edition tests establish a deterministic fixture, **not** successful
  execution of those Editions. Missing-input rejection does not prove readiness
  of a fully prepared native FAX Run. No new real Viewer browser run, whole
  reference season, 50-season release or full-suite certification is claimed.

## Native Save performance candidate

#1662 demonstrably removes repeated checkpoint copies and evidence parses while
preserving complete-content/Run/Branch keys, isolated callers, bounded retention,
physical/source/ancestry/dependency/math/post-write gates, legacy behavior,
manual Save and immutable history. Independent review found no confirmed
user-facing defect in its patch.

The same 64 MiB limit accounts for serialized input bytes; it is **not** a Python
heap or RSS cap. The paired measurements and raw samples are in #1662 and
`docs/NATIVE_SAVE_PERFORMANCE.md` on that branch. Two ordinary samples per version
do not establish a stable end-to-end speedup; cold restart is slower in the final
sample. Its unchanged W80/1,000 Chromium and every-week/Season Transition gates
passed on the final candidate head, without a timeout or population relaxation.

## Copied-FAX preparation and continuation candidates

#1671 remains open at `b36eed8e2edcac5e849d4852cb05b0d0bc3bb7f6`.
Actual production HTTP/SQLite now prepares 1,000 players/80 Editions, binds authored
points and reviewed sources, authenticates the original Saved hash and live inputs,
and verifies concurrent-read consistency, Entry decisions and restart. Functional
acceptance/CodeQL passed. Sonar C Security/D Reliability has three unspecified
annotations; their unavailable details remain unclassified, not disproved.
#1672 remains open at `d2fc8c8695840c8445a321a62732d79b0f073b6c`.
The actual probe reuses the same original command across checkpoint/restart,
respects Pause/Resume and rejects changed audit/retargeted contexts. All applicable
checks including Sonar passed. Neither candidate is merged or a release.

## Next development priority

Finish the bounded open work without additional Viewer expansion. The real
copied-FAX preparation now reaches the OPEN automatic application eligibility/
deadline policy. Do not invent it while the owner is unavailable. Confirm that
product boundary before dependent unattended simulation work. Native reference
migration and a played 80-Edition season remain unproven; the existing legacy
reference preparation actually works to the explicit policy boundary. Continue
through existing owners/commands, manual Save and reopen without a parallel state
model. A structured blocked probe is not the mandatory 50-season acceptance.

The evidence map below separates decided scope, implemented pieces, tested
integration and release evidence. W80, 80 Editions, 1,000 players and 50 seasons
are distinct axes. No PAQ or sporting rule is changed by this checkpoint.

---

# Active pre-alpha completion map — 30 October 2026

Verified merged base: `edd237b7a2d5e1d69cf96aafce13799bf428253b`.
This is the single current dependency/evidence view; older entries in ROADMAP.md
are historical. The canonical scope remains the **entire** Master, especially
chapter 31 and its later consolidations. This operational table is not a reduced
scope specification or a complete re-audit of every PAQ.

## How to read status

**Decided** is a product status, not an implementation pass. **Implemented**
requires code; **integration proven** requires actual production boundaries;
**release proven** requires the complete assigned release scenario. An unknown
or unreviewed row is not a newly discovered product omission or a scope deferral.
A successful narrow PR, smoke/component mock or Draft skip cannot close a release
row. Every future update records the exact tested commit and scenario.

## Current evidence and remaining blockers

| Requirement / authority | Actual evidence boundary | Remaining blocker / next action | Priority |
| --- | --- | --- | --- |
| Empty Run → two manual players → Saved standalone match; §31.3 PAQ-003 | Existing `tests/application/test_standalone_match_acceptance.py::test_empty_run_two_manual_players_can_play_one_saved_standalone_match` passed on the combined audit tree using actual services/HTTP/SQLite | Retain this operation-scoped independent flow; its API evidence is not a new real Admin browser acceptance | Preserve |
| Canonical native matches, global slots, explicit Save/reopen/fork; §31.5/7/11/18 | Merged native work plus #1662 final-head 49 actual acceptance jobs; three focused production Save/reopen cases rerun independently | Merge is owner-only; preserve full source/math/corruption and same-slot invariants in subsequent work | Integration prerequisite |
| W52/W61/W80 full-week and Season Transition boundaries; §31.37 | #1662 final-head separate matrices actually ran every selected week and the true rollover | Sparse sporting schedules are not a full reference World Tour season | Preserve; no redundant broad reruns |
| Native Save/Load performance; PAQ-006/133 | #1662 paired 1,000-player timing, counters, reachable data and RSS; unchanged W80/1,000 browser passed | Candidate remains open; cold reads are still expensive and stable total speedup is unproven. Measure on the owner's target machine before setting product budgets | Finish current #1662 |
| FAX reference input shape: editable copy, ≥1,000 initial players, 80 World Tour Editions; §31.19/26/28 | #1671 actual copied-FAX HTTP/SQLite generation/Save, 1,000 players/80 Editions, Saved-source/hash and concurrent-read integrity; #1672 actual pending-command/restart/control checks | Preparation reaches OPEN automatic application validation with complete disposable test points. Native migration, final FAX awards and season completion remain separate; readiness is not completion | Next integration slice |
| Full FAX season → Save/reopen → next Season Week 1; PAQ-001/004 | Legacy `test_official_run_full_season_acceptance.py` explicitly uses four participants; native sparse season matrices provide separate bounded evidence | Demonstrate the real reference population and all 80 Editions through the supported Admin/production path without manual database repair | Blocking release evidence |
| Entire reference FAX 50-season Run; §31.28/37 | Existing long-probe code and structured blocked/progress contracts; no completed reference 50-season run verified by this audit | Resolve the actual application-validation product boundary, establish a complete season, then deterministic long-run/recovery/history-size evidence. A probe returning blocked is not a pass | Blocking release evidence after season |
| World Tour Finals in the FAX flow; §31.1/19/26 | Group/hybrid/native-match kernels and scoped acceptance exist; Finals Race/selection/publication have separate legacy projections | Verify the complete reference Finals qualification/selection/competition/closure and subsequent season on the same native owner; do not infer this from a Viewer Race page or a pure-group case | Validate during reference season |
| Lower Tours' aggregate outcomes and consequences; §14.3/31.26 | Canonical target is explicit; full execution was not re-audited here | Inventory existing implementation and verify its participation, points, history and physical/time consequences in the reference flow; do not invent played rally logs | Scope reconciliation before release |
| Initial historical cohort model and continued intake/lifecycle; §9.8/31.38 | Native birth/intake/epoch and worker cases exist; their successful boundaries remain intact | Reconcile full v83 initial-population requirements, historical country inputs and retirement filtering against current code. Do not equate generated roster size with complete cohort behavior | Full Master scope audit |
| Minimum Reconstruction and independent three Labs; §31.15/25 | Separate implementations and prior scoped workflows exist; this review did not rerun those workflows | Carry their actual evidence into the release matrix; missing coverage is unknown until inspected, not silently deferred | Required scope audit |
| Records, holder history, milestones, followed notifications and season comparisons; §31.27/39/40 | Saved career/Country/season read models exist; broader target completion was not re-audited here | Map each decided requirement to actual producer, persisted history and consumer. Read-only lists alone do not establish notification or record-event generation | Required scope audit |
| Packages including decided FAX/Earth requirements; §31.6 and newer owner decisions | Existing Package implementation and security/integration evidence; current full content coverage not re-audited | Reconcile the owner's later confirmed FIFA/ATP Earth scope with canonical implementation/content evidence; do not silently omit it from release planning | Required scope audit |
| CS/EN and usable Admin; §31.17/30–36 | Many scoped frontend flows exist; new #1661/#1663–#1669 improve Viewer legacy browsing only | Verify the required Admin operations and real historical navigation in both languages. Viewer is not the first pre-alpha acceptance gate | Admin before further Viewer expansion |
| Complete release regression and recovery; test policy / §31.3/18 | Focused PR checks and bounded integration passes are available | Run the complete backend/frontend release suite and assigned end-to-end gates at an intentional checkpoint, on one actual release candidate; never certify from mixed old SHAs | Release-only gate |

The local combined audit tree contains base plus heads:
#1661 `cbd56cfc`, #1662 `e1f7c578`, #1663 `199701b3`,
#1664 `d97f29ce`, #1665 `e5c39358`, #1666 `8a7d1326`,
#1667 `811bbd65`, #1668 `05aedd9a`, #1669 `6119781f`.
It passed 113 focused mocked-frontend tests/build, 56 backend unit/domain/cache/
profiling checks, three actual Save/reopen cases and seven additional release-map
checks. This unpublished composition is not the merged base or a release.

## Next bounded work and ownership

1. Finish current PRs without growing scope. The checkpoint overview is kept in
   this scoped document; root links are inserted after an existing historical
   section so #1662 can prepend its measured notes without a merge conflict.
   #1669's Sonar reliability advisory remains unclassified because issue detail
   was unavailable; Fast CI/CodeQL success is not a dismissal of that advisory.
2. The actual copied-FAX preparation now reaches OPEN application validation.
   Resolve that product boundary before dependent unattended execution. Keep
   native-reference migration distinct from the proven legacy preparation. Preserve the same
   immutable source, explicit Save and command/seed/retry/restore semantics.
3. Fix one confirmed integration blocker per PR. Missing PRODUCT policy goes to
   the owner with one recommendation; calibration defaults are not invented.
4. Establish the complete reference season before the full 50-season acceptance.
   W52/W80 compatibility uses its assigned targeted scenarios; this table does
   not invent a mandatory 50-season Cartesian matrix for every calendar.
5. Consolidate integration evidence after this subsystem checkpoint. Archive
   history without deleting decided scope, reusing PAQ IDs, counting PRs as
   release coverage or creating a second Master.

Sonar is advisory under the owner's instruction. Classify its actual findings
before accepting or rejecting fixes; it is not sporting authority. A confirmed
functional/security problem remains a blocker regardless of which tool found it.
