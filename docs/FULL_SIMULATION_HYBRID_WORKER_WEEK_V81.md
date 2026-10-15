# Native Full Simulation worker executes genuine hybrid Week Transition — acceptance

PR #1481, 15 October 2026. Separate Chromium/SQLite workflow after #1480.
The test creates an *actual* Full Simulation server task before the group Match
Days. It waits for human, and real Run Admin plays two genuine MatchEngine
group matches, freezes standings and entrants/bracket, simulates the knockout
final and explicitly freezes the ranking policy/closure.

It deliberately does **not** use the Admin manual Week Transition surface.
After human-reviewed Ranking Transition Authority, the operator idempotently
chooses Week 2 as the original task's target and explicitly resumes the same
Task ID in the real English Task Center. The original server worker must
perform audited Next Season → Next Week → authoritative Week Transition.
Assertions check task `target_reached`, exact Week-2 current Position,
world/authoritative week transition followed by a separately Saved public Official Ranking fingerprint matching the *independently reviewed* derived transition, exactly three unchanged MatchEngine receipts, preserved
historic Week 1, public Viewer remaining at frozen Week 1 until an explicit Admin Save then one new Week-2 publication, and unchanged Saved Revision before that deliberate separate Save. The existing hybrid browser journey
then independently checks real ranking points, immutable historical Edition
and SQLite process restart.

One single terminal task run does not prove self-sufficient 50-season
progression or automatic approval of future group decisions; those remain
manual by the product contract. The workflow is not green until all browser,
backend and actual worker transition assertions pass on final HEAD.
