# Current implementation — Master v85

Audited buuk `f7a999e1661858742b50df1dbff775ae8e49687a` after merged #1527, 17 October 2026.
#1520–1527 are merged; no open PR at task start. Refresh before new work.
Master remains v85; this task changes sporting execution, not product decisions.

**Merged and usable:** calendar creation/first Save, population and Health facts,
all-Branch horizon extension (#1508), Saved Home readiness (#1509), calendar-aware
ranking math/staging (#1510–1519). A84-01 fixed in #1521 (both ranking modules green).
#1522–1525 add actual opening-week exhibition or four-player knockout, real
MatchEngine logs, manual immutable Save, exact replay/restart/restore, reviewed
operator-authored points with a second Save, and a hypothetical as-of one-event
scoreboard with W-week expiry. Real W52 1,000-player Chromium acceptance passed.

**Hard limits:** one native opening-week sporting operation per Branch. Seven-value
population compatibility projection, no full canonical sporting/Health effects.
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

**Current candidate:** a fully Saved calendar Health baseline/edited state no longer
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

**Next:** implement true calendar-native canonical sporting/Health checkpoint
ownership and full attribute projection, then historically configured points,
Tour entry, Official publication and real Week/Season transitions/Full Simulation.
Preserve historical schemas/hashes and manual Save; do not weaken guards or create
another sequence of read-only candidate wrappers. Complete pre-alpha scope and
reference 50-season acceptance remain in Master; never mutate protected sources.

Owner alone merges. Work directly in the continuation ChatGPT/environment, no
paid Codex/agents unless explicitly requested. Avoid concurrent duplicate work.
