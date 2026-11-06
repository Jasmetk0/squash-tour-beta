# FAX reference knockout geometry V1 — 2026-11-01

## Implemented structural domain boundary

Source: the existing *noncanonical* copied-FAX 80-World-Tour-Edition release fixture, not an edited tournament catalog. Existing native Tour MatchEngine supports genuine 4/8-main-only knockout; simply changing its maximum to 32 would be incorrect, because global frozen slots, feeder indexing, completed-point policy, result model, Entry and replay still use 4/8-specific contracts.

New pure `beta_engine.domain.tournaments.fax_reference_bracket_topology` uses the exact original SeasonCalendarEvent source and the **existing canonical TournamentDrawNode builder**. It provides a versioned, source-hash-bound unassigned topology for Gold/Platinum Main and their four actual Qualification sections, preserving every entrance place, WC, Q placeholder and BYE count. It does NOT assign players or seed positions, run Draw/Entry/MatchEngine, award points, Save, modify FAX source or declare release acceptance.

| Authentic reference input | GOLD | PLATINUM |
| --- | ---: | ---: |
| Original Main entrants | 24 | 32 |
| Main bracket positions | 32 | 32 |
| Main BYEs, not yet placed | 8 | 0 |
| Direct Main positions (excluding 2 WC + 4 qualifiers) | 18 | 26 |
| Wild-card placeholders requiring an owned decision | 2 | 2 |
| Qualification winner placeholders Q1–Q4 | 4 | 4 |
| Original Qualification players | 16 | 24 |
| Q sections / original entrants per section | 4 × 4 | 4 × 6 |
| Q positions per section | 4 | 8 |
| Unplaced Q BYEs per section | 0 | 2 |
| Main actual matches if *fully played* | 23 | 31 |
| Q actual matches if *fully played* | 12 | 20 |
| **Total future actually required MatchEngine games** | **35** | **51** |

Note: canonical full binary bracket node count is larger than the future genuine played match count when BYEs exist. A node with a BYE does **not** authorize simulation of a fabricated match; exact BYE placements and promoted feeder winners must come from later player-/seed-aware Draw and continuation authorities. This module does not choose their order.

## All 80 source Editions

The read-only command below builds the original 80 World Tour Editions from existing Tournament Templates and Season Category Points preview, verifies their single actual source Calendar fingerprint, runs the pure topology builder for each Edition and emits an exact JSON engineering report:

```bash
python -m tools.preview_fax_reference_brackets --output fax-bracket-geometry.json
```

By unchanged source construction, 40 Gold + 40 Platinum events would require **3,440 genuinely played matches** (40 × 35 + 40 × 51) for the 80 full qualification+main tournaments, assuming no RET/W/O/DQ and exactly the current source geometries. This is a deterministic *plan count*, not execution evidence or any prediction of actual runtime; it excludes other FAX Events, lower Tours and Finals.

Across those 80 Editions, the actual source has 2,240 original Main entrant places, 1,600 Qualification entrant places, 320 unresolved Q winner placeholders, 320 Main BYEs and 320 Qualification BYEs. The Q winner links are obligations and do **not** duplicate players or manufacture 320 new player identities.

## Strong negative guarantees

- No overwrite of calendar/packages/Category points/Saved World; the CLI only writes the requested report. Every topology carries original source Calendar, original source Edition and original Template identity; re-serializing checks model validity.
- Original Main 24 does not become 32 real entrants. Real Q section 6 becomes capacity 8 with **2 unplaced BYEs**, not 8 imaginary entrants.
- Duplicate or foreign source identity, missing versioned Calendar fingerprint, inconsistent BYEs, nondivisible Qualification, too many WCs or unbalanced Main/Q links fail closed.
- Source-specific point stages and the W1–W3 preannouncement policy remain **unresolved**. This code does not choose new sporting/Entry rules and does not automatically rewrite 24-player FAX Gold into a native 4/8 tournament.
- Existing global-slot `FrozenSlotMatch` indices (0..6), native `ROUNDS`, `ROUNDS_EIGHT`, `participants`, `GlobalTournamentResult` and immutable 4/8 award policies are untouched. No false claim of 24/32 executable support.

## Next code and product integration dependencies

Use the canonical field/Draw/qualification authorities to perform an exact, source-bound player-/seed-aware 24/32+Q draw with real 6→8 section BYE placement and source lineage. Version the global-slot feeder/round and match-acceptance models without changing historical v2/v3 blobs or prior seeds. Only then extend 24/32 results and independently reviewed ranking awards; build actual per-Edition qualification Entry and source-accurate timing, and run first real Gold, then Platinum, then multi-Edition FAX season. Existing #1729 owns the distinct source-vs-executor diagnostic and should be reviewed independently.

## Test evidence

Dedicated Draft-inclusive workflow runs real 80-Edition source topology tests and produces an exact JSON artifact; Fast CI runs marked domain critical cases. **A green topology test does not establish any played tournament**. The user alone chooses merges.
