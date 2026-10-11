# Tournament Test Lab V5C — Lab → Run draft compatibility preview

## Scope

This slice adds a read-only bridge from one reviewed Tournament Lab Session to a specific Product Run/Branch draft target.

It does not write tournament state, mutate a Working Draft, create authorities, or apply a calendar/event change. It freezes enough target and Lab identity to make a later explicit draft/apply step reviewable.

## Review binding

The preview requires the exact current Tournament Lab Session fingerprint. It also reads the target Branch revision boundary and freezes:

- Product Run and Branch identity,
- target event identity,
- current Saved Head revision ID,
- current Working Draft version and status,
- Lab Session fingerprint,
- Lab Scenario fingerprint,
- deterministic candidate fingerprint.

If the Lab Session changed after review, the preview fails rather than silently rebasing.

## Candidate

The candidate carries only tournament configuration already present in the Lab scenario: format kind, participant IDs, Main/Qualification geometry, seed order, group geometry and placements, hybrid advancement/crossings, topology seed and draw seed.

No ranking state, entry applications, WC/LL/replacement policy, schedule chronology, results, points or Run-owned authority is invented.

## Compatibility

The existing Tournament Lab shared-authority inspection remains the source of scenario compatibility. A candidate is marked `ready_for_draft` only when the scenario is normal-Run compatible and the target Working Draft is clean.

A dirty target Working Draft is reported as `TARGET_WORKING_DRAFT_DIRTY`. The preview remains read-only.

## Next

Implement the explicit reviewed draft mutation/application boundary using this frozen preview contract, or continue first with Tournament Lab withdrawal/WC/LL/replacement and ranking-consequence slices if those authorities need to be representable before application.
