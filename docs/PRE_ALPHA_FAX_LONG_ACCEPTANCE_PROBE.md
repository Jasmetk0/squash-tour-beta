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

## First observed architectural blocker

Review of the current copied-FAX materialization path shows that InitialWorld persistence alone does not create the first authoritative sporting-week/world position. The canonical driver therefore cannot establish Week 1 and reports `authoritative sporting week state is missing`.

This identifies the next implementation slice: bootstrap Week 1 sporting/world state from the saved InitialWorld through an explicit Run-owned boundary, then rerun this probe to expose the next canonical preparation checkpoint.
