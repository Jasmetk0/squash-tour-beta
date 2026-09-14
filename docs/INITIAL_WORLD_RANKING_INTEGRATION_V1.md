# Initial world and ranking integration V1

## Implemented boundary

A writable product Run/Branch can explicitly preview and adopt the complete supported
`2000/2001` production initial-player pool. The server reuses the existing initial-pool
season bootstrap conversion, validates the whole source, sorts it canonically, and stores
all `SeasonActivePlayer` identity/profile fields as an independent SQLite snapshot. The
snapshot retains source kind, source/player/bootstrap fingerprints, seed, command identity,
and declared Admin audit context. It never reads the source file again after adoption.

The same operation creates exactly one historically stored first-season MSA policy. An
Official Run request is constrained to decided Best 15; a custom Run must explicitly state
Best N and receives no global default. Empty Run creation remains unaffected.

The derived initial-ranking endpoints accept only command/audit intent. The server resolves
the owned roster and policy, derives stable tie-break tokens from stored identity facts, and
calls the existing `RankingBootstrapCommand` calculator/preview/confirm path. Legacy
`ranking_points` are deliberately ignored and no historical results are invented. Under
the existing rule that an entrant is classified in the following snapshot, the Week 1
candidate can have no rows; its verified input manifest nevertheless contains the complete
roster and policy for deterministic continuation.

## Integrity and history

Both initial-world adoption and derived ranking confirmation bind their previews to SHA-256
fingerprints. Ranking staging rechecks the initial-world fingerprint and the complete server-derived roster,
policy and tie-break identities inside its SQLite write transaction, so even a forged input
set yielding the same ranking rows is rejected. Idempotency
receipts retain the complete derived command. Exact adoption retries verify the original
scoped request and return the owned snapshot without reopening a changed or removed global source. Initial-world state is a distinct Saved
Revision component: an explicit save can occur before ranking preparation, restart/reopen
preserves it, and restore removes or reinstalls it together with ranking state.

Player IDs are unique only inside the owned Run/Branch state. Equal IDs in another scope do
not share rows. Source generation files remain global authoring inputs, not product Run
ownership, and tests mutate only disposable copies.

## Deliberate limits

This is real initial-world/ranking integration, not a completed lifecycle resolver or
pre-alpha. It does not advance time, publish Viewer ranking, invent pre-2000 results,
automatically retire players, implement Protected Ranking, or remap ranking-bearing forks.
The next vertical slice should consume this owned state in the real Week Transition together
with clock, lifecycle/development and public World Event boundaries.
