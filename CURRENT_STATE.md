# Current implementation — Master v85

Audited buuk `1fe5cb9080cd8cc84bd1002c393f720951020f0f` after merged #1525, 17 October 2026.
#1520–1525 are merged; no open PR at audit. Refresh before new work.
The v85 candidate contains new product canon plus the fixes below, not a release.

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

**Current v85 fixes (candidate until owner merge):**
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

**Next:** implement true calendar-native canonical sporting/Health checkpoint
ownership and full attribute projection, then historically configured points,
Tour entry, Official publication and real Week/Season transitions/Full Simulation.
Preserve historical schemas/hashes and manual Save; do not weaken guards or create
another sequence of read-only candidate wrappers. Complete pre-alpha scope and
reference 50-season acceptance remain in Master; never mutate protected sources.

Owner alone merges. Work directly in the continuation ChatGPT/environment, no
paid Codex/agents unless explicitly requested. Avoid concurrent duplicate work.
