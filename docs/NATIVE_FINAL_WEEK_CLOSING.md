# Native final-week Edition closing authority

Base: owner-merged `buuk` `16c6ff737372d27b97c3237b21f7b988218df1ab`
(includes #1639 and #1640). One branch/PR; owner alone merges. Status: bounded implementation and local verification completed; final-head
hosted acceptance is the merge gate. Skipped Draft checks never satisfy that gate.

## Result and time

`calendar_terminal_edition_result.v1` represents an actual completed configured
Edition played at the end of its original Run calendar. It retains Run/Branch,
actual completed RunWeekPosition and original calendar, scalar closing eligibility
boundary, original creation/pre-play Saved sources, Edition/execution/played
fingerprints, actual per-player awards, validity and ranked state. It has no
`first_publication_week`. The scalar boundary is not a valid future Run position.
No RunWeekPosition, RankingWeek or calendar bound is relaxed.

The existing Edition factory reconstructs it from the approved draw, configured
point table and genuine MatchEngine tournament. Independent Saved/command replay,
actual ancestry and physical source verification remain mandatory. The terminal
receipt's calendar is bound to the actual pre-play Saved calendar. A rehashed
receipt is not proof. Ordinary results/commands/Saved records retain their old
shape and meaning; no stored record is migrated.

Closing Ranking uses the outgoing effective Best N, original result eligibility
and W-based validity, existing tie breaks, counted result evidence and retirement
rules. A result is unique per Edition/player. Inactive entrants remain eligible;
retirees are excluded. An inherited source owner may only come from the fully
verified native fork dependency graph, not request JSON.

## Operator workflow

The existing Tour and Full Simulation authorities still separate Entry/field/draw,
actual play, result confirmation, manual Tour Save, final review/approval, final
manual Save and explicit continuation of the same task. The worker never supplies
operator approvals or Saves. Opening the final selected week remains `target_reached`
before any of its tournaments are played. Run-end completion requires a real Saved
closure and settles as `complete`. Pause and Stop retain their existing semantics.

The Admin displays the terminal result boundary and separate Closing Ranking
points. The authenticated Saved final season summary includes its actual Edition
awards and archived Closing Ranking, without requiring a next-season transition.
No extra week, development, birthday, intake or Official snapshot is produced by
final closure.

## Explicit extension

The terminal result and original closure/task retain their original bytes and
calendar. A strict Run horizon extension does not retarget or resume those tasks.
A new explicitly reviewed command may perform the actual Season Transition.
Only on the now-available extended calendar does the ranking adapter project the
same source into the ordinary first-publication result at the newly opened Week 1.
This preserves the original eligibility/expiry boundary and source fingerprint;
it neither creates a second result nor retroactively claims that Week 1 existed.

## Evidence

- Initial focused existing domain regressions: 18 passed, 0.19 s.
- Expanded domain/application/physical dependency/projection/format contracts:
  104 passed, 3.35 s (unit/storage contracts, not sporting integration).
- Initial actual short original Run: final-week four-player/three-match Edition,
  separate approvals/Saves, uncertain confirmation retry, final Save late rollback,
  physical SQLite reopen, explicit completed extension and actual next-season
  continuation: 1 passed, 322.28 s on the initial runtime candidate.
- Actual independent native fork final-week completion, final Save rollback,
  physical restart and completed extension/Season continuation: 1 passed,
  225.64 s on the subsequent runtime candidate.
- Genuine Chromium final-week results review, three actual matches, separate
  result/closure approvals/Saves and physical SQLite restart: passed. The expanded
  repeat also opens Chromium against the physically restarted application.
- Focused frontend CS/EN/consent/client contracts: 91 passed, 5.93 s (mocked API
  contracts, distinct from actual Chromium acceptance).
- Production frontend build passed; current candidate still requires all relevant
  final-head acceptance. Failed development runs remain recorded as failures.

The production HTTP matrix, browser and adversarial evidence will be recorded
here when executed. Draft skips are not passes. This bounded slice does not
certify the whole pre-alpha or the reference 50-season release acceptance.

## Separate adversarial review

The separate pass traced result construction, ordinary and native-fork replay,
physical pre-play origins, final closure ancestry, approval/Save boundaries,
historical reads and strict extension. It found two additional boundaries:
independent forks report `run_horizon_exhausted` at their real final point, and
ordinary Saved terminal results also require an independently resolved physical
pre-play calendar (including rejection of changing the source to claim a future
publication). Both are addressed without relaxing calendar bounds. Source checks
reuse existing per-snapshot Saved proofs and do not add sporting replay to task
polls. No unrelated shared-file lint refactor is included.

A genuine completed/extended original fixture was copied by isolated SQLite
backup, cold reopened and validated with the new source verifier. Six separate
rehash attacks changed result owner, played source, eligibility time, points,
the physical pre-play horizon and final summary. All were rejected: complete
positive/rejection run 100.05 s. This is reused genuine sporting evidence, not a
new manually inserted result or a second fresh MatchEngine acceptance claim.

The source is also checked through the existing Saved-only Viewer season-summary
API; it remains separate from ordinary Official Ranking and Branch selection.
Known broader Viewer work remains outside this slice.

The minimum currently supported real Tour fixture is W4: native Tour requires an
already Saved Week 2+ sporting checkpoint, the announcement must become public
on a future Week Transition, and an entire announcement week must precede play.
The existing W3 empty-final-week closure fixture is retained as a separate task
contract; no initialization or announcement guard is weakened.

A new runtime fork selecting a historical source after a Run extension now Saves
an envelope with the already available current Run horizon. Its baseline, actual
week and selected source retain the original calendar. Pending v1 installations
retain their exact older envelope semantics. A source Closing Ranking is visible
as inherited Saved history; it never becomes the target Branch's own completion
marker or starts/retargets a task. Actual nested continuation passed in the expanded short scenario; a fresh
read of its inherited summary and task non-mutation passed separately in 18.25 s.

## Stable-candidate local verification

| Evidence | Actual result |
| --- | --- |
| Production original + independent fork final-week completion, explicit Saves/rollback, SQLite restart, completed extension and actual nested inherited continuation | 2 passed, 711.29 s; current source-validated short fixture |
| Final-week real Admin Chromium, separate result/closure approvals/Saves, physical SQLite reopen and Chromium opened against the restarted application; Saved Admin/Viewer summary | passed, 174.02 s |
| Complete actual W52 original timeline, last-week four-player/three-match Edition, final Save, restart and extended continuation | passed, 993.08 s on the preceding runtime candidate |
| Same genuine W52 fixture, isolated SQLite backup and cold reopen with the final physical-source verifier | passed, 37.83 s; this is source/recovery evidence, not another fresh all-weeks execution |
| Two actual Editions, six matches, 440 awarded points and effective outgoing Best N = 1 | passed, 438.40 s on the preceding runtime candidate |
| Same genuinely completed/extended original fixture and six separately rehashed result/physical-source/closing attacks | positive and all six rejections passed, 100.05 s |
| Actual inherited final summary / original marker / explicit extended publication / terminal task non-mutation, fresh application and backup | passed, 18.25 s |
| Focused domain/application/Saved proof/source projection/root compatibility contracts | 132 passed, 2.16 s |
| Focused frontend CS/EN, missing publication, consent, retry and task/client contracts | 91 passed, 5.26 s; API mocked, separate from actual Chromium |
| TypeScript / production Vite build | passed, 4.68 s Vite phase |

Failed development attempts remain in the logs: initial socket permission setup,
the fork's distinct terminal-horizon blocker, the historical fork's old-envelope
range mismatch, a test-only TypeScript selector option and a scratch proof's
incorrect assumption about an already-settled task state. They are not counted
as passes; the corrected production paths and assertions above actually executed.

Run the complete six-case final-week HTTP matrix through
`tests/api/test_native_final_week_closing.py`, the existing task/season matrices
and `scripts/native_full_simulation_browser.py`. The dedicated workflow retains
actual SQLite artifacts and still executes every original negative check, W52/
W61/W80/short transition case, task recovery/fencing case and real browser gate.
The relevant native Tour, Season, Saved Branch and shared control/browser gates
remain required on the same final PR head. Refer to the actual PR checks for the
hosted result; none of these local rows substitutes for a pending final-head gate.
