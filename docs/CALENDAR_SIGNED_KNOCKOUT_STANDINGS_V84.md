# Signed calendar knockout as-of point standings (V84 follow-up)

## Scope, authority and semantics

The existing #1523 real W52/W80 three-MatchEngine-match knockout and #1524
operator-reviewed point table are **signed only after two separate explicit
manual Saved Revision commits**. This candidate adds a real FastAPI/SQLite
and CS/EN Admin read of tournament point standings over the Run-owned clock.
The read never accepts scores, winner identities, names, Tour-entry dates or
point awards supplied by the browser. Instead it authenticates within **one
SQLite read snapshot**:

- Run calendar from current verified Signed Saved HEAD;
- exactly one matching live `calendar_scored_opening_knockout.v1` result;
- the exact same scored payload in the immutable Signed Saved HEAD;
- Saved InitialWorld v2, its source population fingerprint, Saved
  `population_only` lifecycle and the precise four MatchEngine participants;
- immutable point policy fingerprint, derived champion/finalist/semifinalists,
  completed Week 1 and proposed first eligibility Week 2;
- the explicitly supplied expected Saved HEAD to reject stale callers.

No payload/source is rewritten; API is GET-only. The standalone exhibition,
unsigned original knockout and **scored-but-not-yet-Saved** live row are
deliberately rejected (409). A historical Saved restore naturally revokes
eligibility when its target predates the scored revision. SQLite tamper,
wrong Run/Branch, stale HEAD, unsupported W and bad source identity fail closed.

## Correct W-sensitive as-of expiry

For an event with completed `S1 W1` and proposed first publication `S1 W2`,
points count for exactly W weeks: all of S1 W2..W and S2 W1. In S2 W2
they expire, with **zero currently eligible points** but original signed
awards and finishing positions still visible to Admin. The exclusive
expiration `S2 W2` is represented as a symbolic calendar position even
if the saved Run has only one season; no season is actually created or
advanced. Week 1 requests and out-of-horizon queries are refused.
The snapshot fingerprint binds Saved HEAD content hash, clock, exact
as-of week, roster IDs, point values, stages and remaining blockers.

The four-player ordering is 1 champion, 2 finalist, 3= two semifinalists.
Positive point-rank ties use competition rank (1,2,3,3); expired players
have no active points rank. It is **not the entire World Tour ranking**,
and absence of an award in this one tournament must never be interpreted
as a zero-point/retirement decision about the other initial players.

## Important blockers; never promote this candidate as Official

The Saved calendar InitialWorld lifecycle is explicitly
`initialization_stage=population_only`. That does **not** prove Tour Entry,
so it would be wrong to manufacture an entry week for 1,000 players and
call the resulting calculated ranking official. Also the operator-authored
point table has not been authenticated as historically effective from
Category/Edition config, and the calendar-native Week Transition has not
run. Therefore this surface always declares:
`publication_status=not_official_no_week_transition`,
`official_ready=false`, and all three concrete missing prerequisites.

It offers a useful honest scoring view of genuine Signed outcomes today,
while the next vertical slice must implement actual Tour Entry provenance,
historically valid Category/Edition scoring and the native Week/Season
Transition before any Official Ranking/Viewer publication.

## Evidence

`tests/api/test_calendar_signed_knockout_standings_flow.py` drives
real FastAPI/SQLite for W52, W80 and a one-season horizon: full
Saved bracket+points commands, W2 eligibility, W2..S2W1 validity,
S2W2 expiry, exact as-of fingerprint, API future/stale/unsigned
protection, cold restart and prior-Saved restore, byte-true signed
predecessor and SQLite tamper.

`web/acceptance/calendar_opening_knockout_browser_check.py` extends
existing Chromium Shell: 1,000-player W52 Run, Saved result/points,
CS/EN interface, four correct point rows, S2W2 expiration and return
to S1W2 with correct points. Separate legacy Full Simulation
browser regressions remain enforced by their workflows.
