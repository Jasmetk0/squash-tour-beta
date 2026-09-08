# Official Ranking calculation V1

Master v63, chapters 18.1–18.3, defines the contract for this pure calculation
kernel in `domain/rankings/official.py`. It is separate from the legacy
`RankingRaceEngine` and active-player-total snapshot foundation. Existing APIs
are unchanged; this is not yet an end-to-end Week Transition implementation.

## Inputs and behavior

- The caller supplies one Run/Branch scope, a target Season Week, the historically
  effective policy, player lifecycle state, and resolved authoritative results.
- The first Official season defaults to Best 15. `propose_next_season_policy`
  inherits the supplied previous effective Best N unless explicitly overridden.
  It does not cascade later edits through future season plans.
- Each Edition/player has exactly one result with final qualification and main
  components. Their sum consumes one Best N place. This kernel does not derive
  those stage values, BYE unlocks, W/O handling or abandonment awards from matches.
- Only completed or formally abandoned results are accepted. First publication
  must follow completion. Eligibility uses the explicit first-publication week;
  validity is inclusive there and exclusive at first publication + validity.
  The default is 61 weeks, with an explicit per-result override.
- Unranked results are excluded. Retired players and pre-Tour/current-week
  entrants are not classified. Existing Tour players with zero points remain.
- Order uses total points, descending counted point profile, newer completion
  profile, previous Official position, then a unique persisted token. Zero-point
  players use previous position/token. All positions are unique. Technical input
  order and player ability never decide an otherwise tied position.
- The immediately preceding snapshot must share the Run/Branch scope. Its hash
  is linked into the candidate. With no previous snapshot, the caller must be
  performing an explicit bootstrap; the calculator cannot verify stored history.
- Models are frozen and collection fields are tuples. Candidate hashes include
  scope, target week, policy, provenance and resolved output; reordered input
  tuples produce identical hashes. Loading stored JSON does not rerun simulation.

## Integration boundary

These are calculated candidates, not published snapshots. The transition service
must resolve historical knowledge, actual first publication, corrections, Ranked
status and lifecycle before calling; validate source provenance; and commit the
entire transition and its candidate atomically. In particular, a later correction
must retain the result's original first-publication boundary, not restart expiry.

Persisted token assignment, branch-fork ancestry, discipline/mandatory zeros,
Protected Ranking, Race, Season Closing Ranking, API/UI wiring and migration of
legacy active-player totals are not implemented by this kernel. It must not yet
replace the complete production ranking path. Disciplined scenarios require the
dedicated discipline extension before using this calculation as authoritative.

The V1 age comparison follows the counted results sorted by points, then newest
completion, with Edition identity only stabilizing selection among equivalent
results of the same player. Numeric Best N validation is positive integer without
an invented upper product limit; further Admin policy validation remains separate.

## Verification

Domain tests cover deferred eligibility, delayed initial publication, expiry,
Week 61 rollover, Best N and inheritance, additive Q/main components, Unranked and
Abandoned inputs, lifecycle, each tie-break level, unique ranks, order independence,
immutable history/JSON reload, distinct unchanged weekly snapshots and invalid
identity, timing and status inputs. These are domain tests, not integration tests.
