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
      requested_candidate_identity_reference_type: 'future_apply_reference_contract'
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
