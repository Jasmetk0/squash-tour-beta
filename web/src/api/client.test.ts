import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  applyCalendarTemplateToPlanningCalendar,
  compareCalendarTemplateDryRun,
  cloneOfficialWorldPackage,
  createCalendarTemplate,
  getPlanningSeasonCalendar,
  listPlanningSeasonCalendars,
  listWorldPackages,
  getWorldPackage,
  getWorldPackageCountries,
  getWorldPackageCountryEffectivePopulation,
  getWorldPackageWeeklyIntakePreview,
  getWorldPackageWeeklyIntakeSeasonSchedulePreview,
  getRunWeeklyIntakeCohortSeasonPreview,
  listRunProspects,
  materializeRunProspects,
  listRunContainers,
  getRunContainer,
  listRunBranches,
  getRunBranch,
  listBranchCheckpoints,
  getBranchCheckpoint,
  captureInitialBranchCheckpoint,
  captureCurrentBranchCheckpoint,
  captureCompletedEventBranchCheckpoint,
  captureCompletedWeekBranchCheckpoint,
  captureAdminActionBranchCheckpoint,
  listBranchStates,
  getBranchState,
  getWorldPackageValidation,
  updateCalendarTemplate,
  postSeasonBuilderApplyCreateOnlyCommand,
  validateFutureApplyRequestPreview
} from './client'
import type {
  CalendarTemplateCompareDryRunRequest,
  CalendarTemplateUpsertPayload,
  PlanningSeasonCalendarDetailResponse,
  PlanningCalendarApplyTemplateCommandRequest,
  PlanningCalendarApplyTemplateCommandResponse,
  PlanningSeasonCalendarListResponse,
  SeasonBuilderApplyCreateOnlyCommandRequest,
  SeasonBuilderApplyCreateOnlyCommandResponse,
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




describe('compareCalendarTemplateDryRun', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('uses POST /admin/seasons/calendar-templates/compare-dry-run and sends payload unchanged', async () => {
    const payload: CalendarTemplateCompareDryRunRequest = {
      target_season_label: '2006/07',
      source_template_id: 'template-a',
      policy: 'replace_unlocked_only',
      target_source: 'payload',
      target_events: [{
        id: 'target-nemarque-open-2006-07',
        name: 'Némarque Open',
        category_code: 'DIAMOND',
        qualification_weeks: [5],
        weeks: [6, 7],
        locked: true
      }]
    }
    const responseBody = {
      dry_run: true,
      mutation_performed: false,
      target_season_label: '2006/07',
      source_template_id: 'template-a',
      policy: 'replace_unlocked_only',
      target_source: 'payload',
      source_template_fingerprint: 'source-fp',
      target_calendar_fingerprint: null,
      target_calendar_exists: false,
      target_fingerprint: 'target-fp',
      diff_fingerprint: 'diff-fp',
      summary: { same_count: 1, missing_from_target_count: 0, only_in_target_count: 0, conflict_count: 0, locked_target_preserved_count: 1, selected_source_event_count: 1, source_event_count: 1, target_event_count: 1 },
      items: [],
      safety: { read_only: true, mutation_performed: false, apply_endpoint_enabled: false, message: 'Dry-run only.' },
      status: 'ok'
    }

    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(responseBody), { status: 200, headers: { 'Content-Type': 'application/json' } }))

    const result = await compareCalendarTemplateDryRun(payload)

    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/admin/seasons/calendar-templates/compare-dry-run',
      expect.objectContaining({ method: 'POST', body: JSON.stringify(payload) })
    )
    const [, init] = vi.mocked(globalThis.fetch).mock.calls[0]
    expect(JSON.parse(String((init as RequestInit).body))).toEqual(payload)
    expect(result).toEqual(responseBody)
  })

  it('can send planning_calendar target source without target_events', async () => {
    const payload: CalendarTemplateCompareDryRunRequest = {
      target_season_label: '2000/2001',
      source_template_id: 'template-a',
      target_source: 'planning_calendar',
      policy: 'replace_unlocked_only'
    }
    const responseBody = {
      dry_run: true,
      mutation_performed: false,
      target_season_label: '2000/2001',
      source_template_id: 'template-a',
      policy: 'replace_unlocked_only',
      target_source: 'planning_calendar',
      source_template_fingerprint: 'source-fp',
      target_fingerprint: 'pl_cal_abc',
      target_calendar_fingerprint: 'pl_cal_abc',
      target_calendar_exists: true,
      diff_fingerprint: 'diff-fp',
      summary: { same_count: 1, missing_from_target_count: 0, only_in_target_count: 0, conflict_count: 0, locked_target_preserved_count: 0, selected_source_event_count: 1, source_event_count: 1, target_event_count: 1 },
      items: [],
      safety: { read_only: true, mutation_performed: false, apply_endpoint_enabled: false, message: 'Dry-run only.' },
      status: 'ok'
    }

    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(responseBody), { status: 200, headers: { 'Content-Type': 'application/json' } }))

    await compareCalendarTemplateDryRun(payload)

    const [, init] = vi.mocked(globalThis.fetch).mock.calls[0]
    const sentPayload = JSON.parse(String((init as RequestInit).body))
    expect(sentPayload).toEqual(payload)
    expect(sentPayload).not.toHaveProperty('target_events')
  })

})

describe('planning season calendar API client', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  const listResponse: PlanningSeasonCalendarListResponse = {
    calendars: [],
    source_path: 'config/world/planning_season_calendars.json',
    schema_version: 'planning_season_calendars.v1',
    registry_fingerprint: 'pl_reg_empty',
    read_only: true,
    status: 'ok',
    safety: { planning_only: true, viewer_visible: false, simulation_consumed: false, canonical_season_calendar_modified: false }
  }

  it('listPlanningSeasonCalendars uses GET /admin/seasons/planning-calendars', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(listResponse), { status: 200, headers: { 'Content-Type': 'application/json' } }))

    const result = await listPlanningSeasonCalendars()

    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/admin/seasons/planning-calendars',
      expect.objectContaining({ headers: expect.objectContaining({ 'Content-Type': 'application/json' }) })
    )
    expect(result).toEqual(listResponse)
  })



  it('applyCalendarTemplateToPlanningCalendar posts snake_case copy_missing_only payload to encoded season endpoint', async () => {
    const payload: PlanningCalendarApplyTemplateCommandRequest = {
      source_template_id: 'template-a',
      policy: 'copy_missing_only',
      selected_source_event_ids: ['event-a'],
      expected_planning_calendar_fingerprint: 'target-fp',
      source_template_fingerprint: 'source-fp',
      reviewed_diff_fingerprint: 'diff-fp',
      requested_by: 'admin',
      audit_reason: 'reviewed missing events',
      explicit_confirmation: 'I understand this will apply reviewed template events to the planning calendar only.',
      idempotency_key: null
    }
    const responseBody: PlanningCalendarApplyTemplateCommandResponse = {
      command: 'apply_template_to_planning_calendar',
      applied: true,
      mutation_performed: true,
      target_season_label: '2000/01',
      normalized_target_season_label: '2000/2001',
      source_template_id: 'template-a',
      policy: 'copy_missing_only',
      audit_record_id: 'audit-1',
      audit_record_fingerprint: 'audit-fp',
      audit_persisted: true,
      audit_persistence_status: 'persisted',
      before_calendar_fingerprint: 'before-fp',
      after_calendar_fingerprint: 'after-fp',
      source_template_fingerprint: 'source-fp',
      reviewed_diff_fingerprint: 'diff-fp',
      recomputed_diff_fingerprint: 'diff-fp',
      apply_plan_fingerprint: 'plan-fp',
      applied_event_count: 1,
      created_event_count: 1,
      updated_event_count: 0,
      preserved_locked_event_count: 0,
      skipped_event_count: 0,
      rejected_event_count: 0,
      created_items: [],
      updated_items: [],
      preserved_locked_items: [],
      skipped_items: [],
      rejected_items: [],
      validation_errors: [],
      validation_warnings: [],
      safety_summary: { planning_only: true },
      message: 'Applied.'
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(responseBody), { status: 200, headers: { 'Content-Type': 'application/json' } }))

    const result = await applyCalendarTemplateToPlanningCalendar('2000/01', payload)

    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/admin/seasons/planning-calendars/2000%2F01/apply-template',
      expect.objectContaining({ method: 'POST', body: JSON.stringify(payload) })
    )
    const [, init] = vi.mocked(globalThis.fetch).mock.calls[0]
    const sentPayload = JSON.parse(String((init as RequestInit).body))
    expect(sentPayload.policy).toBe('copy_missing_only')
    expect(sentPayload.expected_planning_calendar_fingerprint).toBe('target-fp')
    expect(sentPayload.reviewed_diff_fingerprint).toBe('diff-fp')
    expect(sentPayload).not.toHaveProperty('target_events')
    expect(result).toEqual(responseBody)
  })

  it('getPlanningSeasonCalendar encodes season labels', async () => {
    const detailResponse: PlanningSeasonCalendarDetailResponse = {
      calendar: null,
      source_path: 'config/world/planning_season_calendars.json',
      schema_version: 'planning_season_calendars.v1',
      registry_fingerprint: 'pl_reg_empty',
      read_only: true,
      status: 'ok',
      safety: { planning_only: true, viewer_visible: false, simulation_consumed: false, canonical_season_calendar_modified: false }
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(detailResponse), { status: 200, headers: { 'Content-Type': 'application/json' } }))

    const result = await getPlanningSeasonCalendar('2000/01')

    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/admin/seasons/planning-calendars/2000%2F01',
      expect.objectContaining({ headers: expect.objectContaining({ 'Content-Type': 'application/json' }) })
    )
    expect(result).toEqual(detailResponse)
  })
})

describe('calendar template upsert API client', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  const payload: CalendarTemplateUpsertPayload = {
    id: 'template-a',
    name: 'Template A',
    description: 'Admin template',
    status: 'draft',
    events: [{
      id: 'event-a',
      name: 'Event A',
      category_code: 'DIAMOND',
      weeks: [6, 7],
      qualification_weeks: [5],
      locked: true,
      country_code: 'EGY',
      city: 'Cairo',
      venue: 'Glass Court',
      notes: 'Notes',
      source_template_id: null,
      event_fingerprint: null
    }]
  }

  it('createCalendarTemplate uses POST /admin/seasons/calendar-templates', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ template: payload, status: 'ok', schema_version: 'calendar_templates.v1' }), { status: 200 }))
    await createCalendarTemplate(payload)
    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/admin/seasons/calendar-templates',
      expect.objectContaining({ method: 'POST', body: JSON.stringify(payload) })
    )
  })

  it('updateCalendarTemplate uses PUT /admin/seasons/calendar-templates/:templateId', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ template: payload, status: 'ok', schema_version: 'calendar_templates.v1' }), { status: 200 }))
    await updateCalendarTemplate('template/a', payload)
    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/admin/seasons/calendar-templates/template%2Fa',
      expect.objectContaining({ method: 'PUT', body: JSON.stringify(payload) })
    )
  })
})

describe('postSeasonBuilderApplyCreateOnlyCommand', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('posts required candidate identity fields unchanged to the create-only command endpoint', async () => {
    const payload: SeasonBuilderApplyCreateOnlyCommandRequest = {
      target_season_label: '2032/2033',
      source_type: 'season_template',
      source_template_id: 'default_msa_template_preview',
      overwrite_policy: null,
      preflight_fingerprint: 'pf-create-only',
      reviewed_diff_id: 'rd-create-only',
      dry_run_result_fingerprint: 'drf-create-only',
      dry_run_result_id: 'drr-create-only',
      requested_candidate_identity_reference_id: 'candidate-ref-create-only',
      requested_candidate_identity_fingerprint: 'candidate-fp-create-only',
      requested_candidate_identity_reference_type: 'candidate_identity_set',
      requested_by: 'local-admin-preview',
      audit_reason: 'create only command',
      explicit_confirmation: 'I understand this will create a new season calendar.',
      mutation_scope: 'create_only'
    }
    const responseBody: SeasonBuilderApplyCreateOnlyCommandResponse = {
      command: 'season_builder_apply_create_only',
      enabled: true,
      can_execute: true,
      can_mutate: true,
      applied: true,
      target_season_label: '2032/2033',
      validation_errors: [],
      validation_warnings: [],
      created_calendar_summary: {},
      created_event_preview: [],
      created_calendar_identity: {},
      created_calendar_validation_preview: {},
      apply_gate_summary: {},
      applied_event_count: 0,
      dry_run_identity: {},
      audit_preview: {},
      message: 'Create-only apply executed successfully.'
    }

    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(responseBody), { status: 200, headers: { 'Content-Type': 'application/json' } })
    )

    const result = await postSeasonBuilderApplyCreateOnlyCommand(payload)

    const [url, init] = vi.mocked(globalThis.fetch).mock.calls[0]
    expect(url).toBe('http://127.0.0.1:8000/admin/seasons/builder/apply-create-only-command')
    const sentPayload = JSON.parse(String((init as RequestInit).body))
    expect(sentPayload.requested_candidate_identity_reference_id).toBe('candidate-ref-create-only')
    expect(sentPayload.requested_candidate_identity_fingerprint).toBe('candidate-fp-create-only')
    expect(sentPayload.requested_candidate_identity_reference_type).toBe('candidate_identity_set')
    expect(result).toEqual(responseBody)
  })
})


describe('world package registry client', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('lists World Packages from GET /world/packages', async () => {
    const responseBody = { packages: [] }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(responseBody), { status: 200 }))

    const result = await listWorldPackages()

    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/world/packages',
      expect.objectContaining({ headers: expect.objectContaining({ 'Content-Type': 'application/json' }) })
    )
    expect(result).toEqual(responseBody)
  })

  it('gets one World Package from GET /world/packages/:worldId with encoding', async () => {
    const responseBody = {
      world_id: 'official_fax_world',
      name: 'Official FAX World',
      description: 'Built-in official FAX squash world package.',
      type: 'official',
      status: 'active',
      source: 'built_in',
      editable: false,
      deletable: false,
      archivable: false,
      version: 'v1',
      fingerprint: 'abc123',
      country_count: 1,
      manual_override_count: 0,
      continent_count: 1,
      region_count: 1,
      travel_region_count: 1,
      used_by_run_count: null,
      validation_status: 'valid',
      storage: { countries_path: 'config/worlds/official_fax_world/countries.json', manual_player_overrides_path: 'config/world/manual_player_overrides.json' }
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(responseBody), { status: 200 }))

    const result = await getWorldPackage('official/fax world')

    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/world/packages/official%2Ffax%20world',
      expect.objectContaining({ headers: expect.objectContaining({ 'Content-Type': 'application/json' }) })
    )
    expect(result).toEqual(responseBody)
  })

  it('gets World Package validation from GET /world/packages/:worldId/validation with encoding', async () => {
    const responseBody = {
      world_id: 'official_fax_world',
      status: 'valid',
      error_count: 0,
      warning_count: 0,
      info_count: 1,
      checks: []
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(responseBody), { status: 200 }))

    const result = await getWorldPackageValidation('official/fax world')

    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/world/packages/official%2Ffax%20world/validation',
      expect.objectContaining({ headers: expect.objectContaining({ 'Content-Type': 'application/json' }) })
    )
    expect(result).toEqual(responseBody)
  })

  it('gets World Package countries from GET /world/packages/:worldId/countries with encoding', async () => {
    const responseBody = {
      world_id: 'official_fax_world',
      world_name: 'Official FAX World',
      type: 'official',
      source: 'built_in',
      read_only: true,
      country_count: 0,
      source_path: 'config/worlds/official_fax_world/countries.json',
      countries: []
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(responseBody), { status: 200 }))

    const result = await getWorldPackageCountries('official/fax world')

    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/world/packages/official%2Ffax%20world/countries',
      expect.objectContaining({ headers: expect.objectContaining({ 'Content-Type': 'application/json' }) })
    )
    expect(result).toEqual(responseBody)
  })


  it('gets World Package weekly intake preview with encoded path and query params', async () => {
    const responseBody = {
      world_id: 'official_fax_world',
      world_name: 'Official FAX World',
      season: '2000/2001',
      season_start_year: 2000,
      season_week: 1,
      calendar_year: 2000,
      year_week: 37,
      birth_year: 1985,
      birth_year_week: 37,
      intake_age: 15,
      target_intake_count: 10,
      total_allocated: 10,
      allocations: []
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(responseBody), { status: 200 }))

    const result = await getWorldPackageWeeklyIntakePreview('official/fax world', { season: '2000/2001', season_week: 1, target_intake_count: 10, country_code: 'GER', region: 'EUROPE' })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/world/packages/official%2Ffax%20world/weekly-intake/preview?season=2000%2F2001&season_week=1&target_intake_count=10&country_code=GER&region=EUROPE',
      expect.objectContaining({ headers: expect.objectContaining({ 'Content-Type': 'application/json' }) })
    )
    expect(result).toEqual(responseBody)
  })


  it('gets World Package weekly intake season schedule preview with encoded path and query params', async () => {
    const responseBody = {
      world_id: 'official_fax_world',
      world_name: 'Official FAX World',
      season: '2000/2001',
      season_start_year: 2000,
      season_index: 0,
      base_annual_intake_target: 200,
      season_growth_rate: 0.015,
      season_variation_multiplier: 1.0,
      annual_target: 200,
      total_weekly_target: 200,
      weeks: []
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(responseBody), { status: 200 }))

    const result = await getWorldPackageWeeklyIntakeSeasonSchedulePreview('official/fax world', {
      season: '2000/2001',
      base_annual_intake_target: 200,
      season_growth_rate: 0.015
    })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/world/packages/official%2Ffax%20world/weekly-intake/season-schedule/preview?season=2000%2F2001&base_annual_intake_target=200&season_growth_rate=0.015',
      expect.objectContaining({ headers: expect.objectContaining({ 'Content-Type': 'application/json' }) })
    )
    expect(result).toEqual(responseBody)
  })


  it('gets run weekly intake cohort season preview with encoded path and query params', async () => {
    const responseBody = {
      run_id: 'run/a',
      world_id: 'official_fax_world',
      world_name: 'Official FAX World',
      season: '2000/2001',
      season_start_year: 2000,
      season_index: 0,
      base_annual_intake_target: 200,
      season_growth_rate: 0.015,
      season_variation_multiplier: 1.0,
      annual_target: 200,
      total_weekly_target: 200,
      weeks: [],
      country_totals: []
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(responseBody), { status: 200 }))

    const result = await getRunWeeklyIntakeCohortSeasonPreview('run/a', {
      base_annual_intake_target: 200,
      season_growth_rate: 0.015,
      country_code: 'GER',
      region: 'EUROPE'
    })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/runs/run%2Fa/weekly-intake/cohort-season/preview?base_annual_intake_target=200&season_growth_rate=0.015&country_code=GER&region=EUROPE',
      expect.objectContaining({ headers: expect.objectContaining({ 'Content-Type': 'application/json' }) })
    )
    expect(result).toEqual(responseBody)
  })


  it('lists run prospects with encoded path and filters', async () => {
    const responseBody = { run_id: 'run/a', total: 0, limit: 25, offset: 5, prospects: [] }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(responseBody), { status: 200 }))

    const result = await listRunProspects('run/a', { country_code: 'EGY', status: 'prospect', season_start_year: 2027, season_week: 4, limit: 25, offset: 5 })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/runs/run%2Fa/prospects?country_code=EGY&status=prospect&season_start_year=2027&season_week=4&limit=25&offset=5',
      expect.objectContaining({ headers: expect.objectContaining({ 'Content-Type': 'application/json' }) })
    )
    expect(result).toEqual(responseBody)
  })


  it('materializes run prospects with encoded path and payload', async () => {
    const responseBody = {
      run_id: 'run/a', world_id: 'official_fax_world', season: '2027/2028', season_start_year: 2027, annual_target: 3,
      requested_prospect_count: 3, created_count: 3, existing_count: 0, skipped_count: 0, conflict_count: 0,
      total_persisted_for_scope: 3, weeks_materialized: [], country_totals: [], already_materialized: false, message: 'ok'
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(responseBody), { status: 200 }))

    const result = await materializeRunProspects('run/a', { base_annual_intake_target: 3, country_code: 'GER', overwrite: true })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/runs/run%2Fa/prospects/materialize-15yo-cohort',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ base_annual_intake_target: 3, country_code: 'GER', overwrite: true }) })
    )
    expect(result).toEqual(responseBody)
  })


  it('gets World Package country effective population diagnostics with encoded path and year query', async () => {
    const responseBody = {
      world_id: 'official_fax_world',
      world_name: 'Official FAX World',
      type: 'official',
      source: 'built_in',
      read_only: true,
      source_path: 'config/worlds/official_fax_world/countries.json',
      country_code: 'GER',
      country_name: 'Germanica',
      requested_year: 1987,
      effective_population: 169702055,
      source_year: 2020,
      source_type: 'nearest_population_year',
      is_estimated: true,
      default_population_year: 2020,
      default_population: 169702055,
      legacy_population: 169702055,
      population_by_year_count: 1,
      usable_population_by_year_count: 1
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(responseBody), { status: 200 }))

    const result = await getWorldPackageCountryEffectivePopulation('official/fax world', 'g/e/r', 1987)

    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/world/packages/official%2Ffax%20world/countries/g%2Fe%2Fr/effective-population?year=1987',
      expect.objectContaining({ headers: expect.objectContaining({ 'Content-Type': 'application/json' }) })
    )
    expect(result).toEqual(responseBody)
  })

  it('clones Official FAX World via POST /world/packages/official_fax_world/clone', async () => {
    const payload = {
      new_world_id: 'my_custom_world',
      name: 'My Custom World',
      description: 'Custom world cloned from Official FAX World.',
      dry_run: true
    }
    const responseBody = {
      ok: true,
      dry_run: true,
      source_world_id: 'official_fax_world',
      new_world_id: 'my_custom_world',
      target_path: 'config/worlds/custom/my_custom_world',
      created_files: ['world.json'],
      package: null,
      validation: null,
      errors: []
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(responseBody), { status: 200 }))

    const result = await cloneOfficialWorldPackage(payload)

    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/world/packages/official_fax_world/clone',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(payload)
      })
    )
    expect(result).toEqual(responseBody)
  })

  it('lists Run branches with an encoded run query and encodes branch detail ids', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ run_branches: [] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ branch_id: 'branch/a #1' }), { status: 200 }))

    await listRunBranches('save/a #1')
    await getRunBranch('branch/a #1')

    expect(globalThis.fetch).toHaveBeenNthCalledWith(
      1, 'http://127.0.0.1:8000/run-branches?run_id=save%2Fa+%231', expect.anything()
    )
    expect(globalThis.fetch).toHaveBeenNthCalledWith(
      2, 'http://127.0.0.1:8000/run-branches/branch%2Fa%20%231', expect.anything()
    )
  })

  it('lists, gets, and capture-posts immutable branch checkpoints', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ branch_checkpoints: [] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ checkpoint_id: 'cp/a #1' }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ checkpoint_id: 'cp/a #1' }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ checkpoint_id: 'cp/a #2' }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ checkpoint_id: 'cp/a #3' }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ checkpoint_id: 'cp/a #4' }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ checkpoint_id: 'cp/a #5' }), { status: 200 }))
    await listBranchCheckpoints({ branch_id: 'branch/a #1' })
    await getBranchCheckpoint('cp/a #1')
    await captureInitialBranchCheckpoint({ simulation_run_id: 'save/a #1', command_id: 'initial' })
    await captureCurrentBranchCheckpoint({ simulation_run_id: 'save/a #1' })
    await captureCompletedEventBranchCheckpoint({ simulation_run_id: 'save/a #1', event_id: 'event-1', event_sequence: 1, command_id: 'event' })
    await captureCompletedWeekBranchCheckpoint({ simulation_run_id: 'save/a #1', week: 12, command_id: 'week' })
    await captureAdminActionBranchCheckpoint({ simulation_run_id: 'save/a #1', action_sequence: 1, command_id: 'admin' })
    expect(globalThis.fetch).toHaveBeenNthCalledWith(1, 'http://127.0.0.1:8000/branch-checkpoints?branch_id=branch%2Fa+%231', expect.anything())
    expect(globalThis.fetch).toHaveBeenNthCalledWith(2, 'http://127.0.0.1:8000/branch-checkpoints/cp%2Fa%20%231', expect.anything())
    expect(globalThis.fetch).toHaveBeenNthCalledWith(3, 'http://127.0.0.1:8000/branch-checkpoints/capture-initial', expect.objectContaining({ method: 'POST', body: JSON.stringify({ simulation_run_id: 'save/a #1', command_id: 'initial' }) }))
    expect(globalThis.fetch).toHaveBeenNthCalledWith(4, 'http://127.0.0.1:8000/branch-checkpoints/capture-current', expect.objectContaining({ method: 'POST', body: JSON.stringify({ simulation_run_id: 'save/a #1' }) }))
    expect(globalThis.fetch).toHaveBeenNthCalledWith(5, 'http://127.0.0.1:8000/branch-checkpoints/capture-completed-event', expect.objectContaining({ method: 'POST', body: JSON.stringify({ simulation_run_id: 'save/a #1', event_id: 'event-1', event_sequence: 1, command_id: 'event' }) }))
    expect(globalThis.fetch).toHaveBeenNthCalledWith(6, 'http://127.0.0.1:8000/branch-checkpoints/capture-completed-week', expect.objectContaining({ method: 'POST', body: JSON.stringify({ simulation_run_id: 'save/a #1', week: 12, command_id: 'week' }) }))
    expect(globalThis.fetch).toHaveBeenNthCalledWith(7, 'http://127.0.0.1:8000/branch-checkpoints/capture-admin-action', expect.objectContaining({ method: 'POST', body: JSON.stringify({ simulation_run_id: 'save/a #1', action_sequence: 1, command_id: 'admin' }) }))
  })

  it('lists BranchState metadata and encodes branch state detail ids', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ branch_states: [] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ branch_id: 'branch/a #1' }), { status: 200 }))
    await listBranchStates({ run_id: 'save/a #1' })
    await getBranchState('branch/a #1')
    expect(globalThis.fetch).toHaveBeenNthCalledWith(1, 'http://127.0.0.1:8000/branch-states?run_id=save%2Fa+%231', expect.anything())
    expect(globalThis.fetch).toHaveBeenNthCalledWith(2, 'http://127.0.0.1:8000/branch-states/branch%2Fa%20%231', expect.anything())
  })

  it('lists read-only Run containers and encodes a Run container id on detail lookup', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ run_containers: [] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ run_id: 'save/a #1' }), { status: 200 }))

    await listRunContainers()
    await getRunContainer('save/a #1')

    expect(globalThis.fetch).toHaveBeenNthCalledWith(
      1, 'http://127.0.0.1:8000/run-containers', expect.anything()
    )
    expect(globalThis.fetch).toHaveBeenNthCalledWith(
      2, 'http://127.0.0.1:8000/run-containers/save%2Fa%20%231', expect.anything()
    )
  })

})
