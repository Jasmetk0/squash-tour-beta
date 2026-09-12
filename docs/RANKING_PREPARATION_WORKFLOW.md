# Ranking preparation form and reviewed confirmation

The Admin ranking-candidates page now supports a complete preparation workflow:

1. Open initial preparation on an empty branch or next-week preparation on the latest
   candidate. A weekly form loads the verified prior roster and effective zero history.
2. Review the target week, policy reference and Best N, complete roster and stable
   tie-break tokens, Tour entry timing and retired state. Add explicit new zeros or
   change the duration/reference of an existing stored zero decision.
3. Enter the declared operator and reason, acknowledge review, and calculate a preview.
4. Review the candidate table. Inputs are frozen until the user chooses to edit and
   recalculate. Confirm explicitly to persist the candidate and its audit.
5. Use the existing ranking review and Save controls to create a recoverable revision.

The form contains structured controls, not editable JSON. It uses persisted tournament
sources; it does not offer unscoped legacy tournament ingestion or a result-correction
editor. Caller-resolved historical zeros are not silently migrated to stored decisions.
Legacy missing manifests block weekly prefill. An empty roster is explicit and produces
no classified players. A newly entered Tour player remains subject to the existing NR
rule. New zero duration is blank rather than an invented sanction tariff.

At rollover, the next week is computed within the existing 50×61 frame and the form
asks for explicit review of the incoming policy. It cannot offer season 51 after the
last Run week. This is candidate preparation, not a Season Transition or final closure.

## Preview and confirmation API

`POST /prepare/initial/preview` and `POST /prepare/week/preview` (under the existing
scoped ranking-candidates root) accept the same audited command as preparation.
The response contains `preview_only: true`, `request_fingerprint`, and `candidate`.
The runner exercises the real preparation pipeline in a SQLite transaction and always
rolls it back, including sources, zeros, candidate and receipt. It takes a writer lock
for the duration of that calculation, and does not create a Saved Revision or publish.

Confirmation supports two optional headers, both sent by the form:

| Header | Guard |
| --- | --- |
| `X-Ranking-Preview-Request` | Canonical command hash must match the reviewed request, including audit metadata |
| `X-Ranking-Preview-Fingerprint` | Recomputed candidate must match the reviewed candidate before transaction commit |

If stored sources change between preview and confirmation, the entire preparation is
rolled back and the caller receives a conflict. The external source change remains.
Recalculate to review the new result. Existing API callers without preview headers keep
their explicit-command behavior; headers do not change persisted request hashes.

The client verifies returned scope, week, command identity and candidate fingerprint.
It does not automatically retry writes. If a response is lost, the same immutable
request and preview remain available for an exact retry. Editing discards the review,
requires acknowledgement again and creates a new command for a new preview. Late async
responses from an unmounted branch form cannot signal success in the new branch.

## Validation and boundaries

Real HTTP/SQLite tests cover preview nonmutation, decision-batch rollback, request and
result guards, changes between preview and confirmation, exact retries, and a fresh
Run → preview → confirm → Save → reopen flow retaining the audit. Frontend component
and transport tests cover form data, correction start preservation, frozen review,
manual retry, editing/recalculation, branch unmount, legacy input handling, scope/header
checks and final-season bounds. These tests are included in Fast CI.

No automatic sanction issuance, authoritative roster/policy resolution, full-world
Week/Season Transition, public publication, Season Closing Ranking or Protected Ranking
is claimed. The operator still supplies and reviews the complete boundary inputs.
