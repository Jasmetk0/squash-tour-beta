# World Package → Run Adapter V1

Status: **implemented semantic adapter for World metadata/geography/countries**.

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
- timezone-area geography when that source file exists.

The existing source registry fingerprint is preserved as provenance. The canonical
Run Package document has its own deterministic fingerprint. Source version labels such
as `v1` / `test-v1` are mapped to the positive integer version required by the
Run Package backbone; unsupported labels fail closed.

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

V1 consumes World metadata/geography/countries only. It does not yet migrate the
production player-generation pipeline, Category hierarchy, Series, Calendar, entry
policy or tournament templates into Run Package semantic consumers.

`Official FAX World` remains an offered Official Run default, not a mandatory Package.
A Run may still exist and valid independent operations may still execute without any
World Package.
