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

### Stored snapshot integrity

Rows validate player ownership, unique Edition results and their point sum.
Snapshots validate unique players, contiguous ordered ranks, descending totals,
Best N capacity, canonical counted profiles and eligibility at the stored week.
Fingerprint references must be lowercase SHA-256 strings. Previous snapshots
are revalidated before calculation, including objects created using unchecked
`model_copy(update=...)`.

`load_official_ranking_snapshot` additionally checks the requested Run/Branch/week
and an independently trusted expected fingerprint, without recomputing ranking.
Rehashing a malformed point sum does not bypass structural validation. A valid
but altered payload fails against the trusted fingerprint. This is integrity
checking, not authentication: an attacker controlling both payload and trusted
metadata cannot be detected by a plain hash.

These checks preserve valid V1 serialization/fingerprints and add no sport rules.
They cannot prove that omitted source results were included, that the supplied
player lifecycle was true, or that tie-break tokens were correctly assigned:
those require the full source inputs and trusted publication service. This
increment does not publish a ranking, advance a week or mutate persistence.

Domain tests cover deferred eligibility, delayed initial publication, expiry,
Week 61 rollover, Best N and inheritance, additive Q/main components, Unranked and
Abandoned inputs, lifecycle, each tie-break level, unique ranks, order independence,
immutable history/JSON reload, distinct unchanged weekly snapshots and invalid
identity, timing and status inputs. These are domain tests, not integration tests.

## Historical tie explanations

`explain_ranking_ties` reports the first deciding layer between adjacent players
with equal totals. It first reconstructs the candidate from its complete stored
manifest and predecessor. Calculation and explanation share `ranking_order_key`;
this refactor preserves existing calculation output and fingerprints.

Evidence identifies both players/ranks, total points, the deciding layer and values.
Result profile and completion-age comparisons include the one-based counted-result
slot. Completion values are absolute zero-based week ordinals (rendered as Season
Week in Admin); absent previous rank/completion is null. Zero-point comparisons
still skip completion age. Missing classifications never become invented ranks.
No tie explanation is emitted for different totals. Adjacent comparisons describe
the existing order, not all possible pairs inside a tied group.

The Admin stored-inputs response includes these explanations for complete manifests,
and its UI renders the first deciding criterion and evidence. Legacy candidates
without complete inputs retain their explicit unavailable state. No active player
records, current policy or live tokens substitute for historical inputs. Inspection
is read-only and neither publishes candidates nor advances time. This feature does
not complete discipline, PR, season closing or the Week Transition publication path.
