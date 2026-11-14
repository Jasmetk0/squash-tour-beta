# Claude long native Run reads and two full seasons — 14 November 2026

Base `buuk 342b826d20b43055f5e1117bab8d58176259360c` (#1801 merged). Claude's Draft PR
(branch `claude/ecstatic-davinci-qpie07`) measures and speeds up Saved Tour/season-archive
reads of long native Runs and adds two-complete-season W52/W61/W80 acceptance. Details,
inputs, raw before/after numbers and limits: `docs/NATIVE_LONG_RUN_SAVED_READ_PERFORMANCE.md`.

- Measured causes: FIFO-128 proof eviction (lineages >128 re-decoded every read), the
  same Saved text hashed 3–4× per revision per read, quadratic dependency-graph
  construction, cyclic GC, and a recursive cold validation keeping every decoded
  payload alive at once (W52 after one season: 3.1 GB peak).
- Changes keep every physical/owner/source/replay gate, public DTO, Saved byte,
  fingerprint, seed and sporting rule. No Entry, tournament rule, point table,
  calibration, frontend or ATP file is touched.
- `test_two_closed_seasons_archive_compare_extend_and_restart[w6|w52|w61|w80]`:
  fast `w6` stays in the existing job by exact node id; the long clocks have a
  separate `long_seasons` CI job. The 120 s read transport bound is unchanged.

Not certified: 50-season reference release, 1,000-player long Runs, browser execution.
Per-read cost remains linear in the total bytes of the lineage (each Saved Revision is a
full snapshot); longer horizons need a storage/proof decision (see the document).

---

# Work takeover of Claude native features — 13 November 2026

Owner asked Work to review and finish Claude's implementation. Owner-merged base
is `buuk fcf0deb9cfcb525641f20d73b03f5bdb3d647d3f` (includes #1800/#1796/#1797/#1798).
The implementation candidate combines these pinned, unmerged Claude tips:

- #1799 `bf1cef4d6d9bdd4f9a5ad020e2b5fefed227573d` (contains #1793 `0aa87ec3`
  and #1790 `ea6b2307`, including the older Turn Pro chain).
- #1795 `3cc3ab69b065fb2e019b1e9df510b17c87300227` (season archive).
- #1789 `8ea924f0d018f98ab5b2e39511848a99a92af29e` (Saved Draw reader).

Work's integration branch is `fix/claude-native-readers-integration-20261113`.
It resolves the real client/router merge conflicts and repairs observed issues:

1. Opening professionals use their own recorded self-perception under a new v2
   evidence boundary. The old true-strength v1 reader retains its original bytes.
2. New v4 exhibition advances record actual weekly Turn Pro decisions/model and
   lifecycle/never-pro retirement evidence before Tour initialization. Preview,
   commit, exact retry and replay bind those inputs; initialization copies them,
   rather than evaluating the past under a later default. Old v1 advances remain
   a compatibility path, not silently rewritten history.
3. Every improved career ranking remains in history; a later improvement cannot
   erase the earlier alert or change its anchored identity. Country alerts use
   the domestic leaders at the fact's week. Real never-pro retirement/restart
   is additionally tested, including a historical view before retirement.
4. Native birth identities come from the authenticated Saved lifecycle/prospect
   source, even before the first match; future source records are excluded.
5. Alert acknowledgements carry the number of facts actually displayed, so a
   delayed/repeated read acknowledgement leaves later facts unread.
6. Season comparison detects changed stored point tables and draw formats; other
   unsupported comparisons remain explicit. Invalid career/season responses fail
   closed instead of inventing facts or crashing the panel.
7. Fast CI's changed-module selector falls back to actual critical tests when
   there are no changed critical tests. The prior red checks on #1789/#1795 were
   reproduced from logs as pytest exit 5, not failing runtime assertions.

Local review initially passed all 381 frontend files / 3,585 tests. After the first
repairs all 3,587 tests passed; the final additional acknowledgement/identity cases
have focused checks and must also pass the final candidate gates. Two alert and
two career-validator regressions were failing-before/passing-after. Additional
unit and real HTTP/SQLite checks exercise the new writer boundaries. Consult the
candidate PR for exact final-head results, not older source-branch checks.

A new Ready/manual workflow runs genuine lifecycle/career/alerts/season HTTP/SQLite
and all four actual CS/EN reader browser scripts. Local Chromium is blocked by
process-singleton `socket()` EPERM; no local browser pass is claimed. Wide two-season
W52 remains a separate, unverified long test; its added 1,800-second transport timeout
was restored to the normal 120-second limit. One closed W52/W61/W80 season and
short-clock multi-season proofs do not certify two full wide seasons or the
50-season pre-alpha release. Saved growth/replay performance remain release work.

This is an unmerged integration candidate, not merge approval or full pre-alpha
completion. Work is the current writer/reviewer of these shared files; Radim alone
merges. No sporting calibration, Master rule, shared FAX source or production
configuration was changed. Earlier status/queue entries below are dated history.

---

# Ordinary ChatGPT review and second queue — 12 November 2026

Owner-merged base `buuk 8c2507bfe20601c5dd7b7fc7a47c48c5190180e9` now includes
#1788/#1791/#1792. Work reviewed all source/test changes, corrected the null URL
filter bug with two failing-before/passing-after regressions and paired duplicated
feature translations. Combined final sources: 85 tests, typecheck/build passed;
all final CI/CodeQL/Sonar passed. No browser pass: local Chromium was blocked by
EPERM and the cloud browser could not reach the local application.

Radim requested a second queue for this contributor: recent-Run controls on
Admin Home, URL filters for the legacy Events reader, then Ranking/Race snapshot
URL filters. Full source boundaries, examples and acceptance are in
`docs/CHATGPT_PARALLEL_RUN_VIEWS_TASK.md`. These are new assignments, not completed
features. Claude retains native lifecycle/career/season/notification work; Work
retains ATP source/calendar/Q/Main integration. No sporting rule or Master changed.
Earlier dated queue and pending-merge statements below remain history.

---

# Expanded Claude work queue — 12 November 2026

Owner has merged #1784 and #1785; the refreshed baseline is
`buuk 6e4066a8359307be4d89c0f9202260bcc69a4e92`. Radim requested a new Claude-chat
prompt including larger follow-on implementation packages, not only the repairs.
The existing `docs/AI_REVIEW_HANDOFF.md` now authorises, in order: Turn Pro repair,
Saved Draw read-only UI repair, native career timeline/milestones, completed-season
summary/comparison, and following/milestone notifications. Each has a product
basis, source boundary, concrete acceptance example and complete-PR handoff.
These are assignments, not new implementation evidence or new product decisions.
Claude may continue independent packages while Work reviews completed results;
shared sporting writers require a single owner. Work retains ATP source/calendar
and native Q/Main slot integration. Earlier pending-merge wording below is dated
history; #1783 runtime remains unmerged and unapproved at this checkpoint.

---

# Claude review checkpoint — 12 November 2026

Reviewed `buuk a86053f7ded5b72cd594f7e51ce64ab6ea43d11b` includes owner merges
#1763/#1780/#1781/#1782. All 17 remaining Claude PRs were inventoried by actual
ancestry; the complete final lifecycle candidate is #1783 `06b41e4` (41 files),
not 13 independent runtime releases. Its seven manual acceptance workflows pass,
but important v87 paths/evidence and other applicable gates remain incomplete.

Work #1784 combines the useful #1766/#1769 test repairs and restores the positive
Reconstruction `pr_critical` marker: 22 independent tests pass and actual final-head
Fast CI/CodeQL/Sonar pass. No production config or Health guard changed.
The accompanying Master v87 consolidation records the owner's 12 November
confirmations: own imperfect self-view; near-certain entry without forced age,
with explicit history/audit for the rare never-pro career. Calibration remains
provisional; no runtime merge or release is implied.

Next Claude task: exact historical decision evidence, older Tour model replay,
early pre-Tour weeks and direct native FAX/never-pro integration; then separate
read-only Saved Draw UI correction. Work owns independent review and the ATP
source/scheduled integration; avoid concurrent shared Tour/persistence writers.
The [current evidence map](docs/PRE_ALPHA_INTEGRATION_2026_10_30.md) contains all
17 pinned heads, findings, checks and the bounded merge recommendation. The
[new Claude chat prompt](docs/AI_REVIEW_HANDOFF.md#prompt-to-paste-into-a-new-claude-code-chat)
is ready to paste. Owner alone merges. Earlier candidate entries below are dated
history and do not certify current runtime or full pre-alpha completion.

---

# Turn Pro continuation — 12 November 2026 (draft PR, not owner-approved)

Own delta over #1783: positive decisions store the prospect's own observation
(`decision_evidence: observation.v1`, versioned through the model policy; earlier
v1/v2 bytes unchanged); replay recomputes chance/draw and checks the observation's
internal consistency; Tour initialization records Turn Pro for every exhibition
week before the Tour (`CalendarPreTourTurnPro`); the existing player read gains a
read-only `turn_pro` block incl. the never-pro exception; Saved FAX Draws are
tested under v87 for Ranked and Unranked.

Measured (provisional): one positive decision grows from 500 B to 2503 B (+~2 KB,
57 perceived attributes dominate); verification is ~0.05 ms per decision. The Tour
state is part of every Saved revision, so ~3000 AI professionals would add ~6 MB per
revision. A compact attribute encoding is the obvious reduction if this proves too
large; it was not done here. Limits: observation-vs-true-attributes is provable only
on the native replay path, and the older Tour path cannot prove no prospect was
omitted (candidate set not stored). Annual W52/W61/W80 timing is covered by the
existing model/perception domain tests; decision-evidence replay is now also tested
for W52/W61/W80. Measured cost: 1000 prospects in one week take ~0.5 s (almost all
self-perception, ~0.4 ms per prospect; ~0.07-0.11 s to decide), so a long Run that
keeps ~1000 prospects in play every week of 50 seasons would spend tens of minutes
there. The persistent perception components are now memoised (output verified
byte-identical to the previous implementation on 90 samples): warm cost fell from
0.36 s to 0.13 s per 1000 perceptions. No full W80/1000-player Run and no simultaneous-slot run was added. Fork read of the never-pro exception shares the same pure helper but has
no fork execution test. Hosted workflows were not run on this head.

---

# Turn Pro model v2: own self-perception (Master v87) — 11 November 2026

Stacked on the FAX Saved Draw branch. Following the owner clarification, the
weekly Turn Pro AI no longer reads other players' hidden strength. A prospect
perceives its own 57 attributes imperfectly (level/group/attribute errors,
Confidence bias, Analysis/Self Control reflection, unknown Financial Level),
compares its perceived level with a fixed professional threshold and adds its own
ambition/professionalism. Each decision records what the prospect knew. v1
remains only for replaying recorded history. Owner decision B: eventual entry is
near-certain, not forced. See [docs/TURN_PRO_LIFECYCLE_V87.md](docs/TURN_PRO_LIFECYCLE_V87.md).

---

# Turn Pro v87 FAX Saved Draw candidate (Master v87) — 11 November 2026

Stacked on the Admin-default branch. Owner decision: the FAX reference path also
follows v87 — turn pro first, then apply. Under a v87 World, Saved Draw adoption
(Ranked or Unranked) requires every participant to be a professional by the
adoption week and otherwise fails closed, naming them. Proven over HTTP/SQLite
(rejected with prospects, adopted and Saved with professionals only). The legacy
copied-FAX acceptance materializer still uses the legacy 61-week lifecycle; its
move to the native population is a separate step. See
[docs/TURN_PRO_LIFECYCLE_V87.md](docs/TURN_PRO_LIFECYCLE_V87.md).

---

# Turn Pro v87 Admin default candidate (Master v87) — 11 November 2026

Stacked on the native-fork branch. New Runs created through the Admin population
controls default to the v87 Turn Pro rule (historical rule remains an explicit
choice); the HTTP API default is unchanged. The review shows how many players are
already professional at Run start. See
[docs/TURN_PRO_LIFECYCLE_V87.md](docs/TURN_PRO_LIFECYCLE_V87.md).

---

# Turn Pro native fork candidate (Master v87) — 11 November 2026

Stacked on the native-weeks branch. Public native forks of a v87 Run now run and
record Turn Pro at their Week Transitions and re-run each recorded model on
replay. Proven over HTTP/SQLite: fork birth week with decisions owned by the fork,
untouched original Branch, a following default-calibration week and restart.
See [docs/TURN_PRO_LIFECYCLE_V87.md](docs/TURN_PRO_LIFECYCLE_V87.md).

---

# Turn Pro native weeks candidate (Master v87) — 11 November 2026

Stacked on the public-event branch. Native birth/competition Week Transitions run
the v87 model and record it; Signed replay re-runs the recorded model and must
reproduce every decision. Proven over HTTP/SQLite for a native birth week, Save,
a forged-decision rejection, restart and a following native week. Native forks
still reject v87. See [docs/TURN_PRO_LIFECYCLE_V87.md](docs/TURN_PRO_LIFECYCLE_V87.md).

---

# Turn Pro public World Event candidate (Master v87) — 11 November 2026

Stacked on the home-opportunity branch. v87 Week Transitions with decisions publish
`turned_pro_player_ids` in their public event (absent otherwise, historical bytes
unchanged), verified on Saved replay and visible in Viewer `public_events` from
the target week only. See
[docs/TURN_PRO_LIFECYCLE_V87.md](docs/TURN_PRO_LIFECYCLE_V87.md).

---

# Turn Pro home opportunity candidate (Master v87) — 11 November 2026

Stacked on the v87 HTTP/SQLite acceptance branch. Editions may record an optional
`host_country_code` (absent = identical historical bytes). Under v87 a prospect
with a public, not-yet-played Edition in their country gets the model's home
opportunity at the Week Transition; announcements that become public at that same
transition are excluded (no future leak). PROVISIONAL: any such Edition counts.
See [docs/TURN_PRO_LIFECYCLE_V87.md](docs/TURN_PRO_LIFECYCLE_V87.md).

---

# Turn Pro v87 HTTP/SQLite acceptance candidate (Master v87) — 11 November 2026

Stacked on #1772. First real production-stack v87 path: opening professionals,
model-recorded Week Transitions, a prospect who turns pro then applies, plays and
is ranked, a refused non-professional application, exact replay, Saved hash and
restart retry. Fixes the application gate for Tours without a stored native
lifecycle. Known gap: pre-Tour continuation weeks do not run Turn Pro; native
competition/birth weeks and forks still reject v87. See
[docs/TURN_PRO_LIFECYCLE_V87.md](docs/TURN_PRO_LIFECYCLE_V87.md).

---

# Turn Pro opening professionals candidate (Master v87) — 11 November 2026

Stacked on #1771. A new Run selects v87 through the existing calendar population
adoption request (`lifecycle_policy.tour_entry_rule = "turn_pro.v87"`); earlier
notes saying no runtime could select v87 missed this path. The adopted InitialWorld
then records recomputable `initial_turn_pro` evidence (model, seed, opening
professional ids from a PROVISIONAL retrospective integration of the pre-alpha
model) and the bootstrap lifecycle gives those players Tour entry at opening Week
1 with a Run-keyed token, so forks keep them. Proven over HTTP/SQLite for
adoption, Save, restart and fork; the full v87 sporting path is not yet proven.
See [docs/TURN_PRO_LIFECYCLE_V87.md](docs/TURN_PRO_LIFECYCLE_V87.md).

---

# Turn Pro Week Transition candidate (Master v87) — 11 November 2026

Stacked on #1770. Under the opt-in v87 policy the native Week Transition runs the
pre-alpha player-AI model and records its decisions and model policy in the
transition; lifecycle history, the Saved lifecycle check and ranking replay rebuild
the v87 lifecycle from them. Historical-policy Runs are byte-for-byte unchanged.
Birth transitions and forks reject v87 explicitly. No runtime selects v87 yet; see
[docs/TURN_PRO_LIFECYCLE_V87.md](docs/TURN_PRO_LIFECYCLE_V87.md).

---

# Turn Pro pre-alpha AI model candidate (Master v87) — 11 November 2026

Stacked on #1768. Adds the pure, deterministic `turn_pro_model.v1`: a weekly
chance by age, strength versus Tour Players and a home opportunity, converted by
the Run's W, with a hash-derived per-player/week draw. Default calibration gives a
neutral median of about 17.8 years and 99.7 % by 22. Not yet called by Week
Transition; see [docs/TURN_PRO_LIFECYCLE_V87.md](docs/TURN_PRO_LIFECYCLE_V87.md).

---

# Turn Pro ranking roster and application gate candidate (Master v87) — 10 November 2026

Stacked on the kernel candidate (#1767). Under the opt-in v87 policy the native
Tour ranking roster comes from Turn Pro (a pro without any application is ranked
from the next snapshot) and native `submit` rejects players who have not turned
pro. Historical-policy rankings keep the application roster byte-for-byte. No
runtime selects v87 yet; see [docs/TURN_PRO_LIFECYCLE_V87.md](docs/TURN_PRO_LIFECYCLE_V87.md).

---

# Turn Pro lifecycle kernel candidate (Master v87) — 10 November 2026

Base `buuk` `04c9879c49921865e35240cbcf411426d84ef68d`; the v87 decision itself is
in Draft PR #1765. This candidate adds the pure domain kernel only: an opt-in
`tour_entry_rule="turn_pro.v87"` lifecycle policy (historical bytes unchanged),
the `PlayerTurnProDecision` contract, native lifecycle advance driven by Turn Pro
instead of applications, and the pre-entry gate. No runtime selects v87 yet, so
behavior of every Run is unchanged. Persistence, player AI, ranking roster and
application/WC wiring are listed in
[docs/TURN_PRO_LIFECYCLE_V87.md](docs/TURN_PRO_LIFECYCLE_V87.md).

---

# Scheduled ATP horizon-continuation repair candidate — 11 November 2026

An explicit compatible Run horizon extension can now be consumed between Q and
Main, including a partially accepted frozen slot, without rewriting the original
schedule, Draw, seeds or already played records. Accepted rounds retain their
actual Saved clocks; rebasing, future horizons, mixed clocks within a frozen
round and shrinking horizons between rounds are rejected. Completed results use
the actual final match clock and remain unchanged on a later extension.

Targeted proofs exercise 43 genuine Q/Main matches with extension between phases,
unchanged sporting outcomes/phase points, and a real HTTP/SQLite source Save,
explicit Run extension and cold restart preserving the original source envelope.
The played component proof and source-persistence proof are separate: this does
not claim a public cross-week native Tour/Entry/Week Transition acceptance pass.
The repair is stacked on the unchanged, reviewed #1763 head; owner alone merges.

---

# Run-calendar scheduled knockout results and points candidate — 11 November 2026

Completed scheduled matches now derive clock-free knockout facts and the same
shared Q/Main/BYE/W/O point semantics as the unchanged legacy award wrapper.
A separate versioned result projection retains the actual Run week/clock;
calendar ranking inputs contain one combined result per player with distinct Q
and Main components, next-week publication eligibility and W-week validity.

Actual-match tests compare all 44 players' awards to independent elimination
values, reject future ranking input/duplicates/incomplete tournaments and verify
52-week expiry. Explicit W80/season55 and terminal-W52 scenarios preserve modern
clock semantics. A compatible horizon extension permits next-week publication
without rewriting the frozen completed result; rebasing is rejected. Legacy
result/award JSON bytes and fingerprints match the committed baseline.
These are derived results and ranking candidates, not a native publication or
Week Transition/Save integration pass. Terminal closing and native lifecycle
ownership remain separate. No legacy calendar/schema guard was loosened.

---

# Saved ATP scheduled-source loader candidate — 11 November 2026

The scheduled knockout plan can now be prepared from a physical hash-verified
Saved ATP Package and the canonical Draw Input/Draw in that same revision.
The loader never falls back to live Draw tables. A read-only Admin feeder preview
reports exact source/plan fingerprints and initial Q dependencies, with sporting
execution still false. Uncommitted and revised Draws are rejected.

Reload requires the selected Run/Branch, the consuming owner's reviewed plan
fingerprint and the original reachable Saved envelope. The proposed schedule is
not itself part of the source Package; its binding must be retained by that owner.
Real HTTP/SQLite tests use ordinary simulation Save, later Saved history, live
data corruption and cold application restart. They prove source preparation and
recovery, not native Turn Pro/Entry/Week Transition/points or a played Run.

---

# Scheduled knockout MatchEngine consumer candidate — 11 November 2026

The source-neutral feeder rules are shared by the unchanged FAX wrapper and a
new versioned scheduled ATP adapter. The adapter freezes the copied sporting
profile payload, committed Draw Input/Draw and Run round schedule. It validates
source capacities/seeds, actual accepted match provenance, schedule positions
and Q-before-Main dependencies without storing a second result ledger.

A component proof plays the 32/16 Rotterdam geometry with 44 explicit test
players through real MatchEngine: 12 Qualification matches on the proposed first
week and 31 Main matches on the second. Actual Q winners feed Main. Frozen
plan/match DTOs reopen between phases; input-order and source/schedule corruption
checks remain distinct. This is not a public native Run Save/Week Transition or
Official ranking acceptance pass. Those consumers and actual source Q dates
still need integration. No ATP sporting readiness or merge readiness is implied.

---

# Run-owned cross-week knockout scheduling candidate — 11 November 2026

A separate versioned round schedule stores exact Run week/slot positions for
Qualification and Main. It validates complete bracket-round coverage, strict
Q-before-Main chronology, common calendar and one season; it supports W52/W61/W80
and calendar-year rollover inside an offset season without clipping horizons.
Canonical match planning retains original node IDs and excludes BYEs. The
existing native same-week planner now uses this shared validation through an
ephemeral adapter; old stored schedules and planning output remain unchanged.

An Admin API read validates an explicitly proposed schedule against the exact
Saved ATP profile/head and Main source weeks. It never commits a sporting
Edition or verifies unknown real Qualification dates. Actual cross-week native
execution/Entry/Ranked publication remain follow-up integration, not implied by
this read-only planning result. See the sporting profile document.

---

# ATP knockout source and shared geometry candidate — 11 November 2026

Setup v3 / sporting Category v2 adds the sourced Rotterdam 2025 Main32/Q16
configuration, four Q sections, four WC, eight seeds and complete phase points.
The Main and Qualification PDFs are identified by URL and SHA-256. Shared pure
bracket construction now supplies both this ATP shape and the existing FAX
wrapper; all 80 original FAX geometry dumps/fingerprints remain unchanged.
The Saved catalog exposes 43 actual match nodes and explicit execution blockers.
Rotterdam is structural data, not a playable Edition. Setup v4 / sporting source
v3 / knockout profile v2 adds organiser-sourced Qualification dates (1–2 February
2025, W5) before Main (3–9 February, W6). Saved preview validates both phase weeks;
old profile v1 bytes and date knowledge remain unchanged after cold reopen.
Native Ranked knockout execution remains tied to W61/FAX and requires a separate
versioned cross-week consumer; verified dates alone do not grant execution.
The UI leaves import disabled and explains this boundary. Group profiles retain
their existing native path. See the sporting profile contract below.

---

# ATP Saved sporting profiles candidate — 11 November 2026

The ATP Calendar Setup v2 adds an independent, versioned squash sporting-profile
Category alongside unchanged historical source documents. A generic Saved-profile
catalog and preview path consumes ATP Finals and Next Gen 2025 through ordinary
native group/knockout Tour operations. The Admin can load the available profiles
and review one before explicit confirmation and manual Save. ATP Finals stores
200 per played group win plus 900/400/0 knockout components; no duplicate points.
The source calendar remains reference data for other occurrences. Race/age entry,
ATP seed placement and ordinary Main/Qualification formats remain follow-up work.
See [sporting profile contract and evidence](docs/ATP_SQUASH_SPORTING_PROFILES_V1.md).

---

# ATP Earth W52 Saved Package and Next Gen pilot — 11 November 2026

On base `buuk` `04c9879c4`, the historical ATP Calendar source (#1741) is
available. This candidate brings the W52 mapping and Saved snapshot source
validation from #1742 and #1748 into a single PR against that base.

The Admin Packages page can preview a chosen ATP year from the exact Saved
Run Package and verified W52 clock. A partial-year Run horizon displays
conflicting occurrences separately with their original dates and weeks.
The full 1990–2026 source maps 2,407 occurrences. The three source intervals
touching three weeks remain flagged for sporting review.

The same candidate integrates the owner-merged #1762 pilot. Calendar Tour can
review and explicitly confirm the Saved 2025 Next Gen source as an eight-player
group/knockout Edition. It uses the W52 source date, ordinary Entry/draw, actual
squash MatchEngine, manual Saves and zero ranking points. The UI checks the
exact target and announcement weeks against the chosen Run horizon. Admin
selects the entrants. Automated age/Race eligibility and other ATP sporting
formats remain follow-up work. See [mapping and validation](docs/ATP_EARTH_WEEK_MAPPING_V1.md).

---

# Saved Draw native readiness panel candidate — 10 November 2026

Base `buuk` `04c9879c49921865e35240cbcf411426d84ef68d`. Admin now surfaces the two
existing read-only Saved Draw inspections (`saved-native-preflight`,
`saved-entry-evidence`) on the Saved Edition Draw tab, for the Branch's current
Saved head only. It shows point-table gaps, the native execution status and which
Main / Qualification / wild-card participants have a recorded first Tour Entry.
It adds no backend behavior, command, sporting rule or calibration, and it neither
creates first Entry nor adopts a Draw. Wiring valid first Entry into the native
lifecycle, the adoption wizard and original-source chronology stay the next
boundaries.

The panel is requested only when the page's revision equals the Branch's current
Saved head; historical revisions never call these current-head endpoints. Any
response whose Saved revision, Edition, Draw source fingerprint or trigger owner
differs from the request is discarded, not displayed. Unsupported Draws (HTTP
404/409) appear as information. The panel has no action and does not decide
whether a missing Entry is acceptable. Evidence is mocked-API component/contract
tests plus the existing frontend suite and production build; no browser or
HTTP/SQLite pass is claimed.

---

# Saved FAX Entry evidence candidate — 8 November 2026

Base `buuk` `d239a972fe2f9834b36c608193d196a67d4abb1a` includes the reviewed
Ranked award projection. Separate PR #1758 passed the disposable Ranked Gold
HTTP/SQLite weekly publication and restart gate; it requires prior native Entry.
This candidate adds a [Saved Draw Entry evidence read](docs/FAX_REFERENCE_KNOCKOUT_GEOMETRY_V1.md#saved-first-tour-entry-evidence)
on the merged base. It verifies recorded first applications and definitive wild
cards against their Saved sources. It does not create native first Entry or
certify original FAX source chronology. Wiring valid first Entry into the
native lifecycle remains the next boundary.

---

# Historical native canonical Q/Main candidate — 6 November 2026

Merged base `buuk` **`c7bb53eb893dceb2cb603bc0d312b71070489a0e`** is the owner
merge of #1746 and preserves its exact reviewed tree. This candidate consumes its
pure domain feeder through Edition v4, frozen canonical match / GlobalSlot v4 and
the existing v13 checkpoint. Actual results remain accepted continuation records;
the terminal tournament result is derived, never another persisted result ledger.

`adopt-saved-draw` explicitly selects the exact current Saved Calendar/Draw/Input
and a complete strictly increasing Q/Main round-slot schedule. The source supplies
`event_level_overrides.native_announcement_week` on its original Run clock.
Adoption must precede that week; normal Week Transition publishes the public event
and a whole week passes before play. No date, eligibility, points or rest calibration
is invented. Physical reachable Saved-envelope/hash/Draw validation is separate
from mathematical replay and still runs with warmed prefix reads.

Scope: source-authored **Unranked single-week FAX reference geometry**, preserving
Main24/Q16 and Main32/Q24 capacities and actual BYEs. Original Ranked 80-Edition
source is NOT enabled through zero-point awards. Inherited native fork remapping,
revised Draws/replacements, multi-week execution and complete Ranked awards remain
unsupported. Old schemas, seeds, legacy index bounds and pure domain boundaries stay.

Dedicated real HTTP/SQLite cases exercise actual Q/Main, public announcement,
partial Next Match Save/reopen, exact retry, terminal confirmation and transition.
Their disposable sources explicitly author Unranked status/week/announcement;
they do not prove original full season or 50-season acceptance. Small contract and
old-golden regressions remain separate. Candidate final-head local/hosted results
must be recorded in PR; Draft skips are not passing acceptance.

Next finish original Entry/publication/complete Ranked awards/chronology and
owner-level Admin adoption, then multiple Editions/full season and existing
50-season/recovery/performance gates. No Master, source Package, canon or calibration
change. ATP package PRs are separate. Owner alone merges.

---

# Historical Saved-bound feeder kernel — owner-merged as #1746

Current merged base: `buuk` **`7620b89ab53b93780216955a72bd5e4c91f6d691`**
(owner merge of #1745). Its tree exactly preserves the reviewed player Draw.
The next candidate derives immutable initial feeder plans from an explicit,
hash-verified Branch-owned Saved head, its copied Calendar and saved Draw/Input.
Unsaved live Draws cannot supply that plan; later live edits do not reinterpret it.
Reload authenticates the original reachable source after further explicit Saves,
rejecting unreachable or altered serialized plans instead of rebinding to new data.

The canonical node planner shares the existing legacy BYE/Q resolver. It emits
35 actual Gold match nodes or 51 Platinum nodes; eight BYE nodes are advances,
not MatchResults. A stateless projection consumes existing continuation records,
requires the complete Qualification before Main, resolves exact Q1–Q4 opponents,
and rejects foreign, duplicate, premature, stale-source and wrongly seeded records.
It does not own a second ledger. New seed v1 uses the saved draw seed, Edition,
season and canonical node; old native seeds and old topology bytes are unchanged.

Kernel tests play actual MatchEngine Gold35/Platinum51, preserve frozen wave
inputs, apply existing player effects, and check opposite acceptance order.
Real SQLite tests explicitly Save/reopen, reject stale heads/corruption and prove
isolation from changed live data. This is component/kernel + Saved-source evidence,
**not a native Next Slot/Next Match, season or ranking release pass**. Readiness is
explicitly `feeder_dependencies_only`, with native execution still false.

Next: bind this plan to versioned native Edition/global-slot/result models and
existing v13 result ownership, then prove real public Save/resume/restart and
existing Entry/award/schedule prerequisites. Do not widen legacy match indexes or
remove the Main4/8 guard. No sporting canon, calibration, Package or Master change.
ATP package Drafts #1731 → #1741 → #1742 remain separate and untouched. Final-head
hosted gates and owner merge remain required. See the existing evidence checkpoint.

---

# Historical source-sized player Draw — merged as #1745

Current merged base: `buuk` **`1800697b978a33f6895d2e6a3fa3e77bfb066954`**
(owner merge of #1744). The complete frontend regression repair is merged; the
candidate wording in its historical entry below is no longer current.

This isolated candidate connects original Gold Main24/Q16 and Platinum Main32/Q24
geometry to real-player canonical Entry Field, reviewed WC, Draw Input and Draw.
Draw Input v12 / `padded_qualification_sections.v3` separates Q admission count
from physical bracket positions: Platinum admits 24, distributes six per Q1–Q4,
and places two BYEs per eight-position section. Gold keeps historical v3 input /
v2 Draw bytes. Main remains 32 physical positions, eight Main BYEs only for Gold,
and four unresolved Q placeholders. No Q winner or match result is invented.

The source-bound reader loads the copied Run Calendar and authenticated stored
input/Draw. Focused evidence covers all 80 original source geometries with named
test players, real HTTP/SQLite commit/retry, Saved component restore, physical
connection reopen and adversarial source/replay rejection. Test eligibility and
WC nominations are explicit fixtures, not a new automatic selection policy.
Candidate tests and exact-head hosted gates are recorded in its PR.

The complete Gold/Platinum sporting path remains blocked on versioned global-slot
match/result execution, source awards and existing Entry prerequisites. This is
not a played 80-Edition season, owner-level Save/browser acceptance or a 50-season
release pass. ATP package Drafts #1731 → #1741 → #1742 are untouched. The sole
active evidence map remains the existing integration checkpoint below.

---

# Historical frontend regression repair — merged as #1744

Base: merged `buuk` **`7e92ad5ee714092263335420e0f6e8ed0b79a045`**
(owner merge of the integrated audit #1743). The isolated frontend test repair
now passes **all 3,423 tests / 364 files**, with zero failures, plus the production
TypeScript/Vite build. The prior 3,326-pass/88-failure result below is historical.
These are mocked frontend/component contracts, not new sporting browser or
HTTP/SQLite execution evidence. No production code, API, fixture source data,
sporting rule, timeout, CI selector or test-policy gate is changed.

Legacy read mocks, stale labels and removed preview expectations now follow the
current canonical Saved readers. Ranking ordinals and Race fixture totals are
internally consistent; exact-player comparisons use actual detail mocks rather
than the first-50 discovery sample. Nine additional negative/boundary cases cover
current source contracts. The historical Lab selector test awaits loaded options
and resets one-shot mocks between cases instead of racing asynchronous inventory.

The candidate still requires final-head hosted checks and owner merge. The next
functional dependency remains the real source-bound FAX Main/Qualification path;
the 80-Edition, full season, 50-season, recovery and full-backend release gates
are not satisfied by this frontend result. Retain the rest of the Master scope.
See the existing integration checkpoint for the preserved audit and correction.

---

# Historical integrated audit — 6 November 2026

Audited merged `buuk`: **`b666c109b9dc596a6d226025500ceb462a4fff8b`**.
All 38 reviewed non-package PRs (#1700–#1740, excluding already merged #1701/#1704)
are present with their exact reviewed heads. All 144 feature-changed files match
their reviewed feature contents; no merge loss was found. Only ATP package
Drafts #1731 → #1741 → #1742 remained open at audit time and were not modified.

The single current requirement/evidence map remains
[the existing integration checkpoint](docs/PRE_ALPHA_INTEGRATION_2026_10_30.md).
Its 6 November section supersedes older implementation status and task ordering,
not the complete Master v86 or newer explicit owner decisions. This audit is
not an internal release declaration.

- Production frontend build passed. The **complete** local frontend suite has
  **3,326 passes / 88 failures in 13 files**. The pre-batch `a07c5154` suite has
  3,213 passes / 92 failures; all 88 current failure identities already failed
  there. No newly failing test was found in that comparison. Failures still
  require triage and repair; unchanged failures are not release permission.
- **193 selected backend/tool/domain/HTTP tests passed**, including atomic Save
  rollback, archive boundaries, backup checks, the three production Labs and
  paired Match Lab. The separate real one-Edition operator module passed its
  **two tests**, including MatchEngine, points, manual Save, physical SQLite
  reopen and exact command retries. This was not the complete backend suite.
- Current-base Python/Actions/TypeScript CodeQL passed. Sonar remains advisory
  and red; this audit is not a repository-wide security clearance.
- The exact current FAX source audit still reports **80/80 Editions blocked**
  for native execution. The separate topology builds all 80 source-bound graphs;
  its **3,440 potential matches are a plan, not played matches**. Current native
  knockout execution still accepts only full ranked Main 4/8; qualification,
  Gold24/Platinum32, source points and early announcements need real integration.
- Existing read-only Admin/Viewer helpers, isolated Labs and Windows preview
  are useful bounded features, not proof of full-season or 50-season completion.

**Next technical work:** triage the 13 failing frontend modules without weakening
their actual safety contracts, refresh stale test fixtures/guards where proven,
then prioritize the exact source-bound FAX Main/Qualification execution path.
Locate genuinely unresolved automatic Entry policy/content decisions before
their consumer; do not invent awards, silently reduce fields or waive Save/replay.
No further Viewer expansion or speculative realism tuning outranks this path.
Retain the rest of the decided pre-alpha scope and full release/recovery gates.

---

# Historical candidate — portable Windows preview, 31 October 2026

Verified base `buuk`: `7a08ff441dd185189638c05dfc3bd33401407b7d`.
This isolated delivery slice adds a bundled Windows runtime, compiled UI and
one-file console launcher; it does not change sporting logic or declare a release.
Each source commit owns separate local data and never migrates an older world
automatically. See [download, shutdown, backup and evidence boundaries](docs/WINDOWS_PREVIEW.md).
The dedicated Windows workflow must prove the actual frozen executable, real
browser/SQLite empty-Run first Save and restart before publishing its ZIP.
The full pre-alpha integration/release gates remain separate. Older checkpoints
below retain their original dates and do not describe the present merge queue.

---

# Edition Entry timing preparation candidate — 30 October 2026

Verified `buuk`: `57d07a1c52c48bd5460519f2e837829ce7770de2`; owner merges
#1673 (requirement map) and #1674 (summary test repair) are present. Earlier
candidate labels below are historical evidence, not the active merge queue.

This candidate adds backend/API preparation of explicit per-Edition Entry windows
inside the existing Run Calendar Package/Working Draft, plus optional adoption of
the exact already-published Tournament Ranking Snapshot in the same transaction.
Ordinary Save captures both owners; source Packages and sporting execution remain
unchanged. See [contract and validation](docs/EDITION_ENTRY_TIMING.md).

Master §15.1's data through Main Closing Week−1 maps via §18 to the publication
labelled Main Closing Week (13–14 Main selects data through 13, publication 14).
No latest-ranking fallback, pre-start history or play-to-opening lead is invented.
Missing sources and unsupported clocks remain explicit; a future plan can Save
without claiming a ready binding or automatic eligibility. Existing immutable
binding and native/legacy ownership protections remain.

The API is not yet an Admin form or an automatic eligibility validator. The next
consumer should expose this exact review/Save boundary, then resolve the concrete
remaining validation/content prerequisites before fields/draws and actual matches.
The full requirement map and progressive integration ladder remain in
`docs/PRE_ALPHA_INTEGRATION_2026_10_30.md`; no release or Master change is claimed.

---

# Season-summary test fixture repair candidate — 30 October 2026

Verified base `buuk`: `abe8fa307a08ccb25e2209c1abc8610d7b41bff9`, owner merge
of #1673. The post-merge requirement map below remains the active scope/evidence
index; its four summary failures describe the audited baseline, not a new runtime
defect. This candidate replaces only the obsolete unit-test Edition namespace
with the real `CalendarTourEdition` model and checks each forged input's specific
rejection reason. Production schema/group guards and sporting behavior are intact.

The six summary contracts now pass. Together with nine existing calendar-domain
contracts and three actual HTTP/SQLite terminal-summary scenarios, all 18 focused
tests pass locally. These are scoped results, not a full regression or release.
Final-head hosted checks must pass before merge; this candidate is not yet merged.

Next feature task remains the Saved Edition Entry timing/preflight and historical
ranking-source binding described in the existing checkpoint. No new product
decision, Master edit, Viewer expansion or automatic application approval is made.

---

# Current merged baseline — 30 October 2026

Audited `buuk`: `d45b7d3b3aa7e585e3c777cb166c6c5f2bb2f81d` (Master v86).
All PRs #1661–#1672 are merged; none was open at this audit. Reconstructing all
reviewed heads gives the identical tree `307c44b66b503c1b2c27a7ed83c0eab2f7c995a2`.
This is an implementation checkpoint, not an official pre-alpha release.

The active requirement/evidence/blocker map is
[the post-merge checkpoint](docs/PRE_ALPHA_INTEGRATION_2026_10_30.md). It accounts
for PAQ-001–157 and the later §31.25–40 scope without changing product statuses.
RESOLVED, implemented, integration-tested and release-proven remain separate.

**Immediate next:** repair the stale Edition mock behind four season-summary unit
failures found by this audit; retain the production schema guard and negative
assertions. **Following feature slice:** persisted per-Edition Entry timing/preflight and historical
ranking-source binding. Main 2 + Q 1 weeks and Main Closing Week − 1 ranking already
have product answers. The code's blanket unresolved-policy label is not a reason
to re-ask those rules or to approve all applications. Exact implementation boundary,
acceptance checks, real remaining unknowns and alternative release gaps are in
the checkpoint. No additional Viewer expansion is selected.

Saved/source/concurrency/retry and native W52/W61/W80 evidence is scoped; the full
1,000-player/80-played-Edition season, 50 seasons, full regression and side-capability
closure remain outstanding. Sonar advisories from #1669/#1671 are not declared fixed.

---

# Historical state notes

Earlier entries below retain their original date and candidate language. For the
current merged inventory and next task use the active checkpoint above.

# Native Save performance candidate — 29 October 2026

Verified base `buuk`: `edd237b7a2d5e1d69cf96aafce13799bf428253b`.
#1660 and #1659 are merged; the older candidate/unmerged headings below are
historical evidence, not the current merge inventory. This backend slice is
PR #1662 on `feat/native-save-performance-20261029`. Independent Viewer PR
#1661 and all `web/` files remain outside its scope.

An actual HTTP/SQLite profile confirmed duplicate retained checkpoint copies
in the successful Save handoffs. The bounded full-DTO adapter now references
one retained complete-component value; the native reader can consume an
already retained DTO while cold misses retain the original component route.
All physical/source/dependency/math/post-write gates, whole-DTO reuse, legacy
schemas, caller isolation, manual Save, sporting outcomes and audit remain.
The unchanged 64 MiB budget measures input bytes, not process heap; actual
reachable heap and RSS are measured separately. See `docs/NATIVE_SAVE_PERFORMANCE.md`
for paired results, targeted regressions and the distinct adversarial review.
Relevant final-head hosted gates, including unchanged W80/1,000 Chromium,
are required before owner handoff; their exact inventory belongs to PR #1662.
No merge, auto-merge or full pre-alpha/50-season certification is performed.

---

# Native Save decode continuity candidate — 29 October 2026

Verified `buuk`: `fbe8e00c346b1de6de6d3144509a92592dec38d0`, owner merge of #1657.
That exact feature head passed all 58 applicable hosted checks, including the
complete W80 calendar/Season Transition and the W80/1,000 Chromium scenario.
The two unrelated scoped-out jobs were not counted as executed tests.

The next bounded candidate connects successful manual Save to the component
value cache used by the next native command. A direct real HTTP/SQLite test
reproduced redundant structural decoding immediately after Save. The existing
whole-payload handoff remains, and the additional component uses the same shared
byte budget and isolated copies only after successful commit. All source/math,
physical and late-write gates stay required. See `docs/NATIVE_SAVE_DECODE_CONTINUITY.md`.
This candidate is not merged or release-certified. Parallel PRs #1652–#1656 and
#1659 own their independent frontend/read-model files and are untouched.

---

## Current audited checkpoint — 30 October 2026

The active state, full pre-alpha evidence map and next dependency are maintained
in [the current integration checkpoint](docs/PRE_ALPHA_INTEGRATION_2026_10_30.md).
Earlier dated candidate notes in this file are historical evidence, not the
current open-PR inventory. Product authority remains the complete Master.

---

# Native pure-group withdrawal candidate — 29 October 2026

Owner merges #1647 and #1651 are present on `buuk` at
`e4d0dd3b7da9f8767d19ece2cf194919a9bf864d`. Their final feature heads
completed their relevant functional gates, including the W80/1,000 browser
(946.88s) and all-week W52/W61/W80 Season Transition cases. Older candidate
sections below are historical evidence, not the current open-PR inventory.

The next bounded candidate adds explicit post-start pure-group withdrawal,
separate non-played W/O in the global ledger, original/target/nested-fork source
integrity and normal Full Simulation/manual Save controls. It deliberately
rejects hybrid advancement, nonzero Official W/O phase rewards and a second
withdrawal in one group until their specific policies exist. It fabricates no
played match, rally, physical effect or H2H. Five real HTTP/SQLite cases and a
real CS/EN Chromium flow passed locally; hosted final-head gates remain required.
See `docs/NATIVE_GROUP_WITHDRAWALS.md`. The parallel Saved player career/replay
and Country match record frontend slices are untouched. No release is certified.

---

# Native groups/global-slot integration candidate — 27 October 2026

Refreshed `buuk`: `af0e906ce374c3406fb43c29fe65b007546b9303`; #1643,
#1645 and #1644 are merged, #1646 stays separate. Native group/hybrid Editions
now have explicit v3 configuration, shared topology/schedule/standings/crossing
and phase-point composition over actual global slots. Old schemas retain their
original shapes and sources. The real two-group 15-match HTTP/SQLite Save/restart
and Official-point flow and the rehashed-slot/rollback/retry checks passed.
Four-group/pure-group, fork/worker and actual Chromium acceptance are still in
progress; this is not a merge-ready handoff or full pre-alpha certification.
See `docs/NATIVE_GROUPS_GLOBAL_SLOTS.md` for exact evidence and outstanding gates.
Only the owner merges; no auto-merge.

---

# Confirmed Save value continuity — 26 October 2026 candidate

Preceding 37f627a4 passed fourteen hosted workflows; the complete global
all-week matrix was still running. Whole W80/1,000 Chromium now completed and
Saved BOTH seven-match tournaments and both result confirmations. Its unchanged
18-minute deadline expired during the last Week Transition; it is still WAIT.
The separate two-round hybrid browser passed a same-head retry after one
ECONNRESET (its server log contained no exception). No failed result is hidden.

This follow-up avoids another full read after confirmed Save in a deliberately
narrow native v13/v5 case. The normal independently verified context exports
only its private captured payload values after successful replay. The view may
carry the fingerprint of that COMPLETE payload. After every original Save
before/staged/installed/commit gate succeeds, its receipt may carry the actual
Saved payload fingerprint, exact source/revision IDs, clean draft version and
checkpoint/Tour fingerprints. A match permits a one-use UI handoff to the new
HEAD. No client token authorizes a server action, and no source proof is copied.

Forks, prospect sources, any live prospective/disciplinary/correction inputs,
completed seasons, closures and differing Run/Tour calendars do NOT use this
optimization. Missing or changed full values use the original GET. The UI still
validates receipt/Run/Branch/old/new HEAD/draft/owner fingerprints and its scope
and epoch fences. A handoff cannot be applied to another Run/Branch/HEAD.
The stored payload, its original hash, all math/source gates and manual consent
remain unchanged. There is no new cache, copier, schema/GC policy or timeout.

Local final checks: five real HTTP/SQLite cases pass (including before/after
write gates, rollback/retry, complete Saved DTO equality with independent GET,
changed Run metadata despite unchanged Tour/CP fingerprints, and conservative
external-source/calendar/fork/season/closure eligibility). Forty-six frontend
component/value tests and TypeScript/Vite build pass. The genuine 1,000-player
failed CI database completes actual manual Saves, result confirmation and W6
with 560 points; all THREE retained Saved DTOs equal full independent GETs.
Those Saved GETs cost 11.11/10.56/12.08 seconds in the diagnostic; they are omitted
only by the eligible UI. The diagnostic includes extra verification GETs and
concurrent local build load; it is not a whole-browser performance pass.

The browser observer records whether a Save used full-payload continuity or an
independent GET, verifies the actual receipt and Saved UI, and retains the real
cold SQLite restart, exact final replays, player details, Viewer/public points,
all original sporting assertions, 1,000 players and unchanged deadlines.
Final-head hosted acceptance must execute successfully before owner merge.

---

# Post-command inspection response — 26 October 2026 candidate

The preceding 0f0f6eca head completed eight workflows successfully, including
all Global Slots weeks/Season Transition and all Full Simulation jobs. Its sole
remaining failure was the whole W80/1,000 Tour Chromium at the unchanged
18-minute deadline. This still blocks owner merge handoff. #1641 has been
merged by the owner into buuk (3ee384253); its files remain separate.

The opt-in POST /calendar-tour/execute?include_inspection=true returns the
original command result plus the current Tour inspection. The ordinary command
receipt, persisted history and default API response are unchanged. Native
commands project the SAME independently authenticated POST-WRITE context that
already ran before commit; they do not authorize reads from the calculated
successor or pre-command state. Projection/commit failure cannot return success.
Exact retries still authenticate the current physical context and preserve the
original result. Forks retain their existing execute plus independent read path.

The Admin panel validates envelope/version, command identity/action, Run/Branch
and the unchanged Saved source, with its existing scope/input/epoch fences. It
uses the supplied inspection without another full GET; old result-only servers
retain the ordinary GET fallback. Explicit consent and manual Save remain.
Browser observers use the post-write response; independent Saved GET, physical
restart, 1,000-player population, real matches/points and every original sporting
assertion/deadline remain. No GC, copy compiler, cache-budget or schema experiment
is included. No source validation, hash, seed, replay or transaction fence changes.

Local evidence: two actual HTTP/SQLite cases verify full equality with an
independent GET, both before/after gates, rehashed coupled-write rejection,
projection failure rollback and default/opt-in exact retries. All 36 Tour panel
component tests and TypeScript/Vite build pass. The new UI cases verify no
redundant read/implicit Save and reject foreign Run, changed HEAD, mismatched
command and unknown envelope. The genuine failed 1,000-player SQLite flow is
being measured separately; it is not a whole-browser pass. Final-head hosted
Chromium, fork/restart and all relevant acceptance matrices must actually pass
before owner merge. Complete pre-alpha/50-season release acceptance is separate.

---

# Save origin values and Working Draft projection — 26 October 2026 candidate

Preceding `bc5d60a5` completed eight of nine hosted workflows successfully,
including every actual W52/W61/W80 week and Season Transition, cold restart,
all Full Simulation jobs, and both global CS/EN Chromium scenarios. The sole
remaining failure was the whole W80/1,000 Tour browser's unchanged 18-minute
limit during the second tournament. It still blocks owner merge handoff.

This follow-up gives each Save its own borrowed map of bounded immutable origin
JSON values. Capture and the staged physical origin gate share that map, while
every lookup still hashes complete current source bytes and binds Run/Branch/
revision. Only JSON values are retained after successful commit; no source or
math proofs are borrowed or published. Failure leaves the shared value map
unchanged. The original before/staged/installed dependency fences remain.

The Save gate can project its already decoded actual new row only after its
FULL original canonical JSON equals every current SQLite byte. A mutated private
payload or noncanonical stored encoding takes the original raw parser. Ordinary
cold readers keep their existing path. Physical ownership, reachable sources,
independent mathematical replay and terminal/closure checks all remain.

A Working Draft DTO can use the existing small exact-byte/hash-verified Run
projection after authenticating the entire actual global lineage. It needs only
the Saved Viewer selection. Internal callers requesting revision state still get
the full payload. Eviction, changed actual bytes or an unavailable projection
falls back to full materialization; ancestor corruption/closure still fails.

Local evidence: seven actual HTTP/SQLite cases passed the origin-pool change,
including partial matches, Save/restart/points, concurrent retry, rehashed-source
and Health rejection/recovery. Final focused staging/raw-value/draft checks pass
six cases, including private-payload mutation, whitespace reencoding, cache
eviction and rehashed ancestor closure rejection. Eleven general Working Draft
API/application regressions and 28 focused value/calendar contracts also pass.
On the genuine failed 1,000-player CI database, three late Saves under profiling
improved from 157.72 s combined to 126.68 s, reaching W6 and 560 points. This
measures the origin-pool change before the additional draft projection; it is
not whole-browser acceptance. A separate whole HTTP protocol diagnostic is
being measured; final-head hosted Chromium and complete relevant matrices must
actually pass before owner merge. Only the owner merges; #1641 stays separate.

---

# Global-slot whole-browser follow-up — 26 October 2026 candidate

On `add6b6ee`, eight hosted workflows passed, including every W52/W61/W80
actual week, real Season Transition, correct points/summary and final cold restart.
All native Full Simulation jobs, global API/fork/worker and both global Chromium
scenarios also passed. W80/1,000 Tour Chromium still exceeded its unchanged
18-minute whole-flow limit during the second tournament. Its restart improved
to about 88 seconds. This remaining failure blocks the owner merge handoff.

The follow-up keeps immutable origin JSON projections in a repository-local,
32 MiB/128-entry decode-value cache. Each lookup still hashes complete current
source bytes and binds Run/Branch/revision; independent physical, ownership,
reachability and math gates remain. Borrowed operation dictionaries are separate,
and no source/math proofs enter this cache. A newly decoded actual Saved head
seeds the projection only after its complete physical gate.

Calendar reads reuse at most 128 small immutable Run projections (32 KiB each)
only when every actual Saved byte and metadata field matches a completed content
hash check. Changed payload, summary, declared hash, identity or rehashed clock
takes the original full gate. The sporting context validates the complete
Saved lineage before this reuse. Every current Run/calendar consistency check
remains. Native Working Health returns a fresh strictly parsed head only after
the complete actual history already passed replay or its exact full-payload proof.

Defensive DTO copies retain new models, dictionaries and field sets. Only actual
runtime-proven immutable (str,int) attribute tuples can reuse their copy-safety
check; the tuple itself binds object identity and lives only with the bounded
owning cache entry. Mutable replacements, subclasses and incomplete models keep
ordinary deepcopy. No persisted schema/hash/seed/result, population, sporting
rule, timeout or acceptance assertion changes.

Local evidence: four real HTTP cases pass Save/ancestor rollback, rehashed-source
and retry guards, partial results/restart/points, and older/latest rehashed Health
rejection with recovery. 43 focused contracts and 12 calendar/concurrency checks
pass. Actual large DTO copy measured about 0.59–0.65 s with retained immutable
attribute hints versus 0.73–0.81 s without; a general copier had no reliable
benefit and is excluded. A complete actual 1,000-player two-tournament HTTP probe
is running; it is not Chromium acceptance. Require all relevant final-head hosted
workflows to execute successfully before the owner merge recommendation.
Only the owner merges; #1641 remains separate.

---

# Global-slot cold lineage repair — 26 October 2026 candidate

Published `a473cd2a` finished seven hosted workflows successfully: Fast CI,
Sporting Context, Saved Branch Review, Shell Browser, Calendar Boundary, Tour API
and all native Full Simulation jobs. Global W52 completed every actual week,
Season Transition, correct points/summary and cold restart. W61/W80 completed the
same sporting assertions but failed only their final 120-second cold restart.
The W80/1,000 Tour Chromium flow passed its restart, then exceeded the unchanged
18-minute whole-flow deadline after the second draw. These are real remaining
failures; neither PR readiness nor partial timings satisfy the owner merge gate.

The follow-up reuses independently replayed private Tour values only after
binding the complete actual component and fresh model fingerprint. Physical
owner/reachability/source checks remain mandatory for every Saved revision.
Already authenticated actual JSON can seed the bounded immutable origin
projection, and routing transfers its fresh parse only when complete raw bytes
still match. Changed input retains ordinary strict decoding.

Checkpoint replay incrementally hashes the exact original sorted canonical JSON
of private immutable prefixes; replacement, truncation, different owners and
unsupported model extensions retain exact original semantics or full fallback.
An optional separate ordered-JSON digest compares every actual checkpoint value
against a fully replayed reference. It never changes persisted hashes or grants
source/math authority by itself; full input/history binding and Tour hashes
remain required. Reordered JSON or an unusable auxiliary digest falls back to
the original canonical comparison.

Local evidence before workspace loss: 24 domain/value contracts passed, including
boolean/integer/float/signed-zero/NaN distinctions and rejection of auxiliary-only
proofs. Real HTTP tests passed exact original checkpoint hashes, private witness
mutation/foreign owner rejection, raw parse transfer, changed captured content,
ancestor rollback and concurrent retry. The genuine failed W80 CI database has
94 revisions; cold inspection improved from 198.6 to 143.7 seconds under cProfile.
The latest plain measurement was 138.4 seconds, so sufficient hosted deadline
margin remains unproven. The additional ordered-digest golden assertion and
reconstructed candidate require final-head CI. No timeout, population, sporting
assertion, schema, seed or result is relaxed. An interrupted later byte-digest
memo experiment is excluded. Continue the same #1643; only the owner merges.

---

# Global-slot whole-operation and restart repair — 25 October 2026 candidate

On `01c2776c9`, W52/W61 Tour Chromium passed and W80/1,000 passed the formerly
failing cold restart, then hit the unchanged 18-minute total limit at the second
draw. A real local HTTP sequence completed both tournaments and Saves in 1,151 s,
but also failed that total bound before its final transition. The isolated final
transition, Save and 560-point result passed separately; this is not a whole-flow
pass. The signed-restore job's initial test-server startup failure was rerun alone.

The next candidate isolates each sporting record copy while reusing only its
runtime-checked deeply immutable attribute tuples; mutable bypass values and
subclasses retain ordinary deep copying. Actual large DTO copying measured
1.30 s versus 2.26 s. Actual stored JSON snapshots get an independent JSON value
tree rather than millions of scalar deepcopy calls. Save rebinds its already
captured checkpoint to complete actual row bytes before reuse; changed bytes
force strict decoding. Inspection memoization ends with its private JSON
projection, including on failure. Original version-default validation remains
available for noncanonical nested input. Copy isolation, real completed-history
DTO equivalence and error cleanup, Entry/ancestor/changed-capture contracts pass;
the additional in-transaction captured-row tamper case and 1,000-player flow are
running. Require all final-head hosted acceptance before the owner merge gate.

The captured-row tamper case now passes: changing and rehashing the actual
checkpoint between its private preload and capture triggers strict rejection and
rollback. Complete actual raw bytes can also reuse their computed value hash in
a repository-local 32-entry decode-result cache; Run/Branch/component and every
raw byte are part of the key. Declared row hashes never authorize reuse, changed
bytes miss, and the full Saved graph/source gates still run. 29 copy/byte-binding
contracts pass. Earlier `01c2776c9` now has seven green hosted workflows, including
the successful isolated retry of the test-server startup and Full Simulation.

The `c5c4ce92` follow-up passes the six completed shorter hosted workflows and
the real global-slot Chromium/HTTP matrices. Its W80/1,000-player Tour browser
now finishes the first tournament and W5 transition, but fails the unchanged
120-second cold-restart read. Full Simulation and every-week matrices were still
running when the next repair was prepared; these are not final-head evidence.

The next repair always strictly decodes v13 root/events by their explicit schema,
avoiding repeated wrong Union alternatives without changing accepted values,
serialized bytes or fingerprints. The native working proof now captures actual
production Entry submissions, exactly as Save does; changed/rehashed Entry
authority independently rejects at Save. Actual HTTP tests compare the directed
parser with the original validator, including malformed nested parts, and prove
Entry tamper rejection, ancestor rollback and changed-payload replay fallback.
Final-head hosted green acceptance remains required.

Continuation remains in #1643. Head `c15f35b3` passed seven hosted workflows and
all native Full Simulation jobs, but W80/1,000 still exceeded its whole-browser
deadline. W52 completed every real week and Season Transition, then timed out on
final cold reopen; W61/W80 whole-calendar jobs reached their limit.

The follow-up verifies a new actual global Saved row before moving HEAD, compares
the complete before/staged/installed physical graphs, and retains bounded proofs
only after successful commit for exact unchanged own ancestry plus the new row.
Any changed dependency rejects/rolls back; every independent read rehashes the
complete actual graph. Exact complete-payload math proofs and isolated captured
DTOs avoid duplicate work; changed inputs retain full verification. Parent-edge
reads are snapshot-bound metadata, and pure value fingerprints never become
physical authority. The UI avoids StrictMode's discarded initial HTTP dispatch.

Actual Save mutation/rollback/recovery and changed-capture fallback regressions,
source/snapshot/mutation guards, 31 Tour frontend contracts and production build
passed. The real W52 failure database reopened in 81.84 s under cProfile before
the last refinements. Complete final-head hosted acceptance is the merge gate;
check the exact SHA/results in #1643. This is not full pre-alpha certification.

---

# Native global-slot acceptance repairs — 25 October 2026 candidate

Follow-up after `3d6906c6`: seven hosted workflows and all native Full Simulation
jobs passed, including the W80 worker. The W80/1,000-player Tour browser still
hit its unchanged whole-script deadline; the three all-week matrices were still
running. The next candidate adds bounded actual-byte live DTO decoding, reuses
unchanged authenticated component representations, and avoids old payload
decoding only after the full physical graph proof plus exact closure-key absence.
Changed/rehashed sources and inserted malformed closure markers still reject.
51 focused contracts and the actual birth/metadata/retry regression cases passed.
A genuine late 1,000-player third-slot Save took 52.96 seconds under cProfile,
then 17.15 seconds to inspect. The merge gate is complete successful hosted
acceptance on the final head; the PR records its exact SHA and current result.
These local measurements do not certify merge readiness or complete pre-alpha.

Continuation stays in PR #1643, branch `feat/native-global-simulation-slots-20261024`,
from base `buuk` `94737b0dab67c38c57682480f66bfae365c3225e`. The inherited
`afc10bbc` head failed three Native Tour browser checks and W80 worker cold reopen;
its three all-week global matrices were cancelled. These remain failures/missing
evidence until the new exact head executes the required acceptance green.

Viewer publication now opens one actual SQLite read snapshot, authenticates the
complete Saved lineage/physical graph, and carries its decoded Tour projection
into public read DTOs rather than replaying the same sporting history twice more.
Global origin checks reuse only the exact command prefix of the physically
verified Saved predecessor; new live/Saved command origins still validate. Native
fork structural decoding is carried into its physical verifier once. Metadata-only
history drops native payloads only after source and closure gates finish.
No persisted schema/hash/seed/result, sporting rule, population, timeout or required
acceptance assertion changes. PR #1641 frontend files remain separate.

Local evidence on the candidate: three actual production HTTP/SQLite regression
cases passed (birth/first global Edition, concurrent retry/stale/rollback/rehashed
source and player collision); the expanded source test also proves warm Viewer
reads do not run MatchEngine and reject changed/rehashed physical sources. The new
metadata-only physical-gate scenario passed. A concurrent real SQLite owner edit
cannot split one Viewer snapshot and appears in the next request. Focused contracts
and compile checks passed; final hosted native/global/Tour/Saved acceptance remains
the merge gate. These targeted proofs do not certify complete pre-alpha or the
reference 50-season release. Only the owner merges; auto-merge stays disabled.

---

# Native global Simulation Slots candidate — 24 October 2026

Verified `buuk` `94737b0dab67c38c57682480f66bfae365c3225e` includes owner-merged
#1642. Implementation continues in one PR #1643; only the owner merges.
The parallel #1641 diagnostic/history pages and their tests remain excluded.

New v2 Editions share the Branch's nearest chronological match slot. A v13
sporting ledger and v5 Tour keep original frozen slot inputs and accepted real
MatchEngine results across Next Match, Next Slot and manual Save. Completed
brackets/awards derive from that ledger. The native worker uses slot children;
Entry, results, Week/Season review, final approval and Saves remain explicit.
Original schemas and history keep their original seeds, hashes and meaning.
Native fork runtime v2 references accepted source matches and independently
continues the remaining work, without rewriting their original owners.

**WAIT — implementation/acceptance candidate.** Executed development checks
include legacy/domain contracts, frontend contracts/build, a complete original
HTTP/SQLite two-Edition Save/restart/points flow, equal batch/reversed-order
sporting checkpoints and actual worker slot children/frozen target. Subsequent
source-proof, summary and recovery corrections require the final candidate's
full acceptance again. Earlier-head results and Draft skips are not final-head
passes. Relevant W52/W61/W80 API, every-week Season Transition, final-week,
native/Saved regressions and actual CS/EN Chromium must execute successfully.
See [contract and verification ledger](docs/NATIVE_GLOBAL_SIMULATION_SLOTS.md).
This is not a claim of completed pre-alpha or release acceptance.

Independent completion review found and corrected simultaneous application batch
reuse, the invalid empty v4 intermediate during the first post-birth global
Edition, outdated whole-Edition browser controls and repeated overlapping origin
walks. Actual collision, birth/Save/reopen and concurrent/retry/rollback/rehash
scenarios passed locally; 54 backend and 125 frontend contracts/build passed.
Long-calendar performance and exact-head hosted acceptance are still required.
No timeout or required sporting/integrity assertion is relaxed.

The next performance candidate bounds per-walk decoded parts/origin projections,
reuses only exact fully replayed component values with complete source/history
binding, and isolates decoded Tour DTO reuse behind physical authentication.
62 focused contracts pass locally. The preceding published head still failed
three browser budgets and the W80 worker; these remain failures until the new
exact head executes those gates successfully. No release/merge claim is made.

---

# Native final-week Edition closing candidate — 24 October 2026

Verified base `buuk` `16c6ff737372d27b97c3237b21f7b988218df1ab` includes owner-merged
#1639 and #1640. One implementation branch `feat/native-final-week-closing-20261024`
and PR #1642; only the owner merges. No merge or auto-merge is performed.

The existing native Tour/MatchEngine and Full Simulation worker now retain a
versioned actual final-week Edition result without a fictional publication week.
Separate result confirmation/Tour Save and closure approval/final Save remain
explicit. The outgoing Closing Ranking and Saved final season summary include
real points; final completion opens no week, intake, development or Official
Ranking beyond the original horizon. Explicit strict extension and a new reviewed
command can publish that same source once in the genuinely opened next season.
Historical terminal sources/forks keep their original clock, closure and tasks.
A newly created historical native fork gets only the already available Run range
in its new Saved envelope; inherited closure is read-only history, not its own
completion authority.

Local evidence: original + independent/nested-fork short production HTTP/SQLite
matrix passed (711.29 s), real final-week Chromium and physical/browser restart
passed (174.02 s), two actual Editions/Best N = 1 passed (438.40 s), full W52
final-week/closure/extension passed on the preceding runtime (993.08 s), then its
actual cold copied fixture passed the final source verifier (37.83 s). Six
separately rehashed result/physical-source/closing forgeries were rejected with a
positive cold reopen (100.05 s). Current inherited-summary/task non-mutation read
passed (18.25 s); 132 focused contracts and 91 frontend contracts passed, build
passed. These are bounded local proofs, not final-head hosted or release claims.

The complete final-head Native Full Simulation (including new final-week six-case
matrix and W52/W61/W80), native Tour API/browser, Season, Saved Branch and shared
control gates must actually execute successfully before recommending merge.
Draft skips do not count. See [scoped contract and evidence](docs/NATIVE_FINAL_WEEK_CLOSING.md).
The whole pre-alpha, reference 50-season release gate, reserved parallel Admin/
Lab/Packages work and known broader Viewer debt remain outside this slice.

---

# Native Full Simulation history performance candidate — 23 October 2026

Verified base `buuk` `e39d962bb6797960c47c1c659d57be1dc67bba6b`
contains owner-merged #1636–#1638. Implementation is one PR, #1639; only the
owner merges. The parallel Lab/Packages CS/EN PR #1640 is outside this change.

The same genuine W52 pre-Start SQLite input completed every actual week,
tournament/points, manual Save, Season Transition and cold reopen. Comparable
execution is ~1,589.74 → 774.04 s (~2.05×); W50 Save/resume is 46.68 → 18.02 s.
Both runs retain 63 Saved revisions / 80,909,929 payload bytes, the exact original
source rows and equal UUID-normalized sporting facts at all 55 native Saved points.
Generated Save IDs change their derived log anchors; raw equality is not claimed
for those post-tournament hashes. No fixture, week, Save or sporting check was cut.

Bounded exact-value source projections and compact dependency-reference hints
avoid repeated parsing after fresh physical-byte hashing. Existing full source,
owner/head/ancestry checks remain; operation proofs follow the actual snapshot,
including raw-driver/cross-context rollback. Stored formats/hashes are unchanged.
Cold replay and history growth remain: cold W50 is 31.28 versus 27.66 s here,
and W4→W50 cycle growth is still ~7.5×. This is a measured scoped speedup,
not flat-cost history, all-Run performance or release completion.

Local evidence includes 65 contracts (2.51 s), real native controls/recovery,
the complete W52 and genuine Chromium final closure/reopen. Final-head hosted
W52/W61/W80, short/control/browser, native Tour and Saved integrity gates must
actually pass before a merge recommendation. See
`docs/NATIVE_FULL_SIMULATION_PERFORMANCE.md` and the latest PR checks for the
repeatable procedure, exact scope, limitations and final evidence. Draft skips
never count. The Master/product rules and reserved frontend remain unchanged.

---

# Native Full Simulation integration candidate — 23 October 2026

Base `buuk` `79affb0e5e8b76d58535d01d50acd5a8ec7577fa` includes owner-merged
#1635. Implementation continues in the single PR #1637 on
`feat/native-full-simulation-20261023`; only the owner merges.

Native v2 commands use the existing server task worker, singleton lease and stale
writer fences, with the original hash-bound Saved calendar, seed and frozen target.
Actual Tour matches/awards and Week/Season services own sporting changes. Entry,
results, separate Season Transition review/approval and manual Save remain explicit.
Native final closure has its own review, approval and manual immutable Save, with
an outgoing Closing Ranking and summary; it opens no extra week. A native Branch
aggregate cannot be consumed by the legacy FAX driver, even on reference numbers.

The Admin exposes native review/start, same-task continuation, safe pause/stop,
season approval and final Save. Polling checks actual stored receipt identities
and hashes without running MatchEngine; the writers still authenticate/replay
complete production sources. See docs/NATIVE_FULL_SIMULATION_TASKS.md for the
precise supported boundary and verification ledger.

**WAIT:** implementation acceptance is still running. The actual short sporting
season, native Save/target/restart, final closure/rollback, explicit seasonal
approval/restart and recovery/stale/concurrent cases have executed locally, along
with legacy task regressions and frontend contracts/build. The W52/W61/W80 full
production matrix and all relevant hosted checks on the eventual final SHA
must actually pass. Genuine native Chromium has passed locally. Draft skips are not evidence. No merge readiness
is claimed. Final-week native Editions requiring a closing-only result adapter,
unsupported Health/calibration and other existing native Tour formats remain
explicitly blocked; no result or prerequisite is invented.

---

# Original-calendar task evidence — 22 October 2026 candidate

Verified base `buuk` `26e67903` contains owner-merged #1632–1634. Server task
views now expose an authenticated original Saved calendar and revision in a v2
read DTO. Progress calculations use its W/horizon; CS/EN rows show the true
season/year/week. Compatible v2 preparation links select the actual source season;
unsupported source-picker clocks remain explicit Branch-only handoffs.
Old v1 client responses retain explicit legacy semantics. GET never rewrites
Saved history, task storage, commands, audit or idempotency receipts; a later
Run horizon cannot silently replace the original task clock.

This does NOT enable arbitrary-calendar Full Simulation: legacy driver, ranking,
summary and target execution guards remain. W52/W80 read/arithmetic tests are
not complete worker execution proofs. Supported FAX HTTP/browser acceptance and
final-head CI remain the merge gate. The historical 78 Viewer failures remain
separate release debt. See docs/FULL_SIMULATION_TASK_CALENDAR.md.

Next integration work: migrate actual native Full Simulation orchestration and
its target/transition authorities, with real W52/W61/W80 execution evidence;
do not remove legacy guards merely because the read DTO now accepts a clock.

---

# Consolidated Admin frontend review — 22 October 2026

Baseline buuk `a0308cef` contains owner-merged #1606. The 52 remaining ordinary
ChatGPT frontend PRs were integrated together (114 non-overlapping source/test
files), preserving their source heads in a machine-readable manifest. This
covers truthful Saved/calendar labels, source-scoped selection and pagination,
strict/encoded navigation, archived-template safety, loading/error feedback and
read-only catalog/filter/table usability. No simulation, backend or product
Master rule changes are implied.

Independent review reproduced and corrected a paused Calendar Compare Apply
switching to a later source/season; the submitted command is now frozen and a
late result is scoped to its reviewed context. Existing route-level assertions
were aligned with the intended labels and exact preview counts. Baseline full
frontend testing has 78 failures in 13 Viewer files; these are retained and must
not be hidden or described as successful checks. Final scoped/full-delta/build
and exact-head hosted results belong to the integration PR before owner merge.

See [review boundary and all source PRs](docs/ADMIN_FRONTEND_CONSOLIDATION_2026_10_22.md).
This replaces 52 separate merge/test cycles; only the owner merges. Then resume
canonical pre-alpha integration rather than continuing indefinitely with small
legacy-screen polish. Prior candidate notes below remain historical evidence.

---

# PR #1606 independent review correction — 22 October 2026

Review reproduced a Player Lab request-selection race: an offline-paused run
submitted for one saved Session could resume against a newly selected Session.
Scratch runs could likewise be redirected to a later saved selection. The run
now captures scenario and Session ID/fingerprint synchronously in mutation
variables; source switches cannot change the submitted request or display its
late result in another editor. Two regressions exercise actual QueryClient
pause/resume for saved and scratch submissions.

Independent local verification: 52 focused frontend/editor tests passed, 54 Lab
service/calendar/legacy compatibility tests passed, and production build passed.
Final-head hosted acceptance remains required; earlier-head results and Draft
skips do not establish merge readiness. This is a bounded frontend correction,
not a new simulation rule or broader native authoring support.

---

# Historical Run-to-Lab copies — 22 October 2026 candidate

Verified base: `buuk` `405b569c4a84ae3b5e834ad7e89806126871f223`, owner-merged
#1577; no other PR was open at task start. Older candidate/pending entries below
are historical evidence, not the current implementation boundary.

Match, Tournament and Player Labs now read the explicitly selected reachable
Saved Revision through shared authenticated source resolution, including actual
pre-fork ownership, native-v2 dependencies and born-player biography. Copies
retain complete sporting/Health source facts and provenance; seven MatchEngine
values remain an explicit projection. Native tournament copies support their
frozen ranked main-only 4/8 field; unsupported repair formats still fail closed.
Player Lab gains persistent independent Sessions, source selectors and calendar
v2 experiments using the existing W-aware development kernel. Legacy v1 bytes,
fingerprints and replay remain unchanged. Dirty/stale editors, late import/Save,
selection changes and genuine running calculations retain their protections.

Candidate evidence so far: 19 existing real Lab API tests passed in 28.13s;
50 focused frontend/concurrency tests passed in 6.38s; production build passed;
seven calendar/Health/legacy-byte contracts passed in 0.78s. Actual historical
native W52 API/restart/isolation acceptance passed in 54.78s and separate
rehashed-provenance/missing-dependency rejection in 25.35s. Genuine Chromium
completed historical source selection, all three Lab experiments, late-import
editor preservation, persisted Sessions, SQLite restart and identical replay,
with no source-table mutation. These are executed candidate results, not a claim
that final-head hosted checks already ran. Final acceptance must run again on the
exact final commit; Draft skips do not count as passes.

Distinct adversarial review checked actual-row proof scope, shared ownership,
pre-birth membership, inherited Edition resolution, unsupported Health/repair
rejection, legacy byte compatibility and UI reply ordering. The consolidated
Lab service/API/calendar suite passed 73 tests in 55.57s. A real nested native
fork inherited-Edition copy passed in 61.22s, with source-table isolation.
No unresolved implementation defect was found in that review. Hosted manual
workflow dispatch is currently blocked by `Forbidden` in the available CLI;
local exact-head acceptance and hosted status are reported separately in the PR.

Limits: complete sporting state is required; no seven-value-only bootstrap is
advertised as a full copy. Unsupported numeric Health effects block Match and
Tournament imports; Player v2 preserves/projects stored Health without invented
healing. General native-v2 component authoring stays blocked. Training Load,
career AI and broader Player Lab simulation remain separate work. See
[the implemented contract and acceptance](docs/HISTORICAL_LAB_COPIES.md).
Next: finish exact-head acceptance and owner review of this single Draft PR;
then extend only the documented remaining Lab capabilities. No merge performed.

---

# Admin and Test Lab workflow review candidate — 22 October 2026

Baseline `buuk` is `aecec53c560f8a850f82358158e9606da12483a4`, containing
owner-merged #1576. That prior final head had 53 successful checks and only the
inapplicable docs-only check skipped. Its older pending notes below are history.

The follow-up Admin UI work has been reviewed beyond its original happy-path
component checks. Saved Match/Tournament Sessions now retain an explicit editor
baseline. Inventory refresh never replaces local text; remote changes/removal
block session commands until explicit reload, with confirmed local discard when
needed. Late Save/create/import replies respect subsequent selection and edits.
An in-flight calculation stays pending after input invalidation, so a second
expensive run cannot silently start and an old result cannot reappear.

Tournament proposals authenticate the exact selected Session and target in the
UI, keep the same command for uncertain Apply retries, and stage only after the
separate reviewed action. Actual production API testing exposed a missing flush
before the aggregate SELECT in a session with autoflush disabled. The explicit
transactional flush fixes first Apply; late-failure rollback, retry and normal
Save remain covered. Unsupported native-v2 component edits are blocked before
staging, matching the existing Package boundary.

Evidence for this candidate: focused frontend regression/build checks, 66 real
Lab API/application checks (62.34s), and genuine Chromium Match/Tournament/Player
flows including concurrent real session writes, delayed real Save delivery,
Run isolation, reviewed Apply/Save and physical SQLite restart. A new scoped
Ready/manual Chromium workflow preserves that acceptance. The expanded native
fork corruption/continuation scenario and final-head hosted gates must also pass
before this candidate is called merge-ready; Draft skips are not passes.

This is workflow correctness, not a claim of calibrated realism or a complete
pre-alpha. Native-v2 general component authoring remains unsupported. A subsequent
bounded integration should review historical Run-to-Lab copies against modern
Run calendars, born players and native Saved authority rather than substituting
legacy 61-week assumptions or Initial World-only biographies.

---

# Native public Saved fork continuation candidate — 21 October 2026

The public reviewed writer now installs an active independent v2 native Branch
with authenticated original history, its own current lifecycle/Health/Tour and
new Entry, MatchEngine, development/ranking and Week/Season commands. Manual
Save/linear restore, restart, nested forks, Signed Viewer selection/publication
and strict Run horizon envelopes use that versioned aggregate. Original sources
and later original-Branch prospect epochs are never silently remapped/substituted.

Duplicate proof work is removed within transactions. Completed immutable proofs
can be reused only after freshly checking the full physical SQLite dependency
graph; target self-hashes alone never authorize reuse. Run overview also defers
unneeded large World catalogs, and each actual registry response loads its
country config once without changing fingerprints.

**Local candidate evidence:** complete public HTTP/SQLite birth, real matches,
points, restore/restart, nested/concurrent forks, source corruption, Viewer and
strict extension passed in 574.15s. Real Chromium CS/EN create/transition/Save/
reload now exits cleanly. Focused checks: 101 passed in 42.68s; 77 Package/security
checks passed in 2.66s; 35 Package-guard regressions passed in 10.83s; 70 frontend
tests and production build passed. Actual-source and born-player regressions
passed (2 tests in 496.02s); private baseline/install checks passed (15 tests in
92.50s). Final command-namespace and no-stage Package guards also passed.
Latest-head hosted acceptance still requires verification; no merge readiness
is claimed here yet.
Fast CI/CodeQL continue during Draft;
relevant Ready/manual acceptance must execute on the exact final commit.
See [current contract and explicit limits](docs/NATIVE_SAVED_FORK_AUTHORITY.md).
This supersedes earlier public-blocking implementation notes below; the private
pending v1 staging path itself stays read-only and covered.

---

# Native fork typed sporting Save candidate — 21 October 2026

The internal read-only Save preflight now returns a strict versioned candidate
containing **complete** independently played match evidence, target/parent
Saved identity and exact Working Draft identity/version. The candidate's
canonical fingerprint is included in the Save review. A source-foreign,
empty or stale candidate fails structural checks, while actual SQLite
preflight still authenticates and replays original historical facts. New
pure and integrated assertions cover deterministic roundtrip, rejection of
foreign/stale inputs, non-mutation and invalidation by a later match.

**Not implemented:** persistent Saved descendants, writer-side
reauthentication, Manual Save/Restore, Tour/lifecycle/Health/Entry integration,
public native Branch activation or Viewer selection. All old guards remain.
The new code is not merge-ready until its focused and latest-head hosted
tests pass, and the full native fork objective remains incomplete.

---

# Native fork read-only sporting Save preflight — 21 October 2026

An internal `NativeForkSportingService.preview_save` now reviews the
authenticated, replayed, nonempty dirty match draft and binds current Saved
HEAD, Working Draft version and full checkpoint fingerprint in a deterministic
review token. Clean drafts and stale inputs are rejected; fresh matches
invalidate older reviews. The preflight is read-only and explicitly returns
`saved: false`, with no public endpoint, Saved descendant, restore, Viewer
activation or pending-Branch permission changes.

Focused actual-SQLite integration assertions were added to the existing native
fork draft exercise. Hosted results for this change are still required; no
successful latest-head acceptance is claimed until those jobs run.

---

# Native fork independent sporting draft — 21 October 2026

The internal pending fork now executes genuine same-week MatchEngine exhibitions
and persists its own versioned Working Draft. New matches consume exact current
57-attribute records and prior Form/sharpness/fatigue, with original lifecycle,
Health and historically effective Saved biography/prospect sources. Every dirty
read replays the new events against actual sources. Original histories/runtime,
Saved HEAD and Viewer remain unchanged; no neutral bootstrap, healing, ranking
award or old-owner remapping is introduced.

Preview/confirmation, stale checks, exact/concurrent/conflicting retries, write
failure, restart and explicit discard have real application/SQLite coverage over
production HTTP/MatchEngine sources. A born-player target remains at Week 3 while
the original actually transitions/Saves Week 4; both survive restart independently.
Fully rehashed false biography and changed original source rows fail closed.

**Local evidence:** 138 focused regressions passed in 65.36s; expanded actual
baseline/match-draft/restart/discard integration passed in 105.14s (109.18s total).
The separate historical born-player/epoch/independent-original integration passed
in 125.17s (129.17s total). Original source/birth/post-match/epoch assertions also
passed in a combined local run with another historical draft check. New code and
tests pass Ruff/compile checks. The born-draft acceptance runs as a separate job
alongside the preserved original source gate; heavy Draft skips remain non-passes.
See [contract and exact limits](docs/NATIVE_SAVED_FORK_AUTHORITY.md).

**Remaining:** Manual Save/restore of the new sporting draft, joined versioned
lifecycle/Health/Entry/Tour continuation and atomic public activation, followed by
independent real two-Branch Tour play/Save/restart/restore and native Chromium
creation. Public native create/Save/Viewer activation remain blocked; the internal
match draft reports `saved: false`. This Draft PR is still incomplete.

---

# Native fork atomic baseline persistence — 21 October 2026

The internal installer now persists an authenticated, target-owned Saved root,
clean Working Draft, Branch/state metadata and audit/receipt in one SQLite
transaction. It retains the original source ancestry and exact current facts;
it does not rewrite historical matches, admissions, Health or ranking owners.
Normal Saved reads reauthenticate actual source dependencies outside stripe
locks. Exact concurrent retries are durable; conflicting retries, source cycles,
changed source bytes, rehashed facts and schema/component downgrades fail closed.
See [the persistence contract](docs/NATIVE_SAVED_FORK_AUTHORITY.md).

The persisted target is deliberately pending (`preparing_native_fork`) and
read-only. There are no live continuation rows and no public staging endpoint.
Existing guards still prevent native creation, execution, Manual Save/restore
and Viewer selection. This is real baseline persistence, not a functioning
independently simulated fork or merge readiness.

**Local evidence:** 124 focused regression cases passed in 40.29 seconds. The
real HTTP/MatchEngine-source installation and 14 structural cases passed in
52.70 seconds, including final-audit rollback, two concurrent first attempts,
retry, restart, ordinary history, shared-lock/cycle and tamper checks. Only five
new rows are added; every existing SQLite dump statement remains unchanged.
The original real native birth/post-birth-match/epoch scenario also passed in
354.63 seconds (126 distinct cases across the three selections).
The separate acceptance job runs alongside the longer native birth/epoch gate
on Ready/manual execution; Draft Fast CI stays focused. Draft skips are not passes.

**Next:** versioned independent sporting/lifecycle/Health/Entry/Tour continuation
and atomic activation, followed by real two-Branch play/Save/restart/restore and
successful native browser creation. The original PR remains incomplete.

---

# Native fork target baseline preparation — 21 October 2026

The same PR now prepares a typed, target-owned current baseline from authenticated
native Saved sources. Lifecycle identities/policy, full sporting values and
Health facts/actual source week remain exact; original Tour/ranking and historical
events retain source identities. Read-only verification independently rebuilds
the facts and checks caller-supplied expected command scope. Target identifiers
are not reserved and no Branch/runtime rows are installed by this preparation.
See [contract and current limits](docs/NATIVE_SAVED_FORK_AUTHORITY.md).

**Local evidence:** 66 focused fast tests passed in 16.64 seconds; the expanded
real native Saved scenario passed in 410.90 seconds (67 distinct cases combined).
Preparation and JSON reauthentication cover pre/post-birth, real post-birth
matches, source epochs and server restart without SQLite changes. Rehashed
sporting/Health/policy/ranking facts, wrong command target and existing target
origins are rejected. W7/W52/W61/W80 and older Health facts/compatible horizon
dates have separate pure contracts. This is baseline preparation evidence, not
persisted target creation or independent runtime continuation.

**Remaining original objective:** atomically install the baseline and integrate
versioned sporting/lifecycle/Health/Entry/Tour continuation, then prove independent
actual play/Save/restart/restore of both Branches and successful native browser
creation. Public native creation remains blocked; this is not merge readiness.

---

# Native fork historical source authority — 21 October 2026

PR #1576 now has an explicit immutable source binding, resolved against the actual
authenticated Saved ancestry. Branch review verifies original pre-play population
and Health, original Tour/Edition/command sources, and a strict historical cutoff
propagated into nested native roots. Recomputed reference hashes do not authorize
changed source components, a different original owner, or an unreachable revision.
No original match input/log, admission or prospect epoch is rewritten; review
remains read-only. See [source authority contract](docs/NATIVE_SAVED_FORK_AUTHORITY.md).

**Completed local evidence:** 52 distinct focused tests across source contracts,
real Branch review HTTP/SQLite, existing Branch creation and CI phase policy.
The expanded native scenario includes a real configured post-birth tournament,
before/after admission and source epochs, original byte preservation, tampered
reference rejection, source corruption, unreachable sibling history, restart
and restore. Its 16-test source/review selection took 386.81 seconds. Actual
Chromium CS/EN review, safe native refusal and Viewer isolation passed; TypeScript
and production build passed. These are local source-side results, not successful
target continuation or final-head hosted acceptance.

**Still incomplete:** the target-owned native fork baseline and independent
continuation writer. Existing native create guards remain. The PR is an unfinished
implementation, not a merge recommendation or native fork completion.

---

# PR #1576 follow-up — 21 October 2026

The owner requested takeover of the interrupted branch and shorter development
feedback. This follow-up fixes explicit configuration/security test commands
being deselected by the PR changed-file collector. It also synchronizes Shell
acceptance with actual navigation dialogs and gives native knockout table headers
explicit column scope. All 188 existing Shell assertions remain present.

Dedicated pre-alpha/Earth acceptance jobs now defer expensive execution for Draft
PRs, run on Ready for review and subsequent ready-PR pushes, and remain available
through manual dispatch. Fast CI and CodeQL remain active during Draft work.
Draft skips are not integration evidence or merge permission; final review must
still have all relevant latest-head acceptance actually green. See the updated
[test policy](docs/PRE_ALPHA_TEST_POLICY.md).

The original match-bearing native fork remains incomplete, as the detailed
checkpoint below records. This follow-up does not remove its authenticated-source
guards, rewrite sporting history, or claim successful native continuation.

---

# Saved Revision Branch review — incomplete native fork candidate, 20 October 2026

**Verified integration base:** `buuk` is
`428ef8b75de4dd7dc980f307c6a2ffd31d4e4ec0`, owner-merged #1575.
Remote history and the GitHub PR metadata agree; no PR was open at task start.
The prior candidate/unmerged checkpoints below remain historical evidence.

**Main requested behavior is still incomplete:** creating a Branch from a
match-bearing native Saved Revision remains deliberately blocked. Real HTTP/SQLite
reproduction identifies `calendar_standalone_match`,
`calendar_player_sporting_checkpoint` and `calendar_tour_authority` as missing
fork coverage. Actual native admission adds the existing v4 lifecycle and v3
Health source/Entry/transition authority guards. Removing these guards or
rehashing rewritten history would not provide valid fork authority.

**Current implementation candidate:** the existing Saved Revision Branch writer
now has a read-only server review, a compact historical summary and known
blockers, a server-checked confirmation bound to the source/head/Viewer/name
inventory, and an atomic durable retry receipt. CS/EN History exposes blockers
before confirmation, retries an uncertain request with the same command and
opens the created supported Branch. Opening the review never starts simulation
or saves a draft. The original unreviewed API remains compatible; it retains
all existing full writer guards. See [contract](docs/SAVED_REVISION_BRANCH_REVIEW.md).

**Local evidence:** production HTTP/SQLite checks exercise confirmed supported
creation, source integrity, concurrent exact retry, changed-input collision,
stale review, late receipt rollback, independent Manual Save and physical
restart. A separate native HTTP/SQLite scenario tests original real matches,
before/after actual admission and v2 prospect epochs, unchanged historical
Saved bytes, replay and source restore. It proves the native refusal remains
safe, **not** a successful native fork. Frontend component/build and actual
Chromium evidence are recorded with the PR; only completed runs count.
Latest-head hosted CI remains a separate requirement.

**Next work on this same objective:** authenticate a source-bound native fork
root; preserve the original historical MatchEngine inputs/results/log anchors
and prospect epochs; establish target-owned current lifecycle, Health, sporting
and Tour continuation without rewriting the source. Then prove independent
play/Save/restart/restore of both Branches. This candidate must not be presented
as completion of that task or as pre-alpha/Full Simulation readiness. Only the
owner merges.

---

# Canonical Admin entry-point recovery — 20 October 2026

**Verified integrated base:** `buuk` `5615a293df881d4bbde8819234269b174f21713e`
is the owner's merge of #1573. No PRs were open at this task's start.

**Current candidate:** bilingual global Simulation guidance now points to the
Run inventory and Task Center, lists current authoritative scope names and
explains capability blockers and explicit manual Save. It does not pick a
remembered Run, create commands or promise native Full Simulation readiness.
The older routed Admin regression suite is updated to canonical global Home,
Product Run inventory and canonical Viewer source boundaries. Its existing
196 cases are retained; missing mocks and obsolete expectations are repaired.

**Hosted implementation evidence:** `41c6bfa070aab13b3723fe3bd10da79816641a36`
passed the 192-test critical baseline and 202 changed-file component tests,
including all 196 retained routed cases. Four runtime smoke cases overlap the
sets; these are not 394 distinct tests. TypeScript/Vite build and all three
CodeQL analyses passed; the PR comparison reported no new alerts. The complete
frontend CI job took 68 seconds. Backend tests were correctly outside this diff.

This closing documentation commit preserves the tested implementation; its own
latest-head CI must also pass before review readiness. Local execution is still
unavailable. These are component/build results, not real HTTP/browser integration,
a green complete frontend suite or pre-alpha release certification. Remaining
stale Viewer-specific regressions and full Master acceptance remain.

---

# Integrated baseline and focused frontend recovery — 20 October 2026

**Verified integration baseline:** `buuk` `7301d34b86db833bf710d84f1dd387ffe90c938c`
contains owner-merged #1571 (future prospect source epochs, including historical
replay/prefix validation and reload recovery fixes) and #1572 (frontend dependency
advisories). Both feature heads completed their applicable CI before owner merge.
The earlier candidate paragraphs below are retained historical checkpoints.

**Current candidate:** restore routed Admin Time and historical-view component
checks, current global Home/empty Run private-storage smoke coverage, and stable
accessible malformed-JSON feedback in Match Lab. Unsaved session edits now visibly
block running an older saved scenario until an explicit successful session Save. Add these focused contracts to
Fast CI so unrelated UI work cannot silently break them again. No backend writer,
Saved signature, simulation policy or numeric Health calibration changes.

**Hosted validation evidence:** implementation head `5a08e44bfea69921d717405866de7c534a384641`
passed 192 critical component tests (14 files), the 24 changed-file component tests
(4 files), TypeScript/Vite build, all three CodeQL analyses and its no-new-alert
comparison. The final test/docs refinement also checks direct form submission;
latest-head CI is required before review readiness. Local execution is unavailable.
The backend job compiled source and generated the existing Earth realism audit;
it did not run pytest for this frontend/workflow-only diff.

The earlier exploratory full frontend run had 107 pre-existing failing tests.
This bounded repair covers the failing Admin Time, historical simulation, runtime
smoke and Match Lab contracts; the remaining full-suite failures were not recounted.
It is not a green full frontend suite or 50×61 release certification. Remaining
legacy Viewer tests and complete Master acceptance remain follow-up work.

---

# Native future prospect source epochs v2 — unmerged candidate, 20 October 2026

**Integration baseline verified:** `buuk` `59309089663f7a5bd62d4bbbb23329da70215f5b`
includes owner-merges #1569 and #1570; no open PR at start.
This new **single-PR candidate** adds append-only historically Signed Run
prospect sources after genuine admission and competition, with a dedicated
CS/EN Admin review/materialize/manual Save and preserved v1 signatures.
Strict per-week v1/v2 native transition, replay and restore selection replaces
the old `native_prospect_source_epochs_required` blanket Save blocker.
See [contract](docs/RUN_PROSPECT_SOURCE_EPOCHS_V2.md).

**Important:** this paragraph records candidate code, not owner-merged
production or green tests. Required targeted HTTP/SQLite, real Chromium,
existing native Tour/birth/recovery and browser workflows must pass on the
**latest PR commit** before merge can be recommended. Historical API
acceptance is deliberately separate from Fast CI; no 50×61 full release suite
runs automatically for this PR. Earlier audited checkpoints remain below.

**Remaining pre-alpha work:** historic prospect edits/deletions stay forbidden,
numeric Health/policy, full cross-Branch coverage, career AI and other Master
scope are not completed. The actual full pre-alpha release gate remains
separate and unexecuted by this implementation candidate.

---

# Post-admission competition candidate — 20 October 2026

**Verified integration base:** `buuk` `0b82cd96fadd9d402ac8e3ad70383a36cd0d5199`,
owner merge #1569; no open PRs at task start. The entire preserved intake stack
is integrated. Earlier integration-candidate paragraphs below are history.

**Independent implementation candidate:** one PR directly into `buuk` adds
Tour v4 / checkpoint v12 / tournament v6 after actual Signed admission and
manual Save: genuine current-population Entry/draw, original 57-backed
MatchEngine and Health, confirmed Edition points/ranking, actual next-week
match counts, complete command/history replay and Save/restart/restore.
CS/EN Admin exposes real capability and preserves explicit consent/Save and
stale-response guards. See [contract](docs/CALENDAR_NATIVE_POST_INTAKE_COMPETITION_V1.md).

**Verification boundary:** local initial complete HTTP/SQLite flow passed;
focused domain/frontend checks and production web build passed. The expanded
local Earth/FAX scenarios (including rollback/tamper) and actual post-admission
Chromium path also passed. Final-head extension and all applicable CI gates
remain the handoff authority, recorded in the PR. This candidate has not been
owner-merged; local evidence does not substitute for latest-commit green checks.
Only the owner merges; no dependency PR chain.

**Remaining limits:** unchanged Signed prospect source (no historical epochs),
legacy-only prospect style/archetype/career metadata explicitly unavailable,
post-admission policy edits, numeric Health/healing, protected forks,
cross-Edition simultaneity, remaining Master scope and full pre-alpha/50×61
release certification. Full Simulation stays blocked. Product canon unchanged.

## Earlier checkpoint history (retained)

# Native intake integration correction — 20 October 2026

**Actual remote baseline:** `buuk` is
`51dae9f56bdcf021422dd6696652a13681f503c5` (owner-merged #1562).
Reverified for issue #1568 with no open PRs at task start. Although #1563–#1567
and #1560 show merged, their dependent feature-branch merges did not reach
`buuk`. The older checkpoints below describe development evidence, not proof
that those changes were integrated into the target branch.

**Proposed integration, not an owner merge:** branch
`fix/native-intake-integration-buuk-1568` starts at that actual `buuk` and
normally merges preserved source
`b12e53566dd45e313444eec3c49380f2d33bfb06` from
`feat/native-birth-historical-replay-20261019`. Pure merge commit
`11cb239db30b9cb4b791b2ba36052b9cba3ccdb2` has tree
`4f24a4f3da6692cfd18b42369624b3cfcecd8262`, exactly identical to the preserved
source and combined UI head `9cd7319882c17798a3326fa09575acbef7ef1483`.
No runtime, test, workflow or historical Signed bytes were reimplemented or
changed by this correction. The subsequent correction changes only
`CURRENT_STATE.md` and `ROADMAP.md`; all earlier checkpoint history is retained.

**Verified ancestry:** `git merge-base --is-ancestor <source> HEAD` succeeds
for every required source head, as well as both merge parents:

| Source | Required source head |
| --- | --- |
| #1562 Health (already in buuk) | `095a365248c380aac9560c15f38ef01c5b98fe73` |
| #1563 complete Health preparation | `b263ed0ab5f28f192ad1647e49d7ff43a6d4ff35` |
| #1564 sporting checkpoint v11 | `c9838912f87a99ca60b9d9e6b1f1d251d498db44` |
| #1565 atomic confirmed birth writer | `ca447c2eaa3e41edb499583459dde71acb143fbb` |
| #1566 runtime readiness/Admin | `effeb11eb8a7605f8f27cea332cddb883eb0a9f7` |
| #1567 frozen historical match replay | `f3dbad847df044b199f4f6b98a02ee1efd80f46b` |
| #1560 combined Admin UI | `9cd7319882c17798a3326fa09575acbef7ef1483` |

**Composed bounded behavior:** explicit confirmed 15-year-old intake atomically
stages full Health history, lifecycle, sporting v11, ranking/public transition
and Tour v3 receipts. Separate manual Save publishes an immutable revision;
exact retry, rollback, restart/restore, strict calendar extension and frozen
pre-birth match replay retain their original authorities. Both CS/EN Admin
panels coexist with stale-response protection; post-intake competition stays
disabled. See the [birth execution](docs/CALENDAR_NATIVE_BIRTH_WEEK_EXECUTION_V1.md),
[readiness](docs/CALENDAR_NATIVE_TRANSITION_READINESS_V1.md) and
[historical replay](docs/CALENDAR_NATIVE_HISTORICAL_MATCH_REPLAY_V1.md) contracts.

**New-head validation boundary:** prior source greens are historical evidence
only. The integration PR must stay draft until its latest head passes focused
local checks, Fast CI, all six real birth/readiness HTTP/SQLite cases, original
full native HTTP/SQLite Signed restore, Season API, real birth Chromium,
W52/W61/W80-1000 Tour Chromium and every other applicable browser/recovery gate.
Inspect actual logs, including the process-level acceptance event override;
a deselected mandatory case is not a pass. Report selector-scoped unrelated
legacy scenarios separately from executed browsers. Final SHA/results belong
in the PR evidence; this document does not claim pending CI has passed.
A separate adversarial pass must check live/Saved ownership, Signed bytes and
actual PR branch/HEAD/base identity before handoff. Only the owner merges,
explicitly into `buuk`; preserve ancestry with a merge commit rather than
squash/rebase. This correction itself is not merged by the assistant.

**Still unfinished:** post-intake competition, immutable historical prospect
source epochs, numeric Health/healing, protected fork/re-signing, remaining
Master scope and full pre-alpha release/50×61 certification. Master and sporting
product decisions are unchanged. No Full Simulation or release unlock.

## Earlier checkpoint history (retained)

# Frozen pre-birth match replay candidate — 19 October 2026

**Verified:** #1565 `ca447c2` has every applicable final-head check green and is
ready for owner review. The corrected #1566 head `effeb11` has green Fast CI,
frontend build, all six new native HTTP scenarios and its real Chromium birth/
57-attribute/explicit Save/Viewer scenario. That screenshot was visually inspected;
all remaining native/legacy gates have now passed on the same `effeb11` head.
Neither candidate was merged by the assistant. `buuk` is unchanged at the last
verified `14e2784`.

**Current dependent fix:** historical continuation/final replay recognizes a v11
owner only through its unchanged, actually Signed pre-birth root. It authenticates
Run/Branch lineage and rejects rehashed root divergence without consuming today's
Health or granting mutation readiness. Original MatchEngine inputs, complete
result/log comparison, native provenance and ordinary old responses are preserved.
See [contract and tests](docs/CALENDAR_NATIVE_HISTORICAL_MATCH_REPLAY_V1.md).
The initial replay head passed its actual match-replay and browser gates, but the
mandatory readiness job deselected its unchanged test: GitHub's reserved event
variable ignored a step-level override. The workflow now passes the acceptance
event directly to pytest, as the original native Tour gate already does. This
fix must pass its own final-head gates; no acceptance assertion or timeout changed.

No post-birth new competition, source epochs, numeric Health, protected fork or
release certification is implied. These remain the main integration blockers.

## Earlier checkpoint history (retained)

# Native birth runtime capability candidate — 19 October 2026

**Published writer:** #1565 `ca447c2` has all applicable final-head gates green:
Fast CI, all five new real birthday cases, full native HTTP/SQLite Signed restore,
Season API, Shell and W52/W61/W80-1000 browser acceptance. It is ready for owner
review, not merged.
Earlier #1560/#1562/#1563/#1564 heads were green. Owner alone merges;
`buuk` remains `14e27846898500aaffc6462878c45aa03792147f`.

**Current dependent slice:** real runtime transition readiness, distinct from
older read-only component preflight; exact owner/clock capability, unsaved/terminal
responses, CS/EN Admin, stale-result rejection and disabled unsupported post-birth
competition. Run-shared incompatible source Save reports its existing epoch
blocker in preview and rejects forced writes transactionally. See
[contract and bounded evidence](docs/CALENDAR_NATIVE_TRANSITION_READINESS_V1.md).
Actual local Chromium is missing; its added real browser gate must pass in CI.
The first CI browser attempt used a random Vite port outside the application's
allowed CORS origins and failed before Tour mount; the test harness now uses the
existing allowed 5173 origin. Product CORS rules are unchanged. Check the corrected
head, not the superseded failed run.
This slice is not merge-ready before its final-head checks complete.

Post-birth competition, immutable historical source epochs, protected forks,
numeric Health, remaining Master scope and full release acceptance stay open.

## Earlier checkpoint history (retained)

# Confirmed native birth Week/Season candidate — 19 October 2026

**Verified stack:** #1560 `db84d65`, #1562 `095a365`, #1563 `b263ed0` and
#1564 `c983891` have green final-head applicable checks and are ready for owner
review. #1564 includes real native Tour HTTP/SQLite Signed restore, season API,
Shell and W52/W61/W80 browser acceptance. Nothing was merged by the assistant;
`buuk` remains `14e27846898500aaffc6462878c45aa03792147f`.

**Current dependent candidate:** the ordinary explicitly confirmed Tour Week/
Season command now atomically stages checkpoint v11, complete natural Health,
birth/lifecycle, genuine Entry-gated ranking, public event and Tour v3 receipts.
It independently replays actual live rows before commit; manual Save remains
separate. Restore verifies the full captured post-restore aggregate. Native
receipt origins must really own their referenced Saved Tour/checkpoint; proof
reuse includes the additional native dependencies. See
[bounded execution contract](docs/CALENDAR_NATIVE_BIRTH_WEEK_EXECUTION_V1.md).
This candidate is not merge-ready until its own final-head gates pass.

**Next blockers:** post-birth Edition/Entry/match/policy operations remain
deliberately blocked; v3 currently permits natural transitions only. More annual
prospects require historical source epochs, not changes to the current single
Signed source snapshot. Protected fork re-signing, v3 Health corrections,
historical initial population, remaining Records/notifications, Full Simulation
and Master release gates are still unfinished. No release or 50×61 claim.

## Earlier checkpoint history (retained)

# Native sporting checkpoint candidate — 19 October 2026

**Verified latest open heads:** #1560 `db84d65`, #1562 `095a365` and #1563
`b263ed0` have completed all their applicable checks successfully. This includes
the long native HTTP/SQLite acceptance, Shell and W52/W61/W80 browser gates as
applicable; legacy hybrid checks on #1560 were scoped out by their selectors,
not executed sporting scenarios. The owner has not merged these PRs; `buuk`
remains `14e27846898500aaffc6462878c45aa03792147f`.

**Current dependent candidate:** durable sporting checkpoint v11 preserves the
complete historical root and records exact native birth/week stages. Production
SQLite parsing/replacement/restore and Saved component verification independently
rebuild the native ledger against Signed source, lifecycle, Health and effective
Tour development policy. The real Admin preflight now reports this checkpoint's
fingerprint, bound into the versioned combined transition proof. See
[checkpoint contract and evidence](docs/CALENDAR_NATIVE_SPORTING_CHECKPOINT_V11.md).
This candidate is not merged or certified until its own final-head gates pass.

**Next blocker remains the coupled live writer:** explicit command/confirmation,
Tour receipts, all-domain atomic Week/Season execution, manual Save and genuine
Entry/ranking adoption. Whole Tour validation explicitly refuses a bare v11
component. Native post-birth match evidence, historical prospect-source epochs
for later annual additions, protected fork re-signing and v3 Health corrections
remain necessary. Existing Master release gates and unsupported mechanics stay
unchanged. No full live intake or pre-alpha release is claimed.

## Earlier checkpoint history (retained)

# Native intake integration checkpoint — 19 October 2026

**Verified owner-merged baseline:** `buuk` =
`14e27846898500aaffc6462878c45aa03792147f` (CI cleanup #1561).
Since the earlier #1547 checkpoint, #1548 merged Signed career Records;
#1550 reduced duplicate authenticated inspection replay; #1551 added atomic
Run prospect materialization; #1552–#1559 added native cohort generation,
Saved-source birthday preflight, full 57-attribute birth/lifecycle proposals,
birth/Entry history validation, W-aware completed-week sporting development,
Saved v4 lifecycle parsing and the real seed-locked Admin HTTP preflight.
These staged/reader capabilities do **not** mean automatic native intake works.

**Reviewed open candidates:** #1560 Admin CS/EN sporting review and #1562
natural Health v3/Saved replay. Review found missing exact frontend week binding,
a rejected valid horizon extension and possible v3-to-v2 Admin proof loss.
Corrections are on their respective branches; check their latest heads, not
superseded CI. #1560 now targets `buuk` and includes merged #1561 cleanup.
The owner alone merges; neither candidate is certified by this document.

**Current dependent implementation:** complete missing Health weeks from the
verified Saved prefix, then bind the target v3 Health component to the real
Signed birthday/sporting preflight. The HTTP response exposes compact backfill
counts and full-chain/combined transition fingerprints. Its target uses the
current extended Run horizon while completed historical clocks remain frozen.
No database/Draft/Save
mutation or activation is added. See
[complete Health preparation](docs/CALENDAR_NATIVE_HEALTH_PREPARATION_V1.md).
This branch depends on the corrected #1562; its required final-head CI remains
necessary before owner merge. Master product decisions are unchanged.

**Next integration blocker:** native sporting checkpoint birth ledger/replay,
then one guarded atomic Week/Season writer for sporting + full Health + v4
lifecycle + genuine Entry/ranking/Tour receipts, followed by real rollback,
Save/restart/restore and protected fork re-signing. Do not remove existing intake
refusals merely because projections and schemas are available. Full Simulation,
numeric Health/healing, correction/discipline, historical initial cohort,
complete Records/Saved Views/notifications and the full Master §31 release gates
remain unfinished. No pre-alpha release or full 50×61 certification is claimed.

## Earlier checkpoint history (retained)

# Current verified integration and next records candidate — 19 October 2026

**Verified owner merge:** PR #1547 to `buuk` at
`93a3f946e86af8265b8e7539d6c6ffcd174f3282`. The production
bounded native Tour now publishes Signed completed-season summaries,
country/Edition/player actual awards, historical Admin/Viewer season
comparison, and the existing genuine next-season MatchEngine/Entry,
Official Ranking, Save, restore and Season Transition. 13 GitHub checks
were successful; original native full HTTP/SQLite Signed Restore reported
`1 passed in 1159.23s` in its job log even though GitHub's workflow
status was stale during the last inspection. Owner performed the merge.

**New independent candidate:** Signed native career Records projection;
six extensible country/player titles, runner-up and Edition-awarded-point
metrics with co-holder chronological history, inclusive fixed season
window, optional country filter, CS/EN Admin, Selected Viewer Saved
Branch, historical cutoff/negative guard and restart equivalence.
[Full bounded contract](docs/CALENDAR_NATIVE_SIGNED_RECORDS_V1.md).
This candidate is NOT merged or green until its latest-head Fast CI,
real HTTP/SQLite and native browser gates pass.

**Remaining unsupported:** full Master §31.39 Records catalog,
persistent Saved Views, rolling period presets, numeric Health and
healing, automatic native intake, correction/discipline, protected
match-fork remap, Full Simulation and complete 50×61 reference release
certification.

## Earlier checkpoint history (retained)

# Current verified integration — 19 October 2026

**Merged:** PR #1546 into `buuk` at
`bb38e5a17e6a9b667c8f47287fb992d8e00ee3be`. Bounded native
W→next Season Week 1 and genuine next-season Editions/Entry/MatchEngine,
ranking, public announcement, manual Save and full signed restore are
production code. The final-head Fast CI, native HTTP/SQLite and W52/W61/W80
browser acceptance all passed. These are NOT a full multi-season release.

**Active independent candidate:** read-only Signed Season Summary. Consume
only the actual previously validated Tour/MatchEngine receipts and Saved
InitialWorld nationality, count actual Edition titles/finals/award points,
show completed seasons in CS/EN Admin and Saved Viewer, compare any two
recorded seasons, reject Working/future/foreign/tampered history. This
candidate is not merged or approved until its real final-head tests pass;
see [bounded summary contract](docs/CALENDAR_NATIVE_SIGNED_SEASON_SUMMARY_V1.md).

**Still unsupported:** numeric Health, native prospect intake,
correction/disciplinary sources, match-fork remap, complete season record
catalog/notifications, Full Simulation and complete 50×61 reference
release gate.

## Earlier checkpoint history (retained)

# Integration checkpoint — 19 October 2026 (verified merge and new candidate)

**Verified `buuk`:** owner-merged PR #1545 at
`9adfa2205fd5f420f9fe59682217ac5f65b7ef13`. Its final-head
Fast CI, Shell browser, Native Tour W52/W61/W80 browser and real SQLite
Tour acceptance passed. Native W→next-season Week 1 Season Transition,
signed sporting v3/checkpoint v10/Tour v2, manual Save, lifecycle and
historically effective Best N ranking are now **merged** within the
bounded configured Tour.

**Active independent candidate:** complete the immediate next-season
Edition continuation. The old Admin scheduling form could emit invalid W+2
at a season boundary; the v10 configured Tour knockout replay needed to
preserve v10 rather than reject/downgrade it. This branch adds horizon-aware
season/week Edition dates and actual next-season tournament HTTP/SQLite
acceptance. These changes remain **unverified and unmerged** until
all required final-head gates succeed. See
[Season Transition contract](docs/CALENDAR_NATIVE_SEASON_TRANSITION_V1.md).

**Still unsupported:** numeric Health/healing, automatic native prospect
intake, staged disciplinary/correction materialization, protected match
fork/remap, full season summary system and complete 50×61 pre-alpha gates.
Full Simulation is NOT unlocked.

## Earlier checkpoint history (retained)

# Current integration checkpoint — 19 October 2026

**Verified base:** owner merged #1543 into `buuk` as
`63a489b6857cece922a98e597ee225a8deb07119`. #1543 completed
its final-head Fast CI, Native Tour browser W52/W61/W80 and Shell browser,
real HTTP/SQLite Tour acceptance and matched W52/W80 replay benchmarks.
The W52 eight-match HTTP scenario improved 375.065→325.369 s (13.25%);
W80 improved 343.488→273.330 s (20.43%); timings describe those CI runs,
not performance SLAs. The preceding configured Edition/Entry, real matches,
Official **Week** Transition and manual Save are therefore merged.

**Active candidate — PR #1545 / issue #1544:** bounded native configured
Tour Season Transition W→next-season Week 1, versioned sporting v3/checkpoint
v10/Tour v2, historically effective next-season ranking, atomic preview/
confirmation, separate manual Save, lifecycle linkage and CS/EN Admin.
[Contract and limits](docs/CALENDAR_NATIVE_SEASON_TRANSITION_V1.md).
This implementation is **not verified or merge-ready yet**; final-head
domain, real HTTP/SQLite season boundary, original full Tour API, browser and
recovery gates must pass. Do not treat a candidate as merged or full pre-alpha.

**Still unsupported:** numeric Health/healing, native prospect intake,
external correction/disciplinary authority, protected match-containing Branch
fork/remap, full season-closing summaries/records and Full Simulation.
These guards are not relaxed by the bounded season action.

## Prior checkpoint and historical implementation evidence (retained)

# Verified integration state — 19 October 2026

The current `buuk` HEAD is `2d5e5a9f21cb288639421f78e19cb3ca489cab02`,
owner-merged PR #1542 (including #1541). The complete configured native Tour
implementation is merged, **not pending**. Its final implementation head
`096246987e7520121447f6565e63a0e711eaa1d9` passed all 14 required
workflows, including the 42-test critical backend gate (140.67 seconds),
the W80/1,000-player Chromium scenario (14:42) and real HTTP/SQLite native
Tour acceptance (16:41). These are measured runs, not universal speed guarantees.
See the merged PR evidence and
[performance review](docs/NATIVE_TOUR_PERFORMANCE_REVIEW_2026_10_19.md).

**Usable bounded path:** versioned Run/Branch and manual immutable Save;
configured native Tour Edition, production Entry, approved field/draw,
real MatchEngine and full-population sporting state, frozen result awards,
lifecycle, Official Week Transition and CS/EN Admin; authentic Saved
history, replay/restart/restore, signed component scope and negative checks.

**Remaining limitations:** native Season Transition is not yet integrated;
match-containing fork/remap, numeric Health/healing, intake and correction/
disciplinary authorities are not complete. Full Simulation and pre-alpha
release acceptance remain blocked. Do not bypass those guards.

**Active optimization candidate on separate branch:** reuse fully authenticated
Saved sporting sources across Opening/Continuation contexts while rechecking
physical SQLite bytes and owners. Its new timings, tamper regressions and
final-head CI/browser/API gates are **not yet verified**; it must not be
described as merge-ready. Avoid overlapping work on this branch.

## Historical #1542 development notes (superseded by verified merge above)

# Performance review — 19 October 2026 (verification pending)

Repair follows #1542 head `4ee5b826`, including #1541; consolidated into #1542 targeting buuk. The previous head's
Fast CI, API acceptance and Shell Browser passed, but Native Tour W80/1000
failed its first post-restart inspection at the unchanged 120-second bound.

Four reproducible causes are addressed: concurrent cold requests duplicated
full validation of identical Saved revisions; and live checkpoint proof reuse
compared JSON insertion order, which changes for maps such as `sets_won`
after canonical Saved serialization. A bounded per-signature single-flight
now shares only successful existing metadata proofs; live reuse hashes the
actual decoded row against the authenticated source's canonical fingerprint.
Every request still verifies its live owner and altered bytes invalidate proof.
Native Tour Save also publishes its already complete exact-byte metadata proof
only after successful commit, avoiding a second full replay in its response.
Rollback publishes no proof; other component, scope and content checks remain.
An unsaved Tour owner now also uses its authenticated Saved predecessor to
verify every newly appended event and the full successor, falling back to the
original full replay if any prefix/source identity differs.

58 focused tests and 15 original Tour integration regressions pass, including concurrent corrupted-source rejection,
independent response payloads, mapping-order reuse, actual HTTP Save rollback,
one post-commit source fold, real live-week suffix reuse and rehashed forged
successor rejection, historical restore/fork
and original hash compatibility. Required final-head browser/API/CI checks
remain pending; this is not a merge-ready or pre-alpha release claim.

Follow-up on `fd8dbb41`: 12/14 workflows passed, including Native Tour API
(about 14 minutes), Shell and W52/W61 browsers. W80 completed all sporting
operations but hit the unchanged 18-minute outer bound during final evidence.
Further repair dispatches checkpoint events by their disjoint required shape
instead of repeatedly validating large logs through every union alternative;
default version omission and all selected-model validators remain supported.
Tour reads also avoid two repeated checkpoint hashes and reuse an authenticated
played root only after hashing actual live values and checking all row identities.
The Server Tasks browser released its next writer before awaiting the pause HTTP
commit, racing/starving the control writer. It now requires its real ACK first.
These follow-up changes still require final-head CI/browser verification.

The subsequent W61 browser also exposed an initial-read race after restart:
StrictMode's superseded effect could overwrite the current view and clear a
new command's busy state. A deterministic frontend regression reproduces it.
Effect cleanup now aborts that fetch and ignores all superseded callbacks.
The browser correlates follow-up reads with requests issued after the actual
write ACK, retaining its response timeout and unsaved/identity/hash assertions.
The real local Server Tasks browser passed pause, page close, SIGKILL, explicit
recovery and uninterrupted equivalence. New final-head checks remain required.

# Current implementation — Master v85

Current integration base verified 18 October 2026: `buuk`
`44c782870391d45d39b05cf00fa1edd6e938e6a6`, owner-merged #1540.
The earlier audits below remain historical evidence, not the current branch tip.

**Candidate in implementation:** configured native Edition → production Entry →
approved field/draw → actual 57-backed MatchEngine → frozen Edition points →
atomic native Week Transition/lifecycle/Official ranking, with separate manual
Save and CS/EN Admin. See [authority and scope contract](docs/CALENDAR_CONFIGURED_TOUR_V1.md).
Final API/browser/recovery/performance checks are pending; this candidate is not
merge-ready or a complete pre-alpha release. Existing match-fork, Season Transition,
numeric Health, intake-source and external correction/discipline guards remain.

Audit base: buuk `4df7580c5548fbb27b0f7ee1a28ce6b3af5f71bd`, after owner-merged #1539, 18 October 2026.
#1533–1539 are merged. The current repair follows a code/CI review of all seven PRs.
Earlier in-progress paragraphs below are chronological history; this audit supersedes their status.
See [review and regression scope](docs/NATIVE_PR_AUDIT_2026_10_18.md).
Master remains v85; this task changes sporting execution, not product decisions.

**Merged and usable:** calendar creation/first Save, population and Health facts,
all-Branch horizon extension (#1508), Saved Home readiness (#1509), calendar-aware
ranking math/staging (#1510–1519). A84-01 fixed in #1521 (both ranking modules green).
#1522–1525 add actual opening-week exhibition or four-player knockout, real
MatchEngine logs, manual immutable Save, exact replay/restart/restore, reviewed
operator-authored points with a second Save, and a hypothetical as-of one-event
scoreboard with W-week expiry. Real W52 1,000-player Chromium acceptance passed.

**Hard limits:** one native opening knockout establishes each Branch sporting owner;
Saved continuations, sporting-only weekly development, later four/eight-player
knockouts, prepared awards and native result closure now follow that owner.
Population source generation retains provisional seven-value calibration; numeric
Health effects and complete historical development remain incomplete.
Prepared points and hypothetical future eligibility are not Official publication
or an advanced clock. Population-only is not proven Tour entry. Match-containing
fork remains blocked. Legacy W61 sporting guards remain on unsupported calendars,
including extended reference horizons; no false Full Simulation unlock.

**Merged v85 fixes (#1526):**
- A85-01: include the new Saved native match component in extension live capture,
  enabling review/Save after native sport while preserving exact historical bytes.
- A85-02: exact original knockout command retry works after scoring/Save/extension;
  it returns its original receipt without replaying or overwriting points.
- A85-03: reviewed point policy and consent cannot survive source HEAD changes;
  late responses, including A→B→A, are ignored.
- A85-04: Home recognizes actual Saved native sporting history, without inventing
  a Week Transition or Official Ranking.
- A85-05: existing Shell browser gate covers native services/panels/helper paths;
  its acceptance now includes all-Branch extension after the real scored knockout.

**Evidence:** [v85 audit](docs/PRE_ALPHA_CHECKPOINT_V85_2026_10_17.md) contains
exact final-head CI for #1521–1525 and local tests. Base audit 53 backend tests
passed; new real HTTP/SQLite module 4 passed; frontend source-change/Home tests
6 passed and production build passed. Final PR checks must be green before handoff.
No full release or realism acceptance is implied.

**New product targets:** personal milestones/career timeline, retirement summary,
followed-player notifications, automatic domestic leaders and important national/
exceptional individual successes, grouped notifications, season summary with
compact/detail national comparisons and previous/arbitrary-season comparison.
Summaries do not themselves pause simulation. See Master 21.5/25.6.1/27.25/31.40.
Thresholds/layout/calibration and deferred initial-rule inheritance remain open.

**Merged #1527:** new four-player knockouts use `calendar_opening_knockout.v2`.
Both semifinals consume one frozen fresh operation baseline. Actual rally/timeline/
stamina evidence changes form, sharpness and long-term fatigue; the final consumes
post-semifinal state, and the embedded terminal checkpoint retains all four players.
Save/points/extension/restore/restart carry this state under the existing immutable
component. Admin CS/EN shows all three stages. Historical v1 JSON/hash/replay retain
their original unchanged-input semantics. See
[contract and verification](docs/CALENDAR_KNOCKOUT_SPORTING_STATE_V1.md).
This is operation-owned state, **not** a full canonical 57-attribute/Health week
owner. Seven-value attributes, fresh initial baseline and no between-round recovery
remain explicit. No native calendar advance, Tour entry or Official publication.

**Merged #1528:** a fully Saved calendar Health baseline/edited state no longer
blocks the knockout. Health-backed play uses explicit `calendar_opening_knockout.v3`,
freezing four participant Health profiles and source identity. Each actual match
receives its participant-ordered `EffectiveMatchHealthSnapshot`; a v2 log anchor
binds these facts to real rally evidence. Replay uses frozen facts even after later
medical corrections. Points/Save/extension/restore share this validated authority.
Admin shows current readiness, limitation warnings and original played facts in CS/EN.
Unsaved/missing/drifting/legacy Health still blocks. No automatic Health mutation or
numeric injury penalty is invented; standalone exhibition retains its old guard.
Historical v1/v2 bytes and semantics remain unchanged. See
[implementation contract](docs/CALENDAR_KNOCKOUT_HEALTH_V1.md).

**Merged #1529:** new knockout writes use `calendar_opening_knockout.v4`.
Four operation-owned `PlayerSportingRecord` inputs preserve all 57 attributes,
potential provenance and an explicit existing provisional bootstrap policy.
Every actual MatchEngine call consumes the existing versioned 57→engine projection;
full per-player projections are frozen into a new v3 log anchor. Finalists consume
post-semifinal form/load while their canonical attributes remain unchanged.
Admin can preview the four exact sources read-only before play and inspect the
frozen 57 values after Save/reload. v1/v2/v3 JSON/hash/replay remain intact.
[Contract](docs/CALENDAR_CANONICAL_KNOCKOUT_V1.md) explains scope and verification.
The initial pool still originates in seven-value calibration; this is a real
57-backed match-input slice, **not** full world/week sporting ownership, historical
cohort development, a native 57-dimensional rally formula or annual advancement.

**Merged #1530:** new knockout writes use explicit v5 and atomically create
`calendar_sporting_checkpoint.v1`, a Run/Branch-owned native checkpoint containing
all population players and all 57 attributes. Actual entrants retain terminal
form/load; nonparticipants retain exact provisional bootstrap records. One manual
Save and immutable hash cover both match evidence and the population owner.
Saved validation, restore/restart and horizon capture authenticate the coupled
components; historical v1–v4 remain unchanged and are not retroactively upgraded.
Admin CS/EN can inspect any stored record, including players outside the draw.
See [contract](docs/CALENDAR_POPULATION_SPORTING_CHECKPOINT_V1.md).
This is real persisted population ownership, but still one opening operation per
Branch: it does not itself implement a second event, development or an advanced week.

**Merged #1531:** actual sequential opening-week exhibitions consume the
Saved native full-population 57-attribute/form/load checkpoint. Explicit v2 stores
an ordered match ledger and current population, with existing match effects applied
to only two participants. Each new match requires Save of its predecessor; exact
retries, independent manual Save, replay, restore/restart, Health and compatible
horizon extension retain authority. CS/EN Admin supports play/Save/history/replay.
See [contract](docs/CALENDAR_STATEFUL_CONTINUATION_V1.md). This removes the blanket
one-operation limit for these bounded sequential exhibitions, not for additional
Tour tournaments or weekly progression. No recovery/development/ageing or points
are introduced; frozen v1–v5 tournament and v1 population bytes remain intact.

**Next:** native weekly ownership/development and actual Week/Season Transition
from the played terminal checkpoint; add historically configured points,
Tour entry, Official publication and real Week/Season transitions/Full Simulation.
Preserve historical schemas/hashes and manual Save; do not weaken guards or create
another sequence of read-only candidate wrappers. Complete pre-alpha scope and
reference 50-season acceptance remain in Master; never mutate protected sources.

Owner alone merges. Work directly in the continuation ChatGPT/environment, no
paid Codex/agents unless explicitly requested. Avoid concurrent duplicate work.

**Merged #1532:** native sporting-week preparation advances the explicit
exhibition sporting owner from completed terminal records, with annual attribute
exposure 1/W and existing weekly Form/sharpness/fatigue updates. Reviewed preview,
explicit consent and separate manual Save precede actual later-week exhibitions
from those stored 57 attributes. Ordered v3 owner history retains old hashes and
supports replay/restart/restore/extension. This does not advance the legacy/public
clock or implement Official Ranking, lifecycle/intake, Health healing, Season
Transition or full nine-step Week Transition. The end of season remains blocked.
See [scope and validation](docs/CALENDAR_NATIVE_SPORTING_WEEK_V1.md). Final-head CI and actual 1,000-player Chromium acceptance passed on #1532
(9d2d6a9a3b802999597b32fff4677d504ec25afb). This does not satisfy the
full pre-alpha release gate.

**Next focused performance repair (pending PR verification):** manual Save and several
Save reviews currently call the same authoritative branch lineage validation twice
inside a single SQLite transaction. Reusing the already validated Saved HEAD in
those specific transactions avoids duplicate traversal without weakening raw-byte
hash, component, scope, lineage, draft, or concurrent-writer checks. Verification
must still run afresh on every distinct request/transaction; no public history
validation or persisted revision semantics are changed. This is a bounded
performance reduction, not a claimed end-to-end latency fix or Tour integration.


**Merged #1533–1534 (verified 18 October 2026):** #1533 removes a
duplicate Saved ancestry walk within eligible Save/review transactions
without weakening per-transaction validation. #1534 adds actual later-week
four-player exhibition knockouts on the Saved v4 sporting owner: three
MatchEngine matches execute atomically, the final consumes semifinal state,
and all three retain replay, immutable Saved history, restart/restore,
exact retry and horizon-extension compatibility. These events are explicitly
**not** configured Tour Editions, Official points, public Week Transition
or Official Ranking. No open PR existed at this checkpoint before the
current integrity change.

**In-progress correctness gate after #1534:** validate a logged match's
top-level winner against signed played-set tallies (with proper retirement
semantics). Later-week bracket wiring alone is insufficient to authenticate
a fabricated standalone final result or future Official award. Add targeted
tamper and unchanged-result tests; do not change stored hash/serialization
or pretend that the full Tour publication bridge is complete.


**Merged #1535:** logged MatchEngine results now reject a declared winner
contradicting their real scored sets; retirements require the non-retired
player to win. Three focused PR-critical tampering regressions and final CI
are green. This protects subsequent bracket placements without changing
historical match serialization.

**In-progress next PR:** a separate explicit scored native later-week
knockout command derives four *prepared*, not Official, point awards
from three actual MatchEngine results. V2 sporting tournament event + v5
population checkpoint keep older v1/v2/v3/v4 bytes untouched. W-valid
operator-authored policy is saved and replayable with the same manually
Saved owner; UI has independent CS/EN point confirmation and history.
The real configured Tour Edition/Entry and Official publication remain
next, not implicitly unlocked by prepared scoring. See
`docs/CALENDAR_FOLLOWUP_PREPARED_POINTS_V1.md`.


**Merged #1536, merge verified on 18 October 2026:** explicit operator-prepared
scores for real *four-player* later-week knockouts use v2 tournament events
and v5 full-population checkpoints, with independent confirmation, replay
and manual immutable Save. They remain not Official Ranking; the owner
chose to defer the aggregate post-merge test review. The latest verified
buuk merge SHA at next-task start was `28365c3f98cdc6401ea6067d50a1daec94664444`.

**In-progress native eight-player tournament slice:** new `calendar_followup_knockout.v3`
adds one atomically played seven-match tournament (four qfs/two sfs/final)
from the Saved 57-attribute population and exact player states.
`calendar_sporting_checkpoint.v6` retains full history and weekly recovery;
all older event/checkpoint schema bytes and sources remain immutable.
Separate Run/Branch API, CS/EN eight-draw Admin, explicit seven-match consent,
Saved history/replay/restart/restore and W52/W80 tests are included.
Scoring is intentionally unavailable for eight-player exhibitions;
configured Tour Entry, Official Ranking and full Week/Season Transition
remain unimplemented. See `docs/CALENDAR_FOLLOWUP_EIGHT_KNOCKOUT_V1.md`.


**Merged #1537 (checked 18 Oct 2026):** seven genuine winner-fed
MatchEngine matches from the Saved W52/W80 sporting owner now form an
eight-player native later-week knockout, with an explicit v3 event / v6
checkpoint, complete replay/restore and manual Save. Nine final-head
workflow checks were green before the owner merged it into `buuk`.

**Under construction:** a *separate* confirmed eight-player prepared
point award operation, deriving 8 canonical player awards across
champion/finalist/semifinal/quarterfinal from the actual played
v3-style bracket. This writes v4 scored tournament/v7 Saved sporting
checkpoint, retaining historical v1–v6 JSON/hash semantics and existing
four-player scoring unchanged. Independent CS/EN confirmation, point
table and signed result history are included. No Official Tour Entry,
ranking publication or complete Week/Season Transition is claimed.
See `docs/CALENDAR_EIGHT_PREPARED_AWARDS_V1.md`.


**After owner-merged #1538 (verified on 18 Oct 2026):** genuine
seven-MatchEngine-game native eight-player knockout now supports four
winner-fed finishing stages and exactly eight review-confirmed prepared
award records, with immutable sporting checkpoint v7 and all earlier
v1–v6 semantics preserved. Its frontend build passed; some final-head
backend and browser workflow checks were still outstanding when the owner
merged.

**Merged #1539 native result closure (CI reviewed separately below):** a *new Saved sporting write*
freezes per-player played-match IDs, win/loss counters, placement and existing
prepared points from the actual seven logged MatchEngine results into
`calendar_native_tournament_closure.v1`, backed by sporting checkpoint v8.
Distinct explicit confirmation and manual Save, SQLite atomicity, exact
retry/restart/restore, later W-aware advances, tamper checks and CS/EN Admin
are included. This closes genuine native sporting result evidence, but is
NOT yet a configured Tour Edition/Entry, published Official Ranking or full
Week/Season Transition. Contract:
`docs/CALENDAR_NATIVE_SAVED_RESULT_CLOSURE_V1.md`.


**Post-merge audit repair (#1533–1539):** restore closure events at their original
boundaries when reconstructing an exact standalone-match retry. Reserve closure
command identities in both continuation/tournament reducers and reject generated
nested-command collisions before playing. Check W-valid point policy before
expensive MatchEngine work. Client inspection/receipts derive all four/eight-player
placements from actual winner-fed draws, and the closure UI respects the backend's
latest-event/current-week restriction. Historical schema bytes and sporting scope
are unchanged.

#1538 Fast CI actually failed on a 120-second HTTP timeout at the final W52
Saved restore (job 117676449651), despite eight green browser workflows. #1539
contains performance changes but its changed-test selection does not rerun that
#1538 module. The audit therefore runs both affected real W52/W80 API modules
explicitly; final repair-head CI must finish green before handoff. Existing browser
smokes do not exercise the new four/eight-player/closure UI end to end.

The extended repair regression subsequently exposed a >120-second first read
after restart with the longer post-closure match history. Scoped profiling found
eight identical full-tournament hashes per award derivation and a duplicate Saved
checkpoint fold inside continuation context. These are now computed/validated
once within the same operation; no cross-request cache or integrity bypass is
added. Profiled cold inspection of the same copied nine-revision history fell
from 130.96s to 74.34s. New focused regressions preserve four/eight-player award
facts and fail-closed malformed Saved validation; final-head real regressions
remain the handoff gate. See the audit for evidence and scope.


Shell performance follow-up: its real population fixture now defaults to 64,
with all existing scenario assertions parameterized. The separate 1,000-player
cohort and native W80/1,000-player gates remain unchanged. Internal checkpoint
Shell scale is explicitly available via `--population-size 1000`; a 64-player
Shell pass is not represented as a large-population pass.
