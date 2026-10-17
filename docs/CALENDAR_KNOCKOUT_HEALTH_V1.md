# Calendar knockout consumes Saved Health — implementation contract

Base `buuk`: `f7a999e1661858742b50df1dbff775ae8e49687a`, after owner merge #1527.
No open PR at task start. Master remains v85; this task adds implementation, not
new injury calibration or a pre-alpha release. Owner alone merges.

## Usable integration

Creating even a healthy calendar Health baseline previously blocked the native
knockout, point preparation and signed standings: all three reused the standalone
exhibition's blanket Health guard. This candidate gives the knockout path its own
verified authority. It accepts only an exact, fully Saved opening-week calendar
Health component, authenticated against its InitialWorld/lifecycle/Run/Branch and
live rows. Missing or drifting live state, pending edits, legacy/later Health or
other unsupported sporting ownership still blocks. Standalone exhibition keeps
its original guard. No global calendar/legacy guard is removed.

A Health-backed play writes `calendar_opening_knockout.v3`. It freezes four
participant projections, source Health schema/fingerprint/week and the existing
source Saved HEAD. Each real MatchEngine call receives the correctly ordered
`EffectiveMatchHealthSnapshot`. A new match-anchor v2 includes this snapshot;
the parser verifies both the frozen source and actual rally input anchor.
The current projection is descriptive: exact limitation arithmetic, Health Checks,
medical start/retirement decisions, healing and medical timeouts remain unsupported.
There is no hidden numeric penalty and no assertion that an injured player has
been treated realistically. Existing form/sharpness/load effects remain v2 behavior.

Playing never modifies medical records, generates an injury or heals a player.
A later explicit Health correction and Save updates current facts but leaves the
original played input intact. Manual match/points Saves, Signed as-of standings,
all-Branch horizon extension, cold restart and backward/forward restore preserve
both independent histories. Exact command retries do not replay matches or medical
facts. No actual Tour entry, Official publication or Week/Season advance is added.

## Admin and evidence

Before play, Admin shows Saved Health readiness and a warning for selected entrants
with current/permanent limitations. After play, a CS/EN table shows the facts used
then, clearly distinct from later corrected facts, and explicitly says numeric
limitation effects were not applied. Existing play confirmation and Save/review
controls remain. No new medical rules or arbitrary realism threshold is decided.

Real Chromium acceptance now forks the existing genuinely Saved 1,000-player
calendar Health state, deliberately includes a limited player, checks the warning
and frozen facts, then plays/Saves/reloads/replays/scores/extends the real knockout.
The exhibition acceptance still independently checks the original no-Health path.

## Compatibility and focused verification

- Historical v1/v2 omit the new fields from serialization. v1 frozen fixture and
  v2 JSON/hash were compared with the original merged parser; old versions cannot
  silently acquire newer Health input. No existing Saved revision is rehashed.
- Pure checks reject missing/foreign/misordered snapshots, foreign clocks,
  detached log anchors and old-schema injection. A same-input comparison confirms
  descriptive injury facts do not covertly change the numerical sporting result.
- Real HTTP/SQLite W52/W80 checks cover Saved healthy/edited facts, explicit
  warning data, real MatchEngine play, points/second Save, later correction,
  horizon extension, restart and historical removal/reinstallation of the match.
  Missing or validly rehashed but unsaved Health rows cannot bypass a clean draft.
- Frontend boundary/consent checks and TypeScript/Vite build are required. They
  are separate from the real Chromium evidence; mocks are not integration proof.
- Final-head PR workflows must all pass before handoff. Exact CI/local results
  belong in the PR body so documentation metadata does not invalidate tested HEAD.

Full canonical 57-attribute input, numerical Health simulation and durable calendar
Week/Season/Full Simulation remain further work. This delivers a previously blocked
Health-to-play-to-Save integration, not another read-only readiness wrapper.
