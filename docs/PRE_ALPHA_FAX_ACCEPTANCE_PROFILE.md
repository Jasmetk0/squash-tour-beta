# Pre-alpha FAX long-acceptance input profile

## Purpose

Master v88 requires one automated release-gating run through an editable copy of the FAX test template that completes its first 25 seasons (2000/01–2024/25, 61 weeks each), including Season 25 closure. The readiness profile below validates the full 50-season reference configuration, which remains available for extended validation. The World Tour is fully simulated, lower Tours may remain abstract, the starting world contains at least 1,000 non-retired players, and the reference calendar contains 80 World Tour Editions per season.

This slice makes the **input readiness** for that long acceptance machine-readable. It does not claim that the long test has already executed or passed.

## Read-only evidence

The profile reads only Run-owned state:

- Product Run timeline and writable status,
- Branch ownership and active status,
- current Run-owned Initial World,
- current Run Package state,
- the Run-owned `calendar-2000-2001` projection.

It does not read the live source Calendar registry to fill missing Run state.

## Reference fixture readiness

The current input profile reports the reference Run/Branch as ready only when:

- the Run is editable,
- the Branch is active,
- the timeline is exactly 2000–2049 / 50 seasons,
- an Initial World exists with at least 1,000 players,
- the first-season Run-owned Calendar Package exists and validates,
- the first-season calendar contains exactly 80 `WORLD_TOUR` Editions,
- those Editions pass their existing ranking-points completeness contract; missing
  awards produce `FAX_ACCEPTANCE_RANKING_POINTS_INCOMPLETE`, never implicit zeros.

Non-World-Tour Editions are counted and reported as informational evidence because Master v72 permits lower Tours to remain abstract in the release test.

## Admin/API

The profile is exposed below the canonical Authoritative Simulation boundary and shown at the top of the Admin simulation panel. It has a deterministic fingerprint so release tooling can bind a future long-run command/report to the exact reviewed input profile.

## Next

Build the copied-FAX release fixture at the decided scale and add the acceptance harness/report. The first pre-alpha run verifies the first 25 complete seasons. Extended validation can cover all 50. The harness persists and reopens required checkpoints, records history growth and fails on any manual-repair requirement.

Current real preparation evidence and limitations: [copied-FAX preparation](PRE_ALPHA_FAX_REFERENCE_PREPARATION.md).
