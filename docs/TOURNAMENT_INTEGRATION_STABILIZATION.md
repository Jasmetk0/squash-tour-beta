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

## Owned Official-ranking source bridge

The supported ordinary four-player main-draw path can now be selected explicitly
in an audited Admin ranking command. Before its first database mutation, the command
validates the complete persisted result and authored award packages, identities,
completion status and both fingerprints. It then freezes an immutable, independently
Run/Branch-owned copy and prepares the next Official candidate in the same SQLite
transaction. Preview rolls this work back; exact retries use the frozen copy rather
than mutable legacy files. Saved Revision ranking components capture and restore the
copy together with result versions, manifests, receipts and candidates.

This is an explicit adoption boundary, not proof that the legacy producer itself is
Run/Branch-owned. Qualification, BYE, W/O, RET, fallback/unauthored points, future
weeks and fingerprint drift remain rejected.

## Remaining boundary

Preparing and saving a candidate is not publication of an Official Ranking. The existing legacy
apply endpoint updates active-player totals, and the existing snapshot foundation
copies those totals. This change does not implement the Master contract for
Week Transition, delayed result eligibility, rolling expiration, season-inherited
Best N, or atomic Official Ranking publication. The legacy domain report defaults
and schemas also remain unchanged. Those require a dedicated follow-up; passing
these tests must not be interpreted as full Official Run readiness.
