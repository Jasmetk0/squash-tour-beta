# Valid tournament application persistence v1

Master Vision §9.2 makes the **first valid MSA Tour tournament application submission**
a formal Tour-entry trigger. Acceptance into Main Draw or Qualification is downstream
and cannot undo that career transition.

This slice persists the already-valid
`TournamentApplicationSubmissionAuthority` as append-only Branch-owned evidence and
coordinates it with the existing first-entry trigger store in the same database
transaction.

## Rules

- every valid submission remains a separate historical object;
- application identity is immutable and exact retry is idempotent;
- a player's first valid submission creates the canonical
  `PlayerTourEntryTrigger` when no earlier trigger exists;
- later valid submissions remain historical evidence and do not rewrite first entry;
- an out-of-order submission that predates persisted first-entry truth fails closed;
- two distinct first-entry authorities in the exact same global slot fail closed until
  slot-level arbitration chooses canonical evidence rather than relying on technical
  processing order.

The submission history is captured in Saved Revisions and restored before Tour-entry
triggers so recovered trigger evidence cannot point at missing application truth.
