# Tournament application validation authority v1

Master Vision defines formal Tour entry at the first **valid** MSA Tour application,
but deliberately leaves parts of exact eligibility, deadlines and exception handling
open.

The engine therefore must not infer validity from field acceptance, legacy EntryList
status or simple application intent.

This contract freezes only the **resolved outcome** of whatever versioned policy or
explicit Admin authority decided those rules.

## One decision, one outcome

`TournamentApplicationValidationAuthority` binds:

- stable validation and application identities;
- exact Run, Branch, FAX week and global entry slot;
- the source `RunEntryDecisionSlotAuthority` fingerprint;
- exact event/player and Main/Qualification window;
- the source pre-cut decision fingerprint;
- `valid` or `invalid`;
- NR tie-break identity when valid;
- validation-policy identity and fingerprint;
- canonical reason codes/text;
- provenance.

A valid outcome requires the NR tie-break token needed by the later field/ranking
boundary. An invalid outcome requires at least one reason.

This model contains **no eligibility algorithm**.

## Slot completeness

`ResolvedApplicationValidationSlot` requires exactly one validation result for every
preserved application decision in its source slot.

That means the slot cannot be considered resolved while some application intents have
silently missing validity state.

Each validation must match:

- source Run/Branch;
- exact FAX week and global slot;
- source slot fingerprint;
- event/player identity;
- Main vs Qualification target;
- exact source-decision fingerprint.

Unknown, duplicated, missing or drifted evidence fails closed.

## Downstream projection

Only `valid` outcomes project to `ValidatedApplicationDecision`.

The complete path is therefore:

shared-snapshot Entry decision
→ Run/Branch slot authority
→ complete validation outcome slot
→ valid subset
→ simultaneous valid-submission batch
→ persisted application history
→ first Tour-entry trigger.

Invalid application attempts remain explicit validation evidence but do not create
Tour status.

## Deferred policy

This slice intentionally does **not** decide:

- exact player eligibility;
- entry-window deadlines;
- mandatory tournaments;
- exception rules;
- automatic vs Manual Override policy;
- Final Commitment rules.

Those can later implement their own versioned validator and emit this stable outcome
contract without changing downstream Tour-entry semantics.
