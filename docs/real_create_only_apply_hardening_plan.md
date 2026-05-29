# Real Create-Only Apply Hardening Plan (Phase 24A)

## Scope

This document describes the existing real guarded create-only apply command for Season Builder calendar creation.

It is separate from the Phase 15-23 future-apply preview/pre-execution stack. The preview stack remains disabled, read-only, non-mutating, manual-only, and informational. This document does not authorize production use of the real command by itself; it records the current command shape, current safety guarantees, known gaps, and the hardening plan required before the command can be treated as reliable.

This document originated in Phase 24A as planning-only documentation. Phase 24C2 has since implemented the candidate identity reference enforcement slice for the real create-only apply command. Phase 24D2 has implemented durable append-only JSONL audit persistence for schema-valid real create-only apply attempts that reach the handler; the remaining gaps below still require separate owner-approved hardening work.

## Existing real command

The existing real command is:

- **Endpoint:** `POST /admin/seasons/builder/apply-create-only-command`
- **Handler:** `post_season_builder_apply_create_only_command`
- **Request model:** `SeasonBuilderApplyCreateOnlyCommandRequest`
- **Response model:** `SeasonBuilderApplyCreateOnlyCommandResponse`
- **Persistence helper:** `SeasonCalendarService.create_calendar_if_absent`
- **Current frontend control:** `Execute create-only season calendar command`

When all current guards pass, the command can create a missing target season calendar from recomputed dry-run candidate events. It creates a `SeasonCalendar` and `SeasonCalendarEvent` records in the file-backed season calendar registry through `create_calendar_if_absent`.

The command must never:

- modify an existing calendar,
- merge into an existing calendar,
- overwrite an existing calendar,
- repair an existing calendar,
- bypass the target-absence guard,
- bypass exact confirmation and `create_only` mutation-scope checks,
- be confused with the disabled future-apply preview endpoint,
- be treated as production-reliable before the hardening plan below is complete.

## Relationship to the Phase 15-23 preview stack

The future-apply preview/pre-execution stack is exposed through `POST /admin/seasons/builder/future-apply-request-validation-preview`. That endpoint is preview-only and must remain disabled for execution and mutation.

The preview endpoint does not call the real create-only apply command. The real create-only apply command is a separate endpoint and command path.

The real command consumes preflight and dry-run identity fields and recomputes the dry-run result before mutation. As of Phase 24C2, it also requires and enforces the candidate identity reference fields produced for the Phase 15-23 stack:

- `requested_candidate_identity_reference_id`,
- `requested_candidate_identity_fingerprint`,
- `requested_candidate_identity_reference_type`.

The server recomputes expected candidate identity values from the dry-run preview's `future_apply_reference_contract` before any calendar mutation and rejects missing, unavailable, unreferenceable, or mismatched candidate identity references. The preview stack remains valid as non-mutating metadata and does not authorize execution by itself.

## Current guard summary

The existing real create-only command currently enforces these guards before it persists a calendar:

- target season label must normalize successfully,
- `source_type` must be `season_template`,
- `source_template_id` is required for `season_template` sources,
- `overwrite_policy` is limited to the current create-only-compatible values accepted by the endpoint,
- exact confirmation phrase is required: `I understand this will create a new season calendar.`,
- `mutation_scope` must be exactly `create_only`,
- preflight and dry-run identity fields must be present,
- candidate identity reference id, fingerprint, and reference type must be present,
- target calendar must be absent before apply,
- dry-run output is recomputed inside the command path,
- recomputed dry-run fingerprint and dry-run result id must match the request,
- recomputed future apply reference contract must be available and referenceable,
- requested candidate identity reference id, fingerprint, and reference type must match the recomputed contract,
- recomputed dry-run validation summary must be clean,
- recomputed candidate events must be non-empty,
- `requested_by` and `audit_reason` must be present,
- `create_calendar_if_absent` rejects insertion if the calendar already exists at persistence time.

These guards are useful, but they are not the complete reliability envelope required for long-term commissioner/admin use.

## Known gaps

The current real create-only apply path has these known gaps:

1. **Candidate identity reference enforcement implemented in Phase 24C2**
   - The real command now accepts and enforces `requested_candidate_identity_reference_id`, `requested_candidate_identity_fingerprint`, and `requested_candidate_identity_reference_type` from the Phase 15-23 preview stack before mutation.

2. **Durable audit trail implemented in Phase 24D2**
   - Schema-valid real create-only apply command attempts that reach the handler are persisted as append-only JSONL audit records before rejection responses or before/after successful mutation.
   - FastAPI/Pydantic 422 requests that never enter the handler are intentionally not audited in Phase 24D2.

3. **Weak idempotency/retry contract**
   - Duplicate/retry safety relies mostly on the target-absence guard and `create_calendar_if_absent`.
   - There is no explicit idempotency key, command record, or replay contract.

4. **Unclear concurrent/race protection**
   - Calendar persistence is file-backed load/check/save.
   - Race-safe behavior for concurrent duplicate requests is not yet designed or proven.

5. **Direct negative API test gaps**
   - Existing coverage is strongest around readiness, dry-run identity, preview metadata, and frontend wiring.
   - Direct real-command negative API tests are incomplete.

6. **Overwrite policy vocabulary ambiguity**
   - The preview/gate language refers to overwrite policy `none`, while the real command accepts its current create-only-compatible policy values. This vocabulary should be reconciled before relying on the command.

7. **Documentation ambiguity**
   - Existing pre-execution documentation correctly says the preview stack is non-mutating, but it was ambiguous because a separate real create-only command already exists elsewhere in the repository.

## Hardening plan

### Phase 24B: Direct real-command negative API tests

Add direct API tests for the real command proving failed guards do not mutate state:

- wrong confirmation phrase,
- wrong mutation scope,
- target exists,
- wrong source type,
- missing source template,
- stale dry-run identity,
- overwrite/merge/repair attempts,
- missing audit metadata,
- duplicate request.

### Phase 24C: Candidate identity reference alignment — implemented in Phase 24C2

The owner decision was to require immediate enforcement for the real mutation endpoint. Phase 24C2 updated the real command contract to require:

- `requested_candidate_identity_reference_id`,
- `requested_candidate_identity_fingerprint`,
- `requested_candidate_identity_reference_type`.

The command recomputes dry-run output, derives expected candidate identity values from the recomputed `future_apply_reference_contract`, requires the contract to be available/referenceable, rejects mismatches with no mutation, and includes direct API and frontend/client coverage for the new guards.

### Phase 24D: Audit persistence design — implemented in Phase 24D2

Phase 24D2 persists durable audit records for schema-valid `POST /admin/seasons/builder/apply-create-only-command` attempts that reach the handler. The selected backend is an append-only JSONL log stored adjacent to the season calendar registry by default, with one canonical JSON object per line. Records use schema version `season_builder_apply_create_only_audit.v1` and store safe scalar fields plus fingerprints rather than full raw request/response payloads.

The durable audit record includes, at minimum:

- command attempt id,
- requested_by,
- audit_reason,
- timestamp,
- input identity,
- requested and expected candidate identity references,
- guard result,
- mutation result,
- created calendar identity/event-id fingerprint on success,
- rejection status/reason when applicable.

Rejected schema-valid attempts are audited before the rejection response is returned. Successful attempts write a pre-mutation reservation before calendar insertion and a final success record after calendar insertion. If audit persistence fails before mutation, the command fails closed and does not create a calendar.

Phase 24D2 deliberately does not audit FastAPI/Pydantic 422 requests that fail request-model validation before handler entry.

### Phase 24E: Idempotency/retry/concurrency design

Design explicit retry and duplicate-submit semantics. Options include:

- idempotency key,
- persisted command record,
- deterministic duplicate-submit result,
- race-safe create-if-absent strategy,
- tests for duplicate clicks, retry after unknown network result, and concurrent duplicate requests.

### Phase 24F: Frontend UX hardening

Clarify the Season Builder danger-zone UX so operators understand that this is a real persistent command, separate from the preview stack. Future UX hardening should:

- make the danger zone clearer,
- show current guard readiness plainly,
- prevent confusion with the disabled preview stack,
- explain that successful execution creates persistent calendar state,
- show audit/idempotency status once those backend features exist.

Audit persistence now exists for the backend real command as of Phase 24D2; idempotency status and danger-zone UX hardening remain future work.

## Required invariant until hardening is complete

Until the hardening plan is complete and owner-approved, the existing real create-only command should be treated as an under-hardening admin command, not as a fully reliable production workflow. The Phase 15-23 preview stack remains non-mutating and must not be used as an implicit authorization grant for execution.
