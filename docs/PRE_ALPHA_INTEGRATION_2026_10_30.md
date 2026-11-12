# Current Claude review and handoff — 12 November 2026

Reviewed baseline: `buuk a86053f7ded5b72cd594f7e51ce64ab6ea43d11b`,
including owner merges #1763/#1780/#1781/#1782. The approved repository Master
was v86; the Work documentation candidate consolidates v87 with the owner's
explicit 12 November confirmations. A candidate is not a runtime merge.

This review covers all **17 open Claude PRs** below: actual ancestry, each
feature increment, complete final runtime delta, separate UI/document/test
changes, changed production paths, tests, CI checks and review discussions.
The final runtime is 41 files (+3922/-70) versus current buuk. Its merge of buuk
includes Work's ATP changes; those are not new Claude contributions. Historical
heads are not individually certified, and this is not a repository-wide security
audit, full release or line-count productivity ranking.

## Current PR disposition

| PR | Purpose | Closest open ancestor | Files: own / cumulative | Exact reviewed head | Disposition |
| --- | --- | --- | --- | --- | --- |
| [#1764](https://github.com/Jasmetk0/squash-tour-beta/pull/1764) | Saved Draw readiness UI | buuk | 8 / 8 | `4099a5f5caa9c1f0504d2a81edf0ff3ce59eb2c2` | CHANGES REQUIRED; separate UI follow-up |
| [#1765](https://github.com/Jasmetk0/squash-tour-beta/pull/1765) | Proposed Master v87 | buuk | 3 / 3 | `409cdbc440c305382abc836dd4e63d74d66fe872` | Reconciled in Work documentation candidate |
| [#1766](https://github.com/Jasmetk0/squash-tour-beta/pull/1766) | Signed-intake test repair | buuk | 1 / 1 | `5ac6413a771b996263f67112f41efeab53e818e9` | Useful; included in Work #1784 |
| [#1767](https://github.com/Jasmetk0/squash-tour-beta/pull/1767) | Lifecycle kernel | buuk | 7 / 7 | `8165894e1e02f24eaf1f24f8e7d8ad0d2bd6a93b` | Review only as part of final runtime |
| [#1768](https://github.com/Jasmetk0/squash-tour-beta/pull/1768) | Professional roster/Entry gate | #1767 | 7 / 12 | `b0e29a9ff0c41a7e192ea86d1bb1961a94bc5ecb` | Review only as part of final runtime |
| [#1769](https://github.com/Jasmetk0/squash-tour-beta/pull/1769) | Entry isolation/Health tests | buuk | 3 / 3 | `cf7d55373669608ed78e163ee7ac3b6339b40137` | Positive critical marker corrected in #1784 |
| [#1770](https://github.com/Jasmetk0/squash-tour-beta/pull/1770) | Model v1 | #1768 | 4 / 14 | `9ee97c347adc28d2118b7f662cdb8cb6d6123e74` | Do not merge as the final default |
| [#1771](https://github.com/Jasmetk0/squash-tour-beta/pull/1771) | Weekly decisions | #1770 | 9 / 17 | `26652b7e953480b02a6ce3ea5143aad1dc609eed` | Review only as part of final runtime |
| [#1772](https://github.com/Jasmetk0/squash-tour-beta/pull/1772) | Opening professionals | #1771 | 10 / 21 | `d50cdf056c340778a49773e0cc63a405209fbaf9` | Review only as part of final runtime |
| [#1773](https://github.com/Jasmetk0/squash-tour-beta/pull/1773) | HTTP/SQLite flow | #1772 | 4 / 22 | `cf7cb8658579881d673dc7a05305bbd80d1e6681` | Review only as part of final runtime |
| [#1774](https://github.com/Jasmetk0/squash-tour-beta/pull/1774) | Home opportunity | #1773 | 6 / 23 | `8cd82e4ddd49566728a4a1e3b0d5b3cb4fb43454` | Review only as part of final runtime |
| [#1775](https://github.com/Jasmetk0/squash-tour-beta/pull/1775) | Public Turn Pro event | #1774 | 7 / 23 | `6e5eb61a170cdf001eb5ebb49ae7b1d674e9114e` | Review only as part of final runtime |
| [#1776](https://github.com/Jasmetk0/squash-tour-beta/pull/1776) | Native birth/week integration | #1775 | 8 / 28 | `84726500f743eb1df0c59daf1ee6ef7a9ec28662` | Review only as part of final runtime |
| [#1777](https://github.com/Jasmetk0/squash-tour-beta/pull/1777) | Native fork; config restored | #1776 | 6 / 30 | `b17fc7ac5b0a05307952579706d5052a5296c228` | Do not revive the earlier polluted head |
| [#1778](https://github.com/Jasmetk0/squash-tour-beta/pull/1778) | New Admin default | #1777 | 9 / 35 | `77fdd8149597fee5d6c6f973fd3c5bd02fb4f1e5` | Review only with v2 and early-week repair |
| [#1779](https://github.com/Jasmetk0/squash-tour-beta/pull/1779) | Professional-only FAX adoption | #1778 | 6 / 38 | `cb9181c995bcbcb6c398de285a9d0a290d800a6b` | Bounded path, not v87 full FAX acceptance |
| [#1783](https://github.com/Jasmetk0/squash-tour-beta/pull/1783) | Own-self model v2, final runtime | #1779 + merged buuk | 41 vs current buuk | `06b41e45467f1131883787e4ef3697a3339977a0` | CHANGES REQUIRED; 7 manual workflows pass |

The chain #1767 → #1768 → #1770 → #1771 → #1772 → #1773 → #1774 → #1775 →
#1776 → #1777 → #1778 → #1779 → #1783 is cumulative. The smaller parent deltas
explain provenance, not independently mergeable feature releases. #1783 already
contains the reviewed buuk. #1764/#1765 and the two test repairs are separate.

**Recommendation:** use Work #1784 for the complete test repair and the Work
documentation candidate for reconciled Master/handoff; then review ONE completed
v2 runtime head. Do not merge intermediate runtime PRs one by one. After owner
merge of their replacements, the old PRs can be closed as superseded by an
explicit owner/Work decision. This review closes or merges none of them.

## Findings and concrete repairs

1. **Lost positive critical-CI coverage — fixed by Work #1784.**
   In #1769 `cf7d553`, adding the negative missing-Health test immediately after
   `@pytest.mark.pr_critical` transferred that marker away from the original
   `test_match_reconstruction_http_preview_is_read_only_and_commit_is_exact`.
   The positive test was no longer selected. Work restores its marker while
   retaining the real Health bootstrap/carry fixture and negative guard. This
   is a test-selection regression, not a weakened production Health rule.
   #1784 also includes #1766's genuine Signed-source preflight repair and both
   Claude commits as ancestors. All 22 tests in the four changed modules pass;
   critical collection selects 16, including both Reconstruction cases.
   Exact remote head: `95c704c4683933cf8836d8ba0303b1200a7513a4`;
   identical tested tree: `8258c085c32ad9e374d4e86aeeccbd99dc71babc`.
   Fast CI run [43209396768](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/43209396768),
   CodeQL and Sonar pass. Frontend/security/docs skips are unrelated test-only
   path selections, not claimed execution of those suites.

2. **Decision observation is hashed, not stored as claimed — runtime repair.**
   `turn_pro_model.py::decide_turn_pro` fingerprints full candidates, including
   their observations, then emits `PlayerTurnProDecision.v1`. That DTO stores
   identity, effective week, source hash and provenance; it has no observation.
   `CalendarTourTransition` stores the model and decisions, not the candidates.
   The default-model API test has an unused `observation` variable and comments
   about knowledge but only asserts a public player ID. Thus the PR, handoff
   comment and `TURN_PRO_LIFECYCLE_V87.md` overstate persisted evidence.
   An authenticated deterministic reconstruction can be a valid design, but no
   inspectable historical-observation read is implemented here. Complete it with
   proper version/byte compatibility; do not add fields only when replaying an
   older recorded decision or multiply Saved size by all weekly 57-attribute
   prospect observations.

3. **Older Tour model replay is incomplete — runtime repair.**
   The fallback in `infrastructure/db/calendar_tour.py` rebuilds lifecycle and
   ranking using stored Turn Pro decisions, rather than regenerating decisions
   from the stored model and predecessor inputs. Native birth/competition/fork
   paths do rerun their recorded policy. The author correctly lists the older
   path as unsupported in the scope document/handoff. The existing default-model
   HTTP demo uses that older Tour path: an unchanged view under changed defaults
   is useful compatibility evidence but does not prove model replay.
   This finding is a missing mathematical-verification contract; it is **not**
   a demonstrated bypass of physical Saved hashes/origin authentication. Keep
   those proof layers separate and add real negative replay/ownership cases.

4. **New-default v87 skips pre-Tour sporting weeks — runtime integration gap.**
   `calendar_sporting_week_service.py` explicitly advances sporting state without
   lifecycle/intake. A new Admin v87 population must pass through early sporting
   preparation before Tour initialization. Opening professionals are generated,
   but normal prospect decisions in those early weeks are not executed. Connect
   the actual versioned owner/replay path; do not silently delay all decisions
   until Tour exists or introduce a first-application shortcut.

5. **Never-pro exception is only a public event — partial implementation.**
   `retired_without_turn_pro_player_ids` correctly selects players retiring in
   this transition who never had a Tour entry, only under v87. It is integrated
   into public-event rebuilds, rather than exposed before its effective week.
   It does not yet provide the confirmed explicit career-history/audit display.
   Reuse existing history/audit, preserve the same profile, and do not force a
   professional event or invent a health cause to explain the exception.

6. **Reference FAX acceptance still uses the historical policy.**
   The native Saved Draw gate now rejects a non-professional in both Ranked and
   Unranked under v87; that bounded implementation is useful. The large copied-FAX
   materializer still uses legacy 61-week lifecycle. Green FAX preparation and
   general native regressions therefore do not establish the owner-required
   direct v87 reference Run. Complete a genuine native-population association
   flow and state the separate full-season/release gap.

7. **UI validators accept unsupported evidence — reproduced, separate follow-up.**
   On exact #1764 head, direct execution of the production pure validators returns
   true for (a) `schema_version='future_unsupported.v99'` on a first-entry trigger,
   and (b) `ranking_status='ranked'`, complete table, no gaps and
   `required_point_stages=[]`. Existing 35 tests all pass but omit these cases.
   The read-only panel also describes only Ranked native Entry requirements,
   which must be distinguished from v87's professional prerequisite for Ranked
   AND Unranked. This is a read/display contract gap, not an authorization bypass;
   the backend still validates adoption. Keep same-head/source scope and no write
   actions. #1764 conflicts with current buuk and has no actual readiness-page
   browser acceptance.

8. **Contradictory Master summaries — reconciled by Work.**
   #1765 retains unconditional eventual-entry guarantees alongside the new rare
   exception, exact Tour-strength wording alongside self-perception, and an
   AGENTS summary with both stale rules. Its older AGENTS also drops the current
   coordination pointer. Work preserves that pointer and ATP/current-state
   history; updates active 9.2, summaries/registers and the health exception;
   records the two explicit 12 November owner confirmations. Exact observation
   granularity, threshold/errors/weights and other calibration remain provisional.
   No new financial subsystem, forced age, migration rule or broad notification
   layout is invented.

## Corrections already completed by Claude

- Production Entry tuning is restored in **all current reviewed heads** to blob
  `02fd58856ca05ca248c20373fa8a296c72d4c797`. Earlier #1777 pollution is historical,
  not an unresolved current-head defect.
- Default v2 weekly candidates consume the prospect's own noisy attributes and
  own available traits; they do not compare with opponents' hidden true OVR.
  Unknown Financial Level and born-prospect traits remain neutral, explicitly
  bounded. V1 is retained for old-policy replay and opening-population generation.
- Annual chance normalization is exercised for W52/W61/W80. Home opportunities
  use already-public future Editions; same-transition announcements are excluded.
  Exact age/strength/opportunity calibration remains provisional.
- Versioned Entry/WC gate, professional ranking roster, opening identities,
  native birth, fork and public events have substantial deterministic tests.
  Optional fields are omitted for historical bytes.
- Earlier wrap serializers caused a real W80/1000 slowdown. `06b41e4` replaces
  them with field `exclude_if`; the existing byte tests and final browser pass
  are useful evidence. Author-reported local timings are not Work benchmarks.

## Independent execution and hosted evidence

- Work #1784: `GITHUB_EVENT_NAME=claude_test_review PYTHONPATH=src:.:tests/api`,
  `pytest -o addopts='' -q` on
  `tests/application/test_authoritative_entry_decision_slot.py`,
  `tests/application/test_authoritative_simulation_api.py`,
  `tests/application/test_shared_config_is_not_mutated_by_tests.py`,
  `tests/api/test_calendar_native_prospect_intake_api.py`:
  **22 passed in 256.53s**. Critical collection: **16/22 selected**.
- #1783 exact `06b41e4`: independent targeted domain + real v87 HTTP/SQLite
  execution: **68 passed in 1578.11s (26m18s)**.
- #1783 frontend: `vitest run src/api/calendarPopulation.test.ts
  src/components/RunCalendarPopulationControls.test.tsx`: **14 passed**.
- #1764 frontend: `vitest run src/api/savedNativeReadiness.test.ts
  src/components/SavedDrawNativeReadiness.test.tsx
  src/pages/SavedTourEditionPage.test.tsx`: **35 passed**. These are pure/
  mocked-boundary component/page tests, not genuine API/browser acceptance.
- No full release, 50-season, exhaustive repository regression or new global
  performance benchmark was run by Work in this review.

The commit check-runs endpoint matters: the convenience workflow wrapper filters
to PR-triggered runs and misses manual dispatch. At #1783 `06b41e4`, **all seven
manual workflows really passed**, alongside Fast CI and CodeQL:

| Workflow | Exact-head manual run |
| --- | --- |
| Native Tour Browser, including W80/1000 | [43188495406](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/43188495406) |
| Native Tour API | [43188500087](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/43188500087) |
| Native Full Simulation | [43188505189](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/43188505189) |
| Native two-Edition restart | [43188509306](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/43188509306) |
| Native one-Edition operator | [43188513973](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/43188513973) |
| Native Season Boundary API | [43188518747](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/43188518747) |
| FAX Reference Preparation | [43188522710](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/43188522710) |

This is real evidence, not seven Draft skips. However, groups/global-slot and
Saved Branch/fork workflows are still Draft-skipped without a corresponding
observed exact-head manual run, and many green fixtures exercise historical
policy. They do not replace new v87 acceptance for the gaps above. Sonar remains
failed on #1783 (C Reliability) and #1764; issue-level details were not exposed by
the connected check-annotation endpoint, so no false-positive claim is made.
There are no inline review threads on any of the 17 PRs; the #1783 author's
handoff/review comments were also read. Author self-review is not independent.

## Next work and merge boundary

Work #1784 is the independently verified test-only merge candidate. The Work
documentation candidate reconciles Master/coordination without changing runtime.
Claude receives the [new-chat prompt](AI_REVIEW_HANDOFF.md#prompt-to-paste-into-a-new-claude-code-chat)
for one completed runtime candidate and then the separate read-only UI repair.
Do not merge #1783 yet or certify intermediate v1 defaults. Recheck exact final
heads and required checks after every change; Radim alone merges.

ATP source/schedule/points foundations are now owner-merged, but their public
native Run owner with normal cross-week Q/Main/Entry/Save remains a separate
dependency. Do not disturb those helpers while completing lifecycle. Full
reference season/Finals, 50-season/recovery/performance and the rest of the Master
remain release requirements.

---

# Historical AI/PR coordination checkpoint — 11 November 2026

Baseline: `buuk` `04c9879c49921865e35240cbcf411426d84ef68d`, approved Master v86.
Inventory captured 11 Nov 2026, 20:38 (Europe/Prague), before the new coordination PR.
There were 18 open PRs. This is a complete metadata/ancestry inventory with
risk-focused review of changed configuration, Turn Pro inputs and selected
contracts; it is not an exhaustive line-by-line certification of the whole stack
or a pre-alpha release. Current owner clarification is in
[the repair handoff](AI_REVIEW_HANDOFF.md).

## PR inventory and actual dependencies

All these PRs target `buuk` now, except that #1780 originally targeted #1763's
feature branch and was retargeted during this review. The parent column comes
from actual Git ancestry, not titles or base-branch labels. File counts are
own delta / complete delta against baseline `buuk`; inherited files are not
counted as a new developer contribution.

| PR | Purpose | Closest open ancestor | Files: own / total | Exact reviewed head | Fast CI | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| #1763 | ATP source, profiles and scheduled foundations | buuk | 56 / 56 | [`948d730610`](https://github.com/Jasmetk0/squash-tour-beta/commit/948d730610df1b3985ece737be5e3c33403097b5) | success | READY FOR OWNER MERGE |
| #1764 | Saved Draw readiness UI | buuk | 8 / 8 | [`4099a5f5ca`](https://github.com/Jasmetk0/squash-tour-beta/commit/4099a5f5caa9c1f0504d2a81edf0ff3ce59eb2c2) | success | INSUFFICIENT EVIDENCE |
| #1765 | Proposed Master v87 | buuk | 3 / 3 | [`df52812bc5`](https://github.com/Jasmetk0/squash-tour-beta/commit/df52812bc56d1bb11a20a95e8e166f31cef09da7) | success | BLOCKED |
| #1766 | Signed-intake corruption test repair | buuk | 1 / 1 | [`5ac6413a77`](https://github.com/Jasmetk0/squash-tour-beta/commit/5ac6413a771b996263f67112f41efeab53e818e9) | success | READY FOR OWNER MERGE |
| #1767 | Turn Pro lifecycle kernel | buuk | 7 / 7 | [`8165894e1e`](https://github.com/Jasmetk0/squash-tour-beta/commit/8165894e1e02f24eaf1f24f8e7d8ad0d2bd6a93b) | success | INSUFFICIENT EVIDENCE |
| #1768 | Ranking roster and application gate | #1767 | 7 / 12 | [`b0e29a9ff0`](https://github.com/Jasmetk0/squash-tour-beta/commit/b0e29a9ff0c41a7e192ea86d1bb1961a94bc5ecb) | success | INSUFFICIENT EVIDENCE |
| #1769 | Isolate Entry test tuning | buuk | 3 / 3 | [`8aa0b4d894`](https://github.com/Jasmetk0/squash-tour-beta/commit/8aa0b4d8944fa56b5f2aaa31680268cd13115de7) | failure | CHANGES REQUIRED |
| #1770 | Provisional Turn Pro model | #1768 | 4 / 14 | [`9ee97c347a`](https://github.com/Jasmetk0/squash-tour-beta/commit/9ee97c347adc28d2118b7f662cdb8cb6d6123e74) | success | INSUFFICIENT EVIDENCE |
| #1771 | Weekly model decisions and replay input | #1770 | 9 / 17 | [`26652b7e95`](https://github.com/Jasmetk0/squash-tour-beta/commit/26652b7e953480b02a6ce3ea5143aad1dc609eed) | success | CHANGES REQUIRED |
| #1772 | Opening professionals | #1771 | 10 / 21 | [`d50cdf056c`](https://github.com/Jasmetk0/squash-tour-beta/commit/d50cdf056c340778a49773e0cc63a405209fbaf9) | success | CHANGES REQUIRED |
| #1773 | First HTTP/SQLite v87 path | #1772 | 4 / 22 | [`cf7cb86585`](https://github.com/Jasmetk0/squash-tour-beta/commit/cf7cb8658579881d673dc7a05305bbd80d1e6681) | success | CHANGES REQUIRED |
| #1774 | Public home-event opportunity | #1773 | 6 / 23 | [`8cd82e4ddd`](https://github.com/Jasmetk0/squash-tour-beta/commit/8cd82e4ddd49566728a4a1e3b0d5b3cb4fb43454) | success | CHANGES REQUIRED |
| #1775 | Public Turn Pro World Event | #1774 | 7 / 23 | [`6e5eb61a17`](https://github.com/Jasmetk0/squash-tour-beta/commit/6e5eb61a170cdf001eb5ebb49ae7b1d674e9114e) | success | CHANGES REQUIRED |
| #1776 | Birth-week integration and model replay | #1775 | 8 / 28 | [`84726500f7`](https://github.com/Jasmetk0/squash-tour-beta/commit/84726500f743eb1df0c59daf1ee6ef7a9ec28662) | success | CHANGES REQUIRED |
| #1777 | Native fork + accidental config change | #1776 | 7 / 31 | [`041ecfab8b`](https://github.com/Jasmetk0/squash-tour-beta/commit/041ecfab8bf0172e36a400f704342783e1283961) | success | CHANGES REQUIRED |
| #1778 | Admin v87 default | #1777 | 9 / 36 | [`0fdb677dad`](https://github.com/Jasmetk0/squash-tour-beta/commit/0fdb677dad312a1b22ccfad2bffd1e265b36eab6) | success | CHANGES REQUIRED |
| #1779 | Professional-only Saved FAX adoption | #1778 | 6 / 39 | [`15ccc56806`](https://github.com/Jasmetk0/squash-tour-beta/commit/15ccc568065a75f3ed90fd4425add3939801a423) | success | CHANGES REQUIRED |
| #1780 | Horizon-safe ATP continuation | #1763 | 9 / 57 | [`03727d0e82`](https://github.com/Jasmetk0/squash-tour-beta/commit/03727d0e82cec7e28f77af78a8187f767d910b1a) | success | INSUFFICIENT EVIDENCE |

- #1763: 20 applicable workflows and CodeQL passed at the exact head; no conflict.
  Sonar's single reliability annotation concerns two independent factory calls
  in a reproducibility test. Faulting only the second build makes the assertion
  fail; the documented false positive is not reported as a green Sonar check.
- #1780: 105 local targeted tests and hosted Fast CI passed. Full combined-head
  Ready acceptance was triggered after retargeting. One first browser attempt
  failed with `ECONNRESET` on a read-only hybrid policy GET; its server-log artifact
  was empty. One unchanged-head retry was requested, with no removed assertions.
  That retry passed. Another workflow's W80 all-week test passed in 3,992 s,
  but uploading its evidence failed after five invalid-JSON responses from the
  artifact service (run `43085487952`, job `130748646844`). Only that failed job
  is being repeated unchanged. The current workflow status is 19 successes and
  one failed/retrying workflow; it is not approved until the final checks pass.
- #1766: the complete one-file delta and the exact modified HTTP case were
  reviewed/executed independently against identical production/config trees.
  Fast CI, CodeQL and Sonar passed on the pinned head. It was marked Ready.
- #1769: actual HTTP 409 is `Simulation Slot requires authoritative Health state`.
  The same isolated test also fails on baseline `buuk`. Preserve the useful
  config isolation; repair the positive fixture without weakening the Health guard.
- #1777/#1778/#1779: production Entry tuning is actually polluted, despite green
  Fast CI. Every other inventoried head retains the baseline config blob.
- #1771 onward: native Turn Pro reads exact checkpoint OVR. The owner now requires
  strength estimates from then-available information. Repair the boundary and
  review opening-world approximation separately from runtime AI knowledge.
- #1765: accepting separate Turn Pro and professional-only association entry does
  not approve the entire proposed document, provisional calibration or hidden-OVR
  access. Existing policy/history remains authoritative for old Runs.

The Turn Pro ancestry is #1767 → #1768 → #1770 → #1771 → #1772 → #1773 →
#1774 → #1775 → #1776 → #1777 → #1778 → #1779. #1765 and #1769 are separate
branches, not automatically included in that chain. Stop propagating the bad
config; stabilise the chain before adding another feature stack.

Draft acceptance skips on Claude's branches are not executed passes. The initial
workflow inventory found 11 skipped workflows on #1764, four on #1767, and seven
on #1768/#1770–#1779; counts are control-plane statuses, not comparable amounts
of delivered functionality. #1769 Fast CI run `42918982448`, failed backend job
`130188747990`, and both local reproductions identify its incomplete Health fixture.

## Integration order and bounded next work

1. Owner can merge #1763. #1766 is an independent, reviewed test-only repair.
2. Finish exact-head #1780 acceptance; owner merges it after #1763. No auto-merge.
3. Claude restores Entry tuning in #1777 and every affected descendant, fixes
   #1769's positive Health fixture and the observable-strength input boundary.
4. Review the final v87 product text/remaining model choices, then verify one
   genuine professional transition → Entry/WC → actual Edition → points → manual
   Save → SQLite restart and replay/fork. Consolidate/retarget only by an agreed
   plan; do not merge every cumulative stack head as independent functionality.
5. Work continues ATP's versioned native scheduled owner and existing GlobalSlot
   ledger. Prove Q → explicit Save/restart → normal Week Transition → Main →
   terminal confirmation and following-week ranking on the same actual Run.
   Copied source dates and an Admin-proposed schedule remain distinct evidence.
6. Then multiple simultaneous Editions, complete reference season, release
   performance/recovery/50-season gates, plus retained side requirements below.

Work owns ATP helpers/source integration and the CI/review handoff. Claude owns
the current lifecycle/Turn Pro/fork repair. Shared Tour/persistence files need one
active writer and a handoff, avoiding competing implementations. No new sporting
rule is inferred from a data Package or from a passed component test.

## Pre-alpha requirement/evidence map

This map distinguishes scoped working paths from the entire Master target.
The 20 passed acceptance suites cited above ran on candidate #1763, not a signed
release; current `buuk` and the unmerged candidates remain distinct.

| Area | Current implementation/evidence | Remaining boundary |
| --- | --- | --- |
| Empty Run / Branch / Saved | Actual immutable Save, lineage, restore, fork and corruption tests exist; selected candidate acceptance passed | Portable archive/recovery and all release combinations require their own proof |
| Native calendar | W52/W61/W80, offset, actual Week/Season transitions, extension and terminal scenarios covered in scoped gates | Entire multi-season sporting world and full release matrix |
| Initial population / intake | Native population/birth/intake paths exist with real HTTP/SQLite cases | Complete historical cohort/development/country semantics and whole-Master generator scope remain partial |
| Player lifecycle / Turn Pro | Current historical policy works on its supported paths; v87 is an unmerged stack | Config, estimated knowledge, pre-Tour/older-replay/materializer gaps and final native acceptance |
| Entry / wildcard AI | Existing versioned subsystems and actual decision/validation paths | v87 professional prerequisites, genuinely then-known inputs and original-source chronology |
| Draw / Q / groups | Source-sized geometries, real feeder results, groups/hybrid and partial Save/restart are exercised | Original full reference season, remapping/revised Draws and complete ATP cross-week ownership |
| Match Engine / Health | Genuine rally MatchEngine and owned Health paths are exercised | Full realism/calibration and complete decided Health scope are not certified |
| Ranking / Finals | Versioned W-aware result/publication paths and genuine native scenarios; ATP group profiles have separate proofs | Full Race/selection/exception scope and source-complete seasons |
| ATP Packages | 2,407 mapped source occurrences; two playable group profiles and a sourced Main32/Q16 foundation in #1763 | General playable ATP catalogue, verified Q dates/seed/Entry policies and full native cross-week flow |
| Saved / replay / fork | Actual selected restart, independent fork and stale/corrupt-source rejection gates | v87 fixes and broader archive/migration/release coverage |
| Admin / Viewer | Existing actual Chromium scenarios and read-only historically bound views | Complete Master UI/notification/record requirements, CS/EN acceptance and finishing |
| Labs / Reconstruction | Real Lab workflows exist; selected Lab gate passed | Reconstruction's positive legacy HTTP fixture needs actual Health; release Lab/Reconstruction scope still needs reconciliation |
| Records / notifications / history | Master targets and partial subsystems exist | Whole-catalog verification and followed-player/country notification scope not audited as complete here |
| Persistence / performance | Existing profilers measure actual HTTP/SQLite/Saved behaviour | Scale/long-term limits must follow measured evidence, not extrapolated percentages |
| Release | No release declared by these PRs | Full regression, copied reference FAX season/50 seasons and all retained pre-alpha requirements |

No completion percentages or unmeasured productivity/cost claims are assigned.
The lightweight monthly ledger and ready-to-paste repair prompt are in
[AI_REVIEW_HANDOFF.md](AI_REVIEW_HANDOFF.md); [CLAUDE.md](../CLAUDE.md) is only an entry point.

## Measured native W52 baseline

The existing `scripts/profile_native_full_simulation_scenario.py --weeks 52`
completed on baseline `04c9879...`, Python 3.12.14/Linux x86-64. The actual
HTTP/SQLite scenario uses four synthetic players, one four-player Tour Edition,
genuine MatchEngine results, a native fork, 51 Week/Season transitions from
S1W2 through S2W1, explicit approvals/Saves and cold restart. The Run has W52,
offset 51, start year 2030 and an initial two-season horizon.

| Measurement | Single instrumented local run |
| --- | --- |
| Complete scenario, including fixtures | 1,072.39 s (17 min 52 s) |
| Execution after review | 1,027.05 s |
| SQL statements, complete / after review | 39,577 / 37,615 |
| Peak profiler-process RSS, including final verification | 1,743,120 KiB (1.66 GiB) |
| Initial / final SQLite file | 11,870,208 / 88,854,528 bytes |
| Final Saved revisions, original + fork lineage | 63 |
| Final UTF-8 Saved payload bytes | 80,666,279 |
| Task reads | 250 calls, 90.20 s wall time |

[Raw metrics, clock, source/config tree hashes and command](evidence/native-w52-baseline-2026-11-11.json)
are committed separately from binary databases. A retained replay archive contains
the profiler input, starting/final SQLite databases, steps and sporting digests;
the existing profiler's `--input` mode can reuse its fixed identities.
These measurements include instrumentation, API, fixture and restart overhead.
They show a performance/storage concern worth investigating, without establishing
a cause or a scaling curve. They do not certify 1,000 players, 80 Editions, a full
ATP catalogue, 50 seasons or a release budget. Do not extrapolate this small case.

---

# Native canonical consumer candidate after #1746 — 6 November 2026

Merged base `c7bb53eb893dceb2cb603bc0d312b71070489a0e` preserves #1746 exactly.
This extends the existing evidence map, not product release requirements.

| Boundary | Candidate implementation / verification scope | Remaining boundary |
| --- | --- | --- |
| Saved source → native | Explicit exact source adoption; separate physical reachable Saved-envelope/hash/Draw verification and mathematical replay | Original complete Ranked/Entry integration; inherited fork and revised Draw remapping |
| Publication / scheduling | Explicit source announcement, prospective adoption, normal Week Transition public event and whole-week delay; explicit increasing Q/Main Simulation Slots | No inferred dates, day/rest calibration or multi-week execution |
| Actual matches | Edition/slot v4, source IDs/seeds, same pre-slot inputs; existing v13 records/effects; derived terminal only | Original 80 Editions/full season/50-season proof remains separate |
| Honest acceptance | Dedicated actual HTTP/SQLite Gold35/Platinum51, partial Save/restart/retry/confirmation/transition on explicitly authored disposable Unranked source; negative contracts and old goldens | Final-head local/hosted results recorded in PR; no Draft skip or mocked boundary substitutes for acceptance |

Original FAX source, sporting rules and Master are unchanged. No zero-point fallback,
second result store, fabricated Q winner, widened old match index or arbitrary Run
cap. Admin consumption keeps null/BYE/Q positions and blocks mutations of adopted
Draws. No UI adoption wizard or owner Chromium acceptance is claimed here.

---

# Historical Saved-bound feeder kernel — owner-merged as #1746

Merged base `7620b89ab53b93780216955a72bd5e4c91f6d691` preserves #1745 exactly.
This continues the same evidence map and adds no release requirements.

| Boundary | Candidate implementation / proof | Still not established |
| --- | --- | --- |
| Source frozen before play | `SavedFaxKnockoutFeederService` authenticates an explicit current Saved head; reads its Calendar, Draw/Input and clock. Real explicit owner Save, connection reopen, stale/corrupt source rejection, original-source reload after a later Save and live-edit isolation tests | Materialized native-fork continuation and versioned native execution adoption |
| Canonical node/feeder graph | `project_canonical_draw_nodes` reuses the legacy BYE/Q resolver without fabricating a MatchPackage. All 80 source topologies produce Gold35/Platinum51 real nodes and eight non-played BYE advances | Native slot/day/rest scheduling and complete source awards |
| Actual Q/Main progression | Stateless existing-continuation projection checks owners, exact ordered feeder participants, stable seeds, chronology and the whole Qualification barrier. Actual MatchEngine component tests play both complete brackets and apply existing effects | No native v4 ledger persistence, public Next Match/Next Slot or ranking/season claim |
| Historical determinism | New seed contract excludes technical revision/command labels and unrelated Calendar metadata. Four legacy Main/Q/BYE topology payloads match prechange fingerprints byte-for-byte | Full reference-season / 50-season replay remains a release gate |

`feeder_dependencies_only` and `native_slot_execution_ready=false` are explicit.
No second result ledger, new eligibility/award calibration, source Package change,
implicit Save, old seed rewrite, widened legacy index or removed Main4/8 guard.
Follow with the native versioned consumer and its real HTTP/SQLite/browser gate;
final-head scoped checks and owner merge are required for this candidate.

---

# Historical source-sized player Draw — merged as #1745

Base `buuk` `1800697b978a33f6895d2e6a3fa3e77bfb066954`; #1744 is owner-merged.
This extends the existing requirement/evidence map, not the approved release scope.

| Requirement | New implementation/evidence | Remaining boundary |
| --- | --- | --- |
| Original Gold24/Platinum32 + Q geometry | `fax_reference_entry_capacity` preserves source admission cut; v12 input / padded Q v3 Draw supports Q24 as four six-player/eight-position sections | No automatic Entry eligibility or WC choice is inferred |
| Real-player/seed-aware initial Draw | Existing field, ranking and WC authorities feed canonical initial Draw; Main8 seeds, Q4/Q8 seeds, deterministic protected BYEs and unresolved Q1–Q4 | Match/round/global-slot execution and Q winner consumption remain separate |
| Exact source/replay/storage | Source-bound reader consumes copied Run Calendar and authenticated stores. Tests cover all 80 source geometries, SQLite commit/retry, Saved component restore, connection reopen, actual HTTP commands and stale/corrupt source rejection | These use explicit named test players and reviewed fixture applications, not the actual full World/Entry chronology |
| Historical compatibility | All 40 Gold Draw JSON payloads compared byte-for-byte against base `1800697b`; retained first-Gold golden fingerprint and existing v1/v2/storage/API regressions | New padded-Q withdrawal/replacement/result paths must be versioned and proven before use |
| Admin consumption | Frontend accepts the new explicit algorithm and checks it against Draw state; focused contracts and production build | No new owner-level browser or complete Gold/Platinum tournament pass claimed |

The existing source hash, incomplete awards and native executor Main4/8 limitation
remain unchanged. **80/80 were blocked at the sporting execution audit; this Draw
work does not turn that audit into 80 played Editions.** No Master, source Package,
points/calibration, timeout or test policy is weakened. Final-head hosted evidence
and owner merge remain required for this candidate; older entries below are history.

---

# Historical frontend repair — merged as #1744

Merged base `7e92ad5ee714092263335420e0f6e8ed0b79a045` includes audit #1743.
The isolated repair has **3,423 passing frontend tests in all 364 files, zero
failures**, plus TypeScript/Vite production build. Local Python/backend, sporting
browser and long-Run gates were not rerun for these test/documentation changes.
There is no production code, Package data, API, calibration, workflow, timeout,
test selection or Master change. Final-head hosted checks and owner merge remain
required. This is still the same evidence index, not a new release declaration.

The repair preserves navigation, read-only, exact identity/source, conservative
legacy payload and private-data assertions using current canonical Saved DTOs.
It replaces obsolete legacy `getRun/listEvents` fixtures and old UI scaffolds;
sets English explicitly in English route tests; repairs inconsistent ordinal,
Race count/point and source-Branch positive fixtures; and reads exact comparison
players independently of the discovery sample. The source scanner excludes test
files from production-only rules, and Race guards now forbid reinstating preview
inference. Nine additional boundary/adversarial cases cover publication ownership,
metadata mismatch, public-head limits and unsafe week coordinates. A subsequent
full run exposed an inventory test race: the Lab picker test now awaits the
actual option and resets one-shot mocks, retaining every retry/selection assertion.

**Correction to the earlier audit:** planned-Edition mounts already receive a
Product Run context through `renderWithViewerProviders`; their principal error
was mocking retired readers, not omitting that provider. The historical 88-failure
result below is superseded by this scoped frontend result. The FAX execution,
automatic Entry, performance, recovery and retained full-scope gaps remain open.

---

# Historical integrated evidence checkpoint — 6 November 2026

## Audited source and method

Actual merged `buuk`: **`b666c109b9dc596a6d226025500ceb462a4fff8b`**, tree
`40a66e4b9f7146e015332f80ffe41dd4d2aaa65c`. This section updates the EXISTING
evidence map; it creates neither another Master nor another PAQ registry.
All prior dated checkpoints below remain historical evidence and do not override
this section's present implementation status or next-work ordering.

All 38 reviewed non-package PRs (#1700, #1702, #1703, #1705–#1730, #1732–#1740)
are merged. Git ancestry includes every exact approved feature head, and every
one of their 144 changed files equals its reviewed head's blob on this base.
No merge content loss was found. Open ATP package Drafts #1731 → #1741 → #1742
were inventoried, not reviewed or modified as part of this batch.

Review read AGENTS, the active Master/constitution and relevant acceptance,
Entry, geometry, storage, desktop and research contracts; inspected touched
runtime/read models and source consumers; compared both full frontend suites;
and executed the bounded backend/HTTP scenarios below on the actual merged base.
This is not a line-by-line recertification of all historical code or scholarly
sources, an exhaustive security audit, or a completed pre-alpha release gate.
Product statuses, sporting rules, coefficients and approved scope are unchanged.

## Newly executed evidence

Local environment: Python **3.12.14**, Node **24.22.1**, Linux. These are local
results, not a claim that the Windows executable or the CI Python 3.11/Node 20
environment was freshly rerun for this checkpoint.

| Check on actual merged base | Observed result | Meaning / limit |
| --- | --- | --- |
| `npm --prefix web run build` | TypeScript/Vite production build passed | Build is not browser or release acceptance |
| Complete `npm --prefix web test` | **3,326 passed, 88 failed; 13 failed / 364 total files** | Full frontend gate is RED |
| Same full suite at pre-batch `a07c51548ef3f398edba3e92551008ab2d61ec61` | **3,213 passed, 92 failed; 15 failed / 348 files** | Comparing exact failed test names finds **zero new failures**, four old failures now pass; this does not excuse the remaining 88 |
| Selected backend/tools/domain/HTTP tests | **193 passed** | Includes atomic late-audit Save rollback, Branch archive boundaries, backup integrity, three production Labs and paired Match Lab; not the full backend suite |
| `tests/api/test_native_one_edition_operator_journey.py` | **2 passed** | Actual MatchEngine, points, explicit Save, physical SQLite reopen and exact retries; one small Edition, not a reference FAX season |
| `python -m tools.audit_fax_native_playability --output <new-file>` | Expected **exit 2; 80/80 structurally blocked** | Correct diagnostic execution; NOT sporting acceptance |
| `python -m tools.preview_fax_reference_brackets --output <new-file>` | **80 source-bound topologies, 3,440 potential actual matches, 0 results generated** | Geometry only, not assigned draws or simulated Q/Main |
| Current-base hosted CodeQL | Python, Actions, JavaScript/TypeScript success | Static evidence only; Sonar remains red/advisory and is not dismissed wholesale |

The 193-test command selected `tests/tools`, `tools/tests/test_audit_earth_packages.py`,
`tools/tests/test_desktop_backup.py`, the new FAX topology and paired-Lab
domain/application/API modules, `test_labs_integration_production_labs.py`,
`test_pre_alpha_fax_calendar_80_edition_audit.py`, `test_admin_player_health_api.py`,
`test_run_working_draft_save.py`, `test_standalone_match_acceptance.py`,
`test_match_reconstruction_run_save_restart.py`, and the domain/API/boundaries/native
Branch archive modules. Local pytest had no PR changed-module filter. The desktop
negative test intentionally created a duplicate ZIP manifest and emitted its
expected standard-library warning. The complete backend, full sporting browser
matrix, actual reference season and 50-season campaign were NOT rerun here.

## Present engineering assessment and remaining path

| Requirement / existing authority | Current evidence and concrete limitation | Next action |
| --- | --- | --- |
| Integrated correctness / test policy | Approved feature contents survive merge; scoped tests pass, but the full frontend still has 88 baseline failures | Triage all 13 modules. Repair real faults or demonstrably stale fixtures/guards; never weaken provenance, privacy or routing assertions just to turn green |
| FAX full source Q/Main execution; §31.3/13/19/26 | Exact source fingerprint `e2150e66eef92943b56b2d22f3de26b8fe6c161669bd5d24c770c516f560e197`; 40 Gold Main24/Q16 and 40 Platinum Main32/Q24. Current `CalendarTourService` still rejects non-v3 Main counts outside 4/8. Pure geometry does not change the executor | Build exact player-/seed-aware Main/Q field/Draw and versioned global-slot/result execution; preserve real BYEs, original source IDs and legacy seeds |
| Entry eligibility, timing, points and publication | Merged timing uses decided 2+1-week preparation/ranking binding; `automatic_eligibility_status` is still `not_implemented`. Exact-source diagnostic reports missing awards for all 80 and an early-announcement conflict for four | Audit the consuming native path. Resolve only genuinely open policy/content with the owner; do not invent zeros, redate the fixture or substitute small main-only events |
| Real full season, Finals and 50 seasons | Small actual overlapping/two-signed-season gates are valuable bounded evidence. Neither W80 nor the evidence scanner supplies a completed full reference season | First actual Gold then Platinum, several authentic Editions/weeks, complete FAX season/Finals/rollover, then 50 seasons with restart/replay and resource history |
| Performance/storage; §31.18 | Existing paired measurements show removed copy work but no stable overall elapsed-time speedup. Cold verification remains expensive. New storage comparator measures supplied samples; it does not supply a long Run | Attach time, RSS, DB/WAL/SHM and Saved payload/branch growth to the actual staged reference runs; profile measured dominant work before choosing optimizations or budgets |
| Recovery/portable use; §31.5/6/18/25 | Portable Windows preview and offline verified backup are useful. ZIP verification is not actual restore; per-build data separation is not cross-version migration. `.sqbranch` 128 MiB remains an operation budget, not a Run quota | Demonstrate actual backup restoration and portable round-trip on sporting histories of measured size; use evidence before changing archive format/budget |
| Remaining full Master scope | Historical initial-cohort development/survival, permanent health consequences, lower Tours/Finals, general Records/holder history, milestones/watchlists/notifications and complete CS/EN Admin still need the retained map's producer→persistence→consumer evidence | Preserve these requirements. Locate/reuse existing implementations before authoring more mechanisms or claiming absence. Unknown coverage is not an approved deferral |

Specific frontend triage examples are already reproducible: the top-level source
guard's `*.tsx` glob scans `ViewerH2HSubroutePage.test.tsx` as if it were a
production deferred page; old planned-Edition test mounts omit the required
Product Run route context; several source guards expect superseded component
names. These observations justify individual test repairs, not treating all 88
failures as false positives. The shared `ViewerProductRunRouteContext.tsx` also
still renders literal **Official Branch** and English-only context/error text;
align visible labels with Viewer Branch and the existing CS/EN contract without
renaming historical stored fields or introducing privileged Branch semantics.

The 14 research archival PRs are accepted as research records, not new sporting
decisions or empirically validated model parameters. The paired Match Lab API is
a sensible isolated diagnostic for later calibration; its same-seed comparisons
do not themselves prove causal alignment, realistic distributions or source
equivalence. Read-only queues, comparisons and export helpers are useful, but
additional Viewer polish/research/tooling must not displace the real FAX path.
Keep the existing modular monolith and integrity contracts; no broad architecture
rewrite or speculative cache/schema migration follows from this audit.

**Recommended order:** (1) bounded frontend regression triage/repair; (2) one
source-bound Main/Q integration slice at a time, with concrete open product
dependencies separated; (3) actual progressive FAX acceptance plus resource
measurement; (4) reconcile retained side scope and perform the complete release
gate on one candidate. No new product decision is needed to start technical
triage. Only the owner merges. This checkpoint authorizes no release.

---

# Historical post-merge evidence map — 30 October 2026

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
