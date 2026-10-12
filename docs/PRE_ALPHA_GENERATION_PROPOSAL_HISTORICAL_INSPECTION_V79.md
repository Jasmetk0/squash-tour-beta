# F79-02 — Historical Generation Proposal inspection and explicit revalidation

Scope: Run/Branch-owned saved initial-player generation proposals, including
existing legacy and V2 Keep/edit sessions. This is not a Saved Revision
restore, proposal overwrite, unrestricted copy or a new player generation
mechanism.

## Two explicitly different operations

**Inspect historical proposal (GET `.../generation-proposals/{id}/inspection`):**
Read the existing exact immutable SQLite proposal and its stored player cohort,
using the established checksum and a full authoritative source/ownership
provenance check. The Run/Branch ownership is strict. No generation, matching
against current HEAD, adoption, Working Draft mutation or manual Save occurs.
Return old proposal and current context indicators for Saved HEAD, Draft,
package fingerprint and existing InitialWorld. This is a historical read and
never approves adoption. The original strict `GET {id}` still rejects stale
proposals, preserving existing clients' fail-closed behavior.

**Revalidate against current Run (POST `.../{id}/revalidate`):**
An explicit user-triggered command only. It requires supplied exact current
Saved HEAD, clean Working Draft version and Run-owned package fingerprint,
checks them against *both* stored Saved Revision package material and current
Run package state, refuses an already-created InitialWorld, loads the old
immutable authoritative request from SQLite, then executes a completely fresh
production preview against the current World. The browser does not send
player objects. The response contains the independent new preview fingerprint
and old/new cohort counts, changed/unchanged player profiles and
added/removed identities. Changed country/age quota/Keep constraints which
cannot replay against the new World are explicit conflicts, never hints.
Neither read nor revalidation updates the old proposal row.

**Use revalidated preview for review:** A third deliberate UI action.
The newly validated candidate becomes the only eligible review only after
the UI rechecks target Run, Branch, clean Draft, package fingerprint and
supported generation constraints. Even then Adopt requires another explicit
approval checkbox and the authoritative backend rechecks all conditions;
manual Run Save remains separate.

## Compatibility and boundaries

- Historical proposal payload/fingerprints and Saved Revision contents are not
  migrated or mutated.
- Cross-Run/Branch inspection and corrupted/tampered proposal provenance
  fail closed.
- Read-only/archived owned Runs can inspect history but cannot revalidate or
  Adopt without appropriate writable active target and clean context.
- Current existing `Open saved proposal` retains its prior strict behavior.
- The comparison describes old and new snapshots, not evidence of canonical
  57 attributes, 0–200 OVR or universal future-season player creation.
- UI filters remain read-only and never define a Keep or selection mutation.
- Dedicated API tests use real SQLite; component tests mock the API boundary.
  A passing browser baseline alone does not prove the historical inspection
  workflow; full internal-release checks follow `docs/PRE_ALPHA_TEST_POLICY.md`.
