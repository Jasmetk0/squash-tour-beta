# Pre-cut application decision evidence v1

The existing `SeasonEntryBatchService` already evaluates overlapping tournaments from
one shared player snapshot and commits their provisional lists together. However, its
public result previously exposed only the post-cut EntryList representation. Depending
on `max_alternates` and `include_not_entered`, valid application intentions outside
the visible cut could disappear from the returned batch result.

That is insufficient for formal Tour-entry work because Master Vision §9.2 ties Tour
status to the first valid MSA Tour application, not to surviving a Main/Qualification
field cut.

This slice therefore preserves a canonical `application_decisions` tuple on every
`SeasonEntryBatchResult`.

## Boundary

The evidence contains every deterministic `EntryDecision` whose target is Main or
Qualification, before field capacity is applied.

It deliberately excludes `EntryTarget.NONE` because no application was made.

The evidence is:

- canonicalized by event, player and target;
- independent of input event order;
- independent of EntryList presentation options such as alternate limits or
  `include_not_entered`;
- bound by its own `application_decisions_fingerprint`;
- included in the overall batch build fingerprint.

This evidence still does **not** by itself declare decisions valid MSA Tour
submissions. Exact eligibility/deadline policy remains a separate versioned authority.

The downstream Run/Branch bridge is now implemented: a guarded authoritative-driver
preview rebuilds the complete shared-snapshot batch without mutating the legacy
EntryList registry, freezes it at an exact global Simulation Slot ordinal, and commits
that immutable Run entry-decision authority transactionally. Saved Revisions preserve
the Run slot, complete validation result, valid submissions and first Tour-entry
triggers in causal order. This keeps the original purpose intact: no later layer has to
reconstruct or guess who actually applied from a lossy field-cut list.
