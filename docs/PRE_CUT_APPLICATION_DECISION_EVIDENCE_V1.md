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

This does **not** yet declare the decisions valid MSA Tour submissions. Exact
eligibility remains the separate authority that Master still leaves partly open.
Likewise, this slice does not add Run/Branch ownership, global Simulation Slot timing,
Tour-entry triggers or Saved Revision persistence.

Its purpose is narrower: preserve the complete shared-snapshot pre-cut decision truth
so the later Run/Branch application authority does not have to reconstruct or guess
who actually applied from a lossy field-cut list.
