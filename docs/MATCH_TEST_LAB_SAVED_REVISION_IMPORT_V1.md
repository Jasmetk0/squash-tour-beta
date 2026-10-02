# Match Test Lab — verified Saved Revision player import V1

Status: implemented historical-player import slice for existing isolated Match Lab Test Sessions.

## Goal

Allow Admin to copy one historical player from a reachable immutable Saved Revision into an
isolated Match Lab Test Session without creating a live link to the Run, Branch or revision.

The imported participant is test data only. The source Run is never mutated.

## Source authority

The import request identifies:

- Product Run ID;
- Branch ID;
- Saved Revision ID;
- Player ID;
- target Match Lab side (`player_a` or `player_b`).

The source revision is resolved through the existing validated Saved Revision history service.
That preserves the existing reachable-history and revision-integrity boundary instead of reading
an arbitrary persistence row directly.

The importer then requires two validated Saved Revision components:

1. `initial_world` for the player's historical identity/profile;
2. `player_sporting_state` for the canonical sporting state frozen in that revision.

Malformed component identity, fingerprint or sporting lineage fails closed through the existing
component loaders.

## Projection into Match Engine input

For the saved sporting head, the importer:

- selects the requested canonical `PlayerSportingRecord`;
- resolves the matching historical Initial World profile;
- calculates age at the saved sporting week from the persisted birth week;
- runs the existing `CanonicalMatchInputProjectionPolicy` / `project_player` compatibility adapter;
- installs the resulting engine player and Form / Sharpness / Fatigue modifiers into the selected
  Match Lab participant slot.

No second projection formula is introduced.

## Provenance and isolation

Each imported side adds one `MatchLabParticipantImportEvidence` row containing:

- source Run / Branch / Saved Revision;
- exact Saved Revision content hash;
- exact sporting-state fingerprint and week ordinal;
- player identity;
- source profile fingerprint;
- canonical projection fingerprint.

Participant evidence is part of the Test Session fingerprint once present. Re-importing a side
replaces only that side's evidence.

The source identifiers are provenance only. Running or editing the Test Session never reads the
source Run again and never writes to it.

Save/import commands retain the Test Session reviewed-fingerprint boundary, so stale editor state
cannot silently overwrite a newer session.

## Compatibility

Older V2 Test Sessions with no historical imports retain their previous exact fingerprint.
`participant_imports` is omitted from the fingerprint payload while empty, preserving persisted
V2 session compatibility.

## Current intentional limitation

V1 imports only players whose full historical profile exists in the Saved Revision Initial World.
A later prospect that exists in sporting state but not Initial World fails closed rather than
inventing hidden career/profile data from incomplete prospect metadata.

Prospect-profile historical import is a separate future slice if needed.

## API

`POST /admin/labs/match/sessions/{session_id}/import-saved-revision-player`

The endpoint returns the newly versioned Test Session.

## Next

With portable scenarios, built-ins, isolated Test Sessions and verified historical player import
now available, the next major Lab slice is Tournament Test Lab composition over the existing
shared tournament/draw/match authorities. The copied-FAX full-season acceptance track remains
separate.
