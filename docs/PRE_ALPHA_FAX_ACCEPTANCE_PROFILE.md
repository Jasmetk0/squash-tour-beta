# Pre-alpha FAX long-acceptance input profile

## Purpose

Master v72 requires one automated release-gating run through an editable copy of the FAX test template across all 50 seasons 2000/01–2049/50. The World Tour is fully simulated, lower Tours may remain abstract, the starting world contains at least 1,000 non-retired players, and the reference calendar contains 80 World Tour Editions per season.

This slice makes the **input readiness** for that long acceptance machine-readable. It does not claim that the long test has already executed or passed.

## Read-only evidence

The profile reads only Run-owned state:

- Product Run timeline and writable status,
- Branch ownership and active status,
- current Run-owned Initial World,
- current Run Package state,
- the Run-owned `calendar-2000-2001` projection.

It does not read the live source Calendar registry to fill missing Run state.

## Gate

A Run/Branch is ready to start the long acceptance only when:

- the Run is editable,
- the Branch is active,
- the timeline is exactly 2000–2049 / 50 seasons,
- an Initial World exists with at least 1,000 players,
- the first-season Run-owned Calendar Package exists and validates,
- the first-season calendar contains exactly 80 `WORLD_TOUR` Editions.

Non-World-Tour Editions are counted and reported as informational evidence because Master v72 permits lower Tours to remain abstract in the release test.

## Admin/API

The profile is exposed below the canonical Authoritative Simulation boundary and shown at the top of the Admin simulation panel. It has a deterministic fingerprint so release tooling can bind a future long-run command/report to the exact reviewed input profile.

## Next

Build the copied-FAX release fixture at the decided scale and add the long-running acceptance harness/report that executes all 50 seasons, persists/reopens required checkpoints, records history growth and fails on any manual-repair requirement.
