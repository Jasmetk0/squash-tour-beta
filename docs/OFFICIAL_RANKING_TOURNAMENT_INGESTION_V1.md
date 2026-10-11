# Tournament awards to Official Ranking sources V1

The internal `ingest_tournament_ranking_sources` application function reads the
persisted result and award packages through `SeasonPointAwardsService` and its
result service, validates the complete batch, then appends one initial ranking
source per player through the transactional source store from #694.

Supported input is an ordinary completed ranked main draw without qualification,
BYE, W/O or RET. The existing legacy package exposes one stage award rather than
independent Q/main components, so this adapter refuses those richer cases instead
of inventing missing components. Abandoned/Unranked ingestion and corrections are
separate follow-ups. Existing kernel capabilities remain unchanged.

The caller must supply a trusted `TournamentRankingBinding`: Run/Branch, Edition,
legacy event identity, actual completion week, actual first-publication week,
validity and expected result/award build fingerprints. These are mandatory because
legacy JSON packages lack product scope and actual publication history. This
binding is an internal trust boundary, not an externally authenticated request.
The caller must establish scope and capture expected hashes independently of
untrusted input; hashing the same untrusted bytes cannot establish authority.

Validation checks persisted/non-preview status, errors, identities, season/week,
completion, supported result shape, match references, duplicate/missing players,
authored award source, recalculated legacy build fingerprints and player-result
provenance. It copies awarded main points, without recalculating the current
points configuration or reading mutable player totals. Source provenance binds
the import context and individual award fingerprint. Reads do not change source
JSON, player totals, previous rankings or simulation state.

The complete package is validated before any source append. All appends must be
inside a caller-owned transaction; on any append conflict the caller must roll
back the entire transaction. The adapter neither commits nor catches an error
and commits a partial batch. Identical retries use the source store's exact-retry
semantics, including after candidate calculation. JSON files themselves are not
part of the SQLite transaction. Production ingestion requires serialized source
access and a branch writer; this is not an atomic JSON/SQLite distributed commit.

Tests use a synthetic completed bracket passed through the real result extraction
and award persistence services, then reload its packages into the real SQLite
source store and ranking calculator. They verify points, commit/reload, exact
retry, unchanged source/player bytes, invalid inputs and rollback when the last
player conflicts after earlier inserts. They do not claim to simulate a complete
season or to exercise new API/Viewer publication, neither of which is introduced.

Remaining: production binding/publication resolution and scheduler wiring,
qualification and exceptional award adapters, corrections ingestion, historical
roster/token/policy resolution, discipline, revision/fork integration and full
Week/Season Transition publication. Master and realism are unchanged.
