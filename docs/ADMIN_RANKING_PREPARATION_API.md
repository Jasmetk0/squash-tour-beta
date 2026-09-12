# Audited Admin ranking preparation

The scoped Admin API can prepare unpublished candidates using the existing atomic
command runner. This does not advance the world clock, publish Official rankings,
change Viewer selection or create a Saved Revision. Use the existing explicit ranking
Save afterward. Preparation remains separate from full-world Week/Season Transition.

| Endpoint suffix under `/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates` | Command |
| --- | --- |
| `POST /prepare/initial` | `RankingBootstrapCommand`, Run Week 1 only |
| `POST /prepare/week` | `RankingWeekCommand`, immediately following a stored candidate |

Send the command as a JSON object. Both operations require an `audit` object with
nonblank `actor_label` (maximum 128 characters) and `reason` (maximum 2000 characters).
This is declared operator provenance, not authentication or an authorization grant.
The API follows the application's existing Admin access boundary; no account system
is added. Invalid strict command data returns 422. Scope, history, read-only/fork or
input dependency conflicts return a generic 409 without stored request payloads.
Success returns 201 and `RankingCandidateDetail` marked `candidate_only`, including
for an exact no-write retry. A changed reason/actor under the same command ID is a
conflicting request, since audit metadata participates in the request fingerprint.

Example initial body:

```json
{
  "command_id": "prepare-initial-001",
  "run_id": "run-id",
  "branch_id": "branch-id",
  "policy": {"policy_id": "reviewed-policy", "best_n": 15},
  "players": [],
  "discipline": "stored_zeros",
  "audit": {"actor_label": "Admin operator", "reason": "Prepare reviewed initial roster"}
}
```

This explicitly prepares an empty roster; it does not resolve or generate players.
The caller supplies the complete historically appropriate roster, tokens and policy.
Weekly commands also require `context.completed_week`, `context.target_week` and
`tournaments: []`. They can include scoped `corrections` and `zero_versions` using the
existing domain contracts. Automatic sanction rules and an issuance form are not added.

The public Admin adapter rejects nonempty tournament bindings because legacy award
files lack authoritative Run/Branch identity. Their trusted internal ingestion adapter
is unchanged. A dedicated scoped source adapter is required before this API can accept
those file bindings; matching caller labels and hashes alone are insufficient.

## Audit persistence and recovery

All newly staged commands store their canonical request JSON alongside the existing
receipt hash. New input manifests bind `command_request_fingerprint` to that payload,
so removing it cannot silently turn a new request into a legacy receipt. Inspection,
replay and revision capture validate the request hash, command ID, Run/Branch and week.

Saved revision receipts retain optional `request_payload_json`, including actor/reason
and the exact explicit inputs. Capture/install/restore preserve it within the existing
transaction. Admin `/inputs` exposes verified `command_audits`; the input panel displays
the declared operator, reason and command ID. Full payloads remain in stored receipts
and revision evidence rather than generic error responses.

Existing databases gain a nullable request column when opened. Legacy receipts lacking
both request evidence and the new manifest binding remain readable and receive no
invented audit. Empty audit/request extensions are omitted from old model serialization;
unaudited existing command fingerprints retain their previous canonical representation.
