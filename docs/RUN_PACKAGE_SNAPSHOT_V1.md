# Run Package Snapshot V1

Status: **implemented technical backbone**, not an end-to-end Official Run content path.

## Four distinct objects

1. A **source Package** is a portable, global authoring/library object. Existing World
   Package files remain source-side and read-only where configured that way.
2. A **Package document** is the immutable, canonical-serialized input reviewed by one
   preview/application operation. It has one of exactly five type identities: `World`,
   `Category`, `Series`, `Calendar`, or `Setup`.
3. **Run Package state** is the independent materialized copy owned by one Run/Branch.
   It contains payloads, provenance, stable numeric Run-local IDs, baselines, explicit
   source identities and unresolved references. It never reloads content from a source.
4. The **Saved Revision component** `run_package_state` is the immutable historical
   copy of that complete state, protected by both its component fingerprint and the
   outer Saved Revision hash.

## Identity and fingerprints

Package identity is `package_id + package_type`; each immutable source version has a
positive version, schema version, deterministic content fingerprint, provenance and
optional parent fingerprint. Same-version/different-content and a newer version whose
declared parent is not the applied source fingerprint fail closed.

An entity source identity is `(source_package_id, source_entity_id)`. Materialization
allocates a monotonically increasing Run-local integer from a Run-wide high-water mark.
The mapping is never based on a name, survives Save/restore, and is copied unchanged
across shared-history Branch forks. The high-water mark is not rewound by restore.

## Preview and application

Preview is read-only and deterministically classifies additions, unchanged entities,
updates, omitted (`not_included`) entities, unresolved references, exact-source
automatic resolutions, invalid bundles and local-divergence conflicts. Confirm repeats
the preview under `BEGIN IMMEDIATE` and CAS-checks Run, Branch, Saved head, draft version,
current state fingerprint, source document and reviewed preview fingerprint.

Application is non-destructive: only selected entities are added or updated. Omitted
entities and Calendar seasons remain unchanged. Missing references retain their exact
source identity; arrival of that identity with a compatible entity kind makes resolution
possible. Names never resolve references. Invalid selected bundles block the whole
transaction. Exact reapplication is a deterministic no-op. Command receipts make an
exact retry idempotent and reject command-ID reuse with different request content.

A local edit preserves the Run-local ID, marks manual provenance and dirties the Working
Draft. A newer source version cannot overwrite that divergence without explicit
`keep_run` or `use_source`; this is entity-level resolution, not a field merge engine.

## Setup composition

A Setup freezes selected non-Setup child Package documents. Preview expands those child
logical bundles. Confirm applies the selected valid child scope in one transaction;
invalid selected content or an inconsistent source history rolls back all children.
Missing child Package types are not synthesized and no placeholder sporting objects are
created.

## Save, restore, and Branch fork

Ordinary Working Draft Save captures `run_package_state`. Strict load checks schema,
Run/Branch scope, inner fingerprint, duplicate IDs/source mappings and reference-kind
consistency. Restore first proves live state equals the current Saved head, then replaces
only the target Branch state atomically. A Package-bearing historical fork is materialized:
the target owns a Branch-rescoped state and Saved Revision while source provenance,
payload and shared-history Run-local IDs remain unchanged. Nested forks use the same path.

## Deliberate boundary

This V1 establishes authority, persistence, application, recovery and API plumbing.
It does **not** yet make opaque Category/Series/Calendar payloads, or existing source World
Package files, automatic sporting consumers of the Match Engine, tournament services,
ranking, Calendar or InitialWorld. Dedicated semantic adapters and concrete Official Run
content/bootstrap remain follow-up work. No Player Package, implicit delete/full replace,
field-level merge, source-authoring UI or World Event is introduced.
