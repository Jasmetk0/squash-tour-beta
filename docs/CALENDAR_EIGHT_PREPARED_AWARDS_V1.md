# Native eight-player knockout: actual match-derived prepared points

Master v85 continuation after merged #1537. Distinct v4 eight-player scoring
keeps the existing v1/v2 four-player and v3 eight-player exhibition record
bytes, operation semantics and Saved fingerprints untouched.

## Executable user workflow

From a Run/Branch with a validated **Saved** calendar 57-attribute population
checkpoint in sporting Week 2 or later, Admin can choose eight distinct players,
order them in the knockout, enable prepared scoring, enter a policy
(champion/finalist/semifinal/quarterfinal) with nonincreasing nonnegative integer
points, confirm seven actual MatchEngine games, and *separately* confirm that
these are only prepared awards. The existing manual Save review remains
required after one atomic operation.

`POST /calendar-continuation/knockouts/simulate-eight-scored` accepts the
original source-bound eight-player command plus
`point_policy` (explicit `calendar_followup_point_policy.v2`, Run-W validity,
operator label/category, four stage values), and literal
`explicit_point_confirmation: true`. Wrong Saved HEAD, checkpoint, roster,
consent, W, duplicate identity and policy fail without writing.

Four quarterfinal loser IDs, two semifinal loser IDs, final loser and final
winner are obtained from the **seven actual signed nested matches**. A
canonical, player-ID-sorted set of **eight** immutable prepared award records
is saved to `calendar_followup_knockout.v4`; each record binds the actual
sporting tournament fingerprint and the reviewed policy fingerprint.
`calendar_sporting_checkpoint.v7` holds all earlier evidence, player
states and exactly that event. A v7 owner remains v7 through subsequent
sporting weeks and later tournaments. No old schema gets silently upgraded.

Same-command identical retries must return original receipts even after later
Save, restart or advancement; changed command payload/roster/policy conflicts.
An outer checkpoint rehash cannot legitimize forged stage, points, winner,
round participants or frozen source. Saved/restore/replay and corrected
lineage remain authoritative. Four-player prepared events still generate
v2/v5, eight-player unscored events v3/v6, unless the owner is already newer.

CS/EN Admin exposes the separate checkbox, four scoring fields, category,
confirmation, result breakdown and explicit **NOT Official** language.
Frontend validates all eight placings against the authentic signed bracket
and refuses incorrect 7-match progression or mutation of the scored receipt.

## Boundary

This is **not** official Tour category source, Edition, Entry, ranking release,
Race, Week Transition, real public time, Season Transition, lifecycle or
Full Simulation. No candidate/v1 points may be automatically published. It
is an operationally coherent played-results-to-prepared-awards slice,
not the end of the canonical integration.

## Acceptance targets

W52 and W80 HTTP/SQLite real 7-match v4 tournament with four QF, two SF,
one finalist and one champion award. Bad consent/policy/W must fail and
preserve database. Event and policy fingerprints must survive manual Save,
cold restart, replay of all seven matches, Week 3 recovery (14 match-player
participations), exact retry and backward/forward restore. Mutating awards,
bracket or schema even after rehash must be rejected; v1–v6 checks stay green.
Frontend CS/EN consent and history tests, fast CI, and applicable browser
workflows must be run on the last commit. Owner handles merging.
