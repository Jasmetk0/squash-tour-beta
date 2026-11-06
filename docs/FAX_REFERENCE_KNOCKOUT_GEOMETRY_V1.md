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


## Source-sized real-player initial Draw (6 November 2026 candidate)

The topology-only report remains result-free. The next layer now reuses canonical
`TournamentEntryFieldResolver`, WC authority, Draw Input and Draw stores/builders.
`fax_reference_entry_capacity(event)` binds admission capacities to the source:
Gold Main32 positions minus eight BYEs / Q16, Platinum Main32 / **Q24**, four Q
spots and two WC places. It never widens the Platinum Entry cut to 32 applicants.

Binary sections retain their historical input v2/v3 and Draw algorithms. Only
uniform non-binary Q sections select Draw Input v12 and
`padded_qualification_sections.v3`. Physical section capacity is the next power
of two; seed pools, protected BYE placement, RNG sub-seeds and canonical nodes
reuse the established Master helpers. The original Q admission count is retained
in the immutable input and its fingerprint. Historical schemas still reject
six-position brackets instead of acquiring a different meaning on replay.

`FaxReferencePlayerDrawService.inspect` reads the copied Run Calendar plus normal
authenticated initial Draw/Input stores. Its domain envelope validates full source
counts, WC/Q partition, exact initial algorithm and replay, Main/Q node topology
and section BYEs. This is a read-only projection, not another Saved component,
Entry eligibility decision or implicit Save. Edited Global sources are not read.
Edited Run Calendar entities are rejected against their applied source baseline.
The explicit `source_binding_scope=current_copied_calendar_geometry` is a current
source/Draw coherence check, not proof of a source fingerprint frozen at Draw
commit time. A newly reapplied Calendar version still needs the future execution
boundary's immutable source binding. `sporting_execution_ready` remains false.
The existing Admin Draw commit/generate API produces the new version, and the
frontend first-Draw reader recognizes its explicit algorithm.

Focused tests use the actual 80-Edition source with named test players and explicit
eligible applications/WC nominations. They cover source cut vs waiting list,
Main/Q/WC disjointness, protected BYEs, deterministic seeds, JSON replay, actual
HTTP/SQLite retry, stale command rejection, Saved component rollback/restore,
connection reopen and adversarial payloads. All 40 Gold Draw payloads were compared
byte-for-byte with the old builder at base `1800697b`; a fixed golden fingerprint
is retained. These tests do not choose production eligibility or award policy.

Next: version the native global-slot feeder/round/match-result contracts for real
Main24/32 and Q winners, then prove results, points, explicit owner Save/restart,
withdrawal/replacement and multiple Editions. Unsupported padded-Q repair paths
remain fail-closed. Do not remove the native executor Main4/8 guard as a shortcut.
The original incomplete awards and early announcement prerequisites still apply.
Neither this Draw nor its restored component proves a played season/50-season Run.


## Saved-bound node feeders (6 November 2026 candidate)

`project_canonical_draw_nodes` uses canonical node IDs as stable match IDs and
shares the existing legacy BYE/Q resolver. It needs no fabricated legacy
MatchPackage or outcome. Legacy projections retain their exact original payloads.

`SavedFaxKnockoutFeederService.prepare` authenticates the explicitly expected
current Branch-owned Saved head, then reads **saved** Calendar, Draw/Input and
clock. Unsaved live inputs, stale heads, edited adopted sources, revised Draws,
foreign scopes and unmaterialized inherited roots fail closed. Preparing a plan
never saves or starts play. Later live edits cannot retcon the returned snapshot.
`reload(plan)` reauthenticates the original source through the exact owner Branch's
reachable history after later Saves; it never substitutes the newest Calendar.
Unreachable revisions and altered serialized plans fail closed. This is preparation/
reload validation, not a new per-match full-history scan or validation bypass.
The plan binds the original Saved revision ID/content hash and source fingerprint;
these are verified by the service, not a standalone authorization signature.

`project_knockout_progress` is stateless and accepts event-only existing
`CalendarContinuationMatch` evidence. The authenticated native ledger still owns
replay, results and player-state validation. The graph checks exact owners,
source head/clock/season, seed, ordered opponents and predecessor chronology.
**All Qualification must finish before any Main match**, including direct-only
Main pairs. Q1–Q4 resolve from their actual section finals; BYEs never become
played records. Independent acceptance order gives the same readiness/champion.
Dependent rounds may not reuse their predecessor's frozen input snapshot.

New `canonical_knockout_match_seed.v1` derives from the frozen draw seed, Edition,
season and canonical node. Revision/command labels, acceptance order, horizon and
unrelated Calendar metadata do not reseed matches. Old native seed paths remain.

Tests use actual MatchEngine BO5 results/logs for Gold35 and Platinum51, one frozen
population per test wave, the existing effect reducer, and unmodified unrelated
players. Valid engine records with wrong opponents or a predecessor snapshot are
rejected, alongside duplicate/foreign/BYE/stale/seed/chronology corruption. Separate
real SQLite tests require normal explicit Save, reopen physical connections and
prove immunity to changed live Calendar/Draw rows and rejection of damaged Saved
bytes. Test players/eligibility are explicit fixtures, not automatic policy.

This is a **component/kernel and Saved-source checkpoint**, not the native public
Run executor. `readiness_scope=feeder_dependencies_only` and
`native_slot_execution_ready=false` prevent treating it as sporting permission.
Next consume it through versioned native Edition/global-slot/result models,
existing v13 ownership, operation/Health/award/schedule guards and public partial
Next Match/Save/resume/restart. No points, time progression, branch fork remapping,
withdrawal/LL mechanics, full season or 50-season acceptance is inferred here.
