# FAX reference testing strategy (phase 1)

## Decision and scope

Integration-style tests use one named, versioned reference: `fax-reference-v1`. Its
world identity is `official_fax_world`, whose authoritative data stays in
`config/worlds/official_fax_world/`; the test fixture is a small API projection,
not a second world or a copied JSON dump. The projection has a fixed global seed
(`20270807`), a fixed Viewer Branch identity, and a fixed 2000–2049 horizon.

The reference projection is frozen and represents a built-in, read-only Run.
Tests must not change it. A test which executes a command must create a uniquely
named disposable editable Run/Branch derived from the reference, work only on
that copy, and let the test's temporary storage remove it. The phase-1 frontend
helper `makeDisposableFaxRun()` provides the identity/read-only transition for UI
contract tests; a backend persistence-level fork factory is follow-up work before
simulation suites are migrated.

## Test categories

### Unit test

A unit test exercises one pure function, component decision, validator, or domain
rule. It should use the smallest explicit values needed. A mock is appropriate at
a real boundary (HTTP, filesystem, clock adapter, repository) when the integration
is not the behavior under test. Do not reproduce a large Run graph in a unit test.

### FAX integration test

A FAX integration test verifies multiple production contracts working together
against the canonical reference projection. Use the shared fixture for Run,
Branch, navigation, Viewer/Admin context, and other cross-surface behavior. Reads
must leave the fixture byte-for-byte/logically unchanged. Prefer asserting stable
identities and domain facts over incidental formatting.

### Mutation/simulation test

A mutation/simulation test starts with a disposable editable clone/fork derived
from the canonical reference, uses an injected fixed seed and temporary database,
and discards it after the test. It must also cover replay (same reference, seed,
and command gives the same result) and reference integrity. Never point mutation
tests at a built-in Run, a developer's local Run, or live/user storage.

## Audit findings

The audit covered backend tests and fixtures, frontend Vitest fixtures/mocks,
`config/worlds/official_fax_world`, the legacy SimulationRun and newer Product
Run/Branch/checkpoint records, and both CI workflows.

Largest duplication observed:

1. Frontend page tests repeatedly hand-build subtly different Run summaries,
   Product Run containers, and Viewer context payloads (`run-a`, `run alpha`, and
   `product-run-a`). This obscures whether navigation identities actually align.
2. Backend API modules repeatedly define HTTP server/request helpers and create a
   fresh Run plus initial branch/checkpoint through nearly identical setup code.
3. `viewerDeferredFixtures.ts` already reduces payload duplication, but it models
   generic deferred Viewer read data and is not a canonical FAX Run contract.
4. Tests correctly use temporary SQLite databases in most mutation paths, but
   there was no shared, explicitly versioned read-only reference boundary.

## Reuse assessment

The built-in **Official FAX World package is suitable and remains the canonical
world source**: it is config-backed, validated, stable in-repository, and already
distinguished from custom clones. It should not be copied into a large test dump.

The current built-in **Run** mechanism is not yet sufficient as a persisted test
fixture. Legacy `POST /runs` creates a mutable `custom_local` Product Run; newer
Branch/checkpoint persistence can enforce read-only/built-in mutation guards, but
there is no canonical bootstrap command that creates a complete built-in FAX Run
and then derives a new editable Product Run from it. Existing Branch fork commands
fork inside one Product Run and therefore do not provide that lifecycle boundary.
Phase 1 consequently introduces the versioned read-only API projection and does
not pretend that a live/local Official Run is a safe fixture.

## Phase-1 migration

The shared frontend fixture is used by representative Run Admin Home/dashboard,
Layout/Run navigation, and Viewer Product Run context-switch coverage. Existing
small/special-purpose fixtures remain where their distinct states are the subject
of the test; they are not additional “official” worlds. No coverage is removed.

## Versioning and change policy

Change `FAX_REFERENCE_VERSION` only when a deliberate contract baseline changes.
In the same PR, document the reason, update stable assertions, and verify the
canonical source configuration. Avoid dates, network calls, ambient randomness,
and generated snapshots. The next phase should add a backend factory that
materializes this manifest from the canonical package into a temporary database,
verifies a source fingerprint, and exposes a supported disposable Product
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
