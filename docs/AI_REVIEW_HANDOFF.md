# Active takeover — 13 November 2026

Radim asked Work to independently review and finish Claude's five native packages.
The pinned source heads, observed fixes, evidence boundary and remaining release
limits are now at the top of `CURRENT_STATE.md`. Work owns the active integration
branch `fix/claude-native-readers-integration-20261113`, including the shared Tour,
Saved, career, season and alert files during this review. Do not repeat the old
queue or write concurrently into those files. Claude's original PRs remain open;
no middle stack is independently approved merely because a later head passed CI.
Owner alone merges the final reviewed candidate. Older instructions below retain
product context but their completed assignments are not new work to reimplement.

---

# AI repair handoff — 12 November 2026

Current assignment, expanded at Radim's request on 12 November with three
follow-on implementation packages. This follows Work's review of all 17 open
Claude PRs and replaces
the 11 November repair prompt; the old findings remain dated history in the
[existing evidence map](PRE_ALPHA_INTEGRATION_2026_10_30.md). This is a one-month
trial, not a subscription commitment. Radim owns every merge.

## Confirmed owner decisions and current division

Radim confirmed both decisions in the Work chat on **12 November 2026
(Europe/Prague)**:

- Turn Pro uses the player's own imperfect self-view; overconfidence and
  underconfidence are possible. No hidden true opponent strength.
- Entry is practically certain, never forced by age/delay. An extremely rare
  career ending without Turn Pro is an explicit recorded exception.

The separate Turn Pro event, association-only eligibility including WC, direct
v87 reference FAX/Saved Draw path and default for new Admin Runs were already
confirmed. Historical policies keep their original semantics. Timing, ranking,
publicity and numerical calibration retain the Master labels; this review does
not silently approve every detail in Claude's proposed #1765.

**Work completed:** #1784 consolidates #1766/#1769 and restores the positive
Reconstruction test's lost `pr_critical` marker; 22 focused tests pass, including
both real successful Reconstruction and missing-Health rejection. Production
config is unchanged. Work #1785 reconciled #1765 with the
owner's confirmations, retaining current ATP/coordination evidence. Both #1784
and #1785 are now owner-merged. Do not redo either repair; fetch the
actual latest buuk before continuing.

**Claude owns, in order:** the final Turn Pro repair, the separate Saved Draw UI
repair, then the native career/milestone, seasonal-summary/comparison and
following/notification packages below. These are authorised implementation
packages, not a request to return only another plan. Work independently reviews
the results and owns ATP source/schedule/slot integration. Shared Tour/persistence
writers require an explicit file-boundary handoff, not competing implementations.

## Separate ordinary-ChatGPT assignment — queue 2

Owner has merged #1788/#1791/#1792 after Work's independent review and corrections:
85 combined frontend tests, typecheck/build and final-head CI/CodeQL/Sonar passed.
Browser execution was blocked by the environment and is not claimed.

At Radim's request the next bounded queue is documented in
`docs/CHATGPT_PARALLEL_RUN_VIEWS_TASK.md`: (1) recent-Run history management on
Admin Home; (2) URL filters for legacy EventsPage; (3) URL filters for legacy
SnapshotsPage (Ranking/Race). Reserve only those pages, recentProductRuns helper
and their isolated tests. They do not own global favorites/following, native
career/season views, backend or the API client. Independent PRs use fresh buuk.

Claude keeps Tasks 1–5 below; Work keeps ATP. Check actual open PRs before shared
edits. These new assignments are not implementation evidence or new product canon.

## Prompt to paste into a NEW Claude Code chat

You are continuing Squash Engine for Radim. Implement autonomously within this
assignment. Work is technical lead, active developer and independent reviewer;
Radim alone merges. Read `AGENTS.md`, `CLAUDE.md`, `CURRENT_STATE.md`,
`ROADMAP.md`, this file and the current integration evidence map before editing.
Map the canonical Master's structure and read the full relevant clauses/statuses
for each package, including 9.2, 19.2, 21.5, 25.6/25.6.1, 27.23/27.25 and 36.
This handoff selects work; it does not replace the Master or discard its other
pre-alpha requirements.

### Start from the real current heads

- Repository: `Jasmetk0/squash-tour-beta`; integration branch: `buuk`.
- Current owner-merged base at this prompt expansion:
  `6e4066a8359307be4d89c0f9202260bcc69a4e92`, including #1784 and #1785.
  Fetch current refs; do not assume this remains the latest baseline. The prior
  runtime audit used `a86053f7ded5b72cd594f7e51ce64ab6ea43d11b`.
- Runtime #1783: `claude/turn-pro-self-perception-v87`, reviewed head
  `06b41e45467f1131883787e4ef3697a3339977a0`. It already contains the former audited
  `buuk a86053f7` and the entire chain #1767 → #1768 → #1770 → #1771 → #1772 → #1773 →
  #1774 → #1775 → #1776 → #1777 → #1778 → #1779. Its real delta is 41 files,
  +3922/-70 versus buuk, not every ATP file seen in a two-dot parent comparison.
- Work #1784: `feat/claude-entry-test-review-20261112`, reviewed head
  `95c704c4683933cf8836d8ba0303b1200a7513a4`, contains the two useful test repairs
  AND restores the positive Reconstruction marker. It is already in buuk; retain
  it when integrating the latest base. Never copy the uncorrected #1769 over it.
- Work's documentation #1785 is already merged. This expanded prompt is on
  `feat/claude-next-work-packages-20261112` until its owner merge. If necessary,
  fetch/read this file from that branch. Do not replace current coordination/ATP
  evidence with #1765's old versions. The owner decisions already apply.

Continue the existing runtime branch through normal commits if your environment
allows it. Otherwise create ONE coherent Draft continuation PR from the latest
#1783 head, explain the dependency and final-head diff, and leave #1783 intact.
Do not make another chain of one-feature PRs, force-push, merge, enable auto-merge,
write directly to buuk or close predecessors without Radim/Work's decision.
Do not merge intermediate v1-model heads as standalone production defaults.

### Task 1 — finish the supported Turn Pro path as a reviewable whole

1. **Make decision knowledge inspectable and historically exact.**
   `turn_pro_model.py::decide_turn_pro` hashes the candidates/observations, then
   creates `PlayerTurnProDecision` without an observation field. The stored
   `CalendarTourTransition` contains decisions and policy, not candidate bodies.
   Thus the PR/docs claim that every decision stores `TurnProObservation` is
   currently false. The default-model API test's comment asserts that claim but
   only checks a public player ID. Fix the actual evidence boundary and test it
   after Save, SQLite restart, restore and fork. A compact versioned positive
   decision observation, or an authenticated exact historical reconstruction
   with an inspectable read, is acceptable; a hash alone is not that read.
   Preserve already-recorded v1/v2 bytes/fingerprints and their replay outputs:
   adding an optional field only to today's replay output is NOT compatible.
   Do not persist all 57 observations for every prospect every week or build a
   new scouting subsystem. Keep hidden knowledge out of Viewer/public events.

2. **Complete model verification on every supported producer/replay path.**
   In `infrastructure/db/calendar_tour.py`, the older Tour path calls
   `_turn_pro_replay_lifecycle`, feeding recorded decisions into lifecycle, but
   does not regenerate them using the recorded model/then-known inputs. Native
   birth/competition/fork replay does rerun the model. The default-model demo
   currently uses the older Tour path, so changing today's defaults and seeing
   an unchanged view does not alone prove historical model replay. Close this
   gap with versioned receipt/input ownership and negative cases for changed
   model, observation, seed, decision and foreign/stale Saved source. Separate
   DTO consistency, mathematical replay and physical Saved origin verification.
   Preserve old recorded history; do not blindly reinterpret old v57 or v1/v2
   artifacts with a new model. If an old schema cannot supply a required proof,
   keep its genuine historical reader and add an explicit new-writer boundary.

3. **Do not silently skip pre-Tour weeks under the new default.**
   `application/calendar_sporting_week_service.py` intentionally advances no
   lifecycle on the exhibition/pre-Tour path. Yet a new Admin Run defaults to
   v87 and must advance at least once before Tour initialization. Connect the
   actual early-week writer to the existing versioned authoritative lifecycle,
   or route the v87 flow through the equivalent complete owner. Prove the first
   eligible transition, several early weeks and later Tour adoption; no missing
   or duplicated decision, no age-forced entry and no first-application fallback.
   Keep explicit preview/confirmation/Save and old exhibition behavior intact.

4. **Make the confirmed never-pro exception visible in actual history/audit.**
   `retired_without_turn_pro_player_ids` is already in the public transition
   event. That is useful but is not the complete promised career/audit evidence.
   Use existing retirement/history/audit infrastructure for a persistent reason
   and a read-only explanation, including restart/restore/fork. No fake Turn Pro
   and no invented health cause. Use a deterministic rare-case fixture without
   changing production calibration. A full new notification/editor subsystem is
   outside this task.

5. **Prove the direct native FAX path under v87.**
   The copied-FAX reference materializer still uses legacy lifecycle. Existing
   green FAX Reference Preparation is not v87 acceptance. Use the native calendar
   population and genuine Saved source/Entry/Draw commands for at least one
   association Edition; both Ranked and Unranked reject a non-professional and
   accept an eligible real professional. Carry actual Q winners to Main where
   applicable, play real MatchEngine, confirm points, explicit Save and reopen.
   Do not mark prospects professional because they appear in an old Draw, weaken
   Health/ownership checks, add the rejected first-application bridge, fabricate
   results or rewrite ATP helpers. Show which reference paths remain legacy;
   do not claim the entire 80-Edition/50-season release from a bounded flow.

6. **Final evidence and performance.**
   Run focused changed contracts and real v87 HTTP/SQLite acceptance. Include one
   genuine default-v2 prospect → Turn Pro → normal Entry/WC → real played Edition
   → next ranking → Save/restart, with inspectable exact decision evidence and
   historical-default independence. Keep separate deterministic eager-policy
   fixtures clearly labelled. Exercise birth and fork/restore, simultaneous-slot
   inputs, W52/W61/W80 annual timing, current-source ownership and rejection of
   future/unannounced events. Preserve frozen slots/strict horizon extension.
   The earlier wrap-serializer regression was repaired by `exclude_if` in
   `06b41e4`: do not reintroduce it, change old omitted-field bytes, raise timeouts
   or remove the W80/1000 proof just to get green CI. Measure any new Saved size
   or replay cost rather than assuming it is negligible.

Financial Level remains unknown until it exists as a real engine input. Current
numeric perception errors, threshold 100, age bases and personality/opportunity
weights are provisional calibration, not new owner-approved canon. Do not ask
again about the confirmed self-perception/never-pro principles. Ask Radim only
if a genuinely new product choice blocks implementation; present alternatives
and a concrete player/Run example.

### Task 2 — separate read-only UI repair after Task 1 is reviewable

Review/integrate #1764 (`4099a5f5caa9c1f0504d2a81edf0ff3ce59eb2c2`), now conflicting
with buuk, in a separate coherent branch/PR. Do not overwrite Work's ATP client
wrappers or current-state text. Its 35 focused tests pass, but Work independently
reproduced two accepted invalid inputs in `web/src/api/savedNativeReadiness.ts`:

- a first-entry trigger with `schema_version='future_unsupported.v99'`;
- a Ranked preflight labelled complete with `required_point_stages=[]`.

Validate the actual versioned contract and required stages; add focused negative
checks for these real gaps. `SavedDrawNativeReadiness.tsx` also states that only
Ranked adoption requires native Entry. Explain legacy Saved first-entry evidence
separately from v87 professional eligibility (required for Ranked AND Unranked),
without claiming the historical first-entry rows establish today's pro status.
Keep current-Saved/same-source checks, CS/EN, archived/foreign rejection and the
Admin-only/read-only boundary. Do not add an adoption button or a second writer.
Run the relevant API/component/page tests, typecheck/build and the actual changed
page's Chromium acceptance; account for shared `api/client.ts` path filters.

### Task 3 — native player careers, milestones and retirement summary

**Product basis:** Master 9.2, 21.5 and 27.25. Deliver a usable native Run player
profile section: concise career overview, filterable timeline, factual milestones
and a retirement summary, with real underlying evidence links and CS/EN. This
extends existing readers/components rather than creating a second player profile.

- First audit the current readers, especially `player_career_query_service.py`,
  `player_career_performance_query_service.py`, `PlayerCareerPage.tsx`, Saved
  player navigation and native signed records. The legacy career service walks
  connected legacy Run trees; that is not authority to combine sibling native
  Branch histories. Use authenticated selected Run/Branch/reachable Saved time,
  actual public events, matches, results, ranking snapshots and supported Health.
- Include Turn Pro/debut, first evidenced title, first TOP-100 entry, career-high
  published ranking and retirement where data exists. Preserve source identity,
  covered period and unknown/unsupported cases. A player with partial prehistory
  has a *first recorded title*, not an invented first lifetime title. A missing
  injury/return source is unavailable, not a guessed event.
- Derive achievements from existing immutable facts. Reading a page creates no
  events, Save or sport. A retirement summary survives restart/restore and links
  to that player's recorded career, including the never-pro exception from
  Task 1. Do not duplicate Task 1's audit/exception implementation.
- **Acceptance example:** P turns pro in Week 4 and wins its first evidenced
  Edition in Week 10. The Week-3 view contains neither future fact; the Week-10
  view links both to exact sources. A fork where P loses has no inherited future
  title from its sibling. Cold restart and later source/default changes preserve
  the old view. Show this through real HTTP/SQLite plus the actual Admin profile
  in Chromium; UI mocks alone are not completion.

Do not redesign development, scoring, injuries or retirement AI to populate the
page. Keep exact milestone catalog/layout extensible and calibration labelled.
A complete new Viewer frontend or annual Awards is outside this package.

### Task 4 — completed-season overview and country/season comparison

**Product basis:** Master 6.5/6.9, 21.5, 27.25 and 31.40. Deliver an Admin seasonal
archive with a compact summary, detailed player/country/Edition tables and
comparison with the previous OR another recorded completed season.

- Extend `application/calendar_tour_season_summary.py`, its actual Saved API and
  existing native Tour season-summary/record UI. They already provide bounded
  national comparison; audit and complete the missing product flow, do not
  rebuild it or report their existing functions as new work.
- Use signed Season Transition/terminal closure and actual authoritative played
  Edition results. Include available end-of-season ranking, major winners,
  evidenced debuts/retirements/milestones, and explainable changes. Respect the
  distinct Week-W published ranking, outgoing-policy Season Closing Ranking and
  next-season Week-1 ranking. Preserve final-week results and closure ownership.
- Country comparison shows explicit metrics (e.g. titles/finals, TOP-10/100,
  highest-ranked player), not an invented mandatory composite country score.
  Keep historical sporting representation/identity where available. Changed
  categories, policies or definitions expose limited comparability; missing
  or unplayed history is not zero. Do not silently use current nationality,
  present-day rules or future results in an older summary.
- **Acceptance example:** complete two real bounded populated seasons, compare
  both directions, then extend the Run or continue another Branch. The old
  summaries and their sources remain unchanged. Cover W52/W61/W80 in separate
  Runs, keeping each Run clock fixed. After automated continuation of
  several short test seasons, every completed season remains accessible; no
  extra pause, implicit Save, duplicate closure or fabricated full-season pass.
  Prove real HTTP/SQLite cold restart and actual CS/EN Admin navigation.

Reuse the existing summary projections/closures. If any shared sporting writer
hook is essential, coordinate the small boundary with Work first; do not rewrite
ATP scheduling, points, Week/Season mechanics or stop rules. This package does
not certify the reference 50-season release.

### Task 5 — following and milestone notifications from the same facts

**Product basis:** Master 25.6/25.6.1 and 27.23/27.25. Deliver the bounded Admin
following/attention flow over the achievements and summaries above. World Event
Log, Audit Log, Task Center and Notification Center retain distinct meanings.

- First discover what actually exists. Current `full_simulation_summary.py`
  explicitly reports watched events/notifications unavailable; a Master target
  is not evidence of an implemented watchlist service. Reuse real infrastructure
  when present; otherwise implement the smallest coherent V1 of the approved
  model, not a second parallel watchlist or a speculative full editor.
- Player/country follows use the Master Run-level scope; event/history/notification
  sources retain their exact Branch/time scope. Followed players get ordinary
  personal milestone notifications; others still retain those facts in career
  history. A followed country includes collective successes, meaningful domestic
  leaders and exceptional individual achievements, not every minor event of
  every representative. Label configurable leader/importance selection as
  provisional calibration, with an explainable criterion.
- Group related milestones into a readable item with source-linked details.
  Dedupe the same event matching both player and country follows and exact retry,
  reconnect/restart. Reading, hiding, muting or marking a notification read must
  not delete the underlying facts or influence sport/RNG. Respect the existing
  save/preferences ownership rather than inventing an implicit Run Save.
- Keep supported UI clear and bilingual. No future knowledge, technical warnings
  in public Viewer, notification-driven pauses or new stop-rule mechanism. Full
  badge taxonomy, broad watchlist editor, News Importance Score and editorial
  story generation are not prerequisites.
- **Acceptance example:** following P and its country yields one grouped card
  for P's first recorded title plus a ranking milestone, with both separate
  historical facts accessible. An unrelated ordinary player milestone stays in
  history without an ordinary personal alert. Read/mute persists appropriately;
  repeat/restart does not duplicate delivery or change match results. A historical
  or foreign Branch view reveals no later/sibling event. Exercise real persistence
  and the actual Admin UI, not only a hard-coded notification fixture.

### How to continue across the packages

These follow-on packages are authorised now; do not stop after the first tiny
repair to ask whether you may continue. Start with Tasks 1 and 2, then take the
next feasible complete package in the order above. This is a queue, not a demand
to finish all packages in one huge PR or one response.

Before editing a package, inspect the current owner-merged baseline, open PRs,
actual implementation and current Work assignment. Write a short scope/boundary
note in its PR and start implementing. Skip already completed work with source
and test evidence. Deliver backend + API + supported Admin flow + real persistence
and focused acceptance where required, rather than disconnected helpers/mock UI.
One coherent Draft PR per package; finish and test a stable head before starting
another. If a package proves too large, split only at a complete usable boundary
and explicitly preserve the remaining requirement.

Hand completed PRs to Work for independent review. You may continue an independent
package from current buuk while that review is pending. If the next package needs
unmerged work, disclose the dependency and choose an independent package when
possible; never treat your own green tests as owner merge approval or create a
long unreviewed cumulative stack. Do not close predecessors unilaterally.

Work owns ATP Packages, source/calendar mapping and native scheduled Q/Main slot
integration. Claude owns lifecycle and the career/summary/notification readers
above. Shared `calendar_tour_service.py`, Tour schemas, persistence and the API
client require a clear single active writer; prefer existing adapters/projections
and a bounded handoff for unavoidable shared edits. Do not redesign another
owner's work just because you touch a shared file.

Implementation choices and labelled provisional calibration are autonomous.
Unresolved product decisions are not: ask Radim only when they block the current
package, explain the consequence, and give two or three concrete options plus
an example. Continue independent authorised work when possible. Do not implement
finance, travel, referee, country DNA, scouting or other new subsystems as a
prerequisite or invent new canon to fill an empty dashboard.

### Handoff and checks

- Stable final head(s), actual parent and own delta against fetched current buuk;
  complete changed-file explanation, compatibility/version choices and known gaps.
- Exact commands/results/artifacts; distinguish authored self-review from Work's
  independent review, contract mocks from genuine HTTP/SQLite/Chromium execution.
- Preserve production Entry blob `02fd58856ca05ca248c20373fa8a296c72d4c797` and zero
  unintended config diff. Inspect staged and unstaged files after tests; do not
  stage generated test pollution.
- Assess Sonar's current reliability failures (#1764 and #1783) from their actual
  issue details. Correct real issues or document a demonstrated false positive;
  do not suppress gates or treat Sonar as product authority.
- Final-head applicable acceptance must really execute and pass, by Ready or
  manual workflow dispatch. Existing #1783 exact-head seven manual workflows
  passed, but not every Draft-skipped fork/groups/global-slot gate has an
  equivalent current-head run, and most fixtures use historical policy. New
  behavior must have v87 evidence; a skipped or old-head pass does not count.
- Preserve corruption/rollback/retry negatives, legacy bytes and the full release
  policy. Ordinary PR review is not a 50-season/pre-alpha release certification.
- Update the existing state/evidence map; no parallel authoritative status ledger.
  Hand off each concrete reviewable result and remaining limitations, then
  continue the next independent authorised package as described above. Radim merges.

## Reusable task brief and review checklist

A task brief needs: problem/result; approved Master clauses; owned files and
shared boundaries; explicit non-goals; supported inputs/failure cases; actual
acceptance commands; final-head evidence; next dependency.

Before a merge recommendation:

- Verify exact head/base, ancestry, own delta and complete `buuk` diff.
- Inspect configuration/data changes against the trusted base, including changes
  inherited from a predecessor; inspect unstaged and staged changes after tests.
- Check immutable Saved/schema/hash compatibility, source ownership, explicit
  Save, exact retry, rollback and genuinely exercised restart/replay/fork paths.
- Check simultaneous inputs, chronology and then-public AI knowledge.
- Require the relevant final-head checks to execute successfully. Keep local,
  component, HTTP/SQLite, Chromium and full-season evidence distinct.
- Record an author's adversarial pass honestly; do not call it an independent
  second-AI review. Use an actual independent reviewer when available/justified.
- Merge belongs to Radim. Sonar/CodeQL are evidence, not product authority;
  document a validated false positive rather than hiding a real finding.

Fast CI adds a final tracked-worktree guard to its backend, Python-3.12 security
and frontend jobs, including failed test runs after a successful checkout. It
checks the repository root even from `web/`, and catches staged/unstaged writes.
It does not detect a bad value already committed in HEAD, audit untracked outputs,
or cover the separate acceptance workflows; it complements review and isolation.

## Work allocation and light trial ledger

| Work item | Developer | Current evidence / integration state | Review or repair cost |
| --- | --- | --- | --- |
| Turn Pro chain, final #1783 | Claude | Config restored; own-self v2 implemented; seven exact-head manual workflows pass; observation, older replay, pre-Tour and FAX-reference gaps remain | Configuration incident corrected; serializer performance regression corrected; Work review found the additional evidence gaps |
| Test isolation/Health #1769 and stale-intake #1766 | Claude, consolidated/corrected by Work in #1784 | 22 independent tests pass; positive critical-CI marker restored; hosted status must match #1784 final head | Marker moved accidentally during negative-test insertion; production Health guard preserved |
| Proposed Master #1765 | Claude, reconciled by Work | Explicit owner confirmations now recorded without mathematical guarantee or hidden opponent strength; calibration stays provisional | Old contradictory summaries and stale coordination removal corrected |
| Saved Draw readiness #1764 | Claude | 35 independent focused frontend tests pass; two validator gaps reproduced; policy copy and actual browser acceptance still need work | Separate follow-up after lifecycle candidate |
| ATP #1763/#1780/#1782 and coordination #1781 | Work | Owner-merged into reviewed buuk; native public ATP Run integration remains a separate dependency | No runtime acceptance inferred from data/scheduled component proofs |

Earlier Claude work predates this coordination. Actual effort, cost and trial
expiry have not been supplied. At the trial end compare accepted functionality,
regressions and review/integration work on similarly risky tasks; PR/line/test
counts are not productivity scores. Radim decides whether to renew or stop.
