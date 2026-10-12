# F79-06 – guarded Add Selected into a SAVED opening InitialWorld

This is the first authority-backed selected Add slice after the approved v79
generation review/Keep/bulk editing controls (#1387–1390). An action selection
is NOT automatically a Keep selection, implicit Add or a replacement for the
existing whole-cohort Adopt command.

## Preconditions
- Run-owned custom writable active Run + Branch, clean exact Working Draft,
  immutable Saved HEAD and unchanged saved/live World Package fingerprint.
- The current **InitialWorld must already be Saved** at that HEAD, with the
  supplied SHA-256 fingerprint and no unpublished InitialWorld changes.
- First season only (2000/01); strictly the existing Run-owned generated
  InitialWorld source with the same saved World/country/generation provenance.
- Append only **before** any Initial Ranking preparation/publication,
  authoritative world clock, sporting event or later Week 1 player-state
  progression. Existing Week-1 lifecycle, sporting and health states must
  still have the original InitialWorld fingerprint and the same roster.
- An explicit source generation request with a seed, size and stored World.
  The production generator is recomputed by the server, never trusted from
  browser-supplied player JSON.
- Sorted, nonempty, unique list of up to 1,000 **candidate IDs**, all present
  in the new preview and all absent from existing InitialWorld. Maximum new
  combined size 2,000; duplicate/reused per-country IDs are rejected.
  To add from a country already present, generate enough profiles to obtain
  higher unused per-country sequence IDs; generation cannot rename/rekey
  an existing identity merely to avoid a collision.

## Preview → explicit commit → manual Saved Revision
1. In the Admin, choose seed and source cohort size; obtain an entirely
   read-only new Run World generation preview.
2. Pick individual candidate identities (page/filter selection in the
   inspector). Existing IDs appear as conflicts. Selection alone changes
   nothing.
3. Click **Verify selected addition on server**. This separately validates
   HEAD/Draft/World/current saved InitialWorld, recreates the *entire* source
   through production and returns the exact **combined** InitialWorld
   fingerprint + selected count. The old player models are unchanged.
4. Approve and **Commit selected players** with that exact fingerprint.
   The server repeats the provenance checks, then in one SQLite
   `BEGIN IMMEDIATE` CAS transaction installs the combined InitialWorld and
   replaces the pristine Week-1 lifecycle, sporting and health projections.
   Ranking/sporting progress, modified Week-1 evidence, failed duplicate
   checks or stale HEAD/fingerprint cause an all-or-nothing 409 conflict.
5. The existing **Save InitialWorld revision** UI must still be used
   separately to create a new immutable Saved Revision. Earlier Saved HEAD,
   its recorded InitialWorld/players and other ancestors are not rewritten.
   One new append record stores command ID, exact source-pool fingerprint,
   sorted player IDs and audit label/reason. Another append requires a newly
   Saved state and another explicit review.

## Backward compatibility and limits
- Existing `initial_world_state.v1` serialized payloads/fingerprints remain
  readable: the optional `selected_appends` field is **excluded from the
  fingerprint when empty**, preserving old immutable SHA-256. It is included
  for modified states and exported in new revision content.
- Original `adopted_by_command_id`, original generation lineage, policy and
  original player objects survive untouched. Each added player retains its
  individual source generation identity/bootstrap metadata; append history
  gives the subsequent source-batch provenance.
- This deliberately does **not** insert a late player into already published
  Ranking/Viewer/sporting history. That requires a distinct historically
  effective player addition with explicit Ranking Week, registration and
  league-entry policy. It is also not an authorization to edit previously
  saved revisions, a generic future-season intake, or a 57-field ability model.

## Tests and evidence
- Real SQLite focused regressions for per-player nonmutation, exact resulting
  persisted roster, 3 rebuilt Week-1 authority rosters, immutable Saved HEAD,
  next-Save readiness, duplicate ID/foreign World rejection, ranking
  blocker, checksum corruption and transaction rollback.
- Frontend Admin boundary tests for source preview, independent selection,
  collision warnings, server preflight, explicit commit and unsaved guard.
- Existing 1,000-player browser path remains regression for the original
  whole-cohort Adopt + Save. New append is not claimed as a full-season or
  calibrated-realism acceptance gate.
