# Run prospect source Saved Revision snapshot v1

## Purpose

Generated prospect metadata is persisted at **Run scope**, not Branch scope. Multiple
Branches can therefore consume the same deterministic prospect source. Historical
Branch restore must never delete, overwrite, or rewind that shared table as a side
effect of restoring one Branch.

This slice adds a Saved Revision **reference snapshot** for that Run-scoped source.

## Component

Saved Revision content key:

`run_prospect_source`

Schema:

`run_prospect_source_snapshot.v1`

The component stores the canonical Run prospect catalog ordered by `prospect_id`,
including identity/provenance fields and the persisted profile, development, potential,
and trait JSON payloads. The component fingerprint is SHA-256 over the exact canonical
snapshot.

Raw persisted prospect source remains in `run_prospects`; the component is historical
evidence, not a second mutable store.

## Save boundary

Every new Saved Revision captures the current Run prospect source when one exists.
Materialized prospect state can also be saved explicitly through:

- `GET .../authoritative-simulation/prospect-source/save/preview`
- `POST .../authoritative-simulation/prospect-source/save`

The preview returns the source fingerprint, prospect count, current Saved Revision head,
Working Draft version, and whether there is an unsaved source change.

The explicit Save requires a clean Working Draft and the exact reviewed fingerprint.

## Restore semantics

Run prospects are shared Run state, so Branch restore **does not mutate the live
`run_prospects` rows**.

Instead, restore:

1. verifies that the current Saved Revision captures the live Run prospect source;
2. verifies that the target Saved Revision's prospect-source snapshot matches the live
   Run source exactly;
3. fails before any Branch mutation if either check is missing or mismatched;
4. captures the same validated Run source into the new restore revision.

This prevents a restored historical Branch from continuing with a prospect catalog that
differs from the source against which its future lifecycle/sporting transitions were
saved, while avoiding destructive cross-Branch rewrites.

A legacy target that lacks `run_prospect_source` is intentionally fail-closed once a
live Run prospect source exists. The legacy revision is not rewritten.

## Recovery ownership

The restore coverage registry now distinguishes:

- Branch-owned components that may be replaced by historical restore;
- Run-scoped reference components that are immutable shared evidence and may only be
  validated;
- transient authoring state that blocks restore while active.

`RunProspectModel` is the first Run-scoped reference family.

## Scope

This advances the ROADMAP's complete sporting-world recovery follow-up by preserving the
source fidelity required for prospect→lifecycle→sporting adoption after restore.

It does **not** complete all sporting-world recovery, ranking identity remapping, formal
Tour-entry policy, or the remaining legacy-backed Run state.
