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
identity and remaining Best N capacity. Explicit `resolved_zeros` mode is required
on bootstrap/weekly preparation commands; `none` cannot carry zero inputs. Unsupported
point deductions remain unsupported. Callers remain responsible for resolving the
complete authoritative sanction state at each boundary, including corrections.

Frozen manifests store all supplied zero inputs, including currently inactive ones;
rows store the active ones for classified players. Verification reconstructs the same
candidate, and existing revision capture/install/restore retains this evidence.
There is no new sanction registry or sanction history editor: independently verifying
that no sanctions were omitted, and auditing issuance/modification, remain integration
work. A caller-supplied source fingerprint is provenance data, not authentication.

Empty zero fields are omitted from serialization so existing non-disciplinary row,
manifest and command payloads retain their representation and hashes. Admin shows
active zero identities, durations and remaining result capacity, and exposes the
resolved inputs separately from tournament sources. This does not publish candidates
or complete Week/Season Transition, Protected Ranking or the full discipline system.
