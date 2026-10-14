# Explicit hybrid groups + knockout Admin configuration — 14 October 2026

## What the operator can now do

In the verified, writable Run → Tour → Tournament Event with a frozen
ranking-application Entry Field and before any Draw/Format authority, select
**Groups + knockout** in addition to the previously supported pure groups.
Adopt effective Season Group Rules (BO3/BO5), provide equally sized groups,
choose the number advancing per group, and explicitly assign every advancing
`(group number, achieved group position)` once to a first-round knockout
match. No seed placement or crossing is invented from player IDs, rankings
or previous player results.

Validation prohibits incomplete/reused group positions, over-capacity fields,
odd or non-power-of-two knockout sizes, Qualification/BYEs, and unauthorized
Run/Branch/Event. Confirmation is bound to the exact reviewed inputs and is
revoked when group structure or any crossing changes. The full submitted
crossing list is compared with the canonical frozen backend response before
the UI treats it as accepted. Post-configuration, existing frozen Topology and
Group Match Schedule generation controls stay available; actual completed
Group Standings become visible through the same production Admin component.

## Boundaries

The backend has hybrid Entrants, Bracket, Point Policy and Closure services,
but this PR does **not** implement their complete Admin UI orchestration,
a completed hybrid sporting browser match, a saved hybrid Edition, historical
ranking replay or fork-remap. The operator must not interpret configured
crossing positions as known match winners. Backend rejects incomplete
authority. No production RNG or sporting formulas change. Follow-up integration
is the actual group simulation -> frozen standings -> entrants -> knockout
bracket -> actual knockout Match-Day -> Result/Ranking closure -> Save/SQLite
restart acceptance.

Tests: deterministic payload and validation checks; editable Admin controls
and explicit confirmation; frontend build/critical tests on final HEAD.
