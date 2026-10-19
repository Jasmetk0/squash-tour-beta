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
