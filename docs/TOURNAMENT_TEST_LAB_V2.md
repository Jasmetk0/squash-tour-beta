# Global Tournament Test Lab V2 — persistent isolated Test Sessions

V2 extends Tournament Test Lab V1 with durable editable Test Sessions while preserving the Lab's global, non-Run-owned boundary.

## Session boundary

A Tournament Test Session:

- has its own stable session ID, display name, monotonically increasing version and fingerprint;
- stores one complete `tournament_test_lab_scenario.v1`;
- is outside every Product Run and Branch;
- is not part of Saved Revision history, Branch restore or Branch fork ownership;
- never creates a live link to the source scenario.

The persistence row redundantly stores session metadata plus source provenance. Loading cross-checks the serialized session against those columns and fails closed on mismatch or tampering.

## Built-in copy

Read-only built-in Tournament Lab scenarios remain immutable.

`New Test Session` from a built-in creates an independent editable scenario with:

- a new session identity;
- `source_kind=built_in_copy`;
- source reference equal to the built-in scenario ID;
- source fingerprint equal to the exact built-in scenario fingerprint.

Editing or running the session never mutates the built-in baseline.

## Reviewed-state concurrency

Update and Run require the exact `expected_session_fingerprint` reviewed by the caller.

If another save changed the session first, stale update/run requests fail closed instead of silently applying against a newer session.

## API

- `GET /admin/labs/tournament/sessions`
- `GET /admin/labs/tournament/sessions/{session_id}`
- `POST /admin/labs/tournament/sessions`
- `PUT /admin/labs/tournament/sessions/{session_id}`
- `POST /admin/labs/tournament/sessions/{session_id}/run`

The original scratch endpoints remain available.

## UI

`/admin/labs/tournament` now supports:

- scratch scenario mode;
- New Test Session from a read-only built-in;
- opening an existing Test Session;
- editing session name and scenario JSON;
- saving with reviewed fingerprint protection;
- running the selected persisted session through the same V1 shared draw/match kernels.

## Remaining Tournament Lab work

Persistent sessions close the save/clone baseline required by the Master, but do not yet complete:

- explicit scenario import/export UX;
- Run → Lab historical tournament copy;
- Lab → Run compatibility-preview draft bridge;
- Qualification;
- groups and groups+knockout;
- replacements/withdrawals/WC/LL;
- tournament ranking consequences.

Copied-FAX full-season acceptance remains a separate later track.
