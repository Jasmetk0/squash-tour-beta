# Real Create-Only Apply Hardening Plan (Phase 24A)

## Scope

This document describes the existing real guarded create-only apply command for Season Builder calendar creation.

It is separate from the Phase 15-23 future-apply preview/pre-execution stack. The preview stack remains disabled, read-only, non-mutating, manual-only, and informational. This document does not authorize production use of the real command by itself; it records the current command shape, current safety guarantees, known gaps, and the hardening plan required before the command can be treated as reliable.

This Phase 24A document is planning-only. It does not change runtime behavior, endpoint behavior, frontend behavior, calendar creation logic, guards, or mutation capabilities.

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

The real command currently consumes preflight and dry-run identity fields and recomputes the dry-run result before mutation. However, it does not yet consume or enforce all candidate identity reference fields produced for the Phase 15-23 stack, including:

- `requested_candidate_identity_reference_id`,
- `requested_candidate_identity_fingerprint`,
- `requested_candidate_identity_reference_type`.

That missing candidate-reference alignment is a known hardening gap. The preview stack remains valid as non-mutating metadata, but the real command must not be considered fully aligned with that stack until Phase 24C or an equivalent owner-approved slice resolves this decision.

## Current guard summary

The existing real create-only command currently enforces these guards before it persists a calendar:

- target season label must normalize successfully,
- `source_type` must be `season_template`,
- `source_template_id` is required for `season_template` sources,
- `overwrite_policy` is limited to the current create-only-compatible values accepted by the endpoint,
- exact confirmation phrase is required: `I understand this will create a new season calendar.`,
- `mutation_scope` must be exactly `create_only`,
- preflight and dry-run identity fields must be present,
- target calendar must be absent before apply,
- dry-run output is recomputed inside the command path,
- recomputed dry-run fingerprint and dry-run result id must match the request,
- recomputed dry-run validation summary must be clean,
- recomputed candidate events must be non-empty,
- `requested_by` and `audit_reason` must be present,
- `create_calendar_if_absent` rejects insertion if the calendar already exists at persistence time.

These guards are useful, but they are not the complete reliability envelope required for long-term commissioner/admin use.

## Known gaps

The current real create-only apply path has these known gaps:

1. **Missing candidate identity reference enforcement**
   - The real command does not currently accept or enforce `requested_candidate_identity_reference_id`, `requested_candidate_identity_fingerprint`, or `requested_candidate_identity_reference_type` from the Phase 15-23 preview stack.

2. **No durable audit trail**
   - Audit metadata is checked for presence, but command attempts and results are not yet persisted as durable audit records.

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

### Phase 24C: Candidate identity reference alignment

Make an owner decision on whether the real command must accept and enforce:

- `requested_candidate_identity_reference_id`,
- `requested_candidate_identity_fingerprint`,
- `requested_candidate_identity_reference_type`.

If yes, update the real command contract to require those fields, enforce mismatch rejection, and add direct tests proving mismatches do not mutate calendars.

### Phase 24D: Audit persistence design

Design and implement durable audit records for command attempts. At minimum, persist:

- command attempt id,
- requested_by,
- audit_reason,
- timestamp,
- input identity,
- guard result,
- mutation result,
- rejection reason when applicable.

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

## Required invariant until hardening is complete

Until the hardening plan is complete and owner-approved, the existing real create-only command should be treated as an under-hardening admin command, not as a fully reliable production workflow. The Phase 15-23 preview stack remains non-mutating and must not be used as an implicit authorization grant for execution.
