import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  validateFutureApplyRequestPreview
} from './client'
import type {
  SeasonBuilderFutureApplyRequestValidationPreviewRequest,
  SeasonBuilderFutureApplyRequestValidationPreviewResponse
} from './types'

describe('validateFutureApplyRequestPreview', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('posts to the future apply request validation preview endpoint with provided payload', async () => {
    const payload: SeasonBuilderFutureApplyRequestValidationPreviewRequest = {
      target_season_label: '2031/2032',
      source_type: 'season_template',
      source_template_id: 'default_msa_template_preview',
      overwrite_policy: 'create_only',
      preflight_fingerprint: 'pf-123',
      reviewed_diff_id: 'rd-123',
      requested_candidate_identity_reference_id: 'ref-123',
      requested_candidate_identity_fingerprint: 'fp-123',
      requested_candidate_identity_reference_type: 'future_apply_reference_contract',
      requested_by: 'local-admin-preview',
      audit_reason: 'manual validation preview',
      explicit_confirmation: 'I understand this will create a new season calendar.',
      mutation_scope: 'create_only'
    }
    const responseBody: SeasonBuilderFutureApplyRequestValidationPreviewResponse = {
      enabled: false,
      can_execute: false,
      can_mutate: false,
      target_season_label: '2031/2032',
      source_type: 'season_template',
      source_template_id: 'default_msa_template_preview',
      overwrite_policy: 'create_only',
      future_apply_reference_contract: null,
      future_apply_request_validation_preview: {
        available: true,
        requested_candidate_identity_reference_id: 'ref-123',
        requested_candidate_identity_fingerprint: 'fp-123',
        requested_candidate_identity_reference_type: 'future_apply_reference_contract'
      },
      create_only_apply_execution_preflight_preview: {
        available: true,
        preflight_type: 'create_only_apply_execution_preflight_preview',
        execution_enabled: false,
        can_execute: false,
        mutation_permitted: false,
        read_only: true,
        message: 'Preview only.'
      },
      create_only_apply_audit_metadata_preview: {
        available: true,
        preview_type: 'create_only_apply_audit_metadata_preview',
        requested_by_present: true,
        audit_reason_present: true,
        explicit_confirmation_present: true,
        explicit_confirmation_matches: true,
        mutation_scope_present: true,
        mutation_scope_matches: true,
        required_confirmation_phrase: 'I understand this will create a new season calendar.',
        required_mutation_scope: 'create_only',
        all_required_audit_metadata_present: true,
        execution_enabled: false,
        can_execute: false,
        read_only: true,
        mutation_permitted: false,
        message: 'Preview only.'
      },
      disabled_execution_contract_summary: {
        available: true,
        summary_type: 'disabled_execution_contract_summary',
        future_apply_reference_contract_available: true,
        future_apply_request_validation_available: true,
        audit_metadata_available: true,
        execution_preflight_available: true,
        identity_reference_matches: true,
        audit_metadata_complete: true,
        all_known_preconditions_met: true,
        all_preview_layers_available: true,
        execution_enabled: false,
        can_execute: false,
        read_only: true,
        mutation_permitted: false,
        message: 'Execution remains disabled in this phase.'
      },
      final_guarded_apply_readiness_checklist: {
        available: true,
        checklist_type: 'final_guarded_apply_readiness_checklist',
        endpoint_disabled: true,
        endpoint_execution_disabled: true,
        endpoint_mutation_disabled: true,
        summary_available: true,
        summary_all_preview_layers_available: true,
        summary_all_known_preconditions_met: true,
        summary_execution_disabled: true,
        summary_mutation_disabled: true,
        all_readiness_checks_passed: true,
        execution_enabled: false,
        can_execute: false,
        read_only: true,
        mutation_permitted: false,
        message: 'Final checklist is read-only in preview mode.'
      },
      guarded_apply_execution_gate_specification: {
        available: true,
        specification_type: 'guarded_apply_execution_gate_specification',
        final_checklist_available: true,
        final_readiness_checks_passed: true,
        requires_target_absent: true,
        requires_create_only_scope: true,
        requires_allowed_source_type: 'season_template',
        requires_allowed_overwrite_policy: 'none',
        requires_audit_metadata: true,
        required_confirmation_phrase: 'I understand this will create a new season calendar.',
        required_mutation_scope: 'create_only',
        requires_identity_reference_match: true,
        requires_summary_execution_disabled: true,
        requires_endpoint_disabled_before_execution: true,
        gate_specification_complete: true,
        execution_enabled: false,
        can_execute: false,
        read_only: true,
        mutation_permitted: false,
        message: 'Execution gate specification is read-only in preview mode.'
      },
      future_apply_execution_boundary_contract: {
        available: true,
        contract_type: 'future_apply_execution_boundary_contract',
        gate_specification_available: true,
        gate_specification_complete: true,
        actual_execution_endpoint_exists: false,
        actual_execution_wiring_enabled: false,
        mutation_path_enabled: false,
        preview_stack_only: true,
        execution_boundary_intact: true,
        requires_separate_execution_phase: true,
        requires_separate_endpoint_wiring: true,
        requires_separate_mutation_audit: true,
        execution_enabled: false,
        can_execute: false,
        read_only: true,
        mutation_permitted: false,
        message: 'Execution boundary contract is read-only in preview mode.'
      },
      future_apply_execution_decision_summary: {
        available: true,
        summary_type: 'future_apply_execution_decision_summary',
        boundary_contract_available: true,
        execution_boundary_intact: true,
        preview_stack_only: true,
        manual_validation_only: true,
        separate_execution_phase_required: true,
        operator_review_required: true,
        future_execution_phase_may_be_considered: true,
        execution_authorized: false,
        execution_enabled: false,
        can_execute: false,
        read_only: true,
        mutation_permitted: false,
        message: 'Execution is disabled and read-only; no execution occurs in preview mode.'
      },
      audit_preview: null
    }

    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(responseBody), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      })
    )

    const result = await validateFutureApplyRequestPreview(payload)

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/admin/seasons/builder/future-apply-request-validation-preview',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(payload),
        headers: expect.objectContaining({ 'Content-Type': 'application/json' })
      })
    )
    const [, init] = fetchMock.mock.calls[0]
    const sentPayload = JSON.parse(String((init as RequestInit).body))
    expect(sentPayload.requested_by).toBe('local-admin-preview')
    expect(sentPayload.audit_reason).toBe('manual validation preview')
    expect(sentPayload.explicit_confirmation).toBe('I understand this will create a new season calendar.')
    expect(sentPayload.mutation_scope).toBe('create_only')
    expect(result).toEqual(responseBody)
  })

  it('does not alter candidate identity payload fields', async () => {
    const payload: SeasonBuilderFutureApplyRequestValidationPreviewRequest = {
      target_season_label: '2032/2033',
      source_type: 'season_template',
      requested_candidate_identity_reference_id: 'candidate-ref-1',
      requested_candidate_identity_fingerprint: 'candidate-fp-1',
      requested_candidate_identity_reference_type: 'future_apply_reference_contract'
    }

    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          enabled: false,
          can_execute: false,
          can_mutate: false,
          target_season_label: '2032/2033',
          source_type: 'season_template',
          source_template_id: null,
          overwrite_policy: null,
          future_apply_reference_contract: null,
          future_apply_request_validation_preview: null,
          create_only_apply_execution_preflight_preview: {
            available: true,
            preflight_type: 'create_only_apply_execution_preflight_preview',
            execution_enabled: false,
            can_execute: false,
            mutation_permitted: false,
            read_only: true,
            message: 'Preview only.'
          },
          create_only_apply_audit_metadata_preview: null,
          disabled_execution_contract_summary: null,
          final_guarded_apply_readiness_checklist: null,
          guarded_apply_execution_gate_specification: null,
          future_apply_execution_boundary_contract: null,
          future_apply_execution_decision_summary: null,
          audit_preview: null
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    await validateFutureApplyRequestPreview(payload)

    const [, init] = vi.mocked(globalThis.fetch).mock.calls[0]
    const sentPayload = JSON.parse(String((init as RequestInit).body))
    expect(sentPayload.requested_candidate_identity_reference_id).toBe('candidate-ref-1')
    expect(sentPayload.requested_candidate_identity_fingerprint).toBe('candidate-fp-1')
    expect(sentPayload.requested_candidate_identity_reference_type).toBe('future_apply_reference_contract')
  })
})
