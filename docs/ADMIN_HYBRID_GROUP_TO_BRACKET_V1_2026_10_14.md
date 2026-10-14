# Hybrid Group → Knockout — genuine advancing players and frozen bracket

**14 October 2026 — pre-alpha functional slice after merged PR #1450.**

## Newly usable from Run Admin

For an event whose **immutable format is `groups_knockout`**, the operator
first simulates all group Match Days in the existing authoritative Run Simulation
and explicitly generates the completed Group Standings (including any
operator-reviewed cyclic tie decisions).

Only after the real frozen standings exist may the next Admin section propose
**Generate frozen knockout entrants**. The operator reviews the exact group
standings fingerprint, confirms, and invokes the existing production backend.
Each first-round entrant is resolved from a configured source
`(group_index, finishing_position)` against the **final immutable Group Standings**.
There is no new seeding, no ranking/Race sorting and no guessed group winner.

The operator can then review these **actual** first-round matchups, separately
confirm **Generate frozen knockout bracket**, and inspect the entire frozen
standard winner-to-winner tree (round numbers, match IDs, participant source
IDs, and terminal final match). All read and write API responses are validated
against original Run/Branch/Event, underlying authority fingerprints,
exact player-to-group-position mapping and the canonical adjacent winner-tree
shape. Missing or corrupted evidence fails closed; absence is never displayed
as a sporting zero.

## Real production acceptance

The upgraded hybrid Chromium CI additionally:
1. Creates a real Run, four natural generated athletes, a two-group-of-two
   hybrid Format with explicit Group 1 winner vs Group 2 winner crossing.
2. Materializes an actual canonical Group Match Schedule and **plays both**
   matches in a real group Match Day through the production Simulation UI.
3. Explicitly freezes two Group Standings tables from authentic persisted
   MatchEngine receipts; no synthetic scores, fake match HTTP, or outcome overrides.
4. Browser confirms Entrants and Bracket separately; production HTTP proves
   entrant IDs match the final group winner rows, and the final first-round
   match uses those exact player IDs.
5. Explicitly Saves Simulation; verifies immutable Saved Tour group standings,
   no published/unplayed hybrid tournament result, preservation of previous
   revision, and identical SQLite authorities after full backend restart.
6. Saves screenshots, traces and structured acceptance evidence.

## Important remaining work

An immutable bracket is **not** a completed elimination: this PR does not play
the knockout Match Days, decide its winner, configure authoritative phase
ranking points, publish the Tournament Result, or apply a completed ranking
source. Next vertical slice: **real knockout Slot execution + frozen hybrid
ranking policy / closure, and Saved Edition replay**. The 50-season release
suite also remains a separate gate.

Implementation: `web/src/api/tournamentHybridKnockout.ts`,
`web/src/components/HybridKnockoutProgressionPanel.tsx`,
`scripts/real_hybrid_progression_browser_checks.py`, and
`.github/workflows/prealpha-hybrid-format-browser.yml`.
