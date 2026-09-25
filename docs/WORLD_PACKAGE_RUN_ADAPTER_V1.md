# World Package → Run Adapter V1

Status: **implemented semantic adapter for World metadata/geography/countries and player-generation identity configuration**.

This adapter is the first production bridge from a global source Package into the
canonical Run Package snapshot backbone. It does not make a source Package a live
runtime dependency.

## Source boundary

`WorldPackageRunAdapter.build_document(world_id)` reads one directory-backed source
World Package through the existing registry/storage contracts and creates a
`CanonicalPackageDocument` of type `World`.

The document contains:

- one World metadata entity;
- one `world.country.v1` entity per authored country;
- the authored continents, regions and travel-region geography datasets;
- timezone-area geography when that source file exists;
- `generation/player_identity.json` when authored, validated as the canonical
  `PlayerIdentityConfig`.

The existing source registry fingerprint is preserved as provenance. The canonical
Run Package document has its own deterministic fingerprint. Source version labels such
as `v1` / `test-v1` are mapped to the positive integer version required by the
Run Package backbone; unsupported labels fail closed.

The directory-backed World Package semantic fingerprint includes the player-identity
payload when present. A source edit therefore invalidates an outstanding reviewed
source-world preview before confirm.

## Run-owned country projection

After normal Package preview/confirm, `project_countries()` derives a typed
`Country` projection exclusively from the Run/Branch-owned `RunPackageState`.

The projection:

- never opens source World files;
- validates each materialized payload with the canonical Country model;
- requires source entity identity to equal the country code;
- carries exact source Package version/fingerprint and Run-local identity provenance;
- fails closed on malformed or duplicate semantic country state.

Its `content_fingerprint` deliberately excludes Run/Branch identity while including
the exact materialized country payload/provenance, so the same shared-history World
snapshot remains identifiable across a Branch fork.

## Run-owned generation projection

`project_generation()` reads exactly one materialized
`world.player_identity.v1` entity from the Run Package state and validates it as
`PlayerIdentityConfig`. It never reopens `config/player_generation/player_identity.json`
or the source World Package directory.

The projection retains the Run-local entity identity, source Package
version/fingerprint and entity-content fingerprint. Its content fingerprint is
branch-independent and suitable as provenance for deterministic downstream generation.

A World Package that does not carry player-generation identity data remains a valid
partial World Package, but operations that specifically require generation config fail
closed.

## Run-owned initial-pool preview

Run Admin exposes:

`POST /admin/players/runs/{run}/branches/{branch}/initial-pool/world-package/preview`

The request explicitly supplies:

- `world_package_id`;
- season;
- deterministic seed;
- target pool size;
- optional country/region filter.

The preview combines only the current Run-owned country projection and Run-owned
player-generation projection, then calls the existing deterministic
`InitialPlayerPoolGenerator`. It is strictly read-only:

- it does not write `config/simulation/initial_player_pool.json`;
- it does not create InitialWorld;
- it does not mutate the Working Draft;
- it does not read global country or player-identity config.

Repeated identical requests against the same Run snapshot return the same preview
fingerprint. Editing the global/source World Package after application does not change
the preview until a newer Package version is explicitly reviewed and applied.

## Run-owned InitialWorld adoption

Run Admin also exposes a reviewed InitialWorld path sourced directly from the
Run-owned generated pool:

- `POST /admin/players/runs/{run}/branches/{branch}/initial-world/world-package/preview`
- `POST /admin/players/runs/{run}/branches/{branch}/initial-world/world-package`

The adoption request embeds the exact generation request plus command/audit and
first-season ranking policy intent. Preview is read-only. Confirm requires the reviewed
InitialWorld fingerprint in `X-Initial-World-Preview-Fingerprint` and rebuilds from the
current Run-owned Package state before persistence.

The resulting immutable `InitialWorldState` records:

- `source_kind = run_world_generated_pool.v1`;
- the exact generated-pool preview fingerprint;
- the Run-owned World country content fingerprint;
- the Run-owned player-generation content fingerprint;
- the normal bootstrap/adoption request provenance.

This path does not read or persist the legacy global initial-pool file. Identical
Run-owned Package state + identical explicit request is deterministic, while stale
reviewed previews fail closed. Normal InitialWorld Save/reopen preserves the same
generation provenance.

## Source World Admin API

Run Admin exposes server-side source adaptation at:

- `POST /admin/runs/{run}/branches/{branch}/packages/source-world/{world_id}/preview`
- `POST /admin/runs/{run}/branches/{branch}/packages/source-world/{world_id}/confirm`
- `GET /admin/runs/{run}/branches/{branch}/packages/world/{package_id}/countries`

Preview/confirm rebuild the source document server-side. If the source changes after
preview, the reviewed preview fingerprint becomes stale and confirm fails. Once confirm
succeeds, later source edits do not change the Run snapshot.

## Optional InitialWorld binding

`InitialWorldAdoptionRequest.world_package_id` is optional.

When absent, existing manual/empty/custom flows behave exactly as before.

When present, InitialWorld preview/adopt:

1. reads the current Run-owned Package state;
2. projects the explicitly named World Package;
3. verifies every player's country/nationality code exists in that projection;
4. freezes the World country `content_fingerprint` into InitialWorld provenance.

This is an explicit binding, not an automatic priority rule. The engine therefore does
not invent semantics for multiple simultaneously applied World Packages, which remains
an open Package-composition question in the Master.

Changing the global source Package later does not alter InitialWorld. Changing the Run
Package after InitialWorld adoption likewise does not rewrite the already adopted
InitialWorld provenance.

## Deliberate boundary

V1 consumes World metadata/geography/countries and the player identity portion of the
production generation pipeline. A generated Run-owned pool remains a reviewed,
non-file-backed preview, but it can now be confirmed directly into immutable
InitialWorld state with exact provenance. Other player-generation calibration/policy,
Category hierarchy, Series, Calendar, entry policy and tournament templates remain
outside this adapter.

`Official FAX World` remains an offered Official Run default, not a mandatory Package.
A Run may still exist and valid independent operations may still execute without any
World Package.
