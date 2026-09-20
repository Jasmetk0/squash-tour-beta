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


## Entry decision slot batching

Master requires every player decision inside one entry decision slot to read the same
pre-slot snapshot and become visible together. The canonical write boundary is
therefore now `TournamentApplicationSubmissionBatchAuthority`, not technical
per-application call order.

A batch has one Run/Branch, FAX week and global decision-slot ordinal. All contained
valid submissions must share that exact boundary and are stored together.

If one pre-Tour player submits several first applications in the same slot, all are
historically simultaneous. The lexicographically first application ID is used only as
stable `PlayerTourEntryTrigger` provenance; it does not imply sporting priority,
causality or an earlier decision. Reversing input order therefore produces the same
batch fingerprint and first-entry truth.

The single-submission writer remains a compatibility wrapper for slots containing one
valid application. Calling it repeatedly for distinct simultaneous first applications
fails closed rather than letting call order decide provenance.
