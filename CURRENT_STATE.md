# Current implementation — Master v85

Audited buuk `642617430b66853285415ac6690d89165e2c47e2` after merged #1531, 18 October 2026.
#1520–1531 are merged; no open PR at task start. Refresh before new work.
Master remains v85; this task changes sporting execution, not product decisions.

**Merged and usable:** calendar creation/first Save, population and Health facts,
all-Branch horizon extension (#1508), Saved Home readiness (#1509), calendar-aware
ranking math/staging (#1510–1519). A84-01 fixed in #1521 (both ranking modules green).
#1522–1525 add actual opening-week exhibition or four-player knockout, real
MatchEngine logs, manual immutable Save, exact replay/restart/restore, reviewed
operator-authored points with a second Save, and a hypothetical as-of one-event
scoreboard with W-week expiry. Real W52 1,000-player Chromium acceptance passed.

**Hard limits:** one native opening knockout per Branch; the current candidate
adds only explicit sequential exhibitions from its Saved checkpoint. Population
source generation retains provisional seven-value calibration; numeric Health
effects and annual development are incomplete.
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

**Current candidate:** native sporting-week preparation advances the explicit
exhibition sporting owner from completed terminal records, with annual attribute
exposure 1/W and existing weekly Form/sharpness/fatigue updates. Reviewed preview,
explicit consent and separate manual Save precede actual later-week exhibitions
from those stored 57 attributes. Ordered v3 owner history retains old hashes and
supports replay/restart/restore/extension. This does not advance the legacy/public
clock or implement Official Ranking, lifecycle/intake, Health healing, Season
Transition or full nine-step Week Transition. The end of season remains blocked.
See [scope and validation](docs/CALENDAR_NATIVE_SPORTING_WEEK_V1.md). Final latest-head
CI/browser evidence belongs to the PR; do not infer release readiness from this note.
