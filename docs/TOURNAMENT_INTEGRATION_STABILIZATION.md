# Tournament integration stabilization

This change repairs point-stage compatibility and restores the API test fixtures
to the explicit Season Category Points initialization contract.

The ranking/race domain engine previously requested `winner`, `semifinalist`,
and `quarterfinalist` after the loader had normalized those keys to `champion`,
`semifinal`, and `quarterfinal`. Valid results could therefore receive zero points.
The engine now uses the canonical keys and the same pure normalizer for both
referenced and inline tables. Legacy authored names remain readable; duplicate
aliases are rejected instead of choosing one silently. The infrastructure module
re-exports the existing public names for compatibility.

API fixtures now initialize isolated season point registries with explicit test
values, including required qualification stages. Production calendar and entry
validation is unchanged. Point-award service tests assert the authored Edition
table instead of outdated fallback values.

The reference API scenario runs a four-player main draw from calendar and entries
through the real match engine, result extraction, persisted awards, reload, and
duplicate-generation rejection. It checks that player records remain unchanged.
Existing match API tests separately verify stored event Replay without RNG reruns.
The reference scenario does not cover a complete qualification/WC lifecycle.

## Remaining boundary

Persisting awards is not publication of an Official Ranking. The existing legacy
apply endpoint updates active-player totals, and the existing snapshot foundation
copies those totals. This change does not implement the Master contract for
Week Transition, delayed result eligibility, rolling expiration, season-inherited
Best N, or atomic Official Ranking publication. The legacy domain report defaults
and schemas also remain unchanged. Those require a dedicated follow-up; passing
these tests must not be interpreted as full Official Run readiness.
