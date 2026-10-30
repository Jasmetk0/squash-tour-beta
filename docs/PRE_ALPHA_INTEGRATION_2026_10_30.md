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
