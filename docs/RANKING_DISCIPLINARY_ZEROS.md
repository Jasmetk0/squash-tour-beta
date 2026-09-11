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
