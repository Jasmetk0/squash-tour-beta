# Global Match Test Lab V2 — isolated Test Sessions

V2 extends the V1 portable/read-only Match Lab with persistent editable **Test Sessions** while keeping the Lab outside all Run and Branch ownership.

## Built-in baselines

The backend exposes a deterministic read-only catalogue:

- `standard-even-match`
- `standard-strength-gap`

Each built-in carries a stable scenario fingerprint. The catalogue is source truth only and cannot be edited in place.

## New Test Session

`New Test Session` creates a new global `match_test_lab_session.v1` object with:

- its own generated `session_id`;
- display name and monotonically increasing version;
- a complete copied `MatchLabScenario`;
- source provenance when copied from a built-in;
- a canonical session fingerprint.

A Test Session has **no `run_id` and no `branch_id`**. It is therefore not Saved Revision content, not a Candidate Branch and not part of Run restore/fork semantics.

Editing the copied scenario cannot mutate the built-in baseline. Running the session still calls the shared production `MatchEngine.simulate` kernel.

## Reviewed-write boundary

Update and Run commands must submit the exact current `session_fingerprint`.

- stale editor state is rejected;
- concurrent changes cannot be silently overwritten;
- persisted row metadata and payload fingerprints are cross-checked on every read;
- corrupted persistence fails closed.

## Provenance

A built-in copy records:

- `source_kind = built_in_copy`;
- `source_reference = <built-in scenario id>`;
- `source_fingerprint = <exact baseline fingerprint>`.

That provenance is informational and immutable evidence of the copy origin. It is **not** a live link.

Portable and future Run-snapshot imports remain data copies. V2 still does not claim canonical Saved Revision player-snapshot import equivalence.

## API

- `GET /admin/labs/match/scenarios`
- `GET /admin/labs/match/sessions`
- `GET /admin/labs/match/sessions/{session_id}`
- `POST /admin/labs/match/sessions`
- `PUT /admin/labs/match/sessions/{session_id}`
- `POST /admin/labs/match/sessions/{session_id}/run`

The original stateless `POST /admin/labs/match/run` remains available for scratch/portable scenarios.

## Still next

Match Lab now has the required read-only-baseline → editable-copy isolation primitive. Remaining Lab milestone work is primarily:

1. verified import from canonical historical Run/Saved Revision player snapshots;
2. scenario export/library ergonomics;
3. Tournament Test Lab composition over shared tournament/draw/match authorities;
4. richer compatibility diagnostics explaining why a Lab tournament can or cannot become a normal Run tournament.

The copied-FAX full-season acceptance remains a later roadmap item and is not started by this slice.
