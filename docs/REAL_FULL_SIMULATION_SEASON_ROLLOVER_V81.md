# Real Season 2000/01 → 2001/02 from one continuous Full Simulation parent

The existing authentic MatchEngine group+knockout browser journey executes Week 1,
publishes Week-2 Official Ranking, restarts SQLite, and starts a second Full Simulation
parent from the **same Saved Run** at Week 2. That unchanged nonterminal parent
automatically advances through Calendar-proven empty weeks to **Week 61** and stops
at `season_transition_save_required` (observed in successful #1483 CI artifacts).

This independent acceptance reuses the original Run, sporting receipts,
operator Task ID, immutable parent command and double SQLite restart. It
confirms Save did **not** occur implicitly. An operator explicitly selects
**Save authoritative simulation** in the production Chromium UI, verifies
the new Saved Revision and still-unadvanced world Week 61. A real derived
Season Transition preflight must be ready without implementation gaps.
Only then the operator clicks **Review Season Transition** and
**Advance to next season**, staging the canonical atomic Season Closing
Ranking, lifecycle, sporting, health, Week-1 Official Ranking, world clock,
and Saved Revision. The same existing nonterminal Full Simulation task
is then explicitly resumed from Task Center.

Proof requires at least 2001/02 Week 1 in the world, the exact unchanged
task/parent/original command, unchanged genuine three MatchEngine replays,
preserved historical Week-2 published ranking and no hidden Save. If the
next season has a genuine unreviewed Entry/Calendar requirement, a later
operator checkpoint is permitted rather than inventing sport or approval.

Critical tests reject 15 unsafe input or stale-history scenarios *before*
any Save/Season Transition occurs. A separate Chromium+SQLite workflow
runs the actual end-to-end acceptance on final PR head. Do not claim the
50-season Run is fully autonomous; crossings require operator review.
