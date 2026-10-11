# FAX reference testing strategy (phase 1)

## Decision and scope

Phase 1 pins one **FAX world-package source reference**, `fax-reference-v1`, to
the required files under `config/world_packages/official_fax_world/`. Its manifest contains
an explicit `source_tree_hash`; changing those source inputs fails the foundation
test until the version/hash is deliberately reviewed and updated. This hash is a
test-manifest identity, not the production `world_package_fingerprint` contract.

The backend fixture is a temporary, read-only copy of that package source, with a
post-test hash integrity check. It is **not a complete persisted Official FAX Run**.
The frontend object is a frozen API contract projection only. Its disposable
RunContainer helper is also an in-memory projection, not persisted mutation
isolation. Persisted Run/Branch materialization remains follow-up work.

## Test categories

### Unit test

A unit test exercises one pure function, component decision, validator, or domain
rule. It should use the smallest explicit values needed. A mock is appropriate at
a real boundary (HTTP, filesystem, clock adapter, repository) when the integration
is not the behavior under test. Do not reproduce a large Run graph in a unit test.

### FAX contract/component test

A frontend component test may mock `api/client` while using the shared, typed FAX
contract projection. It checks component/navigation handling of aligned API shapes,
but does not prove frontend-to-backend integration. Phase 1 establishes this tier.

### FAX integration test

A FAX integration test runs the actual production service/API/persistence stack on
a canonically materialized FAX reference. This tier does not exist yet; do not use
the component projection as evidence that it does.

### Mutation/simulation test

A mutation/simulation test starts with an actual disposable persisted Run/Branch
derived from a materialized canonical reference, uses a fixed injected seed,
and discards it after the test. It must also cover replay (same reference, seed,
and command gives the same result) and reference integrity. Never point mutation
tests at a built-in Run, a developer's local Run, or live/user storage.

## Audit findings

The audit covered backend tests and fixtures, frontend Vitest fixtures/mocks,
`config/world_packages/official_fax_world`, the legacy SimulationRun and newer Product
Run/Branch/checkpoint records, and both CI workflows.

Largest duplication observed:

1. Frontend page tests repeatedly hand-build subtly different Run summaries,
   Product Run containers, and Viewer context payloads (`run-a`, `run alpha`, and
   `product-run-a`). This obscures whether navigation identities actually align.
2. Backend API modules repeatedly define HTTP server/request helpers and create a
   fresh Run plus initial branch/checkpoint through nearly identical setup code.
3. `viewerDeferredFixtures.ts` already reduces payload duplication, but it models
   generic deferred Viewer read data and is not the shared FAX contract projection.
4. Tests correctly use temporary SQLite databases in most mutation paths, but
   there was no shared, explicitly versioned read-only reference boundary.

## Reuse assessment

The built-in **Official FAX World package is suitable and remains the canonical
world-package source**: it is config-backed, validated, stable in-repository, and already
distinguished from custom clones. It should not be copied into a large test dump.

`config/world/manual_player_overrides.json` is an external input used by the
production Official package registry but is not one of
`REQUIRED_WORLD_PACKAGE_FILES`, and is therefore not included in the phase-1
source-tree hash. Category Package inputs are likewise not materialized here.
Because the Master requires every Run to snapshot both World and Category Packages,
this fixture must not be called a complete canonical FAX Run.

The current built-in **Run** mechanism is not yet sufficient as a persisted test
fixture. Legacy `POST /runs` creates a mutable `custom_local` Product Run; newer
Branch/checkpoint persistence can enforce read-only/built-in mutation guards, but
there is no canonical bootstrap command that creates a complete built-in FAX Run
and then derives a new editable Product Run from it. Existing Branch fork commands
fork inside one Product Run and therefore do not provide that lifecycle boundary.
Phase 1 consequently introduces a pinned world-package source copy and a typed,
read-only API contract projection; it does not pretend that either is a persisted
Official Run.

## Phase-1 migration

The shared frontend fixture is used by representative Run Admin Home/dashboard,
Layout/Run navigation, and Viewer Product Run context-switch coverage. Existing
small/special-purpose fixtures remain where their distinct states are the subject
of the test; they are not additional “official” worlds. Layout retains a real
selection change from the reference projection to a disposable local projection.

## Versioning and change policy

Change `FAX_REFERENCE_VERSION` and its pinned `source_tree_hash` only after a
deliberate source-baseline review. In the same PR, document the reason and verify
the canonical source configuration. Avoid dates, network calls, ambient randomness,
and generated snapshots. The next phase should add a backend factory that
materializes this manifest from the canonical package into a temporary database,
verifies the pinned source-tree hash, and exposes a supported disposable Product
Run/Branch clone command before mutation-heavy suites are converted.

## Assumptions, constraints, and follow-ups

- Phase 1 deliberately does not rewrite all tests or introduce product UI.
- Backend behavior still uses the technical `official_branch_id` compatibility
  field; tests and user-facing expectations call it Viewer Branch.
- The fixture's null source fingerprints are placeholders until canonical Run
  materialization owns and persists those values; they are not authenticity claims.
- Follow-up: centralize the backend API harness, implement persisted reference
  materialization plus disposable cross-Run clone/fork, then migrate simulation
  tests in vertical slices with replay and integrity checks.
