# Resolved disciplinary zeros in ranking preparation

Master v64 §18.2 decides that each active Disciplinary Zero reserves one Best N
place, multiple zeros stack independently, and each expires after its own duration.
Effective dates, offense tariffs, duration rules and combinations with point deductions
remain open policy. This implementation consumes explicit resolved inputs; it does not
choose those rules or issue sanctions automatically.

`DisciplinaryZero` contains an immutable identity, Run/Branch/player scope, source
fingerprint, effective week and positive integer duration. Its interval includes the
effective week and excludes effective + duration. This duration is independent of
tournament-result validity. End dates can fall beyond the final Run week without
inventing a 51st season. Every active zero is retained in the row; tournament capacity
is `max(0, Best N - active zero count)`. Excess zeros are not silently discarded and
still expire independently. Zeros add no points or artificial tournament/completion
history. Existing tie-breaks compare actual counted results; unfilled zero values use
the existing profile padding. Zero-point classification rules are unchanged.

The pure calculator rejects duplicate zero identities, unknown players and mismatched
scope, and canonicalizes input ordering. Snapshot validation verifies active scope,
identity and remaining Best N capacity. Explicit `resolved_zeros` mode is required for caller-supplied zero inputs;
`stored_zeros` resolves them from persisted decisions instead. `none` cannot carry zeros. Unsupported
point deductions remain unsupported. Caller-resolved mode remains supported for branches without stored zero decisions.
Once a branch has zero source history, new commands require `stored_zeros`.

Frozen manifests store all supplied zero inputs, including currently inactive ones;
rows store the active ones for classified players. Verification reconstructs the same
candidate, and existing revision capture/install/restore retains this evidence.
The stored zero history described below verifies resolution against recorded decisions.
An Admin editor and auditing/authorization of sanction issuance remain integration work. A caller-supplied source fingerprint is provenance data, not authentication.

Empty zero fields are omitted from serialization so existing non-disciplinary row,
manifest and command payloads retain their representation and hashes. Admin shows
active zero identities, durations and remaining result capacity, and exposes the
resolved inputs separately from tournament sources. This does not publish candidates
or complete Week/Season Transition, Protected Ranking or the full discipline system.


## Persisted zero decision history

`RankingZeroVersion` records a decision's effective week and predecessor fingerprint.
The initial version starts at the zero's original effective week. Later versions must
extend the latest version at a strictly later week and retain Run, Branch, player,
zero identity and original start. They may change the explicit duration/provenance;
a shortened duration can therefore make the zero already expired at the correction
week. Earlier candidates remain unchanged. This is a storage capability, not a new
policy on when appeals, extensions or reductions are permitted.

`OfficialRankingZeroStore.append` participates in the caller's transaction (acquire
`BEGIN IMMEDIATE` before source reads/writes). It accepts exact retries, rejects
conflicting versions, missing predecessors, writes to read-only/forked scopes and
backdating into staged ranking history. Reads verify scope, keys, hashes and lineage.
No source write publishes a ranking or changes the world clock.

Bootstrap and weekly commands explicitly select `stored_zeros` with no caller-supplied
zeros. Inside the same transaction they resolve each latest version effective at the
target week. Future versions are excluded, expired decisions retained for evidence,
and the calculator determines active capacity. Existing command retries use their
frozen manifest. A stored-mode manifest records `zeros_from_history`; revision
validation checks its zero inputs against historical resolution at that exact week.
The lower-level resolved transition adapter rejects unresolved `stored_zeros` requests.

Saved ranking bundles retain the complete ordered `zero_sources` history, including
future prepared decisions and branches with no candidates yet. Capture, install,
internal replacement, public Save/Restore and unsaved-state guards include this table.
Recovery restores zero history in the same transaction as candidates and receipts.
Empty extension fields are omitted, preserving old manifest/revision serialization.
The existing database initialization creates the additional table on reopening.

There is no automatic import of old caller-resolved zeros into source history: that
would require backdating and trusted decision provenance. No sanction editor/API,
automatic issuance, tariff selection, point deductions or fork identity remapping
is introduced here. Callers must supply authoritative decisions and a complete roster;
missing players still block calculation rather than silently discard sanctions.


## Admin inspection of historical decision evidence

The existing candidate `/inputs` read now reports `zero_history_status` and
`zero_sources`. Stored-mode candidates verify the full source lineage and require its
resolution at the selected week to equal the frozen zero inputs. The response includes
only versions effective by that week, in zero/week order, with version/predecessor
fingerprints and one impact: superseded, expired, reserves a slot, or active while the
player is outside classification. Future decision payloads are never returned by this
historical view; corrupted history returns the existing generic 409 input error.

Caller-resolved and legacy candidates explicitly report their weaker provenance and
do not borrow a current registry to fabricate historical evidence. Empty verified
history is distinct from unavailable history. The Admin stored-input panel shows these
states and expandable provenance. Reads remain in a single SQLite transaction, work
on read-only scopes and do not save, publish, issue or modify decisions.


## Atomic decision batches in preparation commands

Bootstrap and weekly preparation now accept optional `zero_versions`. Each batch
requires `stored_zeros`, contains at most one version per zero, and is scoped to the
command's Run/Branch, target week and supplied roster. Initial Week 1 decisions can
be submitted with bootstrap; later new decisions and corrections can be submitted
with their weekly candidate. Existing lineage validation still requires corrections
to retain the original player, identity and start, and reference the latest version.

The runner appends the batch before resolving inputs inside its existing SQLite
savepoint. Decisions, tournament/result corrections, candidate and command receipt
succeed or fail together. Exact retries return the frozen candidate without applying
versions again; changed batches under the same command ID are rejected. Batch order
is canonicalized in the request fingerprint and empty batches are omitted to retain
legacy command payloads/hashes. Saved revision capture and restore retain the decisions,
frozen inputs and original command receipts, so retries work after recovery too.

These are explicit internal preparation commands. An Admin issuance/editor API and
its actor/reason audit workflow remain outstanding. No offense tariff, sanction
eligibility rule, automatic effective date or duration is selected by this adapter.
