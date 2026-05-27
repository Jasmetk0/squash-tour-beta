# Future Apply Pre-Execution Stack (Phase 15–22)

## Purpose and scope

This document summarizes the **Phase 15 through Phase 22** future-apply stack as a **pre-execution architecture only**.

The stack exists to provide:
- preview metadata,
- readiness metadata,
- specification metadata,
- boundary metadata,
- decision metadata.

It does **not** provide execution authorization.

### Non-negotiable safety meaning

The Phase 15–22 stack:
- does **not** execute apply,
- does **not** authorize execution,
- does **not** mutate calendars, templates, seasons, events, or state,
- does **not** create calendars,
- does **not** merge, overwrite, or repair anything,
- does **not** loosen create-only guards.

Any real guarded create-only apply execution must be implemented in a **separate future phase** with separate authorization and mutation wiring.

---

## Endpoint status (manual preview only)

### `POST /admin/seasons/builder/future-apply-request-validation-preview`

This endpoint remains intentionally disabled for execution and mutation:
- `enabled=False`
- `can_execute=False`
- `can_mutate=False`

Operational characteristics in Phase 15–22:
- manual-only,
- read-only,
- non-mutating,
- preview-only.

This endpoint may return rich readiness/specification/boundary/decision metadata, but that metadata is informational and non-authorizing.

---

## Layer-by-layer stack summary

## A) `future_apply_reference_contract`
- **Phase introduced:** 15
- **Purpose:** Normalize and report whether candidate identity references are structurally available for future review.
- **Why it is not authorization:** Referenceability is metadata only; it never grants execution permission.
- **Key disabled flags:** `apply_execution_enabled=False`, `mutation_permitted=False`.

## B) `future_apply_request_validation_preview`
- **Phase introduced:** 15
- **Purpose:** Show read-only validation of requested candidate identity reference fields versus contract data.
- **Why it is not authorization:** Validation parity is only input quality feedback and does not authorize command execution.
- **Key disabled flags:** `apply_execution_enabled=False`, `mutation_permitted=False`.

## C) `create_only_apply_execution_preflight_preview`
- **Phase introduced:** 16
- **Purpose:** Summarize preconditions that would be required by a future create-only apply command.
- **Why it is not authorization:** Preconditions can be true while execution remains explicitly disabled.
- **Key disabled flags:** `execution_enabled=False`, `can_execute=False`, `mutation_permitted=False`.

## D) `create_only_apply_audit_metadata_preview`
- **Phase introduced:** 17
- **Purpose:** Report whether requested audit fields and confirmation/scope values are present/matching.
- **Why it is not authorization:** Metadata completeness is not permission; it is documentation-only validation.
- **Key disabled flags:** `execution_enabled=False`, `can_execute=False`, `mutation_permitted=False`.

## E) `disabled_execution_contract_summary`
- **Phase introduced:** 18
- **Purpose:** Aggregate cross-layer preview coherence and state that execution remains disabled.
- **Why it is not authorization:** Even a fully coherent stack remains non-executable in this phase.
- **Key disabled flags:** `execution_enabled=False`, `can_execute=False`, `mutation_permitted=False`.

## F) `final_guarded_apply_readiness_checklist`
- **Phase introduced:** 19
- **Purpose:** Present a final read-only checklist including endpoint-disabled assertions.
- **Why it is not authorization:** Checklist pass states are never execution grants.
- **Key disabled flags:** `execution_enabled=False`, `can_execute=False`, `mutation_permitted=False`.

## G) `guarded_apply_execution_gate_specification`
- **Phase introduced:** 20
- **Purpose:** Describe the policy and gate requirements a future execution phase must enforce.
- **Why it is not authorization:** Specification text defines requirements but performs no execution authorization.
- **Key disabled flags:** `execution_enabled=False`, `can_execute=False`, `mutation_permitted=False`.

## H) `future_apply_execution_boundary_contract`
- **Phase introduced:** 21
- **Purpose:** Assert boundary separation: preview stack exists, execution wiring does not.
- **Why it is not authorization:** Boundary integrity is explicitly a non-authorization contract.
- **Key disabled flags:** `actual_execution_endpoint_exists=False`, `actual_execution_wiring_enabled=False`, `mutation_path_enabled=False`, `execution_enabled=False`, `can_execute=False`, `mutation_permitted=False`.

## I) `future_apply_execution_decision_summary`
- **Phase introduced:** 22
- **Purpose:** Summarize that future execution may be considered only in a separate phase after explicit review.
- **Why it is not authorization:** Decision metadata never authorizes current execution.
- **Key disabled flags:** `future_execution_phase_may_be_considered=True` is advisory only; `execution_authorized=False`, `execution_enabled=False`, `can_execute=False`, `mutation_permitted=False`.

---

## Invariant table

| Layer | May report readiness/available true? | Authorizes execution? | execution_enabled | can_execute | mutation_permitted | Notes |
|---|---|---|---|---|---|---|
| future_apply_reference_contract | Yes | No | False (`apply_execution_enabled`) | False (not an execute contract) | False | Availability indicates reference structure only. |
| future_apply_request_validation_preview | Yes | No | False (`apply_execution_enabled`) | False (not an execute contract) | False | Matching requested reference fields is not permission. |
| create_only_apply_execution_preflight_preview | Yes | No | False | False | False | Preconditions may be met while execution remains disabled. |
| create_only_apply_audit_metadata_preview | Yes | No | False | False | False | Audit metadata presence does not authorize mutation. |
| disabled_execution_contract_summary | Yes | No | False | False | False | "All layers available" does not change disabled execution state. |
| final_guarded_apply_readiness_checklist | Yes | No | False | False | False | Checklist pass is informational only in this phase. |
| guarded_apply_execution_gate_specification | Yes | No | False | False | False | Defines future requirements; does not wire execution. |
| future_apply_execution_boundary_contract | Yes | No | False | False | False | Boundary may be intact while execution remains absent. |
| future_apply_execution_decision_summary | Yes (`future_execution_phase_may_be_considered=True`) | No | False | False | False | `future_execution_phase_may_be_considered=True` is not authorization; `execution_authorized=False`. |

---

## Frontend manual validation behavior

Current frontend behavior for this stack is intentionally manual and display-only:
- preview panels render only when `futureApplyValidationResult` exists,
- `validateFutureApplyRequestPreview` is called only from the manual button handler,
- no `useEffect` auto-call exists for this request,
- input changes do not auto-call validation,
- no Apply/Execute button exists in the preview result block,
- all preview/checklist/specification/boundary/decision panels are display-only.

---

## Requirements before real guarded create-only apply execution

The following are **future requirements only** and are listed here as architecture guidance, not implementation.

A real guarded create-only apply execution phase would require, at minimum:
- a separate implementation phase,
- separate endpoint wiring,
- separate mutation audit implementation,
- explicit operator action,
- exact confirmation phrase enforcement,
- `create_only` scope enforcement,
- target-absence guard,
- source-type guard,
- overwrite policy `none` guard,
- required audit metadata,
- identity/reference match enforcement,
- post-apply verification,
- tests proving failed guards do not mutate,
- tests proving duplicate calls/retries are safe,
- tests proving merge/overwrite remains impossible.

> Documentation note: this section does not authorize, enable, or implement execution.
