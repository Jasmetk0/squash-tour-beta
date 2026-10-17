# Actual calendar knockout state — implementation contract

Base: `buuk` `5ff872c5aa718d125dda92617e93f30c53b089b2`, after owner merge #1526.
Master stays v85. No open PR at task start. This branch is a candidate until merge.

## New usable behavior

New opening-week four-player knockouts use `calendar_opening_knockout.v2` and
`calendar_knockout_sporting.v1`, under the existing match component/SQLite row.
Both semifinals read exactly one frozen operation baseline. Only after both
complete are their disjoint effects installed. Finalists then use the actual
post-semifinal form, match sharpness and long-term fatigue as MatchEngine inputs.
The terminal checkpoint retains winners and eliminated players; eliminated players
receive no final load. Actual rally points versus expectation update form; logged
duration and participant workload update sharpness/load. This reuses the existing
provisional kernel, with its original coefficients, bounds and rounding.

All three checkpoints, six player effects, exact input/result/checkpoint hashes
and effective policy are owned by the played operation. The parser rebuilds the
checkpoints from frozen inputs and played logs; a rehashed but inconsistent delta,
foreign roster, stale final input or unknown calibration is rejected. No implicit
recovery occurs between slots. This is long-term fatigue, distinct from the three
within-match stamina bars.

Manual Save, reviewed points/second Save, Run-wide horizon extension, historical
restore and restart retain the same complete component. Exact command retry returns
the original evidence without applying effects again. Restoring pre-match content
removes the entire operation; restoring the match reinstates its exact checkpoints.
There is no second mutable store that could diverge from the signed match.

Admin shows initial/post-semifinal/terminal values in CS/EN, explains the provisional
baseline before playing, and preserves consent/Save/replay controls. The existing
real Chromium gate checks final input fatigue, the visible table, manual Save,
reload, scoring, extension and replay. Its paths now include the new domain kernel.

## Compatibility and boundaries

Historical `calendar_opening_knockout.v1` keeps its original JSON (no new optional
field), hash, unchanged finalist inputs and replay semantics. A frozen real-engine
v1 fixture is accepted identically by both the original merged v85 parser and the
new parser. The existing scored outer schema authenticates either explicitly
versioned nested knockout; point calculations and publication boundaries do not
change. Unknown/new sporting data cannot be attached to a v1 knockout.

The v2 population still contains seven compatibility attributes. This task does
**not** manufacture canonical 57-attribute history or annual development. Its
fresh operation baseline is explicit: form 100, sharpness 100, fatigue 0, under
`calendar-knockout-state.provisional.v1`. Policy and projection snapshots freeze
all provisional calibration; altered values require a new supported policy version.

Existing Health/legacy sporting guards remain. There is no healing, numeric injury
penalty, injury generation, between-round recovery, actual Tour entry, Official
publication, Week/Season Transition or Full Simulation unlock. Standalone exhibition
retains its original v1 behavior. Native match-containing cross-Branch fork stays
blocked until a proper remap exists. This is a usable round-to-round state slice,
not complete canonical sporting/Health ownership or a pre-alpha release.

## Verification

- Deterministic domain checks cover semifinal execution-order independence,
  separate slot fingerprints, six effects, duplicate participants, semantic
  corruption even after rehash, and historical v1 JSON/hash/engine replay.
- Real FastAPI/SQLite W52/W80 checks cover actual MatchEngine play and final
  state consumption, both manual Saves, prepared points, signed expiry,
  all-Branch extension, cold restart and backward/forward historical restore.
- Existing legacy slot-effect tests cover frozen inputs/order independence,
  semifinal-to-final state and completed-week development after extracting the
  shared calendar-independent arithmetic. Legacy temporal keys are unchanged.
- Frontend response-boundary tests reject missing/foreign/out-of-range state;
  component consent regressions and TypeScript/Vite build are required.
- Final-head GitHub checks, including real Chromium, must be green before handoff.
  Mocks are not browser evidence. Focused checks are not a full release regression.

Local focused checks: 15 domain/compatibility tests and 3 directly affected legacy
slot-effect tests passed; 10 frontend tests and TypeScript/Vite production build
passed. Historical legacy effect JSON and fingerprints were also compared directly
with the original merged function for three real-engine fixture matches, unchanged.
Full production integration and final-head CI results are recorded in the PR body
when completed, to avoid changing an already tested HEAD only for CI metadata.
