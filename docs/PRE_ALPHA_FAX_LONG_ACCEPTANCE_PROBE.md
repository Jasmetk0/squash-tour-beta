# Pre-alpha copied-FAX long-acceptance probe

## Purpose

Run the real Authoritative Full Simulation parent against a copied-FAX release fixture until it either completes or exposes the first explicit canonical checkpoint/blocker.

The probe does not auto-resolve Entry, Draw, Ranking or transition decisions and does not implement a second simulation path.

## Contract

- requires the Master v72 FAX input profile to pass first,
- reviews the existing Full Simulation parent,
- commits that exact reviewed parent,
- returns the driver's real checkpoint/blockers when execution pauses,
- fingerprints the underlying Full Simulation execution payload.

If Full Simulation preview itself is unavailable, the probe returns `full_simulation_preview_unavailable` with the exact failure detail instead of hiding it behind an unstructured conflict.

## Historical first observed architectural blocker

Review of the current copied-FAX materialization path shows that InitialWorld persistence alone does not create the first authoritative sporting-week/world position. The canonical driver therefore cannot establish Week 1 and reports `authoritative sporting week state is missing`.

This identifies the next implementation slice: bootstrap Week 1 sporting/world state from the saved InitialWorld through an explicit Run-owned boundary, then rerun this probe to expose the next canonical preparation checkpoint.


## Current preparation evidence — 30 October 2026

The current materializer DOES initialize authoritative Week 1 and publish the
initial ranking. The historical missing-world diagnosis above is superseded.
A real copied 1,000-player/80-Edition HTTP/SQLite fixture exposed empty Edition
points tables before Entry. After the source/readiness correction and explicit
complete disposable test points, actual ranking adoption and Entry decisions
reach `application_validation_policy_unresolved`. No validation policy or played
season is fabricated. See [bounded preparation proof](PRE_ALPHA_FAX_REFERENCE_PREPARATION.md).
